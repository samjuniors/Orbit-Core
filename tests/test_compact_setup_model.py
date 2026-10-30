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

    def test_uninstall_never_erases_memory_implicitly(self):
        with self.assertRaises(Exception):
            ui.preview('uninstall', ['codex'], delete_memory=True)

if __name__ == '__main__':
    unittest.main()
