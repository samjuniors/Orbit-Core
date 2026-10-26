# Publishing the first GitHub Release

The repository source does **not** become a GitHub Release automatically when uploaded to `main`.

After the release automation pull request is merged:

1. Open https://github.com/samjuniors/Orbit-Core-MCP/actions/workflows/release.yml.
2. Click **Run workflow**; select `main`, enter **`0.23.0`**, and click **Run workflow** again.
3. Wait for the **Publish versioned release** job to finish successfully; review its test/build steps.
4. Open https://github.com/samjuniors/Orbit-Core-MCP/releases and confirm **ORBIT Core MCP v0.23.0**, four downloadable assets, and pre-release designation.
5. Open https://github.com/samjuniors/Orbit-Core-MCP/tags and confirm that **`v0.23.0`** exists. Future versions follow the same process after updating `VERSION`, source, and changelog on `main`.

If **Run workflow** is missing, check that the release workflow is merged to the repository's default branch and GitHub Actions is enabled.

Do not create Git history for older pre-baseline plugin versions. Do not reassign existing tags.