"""ObsidianSync desktop client: tkinter GUI + background Flask server + QR pairing.

UI ported from the Claude-designed artifact (redesign-code/ObsidianSync.dc.html):
header with logo/title/status pill/icon buttons, a single state-driven QR/status panel
(waiting -> syncing -> complete/error), and Settings/Activity as modal dialogs.
"""
import secrets
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import config
import qr_util
import theme
from server import SyncServer


class AppState:
    def __init__(self, cfg: dict):
        self.vault_path = cfg["vault_path"]
        self.port = cfg["port"]
        self.device_name = cfg["device_name"]
        self.token = secrets.token_urlsafe(16)
        self.connected_ip = None
        self._ui_callback = None

    def on_event(self, name: str, **kwargs):
        if self._ui_callback:
            self._ui_callback(name, **kwargs)

    def set_ui_callback(self, cb):
        self._ui_callback = cb


class StatusPanel(tk.Frame):
    """The 280x280 rounded panel that shows the QR code, a spinner, a checkmark, or an error."""

    SIZE = 280

    def __init__(self, parent, on_retry):
        super().__init__(parent, bg=theme.CARD_BG)
        self.on_retry = on_retry
        self.canvas = tk.Canvas(
            self, width=self.SIZE, height=self.SIZE, bg=theme.CARD_BG, highlightthickness=0
        )
        self.canvas.pack()
        self._qr_photo = None
        self._spinner = None
        self._inner = None

    def _teardown(self):
        if self._spinner is not None:
            self._spinner.stop()
            self._spinner = None
        if self._inner is not None:
            self._inner.destroy()
            self._inner = None
        self.canvas.delete("all")

    def _embed(self, bg_color, y=None):
        inner = tk.Frame(self.canvas, bg=bg_color)
        self.canvas.create_window(self.SIZE / 2, self.SIZE / 2 if y is None else y, window=inner)
        self._inner = inner
        return inner

    def render_waiting(self, qr_image: Image.Image):
        self._teardown()
        theme.draw_rounded_rect(self.canvas, 0, 0, self.SIZE, self.SIZE, radius=20,
                                 fill="white", outline="")
        padded = qr_image.resize((self.SIZE - 40, self.SIZE - 40))
        self._qr_photo = ImageTk.PhotoImage(padded)
        self.canvas.create_image(self.SIZE / 2, self.SIZE / 2, image=self._qr_photo)

    def render_syncing(self, done: int, total: int):
        bg = "#2a2733"
        if self._spinner is None:
            self._teardown()
            theme.draw_rounded_rect(self.canvas, 0, 0, self.SIZE, self.SIZE, radius=20,
                                     fill=bg, outline="")
            inner = self._embed(bg)
            self._spinner = theme.Spinner(inner, size=64, parent_bg=bg)
            self._spinner.pack(pady=(0, 16))
            self._spinner.start()
            tk.Label(inner, text="Syncing files…", bg=bg, fg=theme.TEXT,
                      font=(theme.FONT_FAMILY, 15, "bold")).pack()
            self._progress_label = tk.Label(
                inner, text="", bg=bg, fg=theme.SUBTEXT, font=(theme.MONO_FAMILY, 12)
            )
            self._progress_label.pack(pady=(4, 0))
        pct = int((done / total) * 100) if total else 0
        self._progress_label.configure(text=f"{done}/{total} · {pct}%" if total else "…")

    def render_connected(self, ip: str):
        self._teardown()
        bg = "#2a2733"
        theme.draw_rounded_rect(self.canvas, 0, 0, self.SIZE, self.SIZE, radius=20,
                                 fill=bg, outline="")
        theme.draw_check_circle(self.canvas, self.SIZE / 2, 100, 36, theme.ACCENT)
        inner = self._embed(bg, y=190)
        tk.Label(inner, text="Device connected", bg=bg, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 16, "bold")).pack()
        subtitle = f"Paired with {ip}" if ip else "Ready to sync"
        tk.Label(inner, text=subtitle, bg=bg, fg=theme.SUBTEXT,
                  font=(theme.MONO_FAMILY, 12)).pack(pady=(4, 0))

    def render_complete(self, updated: int, deleted: int):
        self._teardown()
        bg = "#223b2e"
        theme.draw_rounded_rect(self.canvas, 0, 0, self.SIZE, self.SIZE, radius=20,
                                 fill=bg, outline="")
        theme.draw_check_circle(self.canvas, self.SIZE / 2, 100, 36, theme.SUCCESS)
        inner = self._embed(bg, y=190)
        tk.Label(inner, text="Vault synced", bg=bg, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 16, "bold")).pack()
        subtitle = (
            f"{updated} updated, {deleted} removed" if (updated or deleted) else "All files up to date"
        )
        tk.Label(inner, text=subtitle, bg=bg, fg="#9fd8bb",
                  font=(theme.FONT_FAMILY, 12)).pack(pady=(4, 0))

    def render_error(self, message: str):
        self._teardown()
        bg = "#3a271f"
        theme.draw_rounded_rect(self.canvas, 0, 0, self.SIZE, self.SIZE, radius=20,
                                 fill=bg, outline="")
        theme.draw_warning_circle(self.canvas, self.SIZE / 2, 92, 32, theme.ERROR)
        inner = self._embed(bg, y=175)
        tk.Label(inner, text="Sync failed", bg=bg, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 16, "bold")).pack()
        tk.Label(inner, text=message, bg=bg, fg="#f0b8a8", font=(theme.FONT_FAMILY, 12),
                  wraplength=220, justify="center").pack(pady=(4, 14))
        theme.RoundedButton(
            inner, "Retry", command=self.on_retry, bg="white", hover_bg="#eeeeee",
            fg="#5c2b2e", width=110, height=36, parent_bg=bg
        ).pack()


