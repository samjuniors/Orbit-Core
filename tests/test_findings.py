"""Tests for persistent project finding reconciliation."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_findings


def audit(snapshot, findings, status="SCANNED"):
    return {"status": status, "inventory_snapshot_sha256": snapshot,
            "findings": findings}


def finding(fid="TEST_STRUCTURE_NOT_DISCOVERED", evidence=None):
    return {
        "id": fid, "category": "testing", "severity": "MEDIUM",
        "confidence": "MEDIUM", "summary": "No conventional test structure discovered.",
        "evidence": evidence or ["src/main.py"],
        "recommendation": "Review the actual test strategy.",
        "is_confirmed_defect": False,
    }


class ProjectFindingTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        orbit_findings.setup(self.conn)
        self.root = "/tmp/orbit-project"
        self.project = "sample"

    def tearDown(self):
        self.conn.close()

    def test_new_persistent_resolved_and_recurring_lifecycle(self):
        first = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        self.assertEqual(first["status"], "RECONCILED")
        row = first["findings"][0]
        self.assertEqual(row["lifecycle"], "NEW")
        self.assertEqual(row["disposition"], "UNREVIEWED")
        self.assertFalse(row["is_confirmed_defect"])

        second = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("b" * 64, [finding()])
        )
        self.assertEqual(second["findings"][0]["lifecycle"], "OPEN")
        self.assertEqual(second["findings"][0]["occurrence_count"], 1)

        resolved = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("c" * 64, [])
        )
        self.assertEqual(resolved["resolved_count"], 1)
        self.assertEqual(resolved["findings"][0]["lifecycle"], "RESOLVED")

        recurring = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("d" * 64, [finding()])
        )
        self.assertEqual(recurring["findings"][0]["lifecycle"], "RECURRING")
        self.assertEqual(recurring["findings"][0]["occurrence_count"], 2)
        self.assertEqual(recurring["findings"][0]["disposition"], "UNREVIEWED")

    def test_incomplete_scan_marks_stale_and_never_resolves(self):
        orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("b" * 64, [], "INCOMPLETE")
        )
        self.assertEqual(result["resolved_count"], 0)
        self.assertEqual(result["findings"][0]["lifecycle"], "STALE")

    def test_disposition_requires_revision_and_does_not_confirm_defect(self):
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        updated = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        self.assertEqual(updated["status"], "UPDATED")
        self.assertFalse(updated["defect_confirmed"])
        stale = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "FALSE_POSITIVE", row["revision"]
        )
        self.assertEqual(stale["status"], "STALE_REVISION")

    def test_evidence_change_resets_disposition_for_review(self):
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        changed = orbit_findings.reconcile(
            self.conn, self.project, self.root,
            audit("b" * 64, [finding(evidence=["src/main.py", "src/api.py"])])
        )
        self.assertEqual(changed["findings"][0]["disposition"], "UNREVIEWED")

    def test_project_and_root_are_isolated(self):
        orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        other = orbit_findings.list_findings(self.conn, self.project, "/tmp/other")
        self.assertEqual(other["status"], "EMPTY")



    def test_task_preview_requires_accepted_current_finding_and_is_read_only(self):
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        blocked = orbit_findings.task_preview(
            self.conn, self.project, self.root, row["finding_id"], row["revision"]
        )
        self.assertEqual(blocked["status"], "REVIEW_REQUIRED")
        accepted = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        preview = orbit_findings.task_preview(
            self.conn, self.project, self.root, row["finding_id"], accepted["finding"]["revision"]
        )
        self.assertEqual(preview["status"], "TASK_SPEC_READY")
        self.assertFalse(preview["task_created"])
        self.assertEqual(preview["task_spec"]["write_paths"], [])
        self.assertEqual(preview["task_spec"]["depends_on"], [])
        self.assertFalse(self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_agent_tasks'"
        ).fetchone())

    def test_task_link_requires_existing_task_and_explicit_confirmation(self):
        import orbit_tasks
        orbit_tasks.setup(self.conn)
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        accepted = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        self.conn.execute(
            """INSERT INTO orbit_agent_tasks
               (project,project_root,task_key,step,role,goal,reason,write_paths,depends_on,
                status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.project,self.root,"finding-remediation","audit-remediation","software-engineer",
             "Review and address the accepted structural finding with evidence and tests.",
             "Owner accepted the finding; inspect source and tests before changes.",
             "[]","[]","PLANNED","now","now"),
        )
        preview = orbit_findings.link_task(
            self.conn,self.project,self.root,row["finding_id"],"finding-remediation",
            accepted["finding"]["revision"],False)
        self.assertEqual(preview["status"],"PREVIEW_ONLY")
        self.assertFalse(preview["linked"])
        linked = orbit_findings.link_task(
            self.conn,self.project,self.root,row["finding_id"],"finding-remediation",
            accepted["finding"]["revision"],True)
        self.assertEqual(linked["status"],"LINKED")
        self.assertEqual(linked["finding"]["linked_task_ids"],["finding-remediation"])

    def test_evidence_paths_reject_windows_and_traversal_forms(self):
        for path in (r"..\\secret.txt", r"C:\\secret.txt", "/etc/passwd", "src/../secret", "src//main.py", "src/./main.py", "src\\main.py"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                orbit_findings._validate_finding(finding(evidence=[path]))


if __name__ == "__main__":
    unittest.main()


    def test_structural_reconcile_does_not_resolve_source_scope(self):
        orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        source_finding = finding("SOURCE_DYNAMIC_CODE_1234567890")
        source = orbit_findings.reconcile(
            self.conn, self.project, self.root,
            audit("b" * 64, [source_finding]), audit_scope="SOURCE"
        )
        self.assertEqual(source["audit_scope"], "SOURCE")
        structural_empty = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("c" * 64, [])
        )
        all_rows = orbit_findings.list_findings(self.conn, self.project, self.root)
        source_rows = orbit_findings.list_findings(
            self.conn, self.project, self.root, audit_scope="SOURCE"
        )
        self.assertEqual(structural_empty["resolved_count"], 1)
        self.assertEqual(source_rows["findings"][0]["lifecycle"], "NEW")
        self.assertEqual(source_rows["findings"][0]["audit_scope"], "SOURCE")
        self.assertEqual(len(all_rows["findings"]), 2)

    def test_legacy_findings_table_gets_additive_scope_migration(self):
        legacy = sqlite3.connect(":memory:")
        legacy.row_factory = sqlite3.Row
        legacy.execute("""CREATE TABLE orbit_project_findings (
            project TEXT NOT NULL, project_root TEXT NOT NULL, finding_id TEXT NOT NULL,
            category TEXT NOT NULL, severity TEXT NOT NULL, confidence TEXT NOT NULL,
            summary TEXT NOT NULL, evidence TEXT NOT NULL, recommendation TEXT NOT NULL,
            lifecycle TEXT NOT NULL, disposition TEXT NOT NULL DEFAULT 'UNREVIEWED',
            first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, last_snapshot TEXT NOT NULL,
            evidence_sha256 TEXT NOT NULL, occurrence_count INTEGER NOT NULL DEFAULT 1,
            revision INTEGER NOT NULL DEFAULT 1, linked_task_ids TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY(project,project_root,finding_id))""")
        legacy.execute("""INSERT INTO orbit_project_findings
            VALUES('p','/tmp/p','OLD','testing','LOW','LOW','old','[]','review',
                   'OPEN','UNREVIEWED','now','now','x','y',1,1,'[]')""")
        legacy.commit()
        orbit_findings.setup(legacy)
        row = legacy.execute("SELECT audit_scope FROM orbit_project_findings WHERE finding_id='OLD'").fetchone()
        self.assertEqual(row["audit_scope"], "STRUCTURAL")
        legacy.close()
