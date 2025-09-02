from pydantic import BaseModel, Field


class GAPairOrigin(BaseModel):
    text_style: str = Field(..., description="文体")
    text_desc: str = Field(..., description="文体描述")
    audience: str = Field(..., description="受众")
    audience_desc: str = Field(..., description="受众描述")


class GAPairItem(BaseModel):
    id: str

    text_style: str = Field(..., description="文体")
    text_desc: str = Field(..., description="文体描述")
    audience: str = Field(..., description="受众")
    audience_desc: str = Field(..., description="受众描述")
    enable: bool = Field(..., description="是否活跃")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class GAPairList(BaseModel):
    data: list[GAPairItem] = Field(..., description="GA Pair 列表")
    count: int = Field(..., description="总数")


class GAPairSave(BaseModel):
    text_style: str = Field(..., description="文体")
    text_desc: str = Field(..., description="文体描述")
    audience: str = Field(..., description="受众")
    audience_desc: str = Field(..., description="受众描述")
    enable: bool = Field(..., description="开启关闭活跃")

    project_id: str = Field(..., description="项目id")
    file_id: str = Field(..., description="文件id")


class GaPairGeneratorConfig(BaseModel):
    project_id: str = Field(..., description="项目id")
    file_ids: list[str] = Field(..., description="文件id列表")
    append_mode: bool = Field(..., description="拼接模式")


class Genre(BaseModel):
    title: str
    description: str


class Audience(BaseModel):
    title: str
    description: str


class GaPairChatResultItem(BaseModel):
    genre: Genre
    audience: Audience
