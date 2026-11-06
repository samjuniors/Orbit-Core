"""Orbit install-once administration, audited host discovery and checksum-verified updates."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO='samjuniors/Orbit-Core'
RELEASE_ARCHIVE_URL='https://github.com/'+REPO+'/releases'
VERS=re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
HOSTS=('antigravity','codex','claude-code','vscode')
def home():return Path(os.environ.get('ORBIT_SETUP_HOME') or Path.home()).expanduser().resolve()

def version():
    # Development/source checkout VERSION is NOT evidence of installed software.
    # The per-user immutable versioned runtime inventory survives source cleanup.
    base=home()/'.orbit-universal'
    found=[x.name for x in base.iterdir()
           if x.is_dir() and not x.is_symlink() and VERS.fullmatch(x.name)
           and (x/'orbit_mcp.py').is_file() and not (x/'orbit_mcp.py').is_symlink()] if base.is_dir() else []
    return max(found,key=lambda s:tuple(map(int,s.split('.')))) if found else 'unknown'

def detect(project=None):
    h=home(); p=Path(project).expanduser().resolve() if project else None
    locations={
      'antigravity':[h/'.gemini/config/mcp_config.json']+([p/'.agents/mcp_config.json'] if p else []),
      'codex':[h/'.codex/config.toml']+([p/'.codex/config.toml'] if p else []),
      'claude-code':[h/'.claude.json']+([p/'.mcp.json'] if p else []),
      'vscode':[Path(os.environ.get('APPDATA',h/'AppData/Roaming'))/'Code/User/mcp.json',
                h/'.config/Code/User/mcp.json']+([p/'.vscode/mcp.json'] if p else [])}
    result=[]
    for k,names in [('antigravity',['antigravity']),('codex',['codex']),('claude-code',['claude']),('vscode',['code'])]:
        executable=next((shutil.which(s) for s in names if shutil.which(s)),None)
        configs=[str(f) for f in locations[k] if f.is_file() and not f.is_symlink()]
        result.append({'host':k,'detected':bool(executable or configs),'cli':executable,
                       'configuration_files':configs,'connected':'NOT_VERIFIED',
                       'note':'Presence is not proof of a connected desktop session.'})
    return result

def download(url,limit):
    # GitHub release API and release assets only. TLS is validated by urllib.
    if not url.startswith('https://') or not any(url.startswith(x) for x in
        ('https://api.github.com/','https://github.com/')):
        raise ValueError('Only official HTTPS GitHub release URLs allowed')
    request=urllib.request.Request(url,headers={'User-Agent':'Orbit-Updater/0.24'})
    with urllib.request.urlopen(request,timeout=20) as response:
        if not response.geturl().startswith('https://'):
            raise ValueError('HTTPS redirect required')
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Update asset exceeds byte limit')
        return data

def published_release(channel='stable', requested_version=None):
    """Select an exact, already published version or the newest channel release.

    A requested version must be on the selected channel; unpublished tags,
    drafts and source branches are ineligible. No release code is executed.
    """
    if channel not in {'stable','candidate'}:
        raise ValueError('Unknown update channel')
    if requested_version is not None and not VERS.fullmatch(requested_version):
        raise ValueError('Expected a version in X.Y.Z form')
    data=json.loads(download('https://api.github.com/repos/'+REPO+'/releases?per_page=100',2_000_000))
    if not isinstance(data,list):
        raise ValueError('Unexpected release list; no installation performed')
    matched=[]
    for release in data:
        if not isinstance(release,dict):
            continue
        v=str(release.get('tag_name','')).removeprefix('v')
        if release.get('draft') or not VERS.fullmatch(v):
            continue
        if channel=='stable' and release.get('prerelease'):
            continue
        if channel=='candidate' and not release.get('prerelease'):
            continue
        if requested_version is not None and requested_version!=v:
            continue
        assets={x['name']:x['browser_download_url'] for x in release.get('assets',[])
                if isinstance(x,dict) and isinstance(x.get('name'),str) and isinstance(x.get('browser_download_url'),str)}
        name='ORBIT-Universal-Setup-v'+v+'.zip'
        if name in assets and name+'.sha256' in assets:
            matched.append((tuple(map(int,v.split('.'))),{'version':v,'zip':assets[name],
                'sha':assets[name+'.sha256'],'url':release.get('html_url'),'channel':channel,
                'release_name':str(release.get('name') or ('Orbit v'+v))[:160],
                'release_notes':str(release.get('body') or '')[:6000]}))
    if matched:
        return max(matched,key=lambda x:x[0])[1]
    if requested_version is not None:
        raise ValueError('v'+requested_version+' is not a published '+channel+
                         ' release with a Universal ZIP and SHA256 sidecar')
    raise ValueError('No published '+channel+' release with Universal ZIP and SHA256 sidecar')


def latest(channel='stable'):
    return published_release(channel)



def display_release_notes(info, limit=3000):
    """Display only: cleanse terminal control characters and bound published notes."""
    raw = info.get('release_notes') if isinstance(info,dict) else None
    if not isinstance(raw,str) or not raw.strip():
        return 'No release notes supplied. Review the official release page before updating.'
    clean = ''.join(ch if ch in '\n\t' or ch.isprintable() else ' ' for ch in raw)
    return clean[:limit].strip()


def validate_zip(data,v):
    z=zipfile.ZipFile(io.BytesIO(data))
    root='orbit-universal-'+v+'/'
    names=z.infolist()
    if len(names)>400:raise ValueError('Too many archive entries')
    if len(set(x.filename for x in names))!=len(names):raise ValueError('Duplicate ZIP members forbidden')
    total=0
    for item in names:
        name=item.filename
        if not name.startswith(root) or name.startswith('/') or '\\' in name or '..' in Path(name).parts:
            raise ValueError('Unsafe ZIP member path')
        if ((item.external_attr>>16)&0o170000)==0o120000:raise ValueError('ZIP symlink forbidden')
        total+=item.file_size
        if total>100_000_000:raise ValueError('ZIP uncompressed limit exceeded')
    if z.read(root+'VERSION').decode().strip()!=v or root+'installer.py' not in z.namelist():
        raise ValueError('Installer VERSION mismatch')
    return z

def _read_verified_release(a, info=None):
    """Return (version, checked ZIP) without executing a downloaded installer."""
    if a.from_zip:
        path=Path(a.from_zip).expanduser().resolve(strict=True)
        if not path.is_file() or path.stat().st_size>64_000_000:
            raise ValueError('Invalid local ZIP')
        if not a.sha256 or not re.fullmatch('[0-9a-fA-F]{64}',a.sha256):
            raise ValueError('Local ZIP requires a separately trusted --sha256')
        raw=path.read_bytes()
        claimed=a.sha256
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[n for n in z.namelist() if re.fullmatch(r'orbit-universal-[0-9.]+/VERSION',n)]
            if len(names)!=1:
                raise ValueError('Expected exactly one Universal Setup VERSION')
            v=z.read(names[0]).decode('utf-8').strip()
        if a.version and v!=a.version:
            raise ValueError('Local archive does not match requested --version')
    else:
        if info is None:
            info=published_release(a.channel,a.version) if a.version else latest(a.channel)
        v=info['version']
        claimed=download(info['sha'],1024).decode('ascii').split()[0]
        raw=download(info['zip'],64_000_000)
    if not VERS.fullmatch(v):
        raise ValueError('Invalid SemVer')
    if a.expect_version and a.expect_version!=v:
        raise ValueError('Archive does not match pinned expected release version')
    actual=hashlib.sha256(raw).hexdigest()
    if not re.fullmatch('[0-9a-fA-F]{64}',claimed) or claimed.lower()!=actual:
        raise ValueError('SHA256 mismatch; no files installed or removed')
    package=validate_zip(raw,v)
    print('Verified published/local archive: v'+v,'SHA256:',actual)
    return v,package


def _chosen_hosts(a):
    hosts=a.hosts or [h['host'] for h in detect(a.project) if h['detected'] and h['host'] in HOSTS]
    if not hosts:
        raise ValueError('No detected hosts; specify --hosts explicitly')
    return hosts


def _scope(a):
    if a.scope=='project' and not a.project:
        raise ValueError('--scope project requires --project with the absolute existing project folder')
    if a.scope=='machine' and a.project:
        raise ValueError('--project is allowed only with --scope project')
    return a.scope


def update(a):
    """Install/update only from a published, checksum-checked release or trusted ZIP."""
    scope=_scope(a)
    info=None
    if not a.from_zip:
        info=published_release(a.channel,a.version) if a.version else latest(a.channel)
        v=info['version']
        print('Installed:',version(),'Published:',v,info['url'])
        print("WHAT'S NEW (publisher's release description; informational only):")
        print(display_release_notes(info,limit=2000))
        if a.expect_version and v!=a.expect_version:
            raise ValueError('Published release changed since approval; check again')
        current=version()
        if current!='unknown' and not VERS.fullmatch(current):
            raise ValueError('Unknown installed version; review manually')
        if current!='unknown' and a.command=='update' and not a.force:
            desired=tuple(map(int,v.split('.')))
            existing=tuple(map(int,current.split('.')))
            if desired<existing:
                raise ValueError('Refusing automatic downgrade; review compatibility and use --force explicitly')
            if desired==existing:
                print('No newer '+a.channel+' release. Use install to add another host or --force to repair.')
                return 0
        if a.check:
            return 0
    else:
        if a.check:
            raise ValueError('--check does not support local ZIPs; use a no-apply preview')
    v,package=_read_verified_release(a,info)
    hosts=_chosen_hosts(a)
    if not a.from_zip and version()!='unknown' and VERS.fullmatch(version()):
        if tuple(map(int,v.split('.')))<tuple(map(int,version().split('.'))) and not a.force:
            raise ValueError('Refusing downgrade without explicit --force and data compatibility review')
    if not a.apply:
        print('PREVIEW ONLY: checked archive contents; selected hosts:',', '.join(hosts))
        print('Scope:',scope,'Project:',a.project or '(current OS user)')
        print('No downloaded installer code imported or run. Exact host file plan is computed after --apply.')
        print('No automatic Python/IDE installation, host restart, memory removal or code execution.')
        print('SHA256 proves ZIP integrity against the published checksum, not signing/provenance.')
        return 0
    with tempfile.TemporaryDirectory(prefix='orbit-upgrade-') as tmp:
        package.extractall(tmp)
        pkg=Path(tmp)/('orbit-universal-'+v)
        import importlib.util
        spec=importlib.util.spec_from_file_location('_orbit_release_installer_'+v.replace('.','_'),str(pkg/'installer.py'))
        if spec is None or spec.loader is None:
            raise ValueError('Archive installer could not be loaded')
        release_installer=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=release_installer
        try:
            spec.loader.exec_module(release_installer)
        finally:
            sys.modules.pop(spec.name,None)
        if release_installer.VERSION!=v:
            raise ValueError('Installer version mismatch')
        if any(h not in release_installer.HOSTS for h in hosts):
            raise ValueError('Archive does not support selected hosts')
        changes=release_installer.plan(a.project if scope=='project' else None,hosts,scope)
        for c in changes:
            if c.action not in {'SKIP','PRESERVE'}:
                print(c.action,c.target)
        if any(c.action=='PRESERVE' for c in changes):
            print('Customized files were preserved. Review warnings before relying on the installation.')
        written=release_installer.install(changes)
        print('Applied',len(written),'files/backups from v'+v+'. Restart the selected MCP hosts.')
        return 0


def uninstall(a):
    """Use the exact selected published version's safe, scoped uninstaller."""
    scope=_scope(a)
    info=None
    if not a.from_zip:
        installed=version()
        wanted=a.version or installed
        if not VERS.fullmatch(wanted):
            raise ValueError('Cannot determine installed release; specify --version')
        if a.version and installed!='unknown' and wanted!=installed and not a.force:
            raise ValueError('Selected release differs from detected installed version; review and use --force')
        info=published_release(a.channel,wanted)
        if a.expect_version and info['version']!=a.expect_version:
            raise ValueError('Published release changed since approval')
    v,package=_read_verified_release(a,info)
    hosts=_chosen_hosts(a)
    root='orbit-universal-'+v+'/'
    if root+'orbit_setup.py' not in package.namelist():
        raise ValueError('Published release lacks the unified safe uninstaller')
    if not a.apply:
        print('PREVIEW ONLY: release v'+v+', hosts:',', '.join(hosts))
        print('Scope:',scope,'Project:',a.project or '(current OS user)')
        print('No package code was run; to inspect the exact removals before authorizing,')
        print('extract the verified Universal Setup ZIP and run orbit_setup.py uninstall without --apply.')
        print('Shared runtimes, other MCP registrations and saved project memory are preserved.')
        return 0
    with tempfile.TemporaryDirectory(prefix='orbit-uninstall-') as tmp:
        package.extractall(tmp)
        pkg=Path(tmp)/root
        command=[sys.executable,str(pkg/'orbit_setup.py'),'uninstall',
                 '--scope',scope,'--hosts',*hosts]
        if scope=='project':
            command+=['--project',a.project]
        command+=['--apply']
        print('Authorizing selected released uninstaller v'+v+' for',', '.join(hosts))
        result=subprocess.run(command,check=False)
        if result.returncode:
            raise ValueError('Released uninstaller failed with exit code '+str(result.returncode))
        print('Uninstall completed for selected host integrations; shared runtime and project memory retained.')
        return 0



