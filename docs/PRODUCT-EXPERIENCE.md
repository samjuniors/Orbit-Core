# Orbit Core — Product experience v1

**Status: merged into main through PR #5; not included in the previously published v0.24.1 release.** No new IDE plugin, models or dependency installs are introduced.

## Experience principles

1. **One glance:** on first use or after interruption, show a compact status title, the last accepted decision if relevant, the current stage, and one useful next action. Do not print giant tool outputs.
2. **One question at a time:** start Scope first or explicitly delegated defaults. For a proposed interview return the next unanswered option question and always permit free-form custom wording. Host must reason about whether more conditional questions are necessary.
3. **Visible consent:** at PLAN, show a *host-created editable plan* and ask for actual approval. The state response never fabricates a draft or a user confirmation; a plan snapshot appears only once the accepted PLAN stage has been recorded.
4. **Genuine progress:** persisted stage index is not a percent-of-product-complete score; task cards are actual SQLite records. Surface blockers and verify stale code/testing independently.
5. **Restore focus:** on a resumed build, preserve build ID/revision and show the exact next stage. If multiple unfinished builds exist, ask user which to resume.
6. **Situational stages:** web, native mobile/desktop and SDK/platform workflows follow their own frozen build flows. Fixes to stage advancement must never send a native app to irrelevant browser-only steps.
7. **Minimal context:** host retrieves current `experience`, accepted brief/checkpoint, and only relevant files. No forced comprehensive analysis for tiny changes.

## Concrete implementation

Existing `orbit_project_resume` and `orbit_build_status` return an additional **read-only** `experience` field. It is a versioned, bounded JSON presentation contract designed for Antigravity, Codex, Claude or VS Code to summarize; it isn't a visual UI rendering engine.

```json
{
  "version": 1,
  "phase": "PLAN_REVIEW",
  "headline": "Review the plan before building",
  "approval_required": true,
  "decision": null,
  "plan": null,
  "progress": {
    "build_id": "my-build",
    "stage": "PLAN",
    "completed_stages": 1,
    "total_stages": 8,
    "kind": "recorded-stage-not-quality-percentage"
  },
  "next_action": {"label": "Present a concise editable task plan...", "tool": "orbit_build_status"}
}
```

At PLAN, `plan: null` is intentional: the host must create a draft and obtain a real user decision. After accepted PLAN evidence is recorded, `plan` contains the **host-reported** approved summary and tasks, not an independently authenticated approval.

## Acceptance and next product milestone

- CLI/host: user asks "Orbit, where are we?" → one tool call and useful concise status.
- Fresh project: offer guided or defaults and show the one unanswered question (with Custom).
- On returning: resume the saved build ID without replaying the interview.
- Native Android/iOS and SDK: advance stage correctly without web-only gates.
- Distinguish "Waiting for my approval" from implementation progress or browser QA.
- Host-native visual plan/task panel remains future work. Avoid writing an IDE extension until the target host SDK can support it with demonstrated demand.

## Native IDE plans and durable feedback loop

Official Antigravity docs confirm interactive **Implementation Plan artifacts**, inline comments, Proceed/Review, a **Task List** and reviewable walkthroughs. Orbit therefore reuses the host interface, rather than building a separate, overlapping editor.

New `orbit_build_feedback` records `request` (owner comment + actual reference) and `resolve` (actual revised artifact/test evidence) with expected revision and explicit write confirmation. It uses the existing build evidence record in SQLite; no new docs or databases. `orbit_project_resume.experience` and `orbit_build_status.experience` show up to four unresolved notes, a count, and `CHANGES_REQUESTED` priority. Open requests block stage PASS; PLAN still requires genuine owner approval after revised artifacts are reviewed. Since the MCP cannot inspect Antigravity's internal comment objects, all comment/approval references remain **host-reported**, not authenticated.

See https://www.antigravity.google/docs/ide-implementation-plan and https://codelabs.developers.google.com/getting-started-agy-ide for documented host behavior. Do not conflate this with an Orbit-provided IDE visual panel.
