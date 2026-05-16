"""
Coffee & Axl - Vision Engine (CUDA optimizat)
Echilibru viteza/precizie pe GPU NVIDIA.
Integrat cu EmotionDetector si EmotionStateManager.
"""

import cv2
import numpy as np
import mediapipe as mp
import threading
import time
import os
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from utils.emotion_detector import (
    compute_emotion_metrics, EmotionMetrics)
from utils.emotion_state import (
    EmotionStateManager, EmotionalState)


# ─── Tipuri ───────────────────────────────────────────────────────────────────

class UrgencyLevel(Enum):
    NONE     = "none"
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class AnalysisResult:
    timestamp:        float        = 0.0
    face_detected:    bool         = False
    emotion:          str          = "neutru"
    emotion_conf:     float        = 0.0
    asymmetry_score:  float        = 0.0
    head_tilt:        float        = 0.0
    motion_score:     float        = 0.0
    urgency:          UrgencyLevel = UrgencyLevel.NONE
    urgency_reason:   str          = ""
    landmarks:        list         = field(
        default_factory=list)
    lip_symmetry:     object       = None
    emotion_metrics:  object       = None
    emotion_status:   dict         = field(
        default_factory=dict)


# ─── Constante ────────────────────────────────────────────────────────────────

ASYMMETRY_THRESHOLD = 0.65
HEAD_TILT_THRESHOLD = 58.5
MOTION_THRESHOLD    = 0.65
NEGATIVE_DURATION   = 8.0
URGENCY_COOLDOWN    = 30.0
MOTION_SKIP_FRAMES  = 2

MODEL_PATH = os.path.join(
    os.path.expanduser("~"), ".coffee_axl",
    "face_landmarker.task"
)


# ─── CUDA Processor ───────────────────────────────────────────────────────────

class CudaProcessor:

    def __init__(self):
        self._has_cuda = self._check_cuda()
        if self._has_cuda:
            print("[VISION] OpenCV CUDA activ.")
        else:
            print("[VISION] Fallback CPU.")

    def _check_cuda(self) -> bool:
        try:
            import torch
            if torch.cuda.is_available():
                print(f"[VISION] CUDA activ via PyTorch: "
                      f"{torch.cuda.get_device_name(0)}")
                return True
        except ImportError:
            pass
        try:
            count = cv2.cuda.getCudaEnabledDeviceCount()
            if count > 0:
                cv2.cuda.setDevice(0)
                return True
        except Exception:
            pass
        return False

    def cvt_color(self, frame: np.ndarray,
                  code: int) -> np.ndarray:
        if self._has_cuda:
            try:
                gpu = cv2.cuda_GpuMat()
                gpu.upload(frame)
                gpu_cvt = cv2.cuda.cvtColor(gpu, code)
                return gpu_cvt.download()
            except Exception:
                pass
        return cv2.cvtColor(frame, code)

    def optical_flow(self, prev_gray: np.ndarray,
                     curr_gray: np.ndarray) -> float:
        if self._has_cuda:
            try:
                gpu_prev = cv2.cuda_GpuMat()
                gpu_curr = cv2.cuda_GpuMat()
                gpu_prev.upload(prev_gray)
                gpu_curr.upload(curr_gray)
                flow_gpu = cv2.cuda_FarnebackOpticalFlow\
                    .create(
                        numLevels=3,
                        pyrScale=0.5,
                        fastPyramids=True,
                        winSize=13,
                        numIters=3,
                        polyN=5,
                        polySigma=1.1,
                        flags=0,
                    )
                gpu_flow = flow_gpu.calc(
                    gpu_prev, gpu_curr, None)
                flow = gpu_flow.download()
                mag, _ = cv2.cartToPolar(
                    flow[..., 0], flow[..., 1])
                return float(
                    np.clip(np.mean(mag) / 10.0, 0, 1))
            except Exception:
                pass
        try:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                0.5, 3, 15, 3, 5, 1.2, 0)
            mag, _ = cv2.cartToPolar(
                flow[..., 0], flow[..., 1])
            return float(
                np.clip(np.mean(mag) / 10.0, 0, 1))
        except Exception:
            return 0.0

    @property
    def has_cuda(self) -> bool:
        return self._has_cuda


