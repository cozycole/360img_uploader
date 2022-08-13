import unittest
from src import process_imgs as pim

class TestFileGrouping(unittest.TestCase):
    def test_group_none(self):
        result = pim.group_by_diff([], 2)
        self.assertEqual(result, [])

    def test_group_one(self):
        result = pim.group_by_diff([1], 2)
        self.assertEqual(result, [[1]])

    def test_group_diff0(self):
        result = pim.group_by_diff([1,2], 0)
        self.assertEqual(result, [[1],[2]])

    def test_grouping(self):
        result = pim.group_by_diff([1,2,3,10,11,12,42], 2)
        self.assertEqual(result, [[1,2,3], [10,11,12],[42]])
        self.assertTrue(len(result) == 3)

if __name__ == '__main__':
    unittest.main()