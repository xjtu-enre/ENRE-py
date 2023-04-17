from tests.utils import test_base


class ChildOfTests(test_base.BaseTest):
    """Tests for ValueInfo typename recursion"""

    def test_Class_Inherit(self):
        self.analyze("ChildOfTests", "test_Class_Inherit.py", """
            class Parent:
                def method(self, para):
                    self.attr = para
                    print("Parent's method")

            class Child(Parent):
                def method(self, para):
                    self.attr = para
                    print("Child's method")
        """)
        self.show_qname('ChildOfTests.test_Class_Inherit', show_cells=True)
        self.show_qname('ChildOfTests.test_Class_Inherit.Parent', show_cells=True)
        self.show_qname('ChildOfTests.test_Class_Inherit.Parent.method', show_cells=True)
        self.show_qname('ChildOfTests.test_Class_Inherit.Child', show_cells=True)
        self.show_qname('ChildOfTests.test_Class_Inherit.Child.method', show_cells=True)
