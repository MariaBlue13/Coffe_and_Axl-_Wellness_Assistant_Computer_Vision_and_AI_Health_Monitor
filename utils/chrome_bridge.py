"""
Coffee & Axl - Chrome Bridge
Sincronizeaza reguli, procesa autentificare
si primeste evenimente de la extensia Chrome.
"""

import json
import os
import time
import threading
import hashlib
from typing import Callable

CAFE_DIR    = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
RULES_FILE  = os.path.join(
    CAFE_DIR, "chrome_rules.json")
EVENTS_FILE = os.path.join(
    CAFE_DIR, "chrome_events.json")
AUTH_REQ    = os.path.join(
    CAFE_DIR, "ext_auth_request.json")
AUTH_RESP   = os.path.join(
    CAFE_DIR, "ext_auth_response.json")


class ChromeBridge:

    def __init__(self,
                 engine=None,
                 on_event: Callable = None,
                 on_blocked: Callable = None):
        self._engine     = engine
        self._on_event   = on_event
        self._on_blocked = on_blocked
        self._running    = False
        os.makedirs(CAFE_DIR, exist_ok=True)

    def start(self):
        self._running = True
        threading.Thread(
            target=self._poll_loop,
            daemon=True).start()
        threading.Thread(
            target=self._poll_events,
            daemon=True).start()
        print("[CHROME BRIDGE] Pornit.")

    def stop(self):
        self._running = False

    def publish_rules(self, blocked: list,
                       limited: dict,
                       user_id: int = None):
        """Publica regulile pentru extensie."""
        try:
            rules = {
                "blocked":  blocked,
                "limited":  limited,
                "user_id":  user_id,
                "ts":       time.time(),
            }
            with open(RULES_FILE, "w",
                      encoding="utf-8") as f:
                json.dump(rules, f,
                          indent=2,
                          ensure_ascii=False)
            print(f"[CHROME BRIDGE] "
                  f"{len(blocked)} blocate, "
                  f"{len(limited)} limitate.")
        except Exception as e:
            print(f"[CHROME BRIDGE] "
                  f"Publish err: {e}")

    def _poll_loop(self):
        while self._running:
            self._check_auth()
            time.sleep(0.5)

    def _check_auth(self):
        """Proceseaza cereri de autentificare."""
        if not os.path.exists(AUTH_REQ):
            return
        if self._engine:
            from utils.extension_auth import (
                process_auth_request)
            process_auth_request(self._engine)

    def _poll_events(self):
        """Citeste evenimente de la extensie."""
        while self._running:
            try:
                if os.path.exists(EVENTS_FILE):
                    with open(
                            EVENTS_FILE, "r",
                            encoding="utf-8"
                    ) as f:
                        data = json.load(f)
                    os.remove(EVENTS_FILE)
                    print(f"[CHROME BRIDGE] "
                          f"Event: "
                          f"{data.get('action')}"
                          f" {data.get('domain')}")
                    if self._on_event:
                        self._on_event(data)
                    if (data.get("action")
                            == "blocked"
                            and self._on_blocked):
                        self._on_blocked(
                            data.get("domain",""),
                            data.get("user_id"),
                            data.get("reason",
                                     "blocat"))
            except Exception as e:
                print(f"[CHROME BRIDGE] "
                      f"Poll err: {e}")
            time.sleep(0.5)