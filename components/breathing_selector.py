"""
Coffee & Axl - Breathing Selector
Popup cu recomandare automata per emotie +
optiune de a schimba tipul de respiratie.
"""

import tkinter as tk
from utils.wellness_engine import (
    BREATHING_META, EMOTION_TO_BREATHING)


class BreathingSelector(tk.Toplevel):
    """
    Popup care arata recomandarea de respiratie
    bazata pe starea emotionala curenta,
    cu optiunea de a selecta alta.
    """

    def __init__(self, root,
                 current_emotion: str = "neutral",
                 pet_type: str = "cat",
                 on_select: callable = None):
        super().__init__(root)

        self._on_select    = on_select
        self._pet_type     = pet_type
        self._emotion      = current_emotion
        self._selected     = EMOTION_TO_BREATHING.get(
            current_emotion, "constienta")

        self.title("Axl — Exercițiu de respirație")
        self.geometry("420x580")
        self.resizable(False, False)
        self.configure(bg="#F3E5F5")
        self.attributes("-topmost", True)
        self.protocol(
            "WM_DELETE_WINDOW", self.destroy)

        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 420) // 2
        y  = (sh - 580) // 2
        self.geometry(f"420x580+{x}+{y}")
        self.lift()
        self.focus_force()

        self._build()

    def _build(self):
        # Header
        header = tk.Frame(
            self, bg="#7B1FA2", height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🌬  Exercițiu de Respirație",
            font=("Georgia", 13, "bold"),
            bg="#7B1FA2", fg="white",
            anchor="w",
        ).pack(side="left", padx=16, pady=14)

        tk.Button(
            header, text="✕",
            font=("Arial", 11, "bold"),
            bg="#7B1FA2", fg="white",
            relief="flat", cursor="hand2",
            bd=0, command=self.destroy,
        ).pack(side="right", padx=16)

        # Recomandare automata
        rec_meta = BREATHING_META[self._selected]
        rec_frame = tk.Frame(
            self, bg=rec_meta["culoare"],
            relief="flat")
        rec_frame.pack(
            fill="x", padx=16, pady=(12, 4))

        tk.Label(
            rec_frame,
            text="✦  Recomandat pentru starea ta",
            font=("Arial", 10, "bold"),
            bg=rec_meta["culoare"],
            fg=rec_meta["btn_color"],
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(8, 2))

        tk.Label(
            rec_frame,
            text=f"{rec_meta['icon']}  "
                 f"{rec_meta['nume']}",
            font=("Arial", 13, "bold"),
            bg=rec_meta["culoare"],
            fg="#1A1A1A",
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 2))

        tk.Label(
            rec_frame,
            text=rec_meta["descriere"],
            font=("Arial", 10),
            bg=rec_meta["culoare"],
            fg="#5D4037",
            wraplength=360,
            justify="left",
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 4))

        tk.Label(
            rec_frame,
            text=f"🕐 {rec_meta['cand']}",
            font=("Arial", 9, "italic"),
            bg=rec_meta["culoare"],
            fg="#888",
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Buton Start recomandat
        start_btn = tk.Button(
            rec_frame,
            text=f"▶  Începe — {rec_meta['nume']}",
            font=("Arial", 11, "bold"),
            bg=rec_meta["btn_color"],
            fg="white",
            relief="flat", cursor="hand2",
            pady=10, bd=0,
            command=lambda t=self._selected:
            self._start(t),
        )
        start_btn.pack(
            fill="x", padx=12, pady=(0, 12))
        start_btn.bind(
            "<Enter>",
            lambda e, b=start_btn,
            c=rec_meta["btn_color"]:
            b.configure(bg=self._darken(c)))
        start_btn.bind(
            "<Leave>",
            lambda e, b=start_btn,
            c=rec_meta["btn_color"]:
            b.configure(bg=c))

        # Separator
        tk.Label(
            self,
            text="sau alege alt exercițiu:",
            font=("Arial", 10),
            bg="#F3E5F5", fg="#888",
        ).pack(pady=(4, 4))

        # Scroll cu toate optiunile
        list_frame = tk.Frame(
            self, bg="#F3E5F5")
        list_frame.pack(
            fill="both", expand=True,
            padx=16, pady=(0, 16))

        for key, meta in BREATHING_META.items():
            if key == self._selected:
                continue
            self._build_option(
                list_frame, key, meta)

    def _build_option(self, parent,
                       key: str, meta: dict):
        card = tk.Frame(
            parent, bg=meta["culoare"],
            cursor="hand2", relief="flat")
        card.pack(fill="x", pady=4)

        top = tk.Frame(
            card, bg=meta["culoare"],
            cursor="hand2")
        top.pack(fill="x", padx=10,
                 pady=(8, 2))

        tk.Label(
            top,
            text=f"{meta['icon']}  {meta['nume']}",
            font=("Arial", 11, "bold"),
            bg=meta["culoare"],
            fg="#1A1A1A",
            anchor="w",
            cursor="hand2",
        ).pack(side="left")

        tk.Label(
            card,
            text=meta["descriere"],
            font=("Arial", 9),
            bg=meta["culoare"],
            fg="#5D4037",
            wraplength=340,
            justify="left",
            anchor="w",
            cursor="hand2",
        ).pack(anchor="w", padx=10, pady=(0, 4))

        tk.Label(
            card,
            text=f"🕐 {meta['cand']}",
            font=("Arial", 8, "italic"),
            bg=meta["culoare"],
            fg="#888",
            anchor="w",
            cursor="hand2",
        ).pack(anchor="w", padx=10, pady=(0, 6))

        # Click pe card
        def _click(e=None, k=key):
            self._start(k)

        for w in [card, top] + \
                list(card.winfo_children()) + \
                list(top.winfo_children()):
            try:
                w.bind("<Button-1>", _click)
                w.bind(
                    "<Enter>",
                    lambda e, c=card,
                    col=meta["culoare"]:
                    c.configure(
                        bg=self._lighten(col)))
                w.bind(
                    "<Leave>",
                    lambda e, c=card,
                    col=meta["culoare"]:
                    c.configure(bg=col))
            except Exception:
                pass

    def _start(self, breathing_type: str):
        self.destroy()
        if self._on_select:
            self._on_select(breathing_type)

    @staticmethod
    def _darken(hex_color: str) -> str:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color

    @staticmethod
    def _lighten(hex_color: str) -> str:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            r = min(255, r + 20)
            g = min(255, g + 20)
            b = min(255, b + 20)
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return hex_color