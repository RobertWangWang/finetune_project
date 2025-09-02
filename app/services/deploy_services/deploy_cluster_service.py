import asyncio
import logging
import threading
import uuid
from typing import List, Generator

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.middleware.context import get_current_locale
from app.api.middleware.deps import manual_get_db
from app.db.common_db_model import machine_db
from app.db.deploy_db_model import deploy_cluster_db
from app.db.deploy_db_model.deploy_cluster_db import DeployClusterORM
from app.db.common_db_model.machine_db import MachineORM
from app.lib.finetune_path.path_build import build_deploy_work_path, build_deploy_logs_path, build_deploy_lora_path, \
    build_deploy_lora_tar_path
from app.lib.i18n.config import i18n
from app.models.deploy_models.deploy_cluster_model import DeployClusterCreate, DeployClusterItem, \
    DeployClusterUpdate, DeployStatus, MachineList, LoraAdaptorDeployCreate, LoraDeployInfo, RayRunningStatus
from app.models.user_model import User
from app.services.common_services import machine_service
from app.services.common_services.machine_service import orm_machine_to_item

loop = asyncio.new_event_loop()


def run_event_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()


threading.Thread(target=run_event_loop, daemon=True).start()


def orm_to_item(orm: DeployClusterORM, machine_dict: dict[str: MachineORM]) -> DeployClusterItem:
    machine_list = []
    for machine_id in orm.machine_id_list:
        machine_orm = machine_dict.get(machine_id)
        if machine_orm:
            machine_list.append(orm_machine_to_item(machine_orm))

    item = DeployClusterItem(
        **orm.to_dict(),
        machine_list=machine_list
    )
    return item


def create_deploy_cluster(session: Session, current_user: User,
                          create: DeployClusterCreate) -> DeployClusterItem:
    ray_running_status: list[RayRunningStatus] = []
    for machine_id in create.machine_id_list:
        ray_running_status.append(RayRunningStatus(
            machine_id=machine_id,
            status=DeployStatus.Init,
            error_info=""
        ))
    cluster = deploy_cluster_db.create_deploy_cluster(session, current_user, DeployClusterORM(
        **create.dict(),
        status=DeployStatus.Init,
        lora_deploy_infos=[],
        ray_running_status=ray_running_status
    ))

    return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))


def update_deploy_cluster(session: Session, current_user: User, id: str,
                          update: DeployClusterUpdate) -> DeployClusterItem:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, id)
    if cluster is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=id))
    if cluster.status == DeployStatus.Init:
        ray_running_status: list[RayRunningStatus] = []
        for machine_id in update.machine_id_list:
            ray_running_status.append(RayRunningStatus(
                machine_id=machine_id,
                status=DeployStatus.Init,
                error_info=""
            ))

        cluster = deploy_cluster_db.update_deploy_cluster(session, current_user, id, {
            "name": update.name,
            "machine_id_list": update.machine_id_list,
            "base_model": update.base_model,
            "ray_running_status": ray_running_status
        })
    else:
        cluster = deploy_cluster_db.update_deploy_cluster(session, current_user, id, {
            "name": update.name,
        })
    return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))


def list_deploy_clusters(session: Session, current_user: User, page_no: int, page_size: int, name: str = None,
                         status: DeployStatus = None) -> MachineList:
    cluster_list, total = deploy_cluster_db.list_deploy_clusters(session, current_user, page_no, page_size, name,
                                                                 status)
    machine_id_list = []
    for cluster in cluster_list:
        for id in cluster.machine_id_list:
            machine_id_list.append(id)

    machine_dict = machine_service.machine_map_search(session, current_user, machine_id_list)

    items: List[DeployClusterItem] = []
    for cluster in cluster_list:
        items.append(orm_to_item(cluster, machine_dict))
    return MachineList(
        items=items,
        total=total
    )


