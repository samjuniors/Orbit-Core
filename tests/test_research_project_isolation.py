"""Regression: external research pointers never leak across Orbit projects.

Run: python -m unittest discover -s tests -p 'test_research_project_isolation.py' -v
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))
import orbit_evidence


class ResearchProjectIsolationTests(unittest.TestCase):
    def test_project_and_folder_scoping_survives_sqlite_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root_a = base / "todo-a"
            root_b = base / "todo-b"
            root_a.mkdir()
            root_b.mkdir()
            db = base / "orbit.sqlite3"
            args = {
                "source_key": "ecc-agent-patterns",
                "title": "ECC agent patterns",
                "url": "https://github.com/affaan-m/ECC",
                "tags": ["agent", "memory", "research"],
                "note": "Reference for agent memory research only; not an approved instruction.",
                "confirm_write": True,
            }

            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                orbit_evidence.setup(conn)
                result = orbit_evidence.save(conn, root_a.resolve(), "project-a", args)
                self.assertEqual(result["status"], "SAVED")

                # A recorded pointer remains informational, not an approval.
                saved = result["source"]
                self.assertEqual(saved["status"], "REFERENCE_ONLY")
                self.assertFalse(saved["network_verified"])
                self.assertIn("never agent instructions", saved["source_trust"])

            # Reopen SQLite to model an Orbit/IDE restart.
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                orbit_evidence.setup(conn)
                query = {"objective": "agent memory research", "limit": 6}

                owner = orbit_evidence.context(conn, root_a.resolve(), "project-a", query)
                self.assertEqual(owner["status"], "RELEVANT_REFERENCES")
                self.assertEqual([s["key"] for s in owner["sources"]], ["ecc-agent-patterns"])
                self.assertFalse(owner["network_access"])
                self.assertFalse(owner["external_documents_written"])

                # Different project key, same folder: no leakage.
                other_key = orbit_evidence.context(conn, root_a.resolve(), "project-b", query)
                self.assertEqual(other_key["status"], "NO_RELEVANT_REFERENCES")
                self.assertEqual(other_key["sources"], [])

                # Same key, different folder: no leakage.
                other_folder = orbit_evidence.context(conn, root_b.resolve(), "project-a", query)
                self.assertEqual(other_folder["status"], "NO_RELEVANT_REFERENCES")
                self.assertEqual(other_folder["sources"], [])

                # Verify there is no hidden direct-record cross-project access.
                self.assertIsNone(orbit_evidence.current(conn, root_a.resolve(), "project-b", args["source_key"]))
                self.assertIsNone(orbit_evidence.current(conn, root_b.resolve(), "project-a", args["source_key"]))

    def test_research_is_not_returned_without_objective_match(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "todo"
            root.mkdir()
            with sqlite3.connect(Path(temp) / "db.sqlite3") as conn:
                conn.row_factory = sqlite3.Row
                orbit_evidence.setup(conn)
                orbit_evidence.save(conn, root.resolve(), "todo", {
                    "source_key": "ecc-agent-patterns",
                    "title": "ECC agent patterns",
                    "url": "https://github.com/affaan-m/ECC",
                    "tags": ["agent", "memory", "research"],
                    "note": "Reusable agent memory ideas.",
                    "confirm_write": True,
                })
                result = orbit_evidence.context(conn, root.resolve(), "todo", {
                    "objective": "todo interface styling and responsive layout",
                })
                self.assertEqual(result["status"], "NO_RELEVANT_REFERENCES")
                self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()
