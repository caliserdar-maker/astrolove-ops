#!/usr/bin/env python3
"""P0.7 / A3 kabul kiyasi v2 (Serdar 23 Eki A3 plani; v1 22 Eki gece: poster birebir piksel varsayimi yanlisti, siparis_uret
gorseli her kosuda yeniden cizer: siparis_uret.py:31,59,75).
ESIT TANIMI (kosulardan ONCE; test bir sonraki turda):
  Kupa: BASKI_*.png ve ONIZLEME_*.jpg ayni ad kumesi, BAYT birebir (sha256); BASKI 2700x1050 (11 oz); OZET.json sonuc PASS ya
    da GOZ ve iki tarafta ayni; PRINTFUL_TASLAK.json iki tarafta esit.
  23 Eki inceleme duzeltmeleri: KAPI.json ust duzey PASS (metin aramasi degil); kupa OZET 'durum'; olcu tablosu olcu.py; 15 oz;
    taban kosulari dogrulanir (SURE.json gpt_ref = ref_eski, siparis.json ayni, KAPI PASS, klasorler ayri); ref_eski != ref_yeni.
  Poster (siparis-giris yeni yol):
    1. kod: --agac-eski / --agac-yeni (motor_gpt git tree hash) birebir esit.
    2. dosya kumesi tam olarak 3: AstroLoveArt_<B1>_<B2>.jpg (7200x10800), _<OLCU>.jpg (OLCU inc x 300 dpi), _2000.jpg (2000x3000);
       iki tarafta ayni adlar; fazla/eksik dosya FAIL (bos klasor sarti: eski testten kalan dosya FAIL verir).
    3. her dosya iki tarafta: boyut, DPI (300), format (JPEG), ICC profili (var/yok ve bayt esit) ayni.
    4. siparis.json: cift, isim1, isim2, tagline, olcu iki tarafta esit. KAPI.json iki tarafta FAIL icermez.
    5. TABAN: ayni ref'in en az 3 kosusu (--taban DIR DIR DIR ...) arasindaki dosya basina en buyuk piksel farki (max |fark|);
       eski-temiz max farki her dosyada TABAN'dan buyuk degil.
  23 Eki ikinci inceleme: TAZELIK (her dosya mtime >= --en-erken; posterde ayrica >= SURE.json is_basi_utc; Drive'da eski
    kosudan kalan dosya sahte PASS vermesin), DB/PW siparis.json 'siparis_olcu' (db_pw_uret.py:110), taban doygun (>= 255) FAIL,
    taban klasorlerinde ayni 3 dosya, kupa OZET tam esit ('drive', 'musteri_mesaji_taslak' haric) + eski/yeni klasor ayri.
  Onizleme: ONIZ_*.jpg uzun kenar 1600, gercek oran (Merkez kontrolu); son onay Serdar.
Kullanim: esit_kiyas.py --tur poster|kupa --eski DIR --yeni DIR --out DIR --en-erken EPOCH
          [--agac-eski H --agac-yeni H --ref-eski R --ref-yeni R --taban D1 D2 D3 ...]"""
import argparse
import hashlib
import itertools
import json
import pathlib
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
# motor_gpt/olcu.py:17-19 (243c9a4) OLCU tablosu, birebir; ana kopya ve onizleme siparis_uret.py:5-6
OLCU = {'8x10': (2400, 3000), '16x20': (4800, 6000), '24x30': (7200, 9000), '11x14': (3300, 4200),
        '12x16': (3600, 4800), '18x24': (5400, 7200), '12x18': (3600, 5400), '16x24': (4800, 7200), '20x30': (6000, 9000),
        '24x36': (7200, 10800), 'A4': (2480, 3508), 'A3': (3508, 4961), 'A2': (4961, 7016)}
ANA, ONIZ = (7200, 10800), (2000, 3000)
KUPA_BASKI = {"11oz": (2700, 1050), "15oz": (2700, 1140)}   # kupa_siparis.py:66-67, :263
OZET_DEGISKEN = ("drive", "musteri_mesaji_taslak")          # kupa_siparis.py:444,480: Drive sonucu / taslak yolu, kosuya bagli
SURE_TOLERANS = 5   # sn: SURE.is_basi_utc ile dosya mtime ayni runner saati


def taze(d, en_erken, taraf, hata, is_basi=None):
    """Klasordeki her dosya bu testin kosusundan mi (rclone Drive modtime'i korur)? Degilse FAIL."""
    alt = max(en_erken, (is_basi or 0) - SURE_TOLERANS)
    eski = [p.name for p in pathlib.Path(d).rglob("*") if p.is_file() and p.stat().st_mtime < alt]
    if not en_erken:
        hata.append(f"{taraf}: --en-erken verilmedi (tazelik kapisi)")
    elif eski:
        hata.append(f"{taraf}: test baslangicindan ONCEKI dosya {sorted(eski)[:5]} (bos klasor sarti)")


def dosyalar(d, desen):
    return {p.relative_to(d).as_posix(): p for p in sorted(pathlib.Path(d).rglob(desen))}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def max_fark(a, b):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return None
    return int(np.abs(np.asarray(ia, np.int16) - np.asarray(ib, np.int16)).max())


