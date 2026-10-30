"""Orbit Core — compact, preview-first desktop setup window.

No Tkinter root is created when the module is imported (safe for tests/CI).
Native plugin marketplace installation is a separate, host-specific acceptance
gate; this GUI manages existing verified Orbit MCP/skill/agent integration.
"""
from __future__ import annotations

from pathlib import Path

import installer
import orbit_setup_ui_model as model


def launch():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    app = tk.Tk()
    app.title(f"Orbit Core Setup  ·  {installer.VERSION}")
    app.geometry("704x538")
    app.minsize(640, 495)
    app.configure(bg="#101827")
    try:
        app.tk.call("tk", "scaling", 1.1)
    except tk.TclError:
        pass
    app.option_add("*Font", ("Segoe UI", 9))
    colors = {
        "bg": "#101827", "panel": "#182439", "text": "#F0F5FF",
        "muted": "#A8B5CA", "edge": "#334159", "accent": "#5C85F2",
        "disabled": "#33435E",
    }
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("TLabel", background=colors["panel"], foreground=colors["text"])
    style.configure("Muted.TLabel", background=colors["panel"], foreground=colors["muted"])
    style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"),
                    background=colors["bg"], foreground=colors["text"])
    style.configure("HeaderMuted.TLabel", background=colors["bg"], foreground=colors["muted"])
    style.configure("TCheckbutton", background=colors["panel"], foreground=colors["text"], padding=3)
    style.map("TCheckbutton", background=[("active", colors["panel"])])
    style.configure("TRadiobutton", background=colors["panel"], foreground=colors["text"])
    style.map("TRadiobutton", background=[("active", colors["panel"])])
    style.configure("TButton", padding=(12, 7))
    style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"),
                    background=colors["accent"], foreground="white")
    style.map("Accent.TButton",
              background=[("disabled", colors["disabled"]), ("active", "#3C68DE")],
              foreground=[("disabled", colors["muted"])])
    style.configure("TEntry", padding=5)

    header = tk.Frame(app, bg=colors["bg"])
    header.pack(fill="x", padx=26, pady=(18, 12))
    ttk.Label(header, text="Orbit Core", style="Header.TLabel").pack(anchor="w")
    ttk.Label(header, text=f"v{installer.VERSION}  •  Local AI workspace integration",
              style="HeaderMuted.TLabel").pack(anchor="w", pady=(2, 0))

    panel = ttk.Frame(app, style="Panel.TFrame", padding=18)
    panel.pack(fill="both", expand=True, padx=22, pady=(0, 12))
    ttk.Label(panel, text="Install for", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    scope = tk.StringVar(value="machine")
    scope_row = ttk.Frame(panel, style="Panel.TFrame")
    scope_row.pack(fill="x", pady=(4, 10))
    ttk.Radiobutton(scope_row, text="This computer", variable=scope,
                    value="machine").pack(side="left", padx=(0, 20))
    ttk.Radiobutton(scope_row, text="One project", variable=scope,
                    value="project").pack(side="left")

    project = tk.StringVar()
    pathrow = ttk.Frame(panel, style="Panel.TFrame")
    pathrow.pack(fill="x", pady=(0, 10))
    folder = ttk.Entry(pathrow, textvariable=project)
    folder.pack(side="left", fill="x", expand=True)
    browse = ttk.Button(pathrow, text="Browse", command=lambda: project.set(
        filedialog.askdirectory(parent=app, title="Choose an existing project") or project.get()))
    browse.pack(side="left", padx=(7, 0))
    def scope_changed(*_):
        enabled = scope.get() == "project"
        folder.configure(state="normal" if enabled else "disabled")
        browse.configure(state="normal" if enabled else "disabled")
    scope.trace_add("write", scope_changed)
    scope_changed()

    ttk.Label(panel, text="Detected coding hosts", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    hostvars = {}
    detected = model.detected_hosts()
    choices = ttk.Frame(panel, style="Panel.TFrame")
    choices.pack(fill="x", pady=(5, 4))
    for name, display in model.DISPLAY_NAMES.items():
        var = tk.BooleanVar(value=detected[name])
        hostvars[name] = var
        ttk.Checkbutton(choices, text=display, variable=var).pack(side="left", padx=(0, 12))

    note = tk.StringVar(value="Host detection is local. Choose any supported host.")
    ttk.Label(panel, textvariable=note, style="Muted.TLabel", wraplength=605).pack(anchor="w")
    ttk.Separator(panel).pack(fill="x", pady=(13, 11))
    status = tk.StringVar(value="Review the detected hosts and choose an action.")
    ttk.Label(panel, textvariable=status, wraplength=620).pack(anchor="w")

    actions = ttk.Frame(panel, style="Panel.TFrame")
    actions.pack(fill="x", pady=(15, 6))
    buttons = {}
    def selected():
        return [h for h, value in hostvars.items() if value.get()]
    def current_preview(action):
        return model.preview(action, selected(), scope.get(), project.get())

    def confirm_dialog(review, *, erase_memory=False):
        dialog = tk.Toplevel(app)
        dialog.title("Review Orbit changes")
        dialog.geometry("720x480")
        dialog.minsize(630, 395)
        dialog.transient(app)
        dialog.grab_set()
        dialog.configure(bg=colors["bg"])
        title = tk.Label(dialog, text=f"Review {review.action.title()}  ·  {len(review.changes)} entries",
                         font=("Segoe UI", 13, "bold"), bg=colors["bg"],
                         fg=colors["text"])
        title.pack(anchor="w", padx=18, pady=(16, 8))
        log = tk.Text(dialog, height=12, wrap="none", font=("Consolas", 9),
                      bg="#172339", fg="#E2E9F8", borderwidth=0, padx=10, pady=8)
        log.insert("1.0", model.preview_lines(review))
        log.configure(state="disabled")
        log.pack(fill="both", expand=True, padx=18)
        prompt = ("Type REMOVE ORBIT to confirm clean reset."
                  if review.action == "clean" else
                  "Confirm applying only these reviewed changes. All existing managed files are backed up.")
        tk.Label(dialog, text=prompt, bg=colors["bg"], fg=colors["muted"],
                 wraplength=655).pack(anchor="w", padx=18, pady=(10, 3))
        typed = tk.StringVar()
        if review.action == "clean":
            ttk.Entry(dialog, textvariable=typed).pack(fill="x", padx=18)
        row = tk.Frame(dialog, bg=colors["bg"])
        row.pack(fill="x", padx=18, pady=(12, 16))
        ttk.Button(row, text="Cancel", command=dialog.destroy).pack(side="right")
        do = ttk.Button(row, text="Apply changes", style="Accent.TButton", state="disabled")
        do.pack(side="right", padx=(0, 8))
        def gate(*_):
            do.configure(state="normal" if
                         (review.action != "clean" or typed.get() == "REMOVE ORBIT")
                         else "disabled")
        typed.trace_add("write", gate)
        gate()
        def apply_confirmed():
            do.configure(state="disabled")
            try:
                result = model.apply(review,
                                     confirmation="REMOVE ORBIT" if review.action == "clean"
                                     else "CONFIRM", delete_memory=erase_memory)
            except (installer.SetupError, OSError, ValueError) as err:
                messagebox.showerror("Orbit setup blocked",
                                     str(err) + "\n\nNo successful setup was reported. Review backups before retrying.",
                                     parent=dialog)
                gate()
                return
            dialog.destroy()
            status.set("Completed. Restart selected coding hosts to load the updated integration.")
            messagebox.showinfo("Orbit Core — completed",
                                "Operation completed successfully.\n\n"
                                f"Action: {review.action.title()}\n"
                                f"Hosts: {', '.join(review.hosts)}\n"
                                "Restart the selected coding hosts to apply changes.\n"
                                "Local memory was preserved." if not erase_memory else
                                "Clean reset completed. Review the recovery backup before restarting.",
                                parent=app)
            refresh()
        do.configure(command=apply_confirmed)

    def run(action):
        try:
            review = current_preview(action)
            if not review.changes:
                messagebox.showinfo("Nothing to change", "No applicable Orbit-managed changes were found.", parent=app)
                return
            confirm_dialog(review)
        except (installer.SetupError, OSError, ValueError) as err:
            status.set("Review required: " + str(err))
            messagebox.showwarning("Review required", str(err), parent=app)

    def uninstall():
        dialog = tk.Toplevel(app)
        dialog.title("Uninstall Orbit Core")
        dialog.geometry("520x310")
        dialog.resizable(False, False)
        dialog.transient(app)
        dialog.grab_set()
        dialog.configure(bg=colors["bg"])
        tk.Label(dialog, text="Choose what to remove", bg=colors["bg"],
                 fg=colors["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=20, pady=(18, 8))
        choice = tk.StringVar(value="preserve")
        erase = tk.BooleanVar(value=False)
        for value, label in [
            ("preserve", "Uninstall selected hosts · keep SQLite, checkpoints and projects"),
            ("clean", "Clean reset · remove Orbit's registered components and runtime"),
        ]:
            tk.Radiobutton(dialog, text=label, variable=choice, value=value,
                           bg=colors["bg"], fg=colors["text"], selectcolor=colors["panel"],
                           activebackground=colors["bg"], activeforeground=colors["text"],
                           anchor="w").pack(fill="x", padx=16, pady=3)
        memory = tk.Checkbutton(dialog, text="Also remove local Orbit memory (destructive)",
                                variable=erase, bg=colors["bg"], fg="#F6C4B8",
                                selectcolor=colors["panel"], activebackground=colors["bg"])
        memory.pack(anchor="w", padx=37, pady=(6, 0))
        note_label = tk.Label(dialog, text="Backups are kept. Other projects are not automatically scanned.",
                              bg=colors["bg"], fg=colors["muted"], wraplength=455)
        note_label.pack(anchor="w", padx=20, pady=(10, 8))
        def gate(*_):
            if choice.get() != "clean":
                erase.set(False)
            memory.configure(state="normal" if choice.get() == "clean" else "disabled")
        choice.trace_add("write", gate)
        gate()
        row = ttk.Frame(dialog)
        row.pack(fill="x", padx=20, pady=(2, 10))
        ttk.Button(row, text="Cancel", command=dialog.destroy).pack(side="right")
        def continue_uninstall():
            try:
                review = current_preview("clean" if choice.get()=="clean" else "uninstall")
                if choice.get() == "clean":
                    review = model.preview("clean", selected(), scope.get(), project.get(),
                                           delete_memory=erase.get())
            except (installer.SetupError, ValueError, OSError) as err:
                messagebox.showerror("Uninstall unavailable", str(err), parent=dialog)
                return
            dialog.destroy()
            if not review.changes:
                messagebox.showinfo("Nothing to remove", "No verified Orbit-managed files to remove.", parent=app)
            else:
                confirm_dialog(review, erase_memory=erase.get())
        ttk.Button(row, text="Review removal", style="Accent.TButton",
                   command=continue_uninstall).pack(side="right", padx=(0, 9))

    def refresh(*_):
        for btn in buttons.values():
            btn.configure(state="disabled")
        try:
            review = current_preview("install")
            state = model.local_state(review)
            can_install = state == "install"
            can_update = state == "update"
            buttons["install"].configure(state="normal" if can_install else "disabled")
            buttons["update"].configure(state="normal" if can_update else "disabled")
            buttons["uninstall"].configure(state="normal")
            texts = {
                "install": "Fresh installation available for selected hosts.",
                "update": "This bundled source changes the existing integration; review Update.",
                "current": "Selected Orbit integration matches this local package.",
            }
            status.set(texts[state])
        except (installer.SetupError, ValueError, OSError) as err:
            status.set("Review required: " + str(err))
            buttons["uninstall"].configure(state="normal")

    buttons["install"] = ttk.Button(actions, text="Install", style="Accent.TButton",
                                     command=lambda: run("install"))
    buttons["update"] = ttk.Button(actions, text="Update", style="Accent.TButton",
                                    command=lambda: run("update"))
    buttons["uninstall"] = ttk.Button(actions, text="Uninstall", command=uninstall)
    for button in buttons.values():
        button.pack(side="left", expand=True, fill="x", padx=(0, 7))

    row = ttk.Frame(panel, style="Panel.TFrame")
    row.pack(fill="x", pady=(6, 2))
    def redetect():
        found = model.detected_hosts(project.get() if scope.get()=="project" else None)
        for host, value in found.items():
            hostvars[host].set(value)
        note.set("Detection refreshed. Host selection can be adjusted before applying changes.")
        refresh()
    ttk.Button(row, text="Detect again", command=redetect).pack(side="left")
    ttk.Label(row, text="Source installation · no remote server required",
              style="Muted.TLabel").pack(side="right")
    for var in [scope, project, *hostvars.values()]:
        var.trace_add("write", lambda *_: app.after_idle(refresh))
    footer = tk.Label(app,
                      text="Native host-plugin packages require separate activation and migration validation.",
                      font=("Segoe UI", 8), bg=colors["bg"], fg=colors["muted"])
    footer.pack(fill="x", padx=24, pady=(0, 13))
    app.after(50, refresh)
    app.mainloop()


if __name__ == "__main__":
    launch()
