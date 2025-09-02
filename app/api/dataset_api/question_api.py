from fastapi import APIRouter, HTTPException
from typing import Any
from app.api.middleware.deps import SessionDep, CurrentUserDep
from app.lib.i18n.config import i18n
from app.models.dataset_models.question_model import QuestionList, QuestionItem, QuestionSave, BatchDeleteRequest, \
    DatasetGeneratorRequest
from app.services.dataset_services import question_service

router = APIRouter(prefix="/questions", tags=["questions"])


@router.get(
    "/", response_model=QuestionList, summary="查询所有问题列表", description="查询所有问题列表"
)
def list_question(session: SessionDep, current_user: CurrentUserDep, page: int = 1, page_size: int = 100,
                        project_id: str = None, question: str = None, label: str = None) -> Any:
    if project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    question_list = question_service.list_question(session, current_user, page, page_size, project_id, question,
                                                   label)
    return question_list


@router.put(
    "/{id}", response_model=QuestionItem, summary="更新问题", description="更新问题"
)
def update_question(session: SessionDep, current_user: CurrentUserDep, id: str,
                     update_question: QuestionSave) -> Any:
    question = question_service.update_question(session, current_user, id, update_question)
    return question


@router.post(
    "/", response_model=QuestionItem, summary="创建问题", description="创建问题"
)
def create_question(session: SessionDep, current_user: CurrentUserDep, create_question: QuestionSave) -> Any:
    question = question_service.create_question(session, current_user, create_question)
    return question


@router.delete(
    "/{id}", response_model=QuestionItem, summary="删除问题", description="删除问题"
)
def delete_question(session: SessionDep, current_user: CurrentUserDep, id: str) -> Any:
    question = question_service.delete_question(session, current_user, id)
    return question


@router.delete(
    "/batch_delete", summary="批量删除问题", description="批量删除问题"
)
def delete_question(session: SessionDep, current_user: CurrentUserDep, req: BatchDeleteRequest) -> Any:
    if req.project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    if len(req.question_ids) == 0:
        return i18n.gettext("Param {param} is required").format(param="question_ids")
    question_service.batch_delete_questions(session, current_user, req)
    return "success"


@router.post(
    "/dataset_generator", summary="数据集生成", description="数据集生成"
)
def dataset_generator(session: SessionDep, current_user: CurrentUserDep, req: DatasetGeneratorRequest) -> Any:
    if req.project_id == "":
        raise HTTPException(status_code=500, detail=i18n.gettext("Project_id param is required"))
    if len(req.question_ids) == 0:
        return i18n.gettext("Param {param} is required").format(param="question_ids")

    return question_service.dataset_generator(session, current_user, req)
