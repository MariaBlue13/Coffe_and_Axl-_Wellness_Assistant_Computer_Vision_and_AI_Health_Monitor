"""
Coffee & Axl - Wellness Session
Sesiune interactiva ghidata cu TTS.
"""

import threading
import time
from utils.wellness_engine import (
    WellnessType, SESSIONS, WELLNESS_META)


class WellnessSession:
    """
    Ruleaza o sesiune wellness pas cu pas.
    Fiecare pas are text TTS + durata + callback UI.
    """

    def __init__(self, wtype: WellnessType,
                 on_step:   callable = None,
                 on_done:   callable = None,
                 on_tick:   callable = None):
        self._wtype   = wtype
        self._on_step = on_step
        self._on_done = on_done
        self._on_tick = on_tick

        self._tts     = None
        self._running = False
        self._force_stop = False

        self._init_tts()

    def _init_tts(self):
        try:
            from utils.voice_assistant import (
                SpeechEngine)
            self._tts = SpeechEngine()
        except Exception as e:
            print(f"[SESSION] TTS eroare: {e}")

    def start(self):
        self._running    = True
        self._force_stop = False
        threading.Thread(
            target=self._run,
            daemon=True,
        ).start()

    def stop(self):
        self._force_stop = True
        self._running    = False

    def _run(self):
        steps = SESSIONS.get(self._wtype, [])

        for i, step in enumerate(steps):
            if self._force_stop:
                break

            if self._on_step:
                self._on_step(step, i, len(steps))

            self._say(step["text"])
            if self._force_stop:
                break

            tip = step.get("tip", "mesaj")
            durata = step.get("durata", 3)

            if tip == "ritm":
                # Clipit ritmic — anunta fiecare ciclu
                count = step.get("count", 12)
                cicle = step.get("cicle", 3)
                for n in range(count):
                    if self._force_stop:
                        break
                    # Inchide
                    if self._on_step:
                        s = dict(step)
                        s["text"] = "Închide..."
                        s["icon"] = "😌"
                        self._on_step(s, i, len(steps))
                    time.sleep(cicle * 0.4)
                    if self._force_stop:
                        break
                    # Tine
                    if self._on_step:
                        s = dict(step)
                        s["text"] = "Ține..."
                        s["icon"] = "😌"
                        self._on_step(s, i, len(steps))
                    time.sleep(cicle * 0.3)
                    if self._force_stop:
                        break
                    # Deschide
                    if self._on_step:
                        s = dict(step)
                        s["text"] = f"Deschide! ({n + 1}/{count})"
                        s["icon"] = "👁"
                        self._on_step(s, i, len(steps))
                        if self._on_tick:
                            self._on_tick(
                                count - n, count)
                    time.sleep(cicle * 0.3)

            elif tip in ("countdown", "directie",
                         "actiune", "titlu"):
                for sec in range(durata, 0, -1):
                    if self._force_stop:
                        break
                    if self._on_tick:
                        self._on_tick(sec, durata)
                    time.sleep(1)

            else:
                # mesaj simplu
                for sec in range(durata, 0, -1):
                    if self._force_stop:
                        break
                    time.sleep(1)

        if not self._force_stop and self._on_done:
            self._on_done()

    def _say(self, text: str):
        if not self._tts or self._force_stop:
            return
        done = threading.Event()
        self._tts.speak(
            text,
            on_done=lambda: done.set())
        for _ in range(60):
            if done.is_set() or self._force_stop:
                break
            time.sleep(0.5)