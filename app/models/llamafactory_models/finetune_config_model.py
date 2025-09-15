import time
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from app.db.llamafactory_db_model.finetune_config_db import Module, ConfigType


class FinetuneConfigItem(BaseModel):
    id: str

    name: str = Field(..., description="配置名称")
    description: str = Field(..., description="配重描述")

    module: Module = Field(..., description="模块")
    config_type: ConfigType = Field(..., description="配置类型")
    config: dict = Field(..., description="配置内容")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class FinetuneConfigList(BaseModel):
    data: list[FinetuneConfigItem] = Field(..., description="配置列表")
    count: int = Field(..., description="总数")


class FinetuneConfigSave(BaseModel):
    name: str = Field(..., description="配置名称")
    description: str = Field(..., description="配重描述")

    module: Module = Field(..., description="模块") ### 微调的基座模型
    config_type: ConfigType = Field(..., description="配置类型") ### 配置所属的类别
    config: dict = Field(..., description="配置内容")
