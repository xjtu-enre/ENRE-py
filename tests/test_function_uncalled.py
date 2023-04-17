from tests.utils import test_base


class FunctionUnCalledTests(test_base.BaseTest):
    """Tests for Class constructor __init__"""

    def test_function_uncalled(self):
        self.analyze("FunctionUnCalledTests", "test_function_uncalled.py", """
        def uncalled_func(common, **double):
            print("Common args: ", common)
            print("Double args: ", double)
        
        """)
        self.show_qname('FunctionUnCalledTests.test_function_uncalled.uncalled_func', show_cells=True)



