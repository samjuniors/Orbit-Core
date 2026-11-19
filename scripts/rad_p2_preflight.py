"""RAD P2 read-only AppContainer readiness preflight.

No profile provisioning, ACL changes, credential access, process launch or
host settings changes. Always returns a HOLD until independent OS sandbox
acceptance and host owner approval exist; never a permission grant.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import sys

# This is a read-only diagnostic: importing runtime modules must not create
# __pycache__ files or change anything in the user's checkout.
sys.dont_write_bytecode = True
RUNTIME = Path(__file__).resolve().parents[1] / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))


def inspect(project_root: str) -> dict:
    report = {
        "status": "HOLD_OS_ISOLATION_NOT_VERIFIED",
        "read_only": True,
        "execution_allowed": False,
        "profile_created": False,
        "acl_modified": False,
        "real_lpac_execution_verified": False,
        "filesystem_denial_verified": False,
        "network_denial_verified": False,
        "host_permission_verified": False,
    }
    raw = Path(project_root).expanduser()
    if not raw.is_absolute() or raw.is_symlink():
        report["reason"] = "An existing absolute, non-symlink project root is required"
        return report
    try:
        root = raw.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor) or root == Path.home().resolve():
            report["reason"] = "The path must identify a specific project directory"
            return report
    except (OSError, ValueError, RuntimeError):
        report["reason"] = "Project root could not be validated"
        return report

    import orbit_preview
    profile, hold = orbit_preview.isolated_profile_for(root)
    if hold is not None or profile is None:
        report["reason"] = "Host-owned required isolation/profile mapping is absent or invalid"
        return report
    report["host_profile_binding_verified"] = True
    if os.name != "nt":
        report["reason"] = "The Windows AppContainer adapter is not available on this host"
        return report

    try:
        import orbit_appcontainer as app
        sid = ctypes.c_void_p()
        hr = app._userenv.DeriveAppContainerSidFromAppContainerName(
            profile, ctypes.byref(sid))
        if hr != 0 or not sid.value:
            report["reason"] = "Host profile SID could not be derived"
            return report
        try:
            app._require_registered_profile(sid)
            report["read_only_profile_probe"] = "PROFILE_PATH_FOUND"
            report["reason"] = (
                "A profile folder was located, but actual LPAC enforcement, "
                "filesystem/network denial and host permission have NOT been tested")
        finally:
            app._adv.FreeSid(sid)
    except (OSError, ImportError, PermissionError, AttributeError, ValueError):
        report["reason"] = "Registered profile could not be confirmed by a read-only OS probe"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Orbit RAD P2 preflight; never provisions or approves execution")
    parser.add_argument("--project-root", required=True,
                        help="Existing disposable project root, absolute path")
    args = parser.parse_args(argv)
    print(json.dumps(inspect(args.project_root), sort_keys=True))
    return 2  # HOLD is never silently converted into release acceptance


if __name__ == "__main__":
    raise SystemExit(main())
