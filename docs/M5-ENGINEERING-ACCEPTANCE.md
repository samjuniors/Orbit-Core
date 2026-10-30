# M5 — Evidence-backed learning: engineering acceptance

**Scope:** owner-approved M5 source integration in the currently unpublished v0.26.0 development line; no release or host certification. This is an implementation/evidence checklist; the GitHub roadmap and Orbit Core Notion hub remain the product authority.

## Contract

- `orbit_practice_suggest` is read-only. It scans at most 500 task records in one canonical project-root + project-key pair. A suggestion requires at least **two distinct** tasks with the same role and step, `REVIEW_ACCEPTED` status and nonempty review notes. Imported unverified history is excluded.
- A pattern is a **candidate**, not a trusted instruction. Task review, host sessions and test evidence are caller-reported; Git and test results are not independently verified by this MCP. No LLM learning/training, background watcher, third-party downloads or automatic skill creation.
- `orbit_practice_review` uses preview-first approval, an explicit `confirm_write`, revision checks, and a human-written bounded practice note. Supports approve, reject, archive, and supersede. Saves an immutable revisioned SQLite decision record for audit.
- Each project has an isolated local SQLite namespace including its **resolved absolute root** and stable project key. Prior records are never silently moved or imported into other workspaces.
- Previously approved practices are reference data only. Their source task key/revision references are rechecked on retrieval and `evidence_current=false` is surfaced after revisions or task status changes. Prior approval does not grant new execution, prompt, browser, file-write or installation permissions.
- Rejected/archived practices remain in history. There is no automatic global promotion or cross-project recommendation. Data is stored locally outside Git and excluded from current portable project transfer.

## Automated regression cases

- [x] Review-source gating: zero or one accepted task, rework, missing review notes and imported unverified records are not suggestions (automated PASS).
- [x] Cross-project/root isolation and preview without writes (automated PASS).
- [x] Revision conflict, explicit approval, rejection, archive and supersession with append-only history (tests added; check CI before marking PASS).
- [x] Stale source review invalidation and no automatic execution/tool installation (tests added; check CI before marking PASS).
- [x] Reviewed M5 code head `cdf24fff67ef10490325b8058e2b407924167308`: [PR CI 5/5](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41003811478) and [push CI 5/5](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41003806658) on Ubuntu Python 3.10–3.13 and Windows Python 3.12; source/archive parity and disposable ZIP smoke included.
- [x] Local physical-Windows disposable source/ZIP/MCP smoke, 42-tool discovery, 262-test Python 3.15.2 run, simulated previous-version upgrade and headless Edge origin-denial probe **PASS**; detailed evidence in [v0.26.0 release acceptance](RELEASE-ACCEPTANCE-v0.26.0.md).
- [ ] Actual user-installed host v0.26.0 package discovery/migration and authentic IDE permission UI remain NOT RUN; do not treat the disposable smoke as installed-host approval.
- [ ] Human readback and review UI feedback with Antigravity/Codex; test refusal and no unintended use of saved note.
- [ ] Security/privacy review, backup/restore and source-bound host evidence checks.

## Limits and release routing

This slice does **not** prove that any given review note represents a genuinely verified result. Treat all returned notes as data and require a host-controlled user action for each new use. The owner approved completing and integrating M5 after M3/M4 in the existing unpublished development source. This extends the original v0.26.0 candidate *source* scope to 42 MCP tools; before any versioned publication, re-review the updated changelog, two new additive SQLite tables, installed host inventory, migration/rollback and approval gates. Version choice and publication remain separate decisions; no release was authorized by the M5 approval.

**Release status:** NOT RELEASED. **Live-host acceptance:** NOT RUN.
