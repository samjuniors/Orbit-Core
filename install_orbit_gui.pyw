"""Orbit GUI - single approved install for all current projects or one workspace."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from installer import plan, install, SetupError
from orbit_cli import detect
from orbit_update_gui import launch as open_update_manager
from installer import VERSION
from orbit_setup import plan_uninstall, apply_uninstall

r=tk.Tk()
r.title('Orbit Setup · '+VERSION)
r.geometry('940x760');r.minsize(800,680)
r.configure(background='#f3f5f9')
r.option_add('*Font', ('Segoe UI', 10))
style=ttk.Style(r)
style.theme_use('clam')
style.configure('.',background='#f3f5f9',foreground='#1e293b')
style.configure('TFrame',background='#f3f5f9')
style.configure('TLabel',background='#f3f5f9')
style.configure('Title.TLabel',font=('Segoe UI',24,'bold'))
style.configure('Muted.TLabel',foreground='#526077')
style.configure('TLabelframe',padding=14,borderwidth=1,relief='solid')
style.configure('TLabelframe.Label',font=('Segoe UI',11,'bold'))
style.configure('TButton',padding=(12,8))
style.configure('Primary.TButton',background='#315ce8',foreground='white',font=('Segoe UI',10,'bold'))
style.map('Primary.TButton',background=[('disabled','#dce2ed'),('active','#2446b5')],foreground=[('disabled','#69758b')])
style.configure('TRadiobutton',padding=5)
style.configure('TCheckbutton',padding=5)
header=ttk.Frame(r,padding=(24,20,24,12));header.pack(fill='x')
ttk.Label(header,text='Orbit Setup',style='Title.TLabel').pack(anchor='w')
ttk.Label(header,text='Version '+VERSION+'  ·  Connect Orbit to your coding tools',style='Muted.TLabel').pack(anchor='w',pady=(4,0))
section=ttk.LabelFrame(r,text='1  Choose where Orbit is available');section.pack(fill='x',padx=24,pady=6)
scope=tk.StringVar(value='machine')
scopes=ttk.Frame(section);scopes.pack(fill='x')
for mode,title in [('machine','This computer · all projects'),('project','One project only')]:
    ttk.Radiobutton(scopes,text=title,variable=scope,value=mode).pack(side='left',padx=(0,22))
row=ttk.Frame(section);row.pack(fill='x',pady=(8,0))
project=tk.StringVar();entry=ttk.Entry(row,textvariable=project);entry.pack(side='left',fill='x',expand=True)
btn=ttk.Button(row,text='Choose folder…',command=lambda: project.set(filedialog.askdirectory(title='Select project folder') or project.get()))
btn.pack(side='left',padx=(8,0))
def update_scope(*_):
    enabled=scope.get()=='project'
    entry.config(state='normal' if enabled else 'disabled');btn.config(state='normal' if enabled else 'disabled')
scope.trace_add('write',update_scope);update_scope()
choices=ttk.LabelFrame(r,text='2  Select coding tools');choices.pack(fill='x',padx=24,pady=6)
detected={item['host'] for item in detect() if item['detected']}
selection={h:tk.BooleanVar(value=h in detected) for h in ('antigravity','codex','claude-code','vscode')}
hostrow=ttk.Frame(choices);hostrow.pack(fill='x')
for key,title in [('antigravity','Antigravity'),('codex','Codex'),('claude-code','Claude Code'),('vscode','VS Code')]:
    ttk.Checkbutton(hostrow,text=title,variable=selection[key]).pack(side='left',padx=(0,14))
def refresh_detected():
    root=project.get() if scope.get()=='project' and project.get().strip() else None
    found={item['host'] for item in detect(root) if item['detected']}
    for host,selected in selection.items():selected.set(host in found)
    status.set('Host detection updated. Restart your coding tools after setup to verify MCP connectivity.')
ttk.Button(hostrow,text='Detect again',command=refresh_detected).pack(side='right')
ttk.Label(choices,text='Detected from local files. You can change the selection. Claude Desktop uses a separate extension.',style='Muted.TLabel',wraplength=820).pack(anchor='w',pady=(6,0))
details=ttk.LabelFrame(r,text='3  Review changes');details.pack(fill='both',expand=True,padx=24,pady=6)
ttk.Label(details,text='Preview lists the exact files. Applying changes always asks for confirmation.',style='Muted.TLabel').pack(anchor='w',pady=(0,8))
logrow=ttk.Frame(details);logrow.pack(fill='both',expand=True)
log=tk.Text(logrow,height=9,wrap='word',font=('Consolas',10),background='white',foreground='#334155',relief='flat',padx=12,pady=10)
scroll=ttk.Scrollbar(logrow,command=log.yview);scroll.pack(side='right',fill='y')
log.configure(yscrollcommand=scroll.set);log.pack(fill='both',expand=True)
log.insert('end','Choose your scope and coding tools, then preview the installation.\n')
status=tk.StringVar(value='Checking installation…')
ttk.Label(r,textvariable=status,wraplength=870,justify='left',style='Muted.TLabel').pack(fill='x',padx=24,pady=(8,4))
state={'preview':None,'choices':None,'busy':False}

def installation_action(changes):
    """Derive the action from the selected scope's actual file plan."""
    writable=[c for c in changes if c.action not in {'SKIP','PRESERVE'}]
    if not writable:
        return 'current'
    if any(c.action in {'UPGRADE','MERGE','APPEND'} for c in writable):
        return 'update'
    if any(c.target.exists() for c in changes):
        return 'repair'
    return 'install'

