"""Branch housekeeping never deletes unmerged/modified/protected work."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prune_merged_branches import candidates, audit_and_prune


class BranchPruneTests(unittest.TestCase):
    def entry(self, name="feature/merged", sha="a" * 40, pr=8):
        return {"name": name, "head_sha": sha, "pr": pr}

    def manifest(self, rows):
        return {"repository": "samjuniors/Orbit-Core", "branches": rows}

    def test_rejects_unsafe_branch_patterns_and_other_repository(self):
        for name in ("main", "refs/heads/x", "feature/../../main", "tags/v1",
                     "feature//x", "feature/../main", "feature/.lock"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                candidates(self.manifest([self.entry(name=name)]))
        with self.assertRaises(ValueError):
            candidates({"repository": "someone-else/other", "branches": []})
        with self.assertRaises(ValueError):
            candidates(self.manifest([self.entry(), self.entry()]))

    def test_preview_does_not_call_delete(self):
        sha = "b" * 40
        paths = []
        def api(method, path):
            paths.append((method, path))
            if path.startswith("pulls/"):
                return {"merged_at": "2026-10-27T00:00:00Z",
                        "head": {"ref": "feature/merged", "sha": sha},
                        "base": {"ref": "main"}}
            return {"object": {"sha": sha}}
        result = audit_and_prune(self.manifest([self.entry(sha=sha)]), api=api)
        self.assertEqual(result[0]["status"], "READY_TO_DELETE")
        self.assertTrue(all(method == "GET" for method, _ in paths))

    def test_unmerged_or_modified_ref_is_preserved(self):
        sha = "c" * 40
        for merged, ref_sha in ((None, sha), ("2026-10-27", "d" * 40)):
            calls = []
            def api(method, path):
                calls.append(method)
                if path.startswith("pulls/"):
                    return {"merged_at": merged,
                            "head": {"ref": "feature/merged", "sha": sha},
                            "base": {"ref": "main"}}
                return {"object": {"sha": ref_sha}}
            result = audit_and_prune(self.manifest([self.entry(sha=sha)]), api=api, apply=True)
            self.assertEqual(result[0]["status"], "PRESERVED_UNVERIFIED_OR_CHANGED")
            self.assertEqual(calls, ["GET", "GET"])

    def test_delete_only_exact_merged_commit(self):
        sha = "e" * 40
        calls = []
        def api(method, path):
            calls.append((method, path))
            if method == "DELETE": return {}
            if path.startswith("pulls/"):
                return {"merged_at": "2026-10-27", "head": {"ref": "feature/merged", "sha": sha},
                        "base": {"ref": "main"}}
            return {"object": {"sha": sha}}
        out = audit_and_prune(self.manifest([self.entry(sha=sha)]), api=api, apply=True)
        self.assertEqual(out[0]["status"], "DELETED")
        self.assertEqual(calls[-1], ("DELETE", "git/refs/heads/feature/merged"))


if __name__ == "__main__":
    unittest.main()
