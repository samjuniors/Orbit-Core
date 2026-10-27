"""Orbit Evidence Lens: project-root isolation, review-only writes, bounded retrieval."""
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/runtime"))
import orbit_evidence
import orbit_mcp


class EvidenceLensTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.one = Path(self.folder.name) / "project-a"
        self.two = Path(self.folder.name) / "project-b"
        self.one.mkdir()
        self.two.mkdir()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_evidence.setup(self.db)

    def example(self, root=None, project="orbit", **changes):
        item = {"project_root": str(root or self.one), "project": project,
                "source_key": "ecc", "title": "ECC design study",
                "url": "https://github.com/affaan-m/ECC",
                "tags": ["agent", "memory", "research"],
                "note": "Research agent context and local memory boundaries."}
        item.update(changes)
        return item

    def call(self, name, payload):
        return orbit_mcp.execute(self.db, name, payload)

    def test_preview_only_does_not_write_or_create_project_files(self):
        before = list(self.one.iterdir())
        response = self.call("orbit_research_source_save", self.example())
        self.assertEqual(response["status"], "PREVIEW_ONLY")
        self.assertIsNone(response["existing_revision"])
        self.assertFalse(self.db.execute("SELECT 1 FROM orbit_research_sources").fetchone())
        self.assertEqual(list(self.one.iterdir()), before)

    def test_confirm_save_and_recall_with_verified_identity(self):
        saved = self.call("orbit_research_source_save", self.example(confirm_write=True))
        self.assertEqual(saved["status"], "SAVED")
        self.assertEqual(saved["source"]["revision"], 1)
        self.assertFalse(saved["source"]["network_verified"])
        self.assertEqual(saved["source"]["tags"], ["agent", "memory", "research"])
        ctx = self.call("orbit_research_context",
                        {"project_root": str(self.one), "project": "orbit",
                         "objective": "agent memory research"})
        self.assertEqual(ctx["status"], "RELEVANT_REFERENCES")
        self.assertEqual([x["key"] for x in ctx["sources"]], ["ecc"])
        self.assertFalse(ctx["network_access"])
        self.assertFalse(ctx["external_documents_written"])
        self.assertIn("UNVERIFIED", ctx["source_trust"])
        self.assertLessEqual(len(__import__("json").dumps(ctx, ensure_ascii=True)), 2400)

    def test_identical_save_is_idempotent_and_revisions_block_stale_updates(self):
        original = self.example(confirm_write=True)
        self.assertEqual(self.call("orbit_research_source_save", original)["status"], "SAVED")
        self.assertEqual(self.call("orbit_research_source_save", original)["status"], "UNCHANGED")
        changed = self.example(confirm_write=True, note="Changed reviewed notes")
        self.assertEqual(self.call("orbit_research_source_save", changed)["status"], "STALE_REVISION")
        self.assertEqual(self.call("orbit_research_source_save",
                                  dict(changed, expected_revision=9))["status"], "STALE_REVISION")
        self.assertEqual(self.call("orbit_research_source_save",
                                  dict(changed, expected_revision=1))["source"]["revision"], 2)
        self.assertEqual(self.call("orbit_research_source_save",
                                  dict(changed, expected_revision=1))["status"], "UNCHANGED")
        self.assertEqual(self.call("orbit_research_source_save",
                                  dict(original, expected_revision=1))["status"], "STALE_REVISION")

    def test_root_and_project_isolation_even_with_same_slug(self):
        self.call("orbit_research_source_save", self.example(confirm_write=True))
        for root, project in ((self.two, "orbit"), (self.one, "another")):
            ctx = self.call("orbit_research_context", {"project_root": str(root),
                            "project": project, "objective": "memory"})
            self.assertEqual(ctx["status"], "NO_RELEVANT_REFERENCES")
            self.assertEqual(ctx["sources"], [])
        self.call("orbit_research_source_save",
                  self.example(root=self.two, confirm_write=True, note="Other folder"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM orbit_research_sources").fetchone()[0], 2)

    def test_context_is_relevant_not_everything(self):
        self.call("orbit_research_source_save", self.example(confirm_write=True))
        self.call("orbit_research_source_save",
                  self.example(source_key="android", title="Android official UI",
                               url="https://developer.android.com/guide",
                               tags=["android", "kotlin"],
                               note="Review Compose native UI.", confirm_write=True))
        ctx = self.call("orbit_research_context",
                        {"project_root": str(self.one), "project": "orbit",
                         "objective": "Android kotlin development"})
        self.assertEqual([s["key"] for s in ctx["sources"]], ["android"])
        empty = self.call("orbit_research_context",
                          {"project_root": str(self.one), "project": "orbit",
                           "objective": "please research the best"})
        self.assertEqual(empty["sources"], [])

    def test_context_budget_limits_fields_and_no_uncapped_output(self):
        for i in range(20):
            self.call("orbit_research_source_save",
                      self.example(source_key=f"agent{i}", title=f"Agent {i}",
                                   url=f"https://example.com/research/{i}",
                                   tags=["agent"], note="Research "*100,
                                   confirm_write=True))
        context = self.call("orbit_research_context",
                            {"project_root": str(self.one), "project": "orbit",
                             "objective": "agent research", "limit": 6, "max_chars": 1200})
        self.assertLessEqual(len(__import__("json").dumps(context, ensure_ascii=True)), 1200)
        self.assertLessEqual(len(context["sources"]), 6)
        self.assertGreaterEqual(len(context["sources"]), 1)

    def test_long_objective_still_fits_context_budget(self):
        self.call("orbit_research_source_save", self.example(confirm_write=True))
        objective = "memory " * 95
        output = self.call("orbit_research_context",
                           {"project_root": str(self.one), "project": "orbit",
                            "objective": objective, "max_chars": 600})
        self.assertTrue(output["objective_truncated"])
        self.assertLessEqual(len(__import__("json").dumps(output, ensure_ascii=True)), 600)

    def test_reject_untrusted_url_forms(self):
        for value in ("http://github.com/a/b", "https://localhost/foo",
                      "https://127.0.0.1/x", "https://user:pass@example.com/a",
                      "https://example.com/a#fragment", "https://example.com/\rbad",
                      "file:///etc/passwd", "https://example.local/test"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.call("orbit_research_source_save", self.example(url=value, confirm_write=True))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM orbit_research_sources").fetchone()[0], 0)

    def test_reject_incorrect_tags_and_root(self):
        for tags in ([], ["Bad Space"], ["aaa", "aaa"], ["a"] * 9, ["../secret"]):
            with self.subTest(tags=tags):
                with self.assertRaises(ValueError):
                    self.call("orbit_research_source_save", self.example(tags=tags))
        with self.assertRaises(FileNotFoundError):
            self.call("orbit_research_source_save",
                      self.example(root=Path(self.folder.name) / "does-not-exist"))
        with patch.dict(os.environ, {"ORBIT_TRUSTED_ROOTS": str(self.two)}):
            with self.assertRaises(ValueError):
                self.call("orbit_research_source_save", self.example())

    def test_protocol_describes_safe_save_and_read_only_context(self):
        found = {t["name"]: t for t in orbit_mcp.TOOLS}
        self.assertFalse(found["orbit_research_source_save"]["annotations"]["readOnlyHint"])
        self.assertTrue(found["orbit_research_context"]["annotations"]["readOnlyHint"])
        with self.assertRaises(ValueError):
            orbit_mcp.validate("orbit_research_context", {
                "project_root": str(self.one), "project": "orbit",
                "objective": "test", "confirm_write": True})
        with self.assertRaises(ValueError):
            orbit_mcp.validate("orbit_research_source_save",
                               self.example(max_chars=100, confirm_write=True))


if __name__ == "__main__":
    unittest.main()
