"""
Coffee & Axl — StatsPage
Pagina de statistici zilnice integrata in dashboard.
Conține: timp laptop, pauze, pomodoro, apă, grafic ore, top site-uri.
"""
import tkinter as tk
import customtkinter as ctk
from datetime import date, datetime
from utils.theme import *

_C_BLUE   = "#4C8CE4"
_C_GREEN  = "#3DB85C"
_C_AMBER  = "#F59E0B"
_C_PURPLE = "#8B5CF6"
_C_TEAL   = "#14B8A6"
_BAR_BG   = "#EEF3FB"


def _fmt_time(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "0 min"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}min" if m else f"{h}h"
    return f"{m} min"


class StatsPage(ctk.CTkFrame):
    """
    Frame integrat in DashboardPacient._build_page_stats().
    Apeleaza .refresh() la fiecare afisare.
    """

    def __init__(self, parent, engine, user_id: int,
                 activity_monitor=None):
        super().__init__(parent, fg_color=OFF_WHITE, corner_radius=0)
        self.engine       = engine
        self.user_id      = user_id
        self._monitor     = activity_monitor
        self._water_today = 0.0
        self._refresh_job = None

        self._build_ui()
        self.after(200, self.refresh)  # incarca datele dupa ce UI e gata

    # ═════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ═════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent", corner_radius=0)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.columnconfigure(0, weight=1)
        self._scroll = scroll

        self._build_date_bar(scroll)
        self._build_cards(scroll)
        self._build_water(scroll)
        self._build_chart(scroll)
        self._build_top_sites(scroll)

    # ─── Bara data + refresh ──────────────────────────────────────────────────

    def _build_date_bar(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(18, 4))

        self._date_lbl = ctk.CTkLabel(
            row, text="",
            font=("Arial", 12, "bold"),
            text_color=TEXT_LIGHT)
        self._date_lbl.pack(side="left")

        ctk.CTkButton(
            row, text="↺ Actualizează",
            width=120, height=30, corner_radius=8,
            fg_color="#EEF3FB", hover_color="#DCE6F5",
            text_color=NAVY, font=("Arial", 11, "bold"),
            command=self.refresh,
        ).pack(side="right")

    # ─── 4 carduri principale ─────────────────────────────────────────────────

    def _build_cards(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=(8, 0))

        meta = [
            ("⏱",  "Timp la laptop",   "timp_lbl",    _C_BLUE,   "#EDF4FF"),
            ("☕",  "Pauze luate",      "pauze_lbl",   _C_GREEN,  "#EDFAF1"),
            ("🍅",  "Sesiuni Pomodoro", "pomodoro_lbl", _C_PURPLE, "#F5F0FF"),
            ("🌐",  "Site-uri vizitate","site_lbl",    _C_TEAL,   "#F0FAFA"),
        ]
        self._val_labels = {}

        for icon, title, attr, color, bg in meta:
            card = ctk.CTkFrame(
                row, fg_color=bg,
                corner_radius=14,
                border_width=1, border_color="#DCE6F5",
                height=110,
            )
            card.pack(side="left", padx=5, expand=True, fill="both")
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=icon,
                         font=("Arial", 24)).pack(pady=(14, 2))
            lbl = ctk.CTkLabel(card, text="—",
                               font=("Georgia", 20, "bold"),
                               text_color=color)
            lbl.pack()
            self._val_labels[attr] = lbl
            ctk.CTkLabel(card, text=title,
                         font=("Arial", 10),
                         text_color=TEXT_LIGHT).pack(pady=(2, 10))

    # ─── Tracker apă ─────────────────────────────────────────────────────────

    def _build_water(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=14,
            border_width=1, border_color="#BFE8FF")
        card.pack(fill="x", padx=24, pady=(12, 0))

        # Titlu secțiune
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkFrame(hdr, width=3, height=18,
                     fg_color=_C_BLUE, corner_radius=2).pack(
            side="left", padx=(0, 8))
        ctk.CTkLabel(hdr, text="💧  Apă băută azi",
                     font=("Georgia", 13, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        # Valoare + target
        val_row = ctk.CTkFrame(card, fg_color="transparent")
        val_row.pack(fill="x", padx=18, pady=(0, 4))

        self._water_lbl = ctk.CTkLabel(
            val_row, text="0.0 L",
            font=("Georgia", 22, "bold"),
            text_color=_C_BLUE)
        self._water_lbl.pack(side="left", padx=(0, 10))

        self._water_sub = ctk.CTkLabel(
            val_row, text="din 2.0 L recomandat",
            font=("Arial", 11), text_color=TEXT_LIGHT)
        self._water_sub.pack(side="left")

        # Progress bar
        self._water_bar = ctk.CTkProgressBar(
            card, height=10, corner_radius=5,
            fg_color="#E0F0FF", progress_color=_C_BLUE)
        self._water_bar.pack(fill="x", padx=18, pady=(2, 10))
        self._water_bar.set(0)

        # Butoane cantitate
        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 14))

        ctk.CTkLabel(btn_row, text="Adaugă:",
                     font=("Arial", 11, "bold"),
                     text_color=TEXT_MID).pack(side="left",
                                               padx=(0, 8))
        for label, qty in [("🥤 250ml", 0.25), ("🧴 500ml", 0.50),
                            ("🍶 750ml", 0.75), ("🫙 1L", 1.00)]:
            ctk.CTkButton(
                btn_row, text=label,
                width=82, height=32, corner_radius=8,
                fg_color="#E0F4FF", hover_color="#BFE8FF",
                text_color=_C_BLUE, font=("Arial", 11, "bold"),
                command=lambda q=qty: self._add_water(q),
            ).pack(side="left", padx=3)

        ctk.CTkButton(
            btn_row, text="⟲ Reset",
            width=70, height=32, corner_radius=8,
            fg_color="#F0F4F8", hover_color=GRAY_LIGHT,
            text_color=TEXT_LIGHT, font=("Arial", 11),
            command=self._reset_water,
        ).pack(side="right")

    # ─── Grafic bare pe ore ───────────────────────────────────────────────────

    def _build_chart(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=14,
            border_width=1, border_color=GRAY_LIGHT)
        card.pack(fill="x", padx=24, pady=(12, 0))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkFrame(hdr, width=3, height=18,
                     fg_color=_C_AMBER, corner_radius=2).pack(
            side="left", padx=(0, 8))
        ctk.CTkLabel(hdr, text="🕐  Activitate pe ore",
                     font=("Georgia", 13, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        self._chart_host = ctk.CTkFrame(
            card, fg_color="transparent", height=120)
        self._chart_host.pack(fill="x", padx=18, pady=(0, 14))
        self._chart_host.pack_propagate(False)

    # ─── Top site-uri ─────────────────────────────────────────────────────────

    def _build_top_sites(self, parent):
        card = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=14,
            border_width=1, border_color=GRAY_LIGHT)
        card.pack(fill="x", padx=24, pady=(12, 24))

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkFrame(hdr, width=3, height=18,
                     fg_color=_C_TEAL, corner_radius=2).pack(
            side="left", padx=(0, 8))
        ctk.CTkLabel(hdr, text="🌐  Top site-uri / aplicații azi",
                     font=("Georgia", 13, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        self._sites_host = ctk.CTkFrame(
            card, fg_color="transparent")
        self._sites_host.pack(fill="x", padx=18, pady=(0, 14))

    # ═════════════════════════════════════════════════════════════════════════
    # DATE
    # ═════════════════════════════════════════════════════════════════════════

    def refresh(self):
        """Reîncarcă toate datele din DB + monitor live."""
        if not hasattr(self, "_val_labels") or not self._val_labels:
            return

        today = date.today()
        try:
            self._date_lbl.configure(
                text=today.strftime("%A, %d %B %Y"))
        except Exception:
            pass

        # Citire DB
        from database import get_session, DailyStats, ActivityLog
        from sqlalchemy import and_

        sess = get_session(self.engine)
        try:
            stat = sess.query(DailyStats).filter_by(
                id_utilizator=self.user_id,
                data=today,
            ).first()

            timp_sec = int(getattr(stat, "timp_total_sec",  0) or 0)
            pauze    = int(getattr(stat, "pauze_luate",     0) or 0)
            pomodoro = int(getattr(stat, "sesiuni_pomodoro",0) or 0)
            site_uri = int(getattr(stat, "site_uri_vizitate",0) or 0)
            litri    = float(getattr(stat, "litri_apa",    0.0) or 0.0)

            # Timp live din monitor dacă disponibil
            if self._monitor:
                try:
                    timp_sec = max(
                        timp_sec,
                        self._monitor.get_today_total_time())
                    ms = self._monitor.get_today_stats()
                    site_uri = max(site_uri,
                                   ms.get("site_uri", 0))
                except Exception:
                    pass

            self._val_labels["timp_lbl"].configure(
                text=_fmt_time(timp_sec))
            self._val_labels["pauze_lbl"].configure(
                text=str(pauze))
            self._val_labels["pomodoro_lbl"].configure(
                text=str(pomodoro))
            self._val_labels["site_lbl"].configure(
                text=str(site_uri))

            self._water_today = litri
            self._refresh_water_ui()

            # Logs pentru grafic și top site-uri
            logs = sess.query(ActivityLog).filter(
                and_(
                    ActivityLog.id_utilizator == self.user_id,
                    ActivityLog.inceput_la >= datetime.combine(
                        today, datetime.min.time()),
                )
            ).all()

            self._draw_chart(logs)
            self._draw_top_sites(logs)

        finally:
            sess.close()

    # ─── Apă ─────────────────────────────────────────────────────────────────

    def _refresh_water_ui(self):
        target = 2.0
        val    = self._water_today
        pct    = min(val / target, 1.0)
        try:
            self._water_lbl.configure(
                text=f"{val:.1f} L",
                text_color=_C_GREEN if pct >= 1.0 else _C_BLUE)
            self._water_bar.set(pct)
            if pct >= 1.0:
                self._water_sub.configure(
                    text="✓ Obiectiv atins! 🎉",
                    text_color=_C_GREEN)
            else:
                self._water_sub.configure(
                    text=f"din {target:.0f}L — mai ai "
                         f"{target - val:.1f}L",
                    text_color=TEXT_LIGHT)
        except Exception:
            pass

    def _add_water(self, qty: float):
        self._water_today = round(self._water_today + qty, 2)
        self._save_water(self._water_today)
        self._refresh_water_ui()
        from utils.ui_utils import show_toast
        show_toast(self.winfo_toplevel(),
                   f"+{int(qty*1000)}ml adăugat 💧",
                   kind="success", duration_ms=1800)

    def _reset_water(self):
        self._water_today = 0.0
        self._save_water(0.0)
        self._refresh_water_ui()

    def _save_water(self, litri: float):
        try:
            from database import get_session, DailyStats
            sess = get_session(self.engine)
            try:
                today = date.today()
                stat  = sess.query(DailyStats).filter_by(
                    id_utilizator=self.user_id,
                    data=today,
                ).first()
                if not stat:
                    stat = DailyStats(
                        id_utilizator=self.user_id,
                        data=today,
                        timp_total_sec=0, pauze_luate=0,
                        litri_apa=0.0)
                    sess.add(stat)
                stat.litri_apa = litri
                sess.commit()
            finally:
                sess.close()
        except Exception as e:
            print(f"[STATS] water save: {e}")

    # ─── Grafic ore ───────────────────────────────────────────────────────────

    def _draw_chart(self, logs: list):
        for w in self._chart_host.winfo_children():
            w.destroy()

        by_hour = [0] * 24
        for log in logs:
            try:
                h = log.inceput_la.hour
                by_hour[h] = min(
                    by_hour[h] + (log.durata_secunde or 0), 3600)
            except Exception:
                pass

        now_h    = datetime.now().hour
        max_sec  = max(max(by_hour), 1)
        hours    = list(range(7, 23))

        wrap = ctk.CTkFrame(
            self._chart_host, fg_color="transparent")
        wrap.pack(fill="both", expand=True)

        for h in hours:
            sec    = by_hour[h]
            pct    = sec / max_sec
            bar_h  = max(int(pct * 76), 2) if sec > 0 else 2
            is_now = (h == now_h)
            color  = (_C_AMBER if is_now
                      else _C_BLUE if sec > 1800
                      else "#A8C8F0")

            col = ctk.CTkFrame(
                wrap, fg_color="transparent")
            col.pack(side="left", expand=True, fill="x",
                     padx=1)

            # Eticheta valoare
            ctk.CTkLabel(
                col,
                text=f"{sec//60}m" if sec >= 60 else "",
                font=("Arial", 8),
                text_color=_C_AMBER if is_now else TEXT_LIGHT,
                height=14,
            ).pack()

            # Spatiu gol pana la bara
            ctk.CTkFrame(col, fg_color="transparent",
                         height=76 - bar_h).pack(fill="x")

            # Bara
            ctk.CTkFrame(col, fg_color=color,
                         corner_radius=3,
                         height=bar_h).pack(fill="x")

            # Eticheta ora
            ctk.CTkLabel(
                col, text=f"{h:02d}",
                font=("Arial", 8),
                text_color=_C_AMBER if is_now else TEXT_LIGHT,
                height=14,
            ).pack()

    # ─── Top site-uri ─────────────────────────────────────────────────────────

    def _draw_top_sites(self, logs: list):
        for w in self._sites_host.winfo_children():
            w.destroy()

        by_domain: dict = {}
        for log in logs:
            key = (log.domeniu or log.nume or "—").replace("www.", "")
            by_domain[key] = by_domain.get(key, 0) + (
                log.durata_secunde or 0)

        if not by_domain:
            ctk.CTkLabel(
                self._sites_host,
                text="Nicio activitate înregistrată azi.",
                font=("Arial", 11), text_color=TEXT_LIGHT,
            ).pack(anchor="w", pady=8)
            return

        top = sorted(by_domain.items(),
                     key=lambda x: x[1],
                     reverse=True)[:8]
        max_s = top[0][1] if top else 1

        for domain, sec in top:
            pct = sec / max_s if max_s > 0 else 0
            row = ctk.CTkFrame(
                self._sites_host, fg_color="transparent")
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row, text=domain,
                font=("Arial", 11), text_color=TEXT_DARK,
                width=170, anchor="w",
            ).pack(side="left")

            outer = ctk.CTkFrame(
                row, fg_color=_BAR_BG,
                corner_radius=4, height=14)
            outer.pack(side="left", fill="x", expand=True,
                       padx=(8, 8))
            outer.pack_propagate(False)

            ctk.CTkFrame(
                outer, fg_color=_C_TEAL,
                corner_radius=4, height=14,
            ).place(relx=0, rely=0,
                    relwidth=pct, relheight=1.0)

            ctk.CTkLabel(
                row, text=_fmt_time(sec),
                font=("Arial", 10), text_color=TEXT_LIGHT,
                width=54, anchor="e",
            ).pack(side="right")