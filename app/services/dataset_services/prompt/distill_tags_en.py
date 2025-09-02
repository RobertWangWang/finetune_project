def distill_tags_en_prompt(
        tag_path: str,
        parent_tag: str,
        existing_tags: list[str] = None,
        count: int = 10,
        global_prompt: str = ''
) -> str:
    """
    Prompt for constructing sub-tags based on parent tag

    Args:
        tag_path (str): Tag chain, e.g., "Knowledge Base->Sports"
        parent_tag (str): Parent tag name, e.g., "Sports"
        existing_tags (list[str]): Existing sub-tags under this parent tag (to avoid duplicates), e.g., ["Football", "Table Tennis"]
        count (int): Number of sub-tags to generate, e.g.: 10
        global_prompt (str): Project-wide global prompt

    Returns:
        str: Prompt
    """
    if existing_tags is None:
        existing_tags = []

    existing_tags_text = (
        f"Existing sub-tags include: {'、'.join(existing_tags)}. Please do not generate duplicate tags."
        if existing_tags
        else ""
    )

    # Build the global prompt section
    global_prompt_text = f"You must follow this requirement: {global_prompt}" if global_prompt else ""

    return f"""
You are a professional knowledge tag generation assistant. I need you to generate {count} sub-tags for the parent tag "{parent_tag}".

The full tag chain is: {tag_path if tag_path else parent_tag}

Please follow these rules:
{global_prompt_text}
1. Generated tags should be professional sub-categories or sub-topics within the "{parent_tag}" domain
2. Each tag should be concise and clear, typically 2-6 characters
3. Tags should be clearly distinguishable, covering different aspects
4. Tags should be nouns or noun phrases; avoid verbs or adjectives
5. Tags should be practical and serve as a basis for question generation
6. Tags should have explicit numbering. If the parent tag is numbered (e.g., 1 Automobiles), sub-tags should be 1.1 Car Brands, 1.2 Car Models, 1.3 Car Prices, etc.
7. If the parent tag is unnumbered (e.g., "Automobiles"), indicating top-level tag generation, sub-tags should be 1 Car Brands 2 Car Models 3 Car Prices, etc.

{existing_tags_text}

Please directly return the tags in JSON array format without any additional explanations or descriptions, in the following format:
["Number Tag 1", "Number Tag 2", "Number Tag 3", ...]
"""