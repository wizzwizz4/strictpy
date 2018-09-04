import strict
import unittest
import itertools

class TestTyping(unittest.TestCase):
    def test_union(self):
        from strict.typing import Union
        all_ts = (int, str, dict, set, tuple, list)
        for r in range(1, 6):
            for ts in itertools.combinations(all_ts, r):
                with self.subTest(ts=ts, r=r):
                    union = Union[ts]
                    self.assertTrue(all(isinstance(t(), union) for t in ts))
                    self.assertTrue(all(not isinstance(t(), union)
                                        for t in all_ts
                                        if t not in ts))
            
if __name__ == '__main__':
##    unittest.main()
    pass
