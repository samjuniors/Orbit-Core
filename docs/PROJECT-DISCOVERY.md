# Orbit guided discovery, documentation and compact context (v0.24 candidate)

**Current status:** host orchestration guidance and installer-delivered reference files, not a new MCP gate or autonomous writer daemon. The user's Todo run showed that the coding host started planning/code without an interview and generated only PLAN.md; this policy corrects that expected workflow for *new* projects. Existing builds are preserved.

## Intake before implementation

Audit owner code/docs/ADRs/checkpoints, classify category, complexity, maturity and risk, turn a natural-language prompt into a compact **PROPOSED** brief, then ask 2–5 high-impact questions with recommended answers and a **Use recommendations** response. Skip answered questions and allow explicit user-directed defaults. SDKs require compatibility/API questions; operating systems require kernel/hardware scope; SaaS requires users/data/operations. Do not mistake a resume or tiny bug fix for a new build.

## Documentation by need, not quota

Use existing canonical docs regardless of filenames and keep owner content in place. New small UI products should have concise vision, architecture, roadmap and design descriptions where missing; real SDKs/OSes need specialized docs. `.orbit/PROJECT.md` is only a compact agreed brief and doc-path index; `.orbit/STATE.md` stays the checkpoint. Write real content, not template stubs. Draft via native architect/writer when available, or sequentially through the host. Do not claim delegation if unavailable.

## Compact context

Normalize the agreed scope into 120–220 words (goal, type, choices, requirements, non-goals, acceptance and doc references). On resume, use only the brief, checkpoint, targeted files and up to 3 relevant project-scoped memories, then add deltas. No magic token reduction or hidden independent background work.

See `source/skills/orbit/references/PROJECT-INTAKE.md` and `DOCS-AND-CONTEXT.md` for the full instructions and example guided interview.

## Acceptance tests before release

- A new Todo folder receives relevant recommended options **before** stack/plan; accepted recommendations produce concise actual docs.
- SDK receives compatibility/API/versioning choices; OS receives feasibility/hardware/security scope; no irrelevant boilerplate.
- Existing project owner docs and ADRs are not copied, replaced, moved or deleted.
- A resumed Todo build keeps its SQLite checkpoint and skips reinterview.
- Fresh installs deliver skill reference files to Antigravity, Codex and Claude Code; the installer previews and backs up recognized stock upgrades.
- If host-native writer is unavailable, sequential host writes the docs with an honest execution report.
- No additional model, external tool install, deployment, Git push or public endpoint is automatic.


## Adaptive question and reuse policy

The first interview question resolves the costliest unknown. After the user selects an option, `orbit_intake_answer` persists that choice and `orbit_intake_followup` can append one consequential branch question **only when linked to a stored answer**; the host supplies rationale and its decision-based recommendation. The host must stop asking once scope can be planned safely, rather than automatically presenting all predefined questions. Intake revision guards and the original `orbit_intake_approve` gate remain in place; existing builds are not reset. The host performs reasoning: MCP does not secretly run another model.

Before implementation, compare existing host/project code, standard APIs and maintained prebuilt packages and choose the simplest reliable route after security/license/runtime review and owner approval for installs. The user-supplied `agent-browser` is a visual browser-QA provider, not a UI component library. Evaluate it only when connected and permitted; existing Orbit Playwright QA evidence remains mandatory for its current formal gate.
