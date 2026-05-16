"""
Coffee & Axl - BEFAST Tab
UI responsive, waveform animat, flux video la F si A.
Buton de oprire rapida a testului.
"""

import customtkinter as ctk
import tkinter as tk
import threading
import time
import math
import random

from utils.befast_engine import BEFASTEngine, BEFASTState
from utils.stroke_detector import SEVERE_THRESHOLD
from utils.theme import *


class BEFASTTab(ctk.CTkFrame):

    def __init__(self, parent, user_id: int,
                 engine, pb_api_key: str,
                 user_name: str):
        super().__init__(
            parent, fg_color=OFF_WHITE,
            corner_radius=0)
        self.user_id    = user_id
        self.db_engine  = engine
        self.pb_api_key = pb_api_key
        self.user_name  = user_name

        self._befast_engine = None
        self._mic_active    = False
        self._mic_volume    = 0.0
        self._mic_frame_n   = 0
        self._video_photo   = None

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._init_befast_engine()

    # ── Init engine ───────────────────────────────────────────────────────────

    def _init_befast_engine(self):
        threading.Thread(
            target=self._create_engine,
            daemon=True,
        ).start()

    def _safe_after(self, ms, fn):
        """
        Apeleaza fn pe main thread in mod sigur,
        chiar daca suntem intr-un thread de background.
        """
        try:
            self.after(ms, fn)
        except RuntimeError:
            # Nu suntem pe main thread — folosim
            # event_generate ca workaround
            try:
                self.tk.call('after', ms, self.tk.register(fn))
            except Exception:
                pass

    def _create_engine(self):
        try:
            engine = BEFASTEngine(
                pb_api_key      = self.pb_api_key or "",
                user_name       = self.user_name,
                on_state_change = self._on_state_change,
            )
            self._befast_engine = engine

            # Frame annotat -> video label
            engine._on_annotated_frame = \
                lambda f: self._safe_after(
                    0,
                    lambda fr=f:
                    self.update_video_frame(fr))

            # Volum -> waveform
            engine.set_volume_callback(
                lambda v: self._safe_after(
                    0,
                    lambda vol=v:
                    self._on_volume(vol)))

            # Transcriere -> UI
            def _set_cb():
                time.sleep(0.5)
                if self._befast_engine:
                    self._befast_engine\
                        .on_transcript = \
                        lambda t: self._safe_after(
                            0,
                            lambda: self
                            ._transcript_var
                            .set(f'"{t}"'))
            threading.Thread(
                target=_set_cb,
                daemon=True).start()

            self._safe_after(
                0,
                lambda: self._status_var.set(
                    "Motor BEFAST + Analyzer gata"))
        except Exception as e:
            self._safe_after(
                0,
                lambda err=str(e): self._status_var.set(
                    f"Eroare init: {err}"))

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(
            self, fg_color=NAVY,
            corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="🧠  Detector AVC — "
                 "Protocol B.E.F.A.S.T.",
            font=("Georgia", 15, "bold"),
            text_color=WHITE,
        ).pack(side="left", padx=20, pady=14)

        self._status_var = tk.StringVar(
            value="⟳ Inițializare...")
        ctk.CTkLabel(
            header,
            textvariable=self._status_var,
            font=("Arial", 11),
            text_color=GRAY_MID,
        ).pack(side="right", padx=20)

    def _build_body(self):
        body = ctk.CTkFrame(
            self, fg_color="transparent")
        body.pack(
            fill="both", expand=True,
            padx=16, pady=12)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left_panel(body)
        self._build_right_panel(body)

    # ── Panoul stang ──────────────────────────────────────────────────────────

    def _build_left_panel(self, parent):
        outer = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        outer.grid(row=0, column=0,
                   sticky="nsew", padx=(0, 8))

        scroll = ctk.CTkScrollableFrame(
            outer, fg_color="transparent",
            corner_radius=0,
        )
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            scroll,
            text="Monitorizare Asimetrie Buze",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=14,
               pady=(12, 6))

        # ── Card stare ────────────────────────────────────────────────────────
        self._state_card = ctk.CTkFrame(
            scroll, fg_color="#E8F5E9",
            corner_radius=10,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        self._state_card.pack(
            fill="x", padx=14, pady=(0, 10))

        self._state_var = tk.StringVar(
            value="● IDLE")
        self._state_lbl = ctk.CTkLabel(
            self._state_card,
            textvariable=self._state_var,
            font=("Georgia", 14, "bold"),
            text_color="#2E7D32",
        )
        self._state_lbl.pack(
            anchor="w", padx=12, pady=(8, 2))

        self._state_desc_var = tk.StringVar(
            value="Monitorizare silențioasă activă.")
        ctk.CTkLabel(
            self._state_card,
            textvariable=self._state_desc_var,
            font=("Arial", 11),
            text_color=TEXT_MID,
            wraplength=280,
            justify="left",
        ).pack(anchor="w", padx=12,
               pady=(0, 8))

        # ── Metrici ───────────────────────────────────────────────────────────
        self._metrics = {}
        for key, label in [
            ("score",     "Scor asimetrie"),
            ("horiz",     "Deviație orizontală"),
            ("vert",      "Deviație verticală"),
            ("threshold", "Prag declanșare"),
        ]:
            row = ctk.CTkFrame(
                scroll, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            ctk.CTkLabel(
                row, text=label,
                font=("Arial", 11),
                text_color=TEXT_LIGHT,
                width=145, anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value="—")
            ctk.CTkLabel(
                row, textvariable=var,
                font=("Arial", 11, "bold"),
                text_color=TEXT_DARK,
            ).pack(side="left")
            self._metrics[key] = var

        self._metrics["threshold"].set(
            f"{SEVERE_THRESHOLD:.2f}  (65%)")

        # Bara asimetrie
        ctk.CTkLabel(
            scroll,
            text="Nivel asimetrie buze",
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=14,
               pady=(8, 2))

        self._asym_bar = ctk.CTkProgressBar(
            scroll, height=10, corner_radius=5,
            fg_color=GRAY_LIGHT,
            progress_color="#E57373",
        )
        self._asym_bar.set(0)
        self._asym_bar.pack(
            fill="x", padx=14, pady=(0, 10))

        # ── Card microfon ─────────────────────────────────────────────────────
        mic_card = ctk.CTkFrame(
            scroll, fg_color="#F0F4FF",
            corner_radius=10,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        mic_card.pack(
            fill="x", padx=14, pady=(0, 10))

        mic_hdr = ctk.CTkFrame(
            mic_card, fg_color="transparent")
        mic_hdr.pack(
            fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            mic_hdr, text="🎤 Microfon",
            font=("Arial", 11, "bold"),
            text_color=NAVY,
        ).pack(side="left")

        self._mic_status_var = tk.StringVar(
            value="⏸ Inactiv")
        self._mic_status_lbl = ctk.CTkLabel(
            mic_hdr,
            textvariable=self._mic_status_var,
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        )
        self._mic_status_lbl.pack(side="right")

        self._mic_bar = ctk.CTkProgressBar(
            mic_card, height=10, corner_radius=5,
            fg_color=GRAY_LIGHT,
            progress_color=BLUE,
        )
        self._mic_bar.set(0)
        self._mic_bar.pack(
            fill="x", padx=12, pady=(0, 6))

        # Waveform
        wave_frame = ctk.CTkFrame(
            mic_card, fg_color="transparent",
            height=48,
        )
        wave_frame.pack(
            fill="x", padx=12, pady=(0, 6))
        wave_frame.pack_propagate(False)

        self._wave_bars = []
        for _ in range(24):
            bar = ctk.CTkFrame(
                wave_frame,
                fg_color=GRAY_LIGHT,
                corner_radius=2,
                width=6, height=4,
            )
            bar.pack(
                side="left", padx=1,
                anchor="center")
            self._wave_bars.append(bar)

        ctk.CTkLabel(
            mic_card,
            text="Ultima transcriere:",
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=12,
               pady=(4, 2))

        self._transcript_var = tk.StringVar(
            value="—")
        ctk.CTkLabel(
            mic_card,
            textvariable=self._transcript_var,
            font=("Arial", 11, "bold"),
            text_color=TEXT_DARK,
            wraplength=260,
            justify="left",
        ).pack(anchor="w", padx=12,
               pady=(0, 8))

        # ── Butoane ───────────────────────────────────────────────────────────
        btn_card = ctk.CTkFrame(
            scroll, fg_color="transparent")
        btn_card.pack(
            fill="x", padx=14, pady=(0, 8))

        ctk.CTkButton(
            btn_card,
            text="▶ Test Manual BEFAST",
            height=38, corner_radius=8,
            fg_color=NAVY, hover_color=NAVY_DARK,
            font=("Arial", 12, "bold"),
            text_color=WHITE,
            command=self._trigger_manual,
        ).pack(fill="x", pady=(0, 6))

        self._btn_stop_test = ctk.CTkButton(
            btn_card,
            text="⏹ Oprește Testul",
            height=34, corner_radius=8,
            fg_color=ERROR_RED,
            hover_color="#C04040",
            font=("Arial", 12, "bold"),
            text_color=WHITE,
            state="disabled",
            command=self._stop_test,
        )
        self._btn_stop_test.pack(
            fill="x", pady=(0, 6))

        ctk.CTkButton(
            btn_card,
            text="↺ Reset",
            height=34, corner_radius=8,
            fg_color=GRAY_LIGHT,
            hover_color=GRAY_MID,
            font=("Arial", 12),
            text_color=TEXT_MID,
            command=self._reset,
        ).pack(fill="x")

        # Disclaimer
        disc = ctk.CTkFrame(
            scroll, fg_color=YELLOW_SOFT,
            corner_radius=8,
            border_width=1,
            border_color="#E8E080",
        )
        disc.pack(
            fill="x", padx=14, pady=(8, 14))

        ctk.CTkLabel(
            disc,
            text=(
                "⚠ Sistem de asistență — "
                "nu înlocuiește\n"
                "diagnosticul medical. "
                "Urgență → 112."
            ),
            font=("Arial", 10),
            text_color=TEXT_MID,
            justify="left",
        ).pack(padx=12, pady=8)

    # ── Panoul drept ──────────────────────────────────────────────────────────

    def _build_right_panel(self, parent):
        outer = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        outer.grid(row=0, column=1,
                   sticky="nsew", padx=(8, 0))

        self._right_scroll = ctk.CTkScrollableFrame(
            outer, fg_color="transparent",
            corner_radius=0,
        )
        self._right_scroll.pack(
            fill="both", expand=True)

        ctk.CTkLabel(
            self._right_scroll,
            text="Test B.E.F.A.S.T.",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=14,
               pady=(12, 6))

        # Feed video ascuns initial
        self._video_frame = ctk.CTkFrame(
            self._right_scroll,
            fg_color="black",
            corner_radius=8,
            height=200,
        )
        self._video_lbl = ctk.CTkLabel(
            self._video_frame,
            text="📷 Feed video analiza",
            fg_color="black",
            text_color=GRAY_MID,
            font=("Arial", 11),
        )
        self._video_lbl.pack(
            fill="both", expand=True)

        # Card intrebare
        self._q_card = ctk.CTkFrame(
            self._right_scroll,
            fg_color="#F0F4FF",
            corner_radius=10,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        self._q_card.pack(
            fill="x", padx=14, pady=(0, 8))

        self._q_letter_var = tk.StringVar(value="")
        ctk.CTkLabel(
            self._q_card,
            textvariable=self._q_letter_var,
            font=("Georgia", 17, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=14,
               pady=(10, 2))

        self._q_text_var = tk.StringVar(
            value=(
                "Testul va începe la detectarea "
                "asimetriei\nsau la apăsarea "
                "butonului 'Test Manual'."
            ))
        ctk.CTkLabel(
            self._q_card,
            textvariable=self._q_text_var,
            font=("Arial", 12),
            text_color=TEXT_MID,
            wraplength=300,
            justify="left",
        ).pack(anchor="w", padx=14,
               pady=(0, 10))

        # Indicator mod
        self._listen_var = tk.StringVar(value="")
        self._listen_lbl = ctk.CTkLabel(
            self._right_scroll,
            textvariable=self._listen_var,
            font=("Arial", 12, "bold"),
            text_color=BLUE,
        )
        self._listen_lbl.pack(
            anchor="w", padx=14, pady=(0, 6))

        # Rezultate
        ctk.CTkLabel(
            self._right_scroll,
            text="Rezultate test:",
            font=("Arial", 11, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=14,
               pady=(0, 4))

        self._results_frame = ctk.CTkFrame(
            self._right_scroll,
            fg_color="transparent",
            corner_radius=0,
        )
        self._results_frame.pack(
            fill="x", padx=14, pady=(0, 8))

        self._results_placeholder = ctk.CTkLabel(
            self._results_frame,
            text="Rezultatele vor apărea "
                 "aici după test.",
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
        )
        self._results_placeholder.pack(
            anchor="w", pady=4)

        # Mockup 112
        self._emergency_card = ctk.CTkFrame(
            self._right_scroll,
            fg_color=WHITE,
            corner_radius=10,
            border_width=2,
            border_color=GRAY_LIGHT,
        )
        self._emergency_card.pack(
            fill="x", padx=14, pady=(8, 14))

        self._emergency_title = ctk.CTkLabel(
            self._emergency_card,
            text="🚨  APEL DE URGENȚĂ — SIMULARE",
            font=("Georgia", 13, "bold"),
            text_color=GRAY_MID,
        )
        self._emergency_title.pack(
            padx=14, pady=(10, 4))

        self._emergency_info = ctk.CTkLabel(
            self._emergency_card,
            text="Inactive — nicio urgență.",
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
            wraplength=300,
            justify="center",
        )
        self._emergency_info.pack(
            padx=14, pady=(0, 8))

        self._call_btn = ctk.CTkButton(
            self._emergency_card,
            text="📞  SIMULARE APEL 112",
            height=42, corner_radius=8,
            fg_color=GRAY_LIGHT,
            hover_color=GRAY_MID,
            font=("Arial", 13, "bold"),
            text_color=GRAY_MID,
            state="disabled",
            command=self._mockup_112,
        )
        self._call_btn.pack(
            fill="x", padx=14, pady=(0, 14))

    # ── Video feed ────────────────────────────────────────────────────────────

    def show_video_feed(self, show: bool):
        if show:
            if not self._video_frame.winfo_ismapped():
                self._video_frame.pack(
                    fill="x", padx=14,
                    pady=(0, 8),
                    before=self._q_card)
        else:
            self._video_frame.pack_forget()
            self._video_lbl.configure(
                image=None,
                text="📷 Feed video analiza")
            self._video_photo = None

    def update_video_frame(self, frame):
        if not self._video_frame.winfo_ismapped():
            return
        try:
            from PIL import Image, ImageTk
            import numpy as np
            rgb  = frame[:, :, ::-1]
            img  = Image.fromarray(rgb)
            img  = img.resize((340, 200),
                               Image.LANCZOS)
            self._video_photo = \
                ImageTk.PhotoImage(img)
            self._video_lbl.configure(
                image=self._video_photo,
                text="")
        except Exception:
            pass

    # ── Feed frame la engine ──────────────────────────────────────────────────

    def feed_frame(self, frame):
        if (self._befast_engine
                and self._befast_engine._collecting):
            self._befast_engine.feed_frame(frame)

    # ── Indicator microfon ────────────────────────────────────────────────────

    def _start_mic_indicator(self):
        self._mic_active  = True
        self._mic_frame_n = 0
        self._mic_volume  = 0.0
        self._mic_status_var.set(
            "🔴 Înregistrează...")
        self._mic_status_lbl.configure(
            text_color=ERROR_RED)
        self._animate_waveform()

    def _stop_mic_indicator(self):
        self._mic_active = False
        self._mic_status_var.set("⏸ Inactiv")
        self._mic_status_lbl.configure(
            text_color=TEXT_LIGHT)
        try:
            self._mic_bar.set(0)
            for bar in self._wave_bars:
                bar.configure(
                    fg_color=GRAY_LIGHT, height=4)
        except Exception:
            pass

    def _on_volume(self, vol: float):
        self._mic_volume = vol
        try:
            self._mic_bar.set(vol)
        except Exception:
            pass

    def _animate_waveform(self):
        if not self._mic_active:
            return

        self._mic_frame_n += 1
        vol = self._mic_volume

        for i, bar in enumerate(self._wave_bars):
            try:
                phase  = math.sin(
                    (self._mic_frame_n * 0.3) +
                    (i * 0.5))
                noise  = random.uniform(0.0, 0.3)
                height = max(4, int(
                    4 + (phase + 1) * 0.5 *
                    vol * 34 + noise * vol * 8))
                height = min(height, 40)

                if vol > 0.7:
                    color = ERROR_RED
                elif vol > 0.4:
                    color = BLUE
                elif vol > 0.1:
                    color = GREEN
                else:
                    color = GRAY_MID

                bar.configure(
                    height=height,
                    fg_color=color)
            except Exception:
                pass

        self.after(60, self._animate_waveform)

    # ── State machine ─────────────────────────────────────────────────────────

    def _on_state_change(self, state: BEFASTState,
                         data: dict):
        self.after(
            0,
            lambda s=state, d=data:
            self._apply_state(s, d))

    def _apply_state(self, state: BEFASTState,
                     data: dict):

        if state == BEFASTState.IDLE:
            self._stop_mic_indicator()
            self.show_video_feed(False)
            self._state_card.configure(
                fg_color="#E8F5E9")
            self._state_var.set("● IDLE")
            self._state_lbl.configure(
                text_color="#2E7D32")
            self._state_desc_var.set(
                "Monitorizare silențioasă activă.")
            self._listen_var.set("")
            self._q_letter_var.set("")
            self._q_text_var.set(
                "Testul va începe la detectarea\n"
                "asimetriei sau la 'Test Manual'.")
            self._set_emergency_inactive()
            # Dezactiveaza butonul de oprire
            try:
                self._btn_stop_test.configure(
                    state="disabled",
                    fg_color=GRAY_LIGHT,
                    text_color=TEXT_MID)
            except Exception:
                pass

        elif state == BEFASTState.PHASE1:
            self._stop_mic_indicator()
            self.show_video_feed(False)
            self._state_card.configure(
                fg_color="#FFF8E1")
            self._state_var.set(
                "⚠ FAZA 1 — Asimetrie detectată")
            self._state_lbl.configure(
                text_color="#E65100")
            score = data.get("score", 0)
            self._state_desc_var.set(
                f"Scor: {score:.3f}\n"
                f"Alertă trimisă.\n"
                f"Se inițiază testul BEFAST...")
            # Activeaza butonul de oprire
            try:
                self._btn_stop_test.configure(
                    state="normal",
                    fg_color=ERROR_RED,
                    text_color=WHITE)
            except Exception:
                pass

        elif state == BEFASTState.BEFAST:
            self._state_card.configure(
                fg_color="#E3F2FD")
            self._state_var.set(
                "🎤 FAZA 2 — Test BEFAST")
            self._state_lbl.configure(
                text_color="#1565C0")

            q_display   = data.get(
                "question_display", "")
            q_letter    = data.get("letter", "")
            listening   = data.get(
                "listening", False)
            vision_mode = data.get(
                "vision_mode", False)
            current     = data.get(
                "current_question", 0)
            total       = data.get("total", 5)

            if q_letter:
                self._q_letter_var.set(
                    f"{q_letter}  "
                    f"({current}/{total})")
            if q_display:
                self._q_text_var.set(q_display)

            if listening:
                self._listen_var.set(
                    "🎤 Ascult răspunsul...")
                self._listen_lbl.configure(
                    text_color=BLUE)
                self._start_mic_indicator()
                self.show_video_feed(False)
            elif vision_mode:
                self._listen_var.set(
                    "👁 Analizez video...")
                self._listen_lbl.configure(
                    text_color=GREEN)
                self._stop_mic_indicator()
                self.show_video_feed(True)
            else:
                self._listen_var.set(
                    "🔊 Vorbesc...")
                self._listen_lbl.configure(
                    text_color=TEXT_MID)
                self._stop_mic_indicator()
                self.show_video_feed(False)

            if current > 0:
                self._state_desc_var.set(
                    f"Întrebarea {current} "
                    f"din {total}")

            # Activeaza butonul de oprire
            try:
                self._btn_stop_test.configure(
                    state="normal",
                    fg_color=ERROR_RED,
                    text_color=WHITE)
            except Exception:
                pass

        elif state == BEFASTState.EMERGENCY:
            self._stop_mic_indicator()
            self.show_video_feed(False)
            self._state_card.configure(
                fg_color="#FFEBEE")
            self._state_var.set(
                "🚨 URGENȚĂ — Test picat")
            self._state_lbl.configure(
                text_color="#B71C1C")
            self._listen_var.set("")
            failed = data.get(
                "failed_questions", [])
            self._state_desc_var.set(
                f"Picat la: {', '.join(failed)}")
            self._show_results(
                data.get("results", []))
            self._set_emergency_active(
                failed, data.get("timestamp", ""))
            # Dezactiveaza butonul de oprire
            try:
                self._btn_stop_test.configure(
                    state="disabled",
                    fg_color=GRAY_LIGHT,
                    text_color=TEXT_MID)
            except Exception:
                pass

        elif state == BEFASTState.RESOLVED:
            self._stop_mic_indicator()
            self.show_video_feed(False)
            self._state_card.configure(
                fg_color="#E8F5E9")
            self._state_var.set(
                "✓ RESOLVED — Test trecut")
            self._state_lbl.configure(
                text_color="#2E7D32")
            self._listen_var.set("")
            self._state_desc_var.set(
                "Toate întrebările au primit "
                "răspuns.")
            self._show_results(
                data.get("results", []))
            # Dezactiveaza butonul de oprire
            try:
                self._btn_stop_test.configure(
                    state="disabled",
                    fg_color=GRAY_LIGHT,
                    text_color=TEXT_MID)
            except Exception:
                pass

    def _show_results(self, results: list):
        for w in self._results_frame.winfo_children():
            w.destroy()
        if not results:
            return
        for r in results:
            bg   = "#E8F5E9" \
                if r["passed"] else "#FFEBEE"
            fg   = "#2E7D32" \
                if r["passed"] else "#B71C1C"
            icon = "✓" if r["passed"] else "✗"

            card = ctk.CTkFrame(
                self._results_frame,
                fg_color=bg, corner_radius=8,
                border_width=1,
                border_color=fg,
            )
            card.pack(fill="x", pady=3)

            ctk.CTkLabel(
                card,
                text=f"{icon}  "
                     f"{r['key'].upper()}",
                font=("Arial", 11, "bold"),
                text_color=fg,
            ).pack(anchor="w", padx=10,
                   pady=(6, 2))

            ctk.CTkLabel(
                card,
                text=r["reason"],
                font=("Arial", 10),
                text_color=TEXT_MID,
                wraplength=280,
                justify="left",
            ).pack(anchor="w", padx=10,
                   pady=(0, 6))

    # ── Mockup 112 ────────────────────────────────────────────────────────────

    def _set_emergency_inactive(self):
        self._emergency_card.configure(
            border_color=GRAY_LIGHT)
        self._emergency_title.configure(
            text_color=GRAY_MID)
        self._emergency_info.configure(
            text="Inactive — nicio urgență.",
            text_color=TEXT_LIGHT)
        self._call_btn.configure(
            fg_color=GRAY_LIGHT,
            hover_color=GRAY_MID,
            text_color=GRAY_MID,
            state="disabled")

    def _set_emergency_active(self,
                               failed: list,
                               ts: str):
        self._emergency_card.configure(
            border_color=ERROR_RED)
        self._emergency_title.configure(
            text_color=ERROR_RED)
        self._emergency_info.configure(
            text=(
                f"Urgență la {ts}\n"
                f"Picat: {', '.join(failed)}\n"
                "Apăsați pentru simulare."
            ),
            text_color=ERROR_RED)
        self._call_btn.configure(
            fg_color=ERROR_RED,
            hover_color="#C04040",
            text_color=WHITE,
            state="normal")

    def _mockup_112(self):
        popup = ctk.CTkToplevel(self)
        popup.title("SIMULARE APEL 112")
        popup.geometry("420x340")
        popup.resizable(False, False)
        popup.configure(fg_color="#1A0000")
        popup.grab_set()
        popup.lift()
        popup.focus_force()

        x = (popup.winfo_screenwidth()
             - 420) // 2
        y = (popup.winfo_screenheight()
             - 340) // 2
        popup.geometry(f"420x340+{x}+{y}")

        ctk.CTkLabel(
            popup, text="🚨",
            font=("Arial", 52),
        ).pack(pady=(20, 0))

        ctk.CTkLabel(
            popup,
            text="SIMULARE APEL DE URGENȚĂ",
            font=("Georgia", 16, "bold"),
            text_color="#FF4444",
        ).pack(pady=(4, 2))

        ctk.CTkLabel(
            popup, text="112",
            font=("Georgia", 48, "bold"),
            text_color=WHITE,
        ).pack(pady=(0, 4))

        timer_var = tk.StringVar(
            value="Se apelează... 00:00")
        ctk.CTkLabel(
            popup,
            textvariable=timer_var,
            font=("Courier New", 13),
            text_color="#FF8080",
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            popup,
            text=(
                "⚠ ACEASTA ESTE O SIMULARE\n"
                "Nu este un apel real."
            ),
            font=("Arial", 11),
            text_color=GRAY_MID,
            justify="center",
        ).pack(pady=(0, 8))

        ctk.CTkButton(
            popup,
            text="✕  Închide simularea",
            height=36, corner_radius=8,
            fg_color="#4A0000",
            hover_color="#6A0000",
            font=("Arial", 12),
            text_color=WHITE,
            command=popup.destroy,
        ).pack(pady=(0, 16))

        start = time.time()

        def _tick():
            if not popup.winfo_exists():
                return
            elapsed = int(time.time() - start)
            m, s    = divmod(elapsed, 60)
            timer_var.set(
                f"Se apelează... {m:02d}:{s:02d}")
            popup.after(1000, _tick)

        _tick()

    # ── Control manual ────────────────────────────────────────────────────────

    def _trigger_manual(self):
        if not self._befast_engine:
            self._status_var.set(
                "⟳ Motorul nu e gata încă...")
            return
        if (self._befast_engine.state
                != BEFASTState.IDLE):
            return

        from utils.stroke_detector import (
            LipSymmetryResult)
        mock = LipSymmetryResult(
            asymmetry_score = 0.42,
            horizontal_dev  = 0.38,
            vertical_dev    = 0.21,
            is_severe       = True,
        )
        self._befast_engine._last_trigger = 0
        self._befast_engine.process_frame(mock)

    def _stop_test(self):
        """Opreste testul BEFAST in orice moment."""
        print("[BEFAST UI] Test oprit manual.")
        self._stop_mic_indicator()
        self.show_video_feed(False)

        if self._befast_engine:
            self._befast_engine._force_stop = True
            self._befast_engine._collecting  = False
            self._befast_engine\
                ._current_vision_key = None

        # Dezactiveaza butonul imediat
        try:
            self._btn_stop_test.configure(
                state="disabled",
                fg_color=GRAY_LIGHT,
                text_color=TEXT_MID)
        except Exception:
            pass

        # Reseteaza UI la IDLE
        self._state_card.configure(
            fg_color="#E8F5E9")
        self._state_var.set("● IDLE")
        self._state_lbl.configure(
            text_color="#2E7D32")
        self._state_desc_var.set(
            "Test oprit manual.\n"
            "Monitorizare silențioasă activă.")
        self._listen_var.set("")
        self._q_letter_var.set("")
        self._q_text_var.set(
            "Testul va începe la detectarea\n"
            "asimetriei sau la 'Test Manual'.")

        try:
            self._transcript_var.set("—")
        except Exception:
            pass

        # Seteaza starea in engine
        if self._befast_engine:
            # Forteaza IDLE dupa o mica intarziere
            # (lasa thread-ul sa detecteze force_stop)
            threading.Thread(
                target=self._delayed_idle_reset,
                daemon=True,
            ).start()

    def _delayed_idle_reset(self):
        """Asteapta thread-ul BEFAST sa se opreasca."""
        time.sleep(1.5)
        if self._befast_engine:
            self._befast_engine._force_stop = False
            self._befast_engine._set_state(
                BEFASTState.IDLE, {})

    def _reset(self):
        self._stop_mic_indicator()
        self.show_video_feed(False)
        try:
            self._transcript_var.set("—")
        except Exception:
            pass
        if self._befast_engine:
            self._befast_engine.reset()

    # ── Update din VisionEngine ───────────────────────────────────────────────

    def update_lip_metrics(self, lip_result):
        if not lip_result:
            return
        self.after(
            0,
            lambda: self._update_metrics_ui(
                lip_result))
        if (self._befast_engine
                and self._befast_engine.state
                == BEFASTState.IDLE):
            self._befast_engine.process_frame(
                lip_result)

    def _update_metrics_ui(self, r):
        score = r.asymmetry_score
        self._metrics["score"].set(
            f"{score:.4f}"
            f"  {'⚠ SEVER' if r.is_severe else 'OK'}")
        self._metrics["horiz"].set(
            f"{r.horizontal_dev:.4f}")
        self._metrics["vert"].set(
            f"{r.vertical_dev:.4f}")

        self._asym_bar.set(
            min(score / SEVERE_THRESHOLD, 1.0))

        if score > SEVERE_THRESHOLD:
            self._asym_bar.configure(
                progress_color="#C62828")
        elif score > SEVERE_THRESHOLD * 0.7:
            self._asym_bar.configure(
                progress_color="#FF8F00")
        else:
            self._asym_bar.configure(
                progress_color="#E57373")