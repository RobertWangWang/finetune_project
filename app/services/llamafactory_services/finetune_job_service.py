import asyncio
import json
import logging
import os
import subprocess
import tempfile
import threading
import time
import traceback
from asyncio import events
from typing import Generator, List, Optional

import yaml
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.middleware.context import get_current_locale, set_current_locale
from app.api.middleware.deps import manual_get_db
from app.db.llamafactory_db_model import finetune_job_db, finetune_config_db, release_db
from app.db.dataset_db_model import dataset_version_db
from app.db.common_db_model import machine_db
from app.db.dataset_db_model.dataset_version_db import DatasetVersionORM, DatasetVersion
from app.db.llamafactory_db_model.finetune_config_db import FinetuneConfigORM, FinetuneConfig, ConfigType
from app.db.llamafactory_db_model.finetune_job_db import FinetuneJobORM
from app.db.common_db_model.machine_db import MachineORM, Machine
from app.db.llamafactory_db_model.release_db import ReleaseORM
from app.lib.finetune_path.path_build import build_work_path, build_config_path, build_logs_path, build_dataset_path, \
    build_deepspeed_path, build_output_path, build_train_dataset_info_json_path, build_train_dataset_info_path, \
    build_local_logs_path, build_lora_output_tar_path, build_local_lora_model_path
from app.lib.i18n.config import i18n
from app.lib.machine_connect import machine_connect
from app.lib.machine_connect.machine_connect import RemoteMachine
from app.models.dataset_models.dataset_version_model import DatasetType, DatasetVersionItem
from app.models.llamafactory_models.finetune_config_model import FinetuneConfigItem
from app.models.llamafactory_models.finetune_job_model import FinetuneJobList, FinetuneJobItem, FinetuneJobCreate, \
    FinetuneJobRunningExampleRequest, FinetuneJobRunningExample, FinetuneJobStatus
from app.models.user_model import User
from app.services.dataset_services.dataset_version_service import dataset_version_file_path_builder
from app.services.llamafactory_services.finetune_job_example_template.sft_template import build_sft_template, \
    build_sft_template_params
from app.services.llamafactory_services.finetune_job_example_template.sft_template_en import build_sft_template_en
from app.services.common_services.machine_service import orm_machine_to_item, machine_orm_to_client

loop = asyncio.new_event_loop()


def run_event_loop():
    """
        新建一个 asyncio 循环，用于异步监控任务。
        通过线程在后台常驻运行。
    """
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_event_loop, daemon=True).start()


def task_name_build(job_id: str, machine_id: str) -> str:
    return f"{job_id}_{machine_id}"


def llamafactory_yaml_build(dict_by_module: dict) -> str:
    all_yaml = ""
    for module in dict_by_module:
        config = dict_by_module.get(module)
        yaml_str = yaml.dump(config, sort_keys=True)
        all_yaml += f"### {module}\n{yaml_str}\n\n"
    return all_yaml


