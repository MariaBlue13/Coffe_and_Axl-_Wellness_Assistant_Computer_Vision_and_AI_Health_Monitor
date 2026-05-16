"""
Coffee & Axl - Breathing Popup
Sesiune de respiratie interactiva cu cerc animat
si animalut sincronizat.
"""

import tkinter as tk
import math
import threading
from utils.wellness_engine import (
    BREATHING_META, BREATHING_SESSIONS)
from utils.wellness_session import WellnessSession
from utils.wellness_engine import WellnessType


class BreathingPopup(tk.Toplevel):

    def __init__(self, root,
                 breathing_type: str = "calmare",
                 pet_type: str = "cat"):
        super().__init__(root)

        self._btype    = breathing_type
        self._pet_type = pet_type
        self._session  = None
        self._frame_n  = 0
        self._anim_state   = "idle"
        self._breath_phase = "neutral"
        self._breath_pct   = 0.5
        self._step_idx     = 0
        self._step_total   = 1

        meta = BREATHING_META.get(
            breathing_type,
            BREATHING_META["constienta"])

        self.title(f"Axl — {meta['nume']}")
        self.geometry("380x500")
        self.resizable(False, False)
        self.configure(bg=meta["culoare"])
        self.attributes("-topmost", True)
        self.protocol(
            "WM_DELETE_WINDOW", self._on_close)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 380) // 2
        y  = (sh - 500) // 2
        self.geometry(f"380x500+{x}+{y}")
        self.lift()

        self._build_ui(meta)
        self._start_session()
        self._animate()

    def _build_ui(self, meta: dict):
        # Header
        header = tk.Frame(
            self, bg=meta["btn_color"],
            height=52)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"  {meta['icon']}  "
                 f"{meta['nume']}",
            font=("Georgia", 12, "bold"),
            bg=meta["btn_color"],
            fg="white", anchor="w",
        ).pack(side="left", padx=14, pady=12)

        tk.Button(
            header, text="✕",
            font=("Arial", 10, "bold"),
            bg=meta["btn_color"], fg="white",
            relief="flat", cursor="hand2",
            bd=0, command=self._on_close,
        ).pack(side="right", padx=14)

        # Cerc respiratie principal
        self._circle_canvas = tk.Canvas(
            self, width=200, height=200,
            bg=meta["culoare"],
            highlightthickness=0,
        )
        self._circle_canvas.pack(pady=(16, 8))

        # Text principal
        self._step_text_var = tk.StringVar(
            value="Pregătire...")
        tk.Label(
            self,
            textvariable=self._step_text_var,
            font=("Georgia", 13, "bold"),
            bg=meta["culoare"],
            fg="#1A1A1A",
            wraplength=320,
            justify="center",
        ).pack(pady=(0, 4))

        # Countdown
        self._tick_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self._tick_var,
            font=("Courier New", 22, "bold"),
            bg=meta["culoare"],
            fg=meta["btn_color"],
        ).pack(pady=(0, 8))

        # Progres
        prog_frame = tk.Frame(
            self, bg=meta["culoare"])
        prog_frame.pack(
            fill="x", padx=24, pady=(0, 8))

        self._prog_canvas = tk.Canvas(
            prog_frame, height=6,
            bg="#E0E0E0",
            highlightthickness=0,
        )
        self._prog_canvas.pack(fill="x")
        self._prog_color = meta["btn_color"]

        self._prog_lbl = tk.Label(
            prog_frame,
            text="",
            font=("Arial", 9),
            bg=meta["culoare"],
            fg="#888",
        )
        self._prog_lbl.pack(anchor="e")

        # Butoane
        btn_frame = tk.Frame(
            self, bg=meta["culoare"])
        btn_frame.pack(
            fill="x", padx=20,
            pady=(0, 16), side="bottom")

        tk.Button(
            btn_frame,
            text="⏹ Oprește",
            font=("Arial", 10),
            bg="#E0E0E0", fg="#5D4037",
            relief="flat", cursor="hand2",
            pady=7, bd=0,
            command=self._on_close,
        ).pack(fill="x")

    def _start_session(self):
        steps = BREATHING_SESSIONS.get(
            self._btype, [])
        self._step_total = len(steps)

        # Folosim WellnessSession cu pasi custom
        self._session = _BreathingSessionRunner(
            steps    = steps,
            on_step  = self._on_step,
            on_done  = self._on_done,
            on_tick  = self._on_tick,
        )
        self._session.start()

    def _on_step(self, step: dict,
                 idx: int, total: int):
        self.after(
            0,
            lambda s=step, i=idx, t=total:
            self._apply_step(s, i, t))

    def _apply_step(self, step: dict,
                    idx: int, total: int):
        self._step_idx = idx
        self._step_text_var.set(step["text"])
        self._tick_var.set("")

        tip  = step.get("tip", "mesaj")
        faza = step.get("faza", "neutral")
        self._breath_phase = faza

        # Stare animatie
        if tip in ("respiratie",):
            self._anim_state = "breath"
        elif tip == "intro":
            self._anim_state = "happy"
        elif tip == "mesaj":
            self._anim_state = "happy"
        else:
            self._anim_state = "idle"

        # Progres
        pct = idx / max(total - 1, 1)
        self._draw_progress(pct)
        self._prog_lbl.configure(
            text=f"Pas {idx + 1} / {total}")

    def _on_tick(self, sec: int, total: int):
        self.after(
            0,
            lambda s=sec, t=total:
            self._apply_tick(s, t))

    def _apply_tick(self, sec: int, total: int):
        self._tick_var.set(f"{sec}")

        # Progres cerc respiratie
        faza = self._breath_phase
        if faza == "inspir":
            self._breath_pct = \
                1.0 - (sec / total)
        elif faza in ("expir", "expir_lung",
                      "expir_rapid"):
            self._breath_pct = sec / total
        elif faza == "retine":
            self._breath_pct = 1.0
        else:
            self._breath_pct = 0.5

    def _on_done(self):
        self.after(0, self._show_done)

    def _show_done(self):
        self._step_text_var.set(
            "Sesiune completă! 🌟\n"
            "Excelent!")
        self._tick_var.set("")
        self._anim_state = "happy"
        self._draw_progress(1.0)
        self.after(3500, self.destroy)

    def _draw_progress(self, pct: float):
        self._prog_canvas.delete("all")
        w = self._prog_canvas.winfo_width()
        if w < 2:
            w = 330
        self._prog_canvas.create_rectangle(
            0, 0, w, 6,
            fill="#E0E0E0", outline="")
        self._prog_canvas.create_rectangle(
            0, 0, int(w * pct), 6,
            fill=self._prog_color, outline="")

    def _on_close(self):
        if self._session:
            self._session.stop()
        try:
            self.destroy()
        except Exception:
            pass

    # ── Animatie ──────────────────────────────────────────────────────────────

    def _animate(self):
        if not self.winfo_exists():
            return
        self._frame_n += 1
        self._draw_circle()
        self.after(50, self._animate)

    def _draw_circle(self):
        self._circle_canvas.delete("all")

        f    = self._frame_n
        faza = self._breath_phase
        pct  = self._breath_pct

        # Culori per faza
        colors = {
            "inspir":      ("#4CAF50", "#81C784"),
            "expir":       ("#2196F3", "#64B5F6"),
            "expir_lung":  ("#1565C0", "#42A5F5"),
            "expir_rapid": ("#FF9800", "#FFB74D"),
            "retine":      ("#FF9800", "#FFB74D"),
            "neutral":     ("#9C27B0", "#CE93D8"),
        }
        color_main, color_light = colors.get(
            faza, colors["neutral"])

        cx, cy = 100, 100
        r_max  = 80
        r_min  = 30

        # Cerc de baza (gri)
        self._circle_canvas.create_oval(
            cx - r_max, cy - r_max,
            cx + r_max, cy + r_max,
            fill="#E0E0E0", outline="")

        # Cerc animat per faza
        r = int(r_min + pct * (r_max - r_min))
        self._circle_canvas.create_oval(
            cx - r, cy - r,
            cx + r, cy + r,
            fill=color_main, outline="")

        # Inel de puls
        pulse = math.sin(f * 0.3) * 4
        r_pulse = r + int(pulse)
        self._circle_canvas.create_oval(
            cx - r_pulse, cy - r_pulse,
            cx + r_pulse, cy + r_pulse,
            fill="", outline=color_light,
            width=2)

        # Text in cerc
        faza_labels = {
            "inspir":      "Inspiră",
            "expir":       "Expiră",
            "expir_lung":  "Expiră lent",
            "expir_rapid": "Expiră rapid",
            "retine":      "Ține",
            "neutral":     "",
        }
        lbl = faza_labels.get(faza, "")
        if lbl:
            self._circle_canvas.create_text(
                cx, cy,
                text=lbl,
                font=("Arial", 12, "bold"),
                fill="white",
            )


