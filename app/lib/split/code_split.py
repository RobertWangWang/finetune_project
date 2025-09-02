from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

from app.models.dataset_models.file_model import GetFileItem, FileSplitConfig
from app.lib.split.common import SplitItem, build_chunk_name


def split(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    python_splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language(config.split_language),  # 指定编程语言
        chunk_size=config.chunk_size,  # 每个块的最大字符数
        chunk_overlap=config.chunk_overlap  # 块之间的重叠字符数
    )

    chunks = python_splitter.create_documents([file.content])
    items: list[SplitItem] = []
    for i, doc in enumerate(chunks):
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

