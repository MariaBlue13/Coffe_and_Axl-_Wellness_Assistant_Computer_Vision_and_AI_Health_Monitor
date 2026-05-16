"""
Coffee & Axl - Chatbot Tab
Chat wellness cu Axl, detectie stil EAI.
Interventie AI proactiva pentru emotii detectate video.
Click pe indicator -> navigare la Chat Wellness.
"""

import customtkinter as ctk
import tkinter as tk
import time
import threading
from datetime import datetime

from utils.ai_engine import (
    AIStyle, STYLE_LABELS, STYLE_DESCRIPTIONS,
    stream_response, analyze_thinking,
    _style_from_analysis,
    check_ollama_available,
)
from utils.theme import *


# ─── Culori ───────────────────────────────────────────────────────────────────

BUBBLE_USER_BG   = "#D6E8FF"
BUBBLE_USER_TEXT = "#1A3A5C"
BUBBLE_AXL_BG    = "#FFFFFF"
BUBBLE_AXL_TEXT  = "#2D2D2D"

URGENTA_COLORS = {
    "scazuta":  ("#E8F5E9", "#2E7D32"),
    "medie":    ("#FFF8E1", "#F57F17"),
    "ridicata": ("#FFEBEE", "#C62828"),
}

STYLE_PILL = {
    AIStyle.EMPATHETIC: ("#D6E8FF", "#1A3A5C"),
    AIStyle.EXPERT:     ("#E8E0F5", "#3A2060"),
}

# Icoane si mesaje per tip interventie
INTERVENTION_META = {
    "drowsy": {
        "icon":  "😴",
        "label": "Axl a observat că ești obosit",
        "color": "#FFF8C0",
    },
    "sad": {
        "icon":  "💙",
        "label": "Axl a observat că ești abătut",
        "color": "#E8F0FF",
    },
    "angry": {
        "icon":  "😤",
        "label": "Axl a observat că ești frustrat",
        "color": "#FFE8E8",
    },
    "fearful": {
        "icon":  "😰",
        "label": "Axl a observat că ești anxios",
        "color": "#F0E8FF",
    },
    "disgusted": {
        "icon":  "😟",
        "label": "Axl a observat că ești deranjat",
        "color": "#E8FFE8",
    },
    "both": {
        "icon":  "🌙",
        "label": "Axl a observat că ești obosit și stresat",
        "color": "#FFF0D0",
    },
}


# ─── ThinkingCard ─────────────────────────────────────────────────────────────

