# app/models/evaluation_models/evaluation_model.py
from typing import Optional, List
from pydantic import BaseModel, Field

class EvaluationItem(BaseModel):
    id: str
    project_id: str = Field(..., description="项目ID")
    tag_name: Optional[str] = Field(None, description="标签名称（数据筛选）")
    model: Optional[str] = Field(None, description="模型名称（数据筛选）")
    bleu: Optional[float] = Field(None, description="BLEU值")
    rouge: Optional[float] = Field(None, description="ROUGE值")
    accuracy: Optional[float] = Field(None, description="准确率")
    latency: Optional[float] = Field(None, description="推理延迟")
    throughput: Optional[float] = Field(None, description="吞吐量（tokens/秒）")
    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")

class EvaluationList(BaseModel):
    data: List[EvaluationItem] = Field(..., description="评估任务列表")
    count: int = Field(..., description="总数")

class EvaluationCreate(BaseModel):
    project_id: str = Field(..., description="项目ID")
    tag_name: Optional[str] = Field(None, description="按标签筛选数据")
    model: Optional[str] = Field(None, description="按模型名称筛选数据")

class EvaluationUpdate(BaseModel):
    tag_name: Optional[str] = Field(None, description="按标签筛选数据")
    model: Optional[str] = Field(None, description="按模型名称筛选数据")
    bleu: Optional[float] = Field(None, description="BLEU值")
    rouge: Optional[float] = Field(None, description="ROUGE值")
    accuracy: Optional[float] = Field(None, description="准确率")
    latency: Optional[float] = Field(None, description="推理延迟")
    throughput: Optional[float] = Field(None, description="吞吐量")
