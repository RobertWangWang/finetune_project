import os
import os.path
from typing import List, Dict, Callable, Optional, Tuple

def save_to_separate_files(
    split_result: List[Dict],
    base_filename: str,
    callback: Callable[[Optional[Exception], Optional[str], Optional[int]], None]
) -> None:
    """
    Save split results to separate files
    :param split_result: List of split results (each containing 'summary' and 'content')
    :param base_filename: Base filename (without extension)
    :param callback: Callback function (err, output_dir, file_count)
    """
    # Get base directory and filename without extension
    base_path = os.path.dirname(base_filename)
    filename_without_ext = os.path.splitext(os.path.basename(base_filename))[0]

    # Create directory for split files
    output_dir = os.path.join(base_path, f"{filename_without_ext}_parts")

    # Ensure directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        callback(e, None, None)
        return

    # Recursive function to save files
    def save_file(index: int) -> None:
        if index >= len(split_result):
            # All files saved successfully
            callback(None, output_dir, len(split_result))
            return

        part = split_result[index]
        padded_index = str(index + 1).zfill(3)  # Ensure proper file sorting
        output_file = os.path.join(output_dir, f"{filename_without_ext}_part{padded_index}.md")

        # Format content with summary
        content = f"> **📑 Summarization：** *{part['summary']}*\n\n---\n\n{part['content']}"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            # Continue with next file
            save_file(index + 1)
        except IOError as e:
            callback(e, None, None)

    # Start saving files
    save_file(0)

# Note: The ensure_directory_exists function would be implemented in utils/common.py
# Here's a simple implementation for completeness:
def ensure_directory_exists(directory: str) -> None:
    """Ensure a directory exists, create if it doesn't"""
    os.makedirs(directory, exist_ok=True)