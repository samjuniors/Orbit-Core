# Documentation and context policy

## First audit, never duplicate canonical sources

Map required doc **purposes** (vision, requirements, architecture, roadmap, design, API, decisions, tests, security, operations) to existing paths in README/docs/ADRs/project conventions; don't rely on filenames alone. Existing owner docs are authoritative. Do not archive, delete, move, duplicate or overwrite them without an explicit audit, reason and separate authorization.

Orbit owns coordination. `orbit-architect` drafts design/technical boundaries and tradeoffs. `orbit-writer` produces concise missing documents using *verified* product answers and code; if host-native writer or file tools are unavailable, the lead host writes them sequentially and reports that fact. Review for coherence before accepting. Do not create fake ADRs or fill docs with unapproved assumptions.

`.orbit/PROJECT.md` (if absent and approved) is **only a small Orbit-owned index**: accepted brief, type, complexity, maturity, constraints, link map to owner docs, open decisions and acceptance criteria. It cannot replace existing README, PRD or ADRs. `.orbit/STATE.md` remains the resumable checkpoint.

### Right-sized doc policy

- **Tiny fix/script:** no new architecture-document suite; update existing README/test notes only if meaningful.
- **New Todo-like product with UI/storage:** useful short README and nonduplicate `docs/VISION.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/DESIGN.md`. Each short and substantive. Add REQUIREMENTS only when necessary. If a one-file spike is expressly requested, combine sections in one brief instead of empty placeholders.
- **Normal app/SaaS:** above plus requirements/acceptance, data/API contracts, privacy/auth/security and deployment/runbook only when applicable.
- **SDK/CLI:** public API, compatibility/runtime matrix, examples, versioning/migration and distribution; UI DESIGN isn't mandatory.
- **OS/platform:** platform scope, kernel/distribution/hardware, boot/device/driver boundaries, trust model, reproducible build, tests, staged roadmap, recovery/upgrades; require expert review for high assurance.
- **Data/infra:** architecture/data flow, schema/migrations, security/backup, monitoring and operations based on scope.

A purpose already covered in `PRD.md`, `docs/system-design.md` or elsewhere must be **linked** rather than created a second time. Keep documents cross-referenced and factual. Proposed unconfirmed choices are marked PROPOSED.

## Prompt refinement / low-token operation

Use the **current host model** (no second paid rewriting model) to normalize the user's natural-language request. After interview, persist a compact agreed brief, ideally **120–220 words**, containing:
`goal | product-type | maturity/complexity | audience | selected constraints and stack + rationale | must-haves | non-goals | data/security | acceptance | open questions | canonical paths`.

Subsequent tool/agent turns retrieve only relevant brief fields, current checkpoint, **0–3 pertinent SQLite memories**, changed-file snippets and targeted docs. Pass **delta-based**, bounded handoffs: objective, canonical references, file scope, tests, dependencies and prohibited actions. Never repeatedly copy raw chats, entire plans, all repository files or every subagent transcript. Refresh the checkpoint after milestones with changed/evidence/next; preserve essential constraints.

This reduces repeated **future context**, not past token charges or guaranteed usage/quota. Fidelity, security and user choices outrank brevity.

## Pre-implementation review

Require an agreed/explicitly-defaulted product brief, doc-purpose inventory, required missing docs created or specifically deferred, coherent architecture and roadmap, and an applicable plan before implementation. The Orbit **v0.24 MCP does not yet enforce** this intake gate mechanically; the host instructions must be tested. Do not reset existing builds or checkpoints when introducing the policy.
