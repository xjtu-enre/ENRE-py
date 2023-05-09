import logging
import sys
import unittest
from tests.utils import test_utils
from typing import Tuple
from pathlib import Path

from enre.analysis.analyze_manager import AnalyzeManager
from enre.vis.representation import DepRepr

log = logging.getLogger(__name__)


class BaseTest(unittest.TestCase):
    python_version: Tuple[int, int] = sys.version_info[:2]

    temp_dict = None

    def analyze(self, package_name, py_file_name, py_file_code):
        """create a temp python package and analyze it
        """
        with test_utils.Tempdir() as d:
            package_path_str = d.create_directory(package_name)
            package_path = Path(package_path_str)
            file_path_str = package_path.joinpath(py_file_name).__str__()
            test_utils.create_file(file_path_str, py_file_code)

            root_path = package_path
            manager = AnalyzeManager(root_path)
            manager.work_flow()
            json = DepRepr.from_package_db(manager.root_db).to_json_1()
            # print(json)
            self.temp_json = json

    def show_qname(self, qname, show_cells=False):
        content = self.temp_json
        variables = content['variables']
        cells = content['cells']
        """Use id as key, variables field as value
        """
        v_dic = {}
        qname_id = None
        for v in variables:
            v_dic[v["id"]] = v
            if v["qualifiedName"] == qname:
                BaseTest.pprint(v)
                qname_id = v["id"]
        if qname_id and show_cells:

            print("--------------cells-------------")
            for c in cells:
                src = c["src"]
                dest = c["dest"]
                if qname_id in [src, dest]:
                    src_qname = v_dic[src]["qualifiedName"]
                    src_category = v_dic[src]["category"]
                    dest_qname = v_dic[dest]["qualifiedName"]
                    dest_category = v_dic[dest]["category"]
                    kind = c["values"]["kind"]
                    location = c["location"]
                    print(f"{src_category}[{src_qname}] {kind} {dest_category}[{dest_qname}] location: {location}")
            print("--------------------------->>>>>")
        return None

    @staticmethod
    def pprint(dic: dict):
        print("<<<<<---------------------------")
        print("--------------info--------------")
        for key, value in dic.items():
            print(str(key) + ": " + str(value))


    def assert_type(self, qname):
        ...

    def assert_dependency(self, src_qname, dest_qname, dep_kind):
        content = self.temp_json
        variables = content['variables']
        cells = content['cells']
        """Use id as key, variables field as value
        """
        v_dic = {}
        src_id = None
        dest_id = None
        for v in variables:
            v_dic[v["id"]] = v
            if v["qualifiedName"] == src_qname:
                src_id = v["id"]
            elif v["qualifiedName"] == dest_qname:
                dest_id = v["id"]
        self.assertTrue(src_id and dest_id, "Can't find src_id or dest_id")
        for c in cells:
            src = c["src"]
            dest = c["dest"]
            if src == src_id and dest == dest_id:
                kind = c["values"]["kind"]
                self.assertEqual(kind, dep_kind, "Dependency not match")