def ozellik(p):
    im = Image.open(p)
    dpi = im.info.get("dpi")
    return dict(boyut=list(im.size), format=im.format, dpi=[round(float(x)) for x in dpi] if dpi else None,
                icc=hashlib.sha256(im.info["icc_profile"]).hexdigest()[:16] if im.info.get("icc_profile") else None)


def beklenen_boyut(olcu):
    return OLCU.get(olcu or "")


def json_oku(d, ad):
    k = sorted(pathlib.Path(d).rglob(ad))
    return json.loads(k[0].read_text()) if k else None


def kapi_pass(d):
    """KAPI.json ust duzey PASS true (siparis_kapi.py / kapi_db_pw.py: sonuc['PASS'] = tum kapilar)."""
    k = json_oku(d, "KAPI.json")
    return bool(k) and k.get("PASS") is True


def ref_ayni(a, b):
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def oniz(src, out, ad):
    im = Image.open(src).convert("RGB"); im.thumbnail((1600, 1600))
    im.save(out / f"ONIZ_{ad.replace('/', '_').rsplit('.', 1)[0]}.jpg", quality=90)


def kupa(a, out, R, hata):
    if pathlib.Path(a.eski).resolve() == pathlib.Path(a.yeni).resolve():
        hata.append("eski ve yeni klasor ayni")
    for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
        taze(d, a.en_erken, taraf, hata)
    for desen in ("BASKI_*.png", "ONIZLEME_*.jpg"):
        de, dy = dosyalar(a.eski, desen), dosyalar(a.yeni, desen)
        if not de or set(de) != set(dy):
            hata.append(f"{desen}: ad kumesi farkli ya da bos (eski {len(de)}, yeni {len(dy)})")
        for ad in sorted(set(de) & set(dy)):
            r = dict(bayt_ayni=sha(de[ad]) == sha(dy[ad]), **ozellik(dy[ad])); R["dosya"][ad] = r
            if not r["bayt_ayni"]:
                hata.append(f"{ad}: bayt farkli")
            n = pathlib.Path(ad).name
            if n.startswith("BASKI_"):
                boy = next((k for k in KUPA_BASKI if f"_{k}_" in n), None)
                if boy is None or r["boyut"] != list(KUPA_BASKI[boy]):
                    hata.append(f"{n}: {r['boyut']}, beklenen {KUPA_BASKI.get(boy)} ({boy or 'boy bilinmiyor'})")
            oniz(dy[ad], out, ad)
    for taraf, d in (("eski", a.eski), ("yeni", a.yeni)):
        R[f"ozet_{taraf}"] = [(lambda o: o.get("durum") or o.get("sonuc"))(json.loads(p.read_text()))   # kupa_siparis.py:436,473 'durum'
                              for p in sorted(pathlib.Path(d).rglob("OZET.json"))]
    if not R["ozet_eski"] or R["ozet_eski"] != R["ozet_yeni"] or any(str(x).upper() not in ("PASS", "GOZ") for x in R["ozet_eski"]):
        hata.append(f"OZET sonuc eski {R['ozet_eski']} / yeni {R['ozet_yeni']}")
    oe = [{k: v for k, v in json.loads(p.read_text()).items() if k not in OZET_DEGISKEN} for p in sorted(pathlib.Path(a.eski).rglob("OZET.json"))]
    oy = [{k: v for k, v in json.loads(p.read_text()).items() if k not in OZET_DEGISKEN} for p in sorted(pathlib.Path(a.yeni).rglob("OZET.json"))]
    if oe != oy:
        fark = sorted({k for x, y in zip(oe, oy) for k in set(x) | set(y) if x.get(k) != y.get(k)})
        hata.append(f"OZET.json icerik farkli (alanlar {fark or 'sayi'})")
    pe = [p.read_text() for p in sorted(pathlib.Path(a.eski).rglob("PRINTFUL_TASLAK.json"))]
    py = [p.read_text() for p in sorted(pathlib.Path(a.yeni).rglob("PRINTFUL_TASLAK.json"))]
    if not pe or pe != py:
        hata.append("PRINTFUL_TASLAK.json farkli ya da yok")


