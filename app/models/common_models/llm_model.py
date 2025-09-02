import time
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class LLMBaseModel(BaseModel):
    name: str = Field(..., description="名称")
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(..., description="模型类型")
    capability: list[str] = Field(..., description="能力")

    api_key: Optional[str] = Field("", description="api_key")
    endpoint_id: Optional[str] = Field("", description="连接点")
    is_valid: bool = Field(False, description="是否连通")
    is_default: bool = Field(False, description="是否默认")


class LLMItem(LLMBaseModel):
    id: int = Field(..., description="id")


class LLMSaveRequest(LLMBaseModel):
    pass


class LLMModelList(BaseModel):
    total: int
    items: List[LLMItem]


class LLMModelConfig(BaseModel):
    authType: str = Field(None, description="校验类型")
    apiKey: str = Field(None, description="apikey")
    region: str = Field(None, description="地域")
    endpoint: str = Field(None, description="连接点")
    endpointId: str = Field(None, description="连接点id")
    baseModelName: str = Field(None, description="基础模型名称")


class LLMModel(BaseModel):
    id: int = Field(..., description="id")
    provider_name: str = Field(..., description="模型提供商")
    model_name: str = Field(..., description="模型名称")
    model_type: str = Field(..., description="模型类型")
    is_valid: bool = Field(..., description="是否校验")
    is_default: bool = Field(..., description="默认模型")
    account_name: str = Field(..., description="租户名称")
    provider_id: int = Field(..., description="提供者id")

    config: LLMModelConfig = Field(None, description="模型配置")
    capability: List[str] = Field(None, description="能力范围")
