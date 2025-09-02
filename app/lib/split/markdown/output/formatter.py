from typing import List, Dict


def combine_markdown(split_result: List[Dict]) -> str:
    """
    Combine split text back into a single Markdown document
    :param split_result: List of split results (each containing 'summary' and 'content')
    :return: Combined Markdown document
    """
    result = []

    for i, part in enumerate(split_result):
        # Add separator and summary
        if i > 0:
            result.append('\n\n---\n\n')

        result.append(f"> **📑 Summarization：** *{part['summary']}*\n\n---\n\n{part['content']}")

    return ''.join(result)


# Example usage:
# if __name__ == "__main__":
#     split_data = [
#         {'summary': 'First section', 'content': '# Heading 1\n\nContent of first section'},
#         {'summary': 'Second section', 'content': '# Heading 2\n\nContent of second section'}
#     ]
#     combined = combine_markdown(split_data)
#     print(combined)