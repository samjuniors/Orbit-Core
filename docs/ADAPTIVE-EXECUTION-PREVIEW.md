# Orbit Core — adaptive execution preview pilot (research-informed, original)

**Status:** Experimental, opt-in, read-only engineering pilot on a draft branch. **Not a release claim or an approved automated-routing policy.** Research source: [GitHub Copilot Fusion documentation](https://docs.github.com/en/copilot/concepts/models/copilot-fusion). This implementation is original Orbit code; it does not use Fusion software, models, SDKs, or APIs.

## Why this belongs in the existing model router

Orbit already exposes `orbit_model_route` to recommend host-reported models and host-native role delegation. This pilot adds an **optional `execution_review` input** to that *same* tool without adding a tool, provider, daemon, credential, model proxy, or agent executor.

With `execution_review` absent, the response is unchanged. When present, the tool returns a nested `adaptive_execution` preview with a suggested pattern and specific safety blockers. It never calls a model, changes IDE settings, spawns an agent, writes SQLite, installs a dependency, makes an HTTP request, or grants host approval. The host must independently authenticate its own model/tool availability and permissions.

## Examples (conceptual arguments to existing orbit_model_route)

The original required arguments are `project_root`, `project`, `role`, `task`, and `host`. Optionally provide host-reported `available_models`, `complexity`, `budget`, and:

```json
{"execution_review": {"validation": "PASS"}}
```

For ordinary low-risk read-only work, this returns a `SINGLE_BASELINE_CANDIDATE`; **PASS is only caller-reported** and is not confirmed by Orbit. A failed test with a possible reviewer can return `CASCADE_REWORK_CANDIDATE` **without any invocation or authorization**:

```json
{"execution_review": {"validation": "FAIL", "reviewer_available": true}}
```

High-risk security/architecture work with an available *caller-reported* reviewer can propose `CRITIQUE_REVIEW_CANDIDATE`, but real reviewer independence, host capabilities, consent, scope and source/tests must be verified separately.

```json
{"execution_review": {"validation": "PASS", "reviewer_available": true}}
```

If a host permission was denied, the preview always returns `HOLD_HOST_PERMISSION_DENIED`, even if the model claims tests passed or a reviewer is available. Pending workspace edits always return `HOLD_UNRECONCILED_WORKSPACE_EDITS` and **never assert rollback happened**.

## Safety contract

- Input `execution_review` permits only `validation` (NOT_RUN/PASS/FAIL/BLOCKED), `host_permission_denied`, `side_effects_pending`, and `reviewer_available` (exact booleans). Anything else is invalid. These are untrusted caller hints, **not host attestations**.
- All patterns are suggestions; even `single` does not launch anything. Additional model calls, agent spawns, model switches, cross-provider fallback, permission grants and edit rollbacks stay false/zero.
- Unknown host models inherit the host session, never speculate about plan or availability. High-assurance work with only an insufficient cheap model holds rather than silently downgrading the quality review.
- `BLOCKED` holds; a failed validation requires rework and a fresh real test even when a cascade is suggested. Incomplete edits hold before any reroute. Model/provider denial cannot be retried elsewhere.
- No cache, token, pricing, latency or security benefit is claimed without independent host measurements.
- This does not substitute for RAD P2 Windows LPAC isolation acceptance, application tests, owner approval or an independent security audit.

## Measurement and release gate

Run the focused deterministic tests and GitHub's existing Windows/Linux matrix. In real hosted experiments, measure against the existing single-model baseline on *disposable* simple source discovery, ordinary bug fixing and high-risk code-review cases: correctness from actual tests, independent reviewer findings, extra model calls, latency, cost when the host reports it, permission compliance, context leakage and unrolled edits. Do **not** auto-execute suggested alternatives; use actual host-native approvals and capability discovery.

Before merging or deploying, request independent review and owner acceptance. Keep the v0.33 release candidate and RAD draft chain unchanged. Final release readiness is **NOT VERIFIED** by this preview alone.
