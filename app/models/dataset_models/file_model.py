from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class TocBuildAction(str, Enum):
    Keep = "Keep"
    Rebuild = "Rebuild"
    Revise = "Revise"


class FileItem(BaseModel):
    id: str
    file_name: str = Field(..., description="文件名称")
    file_ext: str = Field(..., description="文件后缀")
    md5: str = Field(..., description="文件的md5")
    file_type: str = Field(..., description="文件类型")
    project_id: str = Field(..., description="所属项目id")
    size: int = Field(..., description="文件大小")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="修改时间")


class FileList(BaseModel):
    data: list[FileItem]
    count: int


class GetFileItem(BaseModel):
    id: str
    file_name: str = Field(..., description="文件名称")
    file_ext: str = Field(..., description="文件后缀")
    md5: str = Field(..., description="文件的md5")
    project_id: str = Field(..., description="所属项目id")
    file_type: str = Field(..., description="文件类型")
    size: int = Field(..., description="文件大小")
    content: str = Field(..., description="文件内容")

    created_at: int = Field(..., description="创建时间")
    updated_at: int = Field(..., description="修改时间")


class FileSplitConfig(BaseModel):
    # 分割的一些参数
    text_split_min_length: int = Field(1500, description="最小分割长度")
    text_split_max_length: int = Field(2000, description="最大分割长度")
    chunk_size: int = Field(1500, description="分块大小")
    chunk_overlap: int = Field(200, description="分块重合大小")
    separator: str = Field('\n\n', description="分隔符")
    separators: List[str] = Field(['|', '##', '>', '-'], description="分隔符列表")
    split_language: str = Field("js", description="默认分割语言")
    split_type: str = Field("", description="分割类型")
    # 领域树的参数
    toc_build_action: str = Field("Rebuild", description="领域构建行为. Keep=保持, Rebuild=重新构建, Revise=修订")


class FileDeleteConfig(BaseModel):
    toc_build_action: str = Field("Rebuild", description="领域构建行为. Keep=保持, Rebuild=重新构建, Revise=修订")


class FileDeleteGeneratorContent(BaseModel):
    file: GetFileItem = Field(None, description="文件内容")
    config: FileDeleteConfig


class FilePairGeneratorContent(BaseModel):
    file_ids: list[str] = Field(default_factory=list)
    config: FileSplitConfig
