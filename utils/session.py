import os
import json
from datetime import datetime, timedelta

SESSION_FILE = os.path.join(os.path.expanduser("~"), ".coffee_axl", "session.json")
SESSION_TTL  = 24   # ore — sesiunea expira dupa 24h


def save_session(user_id: int, rol: str, user_name: str):
    """Salveaza sesiunea curenta pe disk."""
    try:
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        data = {
            "user_id":   user_id,
            "rol":       rol,
            "user_name": user_name,
            "saved_at":  datetime.now().isoformat(),
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[SESSION] Save error: {e}")


def load_session() -> dict | None:
    """
    Incarca sesiunea salvata daca exista si nu a expirat.
    Returneaza dict cu user_id, rol, user_name sau None.
    """
    try:
        if not os.path.exists(SESSION_FILE):
            return None

        with open(SESSION_FILE) as f:
            data = json.load(f)

        saved_at = datetime.fromisoformat(data["saved_at"])
        if datetime.now() - saved_at > timedelta(hours=SESSION_TTL):
            clear_session()
            return None

        return data
    except Exception:
        return None


def clear_session():
    """Sterge sesiunea — la logout."""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass


def has_active_session() -> bool:
    return load_session() is not None