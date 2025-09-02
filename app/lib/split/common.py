import os

from pydantic import BaseModel, Field


class SplitItem(BaseModel):
    size: int = Field(..., description="文件大小")
    content: str = Field(..., description="文件内容")
    summary: str = Field(..., description="文件摘要")
    name: str = Field(..., description="文件名")
    chunk_index: int = Field(..., description="文件分片索引")


def build_chunk_name(file_name: str, index: int) -> str:
    base_name = os.path.basename(file_name)  # 获取文件名（带扩展名）
    file_name_without_ext = os.path.splitext(base_name)[0]  # 去掉扩展名
    return f"{file_name_without_ext}-part-{index + 1}"