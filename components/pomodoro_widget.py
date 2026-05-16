"""
Coffee & Axl - Pomodoro Widget
Widget always-on-top cu timer vizibil permanent.
Axl intreaba ce faci si recomanda planul:
- instant prin cuvinte cheie
- AI pentru explicatie detaliata
"""

import tkinter as tk
import math
import time
import threading
import os
from enum import Enum


# ─── Constante ────────────────────────────────────────────────────────────────

CAFE_DIR = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
IPC_FILE = os.path.join(CAFE_DIR, "pet_ipc.txt")


class PomodoroPhase(Enum):
    IDLE        = "idle"
    WORK        = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK  = "long_break"
    PAUSED      = "paused"


# ─── Planuri ──────────────────────────────────────────────────────────────────

PLANS = {
    "clasic": {
        "nume":        "Clasic 25/5",
        "descriere":   "Varianta standard — echilibru perfect",
        "work":        25 * 60,
        "short_break": 5 * 60,
        "long_break":  20 * 60,
        "sessions_until_long": 4,
        "icon":        "🍅",
        "culoare":     "#E53935",
        "recomandat":  [
            "general", "email", "citit",
            "raspuns", "organizare", "meeting",
            "sedinta", "planificare", "review",
        ],
    },
    "scurt": {
        "nume":        "Scurt 20/5",
        "descriere":   "Pentru sarcini dificile sau lipsă de motivație",
        "work":        20 * 60,
        "short_break": 5 * 60,
        "long_break":  15 * 60,
        "sessions_until_long": 4,
        "icon":        "⚡",
        "culoare":     "#F57F17",
        "recomandat":  [
            "dificil", "greu", "complicat",
            "nu stiu", "blocat", "obosit",
            "motivatie", "incep", "primul",
            "frica", "anxios", "stres",
        ],
    },
    "profund": {
        "nume":        "Profund 40/10",
        "descriere":   "Pentru muncă profundă și concentrare maximă",
        "work":        40 * 60,
        "short_break": 10 * 60,
        "long_break":  30 * 60,
        "sessions_until_long": 3,
        "icon":        "🧠",
        "culoare":     "#1565C0",
        "recomandat":  [
            "cod", "programare", "scris",
            "design", "analiza", "invatat",
            "cercetare", "proiect", "licenta",
            "teza", "lucrare", "algoritm",
            "implementare", "dezvoltare",
            "python", "java", "react",
        ],
    },
}

BREAK_EXERCISES = [
    ("👁", "Pauza ochilor",
     "Hai să facem exercițiul 20-20-20!", "eyes"),
    ("🌬", "Respirație",
     "O respirație scurtă te va relaxa!", "breathing"),
    ("🏃", "Mișcare",
     "Ridică-te și întinde-te puțin!", "movement"),
    ("💧", "Apă",
     "Bea puțină apă acum!", "water"),
]


# ─── Dialog task ──────────────────────────────────────────────────────────────

