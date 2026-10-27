#!/usr/bin/env python3
"""YD (1st Anniversary) 78 kapak: olcumlu QC (plan v3 adim 4; Merkez 27 Eki). ETSY API YOK, Etsy'ye yazma yok, Canva yok.
Goz kontrolunun yerine; gorsel onayi yalniz Serdar'da (kontak sayfasi Serdar'a gider).

olc    : onayli ornek kapak + o ciftin kaynak gorseli (KAPAK_KAYNAK kaynak_image_id, 2400x3000) -> SABLON.json adayi:
         kutu (kapaktaki poster bolgesi, px), kaynak_kirp (kutuya dusen kaynak bolgesi, px), olcek, NCC. Yontem: 1/4 olcekte kaynagin
         orta parcasi kapakta coklu olcekli NCC ile aranir (cv2.matchTemplate), 1/2 olcekte inceltilir; kaynak kapak duzlemine
         tasinir, |fark| (15 px kutu ortalamasi, Otsu esigi) dusuk olan satir / sutun bandi kutudur. Sablon kutusu Canva'da tum ciftlerde
         ayni (DAHZHemU2a4 kopyalari, yd_ops.py KIRP); 3 onayli ornek + pilot kopyasinda olculur, sapmalar raporlanir.
kontrol: her KAPAK_<CIFT>.jpg (yd78 listesi):
         - JPEG ve 2400x2400 (degilse FAIL)
         - ncc_poster: kapak kutusu <-> kaynak gorselin kaynak_kirp bolgesi (kutu boyuna olceklenir), kutunun ic %96'si, 1/2 olcek
         - ncc_sahne : kapak <-> onay anindaki sablon kapak goruntusu (--sahne-ref), kutu (+ 12 px) ve SABLON maske kutulari
                       (cift satiri) disinda, 1/2 olcek
         - en_yakin  : kutu 1/8 olcekte 78 kaynagin hepsiyle NCC; en yakin kaynak kendi cifti degilse FAIL (esiksiz kapi)
         - metin_kapi: METIN_KAPI.tsv (adim 1) satiri yan yana (durum PASS degilse FAIL)
         Esikler (--esik ESIK.json: poster_min, sahne_min) VERILMEZSE durum OLCUM (PASS yok; yukleme kapisi gecmez). Esikler
         ornekler uzerinde olculup Serdar onayiyla sabitlenir; bu betik esik onermez.
Cikti: QC_RAPOR.json (esik, sablon, dosyalar: dosya, cift, ncc_poster, ncc_sahne, en_yakin, metin_kapi, durum, neden),
       QC_RAPOR.md, KONTAK.jpg (78 kucuk kapak, cift adi + durum; 13 sutun)."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BOYUT = (2400, 2400)
KAYNAK_BOYUT = (2400, 3000)
IC = 0.02          # ncc_poster: kutunun her kenarindan %2 iceride (kenar yumusatmasi / golge)
SAHNE_PAY = 12     # ncc_sahne: kutu disina eklenen pay (px)
OLCEKLER = np.linspace(0.30, 1.10, 81)


def gri(p, olcek=1):
    im = Image.open(p).convert("L")
    if olcek != 1:
        im = im.resize((round(im.width / olcek), round(im.height / olcek)), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32)


def ncc(a, b, m=None):
    a = a.astype(np.float64); b = b.astype(np.float64)
    if m is not None:
        a, b = a[m], b[m]
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else 0.0


def kirp_olcekle(K, kirp, hedef_wh):
    x0, y0, x1, y1 = kirp
    return cv2.resize(K[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))], hedef_wh, interpolation=cv2.INTER_AREA)


def ara(C, S, olcekler):
    """S'nin orta parcasini (satir/sutun %30-%70) C'de olcekler boyunca ara -> (skor, olcek, ox, oy) C pikselinde, S -> C esleme"""
    h, w = S.shape
    py0, py1, px0, px1 = int(h * .3), int(h * .7), int(w * .3), int(w * .7)
    parca = S[py0:py1, px0:px1]
    en = (-2, None, None, None)
    for s in olcekler:
        pw, ph = int(round(parca.shape[1] * s)), int(round(parca.shape[0] * s))
        if pw < 16 or ph < 16 or pw >= C.shape[1] or ph >= C.shape[0]:
            continue
        r = cv2.matchTemplate(C, cv2.resize(parca, (pw, ph), interpolation=cv2.INTER_AREA), cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        if mx > en[0]:
            en = (mx, s, loc[0] - px0 * s, loc[1] - py0 * s)
    return en


def bant(prof, merkez):
    """prof (0-1) > 0.5 olan, merkezi iceren kesintisiz aralik -> (bas, son+1)"""
    if not prof[merkez] > 0.5:
        return None
    a = merkez
    while a > 0 and prof[a - 1] > 0.5:
        a -= 1
    b = merkez
    while b < len(prof) - 1 and prof[b + 1] > 0.5:
        b += 1
    return a, b + 1


def olc(kapak, kaynak):
    C4, S4 = gri(kapak, 4), gri(kaynak, 4)
    sk, s, ox, oy = ara(C4, S4, OLCEKLER)
    if s is None:
        raise SystemExit("olc: eslesme yok")
    C2, S2 = gri(kapak, 2), gri(kaynak, 2)
    ince = np.linspace(s * 0.97, s * 1.03, 13)
    sk, s, ox, oy = ara(C2, S2, ince)                     # 1/2 olcek: C2 = s * S2 + o2
    C = gri(kapak); S = gri(kaynak)
    ox, oy = ox * 2, oy * 2                               # tam cozunurluk (olcek ayni: iki goruntu ayni oranda kucultuldu)
    M = np.float32([[s, 0, ox], [0, s, oy]])
    W = cv2.warpAffine(S, M, (C.shape[1], C.shape[0]), flags=cv2.INTER_AREA, borderValue=-1)
    gecerli = cv2.warpAffine(np.ones_like(S), M, (C.shape[1], C.shape[0]), flags=cv2.INTER_NEAREST, borderValue=0) > 0.5
    D = cv2.blur(np.abs(C - W), (15, 15))
    ic = gecerli & (cv2.erode(gecerli.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0)
    yy, xx = np.nonzero(ic)
    my, mx_ = int(np.median(yy)), int(np.median(xx))
    esik, _ = cv2.threshold(np.clip(D[gecerli], 0, 255).astype(np.uint8).reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dusuk = (D <= esik) & gecerli                         # Otsu: kaynakla ortusen (kutu) / ortusmeyen (sahne) |fark| ayrimi
    bx = bant(dusuk[my - 200:my + 200].mean(axis=0), mx_)
    by = bant(dusuk[:, mx_ - 200:mx_ + 200].mean(axis=1), my)
    if not bx or not by:
        raise SystemExit("olc: poster bandi bulunamadi")
    kutu = [bx[0], by[0], bx[1], by[1]]
    kirp = [float((kutu[0] - ox) / s), float((kutu[1] - oy) / s), float((kutu[2] - ox) / s), float((kutu[3] - oy) / s)]
    R = dict(kutu=kutu, kaynak_kirp=[round(v, 1) for v in kirp], olcek=round(float(s), 5), ofset=[round(float(ox), 1), round(float(oy), 1)],
             eslesme=round(float(sk), 4))
    R["ncc_poster"] = round(ncc_poster(C, S, R), 4)
    return R


def ic_kutu(kutu):
    x0, y0, x1, y1 = kutu
    dx, dy = (x1 - x0) * IC, (y1 - y0) * IC
    return x0 + dx, y0 + dy, x1 - dx, y1 - dy


def kaynak_esle(kutu, kirp, alt):
    """kutunun alt bolgesine (alt) dusen kaynak bolgesi (dogrusal esleme)"""
    sx = (kirp[2] - kirp[0]) / (kutu[2] - kutu[0]); sy = (kirp[3] - kirp[1]) / (kutu[3] - kutu[1])
    return (kirp[0] + (alt[0] - kutu[0]) * sx, kirp[1] + (alt[1] - kutu[1]) * sy,
            kirp[0] + (alt[2] - kutu[0]) * sx, kirp[1] + (alt[3] - kutu[1]) * sy)


def ncc_poster(C, S, sab, olcek=1):
    """C, S ayni olcekte (olcek: kucultme orani); sablon kutulari tam cozunurlukte"""
    a = ic_kutu(sab["kutu"])
    k = kaynak_esle(sab["kutu"], sab["kaynak_kirp"], a)
    a = [v / olcek for v in a]; k = [v / olcek for v in k]
    x0, y0, x1, y1 = (int(round(v)) for v in a)
    P = C[y0:y1, x0:x1]
    return ncc(P, kirp_olcekle(S, k, (P.shape[1], P.shape[0])))


def sahne_maske(sab, shape, olcek):
    m = np.ones(shape, bool)
    for k in [sab["kutu"]] + list(sab.get("maske") or []):
        x0, y0, x1, y1 = k
        pay = SAHNE_PAY if k is sab["kutu"] else 0
        m[max(0, int((y0 - pay) / olcek)):int((y1 + pay) / olcek) + 1, max(0, int((x0 - pay) / olcek)):int((x1 + pay) / olcek) + 1] = False
    return m


def jpeg_kontrol(p):
    if not p.exists():
        return "dosya yok"
    b = p.read_bytes()[:3]
    try:
        with Image.open(p) as im:
            f, bt = im.format, im.size
    except Exception:  # noqa: BLE001
        return "okunamadi"
    if b != b"\xff\xd8\xff" or f != "JPEG":
        return f"JPEG degil ({f})"
    if bt != BOYUT:
        return f"boyut {bt[0]}x{bt[1]} != 2400x2400"
    return ""


def metin_kapi_oku(p):
    if not p:
        return {}
    return {(r.get("cift") or "").strip().upper(): r for r in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter="\t")}


def kontak(satirlar, kapak_dir, out, sutun=13, kenar=180):
    yazi = 34
    satir_n = (len(satirlar) + sutun - 1) // sutun
    K = Image.new("RGB", (sutun * kenar, satir_n * (kenar + yazi)), "white")
    d = ImageDraw.Draw(K)
    try:
        font = ImageFont.load_default(size=12)
    except TypeError:   # eski Pillow
        font = ImageFont.load_default()
    for i, s in enumerate(satirlar):
        x, y = (i % sutun) * kenar, (i // sutun) * (kenar + yazi)
        p = Path(kapak_dir) / s["dosya"]
        if p.exists():
            try:
                with Image.open(p) as im:
                    K.paste(im.convert("RGB").resize((kenar - 4, kenar - 4)), (x + 2, y + 2))
            except Exception:  # noqa: BLE001
                pass
        renk = (0, 120, 0) if s["durum"] == "PASS" else ((160, 0, 0) if s["durum"] == "FAIL" else (90, 90, 90))
        d.text((x + 3, y + kenar), s["cift"].replace("_", " & "), fill=(0, 0, 0), font=font)
        d.text((x + 3, y + kenar + 15), f"{s['durum']} p{s.get('ncc_poster') or '-'} s{s.get('ncc_sahne') or '-'}", fill=renk, font=font)
    K.save(out, quality=88)


def kontrol(a):
    sab = json.loads(Path(a.sablon).read_text(encoding="utf-8"))
    esik = json.loads(Path(a.esik).read_text(encoding="utf-8")) if a.esik else None
    if esik is not None and not all(isinstance(esik.get(k), (int, float)) for k in ("poster_min", "sahne_min")):
        print("::error::ESIK.json poster_min / sahne_min sayi degil"); return 2
    ciftler = [r["cift"] for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("cift")]
    kaynak = {r["cift"]: r for r in csv.DictReader(open(a.kaynak_csv, encoding="utf-8-sig")) if r.get("tur") == "yd"}
    mk = metin_kapi_oku(a.metin_kapi)
    R2 = gri(a.sahne_ref, 2)
    if R2.shape != (BOYUT[1] // 2, BOYUT[0] // 2):
        print("::error::sahne referansi 2400x2400 degil"); return 2
    m2 = sahne_maske(sab, R2.shape, 2)
    # en yakin kaynak: tum kaynaklarin kirp bolgesi 1/8 olcekte (kutu boyunda)
    a8 = [v / 8 for v in ic_kutu(sab["kutu"])]
    k8w, k8h = int(round(a8[2])) - int(round(a8[0])), int(round(a8[3])) - int(round(a8[1]))
    k_ic = kaynak_esle(sab["kutu"], sab["kaynak_kirp"], ic_kutu(sab["kutu"]))
    kucuk = {}
    for c in ciftler:
        p = Path(a.kaynak_dir) / f"{kaynak[c]['kaynak_image_id']}.jpg" if c in kaynak else None
        if p and p.exists():
            S8 = gri(p, 8)
            kucuk[c] = kirp_olcekle(S8, [v / 8 for v in k_ic], (k8w, k8h))
    satir = []
    for n, c in enumerate(ciftler, 1):
        dosya = f"KAPAK_{c}.jpg"; p = Path(a.kapak_dir) / dosya
        s = dict(dosya=dosya, cift=c, ncc_poster=None, ncc_sahne=None, en_yakin=None, en_yakin_ncc=None, metin_kapi=None, durum="", neden=[])
        r = mk.get(c)
        s["metin_kapi"] = dict(design_id=r.get("design_id"), satir_metni=r.get("satir_metni"), durum=r.get("durum")) if r else None
        if a.metin_kapi and (not r or (r.get("durum") or "").strip() != "PASS"):
            s["neden"].append("METIN_KAPI PASS degil")
        e = jpeg_kontrol(p)
        kp = Path(a.kaynak_dir) / f"{kaynak[c]['kaynak_image_id']}.jpg" if c in kaynak else None
        if e:
            s["neden"].append(e)
        elif not kp or not kp.exists() or Image.open(kp).size != KAYNAK_BOYUT:
            s["neden"].append("kaynak gorsel yok / 2400x3000 degil")
        else:
            s["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
            C2 = gri(p, 2)
            s["ncc_poster"] = round(ncc_poster(C2, gri(kp, 2), sab, olcek=2), 4)
            s["ncc_sahne"] = round(ncc(C2, R2, m2), 4)
            x0, y0 = int(round(a8[0])), int(round(a8[1]))
            P8 = gri(p, 8)[y0:y0 + k8h, x0:x0 + k8w]
            skor = {k: ncc(P8, v) for k, v in kucuk.items()}
            s["en_yakin"] = max(skor, key=skor.get); s["en_yakin_ncc"] = round(skor[s["en_yakin"]], 4)
            if s["en_yakin"] != c:
                s["neden"].append(f"poster bolgesi en cok {s['en_yakin']} kaynagina benziyor (kendi cifti degil)")
            if esik is not None:
                if s["ncc_poster"] < esik["poster_min"]:
                    s["neden"].append(f"ncc_poster {s['ncc_poster']} < {esik['poster_min']}")
                if s["ncc_sahne"] < esik["sahne_min"]:
                    s["neden"].append(f"ncc_sahne {s['ncc_sahne']} < {esik['sahne_min']}")
        s["durum"] = "FAIL" if s["neden"] else ("PASS" if esik is not None else "OLCUM")
        satir.append(s)
        print(f"[{n}/{len(ciftler)}] {c} {s['durum']} poster {s['ncc_poster']} sahne {s['ncc_sahne']} en yakin {s['en_yakin']}"
              + (f" | {s['neden'][0]}" if s["neden"] else ""), flush=True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    say = {k: sum(1 for s in satir if s["durum"] == k) for k in ("PASS", "FAIL", "OLCUM")}
    np_ = [s["ncc_poster"] for s in satir if s["ncc_poster"] is not None]
    ns = [s["ncc_sahne"] for s in satir if s["ncc_sahne"] is not None]
    J = dict(esik=esik, esik_kaynagi=a.esik or "yok (OLCUM; PASS yok)", sablon=sab, sahne_ref_sha=hashlib.sha256(Path(a.sahne_ref).read_bytes()).hexdigest(),
             sayilar=say, ncc_poster_min=min(np_) if np_ else None, ncc_sahne_min=min(ns) if ns else None, dosyalar=satir)
    (out / "QC_RAPOR.json").write_text(json.dumps(J, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "QC_RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# YD kapak QC\n\nPASS {say['PASS']} | FAIL {say['FAIL']} | OLCUM {say['OLCUM']} | esik: {J['esik_kaynagi']}\n"
                f"ncc_poster en dusuk {J['ncc_poster_min']} | ncc_sahne en dusuk {J['ncc_sahne_min']} (olcum)\n\n"
                "| cift | durum | ncc_poster | ncc_sahne | en_yakin | metin_kapi | neden |\n|---|---|---|---|---|---|---|\n")
        f.writelines(f"| {s['cift']} | {s['durum']} | {s['ncc_poster']} | {s['ncc_sahne']} | {s['en_yakin']} | "
                     f"{(s['metin_kapi'] or {}).get('satir_metni', '-')} {(s['metin_kapi'] or {}).get('durum', '')} | {'; '.join(s['neden'])} |\n"
                     for s in satir)
    kontak(satir, a.kapak_dir, out / "KONTAK.jpg")
    print(f"QC OZET: PASS {say['PASS']} FAIL {say['FAIL']} OLCUM {say['OLCUM']} | poster min {J['ncc_poster_min']} sahne min {J['ncc_sahne_min']}")
    return 1 if say["FAIL"] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="komut", required=True)
    o = sub.add_parser("olc")
    o.add_argument("--kapak", required=True, action="append"); o.add_argument("--kaynak", required=True, action="append")
    o.add_argument("--out", required=True, help="OLCUM.json (her ornek icin kutu / kirp / olcek / ncc + sapmalar)")
    k = sub.add_parser("kontrol")
    for x in ("--kapak-dir", "--kaynak-dir", "--kaynak-csv", "--ciftler", "--sablon", "--sahne-ref", "--out"):
        k.add_argument(x, required=True)
    k.add_argument("--metin-kapi", default=""); k.add_argument("--esik", default="")
    a = ap.parse_args(argv)
    if a.komut == "olc":
        if len(a.kapak) != len(a.kaynak):
            print("::error::--kapak ve --kaynak sayisi ayni olmali"); return 2
        R = [dict(kapak=Path(c).name, **olc(c, s)) for c, s in zip(a.kapak, a.kaynak)]
        ref = R[0]["kutu"]
        for r in R:
            r["kutu_sapma"] = max(abs(x - y) for x, y in zip(r["kutu"], ref))
        Path(a.out).write_text(json.dumps(dict(olcumler=R), indent=1), encoding="utf-8")
        for r in R:
            print(f"OLC {r['kapak']}: kutu {r['kutu']} kirp {r['kaynak_kirp']} olcek {r['olcek']} eslesme {r['eslesme']} "
                  f"ncc_poster {r['ncc_poster']} sapma {r['kutu_sapma']}")
        return 0
    return kontrol(a)


if __name__ == "__main__":
    sys.exit(main())
