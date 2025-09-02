from pydantic import BaseModel, Field


class FilePairItem(BaseModel):
    id: str

    size: int = Field(..., description="文件大小")
    content: str = Field(..., description="文件内容")
    summary: str = Field(..., description="文件摘要")
    name: str = Field(..., description="文件名")
    chunk_index: int = Field(..., description="文件分片索引")
    question_id_list: list[str] = Field(None, description="问题id列表")

    file_id: str = Field(..., description="文件id")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="更新时间")


class FilePairList(BaseModel):
    data: list[FilePairItem] = Field(..., description="文件分片列表")
    count: int = Field(..., description="总数")


class FilePairUpdate(BaseModel):
    content: str = Field(..., description="文件内容")
    summary: str = Field(..., description="文件摘要")


class FilePairExportRequest(BaseModel):
    file_pair_ids: list[str] = Field(..., description="文件分片id")
    project_id: str = Field(..., description="项目id")


class FilePairExportItem(BaseModel):
    file_name: str = Field("", description="文件名称")
    project_name: str = Field("", description="项目名称")
    name: str = Field(..., description="分片名称")
    content: str = Field(..., description="内容")
    summary: str = Field(..., description="目录")
    size: int = Field(..., description="大小")


class FilePairQuestionGeneratorContent(BaseModel):
    file_pair_ids: list[str] = Field(..., description="文件分片id")
    project_id: str = Field(..., description="项目id")

    number: int = Field(0, description="问题生成数量")
    question_generation_length: int = Field(60, description="问题生成长度")
    question_mask_removing_probability: int = Field(60, description="问题掩码移除概率")
    use_ga_generator: bool = Field(True, description="使用 ga 生成问题")