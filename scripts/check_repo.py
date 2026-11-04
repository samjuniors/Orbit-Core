#!/usr/bin/env python3
"""Check a Git repository against the maintainer's repo standard (see SKILL.md).

Standard library only; runs on Python 3.8+.  Usage:

    python check_repo.py [path] [--strict] [--json] [--gh-commands]

Exit status is 1 if any ERROR is found (or any WARN with --strict), else 0.
Levels: ERROR = blocks adoption/release, WARN = should fix, INFO = FYI.
"""
import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

SEMVER = r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.+-]+)?"
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|REPLACE[ _-]?ME|lorem ipsum)\b", re.I)
STALE_LATEST_RE = re.compile(
    r"(?i)(?:latest|currently)\s+(?:published\s+)?(?:release|package|version)\s+is\s+(?:\*\*)?v?\d+\.\d+\.\d+")
SECTION_PATTERNS = [
    ("quickstart", r"install|quick ?start|getting started|get started",
     "README needs an Install / Quick start section"),
    ("usage", r"usage|how to use|how it works|documentation|docs|guide|examples?|features",
     "README needs a Usage, How it works or Documentation section"),
    ("why", r"\bwhy\b|problem|motivation",
     "README should state the problem and the solution (a 'Why <name>?' or 'The problem' section)"),
    ("contributing", r"contribut|development",
     "README should have a Contributing section"),
    ("license", r"licen[sc]e|copying",
     "README should have a License section"),
    ("support", r"\bsponsors?\b|funding|donat|backers?|support (?:the|this|my|our)|show your support",
     "README should have a Sponsor / Support section"),
]


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, code, msg):
        self.items.append({"level": level, "code": code, "message": msg})

    def count(self, level):
        return sum(1 for i in self.items if i["level"] == level)


