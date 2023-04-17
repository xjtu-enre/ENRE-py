from tests.utils import test_base


class ParameterDefaultTests(test_base.BaseTest):
    """Tests for function parameter default"""

    def test_default(self):
        self.analyze("ParameterDefaultTests", "test_default.py", """
        def default(common, defaultStr="default", defaultNum=0):
            print("Common args", common)
            print("Default String", defaultStr)
            print("Default Number", defaultNum)
            
        default("common", "default", 0)
        """)
        self.show_qname('ParameterDefaultTests.test_default.default', show_cells=True)

    def test_default_lack(self):
        """defaults=[<ast.Constant object at 0x0000028E47F25630>, <ast.Constant object at 0x0000028E47F25660>]
        """
        self.analyze("ParameterDefaultTests", "test_default_lack.py", """
        def default(common, defaultStr="default", defaultNum=0):
            print("Common args", common)
            print("Default String", defaultStr)
            print("Default Number", defaultNum)

        default("common")
        """)
        self.show_qname('ParameterDefaultTests.test_default_lack.default', show_cells=True)

    def test_default_star(self):
        """kw_defaults=[None, None, <ast.Constant object at 0x000001E8EFEC5660>]
        """
        self.analyze("ParameterDefaultTests", "test_default_star.py", """
        def default(common, para1=1, *, para2, defaultNum, defaultStr="default"):
            print(common)
            print(para1)
            print(para2)
            print(defaultNum)
            print(defaultStr)

        default("common", defaultNum=0, para2=2)
        default("common", defaultNum=0)
        """)
        self.show_qname('ParameterDefaultTests.test_default_star.default', show_cells=True)

    def test_default_starstar(self):
        self.analyze("ParameterDefaultTests", "test_default_starstar.py", """
        def default_starstar(common, para=2, **para1):
            print(common)
            print(para)
            print(para1)

        default_starstar("common", 1)
        """)
        self.show_qname('ParameterDefaultTests.test_default_starstar.default_starstar', show_cells=True)
        self.show_qname('ParameterDefaultTests.test_default_starstar.default_starstar.para1', show_cells=True)

    def test_default_all_kw(self):
        self.analyze("ParameterDefaultTests", "test_default_all_kw.py", """
        def default(para, para1, para2):
            print(para)
            print(para1)
            print(para2)

        default(para2="0", para1=1, para=2)
        """)
        self.show_qname('ParameterDefaultTests.test_default_all_kw.default', show_cells=True)

