import importlib.util
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "source" / "runtime" / "orbit_remote_fallback.py"
spec = importlib.util.spec_from_file_location("orbit_remote_fallback", SOURCE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class RouterTests(unittest.TestCase):
    def ready(self, **kwargs):
        return m.Provider(available=True, online=True, independently_authorized=True,
                          project_scope_verified=True, **kwargs)

    def test_uses_connected_primary(self):
        self.assertEqual(m.select_provider(self.ready(), self.ready(), 'read').route, 'primary')

    def test_fallback_when_absent(self):
        self.assertEqual(m.select_provider(m.Provider(), self.ready(), 'read').route, 'fallback')

    def test_fallback_after_offline_outcome(self):
        self.assertEqual(m.select_provider(self.ready(), self.ready(), 'read', 'offline').route, 'fallback')

    def test_fallback_after_quota_outcome(self):
        self.assertEqual(m.select_provider(self.ready(), self.ready(), 'read', 'quota_exhausted').route, 'fallback')

    def test_fallback_after_explicit_auth_failure_only_if_independently_authorized(self):
        self.assertEqual(m.select_provider(self.ready(), m.Provider(available=True, online=True), 'read', 'auth_failed').route, 'none')

    def test_denial_never_triggers_bypass(self):
        for reason in ('permission_denied', 'policy_denied'):
            self.assertEqual(m.select_provider(self.ready(), self.ready(), 'read', reason).status, 'BLOCKED')

    def test_ambiguous_result_cannot_be_replayed(self):
        for reason in ('ambiguous_timeout', 'failed_after_side_effect'):
            self.assertEqual(m.select_provider(self.ready(write=True), self.ready(write=True), 'write', reason, write_approved_by_host=True).route, 'none')

    def test_write_requires_real_separate_approval(self):
        self.assertEqual(m.select_provider(self.ready(write=True), self.ready(write=True), 'write').route, 'none')
        self.assertEqual(m.select_provider(self.ready(write=True), self.ready(write=True), 'write', write_approved_by_host=True).route, 'primary')

    def test_write_capability_cannot_be_inferred(self):
        self.assertEqual(m.select_provider(m.Provider(), self.ready(), 'write', write_approved_by_host=True).route, 'none')

    def test_unpaired_or_wrong_project_never_ready(self):
        self.assertEqual(m.select_provider(m.Provider(), m.Provider(available=True, online=True, independently_authorized=True), 'read').route, 'none')
        self.assertEqual(m.select_provider(m.Provider(), m.Provider(available=True, online=True, project_scope_verified=True), 'read').route, 'none')

    def test_connected_but_unauthorized_primary_is_not_outage(self):
        primary = m.Provider(available=True, online=True)
        self.assertEqual(m.select_provider(primary, self.ready(), 'read').route, 'none')

    def test_succeeded_must_not_double_execute(self):
        result = m.select_provider(self.ready(), self.ready(), 'read', 'succeeded')
        self.assertEqual(result.status, 'ALREADY_DONE')

    def test_no_fallback_when_offline(self):
        self.assertEqual(m.select_provider(m.Provider(), m.Provider(), 'read').status, 'BLOCKED')

    def test_unknown_operation_fails(self):
        with self.assertRaises(ValueError): m.select_provider(self.ready(), self.ready(), 'delete')
        with self.assertRaises(ValueError): m.select_provider(self.ready(), self.ready(), 'read', 'unknown')


if __name__ == '__main__':
    unittest.main()
