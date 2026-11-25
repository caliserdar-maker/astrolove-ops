#!/usr/bin/env python3
"""Video kaynagi kapisi (Serdar 25 Kas 18:10: tum kanallarda video = Pinterest video seti, video B; eski mockup videosu yok).
Yapilandirma: config/sosyal_video_kaynak.json {"klasor": Drive klasoru, "ad_kalibi": "{a}-and-{b}-pin-video.mp4",
"onay": "SERDAR_YYYYMMDD"}. klasor ya da onay bossa HICBIR .mp4 medya gecerli degildir (onayla da yayin da GECERSIZ).
Ad kalibi pin78-video-ornek.yml:64,144 ile ayni (kucuk harf, alfabetik cift; ayni burc cifti dahil 78).
Kullanim: video_kaynak.py yol CANCER_LIBRA  -> takvime yazilacak Drive yolu."""
import json
import os
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
AYAR = Path(os.environ.get("SOSYAL_VIDEO_KAYNAK", KOK / "config/sosyal_video_kaynak.json"))
BURCLAR = ["aquarius", "aries", "cancer", "capricorn", "gemini", "leo", "libra", "pisces", "sagittarius", "scorpio",
           "taurus", "virgo"]
ONAY_RX = re.compile(r"^SERDAR_20\d{6}$")


def ayar():
    try:
        d = json.loads(AYAR.read_text())
    except (OSError, ValueError):
        return {"klasor": "", "ad_kalibi": "", "onay": ""}
    return d


def _cift(a, b):
    a, b = a.lower(), b.lower()
    if a not in BURCLAR or b not in BURCLAR:
        raise ValueError(f"gecersiz burc: {a}/{b}")
    if a > b:
        raise ValueError(f"cift alfabetik degil: {a}-{b} (dogrusu {b}-{a})")
    return a, b


def yol(cift_anahtari):
    d = ayar()
    a, b = cift_anahtari.split("_", 1)
    a, b = _cift(a, b)
    if not (d.get("klasor") and d.get("ad_kalibi")):
        raise ValueError("video kaynagi tanimli degil (config/sosyal_video_kaynak.json klasor bos)")
    return f"{d['klasor'].rstrip('/')}/{d['ad_kalibi'].format(a=a, b=b)}"


def medya_hatasi(medya_yolu):
    """MP4 medya icin hata metni (bos = gecerli). MP4 degilse kontrol yok."""
    if not medya_yolu.lower().endswith(".mp4"):
        return ""
    d = ayar()
    klasor, kalip, onay = (d.get("klasor") or "").rstrip("/"), d.get("ad_kalibi") or "", (d.get("onay") or "").strip()
    if not klasor or not kalip or not ONAY_RX.match(onay):
        return "video kaynagi onayli degil (Pinterest video seti klasoru + Serdar onayi config/sosyal_video_kaynak.json'da yok)"
    klasor_y, ad = medya_yolu.rsplit("/", 1) if "/" in medya_yolu else ("", medya_yolu)
    if klasor_y != klasor:
        return "video onayli Pinterest video seti klasorunde degil"
    rx = "^" + re.escape(kalip).replace(r"\{a\}", "(?P<a>[a-z]+)").replace(r"\{b\}", "(?P<b>[a-z]+)") + "$"
    m = re.match(rx, ad)
    if not m:
        return "video adi Pinterest video kalibina uymuyor"
    try:
        _cift(m.group("a"), m.group("b"))
    except ValueError as e:
        return str(e)
    return ""


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "yol":
        try:
            print(yol(sys.argv[2]))
        except ValueError as e:
            print(f"DUR: {e}")
            sys.exit(1)
    else:
        print("kullanim: video_kaynak.py yol CANCER_LIBRA")
        sys.exit(2)
