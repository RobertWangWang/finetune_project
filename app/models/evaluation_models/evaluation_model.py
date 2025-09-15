from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# -------- Base --------
class EvaluationBase(BaseModel):
    """与 evaluations 表字段对齐的公共基类（不含审计/主键/归属）"""
    evaluation_dataset_id: str = Field(..., description="评测使用的数据集版本 ID")
    eval_model_id: str = Field(..., description="使用的模型 ID")
    eval_type: str = Field(..., description="评测类型")
    deploy_cluster_id: str = Field(..., description="部署集群 ID")

    # 评测结果（JSON，可为空）
    eval_result: Optional[Dict[str, Any]] = Field(
        None, description="评测结果 JSON（包含各类指标，如 bleu/rouge/accuracy/latency 等）"
    )

    # 状态 & 错误信息
    status: Optional[str] = Field("", description="评测任务状态")
    error_info: Optional[str] = Field(None, description="错误信息")


# -------- Create / Update --------
class EvaluationCreate(EvaluationBase):
    """创建时的请求体。
    user_id / group_id / created_at / updated_at 由后端注入。
    """
    pass


class EvaluationUpdate(BaseModel):
    """部分字段更新（全部可选）"""
    evaluation_dataset_id: Optional[str] = None
    eval_model_id: Optional[str] = None
    eval_type: Optional[str] = None
    deploy_cluster_id: Optional[str] = None
    eval_result: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    error_info: Optional[str] = None


# -------- Read (Out) --------
class EvaluationOut(EvaluationBase):
    """对外返回的完整对象"""
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2: 支持 ORM 对象解析

    id: str = Field(..., description="评测记录唯一 ID")
    user_id: str
    group_id: str
    created_at: int
    updated_at: int
    is_deleted: int


# -------- List & Paging --------
class EvaluationListQuery(BaseModel):
    """列表查询的 query 参数"""
    page_no: int = Field(1, ge=1)
    page_size: int = Field(100, ge=1, le=1000)

    # 与后端 list() 的过滤条件对齐
    evaluation_dataset_id: Optional[str] = None
    eval_type: Optional[str] = None
    eval_model_id: Optional[str] = None


class EvaluationListOut(BaseModel):
    """列表返回：数据 + 总数"""
    items: List[EvaluationOut]
    total: int

class DatasetEvaluationRequest(BaseModel):
    """
    配置模型：在指定机器上进行数据集评测
    """
    id: str = Field(..., description="评测任务 ID")
    machine_id: str = Field(..., description="运行评测的机器 ID")
    dataset_path: str = Field(..., description="本机绝对路径，例如 /home/user/datasets/data.json")
    eval_type: str = Field(..., description="评测类型，例如 qa-evaluation / text-generation / classification")
    metrics: List[str] = Field(default=["bleu", "rouge", "accuracy"], description="要计算的指标列表")
    partition_keyword:str = Field(default="test", description="用那一部分数据集来评测的过滤关键词，train，test")
    evaluation_extraction_keyword:str = Field(default="", description="数据集的提取关键词，例如：messages,conversation")
    role:str = Field(default="system", description="当前进行评测的角色， system为默认数据集，user为用户上传的数据集")