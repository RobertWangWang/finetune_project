import asyncio
import json
import logging

from fastapi import APIRouter
from typing import Generator, Any, AsyncGenerator

from starlette.responses import StreamingResponse

from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.deploy_models.deploy_cluster_model import DeployClusterCreate, DeployClusterItem, \
    DeployClusterUpdate, DeployStatus, MachineList, LoraAdaptorDeployCreate, ChatRequest
from app.services.deploy_services import deploy_cluster_service

router = APIRouter(prefix="/deploy_clusters", tags=["deploy_clusters"])


@router.post(
    "/", response_model=DeployClusterItem, summary="创建部署集群", description="查询微调任务列表"
)
def create_deploy_cluster(session: SessionDep, current_user: CurrentUserDep,
                          create: DeployClusterCreate) -> DeployClusterItem:
    return deploy_cluster_service.create_deploy_cluster(session, current_user, create)


@router.put(
    "/{id}", response_model=DeployClusterItem, summary="更新部署集群", description="更新部署集群"
)
def update_deploy_cluster(session: SessionDep, current_user: CurrentUserDep, id: str,
                          update: DeployClusterUpdate) -> DeployClusterItem:
    return deploy_cluster_service.update_deploy_cluster(session, current_user, id, update)


@router.get(
    "/", response_model=MachineList, summary="查询部署集群列表", description="查询部署集群列表"
)
def list_deploy_clusters(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100,
                         name: str = None,
                         status: DeployStatus = None) -> MachineList:
    return deploy_cluster_service.list_deploy_clusters(session, current_user, page, page_size, name, status)

@router.delete(
    "/{id}", summary="删除部署集群", description="删除部署集群"
)
def delete_deploy_cluster(session: SessionDep, current_user: CurrentUserDep, id: str) -> bool:
    return deploy_cluster_service.delete_deploy_cluster(session, current_user, id)


@router.post(
    "/{id}/install", response_model=DeployClusterItem, summary="部署部署集群", description="部署部署集群"
)
def install_deploy_cluster(session: SessionDep, current_user: CurrentUserDep, id: str) -> DeployClusterItem:
    return deploy_cluster_service.install_deploy_cluster(session, current_user, id)

@router.post(
    "/{id}/uninstall", response_model=DeployClusterItem, summary="卸载部署集群", description="卸载部署集群"
)
def uninstall_deploy_cluster(session: SessionDep, current_user: CurrentUserDep, id: str) -> DeployClusterItem:
    return deploy_cluster_service.uninstall_deploy_cluster(session, current_user, id)

@router.post(
    "/{id}/lora_adaptor/create", summary="创建 lora adaptor 部署", description="创建 lora adaptor 部署"
)
def lora_adapter_create(session: SessionDep, current_user: CurrentUserDep, id: str, create: LoraAdaptorDeployCreate) -> str:
    return deploy_cluster_service.lora_adapter_create(session, current_user, id, create)

@router.post(
    "/{id}/lora_adaptor/{lora_id}/install", summary="部署 lora adaptor 进部署集群", description="部署 lora adaptor 进部署集群"
)
def lora_adaptor_install(session: SessionDep, current_user: CurrentUserDep, id: str, lora_id: str) -> bool:
    return deploy_cluster_service.lora_adaptor_install(session, current_user, id, lora_id)

@router.post(
    "/{id}/lora_adaptor/{lora_id}/uninstall", summary="卸载 lora adaptor 进部署集群", description="卸载 lora adaptor 进部署集群"
)
def lora_adaptor_uninstall(session: SessionDep, current_user: CurrentUserDep, id: str, lora_id: str) -> bool:
    return deploy_cluster_service.lora_adaptor_uninstall(session, current_user, id, lora_id)

@router.delete(
    "/{id}/lora_adaptor/{lora_id}", summary="删除 lora adaptor", description="删除 lora adaptor"
)
def delete_lora_adaptor(session: SessionDep, current_user: CurrentUserDep, id: str, lora_id: str) -> bool:
    return deploy_cluster_service.delete_lora_adaptor(session, current_user, id, lora_id)

@router.post(
    "/{id}/sync", summary="同步部署集群状态", description="同步部署集群状态"
)
def sync_cluster_status(session: SessionDep, current_user: CurrentUserDep, id: str) -> DeployClusterItem:
    return deploy_cluster_service.sync_cluster_status(session, current_user, id)


@router.get(
    "/{id}/logs", summary="获取部署集群日志", description="获取部署集群日志"
)
async def cluster_logs(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    def generate() -> Generator[str, None, None]:
        for line in deploy_cluster_service.cluster_logs(session, current_user, id):
            yield line
            # 使用 Server-Sent Events (SSE) 格式
            # 前端可以使用 EventSource 接收

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post(
    "/completion/stream", summary="流失问答", description="流失问答"
)
async def completion_stream(session: SessionDep, current_user: CurrentUserDep, chat_request: ChatRequest):
    async def stream_generator():
        try:
            async for chunk in deploy_cluster_service.completion_stream(
                session, current_user, chat_request
            ):
                yield chunk
                # 检查客户端是否还连接
        except asyncio.CancelledError:
            # 客户端断开连接
            logging.info("Client disconnected")
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )