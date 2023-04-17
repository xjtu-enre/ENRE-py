from tests.utils import test_base


class ExportedTests(test_base.BaseTest):
    """Tests for entities exported"""

    def test_Entities_Exported(self):
        self.analyze("ExportedTests", "test_Entities_Exported.py", """
            # lib.py MODULE moniker | isExported = true
            class A:  # CLASS moniker | isExported = true
                class B:  # INNER CLASS moniker | isExported = true
                    ...
                def __init__(self):  # CONSTRUCTOR moniker(PARAMETER moniker) | isExported = true(Parameter false)
                    self.attr = 123  # ATTRIBUTE moniker | isExported = true
                    self._attr: str = '_attr'  # PROTECTED ATTRIBUTE moniker | isExported = true
                    self.__attr: str = '__attr'  # PRIVATE ATTRIBUTE moniker | isExported = false
                    var: str = "test"  # isExported = false
                def foo1(self):  # METHOD moniker(PARAMETER moniker) | isExported = true
                    self.attr2 = 321  # ATTRIBUTE moniker | isExported = true
                    class C:  # INNER CLASS moniker | isExported = false
                        class D:  # INNER CLASS moniker | isExported = false
                            ...
                def __foo2(self):  # PRIVATE METHOD moniker(PARAMETER moniker) | isExported = false
                    ...
            def foo3(para: int):  # FUNCTION moniker (PARAMETER moniker) |  isExported = true
                var: str = "test"  # VARIABLE isExported = false
            def __foo4():  # FUNCTION moniker | isExported = true
                ...
            a = 1  # SCOPE moniker | isExported = true
            global b  # SCOPE moniker | isExported = true
            b = 'b'
            lambda f: f  # LAMBDA isExported = false
        """)
        self.show_qname('ExportedTests.test_Entities_Exported.A', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.B', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.__init__', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.__init__.self', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.attr', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A._attr', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.__attr', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.__init__.var', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.foo1', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.attr2', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.foo1.C', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.foo1.C.D', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.A.__foo2', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.foo3', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.__foo4', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.a', show_cells=False)
        self.show_qname('ExportedTests.test_Entities_Exported.b', show_cells=False)
