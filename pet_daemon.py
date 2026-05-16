"""
Coffee & Axl - Pet Daemon
Proces independent cu system tray, always-on-top, IPC prin fisiere.
Click pe bula -> popup wellness -> buton chat.
Wellness Engine integrat cu sesiuni interactive.
"""

import tkinter as tk
import math
import random
import time
import os
import sys
import subprocess
import threading
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as TrayItem, Menu as TrayMenu

# ─── Cai ──────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CAFE_DIR    = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
PREFS_FILE  = os.path.join(CAFE_DIR, "pet_pref.txt")
POS_FILE    = os.path.join(CAFE_DIR, "pet_pos.txt")
IPC_FILE    = os.path.join(CAFE_DIR, "pet_ipc.txt")
LOCK_FILE   = os.path.join(CAFE_DIR, "pet.lock")
FOCUS_FILE  = os.path.join(CAFE_DIR, "focus_app.txt")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")

PET_SIZE      = 80
MARGIN_BOTTOM = 48
ANIM_INTERVAL = 120
IDLE_TIMEOUT  = 10
WALK_CHANCE   = 0.3

# ─── Culori ───────────────────────────────────────────────────────────────────
PETS = {
    "cat": {
        "name":   "Pisică",
        "body":   "#F4A460",
        "belly":  "#FFF8F0",
        "detail": "#8B6340",
        "eye":    "#2E8B57",
        "nose":   "#FF8FAB",
    },
    "dog": {
        "name":   "Cățeluș",
        "body":   "#C8A882",
        "belly":  "#F5ECD7",
        "detail": "#8B6340",
        "eye":    "#4A3728",
        "nose":   "#3D2B1F",
    },
}

# Alias-uri: axl = dog, coffee = cat
_PET_ALIASES = {"axl": "dog", "coffee": "cat"}

def _resolve_pet(key: str) -> str:
    """Normalizeaza cheia pet: axl->dog, coffee->cat."""
    return _PET_ALIASES.get(key, key if key in PETS else "cat")


BUBBLE_MESSAGES = {
    "cat": {
        "drowsy":    "Miau... 😴\nPari obosit!\nIa o pauză de 5 min.",
        "sad":       "Mrrr... 💙\nEști bine?\nAxl e aici cu tine.",
        "angry":     "Pisss... 😤\nCeva te-a supărat?\nRespiră adânc.",
        "fearful":   "Miau... 😰\nNu-ți fie frică!\nAxl e lângă tine.",
        "disgusted": "Mrrr... 😟\nCeva te deranjează?\nVorbim dacă vrei.",
        "both":      "Pisss... 🌙\nZi grea?\nO pauză te-ar ajuta.",
    },
    "dog": {
        "drowsy":    "Ham! 😴\nPari obosit!\nHai la o pauză scurtă!",
        "sad":       "Woof... 💙\nEști bine?\nAxl e alături de tine!",
        "angry":     "Hâm... 😤\nCeva te-a supărat?\nRespiră adânc!",
        "fearful":   "Woof... 😰\nNu-ți fie teamă!\nAxl e cu tine!",
        "disgusted": "Hâm... 😟\nCeva te deranjează?\nHai să vorbim!",
        "both":      "Woof woof... 🌙\nZi grea?\nO pauză te-ar ajuta!",
    },
}

POPUP_META = {
    "drowsy": {
        "icon":  "😴",
        "titlu": "Ești obosit?",
        "mesaj": "Am observat că pari obosit.\nO pauză de 5 minute\nte-ar ajuta enorm! ☕",
    },
    "sad": {
        "icon":  "💙",
        "titlu": "Ești abătut?",
        "mesaj": "Am observat că pari abătut.\nAxl e aici dacă vrei\nsă vorbești. 💙",
    },
    "angry": {
        "icon":  "😤",
        "titlu": "Ești frustrat?",
        "mesaj": "Am observat că pari frustrat.\nRespiră adânc —\ntotul va fi bine. 😤",
    },
    "fearful": {
        "icon":  "😰",
        "titlu": "Ești anxios?",
        "mesaj": "Am observat că pari anxios.\nNu ești singur,\nAxl e alături de tine. 😰",
    },
    "disgusted": {
        "icon":  "😟",
        "titlu": "Ești deranjat?",
        "mesaj": "Am observat că ceva\nte deranjează.\nVorbim dacă vrei. 😟",
    },
    "both": {
        "icon":  "🌙",
        "titlu": "Zi grea?",
        "mesaj": "Am observat că ai o zi grea.\nO pauză scurtă\nte-ar ajuta mult. 🌙",
    },
}


# ─── ThoughtBubble ────────────────────────────────────────────────────────────

