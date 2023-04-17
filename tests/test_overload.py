from tests.utils import test_base


class OverloadTests(test_base.BaseTest):
    """Tests for entities overload"""

    def test_function_overload(self):
        self.analyze("OverloadTests", "test_function_overload.py", """
            from typing import overload

            class A:
                @overload
                def foo(self, para: int) -> int:
                    ...
            
                @overload
                def foo(self, para: str) -> str:
                    ...
            
                def foo(self, para):
                    if isinstance(para, int):
                        return 123
                    else:
                        return "str"

            a = A()
            print(a.foo("a"))
        """)
        self.show_qname('OverloadTests.test_function_overload.A.foo', show_cells=True)
