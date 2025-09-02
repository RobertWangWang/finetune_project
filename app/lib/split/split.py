from app.models.dataset_models.file_model import FileSplitConfig, GetFileItem
from app.lib.split import code_split, token_split, markdown_split, recursive_split, text_split
from app.lib.split.common import SplitItem

splits = {
    "token": token_split.split,
    "text": text_split.split,
    "markdown": markdown_split.split,
    "recursive": recursive_split.split,
    "code": code_split.split
}


def split_file(file: GetFileItem, config: FileSplitConfig) -> list[SplitItem]:
    split = splits.get(config.split_type)
    if split:
        return split(file, config)
    else:
        return markdown_split.split(file, config)
