"""Read-only Orbit capability discovery and selection; no imports/installs/network."""
from __future__ import annotations
import json
import re
from pathlib import Path

TRIGGERS = {
    'frontend': {'frontend','ui','ux','interface','design','responsive','component','layout','accessibility','visual','polish'},
    'backend': {'backend','api','database','auth','server','schema','sql','endpoint','persistence'},
    'qa': {'test','testing','browser','e2e','regression','quality','playwright','screenshot','screenshots','visual'},
    'security': {'security','secrets','threat','vulnerability','privacy'},
    'devops': {'deploy','ci','release','docker','pipeline','operations'},
}
# Curated *research* targets, not bundled/installable code or blanket endorsements.
CATALOG = [
 {'name':'impeccable', 'category':'frontend', 'description':'Official Impeccable UI/design skill for critique, polish and design systems', 'official_url':'https://impeccable.style/', 'publisher':'pbakaus', 'kind':'skill', 'execution':'external_install_requires_review'},
 {'name':'agent-browser', 'category':'qa', 'description':'Vercel Labs optional agent-friendly browser CLI and MCP provider; interactive snapshots and screenshot testing', 'official_url':'https://github.com/vercel-labs/agent-browser', 'publisher':'vercel-labs', 'kind':'mcp', 'execution':'external_install_requires_review'},
]
MAX_ITEMS = 120

def _parse_skill(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
        return None
    body=path.read_text(encoding='utf-8')[:12000]
    match=re.match(r'\A---\s*\n(.*?)\n---\s*\n', body, re.S)
    if not match:return None
    def field(k):
        m=re.search(r'^'+k+r':\s*(.+?)\s*$', match.group(1), re.M)
        return m.group(1).strip().strip('"\'') if m else ''
    name,description=field('name'),field('description')
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name):return None
    return {'name':name,'description':description[:320], 'source':'installed_skill','path':str(path), 'kind':'skill', 'trust':'local_unverified'}

def _skill_paths(project_root, home):
    folders=[]
    if project_root:
        root=Path(project_root)
        folders += [root/'.agents/skills',root/'.claude/skills']
    folders += [home/'.agents/skills',home/'.gemini/config/skills',home/'.claude/skills']
    return folders

def _configs(project_root, home):
    items=[]
    if project_root:
        p=Path(project_root)
        items += [p/'.agents/mcp_config.json',p/'.mcp.json']
    items += [home/'.gemini/config/mcp_config.json',home/'.claude.json']
    return items

def discover(project_root, *, home=None):
    h=Path(home) if home else Path.home()
    skills=[]; seen=set(); servers=[]; limits=[]
    for folder in _skill_paths(project_root,h):
        if folder.is_symlink() or not folder.is_dir():continue
        try: children=sorted(folder.iterdir())[:MAX_ITEMS]
        except OSError:continue
        for child in children:
            if child.is_symlink() or not child.is_dir():continue
            item=child/'SKILL.md'
            try: val=_parse_skill(item)
            except (OSError,UnicodeError):continue
            if val:
                identity=(val['name'],val['path'])
                if identity not in seen: skills.append(val);seen.add(identity)
            if len(skills)>=MAX_ITEMS:break
        if len(skills)>=MAX_ITEMS:break
    for cfg in _configs(project_root,h):
        if cfg.is_symlink() or not cfg.is_file() or cfg.stat().st_size > 256000: continue
        try:
            data=json.loads(cfg.read_text(encoding='utf-8'))
            rows=data.get('mcpServers',{}) if isinstance(data,dict) else {}
            if isinstance(rows,dict):
                for name in list(rows)[:MAX_ITEMS]:
                    if isinstance(name,str) and name and isinstance(rows[name],dict):
                        servers.append({'name':name[:90], 'kind':'mcp', 'source':'configured_not_connection_verified','config_path':str(cfg)})
        except (OSError,UnicodeError,ValueError): continue
    # Codex MCP keys require full TOML parsing; tomllib is available in Python 3.11+.
    configs=[Path(project_root)/'.codex/config.toml'] if project_root else []
    configs += [h/'.codex/config.toml']
    try:
        import tomllib
        for cfg in configs:
            if cfg.is_symlink() or not cfg.is_file() or cfg.stat().st_size>256000:continue
            try:
                data=tomllib.loads(cfg.read_text(encoding='utf-8'))
                for name in list(data.get('mcp_servers',{}))[:MAX_ITEMS]:
                    servers.append({'name':name[:90], 'kind':'mcp','source':'configured_not_connection_verified','config_path':str(cfg)})
            except (OSError,UnicodeError,ValueError):pass
    except ImportError: pass
    return {'skills':skills[:MAX_ITEMS], 'mcp_servers':servers[:MAX_ITEMS], 'limits':['Installed skills are untrusted until vetted. A configured MCP is NOT proof it is connected.', 'No network, process launching, installations, host tool enumeration or permission changes occurred.']}

