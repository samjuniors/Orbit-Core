"""Project-specific cybersecurity review planning; no scanner or command execution.

Tool names are caller-reported hints, not proof of installation or permission.
A plan is not a threat-model interview, vulnerability scan, penetration test,
certification, or release security attestation.
"""
from __future__ import annotations

import re

import orbit_skill_plan

BASELINE = (
    ("secrets_and_credentials", "Inspect tracked source/configuration for exposed credentials; redact all values."),
    ("authentication_and_authorization", "Review identity, privilege boundaries, object-level access and deny-by-default behavior where applicable."),
    ("input_and_output_boundaries", "Review validation, injection, deserialization, output encoding and untrusted content handling."),
    ("dependencies_and_supply_chain", "Review dependency provenance, known advisories, lockfiles, build scripts and update integrity."),
    ("transport_and_storage", "Review encryption, certificate validation, local storage and sensitive-data retention where applicable."),
    ("logging_and_privacy", "Review data minimization, secret redaction, telemetry and sensitive data in diagnostics."),
    ("build_and_release_integrity", "Review reproducible builds, signing, artifact provenance, permissions and rollback."),
)

PRODUCT_CONTROLS = {
    "website": (
        ("web_sessions", "Review cookie flags, CSRF, session rotation and authentication flows."),
        ("browser_injection", "Review XSS, CSP, CORS and browser-origin trust boundaries."),
    ),
    "web-app": (
        ("web_sessions", "Review cookie flags, CSRF, session rotation and authentication flows."),
        ("browser_injection", "Review XSS, CSP, CORS and browser-origin trust boundaries."),
        ("api_authorization", "Review tenant isolation, object-level authorization and rate limits."),
    ),
    "api-service": (
        ("api_authorization", "Review tenant isolation, object-level authorization and rate limits."),
        ("service_identity", "Review service-to-service identity, token scope, rotation and trust boundaries."),
    ),
    "mobile-app": (
        ("mobile_storage", "Review keychain/keystore use, backups, local databases and cached sensitive data."),
        ("mobile_platform", "Review app permissions, deep links, exported components and platform update behavior."),
        ("mobile_network", "Review TLS validation, certificate handling and cleartext traffic policy."),
    ),
    "desktop-app": (
        ("desktop_ipc", "Review renderer/main-process boundaries, IPC authorization and untrusted document handling."),
        ("desktop_updates", "Review updater signatures, downgrade protection, installer privileges and rollback."),
        ("desktop_local_data", "Review local credential storage, file permissions and plugin loading."),
    ),
    "plugin-mcp": (
        ("tool_authority", "Review tool schemas, least privilege, confirmation boundaries and confused-deputy paths."),
        ("workspace_isolation", "Review project-root validation, symlinks/reparse points and cross-project access."),
        ("prompt_injection", "Treat repository, skill, tool and search content as untrusted data; prevent instruction escalation."),
        ("protocol_validation", "Review malformed inputs, oversized payloads, error handling and data leakage."),
    ),
    "cli": (
        ("filesystem_authority", "Review path traversal, symlink handling, file permissions and destructive defaults."),
        ("process_execution", "Review shell invocation, argument boundaries, environment inheritance and subprocess authority."),
    ),
    "sdk-library": (
        ("api_misuse", "Review unsafe defaults, caller-visible trust assumptions and secure integration examples."),
        ("serialization", "Review parsing, deserialization, resource limits and cryptographic API use."),
    ),
    "os-platform": (
        ("privilege_boundaries", "Review privilege transitions, service boundaries, device access and update channels."),
        ("kernel_interfaces", "Review native interfaces, unsafe memory operations and driver/service trust."),
    ),
    "game": (
        ("game_client_trust", "Review client-authoritative state, matchmaking, anti-cheat boundaries and asset loading."),
        ("player_data", "Review account/session data, moderation surfaces and platform-specific storage."),
    ),
    "data-automation": (
        ("data_access", "Review data source permissions, tenant separation, retention and export paths."),
        ("pipeline_integrity", "Review job identity, secrets, dependency provenance and replay/idempotency behavior."),
    ),
}

