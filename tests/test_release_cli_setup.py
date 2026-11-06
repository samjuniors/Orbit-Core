"""Published-release install/update/uninstall CLI safety regression tests.

All remote metadata and archive bytes are mocked. No Internet, user host
configuration, installed runtime or project memory may be modified.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import orbit_cli
import installer


class ReleaseCliTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="orbit-release-cli-")
        self.addCleanup(temp.cleanup)
        self.temp=Path(temp.name)
        self.home=self.temp/"home"
        self.home.mkdir()
        self.marker=self.temp/"executed.txt"
        old=os.environ.get("ORBIT_SETUP_HOME")
        os.environ["ORBIT_SETUP_HOME"]=str(self.home)
        self.addCleanup(lambda: os.environ.pop("ORBIT_SETUP_HOME",None)
                        if old is None else os.environ.__setitem__("ORBIT_SETUP_HOME",old))

    def archive(self,version="0.31.0"):
        prefix="orbit-universal-"+version+"/"
        payload=io.BytesIO()
        script="""from pathlib import Path
import json,sys
Path({marker!r}).write_text(json.dumps(sys.argv[1:]),encoding='utf-8')
""".format(marker=str(self.marker))
        installer="""VERSION={version!r}
HOSTS=('antigravity','codex')
def plan(project,hosts,scope):
    from pathlib import Path
    return [type('Change',(),{{'action':'CREATE','target':Path({marker!r})}})()]
def install(changes):
    from pathlib import Path
    Path({marker!r}).write_text('APPLIED')
    return [str(changes[0].target)]
