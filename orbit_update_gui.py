"""Orbit Update Manager — opt-in local UI for published-release updates.

Only a human clicking Apply and confirming a dialog can invoke install logic.
Metadata checks run off the GUI thread. No OS background service or auto-apply.
"""
from __future__ import annotations

import contextlib
import io
import queue
import threading

import orbit_cli


def launch():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    app = tk.Tk()
    app.title("Orbit Update Manager")
    app.geometry("730x515")

    def label(value, **kwargs):
        return tk.Label(app, text=value, anchor="w", justify="left", **kwargs)

    label("Orbit — Update Manager", font=("Arial", 18, "bold")).pack(fill="x", padx=18, pady=(14, 5))
    label("Checks official published releases; never installs without your click and confirmation.",
          wraplength=680).pack(fill="x", padx=18)
    installed = orbit_cli.version()
    current = tk.StringVar(value="Installed Orbit: " + installed)
    label("", textvariable=current, font=("Arial", 11, "bold")).pack(fill="x", padx=18, pady=7)
    channel = tk.StringVar(value="candidate")
    scope = tk.StringVar(value="machine")
    project = tk.StringVar(value="")
    hosts = {h: tk.BooleanVar(value=h in {item["host"] for item in orbit_cli.detect()
                                        if item["detected"]}) for h in orbit_cli.HOSTS}

    options = tk.Frame(app)
    options.pack(fill="x", padx=18, pady=4)
    tk.Label(options, text="Release channel").pack(side="left")
    for value, title in (("candidate", "Candidate (0.x)"), ("stable", "Stable")):
        tk.Radiobutton(options, text=title, variable=channel, value=value).pack(side="left", padx=8)

    scopes = tk.Frame(app)
    scopes.pack(fill="x", padx=18)
    tk.Label(scopes, text="Update scope").pack(side="left")
    for value, title in (("machine", "This computer"), ("project", "One project")):
        tk.Radiobutton(scopes, text=title, variable=scope, value=value).pack(side="left", padx=8)

    path_row = tk.Frame(app)
    path_row.pack(fill="x", padx=18, pady=4)
    entry = tk.Entry(path_row, textvariable=project)
    entry.pack(side="left", fill="x", expand=True)
    browse = tk.Button(path_row, text="Choose project",
                       command=lambda: project.set(filedialog.askdirectory() or project.get()))
    browse.pack(side="left", padx=6)

    def on_scope(*_):
        active = scope.get() == "project"
        entry.configure(state="normal" if active else "disabled")
        browse.configure(state="normal" if active else "disabled")
    scope.trace_add("write", on_scope)
    on_scope()

    tk.Label(app, text="Update selected hosts (custom configurations are protected):",
             anchor="w").pack(fill="x", padx=18, pady=(8, 2))
    select_row = tk.Frame(app)
    select_row.pack(fill="x", padx=18)
    for host, flag in hosts.items():
        tk.Checkbutton(select_row, text=host, variable=flag).pack(side="left", padx=5)

    summary = tk.StringVar(value="Checking published releases…")
    label("", textvariable=summary, wraplength=685).pack(fill="x", padx=18, pady=8)
    output = tk.Text(app, height=8, wrap="word")
    output.pack(fill="both", expand=True, padx=18, pady=5)
    output.insert("end", "Orbit only updates installed local MCP/runtime files after approval.\n"
                        "SHA256 checks ZIP integrity, not publisher authenticity.\n"
                        "The host may need a restart to load the new version.\n")
    output.configure(state="disabled")

    controls = tk.Frame(app)
    controls.pack(pady=10)
    state = {"latest": None, "busy": False, "channel": None}
    events = queue.Queue()

    def add_log(text):
        output.configure(state="normal")
        output.insert("end", text.rstrip() + "\n")
        output.see("end")
        output.configure(state="disabled")

    def set_busy(value):
        state["busy"] = value
        check_btn.configure(state="disabled" if value else "normal")
        apply_btn.configure(state="disabled" if value or not state["latest"] else "normal")

    def check():
        if state["busy"]:
            return
        state["latest"] = None
        state["channel"] = channel.get()
        summary.set("Checking published " + channel.get() + " releases (read-only)…")
        set_busy(True)

        def run():
            try:
                info = orbit_cli.latest(state["channel"])
                events.put(("check_ok", info, state["channel"]))
            except Exception as exc:
                events.put(("check_fail", str(exc)))
        threading.Thread(target=run, name="orbit-gui-update-check", daemon=True).start()

    def apply():
        info = state["latest"]
        if state["busy"] or not info:
            return
        if channel.get() != state["channel"]:
            messagebox.showinfo("Check release first", "The channel changed; check again before installing.")
            return
        chosen = [name for name, flag in hosts.items() if flag.get()]
        if not chosen:
            messagebox.showerror("Select a host", "Select at least one host for this installation.")
            return
        target = project.get().strip() if scope.get() == "project" else ""
        if scope.get() == "project" and not target:
            messagebox.showerror("Choose project", "Select the existing project folder first.")
            return
        try:
            if (installed != "unknown" and
                    tuple(map(int, info["version"].split("."))) <=
                    tuple(map(int, installed.split(".")))):
                messagebox.showinfo("Up to date", "The installed version is already current or newer.")
                return
        except ValueError:
            pass
        message = ("Update Orbit v" + installed + " → v" + info["version"] + "?\n\n" +
                   "Hosts: " + ", ".join(chosen) +
                   "\nScope: " + (target or "This computer") +
                   "\n\nThis downloads a published installer and executes its code after "
                   "ZIP SHA256 and path checks. It makes backups of recognized stock files, "
                   "preserves unknown customizations, and can fail closed if conflicts exist. "
                   "Publisher authenticity is not independently signed. "
                   "Review the publisher before proceeding. Continue?")
        if not messagebox.askyesno("Authorize Orbit software update", message):
            return
        pinned = info["version"]
        set_busy(True)
        summary.set("Applying approved update to selected hosts…")
        args = ["update", "--channel", channel.get(), "--apply",
                "--expect-version", pinned, "--hosts", *chosen]
        if target:
            args.extend(["--project", target])

        def run():
            log = io.StringIO()
            try:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    rc = orbit_cli.main(args)
                events.put(("apply_done", rc, log.getvalue(), pinned))
            except Exception as exc:
                events.put(("apply_fail", type(exc).__name__ + ": " + str(exc)))
        # Applying a release writes multiple backed-up files; do not abandon a
        # partially applied upgrade if the user closes the manager window.
        threading.Thread(target=run, name="orbit-gui-approved-updater", daemon=False).start()

    check_btn = tk.Button(controls, text="Check for updates", width=22, command=check)
    check_btn.pack(side="left", padx=8)
    apply_btn = tk.Button(controls, text="Install update", width=22, command=apply, state="disabled")
    apply_btn.pack(side="left", padx=8)
    def close():
        if state["busy"]:
            messagebox.showinfo("Orbit updater busy",
                                "An update check or installation is still running. "
                                "Keep this window open until it finishes.")
            return
        app.destroy()

    tk.Button(controls, text="Close", width=12, command=close).pack(side="left", padx=8)
    app.protocol("WM_DELETE_WINDOW", close)

    def poll():
        try:
            while True:
                item = events.get_nowait()
                if item[0] == "check_ok":
                    info, chosen_channel = item[1:]
                    state["latest"] = info
                    state["channel"] = chosen_channel
                    if installed != "unknown" and tuple(map(int, info["version"].split("."))) <= tuple(map(int, installed.split("."))):
                        state["latest"] = None
                        summary.set("You are up to date for channel " + chosen_channel + ".")
                    else:
                        summary.set("Orbit v" + info["version"] + " is available — select hosts and choose Install update.")
                        add_log("Release: " + info["url"])
                    set_busy(False)
                elif item[0] == "check_fail":
                    summary.set("Unable to check updates; no changes made.")
                    add_log(item[1])
                    set_busy(False)
                elif item[0] == "apply_done":
                    _, rc, log, updated_version = item
                    add_log(log)
                    summary.set("Update installed. Restart the IDE/MCP host." if rc == 0
                                else "Update blocked; inspect conflicts and backups before retrying.")
                    if rc == 0:
                        current.set("Installed Orbit: " + updated_version + " (restart hosts)")
                        state["latest"] = None
                    set_busy(False)
                elif item[0] == "apply_fail":
                    summary.set("Update failed; no success claimed.")
                    add_log(item[1])
                    set_busy(False)
        except queue.Empty:
            pass
        app.after(150, poll)

    app.after(150, poll)
    app.after(300, check)
    app.mainloop()


if __name__ == "__main__":
    launch()
