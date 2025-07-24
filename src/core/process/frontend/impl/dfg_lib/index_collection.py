#
# Fundamental data structures for DFG indexing
#


from lib.shared.utils import dict_dumps, get_parent_module_name, split_module_name
from lib.shared.node_util import SrcNode


############################################################
## Dependency
############################################################


class DependencyEntry:
    """
    This class record the direct dependency we get from SSA.
    It means, for node (of line_no), it depends on the dependency defined
    in SSA with block_id and index.
    """

    def __init__(self, node: SrcNode, block_id, index):
        """
        line_no: the line number of the statement
        block_id: the block id of the statement
        index: the 0-based index of the dependency in the block
        """
        self.node = node
        self.block_id = block_id
        self.index = index

    @property
    def line_no(self):
        return self.node.line_no

    def __eq__(self, other):
        return self.line_no == other.line_no

    def to_dict(self):
        return {"lineno": self.line_no, "block_id": self.block_id, "index": self.index}


class DependencyCollection:
    """
    Index database for DependencyEntry.
    """

    def __init__(self):
        self.context = []

    def add(self, entry: DependencyEntry):
        if self.find(entry.line_no) is None:
            self.context.append(entry)
        else:
            raise Exception("Duplicate dependency entry")

    def find(self, line_no):
        for entry in self.context:
            if entry.line_no == line_no:
                return entry
        return None

    def values(self):
        for entry in self.context:
            yield entry

    def dumps(self):
        return dict_dumps([entry.to_dict() for entry in self.context])


############################################################
## Constant (SSA)
############################################################


class ConstantEntry:
    """
    This class record the constant entry we get from SSA.
    It is the endpoint of each direct dependency.
    """

    def __init__(self, ident, id, node: SrcNode):
        self.ident = ident
        self.id = id
        self.node = node

    @property
    def line_no(self):
        return self.node.line_no if self.node is not None else 0

    def __eq__(self, other):
        return self.ident == other.lexeme and self.id == other.id

    def to_dict(self):
        return {"ident": self.ident, "id": self.id, "lineno": self.line_no}


class ConstantCollection:
    def __init__(self):
        self.context = []

    def add(self, entry: ConstantEntry):
        if self.shallow_find(entry.ident, entry.id) is None:
            self.context.append(entry)
        else:
            raise Exception("Duplicate constant entry")

    def shallow_find(self, ident, id) -> ConstantEntry:
        for entry in self.context:
            if entry.ident == ident and entry.id == id:
                return entry
        return None

    def find(self, ident, id) -> ConstantEntry:
        entry = self._find(ident, id)
        if entry is not None:
            return entry

        module_name, name = split_module_name(ident)
        while module_name != "":
            entry = self._find(module_name + "." + name, id)
            if entry is not None:
                return entry
            module_name = get_parent_module_name(module_name)
        return None

    def _find(self, ident, id) -> ConstantEntry:
        for entry in self.context:
            if entry.ident == ident and entry.id == id:
                return entry
        return None

    def dumps(self):
        return dict_dumps([entry.to_dict() for entry in self.context])


############################################################
## SSA record
############################################################


class SSA_Dep:
    """
    This class represents a single dependency in SSA.
    """

    def __init__(self):
        self.context = {}

    def add(self, ident, id_list: list):
        self.context[ident] = id_list

    def to_dict(self):
        return self.context

    def values(self):
        """
        Return all the values in the SSA dependency as iterator
        """
        for ident, id_list in self.context.items():
            if id_list is None:
                continue
            for id in id_list:
                yield (ident, id)


class SSA_Block:
    """
    This class represents a single block in SSA. Actually, it is
    a block in CFG, which contains several SSA dependencies.
    """

    def __init__(self):
        self.deps = []

    @property
    def count(self):
        return len(self.deps)

    def add(self, dep: SSA_Dep):
        self.deps.append(dep)

    def find(self, id):
        if id >= self.count:
            return None
        return self.deps[id]

    def to_dict(self):
        return [dep.to_dict() for dep in self.deps]


class SSA_Collection:
    """
    This is the final collection of SSA. It contains all SSA blocks
    """

    def __init__(self):
        self.blocks = {}

    def add(self, block_id, block: SSA_Block):
        self.blocks[block_id] = block

    def find_block(self, block_id) -> SSA_Block:
        return self.blocks.get(block_id, None)

    def find_dependency(self, block_id, index) -> SSA_Dep:
        block = self.find_block(block_id)
        if block is None:
            return None
        return block.find(index)

    def dumps(self):
        return dict_dumps(
            {block_id: block.to_dict() for block_id, block in self.blocks.items()}
        )
