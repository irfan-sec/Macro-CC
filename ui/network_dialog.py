"""
Network & Proxy Settings dialog — dark-themed tabbed window
for managing proxy lists, Tor routing, and connection modes.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ui.theme import (
    BG_PRIMARY, BG_SECONDARY, ACCENT, ACCENT_HOVER,
    TEXT_COLOR, TEXT_DIM, BORDER_COLOR, SUCCESS, WARNING,
    FONT_MAIN, FONT_SMALL, FONT_BOLD, FONT_HEADER,
)
from features.proxy_manager import ProxyManager, Proxy


class NetworkDialog(tk.Toplevel):
    """Modal dialog for proxy / Tor / network configuration."""

    def __init__(self, parent, proxy_manager: ProxyManager):
        super().__init__(parent)
        self.pm = proxy_manager
        self.transient(parent)
        self.grab_set()

        self.title("🌐 Network & Proxy Settings")
        self.geometry("680x520")
        self.resizable(False, False)
        self.configure(bg=BG_PRIMARY)

        # ── ttk style overrides for Notebook tabs ──
        style = ttk.Style(self)
        style.configure("Dark.TNotebook", background=BG_PRIMARY,
                         borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                         background=BG_SECONDARY, foreground=TEXT_COLOR,
                         padding=[14, 6], font=FONT_MAIN)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])

        # ── Notebook ──
        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        self._build_mode_tab()
        self._build_proxy_tab()
        self._build_tor_tab()

        # ── Bottom buttons ──
        btn_bar = tk.Frame(self, bg=BG_PRIMARY)
        btn_bar.pack(fill="x", padx=8, pady=8)

        for txt, cmd in [("Cancel", self.destroy),
                         ("Apply", self._apply),
                         ("Save & Close", self._save_close)]:
            b = tk.Button(btn_bar, text=txt, command=cmd,
                          bg=BG_SECONDARY if txt == "Cancel" else ACCENT,
                          fg=TEXT_COLOR, font=FONT_MAIN, relief="flat",
                          padx=16, pady=4, cursor="hand2",
                          activebackground=ACCENT_HOVER,
                          activeforeground="white")
            b.pack(side="right", padx=4)

        self.focus_set()

    # ================================================================
    # TAB 1 — Mode & Rotation
    # ================================================================
    def _build_mode_tab(self):
        tab = tk.Frame(self._nb, bg=BG_PRIMARY)
        self._nb.add(tab, text="  Mode & Rotation  ")

        # ── Mode selector ──
        lbl = tk.Label(tab, text="Connection Mode", font=FONT_BOLD,
                       bg=BG_PRIMARY, fg=TEXT_COLOR)
        lbl.pack(anchor="w", padx=16, pady=(16, 4))

        self._mode_var = tk.StringVar(value=self.pm.mode)

        modes = [
            ("direct", "Direct Connection",
             "No proxy — use your real IP"),
            ("proxy", "Proxy List",
             "Route through your proxy servers"),
            ("tor", "Tor Network",
             "Anonymous routing via Tor (slower)"),
        ]

        for value, title, desc in modes:
            f = tk.Frame(tab, bg=BG_PRIMARY)
            f.pack(fill="x", padx=24, pady=2)
            rb = tk.Radiobutton(
                f, text=title, variable=self._mode_var, value=value,
                font=FONT_MAIN, bg=BG_PRIMARY, fg=TEXT_COLOR,
                selectcolor=BG_SECONDARY, activebackground=BG_PRIMARY,
                activeforeground=ACCENT, indicatoron=True, cursor="hand2",
                command=self._on_mode_change,
            )
            rb.pack(anchor="w")
            tk.Label(f, text=desc, font=FONT_SMALL,
                     bg=BG_PRIMARY, fg=TEXT_DIM).pack(anchor="w", padx=24)

        # ── Rotation settings ──
        self._rot_frame = tk.LabelFrame(
            tab, text=" Rotation Settings ",
            bg=BG_PRIMARY, fg=TEXT_DIM, font=FONT_SMALL,
            bd=1, relief="groove",
        )
        self._rot_frame.pack(fill="x", padx=16, pady=(12, 4))

        rot_row = tk.Frame(self._rot_frame, bg=BG_PRIMARY)
        rot_row.pack(fill="x", padx=12, pady=6)

        self._rot_var = tk.StringVar(value=self.pm.rotation_mode)
        for value, label in [("fixed", "Fixed interval"),
                             ("random", "Random interval"),
                             ("after_macro", "After each macro"),
                             ("manual", "Manual only")]:
            tk.Radiobutton(
                rot_row, text=label, variable=self._rot_var, value=value,
                font=FONT_SMALL, bg=BG_PRIMARY, fg=TEXT_COLOR,
                selectcolor=BG_SECONDARY, activebackground=BG_PRIMARY,
                activeforeground=ACCENT,
            ).pack(side="left", padx=6)

        int_row = tk.Frame(self._rot_frame, bg=BG_PRIMARY)
        int_row.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(int_row, text="Interval:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left")

        self._interval_var = tk.IntVar(value=self.pm.rotation_interval)
        tk.Spinbox(
            int_row, from_=30, to=3600, textvariable=self._interval_var,
            width=6, font=FONT_MAIN, bg=BG_SECONDARY, fg=TEXT_COLOR,
            buttonbackground=BG_SECONDARY, insertbackground=TEXT_COLOR,
            relief="flat",
        ).pack(side="left", padx=4)

        tk.Label(int_row, text="seconds", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left")

        btn_row = tk.Frame(self._rot_frame, bg=BG_PRIMARY)
        btn_row.pack(fill="x", padx=12, pady=(0, 8))

        tk.Button(btn_row, text="▶ Start Auto-Rotation",
                  command=self._start_rotation,
                  bg=SUCCESS, fg="white", font=FONT_SMALL,
                  relief="flat", padx=8, cursor="hand2",
                  activebackground="#27ae60").pack(side="left", padx=4)
        tk.Button(btn_row, text="⏹ Stop",
                  command=self._stop_rotation,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_SMALL,
                  relief="flat", padx=8, cursor="hand2").pack(side="left")

        # ── Current IP ──
        ip_frame = tk.Frame(tab, bg=BG_PRIMARY)
        ip_frame.pack(fill="x", padx=16, pady=(8, 0))

        self._ip_label = tk.Label(ip_frame, text="Current IP: detecting…",
                                  font=FONT_MAIN, bg=BG_PRIMARY, fg=TEXT_COLOR)
        self._ip_label.pack(side="left")

        tk.Button(ip_frame, text="🔄 Refresh", command=self._refresh_ip,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_SMALL,
                  relief="flat", padx=8, cursor="hand2").pack(side="left", padx=8)

        # Show/hide rotation frame based on mode
        self._on_mode_change()
        # Auto-detect IP
        self._refresh_ip()

    def _on_mode_change(self):
        if self._mode_var.get() == "proxy":
            self._rot_frame.pack(fill="x", padx=16, pady=(12, 4))
        else:
            self._rot_frame.pack_forget()

    def _start_rotation(self):
        self._apply()
        self.pm.start_auto_rotation()
        messagebox.showinfo("Rotation",
                            f"Auto-rotation started every {self.pm.rotation_interval}s",
                            parent=self)

    def _stop_rotation(self):
        self.pm.stop_auto_rotation()

    def _refresh_ip(self):
        self._ip_label.config(text="Current IP: detecting…")
        def worker():
            ip = self.pm.get_current_ip()
            try:
                self._ip_label.config(text=f"Current IP: {ip}")
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    # ================================================================
    # TAB 2 — Proxy List
    # ================================================================
    def _build_proxy_tab(self):
        tab = tk.Frame(self._nb, bg=BG_PRIMARY)
        self._nb.add(tab, text="  Proxy List  ")

        # ── Treeview ──
        tree_frame = tk.Frame(tab, bg=BG_PRIMARY)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        cols = ("#", "Type", "Host:Port", "Auth", "Status", "Speed", "CC")
        self._proxy_tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", height=8,
            style="Dark.Treeview",
        )
        col_widths = {"#": 30, "Type": 65, "Host:Port": 175,
                      "Auth": 40, "Status": 55, "Speed": 55, "CC": 35}
        for c in cols:
            self._proxy_tree.heading(c, text=c)
            self._proxy_tree.column(c, width=col_widths.get(c, 60),
                                    anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._proxy_tree.yview)
        self._proxy_tree.configure(yscrollcommand=vsb.set)

        self._proxy_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ── Buttons ──
        btn_row = tk.Frame(tab, bg=BG_PRIMARY)
        btn_row.pack(fill="x", padx=8, pady=4)

        buttons = [
            ("+ Add Proxy", self._show_add_form),
            ("✏ Edit", self._edit_proxy),
            ("🗑 Delete", self._delete_proxy),
            ("📋 Bulk Import", self._open_bulk_import),
            ("📂 Import File", self._import_proxies_file),
            ("✅ Test All", self._test_all_proxies),
        ]
        for txt, cmd in buttons:
            tk.Button(btn_row, text=txt, command=cmd,
                      bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_SMALL,
                      relief="flat", padx=8, pady=2, cursor="hand2",
                      activebackground=ACCENT).pack(side="left", padx=2)

        # ── Progress bar (hidden) ──
        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(tab, variable=self._progress_var,
                                              maximum=100)
        # Not packed initially

        # ── Add proxy form (hidden) ──
        self._add_frame = tk.LabelFrame(
            tab, text=" Add Proxy ", bg=BG_PRIMARY, fg=TEXT_DIM,
            font=FONT_SMALL, bd=1, relief="groove",
        )
        # Not packed initially

        # ROW 1 — Quick paste entry
        row1 = tk.Frame(self._add_frame, bg=BG_PRIMARY)
        row1.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(row1, text="Paste proxy (any format):", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left")
        self._add_paste = tk.Entry(row1, width=32, bg=BG_SECONDARY,
                                    fg=TEXT_COLOR, font=FONT_MAIN,
                                    insertbackground=TEXT_COLOR, relief="flat")
        self._add_paste.pack(side="left", padx=4)
        self._add_paste.bind("<KeyRelease>", self._on_paste_change)

        tk.Label(row1, text="Proto:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left", padx=(8, 0))
        self._add_proto = ttk.Combobox(
            row1, values=["socks5", "socks4", "http", "https"],
            width=7, state="readonly")
        self._add_proto.set("socks5")
        self._add_proto.pack(side="left", padx=2)

        tk.Label(row1, text="Port:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left", padx=(4, 0))
        self._add_port_lbl = tk.Label(row1, text="—", font=FONT_SMALL,
                                       bg=BG_PRIMARY, fg=TEXT_COLOR, width=6)
        self._add_port_lbl.pack(side="left")

        # ROW 2 — Collapsible auth + Add/Cancel buttons
        row2 = tk.Frame(self._add_frame, bg=BG_PRIMARY)
        row2.pack(fill="x", padx=8, pady=(0, 4))

        self._auth_visible = False
        self._auth_toggle_btn = tk.Button(
            row2, text="▶ Authentication (optional)",
            command=self._toggle_auth,
            bg=BG_PRIMARY, fg=TEXT_DIM, font=FONT_SMALL,
            relief="flat", cursor="hand2", bd=0,
            activebackground=BG_PRIMARY, activeforeground=ACCENT)
        self._auth_toggle_btn.pack(side="left")

        tk.Button(row2, text="+ Add Proxy", command=self._add_proxy,
                  bg=ACCENT, fg="white", font=FONT_SMALL,
                  relief="flat", padx=12, cursor="hand2",
                  activebackground=ACCENT_HOVER).pack(side="right", padx=2)
        tk.Button(row2, text="Cancel", command=self._hide_add_form,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_SMALL,
                  relief="flat", padx=8, cursor="hand2").pack(side="right", padx=2)

        # Auth fields (hidden initially)
        self._auth_frame = tk.Frame(self._add_frame, bg=BG_PRIMARY)

        tk.Label(self._auth_frame, text="Username:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left", padx=(8, 0))
        self._add_user = tk.Entry(self._auth_frame, width=14, bg=BG_SECONDARY,
                                   fg=TEXT_COLOR, font=FONT_MAIN,
                                   insertbackground=TEXT_COLOR, relief="flat")
        self._add_user.pack(side="left", padx=4)

        tk.Label(self._auth_frame, text="Password:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left", padx=(8, 0))
        self._add_pass = tk.Entry(self._auth_frame, width=14, bg=BG_SECONDARY,
                                   fg=TEXT_COLOR, font=FONT_MAIN, show="*",
                                   insertbackground=TEXT_COLOR, relief="flat")
        self._add_pass.pack(side="left", padx=4)

        self._refresh_proxy_tree()

    # ── Paste auto-detect ──
    def _on_paste_change(self, event=None):
        """Auto-detect protocol and port from pasted proxy string."""
        raw = self._add_paste.get().strip()
        if not raw:
            self._add_proto.set("socks5")
            self._add_port_lbl.config(text="—")
            return

        # Try URL format
        if "://" in raw:
            from urllib.parse import urlparse
            parsed = urlparse(raw)
            proto_raw = parsed.scheme.rstrip('h')
            if proto_raw in ("http", "https", "socks4", "socks5"):
                self._add_proto.set(proto_raw)
            port = parsed.port
            if port:
                self._add_port_lbl.config(text=str(port))
        else:
            parts = raw.split(":")
            if len(parts) >= 2:
                try:
                    port = int(parts[1])
                    self._add_port_lbl.config(text=str(port))
                    detected = self.pm._detect_protocol_from_port(port)
                    self._add_proto.set(detected)
                except ValueError:
                    pass

    def _toggle_auth(self):
        if self._auth_visible:
            self._auth_frame.pack_forget()
            self._auth_toggle_btn.config(text="▶ Authentication (optional)")
            self._auth_visible = False
        else:
            self._auth_frame.pack(fill="x", padx=8, pady=(0, 8))
            self._auth_toggle_btn.config(text="▼ Authentication (optional)")
            self._auth_visible = True

    def _refresh_proxy_tree(self):
        for item in self._proxy_tree.get_children():
            self._proxy_tree.delete(item)
        for i, p in enumerate(self.pm.proxies):
            status = "✅" if p.is_working else ("❌" if p.last_tested else "—")
            speed = f"{p.response_time}s" if p.response_time else "—"
            auth = "🔑" if p.username else ""
            country = p.country if p.country else "—"
            proto_upper = p.protocol.upper()
            host_port = f"{p.host}:{p.port}"

            # Determine tag for row background + protocol colour
            if p.is_working:
                row_tag = "working"
            elif p.last_tested:
                row_tag = "failed"
            else:
                row_tag = ""

            proto_tag = f"proto_{p.protocol}"
            tags = (row_tag, proto_tag) if row_tag else (proto_tag,)

            self._proxy_tree.insert(
                "", "end",
                values=(i + 1, proto_upper, host_port, auth,
                        status, speed, country),
                tags=tags,
            )

        # Row background colours
        self._proxy_tree.tag_configure("working", background="#1a3a2a")
        self._proxy_tree.tag_configure("failed", background="#3a1a1a")
        # Protocol type colours
        self._proxy_tree.tag_configure("proto_socks5", foreground="#5dade2")
        self._proxy_tree.tag_configure("proto_http", foreground="#2ecc71")
        self._proxy_tree.tag_configure("proto_https", foreground="#2ecc71")
        self._proxy_tree.tag_configure("proto_socks4", foreground="#f1c40f")

    def _show_add_form(self):
        self._add_frame.pack(fill="x", padx=8, pady=4)

    def _hide_add_form(self):
        self._add_frame.pack_forget()

    def _add_proxy(self):
        raw = self._add_paste.get().strip()
        if not raw:
            messagebox.showwarning("Missing", "Paste a proxy string.",
                                   parent=self)
            return

        # Let the smart parser handle it, then override protocol if user changed dropdown
        result = self.pm.parse_and_add(raw)
        if result is None:
            messagebox.showwarning("Invalid", "Could not parse proxy string.",
                                   parent=self)
            return

        # Override protocol with combobox selection
        result.protocol = self._add_proto.get()

        # Override auth if user filled in the auth fields
        if self._auth_visible:
            user = self._add_user.get().strip()
            pw = self._add_pass.get().strip()
            if user:
                result.username = user
                result.password = pw

        self.pm.save()

        # Clear form
        self._add_paste.delete(0, "end")
        self._add_port_lbl.config(text="—")
        self._add_proto.set("socks5")
        if self._auth_visible:
            self._add_user.delete(0, "end")
            self._add_pass.delete(0, "end")
        self._hide_add_form()
        self._refresh_proxy_tree()

    def _edit_proxy(self):
        sel = self._proxy_tree.selection()
        if not sel:
            return
        idx = self._proxy_tree.index(sel[0])
        if idx >= len(self.pm.proxies):
            return
        p = self.pm.proxies[idx]

        # Simple edit via dialog
        from tkinter import simpledialog
        new_host = simpledialog.askstring("Edit Proxy", "Host:",
                                          initialvalue=p.host, parent=self)
        if new_host is None:
            return
        new_port = simpledialog.askinteger("Edit Proxy", "Port:",
                                            initialvalue=p.port, parent=self)
        if new_port is None:
            return
        p.host = new_host
        p.port = new_port
        self.pm.save()
        self._refresh_proxy_tree()

    def _delete_proxy(self):
        sel = self._proxy_tree.selection()
        if not sel:
            return
        idx = self._proxy_tree.index(sel[0])
        self.pm.remove_proxy(idx)
        self._refresh_proxy_tree()

    def _import_proxies_file(self):
        """Import proxies from a text file using smart parser."""
        path = filedialog.askopenfilename(
            title="Import Proxy List",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self,
        )
        if not path:
            return
        added, failed = self.pm.import_from_file(path)
        self._refresh_proxy_tree()
        messagebox.showinfo(
            "Import",
            f"✅ Added {added} proxies" + (f", {failed} failed" if failed else ""),
            parent=self,
        )

    def _open_bulk_import(self):
        """Open a dark-themed bulk import dialog with a text area."""
        dlg = tk.Toplevel(self)
        dlg.title("📋 Bulk Import Proxies")
        dlg.geometry("520x400")
        dlg.resizable(False, False)
        dlg.configure(bg=BG_PRIMARY)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text="Paste proxies (one per line):", font=FONT_BOLD,
                 bg=BG_PRIMARY, fg=TEXT_COLOR).pack(anchor="w", padx=12, pady=(12, 4))

        text_frame = tk.Frame(dlg, bg=BG_PRIMARY)
        text_frame.pack(fill="both", expand=True, padx=12, pady=4)

        txt = tk.Text(text_frame, width=60, height=12,
                      bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_MAIN,
                      insertbackground=TEXT_COLOR, relief="flat",
                      selectbackground=ACCENT, selectforeground="white")
        txt.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(text_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        help_text = (
            "Supported formats:\n"
            "  • 1.2.3.4:1080\n"
            "  • 1.2.3.4:1080:user:pass\n"
            "  • socks5://1.2.3.4:1080\n"
            "  • socks5://user:pass@1.2.3.4:1080\n"
            "  • http://1.2.3.4:8080"
        )
        tk.Label(dlg, text=help_text, font=FONT_SMALL, bg=BG_PRIMARY,
                 fg=TEXT_DIM, justify="left").pack(anchor="w", padx=12, pady=4)

        result_label = tk.Label(dlg, text="", font=FONT_MAIN,
                                bg=BG_PRIMARY, fg=TEXT_COLOR)
        result_label.pack(anchor="w", padx=12)

        btn_row = tk.Frame(dlg, bg=BG_PRIMARY)
        btn_row.pack(fill="x", padx=12, pady=(4, 12))

        def do_import():
            content = txt.get("1.0", "end").strip()
            if not content:
                return
            added, failed = self.pm.import_from_text(content)
            self._refresh_proxy_tree()
            msg = f"✅ Added {added} proxies"
            if failed:
                msg += f", {failed} failed"
            result_label.config(text=msg, fg=SUCCESS if added else WARNING)

        tk.Button(btn_row, text="Import All", command=do_import,
                  bg=ACCENT, fg="white", font=FONT_MAIN, relief="flat",
                  padx=16, pady=4, cursor="hand2",
                  activebackground=ACCENT_HOVER).pack(side="left")
        tk.Button(btn_row, text="Close", command=dlg.destroy,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_MAIN,
                  relief="flat", padx=16, pady=4,
                  cursor="hand2").pack(side="left", padx=8)

    def _test_all_proxies(self):
        if not self.pm.proxies:
            return
        self._progress_bar.pack(fill="x", padx=8, pady=4)
        self._progress_var.set(0)
        total = len(self.pm.proxies)

        def on_progress(done, total_count):
            try:
                self._progress_var.set(done / total_count * 100)
                if done >= total_count:
                    self.after(500, self._on_test_done)
            except Exception:
                pass

        def refresh_after():
            self._refresh_proxy_tree()

        self.after(100, lambda: self.pm.test_all(on_progress=on_progress))

    def _on_test_done(self):
        self._progress_bar.pack_forget()
        self._refresh_proxy_tree()

    # ================================================================
    # TAB 3 — Tor Settings
    # ================================================================
    def _build_tor_tab(self):
        tab = tk.Frame(self._nb, bg=BG_PRIMARY)
        self._nb.add(tab, text="  Tor Settings  ")

        # ── Status indicator ──
        status_frame = tk.Frame(tab, bg=BG_PRIMARY)
        status_frame.pack(fill="x", padx=16, pady=(16, 8))

        self._tor_dot = tk.Canvas(status_frame, width=12, height=12,
                                   bg=BG_PRIMARY, highlightthickness=0)
        self._tor_dot.pack(side="left")
        self._tor_dot.create_oval(1, 1, 11, 11, fill=TEXT_DIM, outline="",
                                   tags="dot")

        self._tor_status = tk.Label(status_frame, text="Tor — Not Checked",
                                     font=FONT_BOLD, bg=BG_PRIMARY,
                                     fg=TEXT_COLOR)
        self._tor_status.pack(side="left", padx=8)

        # ── Instructions ──
        info_frame = tk.LabelFrame(tab, text=" Setup Instructions ",
                                    bg=BG_PRIMARY, fg=TEXT_DIM,
                                    font=FONT_SMALL, bd=1, relief="groove")
        info_frame.pack(fill="x", padx=16, pady=8)

        instructions = (
            "To use Tor, install one of these:\n\n"
            "  • Tor Browser (easiest) — download at torproject.org\n"
            "  • Tor Expert Bundle (background service)\n\n"
            "After installing, Tor Browser must be open and connected.\n"
            "Tor routes traffic through socks5h://127.0.0.1:9050"
        )
        tk.Label(info_frame, text=instructions, font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_COLOR, justify="left",
                 wraplength=600).pack(padx=12, pady=8, anchor="w")

        # ── Test button ──
        test_frame = tk.Frame(tab, bg=BG_PRIMARY)
        test_frame.pack(fill="x", padx=16, pady=4)

        tk.Button(test_frame, text="🔍 Test Tor Connection",
                  command=self._test_tor, bg=ACCENT, fg="white",
                  font=FONT_MAIN, relief="flat", padx=12, pady=4,
                  cursor="hand2",
                  activebackground=ACCENT_HOVER).pack(side="left")

        self._tor_result = tk.Label(test_frame, text="", font=FONT_SMALL,
                                     bg=BG_PRIMARY, fg=TEXT_COLOR)
        self._tor_result.pack(side="left", padx=12)

        # ── New Identity ──
        id_frame = tk.LabelFrame(tab, text=" New Tor Identity ",
                                  bg=BG_PRIMARY, fg=TEXT_DIM,
                                  font=FONT_SMALL, bd=1, relief="groove")
        id_frame.pack(fill="x", padx=16, pady=(12, 4))

        id_row = tk.Frame(id_frame, bg=BG_PRIMARY)
        id_row.pack(fill="x", padx=12, pady=8)

        tk.Label(id_row, text="Control Password:", font=FONT_SMALL,
                 bg=BG_PRIMARY, fg=TEXT_DIM).pack(side="left")
        self._tor_pw = tk.Entry(id_row, width=20, show="*",
                                 bg=BG_SECONDARY, fg=TEXT_COLOR,
                                 font=FONT_MAIN, insertbackground=TEXT_COLOR,
                                 relief="flat")
        self._tor_pw.pack(side="left", padx=4)

        tk.Button(id_row, text="🔄 Request New Identity",
                  command=self._new_tor_identity,
                  bg=BG_SECONDARY, fg=TEXT_COLOR, font=FONT_SMALL,
                  relief="flat", padx=8, cursor="hand2").pack(side="left", padx=8)

        self._identity_result = tk.Label(id_frame, text="", font=FONT_SMALL,
                                          bg=BG_PRIMARY, fg=TEXT_COLOR)
        self._identity_result.pack(padx=12, pady=(0, 8), anchor="w")

    def _test_tor(self):
        self._tor_result.config(text="Testing…", fg=TEXT_DIM)
        def worker():
            try:
                import requests
                r = requests.get(
                    "http://httpbin.org/ip",
                    proxies={"http": "socks5h://127.0.0.1:9050",
                             "https": "socks5h://127.0.0.1:9050"},
                    timeout=15,
                )
                ip = r.json().get("origin", "?")
                self.after(0, self._tor_test_ok, ip)
            except Exception as e:
                self.after(0, self._tor_test_fail, str(e))
        threading.Thread(target=worker, daemon=True).start()

    def _tor_test_ok(self, ip):
        self._tor_dot.delete("dot")
        self._tor_dot.create_oval(1, 1, 11, 11, fill=SUCCESS, outline="",
                                   tags="dot")
        self._tor_status.config(text="Tor — Running")
        self._tor_result.config(text=f"✅ Tor working — Your IP: {ip}",
                                 fg=SUCCESS)

    def _tor_test_fail(self, err):
        self._tor_dot.delete("dot")
        self._tor_dot.create_oval(1, 1, 11, 11, fill="#e74c3c", outline="",
                                   tags="dot")
        self._tor_status.config(text="Tor — Not Detected")
        self._tor_result.config(
            text="❌ Tor not reachable — Is Tor Browser open?",
            fg="#e74c3c")

    def _new_tor_identity(self):
        pw = self._tor_pw.get().strip()
        def worker():
            try:
                from stem import Signal
                from stem.control import Controller
                with Controller.from_port(port=9051) as ctrl:
                    ctrl.authenticate(password=pw or None)
                    ctrl.signal(Signal.NEWNYM)
                self.after(0, lambda: self._identity_result.config(
                    text="✅ New identity requested — IP will change shortly.",
                    fg=SUCCESS))
            except ImportError:
                self.after(0, lambda: self._identity_result.config(
                    text="❌ Install 'stem' package: pip install stem",
                    fg="#e74c3c"))
            except Exception as e:
                self.after(0, lambda err=e: self._identity_result.config(
                    text=f"❌ Failed: {err}", fg="#e74c3c"))
        threading.Thread(target=worker, daemon=True).start()

    # ================================================================
    # Apply / Save
    # ================================================================
    def _apply(self):
        self.pm.mode = self._mode_var.get()
        self.pm.rotation_mode = self._rot_var.get()
        self.pm.rotation_interval = self._interval_var.get()
        # Set env vars based on mode
        current = self.pm.get_current()
        if current:
            import os
            os.environ["HTTP_PROXY"] = current.get("http", "")
            os.environ["HTTPS_PROXY"] = current.get("https", "")
        else:
            import os
            os.environ.pop("HTTP_PROXY", None)
            os.environ.pop("HTTPS_PROXY", None)

    def _save_close(self):
        self._apply()
        self.pm.save()
        self.destroy()


def open_network_dialog(parent, proxy_manager: ProxyManager):
    """Convenience function to open the Network dialog."""
    NetworkDialog(parent, proxy_manager)
