from typing import Optional

from pydantic import BaseModel, Field

from app.models.dataset_models.dataset_version_model import DatasetType


class ReleaseItem(BaseModel):
    id: str

    name: str = Field(..., description="制品名称")
    description: str = Field("", description="制品描述")
    base_model: str = Field(..., description="基础模型名称")
    finetune_type: DatasetType = Field(..., description="制品类型")

    job_id: str = Field(..., description="微调任务id")
    finetune_model_path: str = Field(..., description="微调模型本地路径")

    deploy_ids: Optional[list[str]] = Field(..., description="部署列表")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class ReleaseList(BaseModel):
    data: list[ReleaseItem] = Field(..., description="微调制品列表")
    count: int = Field(..., description="总数")


class ReleaseUpdate(BaseModel):
    name: str = Field(..., description="制品名称")
    description: str = Field(..., description="制品描述")


