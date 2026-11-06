#!/usr/bin/env python3
"""P1-G galeri karti (Serdar 5 Kas "hepsi ok": metin a, yontem b). ETSY API YOK, token yok, kilit yok; Etsy'ye yazim YOK.
Eski W05 "02 Your Approval" sozu ("... or as shown if there is no reply within 24 hours of the preview") yerine yeni onayli metin
(wa_kupa_kart_ornek.ONAY_METNI: "We make your print or file once you approve the preview").

tara  --in <yedek> --out <dir>
    Girdi galeri-v11-yedek-oku + galeri_v11_yedek_indir klasoru (<ilan>_<CIFT>/GALERI.json + r<rank>_<image_id>.jpg). Her gorsel
    galeri_metin_tara.ocr (kucult GENISLIK px, tesseract psm 11) ile okunur; GALERI.json alt_text de taranir. Video taranmaz.
    Metin bosluk normalize, buyuk / kucuk harf duyarsiz DESENLER aranir. OKUNAMADI: dosya yok, OCR hata / zaman asimi, rank 5'te
    "Your Approval" capasi okunmadi. Cikti TARAMA.csv (ilan, cift, rank, image_id, kaynak, desen; METIN YOK) + OZET.md. ETA 50 gorselde bir.
    Cikis 0 (bulgu raporu); girdi yapisi bozuksa 1.
uret  --yedek <yedek> --kaynak <W02_W06> --sonra <KOSU> --ci <ref/kapak_ci> --out <dir> (Serdar 6 Kas, yontem b; GALERI istisnasi
    yalniz W05_SUREC, yalniz bu gorev): 78 cift (data/pod/pod78_ids.csv) icin ornek b ile BIREBIR kapilar (kimlik zinciri, canli OCR,
    bilinen PASS, kart kapilari). Cikti <CIFT>_W05_SUREC.jpg, ONCE_SONRA_<CIFT>.jpg, MANIFEST_W05.csv, RAPOR.json. Cikis 0 = 78/78 PASS.
ornek --yedek <yedek> --kaynak <W02_W06 kosu klasorleri> --sonra <POSTER_GALERI_V11_YUKLE/KOSU> --ci <ref/kapak_ci> --out <dir>
    3 cift (ORNEK) x iki yontem, gercek oran 3000x2250:
      a  bant duzenleme: taban kartta eski 02 govde murekkep kutusu (olculur) + 6 px ZEMIN ile doldurulur, yeni metin K.yaz ile ESKI
         satirin ayni x / y / genisliginde (Manrope 64/400 #2B2220) yazilir; 3. satirin yeri bos kalir.
      b  yeniden cizim: wa_s4(ci) yeni metinle (kart_isle kapilari aynen); yalniz 02 ve 03 kayar.
    TABAN (Serdar 5 Kas A): a ve b icin Drive kaynagi <kaynak>/<kosu>/<CIFT>_W05_SUREC.jpg (dosya sha256 = MANIFEST_W02_W06*.csv =
    yukleme_kaydi sha256). CLAUDE.md GALERI "canli galeriden" kuralindan Serdar onayli sapma; "kaynak canliya karsi fark kapisi" kaldirildi.
    KIMLIK ZINCIRI (kapi, esiksiz): bugunku GALERI.json r5 listing_image_id = SONRA_<ilan>.json son_ids[W05] VE ayni kayittaki
    yukleme_kaydi (hedef_sira 5) sha256 = MANIFEST sha256; tutmazsa o cift DUR. Canli r5 OCR: eski metin desen >= 1 ve "Your Approval" (kapi).
    Bilgi (kapi degil): canli-kaynak fark p99.9 / max (Etsy yeniden kodlama, 4:2:0) ve 256x192 NCC.
    Bilinen PASS: wa_s4(ci, ESKI) cizimi MANIFEST sha256'sini vermezse o ciftte b uretilmez, sonuc DUR.
    Kapilar (kart basina): bant disi fark (p99.9 <= 12, max <= 45; esik eski78_gorsel_uret ile ayni, DEGISMEZ), OCR eski desen 0 ve
    capa okunur, yeni metin difflib >= 0.8 (bant kirpimi), yasak karakter (uzun / orta tire, nokta, +, =), etsy_common METIN_KESIN +
    METIN_BAGLAM 0, 3000x2250 JPEG q95 subsampling 0 (get_sampling 0, nicemleme tablolari q95 referansina esit).
    Cikti <out>/<ilan>_<CIFT>_W05_<a|b>.jpg, ONCE_SONRA_<CIFT>_<a|b>.jpg (kutu isaretli), RAPOR.json. Cikis 0 = 6 kart PASS.
Kutular kod yazilmadan sabitlendi (Merkez 5 Kas): b KUTU_B (K.KUTULAR'dan hesaplanir, sabitle esit degilse ya da 01 / 04 / poster /
baslik / alt not kutusuna degerse DUR); a eski 02 govde murekkebi + 6 px."""
import argparse
import csv
import difflib
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, JpegImagePlugin

BURA = Path(__file__).resolve().parent
sys.path.insert(0, str(BURA))
sys.path.insert(0, str(BURA.parent / "etsy"))
import galeri_metin_tara as G  # noqa: E402  (ocr / kucult / GENISLIK: tek kaynak, kopyalanmaz)
import wa_kupa_kart_ornek as WA  # noqa: E402
import yd_kart_ornek as K  # noqa: E402

