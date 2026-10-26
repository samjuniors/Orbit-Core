# Publish this baseline to GitHub

## First-time remote creation

The GitHub connector used to prepare this snapshot can read and edit existing repositories but does **not** offer repository creation. Do not place this standalone MCP in the unrelated public `samjuniors/orbit` or `orbit-sandbox` by default. Create a **new private repository** in GitHub named `orbit-core-mcp` under your own account. Leave **Initialize with README**, `.gitignore`, and License unchecked (this bundle already contains versioned source).

The download provides a **Git-ready repository ZIP** containing the initial commit and `v0.23.0` tag. The simplest Windows/macOS path is:

1. Extract `ORBIT-Core-MCP-v0.23.0-Git-Repository.zip` to a permanent folder.
2. Open **GitHub Desktop** and sign in.
3. **File → Add local repository → Choose** that extracted folder (the one containing `.git`).
4. **Publish repository**, set the repository name to `orbit-core-mcp` and **Keep this code private** checked. Publish.
5. Verify the files and `v0.23.0` tag on GitHub, and check the **Actions → CI** run.

You can also create an empty private GitHub repository first and push from the terminal in the extracted Git workspace:

```bash
git remote add origin https://github.com/<your-account>/orbit-core-mcp.git
git push -u origin main
git push origin v0.23.0
```

Replace `<your-account>` with the owner visible in GitHub. Keep visibility **private** until the author decides on licensing and security review. Verify `main` and the tag on GitHub and inspect Actions → CI.

If an existing remote is configured, inspect it first (`git remote -v`) and do **not** overwrite its URL or force-push. Never mix this repository with the separate `samjuniors/orbit` product without an explicit migration.

## Future changes

1. `git checkout -b feat/local-preview-manager` from latest main.
2. Make a small change; run tests and project acceptance checks.
3. Commit, push feature branch, open a PR; check the diff and GitHub Actions status.
4. Merge only after approval; bump version and update Changelog in the release PR.
5. Tag the merged validated release and attach the generated ZIP to GitHub Release.
6. Update the ChatGPT Orbit plugin through Plugin Creator as a **separate** explicit action, preserving its current plugin ID.

Never commit customer-specific `.orbit/STATE.md`, SQLite or API credentials.
