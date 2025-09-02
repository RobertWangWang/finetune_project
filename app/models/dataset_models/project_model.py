import time
from typing import Optional

from pydantic import BaseModel, Field


class ProjectItem(BaseModel):
    id: str

    name: str = Field(..., description="项目名称")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class ProjectList(BaseModel):
    data: list[ProjectItem] = Field(..., description="项目列表")
    count: int = Field(..., description="总数")


class ProjectCreate(BaseModel):
    name: str = Field(..., description="项目名称")


class ProjectUpdate(BaseModel):
    id: Optional[str] = Field(None)
    name: str = Field(..., description="项目名称")
