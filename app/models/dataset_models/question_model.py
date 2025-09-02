from typing import List

from pydantic import BaseModel, Field

from app.models.dataset_models.file_pair_model import FilePairItem
from app.models.dataset_models.ga_pair_model import GAPairOrigin


class QuestionItem(BaseModel):
    id: str

    tag_name: str = Field(..., description="标签名称")

    ga_pair_item: GAPairOrigin = Field(None, description="GAPair信息")

    file_pair_item: FilePairItem = Field(None, description="文件分片信息")
    dataset_id_list: List[str] = Field(None, description="数据集id列表")

    question: str = Field(..., description="问题")
    file_id: str = Field(..., description="文件ID")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class QuestionList(BaseModel):
    data: list[QuestionItem] = Field(..., description="文件分片列表")
    count: int = Field(..., description="总数")


class QuestionSave(BaseModel):
    question: str = Field(..., description="问题")
    file_pair_id: str = Field(..., description="文件分片id")
    tag_id: str = Field(..., description="标签ID")


class BatchDeleteRequest(BaseModel):
    question_ids: list[str] = Field(..., description="批量删除的问题列表")
    project_id: str = Field(..., description="项目id")


class DatasetGeneratorRequest(BaseModel):
    question_ids: list[str] = Field(..., description="问题id")
    project_id: str = Field(..., description="项目id")
