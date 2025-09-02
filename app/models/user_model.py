from pydantic import BaseModel, Field


class User(BaseModel):
    id: str = Field(..., description="用户id")
    group_id: str = Field(..., description="分组id")