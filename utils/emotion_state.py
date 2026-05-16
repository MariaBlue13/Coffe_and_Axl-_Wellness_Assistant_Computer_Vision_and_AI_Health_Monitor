"""
Coffee & Axl - Emotion State Manager
Debouncing pentru toate emotiile Ekman + oboseala.
Bazat pe Ekman (1977) - cele 6 emotii universale.
"""

import time
from dataclasses import dataclass
from enum import Enum
from utils.emotion_detector import (
    EmotionMetrics, EkmanEmotion)


# ─── Stari emotionale ─────────────────────────────────────────────────────────

class EmotionalState(Enum):
    NEUTRAL   = "neutral"
    DROWSY    = "drowsy"
    SAD       = "sad"
    ANGRY     = "angry"
    FEARFUL   = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    HAPPY     = "happy"
    BOTH      = "both"


# ─── Configurare ──────────────────────────────────────────────────────────────

CONFIRM_SECONDS  = 8.0
COOLDOWN_SECONDS = 60.0
RESET_SECONDS    = 3.0

# Mapare emotie Ekman -> stare
EKMAN_TO_STATE = {
    EkmanEmotion.HAPPINESS: EmotionalState.HAPPY,
    EkmanEmotion.SADNESS:   EmotionalState.SAD,
    EkmanEmotion.ANGER:     EmotionalState.ANGRY,
    EkmanEmotion.FEAR:      EmotionalState.FEARFUL,
    EkmanEmotion.DISGUST:   EmotionalState.DISGUSTED,
    EkmanEmotion.SURPRISE:  EmotionalState.SURPRISED,
    EkmanEmotion.DROWSY:    EmotionalState.DROWSY,
    EkmanEmotion.NEUTRAL:   EmotionalState.NEUTRAL,
}

# Emotii care declanseaza interventie AI
INTERVENTION_STATES = {
    EmotionalState.DROWSY,
    EmotionalState.SAD,
    EmotionalState.ANGRY,
    EmotionalState.FEARFUL,
    EmotionalState.DISGUSTED,
    EmotionalState.BOTH,
}


# ─── Fereastra de stare ───────────────────────────────────────────────────────

@dataclass
class StateWindow:
    state:      EmotionalState = EmotionalState.NEUTRAL
    started_at: float          = 0.0
    confirmed:  bool           = False

    def duration(self) -> float:
        if self.started_at == 0:
            return 0.0
        return time.time() - self.started_at

    def is_confirmed(self) -> bool:
        return self.duration() >= CONFIRM_SECONDS


# ─── Manager ──────────────────────────────────────────────────────────────────

