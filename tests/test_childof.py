from tests.utils import test_base


class ChildOfTests(test_base.BaseTest):
    """Tests for ValueInfo typename recursion"""

    def test_Class_Inherit(self):
        self.analyze("ChildOfTests", "test_Class_Inherit.py", """
            class Parent:
                attr: int  # Childof Parent 
                def method(self):  # Childof Parent 
                    ...
                def foo(self):  # Childof Parent, Child
                    ...

            class Child(Parent):  # Childof Parent 
                attr: int  # Childof Child
                def method(self): # Childof Child
                    ...
        """)
        # self.show_qname('ChildOfTests.test_Class_Inherit', show_cells=True)
        self.assert_dependency('ChildOfTests.test_Class_Inherit.Parent',
                               'ChildOfTests.test_Class_Inherit',
                               'ChildOf')
        # self.show_qname('ChildOfTests.test_Class_Inherit.Parent', show_cells=True)
        # self.show_qname('ChildOfTests.test_Class_Inherit.Parent.method', show_cells=True)
        self.assert_dependency('ChildOfTests.test_Class_Inherit.Parent.method',
                               'ChildOfTests.test_Class_Inherit.Parent',
                               'ChildOf')
        # self.show_qname('ChildOfTests.test_Class_Inherit.Parent.foo', show_cells=True)
        # self.show_qname('ChildOfTests.test_Class_Inherit.Parent.attr', show_cells=True)
        self.assert_dependency('ChildOfTests.test_Class_Inherit.Parent.attr',
                               'ChildOfTests.test_Class_Inherit.Parent',
                               'ChildOf')
        # self.show_qname('ChildOfTests.test_Class_Inherit.Child', show_cells=True)
        self.assert_dependency('ChildOfTests.test_Class_Inherit.Parent.attr',
                               'ChildOfTests.test_Class_Inherit.Child',
                               'ChildOf')
        self.assert_dependency('ChildOfTests.test_Class_Inherit.Child.attr',
                               'ChildOfTests.test_Class_Inherit.Child',
                               'ChildOf')
