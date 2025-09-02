import re
from typing import List, Dict


def extract_outline(text: str) -> List[Dict]:
    """
    提取Markdown文档大纲

    Args:
        text: Markdown文本

    Returns:
        提取的大纲数组，每个元素包含level(标题级别)、title(标题文本)和position(在文本中的位置)
    """
    outline_regex = r'^(#{1,6})\s+(.+?)(?:\s*\{#[\w-]+\})?\s*$'
    outline = []

    for match in re.finditer(outline_regex, text, flags=re.MULTILINE):
        level = len(match.group(1))
        title = match.group(2).strip()

        outline.append({
            'level': level,
            'title': title,
            'position': match.start()
        })

    return outline


def split_by_headings(text: str, outline: List[Dict]) -> List[Dict]:
    """
    根据标题分割文档

    Args:
        text: Markdown文本
        outline: 文档大纲

    Returns:
        按标题分割的段落数组，每个元素包含heading(标题)、level(级别)、content(内容)和position(位置)
    """
    if not outline:
        return [{
            'heading': None,
            'level': 0,
            'content': text,
            'position': 0
        }]

    sections = []

    # 添加第一个标题前的内容（如果有）
    if outline[0]['position'] > 0:
        front_matter = text[:outline[0]['position']].strip()
        if front_matter:
            sections.append({
                'heading': None,
                'level': 0,
                'content': front_matter,
                'position': 0
            })

    # 分割每个标题的内容
    for i in range(len(outline)):
        current = outline[i]
        next_item = outline[i + 1] if i < len(outline) - 1 else None

        # 获取标题行
        remaining_text = text[current['position']:]
        heading_line = remaining_text.split('\n', 1)[0]

        start_pos = current['position'] + len(heading_line) + 1
        end_pos = next_item['position'] if next_item else len(text)

        content = text[start_pos:end_pos].strip()

        sections.append({
            'heading': current['title'],
            'level': current['level'],
            'content': content,
            'position': current['position']
        })

    return sections