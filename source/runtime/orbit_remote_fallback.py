"""Pure, fail-closed provider routing for Orbit PC access.

No transport is created. The host must independently verify online state,
device pairing, root permissions, and genuine user approval for each action.
"""
from dataclasses import dataclass
from typing import Literal

Operation = Literal["read", "write", "check"]
PrimaryOutcome = Literal[
    "not_attempted", "succeeded", "unavailable", "offline", "quota_exhausted",
    "auth_failed", "permission_denied", "policy_denied", "ambiguous_timeout",
    "failed_after_side_effect",
]


@dataclass(frozen=True)
class Provider:
    available: bool = False
    online: bool = False
    independently_authorized: bool = False
    project_scope_verified: bool = False
    read: bool = True
    write: bool = False
    check: bool = False

    def permits(self, operation: Operation) -> bool:
        return {"read": self.read, "write": self.write, "check": self.check}[operation]

    def ready(self, operation: Operation) -> bool:
        return (self.available and self.online and self.independently_authorized
                and self.project_scope_verified and self.permits(operation))


@dataclass(frozen=True)
class Decision:
    route: Literal["primary", "fallback", "none"]
    status: Literal["READY", "ALREADY_DONE", "BLOCKED"]
    reason: str


def select_provider(
    primary: Provider,
    fallback: Provider,
    operation: Operation,
    primary_outcome: PrimaryOutcome = "not_attempted",
    *,
    write_approved_by_host: bool = False,
) -> Decision:
    """Choose an existing authorized connection; never install or bypass permissions.

    The local host must separately authorize writes and enforce project scoping
    on the actual Windows device. No automatic replay after uncertain effects.
    """
    if operation not in {"read", "write", "check"}:
        raise ValueError("Unknown operation")
    valid_outcomes = {
        "not_attempted", "succeeded", "unavailable", "offline", "quota_exhausted",
        "auth_failed", "permission_denied", "policy_denied", "ambiguous_timeout",
        "failed_after_side_effect",
    }
    if primary_outcome not in valid_outcomes:
        raise ValueError("Unknown primary outcome")
    if primary_outcome == "succeeded":
        return Decision("none", "ALREADY_DONE", "Primary already completed; do not duplicate")
    if primary_outcome in {"permission_denied", "policy_denied"}:
        return Decision("none", "BLOCKED", "Do not route around an explicit denial")
    if primary_outcome in {"ambiguous_timeout", "failed_after_side_effect"}:
        return Decision("none", "BLOCKED", "Effect unknown; inspect state before any retry")
    if operation == "write" and not write_approved_by_host:
        return Decision("none", "BLOCKED", "Separate genuine host write authorization required")
    if primary_outcome == "not_attempted" and primary.ready(operation):
        return Decision("primary", "READY", "Primary connected and authorized")
    if primary_outcome == "not_attempted" and primary.available and primary.online:
        return Decision("none", "BLOCKED", "Primary scope or permission not verified")
    if fallback.ready(operation):
        return Decision("fallback", "READY", "Independently connected and authorized fallback")
    return Decision("none", "BLOCKED", "No independently connected, correctly scoped provider")
