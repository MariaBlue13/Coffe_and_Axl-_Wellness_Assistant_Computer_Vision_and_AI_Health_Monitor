"""
Coffee & Axl - Wellness Engine
Timere pentru apa, ochi, miscare, respiratie.
Sesiuni interactive ghidate per tip si emotie.
Bazat pe tehnici validate: 20-20-20, box breathing,
4-6 breathing, palming, stretching.
"""

import threading
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable


# ─── Tipuri wellness ──────────────────────────────────────────────────────────

class WellnessType(Enum):
    WATER      = "water"
    EYES       = "eyes"
    MOVEMENT   = "movement"
    BREATHING  = "breathing"


# ─── Intervale default ────────────────────────────────────────────────────────

DEFAULT_INTERVALS = {
    WellnessType.WATER:     45 * 60,
    WellnessType.EYES:      20 * 60,
    WellnessType.MOVEMENT:  90 * 60,
    WellnessType.BREATHING: 60 * 60,
}

WELLNESS_META = {
    WellnessType.WATER: {
        "icon":      "💧",
        "titlu":     "Timpul pentru apă!",
        "scurt":     "Hidratează-te!",
        "culoare":   "#E3F2FD",
        "btn_color": "#2196F3",
    },
    WellnessType.EYES: {
        "icon":      "👁",
        "titlu":     "Pauza ochilor!",
        "scurt":     "5 exerciții pentru ochi",
        "culoare":   "#E8F5E9",
        "btn_color": "#4CAF50",
    },
    WellnessType.MOVEMENT: {
        "icon":      "🏃",
        "titlu":     "Timp de mișcare!",
        "scurt":     "Stretching rapid",
        "culoare":   "#FFF3E0",
        "btn_color": "#FF9800",
    },
    WellnessType.BREATHING: {
        "icon":      "🌬",
        "titlu":     "Exercițiu de respirație",
        "scurt":     "Relaxează-te",
        "culoare":   "#F3E5F5",
        "btn_color": "#9C27B0",
    },
}


# ─── Sesiuni respiratie ───────────────────────────────────────────────────────

BREATHING_META = {
    "calmare": {
        "nume":      "Respirație 4-6 (Calmare)",
        "icon":      "😌",
        "descriere": "Reduce anxietatea și încetinește "
                     "ritmul cardiac.",
        "cand":      "Stres, tensiune, înainte de somn",
        "emotii":    ["angry", "fearful", "both"],
        "culoare":   "#E3F2FD",
        "btn_color": "#1976D2",
    },
    "energizare": {
        "nume":      "Respirație profundă (Energizare)",
        "icon":      "⚡",
        "descriere": "Ideală când ești obosit sau "
                     "lipsit de energie.",
        "cand":      "Oboseală, pauze de lucru",
        "emotii":    ["drowsy", "both"],
        "culoare":   "#FFF8E1",
        "btn_color": "#F57F17",
    },
    "box": {
        "nume":      "Box Breathing (Relaxare profundă)",
        "icon":      "⬜",
        "descriere": "Tehnică echilibrată pentru "
                     "reset mental.",
        "cand":      "Tristețe, nemulțumire, "
                     "taskuri importante",
        "emotii":    ["sad", "disgusted"],
        "culoare":   "#E8F5E9",
        "btn_color": "#2E7D32",
    },
    "constienta": {
        "nume":      "Respirație lentă conștientă",
        "icon":      "🍃",
        "descriere": "Cea mai simplă metodă de a "
                     "reveni în prezent.",
        "cand":      "Oricând ai nevoie de claritate",
        "emotii":    ["surprised", "neutral"],
        "culoare":   "#F3E5F5",
        "btn_color": "#7B1FA2",
    },
    "antistres": {
        "nume":      "Expir prelungit (Anti-stres rapid)",
        "icon":      "🌊",
        "descriere": "Relaxare imediată în situații "
                     "tensionate.",
        "cand":      "Agitație, pauze calculator",
        "emotii":    ["pauza"],
        "culoare":   "#FBE9E7",
        "btn_color": "#BF360C",
    },
}

EMOTION_TO_BREATHING = {
    "angry":     "calmare",
    "fearful":   "calmare",
    "drowsy":    "energizare",
    "both":      "energizare",
    "sad":       "box",
    "disgusted": "box",
    "surprised": "constienta",
    "neutral":   "constienta",
    "pauza":     "antistres",
}