def build_sft_example(job_id: str, finetune_config_orm_list: list[FinetuneConfigORM],
                      machine: MachineORM, dataset_version_orm: DatasetVersionORM,
                      local: str, node_finetune_machine_list: list[MachineORM]) -> FinetuneJobRunningExample:
    """
        根据机器数量、GPU 数量，决定是否加 torchrun 或 deepspeed。
        把训练命令写入 systemd service，然后通过 SSH 下发到远程机器。
    """
    # 构建多机器微调命令
    node_num = len(node_finetune_machine_list)
    node_index = 0
    master = node_finetune_machine_list[0]
    for index, value in enumerate(node_finetune_machine_list):
        if value.id == machine.id:
            node_index = index

    if len(node_finetune_machine_list) == 1:
        if master.gpu_count > 1:
            train_cmd = f"/bin/bash -c 'FORCE_TORCHRUN=1 llamafactory-cli train {build_config_path(job_id)}'"
        else:
            train_cmd = f"llamafactory-cli train {build_config_path(job_id)}"
    else:
        master_internal_ip = master.client_config.get("internal_ip")
        train_cmd = f"/bin/bash -c 'FORCE_TORCHRUN=1 NNODES={node_num} NODE_RANK={node_index} MASTER_ADDR={master_internal_ip} MASTER_PORT=29500 llamafactory-cli train {build_config_path(job_id)}'"

    # 启动微调的任务
    cmds = [
        f"""cat << 'EOF' > /etc/systemd/system/{job_id}.service 
[Unit]
Description=finetune job

[Service]
Type=simple                       
WorkingDirectory={build_work_path(job_id)}
ExecStart={train_cmd}
Restart=no
StandardOutput=file:{build_logs_path(job_id)}
StandardError=file:{build_logs_path(job_id)}
Environment=USE_MODELSCOPE_HUB=true

[Install]
WantedBy=multi-user.target
EOF
                    """,
        "systemctl daemon-reload",
        f"systemctl start {job_id}.service"
    ]
    # 所有配置按照模块划分
    config_dict = {finetune_config.config_type: finetune_config for finetune_config in finetune_config_orm_list}

    # 多机多卡时候需要使用 deepspeed 配置
    deepspeed_config_json = ""
    deepspeed_config = config_dict.get(ConfigType.DeepspeedArguments)
    if deepspeed_config is not None:
        deepspeed_config_json = json.dumps(deepspeed_config.config, ensure_ascii=False, indent=2)

    # 微调参数构建
    train_yaml_dict = {}
    for config_type in config_dict:
        if config_type == ConfigType.DeepspeedArguments:
            continue
        # dataset 位置配置
        if config_type == ConfigType.DataArguments:
            config_dict[config_type].config["dataset"] = dataset_version_orm.id
            config_dict[config_type].config["dataset_dir"] = build_train_dataset_info_path(job_id)
        # output 的输出地址配置
        if config_type == ConfigType.OutputArguments:
            config_dict[config_type].config["output_dir"] = build_output_path(job_id)
        if config_type == ConfigType.TrainingArguments:
            if deepspeed_config_json != "":
                # deepspeed 位置配置
                config_dict[config_type].config["deepspeed"] = build_deepspeed_path(job_id)
        # 根据 config_type 分块构建成 yaml 文件
        train_yaml_dict[config_type] = config_dict[config_type].config
    llamafactory_yaml = llamafactory_yaml_build(train_yaml_dict)

    # 前端展示的 markdown 构建
    markdown_template_func = build_sft_template
    if local == "en":
        markdown_template_func = build_sft_template_en
    markdown = markdown_template_func(build_sft_template_params(
        dataset=dataset_version_orm,
        deepspeed_config_json=deepspeed_config_json,
        job_id=job_id,
        train_yaml=llamafactory_yaml,
        cmds=cmds
    ))

    machine_client = machine_connect.Machine(
        ip=machine.client_config.get("ip"),
        ssh_port=machine.client_config.get("ssh_port"),
        ssh_user=machine.client_config.get("ssh_user"),
        ssh_password=machine.client_config.get("ssh_password"),
        ssh_private_key=machine.client_config.get("ssh_private_key")
    )

    return FinetuneJobRunningExample(
        machine_id=machine.id,
        machine_name=machine.hostname,
        machine_client=machine_client,
        cmds=cmds,
        train_yaml=llamafactory_yaml,
        deepspeed_json=deepspeed_config_json,
        markdown=markdown,
        dataset_path=dataset_version_file_path_builder(dataset_version_orm.id)
    )


def _query_finetune_config_and_check_exit(session: Session, current_user: User, finetune_config_id_list: list[str]) -> \
        List[FinetuneConfigORM]:
    finetune_config_orm_list, total = finetune_config_db.list(session, current_user, 1, len(finetune_config_id_list),
                                                              ids=finetune_config_id_list)

    if total != len(finetune_config_id_list):
        finetune_config_orm_dict = {orm.id: orm for orm in finetune_config_orm_list}
        for finetune_config_id in finetune_config_id_list:
            find = finetune_config_orm_dict.get(finetune_config_id)
            if find is None:
                raise HTTPException(status_code=500,
                                    detail=i18n.gettext("FinetuneConfig not found. id: {id}").format(
                                        id=finetune_config_id))

    finetune_config_orm_dict = {orm.id: orm for orm in finetune_config_orm_list}
    # 按照输入id列表的顺序重新排序结果
    ordered_finetune_config_orm_list = [
        finetune_config_orm_dict[finetune_config_id]
        for finetune_config_id in finetune_config_id_list
        if finetune_config_id in finetune_config_orm_dict
    ]
    return ordered_finetune_config_orm_list


