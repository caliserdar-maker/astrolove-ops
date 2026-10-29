#!/usr/bin/env python3
"""Galeri v11 B3 tam boy kapi (Merkez 29 Eki, plan v2 adim 5b): Canva ciktilari <CIFT>_W01_KAPAK / W07_MB / W08_DB / W09_PW / W10_WP.
ETSY YOK. PASS / FAIL / ESIK_YOK. Pillow 11.0.0 (is akislari surumu).
Kapilar (dosya basina):
  1) bicim: JPEG, 3000x2250.
  2) etiket ("Frame not included"): kutu x 2150-2410, y 1960-2110 (canli kartlarda yazi x 2165-2396, y 1987-2095; Merkez olcumu).
     Yontem yuksek geciren fark: L - Gauss(12) mutlak; kutuda |hp| > HP_ESIK (30) piksel sayisi (cerceve golgesi yumusak, sayilmaz).
     Olcum 29 Eki (Denetim, canli v10 CANCER_LIBRA G6 / G7, Pillow 11.0.0): etiketli kutu 6529 piksel; ayni kartin etiketsiz iki kutusu
     (x 2150-2410 y 1700-1850; x 500-760 y 1960-2110) 14 ve 109. Kutunun sol kenari cerceve dis kenarina ~6 px yakin: keskin kenar
     tabana sayi ekler (sentetik testte temiz kutu 1050); bu yuzden esik sabit degil, onayli temiz ciktidan olculur (--olc).
     Karar esigi etiket_hp_max esik dosyasindan (Serdar onayli).
     --onayli verilirse ayni ad icin onayli temiz ciktiyla kutu farki (p99.9, max) bilgi olarak yazilir.
  3) BES KART (Serdar K2, 29 Eki; W01 / W09 Merkez sorusu 29 Eki ile eklendi, dislamak icin olcum nedeni yok): sahne farki ONAYLI
     CANCER_LIBRA v11 kartina (--onayli; ayni ad), cifte ozel bolgeler haric (poster: W07 / W08 / W10 971-2035 x 667-2043, W01 / W09
     876-2125 x 576-2137; cift satiri bandi y 341-432), CLAUDE.md GALERI esigi p99.9 <= 12, max <= 45.
     (Canli v10 kartina fark kullanilmaz: Canva kopyasinda sahne 2-4 px kayik, onayli ornek p99.9 130 verdi; 29 Eki olcumu.)
     + renk kimligi (bes kart; W01 = CI, W09 = PW): poster ici medyan CIELAB (983-2023 x 679-2031), ayni ciftin canli v10 renk
     kartlarina (MB kapak, G6 DB, G7 PW, G8 CI, G9 WP) en yakin beklenen renk ve uzaklik < 5 referansin en kucuk ikili uzakliginin
     yarisi. Onayli CANCER_LIBRA olcumu config/galeri_v11_esik.json "renk" alaninda.
  4) bant (W01 CI kapak, W09 PW; acik poster): poster ile siyah cerceve arasinda farkli bant. Geometri: dort kenarda poster kenarina dik
     profil (kenar boyunca, koselerden 150 px iceride ortalama gri), nominal kenar (oge 888, 588, 1226 x 1538; KARAR dosyasi) +-40 px.
     Cerceve = profilde son KARANLIK (< 40) nokta; bant = ondan sonra komsu fark > EGIM (5 gri/px) surdukce gecen piksel sayisi
     (keskin gecis 0; rampa / serit sayilir; posterin yumusak kenar golgesi (vinyet, < 1 gri/px) sayilmaz).
     29 Eki ilk yontem (|L - ic medyan| <= 4) onayli CI kapakta vinyeti 15 / 21 px bant saymisti: duzeltildi.
     Olcum 29 Eki (canli v10 CANCER_LIBRA G7, PW, bilinen serit): sol 9, sag 12, ust 7, alt 11.
     Karar esigi bant_max_px esik dosyasindan (Serdar onayli).
Esik dosyasi (--esik, JSON; config/galeri_v11_esik.json, Serdar K1 29 Eki: 3264 / 4): {"etiket_hp_max": n, "bant_max_px": n, "onay": "Serdar <tarih>"}; yoksa / onay bos -> etiket ve bant kapisi
ESIK_YOK (PASS sayilmaz). --olc: onayli CANCER_LIBRA 5 gorselden (--onayli) olcum + oneri (ESIK_ONERI.json / .md); kullanilmaz, Serdar'a sunulur.
Cikti --out: KAPI.csv (dosya basina sha256 + olcumler + durum; galeri_v11_liste ayni sha256'yi ister), KAPI.md. Cikis 0 = hepsi PASS."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

BOYUT = (3000, 2250)
ADLAR = ("W01_KAPAK", "W07_MB", "W08_DB", "W09_PW", "W10_WP")
ETIKET_KUTU = (2150, 1960, 2410, 2110)
HP_SIGMA, HP_ESIK = 12, 30
FARK_P999, FARK_MAX = 12, 45                         # CLAUDE.md GALERI kapisi (onayli)
SAHNE_AD = ("W01_KAPAK", "W07_MB", "W08_DB", "W09_PW", "W10_WP")   # K2 (Serdar 29 Eki): referans onayli CANCER_LIBRA v11, cifte ozel haric
RENK_POSTER = (983, 679, 2023, 2031)                 # W07 / W08 / W10 poster (paspartu ici); onayli CANCER_LIBRA olcumu 29 Eki (uc kartta ayni)
CIFT_BANT = (0, 341, 3000, 432)                      # cift satiri ("CANCER & LIBRA" y 353-420, x 1090-1910) +-12 px, tam genislik
PASPARTU_POSTER = (983, 679, 2023, 2031)             # W07 / W08 / W10 (paspartulu); W01 / W09 paspartusuz poster 888-2113 x 588-2125
POSTER_HARIC = {ad: (x0 - 12, y0 - 12, x1 + 12, y1 + 12) for ad, (x0, y0, x1, y1) in (
    ("W07_MB", PASPARTU_POSTER), ("W08_DB", PASPARTU_POSTER), ("W10_WP", PASPARTU_POSTER),
    ("W01_KAPAK", (888, 588, 2113, 2125)), ("W09_PW", (888, 588, 2113, 2125)))}   # onayli CANCER_LIBRA kenar olcumu 29 Eki
RENK_AD = {"W01_KAPAK": "CI", "W07_MB": "MB", "W08_DB": "DB", "W09_PW": "PW", "W10_WP": "WP"}
V10_RENK = {"MB": ("kapak", "KAPAK_{c}.jpg"), "DB": ("galeri", "{c}_G6.jpg"), "PW": ("galeri", "{c}_G7.jpg"),
            "CI": ("galeri", "{c}_G8.jpg"), "WP": ("galeri", "{c}_G9.jpg")}   # ayni ciftin canli v10 renk kartlari
POSTER = (888, 588, 888 + 1226, 588 + 1538)          # KARAR 29 Eki: onayli kapak posteri oge left 888, top 588, 1226 x 1538
PENCERE, KOSE, KARANLIK, EGIM = 40, 150, 40, 5
BANT_AD = ("W01_KAPAK", "W09_PW")


def gri(im):
    return np.asarray(im.convert("L"), dtype=np.float32)


def etiket_olc(im):
    x0, y0, x1, y1 = ETIKET_KUTU
    k = im.crop((x0 - 3 * HP_SIGMA, y0 - 3 * HP_SIGMA, x1 + 3 * HP_SIGMA, y1 + 3 * HP_SIGMA)).convert("L")
    L = np.asarray(k, np.float32); G = np.asarray(k.filter(ImageFilter.GaussianBlur(HP_SIGMA)), np.float32)
    hp = np.abs(L - G)[3 * HP_SIGMA:-3 * HP_SIGMA, 3 * HP_SIGMA:-3 * HP_SIGMA]
    return int((hp > HP_ESIK).sum())


def fark(a, b, haric):
    """a, b PIL RGB ayni boyut; haric: disarida birakilan kutu ya da kutu listesi. -> (p99.9, max)"""
    d = np.abs(np.asarray(a.convert("RGB"), np.int16) - np.asarray(b.convert("RGB"), np.int16)).max(2)
    m = np.ones(d.shape, bool)
    for x0, y0, x1, y1 in (haric if isinstance(haric[0], (tuple, list)) else [haric]):
        m[y0:y1, x0:x1] = False
    v = d[m]
    return round(float(np.percentile(v, 99.9)), 1), int(v.max())


def kutu_fark(a, b):
    x0, y0, x1, y1 = ETIKET_KUTU
    d = np.abs(np.asarray(a.convert("RGB").crop(ETIKET_KUTU), np.int16) - np.asarray(b.convert("RGB").crop(ETIKET_KUTU), np.int16)).max(2)
    return round(float(np.percentile(d, 99.9)), 1), int(d.max())


def profil_bant(p):
    """p: dis -> ic yonunde profil. -> bant px (None: cerceve bulunamadi / gecis pencerede bitmedi)"""
    kar = np.nonzero(p < KARANLIK)[0]
    if not len(kar):
        return None
    j = d = int(kar[-1]) + 1                     # cerceveden sonraki ilk piksel
    while j + 1 < len(p) and abs(float(p[j + 1]) - float(p[j])) > EGIM:
        j += 1
    return None if j + 1 >= len(p) else j - d


def bant_olc(im):
    L = gri(im)
    x0, y0, x1, y1 = POSTER
    ys, xs = slice(y0 + KOSE, y1 - KOSE), slice(x0 + KOSE, x1 - KOSE)
    p = dict(sol=L[ys, x0 - PENCERE:x0 + PENCERE].mean(0),
             sag=L[ys, x1 - PENCERE:x1 + PENCERE].mean(0)[::-1],
             ust=L[y0 - PENCERE:y0 + PENCERE, xs].mean(1),
             alt=L[y1 - PENCERE:y1 + PENCERE, xs].mean(1)[::-1])
    return {k: profil_bant(v) for k, v in p.items()}


def renk_kimlik(im, cift, renk, a):
    """poster medyan CIELAB (galeri_v10_liste.renk_ozet) ayni ciftin 5 canli v10 renk kartina: en yakin = beklenen renk ve
    uzaklik < esik (5 referansin birbirine en kucuk uzakliginin yarisi; v10 renk_kapisi yontemi). 29 Eki onayli CANCER_LIBRA:
    kendi renk 0.0-0.4, en yakin baska renk 18.2."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import galeri_v10_liste as L
    ref = {}
    for k, (kok, ad) in V10_RENK.items():
        p = Path(a.v10_kapak if kok == "kapak" else a.v10_galeri) / ad.format(c=cift)
        if not p.exists():
            return dict(ozet="olculemedi", neden=f"renk kimligi olculemedi: v10 {p.name} yok")
        ref[k] = L.renk_ozet(Image.open(p).convert("RGB"), RENK_POSTER)
    v = L.renk_ozet(im, RENK_POSTER)
    d = {k: round(float(np.linalg.norm(v - x)), 1) for k, x in ref.items()}
    ks = list(ref)
    esik = min(float(np.linalg.norm(ref[x] - ref[y])) for i, x in enumerate(ks) for y in ks[i + 1:]) / 2
    yakin = min(d, key=d.get)
    ozet = f"{renk} {d[renk]} en yakin {yakin} esik {esik:.1f}"
    ok = yakin == renk and d[renk] < esik
    return dict(ozet=ozet, neden="" if ok else f"renk kimligi: {ozet} (beklenen {renk})")


