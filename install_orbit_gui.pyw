"""Orbit GUI - single approved install for all current projects or one workspace."""
import tkinter as tk
from tkinter import filedialog, messagebox
from installer import plan, install, SetupError
from orbit_cli import detect
from orbit_update_gui import launch as open_update_manager
from installer import VERSION

r=tk.Tk();r.title('Orbit Universal Setup v'+VERSION);r.geometry('860x630')
tk.Label(r,text='ORBIT — one-click universal setup',font=('Arial',17,'bold')).pack(anchor='w',padx=18,pady=(12,5))
tk.Label(r,text='Choose availability everywhere on this computer, or only in one selected project. Uses existing coding host models; no other AI CLI.',wraplength=790,justify='left').pack(anchor='w',padx=18)
scope=tk.StringVar(value='machine');section=tk.Frame(r);section.pack(anchor='w',padx=18,pady=8)
for mode,title in [('machine','This computer (all projects)'),('project','One specific project')]:
    tk.Radiobutton(section,text=title,variable=scope,value=mode).pack(side='left',padx=8)
row=tk.Frame(r);row.pack(fill='x',padx=18,pady=7)
project=tk.StringVar();entry=tk.Entry(row,textvariable=project,width=85);entry.pack(side='left',fill='x',expand=True)
btn=tk.Button(row,text='Browse project',command=lambda: project.set(filedialog.askdirectory(title='Select project folder') or project.get()))
btn.pack(side='left',padx=4)
def update_scope(*_):
    x=scope.get()=='project';entry.config(state='normal' if x else 'disabled');btn.config(state='normal' if x else 'disabled')
scope.trace_add('write',update_scope);update_scope()
tk.Label(r,text='Select supported hosts (Claude Desktop regular chat uses a separate optional extension):').pack(anchor='w',padx=18)
detected={item['host'] for item in detect() if item['detected']}
selection={h:tk.BooleanVar(value=h in detected) for h in ('antigravity','codex','claude-code','vscode')}
choices=tk.Frame(r);choices.pack(anchor='w',padx=18,pady=4)
for key,title in [('antigravity','Antigravity'),('codex','Codex'),('claude-code','Claude Code'),('vscode','VS Code')]:
    tk.Checkbutton(choices,text=title,variable=selection[key]).pack(side='left',padx=8)
def refresh_detected():
    root=project.get() if scope.get()=='project' and project.get().strip() else None
    found={item['host'] for item in detect(root) if item['detected']}
    for host,selected in selection.items():selected.set(host in found)
    status.set('Host detection updated; CLI/config presence only, not a live MCP connection.')
tk.Button(choices,text='Detect hosts',command=refresh_detected).pack(side='left',padx=8)
tk.Label(r,text='Hosts selected by local CLI/config evidence; review or override manually.',fg='gray').pack(anchor='w',padx=18)
log=tk.Text(r,height=23,wrap='none');log.pack(padx=18,pady=8,fill='both',expand=True)
status=tk.StringVar(value='Ready. A safety confirmation is required before writing files.');tk.Label(r,textvariable=status,anchor='w').pack(fill='x',padx=18)
state={'preview':None,'choices':None}
def args():return (project.get() if scope.get()=='project' else None,[h for h,b in selection.items() if b.get()],scope.get())
def make_preview():
    log.delete('1.0','end')
    c=plan(*args())
    state['preview']=c;state['choices']=args()
    for item in c:log.insert('end',f'{item.action:7} {item.description}\n  {item.target}\n')
    status.set(f'Preview: {sum(item.action!="SKIP" for item in c)} proposed file changes, no installs executed.')
    return c
def preview():
    try:make_preview()
    except (SetupError,OSError) as e:state['preview']=None;messagebox.showerror('Preview blocked',str(e))
def go():
    try:
        c=make_preview()
        if not messagebox.askyesno('Authorize Orbit installation',f'Install Orbit in {scope.get()} scope for {", ".join(args()[1])}?\n\nOnly verified bundled files and MCP configurations are written. External skills/MCPs are NOT installed automatically.'):
            return
        again=plan(*args())
        if [(x.target,x.action,x.data) for x in c] != [(x.target,x.action,x.data) for x in again]: raise SetupError('Changes detected since preview; review again')
        paths=install(again)
        status.set(f'Orbit installed: {len(paths)} changes. Restart/refresh the selected hosts.')
        messagebox.showinfo('Orbit installed','Orbit setup completed. Restart or refresh your selected coding hosts; verify orbit-core-native in their MCP lists. No external marketplace software was installed.')
    except (SetupError,OSError) as e:messagebox.showerror('Installation blocked',str(e))
buttons=tk.Frame(r);buttons.pack(pady=11)
tk.Button(buttons,text='Preview changes',width=23,command=preview).pack(side='left',padx=8)
tk.Button(buttons,text='Install Orbit (one click)',width=28,command=go).pack(side='left',padx=8)
tk.Button(buttons,text='Manage updates',width=19,command=open_update_manager).pack(side='left',padx=8)
r.mainloop()
