"""Published-release update notices are read-only and the installer stays opt-in."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "source/runtime"))
import orbit_updates
import orbit_cli
import orbit_mcp
import installer


def release(version, prerelease=True, complete=True, draft=False):
    name = "ORBIT-Universal-Setup-v" + version + ".zip"
    assets = [{"name": name}, {"name": name + ".sha256"}] if complete else [{"name": name}]
    return {"tag_name": "v" + version, "prerelease": prerelease, "draft": draft, "assets": assets}


class UpdateNotificationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name) / "update.json"
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "1", "ORBIT_UPDATE_CHANNEL": "candidate"}):
            pass

    def test_only_published_complete_release_is_offered(self):
        options = [release("0.25.1"), release("0.25.2", complete=False),
                   release("0.25.3", draft=True), release("0.24.9"),
                   release("1.0.0", prerelease=False)]
        found = orbit_updates._newest(options, "candidate")
        self.assertEqual(found["version"], "0.25.1")
        self.assertEqual(orbit_updates._newest(options, "stable")["version"], "1.0.0")

    def test_read_only_notice_from_cache_and_new_version(self):
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "1",
                                     "ORBIT_UPDATE_CHANNEL": "candidate"}):
            result = orbit_updates.check_now(self.cache, fetch=lambda: [release("0.25.1")], now=100)
            self.assertEqual(result["status"], "OK")
            notification = orbit_updates.notice("0.25.1", self.cache, now=120)
            self.assertEqual(notification["status"], "UPDATE_AVAILABLE")
            self.assertIn("orbit manager", notification["action"].replace("update --gui", "manager"))
            self.assertTrue(notification["install_requires_explicit_user_action"])
            self.assertFalse(notification["cache_stale"])
            self.assertEqual(orbit_updates.notice("0.25.2", self.cache, now=120)["status"], "UP_TO_DATE")
            self.assertTrue(orbit_updates.notice("0.25.1", self.cache, now=100000)["cache_stale"])

    def test_no_auto_install_or_code_download(self):
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "1",
                                     "ORBIT_UPDATE_CHANNEL": "candidate"}):
            with patch("orbit_updates.urllib.request.urlopen", side_effect=AssertionError("should not fetch")):
                self.assertEqual(orbit_updates.notice("0.25.1", self.cache)["status"], "NOT_CHECKED")
            with patch("orbit_updates._fetch", return_value=[release("0.25.2")]):
                result = orbit_updates.check_now(self.cache, now=10)
            self.assertEqual(result["status"], "OK")
            self.assertEqual(orbit_updates._read(self.cache)["latest"]["version"], "0.25.2")

    def test_opt_out_disables_automatic_checks(self):
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "0"}):
            self.assertEqual(orbit_updates.notice("0.25.1", self.cache)["status"], "DISABLED")
            self.assertFalse(orbit_updates.start_background_check())
            self.assertFalse(self.cache.exists())

    def test_cache_missing_invalid_symlink_is_not_trusted(self):
        self.cache.write_text("{invalid")
        self.assertEqual(orbit_updates._read(self.cache), {})
        self.cache.unlink()
        old = Path(self.temp.name) / "target.json"
        old.write_text("{}")
        try:
            self.cache.symlink_to(old)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks require elevated privileges on this system")
        self.assertEqual(orbit_updates._read(self.cache), {})
        self.assertEqual(old.read_text(), "{}")
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "1", "ORBIT_UPDATE_CHANNEL": "candidate"}):
            orbit_updates.check_now(self.cache, fetch=lambda: [release("0.25.1")])
        self.assertEqual(old.read_text(), "{}")

    def test_failed_network_check_is_bounded_to_cache_and_never_installs(self):
        with patch.dict(os.environ, {"ORBIT_UPDATE_CHECK": "1", "ORBIT_UPDATE_CHANNEL": "candidate"}):
            state = orbit_updates.check_now(self.cache,
                fetch=lambda: (_ for _ in ()).throw(OSError("offline")), now=100)
            self.assertEqual(state["status"], "CHECK_FAILED")
            self.assertEqual(orbit_updates.notice("0.25.1", self.cache, now=100)["status"],
                             "CHECK_FAILED")

    def test_mcp_tool_is_read_only_status_and_no_workspace_argument(self):
        entry = next(x for x in orbit_mcp.TOOLS if x["name"] == "orbit_update_status")
        self.assertTrue(entry["annotations"]["readOnlyHint"])
        with patch.object(orbit_mcp.orbit_updates, "notice",
                          return_value={"status": "UP_TO_DATE"}) as notice:
            self.assertEqual(orbit_mcp.execute(None, "orbit_update_status", {}),
                             {"status": "UP_TO_DATE"})
            notice.assert_called_once_with("0.25.1")
        with self.assertRaises(ValueError):
            orbit_mcp.validate("orbit_update_status", {"confirm_write": True})

    def test_cli_version_pin_rejects_changed_release_before_download(self):
        with patch.object(orbit_cli, "latest", return_value={
             "version": "0.25.2", "url": "https://github.com/x",
             "sha": "https://github.com/y", "zip": "https://github.com/z"}):
            with patch.object(orbit_cli, "download", side_effect=AssertionError("not called")):
                self.assertEqual(orbit_cli.main(["update", "--apply",
                    "--expect-version", "0.25.1", "--hosts", "codex"]), 1)

    def test_manager_command_launches_local_ui_without_auto_apply(self):
        with patch("orbit_update_gui.launch") as launch:
            self.assertEqual(orbit_cli.main(["manager"]), 0)
            launch.assert_called_once_with()

    def test_cached_daily_check_does_not_spawn_background_network_worker(self):
        target_home = Path(self.temp.name) / "user"
        cached = target_home / ".orbit-universal/update-status.json"
        cached.parent.mkdir(parents=True)
        cached.write_text(json.dumps({
            "checked_at": 1000, "channel": "candidate",
            "latest": {"version": "0.25.1"},
            "status": "OK"}), encoding="utf-8")
        with patch.dict(os.environ, {"ORBIT_UPDATE_HOME": str(target_home),
                                     "ORBIT_UPDATE_CHECK": "1",
                                     "ORBIT_UPDATE_CHANNEL": "candidate"}):
            with patch("orbit_updates.time.time", return_value=1001):
                with patch("orbit_updates.threading.Thread") as thread:
                    self.assertFalse(orbit_updates.start_background_check())
                    thread.assert_not_called()

    def test_installer_packages_stable_manager_and_notification_module(self):
        with patch.dict(os.environ, {"ORBIT_SETUP_HOME": self.temp.name}):
            project = Path(self.temp.name) / "project"
            project.mkdir()
            actions = installer.plan(project, ["codex"], scope="project")
            self.assertTrue(any(x.target.name == "orbit_update_gui.py" for x in actions))
            installer.install(actions)
            self.assertTrue((Path(self.temp.name) / ".orbit-universal/orbit_update_gui.py").is_file())
            binary = "Orbit Update Manager.cmd" if os.name == "nt" else "orbit-manager"
            self.assertTrue((Path(self.temp.name) / ".orbit-universal/bin" / binary).is_file())
            self.assertTrue((Path(self.temp.name) / ".orbit-universal" / installer.VERSION / "orbit_updates.py").is_file())


if __name__ == "__main__":
    unittest.main()
