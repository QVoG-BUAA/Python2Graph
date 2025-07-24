"""
Gremlin client is a client for the Gremlin graph database.
"""

from time import sleep
from typing import List, Tuple
from typing_extensions import deprecated
from lib.shared.logger import logger
from core.cache.cache_proxy import CacheProxy
from core.graph.graph import GraphEdge, GraphVertex
from core.db.client import DbClient
from gremlin_python.structure.graph import GraphTraversalSource
from gremlin_python.process.graph_traversal import GraphTraversal
from gremlin_python.process.graph_traversal import __
from core.process.frontend.impl.cg_lib.cg_db import get_cg_db_transformed


@deprecated("This function has performance issue. Use _fetch_vertex_id instead.")
def _fetch_vertex_no_cache(g: GraphTraversal, v: GraphVertex):
    """
    We assume that the vertex is unique in the graph, and it
    must be found in the graph.
    """
    return g.has_label(v.label).has("key", v.key).next()


@deprecated("This function has performance issue. Use _fetch_vertex_id instead.")
def _fetch_vertex(g: GraphTraversal, vertex: GraphVertex, cache: CacheProxy = None):
    """
    Fetch the vertex from the graph. Use cache if it is provided.
    """
    if cache is None:
        return _fetch_vertex_no_cache(g, vertex)
    v = cache.get(vertex.key)
    if v is None:
        v = _fetch_vertex_no_cache(g, vertex)
        cache.set(vertex.key, v)
    return v


def _fetch_vertex_id(vertex: GraphVertex, cache: CacheProxy) -> int:
    """
    Fetch the vertex ID from cache. If not found, raise StopIteration.
    This function is mainly used in DFG construction. However, as we
    folded multi-line statement, a miss in cache doesn't mean the vertex
    is not in the graph. We need to check the above line numbers to find
    the statement it belongs to.
    """
    index = cache.get(vertex.key)
    if index is None:
        lineno = vertex.lineno
        while lineno > 0:
            index = cache.get(f"{vertex.props['file']}:{lineno}")
            if index is not None:
                return index
            lineno = lineno - 1
        raise StopIteration
    return index


class GremlinClient(DbClient):
    """
    Gremlin client for Neo4j-based Gremlin graph database.
    """

    def __init__(self, g: GraphTraversalSource, cache: CacheProxy) -> None:
        self.cache_cg_db_transformed = get_cg_db_transformed()
        self._g: GraphTraversalSource = g
        self.cache: CacheProxy = cache

    def clone(self):
        return GremlinClient(self._g, self.cache)

    def drop(self):
        """
        Drop all vertices and edges in the graph.
        It make take several seconds to finish on large graph.
        """
        self._g.V().drop().iterate()

    def init(self):
        """
        Gremlin database need no initialization.
        """
        pass

    def add_vertex(self, vertex: GraphVertex):
        iterator = self._g.add_v(vertex.label)
        if vertex.props is not None:
            for k, v in vertex.props.items():
                iterator = iterator.property(k, v)
        index = iterator.next().id
        self.cache.set(vertex.key, index)

    def add_vertex_bulk(self, vertices: List[GraphVertex]):
        """
        Using select can retrieve the indices of the vertices added.
        Storing them in cache can speed up the process to add edges.
        """
        iterator = self._g
        i = 0
        as_list = []
        for vertex in vertices:
            iterator = iterator.add_v(vertex.label)
            if vertex.props is not None:
                for k, v in vertex.props.items():
                    iterator = iterator.property(k, v)
            iterator.id_().as_(vertex.key)
            as_list.append(vertex.key)
            i = i + 1
        index_dict = iterator.select(*as_list).toList()[0]
        # FIXME: It is strange that in some cases, index_dict will be
        # an integer, so we add a check here.
        if isinstance(index_dict, int):
            index_dict = {as_list[0]: index_dict}
        for k, v in index_dict.items():
            self.cache.set(k, v)

    def _add_single_edge(
        self, it: GraphTraversal, edge: GraphEdge
    ) -> Tuple[GraphTraversal, bool]:
        try:
            _from_id = _fetch_vertex_id(edge.from_v, self.cache)
        except StopIteration:
            logger().error(f"Missing vertex: {edge.from_v}")
            return it, False
        try:
            _to_id = _fetch_vertex_id(edge.to_v, self.cache)
        except StopIteration:
            logger().error(f"Missing vertex: {edge.to_v}")
            return it, False
        # print(f"self.cache_cg_db: {self.cache_cg_db_transformed}")
        if edge.label == "dfg" and edge.from_v.key in self.cache_cg_db_transformed["callee"] \
                and edge.to_v.key in self.cache_cg_db_transformed["caller"] and \
                set(self.cache_cg_db_transformed["callee"][edge.from_v.key]) & \
                set(self.cache_cg_db_transformed["caller"][edge.to_v.key]):
            iterator = it.add_e(edge.label).from_(__.V(_to_id)).to(__.V(_from_id))
            # print(f"add edge: {edge.label} from {edge.from_v.key} to {edge.to_v.key}")
        else:
            iterator = it.add_e(edge.label).from_(__.V(_from_id)).to(__.V(_to_id))
        if edge.props is not None:
            for k, v in edge.props.items():
                iterator = iterator.property(k, v)
        return iterator, True

    def add_edge(self, edge: GraphEdge):
        iterator, status = self._add_single_edge(self._g, edge)
        if status:
            iterator.iterate()

    def add_edge_bulk(self, edges: List[GraphEdge]):
        self.cache_cg_db_transformed = get_cg_db_transformed()
        # print(f"cache_cg_db: {self.cache_cg_db_transformed}")
        max_retry = 3
        count = 0
        while count < max_retry:
            try:
                self.add_edge_bulk_impl(edges)
                return
            except Exception as e:
                count += 1
                logger().warning(
                    f"Error in add_edge_bulk {e}, retrying * {count}/{max_retry}"
                )
                sleep(1)
        logger().exception(
            f"!!! Failed to add edge bulk after retrying {max_retry} times."
        )

    def add_edge_bulk_impl(self, edges: List[GraphEdge]):
        if len(edges) == 0:
            return
        iterator: GraphTraversal = self._g
        can_iterate = False
        for edge in edges:
            # BUG: We didn't resolve line number missing issue here.
            #   so we need to skip the edge if any of the vertex has no line number.
            if edge.from_v.is_invalid() or edge.to_v.is_invalid():
                logger().debug(f"Invalid edge: {edge.from_v} -> {edge.to_v}")
                continue
            iterator, status = self._add_single_edge(iterator, edge)
            if status:
                can_iterate = True
        if can_iterate:
            iterator.iterate()

    def g(self):
        return self._g