class EmotionStateManager:
    """
    Gestioneaza starea emotionala cu debouncing.
    Starea trebuie mentinuta CONFIRM_SECONDS secunde
    consecutive inainte de a declansa o alerta.
    """

    def __init__(
        self,
        on_drowsy:    callable = None,
        on_sad:       callable = None,
        on_angry:     callable = None,
        on_fearful:   callable = None,
        on_disgusted: callable = None,
        on_surprised: callable = None,
        on_happy:     callable = None,
        on_both:      callable = None,
        on_reset:     callable = None,
    ):
        self.on_drowsy    = on_drowsy
        self.on_sad       = on_sad
        self.on_angry     = on_angry
        self.on_fearful   = on_fearful
        self.on_disgusted = on_disgusted
        self.on_surprised = on_surprised
        self.on_happy     = on_happy
        self.on_both      = on_both
        self.on_reset     = on_reset

        self._current_window = StateWindow()
        self._neutral_since  = time.time()
        self._last_alert: dict = {}
        self._last_state = EmotionalState.NEUTRAL

    # ── Update principal ──────────────────────────────────────────────────────

    def update(self, metrics: EmotionMetrics) -> dict:
        if not metrics.face_detected:
            return self._status()

        state = self._classify(metrics)

        if state == EmotionalState.NEUTRAL:
            self._handle_neutral()
        else:
            self._handle_active(state)

        self._last_state = state
        return self._status()

    # ── Clasificare ───────────────────────────────────────────────────────────

    def _classify(self,
                  m: EmotionMetrics
                  ) -> EmotionalState:
        """
        Determina starea emotionala din EmotionMetrics.
        Foloseste primary_emotion si is_negative/is_drowsy.
        """
        # Daca e obosit SI are o emotie negativa -> BOTH
        if (m.is_drowsy
                and m.is_negative
                and m.primary_emotion
                not in (EkmanEmotion.DROWSY,
                        EkmanEmotion.NEUTRAL)):
            return EmotionalState.BOTH

        # Mapeaza emotia principala la stare
        mapped = EKMAN_TO_STATE.get(
            m.primary_emotion,
            EmotionalState.NEUTRAL)

        # Neutru daca confidenta e sub prag
        if (m.primary_emotion
                not in (EkmanEmotion.DROWSY,)
                and m.confidence < 0.18):
            return EmotionalState.NEUTRAL

        return mapped

    # ── Handle neutral ────────────────────────────────────────────────────────

    def _handle_neutral(self):
        now = time.time()

        if self._last_state != EmotionalState.NEUTRAL:
            self._neutral_since = now

        neutral_dur = now - self._neutral_since
        if (neutral_dur >= RESET_SECONDS
                and self._current_window.state
                != EmotionalState.NEUTRAL):
            self._current_window = StateWindow(
                state      = EmotionalState.NEUTRAL,
                started_at = now,
            )
            if self.on_reset:
                self.on_reset()

    # ── Handle stare activa ───────────────────────────────────────────────────

    def _handle_active(self, state: EmotionalState):
        now = time.time()

        # Starea s-a schimbat -> reseteaza fereastra
        if self._current_window.state != state:
            self._current_window = StateWindow(
                state      = state,
                started_at = now,
            )
            return

        # Verifica confirmare
        if not self._current_window.is_confirmed():
            return

        # Verifica cooldown per stare
        last = self._last_alert.get(state, 0.0)
        if now - last < COOLDOWN_SECONDS:
            return

        # Declanseaza alerta
        self._last_alert[state] = now
        self._current_window.confirmed = True
        self._trigger_alert(state)

    # ── Declanseaza alerta ────────────────────────────────────────────────────

    def _trigger_alert(self, state: EmotionalState):
        print(f"[EMOTION] Alerta confirmata: "
              f"{state.value} dupa "
              f"{CONFIRM_SECONDS}s")

        callbacks = {
            EmotionalState.DROWSY:    self.on_drowsy,
            EmotionalState.SAD:       self.on_sad,
            EmotionalState.ANGRY:     self.on_angry,
            EmotionalState.FEARFUL:   self.on_fearful,
            EmotionalState.DISGUSTED: self.on_disgusted,
            EmotionalState.SURPRISED: self.on_surprised,
            EmotionalState.HAPPY:     self.on_happy,
            EmotionalState.BOTH:      self.on_both,
        }

        cb = callbacks.get(state)
        if cb:
            cb()
        elif state == EmotionalState.BOTH:
            # Fallback la drowsy daca on_both lipseste
            if self.on_drowsy:
                self.on_drowsy()

    # ── Status ────────────────────────────────────────────────────────────────

    def _status(self) -> dict:
        w        = self._current_window
        progress = 0.0

        if w.state != EmotionalState.NEUTRAL:
            progress = min(
                w.duration() / CONFIRM_SECONDS,
                1.0)

        return {
            "state":     w.state,
            "progress":  progress,
            "confirmed": w.confirmed,
            "duration":  w.duration(),
        }

    def get_progress(self) -> float:
        w = self._current_window
        if w.state == EmotionalState.NEUTRAL:
            return 0.0
        return min(
            w.duration() / CONFIRM_SECONDS, 1.0)

    def get_state(self) -> EmotionalState:
        return self._current_window.state

    def reset(self):
        self._current_window = StateWindow()
        self._neutral_since  = time.time()