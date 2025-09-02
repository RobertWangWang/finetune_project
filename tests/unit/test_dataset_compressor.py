import os
from unittest import TestCase

from app.lib.compress import dataset_compressor
from app.models.dataset_models.dataset_model import DatasetItem
from app.models.dataset_models.ga_pair_model import GAPairOrigin


class Test(TestCase):
    def test_compress_dataset(self):
        dataset_list: list[DatasetItem] = [DatasetItem(
            id="1",
            question="test",
            answer="test",
            cot="sss",
            question_id="1",
            tag_name="test",
            ga_pair_id="1",
            ga_pair_item=GAPairOrigin(
                text_style="test",
                text_desc="test",
                audience="test",
                audience_desc="test"
            ),
            model="test",
            confirmed=True,
            file_id="1",
            created_at="1",
            updated_at="1"
        )]
        values = dataset_compressor.compress_dataset(dataset_list)
        dataset_list_decode = dataset_compressor.decompress_dataset(values)
        print(dataset_list_decode)

