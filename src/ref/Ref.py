from abc import ABC



class Ref(ABC):
    def __init__(self, ref_kind, target_ent, lineno, col_offset):
        self.ref_kind = ref_kind
        self.target_ent = target_ent
        self.lineno = lineno
        self.col_offset = col_offset
