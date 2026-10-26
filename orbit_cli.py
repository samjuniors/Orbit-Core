"""Orbit install-once administration, audited host discovery and checksum-verified updates."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO='samjuniors/Orbit-Core-MCP'
VERS=re.compile(r'^[0-9]+\.[0-9]+\.[0-9]+$')
HOSTS=('antigravity','codex','claude-code','vscode')
def home():return Path(os.environ.get('ORBIT_SETUP_HOME') or Path.home()).expanduser().resolve()

def version():
    own=Path(__file__).resolve().parent/'VERSION'
    if own.is_file():return own.read_text(encoding='utf-8').strip()
    base=home()/'.orbit-universal'
    found=[x.name for x in base.iterdir() if x.is_dir() and VERS.fullmatch(x.name)] if base.is_dir() else []
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

def latest(channel='candidate'):
    """Select the highest published release in the opted-in channel.

    v0.x is published as prerelease by policy. Candidate is explicit to avoid
    claiming these are stable or silently switching a stable installation.
    """
    if channel not in {'stable','candidate'}:
        raise ValueError('Unknown update channel')
    data=json.loads(download('https://api.github.com/repos/'+REPO+'/releases?per_page=100',2_000_000))
    matched=[]
    for release in data:
        v=str(release.get('tag_name','')).removeprefix('v')
        if release.get('draft') or not VERS.fullmatch(v):continue
        if channel=='stable' and release.get('prerelease'):continue
        if channel=='candidate' and not release.get('prerelease'):continue
        assets={x['name']:x['browser_download_url'] for x in release.get('assets',[])
                if isinstance(x,dict) and isinstance(x.get('name'),str) and isinstance(x.get('browser_download_url'),str)}
        name='ORBIT-Universal-Setup-v'+v+'.zip'
        if name in assets and name+'.sha256' in assets:
            matched.append((tuple(map(int,v.split('.'))),{'version':v,'zip':assets[name],
                'sha':assets[name+'.sha256'],'url':release.get('html_url'),'channel':channel}))
    if matched:return max(matched,key=lambda x:x[0])[1]
    raise ValueError('No published '+channel+' release with verified ZIP and SHA256 asset')

def validate_zip(data,v):
    z=zipfile.ZipFile(io.BytesIO(data))
    root='orbit-universal-'+v+'/'
    names=z.infolist()
    if len(names)>400:raise ValueError('Too many archive entries')
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

def update(a):
    info=None
    if a.from_zip:
        path=Path(a.from_zip).expanduser().resolve(strict=True)
        if not path.is_file() or path.stat().st_size>64_000_000:raise ValueError('Invalid local ZIP')
        if not a.sha256 or not re.fullmatch('[0-9a-fA-F]{64}',a.sha256):
            raise ValueError('Local ZIP requires a separately trusted --sha256')
        raw=path.read_bytes();claimed=a.sha256
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            v=z.read(next(n for n in z.namelist() if re.fullmatch(r'orbit-universal-[0-9.]+/VERSION',n))).decode().strip()
    else:
        info=latest(a.channel);v=info['version'];print('Installed:',version(),'Available:',v,info['url'])
        if version()!='unknown' and tuple(map(int,v.split('.'))) <= tuple(map(int,version().split('.'))) and not a.force:
            print('No newer '+a.channel+' release.');return 0
        if a.check:return 0
        claimed=download(info['sha'],1024).decode('ascii').split()[0]
        raw=download(info['zip'],64_000_000)
    if not VERS.fullmatch(v):raise ValueError('Invalid SemVer')
    actual=hashlib.sha256(raw).hexdigest()
    if claimed.lower()!=actual or not re.fullmatch('[0-9a-fA-F]{64}',claimed):
        raise ValueError('SHA256 mismatch; no files installed')
    print('Verified release:',v,'SHA256:',actual)
    package=validate_zip(raw,v)
    if a.check:return 0
    with tempfile.TemporaryDirectory(prefix='orbit-upgrade-') as tmp:
        package.extractall(tmp)
        pkg=Path(tmp)/('orbit-universal-'+v)
        sys.path.insert(0,str(pkg))
        import installer
        if installer.VERSION!=v:raise ValueError('Installer version mismatch')
        hosts=a.hosts or [h['host'] for h in detect(a.project) if h['detected'] and h['host'] in installer.HOSTS]
        if not hosts:raise ValueError('No detected hosts: specify --hosts explicitly')
        scope='project' if a.project else 'machine'
        changes=installer.plan(a.project,hosts,scope)
        for c in changes:
            if c.action not in {'SKIP','PRESERVE'}:print(c.action,c.target)
        if not a.apply:
            print('PREVIEW ONLY: rerun with --apply to authorize versioned changes.');return 0
        written=installer.install(changes)
        print('Updated',len(written),'files/backups. Refresh selected MCP hosts.')
        return 0

def main(argv=None):
    p=argparse.ArgumentParser(prog='orbit')
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('status',help='Show installed Orbit version')
    d=sub.add_parser('detect',help='Read-only probable CLI/desktop host detection')
    d.add_argument('--project')
    u=sub.add_parser('update',help='Check verified releases; preview by default, apply explicitly')
    u.add_argument('--channel',choices=['candidate','stable'],default='candidate',
                   help='candidate for published 0.x prereleases (default), stable for production releases')
    u.add_argument('--check',action='store_true')
    u.add_argument('--apply',action='store_true')
    u.add_argument('--project')
    u.add_argument('--hosts',nargs='+',choices=HOSTS)
    u.add_argument('--from-zip')
    u.add_argument('--sha256')
    u.add_argument('--force',action='store_true')
    a=p.parse_args(argv)
    try:
        if a.command=='status':print('Orbit version:',version());return 0
        if a.command=='detect':print(json.dumps(detect(a.project),indent=2));return 0
        return update(a)
    except (OSError,ValueError,KeyError,zipfile.BadZipFile,StopIteration,ImportError) as exc:
        print('ORBIT UPDATE BLOCKED:',str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
