#!/usr/bin/env python3
"""siparis_v2_girdi testi (19 Kas). Ag kapali, sahte isimler. Bilinen PASS + bilinen FAIL (cift, olcu, renk, Format, bos isim, uzun / cok
satirli mesaj, iki kalem). Cikti denetimi: maske satirlari disinda hicbir satirda isim / mesaj parcasi yok; maske satirlari ilk sirada."""
import base64, json, socket, subprocess, sys, tempfile
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok
BETIK = Path(__file__).resolve().parent / "siparis_v2_girdi.py"
HATA = []


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


def kos(td, cift="CANCER_LEO", olcu="11x14", renk="MIDNIGHT_BLUE", fmt="Print", i1="Milo", i2="Harper", mesaj="Always-and-Forever Yours",
        size="11×14″ (28×36cm)", color="Midnight Blue", f_etsy="Print", iki=False):
    var = [dict(ad="Name under Cancer", deger=i1), dict(ad="Name under Leo", deger=i2), dict(ad="Your message", deger=mesaj),
           dict(ad="Color", deger=color), dict(ad="Size", deger=size), dict(ad="Format", deger=f_etsy)]
    kal = [{"varyasyon": var}] * (2 if iki else 1)
    (td / "K.json").write_text(json.dumps({"receipt_id": 900000001, "kalemler": kal}), encoding="utf-8"); ist = td / "istek.json"
    if ist.exists():
        ist.unlink()
    kod = ("import socket, runpy, sys\ndef _ag(*a, **k):\n    raise AssertionError('gercek ag acilmaya calisildi')\n"
           "socket.socket.connect = _ag; socket.create_connection = _ag\n"                     # inceleme F ORTA 8: alt surecte de ag kapali
           f"sys.argv = {[str(BETIK), str(td / 'K.json'), cift, olcu, renk, fmt, str(ist)]!r}; sys.path.insert(0, {str(BETIK.parent)!r})\n"
           f"runpy.run_path({str(BETIK)!r}, run_name='__main__')\n")
    r = subprocess.run([sys.executable, "-I", "-c", kod], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr, (json.loads(ist.read_text()) if ist.exists() else None)


def sizinti(out, parcalar):
    sat = out.splitlines(); m = [i for i, s in enumerate(sat) if s.startswith("::add-mask::")]
    diger = [s for s in sat if not s.startswith("::add-mask::")]
    return (m == list(range(len(m)))) and not any(p in s for s in diger for p in parcalar)


with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    rc, so, se, ist = kos(td)
    kontrol("bilinen PASS: cikis 0, istek dogru (isim1 = Cancer altindaki, isim2 = Leo)", rc == 0 and ist and ist["isim1"] == "Milo" and ist["isim2"] == "Harper"
            and ist["cift"] == "CANCER_LEO" and base64.b64decode(ist["mesaj_b64"]).decode() == "Always-and-Forever Yours" and ist["olcu"] == "11x14", f"{rc} {se[-300:]}")
    kontrol("maske once, deger sizmiyor", sizinti(so, ["Milo", "Harper", "Always", "Forever", "Yours", "MILO", "milo"]), so[-300:])
    kontrol("maskeler kelime ve buyuk harf bicimini kapsiyor", all(f"::add-mask::{x}" in so for x in ("Milo", "MILO", "HARPER", "Forever", "FOREVER", "Always-and-Forever Yours")))
    kontrol("receipt_id maskeli ve acik basilmaz", "::add-mask::900000001" in so
            and not any("900000001" in s for s in so.splitlines() if not s.startswith("::add-mask::")), so[-200:])
    rc, so, se, ist = kos(td, cift="LEO_CANCER")
    kontrol("bilinen FAIL: cift alfabetik degil", rc == 1 and ist is None)
    for ad, kw in (("cift farki (VIRGO)", dict(cift="CANCER_VIRGO")), ("olcu farki", dict(size="16x20 in")), ("renk farki", dict(color="Deep Black")),
                   ("Format Digital File", dict(f_etsy="Digital File")), ("bos isim", dict(i2=" ")), ("mesaj 36 karakter", dict(mesaj="x" * 36)),
                   ("cok satirli mesaj", dict(mesaj="Milo\nHarper")), ("iki kalem", dict(iki=True))):
        rc, so, se, ist = kos(td, **kw)
        kontrol(f"bilinen FAIL: {ad} -> cikis 1, istek yok, sizinti yok", rc == 1 and ist is None and sizinti(so, ["Milo", "Harper", "Forever"]), f"{rc} {so[-200:]}")
    rc, so, se, ist = kos(td, mesaj="Milo & Harper 50% yours")
    kontrol("yuzde isareti kacisli maske (%25)", rc == 0 and "::add-mask::Milo & Harper 50%25 yours" in so)
print("siparis_v2_girdi testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