def select(project_root, objective, host_tools=None, *, home=None):
    if not isinstance(objective,str) or not objective.strip() or len(objective)>1500: raise ValueError('objective must contain 1..1500 characters')
    if not isinstance(host_tools,list) or len(host_tools)>80 or any(not isinstance(x,str) or len(x)>100 for x in host_tools):raise ValueError('host_tools must be a short list of names')
    available=discover(project_root,home=home)
    words=set(re.findall(r'[a-z0-9]+',objective.lower()))
    categories=[k for k,terms in TRIGGERS.items() if words&terms]
    if not categories:categories=['general']
    candidates=[]
    for s in available['skills']:
        text=(s['name']+' '+s['description']).lower()
        overlap=len(set(re.findall('[a-z0-9]+',text))&words)
        if s['name']=='orbit':continue
        if overlap:
            candidates.append({**s,'match_count':overlap,'status':'INSTALLED_NEEDS_TRUST_CHECK','next':'inspect skill instructions and compatibility before use'})
    candidates.sort(key=lambda x:(-x['match_count'],x['name']))
    research=[]
    existing_names={c['name'] for c in candidates}
    for item in CATALOG:
        if item['category'] in categories and item['name'] not in existing_names:
            research.append({**item,'status':'RESEARCH_CANDIDATE_NOT_INSTALLED', 'next':'browse official source, review permissions and request installation approval'})
    # Configuration is an inventory, not proof a provider connected or ran QA.
    agent_browser_configured = any(x['name']=='agent-browser' for x in available['mcp_servers'])
    agent_browser_visible = any(x.startswith('agent_browser_') for x in host_tools)
    browser_provider = {
        'name':'agent-browser', 'kind':'optional_external_mcp',
        'status':('HOST_REPORTED_TOOL_VISIBLE' if agent_browser_visible
                  else 'CONFIGURED_UNVERIFIED' if agent_browser_configured
                  else 'NOT_CONFIGURED'),
        'official_url':'https://github.com/vercel-labs/agent-browser',
        'next':('Check permissions and execute one read-only agent_browser_snapshot in the host before trusting the connection.'
                if agent_browser_visible else 'Review official source and request explicit consent before installing or adding its MCP configuration.'),
        'orbit_browser_qa_gate':'Separate Orbit-recorded Playwright PASS still required; third-party MCP screenshots never bypass a blocked gate.',
    }
    return {'objective':objective,'categories':categories,'installed_matches':candidates[:8], 'configured_mcp_servers':available['mcp_servers'][:20], 'host_reported_tools':host_tools[:50], 'external_research_candidates':research,
            'optional_browser_provider':browser_provider,
        'recommended_action':'REUSE_AND_VERIFY_INSTALLED' if candidates else ('BROWSE_OFFICIAL_SOURCES_AND_REQUEST_APPROVAL' if research else 'USE_EXISTING_HOST_CAPABILITIES'),
        'policy':['Prefer current built-in host abilities and already installed vetted skills.', 'If a needed capability is missing, the agent may web-search reputable official sources using host tools. Never claim MCP performed the search.', 'Never execute npx/curl/script, install packages, add MCP connections, grant OAuth/scopes, or modify agent rules without reviewing source and obtaining applicable host/user approval.', 'Use the minimal permission and project scope; re-check actual tool availability after approved install; no best-in-class guarantee.']}
