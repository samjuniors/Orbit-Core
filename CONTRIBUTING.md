# Contributing to Orbit Core

Thanks for helping improve Orbit Core, a local-first AI workspace orchestrator.

## Before you begin

- Review the [README](README.md), [security guidance](SECURITY.md), and [release process](docs/RELEASE-PROCESS.md).
- Check [existing issues](https://github.com/samjuniors/Orbit-Core/issues) and open a focused proposal before beginning substantial work.
- Keep Orbit Core separate from other projects. Do not introduce external code, models, cloud dependencies, or third-party agents without an explicit rationale, security review and license compatibility check.
- **License status:** This repository does not currently contain an explicit open-source license. Public availability does not grant general reuse, redistribution, or relicensing rights. A license is an owner decision; open an issue to discuss it rather than assuming one.

## Contributions

1. Fork the repository and make a focused branch from the current `main`. For versioned releases, follow the project's reviewed release-branch procedure.
2. Read the relevant existing implementation and regression tests before changing behavior. Keep code maintainable and minimize dependencies.
3. Run `python scripts/prepare_release_candidate.py` only when working on versioned packaging changes. For ordinary code changes, follow the tests and CI for your branch.
4. Run `python -m unittest discover -s tests -v` and the relevant targeted tests. Include test evidence and supported Windows/Linux context where applicable.
5. Open a PR with the problem, exact changes, compatibility and user-data impacts, test results, and any unresolved acceptance gates. Do not report unexecuted tests as passing.

## Compatibility and safety

- Never overwrite project checkpoints, custom agent files, SQLite/WAL data, or host configuration without explicit authorization.
- Retain MCP identifiers, installer settings, and published release compatibility unless a reviewed migration is part of the scope.
- Separate host-native agent execution from caller-reported tool availability; a passing local unit test is not proof of a live permission dialog or GUI acceptance.
- Never include real credentials, tokens, private workspace data, user logs or unpublished user files in a PR.
- Report security concerns using the repository's [security policy](SECURITY.md), rather than publishing exploitable details in a public issue.

Published tags and release packages are immutable. Any change to a released package requires a reviewed new version and owner approval.
