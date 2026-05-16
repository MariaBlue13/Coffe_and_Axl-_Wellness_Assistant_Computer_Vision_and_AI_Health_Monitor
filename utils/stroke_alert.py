"""
Coffee & Axl - Stroke Alert
Pasul 2: Trimiterea alertei Pushbullet la detectarea asimetriei severe.
"""

import urllib.request
import urllib.error
import json
import threading
from datetime import datetime


PUSHBULLET_API = "https://api.pushbullet.com/v2/pushes"


def send_stroke_alert(
    api_key:    str,
    user_name:  str,
    score:      float,
    horiz_dev:  float,
    vert_dev:   float,
    on_success: callable = None,
    on_error:   callable = None,
):
    """
    Trimite alerta de AVC posibil prin Pushbullet.
    Ruleaza in thread daemon — nu blocheaza UI-ul.
    """

    if not api_key or not api_key.strip():
        if on_error:
            on_error("Cheie Pushbullet lipsa.")
        return

    def _send():
        ts    = datetime.now().strftime("%H:%M:%S — %d.%m.%Y")
        title = "🆘 Coffee & Axl — ALERTĂ AVC POSIBIL"
        body  = "\n".join([
            f"Utilizator : {user_name}",
            f"Ora        : {ts}",
            "",
            "⚠ Asimetrie facială severă detectată:",
            f"  Scor total      : {score:.3f} "
            f"(prag: 0.35)",
            f"  Deviație orizont: {horiz_dev:.3f} "
            f"(cădere colț gurii)",
            f"  Deviație vertic : {vert_dev:.3f} "
            f"(gură trasă lateral)",
            "",
            "SE INIȚIAZĂ TESTUL B.E.F.A.S.T.",
            "",
            "Dacă nu răspunde — sunați 112 imediat.",
        ])

        payload = json.dumps({
            "type":  "note",
            "title": title,
            "body":  body,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                PUSHBULLET_API,
                data    = payload,
                headers = {
                    "Content-Type": "application/json",
                    "Access-Token": api_key.strip(),
                },
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            if data.get("active"):
                if on_success:
                    on_success()
            else:
                if on_error:
                    on_error(f"Raspuns neasteptat: {data}")

        except urllib.error.HTTPError as e:
            msg = {
                401: "Cheie API invalida.",
                429: "Prea multe cereri — asteapta.",
            }.get(e.code, f"Eroare HTTP: {e.code}")
            if on_error:
                on_error(msg)

        except Exception as e:
            if on_error:
                on_error(f"Eroare: {str(e)}")

    threading.Thread(target=_send, daemon=True).start()