BREATHING_SESSIONS = {
    "calmare": [
        {
            "tip":    "intro",
            "text":   "Respirația 4-6 te ajută să te "
                      "calmezi. Expirul mai lung transmite "
                      "corpului semnalul de relaxare. 😌",
            "durata": 4,
            "icon":   "😌",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră lent pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră lent pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră lent pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră lent pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "mesaj",
            "text":   "Excelent! Simți cum tensiunea "
                      "s-a redus? 🌟",
            "durata": 4,
            "icon":   "🌟",
        },
    ],

    "energizare": [
        {
            "tip":    "intro",
            "text":   "Respirația profundă te energizează! "
                      "Ridică brațele la inspirație, "
                      "coboară-le la expirație. ⚡",
            "durata": 4,
            "icon":   "⚡",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră PROFUND — ridică brațele!",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră RAPID pe gură — "
                      "coboară brațele!",
            "durata": 2,
            "faza":   "expir_rapid",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră PROFUND — ridică brațele!",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră RAPID pe gură!",
            "durata": 2,
            "faza":   "expir_rapid",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră PROFUND!",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră RAPID!",
            "durata": 2,
            "faza":   "expir_rapid",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ultimul — inspiră PROFUND!",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră RAPID!",
            "durata": 2,
            "faza":   "expir_rapid",
            "icon":   "⬇️",
        },
        {
            "tip":    "mesaj",
            "text":   "Simți energia revenind? "
                      "Ești gata de acțiune! 💪",
            "durata": 4,
            "icon":   "💪",
        },
    ],

    "box": [
        {
            "tip":    "intro",
            "text":   "Box Breathing — 4 secunde "
                      "fiecare fază. Tehnica folosită "
                      "în situații de stres ridicat. ⬜",
            "durata": 4,
            "icon":   "⬜",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține 4 secunde...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră 4 secunde...",
            "durata": 4,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține 4 secunde...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține 4 secunde...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră 4 secunde...",
            "durata": 4,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține 4 secunde...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține 4 secunde...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră 4 secunde...",
            "durata": 4,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține ultima dată...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "mesaj",
            "text":   "Reset mental complet! "
                      "Ești pregătit pentru ce urmează. 🌟",
            "durata": 4,
            "icon":   "🌟",
        },
    ],

    "constienta": [
        {
            "tip":    "intro",
            "text":   "Respirația conștientă — "
                      "nu forța ritmul. "
                      "Doar observă aerul care intră "
                      "și iese. 🍃",
            "durata": 4,
            "icon":   "🍃",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră lent și natural...",
            "durata": 5,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră fără grabă...",
            "durata": 5,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră... observă aerul "
                      "care intră.",
            "durata": 5,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră... eliberează "
                      "orice gând.",
            "durata": 5,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră... ești prezent.",
            "durata": 5,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră... liniște.",
            "durata": 5,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră... claritate.",
            "durata": 5,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră complet...",
            "durata": 5,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "mesaj",
            "text":   "Ești prezent. Mintea ta "
                      "este clară acum. 🍃",
            "durata": 4,
            "icon":   "🍃",
        },
    ],

    "antistres": [
        {
            "tip":    "intro",
            "text":   "Expirul prelungit activează "
                      "sistemul nervos parasimpatic — "
                      "relaxare imediată! 🌊",
            "durata": 4,
            "icon":   "🌊",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră pe nas 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră LENT 8 secunde...",
            "durata": 8,
            "faza":   "expir_lung",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră pe nas 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră LENT 8 secunde...",
            "durata": 8,
            "faza":   "expir_lung",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră pe nas 4 secunde...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expirul final — lent "
                      "și complet...",
            "durata": 8,
            "faza":   "expir_lung",
            "icon":   "⬇️",
        },
        {
            "tip":    "mesaj",
            "text":   "Agitația s-a redus. "
                      "Simți diferența? 🌊",
            "durata": 4,
            "icon":   "🌊",
        },
    ],
}


# ─── Sesiuni wellness principale ──────────────────────────────────────────────

