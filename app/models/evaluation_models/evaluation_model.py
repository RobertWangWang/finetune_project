# app/models/evaluation_models/evaluation_model.py
from typing import Optional, List
from pydantic import BaseModel, Field


class EvaluationItem(BaseModel):
    id: str
    project_id: str = Field(..., description="项目ID")
    tag_name: Optional[str] = Field(None, description="标签筛选（DatasetORM.tag_name）")
    model: Optional[str] = Field(None, description="模型筛选（DatasetORM.model）")
    bleu: Optional[float] = Field(None, description="BLEU")
    rouge: Optional[float] = Field(None, description="ROUGE（rougeLsum）")
    accuracy: Optional[float] = Field(None, description="准确率")
    latency: Optional[float] = Field(None, description="平均延迟（秒）")
    throughput: Optional[float] = Field(None, description="吞吐（requests/sec）")
    created_at: int
    updated_at: int


class EvaluationList(BaseModel):
    data: List[EvaluationItem]
    count: int


class EvaluationCreate(BaseModel):
    project_id: str = Field(..., description="项目ID")
    tag_name: Optional[str] = Field(None, description="标签筛选（可选）")
    model: Optional[str] = Field(None, description="模型筛选（可选）")


class EvaluationUpdate(BaseModel):
    # 可更新过滤条件或回填指标（通常 run 后由服务层写回）
    tag_name: Optional[str] = None
    model: Optional[str] = None
    bleu: Optional[float] = None
    rouge: Optional[float] = None
    accuracy: Optional[float] = None
    latency: Optional[float] = None
    throughput: Optional[float] = None


class EvaluationRun(BaseModel):
    vllm_base_url: str = Field(..., description="vLLM REST Base URL，如 http://127.0.0.1:8000")
    lora_name: str = Field(..., description="LoRA 名称（加载到 vLLM）")
    lora_path: str = Field(..., description="LoRA 权重在 vLLM 机器上的路径")
    max_examples: int = Field(100, ge=1, le=100000, description="抽样评测数据条数")
    concurrency: int = Field(4, ge=1, le=64, description="并发请求数")
    max_tokens: int = Field(512, ge=1, le=8192, description="生成最大 token 数")
    temperature: float = Field(0.1, ge=0.0, le=2.0, description="采样温度")
