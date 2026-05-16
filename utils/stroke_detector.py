"""
Coffee & Axl - Stroke Detector
Pasul 1: Logica matematica pentru detectia asimetriei buzelor.

Landmark-uri MediaPipe folosite pentru buze:
  - 61  : coltul stang al gurii
  - 291 : coltul drept al gurii
  - 0   : centrul buzei superioare
  - 17  : centrul buzei inferioare
  - 13  : mijlocul buzei superioare (interior)
  - 14  : mijlocul buzei inferioare (interior)
  - 78  : buza superioara stanga (interior)
  - 308 : buza superioara dreapta (interior)
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class LipSymmetryResult:
    """Rezultatul analizei de simetrie a buzelor."""

    # Axa orizontala
    left_height:       float = 0.0   # inaltimea colt stang fata de centru
    right_height:      float = 0.0   # inaltimea colt drept fata de centru
    horizontal_dev:    float = 0.0   # deviatia orizontala (0-1)

    # Axa verticala
    left_width:        float = 0.0   # latimea jumatatii stangi
    right_width:       float = 0.0   # latimea jumatatii drepte
    vertical_dev:      float = 0.0   # deviatia verticala (0-1)

    # Scor combinat
    asymmetry_score:   float = 0.0   # 0 = perfect simetric, 1 = asimetrie maxima
    is_severe:         bool  = False  # True daca depaseste pragul AVC

    # Coordonate pentru vizualizare
    center_x:          float = 0.0
    center_y:          float = 0.0
    left_corner:       tuple = (0, 0)
    right_corner:      tuple = (0, 0)


# Prag dupa care consideram asimetria severa (AVC posibil)
SEVERE_THRESHOLD = 0.35


def extract_lip_landmarks(landmarks: list,
                           img_w: int,
                           img_h: int) -> dict:
    """
    Extrage coordonatele pixeli pentru landmark-urile buzelor.
    landmarks = lista de puncte MediaPipe (478 total).
    """
    if len(landmarks) < 400:
        return {}

    def pt(idx: int) -> tuple:
        p = landmarks[idx]
        return (p.x * img_w, p.y * img_h)

    return {
        "corner_left":    pt(61),   # coltul stang
        "corner_right":   pt(291),  # coltul drept
        "top_center":     pt(0),    # centrul buzei superioare
        "bottom_center":  pt(17),   # centrul buzei inferioare
        "top_mid":        pt(13),   # mijloc buza superioara interior
        "bottom_mid":     pt(14),   # mijloc buza inferioara interior
        "top_left":       pt(78),   # buza sup stanga interior
        "top_right":      pt(308),  # buza sup dreapta interior
    }


def compute_lip_symmetry(lip_pts: dict) -> LipSymmetryResult:
    """
    Calculeaza simetria buzelor pe 2 axe.

    AXA ORIZONTALA:
      Centrul gurii = mijlocul dintre cele 2 colturi.
      Comparam inaltimea (Y) coltului stang vs drept fata de centru.
      Deviatia mare = un colt cazut = semn AVC.

    AXA VERTICALA:
      Impartim gura in jumatatea stanga si dreapta.
      Comparam latimea (X) fiecarei jumatati.
      Deviatia mare = gura trasa intr-o parte = semn AVC.
    """
    result = LipSymmetryResult()

    if not lip_pts:
        return result

    cl = np.array(lip_pts["corner_left"])    # colt stang
    cr = np.array(lip_pts["corner_right"])   # colt drept
    tc = np.array(lip_pts["top_center"])     # centru sus
    bc = np.array(lip_pts["bottom_center"])  # centru jos

    # ── Centrul gurii ─────────────────────────────────────────────────────────
    mouth_center = (cl + cr) / 2.0
    result.center_x    = float(mouth_center[0])
    result.center_y    = float(mouth_center[1])
    result.left_corner  = (int(cl[0]), int(cl[1]))
    result.right_corner = (int(cr[0]), int(cr[1]))

    # Latimea totala a gurii (normalizare)
    mouth_width = float(np.linalg.norm(cr - cl))
    if mouth_width < 1.0:
        return result

    # ── AXA ORIZONTALA ────────────────────────────────────────────────────────
    # Inaltimea fiecarui colt fata de centrul orizontal al gurii
    # Un colt cazut (Y mai mare) = paralizie faciala pe acea parte
    center_y = mouth_center[1]

    left_height  = center_y - cl[1]   # pozitiv = coltul e DEASUPRA centrului
    right_height = center_y - cr[1]

    result.left_height  = float(left_height)
    result.right_height = float(right_height)

    # Deviatia orizontala = diferenta normalizata la latimea gurii
    horiz_diff = abs(left_height - right_height)
    result.horizontal_dev = float(
        np.clip(horiz_diff / mouth_width, 0, 1))

    # ── AXA VERTICALA ─────────────────────────────────────────────────────────
    # Latimea jumatatii stangi vs drepte fata de centrul vertical
    center_x = mouth_center[0]

    left_width  = center_x - cl[0]   # distanta de la centru la coltul stang
    right_width = cr[0] - center_x   # distanta de la centru la coltul drept

    result.left_width  = float(left_width)
    result.right_width = float(right_width)

    # Deviatia verticala = cat de mult e gura trasa intr-o parte
    total_width  = left_width + right_width
    if total_width > 0:
        vert_diff = abs(left_width - right_width)
        result.vertical_dev = float(
            np.clip(vert_diff / total_width, 0, 1))

    # ── SCOR COMBINAT ─────────────────────────────────────────────────────────
    # Ponderi: axa orizontala (cazatura colt) e mai importanta pentru AVC
    result.asymmetry_score = float(
        result.horizontal_dev * 0.65 +
        result.vertical_dev   * 0.35
    )

    result.is_severe = result.asymmetry_score > SEVERE_THRESHOLD

    return result


def format_debug(result: LipSymmetryResult) -> str:
    """Text formatat pentru debug — afisat in consola sau UI."""
    lines = [
        f"Asimetrie buze     : {result.asymmetry_score:.4f}"
        f"  {'⚠ SEVERA' if result.is_severe else 'OK'}",
        f"  Deviatie orizontala: {result.horizontal_dev:.4f}"
        f"  (colt stang: {result.left_height:+.1f}px,"
        f" drept: {result.right_height:+.1f}px)",
        f"  Deviatie verticala : {result.vertical_dev:.4f}"
        f"  (stanga: {result.left_width:.1f}px,"
        f" dreapta: {result.right_width:.1f}px)",
    ]
    return "\n".join(lines)