def esik_oku(yol):
    if not yol or not Path(yol).exists():
        return None
    e = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not str(e.get("onay") or "").strip() or not isinstance(e.get("etiket_hp_max"), int) or not isinstance(e.get("bant_max_px"), int):
        return None
    return e


def dosya_kapi(p, ad, cift, a, esik):
    r = dict(cift=cift, ad=ad, dosya=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bicim="", etiket_hp=None,
             etiket_onayli_fark="", v10_fark="", bant="", durum="", neden=[])
    try:
        with Image.open(p) as im0:
            fmt, bt = im0.format, im0.size
            im = im0.convert("RGB")
    except Exception:  # noqa: BLE001
        r.update(durum="FAIL", neden=["okunamadi"]); return r
    r["bicim"] = f"{fmt} {bt[0]}x{bt[1]}"
    if fmt != "JPEG" or bt != BOYUT:
        r.update(durum="FAIL", neden=[f"bicim {fmt} {bt[0]}x{bt[1]} (JPEG 3000x2250)"]); return r
    esik_yok = []
    r["etiket_hp"] = etiket_olc(im)
    if esik is None:
        esik_yok.append("etiket")
    elif r["etiket_hp"] > esik["etiket_hp_max"]:
        r["neden"].append(f"etiket kutusu hp>{HP_ESIK} {r['etiket_hp']} > {esik['etiket_hp_max']}")
    if a.onayli:
        q = Path(a.onayli) / f"CANCER_LIBRA_{ad}.jpg"
        if q.exists():
            r["etiket_onayli_fark"] = "p99.9 %s max %s" % kutu_fark(im, Image.open(q))
    if ad in SAHNE_AD:
        q = Path(a.onayli or "-") / f"CANCER_LIBRA_{ad}.jpg"
        if not q.exists():
            r["neden"].append(f"onayli referans yok ({q.name}; --onayli)")
        else:
            p999, mx = fark(im, Image.open(q), [POSTER_HARIC[ad], CIFT_BANT])
            r["v10_fark"] = f"sahne onayli {q.name} p99.9 {p999} max {mx}"
            if p999 > FARK_P999 or mx > FARK_MAX:
                r["neden"].append(f"sahne farki (onayli CANCER_LIBRA; poster + cift satiri haric) p99.9 {p999} (<= {FARK_P999}) max {mx} (<= {FARK_MAX})")
        rk = renk_kimlik(im, cift, RENK_AD[ad], a)
        r["v10_fark"] += f" | renk {rk['ozet']}"
        if rk["neden"]:
            r["neden"].append(rk["neden"])
    if ad in BANT_AD:
        b = bant_olc(im)
        r["bant"] = " ".join(f"{k}:{v}" for k, v in b.items())
        if any(v is None for v in b.values()):
            r["neden"].append(f"bant olculemedi ({r['bant']})")
        elif esik is None:
            esik_yok.append("bant")
        elif max(b.values()) > esik["bant_max_px"]:
            r["neden"].append(f"bant {max(b.values())} px > {esik['bant_max_px']}")
    r["durum"] = "FAIL" if r["neden"] else ("ESIK_YOK" if esik_yok else "PASS")
    if esik_yok:
        r["neden"].append(f"onayli esik yok: {', '.join(esik_yok)} (olcum yazildi)")
    return r


