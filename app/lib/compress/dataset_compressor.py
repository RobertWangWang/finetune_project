import gzip
import pickle

from fastapi import HTTPException

from app.lib.i18n.config import i18n
from app.models.dataset_models.dataset_model import DatasetItem


def compress_dataset(dataset_list: list) -> bytes:
    """
    Compress a DatasetItem object using pickle and gzip.

    Args:
        dataset_item (DatasetItem): The dataset item to compress.

    Returns:
        bytes: The compressed dataset object as bytes.
    """
    if dataset_list is None:
        raise HTTPException(
            status_code=500,
            detail=i18n.gettext("The dataset to be compressed does not exist.")
        )

    try:
        serialized = pickle.dumps(dataset_list)
        compressed = gzip.compress(serialized)
        return compressed
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=i18n.gettext(f"Compression failed: {str(e)}")
        )


def decompress_dataset(data: bytes) -> list:
    """
    Decompress a gzip-compressed DatasetItem pickle byte stream.

    Args:
        data (bytes): The compressed byte stream.

    Returns:
        DatasetItem: The decompressed DatasetItem object.
    """
    try:
        decompressed = gzip.decompress(data)
        dataset_item = pickle.loads(decompressed)
        return dataset_item
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=i18n.gettext(f"Decompression failed: {str(e)}")
        )