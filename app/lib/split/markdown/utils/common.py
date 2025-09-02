import os
import os.path


def ensure_directory_exists(directory: str) -> None:
    """
    Check and create directory if it doesn't exist
    :param directory: Directory path
    """
    os.makedirs(directory, exist_ok=True)


def get_filename_without_ext(file_path: str) -> str:
    """
    Get filename without extension from file path
    :param file_path: File path
    :return: Filename without extension
    """
    return os.path.splitext(os.path.basename(file_path))[0]


# Example usage:
# if __name__ == "__main__":
#     # Test directory creation
#     test_dir = "./test_directory"
#     ensure_directory_exists(test_dir)
#     print(f"Directory exists or created: {os.path.exists(test_dir)}")
#
#     # Test filename extraction
#     test_path = "/path/to/document.txt"
#     print(f"Filename without extension: {get_filename_without_ext(test_path)}")  # Output: "document"