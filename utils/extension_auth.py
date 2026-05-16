"""
Coffee & Axl - Extension Auth
Genereaza si verifica token-uri pentru extensia Chrome.
"""

import json
import os
import hashlib
import secrets
import time
from datetime import datetime

CAFE_DIR   = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
TOKEN_FILE = os.path.join(
    CAFE_DIR, "ext_token.json")
AUTH_REQ   = os.path.join(
    CAFE_DIR, "ext_auth_request.json")
AUTH_RESP  = os.path.join(
    CAFE_DIR, "ext_auth_response.json")


def sha256_name(name: str) -> str:
    """Cripteaza numele cu SHA256."""
    return hashlib.sha256(
        name.encode("utf-8")
    ).hexdigest()[:16].upper()


def generate_token(user_id: int,
                    username: str) -> str:
    """Genereaza token unic pentru extensie."""
    raw   = f"{user_id}:{username}:{secrets.token_hex(16)}"
    token = hashlib.sha256(
        raw.encode()).hexdigest()
    return token


def save_token(user_id: int,
                username: str,
                display_name: str,
                role: str) -> str:
    """Salveaza token in fisier pentru extensie."""
    os.makedirs(CAFE_DIR, exist_ok=True)
    token = generate_token(user_id, username)

    data = {
        "token":        token,
        "user_id":      user_id,
        "username":     username,
        "display":      sha256_name(display_name),
        "role":         role,
        "created_at":   time.time(),
        "expires_at":   time.time() + 86400,
    }

    with open(TOKEN_FILE, "w",
              encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"[EXT AUTH] Token generat "
          f"pentru {username}")
    return token


def verify_token(token: str) -> dict | None:
    """Verifica token — returneaza datele sau None."""
    try:
        if not os.path.exists(TOKEN_FILE):
            return None
        with open(TOKEN_FILE,
                  encoding="utf-8") as f:
            data = json.load(f)
        if data.get("token") != token:
            return None
        if time.time() > data.get(
                "expires_at", 0):
            return None
        return data
    except Exception:
        return None


def get_current_token() -> dict | None:
    """Returneaza token-ul curent daca e valid."""
    try:
        if not os.path.exists(TOKEN_FILE):
            return None
        with open(TOKEN_FILE,
                  encoding="utf-8") as f:
            data = json.load(f)
        if time.time() > data.get(
                "expires_at", 0):
            return None
        return data
    except Exception:
        return None


def process_auth_request(engine) -> bool:
    """
    Verifica daca extensia a trimis o cerere
    de autentificare si o proceseaza.
    """
    if not os.path.exists(AUTH_REQ):
        return False

    try:
        with open(AUTH_REQ,
                  encoding="utf-8") as f:
            req = json.load(f)
        os.remove(AUTH_REQ)

        username = req.get("username", "")
        password = req.get("password", "")

        if not username or not password:
            _write_auth_response(
                False, "Date incomplete.")
            return False

        # Verifica in DB
        from database import (
            get_session, Utilizator)
        import bcrypt

        session = get_session(engine)
        try:
            user = session.query(Utilizator)\
                .filter_by(
                nume_utilizator=username
            ).first()

            if not user:
                _write_auth_response(
                    False,
                    "Utilizator negăsit.")
                return False

            pwd_ok = bcrypt.checkpw(
                password.encode("utf-8"),
                user.parola_hash.encode("utf-8"))

            if not pwd_ok:
                _write_auth_response(
                    False, "Parolă incorectă.")
                return False

            # Genereaza token
            display = (
                f"{user.prenume or ''} "
                f"{user.nume or ''}".strip()
                or username)

            token = save_token(
                user_id      = user.id_utilizator,
                username     = username,
                display_name = display,
                role         = user.rol,
            )

            _write_auth_response(
                True,
                "Autentificat cu succes!",
                token=token,
                user_id=user.id_utilizator,
                role=user.rol,
                display=sha256_name(display),
            )
            return True

        finally:
            session.close()

    except Exception as e:
        _write_auth_response(
            False, f"Eroare: {e}")
        return False


def _write_auth_response(success: bool,
                          message: str,
                          **kwargs):
    resp = {
        "success": success,
        "message": message,
        "ts":      time.time(),
        **kwargs,
    }
    with open(AUTH_RESP, "w",
              encoding="utf-8") as f:
        json.dump(resp, f, indent=2)