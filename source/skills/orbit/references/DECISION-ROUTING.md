# Just-in-time adaptive decisions and model routing

Read for **new product platform decisions, custom components, uncertain framework/API selection, or role-model delegation**. Do not add this full reference to a small file edit's context.

For each user answer, check: did they select a recommended option, say `Custom` (ask for details), or type a custom description? Record their own wording with `orbit_intake_answer` (max 500 chars) and call `orbit_intake_followup` only if the earlier recorded answer changes meaningful scope. Multi-select answers can be preserved as a concise unambiguous free-form string rather than requiring a preset option. Clearly label inferred constraints as proposed until accepted.

Compare `orbit_decision_route` candidates against *real project stack* (React version, platform, supported runtime) before selecting a library, and allow `component_preference: custom`. For an Astryx component, inspect verified React 19+ compatibility and upstream source/docs; don't assume consumer CSS requires StyleX. For Android/iOS use native platform patterns or approved cross-platform solutions, not web UI kits by default. Context7 is versioned docs if connected, not a component library; Impeccable is a design review skill, agent-browser a QA tool.

For delegation, `orbit_model_route` gives a **suggestion only** from the models the host actually reports. Small read-only work often benefits from a fast model, coding from balanced, high-risk security and architecture from deep; complexity and budget preferences change this. Check the actual CLI/IDE custom-agent model field or per-invocation model support, permissions and account availability. Do not override owner model settings, spawn other CLIs, or claim a model switch on a tool recommendation.

Persist the selected project type, relevant decisions, real test evidence and component tradeoff in the brief and appropriate canonical architecture document. Revisit only decisions invalidated by scope changes. See `docs/ADAPTIVE-DECISION-ENGINE.md` for the official-source capability matrix and limitations.


## Optional evidence-gated execution preview (experimental)

For a nontrivial task where the host already has meaningful test or permission evidence, the existing `orbit_model_route` tool can take an **optional** `execution_review` object. It may contain only `validation` (NOT_RUN/PASS/FAIL/BLOCKED), `host_permission_denied`, `side_effects_pending`, and `reviewer_available`. Use it selectively; do not request a new model/agent just to populate the hints. The extra `adaptive_execution` result is **advice only**, not a runtime action or permission grant. See `docs/ADAPTIVE-EXECUTION-PREVIEW.md` in development source.

- Prefer the single existing host session for low-risk work with evidence. Treat a suggested cascade as a cue to inspect failing tests and request *separately authorized* rework/review, never as automatic fallback.
- For security, architecture and other high-assurance work, require a genuinely independent, host-approved reviewer; a caller-supplied `reviewer_available=true` is not proof.
- Permission denial, BLOCKED validation, a pending edit/rollback, or insufficient model capacity must HOLD. **Never switch accounts/providers or retry tools after denial to satisfy a routing suggestion.**
- Never treat a discarded draft as reverted. Inspect the current working tree, actual diff, test logs and capability/approval state first. Claims of test PASS, model availability, price, cache hits or reviewer independence are caller-reported, unverified by Orbit.
- This experimental guide does not change existing task handoff, Autopilot, release gates or the default `orbit_model_route` response. Do not activate background execution or install anything.
