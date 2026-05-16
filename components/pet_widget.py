import tkinter as tk
import customtkinter as ctk
import math
import random
import time
import os
from PIL import Image, ImageTk
from utils.theme import NAVY, BLUE, YELLOW, GREEN, WHITE, TEXT_LIGHT, ERROR_RED


# ─── Constante ────────────────────────────────────────────────────────────────

PET_SIZE        = 80      # dimensiunea ferestrei pet
MARGIN_RIGHT    = 24
MARGIN_BOTTOM   = 48
ANIM_INTERVAL   = 120     # ms intre frame-uri
IDLE_TIMEOUT    = 8       # secunde pana incepe sa doarma
WALK_CHANCE     = 0.3     # probabilitate sa inceapa sa mearga la fiecare ciclu


# ─── Culori animal ────────────────────────────────────────────────────────────

PETS = {
    "cat": {
        "name":       "Pisică",
        "body":       "#F4A460",   # portocaliu nisip
        "belly":      "#FFF8F0",
        "detail":     "#8B6340",
        "eye":        "#2E8B57",
        "nose":       "#FF8FAB",
    },
    "dog": {
        "name":       "Cățeluș",
        "body":       "#C8A882",   # bej cald
        "belly":      "#F5ECD7",
        "detail":     "#8B6340",
        "eye":        "#4A3728",
        "nose":       "#2C2C2C",
    },
}


# ─── Renderer canvas ──────────────────────────────────────────────────────────

