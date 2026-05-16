"""
Coffee & Axl - Startup Manager
Inregistreaza / sterge pet_daemon.py din autostart Windows.
"""

import os
import sys
import winreg
import subprocess

DAEMON_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "pet_daemon.py")

MAIN_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "main.py")

REG_KEY       = (r"Software\Microsoft\Windows"
                 r"\CurrentVersion\Run")
REG_NAME      = "CoffeeAxlPet"
REG_NAME_MAIN = "CoffeeAxlApp"


def register_startup() -> bool:
    """
    Adauga atat pet_daemon cat si main.py
    in registry pentru autostart la pornirea Windows.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY,
            0, winreg.KEY_SET_VALUE)

        # 1. pet_daemon — porneste animatia in system tray
        cmd_daemon = (f'"{sys.executable}" ' +
                      f'"{DAEMON_SCRIPT}"')
        winreg.SetValueEx(
            key, REG_NAME, 0,
            winreg.REG_SZ, cmd_daemon)

        # 2. main.py — porneste aplicatia principala
        # --hidden = porneste minimizat in fundal
        cmd_main = (f'"{sys.executable}" ' +
                    f'"{MAIN_SCRIPT}" --hidden')
        winreg.SetValueEx(
            key, REG_NAME_MAIN, 0,
            winreg.REG_SZ, cmd_main)

        winreg.CloseKey(key)
        print("[STARTUP] Ambele componente "
              "inregistrate in registry.")
        return True
    except Exception as e:
        print(f"[STARTUP] Eroare register: {e}")
        return False


def unregister_startup() -> bool:
    """Sterge atat pet_daemon cat si main.py din autostart."""
    ok = True
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY,
            0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, REG_NAME)
        except Exception:
            pass
        try:
            winreg.DeleteValue(key, REG_NAME_MAIN)
        except Exception:
            pass
        winreg.CloseKey(key)
        print("[STARTUP] Scos din autostart.")
    except Exception as e:
        print(f"[STARTUP] Eroare unregister: {e}")
        ok = False
    return ok


def is_registered() -> bool:
    """Returneaza True doar daca AMBELE intrari sunt in registry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REG_KEY,
            0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, REG_NAME)
            winreg.QueryValueEx(key, REG_NAME_MAIN)
            winreg.CloseKey(key)
            return True
        except Exception:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def launch_daemon_if_not_running():
    """Porneste pet_daemon.py daca nu ruleaza deja."""
    lock = os.path.join(
        os.path.expanduser("~"),
        ".coffee_axl", "pet.lock")

    already = False

    if os.path.exists(lock):
        try:
            with open(lock) as f:
                pid = int(f.read().strip())

            import ctypes
            handle = ctypes.windll.kernel32\
                .OpenProcess(0x0400, False, pid)
            if handle:
                ctypes.windll.kernel32\
                    .CloseHandle(handle)
                already = True
        except Exception:
            # Lock exista dar procesul nu mai ruleaza
            try:
                os.remove(lock)
            except Exception:
                pass

    if not already:
        subprocess.Popen(
            [sys.executable, DAEMON_SCRIPT],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print("[STARTUP] Pet daemon pornit.")
    else:
        print("[STARTUP] Pet daemon deja rulează.")