"""
Coffee & Axl - AI Intervention Bridge
Detectie emotionala Ekman -> mesaj proactiv AI -> bula pet.
Fara cooldown global — doar blocare daca interventie in progres.
"""

import threading
import time
import os
from enum import Enum


# ─── Tipuri interventie ───────────────────────────────────────────────────────

class InterventionType(Enum):
    DROWSY    = "drowsy"
    SAD       = "sad"
    ANGRY     = "angry"
    FEARFUL   = "fearful"
    DISGUSTED = "disgusted"
    BOTH      = "both"


# ─── Prompturi sistem ─────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    InterventionType.DROWSY: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare obosit — ochii îngreunați, clipiri lente. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj scurt, cald și energizant. "
        "Sugerează o pauză de 5 minute, apă sau "
        "câteva respirații adânci. "
        "Fii natural ca un prieten. "
        "Maximum 2 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
    InterventionType.SAD: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare trist sau abătut — expresie tristă, "
        "colțurile gurii lăsate, sprâncene încruntate. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj scurt, cald și încurajator. "
        "Oferă sprijin emoțional cald. "
        "Fii natural ca un prieten. "
        "Maximum 2 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
    InterventionType.ANGRY: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare frustrat sau supărat — sprâncene "
        "încruntate, tensiune facială. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj calm și empatic. "
        "Sugerează să respire adânc sau o pauză scurtă. "
        "Fii calm și reconfortant. "
        "Maximum 2 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
    InterventionType.FEARFUL: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare anxios sau speriat — ochi larg deschiși, "
        "tensiune facială. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj liniștitor și de suport. "
        "Ajută-l să se calmeze cu blândețe. "
        "Fii calm și reconfortant ca un prieten. "
        "Maximum 2 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
    InterventionType.DISGUSTED: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare deranjat sau nemulțumit. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj empatic și de suport. "
        "Întreabă cu blândețe dacă îl poți ajuta. "
        "Fii natural ca un prieten. "
        "Maximum 2 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
    InterventionType.BOTH: (
        "Ești Axl, asistentul wellness empatic din "
        "aplicația Coffee & Axl. "
        "Analiza video a detectat că utilizatorul "
        "pare atât obosit cât și stresat simultan. "
        "Nu aștepta o întrebare. Inițiază tu primul "
        "un mesaj de suport, odihnă și încurajare. "
        "Fii empatic și natural ca un prieten. "
        "Maximum 3 propoziții scurte. "
        "Nu menționa că ai analizat video."
    ),
}

TRIGGER_MESSAGES = {
    InterventionType.DROWSY: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru oboseala detectata"),
    InterventionType.SAD: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru tristete detectata"),
    InterventionType.ANGRY: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru furie sau frustrare detectata"),
    InterventionType.FEARFUL: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru anxietate sau frica detectata"),
    InterventionType.DISGUSTED: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru nemultumire detectata"),
    InterventionType.BOTH: (
        "[sistem intern] initiaza mesaj proactiv "
        "pentru oboseala si stres detectate simultan"),
}

# Cale IPC pentru pet daemon
CAFE_DIR = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
IPC_FILE = os.path.join(CAFE_DIR, "pet_ipc.txt")


# ─── Bridge ───────────────────────────────────────────────────────────────────

class AIInterventionBridge:
    """
    Bridge intre VisionEngine si ChatbotTab.
    La detectarea unei stari emotionale negative:
    1. Notifica pet_daemon -> bula ganditoare
    2. Injecteaza prompt in chatbot
    3. Declanseaza raspuns proactiv AI
    """

    def __init__(self):
        self._chatbot_tab:     object   = None
        self._on_intervention: callable = None
        self._enabled                   = True
        self._in_progress               = False
        self._on_message: callable      = None

    # ── Conectare ─────────────────────────────────────────────────────────────

    def set_chatbot_tab(self, chatbot_tab):
        self._chatbot_tab = chatbot_tab
        print("[AI BRIDGE] Conectat la ChatbotTab.")

    def set_intervention_callback(self,
                                   cb: callable):
        self._on_intervention = cb

    def set_message_callback(self, cb: callable):
        """
        Callback apelat cu mesajul AI generat.
        cb(itype: str, message: str)
        """
        self._on_message = cb

    def set_enabled(self, enabled: bool):
        self._enabled = enabled

    # ── Triggere publice ──────────────────────────────────────────────────────

    def trigger_drowsy(self):
        self._trigger(InterventionType.DROWSY)

    def trigger_sad(self):
        self._trigger(InterventionType.SAD)

    def trigger_angry(self):
        self._trigger(InterventionType.ANGRY)

    def trigger_fearful(self):
        self._trigger(InterventionType.FEARFUL)

    def trigger_disgusted(self):
        self._trigger(InterventionType.DISGUSTED)

    def trigger_both(self):
        self._trigger(InterventionType.BOTH)

    # ── Logica interna ────────────────────────────────────────────────────────

    def _trigger(self, itype: InterventionType):
        if not self._enabled:
            return

        if self._in_progress:
            print(f"[AI BRIDGE] Interventie in "
                  f"progres — ignoram {itype.value}.")
            return

        print(f"[AI BRIDGE] Interventie: "
              f"{itype.value}")

        if self._on_intervention:
            self._on_intervention(itype)

        threading.Thread(
            target=self._run_intervention,
            args=(itype,),
            daemon=True,
        ).start()

    def _run_intervention(self,
                           itype: InterventionType):
        self._in_progress = True
        try:
            self._notify_pet(itype.value)
            time.sleep(1.5)
            self._inject_prompt(itype)
        finally:
            self._in_progress = False

    # ── IPC catre pet ─────────────────────────────────────────────────────────

    def _notify_pet(self, itype: str):
        try:
            os.makedirs(CAFE_DIR, exist_ok=True)
            with open(IPC_FILE, "w") as f:
                f.write(f"thought_bubble:{itype}")
            print(f"[AI BRIDGE] IPC: "
                  f"thought_bubble:{itype}")
        except Exception as e:
            print(f"[AI BRIDGE] IPC eroare: {e}")

    # ── Injectare prompt ──────────────────────────────────────────────────────

    def _inject_prompt(self, itype: InterventionType):
        if not self._chatbot_tab:
            return
        try:
            self._chatbot_tab.trigger_ai_intervention(
                system_prompt=SYSTEM_PROMPTS[itype],
                trigger_msg=TRIGGER_MESSAGES[itype],
                itype=itype.value,
                on_done=lambda msg:
                self._send_message_to_pet(
                    itype.value, msg),
            )
        except Exception as e:
            print(f"[AI BRIDGE] Eroare: {e}")

    def _send_message_to_pet(self, itype: str,
                             message: str):
        """Trimite mesajul AI generat la pet_daemon prin IPC."""
        try:
            # Scurteaza mesajul pentru popup
            short = message[:120].strip()
            if len(message) > 120:
                short += "..."
            ipc_msg = f"ai_message:{itype}:{short}"
            with open(IPC_FILE, "w",
                      encoding="utf-8") as f:
                f.write(ipc_msg)
            print(f"[AI BRIDGE] Mesaj trimis la pet.")
        except Exception as e:
            print(f"[AI BRIDGE] IPC mesaj eroare: {e}")

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        return {
            "enabled":           self._enabled,
            "chatbot_connected": (
                self._chatbot_tab is not None),
            "in_progress":       self._in_progress,
        }