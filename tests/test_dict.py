from tests.utils import test_base


class DictTests(test_base.BaseTest):
    """Tests for builtins.dict"""

    def test_dict_items(self):
        self.analyze("DictTests", "test_dict_items.py", """
            dic = {"name": "sy", "age": 18}

            for key, value in dic.items():
                print(key)
                print(value)
        """)
        self.assert_type('DictTests.test_dict_items.dic', "dict[str, (str | int)]")
        self.assert_type('DictTests.test_dict_items.key', "str")
        self.assert_type('DictTests.test_dict_items.value', "(str | int)")
