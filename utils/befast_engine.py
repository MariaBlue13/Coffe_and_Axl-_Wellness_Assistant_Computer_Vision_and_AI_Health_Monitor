"""
Coffee & Axl - BEFAST Engine
Orchestrator secvential intr-un singur thread dedicat.
F si A = analiza video cu BEFASTAnalyzer pe GPU.
B, E, S = STT cu Faster-Whisper.
Alerta la 2 din 5 teste picate.
Suporta oprire manuala prin _force_stop.
"""

import threading
import time
import numpy as np
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from utils.stroke_detector import (
    LipSymmetryResult, SEVERE_THRESHOLD
)
from utils.stroke_alert import send_stroke_alert


# ─── Stari ────────────────────────────────────────────────────────────────────

class BEFASTState(Enum):
    IDLE      = auto()
    PHASE1    = auto()
    BEFAST    = auto()
    EMERGENCY = auto()
    RESOLVED  = auto()


# ─── Rezultat ─────────────────────────────────────────────────────────────────

@dataclass
class BEFASTResult:
    question_key:  str  = ""
    question_text: str  = ""
    response:      str  = ""
    passed:        bool = False
    reason:        str  = ""


# ─── Engine ───────────────────────────────────────────────────────────────────

class BEFASTEngine:

    ALERT_THRESHOLD = 2

    def __init__(
        self,
        pb_api_key:      str,
        user_name:       str,
        on_state_change: Callable,
    ):
        self.pb_api_key      = pb_api_key
        self.user_name       = user_name
        self.on_state_change = on_state_change

        self._state          = BEFASTState.IDLE
        self._results        = []
        self._last_trigger   = 0.0
        self._cooldown       = 60.0
        self._force_stop     = False

        # Colectori scoruri video
        self._smile_scores       = []
        self._arms_scores        = []
        self._collecting         = False
        self._current_vision_key = None

        # Callbacks
        self.on_transcript:       callable = None
        self._volume_callback:    callable = None
        self._on_annotated_frame: callable = None

        # Componente audio + analyzer
        self._tts      = None
        self._stt      = None
        self._analyzer = None

        self._init_components()

    def _init_components(self):
        threading.Thread(
            target=self._do_init,
            daemon=True,
        ).start()

    def _do_init(self):
        try:
            from utils.voice_assistant import (
                SpeechEngine, SpeechListener)
            from utils.befast_analyzer import (
                BEFASTAnalyzer)

            self._tts      = SpeechEngine()
            self._stt      = SpeechListener()
            self._analyzer = BEFASTAnalyzer()
            print("[BEFAST] Audio + Analyzer gata.")
        except Exception as e:
            print(f"[BEFAST] Init eroare: {e}")

    # ── Stare ─────────────────────────────────────────────────────────────────

    @property
    def state(self) -> BEFASTState:
        return self._state

    def _set_state(self, state: BEFASTState,
                   data: dict = None):
        self._state = state
        self.on_state_change(state, data or {})

    def set_volume_callback(self, cb: callable):
        self._volume_callback = cb
        if self._stt:
            self._stt.set_volume_callback(cb)

    # ── Feed frame ────────────────────────────────────────────────────────────

    def feed_frame(self, frame: np.ndarray):
        if (self._state != BEFASTState.BEFAST
                or not self._collecting
                or not self._current_vision_key
                or not self._analyzer):
            return

        key = self._current_vision_key

        try:
            if key == "face":
                analysis = \
                    self._analyzer.analyze_smile(frame)
                if analysis.face_detected:
                    self._smile_scores.append(analysis)
                annotated = \
                    self._analyzer.draw_smile_overlay(
                        frame.copy(), analysis)

            elif key == "arms":
                analysis = \
                    self._analyzer.analyze_arms(frame)
                if analysis.pose_detected:
                    self._arms_scores.append(analysis)
                annotated = \
                    self._analyzer.draw_arms_overlay(
                        frame.copy(), analysis)
            else:
                return

            if self._on_annotated_frame:
                self._on_annotated_frame(annotated)

        except Exception as e:
            print(f"[BEFAST] feed_frame eroare: {e}")

    # ── Process frame AVC ─────────────────────────────────────────────────────

    def process_frame(self,
                      lip_result: LipSymmetryResult):
        if self._state != BEFASTState.IDLE:
            return
        if not lip_result.is_severe:
            return
        if (time.time() - self._last_trigger
                < self._cooldown):
            return

        self._last_trigger = time.time()
        threading.Thread(
            target=self._run_protocol,
            args=(lip_result,),
            daemon=True,
        ).start()

    # ── Protocol principal ────────────────────────────────────────────────────

    def _run_protocol(self,
                      lip_result: LipSymmetryResult):
        self._force_stop = False

        self._set_state(BEFASTState.PHASE1, {
            "score":     lip_result.asymmetry_score,
            "timestamp": datetime.now().strftime(
                "%H:%M:%S"),
        })

        send_stroke_alert(
            api_key   = self.pb_api_key,
            user_name = self.user_name,
            score     = lip_result.asymmetry_score,
            horiz_dev = lip_result.horizontal_dev,
            vert_dev  = lip_result.vertical_dev,
            on_success= lambda: print(
                "[BEFAST] Alerta PB trimisa."),
            on_error  = lambda e: print(
                f"[BEFAST] PB eroare: {e}"),
        )

        self._wait_ready()

        if self._force_stop:
            self._set_state(BEFASTState.IDLE, {})
            return

        self._say(
            "Atenție! Am detectat o posibilă "
            "asimetrie facială. Voi realiza acum "
            "testul de urgență B.E.F.A.S.T. "
            "Te rog să urmezi instrucțiunile."
        )

        if self._force_stop:
            self._set_state(BEFASTState.IDLE, {})
            return

        self._set_state(BEFASTState.BEFAST, {
            "current_question": 0,
            "total":            5,
            "listening":        False,
            "vision_mode":      False,
        })

        self._results = []
        questions = self._get_questions()

        for idx, q in enumerate(questions):
            if self._force_stop:
                print("[BEFAST] Oprit in bucla "
                      f"la intrebarea {idx + 1}.")
                self._force_stop = False
                self._collecting = False
                self._current_vision_key = None
                self._set_state(
                    BEFASTState.IDLE, {})
                return

            result = self._run_question(
                q, idx + 1, len(questions))

            if self._force_stop:
                print("[BEFAST] Oprit dupa "
                      f"intrebarea {idx + 1}.")
                self._force_stop = False
                self._collecting = False
                self._current_vision_key = None
                self._set_state(
                    BEFASTState.IDLE, {})
                return

            self._results.append(result)

        self._evaluate()

    def _wait_ready(self):
        for _ in range(40):
            if (self._tts and self._stt
                    and self._analyzer):
                return
            time.sleep(0.5)

    # ── Intrebari ─────────────────────────────────────────────────────────────

    def _get_questions(self) -> list:
        return [
            {
                "key":      "balance",
                "letter":   "B — Echilibru",
                "mode":     "stt",
                "spoken_intro": "Testul B, echilibru. ",
                "spoken_question": (
                    "Simți amețeli severe, "
                    "îți pierzi echilibrul "
                    "sau nu poți merge drept? "
                    "Răspunde da sau nu."
                ),
                "display": (
                    "B — Echilibru\n"
                    "Simți amețeli severe sau\n"
                    "nu poți merge drept?"
                ),
            },
            {
                "key":      "eyes",
                "letter":   "E — Ochi",
                "mode":     "stt",
                "spoken_intro": "Testul E, ochi. ",
                "spoken_question": (
                    "Ai pierdere bruscă a vederii, "
                    "vezi dublu sau ai o perdea "
                    "peste ochi? "
                    "Răspunde da sau nu."
                ),
                "display": (
                    "E — Ochi\n"
                    "Ai pierdere bruscă a vederii\n"
                    "sau vedere dublă?"
                ),
            },
            {
                "key":      "face",
                "letter":   "F — Față",
                "mode":     "vision",
                "spoken_intro": "Testul F, față. ",
                "spoken_question": (
                    "Te rog zâmbește larg "
                    "și arată-mi dinții. "
                    "Menține zâmbetul. "
                    "Te analizez acum."
                ),
                "display": (
                    "F — Față\n"
                    "Zâmbește larg și arată dinții!\n"
                    "Menține zâmbetul."
                ),
                "duration": 5,
            },
            {
                "key":      "arms",
                "letter":   "A — Brațe",
                "mode":     "vision",
                "spoken_intro": "Testul A, brațe. ",
                "spoken_question": (
                    "Te rog ridică ambele brațe "
                    "în fața ta, la nivelul umerilor, "
                    "și închide ochii. "
                    "Menține poziția zece secunde."
                ),
                "display": (
                    "A — Brațe\n"
                    "Ridică ambele brațe la nivelul\n"
                    "umerilor și ține ochii închiși!"
                ),
                "duration": 10,
            },
            {
                "key":      "speech",
                "letter":   "S — Vorbire",
                "mode":     "stt",
                "spoken_intro": "Testul S, vorbire. ",
                "spoken_question": (
                    "Te rog repetă după mine, "
                    "clar și rar: "
                    "Afară este soare și frumos. "
                    "Acum repetă."
                ),
                "display": (
                    "S — Vorbire\n"
                    "Repetă: Afară este soare și frumos."
                ),
                "target_words": {
                    "afară", "afara", "este",
                    "soare", "frumos",
                },
            },
        ]

    # ── Rulare intrebare ──────────────────────────────────────────────────────

    def _run_question(self, q: dict,
                      idx: int,
                      total: int) -> BEFASTResult:
        result = BEFASTResult(
            question_key  = q["key"],
            question_text = q["display"],
        )

        if self._force_stop:
            return self._empty_result(q)

        self._set_state(BEFASTState.BEFAST, {
            "current_question": idx,
            "total":            total,
            "question_display": q["display"],
            "letter":           q["letter"],
            "listening":        False,
            "vision_mode":
                q["mode"] == "vision",
        })

        self._say(q["spoken_intro"])
        if self._force_stop:
            return self._empty_result(q)

        self._say(q["spoken_question"])
        if self._force_stop:
            return self._empty_result(q)

        if q["mode"] == "stt":
            return self._run_stt(
                q, result, idx, total)
        else:
            return self._run_vision(
                q, result, idx, total)

    # ── STT ───────────────────────────────────────────────────────────────────

    def _run_stt(self, q: dict,
                 result: BEFASTResult,
                 idx: int,
                 total: int) -> BEFASTResult:
        if self._force_stop:
            return self._empty_result(q)

        self._set_state(BEFASTState.BEFAST, {
            "current_question": idx,
            "total":            total,
            "question_display": q["display"],
            "letter":           q["letter"],
            "listening":        True,
            "vision_mode":      False,
        })

        if self._volume_callback:
            self._stt.set_volume_callback(
                self._volume_callback)

        response_holder = [None]
        done            = threading.Event()

        def on_result(text):
            response_holder[0] = text
            done.set()

        def on_error(err):
            response_holder[0] = err
            done.set()

        self._stt.listen(
            on_result    = on_result,
            on_error     = on_error,
            timeout      = 10,
            phrase_limit = 6,
        )

        # Asteapta cu verificare force_stop
        for _ in range(20):
            if done.is_set() or self._force_stop:
                break
            time.sleep(1.0)

        if self._stt:
            self._stt.set_volume_callback(None)

        if self._force_stop:
            return self._empty_result(q)

        response = response_holder[0] or "timeout"

        if (self.on_transcript
                and response not in (
                    "timeout", "unclear")
                and not response.startswith(
                    "error:")):
            self.on_transcript(response)

        self._set_state(BEFASTState.BEFAST, {
            "current_question": idx,
            "total":            total,
            "question_display": q["display"],
            "letter":           q["letter"],
            "listening":        False,
            "vision_mode":      False,
        })

        passed, reason = self._evaluate_stt(
            q, response)
        result.response = response
        result.passed   = passed
        result.reason   = reason

        if not self._force_stop:
            self._say(
                "Bine." if passed
                else "Am notat.")
        return result

    def _evaluate_stt(
            self, q: dict,
            response: str) -> tuple[bool, str]:
        if response in ("timeout", "unclear") \
                or response.startswith("error:"):
            return False, {
                "timeout": "Nu a răspuns în timp.",
                "unclear": "Vorbire neinteligibilă.",
            }.get(response,
                  f"Eroare: {response}")

        words = response.split()
        if not words:
            return False, "Răspuns gol."

        key = q["key"]

        if key in ("balance", "eyes"):
            neg = {"nu", "nope", "nici", "fara",
                   "fără", "n-am", "nam"}
            pos = {"da", "daa", "sigur", "foarte",
                   "amețeli", "ameteli", "pierd",
                   "văd", "vad", "dublu", "perdea",
                   "vedere", "cadere"}
            if any(w in response for w in neg):
                return True, \
                    f"Simptom negat: '{response}'"
            if any(w in response for w in pos):
                return False, \
                    f"Simptom confirmat: '{response}'"
            return True, f"Răspuns: '{response}'"

        elif key == "speech":
            target = q.get("target_words", set())
            found  = sum(
                1 for w in target
                if w in response)
            if found >= 2:
                return True, \
                    f"Vorbire clară: '{response}'"
            elif len(words) >= 3:
                return True, \
                    f"Vorbire inteligibilă: '{response}'"
            else:
                return False, \
                    f"Vorbire neclară: '{response}'"

        return True, f"Răspuns: '{response}'"

    # ── Vision ────────────────────────────────────────────────────────────────

    def _run_vision(self, q: dict,
                    result: BEFASTResult,
                    idx: int,
                    total: int) -> BEFASTResult:
        if self._force_stop:
            return self._empty_result(q)

        duration = q.get("duration", 5)

        self._smile_scores.clear()
        self._arms_scores.clear()
        self._current_vision_key = q["key"]
        self._collecting         = True

        # Numara invers cu verificare force_stop
        for sec in range(duration, 0, -1):
            if self._force_stop:
                self._collecting         = False
                self._current_vision_key = None
                return self._empty_result(q)

            self._set_state(BEFASTState.BEFAST, {
                "current_question": idx,
                "total":            total,
                "question_display": (
                    q["display"] +
                    f"\n⏱ {sec}..."
                ),
                "letter":           q["letter"],
                "listening":        False,
                "vision_mode":      True,
                "countdown":        sec,
            })
            self._say(str(sec))

        self._collecting         = False
        self._current_vision_key = None

        if self._force_stop:
            return self._empty_result(q)

        passed, reason = self._evaluate_vision(q)
        result.passed  = passed
        result.reason  = reason

        if not self._force_stop:
            self._say(
                "Bine." if passed
                else "Am notat o anomalie.")
        return result

    def _evaluate_vision(
            self, q: dict) -> tuple[bool, str]:
        key = q["key"]

        if key == "face":
            if not self._smile_scores:
                return True, \
                    "Date video insuficiente."

            scores = [s.asymmetry_score
                      for s in self._smile_scores]
            median = float(np.median(scores))
            worst  = float(np.max(scores))

            smile_vals = [
                s.blendshapes.get(
                    "mouthSmileLeft", 0) +
                s.blendshapes.get(
                    "mouthSmileRight", 0)
                for s in self._smile_scores
                if s.blendshapes
            ]
            smile_bs = float(np.mean(smile_vals)) \
                if smile_vals else 0.0

            print(f"[BEFAST] Zambet — "
                  f"median={median:.3f} "
                  f"worst={worst:.3f} "
                  f"smile_bs={smile_bs:.3f}")

            thr = self._analyzer.SMILE_THRESHOLD
            if median > thr:
                return False, (
                    f"Asimetrie facială la zâmbet: "
                    f"scor {median:.3f} > prag {thr}"
                )
            return True, \
                f"Zâmbet simetric: {median:.3f}"

        elif key == "arms":
            if not self._arms_scores:
                return True, \
                    "Date video insuficiente."

            total_f  = len(self._arms_scores)
            drop_f   = sum(
                1 for a in self._arms_scores
                if a.arm_drop_detected)
            drop_pct = drop_f / max(total_f, 1)

            avg_diff = float(np.mean([
                a.height_diff
                for a in self._arms_scores
            ]))

            both_raised = sum(
                1 for a in self._arms_scores
                if a.left_arm_raised
                and a.right_arm_raised
            ) / max(total_f, 1)

            print(f"[BEFAST] Brate — "
                  f"drop={drop_pct:.2f} "
                  f"diff={avg_diff:.3f} "
                  f"both={both_raised:.2f}")

            if both_raised < 0.2:
                return False, (
                    "Brațele nu au fost ridicate "
                    "suficient.")
            if drop_pct > 0.40:
                return False, (
                    f"Brat cazut in "
                    f"{drop_pct:.0%} din timp.")
            return True, (
                f"Brațe stabile: "
                f"drop în {drop_pct:.0%} din frames.")

        return True, "Analiză completă."

    # ── TTS helper ────────────────────────────────────────────────────────────

    def _say(self, text: str):
        if not self._tts or self._force_stop:
            return
        done = threading.Event()
        self._tts.speak(
            text, on_done=lambda: done.set())
        # Asteapta cu verificare force_stop
        for _ in range(60):
            if done.is_set() or self._force_stop:
                break
            time.sleep(0.5)
        if not self._force_stop:
            time.sleep(0.15)

    # ── Evaluare finala ───────────────────────────────────────────────────────

    def _evaluate(self):
        if self._force_stop:
            self._force_stop = False
            self._set_state(BEFASTState.IDLE, {})
            return

        failed = [r for r in self._results
                  if not r.passed]
        passed = [r for r in self._results
                  if r.passed]

        results_data = [
            {
                "key":    r.question_key,
                "passed": r.passed,
                "reason": r.reason,
            }
            for r in self._results
        ]

        if len(failed) >= self.ALERT_THRESHOLD:
            print(f"[BEFAST] URGENTA: "
                  f"{len(failed)}/5 picate")
            self._say(
                f"Atenție! {len(failed)} din cinci "
                "teste indică posibil accident "
                "vascular. Se activează alerta. "
                "Sunați 112 imediat."
            )
            if not self._force_stop:
                self._set_state(
                    BEFASTState.EMERGENCY, {
                        "failed_questions": [
                            r.question_key
                            for r in failed],
                        "failed_details": [
                            {"key":    r.question_key,
                             "reason": r.reason}
                            for r in failed
                        ],
                        "results":   results_data,
                        "timestamp":
                            datetime.now().strftime(
                                "%H:%M:%S"),
                    })
        else:
            print(f"[BEFAST] OK: "
                  f"{len(failed)}/5 picate")
            self._say(
                f"Ai trecut {len(passed)} din "
                "cinci teste. Nu am detectat "
                "semne clare. Monitorizează "
                "starea ta și la orice simptom "
                "nou, sună 112."
            )
            if not self._force_stop:
                self._set_state(
                    BEFASTState.RESOLVED, {
                        "results": results_data,
                    })
                time.sleep(10)
                if not self._force_stop:
                    self._set_state(
                        BEFASTState.IDLE, {})

    # ── Helper result gol ─────────────────────────────────────────────────────

    def _empty_result(self,
                       q: dict) -> BEFASTResult:
        """Rezultat gol pentru test oprit manual."""
        return BEFASTResult(
            question_key  = q["key"],
            question_text = q["display"],
            response      = "oprit",
            passed        = True,
            reason        = "Test oprit manual.",
        )

    # ── Reset si close ────────────────────────────────────────────────────────

    def reset(self):
        print("[BEFAST] Reset.")
        self._force_stop         = True
        self._collecting         = False
        self._current_vision_key = None
        self._smile_scores.clear()
        self._arms_scores.clear()
        # Starea se seteaza dupa ce thread-ul
        # detecteaza force_stop
        self.after_reset_state = True
        self._set_state(BEFASTState.IDLE, {})

    def close(self):
        self._force_stop = True
        if self._analyzer:
            self._analyzer.close()