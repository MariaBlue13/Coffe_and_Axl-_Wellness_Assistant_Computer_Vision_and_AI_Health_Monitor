"""
Coffee & Axl - Vision Tab
Analiza video in timp real.
Conectat cu BEFASTTab pentru feed frame si lip metrics.
"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import threading
import time
from datetime import datetime

from utils.vision_engine import (
    VisionEngine, AnalysisResult, UrgencyLevel)
from utils.pushbullet_notifier import (
    send_notification, verify_api_key,
    build_alert_message
)
from utils.theme import *
from utils.ai_intervention import AIInterventionBridge


URGENCY_STYLE = {
    UrgencyLevel.NONE:     ("#E8F5E9", "#2E7D32",
                            "✓  Normal"),
    UrgencyLevel.LOW:      ("#E3F2FD", "#1565C0",
                            "ℹ  Stare emotionala"),
    UrgencyLevel.MEDIUM:   ("#FFF8E1", "#E65100",
                            "⚠  Atentie"),
    UrgencyLevel.HIGH:     ("#FFEBEE", "#B71C1C",
                            "⚠⚠  Risc ridicat"),
    UrgencyLevel.CRITICAL: ("#FF1744", "#FFFFFF",
                            "🚨  URGENTA CRITICA"),
}


class VisionTab(ctk.CTkFrame):

    def __init__(self, parent, user_id: int, engine):
        super().__init__(
            parent, fg_color=OFF_WHITE,
            corner_radius=0)
        self.user_id   = user_id
        self.db_engine = engine
        self._vision   = None
        self._running  = False
        self._photo    = None
        self._fps_counter = 0
        self._fps_time    = time.time()
        self._last_urgency_level = UrgencyLevel.NONE

        # Pushbullet
        self._pb_api_key = None
        self._user_name  = ""
        self._load_pb_key()

        # Conectare cu BEFASTTab
        self._befast_tab       = None
        self._befast_video_tab = None

        self.pack(fill="both", expand=True)
        self._build_ui()

        self._ai_bridge = AIInterventionBridge()
        self._ai_bridge.set_intervention_callback(
            self._on_ai_intervention)

    # ── Pushbullet ────────────────────────────────────────────────────────────

    def _load_pb_key(self):
        try:
            from database import PersoanaContact, get_session
            session = get_session(self.db_engine)
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
                    self._pb_api_key = \
                        contact.cheie_pushbullet
            finally:
                session.close()
        except Exception as e:
            print(f"[PB] Eroare: {e}")

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_body()

    def _build_header(self):
        header = ctk.CTkFrame(
            self, fg_color=NAVY,
            corner_radius=0, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = ctk.CTkFrame(
            header, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            left, text="📷",
            font=("Arial", 24),
            text_color=YELLOW,
        ).pack(side="left")
        ctk.CTkLabel(
            left,
            text="  Analiză Video & Detecție Emoții",
            font=("Georgia", 16, "bold"),
            text_color=WHITE,
        ).pack(side="left")

        self._cam_status_var = tk.StringVar(
            value="⏹ Camera oprită")
        ctk.CTkLabel(
            header,
            textvariable=self._cam_status_var,
            font=("Arial", 11),
            text_color=GRAY_MID,
        ).pack(side="right", padx=20)

    def _build_body(self):
        body = ctk.CTkFrame(
            self, fg_color="transparent")
        body.pack(
            fill="both", expand=True,
            padx=20, pady=16)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        self._build_camera_panel(body)
        self._build_info_panel(body)

    def _build_camera_panel(self, parent):
        left = ctk.CTkFrame(
            parent, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        left.grid(row=0, column=0,
                  sticky="nsew", padx=(0, 10))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(
            left, fg_color="transparent")
        ctrl.grid(row=0, column=0,
                  sticky="ew", padx=16, pady=12)

        self._btn_start = ctk.CTkButton(
            ctrl,
            text="▶  Pornește Camera",
            height=38, corner_radius=10,
            fg_color=GREEN, hover_color=GREEN_DARK,
            font=("Arial", 13, "bold"),
            text_color=WHITE,
            command=self._start_camera,
        )
        self._btn_start.pack(side="left", padx=(0, 8))

        self._btn_stop = ctk.CTkButton(
            ctrl,
            text="⏹  Oprește",
            height=38, corner_radius=10,
            fg_color=GRAY_LIGHT,
            hover_color=ERROR_RED,
            font=("Arial", 13),
            text_color=TEXT_MID,
            command=self._stop_camera,
            state="disabled",
        )
        self._btn_stop.pack(side="left")

        self._cuda_var = tk.StringVar(value="")
        ctk.CTkLabel(
            ctrl,
            textvariable=self._cuda_var,
            font=("Arial", 11),
            text_color=GREEN,
        ).pack(side="right", padx=8)

        self._video_label = ctk.CTkLabel(
            left,
            text=(
                "Camera oprită\n\n"
                "Apasă 'Pornește Camera' pentru analiză.\n\n"
                "Detectează:\n"
                "  · Expresii faciale și emoții\n"
                "  · Asimetrie facială (indicator AVC)\n"
                "  · Înclinare cap (indicator leșin)\n"
                "  · Mișcări haotice (indicator epilepsie)"
            ),
            font=("Arial", 13),
            text_color=TEXT_LIGHT,
            fg_color="#F0F4FF",
            corner_radius=8,
            width=640, height=420,
        )
        self._video_label.grid(
            row=1, column=0,
            sticky="nsew", padx=16, pady=(0, 16))

        self._check_cuda_status()

    def _build_info_panel(self, parent):
        right = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")

        # Card urgenta
        self._urgency_card = ctk.CTkFrame(
            right, fg_color="#E8F5E9",
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        self._urgency_card.pack(
            fill="x", pady=(0, 12))

        ctk.CTkLabel(
            self._urgency_card,
            text="Stare detectată",
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=16, pady=(12, 2))

        self._urgency_var = tk.StringVar(
            value="✓  Normal")
        self._urgency_lbl = ctk.CTkLabel(
            self._urgency_card,
            textvariable=self._urgency_var,
            font=("Georgia", 16, "bold"),
            text_color="#2E7D32",
        )
        self._urgency_lbl.pack(
            anchor="w", padx=16, pady=(0, 4))

        self._reason_var = tk.StringVar(value="")
        ctk.CTkLabel(
            self._urgency_card,
            textvariable=self._reason_var,
            font=("Arial", 11),
            text_color=TEXT_MID,
            wraplength=380,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # Metrici
        metrics_card = ctk.CTkFrame(
            right, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        metrics_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            metrics_card, text="Metrici live",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self._metrics = {}
        for key, label in [
            ("emotion",    "Emoție"),
            ("emotion_cf", "Încredere"),
            ("asymmetry",  "Asimetrie facială"),
            ("head_tilt",  "Înclinare cap"),
            ("motion",     "Mișcare"),
            ("lip_asym",   "Asimetrie buze (AVC)"),
            ("fps",        "FPS analiză"),
        ]:
            row = ctk.CTkFrame(
                metrics_card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(
                row, text=label,
                font=("Arial", 11),
                text_color=TEXT_LIGHT,
                width=160, anchor="w",
            ).pack(side="left")
            var = tk.StringVar(value="—")
            ctk.CTkLabel(
                row, textvariable=var,
                font=("Arial", 11, "bold"),
                text_color=TEXT_DARK,
            ).pack(side="left")
            self._metrics[key] = var

        ctk.CTkFrame(
            metrics_card, height=12,
            fg_color="transparent").pack()

        # Bare progres
        prog_card = ctk.CTkFrame(
            right, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        prog_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            prog_card, text="Indicatori vizuali",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=16, pady=(12, 8))

        for label, attr, color in [
            ("Asimetrie facială  (AVC)",
             "asym_bar",   "#E57373"),
            ("Înclinare cap  (Leșin)",
             "tilt_bar",   "#FFB74D"),
            ("Mișcare haotică  (Epilepsie)",
             "motion_bar", "#9575CD"),
            ("Asimetrie buze  (AVC-BEFAST)",
             "lip_bar",    "#EF5350"),
        ]:
            ctk.CTkLabel(
                prog_card, text=label,
                font=("Arial", 10),
                text_color=TEXT_LIGHT,
            ).pack(anchor="w", padx=16, pady=(4, 0))

            bar = ctk.CTkProgressBar(
                prog_card, height=10, corner_radius=5,
                fg_color=GRAY_LIGHT,
                progress_color=color,
            )
            bar.set(0)
            bar.pack(fill="x", padx=16, pady=(2, 6))
            setattr(self, f"_{attr}", bar)

        ctk.CTkLabel(
            prog_card,
            text="Alertă la depășirea pragului de 65%",
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=16, pady=(4, 12))

        # Log urgente
        log_card = ctk.CTkFrame(
            right, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        log_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            log_card, text="Jurnal alerte",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self._log_frame = ctk.CTkFrame(
            log_card, fg_color="transparent")
        self._log_frame.pack(
            fill="x", padx=16, pady=(0, 12))

        self._log_empty = ctk.CTkLabel(
            self._log_frame,
            text="Nicio alertă înregistrată.",
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
        )
        self._log_empty.pack()

        # Pushbullet
        pb_card = ctk.CTkFrame(
            right, fg_color=WHITE,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=GRAY_LIGHT,
        )
        pb_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            pb_card, text="🔔 Pushbullet",
            font=("Arial", 12, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=16, pady=(12, 4))

        self._pb_status_var = tk.StringVar(
            value="✓ Cheie configurată"
            if self._pb_api_key
            else "✗ Fără cheie")
        self._pb_status_lbl = ctk.CTkLabel(
            pb_card,
            textvariable=self._pb_status_var,
            font=("Arial", 11),
            text_color=GREEN
            if self._pb_api_key else ERROR_RED,
        )
        self._pb_status_lbl.pack(
            anchor="w", padx=16)

        pb_row = ctk.CTkFrame(
            pb_card, fg_color="transparent")
        pb_row.pack(
            fill="x", padx=16, pady=(8, 12))

        self._pb_entry = ctk.CTkEntry(
            pb_row,
            placeholder_text="Cheie API Pushbullet",
            height=34, corner_radius=8,
            font=("Arial", 11), show="•",
        )
        self._pb_entry.pack(
            side="left", fill="x",
            expand=True, padx=(0, 8))

        if self._pb_api_key:
            self._pb_entry.insert(0, self._pb_api_key)

        ctk.CTkButton(
            pb_row, text="Test",
            width=60, height=34, corner_radius=8,
            fg_color=BLUE, hover_color=BLUE_HOVER,
            font=("Arial", 11, "bold"),
            text_color=WHITE,
            command=self._test_pb_key,
        ).pack(side="right")

        # Disclaimer
        disc = ctk.CTkFrame(
            right, fg_color=YELLOW_SOFT,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color="#E8E080",
        )
        disc.pack(fill="x")

        ctk.CTkLabel(
            disc,
            text=(
                "⚠  Disclaimer medical\n\n"
                "Indicatori vizuali de risc — "
                "nu diagnostic medical. "
                "Urgență reală → 112."
            ),
            font=("Arial", 10),
            text_color=TEXT_MID,
            wraplength=380, justify="left",
        ).pack(padx=14, pady=12)

    # ── Control camera ────────────────────────────────────────────────────────

    def _safe_after(self, ms, fn):
        """Apeleaza fn pe main thread in mod sigur."""
        try:
            self.after(ms, fn)
        except RuntimeError:
            try:
                self.tk.call('after', ms, self.tk.register(fn))
            except Exception:
                pass

    def _check_cuda_status(self):
        def _check():
            try:
                import torch
                if torch.cuda.is_available():
                    name = torch.cuda.get_device_name(0)
                    self._safe_after(0, lambda: self._cuda_var
                               .set(f"CUDA: {name}"))
                else:
                    self._safe_after(0, lambda:
                               self._cuda_var.set(
                                   "CPU mode"))
            except ImportError:
                self._safe_after(0, lambda:
                           self._cuda_var.set("CPU mode"))
        threading.Thread(
            target=_check, daemon=True).start()

    def _start_camera(self):
        if self._running:
            return
        self._running     = True
        self._fps_counter = 0
        self._fps_time    = time.time()

        self._btn_start.configure(
            state="disabled",
            fg_color=GRAY_LIGHT,
            text_color=TEXT_MID)
        self._btn_stop.configure(
            state="normal",
            fg_color=ERROR_RED,
            text_color=WHITE)
        self._cam_status_var.set(
            "🔴 Camera activă — analiză în desfășurare")

        self._vision = VisionEngine(
            on_result  = self._on_result,
            on_urgency = self._on_urgency,
            on_frame   = self._on_frame,
            on_error   = self._on_error,
        )
        self._vision.start(0)
        # Seteaza callbackurile emotionale
        self._vision.set_emotion_callbacks(
            on_drowsy=self._ai_bridge.trigger_drowsy,
            on_sad=self._ai_bridge.trigger_sad,
            on_angry=self._ai_bridge.trigger_angry,
            on_fearful=self._ai_bridge.trigger_fearful,
            on_disgusted=self._ai_bridge.trigger_disgusted,
            on_both=self._ai_bridge.trigger_both,
        )


    def _stop_camera(self):
        self._running = False
        if self._vision:
            self._vision.stop()
            self._vision = None

        def _do_stop_ui():
            # Curata referintele in ordine:
            # 1. sterge din widget intern (Tk label)
            try:
                self._video_label._label.configure(image="")
            except Exception:
                pass
            # 2. anuleaza referintele Python
            self._photo = None
            if hasattr(self._video_label, '_photo_ref'):
                self._video_label._photo_ref = None
            # 3. acum e sigur sa setam text
            try:
                self._video_label.configure(
                    image=None,
                    text="Camera oprita.")
            except Exception:
                pass
            self._btn_start.configure(
                state="normal",
                fg_color=GREEN, text_color=WHITE,
                text="Porneste Camera")
            self._btn_stop.configure(
                state="disabled",
                fg_color=GRAY_LIGHT,
                text_color=TEXT_MID)
            self._cam_status_var.set("Camera oprita")
            self._reset_metrics()

        try:
            self.after(0, _do_stop_ui)
        except RuntimeError:
            _do_stop_ui()

    # ── Callbacks VisionEngine ────────────────────────────────────────────────

    def _on_frame(self, frame: np.ndarray):
        self._safe_after(0,
                   lambda f=frame: self._display_frame(f))

        if (self._befast_tab
                and hasattr(self._befast_tab,
                            "feed_frame")):
            self._befast_tab.feed_frame(frame)

        if self._befast_video_tab:
            self._safe_after(
                0,
                lambda f=frame:
                self._befast_video_tab
                .update_video_frame(f))

    def _display_frame(self, frame: np.ndarray):
        if not self._running:
            return
        try:
            rgb = frame[:, :, ::-1]
            img = Image.fromarray(rgb)

            lw = self._video_label.winfo_width()
            lh = self._video_label.winfo_height()
            if lw < 10 or lh < 10:
                lw, lh = 640, 420

            img = img.resize((lw, lh), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            # Referinta dubla: pe self SI pe widget
            # Tkinter face GC daca referinta e doar locala
            self._photo = photo
            self._video_label._photo_ref = photo

            if self._running:
                self._video_label.configure(
                    image=photo,
                    text="",
                    fg_color="black")
        except Exception as e:
            if "doesn't exist" not in str(e):
                print(f"[VISION UI] {e}")

    def _on_result(self, result: AnalysisResult):
        self._safe_after(0,
                   lambda r=result:
                   self._update_metrics(r))

        # Trimite lip_symmetry la BEFAST
        if (self._befast_tab
                and hasattr(result, "lip_symmetry")
                and result.lip_symmetry is not None):
            self._safe_after(
                0,
                lambda r=result:
                self._befast_tab.update_lip_metrics(
                    r.lip_symmetry))

    def _update_metrics(self, r: AnalysisResult):
        if not r.face_detected:
            self._metrics["emotion"].set(
                "Față nedetectată")
            for k in ["emotion_cf", "asymmetry",
                      "head_tilt", "motion",
                      "lip_asym"]:
                self._metrics[k].set("—")
            return

        self._metrics["emotion"].set(r.emotion)
        self._metrics["emotion_cf"].set(
            f"{r.emotion_conf:.0%}")
        self._metrics["asymmetry"].set(
            f"{r.asymmetry_score:.4f}"
            f"  {'⚠' if r.asymmetry_score > 0.65 else ''}")
        self._metrics["head_tilt"].set(
            f"{r.head_tilt:.1f}°"
            f"  {'⚠' if r.head_tilt > 58.5 else ''}")
        self._metrics["motion"].set(
            f"{r.motion_score:.4f}"
            f"  {'⚠' if r.motion_score > 0.65 else ''}")

        if (hasattr(r, "lip_symmetry")
                and r.lip_symmetry):
            ls = r.lip_symmetry
            self._metrics["lip_asym"].set(
                f"{ls.asymmetry_score:.4f}"
                f"  {'⚠ SEVER' if ls.is_severe else ''}")
            self._lip_bar.set(
                min(ls.asymmetry_score / 0.35, 1.0))
        else:
            self._metrics["lip_asym"].set("—")

        self._fps_counter += 1
        if time.time() - self._fps_time >= 1.0:
            self._metrics["fps"].set(
                f"{self._fps_counter} fps")
            self._fps_counter = 0
            self._fps_time    = time.time()

        self._asym_bar.set(
            min(r.asymmetry_score / 0.65, 1.0))
        self._tilt_bar.set(
            min(r.head_tilt / 58.5, 1.0))
        self._motion_bar.set(
            min(r.motion_score / 0.65, 1.0))

        bg, fg, label = URGENCY_STYLE.get(
            r.urgency,
            ("#E8F5E9", "#2E7D32", "✓  Normal"))
        self._urgency_card.configure(fg_color=bg)
        self._urgency_var.set(label)
        self._urgency_lbl.configure(text_color=fg)
        self._reason_var.set(r.urgency_reason)

    def _on_urgency(self, result: AnalysisResult):
        self.after(0,
                   lambda r=result:
                   self._handle_urgency(r))

    def _handle_urgency(self, r: AnalysisResult):
        self._last_urgency_level = r.urgency

        ts        = datetime.now().strftime("%H:%M:%S")
        bg, fg, label = URGENCY_STYLE.get(
            r.urgency,
            ("#E8F5E9", "#2E7D32", "Normal"))

        self._log_empty.pack_forget()

        entry = ctk.CTkFrame(
            self._log_frame,
            fg_color=bg, corner_radius=8,
            border_width=1, border_color=fg,
        )
        entry.pack(fill="x", pady=3)

        ctk.CTkLabel(
            entry,
            text=f"{ts}  ·  {label}",
            font=("Arial", 11, "bold"),
            text_color=fg,
        ).pack(anchor="w", padx=10, pady=(6, 2))

        if r.urgency_reason:
            ctk.CTkLabel(
                entry,
                text=r.urgency_reason,
                font=("Arial", 10),
                text_color=TEXT_MID,
                wraplength=360, justify="left",
            ).pack(anchor="w", padx=10, pady=(0, 4))

        pb_status_var = tk.StringVar(value="")
        pb_lbl = ctk.CTkLabel(
            entry,
            textvariable=pb_status_var,
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        )

        if r.urgency.value in (
                "medium", "high", "critical"):
            pb_lbl.pack(
                anchor="w", padx=10, pady=(0, 6))
            pb_status_var.set(
                "⟳ se trimite notificare...")
            self._send_pb_alert(r, pb_status_var)

        threading.Thread(
            target=self._play_alert,
            daemon=True).start()

    def _send_pb_alert(self, r: AnalysisResult,
                       status_var: tk.StringVar):
        manual = self._pb_entry.get().strip()
        key    = manual or self._pb_api_key

        if not key:
            status_var.set("⚠ Fără cheie Pushbullet")
            return

        title, body = build_alert_message(
            urgency_level  = r.urgency.value,
            urgency_reason = r.urgency_reason,
            user_name      = self._user_name
                             or f"User #{self.user_id}",
            metrics        = {
                "asymmetry": r.asymmetry_score,
                "head_tilt": r.head_tilt,
                "motion":    r.motion_score,
                "emotion":   r.emotion,
            },
        )

        send_notification(
            api_key       = key,
            title         = title,
            body          = body,
            urgency_level = r.urgency.value,
            on_success    = lambda: self.after(
                0, lambda: status_var.set(
                    "✓ Notificare trimisă")),
            on_error      = lambda m: self.after(
                0, lambda: status_var.set(f"✗ {m}")),
        )

    def _on_error(self, msg: str):
        self.after(0, lambda: self._show_error(msg))

    def _show_error(self, msg: str):
        self._stop_camera()
        self._cam_status_var.set(
            f"✗ Eroare: {msg[:60]}")
        self._video_label.configure(
            text=f"Eroare:\n{msg}",
            text_color=ERROR_RED)

    def _test_pb_key(self):
        key = self._pb_entry.get().strip()
        if not key:
            self._pb_status_var.set(
                "Introdu o cheie API.")
            return

        self._pb_status_var.set("⟳ Se verifică...")
        self._pb_status_lbl.configure(
            text_color=TEXT_LIGHT)

        def on_ok(name):
            self._pb_api_key = key
            self.after(0, lambda: (
                self._pb_status_var.set(
                    f"✓ Conectat: {name}"),
                self._pb_status_lbl.configure(
                    text_color=GREEN),
            ))

        def on_err(msg):
            self.after(0, lambda: (
                self._pb_status_var.set(f"✗ {msg}"),
                self._pb_status_lbl.configure(
                    text_color=ERROR_RED),
            ))

        verify_api_key(key,
                       on_success=on_ok,
                       on_error=on_err)

    def _play_alert(self):
        try:
            import winsound
            if self._last_urgency_level == \
                    UrgencyLevel.CRITICAL:
                for _ in range(3):
                    winsound.Beep(1000, 300)
                    time.sleep(0.1)
            elif self._last_urgency_level == \
                    UrgencyLevel.HIGH:
                winsound.Beep(800, 500)
            else:
                winsound.Beep(600, 300)
        except Exception:
            pass

    def _reset_metrics(self):
        for var in self._metrics.values():
            var.set("—")
        self._asym_bar.set(0)
        self._tilt_bar.set(0)
        self._motion_bar.set(0)
        self._lip_bar.set(0)
        self._urgency_var.set("✓  Normal")
        self._reason_var.set("")
        self._urgency_card.configure(
            fg_color="#E8F5E9")
        self._urgency_lbl.configure(
            text_color="#2E7D32")

    def connect_chatbot(self, chatbot_tab):
        """Conecteaza VisionTab la ChatbotTab prin AI Bridge."""
        self._ai_bridge.set_chatbot_tab(chatbot_tab)

        if self._vision:
            self._vision.set_emotion_callbacks(
                on_drowsy=self._ai_bridge.trigger_drowsy,
                on_sad=self._ai_bridge.trigger_sad,
                on_angry=self._ai_bridge.trigger_angry,
                on_fearful=self._ai_bridge.trigger_fearful,
                on_disgusted=self._ai_bridge.trigger_disgusted,
                on_both=self._ai_bridge.trigger_both,
            )
        print("[VISION TAB] AI Bridge conectat.")

    def _on_ai_intervention(self, itype):
        """Notifica UI la interventie."""
        from utils.ai_intervention import InterventionType
        labels = {
            InterventionType.DROWSY: "😴 Oboseală detectată",
            InterventionType.SAD: "💙 Tristețe detectată",
            InterventionType.BOTH: "🌙 Oboseală + tristețe",
        }
        msg = labels.get(itype, "Interventie AI")
        self.after(0, lambda: self._cam_status_var.set(
            f"🤖 {msg} — Axl intervine..."))