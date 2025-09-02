def generate_enhanced_summary(section, outline, part_index=None, total_parts=None):
    """
    Generate enhanced summary containing all headings in the section
    :param section: Section dictionary
    :param outline: Table of contents outline
    :param part_index: Subsection index (optional)
    :param total_parts: Total subsections (optional)
    :return: Generated enhanced summary
    """
    # If it's document preface
    if (not section.get('heading') and section.get('level') == 0) or (
            not section.get('headings') and not section.get('heading')):
        # Get document title if exists
        doc_title = outline[0]['title'] if len(outline) > 0 and outline[0].get('level') == 1 else '文档'
        return f"{doc_title} 前言"

    # If there's a headings array, use it
    if section.get('headings') and len(section['headings']) > 0:
        # Sort headings by level and position
        sorted_headings = sorted(section['headings'], key=lambda x: (x.get('level', 0), x.get('position', 0)))

        # Build summary containing all headings
        headings_map = {}  # For deduplication

        # First process each heading to find its full path
        for heading in sorted_headings:
            # Skip empty headings
            if not heading.get('heading'):
                continue

            # Find current heading in outline
            heading_index = next((i for i, item in enumerate(outline)
                                  if item.get('title') == heading.get('heading')
                                  and item.get('level') == heading.get('level')), -1)

            if heading_index == -1:
                # If not found in outline, use current heading directly
                headings_map[heading['heading']] = heading['heading']
                continue

            # Find all parent headings
            path_parts = []
            parent_level = heading.get('level', 1) - 1

            for i in range(heading_index - 1, -1, -1):
                if parent_level <= 0:
                    break
                if outline[i].get('level') == parent_level:
                    path_parts.insert(0, outline[i].get('title'))
                    parent_level -= 1

            # Add current heading
            path_parts.append(heading.get('heading'))

            # Generate full path and store in map
            full_path = ' > '.join(path_parts)
            headings_map[full_path] = full_path

        # Convert all heading paths to array and sort by depth
        paths = sorted(headings_map.values(), key=lambda x: (x.count('>'), x))

        # If no valid headings, return default summary
        if not paths:
            return section.get('heading', '未命名段落')

        # If single heading, return directly
        if len(paths) == 1:
            summary = paths[0]
            # If it's a partial section, add Part info
            if part_index is not None and total_parts > 1:
                summary += f' - Part {part_index}/{total_parts}'
            return summary

        # If multiple headings, generate multi-heading summary
        summary = ''

        # Try to find common prefix
        first_path = paths[0]
        segments = first_path.split(' > ')

        for i in range(len(segments) - 1):
            prefix = ' > '.join(segments[:i + 1])
            is_common_prefix = True

            for j in range(1, len(paths)):
                if not paths[j].startswith(prefix + ' > '):
                    is_common_prefix = False
                    break

            if is_common_prefix:
                summary = prefix + ' > ['
                # Add non-common parts
                for j, path in enumerate(paths):
                    unique_part = path[len(prefix) + 3:]  # +3 for ' > ' length
                    summary += (', ' if j > 0 else '') + unique_part
                summary += ']'
                break

        # If no common prefix, use full list
        if not summary:
            summary = ', '.join(paths)

        # If it's a partial section, add Part info
        if part_index is not None and total_parts > 1:
            summary += f' - Part {part_index}/{total_parts}'

        return summary

    # Compatibility logic when no headings array exists
    if not section.get('heading') and section.get('level') == 0:
        return '文档前言'

    # Find current section in outline
    current_heading_index = next((i for i, item in enumerate(outline)
                                  if item.get('title') == section.get('heading')
                                  and item.get('level') == section.get('level')), -1)

    if current_heading_index == -1:
        return section.get('heading', '未命名段落')

    # Find all parent headings
    parent_headings = []
    parent_level = section.get('level', 1) - 1

    for i in range(current_heading_index - 1, -1, -1):
        if parent_level <= 0:
            break
        if outline[i].get('level') == parent_level:
            parent_headings.insert(0, outline[i].get('title'))
            parent_level -= 1

    # Build summary
    summary = ''

    if parent_headings:
        summary = ' > '.join(parent_headings) + ' > '

    summary += section.get('heading', '')

    # If it's a partial section, add Part info
    if part_index is not None and total_parts > 1:
        summary += f' - Part {part_index}/{total_parts}'

    return summary


def generate_summary(section, outline, part_index=None, total_parts=None):
    """
    Legacy summary generation function, kept for compatibility
    :param section: Section dictionary
    :param outline: Table of contents outline
    :param part_index: Subsection index (optional)
    :param total_parts: Total subsections (optional)
    :return: Generated summary
    """
    return generate_enhanced_summary(section, outline, part_index, total_parts)
