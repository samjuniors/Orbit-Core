"""_visual_walk stops listing at its budgets before materializing entries."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_specialists


class WalkBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def walk(self):
        truncated = [False]
        seen = [(parts, list(dirs), list(names)) for parts, _fd, dirs, names
                in orbit_specialists._visual_walk(self.root, truncated=truncated)]
        return seen, truncated[0]

    def test_large_directory_listing_is_capped(self):
        for i in range(20):
            (self.root / f"f{i}.txt").write_text("x", encoding="utf-8")
        with patch.object(orbit_specialists, "_WALK_MAX_DIR_ENTRIES", 5):
            seen, truncated = self.walk()
        self.assertTrue(truncated)
        self.assertLessEqual(len(seen[0][2]), 5)

    def test_total_entry_budget_stops_many_empty_directories(self):
        for i in range(30):
            (self.root / f"d{i}").mkdir()
        with patch.object(orbit_specialists, "_WALK_MAX_TOTAL_ENTRIES", 10):
            seen, truncated = self.walk()
        self.assertTrue(truncated)
        self.assertLessEqual(sum(len(d) + len(n) for _p, d, n in seen), 10)

    def test_small_tree_is_complete(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("x", encoding="utf-8")
        seen, truncated = self.walk()
        self.assertFalse(truncated)
        self.assertIn((("src",), [], ["a.py"]), seen)


if __name__ == "__main__":
    unittest.main()
