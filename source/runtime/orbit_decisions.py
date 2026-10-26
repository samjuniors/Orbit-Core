"""Read-only product capability and model recommendation router.

All library/model catalogs are research recommendations, not installation, connection,
version, entitlement, benchmark or permission verification. Host owns model switches.
"""
from __future__ import annotations

import re

TYPES={'website','web-app','desktop-app','mobile-app','api-service','cli','sdk-library','plugin-mcp','os-platform','game','data-automation','other'}
HOSTS={'antigravity','claude-code','codex','vscode','generic'}
PLATFORMS={'web','android','ios','macos','windows','linux','server','embedded'}
TASKS={'read','research','documentation','design','implementation','qa','review','security','architecture'}
ROLES={'orbit','orbit-architect','orbit-frontend','orbit-backend','orbit-data','orbit-security',
       'orbit-qa','orbit-devops','orbit-ux','orbit-writer','orbit-research','orbit-reviewer','orbit-integrator'}
FLOWS={
    'web':('RESEARCH','PLAN','IMPLEMENT','VERIFY','PREVIEW','BROWSER_QA','REVIEW','CHECKPOINT','DONE'),
    'native':('RESEARCH','PLAN','IMPLEMENT','VERIFY','NATIVE_QA','REVIEW','CHECKPOINT','DONE'),
    'library':('RESEARCH','PLAN','IMPLEMENT','VERIFY','REVIEW','CHECKPOINT','DONE'),
    'platform':('RESEARCH','PLAN','IMPLEMENT','VERIFY','REVIEW','CHECKPOINT','DONE'),
}
# Small verified-source research index. Nothing is installed or executed from here.
CATALOG=(
    ('astryx','UI components','web','react,stylex','https://astryx.atmeta.com/components',
     'Meta MIT open-source design system, React 19+; StyleX authors internals but consumer styling can use CSS or Tailwind. CLI and custom integrations.'),
    ('shadcn-ui','UI components','web','react,tailwind','https://ui.shadcn.com/docs',
     'Copyable, ownable source components; review registry licenses/compatibility.'),
    ('radix-primitives','UI primitives','web','react','https://www.radix-ui.com/primitives/docs/overview/introduction',
     'Unstyled accessible primitives useful for custom visual design.'),
    ('react-aria','UI primitives','web','react','https://react-aria.adobe.com/',
     'Accessible React interaction primitives; inspect actual package compatibility.'),
    ('native-web','platform APIs','web','vanilla,html,typescript,javascript',
     'https://developer.mozilla.org/en-US/docs/Web/API',
     'Prefer semantic HTML and web platform APIs for appropriately simple web apps.'),
    ('expo','mobile framework','android,ios','react,react-native,typescript',
     'https://docs.expo.dev/get-started/create-a-project/',
     'Shared React Native Android/iOS; verify native capability requirements.'),
    ('flutter','mobile framework','android,ios','flutter,dart',
     'https://docs.flutter.dev/','Cross-platform Dart UI; review build tooling and target support.'),
    ('jetpack-compose','native mobile UI','android','kotlin,android',
     'https://developer.android.com/develop/ui/compose',
     'Google Android native declarative UI; use platform testing/tooling.'),
    ('swiftui','native mobile UI','ios,macos','swift,swiftui',
     'https://developer.apple.com/documentation/swiftui',
     'Apple native UI; iOS build/signing needs compatible Apple tooling.'),
    ('context7','documentation MCP','any','any','https://github.com/upstash/context7',
     'Version-aware library documentation via optional MCP; never a component library.'),
    ('impeccable','design skill','web','any','https://impeccable.style/',
     'UI critique/polish guidance, not a component framework.'),
    ('agent-browser','browser QA','web','any','https://github.com/vercel-labs/agent-browser',
     'Optional browser automation; not a UI kit or replacement for real QA evidence.'),
)
HOST_ROUTING={
    'antigravity':'Host-supported custom agent model setting or subagent tier in compatible Antigravity 2.0/CLI; check exact installed IDE and visible invocation API.',
    'claude-code':'Claude Code subagents support model aliases and per-call model override; current host must confirm model access.',
    'codex':'Codex subagents may use per-role model configs and spawn overrides; check configured agents and signed-in availability.',
    'vscode':'VS Code Local subagents can use a model parameter or custom-agent model preference, subject to harness and cost tier.',
    'generic':'No host model control verified; inherit the parent model.',
}