class PetCanvas(tk.Canvas):
    """
    Canvas care deseneaza animalul din forme geometrice simple.
    Cand vei avea sprite-uri PNG, inlocuiesti metodele _draw_* cu
    self.create_image(PET_SIZE//2, PET_SIZE//2, image=self._frame_img)
    """

    def __init__(self, parent, pet_type: str):
        super().__init__(
            parent,
            width=PET_SIZE,
            height=PET_SIZE,
            bg="white",
            highlightthickness=0,
            bd=0,
        )
        self.pet_type  = pet_type
        self.colors    = PETS[pet_type]
        self._frame    = 0
        self._anim     = "idle"
        self._blink    = False
        self._tail_ang = 0
        self._draw()

    def set_anim(self, anim: str, frame: int, extra: dict = None):
        self._anim  = anim
        self._frame = frame
        if extra:
            self._blink    = extra.get("blink", False)
            self._tail_ang = extra.get("tail_ang", 0)
        self._draw()

    def _draw(self):
        self.delete("all")
        if self.pet_type == "cat":
            self._draw_cat()
        else:
            self._draw_dog()

    # ── Pisica ────────────────────────────────────────────────────────────────

    def _draw_cat(self):
        c  = self.colors
        cx = PET_SIZE // 2
        anim = self._anim

        if anim == "sleep":
            self._cat_sleep(c, cx)
        elif anim == "walk":
            self._cat_walk(c, cx)
        else:
            self._cat_idle(c, cx)

    def _cat_idle(self, c, cx):
        bob = math.sin(self._frame * 0.4) * 2   # miscare verticala subtila

        # Coada
        ang = self._tail_ang
        tx  = cx + 22 + math.sin(math.radians(ang)) * 10
        ty  = 58 + bob + math.cos(math.radians(ang)) * 6
        self.create_line(cx + 16, 62 + bob, tx, ty,
                         fill=c["body"], width=5, smooth=True, capstyle="round")
        self.create_oval(tx - 4, ty - 4, tx + 4, ty + 4, fill=c["body"], outline="")

        # Corp
        self.create_oval(cx - 20, 36 + bob, cx + 20, 72 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        # Burta
        self.create_oval(cx - 11, 44 + bob, cx + 11, 68 + bob,
                         fill=c["belly"], outline="")

        # Cap
        self.create_oval(cx - 18, 12 + bob, cx + 18, 42 + bob,
                         fill=c["body"], outline=c["detail"], width=1)

        # Urechi
        self.create_polygon(cx - 18, 20 + bob, cx - 10, 4 + bob, cx - 4, 18 + bob,
                            fill=c["body"], outline=c["detail"], width=1)
        self.create_polygon(cx + 4, 18 + bob, cx + 10, 4 + bob, cx + 18, 20 + bob,
                            fill=c["body"], outline=c["detail"], width=1)
        # Interior urechi
        self.create_polygon(cx - 15, 19 + bob, cx - 10, 9 + bob, cx - 6, 19 + bob,
                            fill=c["nose"], outline="")
        self.create_polygon(cx + 6, 19 + bob, cx + 10, 9 + bob, cx + 15, 19 + bob,
                            fill=c["nose"], outline="")

        # Ochi
        if self._blink:
            self.create_line(cx - 9, 26 + bob, cx - 4, 26 + bob,
                             fill=c["detail"], width=2, capstyle="round")
            self.create_line(cx + 4, 26 + bob, cx + 9, 26 + bob,
                             fill=c["detail"], width=2, capstyle="round")
        else:
            self.create_oval(cx - 10, 22 + bob, cx - 4, 30 + bob,
                             fill=c["eye"], outline="")
            self.create_oval(cx + 4, 22 + bob, cx + 10, 30 + bob,
                             fill=c["eye"], outline="")
            self.create_oval(cx - 8, 24 + bob, cx - 6, 28 + bob,
                             fill="#111", outline="")
            self.create_oval(cx + 6, 24 + bob, cx + 8, 28 + bob,
                             fill="#111", outline="")

        # Nas + gura
        self.create_oval(cx - 3, 31 + bob, cx + 3, 36 + bob,
                         fill=c["nose"], outline="")
        self.create_line(cx, 36 + bob, cx - 5, 40 + bob,
                         fill=c["detail"], width=1, smooth=True)
        self.create_line(cx, 36 + bob, cx + 5, 40 + bob,
                         fill=c["detail"], width=1, smooth=True)

        # Mustati
        self.create_line(cx - 16, 34 + bob, cx - 4, 33 + bob,
                         fill=c["detail"], width=1)
        self.create_line(cx + 4, 33 + bob, cx + 16, 34 + bob,
                         fill=c["detail"], width=1)

    def _cat_walk(self, c, cx):
        f   = self._frame % 4
        bob = [0, -3, 0, 3][f]
        leg_offsets = [(0, 0), (6, -4), (0, 0), (-6, -4)][f]

        # Corp
        self.create_oval(cx - 20, 36 + bob, cx + 20, 68 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        # Picioare
        for ox, oy in [(-10, 0), (10, 0)]:
            self.create_oval(cx + ox - 4, 64 + bob + oy + leg_offsets[1],
                             cx + ox + 4, 76 + bob + oy,
                             fill=c["body"], outline="")
        # Cap
        self.create_oval(cx - 16, 16 + bob, cx + 16, 40 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        # Urechi mici
        self.create_polygon(cx - 16, 22 + bob, cx - 9, 8 + bob, cx - 4, 20 + bob,
                            fill=c["body"], outline=c["detail"], width=1)
        self.create_polygon(cx + 4, 20 + bob, cx + 9, 8 + bob, cx + 16, 22 + bob,
                            fill=c["body"], outline=c["detail"], width=1)
        # Ochi
        self.create_oval(cx - 9, 22 + bob, cx - 4, 28 + bob,
                         fill=c["eye"], outline="")
        self.create_oval(cx + 4, 22 + bob, cx + 9, 28 + bob,
                         fill=c["eye"], outline="")
        # Coada animata
        self.create_line(cx + 18, 54 + bob, cx + 28, 44 + bob + leg_offsets[0],
                         fill=c["body"], width=5, smooth=True, capstyle="round")

    def _cat_sleep(self, c, cx):
        breath = math.sin(self._frame * 0.15) * 1.5

        # Corp ghemuit
        self.create_oval(cx - 24, 44, cx + 24, 72 + breath,
                         fill=c["body"], outline=c["detail"], width=1)
        # Coada inconjuratoare
        self.create_arc(cx - 22, 48, cx + 22, 74,
                        start=0, extent=200,
                        outline=c["body"], width=6, style="arc")
        # Cap
        self.create_oval(cx - 16, 30, cx + 16, 54,
                         fill=c["body"], outline=c["detail"], width=1)
        # Urechi
        self.create_polygon(cx - 16, 36, cx - 9, 22, cx - 4, 34,
                            fill=c["body"], outline=c["detail"], width=1)
        self.create_polygon(cx + 4, 34, cx + 9, 22, cx + 16, 36,
                            fill=c["body"], outline=c["detail"], width=1)
        # Ochi inchisi (linie curba)
        self.create_line(cx - 9, 40, cx - 4, 43, cx + 1, 40,
                         fill=c["detail"], width=2, smooth=True)
        self.create_line(cx - 1, 40, cx + 4, 43, cx + 9, 40,
                         fill=c["detail"], width=2, smooth=True)
        # ZZZ
        z_alpha = int(abs(math.sin(self._frame * 0.1)) * 200)
        self.create_text(cx + 20, 22, text="z", font=("Arial", 8, "bold"),
                         fill=f"#{z_alpha:02x}{z_alpha:02x}ff")
        self.create_text(cx + 27, 14, text="z", font=("Arial", 10, "bold"),
                         fill=f"#{z_alpha:02x}{z_alpha:02x}ff")

    # ── Catel ─────────────────────────────────────────────────────────────────

    def _draw_dog(self):
        c    = self.colors
        cx   = PET_SIZE // 2
        anim = self._anim

        if anim == "sleep":
            self._dog_sleep(c, cx)
        elif anim == "walk":
            self._dog_walk(c, cx)
        else:
            self._dog_idle(c, cx)

    def _dog_idle(self, c, cx):
        bob = math.sin(self._frame * 0.4) * 2
        wag = math.sin(self._frame * 0.6) * 12   # coada waggle

        # Coada
        self.create_line(cx + 16, 58 + bob,
                         cx + 26 + math.sin(math.radians(wag)) * 8,
                         48 + bob + math.cos(math.radians(wag)) * 4,
                         fill=c["body"], width=6, capstyle="round")

        # Corp
        self.create_oval(cx - 22, 36 + bob, cx + 22, 70 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        self.create_oval(cx - 12, 46 + bob, cx + 12, 66 + bob,
                         fill=c["belly"], outline="")

        # Cap
        self.create_oval(cx - 18, 10 + bob, cx + 18, 40 + bob,
                         fill=c["body"], outline=c["detail"], width=1)

        # Urechi cazute
        self.create_oval(cx - 26, 14 + bob, cx - 10, 36 + bob,
                         fill=c["detail"], outline="")
        self.create_oval(cx + 10, 14 + bob, cx + 26, 36 + bob,
                         fill=c["detail"], outline="")

        # Bot
        self.create_oval(cx - 10, 28 + bob, cx + 10, 42 + bob,
                         fill=c["belly"], outline=c["detail"], width=1)

        # Nas
        self.create_oval(cx - 5, 28 + bob, cx + 5, 34 + bob,
                         fill=c["nose"], outline="")

        # Ochi
        if self._blink:
            self.create_line(cx - 9, 22 + bob, cx - 4, 22 + bob,
                             fill=c["detail"], width=2, capstyle="round")
            self.create_line(cx + 4, 22 + bob, cx + 9, 22 + bob,
                             fill=c["detail"], width=2, capstyle="round")
        else:
            self.create_oval(cx - 10, 18 + bob, cx - 4, 26 + bob,
                             fill=c["eye"], outline="")
            self.create_oval(cx + 4, 18 + bob, cx + 10, 26 + bob,
                             fill=c["eye"], outline="")
            self.create_oval(cx - 8, 20 + bob, cx - 6, 24 + bob,
                             fill="white", outline="")
            self.create_oval(cx + 6, 20 + bob, cx + 8, 24 + bob,
                             fill="white", outline="")

        # Gura fericita
        self.create_arc(cx - 6, 34 + bob, cx + 6, 42 + bob,
                        start=200, extent=140,
                        outline=c["detail"], width=2, style="arc")

    def _dog_walk(self, c, cx):
        f   = self._frame % 4
        bob = [0, -3, 0, 3][f]

        self.create_oval(cx - 22, 38 + bob, cx + 22, 68 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        for ox in [-10, 10]:
            leg_y = 66 + bob + ([0, -4, 0, 4][f] * (1 if ox > 0 else -1))
            self.create_oval(cx + ox - 5, leg_y, cx + ox + 5, leg_y + 12,
                             fill=c["body"], outline="")

        self.create_oval(cx - 16, 14 + bob, cx + 16, 40 + bob,
                         fill=c["body"], outline=c["detail"], width=1)
        self.create_oval(cx - 22, 16 + bob, cx - 8, 34 + bob,
                         fill=c["detail"], outline="")
        self.create_oval(cx + 8, 16 + bob, cx + 22, 34 + bob,
                         fill=c["detail"], outline="")
        self.create_oval(cx - 8, 28 + bob, cx + 8, 40 + bob,
                         fill=c["belly"], outline=c["detail"], width=1)
        self.create_oval(cx - 4, 28 + bob, cx + 4, 34 + bob,
                         fill=c["nose"], outline="")
        self.create_oval(cx - 8, 20 + bob, cx - 4, 26 + bob,
                         fill=c["eye"], outline="")
        self.create_oval(cx + 4, 20 + bob, cx + 8, 26 + bob,
                         fill=c["eye"], outline="")

    def _dog_sleep(self, c, cx):
        breath = math.sin(self._frame * 0.12) * 1.5

        self.create_oval(cx - 26, 46, cx + 26, 72 + breath,
                         fill=c["body"], outline=c["detail"], width=1)
        self.create_oval(cx - 16, 30, cx + 16, 54,
                         fill=c["body"], outline=c["detail"], width=1)
        self.create_oval(cx - 22, 32, cx - 8, 50,
                         fill=c["detail"], outline="")
        self.create_oval(cx + 8, 32, cx + 22, 50,
                         fill=c["detail"], outline="")
        self.create_oval(cx - 8, 40, cx + 8, 52,
                         fill=c["belly"], outline=c["detail"], width=1)
        self.create_line(cx - 8, 40, cx - 4, 44, cx + 1, 40,
                         fill=c["detail"], width=2, smooth=True)
        self.create_line(cx - 1, 40, cx + 4, 44, cx + 8, 40,
                         fill=c["detail"], width=2, smooth=True)

        z_alpha = int(abs(math.sin(self._frame * 0.1)) * 200)
        self.create_text(cx + 22, 22, text="z", font=("Arial", 8, "bold"),
                         fill=f"#{z_alpha:02x}{z_alpha:02x}ff")
        self.create_text(cx + 30, 13, text="z", font=("Arial", 10, "bold"),
                         fill=f"#{z_alpha:02x}{z_alpha:02x}ff")


# ─── Fereastra pet (overlay) ──────────────────────────────────────────────────

class PetWindow(tk.Toplevel):
    """
    Fereastra transparenta always-on-top care gazduieste animalul.
    Nu are bara de titlu, nu blocheaza click-urile pe aplicatie.
    """

    def __init__(self, pet_type: str, on_change: callable):
        super().__init__()
        self.pet_type  = pet_type
        self.on_change = on_change

        self._anim        = "idle"
        self._frame       = 0
        self._last_active = time.time()
        self._walk_dir    = 1       # 1 = dreapta, -1 = stanga
        self._walk_steps  = 0
        self._blink_timer = 0
        self._tail_timer  = 0
        self._tail_ang    = 0
        self._is_dragging = False
        self._drag_x      = 0
        self._drag_y      = 0

        self._setup_window()
        self._build_ui()
        self._position()
        self._tick()

    def _setup_window(self):
        self.overrideredirect(True)          # fara bara titlu
        self.wm_attributes("-topmost", True) # peste toate ferestrele
        self.wm_attributes("-transparentcolor", "white")  # fundal transparent
        self.configure(bg="white")
        self.resizable(False, False)

    def _build_ui(self):
        # Canvas principal
        self.canvas = PetCanvas(self, self.pet_type)
        self.canvas.pack()

        # Tooltip la hover
        self._tooltip_var = tk.StringVar(value="")
        self._tooltip = tk.Label(
            self,
            textvariable=self._tooltip_var,
            bg="#FFFDE7",
            fg="#406093",
            font=("Arial", 9),
            padx=6, pady=2,
            relief="flat",
            bd=0,
        )

        # Meniu context la click dreapta
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(
            label="🐱 Pisică",
            command=lambda: self.on_change("cat"),
        )
        self._menu.add_command(
            label="🐶 Cățeluș",
            command=lambda: self.on_change("dog"),
        )
        self._menu.add_separator()
        self._menu.add_command(
            label="😴 Pune la somn",
            command=self._force_sleep,
        )
        self._menu.add_command(
            label="🙈 Ascunde",
            command=self.withdraw,
        )

        # Bindings
        self.canvas.bind("<Button-1>",        self._on_click)
        self.canvas.bind("<Button-3>",        self._show_menu)
        self.canvas.bind("<ButtonPress-1>",   self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonRelease-1>", self._drag_end)
        self.canvas.bind("<Enter>",           self._on_hover)
        self.canvas.bind("<Leave>",           self._on_leave)

    def _position(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = sw - PET_SIZE - MARGIN_RIGHT
        y  = sh - PET_SIZE - MARGIN_BOTTOM
        self.geometry(f"{PET_SIZE}x{PET_SIZE}+{x}+{y}")

    # ── Animatie ──────────────────────────────────────────────────────────────

    def _tick(self):
        if not self.winfo_exists():
            return

        self._frame      += 1
        self._blink_timer += 1
        self._tail_timer  += 1

        # Blink aleatoriu
        blink = (self._blink_timer > 40 and self._blink_timer < 43)
        if self._blink_timer > random.randint(45, 90):
            self._blink_timer = 0

        # Miscare coada
        self._tail_ang = math.sin(self._tail_timer * 0.08) * 30

        # Tranzitii stare
        idle_time = time.time() - self._last_active
        if self._anim != "sleep" and idle_time > IDLE_TIMEOUT:
            self._anim      = "sleep"
            self._walk_steps = 0

        elif self._anim == "idle" and not self._is_dragging:
            if random.random() < WALK_CHANCE / 60:
                self._anim       = "walk"
                self._walk_steps = random.randint(30, 80)
                self._walk_dir   = random.choice([-1, 1])

        elif self._anim == "walk":
            self._do_walk()

        # Redeseneaza
        self.canvas.set_anim(
            self._anim,
            self._frame,
            {"blink": blink, "tail_ang": self._tail_ang},
        )

        self.after(ANIM_INTERVAL, self._tick)

    def _do_walk(self):
        if self._walk_steps <= 0:
            self._anim = "idle"
            return

        self._walk_steps -= 1
        x = self.winfo_x() + self._walk_dir * 2
        y = self.winfo_y()

        # Marginile ecranului
        sw = self.winfo_screenwidth()
        if x < 0:
            x = 0
            self._walk_dir = 1
        elif x > sw - PET_SIZE:
            x = sw - PET_SIZE
            self._walk_dir = -1

        self.geometry(f"+{x}+{y}")

    def _force_sleep(self):
        self._anim        = "sleep"
        self._walk_steps  = 0
        self._last_active = time.time() - IDLE_TIMEOUT - 1

    # ── Interactiune ──────────────────────────────────────────────────────────

    def _on_click(self, event):
        if self._is_dragging:
            return
        self._last_active = time.time()
        if self._anim == "sleep":
            self._anim = "idle"
            self._show_tooltip("Bună dimineața! ☕")
        else:
            self._anim = "idle"
            msgs = [
                "Mă bucur că ești aici! 🐾",
                "Hai să facem ceva bun azi! ✨",
                "Te simți bine? ☕",
                "Sunt aici dacă ai nevoie! 💙",
            ]
            self._show_tooltip(random.choice(msgs))

    def _show_menu(self, event):
        self._menu.tk_popup(event.x_root, event.y_root)

    def _on_hover(self, event):
        name = PETS[self.pet_type]["name"]
        self._show_tooltip(f"{name} · Click dreapta pentru opțiuni")

    def _on_leave(self, event):
        self._tooltip.place_forget()

    def _show_tooltip(self, text: str):
        self._tooltip_var.set(text)
        self._tooltip.place(x=0, y=-24)
        self.after(2500, lambda: self._tooltip.place_forget())

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, event):
        self._drag_x     = event.x_root - self.winfo_x()
        self._drag_y     = event.y_root - self.winfo_y()
        self._is_dragging = False

    def _drag_move(self, event):
        self._is_dragging = True
        self._last_active = time.time()
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    def _drag_end(self, event):
        self.after(100, lambda: setattr(self, "_is_dragging", False))

    # ── Public ────────────────────────────────────────────────────────────────

    def change_pet(self, pet_type: str):
        self.pet_type          = pet_type
        self.canvas.pet_type   = pet_type
        self.canvas.colors     = PETS[pet_type]
        self._anim             = "idle"
        self._last_active      = time.time()

    def notify_activity(self):
        """Apeleaza din exterior cand utilizatorul e activ (tastatura, click)."""
        self._last_active = time.time()
        if self._anim == "sleep":
            self._anim = "idle"


# ─── Dialog alegere animal (prima conectare) ──────────────────────────────────

class PetChoiceDialog(ctk.CTkToplevel):
    """
    Dialog modal care apare la prima conectare.
    Returneaza tipul ales prin callback on_choose(pet_type).
    """

    def __init__(self, parent, on_choose: callable):
        super().__init__(parent)
        self.on_choose = on_choose
        self.title("")
        self.resizable(False, False)
        self.grab_set()
        self._center(parent)
        self._build()

    def _center(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        w, h = 380, 300
        x = px + (pw - w) // 2
        y = py + (ph - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        from utils.theme import NAVY, BLUE, WHITE, OFF_WHITE, TEXT_DARK, TEXT_LIGHT
        from utils.theme import GRAY_LIGHT, CORNER_RADIUS

        self.configure(fg_color=OFF_WHITE)

        ctk.CTkLabel(
            self,
            text="Alege-ți companionul! 🐾",
            font=("Georgia", 18, "bold"),
            text_color=NAVY,
        ).pack(pady=(28, 4))

        ctk.CTkLabel(
            self,
            text="Va fi mereu cu tine în colțul ecranului.",
            font=("Arial", 12),
            text_color=TEXT_LIGHT,
        ).pack(pady=(0, 24))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()

        for pet_type, label, emoji, color in [
            ("cat", "Pisică",   "🐱", "#F4A460"),
            ("dog", "Cățeluș",  "🐶", "#C8A882"),
        ]:
            card = ctk.CTkFrame(
                row,
                fg_color=WHITE,
                corner_radius=16,
                border_width=2,
                border_color=GRAY_LIGHT,
                width=140, height=140,
            )
            card.pack(side="left", padx=12)
            card.pack_propagate(False)

            ctk.CTkLabel(card, text=emoji,
                         font=("Arial", 48)).pack(pady=(16, 4))
            ctk.CTkLabel(card, text=label,
                         font=("Arial", 13, "bold"),
                         text_color=NAVY).pack()

            card.bind("<Button-1>", lambda e, pt=pet_type: self._choose(pt))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, pt=pet_type: self._choose(pt))

            # Hover effect
            card.bind("<Enter>", lambda e, c=card, col=color: c.configure(border_color=col))
            card.bind("<Leave>", lambda e, c=card: c.configure(border_color=GRAY_LIGHT))

        ctk.CTkLabel(
            self,
            text="Poți schimba oricând din Setări sau click dreapta pe animal.",
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
            wraplength=340,
        ).pack(pady=(20, 0))

    def _choose(self, pet_type: str):
        self.on_choose(pet_type)
        self.destroy()