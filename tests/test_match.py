from tests.utils import test_base


class MatchTests(test_base.BaseTest):
    """Tests for match"""

    def test_match(self):
        self.analyze("MatchTests", "test_match.py", """
            class A:
                ...
            class B:
                ...
            
            v = A()
            match v:
                case "123" as s:
                    print(s)
                case 123 as i:
                    print(i)
                case A() as c:
                    print(c)
        """)
        self.assert_type('MatchTests.test_match.v', "MatchTests.test_match.A")
        self.assert_type('MatchTests.test_match.s', "str")
        self.assert_type('MatchTests.test_match.i', "int")
        self.assert_type('MatchTests.test_match.c', "MatchTests.test_match.A")
