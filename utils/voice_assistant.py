"""
Coffee & Axl - Voice Assistant
Edge TTS Neural + Faster-Whisper pe GPU.
Pygame initializat global — fara reinitializari.
STT asteapta TTS sa termine complet.
"""

import threading
import time
import os
import queue
import tempfile
import numpy as np

# ── Pygame global ─────────────────────────────────────────────────────────────
import pygame
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()
print("[AUDIO] Pygame mixer initializat.")


# ─── TTS ──────────────────────────────────────────────────────────────────────

class SpeechEngine:

    VOICE = "ro-RO-AlinaNeural"

    def __init__(self, voice: str = None):
        self._voice  = voice or self.VOICE
        self._queue  = queue.Queue()
        self._thread = threading.Thread(
            target=self._run, daemon=True)
        self._thread.start()
        print(f"[TTS] Edge Neural: {self._voice}")

    def _run(self):
        while True:
            try:
                item = self._queue.get(timeout=1.0)
                if item is None:
                    break
                text, cb = item
                self._speak_sync(text)
                if cb:
                    cb()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS] Thread eroare: {e}")

    def _speak_sync(self, text: str):
        tmp_path = None
        try:
            import asyncio
            import edge_tts

            tmp      = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()

            asyncio.run(self._gen(text, tmp_path))

            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.04)
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()

        except Exception as e:
            print(f"[TTS] Eroare: {e}")
            try:
                import pyttsx3
                eng = pyttsx3.init()
                eng.setProperty("rate", 140)
                eng.say(text)
                eng.runAndWait()
            except Exception:
                pass
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    async def _gen(self, text: str, path: str):
        import edge_tts
        await edge_tts.Communicate(
            text, self._voice).save(path)

    def speak(self, text: str,
              on_done: callable = None):
        self._queue.put((text, on_done))

    def stop(self):
        self._queue.put(None)


# ─── STT ──────────────────────────────────────────────────────────────────────

class SpeechListener:

    _model      = None
    _model_lock = threading.Lock()

    def __init__(self):
        self._running    = False
        self._on_volume  = None
        threading.Thread(
            target=self._load_model,
            daemon=True,
        ).start()

    def set_volume_callback(self, cb: callable):
        self._on_volume = cb

    def _load_model(self):
        with SpeechListener._model_lock:
            if SpeechListener._model is not None:
                return
            try:
                from faster_whisper import WhisperModel
                try:
                    import torch
                    dev = "cuda" \
                        if torch.cuda.is_available() \
                        else "cpu"
                    ct  = "float16" \
                        if dev == "cuda" else "int8"
                except ImportError:
                    dev, ct = "cpu", "int8"

                print(f"[STT] Whisper ({dev})...")
                SpeechListener._model = WhisperModel(
                    "small", device=dev,
                    compute_type=ct)
                print("[STT] Whisper gata.")
            except Exception as e:
                print(f"[STT] Model eroare: {e}")

    def listen(self, on_result, on_error,
               timeout=10, phrase_limit=6):
        self._running = True
        threading.Thread(
            target=self._record,
            args=(on_result, on_error,
                  timeout, phrase_limit),
            daemon=True,
        ).start()

    def _record(self, on_result, on_error,
                timeout, phrase_limit):
        import pyaudio

        # Asteapta TTS sa termine
        deadline = time.time() + 5
        while (pygame.mixer.music.get_busy()
               and time.time() < deadline):
            time.sleep(0.05)
        time.sleep(0.3)

        CHUNK = 1024
        pa = stream = None
        frames = []

        try:
            pa = pyaudio.PyAudio()

            dev_idx = None
            for i in range(pa.get_device_count()):
                d = pa.get_device_info_by_index(i)
                if (d["maxInputChannels"] >= 1
                        and d["hostApi"] == 0
                        and "mapper" not in
                        d["name"].lower()):
                    dev_idx = i
                    break

            stream = pa.open(
                format             = pyaudio.paInt16,
                channels           = 1,
                rate               = 16000,
                input              = True,
                input_device_index = dev_idx,
                frames_per_buffer  = CHUNK,
            )

            print(f"[STT] Recording (dev={dev_idx})...")

            t0 = time.time()
            silence_t    = 0
            has_speech   = False
            speech_start = None
            THRESH       = 0.008

            while self._running:
                if time.time() - t0 > timeout:
                    break
                if (has_speech and speech_start
                        and time.time() - speech_start
                        > phrase_limit):
                    break

                raw = stream.read(
                    CHUNK,
                    exception_on_overflow=False)
                frames.append(raw)

                arr = np.frombuffer(
                    raw, dtype=np.int16
                ).astype(np.float32)
                rms = float(np.sqrt(
                    np.mean(arr**2))) / 32768.0
                vol = min(rms * 20, 1.0)

                if self._on_volume:
                    self._on_volume(vol)

                if rms > THRESH:
                    if not has_speech:
                        has_speech   = True
                        speech_start = time.time()
                    silence_t = 0
                elif has_speech:
                    silence_t += CHUNK / 16000
                    if silence_t > 1.2:
                        break

        except Exception as e:
            print(f"[STT] Record eroare: {e}")
            on_error(f"error:{e}")
            return
        finally:
            try:
                if stream:
                    stream.stop_stream()
                    stream.close()
                if pa:
                    pa.terminate()
            except Exception:
                pass

        if not frames or not has_speech:
            on_error("timeout")
            return

        self._transcribe(frames, on_result, on_error)

    def _transcribe(self, frames, on_result, on_error):
        try:
            if not SpeechListener._model:
                on_error("unclear")
                return

            raw = b"".join(frames)
            arr = np.frombuffer(
                raw, dtype=np.int16
            ).astype(np.float32) / 32768.0

            segs, _ = SpeechListener._model.transcribe(
                arr, language="ro", beam_size=5,
                vad_filter=True,
                vad_parameters={
                    "min_silence_duration_ms": 400})

            text = " ".join(
                s.text.strip() for s in segs
            ).strip().lower()

            print(f"[STT] '{text}'")
            on_result(text) if text else on_error("unclear")

        except Exception as e:
            print(f"[STT] Transcriere eroare: {e}")
            on_error(f"error:{e}")

    def stop(self):
        self._running = False


# ─── Evaluare ─────────────────────────────────────────────────────────────────

def evaluate_response(question_key: str,
                      response: str) -> tuple[bool, str]:
    if response in ("timeout", "unclear") \
            or response.startswith("error:"):
        return False, {
            "timeout": "Nu a răspuns în timp.",
            "unclear": "Vorbire neinteligibilă.",
        }.get(response, f"Eroare: {response}")

    words = response.split()
    if len(words) < 1:
        return False, f"Răspuns gol."

    return True, f"Răspuns: '{response}'"