"""
Coffee & Axl - BEFAST Analyzer
Analiza video pentru testele F (zambet) si A (brate) pe GPU.
Face Mesh + Pose Landmarker cu MediaPipe Tasks API.
"""

import cv2
import numpy as np
import mediapipe as mp
import time
import os
from dataclasses import dataclass, field
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


# ─── Cai modele ───────────────────────────────────────────────────────────────

FACE_MODEL_PATH = os.path.join(
    os.path.expanduser("~"), ".coffee_axl",
    "face_landmarker.task"
)
POSE_MODEL_PATH = os.path.join(
    os.path.expanduser("~"), ".coffee_axl",
    "pose_landmarker.task"
)


# ─── Rezultate analiza ────────────────────────────────────────────────────────

@dataclass
class SmileAnalysis:
    """Rezultatul analizei testului F — zambet."""
    asymmetry_score:   float = 0.0   # 0=simetric, 1=maxim asimetric
    mouth_asym:        float = 0.0   # asimetrie buze
    eye_asym:          float = 0.0   # asimetrie ochi
    brow_asym:         float = 0.0   # asimetrie sprancene
    left_mouth_height: float = 0.0   # inaltimea coltului stang
    right_mouth_height:float = 0.0   # inaltimea coltului drept
    is_severe:         bool  = False  # depaseste pragul
    face_detected:     bool  = False
    landmarks:         list  = field(default_factory=list)
    blendshapes:       dict  = field(default_factory=dict)


@dataclass
class ArmsAnalysis:
    """Rezultatul analizei testului A — brate."""
    left_wrist_y:   float = 0.0   # pozitia Y incheietura stanga
    right_wrist_y:  float = 0.0   # pozitia Y incheietura dreapta
    left_shoulder_y:float = 0.0
    right_shoulder_y:float= 0.0
    left_arm_raised: bool = False  # bratul stang e ridicat
    right_arm_raised:bool = False  # bratul drept e ridicat
    height_diff:     float = 0.0  # diferenta intre brate
    arm_drop_detected:bool = False # un brat a cazut
    pose_detected:   bool  = False
    landmarks:       list  = field(default_factory=list)


# ─── Analyzer principal ───────────────────────────────────────────────────────