class ThoughtBubble(tk.Toplevel):

    def __init__(self, parent, message: str,
                 pet_x: int, pet_y: int,
                 pet_w: int = 120,
                 timeout_ms: int = 10000,
                 on_open_chat=None):
        super().__init__(parent)

        self._on_open_chat = on_open_chat

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)
        self.configure(bg="#FFFDE7")

        bubble_w = 240
        bubble_h = 120

        x = pet_x + pet_w // 2 - bubble_w // 2
        y = pet_y - bubble_h - 8

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = max(4, min(x, sw - bubble_w - 4))
        y  = max(4, min(y, sh - bubble_h - 4))

        self.geometry(f"{bubble_w}x{bubble_h}+{x}+{y}")

        self._build(message)
        self._fade_in()
        self.after(timeout_ms, self._fade_out)

    def _build(self, message: str):
        frame = tk.Frame(
            self,
            bg="#FFFDE7",
            highlightbackground="#F9A825",
            highlightthickness=2,
        )
        frame.pack(fill="both", expand=True,
                   padx=2, pady=2)

        header = tk.Frame(frame, bg="#FFFDE7")
        header.pack(fill="x", padx=8, pady=(6, 0))

        tk.Label(
            header,
            text="💭 Axl",
            font=("Arial", 10, "bold"),
            bg="#FFFDE7",
            fg="#8B6914",
        ).pack(side="left")

        close_lbl = tk.Label(
            header,
            text="✕",
            font=("Arial", 9),
            bg="#FFFDE7",
            fg="#BDBDBD",
            cursor="hand2",
        )
        close_lbl.pack(side="right")
        close_lbl.bind(
            "<Button-1>",
            lambda e: self._close())

        tk.Label(
            frame,
            text=message,
            font=("Arial", 10),
            bg="#FFFDE7",
            fg="#5D4037",
            wraplength=210,
            justify="left",
        ).pack(padx=10, pady=(2, 4))

        btn = tk.Button(
            frame,
            text="💬 Vezi mesajul lui Axl →",
            font=("Arial", 9, "bold"),
            bg="#F9A825",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=8, pady=4,
            bd=0,
            command=self._open_chat,
        )
        btn.pack(padx=10, pady=(0, 8), fill="x")

        btn.bind(
            "<Enter>",
            lambda e: btn.configure(bg="#E08000"))
        btn.bind(
            "<Leave>",
            lambda e: btn.configure(bg="#F9A825"))

    def _open_chat(self):
        self._close()
        if self._on_open_chat:
            self.master.after(
                150, self._on_open_chat)

    def _fade_in(self, step: float = 0.0):
        step = min(step + 0.10, 0.93)
        try:
            self.attributes("-alpha", step)
        except Exception:
            return
        if step < 0.93:
            self.after(25,
                       lambda: self._fade_in(step))

    def _fade_out(self, step: float = 0.93):
        step = max(step - 0.10, 0.0)
        try:
            self.attributes("-alpha", step)
        except Exception:
            return
        if step > 0:
            self.after(25,
                       lambda: self._fade_out(step))
        else:
            self._close()

    def _close(self):
        try:
            self.destroy()
        except Exception:
            pass


# ─── Pet Daemon ───────────────────────────────────────────────────────────────

