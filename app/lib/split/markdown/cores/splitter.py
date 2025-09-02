import re

def split_long_section(section, max_split_length):
    """
    Split long paragraphs
    :param section: Paragraph object (dict with 'content' key)
    :param max_split_length: Maximum split length in characters
    :return: List of split paragraphs
    """
    content = section['content']
    paragraphs = re.split(r'\n\n+', content)
    result = []
    current_chunk = ''

    for paragraph in paragraphs:
        # If the current paragraph itself exceeds the maximum length, may need further splitting
        if len(paragraph) > max_split_length:
            # If current chunk is not empty, add it to results first
            if len(current_chunk) > 0:
                result.append(current_chunk)
                current_chunk = ''

            # Split extra long paragraphs (e.g., by sentences or fixed length)
            sentence_split = re.findall(r'[^.!?。！？]+[.!?。！？]+', paragraph) or [paragraph]

            # Process split sentences
            sentence_chunk = ''
            for sentence in sentence_split:
                if len(sentence_chunk + sentence) <= max_split_length:
                    sentence_chunk += sentence
                else:
                    if len(sentence_chunk) > 0:
                        result.append(sentence_chunk)
                    # If a single sentence exceeds max length, may need further splitting
                    if len(sentence) > max_split_length:
                        # Simply split by fixed length
                        for i in range(0, len(sentence), max_split_length):
                            result.append(sentence[i:i + max_split_length])
                    else:
                        sentence_chunk = sentence

            if len(sentence_chunk) > 0:
                current_chunk = sentence_chunk
        elif len(current_chunk + '\n\n' + paragraph) <= max_split_length:
            # If adding current paragraph doesn't exceed max length, add to current chunk
            current_chunk = current_chunk + '\n\n' + paragraph if current_chunk else paragraph
        else:
            # If adding current paragraph would exceed max length, add current chunk to results and start new chunk
            result.append(current_chunk)
            current_chunk = paragraph

    # Add the last chunk if it exists
    if current_chunk:
        result.append(current_chunk)

    return result


