"""
Definition of node for the graph.
It is a concept for frontend only, used for graph generation.
The backend database won't rely on this class.
"""

from lib.shared.utils import obj_dumps


class GraphNode:
    """
    Base class for all nodes in the graph.
    """

    def __init__(self, label: str, props: dict = None):
        self.label = label
        self.props = props

    def __str__(self):
        return self.to_string()

    def to_string(self, indent=4):
        """
        If indent is 0, will output a compact string in one line.
        """
        return obj_dumps(self, indent)


class GraphVertex(GraphNode):
    """
    Represent a vertex node in graph.
    """

    def __init__(self, label: str, props: dict = None):
        super().__init__(label, props)
        self.key = self._generate_key()
        props["key"] = self.key

    def is_invalid(self):
        """
        Some how the "code" vertex may lack lineno, which makes it invalid.
        """
        return self.label == "code" and self.props.get("lineno", 0) == 0

    @property
    def lineno(self):
        return self.props.get("lineno", 0)

    def generate_pseudo_key(self, lineno: int):
        """
        This is used in DFG, where the actual line number may not be available.
        So we generate a pseudo key to represent the line it belongs to.
        """
        file = self.props.get("file", None)
        if file is None:
            raise ValueError("file is required to generate pseudo key")
        self.key = f"{file}:{lineno}"

    def _generate_key(self):
        file = self.props.get("file", None)
        lineno = self.props.get("lineno", None)
        if file and lineno:
            return f"{file}:{lineno}"
        elif file:
            return file
        else:
            raise ValueError("file is required to create a key")


class GraphEdge(GraphNode):
    """
    Represent an edge in graph.
    """

    def __init__(
        self,
        label: str,
        from_v: GraphVertex = None,
        to_v: GraphVertex = None,
        props: dict = None,
    ):
        super().__init__(label, props)
        self.from_v = from_v
        self.to_v = to_v