def refresh_action(*_):
    if state['busy']:
        return
    try:
        action=installation_action(plan(*args()))
        labels={'install':'Install Orbit','update':'Update Orbit','repair':'Repair installation','current':'Orbit is up to date'}
        primary.config(text=labels[action],state='disabled' if action=='current' else 'normal')
        status.set('Orbit is up to date for the selected scope and hosts.' if action=='current' else 'Ready: '+labels[action]+'. Preview and approval required before changes.')
    except (SetupError,OSError,ValueError) as e:
        primary.config(text='Review required',state='disabled')
        status.set('Review needed. Use Preview changes for the file path and details.')
def args():return (project.get() if scope.get()=='project' else None,[h for h,b in selection.items() if b.get()],scope.get())
def make_preview():
    log.delete('1.0','end')
    c=plan(*args())
    state['preview']=c;state['choices']=args()
    for item in c:log.insert('end',f'{item.action:7} {item.description}\n  {item.target}\n')
    status.set(f'Preview: {sum(item.action not in {"SKIP","PRESERVE"} for item in c)} proposed file changes, no installs executed.')
    return c
def preview():
    try:make_preview()
    except (SetupError,OSError,ValueError) as e:
        state['preview']=None
        log.insert('end',str(e)+'\n\nKeep the file intact. Compare it with the bundled version before replacing it.\n')
        messagebox.showerror('Review needed',str(e))
def go():
    if state['busy']:
        return
    state['busy']=True
    for button in operation_buttons:
        button.config(state='disabled')
    try:
        selected=args()
        c=make_preview()
        action=installation_action(c)
        if action=='current':
            messagebox.showinfo('Orbit is up to date','No installation changes are needed.')
            return
        if not messagebox.askyesno('Authorize Orbit '+action,f'{action.title()} Orbit from THIS checked-out source in {selected[2]} scope for {", ".join(selected[1])}?\n\nOnly verified bundled files and MCP configurations are written. External skills/MCPs are NOT installed automatically.'):
            return
        if args()!=selected:
            raise SetupError('Selection changed; preview again')
        again=plan(*selected)
        if [(x.target,x.action,x.data) for x in c] != [(x.target,x.action,x.data) for x in again]:
            raise SetupError('Changes detected since preview; review again')
        status.set('Applying Orbit '+action+'...')
        r.update_idletasks()
        paths=install(again)
        if installation_action(plan(*selected))!='current':
            raise SetupError('Files were written but verification found remaining changes; review the preview before retrying')
        result={'install':'installed','update':'updated','repair':'repaired'}[action]
        messagebox.showinfo('Orbit '+result+' successfully',f'Orbit {result} successfully.\n\nRestart or refresh your selected coding hosts and verify orbit-core-native in their MCP lists.')
    except (SetupError,OSError,ValueError) as e:
        messagebox.showerror('Orbit setup blocked',str(e))
    finally:
        state['busy']=False
        for button in operation_buttons:
            button.config(state='normal')
        refresh_action()
def preview_remove():
    log.delete('1.0','end')
    try:
        path, hosts, selected_scope = args()
        changes, warnings = plan_uninstall(path, hosts, selected_scope)
        for item in changes:
            action = 'REMOVE' if item.replacement is None else 'EDIT'
            log.insert('end', f'{action:7} {item.description}\n  {item.path}\n')
        for warning in warnings:
            log.insert('end', warning+'\n')
        status.set(f'Uninstall preview: {len(changes)} verified Orbit targets. No files changed.')
    except (SetupError,OSError,ValueError) as e:
        messagebox.showerror('Uninstall preview blocked',str(e))

def remove():
    try:
        path, hosts, selected_scope = args()
        changes, warnings = plan_uninstall(path,hosts,selected_scope)
        preview_remove()
        if not changes:
            messagebox.showinfo('Nothing to uninstall','No verified Orbit-managed files found for selected scope/hosts. Existing customized files may require manual review.')
            return
        warning = '\n'.join(w for w in warnings if 'PRESERVE customized' in w)
        if not messagebox.askyesno('Confirm safe Orbit uninstall',
                f'Uninstall {len(changes)} verified Orbit targets for {", ".join(hosts)} in {selected_scope} scope?\n\n'
                'All affected files are backed up before deletion or editing. Memory, owner docs and shared runtime stay.\n'
                'Restart selected IDEs afterward.\n'+warning[:480]):
            return
        again, _ = plan_uninstall(path,hosts,selected_scope)
        if again != changes:
            raise SetupError('Uninstall plan changed; preview again')
        backup = apply_uninstall(again)
        status.set(f'Uninstalled {len(again)} Orbit targets. Backup: {backup}')
        refresh_action()
        messagebox.showinfo('Orbit uninstalled',
                            f'Backup: {backup}\n\nShared runtime and memories retained. Restart the affected coding hosts.')
    except (SetupError,OSError,ValueError) as e:
        messagebox.showerror('Orbit uninstall blocked',str(e))

buttons=ttk.Frame(r);buttons.pack(fill='x',padx=24,pady=(8,6))
operation_buttons=[]
def action_button(parent,text,command,width=24):
    button=ttk.Button(parent,text=text,command=command,style='Primary.TButton' if command==go else 'TButton')
    button.pack(side='left',padx=5)
    operation_buttons.append(button)
    return button

action_button(buttons,'Preview changes',preview)
primary=action_button(buttons,'Checking installation...',go)
action_button(buttons,'Check published updates',open_update_manager,20)
remove_buttons=ttk.Frame(r);remove_buttons.pack(fill='x',padx=24,pady=(0,18))
action_button(remove_buttons,'Preview uninstall',preview_remove,26)
action_button(remove_buttons,'Uninstall…',remove,39)
scope.trace_add('write',refresh_action)
project.trace_add('write',refresh_action)
for selected in selection.values():
    selected.trace_add('write',refresh_action)
refresh_action()
r.mainloop()
