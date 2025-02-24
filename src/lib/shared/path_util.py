"""
Handle path related operations.
"""

import os

def last_longest_prefix_matches(path1, path2):
    """
    Start at the end of path1 and search forward for the longest prefix that matches path2
    """
    path1s = path1.split('/')
    # path2s = path2.split('/')
    _max = 0
    _index = len(path1s)

    # from lib.shared.logger import logger
    # logger().info(f"###path1{path1}")
    # logger().info(f"###path2{path2}")

    for i in range(len(path1s) - 1, 0, -1):
        temp = len(os.path.commonprefix([path1[i:].split('/'), path2.split('/')]))
        if _max < temp:
            _max = temp
            _index = i
    if _max == 0:
        temp = path1s[:-1]
        if len(temp) == 0:
            return path2
        else:
            return '/'.join(temp) + '/' + path2
    else:
        return '/'.join(path1s[:_index]) + '/' + path2


def format_path(path):
    """
    Unify the path format to absolute Unix style.
    """
    return os.path.abspath(path).replace("\\", "/")


def module_2_path(path):
    """
    Change ast.ImportFrom module to Unix style path.
    """
    return path.replace(".", "/") + ".py"


def get_relative_path(path, base_path):
    """
    Get the relative path of a file to a base path.
    """
    return os.path.relpath(path, base_path)


def get_parent_path(file_path):
    """
    Get the parent directory of a file.
    """
    return os.path.dirname(file_path)


def get_file_name(file_path):
    """
    Get the file name of a file.
    """
    return os.path.basename(file_path)


def get_file_extension(file_path):
    """
    Get the file extension of a file.
    """
    return os.path.splitext(file_path)[1]


def enumerate_files(path, extensions=None):
    """
    Enumerate files of given extensions in a directory.
    params:
        path: str, the directory to enumerate
        extensions: list, the file extensions to enumerate
    """
    if extensions is None:
        extensions = [""]

    if not os.path.isdir(path):
        raise ValueError(f"Path {path} is not a directory.")

    for root, dirs, files in os.walk(path):
        for file in files:
            if get_file_extension(file) in extensions:
                yield format_path(os.path.join(root, file))


def remove_file(path):
    """
    Remove a file.
    """
    if os.path.exists(path):
        os.remove(path)


def create_file(path):
    """
    Create a file recursively if it does not exist.
    """
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w"):
            pass
    return path


def split_path(path):
    """
    Split a path into a list of directories.
    """
    return path.replace("\\", "/").split("/")