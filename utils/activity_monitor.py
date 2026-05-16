"""
Coffee & Axl - Activity Monitor
Monitorizeaza aplicatii active + primeste date
de la extensia Chrome prin fisier IPC.
Verifica reguli site-uri si alerteaza.
"""

import threading
import time
import os
import json
from datetime import datetime, date
from typing import Callable


CAFE_DIR         = os.path.join(
    os.path.expanduser("~"), ".coffee_axl")
ACTIVITY_IPC     = os.path.join(
    CAFE_DIR, "activity_ipc.json")
BLOCKED_ALERT    = os.path.join(
    CAFE_DIR, "blocked_alert.json")


class ActivityMonitor:

    def __init__(self,
                 engine,
                 user_id: int,
                 user_name: str,
                 pb_api_key: str = "",
                 on_blocked: Callable = None,
                 on_stats_update: Callable = None):
        self._engine          = engine
        self._user_id         = user_id
        self._user_name       = user_name
        self._pb_api_key      = pb_api_key
        self._on_blocked      = on_blocked
        self._on_stats_update = on_stats_update

        self._running         = False
        self._current_site    = None
        self._current_app     = None
        self._site_start      = None
        self._app_start       = None
        self._rules_cache     = {}
        self._time_used       = {}
        # {domeniu: secunde_folosite_azi}
        self._app_start_time  = time.time()

        os.makedirs(CAFE_DIR, exist_ok=True)

    def start(self):
        self._running = True
        self._load_rules()

        threading.Thread(
            target=self._loop_browser,
            daemon=True).start()
        threading.Thread(
            target=self._loop_desktop,
            daemon=True).start()
        threading.Thread(
            target=self._loop_stats,
            daemon=True).start()
        print("[MONITOR] Pornit.")

    def stop(self):
        self._running = False
        self._flush_current()

    # ── Reguli ────────────────────────────────────────────────────────────────

    def _load_rules(self):
        """Incarca regulile din DB."""
        try:
            from database import get_session, SiteRule
            session = get_session(self._engine)
            try:
                rules = session.query(SiteRule)\
                    .filter_by(
                    id_utilizator=self._user_id,
                    activ=True,
                ).all()
                self._rules_cache = {
                    r.domeniu: {
                        "tip":    r.tip,
                        "limita": r.limita_minute,
                    }
                    for r in rules
                }
                print(f"[MONITOR] "
                      f"{len(self._rules_cache)} "
                      f"reguli incarcate.")
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITOR] Reguli eroare: {e}")

    def reload_rules(self):
        self._load_rules()

    def _check_domain(self,
                       domain: str) -> str:
        """
        Verifica un domeniu contra regulilor.
        Returneaza: 'blocat' | 'limitat' | 'ok'
        """
        if not domain:
            return "ok"

        # Cauta domeniu exact sau parinte
        for rule_domain, rule in \
                self._rules_cache.items():
            if (domain == rule_domain
                    or domain.endswith(
                        f".{rule_domain}")):
                if rule["tip"] == "blocat":
                    return "blocat"
                elif rule["tip"] == "limitat":
                    limita_sec = (
                        rule["limita"] or 0) * 60
                    folosit = self._time_used.get(
                        domain, 0)
                    if folosit >= limita_sec:
                        return "limitat_depasit"
                    return "ok"
        return "ok"

    # ── Loop browser (IPC cu extensia Chrome) ─────────────────────────────────

    def _loop_browser(self):
        """
        Citeste date de la extensia Chrome
        prin fisier IPC JSON.
        """
        while self._running:
            try:
                if os.path.exists(ACTIVITY_IPC):
                    with open(
                            ACTIVITY_IPC, "r",
                            encoding="utf-8") as f:
                        data = json.load(f)
                    os.remove(ACTIVITY_IPC)

                    domain = data.get(
                        "domain", "")
                    url    = data.get("url", "")
                    title  = data.get("title", "")
                    action = data.get(
                        "action", "visit")
                    # action: visit | leave | close

                    if action == "visit":
                        self._on_site_visit(
                            domain, url, title)
                    elif action in (
                            "leave", "close"):
                        self._on_site_leave(domain)

            except Exception:
                pass
            time.sleep(0.5)

    def _on_site_visit(self, domain: str,
                        url: str, title: str):
        # Inchide sesiunea anterioara
        if self._current_site and \
                self._current_site != domain:
            self._on_site_leave(
                self._current_site)

        status = self._check_domain(domain)

        if status == "blocat":
            self._block_site(domain, url)
            return
        elif status == "limitat_depasit":
            self._block_site(
                domain, url, limitat=True)
            return

        # Inregistreaza vizita
        self._current_site = domain
        self._site_start   = datetime.now()

        self._log_activity(
            tip="site",
            nume=title or domain,
            domeniu=domain,
            blocat=False)

    def _on_site_leave(self, domain: str):
        if (self._current_site == domain
                and self._site_start):
            elapsed = int(
                (datetime.now() -
                 self._site_start)
                .total_seconds())

            # Actualizeaza timp folosit
            self._time_used[domain] = \
                self._time_used.get(
                    domain, 0) + elapsed

            # Update log in DB
            self._update_activity_duration(
                domain, elapsed)

            self._current_site = None
            self._site_start   = None

    def _block_site(self, domain: str,
                     url: str,
                     limitat: bool = False):
        """Blocheaza site si trimite alerte."""
        print(f"[MONITOR] BLOCAT: {domain}")

        # Scrie comanda de blocare pentru extensie
        try:
            block_cmd = {
                "action": "block",
                "domain": domain,
                "url":    url,
                "reason": "limitat" if limitat
                else "blocat",
            }
            with open(BLOCKED_ALERT, "w",
                      encoding="utf-8") as f:
                json.dump(block_cmd, f)
        except Exception:
            pass

        # Log in DB
        self._log_activity(
            tip="site",
            nume=domain,
            domeniu=domain,
            blocat=True)

        # Callback UI
        if self._on_blocked:
            self._on_blocked(
                domain, limitat)

        # Pushbullet
        self._send_alert(domain, limitat)

    # ── Loop desktop ──────────────────────────────────────────────────────────

    def _loop_desktop(self):
        """Monitorizeaza aplicatia activa."""
        while self._running:
            try:
                app = self._get_active_app()
                if app and app != self._current_app:
                    self._on_app_change(app)
            except Exception:
                pass
            time.sleep(5)

    def _get_active_app(self) -> str:
        """Returneaza numele aplicatiei active."""
        try:
            import ctypes
            import ctypes.wintypes

            hwnd = ctypes.windll.user32\
                .GetForegroundWindow()
            pid  = ctypes.wintypes.DWORD()
            ctypes.windll.user32\
                .GetWindowThreadProcessId(
                hwnd,
                ctypes.byref(pid))

            import psutil
            proc = psutil.Process(pid.value)
            return proc.name().replace(
                ".exe", "")
        except Exception:
            return ""

    def _on_app_change(self, app: str):
        if self._current_app and \
                self._app_start:
            elapsed = int(
                (datetime.now() -
                 self._app_start)
                .total_seconds())
            self._update_activity_duration(
                self._current_app, elapsed,
                tip="aplicatie")

        self._current_app  = app
        self._app_start    = datetime.now()
        self._log_activity(
            tip="aplicatie",
            nume=app,
            domeniu=None,
            blocat=False)

    # ── Loop stats ────────────────────────────────────────────────────────────

    def _loop_stats(self):
        """Actualizeaza statisticile zilnice la 60s."""
        while self._running:
            time.sleep(60)
            self._update_daily_stats()
            if self._on_stats_update:
                self._on_stats_update()

    def _update_daily_stats(self):
        try:
            from database import (
                get_session, DailyStats)
            from sqlalchemy import and_

            session = get_session(self._engine)
            try:
                today = date.today()
                stat  = session.query(
                    DailyStats).filter(
                    and_(
                        DailyStats.id_utilizator
                        == self._user_id,
                        DailyStats.data == today,
                    )).first()

                if not stat:
                    stat = DailyStats(
                        id_utilizator=self._user_id,
                        data=today,
                        timp_total_sec=0,
                        timp_blocat_sec=0,
                    )
                    session.add(stat)

                # Calculeaza timp total azi
                from database import ActivityLog
                logs = session.query(
                    ActivityLog).filter(
                    and_(
                        ActivityLog.id_utilizator
                        == self._user_id,
                        ActivityLog.inceput_la
                        >= datetime.combine(
                            today,
                            datetime.min.time()),
                    )).all()

                total  = sum(
                    l.durata_secunde or 0
                    for l in logs
                    if not l.blocat)
                blocat = sum(
                    l.durata_secunde or 0
                    for l in logs
                    if l.blocat)

                # Foloseste timpul real de sistem
                # (de la boot sau miezul noptii)
                timp_sistem = self.get_today_total_time()
                stat.timp_total_sec  = max(
                    total, timp_sistem)
                stat.timp_blocat_sec = blocat
                stat.site_uri_vizitate = len(
                    set(l.domeniu
                        for l in logs
                        if l.domeniu))

                session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITOR] Stats err: {e}")

    # ── DB helpers ────────────────────────────────────────────────────────────

    def _log_activity(self, tip: str,
                       nume: str,
                       domeniu: str,
                       blocat: bool):
        try:
            from database import (
                get_session, ActivityLog)
            session = get_session(self._engine)
            try:
                log = ActivityLog(
                    id_utilizator=self._user_id,
                    tip=tip,
                    nume=nume,
                    domeniu=domeniu,
                    inceput_la=datetime.now(),
                    blocat=blocat,
                )
                session.add(log)
                session.commit()
                self._last_log_id = log.id
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITOR] Log err: {e}")

    def _update_activity_duration(
            self, identificator: str,
            elapsed: int,
            tip: str = "site"):
        try:
            from database import (
                get_session, ActivityLog)
            from sqlalchemy import and_

            session = get_session(self._engine)
            try:
                log = session.query(
                    ActivityLog).filter(
                    and_(
                        ActivityLog.id_utilizator
                        == self._user_id,
                        ActivityLog.tip == tip,
                        ActivityLog.sfarsit_la
                        .is_(None),
                    )).order_by(
                    ActivityLog.inceput_la.desc()
                ).first()

                if log:
                    log.sfarsit_la = datetime.now()
                    log.durata_secunde = elapsed
                    session.commit()
            finally:
                session.close()
        except Exception as e:
            print(f"[MONITOR] Dur err: {e}")

    def _flush_current(self):
        if self._current_site and \
                self._site_start:
            elapsed = int(
                (datetime.now() -
                 self._site_start)
                .total_seconds())
            self._update_activity_duration(
                self._current_site, elapsed)

    # ── Alerte ────────────────────────────────────────────────────────────────

    def _send_alert(self, domain: str,
                     limitat: bool):
        if not self._pb_api_key:
            return

        try:
            from utils.pushbullet_notifier import (
                send_notification)

            if limitat:
                title = "⏱ Limită de timp depășită"
                body  = (
                    f"Utilizatorul {self._user_name} "
                    f"a depășit limita de timp "
                    f"pentru: {domain}")
            else:
                title = "🚫 Site interzis accesat"
                body  = (
                    f"Utilizatorul {self._user_name} "
                    f"a încercat să acceseze "
                    f"site-ul interzis: {domain}\n"
                    f"Tab-ul a fost închis automat.")

            send_notification(
                api_key=self._pb_api_key,
                title=title,
                body=body)
            print(f"[MONITOR] Alerta PB: {domain}")
        except Exception as e:
            print(f"[MONITOR] PB err: {e}")

    # ── Status public ─────────────────────────────────────────────────────────

    def get_today_stats(self) -> dict:
        try:
            from database import (
                get_session, ActivityLog,
                DailyStats)
            from sqlalchemy import and_

            session = get_session(self._engine)
            try:
                today = date.today()
                stat  = session.query(
                    DailyStats).filter_by(
                    id_utilizator=self._user_id,
                    data=today,
                ).first()

                return {
                    "timp_total":   getattr(
                        stat,
                        "timp_total_sec", 0),
                    "timp_blocat":  getattr(
                        stat,
                        "timp_blocat_sec", 0),
                    "site_uri":     getattr(
                        stat,
                        "site_uri_vizitate", 0),
                    "site_curent":
                        self._current_site,
                    "app_curenta":
                        self._current_app,
                }
            finally:
                session.close()
        except Exception:
            return {}

    def get_time_used(self,
                       domain: str) -> int:
        """Secunde petrecute pe un domeniu azi."""
        return self._time_used.get(domain, 0)

    def get_today_total_time(self) -> int:
        """
        Returneaza secundele petrecute la calculator
        azi — de la pornirea calculatorului sau de la
        miezul noptii, oricare e mai recent.
        """
        try:
            import psutil
            from datetime import datetime, date

            # Momentul cand s-a pornit calculatorul
            boot_ts    = psutil.boot_time()
            boot_dt    = datetime.fromtimestamp(
                boot_ts)

            # Miezul noptii de azi
            midnight   = datetime.combine(
                date.today(),
                datetime.min.time())
            midnight_ts = midnight.timestamp()

            # Folosim ce e mai recent:
            # daca calculatorul a pornit azi,
            # folosim boot time
            # daca ruleaza de ieri/mai mult,
            # folosim miezul noptii
            start_ts = max(boot_ts, midnight_ts)

            return int(time.time() - start_ts)

        except Exception:
            # Fallback la vechea metoda
            if not hasattr(self, '_app_start_time'):
                self._app_start_time = time.time()
            return int(
                time.time() - self._app_start_time)

    def get_today_stats(self) -> dict:
        base = {
            "timp_total":  self.get_today_total_time(),
            "timp_blocat": 0,
            "site_uri":    len(self._time_used),
            "site_curent": self._current_site,
            "app_curenta": self._current_app,
            "time_used":   dict(self._time_used),
        }
        # Adauga timp_blocat din DB
        try:
            from database import (
                get_session, ActivityLog)
            from sqlalchemy import and_
            from datetime import date, datetime

            session = get_session(self._engine)
            try:
                today = date.today()
                logs  = session.query(
                    ActivityLog).filter(
                    and_(
                        ActivityLog.id_utilizator
                        == self._user_id,
                        ActivityLog.blocat == True,
                        ActivityLog.inceput_la
                        >= datetime.combine(
                            today,
                            datetime.min.time()),
                    )).all()
                base["timp_blocat"] = sum(
                    l.durata_secunde or 0
                    for l in logs)
            finally:
                session.close()
        except Exception:
            pass
        return base