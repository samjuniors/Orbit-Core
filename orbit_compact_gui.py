"""Orbit Core setup — focused, minimal Windows interface.

One primary action follows verified local state (Install / Update / Review).
A small disclosure reveals host, scope and uninstall controls. All file changes
still require an explicit preview and confirmation via the existing safe backend.
No Tkinter window or host configuration is changed on module import.
"""
from __future__ import annotations

import installer
import orbit_setup_ui_model as model

WINDOW_WIDTH = 504
COLLAPSED_HEIGHT = 365
EXPANDED_HEIGHT = 612

PALETTE = {
    "background": "#0D1422",
    "surface": "#172237",
    "surface_hover": "#1C2A42",
    "line": "#2B3B54",
    "text": "#F7F9FF",
    "secondary": "#AAB7CF",
    "quiet": "#8393AF",
    "accent": "#7187FF",
    "accent_hover": "#879AFF",
    "green": "#56D9AB",
    "warning": "#F2C079",
    "danger": "#F19491",
}


def rounded(canvas, x1, y1, x2, y2, radius, fill, outline=""):
    """Rounded polygon rendered with Tk's own vector primitives."""
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r,
        x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r,
        x1, y1+r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=18,
                                 fill=fill, outline=outline)


def launch():
    import tkinter as tk
    from tkinter import filedialog

    c = PALETTE
    app = tk.Tk()
    app.title("Orbit Core  ·  Setup")
    app.configure(bg=c["background"])
    app.resizable(False, False)
    app.geometry(f"{WINDOW_WIDTH}x{COLLAPSED_HEIGHT}")
    app.option_add("*Font", ("Segoe UI", 9))

    expanded = tk.BooleanVar(value=False)
    scope = tk.StringVar(value="machine")
    project = tk.StringVar(value="")
    detected = model.detected_hosts()
    hostvars = {key: tk.BooleanVar(value=enabled)
                for key, enabled in detected.items()}
    current_state = {"action": "review", "plan": None, "busy": False,
                     "error": "", "after_id": None}

    def label(parent, text="", *, size=10, color="text", bold=False, **kwargs):
        return tk.Label(parent, text=text, bg=parent["bg"], fg=c[color],
                        font=("Segoe UI", size, "bold" if bold else "normal"),
                        anchor="w", **kwargs)

    def button(parent, title, callback, *, accent=False, danger=False):
        bg = c["accent"] if accent else c["surface_hover"]
        fg = c["background"] if accent else (c["danger"] if danger else c["text"])
        control = tk.Button(
            parent, text=title, command=callback,
            bg=bg, fg=fg, activebackground=c["accent_hover"] if accent else c["line"],
            activeforeground=c["background"] if accent else c["text"],
            font=("Segoe UI", 10, "bold" if accent else "normal"),
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=16, pady=10, cursor="hand2", takefocus=True,
        )
        return control

    class RoundedPrimary(tk.Canvas):
        """Keyboard-accessible, high-contrast rounded primary action."""
        def __init__(self, parent, on_click):
            super().__init__(parent, height=52, bg=c["background"],
                             bd=0, highlightthickness=0, takefocus=True,
                             cursor="hand2")
            self.label = "Checking setup..."
            self.enabled = False
            self.hover = False
            self.on_click = on_click
            self.bind("<Configure>", lambda _: self.draw())
            self.bind("<Enter>", lambda _: self.set_hover(True))
            self.bind("<Leave>", lambda _: self.set_hover(False))
            self.bind("<Button-1>", lambda _: self.press())
            self.bind("<Return>", lambda _: self.press())
            self.bind("<space>", lambda _: self.press())
            self.bind("<FocusIn>", lambda _: self.draw())
            self.bind("<FocusOut>", lambda _: self.draw())

        def set_hover(self, hovered):
            self.hover = hovered
            self.draw()

        def set_action(self, title, enabled):
            self.label = title
            self.enabled = enabled
            self.configure(cursor="hand2" if enabled else "arrow")
            self.draw()

        def press(self):
            if self.enabled:
                self.on_click()

        def draw(self):
            self.delete("all")
            width = max(self.winfo_width(), 100)
            surface = (c["accent_hover"] if self.hover else c["accent"]) if self.enabled else c["line"]
            rounded(self, 1, 1, width-1, 50, 15, surface)
            self.create_text(width/2, 26, text=self.label,
                             fill=c["background"] if self.enabled else c["secondary"],
                             font=("Segoe UI", 11, "bold"))
            if self.focus_get() is self:
                rounded(self, 2, 2, width-2, 49, 14, "", c["text"])

    def show_message(heading, detail, *, error=False):
        popup = tk.Toplevel(app)
        popup.title("Orbit Core")
        popup.configure(bg=c["background"])
        popup.geometry("430x226")
        popup.resizable(False, False)
        popup.transient(app)
        popup.grab_set()
        accent = c["danger"] if error else c["green"]
        label(popup, ("!" if error else "✓") + "   " + heading,
              size=16, bold=True, color="text").pack(
                  fill="x", padx=24, pady=(29, 9))
        label(popup, detail, color="secondary", wraplength=375,
              justify="left").pack(fill="x", padx=24)
        footer = tk.Frame(popup, bg=c["background"])
        footer.pack(side="bottom", fill="x", padx=24, pady=20)
        close = button(footer, "Done", popup.destroy, accent=not error)
        close.pack(side="right")
        close.configure(fg=c["background"] if not error else accent)

    main = tk.Frame(app, bg=c["background"])
    main.pack(fill="both", expand=True, padx=28)

    top = tk.Frame(main, bg=c["background"])
    top.pack(fill="x", pady=(24, 18))
    mark = tk.Canvas(top, width=42, height=42, bg=c["background"],
                     borderwidth=0, highlightthickness=0)
    mark.pack(side="left")
    rounded(mark, 1, 1, 41, 41, 12, c["accent"])
    mark.create_oval(11, 14, 31, 28, outline=c["text"], width=2)
    mark.create_oval(18, 18, 24, 24, fill=c["text"], outline="")
    mark.create_arc(6, 8, 36, 34, start=40, extent=245,
                    outline=c["background"], style="arc", width=2)
    head_text = tk.Frame(top, bg=c["background"])
    head_text.pack(side="left", padx=(12, 0))
    label(head_text, "Orbit Core", size=17, bold=True).pack(anchor="w")
    label(head_text, "DESKTOP SETUP", size=8, color="quiet").pack(anchor="w", pady=(2, 0))
    version = label(top, "v" + installer.VERSION, size=9, color="quiet")
    version.pack(side="right", anchor="n", pady=7)

    # A vector-drawn status card keeps the compact view visually quiet.
    status_text = tk.StringVar(value="Checking this computer")
    app_text = tk.StringVar(value="Detecting coding tools...")
    card = tk.Canvas(main, height=113, bg=c["background"], bd=0,
                     highlightthickness=0)
    card.pack(fill="x")
    def draw_status_card(_=None):
        card.delete("all")
        width = max(card.winfo_width(), 400)
        rounded(card, 1, 1, width-1, 112, 18, c["surface"], c["line"])
        dot_color = c["warning"] if current_state["action"] == "review" else c["green"]
        card.create_oval(21, 28, 31, 38, fill=dot_color, outline="")
        card.create_text(42, 32, text=status_text.get(), anchor="w",
                         fill=c["text"], font=("Segoe UI", 12, "bold"))
        card.create_text(22, 72, text=app_text.get(), anchor="w",
                         fill=c["secondary"], width=width-46,
                         font=("Segoe UI", 10))
    card.bind("<Configure>", draw_status_card)
    status_text.trace_add("write", lambda *_: draw_status_card())
    app_text.trace_add("write", lambda *_: draw_status_card())

    info = tk.StringVar(value="Local install · Your project data stays yours")
    label(main, textvariable=info, color="quiet", size=9,
          wraplength=440).pack(fill="x", pady=(12, 16))

    def selected():
        return [key for key, var in hostvars.items() if var.get()]

    def selected_names():
        return [model.DISPLAY_NAMES[key] for key in selected()]

    def preview(action):
        return model.preview(action, selected(), scope.get(), project.get())

    def modal_review(review, *, delete_memory=False):
        """Small review dialog, with an optional detailed file list."""
        popup = tk.Toplevel(app)
        popup.title("Orbit Core  ·  Review")
        popup.geometry("480x315")
        popup.resizable(False, False)
        popup.configure(bg=c["background"])
        popup.transient(app)
        popup.grab_set()

        title = {"install": "Ready to install", "update": "Ready to update",
                 "uninstall": "Ready to uninstall", "clean": "Review clean reset"}
        label(popup, title.get(review.action, "Review changes"),
              size=16, bold=True).pack(fill="x", padx=23, pady=(20, 6))
        summary = (
            f"{len(review.changes)} file changes  ·  "
            + ("This computer" if review.scope == "machine" else "Selected project")
            + "\n"
            + (", ".join(model.DISPLAY_NAMES.get(h, h) for h in review.hosts))
        )
        label(popup, summary, size=9, color="secondary", justify="left",
              wraplength=420).pack(fill="x", padx=23)
        label(popup, ("SQLite, checkpoints and projects remain preserved."
                      if not delete_memory else
                      "This operation also removes selected saved Orbit memory."),
              size=9, color="danger" if delete_memory else "quiet",
              wraplength=410).pack(fill="x", padx=23, pady=(10, 0))

        detail_on = tk.BooleanVar(value=False)
        detail_holder = tk.Frame(popup, bg=c["background"])
        detail_holder.pack(fill="both", expand=True, padx=23, pady=(5, 0))
        detail = tk.Text(detail_holder, height=9, bg=c["surface"], fg=c["secondary"],
                         relief="flat", bd=0, padx=8, pady=8,
                         font=("Consolas", 8), wrap="none")
        detail.insert("1.0", model.preview_lines(review))
        detail.configure(state="disabled")
        def toggle_details():
            show = not detail_on.get()
            detail_on.set(show)
            if show:
                detail.pack(fill="both", expand=True, pady=(5, 0))
                popup.geometry("480x510" if review.action == "clean" else "480x465")
                details_btn.configure(text="Hide file details  ↑")
            else:
                detail.pack_forget()
                popup.geometry("480x370" if review.action == "clean" else "480x315")
                details_btn.configure(text="View file details  ↓")
        details_btn = tk.Button(
            detail_holder, text="View file details  ↓", command=toggle_details,
            bg=c["background"], fg=c["secondary"], activeforeground=c["text"],
            activebackground=c["background"], relief="flat", bd=0,
            cursor="hand2", anchor="w")
        details_btn.pack(anchor="w")

        typed = tk.StringVar(value="")
        if review.action == "clean":
            label(popup, "Type REMOVE ORBIT to confirm",
                  size=9, color="danger").pack(fill="x", padx=23)
            entry = tk.Entry(popup, textvariable=typed, bg=c["surface"],
                             fg=c["text"], insertbackground=c["text"],
                             relief="flat", font=("Segoe UI", 10))
            entry.pack(fill="x", padx=23, pady=(4, 7))
            popup.geometry("480x370")
        buttons = tk.Frame(popup, bg=c["background"])
        buttons.pack(side="bottom", fill="x", padx=23, pady=(8, 19))
        button(buttons, "Cancel", popup.destroy).pack(side="left")
        apply_button = button(buttons, "Confirm " + ("removal" if review.action in
                             ("clean", "uninstall") else review.action),
                             lambda: None, accent=True)
        apply_button.pack(side="right")

        def gate(*_):
            apply_button.configure(state=("normal" if review.action != "clean"
                                          or typed.get() == "REMOVE ORBIT" else "disabled"))
        typed.trace_add("write", gate)
        gate()
        def apply_clicked():
            apply_button.configure(state="disabled")
            try:
                model.apply(
                    review, confirmation=("REMOVE ORBIT" if review.action == "clean"
                                          else "CONFIRM"),
                    delete_memory=delete_memory,
                )
            except (installer.SetupError, OSError, ValueError) as exc:
                popup.destroy()
                show_message("Operation not completed", str(exc), error=True)
                schedule_refresh()
                return
            popup.destroy()
            show_message(
                "Setup complete",
                ("Restart your selected coding apps to load changes.\n"
                 + ("Orbit memory was preserved." if not delete_memory
                    else "Selected memory removal was requested.")))
            schedule_refresh()
        apply_button.configure(command=apply_clicked)

    def primary_clicked():
        if current_state["busy"] or current_state["action"] == "current":
            return
        try:
            action = ("update" if current_state["action"] == "update" else "install")
            review = preview(action)
        except (installer.SetupError, OSError, ValueError) as exc:
            show_message("Review needed", str(exc), error=True)
            return
        if not review.changes:
            show_message("Nothing to change", "The selected installation is already current.")
            return
        modal_review(review)

    primary = RoundedPrimary(main, primary_clicked)
    primary.pack(fill="x")

    more = tk.Button(
        main, text="More options  ↓",
        bg=c["background"], fg=c["secondary"],
        activebackground=c["background"], activeforeground=c["text"],
        bd=0, relief="flat", cursor="hand2", font=("Segoe UI", 9),
        command=lambda: toggle_options(), takefocus=True,
    )
    more.pack(pady=(12, 0))

    options = tk.Frame(main, bg=c["background"])
    separator = tk.Frame(options, bg=c["line"], height=1)
    separator.pack(fill="x", pady=(6, 13))
    label(options, "INSTALL LOCATION", color="quiet", size=8).pack(anchor="w")
    location = tk.Frame(options, bg=c["background"])
    location.pack(fill="x", pady=(6, 11))
    for key, title in (("machine", "This computer"), ("project", "One project")):
        tk.Radiobutton(
            location, text=title, variable=scope, value=key,
            bg=c["background"], fg=c["text"], selectcolor=c["surface"],
            activebackground=c["background"], activeforeground=c["text"],
            font=("Segoe UI", 9), cursor="hand2",
        ).pack(side="left", padx=(0, 18))
    path_row = tk.Frame(options, bg=c["background"])
    path_entry = tk.Entry(path_row, textvariable=project, bg=c["surface"],
                          fg=c["text"], insertbackground=c["text"],
                          relief="flat", font=("Segoe UI", 9))
    path_entry.pack(side="left", fill="x", expand=True, ipady=7)
    button(path_row, "Browse", lambda: project.set(
        filedialog.askdirectory(parent=app, title="Choose a project") or project.get()
    )).pack(side="left", padx=(6, 0))

    label(options, "CODING APPS", color="quiet", size=8).pack(anchor="w")
    hosts_row = tk.Frame(options, bg=c["background"])
    hosts_row.pack(fill="x", pady=(6, 4))
    for idx, (name, display) in enumerate(model.DISPLAY_NAMES.items()):
        tk.Checkbutton(
            hosts_row, text=display, variable=hostvars[name],
            bg=c["background"], fg=c["text"], selectcolor=c["surface"],
            activebackground=c["background"], activeforeground=c["text"],
            font=("Segoe UI", 9), cursor="hand2",
        ).grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 30), pady=2)

    utilities = tk.Frame(options, bg=c["background"])
    utilities.pack(fill="x", pady=(7, 0))
    def redetect():
        try:
            found = model.detected_hosts(project.get() if scope.get() == "project" else None)
        except (OSError, ValueError) as exc:
            show_message("Detection failed", str(exc), error=True)
            return
        for key, value in found.items():
            hostvars[key].set(value)
        schedule_refresh()
    button(utilities, "Detect again", redetect).pack(side="left")

    def uninstall_clicked():
        uninstall = tk.Toplevel(app)
        uninstall.title("Uninstall Orbit Core")
        uninstall.geometry("460x282")
        uninstall.resizable(False, False)
        uninstall.configure(bg=c["background"])
        uninstall.transient(app)
        uninstall.grab_set()
        label(uninstall, "Remove Orbit", size=16, bold=True).pack(
            fill="x", padx=22, pady=(20, 7))
        mode = tk.StringVar(value="uninstall")
        delete_memory = tk.BooleanVar(value=False)
        for key, title in (
            ("uninstall", "Remove integration, keep memory (recommended)"),
            ("clean", "Clean reset (all Orbit host integrations)"),
        ):
            tk.Radiobutton(
                uninstall, text=title, variable=mode, value=key,
                bg=c["background"], fg=c["text"], selectcolor=c["surface"],
                activebackground=c["background"], activeforeground=c["text"],
            ).pack(anchor="w", padx=17, pady=2)
        erase = tk.Checkbutton(
            uninstall, text="Also delete local memory and checkpoints",
            variable=delete_memory, bg=c["background"], fg=c["danger"],
            selectcolor=c["surface"], activebackground=c["background"],
            activeforeground=c["danger"])
        erase.pack(anchor="w", padx=33, pady=(7, 0))
        label(uninstall, "Backups are retained. Clean reset requires typed confirmation.",
              size=9, color="quiet", wraplength=405).pack(fill="x", padx=22, pady=(6, 4))
        def update_erase(*_):
            if mode.get() != "clean":
                delete_memory.set(False)
            erase.configure(state="normal" if mode.get() == "clean" else "disabled")
        mode.trace_add("write", update_erase)
        update_erase()
        controls = tk.Frame(uninstall, bg=c["background"])
        controls.pack(side="bottom", fill="x", padx=22, pady=15)
        button(controls, "Cancel", uninstall.destroy).pack(side="left")
        def proceed():
            try:
                review = model.preview(mode.get(), selected(), scope.get(), project.get(),
                                       delete_memory=delete_memory.get())
            except (installer.SetupError, OSError, ValueError) as exc:
                show_message("Uninstall blocked", str(exc), error=True)
                return
            uninstall.destroy()
            if not review.changes:
                show_message("Nothing to remove", "No verified Orbit installation changes found.")
                return
            modal_review(review, delete_memory=delete_memory.get())
        button(controls, "Review removal", proceed, accent=True).pack(side="right")

    button(utilities, "Uninstall...", uninstall_clicked, danger=True).pack(side="right")

    def toggle_options():
        expanded.set(not expanded.get())
        if expanded.get():
            options.pack(fill="x", pady=(0, 10))
        else:
            options.pack_forget()
        more.configure(text="Less options  ↑" if expanded.get() else "More options  ↓")
        app.geometry(f"{WINDOW_WIDTH}x"
                     f"{EXPANDED_HEIGHT if expanded.get() else COLLAPSED_HEIGHT}")

    def scope_changed(*_):
        if scope.get() == "project":
            path_row.pack(fill="x", pady=(0, 12), before=hosts_row)
        else:
            path_row.pack_forget()
        schedule_refresh()

    def refresh():
        current_state["after_id"] = None
        try:
            plan = preview("install")
            state = model.local_state(plan)
            name, message, available = model.presentation(state)
            current_state["action"] = state
            current_state["plan"] = plan
            current_state["error"] = ""
            status_text.set(message)
            primary.set_action(name + ("  →" if available else ""), available)
            names = selected_names()
            app_text.set(" · ".join(names) if names else "No coding apps selected")
            info.set("This computer · Local setup · Memory preserved"
                     if scope.get() == "machine" else
                     "One project · Local setup · Memory preserved")
        except (installer.SetupError, OSError, ValueError) as exc:
            current_state["action"] = "review"
            current_state["error"] = str(exc)
            status_text.set("Choose an app or review your settings")
            names = selected_names()
            app_text.set(" · ".join(names) if names else "No coding apps selected")
            primary.set_action("Review setup  →", True)
            info.set(str(exc)[:105])

    def schedule_refresh(*_):
        if current_state["after_id"] is not None:
            app.after_cancel(current_state["after_id"])
        current_state["after_id"] = app.after(80, refresh)

    for var in [scope, project, *hostvars.values()]:
        var.trace_add("write", schedule_refresh)
    scope.trace_add("write", scope_changed)
    scope_changed()
    app.after(80, refresh)
    app.mainloop()


if __name__ == "__main__":
    launch()
