from __future__ import annotations
import hashlib, zipfile, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=(ROOT/'VERSION').read_text().strip()
FILES=['orbit_cli.py','orbit_update_gui.py','installer.py','install_orbit_gui.pyw','README.md','VERSION','NEXT_VERSION','CHANGELOG.md','SECURITY.md','TODO-LAB-TEST.md','CAPABILITY-TEST.md',f'ORBIT-Claude-Desktop-v{VERSION}.mcpb']
FILES += sorted(p.relative_to(ROOT).as_posix() for d in ['source','tests','docs','scripts'] for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo'])
parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
missing=[p for p in FILES if not (ROOT/p).is_file()]
if missing:raise SystemExit(f'Missing: {missing}')
DEST=ROOT/'dist';DEST.mkdir(exist_ok=True);archive=DEST/f'ORBIT-Universal-Setup-v{VERSION}.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for relative in FILES:
  dest=f'orbit-universal-{VERSION}/{relative}'
  entry=zipfile.ZipInfo(dest,date_time=(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=0o644<<16
  z.writestr(entry,(ROOT/relative).read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
(DEST/(archive.name+'.sha256')).write_text(f'{digest}  {archive.name}\n')
with zipfile.ZipFile(archive) as z:
 names=z.namelist()
 assert len(names)==len(set(names))
 assert all(n.startswith(f'orbit-universal-{VERSION}/') and '..' not in Path(n).parts for n in names)
 assert len([n for n in names if n.endswith('source/runtime/orbit_mcp.py')])==1
print(f'{archive.name}: {len(names)} files; sha256={digest}')
