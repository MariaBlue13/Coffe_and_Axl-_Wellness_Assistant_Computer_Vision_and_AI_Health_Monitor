"""
Coffee & Axl - Extension HTTP Server
Server local pentru comunicare cu extensia Chrome.
Ruleaza pe localhost:7842.
"""

import json
import threading
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler


class ExtensionHandler(BaseHTTPRequestHandler):

    engine = None
    # Contor incercari blocare: {(user_id, domain): [timestamps]}
    _blocked_attempts: dict = {}
    # Cate incercari inainte de notificare Pushbullet
    ALERT_THRESHOLD = 3
    on_time_update = None

    def log_message(self, format, *args):
        pass  # Suprima log-urile HTTP

    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        length  = int(
            self.headers.get(
                'Content-Length', 0))
        body    = self.rfile.read(length)

        try:
            data = json.loads(body)
        except Exception:
            self._respond(400, {
                "success": False,
                "message": "JSON invalid"})
            return

        if self.path == '/auth':
            self._handle_auth(data)
        elif self.path == '/event':
            self._handle_event(data)
        elif self.path == '/rules':
            self._handle_rules(data)
        elif self.path == '/time_used':
            self._handle_time_used(data)
        else:
            self._respond(404, {
                "success": False,
                "message": "Not found"})

    def do_GET(self):
        if self.path.startswith('/rules/'):
            user_id = self.path.split('/')[-1]
            self._get_rules(user_id)
        else:
            self._respond(404, {})

    def _handle_auth(self, data: dict):
        username = data.get("username", "")
        password = data.get("password", "")

        if not username or not password:
            self._respond(200, {
                "success": False,
                "message": "Date incomplete."})
            return

        try:
            from database import (
                get_session, Utilizator)
            import bcrypt
            from utils.extension_auth import (
                save_token, sha256_name)

            session = get_session(
                ExtensionHandler.engine)
            try:
                user = session.query(
                    Utilizator).filter_by(
                    nume_utilizator=username
                ).first()

                if not user:
                    self._respond(200, {
                        "success": False,
                        "message":
                            "Utilizator negăsit."
                    })
                    return

                pwd_ok = bcrypt.checkpw(
                    password.encode("utf-8"),
                    user.parola.encode("utf-8"))

                if not pwd_ok:
                    self._respond(200, {
                        "success": False,
                        "message":
                            "Parolă incorectă."
                    })
                    return

                display = (
                    f"{user.prenume or ''} "
                    f"{user.nume or ''}".strip()
                    or username)

                token = save_token(
                    user_id      =
                        user.id_utilizator,
                    username     = username,
                    display_name = display,
                    role         = user.rol,
                )

                # Incarca regulile userului
                rules = self._load_user_rules(
                    user.id_utilizator)

                self._respond(200, {
                    "success": True,
                    "message":
                        "Autentificat cu succes!",
                    "token":   token,
                    "user_id": user.id_utilizator,
                    "role":    user.rol,
                    "display": sha256_name(display),
                    "rules":   rules,
                })
                print(f"[EXT SERVER] Login OK: "
                      f"{username}")

            finally:
                session.close()

        except Exception as e:
            print(f"[EXT SERVER] Auth err: {e}")
            self._respond(200, {
                "success": False,
                "message": f"Eroare server: {e}"
            })

    def _handle_time_used(self, data: dict):
        """
        Primeste timpul petrecut pe un domeniu de la extensia Chrome.
        Payload: { token, domain, used_seconds }
        """
        try:
            token  = data.get("token", "")
            domain = data.get("domain", "")
            used   = int(data.get("used_seconds", 0))

            from utils.extension_auth import verify_token
            token_data = verify_token(token)
            if not token_data:
                self._respond(200, {"success": False,
                                    "message": "Token invalid."})
                return

            user_id = token_data.get("user_id")
            cb = ExtensionHandler.on_time_update
            if cb and domain and used > 0:
                try:
                    cb(user_id, domain, used)
                except Exception as e:
                    print(f"[EXT SERVER] time_update cb err: {e}")

            self._respond(200, {"success": True})
        except Exception as e:
            print(f"[EXT SERVER] time_used err: {e}")
            self._respond(200, {"success": False,
                                "message": str(e)})

    def _handle_event(self, data: dict):
        """Proceseaza un eveniment de la extensie."""
        try:
            action  = data.get("action", "")
            domain  = data.get("domain", "")
            user_id = data.get("user_id")
            token   = data.get("token", "")

            # Verifica token
            from utils.extension_auth import (
                verify_token)
            token_data = verify_token(token)
            if not token_data:
                self._respond(200, {
                    "success": False,
                    "message": "Token invalid."
                })
                return

            if action == "blocked":
                self._process_blocked(
                    domain, data, token_data)

            self._log_activity(data, token_data)
            self._respond(200, {"success": True})

        except Exception as e:
            print(f"[EXT SERVER] Event err: {e}")
            self._respond(200, {
                "success": False,
                "message": str(e)})

    def _process_blocked(self, domain: str,
                          data: dict,
                          token_data: dict):
        """
        Proceseaza un eveniment de blocare.
        Trimite alerta Pushbullet la prima blocare
        si din nou dupa ALERT_THRESHOLD incercari repetate.
        """
        import time
        user_id   = token_data.get("user_id")
        username  = token_data.get("username")
        reason    = data.get("reason", "blocat")

        print(f"[EXT SERVER] BLOCAT: "
              f"{domain} pentru user {user_id}")

        # Contor incercari repetate (in ultimele 5 minute)
        key = (user_id, domain)
        now = time.time()
        window = 300  # 5 minute

        attempts = ExtensionHandler._blocked_attempts
        if key not in attempts:
            attempts[key] = []

        # Pastreaza doar tentativele recente
        attempts[key] = [t for t in attempts[key]
                         if now - t < window]
        attempts[key].append(now)
        count = len(attempts[key])

        print(f"[EXT SERVER] Tentativa {count} "
              f"pentru {domain} (user {user_id})")

        # Trimite PB la prima incercare sau la fiecare THRESHOLD
        should_alert = (
            count == 1 or
            count % ExtensionHandler.ALERT_THRESHOLD == 0
        )

        if should_alert:
            threading.Thread(
                target=self._send_pushbullet_alert,
                args=(domain, user_id,
                      username, reason, count),
                daemon=True,
            ).start()

    def _send_pushbullet_alert(
            self, domain: str,
            user_id: int,
            username: str,
            reason: str,
            count: int = 1):
        try:
            from database import (
                get_session, PersoanaContact)
            from utils.pushbullet_notifier import (
                send_notification)

            session = get_session(
                ExtensionHandler.engine)
            try:
                contact = session.query(
                    PersoanaContact).filter(
                    PersoanaContact.id_utilizator
                    == user_id,
                    PersoanaContact.cheie_pushbullet
                    .isnot(None),
                ).first()

                if not contact:
                    print(f"[EXT SERVER] "
                          f"Niciun contact PB "
                          f"pentru user {user_id}")
                    return

                if reason == "limit_exceeded":
                    urgency = "medie"
                    title   = "Limita de timp depasita"
                    body    = (
                        f"Utilizatorul @{username} "
                        f"a depasit limita de timp "
                        f"pentru: {domain}\n"
                        f"Tab-ul a fost inchis automat.")
                else:
                    # Urgenta creste cu numarul de incercari
                    if count >= 6:
                        urgency = "critica"
                    elif count >= 3:
                        urgency = "ridicata"
                    else:
                        urgency = "medie"

                    incercari = (
                        f" ({count} incercari"
                        f" in ultimele 5 min)"
                        if count > 1 else "")

                    title = f"Site blocat accesat{incercari}"
                    body  = (
                        f"Utilizatorul @{username} "
                        f"a incercat sa acceseze:\n"
                        f"{domain}\n"
                        f"Tab-ul a fost inchis automat.")

                send_notification(
                    api_key       = contact.cheie_pushbullet,
                    title         = title,
                    body          = body,
                    urgency_level = urgency)

                print(f"[EXT SERVER] PB trimis: "
                      f"{domain} (urgenta={urgency}, "
                      f"tentativa={count})")

            finally:
                session.close()
        except Exception as e:
            print(f"[EXT SERVER] PB err: {e}")

    def _log_activity(self, data: dict,
                       token_data: dict):
        try:
            from database import (
                get_session, ActivityLog)
            from datetime import datetime

            session = get_session(
                ExtensionHandler.engine)
            try:
                log = ActivityLog(
                    id_utilizator=token_data.get(
                        "user_id"),
                    tip="site",
                    nume=data.get("title", "")
                        or data.get("domain", ""),
                    domeniu=data.get("domain"),
                    inceput_la=datetime.now(),
                    blocat=(data.get("action")
                            == "blocked"),
                )
                session.add(log)
                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"[EXT SERVER] Log err: {e}")

    def _get_rules(self, user_id: str):
        try:
            # Returneaza toate regulile active
            # (admin a setat pentru toti)
            rules = self._load_all_active_rules()
            self._respond(200, rules)
        except Exception:
            self._respond(200, {
                "blocked": [],
                "limited": {}})

    def _load_all_active_rules(self) -> dict:
        try:
            from database import (
                get_session, SiteRule)
            session = get_session(
                ExtensionHandler.engine)
            try:
                rules = session.query(
                    SiteRule).filter_by(
                    activ=True).all()
                blocked = list(set(
                    r.domeniu for r in rules
                    if r.tip == "blocat"))
                limited = {}
                for r in rules:
                    if r.tip == "limitat":
                        limited[r.domeniu] = \
                            r.limita_minute or 30
                return {
                    "blocked": blocked,
                    "limited": limited,
                }
            finally:
                session.close()
        except Exception as e:
            print(f"[EXT SERVER] Rules err: {e}")
            return {"blocked": [], "limited": {}}

    def _load_user_rules(self,
                          user_id: int) -> dict:
        try:
            from database import (
                get_session, SiteRule)
            session = get_session(
                ExtensionHandler.engine)
            try:
                rules = session.query(
                    SiteRule).filter_by(
                    id_utilizator=user_id,
                    activ=True,
                ).all()
                return {
                    "blocked": [
                        r.domeniu for r in rules
                        if r.tip == "blocat"],
                    "limited": {
                        r.domeniu:
                            r.limita_minute or 30
                        for r in rules
                        if r.tip == "limitat"},
                }
            finally:
                session.close()
        except Exception:
            return {"blocked": [], "limited": {}}

    def _cors_headers(self):
        self.send_header(
            'Access-Control-Allow-Origin', '*')
        self.send_header(
            'Access-Control-Allow-Methods',
            'POST, GET, OPTIONS')
        self.send_header(
            'Access-Control-Allow-Headers',
            'Content-Type')

    def _respond(self, code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self._cors_headers()
        self.send_header(
            'Content-Type', 'application/json')
        self.send_header(
            'Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


def start_extension_server(engine,
                             port: int = 7842,
                             on_time_update=None):
    """
    Porneste serverul HTTP intr-un proces
    separat pentru a evita conflictele cu tkinter.
    on_time_update(user_id, domain, used_seconds) — callback optional.
    """
    import time
    import socket

    ExtensionHandler.engine         = engine
    ExtensionHandler.on_time_update = on_time_update

    # Incearca sa porneasca serverul direct
    # in thread cu retry
    def _run_server():
        try:
            srv = HTTPServer(
                ('localhost', port),
                ExtensionHandler)
            print(f"[EXT SERVER] Pornit "
                  f"pe localhost:{port} "
                  f"(attempt 1)")
            srv.serve_forever()
        except OSError as e:
            if "10048" in str(e) or \
               "Address already in use" in str(e):
                print(f"[EXT SERVER] Port {port} "
                      f"deja ocupat — "
                      f"serverul ruleaza deja.")
            else:
                print(f"[EXT SERVER] Eroare: {e}")

    t = threading.Thread(
        target=_run_server,
        daemon=True,
        name="ExtensionServer",
    )
    t.start()

    # Asteapta sa porneasca
    for i in range(10):
        time.sleep(0.3)
        s = socket.socket()
        result = s.connect_ex(
            ('localhost', port))
        s.close()
        if result == 0:
            print(f"[EXT SERVER] ✓ Activ "
                  f"pe port {port}")
            return t
        print(f"[EXT SERVER] Astept... "
              f"({i+1}/10)")

    print(f"[EXT SERVER] ✗ Nu raspunde "
          f"dupa 3s pe port {port}")
    return t