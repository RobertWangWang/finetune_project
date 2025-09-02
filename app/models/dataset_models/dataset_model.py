from typing import Optional

from pydantic import BaseModel, Field

from app.models.dataset_models.file_pair_model import FilePairItem
from app.models.dataset_models.ga_pair_model import GAPairOrigin


class DatasetItem(BaseModel):
    id: str

    question: str = Field(..., description="问题")
    answer: str = Field(..., description="答案")
    cot: Optional[str] = Field(None, description="思维链")

    question_id: str = Field(..., description="问题id")
    tag_name: str = Field(..., description="标签名称")
    ga_pair_item: GAPairOrigin = Field(None, description="GAPair信息")

    file_pair_item: FilePairItem = Field(None, description="文件分片信息")

    model: str = Field(..., description="模型名称")
    confirmed: bool = Field(..., description="是否确认")

    file_id: str = Field(..., description="文件ID")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class DatasetList(BaseModel):
    data: list[DatasetItem] = Field(..., description="文件分片列表")
    count: int = Field(..., description="总数")


class DatasetUpdate(BaseModel):
    answer: str = Field(..., description="答案")
    cot: str = Field(..., description="思维链")


class BatchDeleteDatasetRequest(BaseModel):
    dataset_ids: list[str] = Field(..., description="批量删除的数据集列表")
    project_id: str = Field(..., description="项目id")