class PetDaemon:

    def __init__(self):
        os.makedirs(CAFE_DIR, exist_ok=True)

        self._pet_type      = self._load_pref()
        self._state         = "idle"
        self._frame         = 0
        self._idle_ticks    = 0
        self._walk_dir      = 1
        self._visible       = True
        self._current_itype = "drowsy"
        self._current_emotion = "neutral"
        self._ai_messages: dict = {}

        self._bubble: ThoughtBubble | None = None
        self._wellness_engine = None

        # Incarca engine DB si user_id din sesiunea activa
        self._engine  = None
        self._user_id = None
        self._load_db_session()

        self._root = tk.Tk()
        self._root.withdraw()

        self._setup_window()
        self._setup_canvas()
        self._load_position()
        self._setup_tray()
        self._write_lock()
        self._init_wellness()
        threading.Thread(
            target=self._poll_extension_auth,
            daemon=True,
        ).start()
        self._poll_ipc()
        self._animate()

    # ── Preferinte ────────────────────────────────────────────────────────────

    def _load_db_session(self):
        """Incarca engine DB si user_id din session.json."""
        try:
            from database import init_db
            import json
            session_file = os.path.join(
                CAFE_DIR, "session.json")
            self._engine = init_db()
            if os.path.exists(session_file):
                with open(session_file) as f:
                    data = json.load(f)
                self._user_id = data.get("user_id")
                print(f"[PET] Session incarcata: "
                      f"user_id={self._user_id}")
        except Exception as e:
            print(f"[PET] DB session err: {e}")

    def _load_pref(self) -> str:
        try:
            if os.path.exists(PREFS_FILE):
                with open(PREFS_FILE) as f:
                    v = f.read().strip()
                    return _resolve_pet(v)
        except Exception:
            pass
        return "cat"

    def _save_pref(self, pet_type: str):
        try:
            with open(PREFS_FILE, "w") as f:
                f.write(pet_type)
        except Exception:
            pass

    # ── Wellness Engine ───────────────────────────────────────────────────────

    def _init_wellness(self):
        try:
            from utils.wellness_engine import (
                WellnessEngine)
            self._wellness_engine = WellnessEngine(
                on_reminder=self._on_wellness_reminder)
            self._wellness_engine.start()
            print("[PET] Wellness Engine pornit.")
        except Exception as e:
            print(f"[PET] Wellness eroare: {e}")

    def _on_wellness_reminder(self, wtype):
        from utils.wellness_engine import WELLNESS_META
        meta  = WELLNESS_META[wtype]
        msg   = (f"{meta['icon']} {meta['titlu']}\n"
                 f"{meta['scurt']}\n"
                 f"Click pentru sesiune ghidată!")
        self._root.after(
            0,
            lambda w=wtype, m=msg:
            self._show_wellness_bubble(w, m))

    def _show_wellness_bubble(self, wtype, msg: str):
        if self._bubble:
            try:
                self._bubble._close()
            except Exception:
                pass
            self._bubble = None

        try:
            x = self._win.winfo_x()
            y = self._win.winfo_y()
            w = self._win.winfo_width()

            self._bubble = ThoughtBubble(
                self._root,
                message      = msg,
                pet_x        = x,
                pet_y        = y,
                pet_w        = w,
                timeout_ms   = 15000,
                on_open_chat = lambda:
                    self._root.after(
                        150,
                        lambda: self
                        ._start_wellness_session(
                            wtype)),
            )
        except Exception as e:
            print(f"[PET] Wellness bubble err: {e}")

    def _start_wellness_session(self, wtype):
        try:
            from components.wellness_popup import (
                WellnessPopup)
            # Reload user_id daca s-a schimbat sesiunea
            if not self._user_id:
                self._load_db_session()
            WellnessPopup(
                self._root,
                wtype    = wtype,
                pet_type = self._pet_type,
                engine   = self._engine,
                user_id  = self._user_id,
            )
            print(f"[PET] Sesiune: {wtype.value}")
        except Exception as e:
            print(f"[PET] Sesiune eroare: {e}")

    def _start_wellness_session_by_name(self, name: str):
        from utils.wellness_engine import WellnessType

        if name == "breathing":
            self._root.after(0, self._open_breathing_selector)
            return

        mapping = {
            "water":    WellnessType.WATER,
            "eyes":     WellnessType.EYES,
            "movement": WellnessType.MOVEMENT,
        }
        wtype = mapping.get(name)
        if wtype:
            self._start_wellness_session(wtype)

    def _open_breathing_selector(self):
        try:
            from components.breathing_selector import BreathingSelector
            BreathingSelector(
                self._root,
                current_emotion=self._current_emotion,
                pet_type=self._pet_type,
                on_select=self._start_breathing_session,
            )
            print("[PET] Selector respiratie deschis.")
        except Exception as e:
            print(f"[PET] Selector eroare: {e}")

    def _start_breathing_session(self, breathing_type: str):
        try:
            from components.breathing_popup import BreathingPopup
            BreathingPopup(
                self._root,
                breathing_type=breathing_type,
                pet_type=self._pet_type,
            )
            print(f"[PET] Respiratie: {breathing_type}")
        except Exception as e:
            print(f"[PET] Respiratie eroare: {e}")

    def _open_pomodoro(self):
        try:
            from components.pomodoro_widget import open_pomodoro
            open_pomodoro(
                self._root,
                pet_type=self._pet_type)
            print("[PET] Pomodoro deschis.")
        except Exception as e:
            print(f"[PET] Pomodoro eroare: {e}")

    def _poll_extension_auth(self):
        """Proceseaza cereri de autentificare de la extensia Chrome."""
        import json

        auth_req = os.path.join(
            CAFE_DIR, "ext_auth_request.json")

        while True:
            try:
                if os.path.exists(auth_req):
                    with open(auth_req,
                              encoding="utf-8") as f:
                        req = json.load(f)
                    os.remove(auth_req)

                    username = req.get(
                        "username", "")
                    print(f"[PET] Auth request: "
                          f"{username}")

                    with open(IPC_FILE, "w") as f:
                        f.write(
                            f"auth_request:"
                            f"{username}")
            except Exception:
                pass
            time.sleep(0.5)

    # ── Fereastra ─────────────────────────────────────────────────────────────

    def _setup_window(self):
        self._win = tk.Toplevel(self._root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.attributes(
            "-transparentcolor", "white")
        self._win.configure(bg="white")
        self._win.resizable(False, False)

        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        x  = sw - PET_SIZE - 20
        y  = sh - PET_SIZE - MARGIN_BOTTOM
        self._win.geometry(
            f"{PET_SIZE}x{PET_SIZE}+{x}+{y}")

        self._win.bind(
            "<ButtonPress-1>",   self._drag_start)
        self._win.bind(
            "<B1-Motion>",       self._drag_motion)
        self._win.bind(
            "<ButtonRelease-1>", self._drag_end)
        self._win.bind(
            "<Button-3>",        self._on_right_click)

        self._drag_x = 0
        self._drag_y = 0

    def _setup_canvas(self):
        self._canvas = tk.Canvas(
            self._win,
            width=PET_SIZE, height=PET_SIZE,
            bg="white", highlightthickness=0,
        )
        self._canvas.pack()

    def _load_position(self):
        try:
            if os.path.exists(POS_FILE):
                with open(POS_FILE) as f:
                    x, y = map(
                        int, f.read().strip().split(","))
                self._win.geometry(
                    f"{PET_SIZE}x{PET_SIZE}+{x}+{y}")
        except Exception:
            pass

    def _save_position(self):
        try:
            x = self._win.winfo_x()
            y = self._win.winfo_y()
            with open(POS_FILE, "w") as f:
                f.write(f"{x},{y}")
        except Exception:
            pass

    # ── Drag ──────────────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y
        self._state  = "idle"

    def _drag_motion(self, event):
        x = self._win.winfo_x() + \
            event.x - self._drag_x
        y = self._win.winfo_y() + \
            event.y - self._drag_y
        self._win.geometry(f"+{x}+{y}")
        if self._bubble:
            try:
                self._bubble._close()
                self._bubble = None
            except Exception:
                pass

    def _drag_end(self, event):
        self._save_position()

    # ── Click dreapta ─────────────────────────────────────────────────────────

    def _on_right_click(self, event):
        menu = tk.Menu(
            self._win, tearoff=0,
            bg="#2A2A2A", fg="white",
            activebackground="#4C8CE4",
            activeforeground="white",
            font=("Arial", 10),
        )
        menu.add_command(
            label="☕ Deschide Coffee & Axl",
            command=self._open_app)
        menu.add_separator()

        # Sesiuni wellness
        menu.add_command(
            label="💧 Reminder Apă",
            command=lambda: self._root.after(
                0, lambda:
                self._start_wellness_session_by_name(
                    "water")))
        menu.add_command(
            label="👁 Pauza Ochilor",
            command=lambda: self._root.after(
                0, lambda:
                self._start_wellness_session_by_name(
                    "eyes")))
        menu.add_command(
            label="🏃 Mișcare",
            command=lambda: self._root.after(
                0, lambda:
                self._start_wellness_session_by_name(
                    "movement")))
        menu.add_command(
            label="🌬 Respirație",
            command=lambda: self._root.after(
                0, lambda:
                self._start_wellness_session_by_name(
                    "breathing")))
        menu.add_command(
            label="🍅 Pomodoro",
            command=lambda: self._root.after(
                0, self._open_pomodoro))

        menu.add_separator()
        menu.add_command(
            label="🐱 Pisică",
            command=lambda: self._set_pet("coffee"))
        menu.add_command(
            label="🐶 Cățeluș",
            command=lambda: self._set_pet("axl"))
        menu.add_separator()
        menu.add_command(
            label="👁 Arată/Ascunde",
            command=self._toggle_visible)
        menu.add_separator()
        menu.add_command(
            label="✕ Închide",
            command=self._quit)

        try:
            menu.tk_popup(
                event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ── System Tray ───────────────────────────────────────────────────────────

    def _setup_tray(self):
        try:
            img = Image.new(
                "RGB", (64, 64), color="#406093")
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [16, 16, 48, 48], fill="#FFF799")

            menu = TrayMenu(
                TrayItem(
                    "☕ Deschide",
                    lambda i, it: self._open_app()),
                TrayItem(
                    "💧 Apă",
                    lambda i, it: self._root.after(
                        0, lambda:
                        self._start_wellness_session_by_name(
                            "water"))),
                TrayItem(
                    "👁 Ochi",
                    lambda i, it: self._root.after(
                        0, lambda:
                        self._start_wellness_session_by_name(
                            "eyes"))),
                TrayItem(
                    "🏃 Mișcare",
                    lambda i, it: self._root.after(
                        0, lambda:
                        self._start_wellness_session_by_name(
                            "movement"))),
                TrayItem(
                    "🌬 Respirație",
                    lambda i, it: self._root.after(
                        0, lambda:
                        self._start_wellness_session_by_name(
                            "breathing"))),
                TrayMenu.SEPARATOR,
                TrayItem(
                    "🐱 Pisică",
                    lambda i, it:
                    self._set_pet("coffee")),
                TrayItem(
                    "🐶 Cățeluș",
                    lambda i, it:
                    self._set_pet("axl")),
                TrayMenu.SEPARATOR,
                TrayItem(
                    "👁 Arată/Ascunde",
                    lambda i, it:
                    self._toggle_visible()),
                TrayMenu.SEPARATOR,
                TrayItem(
                    "✕ Închide",
                    lambda i, it: self._quit()),
            )

            self._tray = pystray.Icon(
                "CoffeeAxl", img,
                "Coffee & Axl", menu)

            threading.Thread(
                target=self._tray.run,
                daemon=True,
            ).start()

        except Exception as e:
            print(f"[PET] Tray eroare: {e}")

    # ── Actiuni ───────────────────────────────────────────────────────────────

    def _set_pet(self, pet_type: str):
        resolved = _resolve_pet(pet_type)
        self._pet_type = resolved
        self._save_pref(pet_type)   # salveaza originalul (axl/coffee)
        self._state = "idle"
        self._frame = 0
        # Redeseneaza imediat cu noul animal
        try:
            self._draw()
        except Exception:
            pass
        print(f"[PET] Schimbat la: {resolved} (din '{pet_type}')")

    def _toggle_visible(self):
        self._visible = not self._visible
        if self._visible:
            self._win.deiconify()
        else:
            self._win.withdraw()

    def _is_main_running(self) -> bool:
        """Verifica daca main.py ruleaza deja."""
        import ctypes
        app_lock = os.path.join(CAFE_DIR, "app.lock")
        if not os.path.exists(app_lock):
            return False
        try:
            with open(app_lock) as f:
                pid = int(f.read().strip())
            # Verifica daca procesul cu PID-ul respectiv exista
            handle = ctypes.windll.kernel32.OpenProcess(
                0x0400, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False

    def _launch_main_app(self):
        """Porneste main.py ca proces independent."""
        try:
            subprocess.Popen(
                [sys.executable, MAIN_SCRIPT],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print("[PET] main.py pornit.")
        except Exception as e:
            print(f"[PET] Eroare pornire app: {e}")

    def _open_app(self):
        """
        Deschide sau aduce in fata aplicatia Coffee & Axl.
        Daca nu ruleaza, o porneste automat.
        """
        try:
            if self._is_main_running():
                # Aplicatia ruleaza — trimite semnal de focus
                with open(FOCUS_FILE, "w") as f:
                    f.write("focus")
                print("[PET] Focus trimis la app.")
            else:
                # Aplicatia nu ruleaza — o pornim
                print("[PET] App nu ruleaza — o pornesc.")
                self._launch_main_app()
                # Asteapta 2s si trimite focus
                # ca sa se asigure ca fereastra apare
                def _focus_after_start():
                    time.sleep(2.5)
                    try:
                        with open(FOCUS_FILE, "w") as f:
                            f.write("focus")
                    except Exception:
                        pass
                threading.Thread(
                    target=_focus_after_start,
                    daemon=True).start()
        except Exception as e:
            print(f"[PET] _open_app err: {e}")

    def _open_app_chat(self):
        try:
            with open(FOCUS_FILE, "w") as f:
                f.write("open_chat")
            print("[PET] open_chat trimis.")
        except Exception as e:
            print(f"[PET] Eroare: {e}")

    def _quit(self):
        self._remove_lock()
        if self._wellness_engine:
            self._wellness_engine.stop()
        try:
            if self._tray:
                self._tray.stop()
        except Exception:
            pass
        self._root.quit()

    # ── Lock ──────────────────────────────────────────────────────────────────

    def _write_lock(self):
        try:
            with open(LOCK_FILE, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass

    def _remove_lock(self):
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass

    # ── IPC Polling ───────────────────────────────────────────────────────────

    def _poll_ipc(self):
        try:
            if os.path.exists(IPC_FILE):
                with open(IPC_FILE,
                          encoding="utf-8") as f:
                    cmd = f.read().strip()
                os.remove(IPC_FILE)

                if cmd == "wake_and_show":
                    self._visible = True
                    self._win.deiconify()
                    self._win.lift()

                elif cmd == "hide":
                    self._visible = False
                    self._win.withdraw()

                elif cmd == "show":
                    self._visible = True
                    self._win.deiconify()
                    self._win.lift()

                elif cmd.startswith("set_pet:"):
                    pet = cmd.split(":", 1)[1].strip()
                    resolved = _resolve_pet(pet)
                    if resolved in PETS:
                        self._root.after(0, lambda p=pet: self._set_pet(p))

                elif cmd.startswith(
                        "thought_bubble:"):
                    itype = cmd.split(
                        ":", 1)[1].strip()
                    self._current_emotion = itype
                    print(f"[PET] Thought bubble: "
                          f"{itype}")
                    self._root.after(
                        0,
                        lambda t=itype:
                        self.show_thought_bubble(t))

                elif cmd.startswith("ai_message:"):
                    parts = cmd.split(":", 2)
                    if len(parts) == 3:
                        _, itype, msg = parts
                        print(f"[PET] Mesaj AI: "
                              f"{itype}")
                        self._ai_messages[itype] = msg

                elif cmd.startswith("pomodoro_work:"):
                    session_n = cmd.split(
                        ":", 1)[1].strip()
                    msg = (f"🍅 Sesiunea "
                           f"{session_n} a început!\n"
                           f"Concentrează-te! 💪")
                    self._root.after(
                        0,
                        lambda m=msg:
                        self._show_simple_bubble(m))

                elif cmd.startswith(
                        "pomodoro_break:"):
                    btype = cmd.split(
                        ":", 1)[1].strip()
                    if btype == "long":
                        msg = ("🎉 Pauză lungă!\n"
                               "Ai muncit excelent!\n"
                               "Odihnește-te bine. 🌙")
                    else:
                        msg = ("☕ Pauză scurtă!\n"
                               "5 minute pentru tine.")
                    self._root.after(
                        0,
                        lambda m=msg:
                        self._show_simple_bubble(m))

                elif cmd.startswith(
                        "wellness_suggest:"):
                    wname = cmd.split(
                        ":", 1)[1].strip()
                    self._root.after(
                        0,
                        lambda n=wname:
                        self._start_wellness_session_by_name(
                            n))

                elif cmd.startswith(
                        "auth_request:"):
                    print(f"[PET] Auth request primit"
                          f" — procesat de main app.")

        except Exception:
            pass

        self._root.after(400, self._poll_ipc)

    # ── Thought Bubble emotii ─────────────────────────────────────────────────

    def show_thought_bubble(self,
                             itype: str = "drowsy"):
        self._current_itype = itype

        if self._bubble:
            try:
                self._bubble._close()
            except Exception:
                pass
            self._bubble = None

        animal_messages = BUBBLE_MESSAGES.get(
            self._pet_type,
            BUBBLE_MESSAGES["cat"])
        msg = animal_messages.get(
            itype,
            animal_messages.get("drowsy", ""))

        try:
            x = self._win.winfo_x()
            y = self._win.winfo_y()
            w = self._win.winfo_width()

            self._bubble = ThoughtBubble(
                self._root,
                message      = msg,
                pet_x        = x,
                pet_y        = y,
                pet_w        = w,
                timeout_ms   = 10000,
                on_open_chat = lambda:
                    self._root.after(
                        150,
                        lambda: self
                        ._show_wellness_popup(itype)),
            )
            print(f"[PET] Bula afisata: {itype}")
        except Exception as e:
            print(f"[PET] Bubble eroare: {e}")

    # ── Popup Wellness emotii ─────────────────────────────────────────────────

    def _show_wellness_popup(self, itype: str):
        meta = POPUP_META.get(
            itype, POPUP_META["drowsy"])

        ai_msg = self._ai_messages.get(itype, "")
        display_msg = ai_msg if ai_msg \
            else meta["mesaj"]

        popup = tk.Toplevel(self._root)
        popup.title("Axl Wellness")
        popup.geometry("340x260")
        popup.resizable(False, False)
        popup.configure(bg="#FFFDE7")
        popup.attributes("-topmost", True)

        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        x  = (sw - 340) // 2
        y  = (sh - 260) // 2
        popup.geometry(f"340x260+{x}+{y}")
        popup.lift()
        popup.focus_force()

        # Header
        header = tk.Frame(
            popup, bg="#F9A825", height=44)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text=f"  {meta['icon']}  Axl Wellness",
            font=("Arial", 12, "bold"),
            bg="#F9A825", fg="white",
            anchor="w",
        ).pack(side="left", padx=12)

        tk.Button(
            header, text="✕",
            font=("Arial", 10, "bold"),
            bg="#F9A825", fg="white",
            relief="flat", cursor="hand2",
            bd=0, command=popup.destroy,
        ).pack(side="right", padx=12)

        # Titlu
        tk.Label(
            popup,
            text=meta["titlu"],
            font=("Arial", 14, "bold"),
            bg="#FFFDE7", fg="#5D4037",
        ).pack(pady=(16, 6))

        # Mesaj AI sau default
        tk.Label(
            popup,
            text=display_msg,
            font=("Arial", 11),
            bg="#FFFDE7", fg="#7D5A3C",
            wraplength=300,
            justify="center",
        ).pack(pady=(0, 16))

        # Butoane
        btn_frame = tk.Frame(
            popup, bg="#FFFDE7")
        btn_frame.pack(
            fill="x", padx=20, pady=(0, 16))

        def _go_chat():
            popup.destroy()
            self._open_app_chat()

        chat_btn = tk.Button(
            btn_frame,
            text="💬  Deschide Chat Wellness",
            font=("Arial", 11, "bold"),
            bg="#4C8CE4", fg="white",
            relief="flat", cursor="hand2",
            pady=10, bd=0,
            command=_go_chat,
        )
        chat_btn.pack(fill="x", pady=(0, 6))
        chat_btn.bind(
            "<Enter>",
            lambda e: chat_btn.configure(
                bg="#3A7BD5"))
        chat_btn.bind(
            "<Leave>",
            lambda e: chat_btn.configure(
                bg="#4C8CE4"))

        close_btn = tk.Button(
            btn_frame,
            text="✕  Închide",
            font=("Arial", 10),
            bg="#E8E8E8", fg="#5D4037",
            relief="flat", cursor="hand2",
            pady=7, bd=0,
            command=popup.destroy,
        )
        close_btn.pack(fill="x")
        close_btn.bind(
            "<Enter>",
            lambda e: close_btn.configure(
                bg="#D0D0D0"))
        close_btn.bind(
            "<Leave>",
            lambda e: close_btn.configure(
                bg="#E8E8E8"))

    def _show_simple_bubble(self, msg: str):
        if self._bubble:
            try:
                self._bubble._close()
            except Exception:
                pass
            self._bubble = None

        try:
            x = self._win.winfo_x()
            y = self._win.winfo_y()
            w = self._win.winfo_width()

            self._bubble = ThoughtBubble(
                self._root,
                message    = msg,
                pet_x      = x,
                pet_y      = y,
                pet_w      = w,
                timeout_ms = 8000,
            )
        except Exception as e:
            print(f"[PET] Simple bubble err: {e}")

    # ── Animatie ──────────────────────────────────────────────────────────────

    def _animate(self):
        self._frame += 1

        if self._state == "idle":
            self._idle_ticks += 1
            if self._idle_ticks > \
                    IDLE_TIMEOUT * (
                    1000 // ANIM_INTERVAL):
                if random.random() < WALK_CHANCE:
                    self._state      = "walk"
                    self._walk_dir   = random.choice(
                        [-1, 1])
                    self._idle_ticks = 0
                elif random.random() < 0.15:
                    self._state      = "sleep"
                    self._idle_ticks = 0
                else:
                    self._idle_ticks = 0

        elif self._state == "walk":
            self._do_walk()
            if random.random() < 0.02:
                self._state = "idle"

        elif self._state == "sleep":
            if random.random() < 0.005:
                self._state = "idle"

        self._draw()
        self._root.after(ANIM_INTERVAL, self._animate)

    def _do_walk(self):
        x   = self._win.winfo_x()
        y   = self._win.winfo_y()
        sw  = self._win.winfo_screenwidth()
        spd = 3

        x += self._walk_dir * spd

        if x < 0:
            x              = 0
            self._walk_dir = 1
        elif x > sw - PET_SIZE:
            x              = sw - PET_SIZE
            self._walk_dir = -1

        self._win.geometry(f"+{x}+{y}")

    # ── Desenare ──────────────────────────────────────────────────────────────

    def _draw(self):
        self._canvas.delete("all")
        c = PETS[self._pet_type]

        if self._state == "sleep":
            self._draw_sleep(c)
        elif self._state == "walk":
            self._draw_walk(c)
        else:
            self._draw_idle(c)

    def _draw_idle(self, c: dict):
        f    = self._frame
        bob  = math.sin(f * 0.15) * 2
        base = 40 + bob

        if self._pet_type == "cat":
            self._draw_cat_idle(c, base)
        else:
            self._draw_dog_idle(c, base)

    def _draw_walk(self, c: dict):
        f    = self._frame
        bob  = math.sin(f * 0.4) * 3
        base = 42 + bob

        if self._pet_type == "cat":
            self._draw_cat_walk(c, base)
        else:
            self._draw_dog_walk(c, base)

    def _draw_sleep(self, c: dict):
        base = 44
        if self._pet_type == "cat":
            self._draw_cat_sleep(c, base)
        else:
            self._draw_dog_sleep(c, base)

    # ── Pisica ────────────────────────────────────────────────────────────────

    def _draw_cat_idle(self, c: dict, base: float):
        cv = self._canvas

        cv.create_arc(
            52, base - 10, 80, base + 20,
            start=20, extent=160,
            outline=c["detail"], width=3,
            style="arc")
        cv.create_oval(
            15, base - 10, 65, base + 28,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            22, base - 2, 58, base + 22,
            fill=c["belly"], outline="")
        cv.create_oval(
            18, base - 34, 62, base + 2,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            22, base - 32, 18, base - 50,
            30, base - 30,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            58, base - 32, 62, base - 50,
            50, base - 30,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            24, base - 33, 21, base - 46,
            30, base - 31,
            fill=c["nose"], outline="")
        cv.create_polygon(
            56, base - 33, 59, base - 46,
            50, base - 31,
            fill=c["nose"], outline="")
        cv.create_oval(
            27, base - 25, 35, base - 17,
            fill=c["eye"], outline="")
        cv.create_oval(
            45, base - 25, 53, base - 17,
            fill=c["eye"], outline="")
        cv.create_oval(
            29, base - 23, 33, base - 19,
            fill="black", outline="")
        cv.create_oval(
            47, base - 23, 51, base - 19,
            fill="black", outline="")
        cv.create_oval(
            30, base - 22, 32, base - 20,
            fill="white", outline="")
        cv.create_oval(
            48, base - 22, 50, base - 20,
            fill="white", outline="")
        cv.create_polygon(
            38, base - 14, 42, base - 14,
            40, base - 11,
            fill=c["nose"], outline="")
        cv.create_line(
            40, base - 11, 36, base - 8,
            fill=c["detail"], width=1)
        cv.create_line(
            40, base - 11, 44, base - 8,
            fill=c["detail"], width=1)
        for dy in [-13, -10]:
            cv.create_line(
                22, base + dy, 36,
                base + dy - 1,
                fill=c["detail"], width=1)
            cv.create_line(
                44, base + dy - 1, 58,
                base + dy,
                fill=c["detail"], width=1)
        cv.create_rectangle(
            20, base + 20, 30, base + 30,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_rectangle(
            50, base + 20, 60, base + 30,
            fill=c["body"],
            outline=c["detail"], width=1)

    def _draw_cat_walk(self, c: dict, base: float):
        f  = self._frame
        l1 = math.sin(f * 0.5) * 6
        l2 = math.cos(f * 0.5) * 6
        cv = self._canvas

        cv.create_oval(
            12, base - 10, 62, base + 25,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            15, base - 34, 55, base,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            19, base - 32, 15, base - 48,
            27, base - 28,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            51, base - 32, 55, base - 48,
            43, base - 28,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            22, base - 24, 30, base - 16,
            fill=c["eye"], outline="")
        cv.create_oval(
            40, base - 24, 48, base - 16,
            fill=c["eye"], outline="")
        cv.create_line(
            20, base + 24,
            20 + l1, base + 24 + abs(l1),
            fill=c["detail"], width=3,
            capstyle="round")
        cv.create_line(
            35, base + 24,
            35 + l2, base + 24 + abs(l2),
            fill=c["detail"], width=3,
            capstyle="round")
        cv.create_line(
            50, base + 24,
            50 + l1, base + 24 + abs(l1),
            fill=c["detail"], width=3,
            capstyle="round")
        tw = math.sin(f * 0.3) * 15
        cv.create_arc(
            50, base - 8, 78 + tw, base + 18,
            start=30, extent=140,
            outline=c["detail"], width=3,
            style="arc")

    def _draw_cat_sleep(self, c: dict, base: float):
        cv = self._canvas
        f  = self._frame

        cv.create_oval(
            10, base - 6, 70, base + 24,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            18, base - 22, 52, base + 2,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            22, base - 20, 18, base - 32,
            28, base - 18,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_polygon(
            48, base - 20, 52, base - 32,
            42, base - 18,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_line(
            26, base - 12, 32, base - 10,
            fill=c["detail"], width=2)
        cv.create_line(
            38, base - 10, 44, base - 12,
            fill=c["detail"], width=2)
        z_y = base - 30 + math.sin(f * 0.1) * 3
        cv.create_text(
            58, z_y, text="z",
            font=("Arial", 10, "bold"),
            fill=c["detail"])
        cv.create_text(
            64, z_y - 8, text="z",
            font=("Arial", 8, "bold"),
            fill=c["detail"])
        cv.create_text(
            68, z_y - 16, text="Z",
            font=("Arial", 12, "bold"),
            fill=c["detail"])

    # ── Catelus ───────────────────────────────────────────────────────────────

    def _draw_dog_idle(self, c: dict, base: float):
        cv = self._canvas

        cv.create_oval(
            12, base - 8, 68, base + 28,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            20, base, 60, base + 24,
            fill=c["belly"], outline="")
        cv.create_oval(
            16, base - 34, 64, base + 4,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            8, base - 28, 26, base + 4,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            54, base - 28, 72, base + 4,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            25, base - 22, 34, base - 13,
            fill=c["eye"], outline="")
        cv.create_oval(
            46, base - 22, 55, base - 13,
            fill=c["eye"], outline="")
        cv.create_oval(
            27, base - 20, 32, base - 15,
            fill="black", outline="")
        cv.create_oval(
            48, base - 20, 53, base - 15,
            fill="black", outline="")
        cv.create_oval(
            28, base - 19, 30, base - 17,
            fill="white", outline="")
        cv.create_oval(
            49, base - 19, 51, base - 17,
            fill="white", outline="")
        cv.create_oval(
            35, base - 10, 45, base - 4,
            fill=c["nose"], outline="")
        cv.create_arc(
            32, base - 8, 48, base + 2,
            start=200, extent=140,
            outline=c["detail"], width=1,
            style="arc")
        cv.create_arc(
            60, base - 14, 80, base + 10,
            start=20, extent=160,
            outline=c["detail"], width=3,
            style="arc")
        for px in [18, 34, 46, 60]:
            cv.create_rectangle(
                px, base + 20,
                px + 10, base + 30,
                fill=c["body"],
                outline=c["detail"], width=1)

    def _draw_dog_walk(self, c: dict, base: float):
        f  = self._frame
        l1 = math.sin(f * 0.5) * 7
        l2 = math.cos(f * 0.5) * 7
        cv = self._canvas

        cv.create_oval(
            10, base - 8, 66, base + 24,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            14, base - 32, 58, base + 2,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            6, base - 26, 22, base + 2,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            50, base - 26, 66, base + 2,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            22, base - 22, 31, base - 13,
            fill=c["eye"], outline="")
        cv.create_oval(
            43, base - 22, 52, base - 13,
            fill=c["eye"], outline="")
        cv.create_oval(
            33, base - 10, 41, base - 4,
            fill=c["nose"], outline="")
        for px, phase in [
            (16, l1), (30, l2),
            (44, l1), (56, l2)
        ]:
            cv.create_line(
                px + 5, base + 22,
                px + 5 + phase * 0.3,
                base + 22 + abs(phase),
                fill=c["detail"], width=3,
                capstyle="round")
        tw = math.sin(f * 0.6) * 12
        cv.create_arc(
            58, base - 12,
            80 + tw, base + 8,
            start=10, extent=160,
            outline=c["detail"], width=3,
            style="arc")

    def _draw_dog_sleep(self, c: dict, base: float):
        cv = self._canvas
        f  = self._frame

        cv.create_oval(
            8, base - 4, 72, base + 26,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            16, base - 20, 54, base + 4,
            fill=c["body"],
            outline=c["detail"], width=1)
        cv.create_oval(
            6, base - 16, 20, base + 4,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_oval(
            50, base - 16, 64, base + 4,
            fill=c["detail"],
            outline=c["detail"], width=1)
        cv.create_line(
            23, base - 10, 30, base - 8,
            fill=c["detail"], width=2)
        cv.create_line(
            36, base - 8, 43, base - 10,
            fill=c["detail"], width=2)
        z_y = base - 28 + math.sin(f * 0.1) * 3
        cv.create_text(
            56, z_y, text="z",
            font=("Arial", 10, "bold"),
            fill=c["detail"])
        cv.create_text(
            62, z_y - 8, text="z",
            font=("Arial", 8, "bold"),
            fill=c["detail"])
        cv.create_text(
            66, z_y - 16, text="Z",
            font=("Arial", 12, "bold"),
            fill=c["detail"])

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self):
        try:
            self._root.mainloop()
        finally:
            self._remove_lock()
            self._save_position()


# ─── Entry point ──────────────────────────────────────────────────────────────

def _check_already_running() -> bool:
    if not os.path.exists(LOCK_FILE):
        return False
    try:
        with open(LOCK_FILE) as f:
            pid = int(f.read().strip())
        import ctypes
        handle = ctypes.windll.kernel32\
            .OpenProcess(0x0400, False, pid)
        if handle:
            ctypes.windll.kernel32\
                .CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    os.makedirs(CAFE_DIR, exist_ok=True)

    if _check_already_running():
        print("[PET] Deja rulează.")
        sys.exit(0)

    daemon = PetDaemon()
    daemon.run()