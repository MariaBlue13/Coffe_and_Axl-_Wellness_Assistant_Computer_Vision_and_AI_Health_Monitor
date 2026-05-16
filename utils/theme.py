"""
Coffee & Axl - Paleta de culori si constante tema
"""

# ─── Paleta principala ────────────────────────────────────────────────────────
NAVY        = "#406093"   # albastru inchis - primary dark
BLUE        = "#4C8CE4"   # albastru viu    - accent principal
GREEN       = "#91D06C"   # verde           - succes / sanatate
YELLOW      = "#FFF799"   # galben pal      - highlight / wellness

# ─── Culori derivate ──────────────────────────────────────────────────────────
NAVY_DARK   = "#2E4A72"   # hover navy
NAVY_LIGHT  = "#5A7DAA"   # border navy subtil
BLUE_HOVER  = "#3A7AD4"   # hover buton albastru
GREEN_DARK  = "#6DB84A"   # verde inchis
YELLOW_SOFT = "#FFF3A0"   # galben si mai pal

WHITE       = "#FFFFFF"
OFF_WHITE   = "#F8F9FC"
GRAY_LIGHT  = "#E8ECF3"
GRAY_MID    = "#B0BDD0"
GRAY_DARK   = "#6B7A91"
TEXT_DARK   = "#1A2540"
TEXT_MID    = "#3D4F6B"
TEXT_LIGHT  = "#7A8BAA"

ERROR_RED   = "#E05555"
WARNING_AMB = "#F0A030"

# ─── Tipografie ───────────────────────────────────────────────────────────────
FONT_TITLE    = ("Georgia", 28, "bold")
FONT_TITLE_SM = ("Georgia", 22, "bold")
FONT_SUBTITLE = ("Georgia", 14, "italic")
FONT_HEADING  = ("Arial", 16, "bold")
FONT_HEADING_SM = ("Arial", 14, "bold")
FONT_BODY     = ("Arial", 13)
FONT_BODY_SM  = ("Arial", 12)
FONT_SMALL    = ("Arial", 11)
FONT_TINY     = ("Arial", 10)
FONT_LABEL    = ("Arial", 12, "bold")
FONT_LABEL_SM = ("Arial", 11, "bold")
FONT_MONO     = ("Courier New", 12)
FONT_NUM_LG   = ("Georgia", 28, "bold")
FONT_NUM_MD   = ("Georgia", 22, "bold")

# ─── Dimensiuni UI ────────────────────────────────────────────────────────────
WINDOW_WIDTH  = 1200
WINDOW_HEIGHT = 750
LOGIN_WIDTH   = 480
LOGIN_HEIGHT  = 580
CORNER_RADIUS = 14
CORNER_RADIUS_SM = 8
CORNER_RADIUS_LG = 20
BTN_HEIGHT    = 44
BTN_HEIGHT_SM = 34
INPUT_HEIGHT  = 44
SIDEBAR_WIDTH = 230

# ─── Culori suplimentare UI ───────────────────────────────────────────────────
# Card backgrounds
CARD_BG        = "#FFFFFF"
CARD_BG_ALT    = "#F5F8FF"
CARD_BORDER    = "#E2EAF5"

# Sidebar gradient simulat (doua straturi)
SIDEBAR_TOP    = "#2E4A72"   # mai inchis sus
SIDEBAR_BTM    = "#406093"   # navy normal jos

# Accent warm pentru wellness
WARM_ORANGE    = "#FF8C42"
WARM_PINK      = "#FF6B9D"
TEAL_ACCENT    = "#3EC9A7"

# Status
SUCCESS_BG     = "#E8F9F0"
SUCCESS_BORDER = "#6FCF97"
WARNING_BG     = "#FFF8E6"
WARNING_BORDER = "#F9A825"
ERROR_BG       = "#FFF0F0"
ERROR_BORDER   = "#FFAAAA"

# Badge-uri
BADGE_BLUE     = "#EAF2FF"
BADGE_GREEN    = "#E8F9F0"
BADGE_RED      = "#FFF0F0"
BADGE_YELLOW   = "#FFF8E0"

# ─── Mapare roluri catre culori ───────────────────────────────────────────────
ROL_CULORI = {
    "pacient":    BLUE,
    "medic":      GREEN,
    "admin":      NAVY,
    "developer":  YELLOW,
    "utilizator": BLUE,
}

ROL_ETICHETE = {
    "pacient":    "Pacient",
    "medic":      "Medic",
    "admin":      "Administrator",
    "developer":  "Developer",
    "utilizator": "Utilizator",
}


# ─── Incarcare logo ───────────────────────────────────────────────────────────

def load_logo(size: tuple = (48, 48)):
    """
    Incarca logo.png din folderul assets/ ca CTkImage.
    CTkImage se scaleza corect pe ecrane HiDPI — elimina warning-ul
    'Given image is not CTkImage'.
    Returneaza CTkImage sau None daca fisierul lipseste.
    """
    import os
    import customtkinter as ctk
    from PIL import Image

    try:
        base = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "assets", "logo.png")

        if not os.path.exists(path):
            return None

        img = Image.open(path).convert("RGBA")
        return ctk.CTkImage(
            light_image=img,
            dark_image=img,
            size=size,
        )
    except Exception as e:
        print(f"[LOGO] Eroare incarcare: {e}")
        return None
# ─── Culori suplimentare (adaugate v1.1) ─────────────────────────────────────
CARD_BG_BLUE   = "#EDF4FF"   # fundal card albastru pal
CARD_BG_GREEN  = "#F0FAF0"   # fundal card verde pal
CARD_BG_RED    = "#FFF0F0"   # fundal card rosu pal
CARD_BG_YELLOW = "#FFFBF0"   # fundal card galben pal
SIDEBAR_ACTIVE = "#2E4A72"   # fundal buton activ sidebar