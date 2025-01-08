class CgDb:
    def __init__(self) -> None:
        self.caller = {}
        self.callee = {}


CG_DB = CgDb()


def get_cg_db() -> CgDb:
    return CG_DB


def get_cg_db_transformed() -> CgDb:
    # print(f"CG_DB.caller: {CG_DB.caller}")
    # print(f"CG_DB.callee: {CG_DB.callee}")
    transformed = {
        "caller": dict(),
        "callee": dict(),
    }
    for file in CG_DB.caller:
        for func in CG_DB.caller[file]:
            for line in list(CG_DB.caller[file][func]):
                if line in transformed["caller"]:
                    transformed["caller"][line].append(func)
                else:
                    transformed["caller"][line] = [func]

    for file in CG_DB.callee:
        for func in CG_DB.callee[file]:
            for line in list(CG_DB.callee[file][func]):
                if line in transformed["callee"]:
                    transformed["callee"][line].append(func)
                else:
                    transformed["callee"][line] = [func]

    return transformed
