from pathlib import Path
import ast, re, sys
root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
if not re.fullmatch(r'\d+\.\d+\.\d+', version):sys.exit('Invalid SemVer')
for rel in ('installer.py','source/runtime/orbit_mcp.py'):
 text=(root/rel).read_text(encoding='utf-8')
 m=re.search(r'^VERSION\s*=\s*[\"\'](\d+\.\d+\.\d+)[\"\']',text,re.M)
 if not m or m.group(1)!=version:sys.exit(f'{rel}: VERSION mismatch ({m.group(1) if m else "absent"} != {version})')
if not (root/f'ORBIT-Claude-Desktop-v{version}.mcpb').is_file():sys.exit('matching .mcpb missing')
import json, zipfile
with zipfile.ZipFile(root/f'ORBIT-Claude-Desktop-v{version}.mcpb') as bundle:
 manifest=json.loads(bundle.read('manifest.json'))
 if manifest.get('version')!=version:sys.exit('Desktop manifest VERSION mismatch')
 for source in (root/'source/runtime').glob('*.py'):
  if bundle.read('server/'+source.name)!=source.read_bytes():
   sys.exit('Desktop runtime source mismatch for '+source.name)
print(f'Version OK: {version}')
