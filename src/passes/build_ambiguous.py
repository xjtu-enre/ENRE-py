from interp.manager_interp import PackageDB
from passes.entity_pass import DepDBPass


class BuildAmbiguous(DepDBPass):
    def __init__(self, package_db: PackageDB):
        self._package_db = package_db

    @property
    def package_db(self) -> PackageDB:
        return self._package_db

    def execute_pass(self):
        self._build_ambiguous_attributes()

    def _build_ambiguous_attributes(self):
        ...