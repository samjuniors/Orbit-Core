"""Research-first v0.32 evidence gate: bounded, read-only, backward compatible.

These fixtures use synthetic sources and test structure only; they do not prove
external web browsing, repository licenses or third-party product capabilities.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_build
import orbit_mcp


def research_evidence():
    return {
        "task": "Choose an offline todo product implementation",
        "candidates": ["Native web platform APIs", "Existing tested list component"],
        "decision": "Integrate a reviewed list primitive and preserve local state",
        "sources": ["https://example.org/tasks", "https://github.com/example/task-list"],
        "risks": ["License and integration tests must be independently checked"],
        "competitors": [{
            "name": "Existing Task Product", "source": "https://example.org/tasks",
            "finding": "Alternative has list onboarding and saved tasks"
        }],
        "open_source": [{
            "name": "Open Task List", "source": "https://github.com/example/task-list",
            "license": "MIT", "finding": "Candidate checklist implementation"
        }],
        "exceptions": {},
        "routes_considered": ["REUSE", "INTEGRATE", "BUILD_NEW", "NO_BUILD"],
        "selected_route": "INTEGRATE",
        "unknowns": ["Actual source and license review is pending"],
        "checked_on": "2026-11-09"
    }


class ResearchFirstGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / "project").resolve()
        self.root.mkdir()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_build.setup(self.db)
        self.a = {"project": "research-test", "build_id": "new",
                  "objective": "Build a product from idea"}

    def begin(self, **kwargs):
        return orbit_build.begin(self.db, self.root, {**self.a, **kwargs})

    def advance(self, evidence, **kwargs):
        return orbit_build.advance(self.db, self.root,
            {**self.a, "expected_revision": 1, "outcome": "PASS",
             "evidence": json.dumps(evidence) if isinstance(evidence, dict) else evidence,
             "confirm_write": True, **kwargs})

    def test_new_full_build_requires_versioned_research_without_writing_preview(self):
        preview = self.begin(confirm_write=False)
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertEqual(self.db.execute("SELECT count(*) FROM build_runs").fetchone()[0], 0)
        started = self.begin(confirm_write=True)
        self.assertEqual(started["run"]["evidence"]["__orbit_research_policy"], "comparison-v1")
        self.assertEqual(started["run"]["stage"], "RESEARCH")
        old = {k: research_evidence()[k] for k in
               ("task", "candidates", "decision", "sources", "risks")}
        hold = self.advance(old)
        self.assertEqual(hold["status"], "HOLD")
        self.assertIn("competitor/open-source", hold["reason"])
        self.assertEqual(orbit_build.get(self.db, self.root, self.a)["revision"], 1)

        result = self.advance(research_evidence(), confirm_write=False)
        self.assertEqual(result["status"], "PREVIEW_ONLY")
        self.assertEqual(orbit_build.get(self.db, self.root, self.a)["stage"], "RESEARCH")
        done = self.advance(research_evidence())
        self.assertEqual(done["status"], "ADVANCED")
        self.assertEqual(done["run"]["stage"], "PLAN")
        self.assertEqual(done["run"]["evidence"]["RESEARCH"]["verification"],
                         "caller-reported-not-attested")

    def test_missing_comparison_requires_explicit_exception(self):
        self.begin(confirm_write=True)
        no_oss = research_evidence()
        no_oss["open_source"] = []
        self.assertEqual(self.advance(no_oss)["status"], "HOLD")
        no_oss["exceptions"] = {
            "open_source": "Inspected available sources; no compatible open-source option."
        }
        self.assertEqual(self.advance(no_oss)["status"], "ADVANCED")

    def test_missing_both_categories_can_be_explained_without_fake_candidates(self):
        self.begin(confirm_write=True)
        report = research_evidence()
        report["competitors"] = []
        report["open_source"] = []
        report["exceptions"] = {
            "competitors": "No comparable product after task-specific source review.",
            "open_source": "No compatible license and target platform candidate found."
        }
        self.assertEqual(self.advance(report)["status"], "ADVANCED")

    def test_reject_missing_provenance_invalid_date_routes_and_license(self):
        self.begin(confirm_write=True)
        for mutate in (
            lambda x: x["competitors"][0].update(source="unknown"),
            lambda x: x["open_source"][0].update(license=""),
            lambda x: x.update(checked_on="2026-02-31"),
            lambda x: x.update(selected_route="NO_ROUTE"),
            lambda x: x.update(routes_considered=["BUILD_NEW"]),
            lambda x: x.update(unknowns=["x" * 300]),
            lambda x: x.update(exceptions={"unknown_key": "Invalid state"}),
        ):
            report = research_evidence()
            mutate(report)
            self.assertEqual(self.advance(report)["status"], "HOLD")
        self.assertEqual(orbit_build.get(self.db, self.root, self.a)["revision"], 1)

    def test_legacy_persisted_research_is_not_retroactively_blocked(self):
        self.begin(confirm_write=True)
        old = orbit_build.get(self.db, self.root, self.a)
        persisted = json.loads(old["evidence_json"])
        del persisted["__orbit_research_policy"]
        self.db.execute("UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? AND build_id=?",
                        (json.dumps(persisted), self.a["project"], str(self.root), self.a["build_id"]))
        self.db.commit()
        legacy = {k: research_evidence()[k] for k in
                  ("task", "candidates", "decision", "sources", "risks")}
        self.assertEqual(self.advance(legacy)["status"], "ADVANCED")

    def test_scoped_fix_does_not_require_unrelated_competitor_survey(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('fixture')\n", encoding="utf-8")
        args = {**self.a, "change_kind": "fix", "baseline_reference": "git:fixture123",
                "confirm_write": True}
        started = orbit_build.begin(self.db, self.root, args)
        self.assertEqual(started["status"], "CREATED")
        self.assertEqual(started["run"]["stage"], "IMPLEMENT")
        self.assertNotIn("__orbit_research_policy", started["run"]["evidence"])

    def test_mcp_schema_matches_evidence_length(self):
        advance = next(item for item in orbit_mcp.TOOLS
                       if item["name"] == "orbit_build_advance")
        self.assertEqual(advance["inputSchema"]["properties"]["evidence"]["maxLength"], 4500)


if __name__ == "__main__":
    unittest.main()
