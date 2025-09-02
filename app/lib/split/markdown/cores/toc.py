import re
from typing import List, Dict, Optional, Union


def extract_table_of_contents(text: str, options: Optional[Dict] = None) -> List[Dict]:
    """
    Extract table of contents structure from Markdown text
    :param text: Markdown text
    :param options: Configuration options
        - max_level: Maximum heading level to extract (default: 6)
        - include_links: Whether to include anchor links (default: True)
        - flat_list: Whether to return a flat list (default: False)
    :return: Table of contents structure
    """
    if options is None:
        options = {}

    max_level = options.get('max_level', 6)
    include_links = options.get('include_links', True)
    flat_list = options.get('flat_list', False)

    # Regex to match headings
    heading_regex = re.compile(r'^(#{1,6})\s+(.+?)(?:\s*\{#[\w-]+\})?\s*$', re.MULTILINE)
    toc_items = []

    for match in heading_regex.finditer(text):
        level = len(match.group(1))

        # Skip if heading level exceeds max level
        if level > max_level:
            continue

        title = match.group(2).strip()
        position = match.start()

        # Generate anchor ID
        anchor_id = generate_anchor_id(title)

        toc_items.append({
            'level': level,
            'title': title,
            'position': position,
            'anchor_id': anchor_id,
            'children': []
        })

    # Return flat list if requested
    if flat_list:
        return [
            {
                'level': item['level'],
                'title': item['title'],
                'position': item['position'],
                **({'link': f"#{item['anchor_id']}"} if include_links else {})
            }
            for item in toc_items
        ]

    # Build nested structure
    return build_nested_toc(toc_items, include_links)


def generate_anchor_id(title: str) -> str:
    """
    Generate anchor ID from title text
    :param title: Heading title
    :return: Generated anchor ID
    """
    # Convert to lowercase
    anchor_id = title.lower()
    # Replace spaces with hyphens
    anchor_id = re.sub(r'\s+', '-', anchor_id)
    # Remove non-word characters except hyphens
    anchor_id = re.sub(r'[^\w-]', '', anchor_id)
    # Replace multiple hyphens with single hyphen
    anchor_id = re.sub(r'-+', '-', anchor_id)
    # Remove leading/trailing hyphens
    anchor_id = anchor_id.strip('-')
    return anchor_id


def build_nested_toc(items: List[Dict], include_links: bool) -> List[Dict]:
    """
    Build nested table of contents structure
    :param items: Flat list of TOC items
    :param include_links: Whether to include links
    :return: Nested TOC structure
    """
    result = []
    stack = [{'level': 0, 'children': result}]

    for item in items:
        toc_item = {
            'title': item['title'],
            'level': item['level'],
            'position': item['position'],
            'children': []
        }

        if include_links:
            toc_item['link'] = f"#{item['anchor_id']}"

        # Find parent item
        while stack[-1]['level'] >= item['level']:
            stack.pop()

        # Add current item to parent's children
        stack[-1]['children'].append(toc_item)

        # Push current item to stack
        stack.append(toc_item)

    return result


def toc_to_markdown(toc: Union[List[Dict], Dict], options: Optional[Dict] = None) -> str:
    """
    Convert TOC structure to Markdown format
    :param toc: Table of contents structure (nested or flat)
    :param options: Configuration options
        - is_nested: Whether the structure is nested (default: True)
        - include_links: Whether to include links (default: True)
    :return: Markdown formatted TOC
    """
    if options is None:
        options = {}

    is_nested = options.get('is_nested', True)
    include_links = options.get('include_links', True)

    if is_nested:
        return nested_toc_to_markdown(toc, 0, include_links)
    else:
        return flat_toc_to_markdown(toc, include_links)


def nested_toc_to_markdown(items: List[Dict], indent: int = 0, include_links: bool = True) -> str:
    """
    Convert nested TOC structure to Markdown format
    :param items: Nested TOC items
    :param indent: Current indentation level
    :param include_links: Whether to include links
    :return: Markdown formatted TOC
    """
    result = []
    indent_str = '  ' * indent

    # Add data validation
    if not isinstance(items, list):
        print('Warning: items is not a list in nested_toc_to_markdown')
        return ''

    for item in items:
        title_text = f"[{item['title']}]({item['link']})" if include_links and item.get('link') else item['title']
        result.append(f"{indent_str}- {title_text}")

        if item.get('children'):
            result.append(nested_toc_to_markdown(item['children'], indent + 1, include_links))

    return '\n'.join(result)


def flat_toc_to_markdown(items: List[Dict], include_links: bool = True) -> str:
    """
    Convert flat TOC structure to Markdown format
    :param items: Flat TOC items
    :param include_links: Whether to include links
    :return: Markdown formatted TOC
    """
    result = []

    for item in items:
        indent = '  ' * (item['level'] - 1)
        title_text = f"[{item['title']}]({item['link']})" if include_links and item.get('link') else item['title']
        result.append(f"{indent}- {title_text}")

    return '\n'.join(result)