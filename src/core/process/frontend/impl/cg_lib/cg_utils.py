import ast
from core.process.frontend.impl.cfg_lib.cfg_utils import CfgBuildCtx
from lib.shared.logger import logger
from lib.shared.path_util import (
    module_2_path,
    last_longest_prefix_matches,
    split_path
)
from core.cache.connection import get_cache_proxy
import re
import builtins
from typing import Tuple
import os


# no need too build repeated edges
def search_callees(stmt_ast: str) -> set:
    callees = set()
    pattern = r"Call\(func=Name\(id='([^']+)',"
    matches = re.findall(pattern, stmt_ast)
    for match in matches:
        callee_function = match
        if callee_function not in dir(builtins):
            # TODO: add full path later
            callees.add(f"{callee_function}")

    pattern = r"Call\(func=Attribute\(value=Name\(id='[^']+'\s*,\s*ctx=.*\)\s*,\s*attr='([^']+)'"
    matches = re.findall(pattern, stmt_ast)
    for match in matches:
        callee_function = match
        if callee_function not in dir(builtins):
            # TODO: add full path later
            callees.add(f"{callee_function}")

    return callees


def update_cache(deck: int, *args: str):
    cache = get_cache_proxy()
    if cache.get(args[0]) == None:
        cache.set(args[0], dict())
    cache.set(args[0], update(cache.get(args[0]), deck, args[1:]))


def update(temp_dict: dict, args: list, name: str, lino: str):
    if args is None:
        if name not in temp_dict:
            temp_dict[name] = set()
        temp_dict[name].add(lino)
    elif args[0] == "":
        update(temp_dict, None, name, lino)
    elif len(args) == 1:
        # fill the dict
        # no recover but append, this need to check if the value is dict
        if temp_dict is None:
            logger().info("NOOOOOONE!")
        if args[0] not in temp_dict or temp_dict[args[0]] is None:
            temp_dict[args[0]] = dict()
        temp_dict[args[0]] = update(temp_dict[args[0]], None, name, lino)
    else:
        if args[0] not in temp_dict or temp_dict[args[0]] is None:
            temp_dict[args[0]] = dict()
        temp_dict[args[0]] = update(temp_dict[args[0]], args[1:], name, lino)
    return temp_dict


# add full path to create an entire "name"
def read_import_from(ctx: CfgBuildCtx, stmt: ast.ImportFrom) -> Tuple[str, dict]:
    if stmt.module == None:
        full_path = os.path.dirname(ctx.file)
    else:
        full_path = last_longest_prefix_matches(ctx.file, module_2_path(stmt.module))
    # finish this could be easy
    new_raw_names = dict()
    for name in stmt.names:
        raw_name = name.name
        # check if is None
        now_name = name.asname if name.asname is not None else name.name
        if now_name not in new_raw_names:
            new_raw_names[now_name] = set()
        new_raw_names[now_name] = raw_name
    return full_path, new_raw_names

def not_appeared_and_add(caller_file: str, callee_file: str, related_edge: dict) -> bool:
    if caller_file not in related_edge:
        related_edge[caller_file] = set()
        related_edge[caller_file].add(callee_file)
        return True
    else:
        if callee_file not in related_edge[caller_file]:
            related_edge[caller_file].add(callee_file)
            return True
        else:
            return False

def search_function_through_path(path, cache):
    path_list = split_path(path)
    current = cache
    for f in path_list:
        if f in current:
            current = current[f]
        else:
            return None
    return current