def delete_deploy_cluster(session: Session, current_user: User, deploy_id: str) -> bool:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, deploy_id)
    if cluster is None:
        raise HTTPException(status_code=500, detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=id))

    if cluster.status == DeployStatus.Deploying or cluster.status == DeployStatus.Starting:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Can not delete Deploying or Starting status deploy cluster"))

    return deploy_cluster_db.delete_deploy_cluster(session, current_user, deploy_id)


# 异步安装 vllm 部署的集群
async def _install_deploy_cluster(current_user: User, deploy_id: str, local: str):
    with manual_get_db() as session:
        cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, deploy_id)
    if cluster is None:
        logging.info(f"_install_deploy_cluster failed. cluster not found id: {deploy_id}")
        return

    try:
        with manual_get_db() as session:
            machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                                       ids=cluster.machine_id_list)
        if len(machine_list) == 0:
            with manual_get_db() as session:
                deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                    "status": DeployStatus.Error,
                    "error_info": i18n.gettext("The connected machine was not found. ids: {ids}", local=local).format(
                        ids=cluster.machine_id_list)
                })
            return

        gpu_num = 0
        error_info = ""
        master_client = None
        master_internal_ip = ""
        ray_running_status = cluster.ray_running_status
        # start ray
        for index, machine in enumerate(machine_list):
            gpu_num += machine.gpu_count

            machine_client = machine.to_remote_machine()
            if index == 0:
                master_client = machine_client
                master_internal_ip = machine.client_config.get("internal_ip")
                cmd = f"ray start --head --node-ip-address {master_internal_ip} --port 26379 --dashboard-host 0.0.0.0"
            else:
                cmd = f"ray start --address {master_internal_ip}:26379"

            # 先停止服务，保证幂等
            machine_client.execute_command("ray stop", timeout=3600)
            machine_client.remove_reboot_task_by_name(deploy_id + "_ray")

            # 启动 cmd
            out, error, code = machine_client.execute_command(cmd, timeout=3600)
            if code != 0:
                ray_running_status[index].status = DeployStatus.Error
                ray_running_status[index].error_info = error
                error_info = error
            else:
                # 添加开机启动
                error = machine_client.add_reboot_task(cmd, cluster.id + "_ray")
                if error == "":
                    ray_running_status[index].status = DeployStatus.Starting
                    ray_running_status[index].error_info = ""
                else:
                    ray_running_status[index].status = DeployStatus.Error
                    ray_running_status[index].error_info = error
                    error_info = error

        if error_info != "":
            with manual_get_db() as session:
                deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                    "status": DeployStatus.Error,
                    "error_info": i18n.gettext("Deploy LLM by vllm and ray failed. error: {error}", local=local).format(
                        error=error_info),
                    "ray_running_status": ray_running_status
                })
            return

        # start vllm openapi
        cmds = [
            f"""cat << 'EOF' > /etc/systemd/system/{deploy_id}.service 
        [Unit]
        Description=deploy job

        [Service]
        Type=simple                       
        WorkingDirectory={build_deploy_work_path(deploy_id)}
        ExecStart=/bin/bash -c 'vllm serve {cluster.base_model} --enable-lora --tensor-parallel-size {gpu_num} --pipeline-parallel-size {len(cluster.machine_id_list)} --gpu-memory-utilization 0.9 --distributed-executor-backend ray --disable-log-stats --host 0.0.0.0 --port 8000 >> {build_deploy_logs_path(deploy_id)} 2>&1'
        Restart=no
        Environment=VLLM_USE_MODELSCOPE=true
        Environment=VLLM_ALLOW_RUNTIME_LORA_UPDATING=true


        [Install]
        WantedBy=multi-user.target
        EOF
                """,
            "systemctl daemon-reload",
            f"mkdir -p {build_deploy_work_path(deploy_id)}",
            f"systemctl enable {deploy_id}.service",
            f"systemctl start {deploy_id}.service"
        ]

        error_info = ""
        for cmd in cmds:
            out, error, code = master_client.execute_command(cmd, timeout=3600)
            if code != 0:
                error_info = i18n.gettext("Start deploy job failed. exit_code: {exit_code}, error: {error}",
                                          local=local).format(exit_code=code, error=error)
                break

        if error_info != "":
            with manual_get_db() as session:
                deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                    "status": DeployStatus.Error,
                    "error_info": i18n.gettext("Deploy LLM by vllm and ray failed. error: {error}", local=local).format(
                        error=error_info),
                    "ray_running_status": ray_running_status
                })
            return

        with manual_get_db() as session:
            deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                "status": DeployStatus.Starting,
                "error_info": "",
                "ray_running_status": ray_running_status
            })
    except Exception as e:
        with manual_get_db() as session:
            deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                "status": DeployStatus.Error,
                "error_info": str(e),
            })


