"""
Coffee & Axl - Dashboard Utilizator v3
Sidebar minimal (Chat / Setări), chatbot ca ecran principal,
setări cu: cont editabil, companion picker cu poze mari,
reguli site-uri, avertisment medical.
Preview animalet în sidebar se actualizează live.
"""
import os
import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from PIL import Image

from utils.theme import *
from utils.ui_utils import show_toast
from components.chatbot_tab import ChatbotTab


# ─── Constante ───────────────────────────────────────────────────────────────
_SIDEBAR_W  = 210
_PREFS_FILE = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "pet_pref.txt")
_IPC_FILE   = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "pet_ipc.txt")
_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets")

_PET_META = {
    "axl":    {"name": "Axl",    "desc": "Husky vesel",   "emoji": "🐺",
               "accent": "#4FB3E8", "bg": "#EAF6FF", "border_sel": "#4FB3E8"},
    "coffee": {"name": "Coffee", "desc": "Pisică curioasă", "emoji": "🐱",
               "accent": "#3DB85C", "bg": "#EDFAF1", "border_sel": "#3DB85C"},
}


def _ctk_img(filename: str, size=(160, 160)):
    try:
        path = os.path.join(_ASSETS_DIR, filename)
        if not os.path.exists(path):
            return None
        img = Image.open(path).convert("RGBA")
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


def _read_pref() -> str:
    try:
        if os.path.exists(_PREFS_FILE):
            val = open(_PREFS_FILE).read().strip()
            if val in _PET_META:
                return val
    except Exception:
        pass
    return "axl"


def _write_pref(pet: str):
    try:
        os.makedirs(os.path.dirname(_PREFS_FILE), exist_ok=True)
        open(_PREFS_FILE, "w").write(pet)
    except Exception:
        pass


def _send_ipc(cmd: str):
    try:
        os.makedirs(os.path.dirname(_IPC_FILE), exist_ok=True)
        open(_IPC_FILE, "w").write(cmd)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