class ThinkingCard(ctk.CTkFrame):

    def __init__(self, parent, analysis: dict):
        self._outer = ctk.CTkFrame(
            parent, fg_color="transparent")
        self._outer.pack(
            fill="x", padx=20, pady=(6, 2))

        super().__init__(
            self._outer,
            fg_color="#F8F6FF",
            corner_radius=16,
            border_width=1,
            border_color="#DDD8F0",
        )
        self.pack(fill="x")
        self._expanded = True
        self._build(analysis)

    def _build(self, analysis: dict):
        header = ctk.CTkFrame(
            self, fg_color="transparent")
        header.pack(
            fill="x", padx=14, pady=(10, 6))

        ctk.CTkLabel(
            header,
            text="✦  Procesul de gândire al lui Axl",
            font=("Arial", 11, "bold"),
            text_color="#6B5EA8",
        ).pack(side="left")

        self._toggle_btn = ctk.CTkButton(
            header,
            text="▲ Restrânge",
            width=90, height=22,
            corner_radius=8,
            fg_color="#EDE8FA",
            hover_color="#DDD8F0",
            text_color="#6B5EA8",
            font=("Arial", 10),
            command=self._toggle,
        )
        self._toggle_btn.pack(side="right")

        self._content = ctk.CTkFrame(
            self, fg_color="transparent")
        self._content.pack(
            fill="x", padx=14, pady=(0, 12))

        keywords = analysis.get("cuvinte_cheie", [])
        if keywords:
            self._row(
                self._content,
                "🔍 Cuvinte cheie",
                "  ·  ".join(keywords), "#406093")

        emotii = analysis.get("emotii", [])
        if emotii:
            self._row(
                self._content,
                "💭 Emoții detectate",
                "  ·  ".join(emotii), "#4C8CE4")

        intentie = analysis.get("intentie", "")
        if intentie:
            self._row(
                self._content,
                "🎯 Intenție",
                intentie, "#2D6A4F")

        urgenta = analysis.get(
            "urgenta", "scazuta").lower()
        urg_bg, urg_fg = URGENTA_COLORS.get(
            urgenta, URGENTA_COLORS["scazuta"])
        urg_row = ctk.CTkFrame(
            self._content, fg_color="transparent")
        urg_row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            urg_row, text="⚡ Urgență",
            font=("Arial", 11, "bold"),
            text_color=TEXT_LIGHT,
            width=140, anchor="w",
        ).pack(side="left")
        pill = ctk.CTkFrame(
            urg_row, fg_color=urg_bg,
            corner_radius=8)
        pill.pack(side="left")
        ctk.CTkLabel(
            pill,
            text=f"  {urgenta.upper()}  ",
            font=("Arial", 10, "bold"),
            text_color=urg_fg, pady=2,
        ).pack()

        stil     = analysis.get("stil", "empathetic")
        motiv    = analysis.get("motiv_stil", "")
        stil_obj = AIStyle.EXPERT \
            if stil == "expert" \
            else AIStyle.EMPATHETIC
        stil_label, stil_color = STYLE_LABELS[stil_obj]
        self._row(
            self._content, "🎨 Stil ales",
            f"{stil_label}  —  {motiv}", stil_color)

    def _row(self, parent, label: str,
             value: str, color: str):
        row = ctk.CTkFrame(
            parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(
            row, text=label,
            font=("Arial", 11, "bold"),
            text_color=TEXT_LIGHT,
            width=140, anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            row, text=value,
            font=("Arial", 11),
            text_color=color,
            wraplength=340,
            justify="left", anchor="w",
        ).pack(side="left", fill="x")

    def _toggle(self):
        if self._expanded:
            self._content.pack_forget()
            self._toggle_btn.configure(
                text="▼ Extinde")
            self._expanded = False
        else:
            self._content.pack(
                fill="x", padx=14,
                pady=(0, 12))
            self._toggle_btn.configure(
                text="▲ Restrânge")
            self._expanded = True

    def destroy_all(self):
        self._outer.destroy()


# ─── TypingIndicator ──────────────────────────────────────────────────────────

class TypingIndicator(ctk.CTkFrame):

    def __init__(self, parent,
                 phase: str = "analyzing"):
        outer = ctk.CTkFrame(
            parent, fg_color="transparent")
        outer.pack(
            fill="x", pady=4, padx=20,
            anchor="w")

        super().__init__(
            outer, fg_color="#F0F4FF",
            corner_radius=18)
        self.pack(side="left")

        self._t_start = time.time()
        self._running = True
        self._frame   = 0
        self._outer   = outer

        self._time_var  = tk.StringVar(value="0.0s")
        self._dots_var  = tk.StringVar(value="●○○")
        self._phase_var = tk.StringVar(
            value=self._phase_text(phase))

        row = ctk.CTkFrame(
            self, fg_color="transparent")
        row.pack(padx=16, pady=10)

        ctk.CTkLabel(
            row, text="☕ ",
            font=("Arial", 13),
            text_color=NAVY,
        ).pack(side="left")
        ctk.CTkLabel(
            row, textvariable=self._phase_var,
            font=("Arial", 12),
            text_color=TEXT_MID,
        ).pack(side="left")
        ctk.CTkLabel(
            row, textvariable=self._dots_var,
            font=("Arial", 12),
            text_color=BLUE,
        ).pack(side="left", padx=(6, 0))
        ctk.CTkLabel(
            row, text="  ⏱ ",
            font=("Arial", 11),
            text_color=TEXT_LIGHT,
        ).pack(side="left")
        ctk.CTkLabel(
            row, textvariable=self._time_var,
            font=("Courier New", 11, "bold"),
            text_color=NAVY,
        ).pack(side="left")

        self._animate()

    def _phase_text(self, phase: str) -> str:
        return {
            "analyzing":  "Axl analizează...",
            "thinking":   "Axl gândește...",
            "responding": "Axl răspunde...",
        }.get(phase, "Axl procesează...")

    def set_phase(self, phase: str):
        self._phase_var.set(
            self._phase_text(phase))

    def _animate(self):
        if not self._running:
            return
        elapsed = time.time() - self._t_start
        self._time_var.set(f"{elapsed:.1f}s")
        frames = ["●○○", "○●○", "○○●", "○●○"]
        self._dots_var.set(
            frames[self._frame % len(frames)])
        self._frame += 1
        self.after(250, self._animate)

    def destroy_all(self):
        self._running = False
        self._outer.destroy()


# ─── MessageBubble ────────────────────────────────────────────────────────────

class MessageBubble(ctk.CTkFrame):

    def __init__(self, parent, text: str,
                 role: str,
                 style: AIStyle = None,
                 elapsed: float = None):
        is_user = (role == "user")

        outer = ctk.CTkFrame(
            parent, fg_color="transparent")
        outer.pack(fill="x", pady=3, padx=20)

        super().__init__(
            outer,
            fg_color=BUBBLE_USER_BG
            if is_user else BUBBLE_AXL_BG,
            corner_radius=18,
            border_width=0 if is_user else 1,
            border_color="#ECECEC",
        )

        if is_user:
            self.pack(side="right",
                      padx=(80, 0))
        else:
            self.pack(side="left",
                      padx=(0, 80))

        self._text_var = tk.StringVar(value=text)
        ctk.CTkLabel(
            self,
            textvariable=self._text_var,
            text_color=BUBBLE_USER_TEXT
            if is_user else BUBBLE_AXL_TEXT,
            font=("Arial", 13),
            wraplength=400,
            justify="left", anchor="w",
        ).pack(padx=16, pady=(12, 6),
               anchor="w")

        if not is_user:
            footer = ctk.CTkFrame(
                self, fg_color="transparent")
            footer.pack(
                fill="x", padx=16,
                pady=(0, 10))

            parts = [datetime.now().strftime(
                "%H:%M")]
            if elapsed is not None:
                parts.append(f"⏱ {elapsed:.1f}s")
            if style:
                label, _ = STYLE_LABELS[style]
                parts.append(label)

            ctk.CTkLabel(
                footer,
                text="  ·  ".join(parts),
                font=("Arial", 10),
                text_color=TEXT_LIGHT,
            ).pack(side="left")

    def append_text(self, token: str):
        self._text_var.set(
            self._text_var.get() + token)


# ─── ChatbotTab ───────────────────────────────────────────────────────────────

class ChatbotTab(ctk.CTkFrame):

    def __init__(self, parent, user_name: str):
        super().__init__(
            parent, fg_color="#F7F9FF",
            corner_radius=0)
        self.user_name      = user_name
        self.history        = []
        self.current_style  = AIStyle.EMPATHETIC
        self._typing        = None
        self._thinking_card = None
        self._resp_bubble   = None
        self._is_waiting    = False

        # AI Intervention
        self._navigate_to_chat = None

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._check_ollama()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_messages_area()
        self._build_input_bar()

    def _build_header(self):
        header = ctk.CTkFrame(
            self, fg_color=WHITE,
            corner_radius=0,
            border_width=1,
            border_color=GRAY_LIGHT,
            height=64)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = ctk.CTkFrame(
            header, fg_color="transparent")
        left.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            left, text="☕",
            font=("Arial", 26),
            text_color=NAVY,
        ).pack(side="left")
        ctk.CTkLabel(
            left, text="  Axl",
            font=("Georgia", 17, "bold"),
            text_color=NAVY,
        ).pack(side="left")
        ctk.CTkLabel(
            left,
            text="  ·  Asistent Wellness",
            font=("Arial", 12),
            text_color=TEXT_LIGHT,
        ).pack(side="left")

        self._style_pill_var = tk.StringVar()
        self._style_pill_lbl = ctk.CTkLabel(
            header,
            textvariable=self._style_pill_var,
            font=("Arial", 11, "bold"),
            text_color=BLUE,
            fg_color="#D6E8FF",
            corner_radius=20,
            padx=12, pady=4,
        )
        self._style_pill_lbl.pack(
            side="left", padx=(20, 0), pady=18)
        self._update_style_pill()

        self._status_var = tk.StringVar(
            value="⟳ verificare...")
        ctk.CTkLabel(
            header,
            textvariable=self._status_var,
            font=("Arial", 10),
            text_color=GRAY_MID,
        ).pack(side="right", padx=16)

        ctk.CTkButton(
            header, text="🗑",
            width=32, height=32,
            corner_radius=8,
            fg_color=GRAY_LIGHT,
            hover_color=ERROR_RED,
            text_color=TEXT_MID,
            font=("Arial", 14),
            command=self._clear_chat,
        ).pack(side="right",
               padx=(0, 8), pady=16)

    def _update_style_pill(self):
        label, color = STYLE_LABELS[
            self.current_style]
        bg, fg = STYLE_PILL[self.current_style]
        self._style_pill_var.set(f"  {label}  ")
        self._style_pill_lbl.configure(
            text_color=fg, fg_color=bg)

    def _build_messages_area(self):
        self._chat_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="#F7F9FF",
            corner_radius=0,
            scrollbar_button_color=GRAY_LIGHT,
            scrollbar_button_hover_color=GRAY_MID,
        )
        self._chat_frame.pack(
            fill="both", expand=True)
        self._add_welcome()

    def _build_input_bar(self):
        bar = ctk.CTkFrame(
            self, fg_color=WHITE,
            corner_radius=0,
            border_width=1,
            border_color=GRAY_LIGHT,
            height=80)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text=(
                "Axl detectează automat "
                "tonul fiecărui mesaj  ✦"),
            font=("Arial", 10),
            text_color=TEXT_LIGHT,
        ).pack(anchor="w", padx=20,
               pady=(8, 0))

        input_row = ctk.CTkFrame(
            bar, fg_color="transparent")
        input_row.pack(
            fill="x", padx=16, pady=(4, 12))

        self._input = ctk.CTkEntry(
            input_row,
            placeholder_text=(
                "Scrie ceva pentru Axl..."),
            height=42, corner_radius=21,
            border_color=GRAY_LIGHT,
            border_width=1.5,
            fg_color="#F0F4FF",
            text_color=TEXT_DARK,
            font=("Arial", 13),
        )
        self._input.pack(
            side="left", fill="x",
            expand=True, padx=(0, 10))
        self._input.bind(
            "<Return>",
            lambda e: self._send_message())
        self._input.bind(
            "<FocusIn>",
            lambda e: self._input.configure(
                border_color=BLUE))
        self._input.bind(
            "<FocusOut>",
            lambda e: self._input.configure(
                border_color=GRAY_LIGHT))

        self._send_btn = ctk.CTkButton(
            input_row,
            text="➤",
            width=42, height=42,
            corner_radius=21,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            font=("Arial", 16, "bold"),
            text_color=WHITE,
            command=self._send_message,
        )
        self._send_btn.pack(side="right")

    # ── Welcome ───────────────────────────────────────────────────────────────

    def _add_welcome(self):
        card = ctk.CTkFrame(
            self._chat_frame,
            fg_color=WHITE,
            corner_radius=20,
            border_width=1,
            border_color=GRAY_LIGHT)
        card.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            card,
            text="☕  Bună, sunt Axl!",
            font=("Georgia", 17, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=24,
               pady=(20, 4))

        ctk.CTkLabel(
            card,
            text=(
                f"Salut, {self.user_name}! "
                f"Sunt asistentul tău wellness.\n\n"
                "Îmi poți spune cum te simți, "
                "ce te doare sau orice\n"
                "întrebare despre sănătate și "
                "starea ta de bine.\n\n"
            ),
            font=("Arial", 13),
            text_color=TEXT_MID,
            justify="left", anchor="w",
        ).pack(anchor="w", padx=24,
               pady=(0, 20))

    # ── Trimitere mesaj ───────────────────────────────────────────────────────

    def _send_message(self):
        if self._is_waiting:
            return
        text = self._input.get().strip()
        if not text:
            return

        self._input.delete(0, "end")
        MessageBubble(
            self._chat_frame, text, role="user")
        self.history.append(
            {"role": "user", "content": text})
        self._scroll_bottom()

        self._is_waiting = True
        self._send_btn.configure(
            state="disabled",
            fg_color=GRAY_LIGHT)
        self._input.configure(state="disabled")

        self._typing = TypingIndicator(
            self._chat_frame, phase="analyzing")
        self._thinking_card = None
        self._resp_bubble   = None
        self._scroll_bottom()

        analyze_thinking(
            text,
            on_result=self._on_analysis_done)

    # ── Flux analiza → gandire → raspuns ─────────────────────────────────────

    def _on_analysis_done(self, analysis: dict):
        self.after(
            0,
            lambda: self._show_thinking(analysis))

    def _show_thinking(self, analysis: dict):
        if self._typing:
            self._typing.set_phase("thinking")

        self.current_style = _style_from_analysis(
            analysis)
        self._update_style_pill()

        self._thinking_card = ThinkingCard(
            self._chat_frame, analysis)
        self._scroll_bottom()

        self.after(800, self._start_response)

    def _start_response(self):
        if self._typing:
            self._typing.set_phase("responding")

        stream_response(
            messages = self.history.copy(),
            style    = self.current_style,
            on_token = self._on_token,
            on_done  = self._on_done,
            on_error = self._on_error,
        )

    # ── Callbacks streaming ───────────────────────────────────────────────────

    def _on_token(self, token: str):
        self.after(
            0,
            lambda t=token:
            self._apply_token(t))

    def _apply_token(self, token: str):
        if self._resp_bubble is None:
            if self._typing:
                self._typing.destroy_all()
                self._typing = None
            if self._thinking_card:
                self._thinking_card.destroy_all()
                self._thinking_card = None
            self._resp_bubble = MessageBubble(
                self._chat_frame, "",
                role="assistant")
        self._resp_bubble.append_text(token)
        self._scroll_bottom()

    def _on_done(self, full_text: str,
                 elapsed: float):
        self.after(
            0,
            lambda: self._finalize(
                full_text, elapsed))

    def _finalize(self, full_text: str,
                  elapsed: float):
        self.history.append(
            {"role": "assistant",
             "content": full_text})

        if self._resp_bubble:
            self._resp_bubble.destroy()
            self._resp_bubble = None

        MessageBubble(
            self._chat_frame, full_text,
            role="assistant",
            style=self.current_style,
            elapsed=elapsed,
        )
        self._unlock_input()
        self._scroll_bottom()

    def _on_error(self, error_msg: str):
        self.after(
            0,
            lambda: self._show_error(error_msg))

    def _show_error(self, error_msg: str):
        if self._typing:
            self._typing.destroy_all()
            self._typing = None
        if self._thinking_card:
            self._thinking_card.destroy_all()
            self._thinking_card = None

        err = ctk.CTkFrame(
            self._chat_frame,
            fg_color="#FFF0F0",
            corner_radius=16,
            border_width=1,
            border_color="#FFCCCC",
        )
        err.pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(
            err, text=error_msg,
            font=("Courier New", 12),
            text_color=ERROR_RED,
            justify="left", anchor="w",
        ).pack(padx=16, pady=14, anchor="w")

        self._unlock_input()
        self._scroll_bottom()

    # ── Utilitare ─────────────────────────────────────────────────────────────

    def _clear_chat(self):
        for w in self._chat_frame.winfo_children():
            w.destroy()
        self.history.clear()
        self.current_style = AIStyle.EMPATHETIC
        self._update_style_pill()
        self._add_welcome()

    def _unlock_input(self):
        self._is_waiting = False
        self._send_btn.configure(
            state="normal", fg_color=BLUE)
        self._input.configure(state="normal")
        self._input.focus()

    def _scroll_bottom(self):
        self.after(
            50,
            self._chat_frame
            ._parent_canvas.yview_moveto, 1.0)

    def _check_ollama(self):
        def _check():
            try:
                ok, msg = check_ollama_available()
                color = GREEN if ok else ERROR_RED
                prefix = "✓ " if ok else "✗ "
                # Folosim root pentru thread-safety
                try:
                    self.after(
                        0,
                        lambda: self._status_var.set(
                            prefix + msg))
                except Exception:
                    pass
            except Exception:
                pass

        threading.Thread(
            target=_check, daemon=True).start()

    # ── AI Intervention ───────────────────────────────────────────────────────

    def set_navigate_to_chat_callback(self,
                                       cb: callable):
        """Seteaza callback pentru click pe indicator."""
        self._navigate_to_chat = cb

    def trigger_ai_intervention(
            self,
            system_prompt: str,
            trigger_msg: str,
            itype: str = "drowsy",
            on_done: callable = None):
        print(f"[CHATBOT] Interventie AI: {itype}")
        self._interv_on_done = on_done
        self.after(
            0,
            lambda: self._run_intervention(
                system_prompt, trigger_msg, itype))

    def _run_intervention(
            self,
            system_prompt: str,
            trigger_msg: str,
            itype: str):
        """
        Porneste raspunsul AI in background.
        Popup-ul e afisat de pet_daemon la click pe bula.
        Nu mai afisam indicator in chat.
        """
        threading.Thread(
            target=self._call_ai_intervention,
            args=(system_prompt, trigger_msg),
            daemon=True,
        ).start()

    def _show_intervention_indicator(
            self, itype: str,
            system_prompt: str,
            trigger_msg: str):
        """Indicator dezactivat — popup vine din pet_daemon."""
        pass

    def _open_ai_popup(self, itype: str):
        """
        Deschide un popup pe ecran cu mesajul AI
        si buton pentru a merge la chat.
        """
        meta = INTERVENTION_META.get(
            itype, INTERVENTION_META["drowsy"])

        # Gaseste fereastra root
        root = self.winfo_toplevel()

        popup = tk.Toplevel(root)
        popup.title("Axl Wellness")
        popup.geometry("360x220")
        popup.resizable(False, False)
        popup.configure(bg="#FFFDE7")
        popup.attributes("-topmost", True)

        # Centreaza popup-ul pe ecran
        sw = popup.winfo_screenwidth()
        sh = popup.winfo_screenheight()
        x = (sw - 360) // 2
        y = (sh - 220) // 2
        popup.geometry(f"360x220+{x}+{y}")

        # Header
        header = tk.Frame(popup, bg="#F9A825")
        header.pack(fill="x")

        tk.Label(
            header,
            text=f"  {meta['icon']}  Axl Wellness",
            font=("Arial", 12, "bold"),
            bg="#F9A825", fg="white",
            anchor="w", padx=8, pady=10,
        ).pack(side="left")

        tk.Button(
            header, text="✕",
            font=("Arial", 10),
            bg="#F9A825", fg="white",
            relief="flat", cursor="hand2",
            command=popup.destroy,
        ).pack(side="right", padx=8)

        # Mesaj
        tk.Label(
            popup,
            text=meta["label"],
            font=("Arial", 12, "bold"),
            bg="#FFFDE7", fg="#5D4037",
            wraplength=320,
            justify="center",
        ).pack(pady=(20, 8))

        # Mesaj AI (din interv_var daca exista)
        ai_text = ""
        if hasattr(self, "_interv_var"):
            ai_text = self._interv_var.get()

        if ai_text:
            tk.Label(
                popup,
                text=ai_text,
                font=("Arial", 11),
                bg="#FFFDE7", fg="#7D5A3C",
                wraplength=320,
                justify="center",
            ).pack(pady=(0, 12))

        # Butoane
        btn_frame = tk.Frame(popup, bg="#FFFDE7")
        btn_frame.pack(fill="x", padx=20,
                       pady=(0, 16))

        def _go_chat():
            popup.destroy()
            if self._navigate_to_chat:
                self._navigate_to_chat()

        tk.Button(
            btn_frame,
            text="💬 Deschide Chat Wellness",
            font=("Arial", 11, "bold"),
            bg="#4C8CE4", fg="white",
            relief="flat", cursor="hand2",
            padx=12, pady=8,
            command=_go_chat,
        ).pack(fill="x", pady=(0, 6))

        tk.Button(
            btn_frame,
            text="✕ Închide",
            font=("Arial", 10),
            bg="#E0E0E0", fg="#5D4037",
            relief="flat", cursor="hand2",
            padx=12, pady=6,
            command=popup.destroy,
        ).pack(fill="x")

    def _call_ai_intervention(
            self,
            system_prompt: str,
            trigger_msg:   str):
        """
        Apeleaza Ollama cu system_prompt specific
        emotiei detectate.
        Mesajele sunt construite cu rolul 'system'
        pentru a injecta contextul emotiei.
        """
        try:
            messages = [
                {
                    "role":    "system",
                    "content": system_prompt,
                },
                {
                    "role":    "user",
                    "content": trigger_msg,
                }
            ]

            self.after(0, self._start_ai_bubble)

            def on_token(token: str):
                self.after(
                    0,
                    lambda t=token:
                    self._append_ai_token(t))

            stream_response(
                messages = messages,
                style    = AIStyle.EMPATHETIC,
                on_token = on_token,
                on_done  = lambda *_: self.after(
                    0, self._finish_ai_bubble),
                on_error = lambda e: print(
                    f"[CHATBOT] AI eroare: {e}"),
            )

        except Exception as e:
            print(
                f"[CHATBOT] interventie eroare: {e}")

    def _start_ai_bubble(self):
        self._interv_var = ctk.StringVar(value="")

        bubble = ctk.CTkFrame(
            self._chat_frame,
            fg_color=BUBBLE_AXL_BG,
            corner_radius=CORNER_RADIUS,
            border_width=1,
            border_color=GRAY_LIGHT,
        )
        bubble.pack(
            anchor="w", fill="x",
            padx=8, pady=4)

        ctk.CTkLabel(
            bubble, text="Axl",
            font=("Arial", 10, "bold"),
            text_color=NAVY,
        ).pack(anchor="w", padx=10,
               pady=(6, 0))

        ctk.CTkLabel(
            bubble,
            textvariable=self._interv_var,
            font=("Arial", 12),
            text_color=BUBBLE_AXL_TEXT,
            wraplength=400,
            justify="left",
        ).pack(anchor="w", padx=10,
               pady=(2, 8))

        self._scroll_bottom()

    def _append_ai_token(self, token: str):
        if hasattr(self, "_interv_var"):
            current = self._interv_var.get()
            self._interv_var.set(current + token)
            self._scroll_bottom()

    def _finish_ai_bubble(self):
        print("[CHATBOT] Interventie AI completa.")
        self._scroll_bottom()
        # Trimite mesajul generat la bridge
        if hasattr(self, "_interv_on_done") \
                and self._interv_on_done:
            msg = ""
            if hasattr(self, "_interv_var"):
                msg = self._interv_var.get()
            try:
                self._interv_on_done(msg)
            except Exception as e:
                print(f"[CHATBOT] on_done err: {e}")
            self._interv_on_done = None