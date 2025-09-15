from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# -------- Base --------
class EvaluationDatasetBase(BaseModel):
    """公共字段（不含主键/归属/审计）"""
    name: str = Field(..., description="数据集名称")
    description: Optional[str] = Field(None, description="数据集描述")
    partition_keyword: str = Field(..., description="分区关键字（train/test等）")
    eval_type: str = Field(..., description="评测类型（qa-eval/text-gen/classification等）")
    dataset_path: str = Field(..., description="数据集文件路径")
    evaluation_extraction_keyword: Optional[str] = Field(
        None, description="数据提取关键字（如 messages/conversation）"
    )
    current_role: str = Field(..., description="角色（system/user）")


# -------- Create / Update --------
class EvaluationDatasetCreate(EvaluationDatasetBase):
    """创建时的请求体"""
    pass


class EvaluationDatasetUpdate(BaseModel):
    """部分更新字段（全部可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    partition_keyword: Optional[str] = None
    eval_type: Optional[str] = None
    dataset_path: Optional[str] = None
    evaluation_extraction_keyword: Optional[str] = None
    current_role: Optional[str] = None
    error_info: Optional[str] = None


# -------- Read (Out) --------
class EvaluationDatasetOut(EvaluationDatasetBase):
    """完整返回对象"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2: 支持 ORM 转换

    id: str
    user_id: str
    group_id: str
    error_info: Optional[str] = None
    created_at: int
    updated_at: int
    is_deleted: int


# -------- List & Paging --------
class EvaluationDatasetListQuery(BaseModel):
    """分页查询参数"""
    page_no: int = Field(1, ge=1)
    page_size: int = Field(100, ge=1, le=1000)

    eval_type: Optional[str] = None
    current_role: Optional[str] = None


class EvaluationDatasetListOut(BaseModel):
    """分页返回"""
    items: List[EvaluationDatasetOut]
    total: int
