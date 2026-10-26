"""Orbit Universal local project setup 0.23.0.

No agent CLI is spawned. No project code or Git is modified. Local MCP uses
Python stdio; file/config edits are previewed and require explicit confirmation.
"""
from __future__ import annotations
import argparse
import json
import hashlib
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent
VERSION = "0.23.0"
SERVER = "orbit-core-native"
HOSTS = ("antigravity", "codex", "claude-code")
SCOPES = ("machine", "project")
# Hashes of exact vendor-packed v0.22.0 stock files ONLY: safe upgrade after backup.
OLD_STOCK_SHA256 = {
    '096c989e51db5c0f123aee197e3c65456a0e5508ec7902a50ce8a5cb3aefc17e',
    '0ff44846a5d26607bbed8d1d3f506e898546e13a614b76962c6029a02e195c44',
    '10fa370a50e8cdc3032c40f5ddec3e221c2999656a7158f5585b053c0dbd67c9',
    '23c88ebcac418d20857737265a900c30c18851bfd0ef4fd27f77f76f6eb59439',
    '291f371c54a393ca37ed90b60a043dd7b61aae1c41ccbcc14624954c2c12f812',
    '2f47b90bc026ee0da72facd7781b6730246986b69226df7b4908493f4c3c4ca3',
    '3413d2f2571460657a1e90ee714e2d4ac8b9223bc0d6c255d2e9e4c9ed57002d',
    '3705b983148983d3d35a9b4dbd53c9cf704a3e445143f79842145a663062ca2f',
    '38662fc36fd3a48d698fcd2039e10a2c6dfb304b0b4050a707237faf033ffe30',
    '38e3094ab64cda3a81ff6d9d84c4dde26620e80f371e84a9fec82c25dcb8cc2d',
    '39ecb53621d44bf4e573cff5362b04250a1d3100f65d62c3ecb1c4573c9fcf23',
    '3c6965f344fd4e8536391f97ef7388c51ce6e3dd385498b467ebe43e8245ee79',
    '4433fbbb27920a5a89e3c27a130bc3f921775687cafbdea5009f27181ef0bfc5',
    '4b0b06086e34eb3769fd09fcf05cb3a3d133ee2b3859822f3b26dc62aea702ef',
    '4e439caf19e4fffa036b60c13c346f7a6199cf20b5929948631286c6a5839a3e',
    '56337132ae0887cb30eae7c0755563645fab1580e23119ad0ca7861d74893bac',
    '6d96b9f10655a1e8e711850f5403a7add8a8257d4f3bb5ba1f215b82b07f8099',
    '7db286c05dcd8bd77a4585f2ad387c04107aff132d84f394faa4ed6bfaf88314',
    '85a3599bc5c43dfdb22f14cf9b73655417292c6f4fe91961c9fe051b27f0c604',
    '86e14167e128f639fdbe8652607cf52e30bede136fbf556a20236b769421ed89',
    '95906cb1cda92139f4154303f319a0fbd489dd15d720edad3dd0fcf28591189f',
    'a9db9aeeb44bef29a1d18918762b4155dbc9d5c2aee02b2a8561f9759e15ac02',
    'ac3c4581f27583552db2a74ed15622475ec0c384718b11888b1866dd98d3cd37',
    'c6664ae0e2e9d697ff2946b176a6e0b2e9c5b05c78e185117ddc997fd5803714',
    'd691d0b30b5cc6fd40557f31de46c5c1963eff698dba630812f9a76a03f04c35',
    'de6e74a86bb3d7cd5909aa9143a11b3b57680e48360f7400d1deef60bdd6d075',
    'dec31c1a6657466fc11269e75f880bc09e65a9bd2b4a5b382c602387d2a063f3',
    'eac64b2c255bdcae6ee64d41708f3adf21d4b7b0623cd5ddb0c1281a2f148071',
    'eb98bde2a77696dbcdd9541f890ae5993017de4bab42acb979e1948c46ccbfc0',
    'f151a221c0a282a2a79cc3dcbfffe75aa9dbb635e3c7195c03bfdb025c41ca47',
    'f19689b6d352ef5a34f165a99c8b4ac624a279e7c39ef5b3cb33f92122888b03' 
}



