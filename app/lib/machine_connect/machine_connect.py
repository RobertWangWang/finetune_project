import paramiko
import time
import threading
import queue
import os
from typing import Optional, Callable, Generator, Tuple
from pydantic import BaseModel, Field
from loguru import logger   # ✅ 使用 loguru

from app.lib.i18n.config import i18n


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
            if self.config.ssh_private_key:  # 私钥连接
                private_key = paramiko.RSAKey.from_private_key_file(self.config.ssh_private_key)
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
                )  # 密码连接
            logger.info(f"成功连接到 {self.config.ip}")
        except paramiko.AuthenticationException:
            raise PermissionError(i18n.gettext("SSH authentication failed: incorrect username/password/private key"))
        except paramiko.SSHException as e:
            raise ConnectionError(i18n.gettext("SSH connection exception. {error}").format(error=str(e)))
        except Exception as e:
            logger.exception(f"未知错误: 无法连接到 {self.config.ip}")
            raise RuntimeError(
                i18n.gettext("An unknown error occurred during the connection process. {error}").format(error=str(e))
            )

    def test_connection(self) -> (bool, str):
        """功能1：测试SSH账号密码是否正确"""
        try:
            self._connect_ssh()
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
            for port in range(start_port, end_port + 1):
                stdin, stdout, stderr = self.ssh_client.exec_command(f"netstat -tuln | grep ':{port} '")
                output = stdout.read().decode().strip()
                if not output:
                    return port
            return None
        except Exception as e:
            logger.error(f"查询连接端口出问题: {e}")
            return None
        finally:
            self.ssh_client.close()

    def execute_command(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """功能2：执行命令并返回输出和退出状态码"""
        self._connect_ssh()
        stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

        stdout_str = stdout.read().decode().strip()
        stderr_str = stderr.read().decode().strip()
        exit_status = stdout.channel.recv_exit_status()
        return stdout_str, stderr_str, exit_status

    def add_crontab_entry(self, entry, comment=None):
        self._connect_ssh()
        current_crontab, error, _ = self.execute_command("crontab -l 2>/dev/null || echo ''")

        if error and "no crontab" not in error:
            return f"Failed to retrieve the current crontab: {error}"

        if comment:
            entry = f"# {comment}\n{entry}"

        if entry in current_crontab:
            return f""

        new_crontab = current_crontab + "\n" + entry + "\n"

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
        current_crontab, error, _ = self.execute_command("crontab -l")

        if error:
            return f"Failed to retrieve the current crontab: {error}"

        lines = current_crontab.split('\n')
        new_lines = []
        skip_next = False

        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue

            if line.strip().startswith('#') and task_name in line:
                skip_next = True
                continue

            if not line.strip().startswith('#') and task_name in line:
                continue

            new_lines.append(line)

        new_crontab = '\n'.join(new_lines)

        if new_crontab == current_crontab:
            return f""

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
        """功能3：实时监听日志文件"""
        self._connect_ssh()
        self._stop_event.clear()

        command = f"tail -n 1000 -f {log_path}"
        self._tail_channel = self.ssh_client.get_transport().open_session()
        self._tail_channel.exec_command(command)

        buffer = ""
        while not self._stop_event.is_set():
            if self._tail_channel.exit_status_ready():
                break

            if self._tail_channel.recv_ready():
                data = self._tail_channel.recv(1024).decode(errors='ignore')

                if line_by_line:
                    buffer += data
                    lines = buffer.splitlines(True)

                    for line in lines:
                        if line.endswith('\n'):
                            processed_line = line
                            if callback:
                                callback(line.rstrip('\n'))
                            yield line
                        else:
                            buffer = line
                else:
                    if callback:
                        callback(data)
                    yield data
            else:
                time.sleep(0.1)

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

    def get_large_file(self, remote_path: str, chunk_size: int = 4096, timeout: int = 300) -> Generator[str, None, None]:
        """获取大文件内容（流式读取）"""
        self._connect_ssh()
        command = f"cat {remote_path}"
        transport = self.ssh_client.get_transport()
        channel = transport.open_session()
        channel.exec_command(command)
        channel.settimeout(timeout)

        start_time = time.time()
        while not channel.exit_status_ready():
            if time.time() - start_time > timeout:
                channel.close()
                raise TimeoutError(i18n.gettext("File read timeout"))

            if channel.recv_ready():
                data = channel.recv(chunk_size).decode(errors='ignore')
                if data:
                    yield data

            time.sleep(0.05)

        while channel.recv_ready():
            data = channel.recv(chunk_size).decode(errors='ignore')
            if data:
                yield data

        exit_status = channel.recv_exit_status()
        if exit_status != 0:
            stderr_data = ""
            while channel.recv_stderr_ready():
                stderr_data += channel.recv_stderr(1024).decode(errors='ignore')
            raise RuntimeError(i18n.gettext("File read error. {error}").format(error=stderr_data.strip()))

        channel.close()
        self.ssh_client.close()

    def download_file(self, remote_path: str, local_path: str) -> None:
        """从远程机器下载文件到本地"""
        self._connect_ssh()

        if os.path.isdir(local_path):
            remote_filename = os.path.basename(remote_path)
            local_path = os.path.join(local_path, remote_filename)

        sftp = None
        try:
            sftp = self.ssh_client.open_sftp()

            try:
                sftp.stat(remote_path)
            except IOError:
                raise FileNotFoundError(
                    i18n.gettext("The file does not exist: {filepath}").format(filepath=remote_path)
                )

            local_dir = os.path.dirname(local_path)
            if local_dir and not os.path.exists(local_dir):
                os.makedirs(local_dir, exist_ok=True)
                logger.debug(f"已创建本地目录: {local_dir}")

            sftp.get(remote_path, local_path)
            logger.info(f"成功下载文件: {remote_path} -> {local_path}")
        except Exception as e:
            logger.exception(f"下载文件失败: {remote_path}")
            raise RuntimeError(i18n.gettext("Failed to download the file. {error}").format(error=str(e)))
        finally:
            if sftp:
                sftp.close()
            self.ssh_client.close()

    def sftp_upload_with_dirs(self, local_path, remote_path, overwrite=False):
        self._connect_ssh()
        sftp = None
        try:
            sftp = self.ssh_client.open_sftp()

            def remote_file_exists(sftp, remote_path):
                try:
                    sftp.stat(remote_path)
                    return True
                except IOError:
                    return False

            if not overwrite and remote_file_exists(sftp, remote_path):
                logger.info(f"文件已存在，跳过上传: {remote_path}")
                return

            def mkdir_p(sftp, remote_directory):
                if remote_directory == '' or remote_directory == '/':
                    return
                remote_directory = remote_directory.rstrip('/')
                parent_dir, _ = os.path.split(remote_directory)
                if parent_dir and parent_dir != '/':
                    mkdir_p(sftp, parent_dir)
                try:
                    sftp.chdir(remote_directory)
                except IOError:
                    try:
                        sftp.mkdir(remote_directory)
                        sftp.chdir(remote_directory)
                        logger.debug(f"创建远程目录: {remote_directory}")
                    except IOError as e:
                        if not remote_file_exists(sftp, remote_directory):
                            raise IOError(f"无法创建目录 {remote_directory}: {str(e)}")

            remote_dir = os.path.dirname(remote_path)
            if remote_dir:
                mkdir_p(sftp, remote_dir)

            sftp.put(local_path, remote_path)
            logger.info(f"成功上传文件: {local_path} -> {remote_path}")
        except Exception as e:
            logger.exception(f"SFTP 上传失败: {local_path} -> {remote_path}")
            raise
        finally:
            if sftp is not None:
                sftp.close()
            self.ssh_client.close()

    def monitor_service_status(self, service_name: str):
        self._connect_ssh()
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(f'systemctl status {service_name}.service')
            status_output = stdout.read().decode().strip()
            error_output = stderr.read().decode().strip()

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