class TaskDialog(tk.Toplevel):

    def __init__(self, root,
                 on_start: callable,
                 pet_type: str = "cat"):
        super().__init__(root)

        self._on_start    = on_start
        self._pet_type    = pet_type
        self._plan_var    = tk.StringVar(
            value="clasic")
        self._task_var    = tk.StringVar()
        self._work_var    = tk.IntVar(value=25)
        self._break_var   = tk.IntVar(value=5)
        self._ai_loading  = False

        self.title("Axl — Ce lucrezi azi?")
        self.geometry("460x620")
        self.resizable(False, False)
        self.configure(bg="#FFF8E1")
        self.attributes("-topmost", True)
        self.protocol(
            "WM_DELETE_WINDOW", self.destroy)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 460) // 2
        y  = (sh - 620) // 2
        self.geometry(f"460x620+{x}+{y}")
        self.lift()
        self.focus_force()

        self._build()
        self._say_greeting()

    def _build(self):
        # Header
        header = tk.Frame(
            self, bg="#F9A825", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🍅  Axl Pomodoro",
            font=("Georgia", 14, "bold"),
            bg="#F9A825", fg="white",
            anchor="w",
        ).pack(side="left", padx=16, pady=14)

        tk.Button(
            header, text="✕",
            font=("Arial", 11, "bold"),
            bg="#F9A825", fg="white",
            relief="flat", cursor="hand2",
            bd=0, command=self.destroy,
        ).pack(side="right", padx=16)

        # Intrebare Axl
        q_frame = tk.Frame(
            self, bg="#FFFDE7")
        q_frame.pack(
            fill="x", padx=16, pady=(12, 8))

        tk.Label(
            q_frame,
            text="💭  Axl te întreabă:",
            font=("Arial", 10, "bold"),
            bg="#FFFDE7", fg="#8B6914",
            anchor="w",
        ).pack(anchor="w", padx=12,
               pady=(8, 2))

        tk.Label(
            q_frame,
            text="Ce ai de lucru azi?\n"
                 "Descrie taskul și îți recomand "
                 "planul potrivit.",
            font=("Arial", 12),
            bg="#FFFDE7", fg="#5D4037",
            justify="left", anchor="w",
            wraplength=400,
        ).pack(anchor="w", padx=12,
               pady=(0, 10))

        # Input task
        input_frame = tk.Frame(
            self, bg="#FFF8E1")
        input_frame.pack(
            fill="x", padx=16, pady=(0, 4))

        tk.Label(
            input_frame,
            text="Taskul meu:",
            font=("Arial", 11, "bold"),
            bg="#FFF8E1", fg="#5D4037",
            anchor="w",
        ).pack(anchor="w")

        entry_frame = tk.Frame(
            input_frame,
            bg="white",
            highlightbackground="#DDD",
            highlightthickness=1,
        )
        entry_frame.pack(fill="x", pady=(4, 0))

        self._task_entry = tk.Entry(
            entry_frame,
            textvariable=self._task_var,
            font=("Arial", 12),
            bg="white", fg="#1A1A1A",
            relief="flat", bd=0,
        )
        self._task_entry.pack(
            fill="x", ipady=10, padx=8)
        self._task_entry.bind(
            "<KeyRelease>",
            lambda e: self._on_task_change())
        self._task_entry.bind(
            "<Return>",
            lambda e: self._start())
        self._task_entry.focus()

        # Card recomandare instant
        self._rec_card = tk.Frame(
            self, bg="#FFF8E1")
        self._rec_card.pack(
            fill="x", padx=16, pady=(6, 0))

        self._rec_icon_var = tk.StringVar(
            value="")
        self._rec_text_var = tk.StringVar(
            value="Scrie taskul pentru recomandare")

        rec_row = tk.Frame(
            self._rec_card, bg="#FFF8E1")
        rec_row.pack(fill="x")

        self._rec_icon_lbl = tk.Label(
            rec_row,
            textvariable=self._rec_icon_var,
            font=("Arial", 14),
            bg="#FFF8E1",
        )
        self._rec_icon_lbl.pack(side="left")

        self._rec_text_lbl = tk.Label(
            rec_row,
            textvariable=self._rec_text_var,
            font=("Arial", 10, "italic"),
            bg="#FFF8E1", fg="#888",
            anchor="w", wraplength=380,
        )
        self._rec_text_lbl.pack(
            side="left", padx=(6, 0),
            fill="x", expand=True)

        # Explicatie AI
        self._ai_frame = tk.Frame(
            self, bg="#F3E5F5",
            relief="flat")

        self._ai_text_var = tk.StringVar(
            value="")
        self._ai_lbl = tk.Label(
            self._ai_frame,
            textvariable=self._ai_text_var,
            font=("Arial", 10),
            bg="#F3E5F5", fg="#4A148C",
            wraplength=400,
            justify="left", anchor="w",
        )
        self._ai_lbl.pack(
            padx=12, pady=8, anchor="w")

        # Separator
        tk.Frame(
            self, bg="#E0E0E0", height=1,
        ).pack(fill="x", padx=16,
               pady=(8, 4))

        # Planuri
        tk.Label(
            self,
            text="Selectează planul:",
            font=("Arial", 11, "bold"),
            bg="#FFF8E1", fg="#5D4037",
            anchor="w",
        ).pack(anchor="w", padx=16,
               pady=(0, 4))

        self._plans_frame = tk.Frame(
            self, bg="#FFF8E1")
        self._plans_frame.pack(
            fill="x", padx=16, pady=(0, 4))

        self._build_plan_cards()

        # Personalizat
        self._build_custom_section()

        # Buton START mare
        start_frame = tk.Frame(
            self, bg="#FFF8E1")
        start_frame.pack(
            fill="x", padx=16,
            pady=(8, 16), side="bottom")

        self._start_btn = tk.Button(
            start_frame,
            text="▶  Pornește Pomodoro",
            font=("Arial", 14, "bold"),
            bg="#E53935", fg="white",
            relief="flat", cursor="hand2",
            pady=14, bd=0,
            command=self._start,
        )
        self._start_btn.pack(fill="x")

        self._start_btn.bind(
            "<Enter>",
            lambda e: self._start_btn.configure(
                bg="#C62828"))
        self._start_btn.bind(
            "<Leave>",
            lambda e: self._start_btn.configure(
                bg=self._get_selected_color()))

    def _get_selected_color(self) -> str:
        plan = PLANS.get(
            self._plan_var.get(), PLANS["clasic"])
        return plan.get("culoare", "#E53935")

    def _build_plan_cards(self):
        for w in self._plans_frame.winfo_children():
            w.destroy()

        for key, plan in PLANS.items():
            self._build_plan_card(
                self._plans_frame, key, plan)

    def _build_plan_card(self, parent,
                          key: str, plan: dict):
        selected = (self._plan_var.get() == key)
        color    = plan["culoare"]

        card = tk.Frame(
            parent,
            bg=color if selected else "#F5F5F5",
            cursor="hand2",
            relief="flat",
        )
        card.pack(fill="x", pady=2)

        def _select(k=key, c=color):
            self._plan_var.set(k)
            self._build_plan_cards()
            self._start_btn.configure(bg=c)

        # Row principale
        row = tk.Frame(
            card,
            bg=card.cget("bg"),
            cursor="hand2")
        row.pack(fill="x", padx=10, pady=(6, 2))

        # Icon + Nume
        tk.Label(
            row,
            text=f"{plan['icon']}  "
                 f"{plan['nume']}",
            font=("Arial", 11, "bold"),
            bg=card.cget("bg"),
            fg="white" if selected else "#1A1A1A",
            cursor="hand2", anchor="w",
        ).pack(side="left")

        # Durate
        work_min  = plan["work"] // 60
        break_min = plan["short_break"] // 60
        long_min  = plan["long_break"] // 60

        tk.Label(
            row,
            text=f"{work_min}' lucru / "
                 f"{break_min}' pauză / "
                 f"{long_min}' lung",
            font=("Arial", 9),
            bg=card.cget("bg"),
            fg="white" if selected else "#888",
            cursor="hand2",
        ).pack(side="right")

        # Descriere
        tk.Label(
            card,
            text=plan["descriere"],
            font=("Arial", 9),
            bg=card.cget("bg"),
            fg="#EEEEEE" if selected else "#666",
            cursor="hand2", anchor="w",
        ).pack(anchor="w", padx=10,
               pady=(0, 6))

        # Click bind
        for w in [card, row] + \
                list(card.winfo_children()) + \
                list(row.winfo_children()):
            try:
                w.bind(
                    "<Button-1>",
                    lambda e, k=key: _select(k))
            except Exception:
                pass

    def _build_custom_section(self):
        frame = tk.Frame(
            self, bg="#FFF8E1")
        frame.pack(
            fill="x", padx=16, pady=(0, 4))

        tk.Label(
            frame,
            text="⚙️  Personalizat:",
            font=("Arial", 10, "bold"),
            bg="#FFF8E1", fg="#6A1B9A",
            anchor="w",
        ).pack(anchor="w")

        row = tk.Frame(frame, bg="#FFF8E1")
        row.pack(fill="x", pady=(4, 0))

        tk.Label(
            row, text="Lucru (min):",
            font=("Arial", 10),
            bg="#FFF8E1", fg="#5D4037",
        ).pack(side="left")

        tk.Spinbox(
            row,
            textvariable=self._work_var,
            from_=5, to=90, width=4,
            font=("Arial", 10),
            command=self._on_custom_change,
        ).pack(side="left", padx=(4, 12))

        tk.Label(
            row, text="Pauză (min):",
            font=("Arial", 10),
            bg="#FFF8E1", fg="#5D4037",
        ).pack(side="left")

        tk.Spinbox(
            row,
            textvariable=self._break_var,
            from_=1, to=30, width=4,
            font=("Arial", 10),
            command=self._on_custom_change,
        ).pack(side="left", padx=(4, 0))

    def _on_custom_change(self):
        self._plan_var.set("personalizat")
        self._build_plan_cards()
        self._start_btn.configure(bg="#6A1B9A")

    # ── Recomandare hybrid ────────────────────────────────────────────────────

    def _on_task_change(self):
        task = self._task_var.get().strip()

        if not task:
            self._rec_icon_var.set("")
            self._rec_text_var.set(
                "Scrie taskul pentru recomandare")
            self._rec_text_lbl.configure(
                fg="#888")
            self._ai_frame.pack_forget()
            return

        # Pas 1: Recomandare instant
        recommended = self._quick_recommend(task)
        plan = PLANS.get(
            recommended, PLANS["clasic"])

        self._plan_var.set(recommended)
        self._build_plan_cards()
        self._start_btn.configure(
            bg=plan["culoare"])

        self._rec_icon_var.set(plan["icon"])
        self._rec_text_var.set(
            f"Axl recomandă: {plan['nume']}")
        self._rec_text_lbl.configure(
            fg=plan["culoare"])

        # Pas 2: AI explicatie (debounced)
        if hasattr(self, "_ai_timer"):
            try:
                self.after_cancel(self._ai_timer)
            except Exception:
                pass

        self._ai_timer = self.after(
            800,
            lambda t=task, r=recommended:
            self._get_ai_explanation(t, r))

    def _quick_recommend(self, task: str) -> str:
        task_lower = task.lower()
        scores = {key: 0 for key in PLANS}

        for key, plan in PLANS.items():
            for kw in plan.get("recomandat", []):
                if kw in task_lower:
                    scores[key] += 1

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "clasic"
        return best

    def _get_ai_explanation(self, task: str,
                             recommended: str):
        if self._ai_loading:
            return
        self._ai_loading = True

        # Arata loading
        self._ai_text_var.set(
            "🧠 Axl analizează taskul tău...")
        self._ai_frame.pack(
            fill="x", padx=16, pady=(0, 4))

        def _run():
            try:
                import urllib.request
                import json

                plan = PLANS.get(
                    recommended, PLANS["clasic"])

                prompt = (
                    f"Ești Axl, asistent wellness. "
                    f"Utilizatorul vrea să lucreze la: "
                    f"'{task}'. "
                    f"Am recomandat planul Pomodoro "
                    f"'{plan['nume']}' "
                    f"({plan['work']//60} minute lucru, "
                    f"{plan['short_break']//60} minute pauză). "
                    f"Explică în 1-2 propoziții scurte "
                    f"DE CE acest plan este potrivit "
                    f"pentru acest task specific. "
                    f"Fii concis și practic. "
                    f"Răspunde doar în română."
                )

                payload = json.dumps({
                    "model": "llama3",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "stream": False,
                }).encode("utf-8")

                req = urllib.request.Request(
                    "http://localhost:11434/api/chat",
                    data=payload,
                    headers={
                        "Content-Type":
                            "application/json"},
                    method="POST",
                )

                with urllib.request.urlopen(
                        req, timeout=10) as resp:
                    data    = json.loads(
                        resp.read())
                    content = data.get(
                        "message", {}).get(
                        "content", "").strip()

                if content:
                    self.after(
                        0,
                        lambda c=content:
                        self._show_ai_explanation(c))
                else:
                    self.after(
                        0, self._hide_ai_explanation)

            except Exception:
                self.after(
                    0, self._hide_ai_explanation)
            finally:
                self._ai_loading = False

        threading.Thread(
            target=_run, daemon=True).start()

    def _show_ai_explanation(self, text: str):
        self._ai_text_var.set(
            f"🧠 {text}")
        self._ai_frame.pack(
            fill="x", padx=16, pady=(0, 4))

    def _hide_ai_explanation(self):
        self._ai_frame.pack_forget()
        self._ai_loading = False

    # ── Start ─────────────────────────────────────────────────────────────────

    def _start(self):
        task = self._task_var.get().strip()
        if not task:
            # Evidentiaza input
            self._task_entry.configure(
                bg="#FFEBEE")
            self.after(
                1000,
                lambda: self._task_entry
                .configure(bg="white"))
            self._task_entry.focus()
            return

        plan_key = self._plan_var.get()

        if plan_key == "personalizat" or \
                plan_key not in PLANS:
            plan = {
                "nume":        "Personalizat",
                "icon":        "⚙️",
                "culoare":     "#6A1B9A",
                "work":
                    self._work_var.get() * 60,
                "short_break":
                    self._break_var.get() * 60,
                "long_break":
                    self._break_var.get() * 3 * 60,
                "sessions_until_long": 4,
            }
        else:
            plan = PLANS[plan_key]

        self.destroy()
        if self._on_start:
            self._on_start(task, plan_key, plan)

    def _say_greeting(self):
        def _tts():
            try:
                from utils.voice_assistant import (
                    SpeechEngine)
                tts  = SpeechEngine()
                done = threading.Event()
                tts.speak(
                    "Salut! Ce ai de lucru azi? "
                    "Descrie taskul și aleg "
                    "planul Pomodoro potrivit.",
                    on_done=lambda: done.set())
                done.wait(timeout=12)
            except Exception:
                pass
        threading.Thread(
            target=_tts, daemon=True).start()


