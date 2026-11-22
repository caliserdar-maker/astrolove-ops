"""Platform kimlikleri: Drive ASTROLOVE/TEMP/SOSYAL_<PLATFORM>_TOKEN.json (tek kaynak; plan 4.5). Okunur okunmaz maskelenir.
Dosya bicimi: {"token"|"refresh_token", hesap kimligi alani, "bitis": ISO-8601 (varsa)}."""
import json
import os

from ortak import Hata, drive_oku, drive_yaz, gizle

KOK = os.environ.get("SOSYAL_TOKEN_KOK", "ASTROLOVE/TEMP")
ALAN = {"instagram": ("token", "ig_id"), "threads": ("token", "th_id"), "facebook": ("token", "page_id"),
        "youtube": ("refresh_token", "kanal_id")}


def yol(platform):
    return f"{KOK}/SOSYAL_{platform.upper()}_TOKEN.json"


def oku(platform):
    try:
        k = json.loads(drive_oku(yol(platform)))
    except Hata:
        raise Hata(f"{platform} kimlik dosyasi okunamadi")
    except ValueError:
        raise Hata(f"{platform} kimlik dosyasi JSON degil")
    sir, hesap = ALAN[platform]
    if not (k.get(sir) and k.get(hesap)):
        raise Hata(f"{platform} kimlik dosyasinda {sir}/{hesap} eksik")
    gizle(k[sir])
    return k


def yaz(platform, k):
    sir, _ = ALAN[platform]
    gizle(k.get(sir, ""))
    drive_yaz(yol(platform), json.dumps(k, ensure_ascii=False))