def read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def strip_fences(text):
    return re.sub(r"(?ms)^(\`\`\`|~~~).*?^\1[^\n]*$", "", text)


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\s+", " ", re.sub(r"[*_\`]", "", s)).strip()


def headings(text):
    """Return [(level, text)] for ATX, setext and HTML headings, in document order."""
    text = strip_fences(text)
    found = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            found.append((i, len(m.group(1)), clean(m.group(2))))
        elif i and re.match(r"^(=+|-+)\s*$", line) and len(line.strip()) >= 3:
            prev = lines[i - 1].strip()
            if prev and not prev.startswith(("#", "|", "-", "*", ">", "<")) and len(prev) < 100:
                found.append((i - 1, 1 if line.startswith("=") else 2, clean(prev)))
    for m in re.finditer(r"(?is)<h([1-6])[^>]*>(.*?)</h\1>", text):
        found.append((text[: m.start()].count("\n"), int(m.group(1)), clean(m.group(2))))
    found.sort(key=lambda x: x[0])
    return [(lvl, t) for _, lvl, t in found if t]


def first_paragraph(text):
    """First prose line after the title, skipping badges, images, HTML, nav and quotes."""
    skip = ("[![", "![", "<", "[**", "|", ">", "#", "---", "===", "\`\`\`")
    lines = strip_fences(text).splitlines()
    start = 0
    for i, line in enumerate(lines[:60]):
        s = line.strip()
        if re.match(r"^#{1,2}\s", s) or re.match(r"^(=|-){3,}$", s) or re.match(r"(?i)^<h[12]", s):
            start = i + 1
            break
    in_html_heading = False
    for line in lines[start:]:
        s = line.strip()
        if re.match(r"(?i)^<h[1-6]", s):
            in_html_heading = not re.search(r"(?i)</h[1-6]>", s)
            continue
        if in_html_heading:
            in_html_heading = not re.search(r"(?i)</h[1-6]>", s)
            continue
        if not s or s.startswith(skip):
            continue
        return clean(s)
    return ""


def find_file(root, names, subdirs=("", ".github", "docs")):
    for sub in subdirs:
        base = root / sub if sub else root
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_file() and any(re.match(n, p.name, re.I) for n in names):
                return p
    return None


def git(root, *args):
    try:
        out = subprocess.run(["git", "-C", str(root)] + list(args), capture_output=True, text=True, timeout=20)
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def check_files(root, rep):
    required = [
        ("F-README", [r"README(\.md|\.rst)?$"], "README.md", ("",)),
        ("F-LICENSE", [r"(LICEN[SC]E|COPYING|UNLICENSE)"], "a LICENSE file (without one, others have no right to use or contribute to the code)", ("",)),
        ("F-CHANGELOG", [r"(CHANGELOG|HISTORY|CHANGES)"], "CHANGELOG.md", ("", "docs")),
    ]
    for code, pats, label, subs in required:
        if not find_file(root, pats, subs):
            rep.add("ERROR", code, f"Missing {label}")
    recommended = [
        ("F-CONTRIBUTING", [r"CONTRIBUTING"], "CONTRIBUTING.md"),
        ("F-SECURITY", [r"SECURITY"], "SECURITY.md (how to report vulnerabilities)"),
    ]
    for code, pats, label in recommended:
        if not find_file(root, pats):
            rep.add("WARN", code, f"Missing {label}")
    if not (root / ".gitignore").is_file():
        rep.add("WARN", "F-GITIGNORE", "Missing .gitignore")
    gh = root / ".github"
    if not (gh / "FUNDING.yml").is_file():
        rep.add("WARN", "F-FUNDING", "Missing .github/FUNDING.yml (Sponsor button)")
    tpl = gh / "ISSUE_TEMPLATE"
    if not (tpl.is_dir() and any(tpl.iterdir())):
        rep.add("WARN", "F-ISSUE-TEMPLATES", "Missing .github/ISSUE_TEMPLATE/ (bug report, feature request)")
    if not any((d / n).is_file() for d in (gh, root) for n in ("pull_request_template.md", "PULL_REQUEST_TEMPLATE.md")):
        rep.add("WARN", "F-PR-TEMPLATE", "Missing pull request template")
    wf = gh / "workflows"
    if not (wf.is_dir() and any(p.suffix in (".yml", ".yaml") for p in wf.iterdir())):
        rep.add("WARN", "F-CI", "Missing CI workflow in .github/workflows/")


def check_readme(root, rep):
    readme = find_file(root, [r"README(\.md|\.rst)?$"], ("",))
    if not readme:
        return None
    text = read(readme)
    hs = headings(text)
    if not any(lvl <= 2 for lvl, _ in hs):
        rep.add("WARN", "R-TITLE", "README has no title heading (a logo image alone is not searchable)")
    tagline = first_paragraph(text)
    if len(tagline) < 15:
        rep.add("WARN", "R-TAGLINE", "README needs a one-sentence description right under the title")
    elif len(tagline) > 220:
        rep.add("WARN", "R-TAGLINE", f"README opening line is {len(tagline)} chars; keep the one-liner under 220")
    htext = [t.lower() for _, t in hs]
    for code, pat, msg in SECTION_PATTERNS:
        if not any(re.search(pat, t) for t in htext):
            rep.add("WARN", "R-" + code.upper(), msg)
    body = strip_fences(text)
    for n, line in enumerate(body.splitlines(), 1):
        if PLACEHOLDER_RE.search(line):
            rep.add("WARN", "R-PLACEHOLDER", f"README line {n} contains a placeholder: {line.strip()[:60]}")
            break
    if STALE_LATEST_RE.search(body):
        rep.add("WARN", "R-STALE-VERSION", "README hard-codes a 'latest version' claim that will go stale; link to the releases page")
    broken = []
    for m in re.finditer(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)', body):
        target = m.group(1).strip("<>")
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.I):
            continue
        rel = unquote(target.split("#")[0].split("?")[0])
        if rel and not (root / rel).exists():
            broken.append(target)
    for t in sorted(set(broken))[:15]:
        rep.add("ERROR", "R-BROKEN-LINK", f"README relative link does not resolve: {t}")
    return text


def declared_versions(root):
    out = {}
    v = read(root / "VERSION").strip().splitlines()
    if v and re.fullmatch(SEMVER, v[0].strip().lstrip("v")):
        out["VERSION"] = v[0].strip().lstrip("v")
    pj = root / "package.json"
    if pj.is_file():
        try:
            ver = json.loads(read(pj)).get("version")
            if ver:
                out["package.json"] = str(ver)
        except ValueError:
            pass
    for name in ("pyproject.toml", "Cargo.toml"):
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', read(root / name))
        if m:
            out[name] = m.group(1)
    return out


def changelog_versions(text):
    vers = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^#{1,3}\s*\[?v?(" + SEMVER + r")\]?(?:\s|$|[—–(-])", line)
        if not m:
            m = re.match(r"^v?(" + SEMVER + r")(?:\s*\(.*\))?\s*$", line)
            if m and not (i + 1 < len(lines) and re.match(r"^(=|-){3,}\s*$", lines[i + 1])):
                m = None
        if m:
            vers.append(m.group(1))
    return vers


def check_versions(root, rep):
    cl = find_file(root, [r"(CHANGELOG|HISTORY|CHANGES)"], ("", "docs"))
    cl_text = read(cl) if cl else ""
    declared = declared_versions(root)
    if len(set(declared.values())) > 1:
        rep.add("ERROR", "V-MISMATCH", "Version files disagree: " + ", ".join(f"{k}={v}" for k, v in sorted(declared.items())))
    if not declared:
        rep.add("WARN", "V-NONE", "No machine-readable version found (VERSION, package.json, pyproject.toml or Cargo.toml)")
    if cl_text:
        vers = changelog_versions(cl_text)
        if not vers:
            rep.add("WARN", "C-NO-RELEASES", "CHANGELOG has no semantic-version release headings")
        elif declared and len(set(declared.values())) == 1 and vers[0] != next(iter(declared.values())):
            rep.add("WARN", "V-CHANGELOG", f"Declared version {next(iter(declared.values()))} differs from newest CHANGELOG release {vers[0]}")
        if not re.search(r"(?im)^\s*(?:#{1,3}\s*)?\[?unreleased\]?|^\s*tbd\b", cl_text):
            rep.add("WARN", "C-UNRELEASED", "CHANGELOG has no 'Unreleased' section for work in progress")
        if vers and not re.search(r"\d{4}-\d{2}-\d{2}", cl_text):
            rep.add("WARN", "C-DATES", "CHANGELOG releases carry no ISO dates (YYYY-MM-DD)")
    if declared and len(set(declared.values())) == 1:
        ver = next(iter(declared.values()))
        tags = set(git(root, "tag", "--list").split())
        if (root / ".git" / "shallow").exists():
            rep.add("INFO", "V-TAGS", "Shallow clone: tag check skipped")
        elif not tags:
            rep.add("INFO", "V-TAGS", "No git tags available locally (shallow clone, or no tags pushed yet)")
        elif ver not in tags and "v" + ver not in tags:
            rep.add("WARN", "V-TAG", f"No git tag v{ver} for the declared version (tag at release time, never move published tags)")


def check_metadata(root, rep):
    meta_path = root / ".github" / "repo-metadata.json"
    if not meta_path.is_file():
        rep.add("WARN", "M-MISSING", "Missing .github/repo-metadata.json (About description, topics, homepage)")
        return None
    try:
        meta = json.loads(read(meta_path))
    except ValueError as exc:
        rep.add("ERROR", "M-JSON", f"repo-metadata.json is not valid JSON: {exc}")
        return None
    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        rep.add("ERROR", "M-DESC", "repo-metadata.json needs a non-empty 'description'")
    elif len(desc) > 350:
        rep.add("ERROR", "M-DESC", f"description is {len(desc)} chars; GitHub's limit is 350")
    elif len(desc) > 160:
        rep.add("INFO", "M-DESC", f"description is {len(desc)} chars; 160 or fewer reads better in search results")
    topics = meta.get("topics")
    if not isinstance(topics, list) or not topics:
        rep.add("WARN", "M-TOPICS", "repo-metadata.json needs a 'topics' list (aim for 5-15)")
    else:
        bad = [t for t in topics if not isinstance(t, str) or not TOPIC_RE.match(t)]
        if bad:
            rep.add("ERROR", "M-TOPICS", f"Invalid topics (lowercase letters, digits, hyphens; max 50 chars): {bad}")
        if len(topics) > 20:
            rep.add("ERROR", "M-TOPICS", f"{len(topics)} topics; GitHub allows at most 20")
        elif len(topics) < 5:
            rep.add("INFO", "M-TOPICS", f"Only {len(topics)} topics; 5-15 helps discovery")
        if len(set(topics)) != len(topics):
            rep.add("WARN", "M-TOPICS", "Duplicate topics")
    return meta


def check_sponsor(root, rep, readme_text):
    fund = read(root / ".github" / "FUNDING.yml")
    keys = [ln for ln in fund.splitlines() if re.match(r"^[a-z_]+:\s*\S", ln)]
    if fund and not keys:
        rep.add("WARN", "S-EMPTY", ".github/FUNDING.yml has no active funding entries")
    m = re.search(r"(?m)^github:\s*\[?([^\]#\n]+)", fund)
    if m and len([x for x in m.group(1).split(",") if x.strip()]) > 4:
        rep.add("ERROR", "S-LIMIT", "FUNDING.yml lists more than 4 GitHub Sponsors usernames (GitHub's limit)")
    if keys and readme_text is not None and not any(
            re.search(SECTION_PATTERNS[5][1], t.lower()) for _, t in headings(readme_text)):
        rep.add("INFO", "S-README", "FUNDING.yml is set but README has no Sponsor / Support section")


def gh_commands(meta):
    cmd = ["gh", "repo", "edit"]
    if meta.get("description"):
        cmd += ["--description", meta["description"]]
    if meta.get("homepage"):
        cmd += ["--homepage", meta["homepage"]]
    for t in meta.get("topics", []):
        cmd += ["--add-topic", t]
    return " ".join(shlex.quote(c) for c in cmd)


def run(root):
    root = Path(root).resolve()
    rep = Report()
    check_files(root, rep)
    readme_text = check_readme(root, rep)
    check_versions(root, rep)
    meta = check_metadata(root, rep)
    check_sponsor(root, rep, readme_text)
    return rep, meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--strict", action="store_true", help="fail on warnings too")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--gh-commands", action="store_true",
                    help="print the 'gh repo edit' command that applies .github/repo-metadata.json")
    args = ap.parse_args(argv)
    if not Path(args.path).is_dir():
        print(f"not a directory: {args.path}", file=sys.stderr)
        return 2
    rep, meta = run(args.path)
    if args.gh_commands:
        if not meta:
            print("no valid .github/repo-metadata.json", file=sys.stderr)
            return 2
        print(gh_commands(meta))
        return 0
    if args.json:
        print(json.dumps({"items": rep.items, "errors": rep.count("ERROR"), "warnings": rep.count("WARN")}, indent=2))
    else:
        for level in ("ERROR", "WARN", "INFO"):
            for i in rep.items:
                if i["level"] == level:
                    print(f"{level:5} {i['code']:<18} {i['message']}")
        print(f"\n{rep.count('ERROR')} error(s), {rep.count('WARN')} warning(s), {rep.count('INFO')} info")
    failed = rep.count("ERROR") or (args.strict and rep.count("WARN"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
