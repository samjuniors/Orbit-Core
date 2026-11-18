"""Orbit RAD P0: host-configured MCP policy gate; no autonomous security agent.

Defense mode is captured from the MCP host process environment at startup,
NOT taken from model arguments, SQLite approvals, repository text or tool output.

This gate limits what Orbit's own dispatcher will do. It is NOT an OS sandbox,
host identity/authentication, cryptographic attestation, or a defense against
arbitrary Python execution in the same process. Those boundaries belong to the
connected host and operating system.
"""
from __future__ import annotations

import os
import threading

EXECUTES_PROJECT_CODE = frozenset({"orbit_preview_start", "orbit_browser_qa"})
# Individually reviewed safe recovery operations. Do not use the MCP tool
# annotation readOnlyHint as an authorization mechanism.
# Never expose project notes, tasks, memory, research pointers or trace
# payloads after containment: "read-only" does not mean non-exfiltrating.
RECOVERY_READS = frozenset({"orbit_gate_evaluate"})
VALID_MODES = frozenset({"NORMAL", "GUARDED", "CONTAINED"})


class Defense:
    """Process-local, scope-limited escalation after confirmed policy denials.

    Repeated project-code execution requests in GUARDED state are observable
    violations of *this* policy, not proof of hostile intent or host compromise.
    A threshold moves only that same canonical project root to CONTAINED.
    Recovery requires a trusted host restart with a reviewed policy setting.
    """

    def __init__(self, mode=None, *, threshold=3, max_scopes=64):
        raw = os.environ.get("ORBIT_DEFENSE_MODE", "NORMAL") if mode is None else mode
        proposed = raw.strip().upper() if isinstance(raw, str) else ""
        # Misconfigured host policy fails closed rather than defaulting to normal.
        self.host_mode = proposed if proposed in VALID_MODES else "CONTAINED"
        if type(threshold) is not int or not 2 <= threshold <= 10:
            raise ValueError("threshold must be an integer between 2 and 10")
        if type(max_scopes) is not int or not 1 <= max_scopes <= 1024:
            raise ValueError("max_scopes must be between 1 and 1024")
        self._threshold = threshold
        self._max_scopes = max_scopes
        self._denied_exec = {}
        self._contained = set()
        self._lock = threading.Lock()

    def mode_for(self, root=None):
        scope = str(root) if root is not None else None
        with self._lock:
            return ("CONTAINED" if self.host_mode == "CONTAINED" or
                    (scope is not None and scope in self._contained)
                    else self.host_mode)

    @staticmethod
    def _safe_recovery(name, args):
        if name in RECOVERY_READS:
            return True
        if name == "orbit_update_status":
            return args.get("refresh") is not True
        if name == "orbit_preview_stop":
            # Allow the user to terminate an existing MCP-owned preview.
            return args.get("confirm_stop") is True
        return False

    @staticmethod
    def _hold(status, mode):
        return {
            "status": status,
            "defense_mode": mode,
            "state_written": False,
            "execution_started": False,
            "host_permission_verified": False,
            "owner_authenticated": False,
            "recovery": "Review the policy event and restart this MCP from a trusted host configuration; MCP calls cannot reset the defense.",
        }

    def check(self, name, args, *, root=None):
        """Enforce before invoking any tool handler; returns a HOLD or None."""
        scope = str(root) if root is not None else None
        with self._lock:
            mode = ("CONTAINED" if self.host_mode == "CONTAINED" or
                    (scope is not None and scope in self._contained)
                    else self.host_mode)
            if mode == "NORMAL":
                return None
            if mode == "CONTAINED":
                if self._safe_recovery(name, args):
                    return None
                return self._hold("HOLD_DEFENSE_CONTAINED", mode)
            if name not in EXECUTES_PROJECT_CODE:
                return None

            # A hostile caller cannot place another workspace into containment
            # via an unvalidated or missing root; no global lockout is possible.
            if scope is None:
                return self._hold("HOLD_DEFENSE_GUARDED", mode)
            count = self._denied_exec.get(scope, 0)
            if count == 0 and len(self._denied_exec) >= self._max_scopes:
                return self._hold("HOLD_DEFENSE_GUARDED", mode)
            count = min(self._threshold, count + 1)
            self._denied_exec[scope] = count
            if count >= self._threshold:
                self._contained.add(scope)
                return self._hold("HOLD_DEFENSE_CONTAINED", "CONTAINED")
            return self._hold("HOLD_DEFENSE_GUARDED", mode)