""".format(version=version,marker=str(self.marker))
        with zipfile.ZipFile(payload,"w") as z:
            z.writestr(prefix+"VERSION",version)
            z.writestr(prefix+"installer.py",installer)
            z.writestr(prefix+"orbit_setup.py",script)
        return payload.getvalue()

    @staticmethod
    def release(v,pre=False,draft=False,assets=True):
        name="ORBIT-Universal-Setup-v"+v+".zip"
        base="https://github.com/samjuniors/Orbit-Core/releases/download/v"+v+"/"
        return {"tag_name":"v"+v,"draft":draft,"prerelease":pre,
                "assets":[{"name":x,"browser_download_url":base+x}
                          for x in (name,name+".sha256")] if assets else [],
                "html_url":base}

    def test_real_published_stock_updater_hashes_are_whitelisted(self):
        # Exact source/tag SHA256 digests were computed from immutable
        # v0.26.0-v0.30.0 GitHub tags, including Windows CRLF. No wildcard
        # or user-modified bytes are eligible for automatic upgrades.
        known={
            "1e704136cf1cc7a7635c70a47f031b8920de585335e5037440ab6c436b4b5319",
            "e0cc8d6962fe8c6d8b06900d237bd51437aa0af5a6254ef6e22343d4dd289e99",
            "c9c9ac90e2eb60e7cd91b975786deb9a06270deca5f28186c412a37f77775f0b",
            "bde59e3bbe62976c1d1d6904459ffe3798946678311b1399eba2bb189448d524",
            "b82796f88aeac5eff826573d43389af16a4c4aff20bf794c8052e82f80fa789f",
            "228da78ad32c36d15de0152ae8385d6db25221c695f40755e3f1b27ad024c698",
        }
        self.assertTrue(known.issubset(installer.OLD_STOCK_SHA256))
        # Still refuse arbitrary owner-edited content.
        dest=self.temp/"owner-orbit-cli.py"
        dest.write_bytes(b"# owner custom Orbit launcher - must preserve")
        with self.assertRaises(installer.SetupError):
            installer.same_or_create([],dest,(ROOT/"orbit_cli.py").read_bytes(),None,"CLI updater")
        self.assertEqual(dest.read_bytes(),b"# owner custom Orbit launcher - must preserve")

    def test_source_checkout_version_not_falsely_installed(self):
        self.assertEqual(orbit_cli.version(),"unknown")
        runtime=self.home/".orbit-universal"/"0.30.0"
        runtime.mkdir(parents=True)
        (runtime/"orbit_mcp.py").write_text("# synthetic")
        self.assertEqual(orbit_cli.version(),"0.30.0")

    def test_exact_release_channel_is_required_and_draft_denied(self):
        source=[self.release("0.29.0"),self.release("0.30.0"),
                self.release("0.31.0",True),self.release("0.32.0",draft=True),
                self.release("0.33.0",assets=False)]
        with patch.object(orbit_cli,"download",return_value=json.dumps(source).encode()):
            self.assertEqual(orbit_cli.latest()["version"],"0.30.0")
            self.assertEqual(orbit_cli.published_release("stable","0.29.0")["version"],"0.29.0")
            self.assertEqual(orbit_cli.published_release("candidate","0.31.0")["version"],"0.31.0")
            for wanted in ("0.31.0","0.32.0","0.33.0"):
                with self.subTest(wanted=wanted),self.assertRaises(ValueError):
                    orbit_cli.published_release("stable",wanted)

    def test_install_preview_does_not_execute_downloaded_code(self):
        data=self.archive()
        zipfile_path=self.temp/"official.zip"
        zipfile_path.write_bytes(data)
        args=["install","--version","0.31.0","--from-zip",str(zipfile_path),
              "--sha256",hashlib.sha256(data).hexdigest(),
              "--hosts","antigravity","codex"]
        self.assertEqual(orbit_cli.main(args),0)
        self.assertFalse(self.marker.exists())
        self.assertFalse((self.home/".orbit-universal").exists())
        self.assertEqual(orbit_cli.main(args+["--apply"]),0)
        self.assertEqual(self.marker.read_text(),"APPLIED")

    def test_pinned_version_rejects_mismatching_archive(self):
        data=self.archive()
        path=self.temp/"candidate.zip"
        path.write_bytes(data)
        args=["install","--version","0.30.0","--from-zip",str(path),
              "--sha256",hashlib.sha256(data).hexdigest(),"--hosts","codex","--apply"]
        self.assertEqual(orbit_cli.main(args),1)
        self.assertFalse(self.marker.exists())

    def test_published_uninstall_preview_is_read_only_and_apply_scoped(self):
        data=self.archive("0.31.0")
        info={"version":"0.31.0","zip":"https://github.com/samjuniors/Orbit-Core/asset",
              "sha":"https://github.com/samjuniors/Orbit-Core/digest",
              "url":"https://github.com/samjuniors/Orbit-Core/releases/tag/v0.31.0"}
        def fake_download(url,limit):
            return (hashlib.sha256(data).hexdigest()+"  archive.zip\n").encode() if url==info["sha"] else data
        args=["uninstall","--version","0.31.0","--hosts","antigravity","codex",
              "--scope","project","--project",str(self.temp)]
        with patch.object(orbit_cli,"published_release",return_value=info),             patch.object(orbit_cli,"download",side_effect=fake_download):
            self.assertEqual(orbit_cli.main(args),0)
            self.assertFalse(self.marker.exists())
            self.assertEqual(orbit_cli.main(args+["--apply"]),0)
        supplied=json.loads(self.marker.read_text())
        self.assertEqual(supplied[0:2],["uninstall","--scope"])
        self.assertIn("antigravity",supplied)
        self.assertIn("codex",supplied)
        self.assertIn(str(self.temp),supplied)
        self.assertIn("--apply",supplied)

    def test_selected_older_release_fails_closed_without_force(self):
        runtime=self.home/".orbit-universal"/"0.31.0"
        runtime.mkdir(parents=True)
        (runtime/"orbit_mcp.py").write_text("# synthetic")
        info={"version":"0.30.0","url":"https://github.com/example","release_notes":"test"}
        with patch.object(orbit_cli,"published_release",return_value=info):
            self.assertEqual(orbit_cli.main(["update","--version","0.30.0",
                                            "--hosts","codex"]),1)
        self.assertFalse(self.marker.exists())

    def test_project_scope_requires_project_and_preserves_home(self):
        self.assertEqual(orbit_cli.main(["install","--scope","project",
                                        "--hosts","codex"]),1)
        self.assertFalse(self.marker.exists())

    def test_duplicate_zip_member_is_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            for _ in range(2):
                z.writestr("orbit-universal-0.31.0/VERSION","0.31.0")
            z.writestr("orbit-universal-0.31.0/installer.py","pass")
        with self.assertRaises(ValueError):
            orbit_cli.validate_zip(b.getvalue(),"0.31.0")

    def test_offline_uninstall_preview_requires_trusted_checksum(self):
        data=self.archive()
        path=self.temp/"official.zip"
        path.write_bytes(data)
        self.assertEqual(orbit_cli.main(["uninstall","--from-zip",str(path),
                                        "--hosts","codex"]),1)
        self.assertFalse(self.marker.exists())


if __name__=="__main__":
    unittest.main()
