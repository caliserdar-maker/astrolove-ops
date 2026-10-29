#!/usr/bin/env python3
"""galeri_v11_kapi.py (B3) yerel testi: sentetik kartlar (JPEG 95), ag / Etsy / Drive yok.
Senaryolar: temiz set + onayli esik PASS; etiket kalmis FAIL; W07 / W10 sahne farki (onayli CANCER_LIBRA, K2) poster ve cift satiri
disinda FAIL, icinde (baska cift) PASS; renk kimligi (DB kartinda WP poster) FAIL; onayli referans yok FAIL;
PW / CI seritli (10 px rampa) FAIL, temiz PASS; esik yok / onay bos ESIK_YOK;
dosya yok, boyut, PNG FAIL; --olc oneri (onayli en buyuk ile canli en kucuk arasi)."""
import csv
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_v11_kapi as K  # noqa: E402

SONUC = []
CIFT = "CANCER_LIBRA"
CIFTLER = HERE.parents[1] / "data/pod/pod78_ids.csv"


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def font(n):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def kart(yol, poster=(252, 252, 252), etiket=False, serit=0, ust="Pure White", ek=None, fmt="JPEG", boyut=K.BOYUT, cs="CANCER & LIBRA",
         isim="EMILY  JAMES"):
    im = Image.new("RGB", K.BOYUT, (214, 204, 192)); d = ImageDraw.Draw(im)
    for y in range(0, K.BOYUT[1], 4):                                    # duvar: yumusak dikey gecis (gercek oda sahnesi gibi)
        v = int(8 * y / K.BOYUT[1])
        d.line([(0, y), (K.BOYUT[0], y)], fill=(214 - v, 204 - v, 192 - v), width=4)
    x0, y0, x1, y1 = K.POSTER
    d.rectangle((x0 - 30, y0 - 30, x1 + 30, y1 + 30), fill=(14, 14, 14))
    for i in range(serit):                                                # cerceve ic kenari rampa (bilinen serit)
        v = int(20 + (230 - 20) * (i + 1) / (serit + 1))
        d.rectangle((x0 + i, y0 + i, x1 - 1 - i, y1 - 1 - i), outline=(v, v, v))
    d.rectangle((x0 + serit, y0 + serit, x1 - 1 - serit, y1 - 1 - serit), fill=poster)
    d.text((1300, 1200), isim, fill=(150, 110, 40), font=font(70))
    d.text((1100, 165), ust, fill=(10, 22, 56), font=font(90))           # ust satir
    d.text((1100, 356), cs, fill=(138, 98, 30), font=font(60))           # cift satiri (bant y 341-432)
    if etiket:
        d.text((2165, 1990), "Frame not", fill=(60, 60, 60), font=font(48)); d.text((2165, 2045), "included", fill=(60, 60, 60), font=font(48))
    if ek:
        d.rectangle(ek, fill=(255, 0, 0))
    if boyut != K.BOYUT:
        im = im.resize(boyut)
    im.save(yol, fmt, **({"quality": 95} if fmt == "JPEG" else {}))


def kur(t, **deg):
    """t: kok. -> (dosya_dir, v10_galeri, v10_kapak); t/onayli = temiz CANCER_LIBRA seti (K2 referansi)"""
    dd, vg, vk = t / "v11", t / "v10g", t / "v10k"
    for d in (dd, vg, vk, t / "onayli"):
        d.mkdir(parents=True, exist_ok=True)
    kart(vg / f"{CIFT}_G6.jpg", poster=(20, 20, 22), etiket=True, ust="Deep Black")
    kart(vg / f"{CIFT}_G9.jpg", poster=(236, 222, 196), etiket=True, ust="Warm Parchment")
    kart(vg / f"{CIFT}_G7.jpg", etiket=True, serit=10)
    kart(vg / f"{CIFT}_G8.jpg", poster=(240, 232, 214), etiket=True, serit=12, ust="Champagne Ivory")
    kart(vk / f"KAPAK_{CIFT}.jpg", poster=(18, 26, 60), ust="Personalized Zodiac Couple Gift")
    ayar = dict(W01_KAPAK=dict(poster=(240, 232, 214), ust="Personalized Zodiac Couple Gift"),
                W07_MB=dict(poster=(18, 26, 60), ust="Midnight Blue"), W08_DB=dict(poster=(20, 20, 22), ust="Deep Black"),
                W09_PW=dict(), W10_WP=dict(poster=(236, 222, 196), ust="Warm Parchment"))
    for ad, k in ayar.items():
        kart(t / "onayli" / f"{CIFT}_{ad}.jpg", **k)
        k = dict(k, **deg.get(ad, {}))
        if k.pop("yok", False):
            continue
        kart(dd / f"{CIFT}_{ad}.jpg", **k)
    return dd, vg, vk


def kos(t, dd, vg, vk, esik=None, onayli=True):
    e = ""
    if esik is not None:
        e = str(t / "esik.json"); Path(e).write_text(json.dumps(esik))
    rc = K.main(["--dosya-dir", str(dd), "--v10-galeri", str(vg), "--v10-kapak", str(vk), "--ciftler", str(CIFTLER),
                 "--sadece", CIFT, "--esik", e, "--out", str(t / "out")] + (["--onayli", str(t / "onayli")] if onayli else []))
    return rc, {r["ad"]: r for r in csv.DictReader(open(t / "out/KAPI.csv"))}


