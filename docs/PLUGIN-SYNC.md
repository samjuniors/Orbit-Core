# Sync policy for ChatGPT Orbit plugin

Two release destinations are intentionally separate:

1. `orbit-core-mcp`: source-of-truth for the local universal Python MCP/runtime, installer, and host integration source.
2. Existing private ChatGPT plugin `plugins_6ad98fbff56c81919fce7a6d5dd3f532`: plugin skills, references and managed package release, updated through Plugin Creator after review.

This repository is a **source snapshot** of the v0.23.0 local distribution, not the complete historical ChatGPT plugin archive. Previous plugin releases remain in Plugin Creator; do not pretend a Git commit recreates their original release dates.

For next versions: code and test on a Git feature branch; PR review; merge and tag; build tested ZIP; update the private plugin with the appropriate updated skill/asset package; verify read-back and record both release IDs in CHANGELOG. No unattended GitHub→ChatGPT sync is installed. Make publication a separate explicit operation with owner approval.