# ─── Vision Engine ────────────────────────────────────────────────────────────

class VisionEngine:

    def __init__(
        self,
        on_result:  Callable,
        on_urgency: Callable,
        on_frame:   Callable,
        on_error:   Callable,
    ):
        self.on_result  = on_result
        self.on_urgency = on_urgency
        self.on_frame   = on_frame
        self.on_error   = on_error

        self._running        = False
        self._thread         = None
        self._last_urgency   = 0.0
        self._neg_start      = None
        self._prev_gray      = None
        self._motion_history = deque(maxlen=12)
        self._frame_count    = 0

        self._cached_emotion      = "neutru"
        self._cached_emotion_conf = 0.5

        self._cuda       = CudaProcessor()
        self._landmarker = None
        self._init_landmarker()

        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            "haarcascade_frontalface_default.xml"
        )


        # Emotion callbacks — toate emotiile Ekman
        self._on_drowsy_confirmed: callable = None
        self._on_sad_confirmed: callable = None
        self._on_angry_confirmed: callable = None
        self._on_fearful_confirmed: callable = None
        self._on_disgusted_confirmed: callable = None
        self._on_both_confirmed: callable = None

        self._emotion_state = EmotionStateManager(
            on_drowsy=self._alert_drowsy,
            on_sad=self._alert_sad,
            on_angry=self._alert_angry,
            on_fearful=self._alert_fearful,
            on_disgusted=self._alert_disgusted,
            on_both=self._alert_both,
            on_reset=self._alert_reset,
        )

    # ── Init landmarker ───────────────────────────────────────────────────────

    def _init_landmarker(self):
        if not os.path.exists(MODEL_PATH):
            print(f"[VISION] Model lips: {MODEL_PATH}")
            return
        try:
            options = mp_vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=MODEL_PATH),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_face_blendshapes=True,
            )
            self._landmarker = \
                mp_vision.FaceLandmarker\
                .create_from_options(options)
            print("[VISION] FaceLandmarker activ (XNNPACK).")
        except Exception as e:
            print(f"[VISION] Landmarker eroare: {e}")

    # ── Emotion callbacks ─────────────────────────────────────────────────────

    def set_emotion_callbacks(
            self,
            on_drowsy:    callable = None,
            on_sad:       callable = None,
            on_angry:     callable = None,
            on_fearful:   callable = None,
            on_disgusted: callable = None,
            on_both:      callable = None):
        self._on_drowsy_confirmed    = on_drowsy
        self._on_sad_confirmed       = on_sad
        self._on_angry_confirmed     = on_angry
        self._on_fearful_confirmed   = on_fearful
        self._on_disgusted_confirmed = on_disgusted
        self._on_both_confirmed      = on_both

    def _alert_drowsy(self):
        print("[VISION] Oboseala confirmata -> AI")
        if self._on_drowsy_confirmed:
            self._on_drowsy_confirmed()

    def _alert_sad(self):
        print("[VISION] Tristete confirmata -> AI")
        if self._on_sad_confirmed:
            self._on_sad_confirmed()

    def _alert_angry(self):
        print("[VISION] Furie confirmata -> AI")
        if self._on_angry_confirmed:
            self._on_angry_confirmed()

    def _alert_fearful(self):
        print("[VISION] Frica confirmata -> AI")
        if self._on_fearful_confirmed:
            self._on_fearful_confirmed()

    def _alert_disgusted(self):
        print("[VISION] Dezgust confirmat -> AI")
        if self._on_disgusted_confirmed:
            self._on_disgusted_confirmed()

    def _alert_both(self):
        print("[VISION] Oboseala + emotie -> AI")
        if self._on_both_confirmed:
            self._on_both_confirmed()
        elif self._on_drowsy_confirmed:
            self._on_drowsy_confirmed()

    def _alert_reset(self):
        print("[VISION] Stare revenita la normal.")

    # ── Control ───────────────────────────────────────────────────────────────

    def start(self, camera_index: int = 0):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop,
            args=(camera_index,),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

    # ── Loop principal ────────────────────────────────────────────────────────

    def _loop(self, camera_index: int):
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            self.on_error(
                "Camera nu a putut fi deschisă.\n"
                "Verifică conexiunea webcam-ului."
            )
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS,          30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE,   1)

        try:
            cap.set(cv2.CAP_PROP_BACKEND,
                    cv2.CAP_DSHOW)
        except Exception:
            pass

        t_last_frame = time.time()

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.02)
                    continue

                self._frame_count += 1
                frame = cv2.flip(frame, 1)

                result    = self._analyze(frame)
                annotated = self._draw_overlay(
                    frame.copy(), result)

                self.on_frame(annotated)
                self.on_result(result)

                if (result.urgency.value in
                        ("medium", "high", "critical")
                        and time.time() -
                        self._last_urgency
                        > URGENCY_COOLDOWN):
                    self._last_urgency = time.time()
                    self.on_urgency(result)

                elapsed = time.time() - t_last_frame
                wait    = max(0.0, 0.033 - elapsed)
                if wait > 0:
                    time.sleep(wait)
                t_last_frame = time.time()

        finally:
            cap.release()
            if self._landmarker:
                self._landmarker.close()

    # ── Analiza frame ─────────────────────────────────────────────────────────

    def _analyze(self, frame: np.ndarray) -> AnalysisResult:
        result = AnalysisResult(timestamp=time.time())

        if self._landmarker is None:
            return self._analyze_haar(frame)

        try:
            rgb = self._cuda.cvt_color(
                frame, cv2.COLOR_BGR2RGB)
            mp_image  = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb)
            ts_ms     = int(time.time() * 1000)
            detection = self._landmarker\
                .detect_for_video(mp_image, ts_ms)
        except Exception as e:
            print(f"[VISION] detect eroare: {e}")
            return result

        if not detection.face_landmarks:
            self._neg_start = None
            self._prev_gray = None
            # Actualizeaza state cu fata nedetectata
            from utils.emotion_detector import EmotionMetrics
            self._emotion_state.update(EmotionMetrics())
            return result

        result.face_detected = True
        h, w = frame.shape[:2]
        lm   = detection.face_landmarks[0]
        pts  = [(int(p.x * w), int(p.y * h))
                for p in lm]
        result.landmarks = pts

        # ── Emotie din blendshapes ────────────────────────────────────────────
        if detection.face_blendshapes:
            result.emotion, result.emotion_conf = \
                self._emotion_from_blendshapes(
                    detection.face_blendshapes[0])
            self._cached_emotion      = result.emotion
            self._cached_emotion_conf = result.emotion_conf
        else:
            result.emotion      = self._cached_emotion
            result.emotion_conf = self._cached_emotion_conf

        # ── Metrici geometrice ────────────────────────────────────────────────
        result.asymmetry_score = self._calc_asymmetry(
            pts, w)
        result.head_tilt       = self._calc_head_tilt(pts)

        # ── Optical flow ──────────────────────────────────────────────────────
        gray = self._cuda.cvt_color(
            frame, cv2.COLOR_BGR2GRAY)

        if (self._prev_gray is not None
                and self._frame_count
                % MOTION_SKIP_FRAMES == 0):
            xs  = [p[0] for p in pts]
            ys  = [p[1] for p in pts]
            x1  = max(0, min(xs) - 10)
            y1  = max(0, min(ys) - 10)
            x2  = min(w, max(xs) + 10)
            y2  = min(h, max(ys) + 10)

            roi_p = self._prev_gray[y1:y2, x1:x2]
            roi_c = gray[y1:y2, x1:x2]

            if roi_p.size > 0 and roi_c.size > 0:
                score = self._cuda.optical_flow(
                    roi_p, roi_c)
                self._motion_history.append(score)

        self._prev_gray    = gray
        result.motion_score = (
            float(np.mean(self._motion_history))
            if self._motion_history else 0.0
        )

        # ── Lip symmetry ──────────────────────────────────────────────────────
        try:
            from utils.stroke_detector import (
                extract_lip_landmarks,
                compute_lip_symmetry)
            lip_pts = extract_lip_landmarks(lm, w, h)
            result.lip_symmetry = compute_lip_symmetry(
                lip_pts)
        except Exception:
            pass

        # ── Emotion metrics (EAR + tristete) ─────────────────────────────────
        result.emotion_metrics = compute_emotion_metrics(
            lm, w, h)

        # Actualizeaza state manager cu debouncing
        status = self._emotion_state.update(
            result.emotion_metrics)
        result.emotion_status = status

        # ── Urgenta ───────────────────────────────────────────────────────────
        result.urgency, result.urgency_reason = \
            self._assess_urgency(result)

        return result

    def _analyze_haar(self,
                      frame: np.ndarray) -> AnalysisResult:
        result = AnalysisResult(timestamp=time.time())
        gray   = self._cuda.cvt_color(
            frame, cv2.COLOR_BGR2GRAY)
        faces  = self._face_cascade.detectMultiScale(
            gray, 1.1, 5, minSize=(60, 60))

        if len(faces) == 0:
            self._prev_gray = gray
            return result

        result.face_detected = True
        x, y, fw, fh = faces[0]

        if (self._prev_gray is not None
                and self._frame_count
                % MOTION_SKIP_FRAMES == 0):
            roi_p = self._prev_gray[y:y+fh, x:x+fw]
            roi_c = gray[y:y+fh, x:x+fw]
            score = self._cuda.optical_flow(roi_p, roi_c)
            self._motion_history.append(score)

        self._prev_gray     = gray
        result.motion_score = (
            float(np.mean(self._motion_history))
            if self._motion_history else 0.0
        )
        result.urgency, result.urgency_reason = \
            self._assess_urgency(result)
        return result

    # ── Emotie din blendshapes ────────────────────────────────────────────────

    def _emotion_from_blendshapes(
            self, blendshapes) -> tuple[str, float]:
        try:
            s = {bs.category_name: bs.score
                 for bs in blendshapes}

            joy = (
                s.get("mouthSmileLeft",  0) * 0.4 +
                s.get("mouthSmileRight", 0) * 0.4 +
                s.get("cheekSquintLeft", 0) * 0.1 +
                s.get("cheekSquintRight",0) * 0.1
            )
            sad = (
                s.get("mouthFrownLeft",  0) * 0.3 +
                s.get("mouthFrownRight", 0) * 0.3 +
                s.get("browInnerUp",     0) * 0.2 +
                s.get("mouthPucker",     0) * 0.2
            )
            angry = (
                s.get("browDownLeft",    0) * 0.35 +
                s.get("browDownRight",   0) * 0.35 +
                s.get("noseSneerLeft",   0) * 0.15 +
                s.get("noseSneerRight",  0) * 0.15
            )
            surprise = (
                s.get("jawOpen",         0) * 0.4 +
                s.get("eyeWideLeft",     0) * 0.3 +
                s.get("eyeWideRight",    0) * 0.3
            )
            fear = (
                s.get("eyeWideLeft",     0) * 0.25 +
                s.get("eyeWideRight",    0) * 0.25 +
                s.get("browInnerUp",     0) * 0.30 +
                s.get("mouthStretchLeft",0) * 0.10 +
                s.get("mouthStretchRight",0)* 0.10
            )
            disgust = (
                s.get("noseSneerLeft",   0) * 0.4 +
                s.get("noseSneerRight",  0) * 0.4 +
                s.get("mouthLeft",       0) * 0.1 +
                s.get("mouthRight",      0) * 0.1
            )

            candidates = {
                "fericit":  joy,
                "trist":    sad,
                "furios":   angry,
                "surprins": surprise,
                "frica":    fear,
                "dezgust":  disgust,
            }

            best       = max(candidates,
                             key=candidates.get)
            best_score = candidates[best]

            if best_score < 0.18:
                return "neutru", 1.0 - best_score

            return best, min(best_score * 1.5, 1.0)

        except Exception:
            return "neutru", 0.5

    # ── Metrici geometrice ────────────────────────────────────────────────────

    def _calc_asymmetry(self, pts: list,
                        w: int) -> float:
        try:
            if len(pts) < 400:
                return 0.0

            lm  = pts[61]
            rm  = pts[291]
            nt  = pts[4]
            dl  = abs(lm[1] - nt[1])
            dr  = abs(rm[1] - nt[1])
            m_a = abs(dl - dr) / max(dl + dr, 1)

            le  = abs(pts[159][1] - pts[145][1])
            re  = abs(pts[386][1] - pts[374][1])
            e_a = abs(le - re) / max(le + re, 1)

            lb  = pts[65]
            rb  = pts[295]
            b_a = abs(lb[1] - rb[1]) / max(
                w * 0.01, 1)
            b_a = min(b_a / 10.0, 1.0)

            return float(np.clip(
                m_a * 0.45 + e_a * 0.35 + b_a * 0.20,
                0, 1
            ))
        except Exception:
            return 0.0

    def _calc_head_tilt(self, pts: list) -> float:
        try:
            if len(pts) < 264:
                return 0.0
            le    = np.array(pts[33])
            re    = np.array(pts[263])
            delta = re - le
            return abs(float(
                np.degrees(
                    np.arctan2(delta[1], delta[0]))))
        except Exception:
            return 0.0

    # ── Evaluare urgenta ──────────────────────────────────────────────────────

    def _assess_urgency(
            self,
            r: AnalysisResult) -> tuple[
                UrgencyLevel, str]:
        if not r.face_detected:
            return UrgencyLevel.NONE, ""

        reasons = []
        score   = 0

        if r.asymmetry_score > ASYMMETRY_THRESHOLD:
            score += 2
            pct = int(r.asymmetry_score * 100)
            reasons.append(
                f"Asimetrie facială {pct}% — AVC")

        if r.head_tilt > HEAD_TILT_THRESHOLD:
            score += 2
            reasons.append(
                f"Cap înclinat {r.head_tilt:.0f}° — leșin")

        if r.motion_score > MOTION_THRESHOLD:
            score += 3
            pct = int(r.motion_score * 100)
            reasons.append(
                f"Mișcări haotice {pct}% — epilepsie")

        neg = {"trist", "frica", "furios", "dezgust"}
        if r.emotion in neg:
            if self._neg_start is None:
                self._neg_start = time.time()
            elif (time.time() - self._neg_start
                  > NEGATIVE_DURATION):
                score += 1
                reasons.append(
                    f"Stare negativă: {r.emotion}")
        else:
            self._neg_start = None

        if score >= 5:
            level = UrgencyLevel.CRITICAL
        elif score >= 3:
            level = UrgencyLevel.HIGH
        elif score >= 2:
            level = UrgencyLevel.MEDIUM
        elif score >= 1:
            level = UrgencyLevel.LOW
        else:
            level = UrgencyLevel.NONE

        return level, " | ".join(reasons)

    # ── Overlay vizual ────────────────────────────────────────────────────────

    def _draw_overlay(self, frame: np.ndarray,
                      r: AnalysisResult) -> np.ndarray:
        if not r.face_detected:
            cv2.putText(
                frame, "Fata nedetectata", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (100, 100, 255), 2)
            return frame

        colors = {
            UrgencyLevel.NONE:     (100, 220, 100),
            UrgencyLevel.LOW:      (100, 220, 220),
            UrgencyLevel.MEDIUM:   (100, 180, 255),
            UrgencyLevel.HIGH:     (50,  100, 255),
            UrgencyLevel.CRITICAL: (50,  50,  255),
        }
        color = colors.get(r.urgency, (200, 200, 200))

        if r.landmarks and len(r.landmarks) > 400:
            key_pts = {
                4, 33, 263, 61, 291,
                159, 386, 145, 374,
                13, 14, 17, 0, 10, 152
            }
            for idx, (x, y) in enumerate(r.landmarks):
                if idx in key_pts:
                    cv2.circle(frame, (x, y), 4,
                               (0, 255, 255), -1)
                else:
                    cv2.circle(frame, (x, y), 1,
                               color, -1)

            # Contur fata
            fc = [10,338,297,332,284,251,389,356,454,
                  323,361,288,397,365,379,378,400,377,
                  152,148,176,149,150,136,172,58,132,
                  93,234,127,162,21,54,103,67,109,10]
            for i in range(len(fc) - 1):
                a, b = fc[i], fc[i+1]
                if (a < len(r.landmarks)
                        and b < len(r.landmarks)):
                    cv2.line(frame,
                             r.landmarks[a],
                             r.landmarks[b],
                             color, 1, cv2.LINE_AA)

            # Ochi
            for eye in [
                [33,160,158,133,153,144,33],
                [362,385,387,263,373,380,362],
            ]:
                for i in range(len(eye)-1):
                    a, b = eye[i], eye[i+1]
                    if (a < len(r.landmarks)
                            and b < len(r.landmarks)):
                        cv2.line(frame,
                                 r.landmarks[a],
                                 r.landmarks[b],
                                 (0, 255, 200), 1,
                                 cv2.LINE_AA)

            # Gura
            mouth = [61,185,40,39,37,0,267,269,270,
                     409,291,375,321,405,314,17,
                     84,181,91,146,61]
            for i in range(len(mouth)-1):
                a, b = mouth[i], mouth[i+1]
                if (a < len(r.landmarks)
                        and b < len(r.landmarks)):
                    cv2.line(frame,
                             r.landmarks[a],
                             r.landmarks[b],
                             (255, 180, 100), 1,
                             cv2.LINE_AA)

            # Sprancene
            for brow in [
                [55,65,52,53,46],
                [285,295,282,283,276],
            ]:
                for i in range(len(brow)-1):
                    a, b = brow[i], brow[i+1]
                    if (a < len(r.landmarks)
                            and b < len(r.landmarks)):
                        cv2.line(frame,
                                 r.landmarks[a],
                                 r.landmarks[b],
                                 (200, 150, 255), 1,
                                 cv2.LINE_AA)

            # Nas
            for nas in [
                [168,6,197,195,5,4],
                [4,45,220,115,48,64,98,97,2,
                 326,327,294,440,275,4],
            ]:
                for i in range(len(nas)-1):
                    a, b = nas[i], nas[i+1]
                    if (a < len(r.landmarks)
                            and b < len(r.landmarks)):
                        cv2.line(frame,
                                 r.landmarks[a],
                                 r.landmarks[b],
                                 (150, 200, 255), 1,
                                 cv2.LINE_AA)

            # Axa cap
            if len(r.landmarks) > 263:
                cv2.line(frame,
                         r.landmarks[33],
                         r.landmarks[263],
                         (255, 255, 0), 2, cv2.LINE_AA)
            if len(r.landmarks) > 152:
                cv2.line(frame,
                         r.landmarks[4],
                         r.landmarks[152],
                         (255, 255, 0), 2, cv2.LINE_AA)

            # Marker asimetrie
            if (r.asymmetry_score > 0.20
                    and len(r.landmarks) > 291):
                ac = ((0, 100, 255)
                      if r.asymmetry_score
                      > ASYMMETRY_THRESHOLD
                      else (0, 200, 255))
                cv2.circle(frame, r.landmarks[61],
                           8, ac, 2)
                cv2.circle(frame, r.landmarks[291],
                           8, ac, 2)
                cv2.line(frame,
                         r.landmarks[61],
                         r.landmarks[291],
                         ac, 1, cv2.LINE_AA)

        # ── EAR overlay ───────────────────────────────────────────────────────
        em = r.emotion_metrics
        ear_color = (0, 100, 255) \
            if (em and em.is_drowsy) \
            else (100, 255, 100)
        sad_color = (0, 100, 255) \
            if (em and em.is_negative) \
            else (100, 255, 100)

        ear_str  = f"{em.ear_avg:.3f}" if em else "—"
        sad_str  = (f"curve={em.mouth_curve:+.3f}"
                    if em else "—")
        prog_str = ""

        if (r.emotion_status
                and r.emotion_status.get("state")
                != EmotionalState.NEUTRAL):
            prog = r.emotion_status.get("progress", 0)
            state_name = r.emotion_status[
                "state"].value.upper()
            prog_str = (f"{state_name} "
                        f"{prog:.0%}")

        # ── Text overlay ──────────────────────────────────────────────────────
        lines = [
            (f"Emotie    : {r.emotion} "
             f"({r.emotion_conf:.0%})",
             color),
            (f"EAR       : {ear_str}"
             f"  {'[OBOSIT]' if em and em.is_drowsy else ''}",
             ear_color),
            (f"Tristete  : {sad_str}"
             f"  {'[TRIST]' if em and em.is_negative else ''}",
             sad_color),
            (f"Asimetrie : {r.asymmetry_score:.4f}"
             f"  {'[!]' if r.asymmetry_score > ASYMMETRY_THRESHOLD else ''}",
             (0, 100, 255)
             if r.asymmetry_score > ASYMMETRY_THRESHOLD
             else color),
            (f"Inclinare : {r.head_tilt:.1f} grade"
             f"  {'[!]' if r.head_tilt > HEAD_TILT_THRESHOLD else ''}",
             color),
            (f"Miscare   : {r.motion_score:.4f}"
             f"  {'[!]' if r.motion_score > MOTION_THRESHOLD else ''}",
             color),
            (f"Urgenta   : {r.urgency.value.upper()}",
             color),
            (f"CUDA      : "
             f"{'DA' if self._cuda.has_cuda else 'NU'}",
             (100, 255, 100)
             if self._cuda.has_cuda
             else (200, 200, 200)),
        ]

        if prog_str:
            lines.append((prog_str, (0, 180, 255)))

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0),
                      (340, len(lines)*24+16),
                      (0, 0, 0), -1)
        cv2.addWeighted(
            overlay, 0.55, frame, 0.45, 0, frame)

        for i, (line, col) in enumerate(lines):
            cv2.putText(
                frame, line, (8, 22 + i*24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50, col, 1, cv2.LINE_AA)

        # Banner urgenta
        if r.urgency not in (
                UrgencyLevel.NONE, UrgencyLevel.LOW):
            bc = {
                UrgencyLevel.MEDIUM:   (0, 140, 255),
                UrgencyLevel.HIGH:     (0,  60, 220),
                UrgencyLevel.CRITICAL: (0,   0, 200),
            }.get(r.urgency, (0, 100, 255))

            cv2.rectangle(
                frame,
                (0, frame.shape[0]-36),
                (frame.shape[1], frame.shape[0]),
                bc, -1)

            label = (f"  ATENTIE: "
                     f"{r.urgency.value.upper()}")
            if r.urgency_reason:
                label += (f"  |  "
                          f"{r.urgency_reason[:55]}")
            cv2.putText(
                frame, label,
                (8, frame.shape[0]-10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52, (255, 255, 255), 1,
                cv2.LINE_AA)

        # Banner emotie detectata
        if em and (em.is_drowsy or em.is_negative):
            state = r.emotion_status.get(
                "state", EmotionalState.NEUTRAL)
            prog  = r.emotion_status.get(
                "progress", 0)

            if state != EmotionalState.NEUTRAL:
                bh = frame.shape[0]
                y0 = bh - 72 \
                    if r.urgency not in (
                        UrgencyLevel.NONE,
                        UrgencyLevel.LOW) \
                    else bh - 36

                cv2.rectangle(
                    frame,
                    (0, y0 - 36),
                    (frame.shape[1], y0),
                    (60, 40, 0), -1)

                state_txt = {
                    EmotionalState.DROWSY: "OBOSEALA",
                    EmotionalState.SAD:    "TRISTETE",
                    EmotionalState.BOTH:
                        "OBOSEALA + TRISTETE",
                }.get(state, "")

                cv2.putText(
                    frame,
                    f"  {state_txt} detectata — "
                    f"confirmare: {prog:.0%}",
                    (8, y0 - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.50, (255, 200, 100), 1,
                    cv2.LINE_AA)

        return frame