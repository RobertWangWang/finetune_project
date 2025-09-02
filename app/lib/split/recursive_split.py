from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.dataset_models.file_model import GetFileItem, FileSplitConfig
from app.lib.split.common import SplitItem, build_chunk_name


def split(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=config.separators  # 按标题分割
    )

    docs = splitter.create_documents([file.content])

    items: list[SplitItem] = []
    # 查看分割结果
    for i, doc in enumerate(docs):
        item = SplitItem(
            size=len(doc.page_content),
            content=doc.page_content,
            summary="",
            name=build_chunk_name(file.file_name, i),
            chunk_index=i + 1,
            file_id=file.file_id,
        )
        items.append(item)
    return items
