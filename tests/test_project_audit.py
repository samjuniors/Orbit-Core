"""Tests for bounded read-only project structure audit."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_project_audit


class ProjectAuditTests(unittest.TestCase):
    def test_reports_structural_signals_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hello')", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            before = sorted(str(p.relative_to(root)) for p in root.rglob("*"))
            result = orbit_project_audit.scan_project(root)
            after = sorted(str(p.relative_to(root)) for p in root.rglob("*"))

            self.assertEqual(result["status"], "SCANNED")
            self.assertEqual(result["summary"]["source_files"], 1)
            self.assertEqual(result["summary"]["test_files"], 0)
            self.assertTrue(any(x["id"] == "TEST_STRUCTURE_NOT_DISCOVERED" for x in result["findings"]))
            self.assertTrue(any(x["id"] == "DOCS_README_NOT_FOUND" for x in result["findings"]))
            self.assertEqual(before, after)
            self.assertFalse(result["data_written"])
            self.assertFalse(result["project_scripts_executed"])
            self.assertFalse(result["source_contents_read"])

    def test_recognizes_test_directory_and_ci_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "src" / "main.ts").write_text("export const x = 1;", encoding="utf-8")
            (root / "tests" / "main.test.ts").write_text("test('x', () => {});", encoding="utf-8")
            result = orbit_project_audit.scan_project(root)
            self.assertEqual(result["summary"]["test_directories"], 1)
            self.assertEqual(result["summary"]["test_files"], 1)
            self.assertIn(".github/workflows", result["discovered"]["ci_markers"])
            self.assertFalse(any(x["id"] == "TEST_STRUCTURE_NOT_DISCOVERED" for x in result["findings"]))

    def test_high_assurance_profile_adds_security_documentation_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("pass", encoding="utf-8")
            result = orbit_project_audit.scan_project(root, {"complexity": "high-assurance"})
            self.assertTrue(any(x["id"] == "SECURITY_DOCUMENTATION_NOT_FOUND" for x in result["findings"]))

    def test_rejects_symlink_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation unavailable")
            with self.assertRaises(ValueError):
                orbit_project_audit.scan_project(link)


if __name__ == "__main__":
    unittest.main()
