#!/usr/bin/env python3
"""YD Y02 sembol tutarlilik QC'si (Merkez 27 Eki onayi; bagimsiz inceleme ORTA bulgusu: Y02 icerigi hicbir kapidan gecmiyordu).
ETSY API YOK, Canva yok, yalniz okur. Girdi: tasima klasoru (<CIFT>_Y02.jpg, 78 cift) + adim 5 yedegi (GALERI.json Botanical bagi).
Iki kontrol, ikisi de ESIKSIZ (siralama kapisi); NCC degerleri raporlanir, sabit esik ancak olcumle ve Serdar onayiyla konur:
  KUCUK_ISARET: Y02'deki sol (a) ve sag (b) burc isaretleri kirpilir (onayli kart yerlesimi, yd_kart_ornek / eski slayt 2 kutulari),
                murekkep kutusuna kirpilir, 96x96'ya oturtulur. Ayni burcun 78 ciftteki ornekleri gruplanir; her ornek 12 burcun
                ortanca (median) goruntuleri icinde en cok KENDI burcuna benzemeli (degilse FAIL). Ayrica kendi grubuna NCC raporlanir.
  POSTER_ISARET (dis referans; bagimsiz inceleme 27 Eki: KUCUK_ISARET yalniz ic tutarlilik): Botanical posterinde isimlerin ustundeki
                kucuk glifler (sol = a, sag = b; bant olcumu 5 ciftte y 0,63-0,71) 12 burcun Y02 isaret medyan sablonuyla olcek taramali NCC ile
                siralanir; sol bolgede en iyi a, sag bolgede en iyi b olmali (sistematik yer degistirmeyi de yakalar).
  ORTAK_SEMBOL: Y02'deki birlesik sembol, o ciftin Botanical posterinde (yedek r12, poster kirpimi) olcek taramali NCC
                (cv2 TM_CCOEFF_NORMED, murekkep haritasi) ile aranir. 78 ciftin Botanical posterleri icinde en yuksek skor KENDI
                cifti olmali (degilse FAIL); rakipler de TAM olcek taramasiyla olculur (inceleme 27 Eki: dar tarama farki sisiriyordu);
                kendi skoru, ikinci en yakin cift ve fark raporlanir. --ortak-min verilirse kendi skoru alt sinir (Serdar onayli esik).
Cikti: QC_SEMBOL_RAPOR.json, OZET.md. Cikis 0 = 78/78 PASS.
Kullanim: yd_sembol_qc.py --kart-dir DIR --yedek DIR --ciftler data/pod/yd78_ids.csv --out DIR"""
import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

ISARET = 96                      # kucuk isaret karsilastirma boyutu (px)
OLCEK = 4                        # ortak sembol aramasi 1/4 cozunurlukte
OLCEKLER = np.linspace(0.6, 2.6, 41)
ARAMA_Y = (0.06, 0.63)           # birlesik sembol dikey bandi (olcum: 5 ciftte sembol alti 0,591-0,598; glif satiri 0,63'te baslar)
GLIF_Y, GLIF_X = (0.60, 0.74), ((0.12, 0.50), (0.50, 0.88))   # kucuk glif bolgeleri (1/2 olcek; sol a, sag b; olcum 27 Eki)
GLIF_OLCEK = np.linspace(0.7, 1.9, 31)   # 96 px medyan sablona gore (posterde glif ~105 px, 1/2 olcek)


def murekkep(g):
    """gri (float) -> 0..1 murekkep haritasi (kagit medyani 0, en koyu %1 dilim 1)"""
    kag = float(np.median(g)); koyu = float(np.percentile(g, 1))
    return np.clip((kag - g) / max(kag - koyu, 1.0), 0, 1).astype(np.float32)


def kutu_kirp(kart, eid, pay=0.06):
    k = K.kutu(K.el(2, eid)); bw, bh = k[2] - k[0], k[3] - k[1]
    return kart.crop([round(k[0] - pay * bw), round(k[1] - pay * bh), round(k[2] + pay * bw), round(k[3] + pay * bh)])