class SetupError(Exception): pass


def python_binary() -> str:
    p = Path(sys.executable).resolve()
    if os.name == 'nt' and p.name.lower() == 'pythonw.exe':
        p = p.with_name('python.exe')
    if not p.is_file(): raise SetupError('Python interpreter not found')
    return str(p)


def user_home() -> Path:
    # Override only useful for isolated test environments; standard install uses OS home.
    return Path(os.getenv('ORBIT_SETUP_HOME') or Path.home()).expanduser().resolve()


def runtime_folder() -> Path:
    base = os.getenv('ORBIT_UNIVERSAL_HOME')
    return (Path(base).expanduser().resolve() if base else user_home() / '.orbit-universal') / VERSION


def check_project(p: str | Path) -> Path:
    raw = Path(p).expanduser()
    if not raw.is_absolute() or raw.is_symlink():
        raise SetupError('Select an existing absolute, non-symlink project directory')
    root = raw.resolve(strict=True)
    if not root.is_dir() or root == Path(root.anchor) or root == Path.home().resolve():
        raise SetupError('Select a specific project, not home or the drive root')
    return root


def check_dest(path: Path, root: Path) -> None:
    if root not in path.parents and path != root:
        raise SetupError('Refusing to write outside project root')
    for x in [path,*path.parents]:
        if x == root: break
        if x.is_symlink(): raise SetupError(f'Symlink destination is not allowed: {x}')


def toml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def agent_claude(content: str) -> str:
    m = re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)',content,re.S)
    if not m: raise SetupError('Agent YAML header missing')
    f, body=m.group(1),m.group(2)
    name=re.search(r'^name:\s*(\S.*)$',f,re.M)
    desc=re.search(r'^description:\s*(\S.*)$',f,re.M)
    if not name or not desc: raise SetupError('Agent name/description missing')
    n=name.group(1).strip().strip('"\'')
    d=desc.group(1).strip().strip('"\'')
    if not re.fullmatch(r'[a-z][a-z0-9-]{1,70}',n):raise SetupError('Invalid agent ID: '+n)
    return '---\nname: '+n+'\ndescription: '+json.dumps(d)+'\n---\n'+body


ORBIT_SKILL = '''---
name: orbit
description: Coordinate a software project through Orbit: inspect project, plan milestones, use authorized specialist subagents, report evidence, and save bounded SQLite project state via Orbit MCP. Use for new apps, debugging, review, handoffs and resume.
---
# ORBIT — universal host adapter

You are the lead project orchestrator, using this host's current model and native tools. The Orbit MCP is a task/memory service; it does NOT spawn models or execute app code. Respect the host's permissions, sandbox and user approvals.

1. Confirm the selected project folder and stable project key. Before planning, inspect current Git status and existing docs/source. Do not invent an existing implementation.
2. Call `orbit_project_resume` or `orbit_memory_recall` on `orbit-core-native` when connected; if disconnected, say memory is unavailable, never claim persistence.
3. Build a right-sized plan: product, accessible UI, backend/API/data if actually needed, security, tests, CI, release/rollback. Track milestone/gate/next bounded step.
4. Prefer existing docs and components. Write missing DRAFT documents only when needed; preserve all owner documents/ADRs.
5. For specialist tasks: use `orbit_task_plan`, then reserve using `orbit_task_reserve` **only** for user-authorized host delegation. Use this host's native subagent interface (Antigravity `invoke_subagent`, Codex delegation, Claude Code Task/Agent tools) only if actually available. Do not call another provider's CLI. Parallelize only non-overlapping work; default 2 task reservations.
6. After a successful native start, record the real session using `orbit_task_started`. Do not claim an agent is running merely because a task was reserved. Report outcome with `orbit_task_report` and independently review actual diffs/tests with `orbit_task_review`. Reject scope violations, failed tests and unverifiable results.
7. Use `orbit_project_checkpoint` with the fresh revision and user-approved `confirm_write=true` after meaningful work. Protect existing `.orbit/STATE.md` and use the same project key across hosts.
8. No automatic git add/commit, push, merge, deploy, delete, billing or auth changes. Never expose secrets. If an operation is unavailable or blocked, report accurately.

Before delegating to a specialist, call `orbit_capability_select` with the real project path, task objective and host tools. Review installed skill compatibility/provenance. Prefer existing trusted skills and native host tools; if something is missing, research using the host's approved web search. The official Impeccable frontend design skill (https://impeccable.style/) is an optional candidate, never silently installed or treated as universally best. Third-party installation and adding MCP connections are user/host approval-gated. Review source/permissions first, then verify actual availability after approval. Specialists may recommend, not self-authorize or spawn more agents.

For a Todo Lab test, develop the app through milestones and explicitly report native delegation and MCP calls separately. A generated test report is not proof that a test ran: show command and exit code.
'''

