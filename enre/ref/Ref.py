from abc import ABC



class Ref(ABC):
    def __init__(self, ref_kind, target_ent, lineno, col_offset):
        self.ref_kind = ref_kind
        self.target_ent = target_ent
        self.lineno = lineno
        self.col_offset = col_offset

    def __eq__(self, other: "Ref"):
        return isinstance(other, Ref) and \
               self.ref_kind == other.ref_kind and self.target_ent == other.target_ent \
               and self.lineno == other.lineno and self.col_offset == other.col_offset