ESKI = "We make your print or file once you approve, or as shown if there is no reply within 24 hours of the preview"
YENI = WA.ONAY_METNI
YENI_SATIR = ["We make your print or file", "once you approve the preview"]
ESKI_SATIR = ["We make your print or file once you", "approve, or as shown if there is no", "reply within 24 hours of the preview"]
DESENLER = [("no reply", re.compile(r"no\s+reply", re.I)), ("as shown", re.compile(r"as\s+shown", re.I)),
            ("if there is no", re.compile(r"if\s+there\s+is\s+no", re.I)), ("24 hours?", re.compile(r"24\s+hours\?", re.I))]
CAPA, CAPA_RANK = "your approval", 5
ORNEK = [("CANCER_LIBRA", "4570143815"), ("SAGITTARIUS_SAGITTARIUS", "4570206865"), ("AQUARIUS_AQUARIUS", "4570110121")]
P999_ESIK, MAX_ESIK = 12, 45          # eski78_gorsel_uret bant disi fark kapisi (DEGISMEZ)
KUTU_B = (1504, 912, 2784, 1592)      # Merkez 5 Kas: 02 + 03 (eski U yeni), >= 8 px pay, 8'e hizali
PAY_B, HIZA, PAY_A = 8, 8, 6
MUREKKEP_ESIK = 40                    # ZEMIN'den kanal farki > 40 = murekkep (JPEG gurultusu <= ~10)
DIFFLIB_ESIK = 0.8
BOYUT = (3000, 2250)
TARA_ALAN = ["listing_id", "cift", "rank", "image_id", "kaynak", "desen"]
AD = re.compile(r"^(\d+)_([A-Z]+_[A-Z]+)$")


def norm(t):
    return " ".join((t or "").split())


def desen_bul(t):
    n = norm(t)
    return [ad for ad, rx in DESENLER if rx.search(n)]


def capa_var(t):
    return CAPA in norm(t).casefold()


# ---------------------------------------------------------------- tara
def ilanlar(kok):
    out = []
    for d in sorted(Path(kok).iterdir()):
        m = AD.match(d.name)
        if d.is_dir() and m and (d / "GALERI.json").exists():
            j = json.loads((d / "GALERI.json").read_text(encoding="utf-8"))
            out.append((m.group(1), m.group(2), d, j))
    return out


def tara_bir(d, g):
    p = d / f"r{g['rank']}_{g['listing_image_id']}.jpg"
    if not p.exists():
        return None, "dosya_yok"
    try:
        return G.ocr(p, G.GENISLIK), None
    except subprocess.TimeoutExpired:
        return None, "zaman_asimi"
    except Exception as e:  # noqa: BLE001
        return None, f"ocr_hata {type(e).__name__}"


