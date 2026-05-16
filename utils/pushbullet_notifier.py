import urllib.request
import urllib.error
import json
import threading
import time
import os
from datetime import datetime


PUSHBULLET_API = "https://api.pushbullet.com/v2/pushes"
COOLDOWN_FILE  = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "pb_cooldown.json"
)

# Cooldown intre notificari per nivel (secunde)
COOLDOWN = {
    "medium":   300,   # 5 minute
    "high":     120,   # 2 minute
    "critical":  60,   # 1 minut
}


def _load_cooldowns() -> dict:
    try:
        with open(COOLDOWN_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cooldowns(data: dict):
    try:
        os.makedirs(os.path.dirname(COOLDOWN_FILE), exist_ok=True)
        with open(COOLDOWN_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _is_in_cooldown(urgency_level: str) -> bool:
    cooldowns = _load_cooldowns()
    last_sent = cooldowns.get(urgency_level, 0)
    elapsed   = time.time() - last_sent
    return elapsed < COOLDOWN.get(urgency_level, 300)


def _mark_sent(urgency_level: str):
    cooldowns = _load_cooldowns()
    cooldowns[urgency_level] = time.time()
    _save_cooldowns(cooldowns)


def send_notification(
    api_key:        str,
    title:          str,
    body:           str,
    urgency_level:  str,
    on_success:     callable = None,
    on_error:       callable = None,
):
    """
    Trimite notificare Pushbullet in thread daemon.
    Respecta cooldown-ul per nivel de urgenta.
    """
    if not api_key or not api_key.strip():
        if on_error:
            on_error("Cheia Pushbullet nu este configurată.")
        return

    if _is_in_cooldown(urgency_level):
        remaining = COOLDOWN.get(urgency_level, 300) - (
            time.time() - _load_cooldowns().get(urgency_level, 0)
        )
        if on_error:
            on_error(
                f"Cooldown activ pentru {urgency_level} — "
                f"mai {int(remaining)}s până la următoarea alertă."
            )
        return

    def _send():
        try:
            payload = json.dumps({
                "type":  "note",
                "title": title,
                "body":  body,
            }).encode("utf-8")

            req = urllib.request.Request(
                PUSHBULLET_API,
                data=payload,
                headers={
                    "Content-Type":  "application/json",
                    "Access-Token":  api_key.strip(),
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            if data.get("active"):
                _mark_sent(urgency_level)
                if on_success:
                    on_success()
            else:
                if on_error:
                    on_error(f"Pushbullet: raspuns neasteptat: {data}")

        except urllib.error.HTTPError as e:
            if e.code == 401:
                msg = "Cheie API Pushbullet invalida."
            elif e.code == 429:
                msg = "Prea multe cereri Pushbullet — asteapta putin."
            else:
                msg = f"Eroare HTTP Pushbullet: {e.code}"
            if on_error:
                on_error(msg)
        except Exception as e:
            if on_error:
                on_error(f"Eroare Pushbullet: {str(e)}")

    threading.Thread(target=_send, daemon=True).start()


def verify_api_key(
    api_key:    str,
    on_success: callable,
    on_error:   callable,
):
    """Verifica daca cheia API e valida fara a trimite o notificare."""
    def _verify():
        try:
            req = urllib.request.Request(
                "https://api.pushbullet.com/v2/users/me",
                headers={"Access-Token": api_key.strip()},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read())
            name = data.get("name", "Utilizator")
            on_success(name)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                on_error("Cheie API invalida.")
            else:
                on_error(f"Eroare HTTP: {e.code}")
        except Exception as e:
            on_error(f"Eroare conexiune: {str(e)}")

    threading.Thread(target=_verify, daemon=True).start()


def build_alert_message(
    urgency_level:  str,
    urgency_reason: str,
    user_name:      str,
    metrics:        dict = None,
) -> tuple[str, str]:
    """
    Construieste titlul si corpul notificarii in functie de nivel.
    Returneaza (title, body).
    """
    ts = datetime.now().strftime("%H:%M — %d.%m.%Y")

    icons = {
        "medium":   "⚠️",
        "high":     "🚨",
        "critical": "🆘",
    }
    icon = icons.get(urgency_level, "⚠️")

    title = f"{icon} Coffee & Axl — Alertă {urgency_level.upper()}"

    body_lines = [
        f"Utilizator: {user_name}",
        f"Ora: {ts}",
        f"Nivel: {urgency_level.upper()}",
        "",
    ]

    if urgency_reason:
        body_lines.append("Motive detectate:")
        for reason in urgency_reason.split(" | "):
            body_lines.append(f"  • {reason}")
        body_lines.append("")

    if metrics:
        body_lines.append("Metrici:")
        if "asymmetry" in metrics:
            body_lines.append(f"  Asimetrie facială: {metrics['asymmetry']:.3f}")
        if "head_tilt" in metrics:
            body_lines.append(f"  Inclinare cap: {metrics['head_tilt']:.1f}°")
        if "motion" in metrics:
            body_lines.append(f"  Mișcare: {metrics['motion']:.3f}")
        if "emotion" in metrics:
            body_lines.append(f"  Emoție: {metrics['emotion']}")
        body_lines.append("")

    body_lines.append("Verificați starea utilizatorului.")
    body_lines.append("În caz de urgență reală sunați 112.")

    return title, "\n".join(body_lines)