from tests.utils import test_base


class ClassConstructorTests(test_base.BaseTest):
    """Tests for Class constructor __init__"""

    def test_init(self):
        self.analyze("ClassConstructorTests", "test_init.py", """
        class A:
            def __init__(self):
                self.attr = "A.attr"
            
            def method(self, para=0):
                return self.attr

        a = A()
        a.method()
        """)
        self.show_qname('ClassConstructorTests.test_init.A.__init__', show_cells=True)
        self.show_qname('ClassConstructorTests.test_init.A.method', show_cells=True)



