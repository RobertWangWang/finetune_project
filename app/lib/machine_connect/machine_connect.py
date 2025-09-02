import paramiko
import time
import logging
import threading
import queue
import os
from typing import Optional, Callable, Generator, Tuple
from pydantic import BaseModel, Field

from app.lib.i18n.config import i18n

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RemoteMachineTool")


class Machine(BaseModel):
    ip: Optional[str] = Field(None, description="机器的 ip")
    ssh_port: Optional[int] = Field(22, description="登陆的端口")
    ssh_user: Optional[str] = Field(None, description="ssh 登陆账号")
    ssh_password: Optional[str] = Field(None, description="登陆的密码")
    ssh_private_key: Optional[str] = Field(None, description="登陆使用的私钥")


class RemoteMachine:
    def __init__(self, config: Machine):
        self.config = config
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self._stop_event = threading.Event()
        self._log_queue = queue.Queue()
        self._tail_thread: Optional[threading.Thread] = None
        self._tail_channel: Optional[paramiko.Channel] = None

    def _connect_ssh(self) -> None:
        """建立SSH连接（支持密码/私钥）"""
        if self.ssh_client and self.ssh_client.get_transport() and self.ssh_client.get_transport().is_active():
            return

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            if self.config.ssh_private_key:
                private_key = paramiko.RSAKey.from_private_key_file(
                    self.config.ssh_private_key
                )
                self.ssh_client.connect(
                    hostname=self.config.ip,
                    port=self.config.ssh_port,
                    username=self.config.ssh_user,
                    pkey=private_key,
                    timeout=10
                )
            else:
                self.ssh_client.connect(
                    hostname=self.config.ip,
                    port=self.config.ssh_port,
                    username=self.config.ssh_user,
                    password=self.config.ssh_password,
                    timeout=10
                )
            logger.info(f"成功连接到 {self.config.ip}")
        except paramiko.AuthenticationException:
            raise PermissionError(i18n.gettext("SSH authentication failed: incorrect username/password/private key"))
        except paramiko.SSHException as e:
            raise ConnectionError(i18n.gettext("SSH connection exception. {error}").format(error=str(e)))
        except Exception as e:
            raise RuntimeError(
                i18n.gettext("An unknown error occurred during the connection process. {error}").format(error=str(e)))

    def test_connection(self) -> (bool, str):
        """功能1：测试SSH账号密码是否正确"""
        try:
            self._connect_ssh()
            # 执行一个简单的命令来验证连接
            stdin, stdout, stderr = self.ssh_client.exec_command("echo 'test'", timeout=5)
            exit_status = stdout.channel.recv_exit_status()
            return exit_status == 0, ""
        except Exception as e:
            logger.error(f"连接测试失败: {str(e)}")
            return False, str(e)
        finally:
            self.close()

    def find_available_port(self, start_port=30000, end_port=40000):
        self._connect_ssh()
        try:
            # 检查端口范围内的每个端口
            for port in range(start_port, end_port + 1):
                # 使用netstat检查端口是否被占用
                stdin, stdout, stderr = self.ssh_client.exec_command(f"netstat -tuln | grep ':{port} '")
                output = stdout.read().decode().strip()
                # 如果没有输出，说明端口未被占用
                if not output:
                    return port
            return None
        except Exception as e:
            print(f"查询连接端口出问题: {e}")
            return None
        finally:
            self.ssh_client.close()

    def execute_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """功能2：执行命令并返回输出和退出状态码"""
        self._connect_ssh()
        stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

        # 读取输出
        stdout_str = stdout.read().decode().strip()
        stderr_str = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()
        return stdout_str, stderr_str, exit_status

    def add_crontab_entry(self, entry, comment=None):
        self._connect_ssh()
        """添加crontab条目"""
        # 获取当前crontab内容
        current_crontab, error, _ = self.execute_command("crontab -l 2>/dev/null || echo ''")

        if error and "no crontab" not in error:
            return f"Failed to retrieve the current crontab: {error}"

        # 添加注释（如果有）
        if comment:
            entry = f"# {comment}\n{entry}"

        # 检查是否已存在相同条目
        if entry in current_crontab:
            return f""

        # 添加新条目
        new_crontab = current_crontab + "\n" + entry + "\n"

        # 更新crontab
        stdin, stdout, stderr = self.ssh_client.exec_command("crontab -")
        stdin.write(new_crontab)
        stdin.close()

        error = stderr.read().decode().strip()
        if error:
            return f"Failed to update crontab: {error}"

        return ""

    def add_reboot_task(self, command, task_name=None):
        """添加开机启动任务"""
        entry = f"@reboot {command}"
        comment = f"Reboot task: {task_name}" if task_name else "Reboot task"
        return self.add_crontab_entry(entry, comment)

    def remove_reboot_task_by_name(self, task_name) -> str:
        self._connect_ssh()
        """根据任务名称删除crontab任务"""
        # 获取当前crontab内容
        current_crontab, error, _ = self.execute_command("crontab -l")

        if error:
            return f"Failed to retrieve the current crontab: {error}"

        # 按行分割并过滤掉包含任务名称的行
        lines = current_crontab.split('\n')
        new_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            # 如果上一行是注释且包含任务名称，则跳过当前行（命令）
            if skip_next:
                skip_next = False
                continue

            # 检查是否是注释行且包含任务名称
            if line.strip().startswith('#') and task_name in line:
                skip_next = True  # 标记下一行（命令）也需要删除
                continue

            # 检查是否是非注释行包含任务名称（直接匹配命令）
            if not line.strip().startswith('#') and task_name in line:
                continue

            new_lines.append(line)

        # 重新构建crontab内容
        new_crontab = '\n'.join(new_lines)

        # 如果内容没有变化，说明没找到匹配的任务
        if new_crontab == current_crontab:
            return f""

        # 更新crontab
        stdin, stdout, stderr = self.ssh_client.exec_command("crontab -")
        stdin.write(new_crontab)
        stdin.close()

        error = stderr.read().decode().strip()
        if error:
            return f"Failed to update crontab: {error}"

        return ""

    def tail_log(
            self,
            log_path: str,
            callback: Optional[Callable[[str], None]] = None,
            line_by_line: bool = True
    ) -> Generator[str, None, None]:
        """
        功能3：实时监听日志文件
        使用tail -f命令实现实时日志监控

        :param log_path: 远程机器上的日志文件路径
        :param callback: 可选的回调函数，用于处理每行日志
        :param line_by_line: 是否按行返回日志（否则按块返回）
        :return: 生成器，产生日志行或日志块
        """
        self._connect_ssh()
        self._stop_event.clear()

        # 启动tail命令
        command = f"tail -n 1000 -f {log_path}"
        self._tail_channel = self.ssh_client.get_transport().open_session()
        self._tail_channel.exec_command(command)

        buffer = ""
        while not self._stop_event.is_set():
            if self._tail_channel.exit_status_ready():
                break

            # 检查是否有数据可读
            if self._tail_channel.recv_ready():
                data = self._tail_channel.recv(1024).decode(errors='ignore')

                if line_by_line:
                    # 按行处理
                    buffer += data
                    lines = buffer.splitlines(True)  # 保留换行符

                    for line in lines:
                        if line.endswith('\n'):
                            # 完整的一行 - 保持换行符不变
                            processed_line = line  # 不要rstrip，保持原样
                            if callback:
                                # 如果回调函数需要处理，可以去掉换行符，但yield时保持原样
                                callback(line.rstrip('\n'))
                            yield line  # 这里直接yield包含换行符的完整行
                        else:
                            # 不完整的行，保留在缓冲区
                            buffer = line
                else:
                    # 按块处理
                    if callback:
                        callback(data)
                    yield data
            else:
                # 短暂休眠以避免CPU占用过高
                time.sleep(0.1)

        # 清理
        if self._tail_channel:
            self._tail_channel.close()
            self._tail_channel = None
        self.ssh_client.close()

    def stop_tail(self):
        """停止实时日志监听"""
        self._stop_event.set()
        if self._tail_channel:
            self._tail_channel.close()
            self._tail_channel = None

    def get_large_file(self, remote_path: str, chunk_size: int = 4096, timeout: int = 300) -> Generator[
        str, None, None]:
        """
        获取大文件内容（流式读取，适用于大文件）

        :param remote_path: 远程文件路径
        :param chunk_size: 每次读取的块大小
        :param timeout: 整体超时时间
        :return: 生成器，产生文件内容块
        """
        self._connect_ssh()
        command = f"cat {remote_path}"
        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)
        channel.settimeout(timeout)

        start_time = time.time()
        while not channel.exit_status_ready():
            # 检查超时
            if time.time() - start_time > timeout:
                channel.close()
                raise TimeoutError(i18n.gettext("File read timeout"))

            # 检查是否有数据可读
            if channel.recv_ready():
                data = channel.recv(chunk_size).decode(errors='ignore')
                if data:
                    yield data

            # 短暂休眠
            time.sleep(0.05)

        # 获取剩余数据
        while channel.recv_ready():
            data = channel.recv(chunk_size).decode(errors='ignore')
            if data:
                yield data

        # 检查错误
        exit_status = channel.recv_exit_status()
        if exit_status != 0:
            # 尝试获取错误信息
            stderr_data = ""
            while channel.recv_stderr_ready():
                stderr_data += channel.recv_stderr(1024).decode(errors='ignore')
            raise RuntimeError(i18n.gettext("File read error. {error}").format(error=stderr_data.strip()))

        channel.close()
        self.ssh_client.close()

    def download_file(self, remote_path: str, local_path: str) -> None:
        """
        从远程机器下载文件到本地

        Args:
            remote_path: 远程机器上的文件路径
            local_path: 本地保存路径（可以是目录或完整文件路径）

        Raises:
            RuntimeError: 如果下载过程中出现错误
        """
        # 确保SSH连接已建立
        self._connect_ssh()

        # 如果本地路径是目录，则使用远程文件名
        if os.path.isdir(local_path):
            remote_filename = os.path.basename(remote_path)
            local_path = os.path.join(local_path, remote_filename)

        sftp = None
        try:
            # 创建SFTP客户端
            sftp = self.ssh_client.open_sftp()

            # 检查远程文件是否存在
            try:
                sftp.stat(remote_path)
            except IOError:
                raise FileNotFoundError(
                    i18n.gettext("The file does not exist: {filepath}").format(filepath=remote_path))

            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
                logger.debug(f"已创建本地目录: {local_dir}")

            # 下载文件
            sftp.get(remote_path, local_path)
            logger.info(f"成功下载文件: {remote_path} -> {local_path}")
        except Exception as e:
            raise RuntimeError(i18n.gettext("Failed to download the file. {error}").format(error=str(e)))
        finally:
            if sftp:
                sftp.close()
            self.ssh_client.close()

    def sftp_upload_with_dirs(self, local_path, remote_path, overwrite=False):
        self._connect_ssh()

        sftp = None
        try:
            # 连接服务器
            sftp = self.ssh_client.open_sftp()

            def remote_file_exists(sftp, remote_path):
                try:
                    sftp.stat(remote_path)
                    return True
                except IOError:
                    return False

            # 如果文件存在且不覆盖，则跳过
            if not overwrite and remote_file_exists(sftp, remote_path):
                logging.info(f"文件已存在，跳过上传: {remote_path}")
                return

            # 递归创建目录函数
            def mkdir_p(sftp, remote_directory):
                if remote_directory == '' or remote_directory == '/':
                    return

                # 标准化路径，处理多余的斜杠
                remote_directory = remote_directory.rstrip('/')
                parent_dir, dir_name = os.path.split(remote_directory)

                # 递归创建父目录
                if parent_dir and parent_dir != '/':
                    mkdir_p(sftp, parent_dir)

                try:
                    sftp.chdir(remote_directory)
                except IOError:
                    try:
                        sftp.mkdir(remote_directory)
                        sftp.chdir(remote_directory)
                    except IOError as e:
                        # 检查目录是否真的不存在
                        if not remote_file_exists(sftp, remote_directory):
                            raise IOError(f"无法创建目录 {remote_directory}: {str(e)}")

            # 获取远程目录路径
            remote_dir = os.path.dirname(remote_path)

            # 创建所有缺失的目录
            if remote_dir:
                mkdir_p(sftp, remote_dir)

            # 上传文件
            sftp.put(local_path, remote_path)
        finally:
            # 关闭连接
            if sftp is not None:
                sftp.close()
            self.ssh_client.close()

    def monitor_service_status(self, service_name: str):
        self._connect_ssh()
        try:
            # 执行 `systemctl status`
            stdin, stdout, stderr = self.ssh_client.exec_command(f'systemctl status {service_name}.service')
            status_output = stdout.read().decode().strip()
            error_output = stderr.read().decode().strip()

            # 解析状态
            if "Active: active (running)" in status_output:
                return "Starting", status_output
            elif "Active: inactive (dead)" in status_output:
                return "Success", status_output
            elif "Active: failed" in status_output:
                return "Failed", status_output
            elif "could not be found" in error_output:
                return "Error", error_output
            else:
                return "Error", status_output

        finally:
            self.ssh_client.close()

    def close(self) -> None:
        """关闭所有连接"""
        self.stop_tail()
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
