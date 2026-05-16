"""
Coffee & Axl - Login Screen
Remediata: animatie fade-in, progress bar la autentificare,
shake animation la eroare, feedback vizual imbunatatit.
"""
import customtkinter as ctk
import tkinter as tk
from PIL import Image
import os
import socket
from datetime import datetime

from database import Utilizator, IstoricLogare, get_session
from utils.theme import *
from utils.ui_utils import fade_in, show_toast


def _load_logo(size: tuple) -> ctk.CTkImage | None:
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "assets", "logo.png")
        img  = Image.open(path).convert("RGBA")
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)
    except Exception:
        return None


class LoginScreen(ctk.CTkFrame):

    def __init__(self, parent, engine, on_login_success):
        super().__init__(parent, fg_color="#EEF3FB", corner_radius=0)
        self.engine           = engine
        self.on_login_success = on_login_success
        self._loading         = False
        self._build_ui()
        # Fade-in fereastra principala la prima afisare
        try:
            fade_in(parent, steps=14, delay_ms=16, start=0.05, end=1.0)
        except Exception:
            pass

    def _build_ui(self):
        self.pack(fill="both", expand=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Card central
        card = ctk.CTkFrame(
            self,
            fg_color=WHITE,
            corner_radius=28,
            border_width=1,
            border_color="#DCE6F5",
            width=420,
            height=660,
        )
        card.grid(row=0, column=0, padx=20, pady=20)
        card.grid_propagate(False)

        self._build_header(card)
        self._build_form(card)
        self._build_footer(card)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self, card):
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(pady=(36, 0))

        logo = _load_logo((100, 100))
        if logo:
            logo_lbl = ctk.CTkLabel(header, image=logo, text="")
            logo_lbl.pack()
        else:
            circle = ctk.CTkFrame(
                header, fg_color="#D6E8FF",
                corner_radius=50, width=100, height=100,
            )
            circle.pack()
            circle.pack_propagate(False)
            ctk.CTkLabel(
                circle, text="☕",
                font=("Arial", 44), text_color=NAVY,
            ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            header, text="Coffee & Axl",
            font=("Georgia", 26, "bold"), text_color=NAVY,
        ).pack(pady=(14, 2))

        ctk.CTkLabel(
            header, text="Wellness-ul tău digital",
            font=("Arial", 13), text_color=TEXT_LIGHT,
        ).pack()

        ctk.CTkFrame(
            header, height=2, width=60,
            fg_color="#D6E8FF", corner_radius=2,
        ).pack(pady=(16, 0))

    # ── Formular ──────────────────────────────────────────────────────────────

    def _build_form(self, card):
        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=40, pady=(24, 0))

        # Camp utilizator
        ctk.CTkLabel(
            form, text="Nume utilizator",
            font=("Arial", 12, "bold"),
            text_color=TEXT_MID, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.entry_user = ctk.CTkEntry(
            form, placeholder_text="ex: ion.popescu",
            height=46, corner_radius=14,
            border_color="#DCE6F5", border_width=1.5,
            fg_color="#F5F8FF", text_color=TEXT_DARK,
            font=("Arial", 13),
        )
        self.entry_user.pack(fill="x", pady=(0, 16))
        self.entry_user.bind("<Return>",   lambda e: self.entry_pass.focus())
        self.entry_user.bind("<FocusIn>",  lambda e: self.entry_user.configure(border_color=BLUE))
        self.entry_user.bind("<FocusOut>", lambda e: self.entry_user.configure(border_color="#DCE6F5"))

        # Camp parola
        ctk.CTkLabel(
            form, text="Parolă",
            font=("Arial", 12, "bold"),
            text_color=TEXT_MID, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self.entry_pass = ctk.CTkEntry(
            form, placeholder_text="••••••••",
            show="•", height=46, corner_radius=14,
            border_color="#DCE6F5", border_width=1.5,
            fg_color="#F5F8FF", text_color=TEXT_DARK,
            font=("Arial", 13),
        )
        self.entry_pass.pack(fill="x", pady=(0, 8))
        self.entry_pass.bind("<Return>",   lambda e: self._handle_login())
        self.entry_pass.bind("<FocusIn>",  lambda e: self.entry_pass.configure(border_color=BLUE))
        self.entry_pass.bind("<FocusOut>", lambda e: self.entry_pass.configure(border_color="#DCE6F5"))

        # Toggle parola
        self._show_pass = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            form, text="Arată parola",
            variable=self._show_pass,
            command=lambda: self.entry_pass.configure(
                show="" if self._show_pass.get() else "•"
            ),
            font=("Arial", 11), text_color=TEXT_LIGHT,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            border_color="#DCE6F5",
            checkbox_width=16, checkbox_height=16,
            corner_radius=4,
        ).pack(anchor="w", pady=(0, 16))

        # Mesaj eroare
        self.lbl_error = ctk.CTkLabel(
            form, text="",
            font=("Arial", 12),
            text_color=ERROR_RED,
            wraplength=300,
        )
        self.lbl_error.pack(pady=(0, 8))

        # Progress bar (ascunsa initial)
        self._progress_frame = ctk.CTkFrame(
            form, fg_color="transparent", height=4)
        self._progress_frame.pack(fill="x", pady=(0, 8))
        self._progress_frame.pack_propagate(False)

        self._progress_bar = ctk.CTkProgressBar(
            self._progress_frame,
            mode="indeterminate",
            height=4, corner_radius=2,
            fg_color="#E8ECF3",
            progress_color=BLUE,
        )
        self._progress_bar.pack(fill="x")
        self._progress_bar.set(0)

        # Buton login
        self.btn_login = ctk.CTkButton(
            form, text="Conectare",
            height=50, corner_radius=14,
            fg_color=NAVY, hover_color=NAVY_DARK,
            font=("Georgia", 15, "bold"),
            text_color=WHITE,
            command=self._handle_login,
        )
        self.btn_login.pack(fill="x")

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self, card):
        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(20, 30))

        ctk.CTkFrame(
            footer, height=1, fg_color="#DCE6F5", corner_radius=0,
        ).pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            footer, text="Conturi demo",
            font=("Arial", 11), text_color=TEXT_LIGHT,
        ).pack(pady=(0, 8))

        btn_row = ctk.CTkFrame(footer, fg_color="transparent")
        btn_row.pack()

        demo_accounts = [
            ("Admin", "admin", "admin123", NAVY,   WHITE),
            ("Dev",   "dev",   "dev123",   YELLOW, TEXT_DARK),
            ("User",  "user",  "user123",  BLUE,   WHITE),
        ]
        for label, user, pwd, bg, fg in demo_accounts:
            ctk.CTkButton(
                btn_row, text=label,
                width=88, height=32, corner_radius=10,
                fg_color=bg,
                hover_color=NAVY_DARK if bg == NAVY else (
                    "#E8E070" if bg == YELLOW else BLUE_HOVER
                ),
                font=("Arial", 11, "bold"), text_color=fg,
                command=lambda u=user, p=pwd: self._fill_demo(u, p),
            ).pack(side="left", padx=4)

    # ── Logica ────────────────────────────────────────────────────────────────

    def _fill_demo(self, username: str, password: str):
        self.entry_user.delete(0, "end")
        self.entry_user.insert(0, username)
        self.entry_pass.delete(0, "end")
        self.entry_pass.insert(0, password)
        self.lbl_error.configure(text="")

    def _handle_login(self):
        if self._loading:
            return
        u = self.entry_user.get().strip()
        p = self.entry_pass.get()

        if not u or not p:
            self._show_error("Completează ambele câmpuri.")
            return

        self._loading = True
        self.btn_login.configure(text="Se verifică...", state="disabled")
        self.lbl_error.configure(text="")
        # Porneste progress bar
        self._progress_bar.start()
        self.after(80, lambda: self._authenticate(u, p))

    def _authenticate(self, username: str, password: str):
        session = get_session(self.engine)
        try:
            user = session.query(Utilizator).filter_by(
                nume_utilizator=username
            ).first()

            if not user or not user.verifica_parola(password):
                self._progress_bar.stop()
                self._progress_bar.set(0)
                self._loading = False
                self._show_error("Credențiale incorecte. Încearcă din nou.")
                self.btn_login.configure(text="Conectare", state="normal")
                return

            user_id   = user.id_utilizator
            user_rol  = user.rol
            user_name = user.prenume or user.nume_utilizator

            session.add(IstoricLogare(
                id_utilizator=user_id,
                adresa_ip=self._get_ip(),
                data_ora=datetime.now(),
            ))
            session.commit()

        except Exception as e:
            self._progress_bar.stop()
            self._progress_bar.set(0)
            self._loading = False
            self._show_error(f"Eroare sistem: {str(e)}")
            self.btn_login.configure(text="Conectare", state="normal")
            return
        finally:
            session.close()

        from utils.session import save_session
        save_session(user_id, user_rol, user_name)

        # Animatie succes
        self._progress_bar.stop()
        self._progress_bar.configure(
            mode="determinate", progress_color=GREEN)
        self._progress_bar.set(1.0)

        self.btn_login.configure(
            text="✓  Acces permis",
            fg_color=GREEN,
            state="disabled",
        )
        self.after(
            480,
            lambda: self.on_login_success(user_id, user_rol, user_name)
        )

    def _show_error(self, msg: str):
        self.lbl_error.configure(text=msg)
        # Shake animation pe campurile de input
        self._shake_widget(self.entry_user)
        self._shake_widget(self.entry_pass)
        self.entry_user.configure(border_color="#FFAAAA")
        self.entry_pass.configure(border_color="#FFAAAA")
        self.after(2500, lambda: (
            self.entry_user.configure(border_color="#DCE6F5"),
            self.entry_pass.configure(border_color="#DCE6F5"),
            self.lbl_error.configure(text=""),
        ) if self.winfo_exists() else None)

    def _shake_widget(self, widget, steps: int = 8,
                      amplitude: int = 5, delay: int = 30):
        """Animatie de shake pe un widget — feedback eroare."""
        try:
            orig_x = widget.winfo_x()
            orig_y = widget.winfo_y()
        except Exception:
            return

        offsets = []
        for i in range(steps):
            sign  = 1 if i % 2 == 0 else -1
            decay = 1.0 - (i / steps)
            offsets.append(int(sign * amplitude * decay))
        offsets.append(0)

        def _step(idx):
            if idx >= len(offsets):
                return
            try:
                widget.place_configure(x=orig_x + offsets[idx])
                widget.after(delay, lambda: _step(idx + 1))
            except Exception:
                pass

        # Shake merge doar daca widget-ul e in place layout
        # In pack layout il sarim (nu da eroare, dar nu se vede)
        try:
            widget.pack_info()
        except Exception:
            _step(0)

    @staticmethod
    def _get_ip() -> str:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"