def _query_machine_and_check_exit(session: Session, current_user: User, node_finetune_machine_id_list: list[str]) -> \
        List[MachineORM]:
    machine_orm_list, total = machine_db.list_machines(session, current_user, 1,
                                                       len(node_finetune_machine_id_list),
                                                       ids=node_finetune_machine_id_list)
    if total != len(node_finetune_machine_id_list):
        machine_orm_dict = {machine.id: machine for machine in machine_orm_list}
        for machine_id in node_finetune_machine_id_list:
            machine = machine_orm_dict.get(machine_id)
            if machine is None:
                raise HTTPException(status_code=500,
                                    detail=i18n.gettext("Machine not found. id: {id}").format(id=machine_id))

    machine_orm_dict = {machine.id: machine for machine in machine_orm_list}
    # 按照输入ID列表的顺序重新排序结果
    ordered_machine_orm_list = [
        machine_orm_dict[machine_id]
        for machine_id in node_finetune_machine_id_list
        if machine_id in machine_orm_dict
    ]
    return ordered_machine_orm_list


def orm_to_item(orm: FinetuneJobORM) -> FinetuneJobItem:
    item = FinetuneJobItem(
        id=orm.id,
        name=orm.name,
        description=orm.description,
        status=orm.status,

        stage=orm.stage,
        finetune_method=orm.finetune_method,
        dataset_version=DatasetVersionItem(**orm.dataset_version.to_dict()),
        finetune_config_list=[FinetuneConfigItem(**config.to_dict()) for config in orm.finetune_config_list],
        node_finetune_machines=[orm_machine_to_item(machine) for machine in orm.node_finetune_machine_list],

        error_info=orm.error_info,
        done_node_num=orm.done_node_num,
        release_id=orm.release_id,

        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
    return item


def get_large_local_file(file_path: str, chunk_size: int = 4096, timeout: int = 300) -> Generator[str, None, None]:
    """
    获取本地大文件内容（流式读取，适用于大文件）

    :param file_path: 本地文件路径
    :param chunk_size: 每次读取的块大小
    :param timeout: 整体超时时间
    :return: 生成器，产生文件内容块
    :raises: TimeoutError, RuntimeError
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(i18n.gettext("The file does not exist: {filepath}").format(filepath=file_path))

    if not os.path.isfile(file_path):
        raise RuntimeError(i18n.gettext("The path is not a file: {filepath}").format(filepath=file_path))

    start_time = time.time()
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                raise TimeoutError(i18n.gettext("File read timeout"))

            # 读取数据块
            data = f.read(chunk_size)
            if not data:
                break

            yield data

            # 短暂休眠（如果需要）
            time.sleep(0.001)  # 比远程读取更短的休眠时间


def finetune_job_logs(session: Session, current_user: User, id: str, machine_id: str) -> Generator[str, None, None]:
    job_orm = finetune_job_db.get(session, current_user, id)
    if job_orm is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Finetune job not found. id: {id}").format(id=id))
    if job_orm.status == FinetuneJobStatus.Cancel or job_orm.status == FinetuneJobStatus.Success or job_orm.status == FinetuneJobStatus.Failed:
        return get_large_local_file(build_local_logs_path(job_orm.id, machine_id), chunk_size=4096, timeout=3600)

    machine_orm: Optional[MachineORM] = None
    for machine in job_orm.node_finetune_machine_list:
        if machine.id == machine_id:
            machine_orm = MachineORM(**machine.to_dict())
            break
    if machine_orm is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Machine not found. id: {id}").format(id=machine_id))

    machine_client = machine_orm.to_remote_machine()
    ok, error_info = machine_client.test_connection()
    if not ok:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Machine connection test failed. error: {error}").format(error_info))

    if job_orm.status == FinetuneJobStatus.Starting:
        return machine_client.tail_log(
            log_path=build_logs_path(job_orm.id)
        )
    else:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Only support Starting, Cancel, Success, Failed status finetune job"))


def list_finetune_job(session: Session, current_user: User, page_no: int, page_size: int, name: str = None,
                      status: Optional[FinetuneJobStatus] = None,
                      stage: Optional[DatasetType] = None,
                      finetune_method: Optional[str] = None) -> FinetuneJobList:
    finetune_job_orm_list, total = finetune_job_db.list_jobs(session, current_user, page_no, page_size, name, status,
                                                             finetune_method)

    return FinetuneJobList(
        data=[orm_to_item(finetune_job_orm) for finetune_job_orm in finetune_job_orm_list],
        count=total,
    )


def copy_dataset_to_machine(machine: RemoteMachine, local_path: str, job_id: str):
    # 本地用 jq 将 jsonl 文件转化为 json 文件
    output_file = os.path.splitext(local_path)[0] + ".json"
    if not os.path.exists(output_file):
        command = f"jq -s '.' {local_path} > {output_file}"
        subprocess.run(command, shell=True, check=True)
    else:
        logging.info(f"Output file {output_file} already exists, skipping...")

    # 将 json 文件上传到远程服务器
    name = os.path.basename(output_file)
    dataset_version_id = name.removesuffix(".json")
    # 该方法内部也会判定 dataset 文件是否存在，存在则跳过上传
    machine.sftp_upload_with_dirs(output_file, build_dataset_path(dataset_version_id))

    temp_path = os.path.join(tempfile.gettempdir(), f"temp_dataset_json_{job_id}.json")
    try:
        # 写入内容
        dataset_info_json = f"""
{{
   "{dataset_version_id}": {{
      "file_name": "../{dataset_version_id}.json"
   }}
}}
            """
        with open(temp_path, 'w') as temp_file:
            temp_file.write(dataset_info_json)
        machine.sftp_upload_with_dirs(temp_path, build_train_dataset_info_json_path(job_id))
    finally:
        # 确保文件被删除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logging.info(f"已删除临时文件: {temp_path}")


def copy_train_config(machine: RemoteMachine, train_config: str, job_id: str):
    temp_path = os.path.join(tempfile.gettempdir(), f"temp_train_{job_id}.yaml")

    try:
        # 写入内容
        with open(temp_path, 'w') as temp_file:
            temp_file.write(train_config)
        machine.sftp_upload_with_dirs(temp_path, build_config_path(job_id))
    finally:
        # 确保文件被删除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logging.info(f"已删除临时文件: {temp_path}")


def copy_deepspeed_config(machine: RemoteMachine, deepspeed_config: str, job_id: str):
    temp_path = os.path.join(tempfile.gettempdir(), f"temp_deepspeed_{job_id}.json")

    try:
        # 写入内容
        with open(temp_path, 'w') as temp_file:
            temp_file.write(deepspeed_config)
        machine.sftp_upload_with_dirs(temp_path, build_deepspeed_path(job_id))
    finally:
        # 确保文件被删除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logging.info(f"已删除临时文件: {temp_path}")


async def init_finetune_job(user: User, id: str, local: str):
    """
        在用户提交微调任务后，负责初始化任务所需的环境和文件，并更新数据库里的任务状态。
        id: finetune_job_db orm id
    """
    update_status = FinetuneJobStatus.Init
    error_info = ""
    try:
        with manual_get_db() as session:
            examples = finetune_job_running_example(session, user, FinetuneJobRunningExampleRequest(
                id=id
            ), local)
            """
                class FinetuneJobRunningExampleRequest(BaseModel):
                    id: Optional[str] = Field(None, description="id")
                    stage: Optional[DatasetType] = Field(None, description="微调类型")
                    dataset_version_id: Optional[str] = Field(None, description="数据集版本id")
                    finetune_config_id_list: list[str] = Field(None, description="配置列表id")
                    node_finetune_machine_id_list: list[str] = Field(None, description="微调 node 机器 id 列表")
            """
            for example in examples:
                machine_client = RemoteMachine(example.machine_client)
                ok, error_info = machine_client.test_connection()
                """
                    创建远程机器客户端。
                    测试是否能连通（SSH 连接）。
                    如果失败 → 抛出异常。
                """
                if not ok:
                    raise HTTPException(status_code=500,
                                        detail=i18n.gettext("Machine connection test failed. error: {error}",
                                                            local=local).format(error=error_info))
                # 拷贝微调数据集
                copy_dataset_to_machine(machine_client, example.dataset_path, id)
                # llamafactory-cli 微调配置文件准备
                copy_train_config(machine_client, example.train_yaml, id)
                # deepspeed 微调配置文件准备
                if example.deepspeed_json != "":
                    copy_deepspeed_config(machine_client, example.deepspeed_json, id)
    except Exception as e:
        traceback.print_exc()
        update_status = FinetuneJobStatus.Error
        error_info = str(e)
    finally:
        with manual_get_db() as session:
            update_dict = {
                "status": update_status,
                "error_info": error_info,
            }
            if update_status == FinetuneJobStatus.Error:
                update_dict["end_at"] = int(time.time())
            finetune_job_db.update(session, user, id, update_dict)


def get_finetune_method(configs):
    for config in configs:
        finetuning_method = config.config.get("finetuning_type")
        if finetuning_method and finetuning_method != "":
            return finetuning_method
    return ""


def create_finetune_job(session: Session, current_user: User,
                        create: FinetuneJobCreate) -> FinetuneJobItem:

    """
    class FinetuneJobCreate(BaseModel):
        name: str = Field(..., description="任务名称")
        description: str = Field(..., description="任务描述")

        stage: DatasetType = Field(..., description="微调类型")
        dataset_version_id: str = Field(..., description="数据集版本id")
        finetune_config_id_list: list[str] = Field(..., description="配置列表id")

        node_finetune_machine_id_list: list[str] = Field(None, description="微调 node 机器 id 列表")
    """

    if create.stage != DatasetType.SupervisedFineTuning: ### 监督式微调
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Parameter verification failed. {param}").format(param="stage"))

    dataset_version_orm = dataset_version_db.get(session, current_user, create.dataset_version_id)
    if dataset_version_orm is None: ### 数据集版本
        raise HTTPException(status_code=500, detail=i18n.gettext("Dataset version not found. id: {id}").format(
            id=create.dataset_version_id))

    finetune_config_orm_list = _query_finetune_config_and_check_exit(session, current_user,
                                                                     create.finetune_config_id_list) ### 查询微调配置是否都存在

    machine_orm_list = _query_machine_and_check_exit(session, current_user, create.node_finetune_machine_id_list) ### 查询机器是否都存在
    if len(machine_orm_list) == 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Machine not found. id: {id}").format(
                                id=','.join(create.node_finetune_machine_id_list)))

    # 如果机器的 gpu 数量大于 1 或者机器数量大于 1 则校验是否存在 deepspeed 配置
    if machine_orm_list[0].gpu_count > 1 or len(machine_orm_list) > 1:
        find = False
        for config in finetune_config_orm_list:
            if config.config_type == ConfigType.DeepspeedArguments:
                find = True
        if not find:
            raise HTTPException(status_code=500, detail=i18n.gettext(
                "In cases of single machine with multiple cards or multiple machines, the DeepSpeed configuration must be chosen"))

    orm = finetune_job_db.create(session, current_user, FinetuneJobORM(
        name=create.name,
        description=create.description,
        status=FinetuneJobStatus.Initializing,
        stage=create.stage,
        finetune_method=get_finetune_method(finetune_config_orm_list),
        dataset_version=DatasetVersion(**dataset_version_orm.to_dict()),
        finetune_config_list=[FinetuneConfig(**orm.to_dict()) for orm in finetune_config_orm_list],
        node_finetune_machine_list=[Machine(**machine.to_dict()) for machine in machine_orm_list],
        error_info="",
        done_node_num=0,
        start_at=0,
        end_at=0,
        release_id="",
        local=get_current_locale()
    ))
    # 异步执行初始化过程
    asyncio.run_coroutine_threadsafe(init_finetune_job(current_user, orm.id, get_current_locale()), loop)
    return orm_to_item(orm)


def finetune_job_running_example(session: Session, current_user: User, req: FinetuneJobRunningExampleRequest,
                                 local: str) -> list[FinetuneJobRunningExample]:
    job_id = "__job_id__"
    if req.id is not None:
        job_orm = finetune_job_db.get(session, current_user, req.id)
        if job_orm is None:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Finetune job not found. id: {id}", local=local).format(id=req.id))
        finetune_config_orm_list = job_orm.finetune_config_list
        node_finetune_machine_list = job_orm.node_finetune_machine_list
        dataset_version_orm = job_orm.dataset_version
        job_id = job_orm.id
    else:
        if req.stage != DatasetType.SupervisedFineTuning:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Parameter verification failed. {param}", local=local).format(
                                    param="finetune_type"))

        finetune_config_orm_list = _query_finetune_config_and_check_exit(session, current_user,
                                                                         req.finetune_config_id_list)
        node_finetune_machine_list = _query_machine_and_check_exit(session, current_user,
                                                                   req.node_finetune_machine_id_list)
        dataset_version_orm = dataset_version_db.get(session, current_user, req.dataset_version_id)
        if dataset_version_orm is None:
            raise HTTPException(status_code=500, detail=i18n.gettext("Dataset version not found. id: {id}").format(
                id=req.dataset_version_id))

    examples = []
    for node in node_finetune_machine_list:
        example = build_sft_example(job_id, finetune_config_orm_list, node, dataset_version_orm, local,
                                    node_finetune_machine_list)
        examples.append(example)
    return examples


async def watch_job_status_by_machine(user: User, job_id: str, machine_id: str, local: str):
    set_current_locale(local)

    try:
        machine_client_failed_num = 0
        while True:
            time.sleep(10)

            with manual_get_db() as session:
                job_orm = finetune_job_db.get(session, user, job_id)
                if job_orm is None:
                    logging.error(
                        f"watch_job_status_by_machine failed. Finetune job not found. job_id: {job_id}. machine_id: {machine_id}")
                    break

                # 机器连接判定，如果超过10次连接失败，则更新整体任务状态为失败
                machine_client = machine_orm_to_client(job_orm.get_node_by_id(machine_id))
                ok, error_info = machine_client.test_connection()
                if not ok:
                    machine_client_failed_num = machine_client_failed_num + 1
                    if machine_client_failed_num > 10:
                        finetune_job_db.update(session, user, job_id, {
                            "status": FinetuneJobStatus.Error,
                            "error_info": i18n.gettext(
                                "Machine connection has failed more than 10 times in a row, fine-tuning terminated",
                                local=local),
                            "end_at": int(time.time()),
                        })
                        break
                    else:
                        continue

            # 获取机器服务状态
            service_status, error_info = machine_client.monitor_service_status(job_id)
            # 获取服务的状态
            with manual_get_db() as new_session:
                job_orm = finetune_job_db.get(new_session, user, job_id)
            # 如果该机器的任务是运行中，但是服务整个服务状态并不是运行中，则将该机器的任务终止和清除 service
            if service_status == FinetuneJobStatus.Starting.name:
                if job_orm.status != FinetuneJobStatus.Starting:
                    out, error, code = machine_client.execute_command(f"systemctl stop {job_id}.service")
                    if code != 0:
                        logging.error(f"stop machine id: {machine_id} {job_id}.service failed. error: {error}")

                    out, error, code = machine_client.execute_command(
                        f"rm -rf /etc/systemd/system/{job_id}.service")
                    if code != 0:
                        logging.error(f"remove machine id: {machine_id} {job_id}.service failed. error: {error}")
                    break
                else:
                    continue
            # 如果该机器的任务执行失败
            elif service_status == FinetuneJobStatus.Failed.name or service_status == FinetuneJobStatus.Error.name:
                # 如果任务也没有运行中, 这时候清除服务的 service 和退出监控
                if job_orm.status != FinetuneJobStatus.Starting:
                    out, error, code = machine_client.execute_command(
                        f"rm -rf /etc/systemd/system/{job_id}.service")
                    if code != 0:
                        logging.error(f"remove machine id: {machine_id} {job_id}.service failed. error: {error}")
                    break
                else:
                    # 任务也是失败，则将任务再次更新为服务状态，并拷贝日志文件
                    machine_client.download_file(build_logs_path(job_id), build_local_logs_path(job_id, machine_id))
                    with manual_get_db() as new_session:
                        finetune_job_db.update(new_session, user, job_id, {
                            "status": service_status,
                            "error_info": error_info,
                            "end_at": int(time.time()),
                        })
                        # 这里继续循环，等待下次自动退出
                    continue
            else:
                # 执行成功
                done_node_num = job_orm.done_node_num
                done_node_num = done_node_num + 1

                status = FinetuneJobStatus.Starting
                end_at = 0
                release_id = ""
                # 结束的数量等于机器的数量则将整体状态更新为成功
                if done_node_num == len(job_orm.node_finetune_machine_list):
                    status = FinetuneJobStatus.Success
                    end_at = int(time.time())
                    # 将远程的微调的模型文件拷贝到本地
                    master_machine_client = machine_orm_to_client(job_orm.node_finetune_machine_list[0])
                    master_machine_client.execute_command(
                        f"tar -czvf {build_lora_output_tar_path(job_id)} -C {build_output_path(job_id)}/.. output",
                        timeout=3600)
                    master_machine_client.download_file(build_lora_output_tar_path(job_id),
                                                        build_local_lora_model_path(job_id))
                    # 创建制品
                    release = ReleaseORM(
                        name=job_orm.name,
                        description=job_orm.description,
                        base_model=job_orm.get_base_model(),
                        stage=job_orm.stage,
                        finetune_method=get_finetune_method(job_orm.finetune_config_list),
                        job_id=job_orm.id,
                        finetune_model_path=build_local_lora_model_path(job_id),
                    )
                    with manual_get_db() as new_session:
                        release = release_db.create_release(new_session, User(id=job_orm.user_id, group_id=job_orm.group_id), release)
                        release_id = release.id

                # 拷贝执行日志文件
                machine_client.download_file(build_logs_path(job_id), build_local_logs_path(job_id, machine_id))
                # todo 加全局锁
                with manual_get_db() as new_session:
                    finetune_job_db.update(new_session, user, job_id, {
                        "status": status,
                        "error_info": "",
                        "done_node_num": done_node_num,
                        "end_at": end_at,
                        "release_id": release_id
                    })

                # 清除 service
                out, error, code = machine_client.execute_command(f"rm -rf /etc/systemd/system/{job_id}.service")
                if code != 0:
                    logging.error(f"remove machine id: {machine_id} {job_id}.service failed. error: {error}")
                break
    except Exception as e:
        traceback.print_exc()
        with manual_get_db() as new_session:
            finetune_job_db.update(new_session, user, job_id, {
                "status": FinetuneJobStatus.Error,
                "error_info": str(e),
                "end_at": int(time.time()),
            })


def start_finetune_job(session: Session, current_user: User,
                       id: str) -> FinetuneJobItem:
    job_orm = finetune_job_db.get(session, current_user, id)
    if job_orm is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Finetune job not found. id: {id}").format(id=id))

    if job_orm.status != FinetuneJobStatus.Init:
        raise HTTPException(status_code=500, detail=i18n.gettext("Only support start Init status finetune job"))

    examples = finetune_job_running_example(session, current_user, FinetuneJobRunningExampleRequest(
        id=id
    ), local=get_current_locale())
    print(examples)
    status = FinetuneJobStatus.Starting
    error_info = ""
    try:
        for example in examples:
            print("---------",example)
            machine_client = RemoteMachine(example.machine_client)
            ok, error_info = machine_client.test_connection()
            if not ok:
                raise HTTPException(status_code=500,
                                    detail=i18n.gettext("Machine connection test failed. error: {error}").format(
                                        error_info))
            for cmd in example.cmds:
                print("---------",cmd)
                out, error, code = machine_client.execute_command(cmd, timeout=180)
                if code != 0:
                    raise HTTPException(status_code=500,
                                        detail=i18n.gettext(
                                            "Start finetune job failed. exit_code: {exit_code}, error: {error}").format(
                                            exit_code=code, error=error))

            asyncio.run_coroutine_threadsafe(watch_job_status_by_machine(current_user, id, example.machine_id,
                                                                         get_current_locale()), loop)
    except Exception as e:
        traceback.print_exc()
        error_info = str(e)
        status = FinetuneJobStatus.Error

    orm = finetune_job_db.update(session, current_user, id, {
        "status": status,
        "start_at": int(time.time()),
        "error_info": error_info
    })
    if error_info is not None and error_info != "":
        raise HTTPException(status_code=500, detail=error_info)

    return orm_to_item(orm)


def cancel_finetune_job(session: Session, current_user: User, id: str) -> FinetuneJobItem:
    job_orm = finetune_job_db.get(session, current_user, id)
    if job_orm is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Finetune job not found. id: {id}").format(id=id))

    if job_orm.status != FinetuneJobStatus.Starting:
        raise HTTPException(status_code=500, detail=i18n.gettext("Only support cancel Starting status finetune job"))

    orm = finetune_job_db.update(session, current_user, id, {
        "status": FinetuneJobStatus.Cancel,
        "end_at": int(time.time()),
    })
    return orm_to_item(orm)


async def watch_starting_jobs():
    loop = events.get_running_loop()
    with manual_get_db() as session:
        jobs, total = finetune_job_db.list_jobs(session, None, 1, 99999, status=FinetuneJobStatus.Starting)

        tasks: List[asyncio.Task] = []
        for job in jobs:
            for machine in job.node_finetune_machine_list:
                task = loop.create_task(
                    watch_job_status_by_machine(User(id=job.user_id, group_id=job.group_id), job.id, machine.id,
                                                job.local)
                )
                tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)
