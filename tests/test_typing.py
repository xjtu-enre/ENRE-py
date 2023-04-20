from tests.utils import test_base


class TypingTests(test_base.BaseTest):
    """Tests for AnyStr"""

    def test_type_parameters(self):
        self.analyze("TypingTests", "test_type_parameters.py", """
            from typing import AnyStr
            
            def f(x: AnyStr) -> AnyStr: 
                ...

            a = f("")
        """)
        self.show_qname('TypingTests.test_type_parameters.f', show_cells=True)
        self.show_qname('TypingTests.test_type_parameters.f.x', show_cells=True)
        self.show_qname('TypingTests.test_type_parameters.a', show_cells=True)

    def test_optional(self):
        self.analyze("TypingTests", "test_optional.py", """
            from typing import Optional

            def f(x: Optional[str, int]) -> Optional[str]:
                ...
        """)
        self.show_qname('TypingTests.test_optional.f', show_cells=True)

    def test_TypeAlias(self):
        self.analyze("TypingTests", "test_TypeAlias.py", """
            from typing import TypeAlias
            i: TypeAlias = list[int]
        """)
        self.show_qname('TypingTests.test_TypeAlias.i', show_cells=True)
