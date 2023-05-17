from tests.utils import test_base


class LateAnnotationTests(test_base.BaseTest):
    """Tests for late annotation"""

    def test_late_annotation(self):
        self.analyze("LateAnnotationTests", "test_late_annotation.py", """
            from typing import TYPE_CHECKING

            if TYPE_CHECKING:
                from ext import Bindings

            def get_module_level_bindings(self) -> "Bindings":
                bindings: Bindings = []
        """)
        self.assert_type('LateAnnotationTests.test_late_annotation.get_module_level_bindings.bindings', "Any")
