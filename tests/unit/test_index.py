from unittest import TestCase

from app.lib.split.markdown.cores.toc import extract_table_of_contents
from app.lib.split.markdown.index import split_markdown


class Test(TestCase):
    def test_split_markdown(self):
        # 第二步：用检测到的编码读取内容
        with open('../data/index.md', 'r', encoding='utf-8') as file:
            content = file.read()
            result = split_markdown(content, 1500, 2000)
            print(result)
    def test_extract_table_of_contents(self):
        with open('../data/index.md', 'r', encoding='utf-8') as file:
            content = file.read()
            result = extract_table_of_contents(content)
            print(result)