def tara(kok, out, isci=None):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    il = ilanlar(kok)
    if not il:
        print(f"::error::tara: {kok} altinda <ilan>_<CIFT>/GALERI.json yok"); return 1
    isler = [(lid, c, d, g) for lid, c, d, j in il for g in sorted(j.get("gorseller") or [], key=lambda x: x["rank"])]
    bozuk = [(lid, g) for lid, _, _, g in isler if not str(g.get("rank", "")).isdigit() or not str(g.get("listing_image_id", "")).isdigit()]
    if bozuk:
        print(f"::error::tara: GALERI.json rank / image_id bozuk ({len(bozuk)})"); return 1
    satir, okunamadi = [], []
    alt_n = 0
    for lid, c, _, g in isler:                          # alt metin (her gorselin alt_text alani)
        alt_n += 1
        for ds in desen_bul(g.get("alt_text") or ""):
            satir.append(dict(listing_id=lid, cift=c, rank=g["rank"], image_id=g["listing_image_id"], kaynak="alt_text", desen=ds))
    okuma = Path(kok) / "OKUMA.csv"                     # galeri-v11-yedek-oku: ilan basina gorsel sayisi (858 = 78 x 11 iddiasi)
    js_say = {lid: len(j.get("gorseller") or []) for lid, _, _, j in il}
    if okuma.exists():
        ok_say = {r_["listing_id"]: int(r_["gorsel"]) for r_ in csv.DictReader(open(okuma, encoding="utf-8"))}
        dag = {}
        for v in ok_say.values():
            dag[v] = dag.get(v, 0) + 1
        sayim = dict(okuma_toplam=sum(ok_say.values()), okuma_dagilim=dag, ilan=len(ok_say), GALERI_json_ayni=ok_say == js_say)
    else:
        sayim = dict(okuma_toplam=None, neden="OKUMA.csv yok")
    t0, n, toplam = time.time(), 0, len(isler)
    with ThreadPoolExecutor(isci or os.cpu_count() or 2) as ex:
        fut = {ex.submit(tara_bir, d, g): (lid, c, g) for lid, c, d, g in isler}
        for f in as_completed(fut):
            lid, c, g = fut[f]
            metin, hata = f.result()
            n += 1
            if hata is None and g["rank"] == CAPA_RANK and not capa_var(metin):
                hata = "capa_yok"
            if hata:
                okunamadi.append(dict(listing_id=lid, cift=c, rank=g["rank"], image_id=g["listing_image_id"], kaynak="okunamadi", desen=hata))
            if metin is not None:
                for ds in desen_bul(metin):
                    satir.append(dict(listing_id=lid, cift=c, rank=g["rank"], image_id=g["listing_image_id"], kaynak="ocr", desen=ds))
            if n % 50 == 0 or n == toplam:
                e = time.time() - t0
                print(f"ETA tara: {n}/{toplam} gorsel, gecen {e:.0f}s, kalan {e * (toplam - n) / n:.0f}s, %{100 * n // toplam}", flush=True)
    anah = lambda s: (s["listing_id"], int(s["rank"]), s["kaynak"], s["desen"])  # noqa: E731
    with open(out / "TARAMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=TARA_ALAN); w.writeheader()
        w.writerows(sorted(satir, key=anah) + sorted(okunamadi, key=anah))
    ocr_g = {(s["listing_id"], int(s["rank"])) for s in satir if s["kaynak"] == "ocr"}
    alt_g = {(s["listing_id"], int(s["rank"])) for s in satir if s["kaynak"] == "alt_text"}
    rank_say = lambda kume: {r: sum(1 for _, x in kume if x == r) for r in sorted({x for _, x in kume})}  # noqa: E731
    ok_r = {}
    for s in okunamadi:
        ok_r.setdefault(int(s["rank"]), {}).setdefault(s["desen"].split()[0], 0)
        ok_r[int(s["rank"])][s["desen"].split()[0]] += 1
    r5_ok = sum(1 for s in okunamadi if int(s["rank"]) == CAPA_RANK)
    sonuc = "TAM" if not okunamadi else ("EKSIK (rank 5 okunamadi > 0)" if r5_ok else "TAM DEGIL (okunamadi var, rank 5 disi)")
    desen_say = {ad: sum(1 for s in satir if s["kaynak"] == "ocr" and s["desen"] == ad) for ad, _ in DESENLER}
    ozet = (f"# P1-G galeri taramasi: eski yanitsiz basim sozu\n\nilan {len(il)} | gorsel (GALERI.json) {toplam} | OCR taranan {n} | "
            f"alt metin taranan {alt_n} | video taranmadi\nOKUMA.csv sayimi: {sayim}\n"
            f"desenler (bosluk normalize, harf duyarsiz): {', '.join(rx.pattern for _, rx in DESENLER)}\n\n"
            f"## Eski metinli gorsel (OCR)\n\ngorsel {len(ocr_g)} | ilan {len({x for x, _ in ocr_g})} | rank basina {rank_say(ocr_g)}\n"
            f"desen basina eslesme {desen_say}\n\n"
            f"## Alt metin eslesmesi\n\ngorsel {len(alt_g)} | ilan {len({x for x, _ in alt_g})} | rank basina {rank_say(alt_g)}\n\n"
            f"## Okunamadi\n\ntoplam {len(okunamadi)} | rank basina / neden {ok_r} | rank 5 {r5_ok}\n\nSONUC: {sonuc}\n"
            f"Ayrinti TARAMA.csv (ilan, cift, rank, image_id, kaynak, desen; metin yazilmaz).\n")
    (out / "OZET.md").write_text(ozet, encoding="utf-8")
    print(f"::notice::P1-G tara sayim: OKUMA.csv toplam {sayim.get('okuma_toplam')}, ilan basina {sayim.get('okuma_dagilim')}, "
          f"GALERI.json ile ayni {sayim.get('GALERI_json_ayni')}")
    print(f"::notice::P1-G tara: ilan {len(il)}, gorsel {toplam} (OCR {n}), alt metin {alt_n}; eski metinli gorsel {len(ocr_g)} "
          f"({len({x for x, _ in ocr_g})} ilan), rank {rank_say(ocr_g)}; alt metin eslesme {len(alt_g)}; okunamadi {len(okunamadi)} (rank 5: {r5_ok}); {sonuc}")
    return 0


# ---------------------------------------------------------------- cizim
def _sifirla():
    K.YAZILAR.clear(); K.SATIRLAR.clear(); K.KUTULAR.clear()


def ciz(ci, metin):
    """wa_s4 + kart_isle (metin / Title Case / yasak / renk kapilari aynen). -> (jpeg bayt, KUTULAR, cizilen satirlar, poster kutusu,
    02 govde yaz cagrisi (x, y, gen))"""
    _sifirla()
    bek = WA.beklenen("A", "B")
    bek["S4_SUREC"] = [metin if x == YENI else x for x in bek["S4_SUREC"]]
    kayit, asil = [], K.yaz

    def izle(d, s, satirlar, x, y, hiza="left", gen=None):
        if s is K.METIN and K.BLOK[0] == "blok1":
            kayit.append((list(satirlar), x, y, gen))
        return asil(d, s, satirlar, x, y, hiza, gen)
    K.yaz = izle
    try:
        _, rapor, jb = WA.kart_isle([("W05.jpg", "S4_SUREC", lambda: (*WA.wa_s4(ci, metin), ()))], bek)
    finally:
        K.yaz = asil
    if len(kayit) < 1:
        raise SystemExit("DUR: 02 govde yaz cagrisi kaydedilmedi")
    return jb["W05.jpg"], [(b, t, list(k)) for b, t, k in K.KUTULAR], [t for _, t in K.SATIRLAR], rapor["W05.jpg"]["foto_kutu"], kayit[-1]


def birlesik(kutular):
    k = list(zip(*kutular))
    return [min(k[0]), min(k[1]), max(k[2]), max(k[3])]


def kesisir(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def kutu_b(eski_k, yeni_k, poster):
    """02 ve 03 bloklari (eski U yeni) + PAY_B, 8'e hizali; diger kutulara degerse DUR"""
    sec = [k for b, _, k in eski_k + yeni_k if b in ("blok1", "blok2")]
    u = birlesik(sec)
    kb = (math.floor((u[0] - PAY_B) / HIZA) * HIZA, math.floor((u[1] - PAY_B) / HIZA) * HIZA,
          math.ceil((u[2] + PAY_B) / HIZA) * HIZA, math.ceil((u[3] + PAY_B) / HIZA) * HIZA)
    diger = [(b, k) for b, _, k in eski_k + yeni_k if b not in ("blok1", "blok2")] + [("poster", p) for p in poster]
    deg = sorted({b for b, k in diger if kesisir(kb, k)})
    if deg:
        raise SystemExit(f"DUR: b kutusu {kb} su kutulara degiyor: {deg}")
    return kb


def dizi(b):
    im = Image.open(io.BytesIO(b) if isinstance(b, (bytes, bytearray)) else b)
    return np.asarray(im.convert("RGB"), np.int16)


def bant_disi(a, b, kutu):
    """kutu disi piksel farki (kanal max): p99.9 ve max"""
    if a.shape != b.shape:
        return dict(p999=None, max=None, PASS=False, neden=f"boyut {a.shape} != {b.shape}")
    f = np.abs(a - b).max(axis=2)
    m = np.ones(f.shape, bool)
    if kutu:
        x0, y0, x1, y1 = kutu
        m[y0:y1, x0:x1] = False
    v = f[m]
    p, mx = float(np.percentile(v, 99.9)), int(v.max())
    return dict(p999=round(p, 2), max=mx, kutu=list(kutu) if kutu else None, PASS=p <= P999_ESIK and mx <= MAX_ESIK)


def murekkep_kutu(a, pencere):
    """pencere icinde ZEMIN'den farki > MUREKKEP_ESIK piksellerin kutusu (PIL: sag / alt haric)"""
    x0, y0, x1, y1 = pencere
    z = np.array(Image.new("RGB", (1, 1), K.ZEMIN).getpixel((0, 0)), np.int16)
    m = np.abs(a[y0:y1, x0:x1] - z).max(axis=2) > MUREKKEP_ESIK
    ys, xs = np.nonzero(m)
    if not len(xs):
        return None
    return [x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1]


def jpeg_bayt(im):
    b = io.BytesIO(); im.save(b, "JPEG", quality=95, subsampling=0)
    return b.getvalue()


def yontem_a(taban_b, eski_k, cagri):
    """taban JPEG uzerinde eski 02 govdesini sil (murekkep + 6 px), yeni satirlari eski satirin x / y / genisliginde yaz"""
    a = dizi(taban_b)
    govde = birlesik([k for b, t, k in eski_k if b == "blok1" and t == "metin"])
    pencere = (govde[0] - 13, govde[1] - 14, govde[2] + 13, govde[3] + 13)
    ink = murekkep_kutu(a, pencere)
    if ink is None or ink[0] < govde[0] - 8 or ink[1] < govde[1] - 8 or ink[2] > govde[2] + 8 or ink[3] > govde[3] + 8:
        raise SystemExit(f"DUR: a eski 02 govde murekkebi beklenen yerde degil (olculen {ink}, metin kutusu {govde})")
    kutu = (ink[0] - PAY_A, ink[1] - PAY_A, ink[2] + PAY_A, ink[3] + PAY_A)
    im = Image.open(io.BytesIO(taban_b)).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([kutu[0], kutu[1], kutu[2] - 1, kutu[3] - 1], fill=K.ZEMIN)
    satirlar, x, y, gen = cagri
    if satirlar != ESKI_SATIR:
        raise SystemExit(f"DUR: a eski 02 satirlari beklenenden farkli {satirlar}")
    _sifirla(); K.BLOK[0] = "blok1"
    K.yaz(d, K.METIN, YENI_SATIR, x, y, "left", gen)
    yk = [k for _, _, k in K.KUTULAR]
    if any(not (k[0] >= kutu[0] and k[1] >= kutu[1] and k[2] <= kutu[2] and k[3] <= kutu[3]) for k in yk):
        raise SystemExit(f"DUR: a yeni satir kutulari {yk} doldurma kutusu {kutu} disina tasiyor")
    return jpeg_bayt(im), kutu, ink, [t for _, t in K.SATIRLAR], yk


# ---------------------------------------------------------------- kapilar
def metin_kapisi(satirlar):
    """yasak karakter (WA.YASAK: nokta, +, =, uzun / orta tire) + satir sonu nokta + etsy_common METIN_KESIN / METIN_BAGLAM"""
    import etsy_common as E
    kotu = [t for t in satirlar if WA.YASAK.search(t) or re.search(r"\.\s*$", t) or re.search(r"[–—+=]", t)]
    rx = [(ad, re.compile(r, re.I)) for ad, r in E.METIN_KESIN + E.METIN_BAGLAM]
    etsy = [(ad, t) for t in satirlar for ad, r in rx if r.search(t)]
    return dict(yasak_karakter=kotu, etsy_metin=[ad for ad, _ in etsy], PASS=not kotu and not etsy)


def jpeg_kapisi(b):
    im = Image.open(io.BytesIO(b))
    ref = Image.open(io.BytesIO(jpeg_bayt(Image.new("RGB", (16, 16), K.ZEMIN))))
    s = JpegImagePlugin.get_sampling(im)
    q = {k: list(v) for k, v in im.quantization.items()} == {k: list(v) for k, v in ref.quantization.items()}
    return dict(boyut=list(im.size), format=im.format, subsampling=s, q95_tablo=q,
                PASS=im.format == "JPEG" and im.size == BOYUT and s == 0 and q)


def ocr_bayt(b, genislik):
    with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
        f.write(b); f.flush()
        return G.ocr(f.name, genislik)


def ocr_kapisi(b, kirp):
    """tum kart (GENISLIK px): eski desen 0 ve capa okunur; bant kirpimi (1:1): yeni metin difflib >= 0.8"""
    try:
        t = ocr_bayt(b, G.GENISLIK)
    except Exception as e:  # noqa: BLE001
        return dict(PASS=False, neden=f"okunamadi {type(e).__name__}")
    ds, capa = desen_bul(t), capa_var(t)
    im = Image.open(io.BytesIO(b)).convert("RGB").crop(kirp)
    try:
        tk = ocr_bayt(jpeg_bayt(im), 0)
    except Exception as e:  # noqa: BLE001
        return dict(PASS=False, eski_desen=ds, capa=capa, neden=f"kirpim okunamadi {type(e).__name__}")
    sade = lambda s: " ".join(re.sub(r"[^a-z0-9 ]", " ", s.casefold()).split())  # noqa: E731
    oran = difflib.SequenceMatcher(None, sade(YENI), sade(tk)).ratio()
    return dict(eski_desen=ds, capa=capa, difflib=round(oran, 3), kirpim=list(kirp),
                PASS=not ds and capa and oran >= DIFFLIB_ESIK)


def kart_kapilari(b, taban_a, kutu, kirp, satirlar):
    k = dict(bant=bant_disi(dizi(b), taban_a, kutu), ocr=ocr_kapisi(b, kirp), metin=metin_kapisi(satirlar), jpeg=jpeg_kapisi(b))
    k["PASS"] = all(v["PASS"] for v in k.values())
    return k


def once_sonra(taban_b, yeni_b, kutu, etiket):
    """ust: iki kart 1500x1125 yan yana (kutu kirmizi); alt: kutu bolgesi 1:1 (onceki | sonraki)"""
    A = Image.open(io.BytesIO(taban_b)).convert("RGB"); B = Image.open(io.BytesIO(yeni_b)).convert("RGB")
    kw, kh = kutu[2] - kutu[0], kutu[3] - kutu[1]
    s = min(1.0, 1480 / kw)
    zw, zh = round(kw * s), round(kh * s)
    t = Image.new("RGB", (3000, 1125 + 40 + zh + 20), "white"); d = ImageDraw.Draw(t)
    for i, im in enumerate((A, B)):
        k = im.resize((1500, 1125), Image.LANCZOS); kd = ImageDraw.Draw(k)
        kd.rectangle([v / 2 for v in kutu], outline=(220, 0, 0), width=3)
        t.paste(k, (i * 1500, 0))
        z = im.crop(kutu)
        t.paste(z.resize((zw, zh), Image.LANCZOS) if s < 1 else z, (i * 1500 + 10, 1125 + 40))
    from PIL import ImageFont
    d.text((10, 1128), f"ONCE | SONRA ({etiket}) kutu {list(kutu)}", fill=(0, 0, 0), font=ImageFont.load_default(size=30))
    b = io.BytesIO(); t.save(b, "JPEG", quality=90)
    return b.getvalue()


# ---------------------------------------------------------------- ornek
def manifest_sha(d):
    out = {}
    for m in sorted(Path(d).glob("MANIFEST_W02_W06*.csv")):
        for r in csv.DictReader(open(m, encoding="utf-8")):
            out[r["dosya"]] = r["sha256"]
    return out


def kosu_no(k):
    n = "".join(ch for ch in Path(k).name if ch.isdigit())
    return int(n) if n else 0


def sonra_kayit(kok, lid):
    """galeri-v11-yukle SONRA_<ilan>.json (KOSU/<kosu>/ilanlar/): galeri_v11_dogrula ile ayni birlestirme (eski kosu once; sonraki kosunun
    kaydi ayni hedef sirasini ezer; son_ids en son kosunun)"""
    kok = Path(kok)
    dosya = sorted(kok.rglob(f"SONRA_{lid}.json"), key=lambda p: kosu_no(p.relative_to(kok).parts[0]))
    son, kay, kosular = {}, {}, []
    for p in dosya:
        j = json.loads(p.read_text(encoding="utf-8"))
        kay.update({int(x["hedef_sira"]): x for x in j.get("yukleme_kaydi") or []})
        son = dict(j); kosular.append(p.relative_to(kok).parts[0])
    return dict(son, yukleme_kaydi=[kay[k] for k in sorted(kay)], _kosular=kosular) if dosya else None


def kimlik_kapisi(r5_id, sonra, manifest):
    """KESIN KIMLIK ZINCIRI (Serdar 5 Kas, esiksiz): bugunku GALERI.json r5 listing_image_id = SONRA son_ids[W05] VE ayni kayittaki
    yukleme_kaydi (hedef_sira 5) sha256 = MANIFEST sha256"""
    if not sonra:
        return dict(PASS=False, neden="SONRA kaydi yok")
    son = sonra.get("son_ids") or []
    k5 = {int(x["hedef_sira"]): x for x in sonra.get("yukleme_kaydi") or []}.get(CAPA_RANK) or {}
    id_ok = len(son) >= CAPA_RANK and son[CAPA_RANK - 1] == r5_id
    sha_ok = bool(manifest) and k5.get("sha256") == manifest
    return dict(r5_id=r5_id, son_ids_W05=son[CAPA_RANK - 1] if len(son) >= CAPA_RANK else None, yukleme_sha256=k5.get("sha256"),
                yukleme_id=k5.get("listing_image_id"), manifest=manifest, kosular=sonra.get("_kosular"), id_PASS=id_ok, sha_PASS=sha_ok,
                PASS=id_ok and sha_ok)


def kaynak_sec(kaynak, cift, hedef_sha):
    """her kosu klasorunde <CIFT>_W05_SUREC.jpg: dosya sha256 = MANIFEST sha256 = yukleme_kaydi sha256 olan ilk kosu (canli fark kapisi YOK)"""
    ad = f"{cift}_W05_SUREC.jpg"
    aday = []
    for d in sorted((p for p in Path(kaynak).iterdir() if p.is_dir()), key=kosu_no):
        p = d / ad
        if p.exists():
            b = p.read_bytes()
            aday.append(dict(kosu=d.name, sha256=hashlib.sha256(b).hexdigest(), manifest=manifest_sha(d).get(ad), _b=b))
    gecen = [x for x in aday if x["sha256"] == x["manifest"] == hedef_sha]
    temiz = [{k: v for k, v in x.items() if k != "_b"} for x in aday]
    return (gecen[0] if gecen else None), temiz


def ncc(a, b):
    """256x192 gri NCC (galeri_v11_dogrula ile ayni olcu; yalniz bilgi)"""
    v = [np.asarray(Image.fromarray(x.astype(np.uint8)).convert("L").resize((256, 192), Image.LANCZOS), np.float64).ravel() for x in (a, b)]
    v = [(x - x.mean()) / (x.std() or 1) for x in v]
    return round(float(v[0] @ v[1] / v[0].size), 4)


def canli_ocr(p):
    """canli r5: eski metin (>= 1 desen) ve 'Your Approval' capasi okunur (KAPI)"""
    try:
        t = G.ocr(p, G.GENISLIK)
    except Exception as e:  # noqa: BLE001
        return dict(PASS=False, neden=f"okunamadi {type(e).__name__}")
    ds, capa = desen_bul(t), capa_var(t)
    return dict(eski_desen=ds, capa=capa, PASS=bool(ds) and capa)


def ornek_cift(r, cift, lid, yedek, kaynak, sonra_kok, ci_kok, out, yontemler=("a", "b"), uretim=False):
    """uretim=True (uret, Serdar 6 Kas yontem b): yalniz b; dosya <CIFT>_W05_SUREC.jpg, ONCE_SONRA_<CIFT>.jpg; ::notice:: yok (ozet)."""
    dd = Path(yedek) / f"{lid}_{cift}"
    j = json.loads((dd / "GALERI.json").read_text(encoding="utf-8"))
    g5 = [g for g in j["gorseller"] if g["rank"] == CAPA_RANK]
    if len(g5) != 1 or not (dd / f"r5_{g5[0]['listing_image_id']}.jpg").exists():
        raise SystemExit(f"DUR: {cift} canli r5 dosyasi yok")
    r5_id = g5[0]["listing_image_id"]; canli_p = dd / f"r5_{r5_id}.jpg"
    canli_b = canli_p.read_bytes(); canli_a = dizi(canli_b)
    sonra = sonra_kayit(sonra_kok, lid)
    k5 = {int(x["hedef_sira"]): x for x in (sonra or {}).get("yukleme_kaydi") or []}.get(CAPA_RANK) or {}
    sec, adaylar = kaynak_sec(kaynak, cift, k5.get("sha256"))
    r["kaynak_adaylar"] = adaylar
    r["kimlik"] = kimlik_kapisi(r5_id, sonra, sec["manifest"] if sec else None)
    r["canli_ocr"] = canli_ocr(canli_p)
    if not sec or not r["kimlik"]["PASS"] or not r["canli_ocr"]["PASS"]:
        raise SystemExit(f"DUR: {cift} kimlik zinciri / canli OCR kapisi: kaynak {'var' if sec else 'yok'}, kimlik {r['kimlik']}, "
                         f"canli OCR {r['canli_ocr']}")
    taban_b = sec["_b"]; taban_a = dizi(taban_b)
    r.update(kaynak_kosu=sec["kosu"], taban="drive (sha = MANIFEST = yukleme_kaydi; Serdar 5 Kas A)",
             canli=dict(sha256=hashlib.sha256(canli_b).hexdigest(), boyut=[int(canli_a.shape[1]), int(canli_a.shape[0])],
                        subsampling=JpegImagePlugin.get_sampling(Image.open(io.BytesIO(canli_b))), bayt=len(canli_b)),
             bilgi_canli_kaynak_fark=(lambda f: dict(p999=f["p999"], max=f["max"]))(bant_disi(taban_a, canli_a, None)),
             bilgi_ncc=ncc(taban_a, canli_a) if canli_a.shape == taban_a.shape else None)
    ci = Image.open(Path(ci_kok) / f"CI_{cift}.png").convert("RGB")
    eski_b, eski_k, eski_s, poster, eski_cagri = ciz(ci, ESKI)
    r["bilinen_pass"] = dict(eski_cizim_sha256=hashlib.sha256(eski_b).hexdigest(), manifest=sec["manifest"],
                             PASS=hashlib.sha256(eski_b).hexdigest() == sec["manifest"])
    if eski_s[eski_s.index("Your Approval") + 1:eski_s.index("03")] != ESKI_SATIR:
        raise SystemExit(f"DUR: {cift} eski 02 satirlari canli kart kirilimindan farkli")
    kartlar = {}
    if "a" in yontemler:
        a_b, kutu_a, ink, a_s, a_k = yontem_a(taban_b, eski_k, eski_cagri)
        ka = kart_kapilari(a_b, taban_a, kutu_a, tuple(kutu_a), a_s)
        r["a"] = dict(kutu=list(kutu_a), murekkep=ink, yeni_satir_kutu=a_k, kapilar=ka,
                      not_="3. satirin yeri bos kalir (eski metin 3 satir, yeni 2)")
        kartlar["a"] = a_b
    if not r["bilinen_pass"]["PASS"]:
        r["b"] = dict(uretilmedi="DUR: wa_s4 ESKI metin cizimi MANIFEST sha256'sini vermedi (bilinen PASS FAIL)")
    else:
        b_b, yeni_k, yeni_s, poster_y, _ = ciz(ci, YENI)
        kb = kutu_b(eski_k, yeni_k, poster + poster_y)
        if tuple(kb) != KUTU_B:
            raise SystemExit(f"DUR: hesaplanan b kutusu {kb} != sabit {KUTU_B}")
        govde = birlesik([k for b, t, k in yeni_k if b == "blok1" and t == "metin"])
        kirp_b = (govde[0] - PAY_A, govde[1] - PAY_A, govde[2] + PAY_A, govde[3] + PAY_A)
        if yeni_s[yeni_s.index("Your Approval") + 1:yeni_s.index("03")] != YENI_SATIR:
            raise SystemExit(f"DUR: {cift} b yeni 02 kirilimi {yeni_s} beklenen {YENI_SATIR} degil")
        r["b"] = dict(kutu=list(kb), kirpim=list(kirp_b), kapilar=kart_kapilari(b_b, taban_a, kb, kirp_b, yeni_s),
                      kayan=[(b, t, k) for b, t, k in yeni_k if b in ("blok1", "blok2")])
        kartlar["b"] = b_b
    ok = r["bilinen_pass"]["PASS"]
    for y, bb in kartlar.items():
        ad = f"{cift}_W05_SUREC.jpg" if uretim else f"{lid}_{cift}_W05_{y}.jpg"
        (out / ad).write_bytes(bb)
        (out / (f"ONCE_SONRA_{cift}.jpg" if uretim else f"ONCE_SONRA_{cift}_{y}.jpg")).write_bytes(once_sonra(taban_b, bb, r[y]["kutu"], y))
        r[y].update(dosya=ad, sha256=hashlib.sha256(bb).hexdigest(), boyut=len(bb))
        k = r[y]["kapilar"]; ok &= k["PASS"]
        if uretim:
            continue
        print(f"::notice::P1-G ornek {cift} {y}: {'PASS' if k['PASS'] else 'FAIL'} | bant p99.9 {k['bant']['p999']} max {k['bant']['max']} | "
              f"OCR eski desen {len(k['ocr'].get('eski_desen') or [])} capa {k['ocr'].get('capa')} difflib {k['ocr'].get('difflib')} | "
              f"metin {'PASS' if k['metin']['PASS'] else 'FAIL'} | jpeg {'PASS' if k['jpeg']['PASS'] else 'FAIL'}")
    f = r["bilgi_canli_kaynak_fark"]
    if uretim:
        return ok
    print(f"::notice::P1-G ornek {cift}: kimlik PASS, canli OCR eski desen {len(r['canli_ocr']['eski_desen'])}; bilgi: canli-kaynak fark "
          f"p99.9 {f['p999']} max {f['max']}, NCC {r['bilgi_ncc']}, canli subsampling {r['canli']['subsampling']}; bilinen PASS {r['bilinen_pass']['PASS']}")
    return ok


def ornek(yedek, kaynak, sonra_kok, ci_kok, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    rapor = dict(yeni_metin=YENI, esik=dict(p999=P999_ESIK, max=MAX_ESIK, difflib=DIFFLIB_ESIK), kutu_b=list(KUTU_B),
                 sapma=("Bant disi fark tabani Drive kaynagi (sha = MANIFEST, eski cizim): CLAUDE.md GALERI 'canli galeriden' kuralindan Serdar "
                        "onayli sapma (5 Kas, A). 'Kaynak canliya karsi fark kapisi' KALDIRILDI (gevseme, Serdar onayi); yerine kesin kimlik "
                        "zinciri (r5 id = SONRA son_ids[W05], yukleme sha256 = MANIFEST) ve canli OCR kapisi. Canli-kaynak fark ve NCC yalniz bilgi."),
                 ciftler={})
    sonuc = True
    for cift, lid in ORNEK:
        r = rapor["ciftler"][cift] = dict(ilan=lid)
        try:
            sonuc &= ornek_cift(r, cift, lid, yedek, kaynak, sonra_kok, ci_kok, out)
        except SystemExit as e:
            r["DUR"] = str(e); sonuc = False
            print(f"::error::P1-G ornek {cift} DUR (RAPOR.json)")
    rapor["SONUC"] = "PASS" if sonuc else "FAIL"
    (out / "RAPOR.json").write_text(json.dumps(rapor, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"P1-G ornek SONUC {rapor['SONUC']} -> {out}")
    return 0 if sonuc else 1


MANIFEST_ALAN = ["cift", "ilan", "dosya", "sha256", "boyut", "kaynak_kosu", "kimlik", "canli_ocr", "bilinen_pass", "bant_p999", "bant_max",
                 "ocr_eski_desen", "capa", "difflib", "metin", "jpeg", "durum", "neden"]


def _uret_is(x):
    """ProcessPool isi: tek cift (b). -> (cift, ilan, r, durum, neden)"""
    cift, lid, yedek, kaynak, sonra_kok, ci_kok, out = x
    r = dict(ilan=lid)
    try:
        ok = ornek_cift(r, cift, lid, yedek, kaynak, sonra_kok, ci_kok, Path(out), yontemler=("b",), uretim=True)
        if "kapilar" not in r.get("b", {}):
            return cift, lid, r, "DUR", r.get("b", {}).get("uretilmedi", "b uretilmedi")
        return cift, lid, r, "PASS" if ok else "FAIL", "" if ok else "kart kapisi FAIL (RAPOR.json)"
    except SystemExit as e:
        return cift, lid, dict(r, DUR=str(e)), "DUR", str(e)[:300]
    except Exception as e:  # noqa: BLE001
        return cift, lid, dict(r, DUR=repr(e)[:300]), "DUR", f"hata {type(e).__name__}: {str(e)[:200]}"


def manifest_satir(cift, lid, r, durum, neden):
    b = r.get("b") or {}; k = b.get("kapilar") or {}
    ev = lambda d: "" if d is None else ("PASS" if d.get("PASS") else "FAIL")  # noqa: E731
    return dict(cift=cift, ilan=lid, dosya=b.get("dosya", ""), sha256=b.get("sha256", ""), boyut=b.get("boyut", ""),
                kaynak_kosu=r.get("kaynak_kosu", ""), kimlik=ev(r.get("kimlik")), canli_ocr=ev(r.get("canli_ocr")),
                bilinen_pass=ev(r.get("bilinen_pass")), bant_p999=(k.get("bant") or {}).get("p999", ""),
                bant_max=(k.get("bant") or {}).get("max", ""), ocr_eski_desen=len((k.get("ocr") or {}).get("eski_desen") or []) if k else "",
                capa=(k.get("ocr") or {}).get("capa", ""), difflib=(k.get("ocr") or {}).get("difflib", ""), metin=ev(k.get("metin")),
                jpeg=ev(k.get("jpeg")), durum=durum, neden=(neden or "")[:300])


def uret(yedek, kaynak, sonra_kok, ci_kok, out, ciftler_csv, isci=None, sadece=""):
    """78 cift (data/pod/pod78_ids.csv) W05 b (Serdar 6 Kas; GALERI istisnasi yalniz W05_SUREC). Kapilar ornek b ile birebir.
    -> 0 = tum ciftler PASS; MANIFEST_W05.csv + RAPOR.json + kartlar + ONCE_SONRA"""
    from concurrent.futures import ProcessPoolExecutor
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    R = [r for r in csv.DictReader(open(ciftler_csv, encoding="utf-8-sig")) if r.get("listing_id", "").strip()]
    sa = {x for x in (sadece or "").split(",") if x}
    if sa - {r["cift"] for r in R}:
        raise SystemExit(f"DUR: sadece listesinde 78 disi cift: {sorted(sa - {r['cift'] for r in R})}")
    R = [r for r in R if not sa or r["cift"] in sa]
    isler = [(r["cift"], r["listing_id"].strip(), str(yedek), str(kaynak), str(sonra_kok), str(ci_kok), str(out)) for r in R]
    rapor = dict(yeni_metin=YENI, yontem="b (wa_s4 yeniden cizim; Serdar 5 Kas secim, 6 Kas uretim)", esik=dict(p999=P999_ESIK, max=MAX_ESIK,
                 difflib=DIFFLIB_ESIK), kutu_b=list(KUTU_B), istisna="CLAUDE.md GALERI kuralina Serdar onayli istisna: yalniz W05_SUREC, yalniz P1-G",
                 sapma=("Bant disi fark tabani Drive kaynagi (sha = MANIFEST = yukleme_kaydi); kaynak-canli fark kapisi yok (Serdar 5 Kas A); "
                        "kimlik zinciri + canli OCR kapi; canli-kaynak fark ve NCC yalniz bilgi."), ciftler={})
    satir, t0 = [], time.time()
    with ProcessPoolExecutor(isci or os.cpu_count() or 2) as ex:
        for n, (cift, lid, r, durum, neden) in enumerate(ex.map(_uret_is, isler), 1):
            rapor["ciftler"][cift] = dict(r, durum=durum)
            satir.append(manifest_satir(cift, lid, r, durum, neden))
            e = time.time() - t0
            print(f"{cift} {durum}" + (f" | {neden[:120]}" if neden else ""), flush=True)
            print(f"ETA uret: {n}/{len(isler)} cift, gecen {e:.0f}s, kalan {e * (len(isler) - n) / n:.0f}s, %{100 * n // len(isler)}", flush=True)
    satir.sort(key=lambda s: s["cift"])
    with open(out / "MANIFEST_W05.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_ALAN); w.writeheader(); w.writerows(satir)
    say = {}
    for s_ in satir:
        say[s_["durum"]] = say.get(s_["durum"], 0) + 1
    rapor.update(sayilar=say, SONUC="PASS" if say.get("PASS", 0) == len(satir) == len(isler) else "FAIL")
    (out / "RAPOR.json").write_text(json.dumps(rapor, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    kotu = [s_["cift"] for s_ in satir if s_["durum"] != "PASS"]
    print(f"::notice::P1-G W05 uretim: {len(satir)} cift | " + " ".join(f"{k} {v}" for k, v in sorted(say.items()))
          + (f" | PASS disi: {' '.join(kotu[:20])}" if kotu else ""))
    return 0 if rapor["SONUC"] == "PASS" else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut", required=True)
    t = alt.add_parser("tara"); t.add_argument("--in", dest="kok", required=True); t.add_argument("--out", required=True)
    t.add_argument("--is", dest="is_", type=int, default=0)
    o = alt.add_parser("ornek")
    for x in ("--yedek", "--kaynak", "--sonra", "--ci", "--out"):
        o.add_argument(x, required=True)
    u = alt.add_parser("uret")
    for x in ("--yedek", "--kaynak", "--sonra", "--ci", "--out"):
        u.add_argument(x, required=True)
    u.add_argument("--ciftler", default=str(BURA.parents[1] / "data" / "pod" / "pod78_ids.csv"))
    u.add_argument("--is", dest="is_", type=int, default=0); u.add_argument("--sadece", default="")
    a = ap.parse_args(argv)
    if a.komut == "uret":
        return uret(a.yedek, a.kaynak, a.sonra, a.ci, a.out, a.ciftler, a.is_ or None, a.sadece)
    if a.komut == "tara":
        return tara(a.kok, a.out, a.is_ or None)
    return ornek(a.yedek, a.kaynak, a.sonra, a.ci, a.out)


if __name__ == "__main__":
    sys.exit(main())