STANDARDS = {
    "website": ["OWASP ASVS 5.0", "NIST SSDF"],
    "web-app": ["OWASP ASVS 5.0", "NIST SSDF"],
    "api-service": ["OWASP ASVS 5.0", "NIST SSDF"],
    "mobile-app": ["OWASP MASVS", "NIST SSDF"],
    "desktop-app": ["NIST SSDF"],
    "plugin-mcp": ["NIST SSDF"],
    "cli": ["NIST SSDF"],
    "sdk-library": ["NIST SSDF"],
    "os-platform": ["NIST SSDF"],
    "game": ["NIST SSDF"],
    "data-automation": ["NIST SSDF"],
}


def _tool_hints(value):
    if value is None:
        return []
    if (not isinstance(value, list) or len(value) > 24 or
            any(not isinstance(x, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", x)
                for x in value) or len(set(value)) != len(value)):
        raise ValueError("available_security_tools must be up to 24 unique tool-name hints")
    return sorted(value)


def plan(project_profile, objective, *, permission_state="UNKNOWN",
         available_security_tools=None):
    """Build a product-appropriate threat/review plan without scanning anything."""
    profile = orbit_skill_plan._profile(project_profile)
    if not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 1200:
        raise ValueError("objective must contain 1..1200 characters")
    if permission_state not in {"UNKNOWN", "APPROVED", "DENIED"}:
        raise ValueError("Unknown permission state")
    hints = _tool_hints(available_security_tools)
    product = profile["product_type"]
    checks = [
        {"control": key, "expectation": text, "status": "REVIEW_REQUIRED",
         "verified": False, "scope": "PROJECT_AND_CHANGED_SLICE"}
        for key, text in BASELINE
    ]
    checks.extend(
        {"control": key, "expectation": text, "status": "REVIEW_REQUIRED",
         "verified": False, "scope": "PROJECT_AND_CHANGED_SLICE"}
        for key, text in PRODUCT_CONTROLS.get(product, ())
    )
    denied = permission_state == "DENIED"
    return {
        "status": "HOLD_PERMISSION_DENIED" if denied else "SECURITY_REVIEW_PLAN_READY",
        "mode": "READ_ONLY_CYBERSECURITY_PLAN",
        "project_profile": profile,
        "objective": objective.strip(),
        "threat_model": {
            "status": "THREAT_MODEL_INTERVIEW_REQUIRED",
            "trust_boundaries": ["user/device", "application/process", "persistent data",
                                 "external services/dependencies", "build/release pipeline"],
            "attacker_capabilities": "Must be scoped to actual product exposure and data sensitivity.",
            "attack_paths_verified": False,
            "data_flows_verified": False,
        },
        "controls": checks,
        "standards_to_consider": STANDARDS.get(product, ["NIST SSDF"]),
        "scanner_discovery": {
            "caller_reported_tool_name_hints": hints,
            "tool_installation_verified": False,
            "tool_callable_verified": False,
            "tool_license_verified": False,
            "auto_install": False,
            "execution_performed": False,
        },
        "release_gate": {
            "status": "REVIEW_REQUIRED",
            "block_on_accepted_material_findings": True,
            "residual_risk_owner_decision_required": True,
            "blanket_secure_claim_allowed": False,
        },
        "permissions": {
            "caller_reported": permission_state,
            "host_permission_verified": False,
            "external_targets_authorized": False,
            "source_upload_or_network_scan": False,
        },
        "findings": [],
        "findings_status": "NOT_SCANNED",
        "vulnerability_scan_performed": False,
        "penetration_test_performed": False,
        "release_security_attested": False,
        "next": ("No scan or source access is performed by this planner. Inspect the actual project, "
                 "scope trust boundaries and data sensitivity, discover approved tools, then run only "
                 "authorized checks and attach source-revision-bound evidence." if not denied else
                 "Respect permission denial; do not scan or switch to another tool."),
    }
