"""Refresh the candidate desktop bundle from canonical runtime source.

The tracked bundle owns desktop manifest metadata; runtime code always comes
from source/runtime. This does not install, publish, or tag a release.
"""
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()
target = ROOT / f'ORBIT-Claude-Desktop-v{VERSION}.mcpb'
with zipfile.ZipFile(target) as previous:
    manifest = previous.read('manifest.json')
if json.loads(manifest)['version'] != VERSION:
    raise SystemExit('Desktop manifest version differs from VERSION')
temporary = target.with_suffix('.mcpb.tmp')
try:
    with zipfile.ZipFile(temporary, 'w') as bundle:
        entries = [('manifest.json', manifest)]
        entries += [(f'server/{p.name}', p.read_bytes())
                    for p in sorted((ROOT / 'source/runtime').glob('*.py'))]
        for name, data in entries:
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.external_attr = 0o644 << 16
            bundle.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED,
                            compresslevel=9)
    temporary.replace(target)
finally:
    temporary.unlink(missing_ok=True)
print(f'Rebuilt {target.name} from source/runtime')
