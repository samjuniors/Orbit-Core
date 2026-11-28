"""Priority-order validation for bounded swarm draft previews."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_tasks
import orbit_swarm_draft


class SwarmPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)

    def _task(self, key):
        return {
            "task_key": key, "step": "review", "role": "reviewer",
            "goal": f"Review the proposed task {key} and verify evidence.",
            "reason": f"Priority ordering test for task {key}.",
            "write_paths": [], "depends_on": [],
        }

    def test_priority_order_controls_review_wave_order(self):
        result = orbit_swarm_draft.preview(
            self.conn, self.root, "sample",
            {"tasks": [self._task("z-task"), self._task("a-task")],
             "priority_order": ["z-task", "a-task"]}
        )
        self.assertEqual(result["status"], "DRAFT_VALIDATED")
        self.assertEqual(result["review_waves"][0]["task_keys"], ["z-task", "a-task"])

    def test_invalid_priority_order_is_rejected(self):
        with self.assertRaises(ValueError):
            orbit_swarm_draft.preview(
                self.conn, self.root, "sample",
                {"tasks": [self._task("z-task"), self._task("a-task")],
                 "priority_order": ["z-task"]}
            )


if __name__ == "__main__":
    unittest.main()
