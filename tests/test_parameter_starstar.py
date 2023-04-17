from tests.utils import test_base


class ParameterUnpackTests(test_base.BaseTest):
    """Tests for Class constructor __init__"""

    def test_starstar_unpack(self):
        self.analyze("ParameterUnpackTests", "test_starstar_unpack.py", """
        def doubleStar(common, **double):
            print("Common args: ", common)
            print("Double args: ", double)

        doubleStar("hello", **{"name": "Test", "age": 24})
        """)
        self.show_qname('ParameterUnpackTests.test_starstar_unpack.doubleStar', show_cells=True)

    def test_star_unpack(self):
        self.analyze("ParameterUnpackTests", "test_star_unpack.py", """
        def foo(para1, *para2):
            print(para1)
            print(para2)

        foo("para1", *("123", 5))
        """)
        self.show_qname('ParameterUnpackTests.test_star_unpack.foo', show_cells=True)

    def test_star_unpack2(self):
        self.analyze("ParameterUnpackTests", "test_star_unpack2.py", """
        def foo(para1, *para2):
            print(para1)
            print(para2)

        t = ("123", 5)
        foo("para1", *t)
        """)
        self.show_qname('ParameterUnpackTests.test_star_unpack2.foo', show_cells=True)



