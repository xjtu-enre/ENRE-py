from enre.analysis.analyze_manager import RootDB
from enre.ent.EntKind import EntKind
from enre.util.common import typing_path, builtins_path


class BuildBuiltinsJson:

    def __init__(self, package_db: RootDB):
        self.package_db = package_db
        self.typing_builtins_ents = dict()
        self.project_ents = dict()
        self.helper_ent_types = [EntKind.Anonymous]
        self.helper_ent_names = ["builtins", "typing"]

    def work_flow(self):
        typing_db = self.package_db.tree[typing_path]
        builtins_db = self.package_db.tree[builtins_path]
        for ent in typing_db.dep_db.ents:
            ent.show_in_json = False
            self.typing_builtins_ents[ent] = False
        for ent in builtins_db.dep_db.ents:
            ent.show_in_json = False
            self.typing_builtins_ents[ent] = False

        for rel_path, module_db in self.package_db.tree.items():
            if rel_path in [typing_path, builtins_path]:
                continue
            for ent in module_db.dep_db.ents:
                self.handle_ent_ref(ent)

        for ent in self.package_db.global_db.ents:
            self.handle_ent_ref(ent)

    def handle_ent_ref(self, ent):
        for ref in ent.refs():
            if ref.target_ent in self.typing_builtins_ents:
                ref.target_ent.show_in_json = True
                ref.target_ent.show_ref = False

