import strict
import unittest
import itertools

class TestTyping(unittest.TestCase):
    def test_union(self):
        from strict.typing import Union
        for r in range(1, 6):
            for ts in itertools.combinations(
                (int, str, dict, set, tuple, list),
                r
            ):
                with self.subTest(ts=ts, r=r):
                    union = Union[ts]
                    self.assertTrue(all(isinstance(t(), union) for t in ts))
            
if __name__ == '__main__':
##    unittest.main()
    pass
