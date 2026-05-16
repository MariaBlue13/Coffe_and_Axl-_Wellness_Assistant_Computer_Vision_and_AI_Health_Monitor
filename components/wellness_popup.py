"""
Coffee & Axl - Wellness Session Popup
Popup always-on-top cu sesiune ghidata pas cu pas.
Animalut animat sincronizat cu exercitiul.
"""

import tkinter as tk
import math
import time
import threading
from utils.wellness_engine import (
    WellnessType, WELLNESS_META, SESSIONS)
from utils.wellness_session import WellnessSession


class WellnessPopup(tk.Toplevel):
    """
    Popup always-on-top cu sesiune wellness ghidata.
    Afiseaza pasul curent, countdown si animatie.
    """

    def __init__(self, root,
                 wtype: WellnessType,
                 pet_type: str = "cat",
                 engine    = None,
                 user_id: int = None):
        super().__init__(root)

        self._wtype    = wtype
        self._pet_type = pet_type
        self._engine   = engine
        self._user_id  = user_id
        self._session  = None
        self._frame_n  = 0
        self._anim_state = "idle"
        self._breath_phase = "neutral"

        meta = WELLNESS_META[wtype]

        # Fereastra
        self.title("Axl Wellness")
        self.geometry("400x520")
        self.resizable(False, False)
        self.configure(bg="#FAFAFA")
        self.attributes("-topmost", True)
        self.protocol(
            "WM_DELETE_WINDOW", self._on_close)

        # Centreaza
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 400) // 2
        y  = (sh - 520) // 2
        self.geometry(f"400x520+{x}+{y}")

        self._build_ui(meta)
        self._start_session()
        self._animate()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self, meta: dict):
        # Header
        header = tk.Frame(
            self, bg=meta["btn_color"],
            height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"  {meta['icon']}  "
                 f"{meta['titlu']}",
            font=("Georgia", 13, "bold"),
            bg=meta["btn_color"],
            fg="white", anchor="w",
        ).pack(side="left", padx=16, pady=14)

        self._close_btn = tk.Button(
            header, text="✕",
            font=("Arial", 11, "bold"),
            bg=meta["btn_color"], fg="white",
            relief="flat", cursor="hand2",
            bd=0, command=self._on_close,
        )
        self._close_btn.pack(
            side="right", padx=16)

        # Canvas animatie animalut
        self._canvas = tk.Canvas(
            self, width=400, height=140,
            bg="#F0F4FF",
            highlightthickness=0,
        )
        self._canvas.pack(fill="x")

        # Card pas curent
        self._step_card = tk.Frame(
            self, bg="white",
            relief="flat")
        self._step_card.pack(
            fill="x", padx=20, pady=(12, 8))

        # Icon pas
        self._step_icon_var = tk.StringVar(
            value="")
        tk.Label(
            self._step_card,
            textvariable=self._step_icon_var,
            font=("Arial", 28),
            bg="white",
        ).pack(pady=(12, 4))

        # Text pas
        self._step_text_var = tk.StringVar(
            value="Se pregătește sesiunea...")
        tk.Label(
            self._step_card,
            textvariable=self._step_text_var,
            font=("Arial", 12),
            bg="white", fg="#5D4037",
            wraplength=340,
            justify="center",
        ).pack(padx=20, pady=(0, 8))

        # Progres pas
        self._step_progress_var = tk.StringVar(
            value="")
        tk.Label(
            self._step_card,
            textvariable=self._step_progress_var,
            font=("Courier New", 11, "bold"),
            bg="white", fg="#9C27B0",
        ).pack(pady=(0, 12))

        # Bara progres totala
        prog_frame = tk.Frame(
            self, bg="#FAFAFA")
        prog_frame.pack(
            fill="x", padx=20, pady=(0, 8))

        tk.Label(
            prog_frame,
            text="Progres sesiune:",
            font=("Arial", 10),
            bg="#FAFAFA", fg="#888",
            anchor="w",
        ).pack(fill="x")

        self._prog_canvas = tk.Canvas(
            prog_frame, height=8,
            bg="#E0E0E0",
            highlightthickness=0,
        )
        self._prog_canvas.pack(
            fill="x", pady=(4, 0))

        self._prog_label = tk.Label(
            prog_frame,
            text="Pasul 0 din 0",
            font=("Arial", 10),
            bg="#FAFAFA", fg="#888",
        )
        self._prog_label.pack(anchor="e")

        # Respiratie vizuala (cerc)
        self._breath_canvas = tk.Canvas(
            self, width=120, height=120,
            bg="#FAFAFA",
            highlightthickness=0,
        )
        self._breath_canvas.pack(pady=(0, 8))
        self._breath_canvas.pack_forget()

        # Butoane
        btn_frame = tk.Frame(
            self, bg="#FAFAFA")
        btn_frame.pack(
            fill="x", padx=20,
            pady=(0, 16), side="bottom")

        self._skip_btn = tk.Button(
            btn_frame,
            text="⏭ Sari peste pas",
            font=("Arial", 10),
            bg="#E0E0E0", fg="#5D4037",
            relief="flat", cursor="hand2",
            pady=6, bd=0,
            command=self._skip_step,
        )
        self._skip_btn.pack(
            fill="x", pady=(0, 6))

        self._stop_btn = tk.Button(
            btn_frame,
            text="⏹ Oprește sesiunea",
            font=("Arial", 10),
            bg="#FFEBEE", fg="#C62828",
            relief="flat", cursor="hand2",
            pady=6, bd=0,
            command=self._on_close,
        )
        self._stop_btn.pack(fill="x")

    # ── Sesiune ───────────────────────────────────────────────────────────────

    def _start_session(self):
        self._session = WellnessSession(
            wtype     = self._wtype,
            on_step   = self._on_step,
            on_done   = self._on_done,
            on_tick   = self._on_tick,
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
        tip = step.get("tip", "mesaj")

        self._step_text_var.set(step["text"])
        self._step_icon_var.set(
            step.get("icon", ""))
        self._step_progress_var.set("")

        pct = (idx / max(total - 1, 1))
        self._draw_progress(pct)
        self._prog_label.configure(
            text=f"Pasul {idx + 1} din {total}")

        # Culoare card per tip
        card_colors = {
            "titlu": "#F3E5F5",
            "countdown": "#E3F2FD",
            "ritm": "#E8F5E9",
            "directie": "#FFF3E0",
            "actiune": "#FFF8E1",
            "mesaj": "#FAFAFA",
            "respiratie": "#F3E5F5",
        }
        self._step_card.configure(
            bg=card_colors.get(tip, "white"))

        for w in self._step_card.winfo_children():
            try:
                w.configure(
                    bg=card_colors.get(tip, "white"))
            except Exception:
                pass

        # Stare animatie
        if tip == "respiratie":
            faza = step.get("faza", "neutral")
            self._breath_phase = faza
            self._anim_state = "breath"
            self._breath_canvas.pack(pady=(0, 8))
        elif tip in ("actiune", "directie", "ritm"):
            self._anim_state = "exercise"
            self._breath_canvas.pack_forget()
        elif tip == "titlu":
            self._anim_state = "happy"
            self._breath_canvas.pack_forget()
        elif tip == "mesaj":
            self._anim_state = "happy"
            self._breath_canvas.pack_forget()
        elif tip == "countdown":
            self._anim_state = "idle"
            self._breath_canvas.pack_forget()
        else:
            self._anim_state = "idle"
            self._breath_canvas.pack_forget()

    def _on_tick(self, sec: int, total: int):
        self.after(
            0,
            lambda s=sec, t=total:
            self._apply_tick(s, t))

    def _apply_tick(self, sec: int, total: int):
        self._step_progress_var.set(
            f"⏱  {sec}s")

        # Animatie respiratie
        if self._anim_state == "breath":
            self._draw_breath_circle(sec, total)

    def _draw_breath_circle(self, sec: int,
                             total: int):
        self._breath_canvas.delete("all")
        faza = self._breath_phase

        if faza == "inspir":
            pct   = 1.0 - (sec / total)
            color = "#4CAF50"
            label = "Inspiră..."
        elif faza == "expir":
            pct   = sec / total
            color = "#2196F3"
            label = "Expiră..."
        else:
            pct   = 0.5
            color = "#FF9800"
            label = "Ține..."

        # Cerc de baza
        self._breath_canvas.create_oval(
            10, 10, 110, 110,
            fill="#E0E0E0", outline="")

        # Cerc progres
        r = int(10 + pct * 50)
        cx, cy = 60, 60
        self._breath_canvas.create_oval(
            cx - r, cy - r,
            cx + r, cy + r,
            fill=color, outline="",
        )

        # Text
        self._breath_canvas.create_text(
            60, 60, text=label,
            font=("Arial", 9, "bold"),
            fill="white",
        )

    def _draw_progress(self, pct: float):
        self._prog_canvas.delete("all")
        w = self._prog_canvas.winfo_width()
        if w < 2:
            w = 360

        meta  = WELLNESS_META[self._wtype]
        color = meta["btn_color"]

        self._prog_canvas.create_rectangle(
            0, 0, w, 8,
            fill="#E0E0E0", outline="")
        self._prog_canvas.create_rectangle(
            0, 0, int(w * pct), 8,
            fill=color, outline="")

    def _on_done(self):
        self.after(0, self._show_done)

    def _show_done(self):
        self._step_icon_var.set("🌟")
        self._step_text_var.set(
            "Sesiune completa! Bravo!")
        self._step_progress_var.set("")
        self._anim_state = "happy"
        self._draw_progress(1.0)
        self._skip_btn.configure(
            state="disabled")

        # Salveaza pauza in DailyStats
        self._save_break_to_db()

        # Inchide automat dupa 4 secunde
        self.after(4000, self.destroy)

    def _save_break_to_db(self):
        """Incrementeaza pauze_luate in DailyStats pentru azi."""
        if not self._engine or not self._user_id:
            return
        try:
            from database import get_session, DailyStats
            from datetime import date

            session = get_session(self._engine)
            try:
                today = date.today()
                stat  = session.query(DailyStats).filter_by(
                    id_utilizator=self._user_id,
                    data=today,
                ).first()

                if not stat:
                    stat = DailyStats(
                        id_utilizator=self._user_id,
                        data=today,
                        timp_total_sec=0,
                        timp_blocat_sec=0,
                        pauze_luate=0,
                    )
                    session.add(stat)

                stat.pauze_luate = (stat.pauze_luate or 0) + 1
                session.commit()
                print(f"[WELLNESS] Pauza salvata: "
                      f"user {self._user_id}, "
                      f"total azi: {stat.pauze_luate}")
            finally:
                session.close()
        except Exception as e:
            print(f"[WELLNESS] DB pauza err: {e}")

    def _skip_step(self):
        if self._session:
            self._session.stop()
            self._start_session()

    def _on_close(self):
        if self._session:
            self._session.stop()
        try:
            self.destroy()
        except Exception:
            pass

    # ── Animatie animalut ─────────────────────────────────────────────────────

    def _animate(self):
        if not self.winfo_exists():
            return

        self._frame_n += 1
        self._draw_pet()
        self.after(100, self._animate)

    def _draw_pet(self):
        self._canvas.delete("all")

        f    = self._frame_n
        state = self._anim_state

        # Bob animatie
        if state == "happy":
            bob = math.sin(f * 0.4) * 6
        elif state == "exercise":
            bob = math.sin(f * 0.6) * 8
        elif state == "breath":
            bob = math.sin(f * 0.15) * 3
        else:
            bob = math.sin(f * 0.15) * 2

        base_x = 200
        base_y = 90 + bob

        if self._pet_type == "cat":
            self._draw_cat(base_x, base_y,
                           state, f)
        else:
            self._draw_dog(base_x, base_y,
                           state, f)

        # Text stare sub animalut
        state_labels = {
            "idle":     "",
            "happy":    "😊",
            "exercise": "💪",
            "breath":   "🌬",
        }
        lbl = state_labels.get(state, "")
        if lbl:
            self._canvas.create_text(
                200, 130,
                text=lbl,
                font=("Arial", 18),
            )

    def _draw_cat(self, cx: float, cy: float,
                  state: str, f: int):
        cv = self._canvas
        c  = {
            "body":   "#F4A460",
            "belly":  "#FFF8F0",
            "detail": "#8B6340",
            "eye":    "#2E8B57",
            "nose":   "#FF8FAB",
        }

        # Brate ridicate la exercitiu
        if state == "exercise":
            arm_y = math.sin(f * 0.4) * 10
            # Brat stang
            cv.create_line(
                cx - 22, cy - 5,
                cx - 38, cy - 20 - abs(arm_y),
                fill=c["body"], width=7,
                capstyle="round")
            # Brat drept
            cv.create_line(
                cx + 22, cy - 5,
                cx + 38, cy - 20 - abs(arm_y),
                fill=c["body"], width=7,
                capstyle="round")
        elif state == "breath":
            # Brate pe burta
            cv.create_line(
                cx - 22, cy,
                cx - 10, cy + 10,
                fill=c["body"], width=7,
                capstyle="round")
            cv.create_line(
                cx + 22, cy,
                cx + 10, cy + 10,
                fill=c["body"], width=7,
                capstyle="round")

        # Corp
        cv.create_oval(
            cx - 28, cy - 18,
            cx + 28, cy + 22,
            fill=c["body"],
            outline=c["detail"], width=1)

        # Burta
        cv.create_oval(
            cx - 18, cy - 6,
            cx + 18, cy + 18,
            fill=c["belly"], outline="")

        # Cap
        cv.create_oval(
            cx - 24, cy - 52,
            cx + 24, cy - 8,
            fill=c["body"],
            outline=c["detail"], width=1)

        # Urechi
        cv.create_polygon(
            cx - 22, cy - 48,
            cx - 28, cy - 64,
            cx - 12, cy - 44,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            cx + 22, cy - 48,
            cx + 28, cy - 64,
            cx + 12, cy - 44,
            fill=c["body"],
            outline=c["detail"], width=1)

        # Ochi — happy = arcuri
        if state == "happy":
            cv.create_arc(
                cx - 18, cy - 40,
                cx - 6, cy - 30,
                start=0, extent=180,
                outline=c["detail"], width=2,
                style="arc")
            cv.create_arc(
                cx + 6, cy - 40,
                cx + 18, cy - 30,
                start=0, extent=180,
                outline=c["detail"], width=2,
                style="arc")
        else:
            cv.create_oval(
                cx - 16, cy - 40,
                cx - 8, cy - 32,
                fill=c["eye"], outline="")
            cv.create_oval(
                cx + 8, cy - 40,
                cx + 16, cy - 32,
                fill=c["eye"], outline="")
            cv.create_oval(
                cx - 14, cy - 38,
                cx - 10, cy - 34,
                fill="black", outline="")
            cv.create_oval(
                cx + 10, cy - 38,
                cx + 14, cy - 34,
                fill="black", outline="")

        # Nas
        cv.create_polygon(
            cx - 2, cy - 26,
            cx + 2, cy - 26,
            cx, cy - 23,
            fill=c["nose"], outline="")

        # Gura — zambet la happy
        if state == "happy":
            cv.create_arc(
                cx - 8, cy - 24,
                cx + 8, cy - 14,
                start=200, extent=140,
                outline=c["detail"], width=2,
                style="arc")
        else:
            cv.create_line(
                cx, cy - 23,
                cx - 4, cy - 20,
                fill=c["detail"], width=1)
            cv.create_line(
                cx, cy - 23,
                cx + 4, cy - 20,
                fill=c["detail"], width=1)

        # Coada animata
        tw = math.sin(f * 0.3) * 15
        cv.create_arc(
            cx + 20, cy - 14,
            cx + 48 + tw, cy + 10,
            start=30, extent=140,
            outline=c["detail"], width=3,
            style="arc")

        # Picioare
        cv.create_rectangle(
            cx - 24, cy + 16,
            cx - 12, cy + 28,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_rectangle(
            cx + 12, cy + 16,
            cx + 24, cy + 28,
            fill=c["body"],
            outline=c["detail"], width=1)

    def _draw_dog(self, cx: float, cy: float,
                  state: str, f: int):
        cv = self._canvas
        c  = {
            "body":   "#C8A882",
            "belly":  "#F5ECD7",
            "detail": "#8B6340",
            "eye":    "#4A3728",
            "nose":   "#3D2B1F",
        }

        # Brate
        if state == "exercise":
            arm_y = math.sin(f * 0.4) * 10
            cv.create_line(
                cx - 24, cy - 5,
                cx - 40, cy - 20 - abs(arm_y),
                fill=c["body"], width=8,
                capstyle="round")
            cv.create_line(
                cx + 24, cy - 5,
                cx + 40, cy - 20 - abs(arm_y),
                fill=c["body"], width=8,
                capstyle="round")

        # Corp
        cv.create_oval(
            cx - 30, cy - 18,
            cx + 30, cy + 24,
            fill=c["body"],
            outline=c["detail"], width=1)

        # Burta
        cv.create_oval(
            cx - 18, cy - 4,
            cx + 18, cy + 20,
            fill=c["belly"], outline="")

        # Cap
        cv.create_oval(
            cx - 26, cy - 52,
            cx + 26, cy - 4,
            fill=c["body"],
            outline=c["detail"], width=1)

        # Urechi floppy
        cv.create_oval(
            cx - 36, cy - 48,
            cx - 16, cy - 16,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            cx + 16, cy - 48,
            cx + 36, cy - 16,
            fill=c["detail"],
            outline=c["detail"], width=1)

        # Ochi
        if state == "happy":
            cv.create_arc(
                cx - 18, cy - 40,
                cx - 6, cy - 30,
                start=0, extent=180,
                outline=c["detail"], width=2,
                style="arc")
            cv.create_arc(
                cx + 6, cy - 40,
                cx + 18, cy - 30,
                start=0, extent=180,
                outline=c["detail"], width=2,
                style="arc")
        else:
            cv.create_oval(
                cx - 16, cy - 40,
                cx - 8, cy - 32,
                fill=c["eye"], outline="")
            cv.create_oval(
                cx + 8, cy - 40,
                cx + 16, cy - 32,
                fill=c["eye"], outline="")
            cv.create_oval(
                cx - 14, cy - 38,
                cx - 10, cy - 34,
                fill="black", outline="")
            cv.create_oval(
                cx + 10, cy - 38,
                cx + 14, cy - 34,
                fill="black", outline="")

        # Nas
        cv.create_oval(
            cx - 6, cy - 26,
            cx + 6, cy - 18,
            fill=c["nose"], outline="")

        # Gura
        if state == "happy":
            cv.create_arc(
                cx - 10, cy - 22,
                cx + 10, cy - 10,
                start=200, extent=140,
                outline=c["detail"], width=2,
                style="arc")

        # Coada animata
        tw = math.sin(f * 0.6) * 14
        cv.create_arc(
            cx + 22, cy - 12,
            cx + 50 + tw, cy + 8,
            start=10, extent=160,
            outline=c["detail"], width=3,
            style="arc")

        # Picioare
        for px in [cx - 22, cx + 10]:
            cv.create_rectangle(
                px, cy + 18,
                px + 14, cy + 30,
                fill=c["body"],
                outline=c["detail"], width=1)