def _tier(name):
    t=name.lower()
    if any(x in t for x in ('haiku','flash','mini','nano','small')):return 'fast'
    if any(x in t for x in ('opus','argon','reasoning-high','xhigh','deep')):return 'deep'
    if any(x in t for x in ('sonnet','pro','codex','gpt','gemini','fable')):return 'balanced'
    return 'unknown'

def model_route(role,task,complexity,models,host,budget):
    if host not in HOSTS or role not in ROLES or task not in TASKS or budget not in {'economy','balanced','quality'}:
        raise ValueError('Unsupported host, role, task or budget')
    if complexity not in {'simple','moderate','complex','high-assurance'}:
        raise ValueError('Unknown complexity')
    if not isinstance(models,list) or len(models)>20 or any(not isinstance(x,str) or not 1<=len(x.strip())<=100 for x in models):
        raise ValueError('available_models must be 0..20 bounded names reported by host')
    if task in {'architecture','security'} and complexity in {'complex','high-assurance'}:
        tier='deep'
    elif task in {'architecture','security','review','implementation'} and complexity!='simple':
        tier='balanced' if budget!='quality' else 'deep'
    elif task in {'read','research','documentation'}:
        tier='fast' if budget=='economy' else 'balanced'
    else:
        tier='fast' if budget=='economy' and complexity=='simple' else 'balanced'
    if complexity=='high-assurance' and tier=='fast':tier='balanced'
    order={'fast':('fast','balanced','deep','unknown'),
           'balanced':('balanced','deep','fast','unknown'),
           'deep':('deep','balanced','fast','unknown')}[tier]
    clean=list(dict.fromkeys(x.strip() for x in models))
    chosen=next((m for k in order for m in clean if _tier(m)==k),None)
    return {'role':role,'task':task,'host':host,'desired_tier':tier,
            'available_models_reported':len(clean),
            'recommended_model':chosen, 'selection_status':'HOST_REPORTED_UNVERIFIED' if chosen else 'INHERIT_HOST_MODEL',
            'chosen_tier':_tier(chosen) if chosen else None,
            'tier_fallback':bool(chosen and _tier(chosen)!=tier),
            'host_control_guidance':HOST_ROUTING[host],
            'no_switch_executed':True,
            'cost_note':'Heuristic only. No real-time quotas, price, billing, entitlements or benchmark measurements.',
            'permission_note':'Do not spawn another CLI, switch providers/accounts, spend credits or edit host model settings without explicit host/user authorization.'}