def doctor(project=None):
    """Local read-only preflight; host must separately prove MCP connection."""
    base=home()/'.orbit-universal'
    v=version()
    runtime=base/v/'orbit_mcp.py'
    report={'installed_version':v,
            'runtime_exists':runtime.is_file() and not runtime.is_symlink(),
            'python':sys.executable,'hosts':detect(project),
            'playwright_importable':False,
            'note':'Configured is not the same as connected. Test orbit_project_scan in the host.',
            'next':'Refresh your MCP host and inspect actual Orbit tools.'}
    try:
        import importlib.util
        report['playwright_importable']=importlib.util.find_spec('playwright') is not None
    except (ImportError,ValueError):
        pass
    print(json.dumps(report,indent=2))
    return 0 if report['runtime_exists'] else 1


def main(argv=None):
    p=argparse.ArgumentParser(prog='orbit')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status',help='Show detected installed Orbit version')
    sub.add_parser('manager',help='Open the optional approval-based Orbit Update Manager GUI')
    sub.add_parser('versions',help='Show the official archive of previous Orbit versions')
    check=sub.add_parser('doctor',help='Read-only installation and host diagnostic')
    check.add_argument('--project')
    d=sub.add_parser('detect',help='Read-only probable CLI/desktop host detection')
    d.add_argument('--project')
    for name,help_text in (
        ('install','Install a selected published release into one or more IDE/CLI hosts'),
        ('update','Check or update from a published release (preview by default)'),
        ('uninstall','Remove selected host integrations using the matching released uninstaller')):
        parser=sub.add_parser(name,help=help_text)
        parser.add_argument('--channel',choices=['stable','candidate'],default='stable',
                            help='Stable published releases by default; candidate is opt-in')
        parser.add_argument('--version',help='Exact already-published X.Y.Z version; no development branch downloads')
        parser.add_argument('--check',action='store_true',help='Check release metadata only (install/update)')
        parser.add_argument('--apply',action='store_true',help='Authorize confirmed downloaded release code execution')
        parser.add_argument('--scope',choices=['machine','project'],default='machine',
                            help='machine=current OS user; project=one existing project')
        parser.add_argument('--project',help='Absolute existing project directory when --scope project')
        parser.add_argument('--hosts',nargs='+',choices=HOSTS)
        parser.add_argument('--from-zip',help='Offline/owner-reviewed Universal Setup ZIP')
        parser.add_argument('--sha256',help='Trusted SHA256 of the optional local ZIP')
        parser.add_argument('--force',action='store_true',
                            help='Explicit compatibility review for older/same-version repair')
        parser.add_argument('--expect-version',help='Pin the version shown during an earlier check')
    a=p.parse_args(argv)
    try:
        if a.command=='status':
            print('Orbit version:',version())
            print('This is local installation inventory, not proof of an active IDE connection.')
            return 0
        if a.command=='versions':
            print('Published Orbit versions (latest first):',RELEASE_ARCHIVE_URL)
            print('Older versions can be reviewed manually; no downgrade performed.')
            return 0
        if a.command=='manager':
            import orbit_update_gui
            orbit_update_gui.launch()
            return 0
        if a.command=='detect':
            print(json.dumps(detect(a.project),indent=2))
            return 0
        if a.command=='doctor':
            return doctor(a.project)
        if a.command=='uninstall':
            if a.check:
                raise ValueError('Uninstall has no --check; run a no-apply preview')
            return uninstall(a)
        return update(a)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,StopIteration,ImportError) as exc:
        print('ORBIT RELEASE ACTION BLOCKED:',str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