def process_sections(sections, outline, min_split_length, max_split_length):
    """
    Process sections, splitting according to min and max split lengths
    :param sections: List of section dicts
    :param outline: Table of contents outline
    :param min_split_length: Minimum split length in characters
    :param max_split_length: Maximum split length in characters
    :return: List of processed sections
    """
    # Preprocessing: Merge adjacent small sections
    preprocessed_sections = []
    current_section = None

    for section in sections:
        content_length = len(section['content'].strip())

        if content_length < min_split_length and current_section:
            # If current section is smaller than min length and there's an accumulated section, try to merge
            merged_content = f"{current_section['content']}\n\n{'#' * section['level']} {section['heading']}\n{section['content']}" if section.get(
                'heading') else f"{current_section['content']}\n\n{section['content']}"

            if len(merged_content) <= max_split_length:
                # If merged content doesn't exceed max length, merge
                current_section['content'] = merged_content
                if section.get('heading'):
                    current_section.setdefault('headings', [])
                    current_section['headings'].append({
                        'heading': section['heading'],
                        'level': section['level'],
                        'position': section.get('position')
                    })
                continue

        # If cannot merge, start new section
        if current_section:
            preprocessed_sections.append(current_section)

        current_section = {
            **section,
            'headings': [{'heading': section['heading'], 'level': section['level'],
                          'position': section.get('position')}] if section.get('heading') else []
        }

    # Add the last section
    if current_section:
        preprocessed_sections.append(current_section)

    result = []
    accumulated_section = None  # For accumulating sections smaller than min split length

    for i in range(len(preprocessed_sections)):
        section = preprocessed_sections[i]
        content_length = len(section['content'].strip())

        # Check if we need to accumulate sections
        if content_length < min_split_length:
            # If we haven't started accumulating, create new accumulated section
            if not accumulated_section:
                accumulated_section = {
                    'heading': section.get('heading'),
                    'level': section.get('level'),
                    'content': section['content'],
                    'position': section.get('position'),
                    'headings': [{'heading': section['heading'], 'level': section['level'],
                                  'position': section.get('position')}] if section.get('heading') else []
                }
            else:
                # Already accumulating, add current section to accumulated section
                heading_part = f"{'#' * section['level']} {section['heading']}\n" if section.get('heading') else ''
                accumulated_section['content'] += f"\n\n{heading_part}{section['content']}"
                if section.get('heading'):
                    accumulated_section.setdefault('headings', [])
                    accumulated_section['headings'].append({
                        'heading': section['heading'],
                        'level': section['level'],
                        'position': section.get('position')
                    })

            # Only process when accumulated content reaches min length
            accumulated_length = len(accumulated_section['content'].strip())
            if accumulated_length >= min_split_length:
                summary = generate_enhanced_summary(accumulated_section, outline)

                if accumulated_length > max_split_length:
                    # If accumulated section exceeds max length, split further
                    sub_sections = split_long_section(accumulated_section, max_split_length)

                    for j in range(len(sub_sections)):
                        result.append({
                            'summary': f"{summary} - Part {j + 1}/{len(sub_sections)}",
                            'content': sub_sections[j]
                        })
                else:
                    # Add to results
                    result.append({
                        'summary': summary,
                        'content': accumulated_section['content']
                    })

                accumulated_section = None  # Reset accumulated section
            continue

        # If we have an accumulated section, process it first
        if accumulated_section:
            summary = generate_enhanced_summary(accumulated_section, outline)
            accumulated_length = len(accumulated_section['content'].strip())

            if accumulated_length > max_split_length:
                # If accumulated section exceeds max length, split further
                sub_sections = split_long_section(accumulated_section, max_split_length)

                for j in range(len(sub_sections)):
                    result.append({
                        'summary': f"{summary} - Part {j + 1}/{len(sub_sections)}",
                        'content': sub_sections[j]
                    })

                # Handle any remaining small chunks (not implemented fully as in JS version)
            else:
                # Add to results
                result.append({
                    'summary': summary,
                    'content': accumulated_section['content']
                })

            accumulated_section = None  # Reset accumulated section

        # Process current section
        # If section length exceeds max split length, split further
        if content_length > max_split_length:
            sub_sections = split_long_section(section, max_split_length)

            # Create standard headings array for current section if needed
            if not section.get('headings') and section.get('heading'):
                section['headings'] = [
                    {'heading': section['heading'], 'level': section['level'], 'position': section.get('position')}]

            for j in range(len(sub_sections)):
                sub_section = sub_sections[j]
                summary = generate_enhanced_summary(section, outline, j + 1, len(sub_sections))

                result.append({
                    'summary': summary,
                    'content': sub_section
                })
        else:
            # Create standard headings array for current section if needed
            if not section.get('headings') and section.get('heading'):
                section['headings'] = [
                    {'heading': section['heading'], 'level': section['level'], 'position': section.get('position')}]

            # Generate enhanced summary and add to results
            summary = generate_enhanced_summary(section, outline)

            content = f"{'#' * section['level']} {section['heading']}\n{section['content']}" if section.get(
                'heading') else section['content']

            result.append({
                'summary': summary,
                'content': content
            })

    # Process any remaining small sections
    if accumulated_section:
        if len(result) > 0:
            # Try to merge remaining small section with last result
            last_result = result[-1]
            merged_content = f"{last_result['content']}\n\n{accumulated_section['content']}"

            if len(merged_content) <= max_split_length:
                # If merged content doesn't exceed max length, merge
                summary = generate_enhanced_summary({
                    **accumulated_section,
                    'content': merged_content
                }, outline)

                result[-1] = {
                    'summary': summary,
                    'content': merged_content
                }
            else:
                # If merged content would exceed max length, add accumulated_section as separate section
                summary = generate_enhanced_summary(accumulated_section, outline)
                content = f"{'#' * accumulated_section['level']} {accumulated_section['heading']}\n{accumulated_section['content']}" if accumulated_section.get(
                    'heading') else accumulated_section['content']
                result.append({
                    'summary': summary,
                    'content': content
                })
        else:
            # If result is empty, add accumulated_section directly
            summary = generate_enhanced_summary(accumulated_section, outline)
            content = f"{'#' * accumulated_section['level']} {accumulated_section['heading']}\n{accumulated_section['content']}" if accumulated_section.get(
                'heading') else accumulated_section['content']
            result.append({
                'summary': summary,
                'content': content
            })

    return result


# Note: The generate_enhanced_summary function would need to be implemented separately
def generate_enhanced_summary(section, outline, part=None, total_parts=None):
    """
    Placeholder for the summary generation function
    :param section: Section dictionary
    :param outline: Table of contents outline
    :param part: Part number (optional)
    :param total_parts: Total parts (optional)
    :return: Generated summary string
    """
    # This should be implemented based on your specific requirements
    base_summary = section.get('heading', 'Untitled Section')
    if part and total_parts:
        return f"{base_summary} (Part {part} of {total_parts})"
    return base_summary