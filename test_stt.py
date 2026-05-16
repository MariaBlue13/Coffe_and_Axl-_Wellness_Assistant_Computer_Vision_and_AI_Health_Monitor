import time
from utils.voice_assistant import SpeechEngine, SpeechListener

engine   = SpeechEngine()
listener = SpeechListener()
time.sleep(1)

def on_result(text):
    print(f'Am inteles: "{text}"')

def on_error(err):
    print(f'Eroare STT: {err}')

engine.speak(
    "Spune ceva, te ascult.",
    on_done=lambda: print("Ascult...")
)
time.sleep(2)

listener.listen(
    on_result    = on_result,
    on_error     = on_error,
    timeout      = 8,
    phrase_limit = 6,
)
time.sleep(12)