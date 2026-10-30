"""Compact Orbit Core setup model regression checks."""
import unittest
import orbit_setup_ui_model as ui
import orbit_compact_gui as compact_gui

class ModelTests(unittest.TestCase):
    def test_import_has_no_gui_side_effect(self):
        self.assertTrue(callable(compact_gui.launch))

    def test_supported_host_labels(self):
        self.assertIn('antigravity', ui.DISPLAY_NAMES)
        self.assertIn('codex', ui.DISPLAY_NAMES)
        self.assertIn('claude-code', ui.DISPLAY_NAMES)
        self.assertNotIn('deepseek-harness', ui.DISPLAY_NAMES)

    def test_action_must_be_known(self):
        with self.assertRaises(Exception):
            ui.preview('random-operation', ['codex'])

    def test_single_primary_action_follows_real_local_state(self):
        self.assertEqual(ui.presentation("install"), ("Install Orbit", "Ready to install", True))
        self.assertEqual(ui.presentation("update")[0], "Update Orbit")
        self.assertEqual(ui.presentation("current")[2], False)
        self.assertEqual(ui.presentation("review")[0], "Review setup")
        with self.assertRaises(ValueError):
            ui.presentation("latest-on-internet")

    def test_preserved_custom_files_never_look_up_to_date(self):
        from types import SimpleNamespace
        from pathlib import Path
        change = SimpleNamespace(action="PRESERVE", target=Path("user-owned"))
        plan = ui.SetupPreview("install", (change,), (), ("codex",), "machine", None)
        self.assertEqual(ui.local_state(plan), "review")

    def test_uninstall_never_erases_memory_implicitly(self):
        with self.assertRaises(Exception):
            ui.preview('uninstall', ['codex'], delete_memory=True)

if __name__ == '__main__':
    unittest.main()