ORBIT_LEAD_CLAUDE = '''---
name: orbit-lead
description: Lead software project orchestrator. Inspect code and docs, coordinate scoped specialist agents, verify tests and checkpoints. Use for project planning, development and resumptions.
---
You are Orbit, the main orchestrator. Follow `.claude/skills/orbit/SKILL.md`. Do not create competing project documentation or spawn external agent CLIs. Use host-native subagents only where available and authorized, and the local Orbit MCP for SQLite memory and task ledger. Never claim a tool ran without its result.
'''

AGENTS_GUIDE = '''# ORBIT project guidance

This project uses the repository skill `.agents/skills/orbit/SKILL.md`. When asked to work as Orbit, invoke `$orbit` or read that skill, then use connected `orbit-core-native` MCP tools for checkpoints, task ledger and memory. The model and native subagent executor belong to the active host (Codex, Antigravity or Claude Code), not MCP. Do not invoke a separate AI CLI; use approved native delegation. Verify outputs; do not invent test runs or saved state. Never stage/commit/merge/deploy without authorization.
'''

CLAUDE_GUIDE = '''# ORBIT project guidance

For Orbit workflows load `.claude/skills/orbit/SKILL.md`. Choose `orbit-lead` as lead when appropriate; delegate frontend/backend/QA work using Claude Code's native agents when supported. Use the connected `orbit-core-native` MCP tools for local persistent memory and ledger. Do not invoke external model CLIs or modify unrelated projects. Validate evidence before accepting work.
'''


@dataclass
class Change:
    target: Path
    data: bytes
    action: str
    description: str


def same_or_create(changes: list[Change], dest: Path, data: bytes, root: Path|None, desc: str):
    if root: check_dest(dest,root)
    if dest.exists():
        if not dest.is_file() or dest.is_symlink():raise SetupError('Destination exists and is not a regular file: '+str(dest))
        current=dest.read_bytes()
        if current != data:
            oldhash=hashlib.sha256(current).hexdigest()
            if oldhash in OLD_STOCK_SHA256:
                changes.append(Change(dest,data,'UPGRADE',desc+' (v0.22 stock file; backup made)'))
            elif dest.name in {'AGENTS.md','CLAUDE.md'}:
                # Existing owner guidance is authoritative; Orbit's skill remains available.
                changes.append(Change(dest,current,'PRESERVE','Existing owner guidance retained'))
            else:
                raise SetupError('Existing customized file needs manual review; no overwrite: '+str(dest))
        else:
            changes.append(Change(dest,data,'SKIP',desc))
    else:
        changes.append(Change(dest,data,'CREATE',desc))


