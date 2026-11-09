# Optional independent AI Code Reviewer specialist

**Status:** Development-only host handoff guidance; no runtime dependency, no
automatic installation, and no claim of verified live host integration.

The independent reviewer lives in its own repository:
https://github.com/samjuniors/-ai-code-reviewer
and can run without Orbit. Do not copy its code into Orbit Core or register it
as a mandatory Orbit component.

## Applicability

When the owner asks Orbit to review implementation code, and a **separately
installed and authorized** independent reviewer MCP exists in the current host,
the lead Orbit agent may request an external second opinion.

Host examples and installation/permission constraints:
https://github.com/samjuniors/-ai-code-reviewer/blob/dev/v0.1.0-agent-interop/integrations/README.md

## Host handoff

1. Inspect the actual host tool inventory. An installed config file does not
   prove the reviewer MCP is connected. The server exposes:
   `code_review_static`, `code_review_plan_ai`, `code_review_orbit_gate`.
2. Determine the approved project root, task ID, Git base/head and optional
   explicit policy document. Avoid a floating head when a snapshot is pinned.
3. When both hosts' permissions allow it, the **Orbit lead in the coding host**
   calls `code_review_orbit_gate` with `base`, `head`, `task_id` and an
   optional allowed-root-relative `repo` and `policy`.
4. The returned `orbit-review-evidence-v1` packet is **not an Orbit tool call,
   ledger write, test result, or approval**. It always sets
   `orbit_state_written=false`, `review_accepted=false`, and
   `merge_authorized=false`.
5. If findings exist (`NEEDS_HUMAN_REVIEW`), present the grounded static
   warning, independent verification needs and next action. If none exist
   (`NO_STATIC_FINDINGS_UNVERIFIED`), explicitly state that only a limited
   static check ran; correctness and acceptance remain unverified.
6. Any persistence into an Orbit task/checkpoint must occur *separately*
   through the actual authorized Orbit MCP task lifecycle, using genuine
   task revisions/evidence and owner/host approvals. Preserve review failures
   and denials as BLOCKED/NOT_RUN, not REVIEW_ACCEPTED.
7. If the reviewer is disconnected or not configured, continue with host-native
   code inspection or the existing Orbit reviewer, noting the absence. Do not
   auto-install, bypass host policies, send source to a model, or spawn tools
   in another host.

## Safety and compatibility

- The independent reviewer MCP pins its allowed repository root at launch
  through `AICODE_REVIEW_ROOT`. Do not scope it to the whole home directory.
- It exposes only local static checks and metadata planning. The optional
  Ollama CLI requires *separate explicit user consent* before source transfer;
  model calls are not exposed by the MCP adapter.
- Orbit never grants the reviewer merge authority or permission to mutate
  `.orbit` records. The reviewer is a specialist, not a new orchestrator.
- No Antigravity, Codex, Claude Code, or real Orbit Core host acceptance has
  been verified for this new integration. Use a disposable project first.
- Stop on real permission denials, missing Git ranges, external source
  boundaries or unresolved tests. No hidden fallback to another provider.

## Acceptance before enabling by default

- Exact MCP tool inventory and host version.
- Fixed scope and symlink traversal denial in a real host.
- A review call returns the expected pinned SHAs, findings and
  `orbit_state_written=false`.
- An authorized Orbit task readback can refer to the evidence without falsely
  changing acceptance status.
- Host approval and denial handling are recorded.
- The independent reviewer's full test suite and GitHub Actions blocker have
  been resolved or are explicitly documented as incomplete.

This integration should remain opt-in and non-blocking for Orbit projects that
do not install the external reviewer.