class ModalDialog(tk.Toplevel):
    """A small centered dialog styled to match the card's dark theme."""

    def __init__(self, parent, title: str, width=480):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.MODAL_BG)
        self.transient(parent)
        self.resizable(False, False)
        self.body = tk.Frame(self, bg=theme.MODAL_BG, padx=28, pady=24)
        self.body.pack(fill="both", expand=True)

        header = tk.Frame(self.body, bg=theme.MODAL_BG)
        header.pack(fill="x", pady=(0, 18))
        tk.Label(header, text=title, bg=theme.MODAL_BG, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 16, "bold")).pack(side="left")
        theme.IconButton(header, "✕", command=self.destroy, size=28, parent_bg=theme.MODAL_BG).pack(
            side="right"
        )

        self._parent = parent
        self._width = width

    def finalize(self):
        """Call after all body content has been added, so sizing/centering accounts for it."""
        self.update_idletasks()
        px, py = self._parent.winfo_rootx(), self._parent.winfo_rooty()
        pw, ph = self._parent.winfo_width(), self._parent.winfo_height()
        w = self._width
        self.geometry(f"{w}x{self.winfo_reqheight()}+{px + (pw - w) // 2}+{py + 60}")
        self.grab_set()


class ObsidianSyncApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ObsidianSync")
        self.root.geometry("820x640")
        self.root.minsize(600, 520)
        self.root.resizable(True, True)
        self.root.configure(bg=theme.CARD_BG)

        self.cfg = config.load()
        self.state = AppState(self.cfg)
        self.state.set_ui_callback(self._handle_server_event)

        self.server = SyncServer(self.state)
        self.server_thread = None
        self.view = "waiting"
        self.history = []
        self._last_result = (0, 0)
        self._last_error = ""
        self._activity_modal = None
        self._watchdog_id = None

        self._build_ui()
        self._start_server()
        self._render_view()

    # ---------- UI ----------
    def _build_ui(self):
        outer = tk.Frame(self.root, bg=theme.CARD_BG)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=theme.CARD_BG)
        header.pack(fill="x", padx=40, pady=(32, 8))

        left = tk.Frame(header, bg=theme.CARD_BG)
        left.pack(side="left", anchor="n")
        title_row = tk.Frame(left, bg=theme.CARD_BG)
        title_row.pack(anchor="w")

        logo = tk.Canvas(title_row, width=40, height=40, bg=theme.CARD_BG, highlightthickness=0)
        theme.draw_rounded_rect(logo, 0, 0, 40, 40, radius=12, fill=theme.ACCENT, outline="")
        theme.draw_rounded_rect(logo, 12, 12, 28, 28, radius=5, fill="white", outline="")
        logo.pack(side="left", padx=(0, 14))

        tk.Label(title_row, text="ObsidianSync", bg=theme.CARD_BG, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 22, "bold")).pack(side="left")
        tk.Label(left, text="Sync your vault to Android over Wi-Fi", bg=theme.CARD_BG,
                  fg=theme.SUBTEXT, font=(theme.FONT_FAMILY, 12)).pack(anchor="w", padx=(54, 0))

        right = tk.Frame(header, bg=theme.CARD_BG)
        right.pack(side="right", anchor="n")
        self.status_pill = theme.Pill(right, "Waiting for device…", "waiting", parent_bg=theme.CARD_BG)
        self.status_pill.pack(side="left", padx=(0, 10))
        theme.IconButton(right, "☰", command=self._open_activity, parent_bg=theme.CARD_BG).pack(
            side="left", padx=(0, 8)
        )
        theme.IconButton(right, "⚙", command=self._open_settings, parent_bg=theme.CARD_BG).pack(
            side="left"
        )

        middle = tk.Frame(outer, bg=theme.CARD_BG)
        middle.pack(expand=True)
        self.panel = StatusPanel(middle, on_retry=self._retry)
        self.panel.pack(pady=(20, 16))

        self.helper_var = tk.StringVar(value=theme.HELPER_TEXT["waiting"])
        tk.Label(middle, textvariable=self.helper_var, bg=theme.CARD_BG, fg=theme.SUBTEXT,
                  font=(theme.FONT_FAMILY, 12), wraplength=380, justify="center").pack(pady=(0, 24))

    def _render_view(self):
        state_label = {
            "waiting": "Waiting for device…",
            "connected": "Connected",
            "syncing": "Syncing…",
            "complete": "Sync complete",
            "error": "Connection error",
        }[self.view]
        self.status_pill.render(state_label, self.view)
        self.helper_var.set(theme.HELPER_TEXT[self.view])

        if self.view == "waiting":
            ip = config.get_local_ip()
            image = qr_util.make_pairing_qr(ip, self.state.port, self.state.token, self.state.device_name)
            self.panel.render_waiting(image)
        elif self.view == "connected":
            self.panel.render_connected(self.state.connected_ip or "")
        elif self.view == "syncing":
            self.panel.render_syncing(0, 0)
        elif self.view == "complete":
            self.panel.render_complete(*self._last_result)
        elif self.view == "error":
            self.panel.render_error(self._last_error or "Unknown error")

    # ---------- Modals ----------
    def _open_settings(self):
        modal = ModalDialog(self.root, "Settings", width=440)
        body = modal.body

        tk.Label(body, text="VAULT FOLDER", bg=theme.MODAL_BG, fg=theme.MUTED,
                  font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w")
        vault_var = tk.StringVar(value=self._vault_display())
        tk.Label(body, textvariable=vault_var, bg=theme.MODAL_BG, fg=theme.TEXT,
                  font=(theme.MONO_FAMILY, 11), wraplength=380, justify="left").pack(
            anchor="w", pady=(6, 16)
        )

        def choose_vault():
            path = filedialog.askdirectory(title="Select your Obsidian vault folder")
            if path:
                self.state.vault_path = path
                self.cfg["vault_path"] = path
                config.save(self.cfg)
                vault_var.set(self._vault_display())
                self._log(f"Vault set to: {path}")

        def new_qr():
            self._new_qr()

        btn_row = tk.Frame(body, bg=theme.MODAL_BG)
        btn_row.pack(fill="x", pady=(0, 20))
        theme.RoundedButton(
            btn_row, "Choose Vault…", command=choose_vault, bg=theme.ACCENT,
            hover_bg=theme.ACCENT_HOVER, width=190, height=40, parent_bg=theme.MODAL_BG
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))
        theme.RoundedButton(
            btn_row, "New QR Code", command=new_qr, bg=theme.GHOST_BTN_BG,
            hover_bg=theme.GHOST_BTN_HOVER, fg=theme.TEXT, width=150, height=40,
            parent_bg=theme.MODAL_BG
        ).pack(side="left", expand=True, fill="x", padx=(8, 0))

        tk.Label(body, text="NETWORK", bg=theme.MODAL_BG, fg=theme.MUTED,
                  font=(theme.FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(0, 10))
        net_row = tk.Frame(body, bg=theme.MODAL_BG)
        net_row.pack(anchor="w")
        tk.Label(net_row, text="Port", bg=theme.MODAL_BG, fg=theme.TEXT,
                  font=(theme.FONT_FAMILY, 13)).pack(side="left", padx=(0, 12))
        port_var = tk.StringVar(value=str(self.state.port))
        port_entry = tk.Entry(
            net_row, textvariable=port_var, width=8, bg=theme.FIELD_BG, fg=theme.TEXT,
            insertbackground=theme.TEXT, relief="flat", highlightthickness=1,
            highlightbackground=theme.FIELD_BORDER, font=(theme.MONO_FAMILY, 12)
        )
        port_entry.pack(side="left", padx=(0, 10), ipady=4)

        def apply_port():
            try:
                port = int(port_var.get())
            except ValueError:
                messagebox.showerror("Invalid port", "Port must be a number.")
                return
            self.cfg["port"] = port
            config.save(self.cfg)
            self._log(f"Port changed to {port}. Restarting server…")
            self._restart_server(port)
            self._render_view()

        theme.RoundedButton(
            net_row, "Apply", command=apply_port, bg=theme.GHOST_BTN_BG,
            hover_bg=theme.GHOST_BTN_HOVER, fg=theme.TEXT, width=80, height=34, radius=10,
            parent_bg=theme.MODAL_BG
        ).pack(side="left")

        modal.finalize()

    def _open_activity(self):
        modal = ModalDialog(self.root, "Activity", width=460)
        self._activity_modal = modal
        text = tk.Text(
            modal.body, height=12, bg=theme.MODAL_BG, fg=theme.SUBTEXT, relief="flat",
            font=(theme.MONO_FAMILY, 11), highlightthickness=0, wrap="word"
        )
        text.pack(fill="both", expand=True)
        text.tag_configure("time", foreground=theme.MUTED)
        text.tag_configure("error", foreground=theme.ERROR)
        text.tag_configure("success", foreground=theme.SUCCESS)
        text.tag_configure("device", foreground=theme.ACCENT)
        for entry in self.history:
            text.insert("end", f"{entry['time']}  ", "time")
            text.insert("end", entry["text"] + "\n", entry["tag"])
        text.configure(state="disabled")
        self._activity_text = text

        def on_close():
            self._activity_modal = None
            modal.destroy()

        modal.protocol("WM_DELETE_WINDOW", on_close)
        modal.finalize()

    def _vault_display(self) -> str:
        return self.cfg["vault_path"] or "(not set)"

    def _log(self, message: str, tag: str = ""):
        entry = {"time": time.strftime("%H:%M:%S"), "text": message, "tag": tag}
        self.history.append(entry)
        if self._activity_modal is not None and self._activity_modal.winfo_exists():
            self._activity_text.configure(state="normal")
            self._activity_text.insert("end", f"{entry['time']}  ", "time")
            self._activity_text.insert("end", message + "\n", tag)
            self._activity_text.see("end")
            self._activity_text.configure(state="disabled")

    # ---------- Actions ----------
    def _new_qr(self):
        self._disarm_watchdog()
        self.state.token = secrets.token_urlsafe(16)
        self.state.connected_ip = None
        self.view = "waiting"
        self._render_view()
        self._log("Generated a new pairing code.")

    def _retry(self):
        self._disarm_watchdog()
        self.view = "waiting"
        self._render_view()
        self._log("Ready for another attempt.")

    # ---------- Sync watchdog ----------
    # The phone reports progress as it downloads files, but if it disconnects mid-sync
    # (Wi-Fi drop, app killed, etc.) it never gets to call /sync-complete, so without this
    # the desktop would sit on "Syncing…" forever.
    SYNC_TIMEOUT_MS = 15000

    def _arm_watchdog(self):
        self._disarm_watchdog()
        self._watchdog_id = self.root.after(self.SYNC_TIMEOUT_MS, self._watchdog_timeout)

    def _disarm_watchdog(self):
        if self._watchdog_id is not None:
            self.root.after_cancel(self._watchdog_id)
            self._watchdog_id = None

    def _watchdog_timeout(self):
        self._watchdog_id = None
        if self.view != "syncing":
            return
        self._last_error = "Device disconnected mid-sync."
        self.view = "error"
        self._render_view()
        self._log("Sync failed: no response from device for 15s.", "error")

    # ---------- Server lifecycle ----------
    def _start_server(self):
        self.server_thread = threading.Thread(
            target=self.server.start, args=("0.0.0.0", self.state.port), daemon=True
        )
        self.server_thread.start()
        self._log(f"Server started on port {self.state.port}.")

    def _restart_server(self, new_port: int):
        self.server.stop()
        self.state.port = new_port
        self.server = SyncServer(self.state)
        self.server.state.set_ui_callback(self._handle_server_event)
        self._start_server()

    def _handle_server_event(self, name: str, **kwargs):
        def update():
            ip = kwargs.get("client_ip", self.state.connected_ip or "")
            if name == "device_connected":
                self.state.connected_ip = ip
                self.view = "connected"
                self._render_view()
                self._log(f"Device connected from {ip}", "device")
            elif name == "sync_started":
                self.state.connected_ip = ip
                self.view = "syncing"
                self._render_view()
                self._arm_watchdog()
                self._log("Sync requested by device.", "device")
            elif name == "sync_progress":
                done, total = kwargs.get("done", 0), kwargs.get("total", 0)
                if self.view != "syncing":
                    self.view = "syncing"
                    self._render_view()
                self.panel.render_syncing(done, total)
                self._arm_watchdog()
                if total and done == 0:
                    self._log(f"Transferring {total} file(s)…")
            elif name == "sync_finished":
                self._disarm_watchdog()
                status = kwargs.get("status", "success")
                if status == "success":
                    self._last_result = (kwargs.get("updated", 0), kwargs.get("deleted", 0))
                    self.view = "complete"
                    self._render_view()
                    updated, deleted = self._last_result
                    self._log(f"Sync complete: {updated} updated, {deleted} removed.", "success")
                else:
                    self._last_error = kwargs.get("message") or "Unknown error"
                    self.view = "error"
                    self._render_view()
                    self._log(f"Sync failed: {self._last_error}", "error")

        self.root.after(0, update)

    def on_close(self):
        self.server.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ObsidianSyncApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