class DashboardPacient(ctk.CTkFrame):

    def __init__(self, parent, engine, user_id: int,
                 user_name: str, on_logout,
                 activity_monitor=None):
        super().__init__(parent, fg_color=OFF_WHITE, corner_radius=0)
        self.engine            = engine
        self.user_id           = user_id
        self.user_name         = user_name
        self.on_logout         = on_logout
        self._activity_monitor = activity_monitor
        self._live_stats_job   = None
        self._current_view     = "chat"
        self._img_cache        = {}   # filename -> CTkImage

        self._build_ui()
        self._start_activity_monitor_bg()

    # ═════════════════════════════════════════════════════════════════════════
    # UI ROOT
    # ═════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    # ═════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ═════════════════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        sb = ctk.CTkFrame(
            self, fg_color=NAVY,
            width=_SIDEBAR_W, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)

        # Logo
        from utils.theme import load_logo
        logo = load_logo(size=(60, 60))
        if logo:
            ctk.CTkLabel(sb, image=logo, text="").pack(pady=(24, 4))
        else:
            ctk.CTkLabel(sb, text="☕",
                         font=("Arial", 36), text_color=YELLOW).pack(
                pady=(24, 4))

        ctk.CTkLabel(sb, text="Coffee & Axl",
                     font=("Georgia", 13, "bold"),
                     text_color=WHITE).pack()

        ctk.CTkFrame(sb, width=60, height=2,
                     fg_color="#2E4A72").pack(pady=(8, 0))

        # Utilizator
        ctk.CTkLabel(sb, text=self.user_name,
                     font=("Arial", 11, "bold"),
                     text_color="#9FBDD8").pack(pady=(10, 0))
        ctk.CTkLabel(sb,
                     text=datetime.now().strftime("%d %b %Y"),
                     font=("Arial", 9),
                     text_color="#4A6A8A").pack(pady=(2, 16))

        ctk.CTkFrame(sb, height=1, fg_color="#1E3050",
                     corner_radius=0).pack(fill="x", padx=16,
                                           pady=(0, 14))

        # Nav
        self._btn_chat = ctk.CTkButton(
            sb, text="  💬  Chat Wellness",
            anchor="w", height=46,
            fg_color="#2A4268", hover_color=NAVY_DARK,
            text_color=WHITE, font=("Arial", 13, "bold"),
            corner_radius=10, command=self._show_chat)
        self._btn_chat.pack(fill="x", padx=12, pady=3)

        self._btn_setari = ctk.CTkButton(
            sb, text="  ⚙️  Setări",
            anchor="w", height=46,
            fg_color="transparent", hover_color=NAVY_DARK,
            text_color="#6B85A8", font=("Arial", 13),
            corner_radius=10, command=self._show_setari)
        self._btn_setari.pack(fill="x", padx=12, pady=3)

        self._btn_stats = ctk.CTkButton(
            sb, text="  📊  Statistici",
            anchor="w", height=46,
            fg_color="transparent", hover_color=NAVY_DARK,
            text_color="#6B85A8", font=("Arial", 13),
            corner_radius=10, command=self._show_stats)
        self._btn_stats.pack(fill="x", padx=12, pady=3)

        ctk.CTkFrame(sb, height=1, fg_color="#1E3050",
                     corner_radius=0).pack(fill="x", padx=16,
                                           pady=(18, 14))

        # Companion preview
        ctk.CTkLabel(sb, text="Companion",
                     font=("Arial", 9),
                     text_color="#4A6A8A").pack()

        self._sb_pet_img_lbl = ctk.CTkLabel(sb, text="", image=None)
        self._sb_pet_img_lbl.pack(pady=(8, 2))

        self._sb_pet_name_lbl = ctk.CTkLabel(
            sb, text="",
            font=("Arial", 11, "bold"),
            text_color="#9FBDD8")
        self._sb_pet_name_lbl.pack()

        self._sb_refresh_pet()

        # Iesire jos
        ctk.CTkButton(
            sb, text="🚪  Ieșire",
            anchor="w", height=38,
            fg_color="transparent", hover_color="#3A1010",
            text_color=ERROR_RED, font=("Arial", 12),
            corner_radius=8, command=self._logout,
        ).pack(fill="x", padx=12, pady=4, side="bottom")
        ctk.CTkLabel(sb, text="v1.1",
                     font=("Arial", 9),
                     text_color="#2A3A50").pack(
            side="bottom", pady=(0, 2))

    def _sb_refresh_pet(self):
        """Actualizează imaginea + numele companionului din sidebar."""
        pet   = _read_pref()
        meta  = _PET_META.get(pet, _PET_META["axl"])
        key   = f"sb_{pet}"

        if key not in self._img_cache:
            img = _ctk_img(f"{pet}_sidebar.png", (64, 64))
            if img is None:
                img = _ctk_img(f"{pet}_companion.png", (64, 64))
            self._img_cache[key] = img

        img = self._img_cache.get(key)
        try:
            if img:
                self._sb_pet_img_lbl.configure(image=img, text="",
                                               font=("Arial", 1))
            else:
                self._sb_pet_img_lbl.configure(
                    image=None, text=meta["emoji"],
                    font=("Arial", 36))
            self._sb_pet_name_lbl.configure(
                text=f"{meta['name']} {meta['emoji']}")
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    # CONTENT AREA
    # ═════════════════════════════════════════════════════════════════════════

    def _build_content(self):
        self._content = ctk.CTkFrame(
            self, fg_color=OFF_WHITE, corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")
        self._content.rowconfigure(1, weight=1)
        self._content.columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(
            self._content, fg_color=WHITE,
            corner_radius=0, height=56)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.columnconfigure(0, weight=1)

        self._hdr_title = ctk.CTkLabel(
            hdr, text="Chat Wellness",
            font=("Georgia", 18, "bold"), text_color=TEXT_DARK)
        self._hdr_title.pack(side="left", padx=24, pady=12)

        self._hdr_sub = ctk.CTkLabel(
            hdr, text="Axl este gata să te asculte",
            font=("Arial", 11), text_color=TEXT_LIGHT)
        self._hdr_sub.pack(side="right", padx=24)

        # Pagini (stacked)
        pf = ctk.CTkFrame(
            self._content, fg_color=OFF_WHITE, corner_radius=0)
        pf.grid(row=1, column=0, sticky="nsew")
        pf.rowconfigure(0, weight=1)
        pf.columnconfigure(0, weight=1)
        self._page_frame = pf

        self._build_page_chat()
        self._build_page_setari()
        self._build_page_stats()
        self._show_chat()

    # ═════════════════════════════════════════════════════════════════════════
    # PAGINA CHAT
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_chat(self):
        self._frame_chat = ctk.CTkFrame(
            self._page_frame, fg_color=OFF_WHITE, corner_radius=0)
        self._frame_chat.grid(row=0, column=0, sticky="nsew")
        ChatbotTab(self._frame_chat, user_name=self.user_name)

    # ═════════════════════════════════════════════════════════════════════════
    # PAGINA SETĂRI
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_setari(self):
        self._frame_setari = ctk.CTkFrame(
            self._page_frame, fg_color=OFF_WHITE, corner_radius=0)
        self._frame_setari.grid(row=0, column=0, sticky="nsew")
        self._frame_setari.rowconfigure(0, weight=1)
        self._frame_setari.columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            self._frame_setari, fg_color="transparent",
            corner_radius=0)
        scroll.pack(fill="both", expand=True)

        self._build_s_cont(scroll)
        self._build_s_companion(scroll)
        self._build_s_reguli(scroll)
        self._build_s_avertisment(scroll)

        ctk.CTkButton(
            scroll, text="🚪  Deconectare",
            height=44, corner_radius=10,
            fg_color=ERROR_RED, hover_color="#C04040",
            font=("Arial", 13, "bold"), text_color=WHITE,
            command=self._logout,
        ).pack(anchor="w", padx=28, pady=(12, 32))

    # ─── Sectiune header helper ───────────────────────────────────────────────

    def _sec(self, parent, icon: str, title: str):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=28, pady=(22, 10))
        ctk.CTkFrame(row, width=4, height=20,
                     fg_color=BLUE, corner_radius=2).pack(
            side="left", padx=(0, 10))
        ctk.CTkLabel(row, text=f"{icon}  {title}",
                     font=("Georgia", 15, "bold"),
                     text_color=TEXT_DARK).pack(side="left")

    def _card(self, parent, **kwargs):
        defaults = dict(fg_color=WHITE, corner_radius=14,
                        border_width=1, border_color=GRAY_LIGHT)
        defaults.update(kwargs)
        c = ctk.CTkFrame(parent, **defaults)
        c.pack(fill="x", padx=28, pady=(0, 8))
        return c

    # ─── Cont ────────────────────────────────────────────────────────────────

    def _build_s_cont(self, parent):
        self._sec(parent, "👤", "Informații cont")

        from database import Utilizator, get_session
        sess = get_session(self.engine)
        try:
            u = sess.query(Utilizator).filter_by(
                id_utilizator=self.user_id).first()
        finally:
            sess.close()

        card = self._card(parent)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=16)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        # Câmpuri editabile: prenume, nume, vârstă, telefon
        fields = [
            ("Prenume",  "prenume",   u.prenume   if u else "", 0, 0),
            ("Nume",     "nume",      u.nume      if u else "", 0, 2),
            ("Vârstă",   "varsta",    str(u.varsta or "") if u else "", 1, 0),
            ("Telefon",  "nr_telefon",u.nr_telefon if u else "", 1, 2),
        ]

        self._cont_entries = {}
        for lbl_text, field, val, row, col in fields:
            ctk.CTkLabel(inner, text=lbl_text,
                         font=("Arial", 11, "bold"),
                         text_color=TEXT_MID,
                         anchor="w").grid(
                row=row*2, column=col, columnspan=2,
                sticky="w", pady=(0, 4),
                padx=(0 if col == 0 else 16, 0))
            ent = ctk.CTkEntry(
                inner, placeholder_text=lbl_text,
                height=38, corner_radius=8,
                border_color="#DCE6F5", border_width=1.5,
                fg_color="#F5F8FF", text_color=TEXT_DARK,
                font=("Arial", 12))
            ent.insert(0, val or "")
            ent.grid(row=row*2+1, column=col, columnspan=2,
                     sticky="ew", pady=(0, 12),
                     padx=(0 if col == 0 else 16, 0))
            ent.bind("<FocusIn>",
                     lambda e, w=ent: w.configure(
                         border_color=BLUE))
            ent.bind("<FocusOut>",
                     lambda e, w=ent: w.configure(
                         border_color="#DCE6F5"))
            self._cont_entries[field] = ent

        # Adresă (full width)
        ctk.CTkLabel(inner, text="Adresă",
                     font=("Arial", 11, "bold"),
                     text_color=TEXT_MID,
                     anchor="w").grid(
            row=4, column=0, columnspan=4,
            sticky="w", pady=(0, 4))
        addr_ent = ctk.CTkEntry(
            inner, placeholder_text="ex: Str. Florilor 12, București",
            height=38, corner_radius=8,
            border_color="#DCE6F5", border_width=1.5,
            fg_color="#F5F8FF", text_color=TEXT_DARK,
            font=("Arial", 12))
        addr_ent.insert(0, u.adresa if (u and u.adresa) else "")
        addr_ent.grid(row=5, column=0, columnspan=4,
                      sticky="ew", pady=(0, 4))
        addr_ent.bind("<FocusIn>",
                      lambda e, w=addr_ent: w.configure(border_color=BLUE))
        addr_ent.bind("<FocusOut>",
                      lambda e, w=addr_ent: w.configure(border_color="#DCE6F5"))
        self._cont_entries["adresa"] = addr_ent

        # Schimbare parolă
        ctk.CTkFrame(inner, height=1, fg_color=GRAY_LIGHT,
                     corner_radius=0).grid(
            row=6, column=0, columnspan=4,
            sticky="ew", pady=(8, 12))

        ctk.CTkLabel(inner, text="Parolă nouă (lasă gol pentru a păstra)",
                     font=("Arial", 11, "bold"),
                     text_color=TEXT_MID, anchor="w").grid(
            row=7, column=0, columnspan=4,
            sticky="w", pady=(0, 4))

        self._pass_entry = ctk.CTkEntry(
            inner, placeholder_text="••••••••",
            show="•", height=38, corner_radius=8,
            border_color="#DCE6F5", border_width=1.5,
            fg_color="#F5F8FF", font=("Arial", 12))
        self._pass_entry.grid(row=8, column=0, columnspan=2,
                              sticky="ew", pady=(0, 4))
        self._pass_entry.bind("<FocusIn>",
                              lambda e: self._pass_entry.configure(
                                  border_color=BLUE))
        self._pass_entry.bind("<FocusOut>",
                              lambda e: self._pass_entry.configure(
                                  border_color="#DCE6F5"))

        self._pass2_entry = ctk.CTkEntry(
            inner, placeholder_text="Confirmă parola",
            show="•", height=38, corner_radius=8,
            border_color="#DCE6F5", border_width=1.5,
            fg_color="#F5F8FF", font=("Arial", 12))
        self._pass2_entry.grid(row=8, column=2, columnspan=2,
                               sticky="ew", padx=(16, 0), pady=(0, 4))
        self._pass2_entry.bind("<FocusIn>",
                               lambda e: self._pass2_entry.configure(
                                   border_color=BLUE))
        self._pass2_entry.bind("<FocusOut>",
                               lambda e: self._pass2_entry.configure(
                                   border_color="#DCE6F5"))

        self._cont_msg = ctk.CTkLabel(
            inner, text="",
            font=("Arial", 11), text_color=GREEN)
        self._cont_msg.grid(row=9, column=0, columnspan=4,
                            sticky="w", pady=(2, 0))

        ctk.CTkButton(
            card, text="💾  Salvează modificările",
            height=40, corner_radius=10,
            fg_color=NAVY, hover_color=NAVY_DARK,
            font=("Arial", 12, "bold"), text_color=WHITE,
            command=self._save_cont,
        ).pack(anchor="e", padx=20, pady=(0, 16))

    def _save_cont(self):
        from database import Utilizator, get_session
        sess = get_session(self.engine)
        try:
            u = sess.query(Utilizator).filter_by(
                id_utilizator=self.user_id).first()
            if not u:
                return

            u.prenume    = self._cont_entries["prenume"].get().strip() or None
            u.nume       = self._cont_entries["nume"].get().strip() or None
            u.adresa     = self._cont_entries["adresa"].get().strip() or None
            u.nr_telefon = self._cont_entries["nr_telefon"].get().strip() or None

            varsta_str = self._cont_entries["varsta"].get().strip()
            try:
                u.varsta = int(varsta_str) if varsta_str else None
            except ValueError:
                self._cont_msg.configure(
                    text="Vârsta trebuie să fie un număr.",
                    text_color=ERROR_RED)
                return

            # Schimbare parolă opțional
            p1 = self._pass_entry.get()
            p2 = self._pass2_entry.get()
            if p1 or p2:
                if p1 != p2:
                    self._cont_msg.configure(
                        text="Parolele nu coincid.",
                        text_color=ERROR_RED)
                    return
                if len(p1) < 6:
                    self._cont_msg.configure(
                        text="Parola trebuie să aibă cel puțin 6 caractere.",
                        text_color=ERROR_RED)
                    return
                u.set_parola(p1)
                self._pass_entry.delete(0, "end")
                self._pass2_entry.delete(0, "end")

            sess.commit()
            self._cont_msg.configure(
                text="✓ Salvat cu succes!",
                text_color=GREEN)
            self.after(3000, lambda: self._cont_msg.configure(text="")
                       if self.winfo_exists() else None)
            show_toast(self.winfo_toplevel(),
                       "Cont actualizat!", kind="success")
        except Exception as e:
            self._cont_msg.configure(
                text=f"Eroare: {e}", text_color=ERROR_RED)
        finally:
            sess.close()

    # ─── Companion ───────────────────────────────────────────────────────────

    def _build_s_companion(self, parent):
        self._sec(parent, "🐾", "Companionul tău")

        card = self._card(parent)

        ctk.CTkLabel(
            card,
            text="Animalul ales apare în colțul ecranului și te însoțește "
                 "toată ziua. Poți schimba oricând.",
            font=("Arial", 11), text_color=TEXT_LIGHT,
            wraplength=580, justify="left",
        ).pack(anchor="w", padx=20, pady=(16, 14))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(pady=(0, 20))

        current = _read_pref()
        self._pet_card_frames = {}

        for pet_key, meta in _PET_META.items():
            is_sel = (pet_key == current)
            accent = meta["accent"]
            bg     = meta["bg"] if is_sel else WHITE

            pet_frame = ctk.CTkFrame(
                row,
                fg_color=bg,
                corner_radius=18,
                border_width=3 if is_sel else 1,
                border_color=accent if is_sel else "#E0E8F0",
                width=200, height=270,
            )
            pet_frame.pack(side="left", padx=14)
            pet_frame.pack_propagate(False)
            self._pet_card_frames[pet_key] = pet_frame

            # Imagine animalet mare
            img_key = f"companion_{pet_key}"
            if img_key not in self._img_cache:
                img = _ctk_img(f"{pet_key}_companion.png", (150, 150))
                if img is None:
                    img = _ctk_img(f"{pet_key}_idle.png", (150, 150))
                self._img_cache[img_key] = img

            img = self._img_cache.get(img_key)
            if img:
                lbl_img = ctk.CTkLabel(
                    pet_frame, image=img, text="",
                    cursor="hand2")
                lbl_img.pack(pady=(18, 6))
                lbl_img.bind("<Button-1>",
                             lambda e, pk=pet_key: self._select_pet(pk))
            else:
                ctk.CTkLabel(
                    pet_frame, text=meta["emoji"],
                    font=("Arial", 70), cursor="hand2",
                ).pack(pady=(22, 6))

            ctk.CTkLabel(
                pet_frame, text=meta["name"],
                font=("Georgia", 15, "bold"),
                text_color=TEXT_DARK,
            ).pack()
            ctk.CTkLabel(
                pet_frame, text=meta["desc"],
                font=("Arial", 10),
                text_color=TEXT_LIGHT,
            ).pack(pady=(2, 0))

            # Badge selectat
            self._build_pet_badge(pet_frame, pet_key, is_sel, accent)

            # Click pe frame
            pet_frame.bind("<Button-1>",
                           lambda e, pk=pet_key: self._select_pet(pk))

    def _build_pet_badge(self, parent, pet_key, is_sel, accent):
        badge = ctk.CTkFrame(
            parent,
            fg_color=accent if is_sel else "#EEF0F4",
            corner_radius=8,
            width=110, height=26,
        )
        badge.pack(pady=(8, 0))
        badge.pack_propagate(False)

        lbl = ctk.CTkLabel(
            badge,
            text="✓ Selectat" if is_sel else "Selectează",
            font=("Arial", 10, "bold"),
            text_color=WHITE if is_sel else TEXT_LIGHT,
        )
        lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Stocam referinte pentru update rapid
        if not hasattr(self, "_pet_badges"):
            self._pet_badges = {}
        self._pet_badges[pet_key] = (badge, lbl)

    def _select_pet(self, pet_key: str):
        _write_pref(pet_key)
        _send_ipc(f"set_pet:{pet_key}")

        for pk, meta in _PET_META.items():
            is_sel = (pk == pet_key)
            accent = meta["accent"]
            bg     = meta["bg"] if is_sel else WHITE

            # Actualizeaza cardul
            try:
                self._pet_card_frames[pk].configure(
                    fg_color=bg,
                    border_width=3 if is_sel else 1,
                    border_color=accent if is_sel else "#E0E8F0",
                )
            except Exception:
                pass

            # Actualizeaza badge
            if hasattr(self, "_pet_badges") and pk in self._pet_badges:
                badge, lbl = self._pet_badges[pk]
                try:
                    badge.configure(
                        fg_color=accent if is_sel else "#EEF0F4")
                    lbl.configure(
                        text="✓ Selectat" if is_sel else "Selectează",
                        text_color=WHITE if is_sel else TEXT_LIGHT)
                except Exception:
                    pass

        # Invalideaza cache sidebar pt re-fetch
        self._img_cache.pop(f"sb_{pet_key}", None)
        self._sb_refresh_pet()

        meta = _PET_META[pet_key]
        show_toast(
            self.winfo_toplevel(),
            f"{meta['name']} {meta['emoji']} este noul tău companion!",
            kind="success", duration_ms=2500)

    # ─── Reguli site-uri ──────────────────────────────────────────────────────

    def _build_s_reguli(self, parent):
        self._sec(parent, "🚫", "Reguli site-uri")

        card = self._card(parent)

        ctk.CTkLabel(
            card,
            text="Domenii pe care extensia Chrome le va bloca "
                 "sau limita ca timp zilnic.",
            font=("Arial", 11), text_color=TEXT_LIGHT,
            wraplength=580, justify="left",
        ).pack(anchor="w", padx=20, pady=(14, 10))

        self._rules_list = ctk.CTkFrame(card, fg_color="transparent")
        self._rules_list.pack(fill="x", padx=16, pady=(0, 6))
        self._reload_rules_ui()

        ctk.CTkFrame(card, height=1, fg_color=GRAY_LIGHT,
                     corner_radius=0).pack(fill="x", padx=16,
                                           pady=(4, 12))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=(0, 16))
        form.columnconfigure(0, weight=1)

        ctk.CTkLabel(form, text="Domeniu",
                     font=("Arial", 11, "bold"),
                     text_color=TEXT_MID, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        ent_row = ctk.CTkFrame(form, fg_color="transparent")
        ent_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ent_row.columnconfigure(0, weight=1)

        self._rule_domain_entry = ctk.CTkEntry(
            ent_row, placeholder_text="ex: facebook.com, tiktok.com",
            height=38, corner_radius=8, font=("Arial", 12))
        self._rule_domain_entry.grid(row=0, column=0, sticky="ew",
                                     padx=(0, 8))
        ctk.CTkButton(
            ent_row, text="+ Adaugă",
            width=100, height=38, corner_radius=8,
            fg_color=NAVY, hover_color=NAVY_DARK,
            font=("Arial", 11, "bold"), text_color=WHITE,
            command=self._add_rule,
        ).grid(row=0, column=1)

        type_row = ctk.CTkFrame(form, fg_color="transparent")
        type_row.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self._rule_type_var = tk.StringVar(value="blocat")
        ctk.CTkRadioButton(
            type_row, text="Blocat total",
            variable=self._rule_type_var, value="blocat",
            text_color=ERROR_RED, fg_color=ERROR_RED,
        ).pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(
            type_row, text="Limitat (minute/zi)",
            variable=self._rule_type_var, value="limitat",
            text_color="#E65100", fg_color="#E65100",
        ).pack(side="left")

        self._rule_limit_entry = ctk.CTkEntry(
            form,
            placeholder_text="Limita în minute/zi (ex: 30)  — doar pentru Limitat",
            height=36, corner_radius=8, font=("Arial", 11))
        self._rule_limit_entry.grid(row=3, column=0, sticky="ew")

    def _reload_rules_ui(self):
        for w in self._rules_list.winfo_children():
            w.destroy()

        rules = []
        try:
            from database import get_session, SiteRule
            sess = get_session(self.engine)
            try:
                rules = sess.query(SiteRule).filter_by(
                    id_utilizator=self.user_id, activ=True).all()
            finally:
                sess.close()
        except Exception:
            pass

        if not rules:
            ctk.CTkLabel(
                self._rules_list,
                text="Nicio regulă configurată.",
                font=("Arial", 11), text_color=TEXT_LIGHT,
            ).pack(anchor="w", pady=6)
            return

        for r in rules:
            blocked = r.tip == "blocat"
            color = ERROR_RED if blocked else "#E65100"
            bg    = "#FFF0F0" if blocked else "#FFF8F0"
            icon  = "🚫" if blocked else "⏱"
            lbl   = f"{icon}  {r.domeniu}"
            if r.tip == "limitat" and r.limita_minute:
                lbl += f"  ({r.limita_minute} min/zi)"

            row = ctk.CTkFrame(
                self._rules_list, fg_color=bg, corner_radius=8)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row, text=lbl,
                font=("Arial", 11), text_color=color, anchor="w",
            ).pack(side="left", padx=12, pady=7,
                   fill="x", expand=True)
            ctk.CTkButton(
                row, text="✕",
                width=28, height=28,
                fg_color="transparent", hover_color=GRAY_LIGHT,
                text_color=color, font=("Arial", 11, "bold"),
                command=lambda d=r.domeniu: self._del_rule(d),
            ).pack(side="right", padx=8, pady=4)

    def _add_rule(self):
        domain  = self._rule_domain_entry.get().strip().lower()
        tip     = self._rule_type_var.get()
        lim_str = self._rule_limit_entry.get().strip()
        if not domain:
            return
        limita = None
        if tip == "limitat":
            try:
                limita = int(lim_str)
                if limita <= 0:
                    return
            except ValueError:
                return
        try:
            from database import get_session, SiteRule
            sess = get_session(self.engine)
            try:
                sess.add(SiteRule(
                    id_utilizator=self.user_id, domeniu=domain,
                    tip=tip, limita_minute=limita, activ=True))
                sess.commit()
            finally:
                sess.close()
            self._rule_domain_entry.delete(0, "end")
            self._rule_limit_entry.delete(0, "end")
            self._reload_rules_ui()
            if self._activity_monitor:
                try:
                    self._activity_monitor.reload_rules()
                except Exception:
                    pass
            show_toast(self.winfo_toplevel(),
                       f"Regulă adăugată: {domain}",
                       kind="success", duration_ms=2000)
        except Exception as e:
            print(f"[RULE] Add err: {e}")

    def _del_rule(self, domain: str):
        try:
            from database import get_session, SiteRule
            sess = get_session(self.engine)
            try:
                for r in sess.query(SiteRule).filter_by(
                    id_utilizator=self.user_id,
                    domeniu=domain, activ=True,
                ).all():
                    r.activ = False
                sess.commit()
            finally:
                sess.close()
            self._reload_rules_ui()
            if self._activity_monitor:
                try:
                    self._activity_monitor.reload_rules()
                except Exception:
                    pass
        except Exception as e:
            print(f"[RULE] Del err: {e}")

    # ─── Avertisment medical ──────────────────────────────────────────────────

    def _build_s_avertisment(self, parent):
        self._sec(parent, "⚕️", "Avertisment medical")

        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFDF0",
            corner_radius=14,
            border_width=1,
            border_color="#EED060",
        )
        card.pack(fill="x", padx=28, pady=(0, 8))

        hdr_row = ctk.CTkFrame(card, fg_color="transparent")
        hdr_row.pack(fill="x", padx=20, pady=(16, 10))
        ctk.CTkLabel(hdr_row, text="⚠️",
                     font=("Arial", 26)).pack(side="left",
                                              padx=(0, 12))
        ctk.CTkLabel(
            hdr_row,
            text="Această aplicație NU înlocuiește\n"
                 "consultul unui medic specialist",
            font=("Arial", 13, "bold"),
            text_color="#7A5800", justify="left",
        ).pack(side="left")

        texts = [
            ("🔵", "Coffee & Axl este un instrument de wellness digital. "
             "Nu poate pune diagnostice și nu înlocuiește evaluarea medicală."),
            ("🔴", "Detectarea BEFAST a semnelor de AVC este o alertă de urgență, "
             "NU un diagnostic. La orice simptom serios, sunați imediat 112."),
            ("🟡", "Axl oferă suport emoțional conversațional, nu terapie psihologică. "
             "Pentru probleme de sănătate mintală, consultați un specialist calificat."),
        ]
        for icon, txt in texts:
            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=20, pady=(0, 8))
            ctk.CTkLabel(r, text=icon,
                         font=("Arial", 13)).pack(side="left",
                                                  padx=(0, 10),
                                                  anchor="n",
                                                  pady=2)
            ctk.CTkLabel(
                r, text=txt,
                font=("Arial", 11), text_color="#6B5500",
                wraplength=540, justify="left",
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkFrame(card, height=12,
                     fg_color="transparent").pack()

    # ═════════════════════════════════════════════════════════════════════════
    # PAGINA STATISTICI
    # ═════════════════════════════════════════════════════════════════════════

    def _build_page_stats(self):
        from components.stats_tab import StatsPage
        self._frame_stats = ctk.CTkFrame(
            self._page_frame, fg_color=OFF_WHITE, corner_radius=0)
        self._frame_stats.grid(row=0, column=0, sticky="nsew")
        self._frame_stats.rowconfigure(0, weight=1)
        self._frame_stats.columnconfigure(0, weight=1)
        self._stats_page = StatsPage(
            self._frame_stats,
            engine           = self.engine,
            user_id          = self.user_id,
            activity_monitor = self._activity_monitor,
        )
        self._stats_page.pack(fill="both", expand=True)

    # ═════════════════════════════════════════════════════════════════════════
    # NAVIGARE
    # ═════════════════════════════════════════════════════════════════════════

    def _show_stats(self):
        """Afiseaza pagina Statistici in zona principala."""
        self._current_view = "stats"
        self._frame_stats.tkraise()
        self._hdr_title.configure(text="Statistici zilnice")
        self._hdr_sub.configure(text="Activitatea ta de azi")
        self._btn_stats.configure(
            fg_color="#2A4268", text_color=WHITE,
            font=("Arial", 13, "bold"))
        self._btn_chat.configure(
            fg_color="transparent", text_color="#6B85A8",
            font=("Arial", 13))
        self._btn_setari.configure(
            fg_color="transparent", text_color="#6B85A8",
            font=("Arial", 13))
        try:
            self._stats_page.refresh()
        except Exception as e:
            print(f"[STATS] refresh err: {e}")
    def _show_chat(self):
        self._current_view = "chat"
        self._frame_chat.tkraise()
        self._hdr_title.configure(text="Chat Wellness")
        self._hdr_sub.configure(text="Axl este gata să te asculte")
        self._btn_chat.configure(
            fg_color="#2A4268", text_color=WHITE,
            font=("Arial", 13, "bold"))
        self._btn_setari.configure(
            fg_color="transparent", text_color="#6B85A8",
            font=("Arial", 13))
        if hasattr(self, "_btn_stats"):
            self._btn_stats.configure(
                fg_color="transparent", text_color="#6B85A8",
                font=("Arial", 13))

    def _show_setari(self):
        self._current_view = "setari"
        self._frame_setari.tkraise()
        self._hdr_title.configure(text="Setări")
        self._hdr_sub.configure(text="Personalizează aplicația")
        self._btn_setari.configure(
            fg_color="#2A4268", text_color=WHITE,
            font=("Arial", 13, "bold"))
        self._btn_chat.configure(
            fg_color="transparent", text_color="#6B85A8",
            font=("Arial", 13))
        if hasattr(self, "_btn_stats"):
            self._btn_stats.configure(
                fg_color="transparent", text_color="#6B85A8",
                font=("Arial", 13))

    def _navigate_to_chat(self):
        self._show_chat()

    def _go_to_tab(self, index: int):
        if index == 1:
            self._show_chat()
        else:
            self._show_setari()

    # ═════════════════════════════════════════════════════════════════════════
    # ACTIVITY MONITOR
    # ═════════════════════════════════════════════════════════════════════════

    def _start_activity_monitor_bg(self):
        try:
            if (self._activity_monitor is not None and
                    hasattr(self._activity_monitor, "_thread") and
                    self._activity_monitor._thread is not None and
                    self._activity_monitor._thread.is_alive()):
                self._activity_monitor._on_blocked = \
                    self._on_blocked_toast
                return
            self._activity_monitor = None

            from utils.activity_monitor import ActivityMonitor
            from database import PersoanaContact, get_session
            pb_key  = ""
            sess = get_session(self.engine)
            try:
                c = sess.query(PersoanaContact).filter(
                    PersoanaContact.id_utilizator == self.user_id,
                    PersoanaContact.cheie_pushbullet.isnot(None),
                ).first()
                if c:
                    pb_key = c.cheie_pushbullet or ""
            finally:
                sess.close()

            self._activity_monitor = ActivityMonitor(
                engine    = self.engine,
                user_id   = self.user_id,
                user_name = self.user_name,
                pb_api_key = pb_key,
                on_blocked = self._on_blocked_toast,
            )
            self._activity_monitor.start()
        except Exception as e:
            print(f"[MONITOR] {e}")

    def _on_blocked_toast(self, domain: str, limitat: bool):
        msg = (f"Limita depășită: {domain}"
               if limitat else f"Site blocat: {domain}")
        try:
            self.after(0, lambda: show_toast(
                self.winfo_toplevel(), msg,
                kind="warning", duration_ms=3500))
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════════
    # LOGOUT
    # ═════════════════════════════════════════════════════════════════════════

    def _logout(self):
        if self._live_stats_job:
            try:
                self.after_cancel(self._live_stats_job)
            except Exception:
                pass
        self._activity_monitor = None
        from utils.session import clear_session
        clear_session()
        show_toast(self.winfo_toplevel(),
                   "Deconectat cu succes.", kind="info",
                   duration_ms=1500)
        self.after(600, self.on_logout)

    # Stubs compatibilitate
    def _tick_live_clock(self): pass
    def _reload_activity_log_ui(self): pass
    def _monitor_status_var(self): return None