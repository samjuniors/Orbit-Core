"""Transactional clean-reset regression tests in isolated temporary homes only."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import installer
import orbit_setup


class UninstallRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.project = self.base / "project"
        self.project.mkdir()
        env = patch.dict(os.environ, {
            "ORBIT_SETUP_HOME": str(self.home),
            "ORBIT_UNIVERSAL_HOME": str(self.home / ".orbit-universal"),
        })
        env.start()
        self.addCleanup(env.stop)
        installer.install(installer.plan(None, installer.HOSTS, "machine"))
        installer.install(installer.plan(self.project, installer.HOSTS, "project"))
        self.memory = self.home / "AppData/Local/OrbitCore/memory.sqlite3"
        self.memory.parent.mkdir(parents=True, exist_ok=True)
        self.memory.write_bytes(b"remembered tasks")
        self.wal = Path(str(self.memory) + "-wal")
        self.wal.write_bytes(b"wal content")
        self.shm = Path(str(self.memory) + "-shm")
        self.shm.write_bytes(b"shm content")
        self.agent = self.home / ".gemini/config/agents/orbit-architect.md"

    def plan(self):
        changes, _ = orbit_setup.plan_clean_reset(self.project, erase_memory=True)
        self.assertTrue(any(c.path == self.memory for c in changes))
        self.assertTrue(any(c.path == self.agent for c in changes))
        return changes

    def assert_restored(self, changes):
        for c in changes:
            with self.subTest(path=str(c.path)):
                self.assertEqual(orbit_setup._read_file(c.path), c.original)

    def single_backup(self):
        backups = sorted((self.home / ".orbit-uninstall-backups").glob("*/manifest.json"))
        self.assertEqual(len(backups), 1)
        return backups[0].parent

    def test_locked_database_rolls_back_runtime_registrations_and_all_memory_bytes(self):
        changes = self.plan()
        unlink = Path.unlink

        def locked_database(path, *args, **kwargs):
            if path == self.memory:
                raise PermissionError("simulated Windows SQLite lock")
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", locked_database):
            with self.assertRaisesRegex(installer.SetupError, "All original targets restored"):
                orbit_setup.apply_clean_reset(
                    changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
                )
        self.assert_restored(changes)
        backup = self.single_backup()
        record = json.loads((backup / "manifest.json").read_text())
        self.assertEqual(record["status"], "ROLLED_BACK")
        self.assertEqual(record["schema"], "orbit-uninstall-v2")
        self.assertEqual(record["operation"], "clean")
        self.assertTrue(record["erase_memory"])
        self.assertEqual(len(record["entries"]), len(changes))
        self.assertEqual(self.memory.read_bytes(), b"remembered tasks")
        self.assertEqual(self.wal.read_bytes(), b"wal content")
        self.assertEqual(self.shm.read_bytes(), b"shm content")

    def test_actual_live_sqlite_transaction_blocks_before_any_host_change(self):
        self.memory.unlink()
        self.wal.unlink()
        self.shm.unlink()
        db = sqlite3.connect(self.memory)
        try:
            db.execute("CREATE TABLE state (name TEXT)")
            db.execute("INSERT INTO state VALUES ('keep')")
            db.commit()
        finally:
            db.close()
        changes = self.plan()
        active = sqlite3.connect(self.memory)
        try:
            active.execute("BEGIN EXCLUSIVE")
            with self.assertRaisesRegex(installer.SetupError, "Close Orbit/SQLite"):
                orbit_setup.apply_clean_reset(
                    changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
                )
        finally:
            active.rollback()
            active.close()
        self.assert_restored(changes)
        self.assertFalse((self.home / ".orbit-uninstall-backups").exists())

    def test_simulated_crash_between_actions_supports_explicit_idempotent_recovery(self):
        changes = self.plan()
        unlink = Path.unlink
        count = 0

        def crash_after_removals(path, *args, **kwargs):
            nonlocal count
            if count == 4:
                raise KeyboardInterrupt("simulated abrupt process termination")
            count += 1
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", crash_after_removals):
            with self.assertRaises(KeyboardInterrupt):
                orbit_setup.apply_clean_reset(
                    changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
                )
        backup = self.single_backup()
        record, entries = orbit_setup.inspect_uninstall_backup(backup)
        self.assertEqual(record["status"], "APPLYING")
        self.assertEqual(len(entries), len(changes))
        self.assertGreater(sum(not c.path.exists() for c in changes), 0)
        with self.assertRaisesRegex(installer.SetupError, "RESTORE ORBIT"):
            orbit_setup.recover_uninstall(backup)
        restored = orbit_setup.recover_uninstall(backup, confirmation="RESTORE ORBIT")
        self.assertGreater(restored, 0)
        self.assertEqual(orbit_setup.recover_uninstall(
            backup, confirmation="RESTORE ORBIT"), 0)
        self.assert_restored(changes)
        self.assertEqual(
            json.loads((backup / "manifest.json").read_text())["status"], "ROLLED_BACK"
        )

    def test_owner_modified_target_causes_fail_closed_recovery(self):
        changes = self.plan()
        unlink = Path.unlink
        count = 0

        def crash(path, *args, **kwargs):
            nonlocal count
            if count == 2:
                raise KeyboardInterrupt("crash")
            count += 1
            return unlink(path, *args, **kwargs)

        with patch.object(Path, "unlink", crash):
            with self.assertRaises(KeyboardInterrupt):
                orbit_setup.apply_clean_reset(
                    changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
                )
        backup = self.single_backup()
        missing = next(c.path for c in changes if not c.path.exists())
        missing.write_bytes(b"new owner content")
        with self.assertRaisesRegex(installer.SetupError, "Recovery conflict"):
            orbit_setup.recover_uninstall(backup, confirmation="RESTORE ORBIT")
        self.assertEqual(missing.read_bytes(), b"new owner content")
        missing.unlink()
        orbit_setup.recover_uninstall(backup, confirmation="RESTORE ORBIT")
        self.assert_restored(changes)

    def test_config_replace_failure_undoes_prior_changes_and_staged_temp(self):
        changes = self.plan()
        original_replace = Path.replace

        def fail_config_replace(path, target):
            if path.name.endswith(".orbit-uninstall-tmp"):
                raise PermissionError("simulated locked host config")
            return original_replace(path, target)

        with patch.object(Path, "replace", fail_config_replace):
            with self.assertRaisesRegex(installer.SetupError, "All original targets restored"):
                orbit_setup.apply_clean_reset(
                    changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
                )
        self.assert_restored(changes)
        for c in changes:
            if c.replacement is not None:
                self.assertFalse(c.path.with_name(c.path.name + ".orbit-uninstall-tmp").exists())
        self.assertEqual(json.loads((self.single_backup() / "manifest.json").read_text())["status"],
                         "ROLLED_BACK")

    def test_legacy_backup_is_not_mutated_or_restored_automatically(self):
        backup = self.home / ".orbit-uninstall-backups/legacy"
        backup.mkdir(parents=True)
        old = '[{"original_path":"C:/historical","backup_name":"000.bak","action":"REMOVE"}]'
        (backup / "manifest.json").write_text(old)
        with self.assertRaisesRegex(installer.SetupError, "Legacy v1"):
            orbit_setup.inspect_uninstall_backup(backup)
        self.assertEqual((backup / "manifest.json").read_text(), old)

    def test_recovery_rejects_tampered_backup_and_outside_scope(self):
        changes = self.plan()
        backup = orbit_setup.apply_clean_reset(
            changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
        )
        record = json.loads((backup / "manifest.json").read_text())
        record["entries"][0]["original_path"] = str(self.base / "outsider.txt")
        (backup / "manifest.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(installer.SetupError, "outside recorded scope"):
            orbit_setup.recover_uninstall(backup, confirmation="RESTORE ORBIT")
        self.assertFalse((self.base / "outsider.txt").exists())

    def test_recover_cli_preview_requires_explicit_confirmation(self):
        changes = self.plan()
        backup = orbit_setup.apply_clean_reset(
            changes, self.project, erase_memory=True, confirmation="REMOVE ORBIT"
        )
        args = ["recover", "--backup", str(backup)]
        self.assertEqual(orbit_setup.main(args), 0)
        self.assertEqual(orbit_setup.main(args + ["--apply"]), 1)
        self.assertFalse(self.agent.exists())
        self.assertEqual(orbit_setup.main(args + [
            "--apply", "--confirm-recover", "RESTORE ORBIT"
        ]), 0)
        self.assert_restored(changes)


if __name__ == "__main__":
    unittest.main()
