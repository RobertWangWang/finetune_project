from fastapi import APIRouter
from typing import Any, Generator, List, Optional

from starlette.responses import StreamingResponse

from app.api.middleware.context import get_current_locale
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.models.dataset_models.dataset_version_model import DatasetType
from app.models.llamafactory_models.finetune_job_model import FinetuneJobList, FinetuneJobItem, FinetuneJobCreate, \
    FinetuneJobRunningExample, FinetuneJobRunningExampleRequest, FinetuneJobStatus
from app.services.llamafactory_services import finetune_job_service

router = APIRouter(prefix="/finetune_jobs", tags=["finetune_jobs"])


@router.get(
    "/", response_model=FinetuneJobList, summary="查询微调任务列表", description="查询微调任务列表"
)
def list_finetune_job(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100, status: Optional[FinetuneJobStatus] = None,
                      stage: Optional[DatasetType] = None,
                      finetune_method: Optional[str] = None) -> Any:
    return finetune_job_service.list_finetune_job(session, current_user, page, page_size, status, stage, finetune_method)


@router.post(
    "/", response_model=FinetuneJobItem, summary="创建微调任务", description="创建微调任务"
)
def create_finetune_job(session: SessionDep, current_user: CurrentUserDep, create: FinetuneJobCreate) -> Any:
    return finetune_job_service.create_finetune_job(session, current_user, create)


@router.post(
    "/{id}/cancel", response_model=FinetuneJobItem, summary="取消微调任务", description="取消微调任务"
)
def cancel_finetune_job(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return finetune_job_service.cancel_finetune_job(session, current_user, id)


@router.post(
    "/{id}/start", response_model=FinetuneJobItem, summary="启动微调任务", description="启动微调任务"
)
def start_finetune_job(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    return finetune_job_service.start_finetune_job(session, current_user, id)



@router.get(
    "/{id}/logs", response_model=FinetuneJobItem, summary="查询日志流", description="查询日志流"
)
async def finetune_job_logs(session: SessionDep, current_user: CurrentUserDep, id: str, machine_id: str) -> Any:
    def generate() -> Generator[str, None, None]:
        for line in finetune_job_service.finetune_job_logs(session, current_user, id, machine_id):
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
    "/running_example", response_model=List[FinetuneJobRunningExample], summary="任务运行指令示例", description="任务运行指令示例"
)
def finetune_job_running_example(session: SessionDep, current_user: CurrentUserDep, req: FinetuneJobRunningExampleRequest) -> Any:
    return finetune_job_service.finetune_job_running_example(session, current_user, req, local=get_current_locale())