def install_deploy_cluster(session: Session, current_user: User, deploy_id: str) -> DeployClusterItem:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, deploy_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=deploy_id))

    if cluster.status == DeployStatus.Deploying or cluster.status == DeployStatus.Starting:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Can not install Deploying or Starting status deploy cluster"))

    cluster = deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
        "status": DeployStatus.Deploying
    })

    asyncio.run_coroutine_threadsafe(_install_deploy_cluster(current_user, deploy_id, get_current_locale()), loop)

    return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))


def uninstall_deploy_cluster(session: Session, current_user: User, deploy_id: str) -> DeployClusterItem:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, deploy_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=deploy_id))

    if cluster.status != DeployStatus.Starting:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Only support Starting status deploy cluster"))

    machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                               ids=cluster.machine_id_list)
    if len(machine_list) == 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("The connected machine was not found. ids: {ids}").format(
                                ids=cluster.machine_id_list))

    master_client = machine_list[0].to_remote_machine()
    # 去除开机启动
    master_client.execute_command(f"systemctl disable {deploy_id}.service")
    # 查看服务状态
    service_status, error_info = master_client.monitor_service_status(deploy_id)
    # 运行中才调用停止
    if service_status == DeployStatus.Starting.name:
        out, error, code = master_client.execute_command(f"systemctl stop {deploy_id}.service")
        if code != 0:
            raise HTTPException(status_code=500,
                                detail=i18n.gettext("Stop deploy cluster service failed. error: {error}").format(
                                    error=error))
    master_client.execute_command(f"rm -rf /etc/systemd/system/{deploy_id}.service")

    # 将 ray 全部停止，从后往前因为 master 为第一个，先停 ray 的 node 节点
    for machine in reversed(machine_list):
        machine_client = machine.to_remote_machine()
        # 删除 ray 的开机启动
        machine_client.remove_reboot_task_by_name(cluster.id + "_ray")
        # 判定 ray 状态
        out, error, code = machine_client.execute_command("ray status")
        # 只有 ray 存在才调用 stop 保证幂等
        if code == 0:
            out, error, code = machine_client.execute_command("ray stop")
            if code != 0:
                raise HTTPException(status_code=500,
                                    detail=i18n.gettext("Stop deploy cluster service failed. error: {error}").format(
                                        error=error))

    ray_status = cluster.ray_running_status
    for ray in ray_status:
        ray.status = DeployStatus.Uninstalled
        ray.error_info = ""

    lora_infos = cluster.lora_deploy_infos
    for info in lora_infos:
        info.status = DeployStatus.Uninstalled

    cluster = deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
        "status": DeployStatus.Uninstalled,
        "lora_deploy_infos": lora_infos,
        "ray_running_status": ray_status
    })

    return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))


def lora_adapter_create(session: Session, current_user: User, cluster_id: str, create: LoraAdaptorDeployCreate) -> str:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))
    lora_deploy_infos = cluster.lora_deploy_infos
    if lora_deploy_infos is None:
        lora_deploy_infos = []

    id = str(uuid.uuid4())
    lora_deploy_infos.append(LoraDeployInfo(
        id=id,
        release_id=create.release_id,
        finetune_model_path=create.finetune_model_path,
        stage=create.stage,
        status=DeployStatus.Init,
        error_info=""
    ))
    deploy_cluster_db.update_deploy_cluster(session, current_user, cluster.id, {
        "lora_deploy_infos": lora_deploy_infos
    })
    return id


async def _lora_adaptor_install(current_user: User, deploy_id: str, lora_deploy_id: str, local: str):
    with manual_get_db() as session:
        cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, deploy_id)
    if cluster is None:
        logging.info(f"_lora_adaptor_install failed. cluster not found id: {deploy_id}")
        return

    with manual_get_db() as session:
        machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                                   ids=cluster.machine_id_list)
    if len(machine_list) == 0:
        with manual_get_db() as session:
            deploy_cluster_db.update_deploy_cluster(session, current_user, deploy_id, {
                "status": DeployStatus.Error,
                "error_info": i18n.gettext("The connected machine was not found. ids: {ids}", local=local).format(
                    ids=cluster.machine_id_list)
            })
        return

    for lora in cluster.lora_deploy_infos:
        if lora.id == lora_deploy_id:
            try:
                # 拷贝压缩的 lora 文件到远程机器
                for node in machine_list:
                    machine_client = node.to_remote_machine()
                    machine_client.sftp_upload_with_dirs(lora.finetune_model_path,
                                                         build_deploy_lora_tar_path(deploy_id, lora_deploy_id))
                    out, error, code = machine_client.execute_command(
                        f"tar -xzf {build_deploy_lora_tar_path(deploy_id, lora_deploy_id)} -C {build_deploy_lora_path(deploy_id, lora_deploy_id)}")
                    if code != 0:
                        raise Exception(error)

                master_node = machine_list[0]
                ip = master_node.client_config.get("ip")
                response = requests.post(f"http://{ip}:8000/v1/load_lora_adapter", headers={
                    "Content-Type": "application/json"
                }, json={
                    "lora_name": f"{lora_deploy_id}",
                    "lora_path": f"{build_deploy_lora_path(deploy_id, lora_deploy_id)}/output"
                })
                if response.status_code != 200:
                    error_info = i18n.gettext(
                        "Request {path} to remote machine failed. ip: {ip}, port: {port}, status_code: {status_code}, error_info: {error_info}",
                        local=local).format(
                        path="/v1/load_lora_adapter",
                        ip=ip,
                        port=8000,
                        status_code=response.status_code,
                        error_info=response.text,
                    )
                    raise Exception(error_info)
            except Exception as e:
                lora.status = DeployStatus.Error
                lora.error_info = str(e)
                continue
            lora.status = DeployStatus.Starting
            lora.error_info = ""

    deploy_cluster_db.update_deploy_cluster(session, current_user, cluster.id, {
        "lora_deploy_infos": cluster.lora_deploy_infos
    })


def lora_adaptor_install(session: Session, current_user: User, cluster_id: str, lora_deploy_id: str) -> bool:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))

    if cluster.status != DeployStatus.Starting:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Only support Starting status deploy cluster"))

    for lora_deploy_info in cluster.lora_deploy_infos:
        if lora_deploy_info.id == lora_deploy_id:
            lora_deploy_info.status = DeployStatus.Deploying

    deploy_cluster_db.update_deploy_cluster(session, current_user, cluster.id, {
        "lora_deploy_infos": cluster.lora_deploy_infos
    })

    asyncio.run_coroutine_threadsafe(
        _lora_adaptor_install(current_user, cluster_id, lora_deploy_id, get_current_locale()), loop)
    return True


