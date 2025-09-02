from langchain_text_splitters import TokenTextSplitter

from app.models.dataset_models.file_model import FileSplitConfig, GetFileItem
from app.lib.split.common import SplitItem, build_chunk_name


def split(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    # 初始化分割器
    text_splitter = TokenTextSplitter(
        chunk_size=config.chunk_size,  # 每个块的最大token数
        chunk_overlap=config.chunk_overlap  # 块之间的重叠token数
    )

    texts = text_splitter.split_text(file.content)
    items: list[SplitItem] = []
    for i, chunk in enumerate(texts):
        item = SplitItem(
            size=len(chunk),
            content=chunk,
            summary="",
            name=build_chunk_name(file.file_name, i),
            chunk_index=i+1,
            file_id=file.file_id,
        )
        items.append(item)
    return items
