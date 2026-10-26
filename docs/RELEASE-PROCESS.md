# Release policy

- `VERSION` is source-of-truth SemVer. Update together with `installer.py`, `source/runtime/orbit_mcp.py` and the release package names/metadata.
- Stable baseline: `v0.23.0`; previous ZIP and plugin iterations are external historical releases, not fabricated commits.
- Run `python -m unittest discover -s tests -v`, `python scripts/check_version.py`, and `python scripts/build_release.py` before tagging.
- Release tags use `vMAJOR.MINOR.PATCH` and are immutable: never silently retag or force-push.
- `scripts/build_release.py` creates a reproducible ZIP under `dist/` from tracked sources and a SHA256 file. The original v0.23.0 distribution is retained under `release-assets/` for provenance and is not rebuilt byte-for-byte by default.
- PR gate: owner approval for merge/release and potentially dangerous permission changes. Test browser-preview capabilities on an isolated Todo app before claiming end-to-end readiness.
- Post-release: verify GitHub tag, CI, distribution ZIP checksums, installer behavior in a real host, and plugin release parity.