SESSIONS = {
    WellnessType.WATER: [
        {
            "tip":    "mesaj",
            "text":   "Hei! Au trecut 45 de minute. "
                      "E timpul să bei puțină apă! 💧",
            "durata": 3,
        },
        {
            "tip":    "actiune",
            "text":   "Ia paharul cu apă și bea cel "
                      "puțin 2-3 înghițituri mari.",
            "durata": 10,
            "icon":   "💧",
        },
        {
            "tip":    "mesaj",
            "text":   "Excelent! Hidratarea ajută "
                      "concentrarea și energia. ☕",
            "durata": 3,
        },
    ],

    WellnessType.EYES: [
        {
            "tip":    "mesaj",
            "text":   "Hai să facem împreună "
                      "5 exerciții pentru ochi! "
                      "Pregătit? 👁",
            "durata": 3,
        },

        # 1. Metoda 20-20-20
        {
            "tip":    "titlu",
            "text":   "1. Metoda 20-20-20",
            "durata": 2,
            "icon":   "👁",
        },
        {
            "tip":    "countdown",
            "text":   "Privește un obiect la 6 metri "
                      "depărtare. Menține privirea...",
            "durata": 20,
            "icon":   "🎯",
        },
        {
            "tip":    "mesaj",
            "text":   "Excelent! Ochii s-au relaxat. ✓",
            "durata": 2,
        },

        # 2. Schimbarea focalizarii
        {
            "tip":    "titlu",
            "text":   "2. Schimbarea focalizării",
            "durata": 2,
            "icon":   "🔍",
        },
        {
            "tip":    "actiune",
            "text":   "Ridică un deget la 25 cm de "
                      "ochi. Concentrează-te pe el "
                      "3 secunde.",
            "durata": 5,
            "icon":   "☝️",
        },
        {
            "tip":    "actiune",
            "text":   "Acum mută privirea la un "
                      "obiect depărtat. "
                      "Concentrează-te 3 secunde.",
            "durata": 5,
            "icon":   "🏔️",
        },
        {
            "tip":    "actiune",
            "text":   "Aproape... "
                      "concentrează-te pe deget.",
            "durata": 4,
            "icon":   "☝️",
        },
        {
            "tip":    "actiune",
            "text":   "Departe... privește în zare.",
            "durata": 4,
            "icon":   "🏔️",
        },
        {
            "tip":    "actiune",
            "text":   "Aproape...",
            "durata": 4,
            "icon":   "☝️",
        },
        {
            "tip":    "actiune",
            "text":   "Departe... ultimul rând.",
            "durata": 4,
            "icon":   "🏔️",
        },
        {
            "tip":    "mesaj",
            "text":   "Flexibilitatea ochilor — "
                      "îmbunătățită! ✓",
            "durata": 2,
        },

        # 3. Clipitul constient
        {
            "tip":    "titlu",
            "text":   "3. Clipitul conștient",
            "durata": 2,
            "icon":   "👁",
        },
        {
            "tip":    "actiune",
            "text":   "Închide ochii lent... "
                      "ține-i închiși 1-2 secunde... "
                      "deschide-i ușor. "
                      "Repetăm de 12 ori.",
            "durata": 3,
            "icon":   "👁",
        },
        {
            "tip":    "ritm",
            "text":   "Închide... ține... deschide...",
            "durata": 36,
            "icon":   "👁",
            "cicle":  3,
            "count":  12,
        },
        {
            "tip":    "mesaj",
            "text":   "Ochii tăi sunt hidratați! ✓",
            "durata": 2,
        },

        # 4. Miscarea ochilor
        {
            "tip":    "titlu",
            "text":   "4. Mișcările ochilor",
            "durata": 2,
            "icon":   "↕️",
        },
        {
            "tip":    "directie",
            "text":   "Privește în SUS... "
                      "fără a mișca capul.",
            "durata": 3,
            "icon":   "⬆️",
        },
        {
            "tip":    "directie",
            "text":   "Privește în JOS...",
            "durata": 3,
            "icon":   "⬇️",
        },
        {
            "tip":    "directie",
            "text":   "Privește la STÂNGA...",
            "durata": 3,
            "icon":   "⬅️",
        },
        {
            "tip":    "directie",
            "text":   "Privește la DREAPTA...",
            "durata": 3,
            "icon":   "➡️",
        },
        {
            "tip":    "directie",
            "text":   "Rotație circulară — "
                      "în sensul acelor de ceasornic, "
                      "lent...",
            "durata": 6,
            "icon":   "🔄",
        },
        {
            "tip":    "directie",
            "text":   "Rotație circulară — invers...",
            "durata": 6,
            "icon":   "🔄",
        },
        {
            "tip":    "mesaj",
            "text":   "Mușchii oculari relaxați! ✓",
            "durata": 2,
        },

        # 5. Palming
        {
            "tip":    "titlu",
            "text":   "5. Palming — relaxare profundă",
            "durata": 2,
            "icon":   "🤲",
        },
        {
            "tip":    "actiune",
            "text":   "Freacă palmele între ele "
                      "pentru a le încălzi...",
            "durata": 6,
            "icon":   "🤲",
        },
        {
            "tip":    "countdown",
            "text":   "Acoperă ușor ochii închiși "
                      "cu palmele calde. Nu apăsa. "
                      "Respiră calm în întuneric...",
            "durata": 30,
            "icon":   "🌑",
        },
        {
            "tip":    "mesaj",
            "text":   "Deschide ochii lent. "
                      "Simți relaxarea? 🌟",
            "durata": 4,
        },

        # Final
        {
            "tip":    "mesaj",
            "text":   "Toate cele 5 exerciții "
                      "completate! "
                      "Ochii tăi îți mulțumesc! 🎉",
            "durata": 4,
        },
    ],

    WellnessType.MOVEMENT: [
        {
            "tip":    "mesaj",
            "text":   "Ai stat jos 90 de minute! "
                      "Hai să facem mișcare "
                      "împreună! 🏃",
            "durata": 3,
        },
        {
            "tip":    "actiune",
            "text":   "Ridică-te în picioare și "
                      "întinde brațele spre tavan.",
            "durata": 8,
            "icon":   "🙆",
        },
        {
            "tip":    "actiune",
            "text":   "Rotește umerii înapoi de "
                      "5 ori, apoi înainte de 5 ori.",
            "durata": 12,
            "icon":   "🔄",
        },
        {
            "tip":    "actiune",
            "text":   "Înclină capul la stânga "
                      "5 secunde, apoi la dreapta "
                      "5 secunde.",
            "durata": 12,
            "icon":   "↔️",
        },
        {
            "tip":    "actiune",
            "text":   "Fă 10 genuflexiuni ușoare "
                      "sau plimbă-te prin cameră.",
            "durata": 20,
            "icon":   "🏃",
        },
        {
            "tip":    "actiune",
            "text":   "Scutură mâinile și degetele "
                      "pentru 5 secunde.",
            "durata": 8,
            "icon":   "🤲",
        },
        {
            "tip":    "mesaj",
            "text":   "Excelent! Te simți mai bine? "
                      "Continuă ziua cu energie! 💪",
            "durata": 4,
        },
    ],

    WellnessType.BREATHING: [
        {
            "tip":    "mesaj",
            "text":   "Hai să facem împreună un "
                      "exercițiu de respirație. 🌬",
            "durata": 3,
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține respirația...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Inspiră pe nas...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține respirația...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră lent pe gură...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ultimul ciclu — inspiră...",
            "durata": 4,
            "faza":   "inspir",
            "icon":   "⬆️",
        },
        {
            "tip":    "respiratie",
            "text":   "Ține...",
            "durata": 4,
            "faza":   "retine",
            "icon":   "⏸️",
        },
        {
            "tip":    "respiratie",
            "text":   "Expiră complet...",
            "durata": 6,
            "faza":   "expir",
            "icon":   "⬇️",
        },
        {
            "tip":    "mesaj",
            "text":   "Minunat! Te simți mai calm "
                      "și relaxat. 🌟",
            "durata": 4,
        },
    ],
}


