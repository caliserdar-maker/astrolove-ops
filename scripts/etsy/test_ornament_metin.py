#!/usr/bin/env python3
"""ornament_metin.py ureteci ile depodaki data/pod/ORNAMENT78_METIN.csv ayni mi (K1, Serdar 15 Kas). Ag yok, yazim yok.
Yalniz satir() ve kapi() cagrilir; main() ve betik KOSULMAZ (cikti yolu sabit, ornament_metin.py main; depodaki CSV'yi ezer).
KURAL: S13 araci (ornament_metin_canli.py) CSV'nin aciklama sutununu canlidan degistirirse uretec (ornament_metin.py) AYNI commit'te
guncellenir; bu test ikisi ayrisirsa FAIL verir. NOT: S13 is akisi dal commit'inde yalniz CSV'nin degismesine izin verir
(.github/workflows/ornament-metin-canli.yml:6, :126); bu yuzden S13 dalinda bu test FAIL verir ve uretec main'e almadan once esitlenir.
Kullanim: python3 scripts/etsy/test_ornament_metin.py -> 'SONUC n/t PASS' (cikis 1 = FAIL)."""
import csv
import hashlib
import io
import sys
from pathlib import Path
import socket
import ssl  # noqa: F401  (ag kapatmadan once yuklenir: ssl/requests socket sinifini alt sinif yapar)
import urllib.request


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


# TEST AGI (CLAUDE.md:124; plan URUN_AYAR_MAIN_PLAN 10-G4): gercek dis ag bastan kapali; emsal scripts/sosyal/test_metricool_yedek.py:19-25
socket.socket.connect = _ag_yok
socket.socket.connect_ex = _ag_yok
socket.socket.sendto = _ag_yok
socket.create_connection = _ag_yok
socket.getaddrinfo = _ag_yok      # DNS de kapali (inceleme 1. tur)
urllib.request.urlopen = _ag_yok
# TEST AGI denetim kancasi: ad yamalari _socket ile ya da yamalanmamis adla (getnameinfo vb.) delinebilir; kanca surec icindeki Python soket yollarini yakalar (alt surec: sitecustomize; -I / Popen / Python disi araclar acik).
import sys as _ag_sys
def _ag_kanca(olay, arg):
    if olay in ("socket.connect", "socket.sendto", "socket.sendmsg"):
        if getattr(arg[0], "family", None) == getattr(socket, "AF_UNIX", -1):
            return
        raise AssertionError("gercek ag acilmaya calisildi: " + olay)
    if olay in ("socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr", "socket.getnameinfo"):
        raise AssertionError("gercek ag acilmaya calisildi: " + olay)
_ag_sys.addaudithook(_ag_kanca)

BURA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURA))
import ornament_metin as OM  # noqa: E402

CSV_YOL = BURA.parents[1] / "data" / "pod" / "ORNAMENT78_METIN.csv"
SONUC = []


def k(ad, kosul):
    SONUC.append(bool(kosul))
    print(("PASS " if kosul else "FAIL ") + ad, flush=True)


def ag_dene(f):
    try:
        f(); return False
    except AssertionError as e:
        return "gercek ag" in str(e)
    except Exception:
        return False


def main():
    b = CSV_YOL.read_bytes(); sha_once = hashlib.sha256(b).hexdigest()
    R = list(csv.DictReader(io.StringIO(b.decode("utf-8"), newline="")))
    rows = [OM.satir(c) for c in OM.CIFTLER]
    k("PASS: 78 cift, depo CSV'si 78 satir", len(rows) == 78 and len(R) == 78)
    k("PASS: kod sirasi ayni", [r["kod"] for r in rows] == [r["kod"] for r in R])
    fark = [(a["kod"], c) for a, r in zip(rows, R) for c in OM.ALAN if a[c] != r[c]]
    k(f"PASS: 20 sutun x 78 satir birebir (fark {len(fark)}: {fark[:3]})", not fark and len(OM.ALAN) == 20)
    s = io.StringIO(newline=""); w = csv.DictWriter(s, fieldnames=OM.ALAN); w.writeheader(); w.writerows(rows)
    k("PASS: uretec ciktisi (DictWriter) depo CSV'siyle bayt bayt ayni", s.getvalue().encode("utf-8") == b)
    k("PASS: aciklamalarda 'free shipping' 0", sum("free shipping" in r["aciklama"].lower() for r in rows) == 0)
    k("PASS: kapi FAIL 0", sum(bool(OM.kapi(r)) for r in rows) == 0)
    import _socket as _ham
    _t = _ham.socket(_ham.AF_INET, _ham.SOCK_STREAM); _t.settimeout(2)   # kanca kalkarsa takilmasin
    _u = _ham.socket(_ham.AF_INET, _ham.SOCK_DGRAM)
    try:
        k("TEST AGI (kanca): _socket connect, UDP sendto, getaddrinfo, gethostbyname, getnameinfo ve create_connection AssertionError verir",
          ag_dene(lambda: _t.connect(("192.0.2.1", 9))) and ag_dene(lambda: _u.sendto(b"x", ("192.0.2.1", 9)))
          and ag_dene(lambda: _ham.getaddrinfo("example.invalid", 80)) and ag_dene(lambda: _ham.gethostbyname("example.invalid"))
          and ag_dene(lambda: _ham.getnameinfo(("192.0.2.1", 9), 0)) and ag_dene(lambda: socket.create_connection(("192.0.2.1", 9), 2)))
    finally:
        _t.close(); _u.close()
    k("PASS: depo CSV'si test sirasinda degismedi", hashlib.sha256(CSV_YOL.read_bytes()).hexdigest() == sha_once)
    n, t = sum(SONUC), len(SONUC)
    print(f"SONUC {n}/{t} PASS")
    return 0 if n == t else 1


if __name__ == "__main__":
    sys.exit(main())