def lora_adaptor_uninstall(session: Session, current_user: User, cluster_id: str, lora_deploy_id: str) -> bool:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))

    if cluster.status != DeployStatus.Starting:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Only support Starting status deploy cluster"))

    machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                               ids=cluster.machine_id_list)
    if len(machine_list) == 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("The connected machine was not found. ids: {ids}").format(
                                ids=cluster.machine_id_list))

    for lora_deploy_info in cluster.lora_deploy_infos:
        if lora_deploy_info.id == lora_deploy_id:
            master = machine_list[0]
            ip = master.client_config.get("ip")
            response = requests.post(f"http://{ip}:8000/v1/unload_lora_adapter", headers={
                "Content-Type": "application/json"
            }, json={
                "lora_name": f"{lora_deploy_id}"
            })
            if response.status_code != 200:
                error_info = i18n.gettext(
                    "Request {path} to remote machine failed. ip: {ip}, port: {port}, status_code: {status_code}, error_info: {error_info}").format(
                    path="/v1/unload_lora_adapter",
                    ip=ip,
                    port=8000,
                    status_code=response.status_code,
                    error_info=response.text,
                )
                raise HTTPException(status_code=500, detail=error_info)
            lora_deploy_info.status = DeployStatus.Uninstalled

    deploy_cluster_db.update_deploy_cluster(session, current_user, cluster.id, {
        "lora_deploy_infos": cluster.lora_deploy_infos
    })
    return True


def delete_lora_adaptor(session: Session, current_user: User, cluster_id: str, lora_deploy_id: str) -> bool:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))
    new_lora_deploy_info = []
    for lora_deploy_info in cluster.lora_deploy_infos:
        if lora_deploy_info.id != lora_deploy_id:
            new_lora_deploy_info.append(lora_deploy_info)
        else:
            if cluster.status == DeployStatus.Deploying or cluster.status == DeployStatus.Starting:
                raise HTTPException(status_code=500,
                                    detail=i18n.gettext("Can not delete Deploying or Starting status lora adaptor"))
    deploy_cluster_db.update_deploy_cluster(session, current_user, cluster.id, {
        "lora_deploy_infos": new_lora_deploy_info
    })
    return True


def sync_cluster_status(session: Session, current_user: User, cluster_id: str) -> DeployClusterItem:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))

    machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                               ids=cluster.machine_id_list)
    if len(machine_list) == 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("The connected machine was not found. ids: {ids}").format(
                                ids=cluster.machine_id_list))
    # 检测所有的 ray 运行状态
    error_info = ""
    master_client = None
    ray_running_status = cluster.ray_running_status
    for index, machine in enumerate(machine_list):
        machine_client = machine.to_remote_machine()
        if index == 0:
            master_client = machine_client

        out, error, code = machine_client.execute_command("ray status")
        if code != 0:
            ray_running_status[index].status = DeployStatus.Error
            ray_running_status[index].error_info = error
            error_info = error
        else:
            ray_running_status[index].status = DeployStatus.Starting

    if error_info != "":
        deploy_cluster_db.update_deploy_cluster(session, current_user, cluster_id, {
            "status": DeployStatus.Error,
            "error_info": error_info,
            "ray_running_status": ray_running_status
        })
        return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))
    else:
        # 最后检测 vllm 的运行状态
        service_status, error_info = master_client.monitor_service_status(cluster_id)
        status = DeployStatus.Starting
        if service_status != DeployStatus.Starting.name:
            status = DeployStatus.Error
        deploy_cluster_db.update_deploy_cluster(session, current_user, cluster_id, {
            "status": status,
            "error_info": error_info,
            "ray_running_status": ray_running_status
        })
        return orm_to_item(cluster, machine_service.machine_map_search(session, current_user, cluster.machine_id_list))


def cluster_logs(session: Session, current_user: User, cluster_id: str) -> Generator[str, None, None]:
    cluster = deploy_cluster_db.get_deploy_cluster_by_id(session, current_user, cluster_id)
    if cluster is None:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("Deploy cluster not found. id: {id}").format(id=cluster_id))

    machine_list, _ = machine_db.list_machines(session, current_user, 1, len(cluster.machine_id_list),
                                               ids=cluster.machine_id_list)
    if len(machine_list) == 0:
        raise HTTPException(status_code=500,
                            detail=i18n.gettext("The connected machine was not found. ids: {ids}").format(
                                ids=cluster.machine_id_list))

    master_node = machine_list[0]
    machine_client = master_node.to_remote_machine()

    return machine_client.tail_log(
        log_path=build_deploy_logs_path(cluster_id)
    )
