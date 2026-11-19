"""Read-only adaptive model routing pilot regression suite.

No host agent or provider calls; simulated evidence is caller-reported only.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source' / 'runtime'))
import orbit_build
import orbit_decisions
import orbit_intake
import orbit_mcp


class AdaptiveExecutionPreviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name, 'project')
        self.root.mkdir()
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_build.setup(self.conn)
        orbit_intake.setup(self.conn)
        self.conn.execute("CREATE TABLE memories (project TEXT, status TEXT, updated_at TEXT)")
        self.base = {
            'project_root': str(self.root.resolve(strict=True)),
            'project': 'synthetic',
            'role': 'orbit-software-engineer',
            'task': 'implementation',
            'host': 'codex',
            'complexity': 'moderate',
            'budget': 'economy',
            'available_models': ['example-mini', 'example-codex'],
        }

    def route(self, **updates):
        return orbit_mcp.execute(self.conn, 'orbit_model_route',
                                 {**self.base, **updates})

    def test_no_opt_in_preserves_prior_output_contract(self):
        result = self.route()
        self.assertNotIn('adaptive_execution', result)
        self.assertTrue(result['no_switch_executed'])
        expected = orbit_decisions.model_route(
            self.base['role'], self.base['task'], self.base['complexity'],
            self.base['available_models'], self.base['host'], self.base['budget'])
        self.assertEqual(result, expected)

    def test_simple_readonly_single_baseline(self):
        result = self.route(
            task='read', complexity='simple',
            execution_review={'validation': 'PASS'})
        preview = result['adaptive_execution']
        self.assertEqual(preview['status'], 'SINGLE_BASELINE_CANDIDATE')
        self.assertEqual(preview['suggested_pattern'], 'single')
        self.assertFalse(preview['test_evidence_verified'])
        self.assertEqual(preview['additional_model_calls_made'], 0)

    def test_code_changes_require_real_tests(self):
        status = self.route(execution_review={})['adaptive_execution']['status']
        self.assertEqual(status, 'HOLD_VALIDATION_REQUIRED')

    def test_failed_validation_requires_rework_even_with_reviewer(self):
        preview = self.route(execution_review={
            'validation': 'FAIL', 'reviewer_available': True})['adaptive_execution']
        self.assertEqual(preview['status'], 'CASCADE_REWORK_CANDIDATE')
        self.assertEqual(preview['suggested_pattern'], 'cascade')
        self.assertFalse(preview['agent_spawned'])
        self.assertFalse(preview['host_approval_verified'])
        self.assertFalse(preview['workspace_edits_reverted'])

    def test_host_denial_takes_precedence_over_reviewer(self):
        preview = self.route(execution_review={
            'host_permission_denied': True, 'validation': 'PASS',
            'reviewer_available': True})['adaptive_execution']
        self.assertEqual(preview['status'], 'HOLD_HOST_PERMISSION_DENIED')
        self.assertEqual(preview['suggested_pattern'], 'none')
        self.assertFalse(preview['provider_fallback_attempted'])

    def test_pending_side_effects_are_not_rolled_back(self):
        preview = self.route(execution_review={
            'validation': 'PASS', 'side_effects_pending': True
        })['adaptive_execution']
        self.assertEqual(preview['status'], 'HOLD_UNRECONCILED_WORKSPACE_EDITS')
        self.assertFalse(preview['workspace_edits_reverted'])

    def test_blocked_evidence_cannot_be_bypassed(self):
        preview = self.route(execution_review={
            'validation': 'BLOCKED', 'reviewer_available': True
        })['adaptive_execution']
        self.assertEqual(preview['status'], 'HOLD_VALIDATION_BLOCKED')
        self.assertEqual(preview['suggested_pattern'], 'none')

    def test_security_requires_independent_review(self):
        result = self.route(
            role='orbit-security', task='security', complexity='high-assurance',
            available_models=['example-opus'], budget='quality',
            execution_review={'validation': 'PASS', 'reviewer_available': True})
        preview = result['adaptive_execution']
        self.assertEqual(preview['status'], 'CRITIQUE_REVIEW_CANDIDATE')
        self.assertEqual(preview['suggested_pattern'], 'critique')
        self.assertFalse(preview['reviewer_independence_verified'])

    def test_security_without_reviewer_holds(self):
        result = self.route(
            role='orbit-security', task='security', complexity='high-assurance',
            available_models=['example-opus'], budget='quality',
            execution_review={'validation': 'PASS'})
        self.assertEqual(result['adaptive_execution']['status'],
                         'HOLD_INDEPENDENT_REVIEW_REQUIRED')

    def test_high_assurance_insufficient_model_holds(self):
        result = self.route(
            role='orbit-security', task='security', complexity='high-assurance',
            available_models=['example-mini'], budget='quality',
            execution_review={'validation': 'PASS', 'reviewer_available': True})
        self.assertEqual(result['adaptive_execution']['status'],
                         'HOLD_MODEL_QUALITY_REVIEW')

    def test_no_host_models_does_not_invent_availability(self):
        result = self.route(task='read', complexity='simple',
                            available_models=[],
                            execution_review={'validation': 'PASS'})
        self.assertIsNone(result['adaptive_execution']['model_suggestion'])
        self.assertEqual(result['selection_status'], 'INHERIT_HOST_MODEL')
        self.assertFalse(result['adaptive_execution']['model_switched'])

    def test_invalid_untrusted_evidence_rejected(self):
        for invalid in (
            None, [], 'PASS', {'validation': 'PWNED'},
            {'side_effects_pending': 1}, {'reviewer_available': 'true'},
            {'host_permission_denied': 0}, {'unexpected': 'injection'},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.route(execution_review=invalid)

    def test_schema_exposes_only_opt_in_and_no_extra_tool(self):
        tool = next(x for x in orbit_mcp.TOOLS if x['name'] == 'orbit_model_route')
        spec = tool['inputSchema']['properties']['execution_review']
        self.assertEqual(spec['type'], 'object')
        self.assertIs(spec['additionalProperties'], False)
        self.assertNotIn('execution_review', tool['inputSchema']['required'])
        self.assertEqual(sum(x['name'] == 'orbit_model_route'
                             for x in orbit_mcp.TOOLS), 1)


if __name__ == '__main__':
    unittest.main()
