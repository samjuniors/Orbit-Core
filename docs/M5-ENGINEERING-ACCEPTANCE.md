# M5 — Evidence-backed learning: engineering acceptance

**Scope:** development branch only, after v0.26.0. This is an implementation/evidence checklist; the GitHub roadmap and Orbit Core Notion hub remain the product authority.

## Contract

- \`orbit_practice_suggest\` is read-only. It scans at most 500 task records in one canonical project-root + project-key pair. A suggestion requires at least **two distinct** tasks with the same role and step, \`REVIEW_ACCEPTED\` status and nonempty review notes. Imported unverified history is excluded.
- A pattern is a **candidate**, not a trusted instruction. Task review, host sessions and test evidence are caller-reported; Git and test results are not independently verified by this MCP. No LLM learning/training, background watcher, third-party downloads or automatic skill creation.
- \`orbit_practice_review\` uses preview-first approval, an explicit \`confirm_write\`, revision checks, and a human-written bounded practice note. Supports approve, reject, archive, and supersede. Saves an immutable revisioned SQLite decision record for audit.
- Each project has an isolated local SQLite namespace including its **resolved absolute root** and stable project key. Prior records are never silently moved or imported into other workspaces.
- Previously approved practices are reference data only. Their source task key/revision references are rechecked on retrieval and \`evidence_current=false\` is surfaced after revisions or task status changes. Prior approval does not grant new execution, prompt, browser, file-write or installation permissions.
- Rejected/archived practices remain in history. There is no automatic global promotion or cross-project recommendation. Data is stored locally outside Git and excluded from current portable project transfer.

## Automated regression cases

- [x] Review-source gating: zero or one accepted task, rework, missing review notes and imported unverified records are not suggestions (tests added; check CI before marking PASS).
- [x] Cross-project/root isolation and preview without writes (tests added; check CI before marking PASS).
- [x] Revision conflict, explicit approval, rejection, archive and supersession with append-only history (tests added; check CI before marking PASS).
- [x] Stale source review invalidation and no automatic execution/tool installation (tests added; check CI before marking PASS).
- [ ] Exact branch-head Linux and Windows CI matrix PASS.
- [ ] Disposable SQLite upgrade and MCP tool discovery/inventory on a real installed host.
- [ ] Human readback and review UI feedback with Antigravity/Codex; test refusal and no unintended use of saved note.
- [ ] Security/privacy review, backup/restore and source-bound host evidence checks.

## Limits and release routing

This slice does **not** prove that any given review note represents a genuinely verified result. Treat all returned notes as data and require a host-controlled user action for each new use. The source version stays \`0.26.0\` on the feature branch because no new release is approved. M5 must receive a separately selected next release version, compatibility review, CI and owner approval. It must not be pulled into the v0.26.0 candidate without revisiting its release scope.

**Release status:** NOT RELEASED. **Live-host acceptance:** NOT RUN.