# ─── Widget Pomodoro ──────────────────────────────────────────────────────────

class PomodoroWidget(tk.Toplevel):

    def __init__(self, root,
                 task: str,
                 plan_key: str,
                 plan: dict,
                 pet_type: str = "cat"):
        super().__init__(root)

        self._task      = task
        self._plan_key  = plan_key
        self._plan      = plan
        self._pet_type  = pet_type
        self._root_ref  = root

        self._phase         = PomodoroPhase.IDLE
        self._seconds_left  = plan["work"]
        self._session_n     = 0
        self._total_done    = 0
        self._running       = False
        self._paused        = False
        self._minimized     = False
        self._frame_n       = 0

        self._drag_x = 0
        self._drag_y = 0

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(
            bg=plan.get("culoare", "#E53935"))

        sw = self.winfo_screenwidth()
        self.geometry(f"290x170+{sw - 310}+20")

        self._build_ui()
        self._start_work()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        color = self._plan.get(
            "culoare", "#E53935")

        # Header
        self._header = tk.Frame(
            self, bg=color, cursor="fleur")
        self._header.pack(fill="x")

        tk.Label(
            self._header,
            text=f"🍅  {self._plan.get('icon', '')} "
                 f"{self._plan.get('nume', '')}",
            font=("Arial", 9, "bold"),
            bg=color, fg="white",
            anchor="w",
        ).pack(side="left", padx=8, pady=4)

        btn_f = tk.Frame(
            self._header, bg=color)
        btn_f.pack(side="right", padx=4)

        tk.Button(
            btn_f, text="—",
            font=("Arial", 9, "bold"),
            bg=color, fg="white",
            relief="flat", cursor="hand2",
            bd=0, width=2,
            command=self._toggle_minimize,
        ).pack(side="left")

        tk.Button(
            btn_f, text="✕",
            font=("Arial", 9, "bold"),
            bg=color, fg="white",
            relief="flat", cursor="hand2",
            bd=0, width=2,
            command=self._confirm_close,
        ).pack(side="left")

        # Drag
        self._header.bind(
            "<ButtonPress-1>",
            self._drag_start)
        self._header.bind(
            "<B1-Motion>",
            self._drag_motion)
        for w in self._header.winfo_children():
            w.bind("<ButtonPress-1>",
                   self._drag_start)
            w.bind("<B1-Motion>",
                   self._drag_motion)

        # Body
        self._body = tk.Frame(
            self, bg="#1A1A1A")
        self._body.pack(
            fill="both", expand=True)

        # Task label
        task_short = (
            self._task[:32] + "..."
            if len(self._task) > 32
            else self._task)
        tk.Label(
            self._body,
            text=f"📋 {task_short}",
            font=("Arial", 9),
            bg="#1A1A1A", fg="#AAAAAA",
            anchor="w",
        ).pack(anchor="w", padx=10,
               pady=(6, 0))

        # Faza
        self._phase_lbl = tk.Label(
            self._body,
            text="LUCRU 💪",
            font=("Arial", 10, "bold"),
            bg="#1A1A1A",
            fg=color,
        )
        self._phase_lbl.pack(
            anchor="w", padx=10, pady=(2, 0))

        # Timer mare
        self._timer_var = tk.StringVar(
            value=self._format_time(
                self._plan["work"]))
        tk.Label(
            self._body,
            textvariable=self._timer_var,
            font=("Courier New", 38, "bold"),
            bg="#1A1A1A", fg="white",
        ).pack(pady=(0, 2))

        # Progres bara
        self._prog_canvas = tk.Canvas(
            self._body, height=4,
            bg="#333333",
            highlightthickness=0,
        )
        self._prog_canvas.pack(
            fill="x", pady=0)

        # Sesiuni dots
        self._sessions_lbl = tk.Label(
            self._body,
            text="",
            font=("Arial", 8),
            bg="#1A1A1A", fg="#666",
        )
        self._sessions_lbl.pack(
            anchor="w", padx=10,
            pady=(2, 0))

        # Butoane control
        ctrl = tk.Frame(
            self._body, bg="#1A1A1A")
        ctrl.pack(
            fill="x", padx=8,
            pady=(4, 8))

        self._pause_btn = tk.Button(
            ctrl,
            text="⏸ Pauză",
            font=("Arial", 9),
            bg="#333333", fg="white",
            relief="flat", cursor="hand2",
            bd=0, padx=8, pady=4,
            command=self._toggle_pause,
        )
        self._pause_btn.pack(
            side="left", padx=(0, 4))

        tk.Button(
            ctrl,
            text="⏭ Sari",
            font=("Arial", 9),
            bg="#333333", fg="white",
            relief="flat", cursor="hand2",
            bd=0, padx=8, pady=4,
            command=self._skip_phase,
        ).pack(side="left")

        tk.Button(
            ctrl,
            text="⏹",
            font=("Arial", 9),
            bg="#4A0000", fg="#FF8080",
            relief="flat", cursor="hand2",
            bd=0, padx=8, pady=4,
            command=self._confirm_close,
        ).pack(side="right")

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x_root - \
                       self.winfo_x()
        self._drag_y = event.y_root - \
                       self.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _toggle_minimize(self):
        if self._minimized:
            self._body.pack(
                fill="both", expand=True)
            self.geometry(
                f"290x170"
                f"+{self.winfo_x()}"
                f"+{self.winfo_y()}")
            self._minimized = False
        else:
            self._body.pack_forget()
            self.geometry(
                f"290x26"
                f"+{self.winfo_x()}"
                f"+{self.winfo_y()}")
            self._minimized = True

    # ── Timer ─────────────────────────────────────────────────────────────────

    def _format_time(self, seconds: int) -> str:
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _start_work(self):
        self._session_n   += 1
        self._phase        = PomodoroPhase.WORK
        self._seconds_left = self._plan["work"]
        self._running      = True
        self._paused       = False

        color = self._plan.get(
            "culoare", "#E53935")
        self._phase_lbl.configure(
            text="LUCRU 💪", fg=color)
        self._update_sessions_dots()
        self._notify_pet(
            f"pomodoro_work:{self._session_n}")

        self._say(
            f"Sesiunea {self._session_n} a început. "
            f"Concentrează-te!")

        threading.Thread(
            target=self._tick,
            daemon=True).start()

    def _start_short_break(self):
        self._phase        = PomodoroPhase.SHORT_BREAK
        self._seconds_left = \
            self._plan["short_break"]
        self._running      = True
        self._paused       = False
        self._total_done  += 1

        self._phase_lbl.configure(
            text="PAUZĂ SCURTĂ ☕",
            fg="#4CAF50")

        mins = self._plan["short_break"] // 60
        self._say(
            f"Sesiunea {self._session_n} completă! "
            f"Pauză de {mins} minute.")

        self._notify_pet("pomodoro_break:short")
        self.after(
            3000,
            self._suggest_break_exercise)

        threading.Thread(
            target=self._tick,
            daemon=True).start()

    def _start_long_break(self):
        self._phase        = PomodoroPhase.LONG_BREAK
        self._seconds_left = \
            self._plan["long_break"]
        self._running      = True
        self._paused       = False

        self._phase_lbl.configure(
            text="PAUZĂ LUNGĂ 🎉",
            fg="#9C27B0")

        sessions = self._plan[
            "sessions_until_long"]
        mins     = self._plan["long_break"] // 60
        self._say(
            f"Felicitări! Ai completat "
            f"{sessions} sesiuni! "
            f"Pauză lungă de {mins} de minute!")

        self._notify_pet("pomodoro_break:long")
        self.after(
            3000,
            self._suggest_break_exercise)

        threading.Thread(
            target=self._tick,
            daemon=True).start()

    def _tick(self):
        while (self._running
               and self._seconds_left > 0):
            if not self._paused:
                time.sleep(1)
                self._seconds_left -= 1
                self.after(
                    0, self._update_ui)
            else:
                time.sleep(0.2)

        if (self._running
                and self._seconds_left <= 0):
            self.after(0, self._phase_complete)

    def _phase_complete(self):
        self._running = False

        if self._phase == PomodoroPhase.WORK:
            sessions_until = self._plan[
                "sessions_until_long"]
            if self._session_n % \
                    sessions_until == 0:
                self._start_long_break()
            else:
                self._start_short_break()

        elif self._phase in (
                PomodoroPhase.SHORT_BREAK,
                PomodoroPhase.LONG_BREAK):
            self._say(
                "Pauza s-a terminat. "
                "Gata de o nouă sesiune?")
            self.after(2000, self._start_work)

    def _toggle_pause(self):
        if self._paused:
            self._paused = False
            self._pause_btn.configure(
                text="⏸ Pauză")
            self._say("Continuăm!")
        else:
            self._paused = True
            self._pause_btn.configure(
                text="▶ Continuă")
            self._say("Pauză. Relaxează-te.")

    def _skip_phase(self):
        self._running      = False
        self._seconds_left = 0
        self.after(100, self._phase_complete)

    # ── UI Update ─────────────────────────────────────────────────────────────

    def _update_ui(self):
        self._timer_var.set(
            self._format_time(self._seconds_left))

        # Progres
        self._prog_canvas.delete("all")
        w = self._prog_canvas.winfo_width()
        if w < 2:
            w = 290

        if self._phase == PomodoroPhase.WORK:
            total = self._plan["work"]
            color = self._plan.get(
                "culoare", "#E53935")
        elif self._phase == \
                PomodoroPhase.LONG_BREAK:
            total = self._plan["long_break"]
            color = "#9C27B0"
        else:
            total = self._plan["short_break"]
            color = "#4CAF50"

        elapsed = total - self._seconds_left
        pct     = elapsed / max(total, 1)

        self._prog_canvas.create_rectangle(
            0, 0, int(w * pct), 4,
            fill=color, outline="")

    def _update_sessions_dots(self):
        total = self._plan[
            "sessions_until_long"]
        done  = (self._session_n - 1) % total
        dots  = "🍅" * done + \
                "○" * (total - done)
        self._sessions_lbl.configure(
            text=f"Sesiunea {self._session_n}"
                 f"   {dots}")

    # ── Notificari ────────────────────────────────────────────────────────────

    def _notify_pet(self, cmd: str):
        try:
            os.makedirs(CAFE_DIR, exist_ok=True)
            with open(IPC_FILE, "w",
                      encoding="utf-8") as f:
                f.write(cmd)
        except Exception:
            pass

    def _suggest_break_exercise(self):
        import random
        icon, nume, msg, wtype = \
            random.choice(BREAK_EXERCISES)
        self._say(msg)
        self.after(
            2000,
            lambda: self._notify_pet(
                f"wellness_suggest:{wtype}"))

    def _say(self, text: str):
        def _tts():
            try:
                from utils.voice_assistant import (
                    SpeechEngine)
                tts  = SpeechEngine()
                done = threading.Event()
                tts.speak(
                    text,
                    on_done=lambda: done.set())
                done.wait(timeout=20)
            except Exception:
                pass
        threading.Thread(
            target=_tts, daemon=True).start()

    # ── Close ─────────────────────────────────────────────────────────────────

    def _confirm_close(self):
        self._running = False
        self._paused  = False

        confirm = tk.Toplevel(self)
        confirm.title("")
        confirm.geometry("300x130")
        confirm.resizable(False, False)
        confirm.configure(bg="#1A1A1A")
        confirm.attributes("-topmost", True)

        sw = confirm.winfo_screenwidth()
        sh = confirm.winfo_screenheight()
        x  = (sw - 300) // 2
        y  = (sh - 130) // 2
        confirm.geometry(f"300x130+{x}+{y}")

        tk.Label(
            confirm,
            text=f"Oprești Pomodoro?\n"
                 f"Sesiuni completate: "
                 f"{self._total_done}",
            font=("Arial", 11),
            bg="#1A1A1A", fg="white",
            justify="center",
        ).pack(pady=(18, 12))

        row = tk.Frame(confirm, bg="#1A1A1A")
        row.pack(fill="x", padx=20)

        tk.Button(
            row, text="⏹ Oprește",
            font=("Arial", 10, "bold"),
            bg="#C62828", fg="white",
            relief="flat", cursor="hand2",
            pady=8, bd=0,
            command=lambda: [
                confirm.destroy(),
                self.destroy()],
        ).pack(side="left", expand=True,
               fill="x", padx=(0, 4))

        tk.Button(
            row, text="▶ Continuă",
            font=("Arial", 10),
            bg="#333", fg="white",
            relief="flat", cursor="hand2",
            pady=8, bd=0,
            command=lambda: [
                confirm.destroy(),
                self._resume()],
        ).pack(side="right", expand=True,
               fill="x", padx=(4, 0))

    def _resume(self):
        if not self._running:
            self._running = True
            self._paused  = False
            threading.Thread(
                target=self._tick,
                daemon=True).start()


# ─── Entry point ──────────────────────────────────────────────────────────────

def open_pomodoro(root, pet_type: str = "cat"):
    def _on_start(task: str,
                  plan_key: str,
                  plan: dict):
        PomodoroWidget(
            root,
            task     = task,
            plan_key = plan_key,
            plan     = plan,
            pet_type = pet_type,
        )

    TaskDialog(
        root,
        on_start = _on_start,
        pet_type = pet_type,
    )