class BEFASTAnalyzer:
    """
    Analizeaza frame-uri video pentru testele F si A.
    Foloseste GPU prin OpenCV CUDA pentru preprocesare
    si MediaPipe XNNPACK pentru inferenta.
    """

    # Praguri
    SMILE_THRESHOLD     = 0.28   # asimetrie zambet
    ARM_DROP_THRESHOLD  = 0.08   # diferenta normalizata brate
    ARM_RAISE_THRESHOLD = 0.15   # cat de sus trebuie ridicat

    def __init__(self):
        self._face_landmarker = None
        self._pose_landmarker = None
        self._has_cuda        = False
        self._frame_ts        = 0

        self._init_cuda()
        self._init_face()
        self._init_pose()

    def _init_cuda(self):
        """Verifica CUDA pentru preprocesare OpenCV."""
        try:
            import torch
            if torch.cuda.is_available():
                self._has_cuda = True
                print("[ANALYZER] CUDA activ pentru "
                      "preprocesare video.")
        except ImportError:
            pass

    def _init_face(self):
        if not os.path.exists(FACE_MODEL_PATH):
            print(f"[ANALYZER] Face model lips: "
                  f"{FACE_MODEL_PATH}")
            return
        try:
            options = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=FACE_MODEL_PATH),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_face_blendshapes=True,
            )
            self._face_landmarker = \
                mp_vision.FaceLandmarker\
                .create_from_options(options)
            print("[ANALYZER] Face Landmarker activ.")
        except Exception as e:
            print(f"[ANALYZER] Face init eroare: {e}")

    def _init_pose(self):
        if not os.path.exists(POSE_MODEL_PATH):
            print(f"[ANALYZER] Pose model lips: "
                  f"{POSE_MODEL_PATH}")
            return
        try:
            options = mp_vision.PoseLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=POSE_MODEL_PATH),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_poses=1,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._pose_landmarker = \
                mp_vision.PoseLandmarker\
                .create_from_options(options)
            print("[ANALYZER] Pose Landmarker activ.")
        except Exception as e:
            print(f"[ANALYZER] Pose init eroare: {e}")

    def close(self):
        if self._face_landmarker:
            self._face_landmarker.close()
        if self._pose_landmarker:
            self._pose_landmarker.close()

    # ── Preprocesare frame ────────────────────────────────────────────────────

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Converteste BGR->RGB, optional pe CUDA."""
        if self._has_cuda:
            try:
                gpu = cv2.cuda_GpuMat()
                gpu.upload(frame)
                gpu_rgb = cv2.cuda.cvtColor(
                    gpu, cv2.COLOR_BGR2RGB)
                return gpu_rgb.download()
            except Exception:
                pass
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def _to_mp_image(self,
                     rgb: np.ndarray) -> mp.Image:
        return mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

    def _ts(self) -> int:
        """Timestamp unic in ms pentru MediaPipe VIDEO mode."""
        self._frame_ts += 33   # ~30fps
        return self._frame_ts

    # ── Analiza zambet (Test F) ───────────────────────────────────────────────

    def analyze_smile(self,
                      frame: np.ndarray) -> SmileAnalysis:
        """
        Analizeaza asimetria faciala completa:
        buze + ochi + sprancene.
        """
        result = SmileAnalysis()

        if not self._face_landmarker:
            return result

        try:
            rgb       = self._preprocess(frame)
            mp_img    = self._to_mp_image(rgb)
            detection = self._face_landmarker\
                .detect_for_video(mp_img, self._ts())
        except Exception as e:
            print(f"[ANALYZER] Face detect eroare: {e}")
            return result

        if not detection.face_landmarks:
            return result

        result.face_detected = True
        h, w = frame.shape[:2]
        lm   = detection.face_landmarks[0]
        pts  = [(p.x * w, p.y * h) for p in lm]
        result.landmarks = [(int(x), int(y))
                            for x, y in pts]

        # Blendshapes pentru context
        if detection.face_blendshapes:
            result.blendshapes = {
                bs.category_name: bs.score
                for bs in detection.face_blendshapes[0]
            }

        # ── Asimetrie buze ────────────────────────────────────────────────────
        # Colturile gurii: 61 (stang), 291 (drept)
        # Centrul gurii: 13 (sus interior), 14 (jos interior)
        if len(pts) > 291:
            cl = np.array(pts[61])   # colt stang
            cr = np.array(pts[291])  # colt drept
            mc = (cl + cr) / 2.0     # centru gura

            # Inaltimea relativa a fiecarui colt
            # fata de centrul gurii
            lh = mc[1] - cl[1]   # pozitiv = colt sus
            rh = mc[1] - cr[1]

            result.left_mouth_height  = float(lh)
            result.right_mouth_height = float(rh)

            mouth_w = float(np.linalg.norm(cr - cl))
            if mouth_w > 1:
                result.mouth_asym = float(
                    np.clip(abs(lh - rh) / mouth_w,
                            0, 1))

        # ── Asimetrie ochi ────────────────────────────────────────────────────
        # Ochi stang: 159 (sus), 145 (jos)
        # Ochi drept: 386 (sus), 374 (jos)
        if len(pts) > 386:
            le_h = abs(pts[159][1] - pts[145][1])
            re_h = abs(pts[386][1] - pts[374][1])
            total_eye = le_h + re_h
            if total_eye > 0:
                result.eye_asym = float(
                    np.clip(
                        abs(le_h - re_h) / total_eye,
                        0, 1))

        # ── Asimetrie sprancene ───────────────────────────────────────────────
        # Spranceana stanga: 65, dreapta: 295
        # Reper nas: 4
        if len(pts) > 295:
            nose_y = pts[4][1]
            lb_y   = pts[65][1]   # spranceana stanga
            rb_y   = pts[295][1]  # spranceana dreapta

            face_h = h * 0.3
            if face_h > 0:
                ld = (nose_y - lb_y) / face_h
                rd = (nose_y - rb_y) / face_h
                result.brow_asym = float(
                    np.clip(abs(ld - rd), 0, 1))

        # ── Scor combinat ─────────────────────────────────────────────────────
        result.asymmetry_score = float(
            result.mouth_asym * 0.50 +
            result.eye_asym   * 0.30 +
            result.brow_asym  * 0.20
        )
        result.is_severe = (
            result.asymmetry_score > self.SMILE_THRESHOLD
        )

        return result

    # ── Analiza brate (Test A) ────────────────────────────────────────────────

    def analyze_arms(self,
                     frame: np.ndarray) -> ArmsAnalysis:
        """
        Detecteaza pozitia bratelor cu Pose Landmarker.
        Verifica daca ambele brate sunt ridicate si
        daca unul cade mai jos decat celalalt.

        Landmark-uri Pose relevante:
          11 = umar stang, 12 = umar drept
          13 = cot stang,  14 = cot drept
          15 = incheietura stanga, 16 = incheietura dreapta
        """
        result = ArmsAnalysis()

        if not self._pose_landmarker:
            return result

        try:
            rgb       = self._preprocess(frame)
            mp_img    = self._to_mp_image(rgb)
            detection = self._pose_landmarker\
                .detect_for_video(mp_img, self._ts())
        except Exception as e:
            print(f"[ANALYZER] Pose detect eroare: {e}")
            return result

        if not detection.pose_landmarks:
            return result

        result.pose_detected = True
        h, w = frame.shape[:2]
        lm   = detection.pose_landmarks[0]
        pts  = [(p.x * w, p.y * h) for p in lm]
        result.landmarks = [(int(x), int(y))
                            for x, y in pts]

        if len(pts) < 17:
            return result

        # Coordonate normalizate (Y: 0=sus, 1=jos)
        ls_y  = lm[11].y   # umar stang
        rs_y  = lm[12].y   # umar drept
        lw_y  = lm[15].y   # incheietura stanga
        rw_y  = lm[16].y   # incheietura dreapta

        result.left_shoulder_y  = float(ls_y)
        result.right_shoulder_y = float(rs_y)
        result.left_wrist_y     = float(lw_y)
        result.right_wrist_y    = float(rw_y)

        # Bratul e ridicat daca incheietura e
        # deasupra umarului (Y mai mic = mai sus)
        result.left_arm_raised  = (
            lw_y < ls_y - self.ARM_RAISE_THRESHOLD)
        result.right_arm_raised = (
            rw_y < rs_y - self.ARM_RAISE_THRESHOLD)

        # Diferenta dintre cele doua incheieturi
        # normalizata la inaltimea corpului
        body_h = abs(lm[0].y - lm[27].y)  # cap - glezna
        if body_h > 0:
            result.height_diff = float(
                abs(lw_y - rw_y) / body_h)
        else:
            result.height_diff = float(abs(lw_y - rw_y))

        # Un brat a cazut daca diferenta e semnificativa
        # si cel putin unul era ridicat
        if (result.left_arm_raised
                or result.right_arm_raised):
            result.arm_drop_detected = (
                result.height_diff > self.ARM_DROP_THRESHOLD
            )

        return result

    # ── Overlay vizual ────────────────────────────────────────────────────────

    def draw_smile_overlay(
            self, frame: np.ndarray,
            analysis: SmileAnalysis) -> np.ndarray:
        """Deseneaza landmark-urile faciale si scorurile."""
        if not analysis.face_detected:
            cv2.putText(
                frame, "Fata nedetectata",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (100, 100, 255), 2)
            return frame

        pts = analysis.landmarks

        # ── Puncte faciale ────────────────────────────────────────────────────
        key_pts = {4, 33, 263, 61, 291,
                   159, 386, 145, 374,
                   65, 295, 13, 14}
        for idx, (x, y) in enumerate(pts):
            if idx in key_pts:
                cv2.circle(frame, (x, y), 5,
                           (0, 255, 255), -1)
            else:
                cv2.circle(frame, (x, y), 1,
                           (180, 180, 180), -1)

        # ── Conexiuni ─────────────────────────────────────────────────────────
        # Contur fata
        fc = [10,338,297,332,284,251,389,356,454,
              323,361,288,397,365,379,378,400,377,
              152,148,176,149,150,136,172,58,132,
              93,234,127,162,21,54,103,67,109,10]
        color = ((0, 0, 255)
                 if analysis.is_severe
                 else (0, 220, 100))
        for i in range(len(fc) - 1):
            a, b = fc[i], fc[i+1]
            if a < len(pts) and b < len(pts):
                cv2.line(frame, pts[a], pts[b],
                         color, 1, cv2.LINE_AA)

        # Ochi
        for eye in [[33,160,158,133,153,144,33],
                    [362,385,387,263,373,380,362]]:
            for i in range(len(eye)-1):
                a, b = eye[i], eye[i+1]
                if a < len(pts) and b < len(pts):
                    cv2.line(frame, pts[a], pts[b],
                             (0, 255, 200), 1,
                             cv2.LINE_AA)

        # Gura
        mouth = [61,185,40,39,37,0,267,269,270,
                 409,291,375,321,405,314,17,
                 84,181,91,146,61]
        m_color = ((0, 0, 255)
                   if analysis.mouth_asym > 0.20
                   else (255, 180, 100))
        for i in range(len(mouth)-1):
            a, b = mouth[i], mouth[i+1]
            if a < len(pts) and b < len(pts):
                cv2.line(frame, pts[a], pts[b],
                         m_color, 2, cv2.LINE_AA)

        # Sprancene
        for brow in [[55,65,52,53,46],
                     [285,295,282,283,276]]:
            b_color = ((0, 100, 255)
                       if analysis.brow_asym > 0.15
                       else (200, 150, 255))
            for i in range(len(brow)-1):
                a, b = brow[i], brow[i+1]
                if a < len(pts) and b < len(pts):
                    cv2.line(frame, pts[a], pts[b],
                             b_color, 2, cv2.LINE_AA)

        # Axa ochi
        if len(pts) > 263:
            cv2.line(frame, pts[33], pts[263],
                     (255, 255, 0), 2, cv2.LINE_AA)

        # Marker colturi gura
        if len(pts) > 291:
            lc = (0, 0, 255) if (
                analysis.mouth_asym > 0.20
            ) else (0, 255, 0)
            cv2.circle(frame, pts[61],  8, lc, 2)
            cv2.circle(frame, pts[291], 8, lc, 2)
            # Linie intre colturi
            cv2.line(frame, pts[61], pts[291],
                     lc, 1, cv2.LINE_AA)

        # ── Text overlay ──────────────────────────────────────────────────────
        lines = [
            (f"Scor total  : "
             f"{analysis.asymmetry_score:.4f}"
             f"  {'[SEVER]' if analysis.is_severe else 'OK'}",
             (0, 0, 255) if analysis.is_severe
             else (0, 220, 100)),
            (f"Asim. buze  : {analysis.mouth_asym:.4f}",
             (0, 180, 255)
             if analysis.mouth_asym > 0.20
             else (180, 255, 180)),
            (f"Asim. ochi  : {analysis.eye_asym:.4f}",
             (0, 180, 255)
             if analysis.eye_asym > 0.15
             else (180, 255, 180)),
            (f"Asim. spr.  : {analysis.brow_asym:.4f}",
             (0, 180, 255)
             if analysis.brow_asym > 0.15
             else (180, 255, 180)),
        ]

        ov = frame.copy()
        cv2.rectangle(ov, (0, 0),
                      (310, len(lines)*24+16),
                      (0, 0, 0), -1)
        cv2.addWeighted(ov, 0.55, frame, 0.45, 0, frame)

        for i, (text, col) in enumerate(lines):
            cv2.putText(frame, text, (8, 22 + i*24),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.52, col, 1, cv2.LINE_AA)

        # Banner urgenta
        if analysis.is_severe:
            cv2.rectangle(
                frame,
                (0, frame.shape[0]-36),
                (frame.shape[1], frame.shape[0]),
                (0, 0, 200), -1)
            cv2.putText(
                frame,
                "  ATENTIE: ASIMETRIE SEVERA DETECTATA",
                (8, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1,
                cv2.LINE_AA)

        return frame

    def draw_arms_overlay(
            self, frame: np.ndarray,
            analysis: ArmsAnalysis) -> np.ndarray:
        """Deseneaza skeleton-ul bratelor si scorurile."""
        if not analysis.pose_detected:
            cv2.putText(
                frame, "Corp nedetectat",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (100, 100, 255), 2)
            return frame

        pts = analysis.landmarks
        h, w = frame.shape[:2]

        # Conexiuni relevante pentru brate
        connections = [
            (11, 13), (13, 15),   # brat stang
            (12, 14), (14, 16),   # brat drept
            (11, 12),             # umeri
        ]

        for a, b in connections:
            if a < len(pts) and b < len(pts):
                # Culoare in functie de brat
                if a in (11, 13, 15) or b in (11, 13, 15):
                    # Brat stang
                    col = ((0, 0, 255)
                           if not analysis.left_arm_raised
                           else (0, 255, 100))
                else:
                    # Brat drept
                    col = ((0, 0, 255)
                           if not analysis.right_arm_raised
                           else (0, 255, 100))

                cv2.line(frame, pts[a], pts[b],
                         col, 3, cv2.LINE_AA)

        # Puncte cheie
        key_pose = {11, 12, 13, 14, 15, 16}
        for idx in key_pose:
            if idx < len(pts):
                col = (0, 255, 100) \
                    if idx in (15, 16) \
                    else (255, 200, 0)
                cv2.circle(frame, pts[idx], 8,
                           col, -1)
                cv2.circle(frame, pts[idx], 10,
                           (255, 255, 255), 2)

        # Linie orizontala de referinta intre incheieturi
        if (15 < len(pts) and 16 < len(pts)):
            lw = pts[15]
            rw = pts[16]
            diff_px = abs(lw[1] - rw[1])

            line_col = ((0, 0, 255)
                        if analysis.arm_drop_detected
                        else (0, 255, 255))
            cv2.line(frame, lw, rw,
                     line_col, 2, cv2.LINE_AA)

            # Eticheta diferenta
            mid_x = (lw[0] + rw[0]) // 2
            mid_y = (lw[1] + rw[1]) // 2
            cv2.putText(
                frame,
                f"diff: {diff_px}px",
                (mid_x - 30, mid_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45, line_col, 1, cv2.LINE_AA)

        # ── Text overlay ──────────────────────────────────────────────────────
        l_status = ("RIDICAT" if analysis.left_arm_raised
                    else "CAZUT/JOS")
        r_status = ("RIDICAT" if analysis.right_arm_raised
                    else "CAZUT/JOS")

        lines = [
            (f"Brat stang  : {l_status}",
             (0, 255, 100)
             if analysis.left_arm_raised
             else (0, 0, 255)),
            (f"Brat drept  : {r_status}",
             (0, 255, 100)
             if analysis.right_arm_raised
             else (0, 0, 255)),
            (f"Diferenta   : "
             f"{analysis.height_diff:.4f}"
             f"  {'[!]' if analysis.arm_drop_detected else 'OK'}",
             (0, 0, 255)
             if analysis.arm_drop_detected
             else (0, 220, 100)),
        ]

        ov = frame.copy()
        cv2.rectangle(ov, (0, 0),
                      (300, len(lines)*24+16),
                      (0, 0, 0), -1)
        cv2.addWeighted(ov, 0.55, frame, 0.45, 0, frame)

        for i, (text, col) in enumerate(lines):
            cv2.putText(frame, text, (8, 22 + i*24),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.52, col, 1, cv2.LINE_AA)

        # Banner
        if analysis.arm_drop_detected:
            cv2.rectangle(
                frame,
                (0, frame.shape[0]-36),
                (frame.shape[1], frame.shape[0]),
                (0, 0, 200), -1)
            cv2.putText(
                frame,
                "  ATENTIE: BRAT CAZUT DETECTAT",
                (8, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (255, 255, 255), 1,
                cv2.LINE_AA)

        return frame