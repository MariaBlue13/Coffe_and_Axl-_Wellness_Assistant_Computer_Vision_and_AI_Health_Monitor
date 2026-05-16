"""
Coffee & Axl - Dashboard Admin / Developer
Tabs: Utilizatori · Chat Wellness · Statistici · Debug
AI Intervention Bridge integrat.
Tab-uri fara emoji — doar text curat.
"""

import customtkinter as ctk
import tkinter as tk
import threading
import time
import socket
from datetime import datetime

from database import Utilizator, IstoricLogare, get_session
from utils.theme import *
from components.chatbot_tab import ChatbotTab


class DashboardAdmin(ctk.CTkFrame):

    def __init__(self, parent, engine, user_id: int,
                 user_name: str, on_logout):
        super().__init__(
            parent, fg_color=OFF_WHITE,
            corner_radius=0)
        self.engine    = engine
        self.user_id   = user_id
        self.user_name = user_name
        self.on_logout = on_logout
        self.user_role = self._get_user_role()

        self._vision_tab  = None
        self._befast_tab  = None
        self._chatbot_ref = None

        self._build_ui()

    def _get_user_role(self) -> str:
        session = get_session(self.engine)
        try:
            user = session.query(Utilizator)\
                .filter_by(
                id_utilizator=self.user_id
            ).first()
            return user.rol if user else "admin"
        finally:
            session.close()

    def _logout(self):
        from utils.session import clear_session
        clear_session()
        self.on_logout()

    def _navigate_to_chat(self):
        try:
            self._tabs.set("Chat Wellness")
        except Exception:
            pass

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self, fg_color=NAVY,
            width=260, corner_radius=0,
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        from utils.theme import load_logo
        logo = load_logo(size=(70, 70))
        if logo:
            ctk.CTkLabel(
                sidebar, image=logo, text=""
            ).pack(pady=(24, 6))
        else:
            ctk.CTkLabel(
                sidebar, text="☕",
                font=("Arial", 45),
                text_color=YELLOW,
            ).pack(pady=(30, 8))

        ctk.CTkLabel(
            sidebar, text="Coffee & Axl",
            font=("Georgia", 18, "bold"),
            text_color=WHITE,
        ).pack()

        if self.user_role == "developer":
            badge_bg, badge_fg = YELLOW, TEXT_DARK
            badge_text = "DEVELOPER"
        else:
            badge_bg, badge_fg = GREEN, WHITE
            badge_text = "ADMIN"

        badge = ctk.CTkFrame(
            sidebar, fg_color=badge_bg,
            corner_radius=10)
        badge.pack(pady=5, padx=50)
        ctk.CTkLabel(
            badge, text=badge_text,
            font=("Arial", 10, "bold"),
            text_color=badge_fg, padx=12,
        ).pack()

        ctk.CTkLabel(
            sidebar,
            text=f"Salut, {self.user_name}",
            font=("Arial", 12),
            text_color=NAVY_LIGHT,
        ).pack(pady=(4, 24))

        ctk.CTkFrame(
            sidebar, height=1,
            fg_color=NAVY_LIGHT,
            corner_radius=0,
        ).pack(fill="x", padx=20, pady=(0, 16))

        nav = [
            ("👥", "Utilizatori",   0),
            ("💬", "Chat Wellness", 1),
            ("📊", "Statistici",    2),
            ("🌐", "Monitorizare",  3),
        ]
        if self.user_role == "developer":
            nav.append(("🛠️", "Debug Console", 4))

        for icon, label, idx in nav:
            is_dev = (label == "Debug Console")
            ctk.CTkButton(
                sidebar,
                text=f"  {icon}  {label}",
                anchor="w", height=45,
                fg_color=YELLOW if is_dev
                else "transparent",
                hover_color=BLUE,
                text_color=TEXT_DARK if is_dev
                else WHITE,
                font=("Arial", 13,
                      "bold" if is_dev
                      else "normal"),
                corner_radius=8,
                command=lambda i=idx:
                self._go_to_tab(i),
            ).pack(fill="x", padx=15, pady=4)

        ctk.CTkButton(
            sidebar, text="🚪  Deconectare",
            anchor="w", height=45,
            fg_color="transparent",
            hover_color="#4A1B1B",
            text_color=ERROR_RED,
            font=("Arial", 13),
            corner_radius=8,
            command=self._logout,
        ).pack(fill="x", padx=15, pady=10,
               side="bottom")

        ctk.CTkLabel(
            sidebar,
            text=f"{badge_text.title()} · v1.0.0",
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(side="bottom", pady=(0, 8))

    def _go_to_tab(self, index: int):
        names = [
            "Utilizatori",
            "Chat Wellness",
            "Statistici",
            "Monitorizare",
        ]
        if self.user_role == "developer":
            names.append("Debug")
        if index < len(names):
            self._tabs.set(names[index])

    # ── Main ──────────────────────────────────────────────────────────────────

    def _build_main(self):
        container = ctk.CTkFrame(
            self, fg_color=OFF_WHITE,
            corner_radius=0)
        container.grid(
            row=0, column=1, sticky="nsew")
        container.rowconfigure(1, weight=1)
        container.columnconfigure(0, weight=1)

        # Header cu logo
        header = ctk.CTkFrame(
            container, fg_color=WHITE,
            corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        from utils.theme import load_logo
        logo_small = load_logo(size=(40, 40))
        if logo_small:
            ctk.CTkLabel(
                header,
                image=logo_small,
                text="",
            ).pack(side="left",
                   padx=(16, 4), pady=12)

        title = ("Developer Dashboard"
                 if self.user_role == "developer"
                 else "Panou Administrare")
        ctk.CTkLabel(
            header, text=title,
            font=("Georgia", 20, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left", padx=(4, 0), pady=18)

        ctk.CTkLabel(
            header,
            text=datetime.now().strftime(
                "%A, %d %B %Y"),
            font=("Arial", 12),
            text_color=TEXT_LIGHT,
        ).pack(side="right", padx=28)

        # TabView fara emoji
        tab_names = [
            "Utilizatori",
            "Chat Wellness",
            "Statistici",
            "Monitorizare",
        ]
        if self.user_role == "developer":
            tab_names.append("Debug")

        self._tabs = ctk.CTkTabview(
            container,
            fg_color=OFF_WHITE,
            segmented_button_fg_color=GRAY_LIGHT,
            segmented_button_selected_color=NAVY,
            segmented_button_selected_hover_color=NAVY_DARK,
            segmented_button_unselected_color=GRAY_LIGHT,
            segmented_button_unselected_hover_color=GRAY_MID,
            text_color=TEXT_MID,
            corner_radius=0,
        )
        self._tabs.grid(
            row=1, column=0, sticky="nsew")

        for name in tab_names:
            self._tabs.add(name)

        self._build_tab_users()
        self._build_tab_chat()
        self._build_tab_stats()
        self._build_tab_monitoring()
        if self.user_role == "developer":
            self._build_tab_debug()

    # ── Tab: Utilizatori ──────────────────────────────────────────────────────

    def _build_tab_users(self):
        tab = self._tabs.tab("Utilizatori")

        top = ctk.CTkFrame(
            tab, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            top, text="Management Utilizatori",
            font=("Georgia", 22, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left")

        ctk.CTkButton(
            top, text="🔄 Refresh", width=100,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            command=self._reload_users,
        ).pack(side="right")

        self._users_table = ctk.CTkScrollableFrame(
            tab, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        self._users_table.pack(
            fill="both", expand=True,
            padx=24, pady=(0, 20))

        self._reload_users()

    def _reload_users(self):
        for w in self._users_table.winfo_children():
            w.destroy()

        for i, h in enumerate([
            "ID", "Username", "Nume complet",
            "Rol", "Ultima logare"
        ]):
            ctk.CTkLabel(
                self._users_table, text=h,
                font=("Arial", 12, "bold"),
                text_color=NAVY,
            ).grid(row=0, column=i,
                   padx=20, pady=14, sticky="w")

        session = get_session(self.engine)
        try:
            users = session.query(Utilizator).all()
            for idx, user in enumerate(users, 1):
                ctk.CTkLabel(
                    self._users_table,
                    text=f"#{user.id_utilizator}",
                    font=("Arial", 12),
                    text_color=TEXT_LIGHT,
                ).grid(row=idx, column=0,
                       padx=20, pady=8,
                       sticky="w")

                ctk.CTkLabel(
                    self._users_table,
                    text=user.nume_utilizator,
                    font=("Arial", 13, "bold"),
                    text_color=TEXT_DARK,
                ).grid(row=idx, column=1,
                       padx=20, pady=8,
                       sticky="w")

                full = (
                    f"{user.prenume or ''} "
                    f"{user.nume or ''}".strip()
                    or "—"
                )
                ctk.CTkLabel(
                    self._users_table,
                    text=full,
                    font=("Arial", 12),
                    text_color=TEXT_MID,
                ).grid(row=idx, column=2,
                       padx=20, pady=8,
                       sticky="w")

                rol_styles = {
                    "admin":
                        ("#E8F0F8", NAVY),
                    "developer":
                        ("#FFFDE0", "#8B7500"),
                    "utilizator":
                        ("#EAF6E0", "#3A7020"),
                }
                bg, fg = rol_styles.get(
                    user.rol,
                    (GRAY_LIGHT, TEXT_MID))
                rf = ctk.CTkFrame(
                    self._users_table,
                    fg_color=bg,
                    corner_radius=6)
                rf.grid(row=idx, column=3,
                        padx=20, pady=8,
                        sticky="w")
                ctk.CTkLabel(
                    rf,
                    text=user.rol.upper(),
                    font=("Arial", 10, "bold"),
                    text_color=fg,
                    padx=8, pady=2,
                ).pack()

                last_log = "Niciodată"
                if user.logari:
                    last_log = user.logari[-1]\
                        .data_ora.strftime(
                        "%H:%M  %d.%m.%Y")
                ctk.CTkLabel(
                    self._users_table,
                    text=last_log,
                    font=("Arial", 11),
                    text_color=TEXT_LIGHT,
                ).grid(row=idx, column=4,
                       padx=20, pady=8,
                       sticky="w")
        finally:
            session.close()

    # ── Tab: Chat Wellness ────────────────────────────────────────────────────

    def _build_tab_chat(self):
        tab = self._tabs.tab("Chat Wellness")
        self._chatbot_ref = ChatbotTab(
            tab, user_name=self.user_name)

        # Click pe indicator -> navigheza la Chat
        self._chatbot_ref\
            .set_navigate_to_chat_callback(
            self._navigate_to_chat)

    # ── Tab: Statistici ───────────────────────────────────────────────────────

    # ── Tab: Statistici ───────────────────────────────────────────────────────

    def _build_tab_stats(self):
        tab = self._tabs.tab("Statistici")

        inner = ctk.CTkTabview(
            tab,
            fg_color=OFF_WHITE,
            segmented_button_fg_color=GRAY_LIGHT,
            segmented_button_selected_color=NAVY,
            segmented_button_selected_hover_color=NAVY_DARK,
            segmented_button_unselected_color=GRAY_LIGHT,
            segmented_button_unselected_hover_color=GRAY_MID,
            text_color=TEXT_MID,
            corner_radius=0,
        )
        inner.pack(fill="both", expand=True)

        for name in ["Generale", "Site-uri", "Per Utilizator", "CRUD"]:
            inner.add(name)

        self._build_stats_generale(inner.tab("Generale"))
        self._build_stats_sites(inner.tab("Site-uri"))
        self._build_stats_per_user(inner.tab("Per Utilizator"))
        self._build_stats_crud(inner.tab("CRUD"))

    # ── Statistici: Generale ──────────────────────────────────────────────────

    def _build_stats_generale(self, tab):
        from database import SiteRule, ActivityLog, DailyStats

        scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=16)

        ctk.CTkLabel(
            scroll, text="Statistici Platforma",
            font=("Georgia", 22, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", pady=(0, 16))

        session = get_session(self.engine)
        try:
            n_users  = session.query(Utilizator).count()
            n_admins = session.query(Utilizator).filter_by(rol="admin").count()
            n_devs   = session.query(Utilizator).filter_by(rol="developer").count()
            n_util   = session.query(Utilizator).filter_by(rol="utilizator").count()
            n_logs   = session.query(IstoricLogare).count()
            n_rules  = session.query(SiteRule).filter_by(activ=True).count()
            n_blocked_events = session.query(ActivityLog).filter_by(blocat=True).count()
            n_activity = session.query(ActivityLog).count()
        finally:
            session.close()

        # Rand 1: conturi
        row1 = ctk.CTkFrame(scroll, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 8))

        for icon, label, val, color in [
            ("👥", "Total conturi",    str(n_users),  NAVY),
            ("🔑", "Administratori",   str(n_admins), BLUE),
            ("🛠", "Developeri",       str(n_devs),   "#8B7500"),
            ("👤", "Utilizatori std",  str(n_util),   GREEN),
            ("📋", "Logari totale",    str(n_logs),   TEXT_MID),
        ]:
            card = ctk.CTkFrame(row1, fg_color=WHITE,
                                corner_radius=CORNER_RADIUS,
                                border_width=1, border_color=GRAY_LIGHT)
            card.pack(side="left", padx=6, expand=True, fill="both")
            ctk.CTkLabel(card, text=icon, font=("Arial", 26)).pack(pady=(16, 2))
            ctk.CTkLabel(card, text=val,
                         font=("Georgia", 22, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=label,
                         font=("Arial", 10),
                         text_color=TEXT_LIGHT).pack(pady=(2, 16))

        # Rand 2: monitorizare
        row2 = ctk.CTkFrame(scroll, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 16))

        for icon, label, val, color in [
            ("🚫", "Reguli active",     str(n_rules),           ERROR_RED),
            ("⛔", "Accesari blocate",  str(n_blocked_events),  "#B71C1C"),
            ("📊", "Activitati log",    str(n_activity),        BLUE),
        ]:
            card = ctk.CTkFrame(row2, fg_color=WHITE,
                                corner_radius=CORNER_RADIUS,
                                border_width=1, border_color=GRAY_LIGHT)
            card.pack(side="left", padx=6, expand=True, fill="both")
            ctk.CTkLabel(card, text=icon, font=("Arial", 26)).pack(pady=(16, 2))
            ctk.CTkLabel(card, text=val,
                         font=("Georgia", 22, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=label,
                         font=("Arial", 10),
                         text_color=TEXT_LIGHT).pack(pady=(2, 16))

    # ── Statistici: Site-uri ──────────────────────────────────────────────────

    def _build_stats_sites(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkLabel(top, text="Statistici Site-uri",
                     font=("Georgia", 20, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        sites_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent")
        sites_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        ctk.CTkButton(
            top, text="🔄 Refresh", width=100,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            command=lambda: self._reload_sites_stats(sites_scroll),
        ).pack(side="right")

        self._reload_sites_stats(sites_scroll)

    def _reload_sites_stats(self, container):
        from database import SiteRule, ActivityLog
        from sqlalchemy import func

        for w in container.winfo_children():
            w.destroy()

        session = get_session(self.engine)
        try:
            top_blocked = session.query(
                ActivityLog.domeniu,
                func.count(ActivityLog.id).label("cnt")
            ).filter(
                ActivityLog.blocat == True,
                ActivityLog.domeniu.isnot(None),
            ).group_by(ActivityLog.domeniu)             .order_by(func.count(ActivityLog.id).desc())             .limit(10).all()

            top_visited = session.query(
                ActivityLog.domeniu,
                func.count(ActivityLog.id).label("cnt")
            ).filter(
                ActivityLog.blocat == False,
                ActivityLog.tip == "site",
                ActivityLog.domeniu.isnot(None),
            ).group_by(ActivityLog.domeniu)             .order_by(func.count(ActivityLog.id).desc())             .limit(10).all()

            n_blocate  = session.query(SiteRule).filter_by(activ=True, tip="blocat").count()
            n_limitate = session.query(SiteRule).filter_by(activ=True, tip="limitat").count()

            all_rules = session.query(SiteRule)                .filter_by(activ=True)                .order_by(SiteRule.creat_la.desc())                .all()
        finally:
            session.close()

        # Top blocate
        sec1 = ctk.CTkFrame(container, fg_color=WHITE,
                             corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=GRAY_LIGHT)
        sec1.pack(fill="x", pady=(0, 12))

        hdr1 = ctk.CTkFrame(sec1, fg_color="#FFF0F0", corner_radius=0, height=40)
        hdr1.pack(fill="x")
        hdr1.pack_propagate(False)
        ctk.CTkLabel(hdr1, text="  🚫  Top site-uri blocate",
                     font=("Arial", 12, "bold"),
                     text_color=ERROR_RED).pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(hdr1, text=f"{n_blocate} reguli active",
                     font=("Arial", 10),
                     text_color=TEXT_LIGHT).pack(side="right", padx=12)

        if not top_blocked:
            ctk.CTkLabel(sec1, text="Nicio activitate blocata inregistrata.",
                         font=("Arial", 11), text_color=TEXT_LIGHT).pack(pady=16)
        else:
            max_cnt = top_blocked[0][1] if top_blocked else 1
            for domain, cnt in top_blocked:
                row = ctk.CTkFrame(sec1, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=3)
                ctk.CTkLabel(row, text=domain,
                             font=("Arial", 11, "bold"), text_color=TEXT_DARK,
                             width=180, anchor="w").pack(side="left")
                bar_bg = ctk.CTkFrame(row, fg_color=GRAY_LIGHT,
                                      corner_radius=4, height=14)
                bar_bg.pack(side="left", fill="x", expand=True, padx=(8, 8))
                ctk.CTkFrame(bar_bg, fg_color=ERROR_RED, corner_radius=4,
                             height=14,
                             width=max(20, int((cnt / max_cnt) * 200))
                             ).pack(side="left")
                ctk.CTkLabel(row, text=f"{cnt}x",
                             font=("Arial", 10, "bold"), text_color=ERROR_RED,
                             width=40, anchor="e").pack(side="right")

        # Top vizitate
        sec2 = ctk.CTkFrame(container, fg_color=WHITE,
                             corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=GRAY_LIGHT)
        sec2.pack(fill="x", pady=(0, 12))

        hdr2 = ctk.CTkFrame(sec2, fg_color="#F0F8FF", corner_radius=0, height=40)
        hdr2.pack(fill="x")
        hdr2.pack_propagate(False)
        ctk.CTkLabel(hdr2, text="  🌐  Top site-uri vizitate",
                     font=("Arial", 12, "bold"),
                     text_color=NAVY).pack(side="left", padx=12, pady=10)

        if not top_visited:
            ctk.CTkLabel(sec2, text="Nicio vizita inregistrata.",
                         font=("Arial", 11), text_color=TEXT_LIGHT).pack(pady=16)
        else:
            max_v = top_visited[0][1] if top_visited else 1
            for domain, cnt in top_visited:
                row = ctk.CTkFrame(sec2, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=3)
                ctk.CTkLabel(row, text=domain,
                             font=("Arial", 11, "bold"), text_color=TEXT_DARK,
                             width=180, anchor="w").pack(side="left")
                bar_bg = ctk.CTkFrame(row, fg_color=GRAY_LIGHT,
                                      corner_radius=4, height=14)
                bar_bg.pack(side="left", fill="x", expand=True, padx=(8, 8))
                ctk.CTkFrame(bar_bg, fg_color=NAVY, corner_radius=4,
                             height=14,
                             width=max(20, int((cnt / max_v) * 200))
                             ).pack(side="left")
                ctk.CTkLabel(row, text=f"{cnt}x",
                             font=("Arial", 10, "bold"), text_color=NAVY,
                             width=40, anchor="e").pack(side="right")

        # Toate regulile active
        sec3 = ctk.CTkFrame(container, fg_color=WHITE,
                             corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=GRAY_LIGHT)
        sec3.pack(fill="x", pady=(0, 12))

        hdr3 = ctk.CTkFrame(sec3, fg_color="#F0F4FF", corner_radius=0, height=40)
        hdr3.pack(fill="x")
        hdr3.pack_propagate(False)
        ctk.CTkLabel(
            hdr3,
            text=f"  📋  Toate regulile active ({n_blocate} blocate, {n_limitate} limitate)",
            font=("Arial", 12, "bold"),
            text_color=NAVY).pack(side="left", padx=12, pady=10)

        if not all_rules:
            ctk.CTkLabel(sec3, text="Nicio regula activa.",
                         font=("Arial", 11), text_color=TEXT_LIGHT).pack(pady=16)
        else:
            hrow = ctk.CTkFrame(sec3, fg_color=GRAY_LIGHT, corner_radius=0)
            hrow.pack(fill="x", padx=12, pady=(8, 0))
            for txt, w in [("Domeniu", 200), ("Tip", 80),
                            ("Limita", 80), ("User ID", 70), ("", 70)]:
                ctk.CTkLabel(hrow, text=txt,
                             font=("Arial", 10, "bold"), text_color=TEXT_MID,
                             width=w, anchor="w").pack(side="left", padx=6, pady=6)

            for r in all_rules:
                blocked = r.tip == "blocat"
                bg      = "#FFF8F8" if blocked else "#FFFAF0"
                color   = ERROR_RED if blocked else "#E65100"

                rrow = ctk.CTkFrame(sec3, fg_color=bg, corner_radius=0)
                rrow.pack(fill="x", padx=12, pady=1)

                ctk.CTkLabel(rrow, text=r.domeniu,
                             font=("Arial", 11, "bold"), text_color=TEXT_DARK,
                             width=200, anchor="w").pack(side="left", padx=6, pady=6)

                tip_badge = ctk.CTkFrame(rrow, fg_color=color, corner_radius=4)
                tip_badge.pack(side="left", padx=(0, 4), pady=4)
                ctk.CTkLabel(tip_badge, text=r.tip.upper(),
                             font=("Arial", 9, "bold"), text_color=WHITE,
                             padx=6, pady=2).pack()

                lim = f"{r.limita_minute} min" if r.limita_minute else "—"
                ctk.CTkLabel(rrow, text=lim,
                             font=("Arial", 11), text_color=TEXT_MID,
                             width=80, anchor="w").pack(side="left", padx=6)

                ctk.CTkLabel(rrow, text=f"User #{r.id_utilizator}",
                             font=("Arial", 10), text_color=TEXT_LIGHT,
                             width=70, anchor="w").pack(side="left", padx=6)

                ctk.CTkButton(
                    rrow, text="Sterge",
                    width=60, height=26,
                    fg_color=GRAY_LIGHT, hover_color=ERROR_RED,
                    text_color=TEXT_MID, font=("Arial", 10),
                    command=lambda rid=r.id, c=sec3:
                        self._stats_delete_rule(rid, container),
                ).pack(side="right", padx=6, pady=4)

    def _stats_delete_rule(self, rule_id: int, refresh_container):
        from database import SiteRule
        try:
            session = get_session(self.engine)
            try:
                r = session.query(SiteRule).filter_by(id=rule_id).first()
                if r:
                    r.activ = False
                    session.commit()
            finally:
                session.close()
            self._reload_sites_stats(refresh_container)
        except Exception as e:
            print(f"[ADMIN] Delete rule err: {e}")

    # ── Statistici: Per Utilizator ────────────────────────────────────────────

    def _build_stats_per_user(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkLabel(top, text="Statistici per Utilizator",
                     font=("Georgia", 20, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        self._per_user_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent")
        self._per_user_scroll.pack(
            fill="both", expand=True, padx=24, pady=(0, 16))

        ctk.CTkButton(
            top, text="🔄 Refresh", width=100,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            command=lambda: self._reload_per_user(self._per_user_scroll),
        ).pack(side="right")

        self._reload_per_user(self._per_user_scroll)

    def _reload_per_user(self, container):
        from database import ActivityLog, SiteRule, DailyStats
        from sqlalchemy import func
        from datetime import date

        for w in container.winfo_children():
            w.destroy()

        session = get_session(self.engine)
        try:
            users = session.query(Utilizator).filter_by(rol="utilizator").all()
            today = date.today()
            data  = []
            for u in users:
                n_rules   = session.query(SiteRule).filter_by(
                    id_utilizator=u.id_utilizator, activ=True).count()
                n_blocked = session.query(ActivityLog).filter_by(
                    id_utilizator=u.id_utilizator, blocat=True).count()
                n_visits  = session.query(ActivityLog).filter_by(
                    id_utilizator=u.id_utilizator, tip="site", blocat=False).count()
                stat_today = session.query(DailyStats).filter_by(
                    id_utilizator=u.id_utilizator, data=today).first()
                timp_azi = stat_today.timp_total_sec if stat_today else 0
                data.append((u, n_rules, n_blocked, n_visits, timp_azi))
        finally:
            session.close()

        if not data:
            ctk.CTkLabel(container,
                         text="Niciun utilizator standard gasit.",
                         font=("Arial", 12), text_color=TEXT_LIGHT).pack(pady=40)
            return

        for u, n_rules, n_blocked, n_visits, timp_azi in data:
            card = ctk.CTkFrame(container, fg_color=WHITE,
                                corner_radius=CORNER_RADIUS,
                                border_width=1, border_color=GRAY_LIGHT)
            card.pack(fill="x", pady=6)

            hdr = ctk.CTkFrame(card, fg_color="#F0F4FF",
                                corner_radius=0, height=42)
            hdr.pack(fill="x")
            hdr.pack_propagate(False)

            full = f"{u.prenume or ''} {u.nume or ''}".strip() or u.nume_utilizator
            ctk.CTkLabel(hdr,
                         text=f"  👤  {full}  (@{u.nume_utilizator})",
                         font=("Arial", 12, "bold"),
                         text_color=NAVY).pack(side="left", padx=12, pady=10)
            ctk.CTkLabel(hdr, text=f"ID #{u.id_utilizator}",
                         font=("Arial", 10),
                         text_color=TEXT_LIGHT).pack(side="right", padx=12)

            stats_row = ctk.CTkFrame(card, fg_color="transparent")
            stats_row.pack(fill="x", padx=16, pady=12)

            h = timp_azi // 3600
            m = (timp_azi % 3600) // 60
            timp_str = f"{h}h {m}m" if h else f"{m}m"

            for lbl, val, color in [
                ("Reguli active",     str(n_rules),   NAVY),
                ("Accesari blocate",  str(n_blocked),  ERROR_RED),
                ("Site-uri vizitate", str(n_visits),   BLUE),
                ("Timp azi",          timp_str,        GREEN),
            ]:
                mini = ctk.CTkFrame(stats_row, fg_color=OFF_WHITE,
                                    corner_radius=8,
                                    border_width=1, border_color=GRAY_LIGHT)
                mini.pack(side="left", padx=6, expand=True, fill="both")
                ctk.CTkLabel(mini, text=val,
                             font=("Georgia", 16, "bold"),
                             text_color=color).pack(pady=(10, 2))
                ctk.CTkLabel(mini, text=lbl,
                             font=("Arial", 9),
                             text_color=TEXT_LIGHT).pack(pady=(0, 10))

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def _build_stats_crud(self, tab):
        inner = ctk.CTkTabview(
            tab,
            fg_color=OFF_WHITE,
            segmented_button_fg_color=GRAY_LIGHT,
            segmented_button_selected_color=NAVY,
            segmented_button_selected_hover_color=NAVY_DARK,
            segmented_button_unselected_color=GRAY_LIGHT,
            segmented_button_unselected_hover_color=GRAY_MID,
            text_color=TEXT_MID,
            corner_radius=0,
        )
        inner.pack(fill="both", expand=True)

        for name in ["Utilizatori", "Reguli", "Activity Log", "Daily Stats"]:
            inner.add(name)

        self._build_crud_utilizatori(inner.tab("Utilizatori"))
        self._build_crud_rules(inner.tab("Reguli"))
        self._build_crud_activity(inner.tab("Activity Log"))
        self._build_crud_daily(inner.tab("Daily Stats"))

    # ── CRUD: Utilizatori ─────────────────────────────────────────────────────

    def _build_crud_utilizatori(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(top, text="Gestionare Utilizatori",
                     font=("Georgia", 16, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        tbl = ctk.CTkScrollableFrame(tab, fg_color=WHITE,
                                      corner_radius=CORNER_RADIUS,
                                      border_width=1, border_color=GRAY_LIGHT)
        tbl.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        ctk.CTkButton(top, text="🔄", width=40,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._crud_reload_users(tbl)
                      ).pack(side="right")

        ctk.CTkButton(top, text="+ Utilizator nou",
                      width=150, height=34,
                      fg_color=GREEN, hover_color="#2E7D32",
                      font=("Arial", 11, "bold"),
                      command=lambda: self._crud_user_dialog(None, tbl)
                      ).pack(side="right", padx=(0, 8))

        self._crud_reload_users(tbl)

    def _crud_reload_users(self, container):
        for w in container.winfo_children():
            w.destroy()

        hrow = ctk.CTkFrame(container, fg_color=GRAY_LIGHT, corner_radius=0)
        hrow.pack(fill="x")
        for txt, w in [("ID", 40), ("Username", 130), ("Nume", 140),
                        ("Rol", 100), ("Varsta", 60), ("Actiuni", 140)]:
            ctk.CTkLabel(hrow, text=txt, font=("Arial", 10, "bold"),
                         text_color=TEXT_MID, width=w, anchor="w"
                         ).pack(side="left", padx=8, pady=8)

        session = get_session(self.engine)
        try:
            users = session.query(Utilizator).order_by(
                Utilizator.id_utilizator).all()
            for u in users:
                row = ctk.CTkFrame(container, fg_color="transparent",
                                   corner_radius=0)
                row.pack(fill="x")
                ctk.CTkFrame(container, height=1, fg_color=GRAY_LIGHT,
                             corner_radius=0).pack(fill="x")

                ctk.CTkLabel(row, text=str(u.id_utilizator),
                             font=("Arial", 11), text_color=TEXT_LIGHT,
                             width=40, anchor="w").pack(side="left", padx=8, pady=8)
                ctk.CTkLabel(row, text=u.nume_utilizator,
                             font=("Arial", 11, "bold"), text_color=TEXT_DARK,
                             width=130, anchor="w").pack(side="left", padx=8)
                full = f"{u.prenume or ''} {u.nume or ''}".strip() or "—"
                ctk.CTkLabel(row, text=full,
                             font=("Arial", 11), text_color=TEXT_MID,
                             width=140, anchor="w").pack(side="left", padx=8)

                rol_colors = {"admin": NAVY, "developer": "#8B7500",
                              "utilizator": GREEN}
                ctk.CTkLabel(row, text=u.rol,
                             font=("Arial", 10, "bold"),
                             text_color=rol_colors.get(u.rol, TEXT_MID),
                             width=100, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text=str(u.varsta or "—"),
                             font=("Arial", 11), text_color=TEXT_MID,
                             width=60, anchor="w").pack(side="left", padx=8)

                act = ctk.CTkFrame(row, fg_color="transparent")
                act.pack(side="left", padx=8)
                ctk.CTkButton(
                    act, text="Edit", width=52, height=28,
                    fg_color=BLUE, hover_color=BLUE_HOVER, font=("Arial", 10),
                    command=lambda uid=u.id_utilizator, c=container:
                        self._crud_user_dialog(uid, c)
                ).pack(side="left", padx=(0, 4))
                ctk.CTkButton(
                    act, text="Sterge", width=60, height=28,
                    fg_color=GRAY_LIGHT, hover_color=ERROR_RED,
                    text_color=TEXT_MID, font=("Arial", 10),
                    command=lambda uid=u.id_utilizator, c=container:
                        self._crud_delete_user(uid, c)
                ).pack(side="left")
        finally:
            session.close()

    def _crud_user_dialog(self, user_id, refresh_container):
        win = ctk.CTkToplevel(self)
        win.title("Utilizator nou" if not user_id else "Editeaza utilizator")
        win.geometry("420x520")
        win.grab_set()

        u_data = {"username": "", "prenume": "", "nume": "",
                  "varsta": "", "rol": "utilizator"}
        if user_id:
            session = get_session(self.engine)
            try:
                u = session.query(Utilizator).filter_by(
                    id_utilizator=user_id).first()
                if u:
                    u_data = {
                        "username": u.nume_utilizator,
                        "prenume":  u.prenume or "",
                        "nume":     u.nume or "",
                        "varsta":   str(u.varsta or ""),
                        "rol":      u.rol,
                    }
            finally:
                session.close()

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=16)

        fields = {}
        for lbl, key, show in [
            ("Username *",  "username", ""),
            ("Prenume",     "prenume",  ""),
            ("Nume",        "nume",     ""),
            ("Varsta",      "varsta",   ""),
            ("Parola noua", "parola",   "•"),
        ]:
            ctk.CTkLabel(scroll, text=lbl,
                         font=("Arial", 11, "bold"),
                         text_color=TEXT_MID).pack(anchor="w", pady=(8, 2))
            e = ctk.CTkEntry(scroll, height=38, font=("Arial", 12),
                             show=show)
            e.pack(fill="x", pady=(0, 4))
            if key in u_data:
                e.insert(0, u_data[key])
            fields[key] = e

        ctk.CTkLabel(scroll, text="Rol *",
                     font=("Arial", 11, "bold"),
                     text_color=TEXT_MID).pack(anchor="w", pady=(8, 2))
        rol_var = tk.StringVar(value=u_data["rol"])
        rol_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        rol_frame.pack(fill="x")
        for r in ["utilizator", "admin", "developer"]:
            ctk.CTkRadioButton(rol_frame, text=r,
                               variable=rol_var, value=r).pack(
                side="left", padx=(0, 16))

        msg_var = tk.StringVar(value="")
        ctk.CTkLabel(scroll, textvariable=msg_var,
                     font=("Arial", 11), text_color=ERROR_RED).pack(pady=(8, 0))

        def do_save():
            username = fields["username"].get().strip()
            if not username:
                msg_var.set("Username obligatoriu.")
                return
            session = get_session(self.engine)
            try:
                if user_id:
                    u = session.query(Utilizator).filter_by(
                        id_utilizator=user_id).first()
                    if not u:
                        msg_var.set("Utilizator negasit.")
                        return
                else:
                    if session.query(Utilizator).filter_by(
                            nume_utilizator=username).first():
                        msg_var.set("Username deja exista.")
                        return
                    u = Utilizator()
                    session.add(u)

                u.nume_utilizator = username
                u.prenume = fields["prenume"].get().strip() or None
                u.nume    = fields["nume"].get().strip() or None
                u.rol     = rol_var.get()
                try:
                    u.varsta = int(fields["varsta"].get()) if fields["varsta"].get().strip() else None
                except ValueError:
                    u.varsta = None

                parola = fields["parola"].get()
                if parola:
                    u.set_parola(parola)
                elif not user_id:
                    msg_var.set("Parola obligatorie pentru utilizator nou.")
                    return

                session.commit()
                win.destroy()
                self._crud_reload_users(refresh_container)
            except Exception as e:
                msg_var.set(f"Eroare: {e}")
            finally:
                session.close()

        ctk.CTkButton(win, text="Salveaza",
                      height=42, fg_color=NAVY, hover_color=NAVY_DARK,
                      font=("Arial", 12, "bold"),
                      command=do_save).pack(fill="x", padx=20, pady=(0, 20))

    def _crud_delete_user(self, user_id, refresh_container):
        import tkinter.messagebox as mb
        if not mb.askyesno("Confirmare",
                           f"Stergi utilizatorul #{user_id}?"):
            return
        session = get_session(self.engine)
        try:
            u = session.query(Utilizator).filter_by(
                id_utilizator=user_id).first()
            if u:
                session.delete(u)
                session.commit()
            self._crud_reload_users(refresh_container)
        except Exception as e:
            print(f"[CRUD] Delete user err: {e}")
        finally:
            session.close()

    # ── CRUD: Reguli ──────────────────────────────────────────────────────────

    def _build_crud_rules(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(top, text="Gestionare Reguli Site-uri",
                     font=("Georgia", 16, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        tbl = ctk.CTkScrollableFrame(tab, fg_color=WHITE,
                                      corner_radius=CORNER_RADIUS,
                                      border_width=1, border_color=GRAY_LIGHT)
        tbl.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        # Formular adaugare rapida
        add_card = ctk.CTkFrame(tab, fg_color=WHITE,
                                corner_radius=CORNER_RADIUS,
                                border_width=1, border_color=GRAY_LIGHT)
        add_card.pack(fill="x", padx=16, pady=(0, 12))

        add_row = ctk.CTkFrame(add_card, fg_color="transparent")
        add_row.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(add_row, text="User ID:",
                     font=("Arial", 11), text_color=TEXT_MID).pack(side="left")
        self._new_rule_uid = ctk.CTkEntry(
            add_row, width=55, height=34, placeholder_text="1")
        self._new_rule_uid.pack(side="left", padx=(4, 10))

        ctk.CTkLabel(add_row, text="Domeniu:",
                     font=("Arial", 11), text_color=TEXT_MID).pack(side="left")
        self._new_rule_domain = ctk.CTkEntry(
            add_row, width=150, height=34, placeholder_text="facebook.com")
        self._new_rule_domain.pack(side="left", padx=(4, 10))

        self._new_rule_type = tk.StringVar(value="blocat")
        ctk.CTkRadioButton(add_row, text="Blocat",
                           variable=self._new_rule_type, value="blocat",
                           text_color=ERROR_RED).pack(side="left", padx=(0, 8))
        ctk.CTkRadioButton(add_row, text="Limitat",
                           variable=self._new_rule_type, value="limitat",
                           text_color="#E65100").pack(side="left", padx=(0, 8))

        self._new_rule_mins = ctk.CTkEntry(
            add_row, width=60, height=34, placeholder_text="min")
        self._new_rule_mins.pack(side="left", padx=(0, 10))

        ctk.CTkButton(add_row, text="+ Adauga",
                      width=90, height=34,
                      fg_color=NAVY, hover_color=NAVY_DARK,
                      font=("Arial", 11, "bold"),
                      command=lambda: self._crud_add_rule(tbl)
                      ).pack(side="left")

        ctk.CTkButton(top, text="🔄", width=40,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._crud_reload_rules(tbl)
                      ).pack(side="right")

        self._crud_reload_rules(tbl)

    def _crud_reload_rules(self, container):
        from database import SiteRule
        for w in container.winfo_children():
            w.destroy()

        hrow = ctk.CTkFrame(container, fg_color=GRAY_LIGHT, corner_radius=0)
        hrow.pack(fill="x")
        for txt, w in [("ID", 40), ("User", 60), ("Domeniu", 170),
                        ("Tip", 80), ("Limita", 70), ("Activ", 50), ("", 80)]:
            ctk.CTkLabel(hrow, text=txt, font=("Arial", 10, "bold"),
                         text_color=TEXT_MID, width=w, anchor="w"
                         ).pack(side="left", padx=8, pady=8)

        session = get_session(self.engine)
        try:
            from database import SiteRule
            rules = session.query(SiteRule)                .order_by(SiteRule.id.desc()).limit(200).all()
            for r in rules:
                blocked = r.tip == "blocat"
                bg  = "#FFF8F8" if blocked else "transparent"
                row = ctk.CTkFrame(container, fg_color=bg, corner_radius=0)
                row.pack(fill="x")
                ctk.CTkFrame(container, height=1, fg_color=GRAY_LIGHT,
                             corner_radius=0).pack(fill="x")

                ctk.CTkLabel(row, text=str(r.id),
                             font=("Arial", 10), text_color=TEXT_LIGHT,
                             width=40, anchor="w").pack(side="left", padx=8, pady=6)
                ctk.CTkLabel(row, text=str(r.id_utilizator),
                             font=("Arial", 11), text_color=TEXT_MID,
                             width=60, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text=r.domeniu,
                             font=("Arial", 11, "bold"), text_color=TEXT_DARK,
                             width=170, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text=r.tip,
                             font=("Arial", 10, "bold"),
                             text_color=ERROR_RED if blocked else "#E65100",
                             width=80, anchor="w").pack(side="left", padx=8)
                lim = f"{r.limita_minute}m" if r.limita_minute else "—"
                ctk.CTkLabel(row, text=lim,
                             font=("Arial", 11), text_color=TEXT_MID,
                             width=70, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row, text="Da" if r.activ else "Nu",
                             font=("Arial", 10, "bold"),
                             text_color=GREEN if r.activ else TEXT_LIGHT,
                             width=50, anchor="w").pack(side="left", padx=8)

                ctk.CTkButton(
                    row,
                    text="Dezact." if r.activ else "Activ.",
                    width=70, height=26,
                    fg_color=GRAY_LIGHT,
                    hover_color=ERROR_RED if r.activ else GREEN,
                    text_color=TEXT_MID, font=("Arial", 10),
                    command=lambda rid=r.id, activ=r.activ, c=container:
                        self._crud_toggle_rule(rid, activ, c)
                ).pack(side="right", padx=6, pady=4)
        finally:
            session.close()

    def _crud_add_rule(self, refresh_container):
        from database import SiteRule
        from datetime import datetime as dt
        try:
            uid    = int(self._new_rule_uid.get().strip())
            domain = self._new_rule_domain.get().strip().lower()
            tip    = self._new_rule_type.get()
            mins_s = self._new_rule_mins.get().strip()
            limita = int(mins_s) if mins_s and tip == "limitat" else None
            if not domain:
                return
            session = get_session(self.engine)
            try:
                session.add(SiteRule(
                    id_utilizator=uid, domeniu=domain,
                    tip=tip, limita_minute=limita,
                    activ=True, creat_la=dt.utcnow()))
                session.commit()
            finally:
                session.close()
            self._new_rule_domain.delete(0, "end")
            self._new_rule_mins.delete(0, "end")
            self._crud_reload_rules(refresh_container)
        except Exception as e:
            print(f"[CRUD] Add rule err: {e}")

    def _crud_toggle_rule(self, rule_id, currently_active, container):
        from database import SiteRule
        session = get_session(self.engine)
        try:
            r = session.query(SiteRule).filter_by(id=rule_id).first()
            if r:
                r.activ = not currently_active
                session.commit()
            self._crud_reload_rules(container)
        except Exception as e:
            print(f"[CRUD] Toggle rule err: {e}")
        finally:
            session.close()

    # ── CRUD: Activity Log ────────────────────────────────────────────────────

    def _build_crud_activity(self, tab):
        # ── Header ──────────────────────────────────
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(top, text="Activity Log",
                     font=("Georgia", 16, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        ctk.CTkButton(top, text="🔄", width=40,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._apply_activity_filters(tbl)
                      ).pack(side="right")
        ctk.CTkButton(top, text="🗑 Sterge tot",
                      width=110, height=34,
                      fg_color=GRAY_LIGHT, hover_color=ERROR_RED,
                      text_color=TEXT_MID, font=("Arial", 11),
                      command=lambda: self._crud_clear_activity(tbl)
                      ).pack(side="right", padx=(0, 8))

        # ── Bara de filtrare ─────────────────────────
        filter_card = ctk.CTkFrame(tab, fg_color=WHITE,
                                    corner_radius=CORNER_RADIUS,
                                    border_width=1, border_color=GRAY_LIGHT)
        filter_card.pack(fill="x", padx=16, pady=(0, 6))

        filter_row1 = ctk.CTkFrame(filter_card, fg_color="transparent")
        filter_row1.pack(fill="x", padx=12, pady=(10, 4))

        # User ID
        ctk.CTkLabel(filter_row1, text="User ID:",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=55, anchor="w").pack(side="left")
        self._af_user = ctk.CTkEntry(filter_row1, width=55, height=30,
                                      placeholder_text="toti")
        self._af_user.pack(side="left", padx=(0, 12))

        # Tip
        ctk.CTkLabel(filter_row1, text="Tip:",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=30, anchor="w").pack(side="left")
        self._af_tip = ctk.CTkOptionMenu(
            filter_row1,
            values=["toate", "site", "aplicatie", "sistem"],
            width=110, height=30,
            fg_color=GRAY_LIGHT, text_color=TEXT_DARK,
            button_color=GRAY_MID, button_hover_color=NAVY,
            dropdown_fg_color=WHITE, dropdown_text_color=TEXT_DARK)
        self._af_tip.set("toate")
        self._af_tip.pack(side="left", padx=(0, 12))

        # Blocat
        ctk.CTkLabel(filter_row1, text="Blocat:",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=50, anchor="w").pack(side="left")
        self._af_blocat = ctk.CTkOptionMenu(
            filter_row1,
            values=["toate", "doar blocate", "doar neblocate"],
            width=130, height=30,
            fg_color=GRAY_LIGHT, text_color=TEXT_DARK,
            button_color=GRAY_MID, button_hover_color=NAVY,
            dropdown_fg_color=WHITE, dropdown_text_color=TEXT_DARK)
        self._af_blocat.set("toate")
        self._af_blocat.pack(side="left", padx=(0, 12))

        # Limita rezultate
        ctk.CTkLabel(filter_row1, text="Limit:",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=40, anchor="w").pack(side="left")
        self._af_limit = ctk.CTkOptionMenu(
            filter_row1,
            values=["50", "100", "200", "500", "toate"],
            width=80, height=30,
            fg_color=GRAY_LIGHT, text_color=TEXT_DARK,
            button_color=GRAY_MID, button_hover_color=NAVY,
            dropdown_fg_color=WHITE, dropdown_text_color=TEXT_DARK)
        self._af_limit.set("100")
        self._af_limit.pack(side="left", padx=(0, 12))

        filter_row2 = ctk.CTkFrame(filter_card, fg_color="transparent")
        filter_row2.pack(fill="x", padx=12, pady=(0, 10))

        # Data de la
        ctk.CTkLabel(filter_row2, text="De la (zz.ll.aaaa):",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=130, anchor="w").pack(side="left")
        self._af_from = ctk.CTkEntry(filter_row2, width=100, height=30,
                                      placeholder_text="ex: 01.05.2026")
        self._af_from.pack(side="left", padx=(0, 12))

        # Data pana la
        ctk.CTkLabel(filter_row2, text="Pana la:",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=60, anchor="w").pack(side="left")
        self._af_to = ctk.CTkEntry(filter_row2, width=100, height=30,
                                    placeholder_text="ex: 31.05.2026")
        self._af_to.pack(side="left", padx=(0, 12))

        # Durata minima
        ctk.CTkLabel(filter_row2, text="Durata min (s):",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=100, anchor="w").pack(side="left")
        self._af_dur_min = ctk.CTkEntry(filter_row2, width=60, height=30,
                                         placeholder_text="0")
        self._af_dur_min.pack(side="left", padx=(0, 12))

        # Durata maxima
        ctk.CTkLabel(filter_row2, text="max (s):",
                     font=("Arial", 11), text_color=TEXT_MID,
                     width=55, anchor="w").pack(side="left")
        self._af_dur_max = ctk.CTkEntry(filter_row2, width=60, height=30,
                                         placeholder_text="∞")
        self._af_dur_max.pack(side="left", padx=(0, 12))

        # Buton Aplica filtre
        ctk.CTkButton(filter_row2, text="🔍 Aplica filtre",
                      width=120, height=30,
                      fg_color=NAVY, hover_color=NAVY_DARK,
                      font=("Arial", 11, "bold"),
                      command=lambda: self._apply_activity_filters(tbl)
                      ).pack(side="left")

        # Buton Reset filtre
        ctk.CTkButton(filter_row2, text="✕ Reset",
                      width=80, height=30,
                      fg_color=GRAY_LIGHT, hover_color=GRAY_MID,
                      text_color=TEXT_MID, font=("Arial", 11),
                      command=lambda: self._reset_activity_filters(tbl)
                      ).pack(side="left", padx=(6, 0))

        # Label rezultate
        self._af_results_var = tk.StringVar(value="")
        ctk.CTkLabel(filter_row2, textvariable=self._af_results_var,
                     font=("Arial", 10, "italic"),
                     text_color=TEXT_LIGHT).pack(side="right", padx=(0, 12))

        # ── Tabel rezultate ──────────────────────────
        tbl = ctk.CTkScrollableFrame(tab, fg_color=WHITE,
                                      corner_radius=CORNER_RADIUS,
                                      border_width=1, border_color=GRAY_LIGHT)
        tbl.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._activity_tbl = tbl
        self._crud_reload_activity(tbl)

    def _apply_activity_filters(self, container):
        """Aplica filtrele selectate si reincarca tabelul."""
        from database import ActivityLog
        from sqlalchemy import and_
        from datetime import datetime

        for w in container.winfo_children():
            w.destroy()

        # Citeste filtrele
        user_id_str  = self._af_user.get().strip()
        tip_val      = self._af_tip.get()
        blocat_val   = self._af_blocat.get()
        limit_val    = self._af_limit.get()
        from_str     = self._af_from.get().strip()
        to_str       = self._af_to.get().strip()
        dur_min_str  = self._af_dur_min.get().strip()
        dur_max_str  = self._af_dur_max.get().strip()

        # Header tabel
        hrow = ctk.CTkFrame(container, fg_color=GRAY_LIGHT, corner_radius=0)
        hrow.pack(fill="x")
        for txt, w in [("ID", 50), ("User", 55), ("Tip", 80), ("Domeniu/Nume", 200),
                        ("Inceput", 130), ("Durata", 70), ("Blocat", 60)]:
            ctk.CTkLabel(hrow, text=txt, font=("Arial", 10, "bold"),
                         text_color=TEXT_MID, width=w, anchor="w"
                         ).pack(side="left", padx=8, pady=8)

        session = get_session(self.engine)
        try:
            q = session.query(ActivityLog)
            filters = []

            # Filtru user
            if user_id_str:
                try:
                    filters.append(
                        ActivityLog.id_utilizator == int(user_id_str))
                except ValueError:
                    pass

            # Filtru tip
            if tip_val != "toate":
                filters.append(ActivityLog.tip == tip_val)

            # Filtru blocat
            if blocat_val == "doar blocate":
                filters.append(ActivityLog.blocat == True)
            elif blocat_val == "doar neblocate":
                filters.append(ActivityLog.blocat == False)

            # Filtru data de la
            if from_str:
                try:
                    dt_from = datetime.strptime(from_str, "%d.%m.%Y")
                    filters.append(ActivityLog.inceput_la >= dt_from)
                except ValueError:
                    pass

            # Filtru data pana la
            if to_str:
                try:
                    dt_to = datetime.strptime(to_str, "%d.%m.%Y")
                    # Include toata ziua de sfarsit
                    dt_to = dt_to.replace(hour=23, minute=59, second=59)
                    filters.append(ActivityLog.inceput_la <= dt_to)
                except ValueError:
                    pass

            # Filtru durata minima
            if dur_min_str:
                try:
                    filters.append(
                        ActivityLog.durata_secunde >= int(dur_min_str))
                except ValueError:
                    pass

            # Filtru durata maxima
            if dur_max_str:
                try:
                    filters.append(
                        ActivityLog.durata_secunde <= int(dur_max_str))
                except ValueError:
                    pass

            if filters:
                q = q.filter(and_(*filters))

            q = q.order_by(ActivityLog.id.desc())

            # Limita
            if limit_val != "toate":
                q = q.limit(int(limit_val))

            logs = q.all()
            count = len(logs)
            self._af_results_var.set(
                f"{count} rezultat{'e' if count != 1 else ''}")

            if not logs:
                ctk.CTkLabel(container,
                             text="Niciun rezultat pentru filtrele selectate.",
                             font=("Arial", 11), text_color=TEXT_LIGHT
                             ).pack(pady=30)
                return

            for log in logs:
                blocked = log.blocat
                bg = "#FFF8F8" if blocked else "transparent"
                row = ctk.CTkFrame(container, fg_color=bg, corner_radius=0)
                row.pack(fill="x")
                ctk.CTkFrame(container, height=1, fg_color=GRAY_LIGHT,
                             corner_radius=0).pack(fill="x")

                time_str = (log.inceput_la.strftime("%d.%m.%Y %H:%M")
                            if log.inceput_la else "—")
                dur_str  = (f"{log.durata_secunde}s"
                            if log.durata_secunde else "—")

                for txt, w, color in [
                    (str(log.id),              50, TEXT_LIGHT),
                    (str(log.id_utilizator),   55, TEXT_MID),
                    (log.tip or "—",           80, NAVY),
                    ((log.domeniu or log.nume or "—")[:30],
                                              200, TEXT_DARK),
                    (time_str,                130, TEXT_MID),
                    (dur_str,                  70, TEXT_MID),
                    ("DA" if blocked else "",  60, ERROR_RED),
                ]:
                    ctk.CTkLabel(row, text=str(txt),
                                 font=("Arial", 10), text_color=color,
                                 width=w, anchor="w"
                                 ).pack(side="left", padx=8, pady=5)
        finally:
            session.close()

    def _reset_activity_filters(self, container):
        """Reseteaza toate filtrele la valorile implicite."""
        self._af_user.delete(0, "end")
        self._af_tip.set("toate")
        self._af_blocat.set("toate")
        self._af_limit.set("100")
        self._af_from.delete(0, "end")
        self._af_to.delete(0, "end")
        self._af_dur_min.delete(0, "end")
        self._af_dur_max.delete(0, "end")
        self._af_results_var.set("")
        self._crud_reload_activity(container)

    def _crud_reload_activity(self, container):
        """Incarcare initiala fara filtre — ultimele 100 loguri."""
        from database import ActivityLog
        for w in container.winfo_children():
            w.destroy()

        hrow = ctk.CTkFrame(container, fg_color=GRAY_LIGHT, corner_radius=0)
        hrow.pack(fill="x")
        for txt, w in [("ID", 50), ("User", 55), ("Tip", 80), ("Domeniu/Nume", 200),
                        ("Inceput", 130), ("Durata", 70), ("Blocat", 60)]:
            ctk.CTkLabel(hrow, text=txt, font=("Arial", 10, "bold"),
                         text_color=TEXT_MID, width=w, anchor="w"
                         ).pack(side="left", padx=8, pady=8)

        session = get_session(self.engine)
        try:
            logs = session.query(ActivityLog)                .order_by(ActivityLog.id.desc()).limit(100).all()
            if not logs:
                ctk.CTkLabel(container,
                             text="Niciun log inregistrat.",
                             font=("Arial", 11), text_color=TEXT_LIGHT
                             ).pack(pady=30)
                return

            for log in logs:
                blocked = log.blocat
                bg  = "#FFF8F8" if blocked else "transparent"
                row = ctk.CTkFrame(container, fg_color=bg, corner_radius=0)
                row.pack(fill="x")
                ctk.CTkFrame(container, height=1, fg_color=GRAY_LIGHT,
                             corner_radius=0).pack(fill="x")

                time_str = (log.inceput_la.strftime("%d.%m.%Y %H:%M")
                            if log.inceput_la else "—")
                dur_str  = (f"{log.durata_secunde}s"
                            if log.durata_secunde else "—")

                for txt, w, color in [
                    (str(log.id),              50, TEXT_LIGHT),
                    (str(log.id_utilizator),   55, TEXT_MID),
                    (log.tip or "—",           80, NAVY),
                    ((log.domeniu or log.nume or "—")[:30],
                                              200, TEXT_DARK),
                    (time_str,                130, TEXT_MID),
                    (dur_str,                  70, TEXT_MID),
                    ("DA" if blocked else "",  60, ERROR_RED),
                ]:
                    ctk.CTkLabel(row, text=str(txt),
                                 font=("Arial", 10), text_color=color,
                                 width=w, anchor="w"
                                 ).pack(side="left", padx=8, pady=5)
        finally:
            session.close()

    def _crud_clear_activity(self, container):
        import tkinter.messagebox as mb
        from database import ActivityLog
        if not mb.askyesno("Confirmare",
                           "Stergi tot istoricul de activitate?"):
            return
        session = get_session(self.engine)
        try:
            session.query(ActivityLog).delete()
            session.commit()
            self._crud_reload_activity(container)
            self._af_results_var.set("")
        except Exception as e:
            print(f"[CRUD] Clear activity err: {e}")
        finally:
            session.close()

    # ── CRUD: Daily Stats ─────────────────────────────────────────────────────

    def _build_crud_daily(self, tab):
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(top, text="Daily Stats",
                     font=("Georgia", 16, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

        tbl = ctk.CTkScrollableFrame(tab, fg_color=WHITE,
                                      corner_radius=CORNER_RADIUS,
                                      border_width=1, border_color=GRAY_LIGHT)
        tbl.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        ctk.CTkButton(top, text="🔄", width=40,
                      fg_color=BLUE, hover_color=BLUE_HOVER,
                      command=lambda: self._crud_reload_daily(tbl)
                      ).pack(side="right")

        self._crud_reload_daily(tbl)

    def _crud_reload_daily(self, container):
        from database import DailyStats
        for w in container.winfo_children():
            w.destroy()

        hrow = ctk.CTkFrame(container, fg_color=GRAY_LIGHT, corner_radius=0)
        hrow.pack(fill="x")
        for txt, w in [("ID", 50), ("User", 55), ("Data", 100),
                        ("Timp total", 100), ("Timp blocat", 100),
                        ("Site-uri", 70), ("Pauze", 60)]:
            ctk.CTkLabel(hrow, text=txt, font=("Arial", 10, "bold"),
                         text_color=TEXT_MID, width=w, anchor="w"
                         ).pack(side="left", padx=8, pady=8)

        session = get_session(self.engine)
        try:
            from database import DailyStats
            stats = session.query(DailyStats)                .order_by(DailyStats.id.desc()).limit(100).all()

            def fmt(sec):
                if not sec:
                    return "0m"
                h = sec // 3600
                m = (sec % 3600) // 60
                return f"{h}h{m}m" if h else f"{m}m"

            for s in stats:
                row = ctk.CTkFrame(container, fg_color="transparent",
                                   corner_radius=0)
                row.pack(fill="x")
                ctk.CTkFrame(container, height=1, fg_color=GRAY_LIGHT,
                             corner_radius=0).pack(fill="x")
                for txt, w, color in [
                    (str(s.id),                        50,  TEXT_LIGHT),
                    (str(s.id_utilizator),             55,  TEXT_MID),
                    (str(s.data),                     100,  TEXT_DARK),
                    (fmt(s.timp_total_sec or 0),      100,  NAVY),
                    (fmt(s.timp_blocat_sec or 0),     100,  ERROR_RED),
                    (str(s.site_uri_vizitate or 0),    70,  BLUE),
                    (str(s.pauze_luate or 0),          60,  GREEN),
                ]:
                    ctk.CTkLabel(row, text=str(txt),
                                 font=("Arial", 10), text_color=color,
                                 width=w, anchor="w").pack(side="left", padx=8, pady=5)
        finally:
            session.close()


    def _build_tab_monitoring(self):
        tab = self._tabs.tab("Monitorizare")

        self._blocked_sites  = []
        self._limited_sites  = {}
        self._activity_log   = []
        self._chrome_bridge  = None

        self._load_chrome_rules()

        top = ctk.CTkFrame(
            tab, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))

        ctk.CTkLabel(
            top,
            text="Monitorizare Web & Chrome",
            font=("Georgia", 22, "bold"),
            text_color=TEXT_DARK,
        ).pack(side="left")

        ctk.CTkButton(
            top, text="🔄 Refresh", width=100,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            command=self._refresh_monitoring,
        ).pack(side="right", padx=(0, 12))

        self._bridge_status_var = tk.StringVar(
            value="⬤  Extensie neconectată")
        ctk.CTkLabel(
            top,
            textvariable=self._bridge_status_var,
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
        ).pack(side="right")

        panels = ctk.CTkFrame(
            tab, fg_color="transparent")
        panels.pack(
            fill="both", expand=True,
            padx=24, pady=(0, 16))
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(0, weight=1)

        rules_panel = ctk.CTkFrame(
            panels, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        rules_panel.grid(
            row=0, column=0,
            sticky="nsew", padx=(0, 8))

        activity_panel = ctk.CTkFrame(
            panels, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        activity_panel.grid(
            row=0, column=1,
            sticky="nsew", padx=(8, 0))

        self._build_monitoring_rules_panel(
            rules_panel)
        self._build_monitoring_activity_panel(
            activity_panel)

        self._start_chrome_bridge()

    def _build_monitoring_rules_panel(self,
                                       parent):
        ph = ctk.CTkFrame(
            parent, fg_color="#F0F4FF",
            corner_radius=0, height=44)
        ph.pack(fill="x")
        ph.pack_propagate(False)

        ctk.CTkLabel(
            ph, text="  🚫  Reguli Chrome",
            font=("Arial", 13, "bold"),
            text_color=NAVY,
        ).pack(side="left", padx=12, pady=10)

        ctk.CTkButton(
            ph, text="💾 Aplică",
            width=80, height=28,
            fg_color=GREEN,
            hover_color="#2E7D32",
            font=("Arial", 11, "bold"),
            command=self._save_chrome_rules,
        ).pack(side="right", padx=12, pady=8)

        scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent")
        scroll.pack(
            fill="both", expand=True,
            padx=12, pady=8)

        # Blocked sites
        ctk.CTkLabel(
            scroll,
            text="Sites Blocate",
            font=("Arial", 12, "bold"),
            text_color=ERROR_RED,
            anchor="w",
        ).pack(anchor="w", pady=(4, 4))

        self._blocked_frame = ctk.CTkFrame(
            scroll, fg_color="transparent")
        self._blocked_frame.pack(fill="x")

        self._reload_blocked_ui()

        add_b = ctk.CTkFrame(
            scroll, fg_color="transparent")
        add_b.pack(fill="x", pady=(6, 0))

        self._add_blocked_entry = ctk.CTkEntry(
            add_b,
            placeholder_text="ex: facebook.com",
            font=("Arial", 11),
        )
        self._add_blocked_entry.pack(
            side="left", fill="x",
            expand=True, padx=(0, 8))

        ctk.CTkButton(
            add_b, text="+ Adaugă",
            width=90, height=32,
            fg_color=ERROR_RED,
            hover_color="#B71C1C",
            command=self._add_blocked_site,
        ).pack(side="right")

        ctk.CTkFrame(
            scroll, height=1,
            fg_color=GRAY_LIGHT,
            corner_radius=0,
        ).pack(fill="x", pady=(16, 8))

        # Limited sites
        ctk.CTkLabel(
            scroll,
            text="Sites cu Limită de Timp",
            font=("Arial", 12, "bold"),
            text_color="#E65100",
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))

        self._limited_frame = ctk.CTkFrame(
            scroll, fg_color="transparent")
        self._limited_frame.pack(fill="x")

        self._reload_limited_ui()

        add_l = ctk.CTkFrame(
            scroll, fg_color="transparent")
        add_l.pack(fill="x", pady=(6, 0))

        self._add_limited_entry = ctk.CTkEntry(
            add_l,
            placeholder_text="ex: youtube.com",
            font=("Arial", 11),
            width=130,
        )
        self._add_limited_entry.pack(
            side="left", padx=(0, 6))

        self._add_limited_mins = ctk.CTkEntry(
            add_l,
            placeholder_text="min",
            font=("Arial", 11),
            width=54,
        )
        self._add_limited_mins.pack(
            side="left", padx=(0, 8))

        ctk.CTkButton(
            add_l, text="+ Adaugă",
            width=90, height=32,
            fg_color="#E65100",
            hover_color="#BF360C",
            command=self._add_limited_site,
        ).pack(side="left")

    def _build_monitoring_activity_panel(self,
                                          parent):
        if self.user_role in (
                "admin", "developer"):
            ph = ctk.CTkFrame(
                parent, fg_color="#F0F4FF",
                corner_radius=0, height=44)
            ph.pack(fill="x")
            ph.pack_propagate(False)

            ctk.CTkLabel(
                ph, text="  📊  Activitate Live",
                font=("Arial", 13, "bold"),
                text_color=NAVY,
            ).pack(side="left", padx=12, pady=10)

            ctk.CTkButton(
                ph, text="🗑 Șterge",
                width=70, height=28,
                fg_color=GRAY_MID,
                hover_color=TEXT_LIGHT,
                font=("Arial", 10),
                command=self._clear_activity_log,
            ).pack(side="right", padx=12, pady=8)

            self._activity_scroll = \
                ctk.CTkScrollableFrame(
                    parent, fg_color="transparent")
            self._activity_scroll.pack(
                fill="both", expand=True,
                padx=12, pady=8)

            self._reload_activity_ui()
        else:
            ctk.CTkLabel(
                parent,
                text="📊 Activitatea live\n"
                     "este disponibilă doar\n"
                     "pentru administratori.",
                font=("Arial", 12),
                text_color=TEXT_LIGHT,
                justify="center",
            ).pack(expand=True)
            return

    def _reload_blocked_ui(self):
        for w in self._blocked_frame\
                .winfo_children():
            w.destroy()

        if not self._blocked_sites:
            ctk.CTkLabel(
                self._blocked_frame,
                text="Niciun site blocat.",
                font=("Arial", 11),
                text_color=TEXT_LIGHT,
            ).pack(anchor="w", pady=4)
            return

        for domain in self._blocked_sites:
            row = ctk.CTkFrame(
                self._blocked_frame,
                fg_color="#FFF0F0",
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=f"🚫  {domain}",
                font=("Arial", 11),
                text_color=ERROR_RED,
                anchor="w",
            ).pack(side="left", padx=10,
                   pady=6, fill="x", expand=True)

            ctk.CTkButton(
                row, text="✕",
                width=28, height=28,
                fg_color="transparent",
                hover_color=GRAY_LIGHT,
                text_color=ERROR_RED,
                font=("Arial", 11, "bold"),
                command=lambda d=domain:
                self._remove_blocked_site(d),
            ).pack(side="right", padx=6, pady=4)

    def _reload_limited_ui(self):
        for w in self._limited_frame\
                .winfo_children():
            w.destroy()

        if not self._limited_sites:
            ctk.CTkLabel(
                self._limited_frame,
                text="Nicio limită configurată.",
                font=("Arial", 11),
                text_color=TEXT_LIGHT,
            ).pack(anchor="w", pady=4)
            return

        for domain, minutes in \
                self._limited_sites.items():
            row = ctk.CTkFrame(
                self._limited_frame,
                fg_color="#FFF8F0",
                corner_radius=6,
            )
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row,
                text=f"⏱  {domain}",
                font=("Arial", 11),
                text_color="#E65100",
                anchor="w",
            ).pack(side="left", padx=10,
                   pady=6, fill="x", expand=True)

            ctk.CTkLabel(
                row,
                text=f"{minutes} min",
                font=("Arial", 11, "bold"),
                text_color="#E65100",
            ).pack(side="right", padx=4, pady=6)

            ctk.CTkButton(
                row, text="✕",
                width=28, height=28,
                fg_color="transparent",
                hover_color=GRAY_LIGHT,
                text_color="#E65100",
                font=("Arial", 11, "bold"),
                command=lambda d=domain:
                self._remove_limited_site(d),
            ).pack(side="right", padx=6, pady=4)

    def _reload_activity_ui(self):
        if not hasattr(self, '_activity_scroll'):
            return
        for w in self._activity_scroll\
                .winfo_children():
            w.destroy()

        if not self._activity_log:
            ctk.CTkLabel(
                self._activity_scroll,
                text="Nicio activitate "
                     "înregistrată.",
                font=("Arial", 11),
                text_color=TEXT_LIGHT,
            ).pack(anchor="w", pady=8)
            return

        from datetime import datetime
        for entry in self._activity_log[:50]:
            action = entry.get("action", "")
            domain = entry.get("domain", "")
            title  = entry.get("title", domain)
            ts     = entry.get("ts", 0)

            is_blocked = (action == "blocked")
            bg   = "#FFEBEE" if is_blocked \
                else "white"
            fg   = ERROR_RED if is_blocked \
                else TEXT_DARK
            icon = "🚫" if is_blocked else "🌐"

            try:
                time_str = datetime.fromtimestamp(
                    ts / 1000).strftime("%H:%M:%S")
            except Exception:
                time_str = "—"

            row = ctk.CTkFrame(
                self._activity_scroll,
                fg_color=bg,
                corner_radius=4,
            )
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                row,
                text=f"{icon}  "
                     f"{title[:35]}"
                     f"{'...' if len(title) > 35 else ''}",
                font=("Arial", 10),
                text_color=fg,
                anchor="w",
            ).pack(side="left", padx=8, pady=4)

            ctk.CTkLabel(
                row,
                text=time_str,
                font=("Arial", 9),
                text_color=TEXT_LIGHT,
            ).pack(side="right", padx=8)

    def _render_activity_entry(self,
                                data: dict):
        action = data.get("action", "visit")
        domain = data.get(
            "domain", data.get("url", "—"))
        ts     = data.get("ts", 0)

        time_str = (
            datetime.fromtimestamp(ts)
            .strftime("%H:%M:%S")
            if ts else "—")

        color_map = {
            "block": (ERROR_RED,  "🚫"),
            "visit": (NAVY,       "🌐"),
            "limit": ("#E65100",  "⏱"),
        }
        color, icon = color_map.get(
            action, (TEXT_MID, "•"))

        row = ctk.CTkFrame(
            self._activity_scroll,
            fg_color="#F8F9FA",
            corner_radius=6,
        )
        row.pack(fill="x", pady=2)

        ctk.CTkLabel(
            row, text=icon,
            font=("Arial", 14),
        ).pack(side="left",
               padx=(10, 4), pady=6)

        ctk.CTkLabel(
            row, text=domain,
            font=("Arial", 11, "bold"),
            text_color=color, anchor="w",
        ).pack(side="left", fill="x",
               expand=True, pady=6)

        ctk.CTkLabel(
            row, text=time_str,
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(side="right", padx=10, pady=6)

    def _add_blocked_site(self):
        raw = self._add_blocked_entry\
            .get().strip().lower()
        # Curata URL -> domeniu curat
        domain = raw\
            .replace("https://", "")\
            .replace("http://", "")\
            .replace("www.", "")\
            .split("/")[0]\
            .strip()
        if not domain:
            return
        if domain in self._blocked_sites:
            return
        self._blocked_sites.append(domain)
        self._add_blocked_entry.delete(0, "end")
        self._reload_blocked_ui()
        self._save_rule_to_db(
            domain, "blocat", None)
        self._save_chrome_rules()

    def _remove_blocked_site(self, domain: str):
        if domain in self._blocked_sites:
            self._blocked_sites.remove(domain)
        self._deactivate_rule_in_db(domain)
        self._reload_blocked_ui()
        self._save_chrome_rules()

    def _add_limited_site(self):
        raw = self._add_limited_entry\
            .get().strip().lower()
        mins_str = self._add_limited_mins\
            .get().strip()

        # DEBUG
        print(f"[DEBUG LIMITED] raw='{raw}' "
              f"mins_str='{mins_str}'")

        domain = raw\
            .replace("https://", "")\
            .replace("http://", "")\
            .replace("www.", "")\
            .split("/")[0]\
            .strip()
        if not domain:
            return
        try:
            mins = int(mins_str) if mins_str else 30
            if mins <= 0:
                mins = 30
        except ValueError:
            mins = 30
        self._limited_sites[domain] = mins
        self._add_limited_entry.delete(0, "end")
        self._add_limited_mins.delete(0, "end")
        self._reload_limited_ui()
        self._save_rule_to_db(
            domain, "limitat", mins)
        print(f"[DEBUG] Salvez limitat: "
              f"{domain} = {mins} min")
        self._save_chrome_rules()

    def _save_rule_to_db(self, domain: str,
                          tip: str,
                          limita: int = None):
        try:
            from database import (
                get_session, SiteRule, Utilizator)
            session = get_session(self.engine)
            try:
                # Determina pentru cine salvam
                if self.user_role in (
                        "admin", "developer"):
                    # Aplica la TOTI utilizatorii
                    users = session.query(
                        Utilizator).all()
                    user_ids = [
                        u.id_utilizator
                        for u in users]
                else:
                    # Doar pentru utilizatorul curent
                    user_ids = [self.user_id]

                for uid in user_ids:
                    existing = session.query(
                        SiteRule).filter_by(
                        id_utilizator=uid,
                        domeniu=domain,
                    ).first()
                    if existing:
                        existing.tip = tip
                        existing.limita_minute = limita
                        existing.activ = True
                    else:
                        rule = SiteRule(
                            id_utilizator=uid,
                            domeniu=domain,
                            tip=tip,
                            limita_minute=limita,
                            activ=True,
                        )
                        session.add(rule)

                session.commit()
                scope = "toti" \
                    if self.user_role in (
                        "admin", "developer") \
                    else "user"
                print(f"[MONITORING] DB: "
                      f"{domain} ({tip}) "
                      f"-> {scope}")
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITORING] DB err: {e}")

    def _remove_limited_site(self, domain: str):
        if domain in self._limited_sites:
            del self._limited_sites[domain]
        self._deactivate_rule_in_db(domain)
        self._reload_limited_ui()
        self._save_chrome_rules()

    def _deactivate_rule_in_db(self,
                                 domain: str):
        try:
            from database import (
                get_session, SiteRule, Utilizator)
            session = get_session(self.engine)
            try:
                if self.user_role in (
                        "admin", "developer"):
                    # Sterge pentru toti
                    rules = session.query(
                        SiteRule).filter_by(
                        domeniu=domain,
                    ).all()
                else:
                    rules = session.query(
                        SiteRule).filter_by(
                        domeniu=domain,
                        id_utilizator=self.user_id,
                    ).all()
                for r in rules:
                    r.activ = False
                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITORING] Del err: {e}")

    def _save_chrome_rules(self):
        try:
            from database import (
                get_session, SiteRule)
            session = get_session(self.engine)
            try:
                # Incarca regulile pentru
                # TOTI utilizatorii daca admin
                if self.user_role in (
                        "admin", "developer"):
                    rules = session.query(
                        SiteRule).filter_by(
                        activ=True).all()
                else:
                    rules = session.query(
                        SiteRule).filter_by(
                        id_utilizator=self.user_id,
                        activ=True).all()

                blocked = list(set(
                    r.domeniu for r in rules
                    if r.tip == "blocat"))
                limited = {}
                for r in rules:
                    if r.tip == "limitat":
                        limited[r.domeniu] = \
                            r.limita_minute or 30

            finally:
                session.close()

            if self._chrome_bridge:
                self._chrome_bridge\
                    .publish_rules(
                    blocked = blocked,
                    limited = limited,
                    user_id = self.user_id,
                )
            print(f"[MONITORING] Trimis: "
                  f"{len(blocked)} blocate, "
                  f"{len(limited)} limitate.")
        except Exception as e:
            print(f"[MONITORING] Save err: {e}")

    def _load_chrome_rules(self):
        try:
            from database import (
                get_session, SiteRule)
            session = get_session(self.engine)
            try:
                if self.user_role in (
                        "admin", "developer"):
                    rules = session.query(
                        SiteRule).filter_by(
                        activ=True,
                    ).all()
                else:
                    rules = session.query(
                        SiteRule).filter_by(
                        id_utilizator=self.user_id,
                        activ=True,
                    ).all()
                blocked = []
                limited = {}
                for r in rules:
                    # Curata domeniu vechi
                    d = r.domeniu\
                        .replace("https://", "")\
                        .replace("http://", "")\
                        .replace("www.", "")\
                        .split("/")[0].strip()
                    if not d:
                        continue
                    # Actualizeaza in DB daca era gresit
                    if d != r.domeniu:
                        r.domeniu = d
                    if r.tip == "blocat":
                        blocked.append(d)
                    elif r.tip == "limitat":
                        limited[d] = \
                            r.limita_minute or 30
                session.commit()
                self._blocked_sites = blocked
                self._limited_sites = limited
                return
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITORING] Load err: {e}")
        # Fallback fisier JSON
        import json, os
        try:
            rules_file = os.path.join(
                os.path.expanduser("~"),
                ".coffee_axl",
                "chrome_rules.json")
            if os.path.exists(rules_file):
                with open(
                        rules_file,
                        encoding="utf-8") as f:
                    data = json.load(f)
                self._blocked_sites = data.get(
                    "blocked", [])
                self._limited_sites = data.get(
                    "limited", {})
        except Exception:
            pass

    def _start_chrome_bridge(self):
        try:
            from utils.chrome_bridge import (
                ChromeBridge)
            self._chrome_bridge = ChromeBridge(
                engine     = self.engine,
                on_event   = lambda d:
                    self.after(
                        0,
                        lambda data=d:
                        self._on_chrome_activity(
                            data)
                    ) if self.user_role in (
                        "admin", "developer"
                    ) else None,
                on_blocked = self._on_site_blocked,
            )
            self._chrome_bridge.start()
            self.after(
                0,
                lambda: self._bridge_status_var
                .set("⬤  Extensie activă"))
            print("[MONITORING] Bridge pornit.")
        except Exception as e:
            print(f"[MONITORING] Bridge err: {e}")

    def _on_chrome_activity(self, data: dict):
        action = data.get("action", "")
        domain = data.get("domain", "")
        if not domain:
            return
        entry = {
            "action": action,
            "domain": domain,
            "title":  data.get("title", domain),
            "ts":     data.get("ts", 0),
        }
        self._activity_log.insert(0, entry)
        # Pastreaza doar ultimele 100
        self._activity_log = \
            self._activity_log[:100]
        self.after(0, self._reload_activity_ui)

    def _refresh_monitoring(self):
        self._load_chrome_rules()
        self._reload_blocked_ui()
        self._reload_limited_ui()
        self._reload_activity_ui()
        self._save_chrome_rules()
        print("[MONITORING] Refreshed.")

    def _clear_activity_log(self):
        self._activity_log = []
        self._reload_activity_ui()

    def _on_site_blocked(self, domain: str,
                          user_id=None,
                          reason: str = "blocat"):
        print(f"[DASHBOARD] Blocat: {domain} "
              f"({reason})")
        self.after(
            0, self._reload_activity_ui)

    # ── Tab: Debug ────────────────────────────────────────────────────────────

    def _build_tab_debug(self):
        tab = self._tabs.tab("Debug")

        inner_tabs = ctk.CTkTabview(
            tab,
            fg_color=OFF_WHITE,
            segmented_button_fg_color=GRAY_LIGHT,
            segmented_button_selected_color="#8B7500",
            segmented_button_selected_hover_color="#6B5500",
            segmented_button_unselected_color=GRAY_LIGHT,
            segmented_button_unselected_hover_color=GRAY_MID,
            text_color=TEXT_MID,
            corner_radius=0,
        )
        inner_tabs.pack(fill="both", expand=True)

        inner_tabs.add("Sistem")
        inner_tabs.add("Vision & Emotii")
        inner_tabs.add("AVC — BEFAST")
        inner_tabs.add("AI Engine")
        inner_tabs.add("Baza de Date")

        self._build_debug_sistem(
            inner_tabs.tab("Sistem"))
        self._build_debug_vision(
            inner_tabs.tab("Vision & Emotii"))
        self._build_debug_befast(
            inner_tabs.tab("AVC — BEFAST"))
        self._build_debug_ai(
            inner_tabs.tab("AI Engine"))
        self._build_debug_db(
            inner_tabs.tab("Baza de Date"))

    # ── Debug: Sistem ─────────────────────────────────────────────────────────

    def _build_debug_sistem(self, tab):
        import sys

        scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent")
        scroll.pack(
            fill="both", expand=True,
            padx=24, pady=16)

        ctk.CTkLabel(
            scroll, text="Sistem & Diagnostics",
            font=("Georgia", 18, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", pady=(0, 12))

        console = ctk.CTkFrame(
            scroll, fg_color="#0D1117",
            corner_radius=12)
        console.pack(fill="both", expand=True)

        session = get_session(self.engine)
        try:
            n_users = session.query(
                Utilizator).count()
            n_logs  = session.query(
                IstoricLogare).count()
        finally:
            session.close()

        try:
            local_ip = socket.gethostbyname(
                socket.gethostname())
        except Exception:
            local_ip = "127.0.0.1"

        lines = [
            ("╔══════════════════════════════════════╗",
             "#4C8CE4"),
            ("║   Coffee & Axl  ·  Dev Console v1.0 ║",
             "#4C8CE4"),
            ("╚══════════════════════════════════════╝",
             "#4C8CE4"),
            ("", None),
            (f"[SYS]  Python       : "
             f"{sys.version.split()[0]}", "#91D06C"),
            (f"[SYS]  Platform     : "
             f"{sys.platform}", "#91D06C"),
            (f"[SYS]  Timestamp    : "
             f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             "#91D06C"),
            (f"[SYS]  Local IP     : "
             f"{local_ip}", "#91D06C"),
            ("", None),
            (f"[DB]   Utilizatori  : {n_users}",
             "#FFF799"),
            (f"[DB]   Sesiuni log  : {n_logs}",
             "#FFF799"),
            ("[DB]   Path         : "
             "~/.coffee_axl/coffee_axl.db",
             "#FFF799"),
            ("", None),
            (f"[AUTH] User ID      : {self.user_id}",
             "#B0BDD0"),
            (f"[AUTH] Username     : "
             f"{self.user_name}", "#B0BDD0"),
            ("[AUTH] Rol activ    : DEVELOPER",
             "#B0BDD0"),
            ("", None),
            ("[AI]   Ollama URL   : "
             "http://localhost:11434", "#E0A0FF"),
            ("[AI]   Model        : llama3",
             "#E0A0FF"),
            ("[AI]   Bridge       : "
             "AIInterventionBridge activ",
             "#E0A0FF"),
            ("", None),
            ("[VISION] EAR Threshold  : 0.22",
             "#FFB347"),
            ("[VISION] Sad Threshold  : -0.02",
             "#FFB347"),
            ("[VISION] Confirm delay  : 8.0s",
             "#FFB347"),
            ("[VISION] Cooldown       : dezactivat",
             "#FFB347"),
            ("", None),
            ("[OK]   Toate modulele sunt nominale.",
             "#91D06C"),
        ]

        for text, color in lines:
            ctk.CTkLabel(
                console,
                text=text or " ",
                font=("Courier New", 12),
                text_color=color or "#0D1117",
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=20, pady=1)

        input_row = ctk.CTkFrame(
            console, fg_color="transparent")
        input_row.pack(
            fill="x", padx=20, pady=(8, 16))
        ctk.CTkLabel(
            input_row,
            text="dev@coffee-axl:~$ ",
            font=("Courier New", 12),
            text_color="#91D06C",
        ).pack(side="left")
        ctk.CTkEntry(
            input_row,
            font=("Courier New", 12),
            fg_color="transparent",
            border_width=0,
            text_color=WHITE,
            placeholder_text="comenzi viitoare...",
            placeholder_text_color="#444",
        ).pack(side="left", fill="x", expand=True)

    # ── Debug: Vision ─────────────────────────────────────────────────────────

    def _build_debug_vision(self, tab):
        from components.vision_tab import VisionTab

        vt = VisionTab(
            tab, user_id=self.user_id,
            engine=self.engine)

        pb_key = self._get_dev_pb_key()
        if pb_key:
            vt._pb_api_key = pb_key
            vt._user_name  = self.user_name
            try:
                vt._pb_status_var.set(
                    f"✓ Cheie dev injectată "
                    f"(••••{pb_key[-6:]})")
                vt._pb_status_lbl.configure(
                    text_color=GREEN)
            except Exception:
                pass

        self._vision_tab = vt

        def _connect():
            time.sleep(1.5)
            try:
                if self._chatbot_ref:
                    vt.connect_chatbot(
                        self._chatbot_ref)
                    self._chatbot_ref\
                        .set_navigate_to_chat_callback(
                        self._navigate_to_chat)
                    print("[DASHBOARD] "
                          "AI Bridge conectat.")
            except Exception as e:
                print(f"[DASHBOARD] "
                      f"AI Bridge eroare: {e}")

        threading.Thread(
            target=_connect, daemon=True).start()

    # ── Debug: AVC BEFAST ─────────────────────────────────────────────────────

    def _build_debug_befast(self, tab):
        from components.befast_tab import BEFASTTab

        pb_key = self._get_dev_pb_key()

        bt = BEFASTTab(
            tab,
            user_id    = self.user_id,
            engine     = self.engine,
            pb_api_key = pb_key or "",
            user_name  = self.user_name,
        )

        if self._vision_tab:
            self._vision_tab._befast_tab       = bt
            self._vision_tab._befast_video_tab = bt

        self._befast_tab = bt

    # ── Debug: AI Engine ──────────────────────────────────────────────────────

    def _build_debug_ai(self, tab):
        outer = ctk.CTkFrame(
            tab, fg_color="transparent")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        header = ctk.CTkFrame(
            outer, fg_color="#0D1117",
            corner_radius=0, height=48)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="AI Engine Debug  ·  "
                 "Ollama / Llama3  ·  "
                 "Intervention Bridge activ",
            font=("Courier New", 11),
            text_color="#91D06C",
        ).pack(side="left", padx=16, pady=12)

        self._ai_status_var = tk.StringVar(
            value="verificare Ollama...")
        ctk.CTkLabel(
            header,
            textvariable=self._ai_status_var,
            font=("Courier New", 10),
            text_color="#FFF799",
        ).pack(side="right", padx=16)

        chat_frame = ctk.CTkFrame(
            outer, fg_color="transparent")
        chat_frame.grid(
            row=1, column=0, sticky="nsew")

        ChatbotTab(
            chat_frame,
            user_name=f"DEV:{self.user_name}")

        def _check():
            try:
                from utils.ai_engine import (
                    check_ollama_available)
                ok, msg = check_ollama_available()
                color  = "#91D06C" if ok \
                    else "#FF8080"
                prefix = "OK: " if ok else "ERR: "
                self.after(
                    0,
                    lambda: self._ai_status_var
                    .set(prefix + msg))
            except Exception as e:
                self.after(
                    0,
                    lambda: self._ai_status_var
                    .set(f"ERR: {e}"))

        threading.Thread(
            target=_check, daemon=True).start()

    # ── Debug: Baza de Date ───────────────────────────────────────────────────

    def _build_debug_db(self, tab):
        from database import (
            IstoricMedical, PersoanaContact)

        scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent")
        scroll.pack(
            fill="both", expand=True,
            padx=24, pady=16)

        ctk.CTkLabel(
            scroll, text="Inspector Baza de Date",
            font=("Georgia", 18, "bold"),
            text_color=TEXT_DARK,
        ).pack(anchor="w", pady=(0, 16))

        session = get_session(self.engine)
        try:
            n_users   = session.query(
                Utilizator).count()
            n_medical = session.query(
                IstoricMedical).count()
            n_contact = session.query(
                PersoanaContact).count()
            n_logare  = session.query(
                IstoricLogare).count()
        finally:
            session.close()

        row = ctk.CTkFrame(
            scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))

        for tbl, count, color in [
            ("utilizator",       n_users,   NAVY),
            ("istoric_medical",  n_medical, GREEN),
            ("persoana_contact", n_contact, BLUE),
            ("istoric_logare",   n_logare,  TEXT_MID),
        ]:
            card = ctk.CTkFrame(
                row, fg_color=WHITE,
                corner_radius=CORNER_RADIUS,
                border_width=1,
                border_color=GRAY_LIGHT,
            )
            card.pack(side="left", padx=6,
                      expand=True, fill="both")
            ctk.CTkLabel(
                card, text=str(count),
                font=("Georgia", 28, "bold"),
                text_color=color,
            ).pack(pady=(16, 2))
            ctk.CTkLabel(
                card, text=tbl,
                font=("Courier New", 10),
                text_color=TEXT_LIGHT,
            ).pack(pady=(0, 16))

        self._build_db_section(
            scroll, "Utilizatori",
            lambda s: s.query(Utilizator).all(),
            self._render_user_row)
        self._build_db_section(
            scroll, "Persoane Contact",
            lambda s: s.query(
                PersoanaContact).all(),
            self._render_contact_row)
        self._build_db_section(
            scroll, "Ultimele 10 Logari",
            lambda s: s.query(IstoricLogare)
            .order_by(
                IstoricLogare.data_ora.desc()
            ).limit(10).all(),
            self._render_logare_row)

    def _build_db_section(self, parent, title,
                          query_fn, render_fn):
        section = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        section.pack(fill="x", pady=(0, 12))

        sh = ctk.CTkFrame(
            section, fg_color="#F0F4FF",
            corner_radius=0, height=40)
        sh.pack(fill="x")
        sh.pack_propagate(False)
        ctk.CTkLabel(
            sh, text=f"  {title}",
            font=("Courier New", 12, "bold"),
            text_color=NAVY,
        ).pack(side="left", padx=12, pady=8)

        inner = ctk.CTkFrame(
            section, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        session = get_session(self.engine)
        try:
            records = query_fn(session)
            if not records:
                ctk.CTkLabel(
                    inner,
                    text="Nicio inregistrare.",
                    font=("Courier New", 11),
                    text_color=TEXT_LIGHT,
                ).pack(anchor="w")
            else:
                for rec in records:
                    render_fn(inner, rec)
        finally:
            session.close()

    def _render_user_row(self, parent, u):
        rw = ctk.CTkFrame(
            parent, fg_color="transparent")
        rw.pack(fill="x", pady=2)
        for text, color, width in [
            (f"#{u.id_utilizator}",
             TEXT_LIGHT,  40),
            (u.nume_utilizator,
             TEXT_DARK,  140),
            (u.rol,
             BLUE,        100),
            (f"{u.prenume or ''} "
             f"{u.nume or ''}".strip() or "—",
             TEXT_MID, 160),
            (u.creat_la.strftime("%d.%m.%Y")
             if u.creat_la else "—",
             TEXT_LIGHT, 100),
        ]:
            ctk.CTkLabel(
                rw, text=text,
                font=("Courier New", 11),
                text_color=color,
                width=width, anchor="w",
            ).pack(side="left")

    def _render_contact_row(self, parent, c):
        rw = ctk.CTkFrame(
            parent, fg_color="transparent")
        rw.pack(fill="x", pady=2)
        has_pb = bool(c.cheie_pushbullet)
        pb_txt = (
            f"PB: ****{c.cheie_pushbullet[-6:]}"
            if has_pb else "PB: —")
        for text, color, width in [
            (f"#{c.id_contact}",
             TEXT_LIGHT,  40),
            (f"{c.prenume} {c.nume}",
             TEXT_DARK,  160),
            (c.nr_telefon or "—",
             TEXT_MID,   120),
            (pb_txt,
             GREEN if has_pb
             else TEXT_LIGHT, 160),
        ]:
            ctk.CTkLabel(
                rw, text=text,
                font=("Courier New", 11),
                text_color=color,
                width=width, anchor="w",
            ).pack(side="left")

    def _render_logare_row(self, parent, lg):
        rw = ctk.CTkFrame(
            parent, fg_color="transparent")
        rw.pack(fill="x", pady=2)
        for text, color, width in [
            (f"#{lg.id_logare}",
             TEXT_LIGHT,  40),
            (f"user={lg.id_utilizator}",
             NAVY,       120),
            (lg.adresa_ip or "—",
             TEXT_MID,   120),
            (lg.data_ora.strftime(
                "%H:%M:%S %d.%m.%Y")
             if lg.data_ora else "—",
             TEXT_LIGHT, 160),
        ]:
            ctk.CTkLabel(
                rw, text=text,
                font=("Courier New", 11),
                text_color=color,
                width=width, anchor="w",
            ).pack(side="left")

    # ── Pushbullet developer ──────────────────────────────────────────────────

    def _get_dev_pb_key(self) -> str | None:
        from database import PersoanaContact

        session = get_session(self.engine)
        try:
            contact = session.query(
                PersoanaContact
            ).filter(
                PersoanaContact.id_utilizator
                == self.user_id,
                PersoanaContact.cheie_pushbullet
                .isnot(None),
            ).first()

            if contact:
                print(f"[DEV] Cheie gasita: "
                      f"{contact.prenume} "
                      f"{contact.nume}")
                return contact.cheie_pushbullet

            contact = session.query(
                PersoanaContact
            ).filter(
                PersoanaContact.cheie_pushbullet
                .isnot(None),
            ).first()

            if contact:
                print(f"[DEV] Cheie globala: "
                      f"{contact.prenume} "
                      f"{contact.nume}")
                return contact.cheie_pushbullet

            return None

        except Exception as e:
            print(f"[DEV] Eroare cheie: {e}")
            return None
        finally:
            session.close()