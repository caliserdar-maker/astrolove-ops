"""Medya (plan 4.3; Merkez 22 Kas karari a): kaynak Drive'da. Instagram ve Threads herkese acik adres ister:
onay aninda dosya astrolove-media deposunda yayin/<YYYYMM>/<satir_no>_<i>.<uzanti> yoluna konur (yalniz yayinlanacak
gorsel/video; musteri verisi asla). Facebook ve YouTube yerel dosyayi yukler.
Yayin aninda: Drive md5 = onay ozetindeki md5 (secim.ozet) ve herkese acik adresten inen dosyanin md5'i ayni olmali."""
import hashlib
import os
import re
from pathlib import Path

from ortak import Hata, drive_indir, md5_dosya

MEDIA_BASE = os.environ.get("MEDIA_BASE", "https://caliserdar-maker.github.io/astrolove-media").rstrip("/")
UZANTI = {".jpg": "gorsel", ".jpeg": "gorsel", ".mp4": "video"}
GENEL_PLATFORM = {"instagram", "threads"}


def tip(yol):
    u = Path(yol).suffix.lower()
    if u not in UZANTI:
        raise Hata(f"desteklenmeyen medya uzantisi: {u or '(yok)'} (yalniz JPEG ve MP4)")
    return UZANTI[u]


def genel_yol(satir, i, kaynak):
    ay = satir["tarih_saat_TR"][:7].replace("-", "")
    no = satir["satir_no"].strip()
    if not (re.fullmatch(r"\d{6}", ay) and no.isdigit()):
        raise Hata("genel yol kurulamadi")
    return f"yayin/{ay}/{no}_{i}{Path(kaynak).suffix.lower()}"


GONDERI_BOYUT = {"instagram": (1080, 1350), "facebook": (1080, 1350), "threads": (1080, 1350)}   # Serdar 25 Kas: 4:5
TUR_BOYUT = {("instagram", "hikaye"): (1080, 1920)}   # hikaye 9:16


def _yon(seg):
    """APP1 Exif segmentinden Orientation (0x0112); yoksa 1."""
    if seg[:6] != b"Exif\x00\x00" or len(seg) < 14:
        return 1
    t = seg[6:]
    e = "little" if t[:2] == b"II" else "big"
    ifd = int.from_bytes(t[4:8], e)
    if ifd + 2 > len(t):
        return 0
    for k in range(int.from_bytes(t[ifd:ifd + 2], e)):
        o = ifd + 2 + 12 * k
        if o + 12 > len(t):
            return 0
        if int.from_bytes(t[o:o + 2], e) == 0x0112:
            return int.from_bytes(t[o + 8:o + 10], e)
    return 1


def jpeg_boyut(yol):
    """JPEG piksel boyutu (genislik, yukseklik); SOF isaretinden okunur (kutuphane yok). Okunamazsa ya da EXIF
    yonlendirmesi 1 degilse (dondurulmus gosterim) None."""
    with open(yol, "rb") as f:
        v = f.read()
    if v[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(v):
        if v[i] != 0xFF:
            return None
        while i + 1 < len(v) and v[i + 1] == 0xFF:   # dolgu baytlari
            i += 1
        m = v[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        n = int.from_bytes(v[i + 2:i + 4], "big")
        if m == 0xE1 and _yon(v[i + 4:i + 2 + n]) != 1:
            return None
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(v[i + 7:i + 9], "big"), int.from_bytes(v[i + 5:i + 7], "big")
        i += 2 + n
    return None


def indir(satir, dizin):
    """Drive'dan yerel kopya. Donus: [{"kaynak", "yerel", "md5", "tip", "genel", "url"}]."""
    out = []
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    for i, kaynak in enumerate([m.strip() for m in satir["medya"].split(";") if m.strip()], start=1):
        t = tip(kaynak)
        hedef = dizin / f"{satir['satir_no'].strip()}_{i}{Path(kaynak).suffix.lower()}"
        drive_indir(kaynak, hedef)
        if not hedef.exists() or hedef.stat().st_size == 0:
            raise Hata(f"medya indirilemedi: {kaynak}")
        pl = (satir.get("platform") or "").strip()
        beklenen = TUR_BOYUT.get((pl, (satir.get("tur") or "").strip()), GONDERI_BOYUT.get(pl))
        if t == "gorsel" and beklenen:
            olcu = jpeg_boyut(hedef)
            if olcu != beklenen:
                raise Hata(f"{pl} gorseli {beklenen[0]}x{beklenen[1]} degil: "
                           f"{'okunamadi ya da EXIF dondurmeli' if olcu is None else f'{olcu[0]}x{olcu[1]}'} ({kaynak}); 2:3 pin gonderilmez")
        g = genel_yol(satir, i, kaynak) if satir["platform"] in GENEL_PLATFORM else None
        out.append({"kaynak": kaynak, "yerel": hedef, "md5": md5_dosya(hedef), "tip": t,
                    "genel": g, "url": f"{MEDIA_BASE}/{g}" if g else None})
    return out


def genele_koy(medya, kok):
    """Onay aninda: herkese acik kopya astrolove-media checkout'una (is akisi commit + push eder)."""
    kok = Path(kok)
    for m in medya:
        if m["genel"]:
            h = kok / m["genel"]
            h.parent.mkdir(parents=True, exist_ok=True)
            h.write_bytes(m["yerel"].read_bytes())


def genel_dogrula(http, medya):
    """Yayin aninda: herkese acik adresteki dosya Drive kopyasiyla ayni mi (md5)."""
    for m in medya:
        if not m["url"]:
            continue
        try:
            r = http.o.request("GET", m["url"], timeout=120)
        except Exception as e:
            raise Hata(f"medya adresi okunamadi: {type(e).__name__}")
        if r.status_code != 200:
            raise Hata(f"medya adresi HTTP {r.status_code}: {m['genel']}")
        if hashlib.md5(r.content).hexdigest() != m["md5"]:
            raise Hata(f"herkese acik medya Drive kopyasindan farkli: {m['genel']}")