def merge_json(changes: list[Change], dest: Path, entry: dict, root: Path, desc: str):
    check_dest(dest,root)
    old={}
    if dest.exists():
        if dest.is_symlink() or not dest.is_file():raise SetupError('Unsafe config: '+str(dest))
        try: old=json.loads(dest.read_text(encoding='utf-8'))
        except Exception as e: raise SetupError('Cannot parse existing config: '+str(dest)) from e
        if not isinstance(old,dict): raise SetupError('Config must be object: '+str(dest))
    servers=old.get('mcpServers',{})
    if not isinstance(servers,dict): raise SetupError('mcpServers must be object')
    if SERVER in servers and servers[SERVER]!=entry:
        prior=servers[SERVER]
        # Only migrate the exact previous stock server command shape, preserving other MCPs.
        if not (isinstance(prior,dict) and prior.get('command')==entry['command']
                and isinstance(prior.get('args'),list) and len(prior['args'])==1
                and '/0.22.0/' in str(prior['args'][0]).replace('\\','/')
                and set(prior)==set(entry)):
            raise SetupError('Existing Orbit MCP registration differs; no overwrite: '+str(dest))
    obj={**old, 'mcpServers':{**servers,SERVER:entry}}
    body=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
    if dest.exists() and json.loads(dest.read_text())==obj:
        changes.append(Change(dest,dest.read_bytes(),'SKIP',desc))
    else:
        changes.append(Change(dest,body,'CREATE' if not dest.exists() else 'MERGE',desc))


def merge_toml(changes: list[Change], dest: Path, python_cmd: str, runtime: Path, root: Path):
    check_dest(dest,root)
    old = dest.read_text('utf-8') if dest.exists() else ''
    section='\n[mcp_servers."orbit-core-native"]\ncommand = '+toml_str(python_cmd)+'\nargs = ['+toml_str(str(runtime))+']\n'
    matching = re.search(r'(?m)^\s*\[mcp_servers[.]["\']?orbit-core-native["\']?\]',old)
    if matching:
        if section.strip() in old:
            changes.append(Change(dest,old.encode('utf-8'),'SKIP','Codex Orbit MCP already matches'))
            return
        # Migrate only a known stock Orbit config section from v0.22; preserve surrounding TOML.
        match=re.search(r'(?ms)^\s*\[mcp_servers\.["\']orbit-core-native["\']\]\n(.*?)(?=^\s*\[|\Z)', old)
        if match:
            body=match.group(1)
            if ('/0.22.0/' in body.replace('\\','/') and
                re.fullmatch(r'(?ms)\s*command\s*=\s*"[^"\n]+"\s*\nargs\s*=\s*\["[^"\n]+"\]\s*',body)):
                next_body=old[:match.start()]+'\n'+section.strip()+'\n'+old[match.end():]
                changes.append(Change(dest,next_body.encode('utf-8'),'APPEND','Codex migrate v0.22 MCP with backup'))
                return
        raise SetupError('Codex Orbit MCP table already exists and differs; review manually: '+str(dest))
    body=(old.rstrip()+ '\n'+ section if old.strip() else section.lstrip()).encode('utf-8')
    changes.append(Change(dest,body,'CREATE' if not dest.exists() else 'APPEND', 'Codex project-local MCP table'))


