#!/usr/bin/env python3
"""galeri_v11_kapi.py (B3) yerel testi: sentetik kartlar (JPEG 95), ag / Etsy / Drive yok.
Senaryolar: temiz set + onayli esik PASS; etiket kalmis FAIL; W07 / W10 sahne farki (onayli CANCER_LIBRA, K2) poster ve cift satiri
disinda FAIL; BASKA CIFT (B5 29 Eki): cift satiri + poster baska cift W01 / W07-W10 FAIL (OCR + poster kimligi), yalniz poster baska
cift FAIL (kimlik), yalniz cift satiri baska FAIL (OCR); poster 6 px kayik FAIL (pay +-3); AQUARIUS Q bandi; onayli sha farkli DUR;
renk kimligi (DB kartinda WP poster) FAIL; onayli referans yok FAIL;
PW / CI seritli (10 px rampa) FAIL, temiz PASS; esik yok / onay bos ESIK_YOK;
dosya yok, boyut, PNG FAIL; --olc oneri (onayli en buyuk ile canli en kucuk arasi)."""
import csv
import hashlib
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
DIGER = "AQUARIUS_SAGITTARIUS"                       # poster kimligi icin ikinci ciftin v10 kartlari
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
         isim="EMILY  JAMES", kay=0):
    im = Image.new("RGB", K.BOYUT, (214, 204, 192)); d = ImageDraw.Draw(im)
    for y in range(0, K.BOYUT[1], 4):                                    # duvar: yumusak dikey gecis (gercek oda sahnesi gibi)
        v = int(8 * y / K.BOYUT[1])
        d.line([(0, y), (K.BOYUT[0], y)], fill=(214 - v, 204 - v, 192 - v), width=4)
    x0, y0, x1, y1 = K.POSTER
    d.rectangle((x0 - 30, y0 - 30, x1 + 30, y1 + 30), fill=(14, 14, 14))
    for i in range(serit):                                                # cerceve ic kenari rampa (bilinen serit)
        v = int(20 + (230 - 20) * (i + 1) / (serit + 1))
        d.rectangle((x0 + i, y0 + i, x1 - 1 - i, y1 - 1 - i), outline=(v, v, v))
    d.rectangle((x0 + serit + kay, y0 + serit, x1 - 1 - serit + kay, y1 - 1 - serit), fill=poster)
    d.text((1300 + kay, 1200), isim, fill=(150, 110, 40), font=font(70))
    d.ellipse((1250 + kay, 800, 1750 + kay, 1100), outline=(150, 110, 40), width=14)    # poster deseni (kimlik NCC icin)
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
    o = dict(cs="AQUARIUS & SAGITTARIUS", isim="OLIVIA      NOAH")
    kart(vg / f"{DIGER}_G6.jpg", poster=(20, 20, 22), ust="Deep Black", **o); kart(vg / f"{DIGER}_G7.jpg", **o)
    kart(vg / f"{DIGER}_G8.jpg", poster=(240, 232, 214), ust="Champagne Ivory", **o)
    kart(vg / f"{DIGER}_G9.jpg", poster=(236, 222, 196), ust="Warm Parchment", **o)
    kart(vk / f"KAPAK_{DIGER}.jpg", poster=(18, 26, 60), ust="Personalized Zodiac Couple Gift", **o)
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
        if onayli and "onayli_sha256" not in esik:
            esik = dict(esik, onayli_sha256={ad: hashlib.sha256((t / "onayli" / f"{CIFT}_{ad}.jpg").read_bytes()).hexdigest() for ad in K.ADLAR})
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
    kontrol(f"DB / WP sahne + renk olculdu ({r['W08_DB']['sahne_fark']})", "sahne onayli" in r["W08_DB"]["sahne_fark"] and "renk DB 0" in r["W08_DB"]["sahne_fark"]
            and "renk WP" in r["W10_WP"]["sahne_fark"])
    kontrol(f"kimlik olculdu, 2 cift ({r['W07_MB']['kimlik'][-60:]})", all("kimlik kendi" in r[x]["kimlik"] and "(2 cift)" in r[x]["kimlik"] for x in K.ADLAR))
    e = t / "esik_sha.json"; e.write_text(json.dumps(dict(ONAY, onayli_sha256={ad: "0" * 64 for ad in K.ADLAR})))
    rc5 = K.main(["--dosya-dir", str(dd), "--v10-galeri", str(vg), "--v10-kapak", str(vk), "--ciftler", str(CIFTLER), "--sadece", CIFT,
                  "--esik", str(e), "--out", str(t / "out_sha"), "--onayli", str(t / "onayli")])
    kontrol("onayli referans sha256 esik dosyasindan farkli: kapi kosmaz (cikis 2)", rc5 == 2 and not (t / "out_sha/KAPI.csv").exists())
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
    baska = dict(cs="AQUARIUS & SAGITTARIUS", isim="OLIVIA      NOAH")
    t = t0 / "c2"; dd, vg, vk = kur(t, **{x: baska for x in K.ADLAR})
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("baska ciftin kartlari bu ciftin adiyla: 5/5 FAIL (cift satiri OCR + poster kimligi)",
            all(r[x]["durum"] == "FAIL" and "cift satiri OCR" in r[x]["neden"] and "poster kimligi" in r[x]["neden"] for x in K.ADLAR))
    t = t0 / "c4"; dd, vg, vk = kur(t, W07_MB=dict(isim="OLIVIA      NOAH"), W01_KAPAK=dict(isim="OLIVIA      NOAH"))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol(f"yalniz poster baska cift (W07, W01): kimlik FAIL ({r['W07_MB']['neden'][:70]})",
            all(r[x]["durum"] == "FAIL" and "poster kimligi" in r[x]["neden"] for x in ("W07_MB", "W01_KAPAK")))
    t = t0 / "c5"; dd, vg, vk = kur(t, W08_DB=dict(cs="CANCER & LEO"), W09_PW=dict(cs=""))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol("yalniz cift satiri baska / silinmis (W08, W09): OCR FAIL",
            all(r[x]["durum"] == "FAIL" and "cift satiri OCR" in r[x]["neden"] for x in ("W08_DB", "W09_PW")))
    t = t0 / "c6"; dd, vg, vk = kur(t, W07_MB=dict(kay=6))
    rc, r = kos(t, dd, vg, vk, ONAY)
    kontrol(f"W07 poster 6 px kayik: sahne FAIL (pay +-{K.PAY})", r["W07_MB"]["durum"] == "FAIL" and "sahne farki" in r["W07_MB"]["neden"])
    from PIL import Image as _I
    a = _I.new("RGB", K.BOYUT, (200, 200, 200)); b = a.copy(); _I.Image.paste(b, (0, 0, 0), (1200, 438, 1300, 446))
    kontrol("AQUARIUS Q kuyrugu bandi (y 438-446) dislanir, CANCER_LIBRA'da sayilir",
            K.fark(a, b, [K.cift_bant("AQUARIUS_LEO")])[1] == 0 and K.fark(a, b, [K.cift_bant("CANCER_LIBRA")])[1] == 200)
    c = a.copy(); _I.Image.paste(c, (0, 0, 0), (300, 380, 400, 400))
    kontrol("cift satiri bandi disinda (x 300) fark sayilir", K.fark(a, c, [K.cift_bant("CANCER_LIBRA")])[1] == 200)
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
