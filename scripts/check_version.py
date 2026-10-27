from pathlib import Path
import ast, re, sys
root=Path(__file__).resolve().parents[1]
version=(root/'VERSION').read_text().strip()
if not re.fullmatch(r'\d+\.\d+\.\d+', version):sys.exit('Invalid SemVer')
# The canonical released bundle remains v0.24.1 until a separate candidate is
# generated, reviewed and published. NEXT_VERSION tracks the planned update.
next_file=root/'NEXT_VERSION'
if next_file.is_file():
 planned=next_file.read_text(encoding='utf-8').strip()
 if not re.fullmatch(r'\d+\.\d+\.\d+',planned):sys.exit('Invalid NEXT_VERSION SemVer')
 if tuple(map(int,planned.split('.')))<=tuple(map(int,version.split('.'))):
  sys.exit('NEXT_VERSION must be greater than the currently packaged VERSION')
for rel in ('installer.py','source/runtime/orbit_mcp.py'):
 text=(root/rel).read_text(encoding='utf-8')
 m=re.search(r'^VERSION\s*=\s*[\"\'](\d+\.\d+\.\d+)[\"\']',text,re.M)
 if not m or m.group(1)!=version:sys.exit(f'{rel}: VERSION mismatch ({m.group(1) if m else "absent"} != {version})')
if not (root/f'ORBIT-Claude-Desktop-v{version}.mcpb').is_file():sys.exit('matching .mcpb missing')
import json, zipfile
with zipfile.ZipFile(root/f'ORBIT-Claude-Desktop-v{version}.mcpb') as bundle:
 manifest=json.loads(bundle.read('manifest.json'))
 if manifest.get('version')!=version:sys.exit('Desktop manifest VERSION mismatch')
 # The desktop .mcpb is a published artifact. Development branches can be
 # ahead of that release; tagged releases and --strict-bundle require parity.
 strict='--strict-bundle' in sys.argv or __import__('os').environ.get('GITHUB_REF_TYPE')=='tag'
 changed=[]
 for source in (root/'source/runtime').glob('*.py'):
  if bundle.read('server/'+source.name)!=source.read_bytes():
   changed.append(source.name)
 if changed and strict:
  sys.exit('Desktop runtime source mismatch (release gate): '+', '.join(changed))
 if changed:print('UNRELEASED SOURCE differs from desktop v'+version+': '+', '.join(changed))
print(f'Version manifest OK: {version}')
