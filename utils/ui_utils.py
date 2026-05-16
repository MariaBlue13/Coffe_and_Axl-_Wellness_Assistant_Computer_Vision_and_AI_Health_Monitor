"""
Coffee & Axl - Utilitare UI: animatii, tranzitii, toast-uri
"""
import customtkinter as ctk
import tkinter as tk


# ─── Animatie fade (transparenta fereastra) ────────────────────────────────────

def fade_in(widget, steps: int = 12, delay_ms: int = 18,
            start: float = 0.0, end: float = 1.0):
    """Fade-in pe orice widget top-level (fereastra)."""
    try:
        widget.attributes("-alpha", start)
    except Exception:
        return

    step_size = (end - start) / steps

    def _step(current, remaining):
        if remaining <= 0:
            try:
                widget.attributes("-alpha", end)
            except Exception:
                pass
            return
        current += step_size
        try:
            widget.attributes("-alpha", min(current, end))
            widget.after(delay_ms, lambda: _step(current, remaining - 1))
        except Exception:
            pass

    widget.after(10, lambda: _step(start, steps))


def fade_out(widget, steps: int = 10, delay_ms: int = 16,
             callback=None):
    """Fade-out, apoi apeleaza callback (ex: destroy)."""
    step_size = 1.0 / steps

    def _step(current, remaining):
        if remaining <= 0:
            try:
                widget.attributes("-alpha", 0.0)
            except Exception:
                pass
            if callback:
                try:
                    callback()
                except Exception:
                    pass
            return
        current -= step_size
        try:
            widget.attributes("-alpha", max(current, 0.0))
            widget.after(delay_ms, lambda: _step(current, remaining - 1))
        except Exception:
            if callback:
                try:
                    callback()
                except Exception:
                    pass

    _step(1.0, steps)


# ─── Animatie slide pentru frame-uri ─────────────────────────────────────────

def slide_in_y(widget, from_y: int, to_y: int = 0,
               steps: int = 16, delay_ms: int = 12):
    """Anima un widget pe axa Y (slide de jos/sus)."""
    diff = to_y - from_y
    step_size = diff / steps
    current_y = [float(from_y)]

    def _step(remaining):
        if remaining <= 0:
            try:
                widget.place_configure(y=to_y)
            except Exception:
                pass
            return
        current_y[0] += step_size
        try:
            widget.place_configure(y=int(current_y[0]))
            widget.after(delay_ms, lambda: _step(remaining - 1))
        except Exception:
            pass

    _step(steps)


# ─── Toast notifications ──────────────────────────────────────────────────────

class Toast(ctk.CTkToplevel):
    """
    Notificare discreta care apare in coltul din dreapta jos,
    se mentine 3 secunde, apoi dispare cu fade-out.
    """

    COLORS = {
        "info":    ("#4C8CE4", "#FFFFFF"),
        "success": ("#5BB85D", "#FFFFFF"),
        "warning": ("#F0A030", "#FFFFFF"),
        "error":   ("#E05555", "#FFFFFF"),
    }

    def __init__(self, parent, message: str,
                 kind: str = "info", duration_ms: int = 3200):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        bg, fg = self.COLORS.get(kind, self.COLORS["info"])

        frame = ctk.CTkFrame(
            self, fg_color=bg, corner_radius=12,
            border_width=0,
        )
        frame.pack(padx=0, pady=0)

        icon_map = {
            "info": "ℹ", "success": "✓",
            "warning": "⚠", "error": "✕",
        }
        icon = icon_map.get(kind, "ℹ")

        ctk.CTkLabel(
            frame,
            text=f"  {icon}  {message}  ",
            font=("Arial", 12, "bold"),
            text_color=fg,
        ).pack(padx=16, pady=12)

        self.update_idletasks()
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        w  = self.winfo_reqwidth()
        h  = self.winfo_reqheight()
        self.geometry(f"{w}x{h}+{sw - w - 32}+{sh - h - 72}")

        # Fade in
        self._fade_step(0.0, direction=1, target=0.92,
                        steps=8, delay=16, after_cb=lambda: (
                            self.after(duration_ms, self._hide)
                        ))

    def _fade_step(self, alpha, direction, target,
                   steps, delay, after_cb=None, remaining=None):
        if remaining is None:
            remaining = steps
        if remaining <= 0:
            try:
                self.attributes("-alpha", target)
            except Exception:
                pass
            if after_cb:
                after_cb()
            return
        alpha += direction * (target / steps)
        alpha  = max(0.0, min(alpha, target))
        try:
            self.attributes("-alpha", alpha)
            self.after(
                delay,
                lambda: self._fade_step(
                    alpha, direction, target,
                    steps, delay, after_cb, remaining - 1),
            )
        except Exception:
            if after_cb:
                after_cb()

    def _hide(self):
        try:
            self._fade_step(
                float(self.attributes("-alpha")),
                direction=-1, target=0.0,
                steps=8, delay=14,
                after_cb=self._safe_destroy,
            )
        except Exception:
            self._safe_destroy()

    def _safe_destroy(self):
        try:
            self.destroy()
        except Exception:
            pass


def show_toast(parent, message: str,
               kind: str = "info", duration_ms: int = 3200):
    """Afiseaza un toast. Apelabil din orice thread UI."""
    try:
        Toast(parent, message, kind=kind, duration_ms=duration_ms)
    except Exception as e:
        print(f"[TOAST] {e}")


# ─── Animatie buton (pulse la click) ─────────────────────────────────────────

def pulse_button(btn, color_on: str, color_off: str,
                 steps: int = 6, delay: int = 40):
    """Scurta animatie de puls pe un CTkButton la click."""
    def _restore(remaining):
        if remaining <= 0:
            try:
                btn.configure(fg_color=color_off)
            except Exception:
                pass
            return
        try:
            btn.after(delay, lambda: _restore(remaining - 1))
        except Exception:
            pass

    try:
        btn.configure(fg_color=color_on)
        btn.after(steps * delay, lambda: _restore(steps))
    except Exception:
        pass


# ─── Shimmer loading placeholder ─────────────────────────────────────────────

class ShimmerLabel(ctk.CTkLabel):
    """
    Label cu efect de shimmer (loading).
    Apeleaza .stop_shimmer() cand datele sunt gata.
    """

    SHIMMER_COLORS = ["#E8ECF3", "#D0D8E8", "#E8ECF3"]

    def __init__(self, parent, width: int = 80, height: int = 18, **kwargs):
        kwargs.setdefault("text", "")
        kwargs.setdefault("fg_color", self.SHIMMER_COLORS[0])
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("width", width)
        kwargs.setdefault("height", height)
        super().__init__(parent, **kwargs)
        self._shimmer_active = True
        self._shimmer_idx    = 0
        self._shimmer_job    = None
        self._animate()

    def _animate(self):
        if not self._shimmer_active:
            return
        try:
            if not self.winfo_exists():
                return
            color = self.SHIMMER_COLORS[
                self._shimmer_idx % len(self.SHIMMER_COLORS)]
            self.configure(fg_color=color)
            self._shimmer_idx += 1
            self._shimmer_job = self.after(340, self._animate)
        except Exception:
            pass

    def stop_shimmer(self, text: str = "", fg_color: str = "transparent",
                     text_color: str = "#1A2540",
                     font=("Georgia", 22, "bold")):
        self._shimmer_active = False
        if self._shimmer_job:
            try:
                self.after_cancel(self._shimmer_job)
            except Exception:
                pass
        try:
            self.configure(
                fg_color=fg_color,
                text=text,
                text_color=text_color,
                font=font,
            )
        except Exception:
            pass