def kare(m):
    """murekkep haritasi -> murekkep kutusuna kirp, kareye ortala, ISARET x ISARET"""
    ys, xs = np.nonzero(m > 0.3)
    if len(xs) < 50:
        raise SystemExit("isaret bulunamadi")
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    n = max(m.shape) + 8; t = np.zeros((n, n), np.float32)
    y0, x0 = (n - m.shape[0]) // 2, (n - m.shape[1]) // 2; t[y0:y0 + m.shape[0], x0:x0 + m.shape[1]] = m
    return cv2.resize(t, (ISARET, ISARET), interpolation=cv2.INTER_AREA)


def ncc(a, b):
    a = a - a.mean(); b = b - b.mean(); d = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d else 0.0


def sablon(kart):
    """Y02 birlesik sembol -> murekkep kutusuna kirpilmis 1/OLCEK harita"""
    m = murekkep(np.asarray(kutu_kirp(kart, "shared_symbol").convert("L"), np.float32))
    ys, xs = np.nonzero(m > 0.3)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return cv2.resize(m, (max(8, m.shape[1] // OLCEK), max(8, m.shape[0] // OLCEK)), interpolation=cv2.INTER_AREA)


def glif_bolge(p):
    poster = K.poster_kirp(Image.open(p))[0].convert("L")
    m = murekkep(np.asarray(poster.resize((poster.width // 2, poster.height // 2), Image.LANCZOS), np.float32))
    h, w = m.shape; y0, y1 = round(GLIF_Y[0] * h), round(GLIF_Y[1] * h)
    return [m[y0:y1, round(x0 * w):round(x1 * w)] for x0, x1 in GLIF_X]


def poster_harita(p):
    poster = K.poster_kirp(Image.open(p))[0].convert("L")
    poster = poster.resize((poster.width // OLCEK, poster.height // OLCEK), Image.LANCZOS)
    m = murekkep(np.asarray(poster, np.float32))
    return m[round(ARAMA_Y[0] * m.shape[0]):round(ARAMA_Y[1] * m.shape[0])]


def esle(t, P, olcekler):
    """sablon t (olcekler) -> P icinde en iyi (skor, olcek)"""
    en = (-1.0, None)
    for s in olcekler:
        ts = cv2.resize(t, (max(4, round(t.shape[1] * s)), max(4, round(t.shape[0] * s))), interpolation=cv2.INTER_AREA)
        if ts.shape[0] >= P.shape[0] or ts.shape[1] >= P.shape[1]:
            continue
        r = float(cv2.matchTemplate(P, ts, cv2.TM_CCOEFF_NORMED).max())
        if r > en[0]:
            en = (r, float(s))
    return en


def botanical(d):
    g = json.loads((d / "GALERI.json").read_text(encoding="utf-8"))
    rk = {x["listing_image_id"]: x["rank"] for x in g["gorseller"]}
    b = [x["image_id"] for x in g["baglar"] if x.get("property_id") == 513 and x["value"] == "Botanical"]
    if len(b) != 1 or b[0] not in rk:
        raise SystemExit("Botanical bagi yok")
    p = d / f"r{rk[b[0]]}_{b[0]}.jpg"
    if not p.exists():
        raise SystemExit(f"yedekte {p.name} yok")
    return p


_SAB, _POST = {}, {}


def _ortak_skor(is_):
    """(cift, ciftler) -> {cift: skor} (her poster TAM olcek taramasi) + _kendi (skor, olcek)"""
    c, ciftler = is_
    sk = {}
    for cc in ciftler:
        r, ol = esle(_SAB[c], _POST[cc], OLCEKLER)
        sk[cc] = r
        if cc == c:
            sk["_kendi"] = (r, ol)
    return sk


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kart-dir", required=True); ap.add_argument("--yedek", required=True)
    ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--sadece", default="", help="yerel test: virgullu cift listesi")
    ap.add_argument("--is-sayisi", type=int, default=4)
    ap.add_argument("--ortak-min", type=float, default=None, help="ORTAK_SEMBOL kendi NCC alt siniri (yalniz Serdar onayli esikle)")
    a = ap.parse_args(argv)
    rows = list(csv.DictReader(open(a.ciftler, encoding="utf-8-sig")))
    if a.sadece:
        rows = [r for r in rows if r["cift"] in set(a.sadece.split(","))]
    kd, yd, out = Path(a.kart_dir), Path(a.yedek), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); s = {}; isaret = {}; sab = {}; post = {}; ham = {}; glif = {}
    for n, r in enumerate(rows, 1):                         # 1) okuma: kucuk isaretler, birlesik sembol sablonu, poster haritasi
        c = r["cift"]; s[c] = dict(cift=c, a=r["a"], b=r["b"], neden=[])
        try:
            kart = Image.open(kd / f"{c}_Y02.jpg").convert("RGB")
            for taraf, eid, burc in (("a", "cancer_symbol", r["a"]), ("b", "libra_symbol", r["b"])):
                isaret.setdefault(burc, []).append((c, taraf, kare(murekkep(np.asarray(kutu_kirp(kart, eid).convert("L"), np.float32)))))
            sab[c] = sablon(kart)
            bp = botanical(yd / f"{r['listing_id']}_{c}")
            post[c] = poster_harita(bp); glif[c] = glif_bolge(bp)
        except (SystemExit, OSError, ValueError) as e:
            s[c]["neden"].append(f"okuma: {e}"[:200])
        if n % 13 == 0 or n == len(rows):
            print(f"[okuma {n}/{len(rows)}] gecen {time.time() - t0:.0f} sn", flush=True)
    medyan = {b: np.median(np.stack([x[2] for x in v]), axis=0) for b, v in isaret.items()}
    ham = medyan                                            # POSTER_ISARET sablonu: burcun 78 ciftteki medyani (tek bozuk kart zehirlemez)
    for b, v in isaret.items():                             # 2) KUCUK_ISARET: en yakin burc medyani kendi burcu
        for c, taraf, m in v:
            sk = {bb: ncc(m, mm) for bb, mm in medyan.items()}
            yakin = max(sk, key=sk.get); s[c][f"isaret_{taraf}"] = dict(burc=b, kendi_ncc=round(sk[b], 4), en_yakin=yakin,
                                                                         grup_n=len(v), ikinci=round(sorted(sk.values())[-2], 4) if len(sk) > 1 else None)
            if yakin != b:
                s[c]["neden"].append(f"KUCUK_ISARET {taraf} ({b}) en cok {yakin} medyanina benziyor")
    for c, v in s.items():                                  # 3) POSTER_ISARET: poster glifleri 12 burc arasinda kendi burcu
        if c not in glif:
            continue
        for taraf, bolge, burc in (("a", glif[c][0], v["a"]), ("b", glif[c][1], v["b"])):
            sk = {bb: esle(t, bolge, GLIF_OLCEK)[0] for bb, t in ham.items()}
            sira = sorted(sk.items(), key=lambda x: -x[1])
            v[f"poster_isaret_{taraf}"] = dict(burc=burc, kendi=round(sk.get(burc, -1), 4), en_yakin=sira[0][0],
                                               ikinci=round(next(x[1] for x in sira if x[0] != burc), 4))
            if sira[0][0] != burc:
                v["neden"].append(f"POSTER_ISARET {taraf} ({burc}) posterdeki glif en cok {sira[0][0]} isaretine uyuyor")
    print(f"[poster isaret] gecen {time.time() - t0:.0f} sn", flush=True)
    global _SAB, _POST
    _SAB, _POST = sab, post
    ciftler = [c for c in s if c in sab and c in post]
    with ProcessPoolExecutor(max_workers=a.is_sayisi) as ex:   # 4) ORTAK_SEMBOL: kendi + 77 rakip, hepsi TAM olcek taramasi
        for n, (c, sk) in enumerate(zip(ciftler, ex.map(_ortak_skor, [(c, ciftler) for c in ciftler])), 1):
            kendi, ol = sk.pop("_kendi")
            sira = sorted(sk.items(), key=lambda x: -x[1])
            ikinci = next((x for x in sira if x[0] != c), (None, None))
            s[c]["ortak"] = dict(kendi_ncc=round(kendi, 4), olcek=ol, en_yakin=sira[0][0], ikinci=ikinci[0],
                                 ikinci_ncc=round(ikinci[1], 4) if ikinci[1] is not None else None,
                                 fark=round(kendi - ikinci[1], 4) if ikinci[1] is not None else None)
            if sira[0][0] != c:
                s[c]["neden"].append(f"ORTAK_SEMBOL Botanical posterlerinde en cok {sira[0][0]} posterine uyuyor (kendi {kendi:.3f})")
            if a.ortak_min is not None and kendi < a.ortak_min:
                s[c]["neden"].append(f"ORTAK_SEMBOL kendi NCC {kendi:.3f} < {a.ortak_min}")
            if n % 13 == 0 or n == len(ciftler):
                print(f"[ortak {n}/{len(ciftler)}] gecen {time.time() - t0:.0f} sn", flush=True)
    for v in s.values():
        v["durum"] = "FAIL" if v["neden"] or "ortak" not in v else "PASS"
    S = list(s.values()); fail = [v for v in S if v["durum"] != "PASS"]
    oz = lambda k, f: [v[k][f] for v in S if k in v and v[k].get(f) is not None]   # noqa: E731
    ozet = dict(cift=len(S), pass_=len(S) - len(fail), fail=len(fail),
                isaret_kendi_ncc_min=round(min(oz("isaret_a", "kendi_ncc") + oz("isaret_b", "kendi_ncc")), 4),
                ortak_kendi_ncc_min=round(min(oz("ortak", "kendi_ncc")), 4) if oz("ortak", "kendi_ncc") else None,
                ortak_fark_min=round(min(oz("ortak", "fark")), 4) if oz("ortak", "fark") else None,
                poster_isaret_kendi_min=round(min(oz("poster_isaret_a", "kendi") + oz("poster_isaret_b", "kendi")), 4)
                if oz("poster_isaret_a", "kendi") else None,
                poster_isaret_fark_min=round(min([v[k]["kendi"] - v[k]["ikinci"] for v in S for k in ("poster_isaret_a", "poster_isaret_b")
                                                  if k in v]), 4)
                if oz("poster_isaret_a", "kendi") else None,
                burc_grup={b: len(v) for b, v in sorted(isaret.items())})
    (out / "QC_SEMBOL_RAPOR.json").write_text(json.dumps(dict(ozet=ozet, ciftler=S), indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# YD Y02 sembol tutarlilik QC\n\nPASS {ozet['pass_']} / {ozet['cift']} | kucuk isaret kendi burc NCC min "
                f"{ozet['isaret_kendi_ncc_min']} | ortak sembol kendi poster NCC min {ozet['ortak_kendi_ncc_min']} | "
                f"kendi - ikinci en yakin fark min {ozet['ortak_fark_min']} | poster glif kendi burc NCC min {ozet['poster_isaret_kendi_min']}"
                f" (fark min {ozet['poster_isaret_fark_min']})\n\n")
        f.write("## FAIL\n" + ("".join(f"- {v['cift']}: {'; '.join(v['neden'])}\n" for v in fail) or "- yok\n"))
        f.write("\n| cift | durum | a isaret | b isaret | poster glif a (ikinci) | poster glif b (ikinci) | ortak kendi | ikinci (cift) | fark |\n"
                "|---|---|---|---|---|---|---|---|---|\n")
        for v in S:
            o = v.get("ortak", {}); pa = v.get("poster_isaret_a", {}); pb = v.get("poster_isaret_b", {})
            f.write(f"| {v['cift']} | {v['durum']} | {v.get('isaret_a', {}).get('kendi_ncc', '-')} | {v.get('isaret_b', {}).get('kendi_ncc', '-')} "
                    f"| {pa.get('kendi', '-')} ({pa.get('ikinci', '-')}) | {pb.get('kendi', '-')} ({pb.get('ikinci', '-')}) "
                    f"| {o.get('kendi_ncc', '-')} | {o.get('ikinci_ncc', '-')} ({o.get('ikinci', '-')}) | {o.get('fark', '-')} |\n")
    print(f"OZET: {json.dumps(ozet, ensure_ascii=False)}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
