"""Icerik takvimi satirlari: sema, onay ozeti, secim (plan 4.2, 4.4, 4.7). Saf fonksiyonlar (ag yok).

Takvim: Drive Google Sheet SOSYAL_TAKVIM (depoya yazilmaz). Ilk satir baslik; sutun adlari asagidaki SUTUNLAR.
Durum makinesi (tekrar paylasim korumasi, publish.py modeli):
  bos       -> zamani geldiyse ve onayliysa yayinla (once BEKLIYOR yazilir)
  BEKLIYOR  -> ATLA (onceki kosu yarim kaldi; elle bakilir, otomatik yeniden deneme YOK; 1 saatten eskiyse bir kez uyari)
  TAMAM / HATA / KACTI -> atla
Onay: ONAY = SERDAR_<YYYYMMDD>; ONAY_OZET = onay anindaki satir + medya md5 ozeti; farkliysa yayin YOK."""
import hashlib
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")
SUTUNLAR = ["satir_no", "tarih_saat_TR", "platform", "tur", "medya", "metin", "link", "pano", "yz_beyani",
            "gorunurluk", "ONAY", "ONAY_OZET", "DURUM", "sonuc_no", "not"]
OZET_ALANLARI = ["satir_no", "tarih_saat_TR", "platform", "tur", "medya", "metin", "link", "pano", "yz_beyani",
                 "gorunurluk"]
TURLER = {
    "instagram": {"reel", "karusel", "hikaye", "gorsel"},
    "facebook": {"reel", "gorsel"},
    "threads": {"metin", "gorsel", "video", "karusel"},
    "youtube": {"short"},
}
PENCERE_SAAT = 6
ONAY_RX = re.compile(r"^SERDAR_20\d{6}$")
SON_DURUMLAR = ("TAMAM", "HATA", "KACTI")


def medya_listesi(satir):
    return [m.strip() for m in (satir.get("medya") or "").split(";") if m.strip()]


def ozet(satir, md5ler):
    """Onay anindaki icerigin ozeti (16 hex). md5ler: medya_listesi sirasiyla Drive md5."""
    d = {k: (satir.get(k) or "").strip() for k in OZET_ALANLARI}
    d["_md5"] = list(md5ler)
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def zaman(satir):
    t = (satir.get("tarih_saat_TR") or "").strip()
    try:
        return datetime.strptime(t, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except ValueError:
        return None


def dogrula(satir):
    """Bicim hatasi listesi (bos = gecerli)."""
    h = []
    p, tur = (satir.get("platform") or "").strip(), (satir.get("tur") or "").strip()
    if p not in TURLER:
        h.append(f"platform gecersiz: {p!r}")
    elif tur not in TURLER[p]:
        h.append(f"{p} icin tur gecersiz: {tur!r}")
    if zaman(satir) is None:
        h.append("tarih_saat_TR bicimi YYYY-MM-DD HH:MM degil")
    if not (satir.get("satir_no") or "").strip().isdigit():
        h.append("satir_no sayi degil")
    m = medya_listesi(satir)
    if tur == "metin" and m:
        h.append("metin turunde medya olmaz")
    if tur != "metin" and not m:
        h.append("medya yok")
    if tur == "karusel" and not 2 <= len(m) <= 10:
        h.append("karusel 2-10 medya")
    if tur not in ("karusel",) and len(m) > 1:
        h.append("bu turde tek medya")
    if (satir.get("yz_beyani") or "").strip() not in ("evet", "hayir"):
        h.append("yz_beyani evet/hayir degil")
    if p == "youtube" and (satir.get("gorunurluk") or "").strip() not in ("public", "private", "unlisted"):
        h.append("youtube gorunurluk public/private/unlisted degil")
    if p == "threads" and len(satir.get("metin") or "") > 500:
        h.append("threads metni 500 karakteri asiyor")
    if p == "instagram" and len(satir.get("metin") or "") > 2200:
        h.append("instagram metni 2200 karakteri asiyor")
    return h


def karar(satir, simdi, acik, md5ler=None):
    """Bir satir icin karar: (kod, aciklama). kod: YAYINLA, BEKLE, ATLA, KACTI, ONAYSIZ, OZET_FARKLI, GECERSIZ, KAPALI.
    md5ler None ise ozet kontrolu yapilmaz (cagiran medya md5'lerini okuyup tekrar sormali)."""
    durum = (satir.get("DURUM") or "").strip()
    if durum:
        return ("ATLA", f"durum {durum.split()[0]}")
    t = zaman(satir)
    if t is not None and t > simdi:
        return ("BEKLE", "zamani gelmedi")
    h = dogrula(satir)
    if h:
        return ("GECERSIZ", "; ".join(h))
    if satir["platform"].strip() not in acik:
        return ("KAPALI", f"{satir['platform']} anahtari kapali")
    if not ONAY_RX.match((satir.get("ONAY") or "").strip()):
        return ("ONAYSIZ", "ONAY yok ya da bicim SERDAR_YYYYMMDD degil")
    if simdi - t > timedelta(hours=PENCERE_SAAT):
        return ("KACTI", f"{PENCERE_SAAT} saatten gec")
    if md5ler is not None and ozet(satir, md5ler) != (satir.get("ONAY_OZET") or "").strip():
        return ("OZET_FARKLI", "onaydan sonra satir ya da medya degisti")
    return ("YAYINLA", "")