def plan(project: str|Path|None=None, hosts=HOSTS, scope='project') -> list[Change]:
    if scope not in SCOPES: raise SetupError('Select machine or project install scope')
    root=check_project(project) if scope=='project' else None
    home=user_home()
    hosts=set(hosts)
    if not hosts or hosts-set(HOSTS):raise SetupError('Choose supported host(s): '+', '.join(HOSTS))
    src=PACKAGE/'source'
    runtime=runtime_folder()
    if any(p.is_symlink() for p in [runtime,runtime.parent]):raise SetupError('Runtime directory is a symlink')
    changes=[]
    for name in ['orbit_mcp.py','orbit_tasks.py','orbit_capabilities.py']:
        p=src/'runtime'/name
        same_or_create(changes,runtime/name,p.read_bytes(),None,'Shared Orbit stdio MCP runtime')
    cmd=python_binary()
    script=runtime/'orbit_mcp.py'
    common={'command':cmd,'args':[str(script)]}
    if 'antigravity' in hosts:
        agents=(root/'.agents/agents') if root else (home/'.gemini/config/agents')
        skills=(root/'.agents/skills') if root else (home/'.gemini/config/skills')
        for p in (src/'agents').glob('*.md'):
            same_or_create(changes,agents/p.name,p.read_bytes(),root or home,'Native Antigravity agent '+p.stem)
        same_or_create(changes,skills/'orbit/SKILL.md',ORBIT_SKILL.encode(),root or home,'Antigravity Orbit skill')
        config=(root/'.agents/mcp_config.json') if root else (home/'.gemini/config/mcp_config.json')
        merge_json(changes,config,common,root or home,'Antigravity MCP configuration')
    if 'codex' in hosts:
        skill=(root/'.agents/skills/orbit/SKILL.md') if root else (home/'.agents/skills/orbit/SKILL.md')
        # Codex and Antigravity share a project skill, but global paths differ.
        if scope=='machine' or 'antigravity' not in hosts:
            same_or_create(changes,skill,ORBIT_SKILL.encode(),root or home,'Codex Orbit skill')
        if root:
            same_or_create(changes,root/'AGENTS.md',AGENTS_GUIDE.encode(),root,'Codex project guidance')
        config=(root/'.codex/config.toml') if root else (home/'.codex/config.toml')
        merge_toml(changes,config,cmd,script,root or home)
    if 'claude-code' in hosts:
        skills=(root/'.claude/skills') if root else (home/'.claude/skills')
        agents=(root/'.claude/agents') if root else (home/'.claude/agents')
        same_or_create(changes,skills/'orbit/SKILL.md',ORBIT_SKILL.encode(),root or home,'Claude Code Orbit skill')
        if root:
            same_or_create(changes,root/'CLAUDE.md',CLAUDE_GUIDE.encode(),root,'Claude Code guidance')
        same_or_create(changes,agents/'orbit-lead.md',ORBIT_LEAD_CLAUDE.encode(),root or home,'Claude lead agent')
        for p in (src/'agents').glob('orbit-*.md'):
            same_or_create(changes,agents/p.name,agent_claude(p.read_text('utf-8')).encode(),root or home,'Claude Code agent '+p.stem)
        config=(root/'.mcp.json') if root else (home/'.claude.json')
        merge_json(changes,config,{**common,'type':'stdio'},root or home,'Claude Code MCP configuration')
    return changes


def install(changes: list[Change]) -> list[str]:
    # Preflight: no contents drift since preview and no symlinks or nonfiles.
    for c in changes:
        if c.target.is_symlink():raise SetupError('Refusing symlink file: '+str(c.target))
        if c.action=='CREATE' and c.target.exists():raise SetupError('New conflict since preview: '+str(c.target))
        if c.action in {'SKIP','PRESERVE'} and (not c.target.is_file() or c.target.read_bytes()!=c.data): raise SetupError('File changed since preview: '+str(c.target))
    applied=[]
    for c in changes:
        if c.action in {'SKIP','PRESERVE'}:continue
        c.target.parent.mkdir(parents=True,exist_ok=True)
        if c.action=='CREATE':
            with c.target.open('xb') as f:f.write(c.data)
        else:
            # Existing configuration is only modified after preview. Backup first.
            if not c.target.is_file():raise SetupError('Config disappeared since preview: '+str(c.target))
            backup=c.target.with_name(c.target.name+'.orbit-backup')
            if backup.exists():raise SetupError('Backup already exists: '+str(backup))
            with backup.open('xb') as b:b.write(c.target.read_bytes())
            tmp=c.target.with_name(c.target.name+'.orbit-new')
            with tmp.open('xb') as f:f.write(c.data)
            tmp.replace(c.target)
            applied.append(str(backup))
        applied.append(str(c.target))
    return applied


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project',type=str)
    ap.add_argument('--scope',choices=SCOPES,default='machine')
    ap.add_argument('--hosts',nargs='+',choices=HOSTS,default=list(HOSTS))
    ap.add_argument('--install',action='store_true',help='Apply changes only with explicit flag (preview default)')
    a=ap.parse_args()
    try:
        changes=plan(a.project,a.hosts,a.scope)
        for c in changes:print(f'{c.action:7} {c.target}')
        if a.install:
            paths=install(changes)
            print(f'Installed {len(paths)} files/backups; restart selected hosts.')
        else:print('PREVIEW ONLY; nothing written. Run with --install to approve.')
    except (OSError,SetupError) as e:
        print('INSTALL BLOCKED:',str(e),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
