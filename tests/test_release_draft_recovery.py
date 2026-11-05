"""Read-only integrity checks for an explicitly approved release draft retry."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.verify_release_draft_assets import (
    main, required_assets, verify_draft_assets,
)

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.29.0"


class DraftRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = []
        for name, relative in required_assets(VERSION).items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(("test:" + name).encode())
            self.assets.append({
                "name": name,
                "size": target.stat().st_size,
                "digest": "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest(),
            })

    def test_exact_eight_matches_rebuilt_files(self):
        self.assertEqual(verify_draft_assets(VERSION, self.assets, self.root), "COMPLETE")

    def test_empty_only_allowed_before_first_upload(self):
        self.assertEqual(verify_draft_assets(VERSION, [], self.root, allow_empty=True),
                         "EMPTY")
        with self.assertRaisesRegex(ValueError, "partial or unexpected"):
            verify_draft_assets(VERSION, [], self.root)

    def test_partial_duplicate_or_extra_asset_fail_closed(self):
        for values in (
            self.assets[:-1],
            self.assets + [self.assets[0]],
            self.assets + [{"name": "unexpected.txt"}],
        ):
            with self.subTest(size=len(values)):
                with self.assertRaises(ValueError):
                    verify_draft_assets(VERSION, values, self.root, allow_empty=True)

    def test_asset_hash_and_size_mismatch_fail(self):
        mutated = [dict(a) for a in self.assets]
        mutated[0]["digest"] = "sha256:" + ("0" * 64)
        with self.assertRaisesRegex(ValueError, "differs from rebuilt"):
            verify_draft_assets(VERSION, mutated, self.root)
        mutated[0] = dict(self.assets[0])
        mutated[0]["size"] = 0
        with self.assertRaisesRegex(ValueError, "size differs"):
            verify_draft_assets(VERSION, mutated, self.root)
        mutated[0]["digest"] = None
        with self.assertRaisesRegex(ValueError, "Missing/invalid"):
            verify_draft_assets(VERSION, mutated, self.root)

    def test_missing_or_symlinked_local_asset_fails(self):
        asset = self.root / required_assets(VERSION)[self.assets[0]["name"]]
        asset.unlink()
        with self.assertRaises(OSError):
            verify_draft_assets(VERSION, self.assets, self.root)
        outside = self.root.parent / ("release-outside-" + self.root.name)
        outside.write_bytes(b"forbidden")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        try:
            asset.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink unavailable")
        with self.assertRaises(ValueError):
            verify_draft_assets(VERSION, self.assets, self.root)

    def test_invalid_metadata_and_version_fail(self):
        with self.assertRaises(ValueError):
            required_assets("../0.29.0")
        with self.assertRaises(ValueError):
            verify_draft_assets(VERSION, [{}], self.root)
        with self.assertRaises(ValueError):
            verify_draft_assets(VERSION, {"assets": self.assets}, self.root)

    def test_cli_preflight_is_read_only(self):
        file = self.root / "release.json"
        file.write_text(json.dumps({"assets": self.assets}))
        code = main(["--version", VERSION, "--assets-json", str(file),
                     "--root", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(len(list(self.root.rglob("*"))), 10)
        self.assets[0]["size"] += 1
        file.write_text(json.dumps({"assets": self.assets}))
        self.assertEqual(main(["--version", VERSION, "--assets-json", str(file),
                               "--root", str(self.root)]), 1)

    def test_workflow_requires_manual_draft_retry_and_postpublish_verification(self):
        yml = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn('if [[ "$existing_draft" == ' + "'true' ]]; then", yml)
        self.assertIn("Existing draft requires an explicit manual main-branch release", yml)
        self.assertIn('gh release upload "$ORBIT_RELEASE_TAG"', yml)
        self.assertNotIn('gh release upload "$ORBIT_RELEASE_TAG" --clobber', yml)
        self.assertIn("verify_release_draft_assets.py", yml)
        self.assertIn('gh release edit "$ORBIT_RELEASE_TAG"', yml)
        self.assertIn("--draft=false", yml)
        self.assertIn("--prerelease=", yml)
        self.assertIn('if [[ "$verified" != ' + "'COMPLETE' ]]; then", yml)


if __name__ == "__main__":
    unittest.main()
