"""
Core functions to generate control flow graph from Python code.
"""

from core.process.frontend.frontend import FrontEndDescriptor
from core.process.frontend.impl.cg_lib.cg_db import get_cg_db
from core.process.frontend.impl.cg_lib.cg_db import get_cg_db
from core.process.frontend.impl.cg_lib.cg_utils import not_appeared_and_add
from lib.shared.logger import logger
from core.process.collector import Collector
from core.graph.graph import GraphEdge, GraphVertex
from core.cache.connection import get_cache_proxy
from lib.shared.task_util import Task


class CgBuildCtx:
    def __init__(self, sink: Collector.Sink) -> None:
        self.sink: Collector.Sink = sink


_RELATED_SET = set()


def _contains(caller: str, callee: str):
    return (caller, callee) in _RELATED_SET


def _add_related(caller: str, callee: str):
    _RELATED_SET.add((caller, callee))


def _add_edge(ctx: CgBuildCtx, caller_id: str, callee_id: str, related_edge: dict):
    """
    you should add every functionDef as key to cache,
    the value could be all vertexs belong to the CFG of this def, or just the pair of their name and id
    for there may be same lines in one CFG, the value should be a list,
    and of course, you should design a class for the "pair"
    in order to divide the same name, the key must contain name and full path
    you may need to add a pair which has a stop_word-key and value of id to save the functionDef vertex itself
    """
    # TODO: the form of id has changed
    if caller_id is not None and callee_id is not None:
        logger().info(f"ced_id: {callee_id};cer_id: {caller_id}")
        caller_file = caller_id[: caller_id.index(":")]
        caller = GraphVertex(
            "code",
            {
                "file": caller_file,
                "lineno": int(caller_id[caller_id.index(":") + 1 :]),
            },
        )
        callee_file = callee_id[: callee_id.index(":")]
        callee = GraphVertex(
            "code",
            {
                "file": callee_file,
                "lineno": int(callee_id[callee_id.index(":") + 1 :]),
            },
        )
        if callee_file != caller_file:
            # add related_edge from caller_file to callee_file
            # check if appeared
            if not _contains(caller_file, callee_file):
                _add_related(caller_file, callee_file)
                ctx.sink.put_edge(
                    GraphEdge(
                        "related",
                        GraphVertex("file", {"file": caller_file}),
                        GraphVertex("file", {"file": callee_file}),
                    )
                )
            # if not_appeared_and_add(caller_file, callee_file, related_edge):
            #     ctx.sink.put_edge(GraphEdge("related", caller, callee))
        ctx.sink.put_edge(GraphEdge("cg", callee, caller))
        # if callee_file != caller_file:
        ctx.sink.put_edge(GraphEdge("dfg", caller, callee))

        call_back = GraphVertex(
            "code",
            {
                "file": caller_file,
                "lineno": -1 * int(caller_id[caller_id.index(":") + 1 :]),
            },
        )
        ctx.sink.put_edge(GraphEdge("cg", call_back, callee))
        ctx.sink.put_edge(GraphEdge("dfg", callee, call_back))


def __read_and_add(ctx: CgBuildCtx, cache_ed: dict, cache_er: dict):
    logger().info(f"len of cache_caller:{len(cache_er)}")
    related_edge = dict()
    for spt_path, sub_ed in cache_ed.items():
        logger().info(f"spt_path:{spt_path}")
        if isinstance(sub_ed, set):
            if spt_path in cache_er:
                linos = cache_er[spt_path]
                caller_id = next(iter(linos))
                for callee_id in sub_ed:
                    _add_edge(ctx, caller_id, callee_id, related_edge)
            else:
                for file_name, func_names in cache_er.items():
                    for callee_id in sub_ed:
                        if spt_path in func_names:
                            linos = func_names[spt_path]
                            caller_id = next(iter(linos))
                            _add_edge(ctx, caller_id, callee_id, related_edge)

        else:
            if spt_path in cache_er:
                logger().info(f"caller contains {spt_path}")
                sub_er = cache_er[spt_path]
                __read_and_add(ctx, sub_ed, sub_er)


def _find_link(sink: Collector.Sink):
    ctx = CgBuildCtx(sink)
    # TODO: rewrite read cache
    """
    for callee may have un_full path, cannot use caller as loop element
    walk callee "tree", and check caller tree at the same time
    for callee may have un_full path, cannot use caller as loop element
    walk callee "tree", and check caller tree at the same time
    maybe we can mark if reach file node instead of folder node
    so that we can traverse all file nodes in one folder,
    meanwhile check if they have function with the same name as callee,
    meanwhile check if they have function with the same name as callee,
    and then build links we want 
    """
    cache = get_cg_db()
    callers = cache.caller
    callees = cache.callee
    cache = get_cg_db()
    callers = cache.caller
    callees = cache.callee
    if callers == None:
        logger().error("Missing 'callers'")
    # traverse callees for every call must have a caller,it's easier for Error judging
    __read_and_add(ctx, callees, callers)


def _build_cg(sink: Collector.Sink):
    logger().info(f"Building CG...")
    _find_link(sink)
    logger().info("CG ready to go!")


class CgFrontEndDescriptor(FrontEndDescriptor):
    def __init__(self, root: str, sink: Collector.Sink) -> None:
        super().__init__(root, None, None, sink, 0)

    def get_process(self) -> Task:
        return Task(_build_cg, (self.sink,))


def get_cg_frontend_descriptor(
    root: str, sink: Collector.Sink, max_workers=None, scg: dict = None
):
    """
    Get the descriptor for CG frontend process.
    """
    return CgFrontEndDescriptor(root, sink)