# ─── Timer ────────────────────────────────────────────────────────────────────

@dataclass
class WellnessTimer:
    wtype:      WellnessType
    interval:   int
    enabled:    bool  = True
    last_fired: float = field(
        default_factory=time.time)

    def seconds_remaining(self) -> float:
        elapsed = time.time() - self.last_fired
        return max(0.0, self.interval - elapsed)

    def progress(self) -> float:
        elapsed = time.time() - self.last_fired
        return min(elapsed / self.interval, 1.0)

    def is_ready(self) -> bool:
        return (self.enabled
                and time.time() - self.last_fired
                >= self.interval)

    def reset(self):
        self.last_fired = time.time()


# ─── Engine ───────────────────────────────────────────────────────────────────

class WellnessEngine:

    def __init__(self,
                 on_reminder: Callable = None):
        self._on_reminder = on_reminder
        self._running     = False
        self._thread      = None

        self._timers = {
            wt: WellnessTimer(
                wtype    = wt,
                interval = DEFAULT_INTERVALS[wt],
            )
            for wt in WellnessType
        }

    def start(self):
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop,
            daemon=True,
        )
        self._thread.start()
        print("[WELLNESS] Engine pornit.")

    def stop(self):
        self._running = False

    def set_interval(self, wtype: WellnessType,
                     minutes: int):
        self._timers[wtype].interval = \
            minutes * 60
        self._timers[wtype].reset()

    def set_enabled(self, wtype: WellnessType,
                    enabled: bool):
        self._timers[wtype].enabled = enabled

    def reset_timer(self, wtype: WellnessType):
        self._timers[wtype].reset()
        print(f"[WELLNESS] Reset: {wtype.value}")

    def get_status(self) -> dict:
        return {
            wt: {
                "enabled":   t.enabled,
                "remaining": t.seconds_remaining(),
                "progress":  t.progress(),
                "interval":  t.interval,
            }
            for wt, t in self._timers.items()
        }

    def trigger_now(self, wtype: WellnessType):
        if self._on_reminder:
            self._on_reminder(wtype)
        self._timers[wtype].reset()

    def _loop(self):
        while self._running:
            for wtype, timer in \
                    self._timers.items():
                if timer.is_ready():
                    timer.reset()
                    print(f"[WELLNESS] "
                          f"Reminder: {wtype.value}")
                    if self._on_reminder:
                        self._on_reminder(wtype)
            time.sleep(30)