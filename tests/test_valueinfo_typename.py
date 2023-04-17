from tests.utils import test_base


class ValueInfoTypeNameTests(test_base.BaseTest):
    """Tests for ValueInfo typename recursion"""

    def test_typename_recursion(self):
        self.analyze("ValueInfoTypeNameTests", "test_typename_recursion.py", """
            li = []
        """)
        self.show_qname('ValueInfoTypeNameTests.test_typename_recursion.doubleStar', show_cells=True)