def olc(a):
    """onayli CANCER_LIBRA 5 gorsel + canli v10 pozitif kontroller (etiketli G6 / G9, seritli G7 / G8) -> ESIK_ONERI"""
    on = Path(a.onayli); v10 = Path(a.v10_galeri)
    O = dict(yontem=dict(hp_sigma=HP_SIGMA, hp_esik=HP_ESIK, karanlik=KARANLIK, egim=EGIM, pencere=PENCERE, poster=POSTER), onayli={}, canli={})
    for ad in ADLAR:
        p = on / f"CANCER_LIBRA_{ad}.jpg"
        if not p.exists():
            O["onayli"][ad] = "yok"; continue
        im = Image.open(p).convert("RGB")
        O["onayli"][ad] = dict(etiket_hp=etiket_olc(im), bant=bant_olc(im) if ad in BANT_AD else None)
    for g in ("G6", "G7", "G8", "G9"):
        p = v10 / f"CANCER_LIBRA_{g}.jpg"
        if p.exists():
            im = Image.open(p).convert("RGB")
            O["canli"][g] = dict(etiket_hp=etiket_olc(im), bant=bant_olc(im) if g in ("G7", "G8") else None)
    on_e = [v["etiket_hp"] for v in O["onayli"].values() if isinstance(v, dict)]
    ca_e = [v["etiket_hp"] for v in O["canli"].values()]
    on_b = [x for v in O["onayli"].values() if isinstance(v, dict) and v["bant"] for x in v["bant"].values() if x is not None]
    ca_b = [x for v in O["canli"].values() if v["bant"] for x in v["bant"].values() if x is not None]
    O["oneri"] = dict(
        etiket_hp_max=(max(on_e) + min(ca_e)) // 2 if on_e and ca_e else None,
        bant_max_px=(max(on_b) + min(ca_b)) // 2 if on_b and ca_b else None,
        kural="onayli en buyuk ile canli (etiketli / seritli) en kucuk olcumun ortasi (tam sayi, asagi); Serdar onayi olmadan kullanilmaz",
        onayli_etiket_max=max(on_e) if on_e else None, canli_etiket_min=min(ca_e) if ca_e else None,
        onayli_bant_max=max(on_b) if on_b else None, canli_bant_min=min(ca_b) if ca_b else None)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "ESIK_ONERI.json").write_text(json.dumps(O, indent=1, ensure_ascii=False), encoding="utf-8")
    o = O["oneri"]
    (out / "ESIK_ONERI.md").write_text(
        "# Galeri v11 B3 esik onerisi (onayli CANCER_LIBRA olcumu; Serdar onayi bekler)\n\n"
        f"- etiket_hp_max oneri {o['etiket_hp_max']} (onayli en buyuk {o['onayli_etiket_max']}, canli etiketli en kucuk {o['canli_etiket_min']})\n"
        f"- bant_max_px oneri {o['bant_max_px']} (onayli en buyuk {o['onayli_bant_max']}, canli seritli en kucuk {o['canli_bant_min']})\n\n"
        + "".join(f"- onayli {k}: {v}\n" for k, v in O["onayli"].items()) + "".join(f"- canli {k}: {v}\n" for k, v in O["canli"].items()),
        encoding="utf-8")
    print(json.dumps(O["oneri"], ensure_ascii=False), flush=True)
    return 0 if o["etiket_hp_max"] is not None and o["bant_max_px"] is not None else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dosya-dir", default=""); ap.add_argument("--v10-galeri", required=True); ap.add_argument("--v10-kapak", default="")
    ap.add_argument("--ciftler", default="data/pod/pod78_ids.csv"); ap.add_argument("--sadece", default="")
    ap.add_argument("--esik", default=""); ap.add_argument("--onayli", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--olc", action="store_true", help="onayli CANCER_LIBRA olcumu + esik onerisi (kapi kosmaz)")
    a = ap.parse_args(argv)
    if a.olc:
        if not a.onayli:
            print("::error::--olc icin --onayli"); return 2
        return olc(a)
    esik = esik_oku(a.esik)
    rows = [r for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("cift")]
    s = {x.strip() for x in a.sadece.split(",") if x.strip()}
    rows = [r for r in rows if not s or r["cift"] in s or r["listing_id"] in s]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = []
    for n, r in enumerate(rows, 1):
        for ad in ADLAR:
            p = Path(a.dosya_dir) / f"{r['cift']}_{ad}.jpg"
            if not p.exists():
                R.append(dict(cift=r["cift"], ad=ad, dosya=p.name, sha256="", bicim="", etiket_hp="", etiket_onayli_fark="", v10_fark="", bant="",
                              durum="FAIL", neden=["dosya yok"]))
                continue
            R.append(dosya_kapi(p, ad, r["cift"], a, esik))
        print(f"[{n}/{len(rows)}] {r['cift']} " + " ".join(f"{x['ad'][:3]}:{x['durum']}" for x in R[-5:]), flush=True)
    alan = ["cift", "ad", "dosya", "sha256", "bicim", "etiket_hp", "etiket_onayli_fark", "v10_fark", "bant", "durum", "neden"]
    with open(out / "KAPI.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alan); w.writeheader()
        w.writerows(dict(x, neden="; ".join(x["neden"])) for x in R)
    say = {}
    for x in R:
        say[x["durum"]] = say.get(x["durum"], 0) + 1
    (out / "KAPI.md").write_text(
        f"# Galeri v11 tam boy kapi\n\n{' | '.join(f'{k} {v}' for k, v in sorted(say.items()))} (dosya {len(R)})\n"
        f"esik: {'onayli ' + str(esik) if esik else 'YOK (etiket ve bant ESIK_YOK)'} | v10 fark esigi p99.9 <= {FARK_P999}, max <= {FARK_MAX} (CLAUDE.md)\n\n"
        + "".join(f"- {x['dosya']} {x['durum']}: {'; '.join(x['neden'])}\n" for x in R if x["durum"] != "PASS"), encoding="utf-8")
    print(f"KAPI: {say}", flush=True)
    return 0 if say.get("PASS", 0) == len(R) else 1


if __name__ == "__main__":
    sys.exit(main())