def poster(a, out, R, hata):
    if not a.agac_eski or a.agac_eski != a.agac_yeni:
        hata.append(f"kod agaci esit degil ya da verilmedi ({a.agac_eski} / {a.agac_yeni})")
    if not a.ref_eski or not a.ref_yeni or ref_ayni(a.ref_eski, a.ref_yeni):
        hata.append("ref_eski / ref_yeni verilmedi ya da ayni")
    yollar = [pathlib.Path(x).resolve() for x in (a.eski, a.yeni, *a.taban)]
    if len(set(yollar)) != len(yollar):
        hata.append("eski / yeni / taban klasorleri ayri olmali")
    sj = {}
    for taraf, d, ref in (("eski", a.eski, a.ref_eski), ("yeni", a.yeni, a.ref_yeni), *((f"taban{i}", d, a.ref_eski) for i, d in enumerate(a.taban))):
        s = json_oku(d, "siparis.json")
        sj[taraf] = dict({f: s.get(f) for f in ("cift", "isim1", "isim2", "tagline")}, olcu=s.get("olcu") or s.get("siparis_olcu")) \
            if s else None   # MB siparis_uret 'olcu'; DB/PW db_pw_uret.py:110 'siparis_olcu'
        taze(d, a.en_erken, taraf, hata, (json_oku(d, "SURE.json") or {}).get("is_basi_utc"))
        if not (json_oku(d, "SURE.json") or {}).get("is_basi_utc"):
            hata.append(f"{taraf} SURE.json is_basi_utc yok")
        if not kapi_pass(d):
            hata.append(f"{taraf} KAPI.json yok ya da PASS degil")
        if not ref_ayni((json_oku(d, "SURE.json") or {}).get("gpt_ref", ""), ref):
            hata.append(f"{taraf} SURE.json gpt_ref beklenen ref degil")
    if not sj["eski"] or any(v != sj["eski"] for v in sj.values()):
        hata.append("siparis.json (cift/isim/tagline/olcu) taraflar arasinda farkli ya da yok")
    R["siparis"] = {"esit": bool(sj["eski"]) and all(v == sj["eski"] for v in sj.values()), "olcu": (sj["yeni"] or {}).get("olcu")}
    de, dy = dosyalar(a.eski, "AstroLoveArt_*.jpg"), dosyalar(a.yeni, "AstroLoveArt_*.jpg")
    olcu = R["siparis"]["olcu"]
    if len(dy) != 3 or set(de) != set(dy):
        hata.append(f"dosya kumesi: eski {sorted(de)}, yeni {sorted(dy)} (tam 3 ve ayni adlar beklenir)")
    tb = [dosyalar(t, "AstroLoveArt_*.jpg") for t in a.taban]
    if len(tb) < 3:
        hata.append(f"taban icin en az 3 ayni-ref kosusu gerekir ({len(tb)})")
    for i, x in enumerate(tb):
        if set(x) != set(dy):
            hata.append(f"taban{i} dosya kumesi yeni ile ayni degil ({sorted(x)})")
    for ad in sorted(set(de) & set(dy)):
        oe, oy = ozellik(de[ad]), ozellik(dy[ad])
        n = pathlib.Path(ad).name
        bek = ONIZ if n.endswith("_2000.jpg") else beklenen_boyut(olcu) if olcu and n.endswith(f"_{olcu}.jpg") else ANA
        taban = [max_fark(x[ad], y[ad]) for x, y in itertools.combinations(tb, 2) if ad in x and ad in y]
        r = dict(eski=oe, yeni=oy, max_fark=max_fark(de[ad], dy[ad]), taban_max=max(taban) if taban else None,
                 taban_ciftler=taban, beklenen=list(bek) if bek else None)
        R["dosya"][ad] = r
        if oe != oy:
            hata.append(f"{n}: boyut/format/DPI/ICC farkli")
        if bek is None or oy["boyut"] != list(bek):
            hata.append(f"{n}: {oy['boyut']}, beklenen {bek}")
        if oy["format"] != "JPEG" or oy["dpi"] != [300, 300]:
            hata.append(f"{n}: format {oy['format']} dpi {oy['dpi']}")
        if r["max_fark"] is None or r["taban_max"] is None or None in taban or r["max_fark"] > r["taban_max"]:
            hata.append(f"{n}: eski-temiz farki {r['max_fark']} > taban {r['taban_max']}")
        elif r["taban_max"] >= 255:
            hata.append(f"{n}: taban doygun ({r['taban_max']}): piksel kapisi bir sey olcmez")
        oniz(dy[ad], out, ad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tur", choices=["poster", "kupa"], required=True)
    ap.add_argument("--eski", required=True)
    ap.add_argument("--yeni", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--agac-eski", default="")
    ap.add_argument("--agac-yeni", default="")
    ap.add_argument("--taban", nargs="*", default=[])
    ap.add_argument("--ref-eski", default="")
    ap.add_argument("--ref-yeni", default="")
    ap.add_argument("--en-erken", type=int, default=0, help="UTC epoch: test kosularinin ilki baslamadan once (tazelik)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R, hata = dict(tur=a.tur, dosya={}), []
    (kupa if a.tur == "kupa" else poster)(a, out, R, hata)
    R["hata"], R["sonuc"] = hata, ("FAIL" if hata else "PASS")
    (out / "KIYAS.json").write_text(json.dumps(R, ensure_ascii=False, indent=1), encoding="utf-8")
    for ad, r in R["dosya"].items():
        print(f"{pathlib.Path(ad).name}: " + json.dumps({k: v for k, v in r.items() if k != "taban_ciftler"}, ensure_ascii=False))
    print(f"KIYAS {a.tur}: {R['sonuc']} | dosya {len(R['dosya'])} | hata {hata}")
    sys.exit(0 if not hata else 1)


if __name__ == "__main__":
    main()
