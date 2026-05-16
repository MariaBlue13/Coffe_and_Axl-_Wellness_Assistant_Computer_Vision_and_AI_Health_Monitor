"""
Coffee & Axl - Emotion Detector
Bazat pe Ekman (1977) - cele 6 emotii universale + oboseala.
Foloseste MediaPipe FaceLandmarker blendshapes + calcule geometrice.

Referinta: Ekman, P. Facial Expression.
In Nonverbal Behavior and Communication, 1977.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


# ─── Emotii universale Ekman ──────────────────────────────────────────────────

class EkmanEmotion(Enum):
    NEUTRAL   = "neutru"
    HAPPINESS = "fericire"
    SADNESS   = "tristete"
    ANGER     = "furie"
    FEAR      = "frica"
    DISGUST   = "dezgust"
    SURPRISE  = "surpriza"
    DROWSY    = "oboseala"   # non-Ekman, EAR


# ─── Praguri ──────────────────────────────────────────────────────────────────

# EAR (Eye Aspect Ratio)
# Ekman: ochii sunt indicator key pentru emotii
# Valori normale: 0.25-0.35
# Oboseala: < 0.22 (Soukupova & Cech, 2016)
EAR_DROWSY_THRESHOLD    = 0.22

# Praguri detectie emotii — calibrate pe FACS
# Ekman: intensitate minima pentru a conta
EMOTION_MIN_CONFIDENCE  = 0.18

# Tristete: colturi gura cazute
MOUTH_SAD_THRESHOLD     = -0.02

# Sprancene incruntate (furie/tristete)
BROW_FROWN_THRESHOLD    = 0.65

# Indecsi MediaPipe pleoape
LEFT_EYE_TOP    = [159, 158, 157]
LEFT_EYE_BOTTOM = [145, 153, 154]
LEFT_EYE_H      = [33, 133]

RIGHT_EYE_TOP    = [386, 385, 384]
RIGHT_EYE_BOTTOM = [374, 380, 381]
RIGHT_EYE_H      = [362, 263]

# Buze
MOUTH_LEFT   = 61
MOUTH_RIGHT  = 291
MOUTH_TOP    = 13
MOUTH_BOTTOM = 14

# Sprancene interioare
BROW_LEFT_INNER  = 107
BROW_RIGHT_INNER = 336


# ─── Rezultat ─────────────────────────────────────────────────────────────────

@dataclass
class EmotionMetrics:
    # Emotia principala detectata
    primary_emotion:   EkmanEmotion = EkmanEmotion.NEUTRAL
    confidence:        float        = 0.0

    # Scoruri individuale per emotie
    scores: dict = field(default_factory=lambda: {
        EkmanEmotion.HAPPINESS: 0.0,
        EkmanEmotion.SADNESS:   0.0,
        EkmanEmotion.ANGER:     0.0,
        EkmanEmotion.FEAR:      0.0,
        EkmanEmotion.DISGUST:   0.0,
        EkmanEmotion.SURPRISE:  0.0,
        EkmanEmotion.DROWSY:    0.0,
    })

    # Metrici geometrice
    ear_left:        float = 0.0
    ear_right:       float = 0.0
    ear_avg:         float = 0.0
    mouth_curve:     float = 0.0
    brow_inner_dist: float = 0.0

    # Flags
    is_drowsy:     bool = False
    is_negative:   bool = False
    face_detected: bool = False


# ─── EAR ──────────────────────────────────────────────────────────────────────

def compute_ear(landmarks, top_ids, bottom_ids,
                h_ids, img_w, img_h) -> float:
    if len(landmarks) < 400:
        return 0.30

    def pt(idx):
        p = landmarks[idx]
        return np.array([p.x * img_w, p.y * img_h])

    try:
        top_pts    = [pt(i) for i in top_ids]
        bottom_pts = [pt(i) for i in bottom_ids]
        h_pts      = [pt(i) for i in h_ids]

        vert_dists = [
            np.linalg.norm(top_pts[i] - bottom_pts[i])
            for i in range(min(
                len(top_pts), len(bottom_pts)))
        ]
        vert_mean = float(np.mean(vert_dists))
        horiz     = float(np.linalg.norm(
            h_pts[0] - h_pts[1]))

        if horiz < 1.0:
            return 0.30

        return float(np.clip(
            vert_mean / horiz, 0.0, 1.0))
    except Exception:
        return 0.30


def compute_ear_both(landmarks, img_w,
                     img_h) -> tuple[float, float]:
    ear_l = compute_ear(
        landmarks,
        LEFT_EYE_TOP, LEFT_EYE_BOTTOM,
        LEFT_EYE_H, img_w, img_h)
    ear_r = compute_ear(
        landmarks,
        RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM,
        RIGHT_EYE_H, img_w, img_h)
    return ear_l, ear_r


# ─── Curbura gura ─────────────────────────────────────────────────────────────

def compute_mouth_curve(landmarks, img_w,
                        img_h) -> float:
    if len(landmarks) < 300:
        return 0.0

    def pt(idx):
        p = landmarks[idx]
        return np.array([p.x * img_w, p.y * img_h])

    try:
        ml = pt(MOUTH_LEFT)
        mr = pt(MOUTH_RIGHT)
        mt = pt(MOUTH_TOP)
        mb = pt(MOUTH_BOTTOM)

        center_y  = (mt[1] + mb[1]) / 2.0
        corners_y = (ml[1] + mr[1]) / 2.0
        face_h    = img_h * 0.3

        if face_h < 1:
            return 0.0

        return float(np.clip(
            (center_y - corners_y) / face_h,
            -1.0, 1.0))
    except Exception:
        return 0.0


# ─── Sprancene ────────────────────────────────────────────────────────────────

def compute_brow_frown(landmarks, img_w,
                       img_h) -> float:
    if len(landmarks) < 400:
        return 1.0

    def pt(idx):
        p = landmarks[idx]
        return np.array([p.x * img_w, p.y * img_h])

    try:
        bl = pt(BROW_LEFT_INNER)
        br = pt(BROW_RIGHT_INNER)
        el = pt(LEFT_EYE_H[0])
        er = pt(RIGHT_EYE_H[1])

        brow_dist = float(np.linalg.norm(bl - br))
        eye_width = float(np.linalg.norm(el - er))

        if eye_width < 1:
            return 1.0

        return float(np.clip(
            brow_dist / eye_width, 0.0, 2.0))
    except Exception:
        return 1.0


# ─── Emotii din blendshapes (FACS-based) ─────────────────────────────────────

def compute_ekman_scores(blendshapes) -> dict:
    """
    Calculeaza scoruri pentru cele 6 emotii Ekman
    folosind blendshapes MediaPipe (FACS-based).

    Ekman (1977): fiecare emotie are un pattern
    specific de actiuni musculare (AU).
    MediaPipe blendshapes aproximeaza aceste AU.

    Referinta FACS -> Emotie:
    - Happiness:  AU6 + AU12 (obraz + zambet)
    - Sadness:    AU1 + AU4 + AU15 (sprancene + gura)
    - Anger:      AU4 + AU5 + AU23 (sprancene + buze)
    - Fear:       AU1 + AU2 + AU4 + AU20 + AU26
    - Disgust:    AU9 + AU15 + AU16
    - Surprise:   AU1 + AU2 + AU5 + AU26 + AU27
    """
    s = {bs.category_name: bs.score
         for bs in blendshapes}

    # ── Fericire (Happiness) ──────────────────────────────────────────────────
    # AU6: cheekSquint, AU12: mouthSmile
    happiness = (
        s.get("mouthSmileLeft",   0) * 0.35 +
        s.get("mouthSmileRight",  0) * 0.35 +
        s.get("cheekSquintLeft",  0) * 0.15 +
        s.get("cheekSquintRight", 0) * 0.15
    )

    # ── Tristete (Sadness) ────────────────────────────────────────────────────
    # AU1: browInnerUp, AU4: browDown, AU15: mouthFrown
    sadness = (
        s.get("mouthFrownLeft",  0) * 0.25 +
        s.get("mouthFrownRight", 0) * 0.25 +
        s.get("browInnerUp",     0) * 0.25 +
        s.get("mouthPucker",     0) * 0.15 +
        s.get("cheekPuff",       0) * 0.10
    )

    # ── Furie (Anger) ─────────────────────────────────────────────────────────
    # AU4: browDown, AU5: upperLidRaiser, AU23: lipTightener
    anger = (
        s.get("browDownLeft",     0) * 0.30 +
        s.get("browDownRight",    0) * 0.30 +
        s.get("noseSneerLeft",    0) * 0.15 +
        s.get("noseSneerRight",   0) * 0.15 +
        s.get("mouthPressLeft",   0) * 0.05 +
        s.get("mouthPressRight",  0) * 0.05
    )

    # ── Frica (Fear) ──────────────────────────────────────────────────────────
    # AU1+2: browRaise, AU4: browDown, AU20: lipStretch
    fear = (
        s.get("eyeWideLeft",       0) * 0.20 +
        s.get("eyeWideRight",      0) * 0.20 +
        s.get("browInnerUp",       0) * 0.20 +
        s.get("mouthStretchLeft",  0) * 0.15 +
        s.get("mouthStretchRight", 0) * 0.15 +
        s.get("jawOpen",           0) * 0.10
    )

    # ── Dezgust (Disgust) ─────────────────────────────────────────────────────
    # AU9: noseWrinkle, AU15: mouthFrown, AU16: lowerLipDepress
    disgust = (
        s.get("noseSneerLeft",    0) * 0.30 +
        s.get("noseSneerRight",   0) * 0.30 +
        s.get("mouthFrownLeft",   0) * 0.15 +
        s.get("mouthFrownRight",  0) * 0.15 +
        s.get("mouthShrugLower",  0) * 0.10
    )

    # ── Surpriza (Surprise) ───────────────────────────────────────────────────
    # AU1+2: browRaise, AU5: eyeWide, AU26+27: jawOpen
    surprise = (
        s.get("jawOpen",          0) * 0.35 +
        s.get("eyeWideLeft",      0) * 0.20 +
        s.get("eyeWideRight",     0) * 0.20 +
        s.get("browOuterUpLeft",  0) * 0.10 +
        s.get("browOuterUpRight", 0) * 0.10 +
        s.get("browInnerUp",      0) * 0.05
    )

    return {
        EkmanEmotion.HAPPINESS: float(happiness),
        EkmanEmotion.SADNESS:   float(sadness),
        EkmanEmotion.ANGER:     float(anger),
        EkmanEmotion.FEAR:      float(fear),
        EkmanEmotion.DISGUST:   float(disgust),
        EkmanEmotion.SURPRISE:  float(surprise),
    }


# ─── Calcul complet ───────────────────────────────────────────────────────────

def compute_emotion_metrics(landmarks, img_w,
                             img_h,
                             blendshapes=None
                             ) -> EmotionMetrics:
    m = EmotionMetrics()

    if not landmarks or len(landmarks) < 400:
        return m

    m.face_detected = True

    # EAR — oboseala
    m.ear_left, m.ear_right = compute_ear_both(
        landmarks, img_w, img_h)
    m.ear_avg   = (m.ear_left + m.ear_right) / 2.0
    m.is_drowsy = m.ear_avg < EAR_DROWSY_THRESHOLD

    # Geometrie
    m.mouth_curve     = compute_mouth_curve(
        landmarks, img_w, img_h)
    m.brow_inner_dist = compute_brow_frown(
        landmarks, img_w, img_h)

    # Scoruri Ekman din blendshapes
    if blendshapes:
        ekman_scores = compute_ekman_scores(
            blendshapes)
    else:
        # Fallback geometric daca nu avem blendshapes
        ekman_scores = {
            EkmanEmotion.HAPPINESS: 0.0,
            EkmanEmotion.SADNESS:
                max(0.0, -m.mouth_curve * 5),
            EkmanEmotion.ANGER:
                max(0.0,
                    (0.65 - m.brow_inner_dist) * 2),
            EkmanEmotion.FEAR:     0.0,
            EkmanEmotion.DISGUST:  0.0,
            EkmanEmotion.SURPRISE: 0.0,
        }

    # Adauga oboseala ca emotie separata
    drowsy_score = max(
        0.0,
        (EAR_DROWSY_THRESHOLD - m.ear_avg)
        / EAR_DROWSY_THRESHOLD
    ) if m.is_drowsy else 0.0

    m.scores = {**ekman_scores,
                EkmanEmotion.DROWSY: drowsy_score}

    # Determina emotia dominanta
    best_emotion = max(
        ekman_scores, key=ekman_scores.get)
    best_score   = ekman_scores[best_emotion]

    if m.is_drowsy and drowsy_score > best_score:
        m.primary_emotion = EkmanEmotion.DROWSY
        m.confidence      = drowsy_score
    elif best_score >= EMOTION_MIN_CONFIDENCE:
        m.primary_emotion = best_emotion
        m.confidence      = min(
            best_score * 1.5, 1.0)
    else:
        m.primary_emotion = EkmanEmotion.NEUTRAL
        m.confidence      = 1.0 - best_score

    # Flag negativ — emotii care necesita interventie
    negative = {
        EkmanEmotion.SADNESS,
        EkmanEmotion.FEAR,
        EkmanEmotion.ANGER,
        EkmanEmotion.DISGUST,
        EkmanEmotion.DROWSY,
    }
    m.is_negative = (
        m.primary_emotion in negative
        and m.confidence >= EMOTION_MIN_CONFIDENCE
    )

    return m


def format_debug(m: EmotionMetrics) -> str:
    lines = [
        f"Emotie principala: "
        f"{m.primary_emotion.value} "
        f"({m.confidence:.0%})",
        f"EAR: {m.ear_avg:.3f}"
        f"  {'[OBOSIT]' if m.is_drowsy else 'OK'}",
        f"Curbura gura: {m.mouth_curve:+.4f}",
        f"Dist sprancene: {m.brow_inner_dist:.3f}",
        "",
        "Scoruri Ekman:",
    ]
    for emotion, score in m.scores.items():
        bar = "█" * int(score * 20)
        lines.append(
            f"  {emotion.value:12}: "
            f"{score:.3f} {bar}")
    return "\n".join(lines)