"""Regression tests for bounded, caller-reported host capacity observations."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_decisions


STAMP = "2026-11-24T12:00:00+00:00"


class CapacityObservationTests(unittest.TestCase):
    def test_missing_signals_remain_unknown(self):
        result = orbit_decisions.capacity_observation({})
        self.assertEqual(result["context_window"]["status"], "UNKNOWN")
        self.assertEqual(result["rate_limit"]["state"], "UNKNOWN")
        self.assertEqual(result["host_availability"]["state"], "UNKNOWN")
        self.assertEqual(result["worker_capacity"]["status"], "UNKNOWN")
        self.assertEqual(result["account_usage"]["status"], "UNKNOWN")
        self.assertFalse(result["telemetry_independently_verified"])
        self.assertFalse(result["actions_executed"])

    def test_context_pressure_is_separate_and_advisory(self):
        result = orbit_decisions.capacity_observation({
            "context_window": {
                "used_tokens": 85000, "total_tokens": 100000,
                "observed_at": STAMP, "source": "claude-code-context-indicator",
            }
        })
        context = result["context_window"]
        self.assertEqual(context["status"], "PRESSURE")
        self.assertEqual(context["remaining_tokens"], 15000)
        self.assertTrue(context["checkpoint_recommended"])
        self.assertFalse(result["actions_executed"])
        self.assertEqual(result["account_usage"]["status"], "UNKNOWN")

    def test_rate_limit_block_does_not_trigger_provider_fallback(self):
        result = orbit_decisions.capacity_observation({
            "rate_limit": {
                "state": "BLOCKED", "observed_at": STAMP, "source": "host-notification"
            }
        })
        self.assertEqual(
            result["rate_limit"]["recommended_action"],
            "HOLD_HOST_WORK_AND_WAIT_FOR_HOST_GUIDANCE")
        self.assertFalse(result["provider_fallback_attempted"])

    def test_host_and_worker_capacity_are_distinct(self):
        result = orbit_decisions.capacity_observation({
            "host_availability": {
                "state": "BUSY", "observed_at": STAMP, "source": "host-status"
            },
            "worker_pool": {
                "active_workers": 2, "worker_limit": 2,
                "observed_at": STAMP, "source": "host-worker-list"
            }
        })
        self.assertEqual(result["host_availability"]["state"], "BUSY")
        self.assertEqual(result["worker_capacity"]["status"], "AT_CAPACITY")
        self.assertEqual(result["worker_capacity"]["recommended_action"],
                         "DEFER_NEW_DELEGATION")

    def test_critical_context_pressure(self):
        result = orbit_decisions.capacity_observation({
            "context_window": {
                "used_tokens": 950, "total_tokens": 1000,
                "observed_at": STAMP, "source": "host-context"
            }
        })
        self.assertEqual(result["context_window"]["status"], "CRITICAL")

    def test_rejects_naive_timestamp_and_unknown_account_claims(self):
        with self.assertRaises(ValueError):
            orbit_decisions.capacity_observation({
                "context_window": {
                    "used_tokens": 10, "total_tokens": 100,
                    "observed_at": "2026-11-24T12:00:00",
                    "source": "host"
                }
            })
        with self.assertRaises(ValueError):
            orbit_decisions.capacity_observation({"account_usage": {"remaining": 80}})

    def test_rejects_inconsistent_or_invalid_capacity(self):
        with self.assertRaises(ValueError):
            orbit_decisions.capacity_observation({
                "context_window": {
                    "used_tokens": 101, "total_tokens": 100,
                    "observed_at": STAMP, "source": "host"
                }
            })
        with self.assertRaises(ValueError):
            orbit_decisions.capacity_observation({
                "worker_pool": {
                    "active_workers": 3, "worker_limit": 2,
                    "observed_at": STAMP, "source": "host"
                }
            })

    def test_model_route_preserves_legacy_shape_without_capacity(self):
        result = orbit_decisions.model_route(
            "orbit-software-engineer", "implementation", "moderate",
            ["example-sonnet"], "claude-code", "balanced")
        self.assertNotIn("capacity", result)
        self.assertTrue(result["no_switch_executed"])

    def test_high_assurance_route_rejects_balanced_model_fallback(self):
        result = orbit_decisions.model_route(
            "orbit-security", "security", "high-assurance",
            ["example-sonnet"], "claude-code", "quality")
        self.assertEqual(result["desired_tier"], "deep")
        self.assertIsNone(result["recommended_model"])
        self.assertEqual(result["selection_status"], "REQUIRES_MODEL_QUALITY_REVIEW")
        self.assertFalse(result["no_switch_executed"])

    def test_model_route_includes_capacity_only_when_supplied(self):
        result = orbit_decisions.model_route(
            "orbit-software-engineer", "implementation", "moderate",
            ["example-sonnet"], "claude-code", "balanced",
            {"rate_limit": {
                "state": "WARNING", "observed_at": STAMP, "source": "host-notification"
            }})
        self.assertEqual(result["capacity"]["rate_limit"]["state"], "WARNING")
        self.assertEqual(result["capacity"]["account_usage"]["status"], "UNKNOWN")
        self.assertTrue(result["no_switch_executed"])


if __name__ == "__main__":
    unittest.main()
