"""Opt-in, read-only GitHub release notices for the Orbit local stdio MCP.

Never downloads executables or invokes an installer. Live metadata checks run in
a daemon thread on MCP startup (at most once a day); user requests may refresh
explicitly. Results are only advisory. MCP clients decide how/when to display.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path

REPO = "samjuniors/Orbit-Core"
RELEASES = "https://api.github.com/repos/" + REPO + "/releases?per_page=100"
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
CHECK_INTERVAL_SECONDS = 24 * 60 * 60
MAX_RESPONSE = 2_000_000
_LOCK = threading.Lock()
_BACKGROUND_LOCK = threading.Lock()
_BACKGROUND_THREAD = None
_BACKGROUND_STOP = None
BACKGROUND_JOIN_TIMEOUT_SECONDS = 8.5


def _semver(s):
    if not isinstance(s, str) or not SEMVER.fullmatch(s):
        raise ValueError("Invalid release version")
    return tuple(int(v) for v in s.split("."))


def enabled():
    return os.environ.get("ORBIT_UPDATE_CHECK", "1").strip().lower() not in {"0", "false", "no", "off"}


def channel():
    value = os.environ.get("ORBIT_UPDATE_CHANNEL", "stable")
    return value if value in {"candidate", "stable"} else "stable"


def cache_path():
    base = Path(os.environ.get("ORBIT_UPDATE_HOME") or
                os.environ.get("ORBIT_SETUP_HOME") or Path.home()).expanduser()
    return base / ".orbit-universal" / "update-status.json"


def _read(path):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("checked_at"), (int, float)):
            return {}
        return data
    except (OSError, ValueError, UnicodeError, TypeError):
        return {}


def _save(path, value):
    # Reject redirected writes through symlinks under the known updater root.
    if path.is_symlink() or path.parent.is_symlink():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + str(os.getpid()) + ".new")
    if temp.exists() or temp.is_symlink():
        return
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True)
        temp.replace(path)
    except OSError:
        pass
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def _fetch():
    req = urllib.request.Request(
        RELEASES,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "Orbit-Core-Update-Metadata-Check"})
    with urllib.request.urlopen(req, timeout=8) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Update metadata requires HTTPS")
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("Release metadata too large")
    return json.loads(raw)


def _newest(releases, which):
    if not isinstance(releases, list):
        raise ValueError("Invalid GitHub releases response")
    matches = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        raw = release.get("tag_name", "")
        if not isinstance(raw, str):
            continue
        value = raw.removeprefix("v")
        try:
            number = _semver(value)
        except ValueError:
            continue
        if which == "stable" and release.get("prerelease"):
            continue
        if which == "candidate" and not release.get("prerelease"):
            continue
        assets = {asset.get("name") for asset in release.get("assets", [])
                  if isinstance(asset, dict)}
        package = "ORBIT-Universal-Setup-v" + value + ".zip"
        if package not in assets or package + ".sha256" not in assets:
            continue
        body = release.get("body") if isinstance(release.get("body"), str) else ""
        title = release.get("name") if isinstance(release.get("name"), str) else ""
        matches.append((number, value, title[:160], body[:1800]))
    if not matches:
        return None
    _, version, title, body = max(matches)
    return {"version": version,
            "title": title or ("Orbit v" + version),
            "whats_new": body or "No release notes provided. Review the official release page.",
            "notes_are_untrusted_display_text": True,
            "url": "https://github.com/" + REPO + "/releases/tag/v" + version}


def check_now(path=None, *, fetch=None, now=None, _cancel_event=None):
    """Read only *official published release metadata*; cache advisory result."""
    if not enabled():
        return {"status": "DISABLED"}
    if _cancel_event is not None and _cancel_event.is_set():
        return {"status": "CANCELLED"}
    location = Path(path) if path is not None else cache_path()
    clock = time.time() if now is None else now
    which = channel()
    getter = _fetch if fetch is None else fetch
    with _LOCK:
        try:
            latest = _newest(getter(), which)
            result = {"checked_at": clock, "channel": which, "latest": latest,
                      "status": "OK" if latest else "NO_PUBLISHED_RELEASE"}
        except (OSError, ValueError, TypeError, KeyError) as exc:
            result = {"checked_at": clock, "channel": which, "latest": None,
                      "status": "CHECK_FAILED", "reason": type(exc).__name__}
        if _cancel_event is not None:
            # Serialize the final cancellation check with shutdown's stop signal:
            # once shutdown sets the event, this worker cannot write the cache.
            with _BACKGROUND_LOCK:
                if _cancel_event.is_set():
                    return {"status": "CANCELLED"}
                _save(location, result)
        else:
            _save(location, result)
        return result


def notice(installed_version, path=None, *, now=None):
    """Report cached version status immediately; never contacts the network."""
    if not enabled():
        return {"status": "DISABLED", "automatic_checks": False}
    state = _read(Path(path) if path is not None else cache_path())
    result = {"status": "NOT_CHECKED", "automatic_checks": True,
              "channel": channel(), "installed_version": installed_version,
              "install_requires_explicit_user_action": True}
    if not state or state.get("channel") != result["channel"]:
        return result
    result["last_checked"] = state["checked_at"]
    clock = time.time() if now is None else now
    result["cache_stale"] = clock - state["checked_at"] > CHECK_INTERVAL_SECONDS
    if state.get("status") == "CHECK_FAILED":
        result["status"] = "CHECK_FAILED"
        return result
    latest = state.get("latest")
    if not isinstance(latest, dict) or not SEMVER.fullmatch(str(latest.get("version", ""))):
        result["status"] = "NO_PUBLISHED_RELEASE"
        return result
    remote = latest["version"]
    result["latest_published"] = remote
    try:
        newer = _semver(remote) > _semver(installed_version)
    except ValueError:
        result["status"] = "UNKNOWN_INSTALLED_VERSION"
        return result
    result["status"] = "UPDATE_AVAILABLE" if newer else "UP_TO_DATE"
    if newer:
        result["message"] = ("Orbit v" + remote + " is published. An update is available. "
                             "Ask the user whether to update; do not invoke an installer "
                             "from a model tool call.")
        result["release_url"] = "https://github.com/" + REPO + "/releases/tag/v" + remote
        result["whats_new"] = str(latest.get("whats_new") or
                                 "No release notes provided; review the official release page.")[:1800]
        result["release_title"] = str(latest.get("title") or "Orbit update")[:160]
        result["notes_are_untrusted_display_text"] = True
        result["action"] = "Open the installed Orbit Update Manager: orbit manager"
        result["limitations"] = ("MCP tools cannot show a native click-to-update "
                                 "button in every IDE. The local manager requests "
                                 "the user's approval and does not guarantee code-signing.")
    return result


def _background_worker(path, stop_event):
    check_now(path, _cancel_event=stop_event)


def start_background_check():
    """Start one cancellable metadata-only startup check per local install."""
    global _BACKGROUND_THREAD, _BACKGROUND_STOP
    if not enabled():
        return False
    path = cache_path()
    state = _read(path)
    if state.get("channel") == channel() and isinstance(state.get("checked_at"), (int, float)):
        age = time.time() - state["checked_at"]
        if 0 <= age < CHECK_INTERVAL_SECONDS:
            return False
    with _BACKGROUND_LOCK:
        if _BACKGROUND_THREAD is not None and _BACKGROUND_THREAD.is_alive():
            return False
        stop_event = threading.Event()
        worker = threading.Thread(
            target=_background_worker, args=(path, stop_event),
            daemon=True, name="orbit-release-metadata-check")
        _BACKGROUND_THREAD = worker
        _BACKGROUND_STOP = stop_event
        try:
            worker.start()
        except Exception:
            _BACKGROUND_THREAD = None
            _BACKGROUND_STOP = None
            raise
    return True


def shutdown_background_check(timeout=BACKGROUND_JOIN_TIMEOUT_SECONDS):
    """Cancel the startup check and join it for a bounded time.

    Returns False only when the underlying network operation outlives the join
    deadline. Even then, the cancellation guard prevents a late cache write.
    """
    global _BACKGROUND_THREAD, _BACKGROUND_STOP
    with _BACKGROUND_LOCK:
        worker = _BACKGROUND_THREAD
        stop_event = _BACKGROUND_STOP
        if worker is None:
            return True
        if stop_event is not None:
            stop_event.set()
    worker.join(timeout=max(0.0, float(timeout)))
    stopped = not worker.is_alive()
    if stopped:
        with _BACKGROUND_LOCK:
            if _BACKGROUND_THREAD is worker:
                _BACKGROUND_THREAD = None
                _BACKGROUND_STOP = None
    return stopped
