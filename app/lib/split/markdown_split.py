from app.models.dataset_models.file_model import GetFileItem, FileSplitConfig
from app.lib.split.common import SplitItem, build_chunk_name
from app.lib.split.markdown.index import split_markdown


def split(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    docs = split_markdown(file.content, config.text_split_min_length, config.text_split_max_length)

    items: list[SplitItem] = []
    for i, docs in enumerate(docs):
        content = docs["content"]
        summary = docs["summary"]
        if summary is None:
            summary = ""

        item = SplitItem(
            size=len(content),
            content=content,
            summary=summary,
            name=build_chunk_name(file.file_name, i),
            chunk_index=i + 1,
        )
        items.append(item)
    return items