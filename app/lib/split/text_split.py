from langchain_text_splitters import CharacterTextSplitter

from app.models.dataset_models.file_model import GetFileItem, FileSplitConfig
from app.lib.split.common import SplitItem, build_chunk_name


def split(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    # 创建分割器
    text_splitter = CharacterTextSplitter(
        separator=config.separator,  # 使用句号作为分隔符
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        length_function=len,
    )

    # 分割文本
    docs = text_splitter.create_documents([file.content])
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