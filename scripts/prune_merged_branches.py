"""One-time, lease-checked cleanup of *already merged* GitHub PR branches.

No implicit wildcard deletion. Requires --apply for writes, exact commit SHAs,
matching merged PRs, and a repository-owned manifest. Keep closed-unmerged work.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPOSITORY = "samjuniors/Orbit-Core"
SHA = re.compile(r"^[a-f0-9]{40}$")
BRANCH = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]{0,150}$")
PROTECTED = {"main", "master", "develop", "development", "production", "staging"}


def candidates(manifest):
    if not isinstance(manifest, dict) or manifest.get("repository") != REPOSITORY:
        raise ValueError("Cleanup manifest must target the approved Orbit Core MCP repository")
    rows = manifest.get("branches")
    if not isinstance(rows, list) or len(rows) > 20:
        raise ValueError("Cleanup requires a bounded explicit branch list")
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid branch entry")
        name, sha, pr = row.get("name"), row.get("head_sha"), row.get("pr")
        if (not isinstance(name, str) or not BRANCH.fullmatch(name) or
                name.lower() in PROTECTED or ".." in name or "//" in name or
                name.endswith(("/", ".lock")) or name.startswith(("refs/", "tags/"))):
            raise ValueError("Unsafe or protected branch name")
        if not isinstance(sha, str) or not SHA.fullmatch(sha):
            raise ValueError("Expected full lowercase commit SHA")
        if type(pr) is not int or pr < 1:
            raise ValueError("Expected an associated merged PR number")
        if name in seen:
            raise ValueError("Duplicate branch in cleanup manifest")
        seen.add(name)
        result.append((name, sha, pr))
    return result


def github(method, path):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required to audit live branch state")
    url = "https://api.github.com/repos/" + REPOSITORY + "/" + path
    request = urllib.request.Request(
        url, method=method,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "Orbit-Verified-Branch-Pruner"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = response.read(1_000_000)
            return json.loads(data) if data else {}
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and method == "GET":
            return None
        raise


def audit_and_prune(manifest, api=github, apply=False):
    """Returns a report; refuses to delete refs that moved since PR review."""
    report = []
    for name, expected_sha, pr_number in candidates(manifest):
        ref_path = "git/ref/heads/" + urllib.parse.quote(name, safe="/")
        pr = api("GET", "pulls/" + str(pr_number))
        ref = api("GET", ref_path)
        if not ref:
            report.append({"branch": name, "status": "ALREADY_MISSING"})
            continue
        actual = ref.get("object", {}).get("sha")
        if (not isinstance(pr, dict) or pr.get("merged_at") is None or
                pr.get("head", {}).get("ref") != name or
                pr.get("head", {}).get("sha") != expected_sha or
                pr.get("base", {}).get("ref") != "main" or
                actual != expected_sha):
            report.append({"branch": name, "status": "PRESERVED_UNVERIFIED_OR_CHANGED"})
            continue
        if not apply:
            report.append({"branch": name, "status": "READY_TO_DELETE", "pr": pr_number})
            continue
        # Ref checks above are not atomic with deletion. This workflow is scoped
        # to old frozen merged branches, not an arbitrary active collaborator.
        api("DELETE", "git/refs/heads/" + urllib.parse.quote(name, safe="/"))
        report.append({"branch": name, "status": "DELETED", "pr": pr_number})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--apply", action="store_true", help="Actually delete matching remote branches")
    args = parser.parse_args(argv)
    if os.getenv("GITHUB_REPOSITORY", REPOSITORY) != REPOSITORY:
        raise SystemExit("Refusing to operate on a different repository")
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = audit_and_prune(manifest, apply=args.apply)
    print(json.dumps({"mode": "APPLY" if args.apply else "PREVIEW", "results": report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
