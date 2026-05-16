import pyaudio
import numpy as np
import time

CHUNK    = 1024
FORMAT   = pyaudio.paInt16
CHANNELS = 1
RATE     = 16000

pa     = pyaudio.PyAudio()

# Afiseaza toate dispozitivele audio
print("Dispozitive audio disponibile:")
for i in range(pa.get_device_count()):
    d = pa.get_device_info_by_index(i)
    if d["maxInputChannels"] > 0:
        print(f"  [{i}] {d['name']} "
              f"— {d['maxInputChannels']} canale")

print("\nFolosesc dispozitivul default...")
stream = pa.open(
    format            = FORMAT,
    channels          = CHANNELS,
    rate              = RATE,
    input             = True,
    frames_per_buffer = CHUNK,
)

print("Vorbeste 5 secunde...\n")
for i in range(80):
    raw = stream.read(CHUNK, exception_on_overflow=False)
    arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    rms = float(np.sqrt(np.mean(arr ** 2))) / 32768.0
    vol = min(rms * 15, 1.0)
    bars = int(vol * 40)
    print(f"\r[{'█' * bars}{' ' * (40-bars)}] {vol:.3f}",
          end="", flush=True)
    time.sleep(0.06)

stream.stop_stream()
stream.close()
pa.terminate()
print("\nTest terminat.")