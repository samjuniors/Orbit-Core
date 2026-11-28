"""Project-specific cybersecurity review planning; no scanner or command execution.

Tool names are caller-reported hints, not proof of installation or permission.
A plan is not a threat-model interview, vulnerability scan, penetration test,
certification, or release security attestation.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

# Per-process key: the snapshot detects source changes within one MCP session,
# but cannot be used offline to test guessed file contents (credentials).
_SNAPSHOT_KEY = secrets.token_bytes(32)

import orbit_skill_plan
import orbit_specialists

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


# This bounded scanner is intentionally a static source-pattern review, not SAST.
# It reuses Orbit's handle-relative, no-follow project traversal and never
# returns source lines or secret values to the caller.
_SOURCE_SUFFIXES = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java",
    ".kt", ".kts", ".swift", ".go", ".rs", ".cs", ".c", ".h", ".cpp",
    ".hpp", ".php", ".rb", ".sh", ".ps1", ".bat", ".cmd", ".sql",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".properties",
})
_SOURCE_EXCLUDE = frozenset({
    ".git", ".orbit", "node_modules", "vendor", "dist", "build",
    "coverage", "__pycache__", ".venv", "venv", "target", ".next",
    ".nuxt", ".svelte-kit", ".idea", ".vscode",
})
_SOURCE_PATTERNS = (
    ("PRIVATE_KEY_MATERIAL", "HIGH",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
     "Private-key material appears in a scanned source/configuration file.",
     "Remove the key from the repository, rotate it, and use an approved secret store."),
    ("AWS_ACCESS_KEY_ID", "HIGH",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     "An AWS access-key identifier pattern appears in a scanned file.",
     "Revoke/rotate the credential and inspect repository history and access logs."),
    ("HARDCODED_CREDENTIAL", "HIGH",
     re.compile(r"""(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token|secret)\b\s*[:=]\s*["'][^"']{8,}["']"""),
     "A credential-like assignment appears to contain a literal value.",
     "Verify whether it is live; rotate if exposed and load secrets from the host environment."),
    ("TLS_VERIFICATION_DISABLED", "MEDIUM",
     re.compile(r"(?i)(?:verify\s*=\s*False|rejectUnauthorized\s*:\s*false|ssl\._create_unverified_context)"),
     "TLS certificate verification appears to be disabled.",
     "Restore certificate verification and use a trusted CA configuration."),
    ("SHELL_TRUE", "MEDIUM",
     re.compile(r"(?i)\bshell\s*=\s*True\b"),
     "A subprocess call appears to enable shell parsing.",
     "Prefer argument arrays with shell disabled; validate any unavoidable command input."),
    ("UNSAFE_DESERIALIZATION", "MEDIUM",
     re.compile(r"(?i)(?:pickle\.loads?\s*\(|yaml\.load\s*\()"),
     "A potentially unsafe deserialization API appears in source.",
     "Use safe data formats/loaders and strict schemas; verify caller-controlled input boundaries."),
    ("DYNAMIC_CODE_EVALUATION", "MEDIUM",
     re.compile(r"(?i)\b(?:eval|exec)\s*\("),
     "Dynamic code evaluation appears in source.",
     "Avoid evaluating untrusted strings; replace with explicit parsers or dispatch tables."),
    ("JWT_NONE_ALGORITHM", "HIGH",
     re.compile(r"""(?i)\b(?:alg|algorithm)\s*[:=]\s*["']none["']"""),
     "A JWT algorithm configuration appears to allow the none algorithm.",
     "Pin an explicit allowed signing algorithm and reject unsigned tokens."),
)