# ─── Session Runner intern ────────────────────────────────────────────────────

class _BreathingSessionRunner:
    """Runner dedicat pentru sesiunile de respiratie."""

    def __init__(self, steps: list,
                 on_step:  callable = None,
                 on_done:  callable = None,
                 on_tick:  callable = None):
        self._steps      = steps
        self._on_step    = on_step
        self._on_done    = on_done
        self._on_tick    = on_tick
        self._force_stop = False

    def start(self):
        self._force_stop = False
        threading.Thread(
            target=self._run,
            daemon=True,
        ).start()

    def stop(self):
        self._force_stop = True

    def _run(self):
        import time
        steps = self._steps

        for i, step in enumerate(steps):
            if self._force_stop:
                break

            if self._on_step:
                self._on_step(
                    step, i, len(steps))

            # TTS
            self._say(step["text"])
            if self._force_stop:
                break

            durata = step.get("durata", 3)
            for sec in range(durata, 0, -1):
                if self._force_stop:
                    break
                if self._on_tick:
                    self._on_tick(sec, durata)
                time.sleep(1)

        if not self._force_stop and self._on_done:
            self._on_done()

    def _say(self, text: str):
        if self._force_stop:
            return
        try:
            from utils.voice_assistant import (
                SpeechEngine)
            tts  = SpeechEngine()
            import threading
            done = threading.Event()
            tts.speak(text,
                      on_done=lambda: done.set())
            for _ in range(40):
                if done.is_set() or \
                        self._force_stop:
                    break
                import time
                time.sleep(0.5)
        except Exception:
            pass