def components(product_type,platforms,stack,preference):
    if product_type not in TYPES or preference not in {'balanced','reuse','custom'}:
        raise ValueError('Unknown product type or component preference')
    if not isinstance(platforms,list) or len(platforms)>6 or any(p not in PLATFORMS for p in platforms):
        raise ValueError('Invalid platforms')
    if not isinstance(stack,str) or len(stack)>160:raise ValueError('Invalid stack')
    wants=set(platforms)
    if product_type in {'website','web-app'}:wants.add('web')
    if product_type=='mobile-app' and not wants:wants={'android','ios'}
    if product_type in {'sdk-library','cli','api-service','plugin-mcp','os-platform','data-automation'}:
        wants= wants or {'server'}
    lower=stack.lower()
    flags={
        'react':bool(re.search(r'\breact\b|\bnext(?:\.js)?\b',lower)),
        'stylex':'stylex' in lower,
        'tailwind':'tailwind' in lower,
        'vanilla':bool(re.search(r'\bvanilla\b|\bplain html\b',lower)),
        'flutter':'flutter' in lower or 'dart' in lower,
        'swift':'swift' in lower,
        'kotlin':'kotlin' in lower,
    }
    result=[]
    for ident,kind,platform,stacks,url,why in CATALOG:
        permitted=set(platform.split(','))
        if 'any' not in permitted and not wants.intersection(permitted):continue
        if product_type in {'sdk-library','cli','api-service','plugin-mcp','os-platform','data-automation'} and kind in {'UI components','UI primitives','mobile framework','native mobile UI','browser QA'}:continue
        if ident=='astryx':
            status='INCOMPATIBLE_STACK' if re.search(r'\breact\s*(?:1[0-8]|[1-9])\b',lower) else 'REVIEW_MATCH' if flags['react'] else 'REVIEW_COMPATIBILITY' if not lower else 'INCOMPATIBLE_STACK'
        elif ident in {'shadcn-ui','radix-primitives','react-aria'}:
            status='REVIEW_MATCH' if flags['react'] and (ident!='shadcn-ui' or flags['tailwind']) else 'REVIEW_COMPATIBILITY' if not lower else 'INCOMPATIBLE_STACK'
        elif ident=='native-web':
            status='REVIEW_MATCH' if flags['vanilla'] else 'REVIEW_COMPATIBILITY'
        elif ident=='expo':
            status='REVIEW_MATCH' if flags['react'] else 'REVIEW_COMPATIBILITY' if not lower else 'STACK_CHANGE_REQUIRED'
        elif ident=='flutter':
            status='REVIEW_MATCH' if flags['flutter'] else 'REVIEW_COMPATIBILITY' if not lower else 'STACK_CHANGE_REQUIRED'
        elif ident=='jetpack-compose':
            status='REVIEW_MATCH' if flags['kotlin'] else 'REVIEW_COMPATIBILITY' if not lower else 'STACK_CHANGE_REQUIRED'
        elif ident=='swiftui':
            status='REVIEW_MATCH' if flags['swift'] else 'REVIEW_COMPATIBILITY' if not lower else 'STACK_CHANGE_REQUIRED'
        else:
            status='OPTIONAL_TOOL_REQUIRES_HOST_PERMISSION'
        if preference=='custom' and kind in {'UI components','UI primitives'}:
            why+=' Use as a customizable accessibility foundation only if design constraints permit.'
        result.append({'id':ident,'kind':kind,'official_url':url,'status':status,'reason':why})
    result.sort(key=lambda v:({'REVIEW_MATCH':0,'REVIEW_COMPATIBILITY':1,'OPTIONAL_TOOL_REQUIRES_HOST_PERMISSION':2,
                               'STACK_CHANGE_REQUIRED':3,'INCOMPATIBLE_STACK':4}[v['status']],v['id']))
    if product_type in {'mobile-app','desktop-app'}:
        profile='native'
    elif product_type in {'cli','sdk-library','plugin-mcp','api-service','data-automation'}:profile='library'
    elif product_type=='os-platform':profile='platform'
    else:profile='web'
    required_question='Which target platform and native capabilities are required?' if product_type=='mobile-app' else (
        'Which runtime compatibility and public API contract must be supported?' if profile=='library'
        else 'Is this a kernel, distribution, desktop shell or platform SDK?' if profile=='platform'
        else 'Do you want existing-library components customized, or entirely custom components with the same accessibility requirements?')
    return {'product_type':product_type,'platforms':sorted(wants),'workflow_profile':profile,
            'recommended_stages':list(FLOWS[profile]),'initial_question':required_question,
            'component_preference':preference,
            'candidates':result[:9],
            'custom_component_allowed':True,
            'warning':'Recommendations are read-only research pointers, not verified installed components or permission to install.'}
