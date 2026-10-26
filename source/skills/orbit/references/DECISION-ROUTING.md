# Just-in-time adaptive decisions and model routing

Read for **new product platform decisions, custom components, uncertain framework/API selection, or role-model delegation**. Do not add this full reference to a small file edit's context.

For each user answer, check: did they select a recommended option, say `Custom` (ask for details), or type a custom description? Record their own wording with `orbit_intake_answer` (max 500 chars) and call `orbit_intake_followup` only if the earlier recorded answer changes meaningful scope. Multi-select answers can be preserved as a concise unambiguous free-form string rather than requiring a preset option. Clearly label inferred constraints as proposed until accepted.

Compare `orbit_decision_route` candidates against *real project stack* (React version, platform, supported runtime) before selecting a library, and allow `component_preference: custom`. For an Astryx component, inspect verified React 19+ compatibility and upstream source/docs; don't assume consumer CSS requires StyleX. For Android/iOS use native platform patterns or approved cross-platform solutions, not web UI kits by default. Context7 is versioned docs if connected, not a component library; Impeccable is a design review skill, agent-browser a QA tool.

For delegation, `orbit_model_route` gives a **suggestion only** from the models the host actually reports. Small read-only work often benefits from a fast model, coding from balanced, high-risk security and architecture from deep; complexity and budget preferences change this. Check the actual CLI/IDE custom-agent model field or per-invocation model support, permissions and account availability. Do not override owner model settings, spawn other CLIs, or claim a model switch on a tool recommendation.

Persist the selected project type, relevant decisions, real test evidence and component tradeoff in the brief and appropriate canonical architecture document. Revisit only decisions invalidated by scope changes. See `docs/ADAPTIVE-DECISION-ENGINE.md` for the official-source capability matrix and limitations.