ONAY = dict(etiket_hp_max=3000, bant_max_px=3, onay="Serdar test")   # sentetik: temiz kutu ~1050 (cerceve kenari 6 px), etiketli ~9500


def main():
    t0 = Path(tempfile.mkdtemp(prefix="gv11k_"))

    t = t0 / "a"; dd, vg, vk = kur(t)
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("temiz set + onayli esik: 5/5 PASS, cikis 0", rc == 0 and all(x["durum"] == "PASS" for x in r.values()))
    b = {k: int(v) for k, v in (x.split(":") for x in r["W09_PW"]["bant"].split())}
    kontrol(f"temiz PW bant <= 1 ({r['W09_PW']['bant']})", max(b.values()) <= 1)
    kontrol(f"DB / WP sahne + renk olculdu ({r['W08_DB']['v10_fark']})", "sahne onayli" in r["W08_DB"]["v10_fark"] and "renk DB 0" in r["W08_DB"]["v10_fark"]
            and "renk WP" in r["W10_WP"]["v10_fark"])
    rc4, r4 = kos(t, dd, vg, vk, ONAY, onayli=False)
    kontrol("onayli referans yok: W07 / W08 / W10 FAIL", all("onayli referans yok" in r4[x]["neden"] for x in ("W07_MB", "W08_DB", "W10_WP")))
    rc2, r2 = kos(t, dd, vg, vk, None)
    kontrol("esik yok: etiket / bant ESIK_YOK, cikis 1", rc2 == 1 and all(x["durum"] == "ESIK_YOK" for x in r2.values()))
    rc3, r3 = kos(t, dd, vg, vk, dict(ONAY, onay=""))
    kontrol("esik onay bos: ESIK_YOK", all(x["durum"] == "ESIK_YOK" for x in r3.values()))

    t = t0 / "b"; dd, vg, vk = kur(t, W08_DB=dict(etiket=True), W09_PW=dict(serit=10), W01_KAPAK=dict(serit=12))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol(f"etiket kalmis W08 FAIL ({r['W08_DB']['etiket_hp']} piksel)", r["W08_DB"]["durum"] == "FAIL" and "etiket kutusu" in r["W08_DB"]["neden"])
    kontrol(f"seritli PW FAIL ({r['W09_PW']['bant']})", r["W09_PW"]["durum"] == "FAIL" and "bant" in r["W09_PW"]["neden"])
    kontrol(f"seritli CI kapak FAIL ({r['W01_KAPAK']['bant']})", r["W01_KAPAK"]["durum"] == "FAIL")

    t = t0 / "c"; dd, vg, vk = kur(t, W10_WP=dict(ek=(300, 1500, 420, 1600)), W07_MB=dict(ek=(300, 1500, 420, 1600)))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("WP sahne farki (poster / cift satiri disi) FAIL", r["W10_WP"]["durum"] == "FAIL" and "sahne farki" in r["W10_WP"]["neden"])
    kontrol("MB sahne farki FAIL", r["W07_MB"]["durum"] == "FAIL" and "sahne farki" in r["W07_MB"]["neden"])
    baska = dict(cs="SAGITTARIUS & SAGITTARIUS", isim="OLIVIA  NOAH")
    t = t0 / "c2"; dd, vg, vk = kur(t, W07_MB=baska, W08_DB=baska, W10_WP=baska)
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("baska cift (cift satiri + poster ici farkli) W07 / W08 / W10 PASS", all(r[x]["durum"] == "PASS" for x in ("W07_MB", "W08_DB", "W10_WP")))
    t = t0 / "c3"; dd, vg, vk = kur(t, W08_DB=dict(poster=(236, 222, 196)))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol(f"DB kartinda WP poster: renk kimligi FAIL ({r['W08_DB']['neden'][:80]})", r["W08_DB"]["durum"] == "FAIL" and "renk kimligi" in r["W08_DB"]["neden"])

    t = t0 / "d"; dd, vg, vk = kur(t, W08_DB=dict(yok=True), W10_WP=dict(boyut=(3000, 2000)), W09_PW=dict(fmt="PNG"))
    (dd / f"{CIFT}_W09_PW.jpg").rename(dd / f"{CIFT}_W09_PW.jpg")
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("dosya yok / boyut / PNG FAIL", r["W08_DB"]["neden"] == "dosya yok" and "3000x2000" in r["W10_WP"]["neden"]
            and "PNG" in r["W09_PW"]["neden"] and rc == 1)

    t = t0 / "e"; dd, vg, vk = kur(t)
    on = t / "onayli"                                                     # kur() temiz CANCER_LIBRA seti
    rc = K.main(["--olc", "--onayli", str(on), "--v10-galeri", str(vg), "--out", str(t / "olc")])
    o = json.loads((t / "olc/ESIK_ONERI.json").read_text())["oneri"]
    kontrol(f"--olc oneri ({o['etiket_hp_max']}, {o['bant_max_px']}) onayli < oneri < canli",
            rc == 0 and o["onayli_etiket_max"] < o["etiket_hp_max"] < o["canli_etiket_min"]
            and o["onayli_bant_max"] <= o["bant_max_px"] < o["canli_bant_min"])
    bad = [a for a, ok in SONUC if not ok]
    print(f"\nTEST {len(SONUC) - len(bad)}/{len(SONUC)} PASS" + (f" | FAIL: {bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
