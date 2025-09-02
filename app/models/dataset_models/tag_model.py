from typing import Optional, List

from pydantic import BaseModel, Field


class TagItem(BaseModel):
    id: str

    label: str = Field(..., description="标签名称")
    parent_id: str = Field(..., description="标签父id")
    project_id: str = Field(..., description="标签所属项目")
    childes: Optional[list] = Field(None, description="子标签列表")

    question_id_list: List[str] = Field(None, description="问题列表")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class TagCreate(BaseModel):
    label: str = Field(..., description="标签名称")
    parent_id: str = Field(..., description="标签父id")
    project_id: str = Field(..., description="标签所属项目")


class TagUpdate(BaseModel):
    label: str = Field(..., description="标签名称")


class TagChatResultItem(BaseModel):
    label: str = Field(..., description="标签")
    child: list = Field(None, description="子标签")