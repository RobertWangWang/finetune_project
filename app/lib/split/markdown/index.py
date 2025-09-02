from app.lib.split.markdown.cores import splitter, parser


def split_markdown(
        markdown_text: str,
        min_split_length: int,
        max_split_length: int,
) -> list:
    # Parse document structure
    outline = parser.extract_outline(markdown_text)

    # Split document by headings
    sections = parser.split_by_headings(markdown_text, outline)

    # Process sections to meet split requirements
    processed_sections = splitter.process_sections(
        sections,
        outline,
        min_split_length,
        max_split_length
    )

    # Format results with summaries
    return [
        {
            "result": f"> **📑 Summarization：** *{section['summary']}*\n\n---\n\n{section['content']}",
            **section
        }
        for section in processed_sections
    ]