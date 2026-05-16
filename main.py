"""
Coffee & Axl - Digital Wellness Platform
Punct de intrare cu rutare pe roluri si daemon pet.
"""

import os
import sys
import threading

# Suprima warning-urile MediaPipe si TensorFlow
os.environ["GLOG_minloglevel"]   = "3"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import customtkinter as ctk

from database import init_db
from screens import LoginScreen, DashboardPacient, DashboardAdmin
from utils.theme import WINDOW_WIDTH, WINDOW_HEIGHT
from utils.session import load_session, clear_session
from utils.extension_auth import save_token
from utils.extension_server import start_extension_server

IPC_FILE   = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "pet_ipc.txt")
FOCUS_FILE = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "focus_app.txt")
APP_LOCK   = os.path.join(
    os.path.expanduser("~"), ".coffee_axl", "app.lock")


def _send_ipc(cmd: str):
    try:
        os.makedirs(os.path.dirname(IPC_FILE), exist_ok=True)
        with open(IPC_FILE, "w") as f:
            f.write(cmd)
    except Exception:
        pass


def _write_app_lock():
    try:
        os.makedirs(os.path.dirname(APP_LOCK), exist_ok=True)
        with open(APP_LOCK, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _clear_app_lock():
    try:
        if os.path.exists(APP_LOCK):
            os.remove(APP_LOCK)
    except Exception:
        pass


class CoffeeAxlApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Coffee & Axl · Digital Wellness")
        self._set_icon()
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(960, 620)
        self._center_window()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.engine             = init_db()
        self._current_screen    = None
        self._activity_monitor  = None

        # Scrie PID-ul in app.lock
        # ca pet_daemon sa stie ca rulam
        self._write_app_lock()

        # Incearca cu on_time_update (versiunea noua)
        # Fallback la versiunea veche daca nu e inca actualizata
        try:
            self._ext_server = start_extension_server(
                self.engine,
                on_time_update=self._on_time_update)
        except TypeError:
            self._ext_server = start_extension_server(
                self.engine)
            print("[APP] extension_server vechi detectat — "
                  "sincronizare timeUsed dezactivata. "
                  "Inlocuieste utils/extension_server.py.")
        if self._ext_server:
            print("[APP] Extension server OK")
        else:
            print("[APP] Extension server FAILED")

        threading.Thread(
            target=self._keep_server_alive,
            daemon=True,
        ).start()

        threading.Thread(
            target=self._poll_extension_auth,
            daemon=True,
        ).start()

        # Inregistreaza autostart daca nu e deja
        self._ensure_autostart()

        # Porneste daemon-ul pet
        self._launch_daemon()

        # Polling focus de la daemon
        self._poll_focus()

        # Incearca restaurare sesiune
        # Daca pornit cu --hidden, ascunde fereastra pana la login
        if "--hidden" in sys.argv:
            self.withdraw()
            print("[APP] Pornit in fundal (--hidden).")

        self._try_restore_session()

    # ── Server ────────────────────────────────────────────────────────────────

    def _keep_server_alive(self):
        import socket
        import time
        from utils.extension_server import (
            start_extension_server)

        # Asteapta 30s inainte de primul check
        # sa nu interfere cu pornirea initiala
        time.sleep(30)

        consecutive_fails = 0

        while True:
            time.sleep(15)
            s = socket.socket()
            result = s.connect_ex(
                ('localhost', 7842))
            s.close()

            if result == 0:
                consecutive_fails = 0
            else:
                consecutive_fails += 1
                print(f"[APP] Server check fail "
                      f"({consecutive_fails}/3)")

                # Doar dupa 3 esecuri consecutive
                # incercam repornire
                if consecutive_fails >= 3:
                    print("[APP] Server mort — "
                          "repornesc...")
                    self._ext_server = \
                        start_extension_server(
                            self.engine)
                    consecutive_fails = 0

    # ── Daemon ────────────────────────────────────────────────────────────────

    def _ensure_autostart(self):
        """
        Inregistreaza ambele componente in autostart Windows
        la prima pornire. Nu face nimic daca sunt deja inregistrate.
        """
        try:
            from startup_manager import (
                is_registered, register_startup)
            if not is_registered():
                ok = register_startup()
                if ok:
                    print("[APP] Autostart inregistrat "
                          "— va porni la urmatoarea "
                          "repornire Windows.")
        except Exception as e:
            print(f"[AUTOSTART] {e}")

    def _launch_daemon(self):
        try:
            from startup_manager import (
                launch_daemon_if_not_running,
            )
            launch_daemon_if_not_running()
        except Exception as e:
            print(f"[DAEMON] {e}")

    def _poll_extension_auth(self):
        from utils.extension_auth import process_auth_request
        import time
        while True:
            try:
                if hasattr(self, 'engine') and self.engine:
                    process_auth_request(self.engine)
            except Exception as e:
                print(f"[EXT AUTH] Eroare: {e}")
            time.sleep(0.5)

    def _poll_focus(self):
        try:
            if os.path.exists(FOCUS_FILE):
                with open(FOCUS_FILE) as f:
                    cmd = f.read().strip()
                os.remove(FOCUS_FILE)

                # Aduce fereastra in fata in orice caz
                self.deiconify()
                self.lift()
                self.focus_force()
                self.wm_attributes("-topmost", True)
                self.after(
                    200,
                    lambda: self.wm_attributes(
                        "-topmost", False))

                if cmd == "open_chat":
                    print("[APP] Navigare la Chat Wellness")
                    # Navigheaza la Chat Wellness
                    if self._current_screen:
                        try:
                            self._current_screen \
                                ._navigate_to_chat()
                        except AttributeError:
                            try:
                                self._current_screen \
                                    ._tabs.set(
                                    "Chat Wellness")
                            except Exception as e:
                                print(f"[APP] Nav err: {e}")

        except Exception as e:
            print(f"[POLL] Eroare: {e}")

        self.after(500, self._poll_focus)

    # ── Sesiune ───────────────────────────────────────────────────────────────

    def _try_restore_session(self):
        """
        Daca exista sesiune valida, sare direct la dashboard.
        Altfel arata login-ul.
        """
        session_data = load_session()
        if session_data:
            print(f"[SESSION] Restaurez: {session_data['user_name']}")
            self._on_login(
                user_id      = session_data["user_id"],
                rol          = session_data["rol"],
                user_name    = session_data["user_name"],
                from_session = True,
            )
        else:
            self._show_login()

    # ── Fereastra ─────────────────────────────────────────────────────────────

    def _write_app_lock(self):
        _write_app_lock()

    def _center_window(self):
        self.update_idletasks()
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (w - WINDOW_WIDTH)  // 2
        y = (h - WINDOW_HEIGHT) // 2
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

    def _set_icon(self):
        """
        Iconita ferestrei foloseste ImageTk.PhotoImage — nu CTkImage.
        Acesta e comportamentul corect pentru iconphoto().
        """
        try:
            from PIL import Image, ImageTk
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "assets", "logo.png",
            )
            self._icon = ImageTk.PhotoImage(Image.open(path))
            self.iconphoto(True, self._icon)
        except Exception as e:
            print(f"[ICON] {e}")

    # ── Navigare ──────────────────────────────────────────────────────────────

    def _clear_screen(self):
        if self._current_screen:
            self._current_screen.destroy()
            self._current_screen = None

    def _show_login(self):
        # Opreste monitorul la logout
        self._stop_activity_monitor()
        self._clear_screen()
        self._set_icon()
        self._current_screen = LoginScreen(
            parent           = self,
            engine           = self.engine,
            on_login_success = self._on_login,
        )

    def _on_login(self, user_id: int, rol: str,
                  user_name: str, from_session: bool = False):
        print(f"[APP] Login: {user_name} | rol={rol} "
              f"| sesiune={from_session}")
        self._clear_screen()
        self._set_icon()

        # Trezeste si arata animalul
        _send_ipc("wake_and_show")

        # Porneste ActivityMonitor imediat la login
        # pentru rolul utilizator (nu admin/developer)
        if rol in ("utilizator", "pacient"):
            self._start_activity_monitor(user_id, user_name)
        else:
            self._activity_monitor = None

        dashboard_map = {
            "utilizator": DashboardPacient,
            "pacient":    DashboardPacient,
            "admin":      DashboardAdmin,
            "developer":  DashboardAdmin,
        }

        DashboardClass = dashboard_map.get(rol, DashboardPacient)

        # Pasam monitorul gata pornit catre dashboard
        if DashboardClass is DashboardPacient:
            self._current_screen = DashboardClass(
                parent           = self,
                engine           = self.engine,
                user_id          = user_id,
                user_name        = user_name,
                on_logout        = self._show_login,
                activity_monitor = self._activity_monitor,
            )
        else:
            self._current_screen = DashboardClass(
                parent    = self,
                engine    = self.engine,
                user_id   = user_id,
                user_name = user_name,
                on_logout = self._show_login,
            )

        prenume = None
        nume    = None
        try:
            from database import get_session, Utilizator
            _s = get_session(self.engine)
            try:
                _u = _s.query(Utilizator).filter_by(
                    id_utilizator=user_id).first()
                if _u:
                    prenume = _u.prenume
                    nume    = _u.nume
            finally:
                _s.close()
        except Exception:
            pass

        try:
            display = (
                f"{prenume or ''} {nume or ''}"
                .strip() or user_name)
            save_token(
                user_id      = user_id,
                username     = user_name,
                display_name = display,
                role         = rol,
            )
            print("[AUTH] Token extensie Chrome generat.")
        except Exception as e:
            print(f"[AUTH] Token eroare: {e}")

    def _start_activity_monitor(self, user_id: int,
                                  user_name: str):
        """Porneste ActivityMonitor la login si il tine in main."""
        # Opreste monitorul anterior daca exista
        self._stop_activity_monitor()
        try:
            from utils.activity_monitor import ActivityMonitor
            from database import PersoanaContact, get_session

            pb_key  = ""
            session = get_session(self.engine)
            try:
                c = session.query(PersoanaContact).filter(
                    PersoanaContact.id_utilizator == user_id,
                    PersoanaContact.cheie_pushbullet.isnot(None),
                ).first()
                if c:
                    pb_key = c.cheie_pushbullet or ""
            finally:
                session.close()

            self._activity_monitor = ActivityMonitor(
                engine    = self.engine,
                user_id   = user_id,
                user_name = user_name,
                pb_api_key = pb_key,
            )
            self._activity_monitor.start()
            print(f"[APP] ActivityMonitor pornit "
                  f"pentru user {user_id}.")
        except Exception as e:
            print(f"[APP] ActivityMonitor eroare: {e}")
            self._activity_monitor = None

    def _on_time_update(self, user_id: int,
                        domain: str,
                        used_seconds: int):
        """
        Callback apelat de extension_server cand Chrome
        raporteaza timpul petrecut pe un domeniu.
        Actualizeaza _time_used in activity_monitor.
        """
        if not self._activity_monitor:
            return
        try:
            current = self._activity_monitor                ._time_used.get(domain, 0)
            # Actualizeaza doar daca valoarea e mai mare
            # (evita out-of-order)
            if used_seconds > current:
                self._activity_monitor                    ._time_used[domain] = used_seconds
        except Exception as e:
            print(f"[APP] time_update err: {e}")

    def _stop_activity_monitor(self):
        """Opreste ActivityMonitor la logout sau inchidere."""
        if hasattr(self, '_activity_monitor') and                 self._activity_monitor:
            try:
                self._activity_monitor.stop()
                print("[APP] ActivityMonitor oprit.")
            except Exception as e:
                print(f"[APP] ActivityMonitor stop err: {e}")
            self._activity_monitor = None

    def on_closing(self):
        """
        La X, aplicatia se ascunde in fundal — NU se inchide.
        Monitorizarea timpului continua sa ruleze.
        Fereastra poate fi redeschisa din click dreapta pe animalet.
        """
        self._stop_activity_monitor()
        self.withdraw()
        print("[APP] Fereastra ascunsa — "
              "ruleaza in fundal. "
              "Click dreapta pe animalet -> Deschide.")

    def on_quit(self):
        """Inchidere completa — sterge lock-ul."""
        self._stop_activity_monitor()
        _clear_app_lock()
        self.destroy()


def main():
    app = CoffeeAxlApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
    # La iesire din mainloop, sterge lock-ul
    _clear_app_lock()


if __name__ == "__main__":
    main()