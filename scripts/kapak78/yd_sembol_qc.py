#!/usr/bin/env python3
"""YD Y02 sembol tutarlilik QC'si (Merkez 27 Eki onayi; bagimsiz inceleme ORTA bulgusu: Y02 icerigi hicbir kapidan gecmiyordu).
ETSY API YOK, Canva yok, yalniz okur. Girdi: tasima klasoru (<CIFT>_Y02.jpg, 78 cift) + adim 5 yedegi (GALERI.json Botanical bagi).
Iki kontrol, ikisi de ESIKSIZ (siralama kapisi); NCC degerleri raporlanir, sabit esik ancak olcumle ve Serdar onayiyla konur:
  KUCUK_ISARET: Y02'deki sol (a) ve sag (b) burc isaretleri kirpilir (onayli kart yerlesimi, yd_kart_ornek / eski slayt 2 kutulari),
                murekkep kutusuna kirpilir, 96x96'ya oturtulur. Ayni burcun 78 ciftteki ornekleri gruplanir; her ornek 12 burcun
                ortanca (median) goruntuleri icinde en cok KENDI burcuna benzemeli (degilse FAIL). Ayrica kendi grubuna NCC raporlanir.
  ORTAK_SEMBOL: Y02'deki birlesik sembol, o ciftin Botanical posterinde (yedek r12, poster kirpimi) olcek taramali NCC
                (cv2 TM_CCOEFF_NORMED, murekkep haritasi) ile aranir. 78 ciftin Botanical posterleri icinde en yuksek skor KENDI
                cifti olmali (degilse FAIL); kendi skoru, ikinci en yakin cift ve fark raporlanir.
Cikti: QC_SEMBOL_RAPOR.json, OZET.md. Cikis 0 = 78/78 PASS.
Kullanim: yd_sembol_qc.py --kart-dir DIR --yedek DIR --ciftler data/pod/yd78_ids.csv --out DIR"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

ISARET = 96                      # kucuk isaret karsilastirma boyutu (px)
OLCEK = 4                        # ortak sembol aramasi 1/4 cozunurlukte
OLCEKLER = np.linspace(0.6, 2.6, 41)
ARAMA_Y = (0.08, 0.62)           # Botanical posterinde birlesik sembolun arandigi dikey bant (poster yuksekligine oran)


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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kart-dir", required=True); ap.add_argument("--yedek", required=True)
    ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--sadece", default="", help="yerel test: virgullu cift listesi")
    a = ap.parse_args(argv)
    rows = list(csv.DictReader(open(a.ciftler, encoding="utf-8-sig")))
    if a.sadece:
        rows = [r for r in rows if r["cift"] in set(a.sadece.split(","))]
    kd, yd, out = Path(a.kart_dir), Path(a.yedek), Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time(); s = {}; isaret = {}; sab = {}; post = {}
    for n, r in enumerate(rows, 1):                         # 1) okuma: kucuk isaretler, birlesik sembol sablonu, poster haritasi
        c = r["cift"]; s[c] = dict(cift=c, a=r["a"], b=r["b"], neden=[])
        try:
            kart = Image.open(kd / f"{c}_Y02.jpg").convert("RGB")
            for taraf, eid, burc in (("a", "cancer_symbol", r["a"]), ("b", "libra_symbol", r["b"])):
                isaret.setdefault(burc, []).append((c, taraf, kare(murekkep(np.asarray(kutu_kirp(kart, eid).convert("L"), np.float32)))))
            sab[c] = sablon(kart)
            post[c] = poster_harita(botanical(yd / f"{r['listing_id']}_{c}"))
        except (SystemExit, OSError, ValueError) as e:
            s[c]["neden"].append(f"okuma: {e}"[:200])
        if n % 13 == 0 or n == len(rows):
            print(f"[okuma {n}/{len(rows)}] gecen {time.time() - t0:.0f} sn", flush=True)
    medyan = {b: np.median(np.stack([x[2] for x in v]), axis=0) for b, v in isaret.items()}
    for b, v in isaret.items():                             # 2) KUCUK_ISARET: en yakin burc medyani kendi burcu
        for c, taraf, m in v:
            sk = {bb: ncc(m, mm) for bb, mm in medyan.items()}
            yakin = max(sk, key=sk.get); s[c][f"isaret_{taraf}"] = dict(burc=b, kendi_ncc=round(sk[b], 4), en_yakin=yakin,
                                                                         grup_n=len(v), ikinci=round(sorted(sk.values())[-2], 4) if len(sk) > 1 else None)
            if yakin != b:
                s[c]["neden"].append(f"KUCUK_ISARET {taraf} ({b}) en cok {yakin} medyanina benziyor")
    ciftler = [c for c in s if c in sab and c in post]
    for n, c in enumerate(ciftler, 1):                      # 3) ORTAK_SEMBOL: kendi posterinde olcek taramasi, sonra o olcekte 78 poster
        kendi, ol = esle(sab[c], post[c], OLCEKLER)
        dar = [ol * x for x in (0.95, 1.0, 1.05)] if ol else OLCEKLER
        sk = {cc: (kendi if cc == c else esle(sab[c], post[cc], dar)[0]) for cc in ciftler}
        sira = sorted(sk.items(), key=lambda x: -x[1])
        ikinci = next((x for x in sira if x[0] != c), (None, None))
        s[c]["ortak"] = dict(kendi_ncc=round(kendi, 4), olcek=ol, en_yakin=sira[0][0], ikinci=ikinci[0],
                             ikinci_ncc=round(ikinci[1], 4) if ikinci[1] is not None else None,
                             fark=round(kendi - ikinci[1], 4) if ikinci[1] is not None else None)
        if sira[0][0] != c:
            s[c]["neden"].append(f"ORTAK_SEMBOL Botanical posterlerinde en cok {sira[0][0]} posterine uyuyor (kendi {kendi:.3f})")
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
                burc_grup={b: len(v) for b, v in sorted(isaret.items())})
    (out / "QC_SEMBOL_RAPOR.json").write_text(json.dumps(dict(ozet=ozet, ciftler=S), indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# YD Y02 sembol tutarlilik QC\n\nPASS {ozet['pass_']} / {ozet['cift']} | kucuk isaret kendi burc NCC min "
                f"{ozet['isaret_kendi_ncc_min']} | ortak sembol kendi poster NCC min {ozet['ortak_kendi_ncc_min']} | "
                f"kendi - ikinci en yakin fark min {ozet['ortak_fark_min']}\n\n")
        f.write("## FAIL\n" + ("".join(f"- {v['cift']}: {'; '.join(v['neden'])}\n" for v in fail) or "- yok\n"))
        f.write("\n| cift | durum | a isaret NCC | b isaret NCC | ortak kendi | ikinci (cift) | fark |\n|---|---|---|---|---|---|---|\n")
        for v in S:
            o = v.get("ortak", {})
            f.write(f"| {v['cift']} | {v['durum']} | {v.get('isaret_a', {}).get('kendi_ncc', '-')} | {v.get('isaret_b', {}).get('kendi_ncc', '-')} "
                    f"| {o.get('kendi_ncc', '-')} | {o.get('ikinci_ncc', '-')} ({o.get('ikinci', '-')}) | {o.get('fark', '-')} |\n")
    print(f"OZET: {json.dumps(ozet, ensure_ascii=False)}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
