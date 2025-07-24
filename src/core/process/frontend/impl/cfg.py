"""
Core functions to generate control flow graph from Python code.
"""

import ast
import json
from core.process.frontend.common import get_frontend_producer, count_python_files
from core.process.frontend.impl.cfg_lib.cfg_utils import CfgBuildCtx
from core.process.frontend.impl.cg_lib.cg_db import get_cg_db
from core.process.frontend.impl.cg_lib.cg_utils import (
    read_import_from,
    search_callees,
    update,
    search_function_through_path
)
from lib.shared.task_util import Task, get_cpu_count
from lib.shared.node_util import SrcNode, to_src_without_children
from lib.shared.logger import logger
from lib.shared.path_util import (
    get_file_name,
    get_relative_path,
    split_path
)
from core.process.frontend.frontend import FrontEndDescriptor
from core.process.collector import Collector
from core.graph.graph import GraphEdge, GraphVertex
from scalpel.cfg import CFGBuilder
from ast2json import ast2json
from core.cache.connection import get_cache_proxy
from collections import OrderedDict


def get_blocks_of_cfg(flattened_cfg):
    blocks = []
    for _, cfg in flattened_cfg.items():
        blocks += cfg.get_all_blocks()

    return blocks


def _get_no_fc_stmt(block):
    no_fcDef_statements = []
    for statement in block.statements:
        if not isinstance(statement, ast.FunctionDef) and not isinstance(
            statement, ast.ClassDef
        ):
            no_fcDef_statements.append(statement)
    return no_fcDef_statements


# def _add_vertices(ctx: CfgBuildCtx, block, visited: set):
def _add_vertices(
    cache_caller: dict, cache_callee: dict, rename_map: dict, ctx: CfgBuildCtx, block, visited: set
):
    if block.id in visited:
        return
    visited.add(block.id)

    no_fc_stmt = _get_no_fc_stmt(block)

    ctx.visited_block_first[block.id] = no_fc_stmt[0] if len(no_fc_stmt) > 0 else None
    # ctx.visited_block_last[block.id] = block.statements[-1]

    for statement in block.statements:
        node: SrcNode = to_src_without_children(statement)
        json_ast = json.dumps(ast2json(statement))
        v = None

        if isinstance(statement, ast.FunctionDef):
            v = GraphVertex(
                "code",
                {
                    "file": ctx.file,
                    "json": json_ast,
                    "code": node.code,
                    "lineno": node.line_no,
                    "functionDefName": statement.name,
                },
            )
            ctx.function_def_dic[statement.name] = GraphVertex(
                "code",
                {
                    "file": ctx.file,
                    "lineno": node.line_no,
                    "functionDefName": statement.name,
                },
            )
            # load info under key "caller"
            # get file path and add function name to the end
            # add full path

            # __update_cache(1, "caller", f"{statement.name}", v.key)
            # __update(cache_caller, 1, f"{ctx.file}:{statement.name}", v.key)
            update(cache_caller, split_path(ctx.file), statement.name, v.key)
            # logger().info(f"add caller: {ctx.file}:{statement.name};{v.key}")

            # add function end vertex
            ctx.sink.put_vertex(GraphVertex(
                "code",
                {
                    "file": ctx.file,
                    "code": f"[function end] {statement.name}",
                    "lineno": -1 * node.line_no,
                    "json": json_ast
                },
            ))
        elif isinstance(statement, ast.ImportFrom):
            # must import before use, so no need to do another loop
            full_path, new_raw_names = read_import_from(ctx, statement)
            # set now_name as key, raw_name and path for the value
            """
            remember that the path may not be full one, get current path to mix it
            at the same time, now_name should be asname, use name to replace when it is null
            raw_name will always be name

            for checking in callees, match the now_name and replace it with raw_name
            then you can simply add path to it
            """
            # import is just usable in this file, so no need to use cache
            for now_name, raw_name in new_raw_names.items():
                rename_map[now_name] = (raw_name, full_path)
                # logger().info("Name is \"" + raw_name + "\" later \"" + now_name + " with path " + full_path)
            v = GraphVertex(
                "code",
                {
                    "file": ctx.file,
                    "json": json_ast,
                    "code": node.code,
                    "lineno": node.line_no,
                },
            )
        else:
            v = GraphVertex(
                "code",
                {
                    "file": ctx.file,
                    "json": json_ast,
                    "code": node.code,
                    "lineno": node.line_no,
                },
            )
            # if there is Call line: load info under key "callee"
            """
            here, we choose a double-deck dic as value, keys are function names
            and each function name has a list of the files and linos(id) it appears
            """
            # match JSON and put Call
            stmt_ast = json.dumps(ast.dump(to_src_without_children(statement).node))
            callees = search_callees(stmt_ast)
            for callee in callees:

                # TODO: search, add the real name and path
                if callee in rename_map:
                    details = rename_map[callee]
                    raw_name = details[0]
                    full_path = details[1]
                else:
                    raw_name = callee
                    full_path = ctx.file
                update(cache_callee, split_path(full_path), raw_name, v.key)

        if v is not None:
            ctx.sink.put_vertex(v)
        else:
            logger().error(f"Failed to create vertex for: {statement}")

    for exit in block.exits:
        _add_vertices(cache_caller, cache_callee, rename_map, ctx, exit.target, visited)