def scan_project(root, *, permission_state="UNKNOWN"):
    """Run bounded, local-only source pattern checks under an approved workspace.

    Findings are likely indicators, not verified vulnerabilities. This scanner
    does not execute code, install tools, access the network, or return matched
    source text. It fails closed on unsafe traversal and incomplete budgets.
    """
    import hashlib
    import os
    from pathlib import Path, PurePosixPath

    if permission_state != "APPROVED":
        return {
            "status": "HOLD_PERMISSION_DENIED" if permission_state == "DENIED"
                      else "HOLD_PERMISSION_UNKNOWN",
            "findings": [], "findings_status": "NOT_SCANNED",
            "source_files_scanned": 0, "source_snapshot_sha256": None,
            "source_revision_verified": False, "project_code_executed": False,
            "network_accessed": False,
        }
    base = Path(root)
    if base.is_symlink() or not base.is_dir():
        raise ValueError("Expected an existing non-symlink project root")
    base = Path(os.path.abspath(base)) if os.name == "nt" else base.resolve(strict=True)
    max_files, max_bytes, max_entries = 240, 8 * 1024 * 1024, 4000
    files_seen = 0
    bytes_read = 0
    entries_seen = 0
    reasons = set()
    findings = []
    snapshot = hmac.new(_SNAPSHOT_KEY, digestmod=hashlib.sha256)
    walker = orbit_specialists._visual_walk(base)
    try:
        for rel_dir, directory, dirs, names in walker:
            if len(rel_dir) >= 10:
                dirs[:] = []
                reasons.add("MAX_DIRECTORY_DEPTH")
                continue
            dirs[:] = sorted(
                d for d in dirs
                if d not in _SOURCE_EXCLUDE and not d.startswith(".")
            )
            entries_seen += len(dirs) + len(names)
            if entries_seen > max_entries:
                reasons.add("MAX_DIRECTORY_ENTRIES")
                break
            for name in sorted(names):
                if name.startswith("."):
                    continue
                rel = PurePosixPath(*(tuple(rel_dir) + (name,)))
                if rel.suffix.lower() not in _SOURCE_SUFFIXES:
                    continue
                if files_seen >= max_files:
                    reasons.add("MAX_SOURCE_FILES")
                    break
                try:
                    stream, metadata = orbit_specialists._open_visual_source(directory, name)
                    with stream:
                        if type(getattr(metadata, "st_nlink", None)) is not int or metadata.st_nlink != 1:
                            reasons.add("HARD_LINK_SOURCE_FILE")
                            continue
                        if metadata.st_size > 256 * 1024 or bytes_read + metadata.st_size > max_bytes:
                            reasons.add("MAX_FILE_OR_BYTE_LIMIT")
                            continue
                        raw = stream.read(256 * 1024 + 1)
                except orbit_specialists.UnsafeVisualSourceError:
                    reasons.add("UNSAFE_OR_MISSING_SOURCE_FILE")
                    continue
                except (OSError, ValueError):
                    reasons.add("UNREADABLE_SOURCE_FILE")
                    continue
                if len(raw) > 256 * 1024 or bytes_read + len(raw) > max_bytes:
                    reasons.add("MAX_FILE_OR_BYTE_LIMIT")
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    reasons.add("NON_UTF8_SOURCE_SKIPPED")
                    continue
                files_seen += 1
                bytes_read += len(raw)
                relative = rel.as_posix()
                digest = hashlib.sha256(raw).digest()
                snapshot.update(relative.encode("utf-8", "surrogatepass") + b":" + digest)
                for line_number, line in enumerate(text.splitlines(), 1):
                    for rule, severity, pattern, summary, remediation in _SOURCE_PATTERNS:
                        if not pattern.search(line):
                            continue
                        # Known placeholders and environment indirection are not
                        # treated as literal credential exposures.
                        if rule == "HARDCODED_CREDENTIAL" and re.search(
                            r"(?i)(?:example|placeholder|changeme|dummy|fake|"
                            r"your[_ -]|process\.env|os\.environ|getenv|\$\{)",
                            line,
                        ):
                            continue
                        # This is a stable finding locator, not a content digest.
                        # Never hash matched source text: predictable credentials can
                        # otherwise be tested offline against the returned digest.
                        evidence_ref = hashlib.sha256(
                            (rule + ":" + relative + ":" + str(line_number)).encode("utf-8", "surrogatepass")
                        ).hexdigest()
                        findings.append({
                            "id": "ORBIT-" + rule,
                            "severity": severity,
                            "status": "LIKELY_NOT_VERIFIED",
                            "file": relative,
                            "line": line_number,
                            "evidence_ref_sha256": evidence_ref,
                            "summary": summary,
                            "remediation_guidance": remediation,
                            "source_text_returned": False,
                        })
                        if len(findings) >= 120:
                            reasons.add("MAX_FINDINGS")
                            break
                    if len(findings) >= 120:
                        break
                if len(findings) >= 120:
                    break
            if files_seen >= max_files or len(findings) >= 120:
                break
    finally:
        walker.close()
    return {
        "status": "STATIC_REVIEW_HINTS_FOUND" if findings else "NO_STATIC_HINTS_REVIEW_REQUIRED",
        "findings_status": "LIKELY_NOT_VERIFIED" if findings else "NO_STATIC_HINTS_NOT_A_PASS",
        "findings": findings,
        "source_files_scanned": files_seen,
        "source_bytes_scanned": bytes_read,
        "source_snapshot_sha256": snapshot.hexdigest(),
        "source_snapshot_keyed_per_process": True,
        "source_revision_verified": False,
        "partial_reasons": sorted(reasons),
        "scan_limits": {"max_files": max_files, "max_bytes": max_bytes,
                        "max_entries": max_entries, "max_findings": 120},
        "source_text_returned": False,
        "secret_values_returned": False,
        "project_code_executed": False,
        "network_accessed": False,
        "tool_installed_or_invoked": False,
        "penetration_test_performed": False,
        "security_certification": False,
        "next": "Independently reproduce and triage each hint, review unscanned areas and source revision, remediate, then rerun relevant checks. No hints is not a security pass.",
    }