def _add_edges(
        ctx: CfgBuildCtx, block, visited: set, name=None, cache_caller=None, belong_to_func_name=None
):
    if block.id in visited:
        return
    visited.add(block.id)

    no_fc_stmt = _get_no_fc_stmt(block)
    from_v = None

    if name is not None and name in ctx.function_def_dic:
        from_v = ctx.function_def_dic[name]
    if len(no_fc_stmt) != 0:
        if block.id == 1:
            from_v = GraphVertex("file", {"file": ctx.file})
            stmt_to = no_fc_stmt[0]
            node = to_src_without_children(stmt_to)
            to_v = GraphVertex("code", {"file": ctx.file, "lineno": node.line_no})
            # BUG: This seems to add duplicate edges?
            # ctx.edge_agent.add(GremlinEdge("cfg", from_v, to_v))
        for statement in no_fc_stmt:
            node = to_src_without_children(statement)
            to_v = GraphVertex("code", {"file": ctx.file, "lineno": node.line_no})
            if from_v is not None and to_v is not None:
                ctx.sink.put_edge(GraphEdge("cfg", from_v, to_v))
            from_v = to_v

    if from_v is not None:
        for exit in block.exits:
            if ctx.visited_block_first[exit.target.id] is not None:
                node = to_src_without_children(ctx.visited_block_first[exit.target.id])
                to_v = GraphVertex("code", {"file": ctx.file, "lineno": node.line_no})
                ctx.sink.put_edge(GraphEdge("cfg", from_v, to_v))
    for exit in block.exits:
        _add_edges(ctx, exit.target, visited, cache_caller=cache_caller, belong_to_func_name=belong_to_func_name)

    # add cfg and dfg from the last statement to the special vertex [function end]
    if len(block.exits) == 0:
        func_info = search_function_through_path(ctx.file, cache_caller)
        if func_info is not None and belong_to_func_name in func_info:
            line_no = -1 * int(list(func_info[belong_to_func_name])[0].split(":")[1])
            to_v = GraphVertex("code", {"file": ctx.file, "lineno": line_no})
            ctx.sink.put_edge(GraphEdge("cfg", from_v, to_v))
            if len(no_fc_stmt) != 0:
                statement = no_fc_stmt[-1]
                if statement is not None and isinstance(statement, ast.Return) and statement.value is not None:
                    ctx.sink.put_edge(GraphEdge("dfg", to_v, from_v))


def _build_cfg_for_single_file(root: str, file: str, sink: Collector.Sink):
    logger().info(f"Building CFG for: {file}")
    flattened_cfg = CFGBuilder().build_from_file(
        get_file_name(file), file, flattened=True
    )
    file = get_relative_path(file, root)
    # first we put a file vertex
    sink.put_vertex(GraphVertex("file", {"file": file}))
    ctx = CfgBuildCtx(file, sink)

    # TODO: create new cache value
    cache = get_cg_db()

    cache_caller = cache.caller
    cache_callee = cache.callee
    rename_map = OrderedDict()

    for _, cfg in flattened_cfg.items():
        _add_vertices(cache_caller, cache_callee, rename_map, ctx, cfg.entryblock, set())
        _add_edges(ctx, cfg.entryblock, set(), name=cfg.name, cache_caller=cache_caller, belong_to_func_name=cfg.name)


def get_cfg_frontend_descriptor(
    root: str, producer: Task, sink: Collector.Sink, max_workers=None
) -> FrontEndDescriptor:
    """
    Get the descriptor for CFG frontend process.
    """
    if max_workers is None:
        max_workers = max(1, min(get_cpu_count(), count_python_files(root) // 4))
    return FrontEndDescriptor(
        root=root,
        producer=producer,
        consumer=Task(_build_cfg_for_single_file),
        sink=sink,
        max_workers=max_workers,
    )
