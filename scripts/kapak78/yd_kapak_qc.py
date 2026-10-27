#!/usr/bin/env python3
"""YD (1st Anniversary) 10'lu galeri: olcumlu QC (plan v3 adim 4; Serdar / Merkez 27 Eki). ETSY API YOK, Etsy'ye yazma yok, Canva yok.
Goz kontrolunun yerine; gorsel onayi yalniz Serdar'da (kontak sayfalari Serdar'a gider).
Galeri: Y01 kapak, Y02 sembol, Y03 kisisellestirme, Y04 format (ORTAK), Y05 surec (cifte ozel; Merkez 27 Eki karar d), Y06 Starlit,
Y07 Timeless, Y08 First Page, Y09 Layers, Y10 Botanical. TUM kartlar 3000x2250 (Merkez 27 Eki karar e; Y01 ve Y06-Y10 poster bolgeli).

stil-kaynak: YD_STIL_KAYNAK.csv uretir: yedek BAGLAR.csv (adim 5) + KAPAK_KAYNAK tur=yd -> (cift, kart) -> kaynak gorsel (2400x3000;
         Y01 = KAPAK_KAYNAK kaynak_image_id = Botanical bagi, Y03 Botanical, Y05 Timeless, Y06-Y10 = o stilin bagli gorseli).
olc    : onayli ornek kart + o ciftin kaynak gorseli -> SABLON.json adayi (kart basina): kutu (karttaki poster bolgesi, px),
         kaynak_kirp (kutuya dusen kaynak bolgesi, px), olcek, NCC. Yontem: 1/4 olcekte kaynagin orta parcasi kartta coklu olcekli NCC
         ile aranir (cv2.matchTemplate), 1/2 olcekte inceltilir; kaynak kart duzlemine tasinir, |fark| (15 px kutu ortalamasi, Otsu
         esigi) dusuk olan satir / sutun bandi kutudur. Ayni kartta orneklerin kutu sapmasi raporlanir.
kontrol: 78 x 9 + 1 = 703 dosya (Merkez 27 Eki):
         - her dosya JPEG ve karta gore boyut (degilse FAIL)
         - Y01, Y03, Y05, Y06-Y10 (poster bolgeli; Y03 Botanical, Y05 Timeless, bagimsiz inceleme 27 Eki): ncc_poster (kutu <-> YD_STIL_KAYNAK kaynaginin kaynak_kirp bolgesi, ic %96, 1/2 olcek), ncc_sahne
           (kart <-> onayli ornek ciftin (--sahne-cift, CANCER_LIBRA) ayni karti, kutu + 12 px ve SABLON maske kutulari disinda),
           en_yakin (kutu 1/8 olcekte o kartin 78 kaynagiyla NCC; en yakin kendi cifti degilse FAIL, esiksiz kapi)
         - Y01: METIN_KAPI.tsv (adim 1) satiri yan yana (PASS degilse FAIL)
         - Y06-Y10: en_yakin_stil (ayni ciftin 5 stil kaynagi icinde en yakin kendi stili degilse FAIL)
         - Y02, Y04: yalniz JPEG + boyut (olcum "bicim"); icerik Serdar'in kontak onayinda
         Esikler (--esik ESIK.json: kartlar.<k>.poster_min / sahne_min / sahne_sha) VERILMEZSE durum OLCUM (PASS yok; yukleme kapisi gecmez).
         Esikler ornekler uzerinde olculup Serdar onayiyla sabitlenir; bu betik esik onermez.
Cikti: QC_RAPOR.json (esik, sablon, kart_ozet, dosyalar: dosya, cift, kart_no, ncc_poster, ncc_sahne, en_yakin, sha256, durum, neden),
       QC_RAPOR.md, KONTAK_<NN>.jpg (sayfa basina 13 cift x 10 kart, durum + NCC)."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BOYUT = (3000, 2250)                # Merkez 27 Eki karar e: tum kartlar 4:3
KAYNAK_BOYUT = (2400, 3000)
KARTLAR = tuple(range(1, 11))
ORTAK = (4,)                        # Merkez 27 Eki karar d: Y05 cifte ozel
KART_BOYUT = {k: BOYUT for k in KARTLAR}
NCC_KART = (1, 3, 5, 6, 7, 8, 9, 10)   # poster bolgesi olan kartlar: kapak, Y03 (Botanical) ve Y05 (Timeless; cifte ozel, karar d), 5 stil
STIL_NCC = (6, 7, 8, 9, 10)
STIL_KART = {1: "Botanical", 3: "Botanical", 5: "Timeless", 6: "Starlit", 7: "Timeless", 8: "First Page", 9: "Layers", 10: "Botanical"}


def kart_ad(cift, k):
    return f"ORTAK_Y{k:02d}.jpg" if k in ORTAK else f"{cift}_Y{k:02d}.jpg"
# Ayar degerleri (OLCULMEDI; sahte gorsellerle secildi): IC, SAHNE_PAY, OLCEKLER, bulaniklik 15 / asinma 31 / bant +-200.
# NCC degerlerini etkiler; esikler bunlarla olculur. Ornek olcumunde (olc) kutu sapmasi / NCC raporlanir, degisiklik Serdar onayiyla.
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


def jpeg_kontrol(p, boyut=BOYUT):
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
    if bt != tuple(boyut):
        return f"boyut {bt[0]}x{bt[1]} != {boyut[0]}x{boyut[1]}"
    return ""


def metin_kapi_oku(p):
    """cift -> kapak (Y01) satiri; ayni ciftte PASS satiri varsa o. kart_no sutunu varsa yalniz kart_no 1 satirlari
    (inceleme 27 Eki: baska kartin PASS satiri kapagi gecirmesin)."""
    if not p:
        return {}
    out = {}
    for r in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter="\t"):
        if "kart_no" in r and (r.get("kart_no") or "").strip() != "1":
            continue
        c = (r.get("cift") or "").strip().upper()
        if c not in out or (r.get("durum") or "").strip() == "PASS":
            out[c] = r
    return out


def kontak(satirlar, kapak_dir, out_dir, ciftler, sayfa_cift=13, kenar=150):
    """KONTAK_<NN>.jpg: satir basina bir cift, 10 kart (4 ORTAK), kart altinda durum + NCC."""
    yazi = 30
    try:
        font = ImageFont.load_default(size=11)
    except TypeError:   # eski Pillow
        font = ImageFont.load_default()
    durum = {s["dosya"]: s for s in satirlar}
    yollar = []
    for sy in range(0, len(ciftler), sayfa_cift):
        grup = ciftler[sy:sy + sayfa_cift]
        K = Image.new("RGB", (190 + 10 * kenar, len(grup) * (kenar + yazi)), "white")
        d = ImageDraw.Draw(K)
        for i, c in enumerate(grup):
            y = i * (kenar + yazi)
            d.text((4, y + kenar // 2), c.replace("_", " & "), fill=(0, 0, 0), font=font)
            for k in KARTLAR:
                ad = kart_ad(c, k); x = 190 + (k - 1) * kenar
                p = Path(kapak_dir) / ad
                if p.exists():
                    try:
                        with Image.open(p) as im:
                            im = im.convert("RGB"); im.thumbnail((kenar - 4, kenar - 4)); K.paste(im, (x + 2, y + 2))
                    except Exception:  # noqa: BLE001
                        pass
                s = durum.get(ad) or {}
                renk = (0, 120, 0) if s.get("durum") == "PASS" else ((160, 0, 0) if s.get("durum") == "FAIL" else (90, 90, 90))
                d.text((x + 3, y + kenar), f"Y{k:02d} {s.get('durum', '-')}", fill=renk, font=font)
                if s.get("ncc_poster") is not None:
                    d.text((x + 3, y + kenar + 13), f"p{s['ncc_poster']} s{s['ncc_sahne']}", fill=renk, font=font)
        yol = Path(out_dir) / f"KONTAK_{sy // sayfa_cift + 1:02d}.jpg"; K.save(yol, quality=88); yollar.append(yol)
    return yollar


def stil_kaynak_oku(p):
    """YD_STIL_KAYNAK.csv (listing_id, cift, kart_no, stil, kaynak_image_id, rank, yedek_yol) -> {(cift, kart): satir}"""
    out = {}
    for r in csv.DictReader(open(p, encoding="utf-8-sig")):
        out[(r["cift"], int(r["kart_no"]))] = r
    return out


def kontrol(a):
    sab = json.loads(Path(a.sablon).read_text(encoding="utf-8"))
    if not isinstance(sab.get("kartlar"), dict) or sorted(int(k) for k in sab["kartlar"]) != list(NCC_KART):
        print(f"::error::SABLON.json kartlar {list(NCC_KART)} icin kutu / kaynak_kirp icermiyor"); return 2
    sabk = {int(k): v for k, v in sab["kartlar"].items()}
    esik = json.loads(Path(a.esik).read_text(encoding="utf-8")) if a.esik else None
    if esik is not None:
        try:
            esik = {k: dict(poster_min=float(esik["kartlar"][str(k)]["poster_min"]), sahne_min=float(esik["kartlar"][str(k)]["sahne_min"]),
                            sahne_sha=str(esik["kartlar"][str(k)]["sahne_sha"]))
                    for k in NCC_KART}
        except (KeyError, TypeError, ValueError):
            print("::error::ESIK.json kartlar.<1,3,5,6..10>.poster_min / sahne_min sayi ya da sahne_sha (onayli ornek kartin sha256'si) yok"); return 2
    ciftler = [r["cift"] for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig")) if r.get("cift")]
    if a.sahne_cift not in ciftler:
        print(f"::error::sahne cifti {a.sahne_cift} listede yok"); return 2
    sk = stil_kaynak_oku(a.stil_kaynak)
    mk = metin_kapi_oku(a.metin_kapi)
    kdir = Path(a.kaynak_dir)
    hazir = {}
    for k in NCC_KART:   # sahne referansi (onayli ornek ciftin kendi karti), maske, 1/8 en_yakin kaynaklari
        rp = Path(a.kapak_dir) / kart_ad(a.sahne_cift, k)
        if jpeg_kontrol(rp, KART_BOYUT[k]):
            print(f"::error::sahne referansi {rp.name}: {jpeg_kontrol(rp, KART_BOYUT[k])}"); return 2
        R2 = gri(rp, 2); sb = sabk[k]
        a8 = [v / 8 for v in ic_kutu(sb["kutu"])]
        k8w, k8h = int(round(a8[2])) - int(round(a8[0])), int(round(a8[3])) - int(round(a8[1]))
        k_ic = kaynak_esle(sb["kutu"], sb["kaynak_kirp"], ic_kutu(sb["kutu"]))
        kucuk = {}
        for c in ciftler:
            r = sk.get((c, k))
            p = kdir / r["yedek_yol"] if r else None
            if p and p.exists():
                kucuk[c] = kirp_olcekle(gri(p, 8), [v / 8 for v in k_ic], (k8w, k8h))
        ref_sha = hashlib.sha256(rp.read_bytes()).hexdigest()
        if esik is not None and esik[k]["sahne_sha"] != ref_sha:   # inceleme 27 Eki: referans onayli dosyaya sabit
            print(f"::error::sahne referansi {rp.name} sha256 ESIK.json'daki onayli ornekle ayni degil"); return 2
        stil = {}    # ayni ciftin 5 stil kaynagi bu kartin kirpimiyla (cift ici stil karismasi; inceleme 27 Eki)
        if k in STIL_NCC:
            for c in ciftler:
                for k2 in STIL_NCC:
                    r = sk.get((c, k2))
                    p = kdir / r["yedek_yol"] if r else None
                    if p and p.exists():
                        stil[(c, k2)] = kirp_olcekle(gri(p, 8), [v / 8 for v in k_ic], (k8w, k8h))
        hazir[k] = dict(R2=R2, m2=sahne_maske(sb, R2.shape, 2), a8=a8, wh=(k8w, k8h), kucuk=kucuk, stil=stil, ref_sha=ref_sha)
    satir = []
    isler = [(c, k) for c in ciftler for k in KARTLAR if k not in ORTAK] + [("ORTAK", k) for k in ORTAK]
    for n, (c, k) in enumerate(isler, 1):
        dosya = kart_ad(c, k); p = Path(a.kapak_dir) / dosya
        s = dict(dosya=dosya, cift=c, kart_no=k, ncc_poster=None, ncc_sahne=None, en_yakin=None, en_yakin_ncc=None, metin_kapi=None,
                 durum="", neden=[])
        r = mk.get(c)
        s["metin_kapi"] = dict(design_id=r.get("design_id"), satir_metni=r.get("satir_metni"), durum=r.get("durum")) if r else None
        if a.metin_kapi and k == 1 and (not r or (r.get("durum") or "").strip() != "PASS"):
            s["neden"].append("METIN_KAPI PASS degil")
        e = jpeg_kontrol(p, KART_BOYUT[k])
        if e:
            s["neden"].append(e)
        else:
            s["sha256"] = hashlib.sha256(p.read_bytes()).hexdigest()
        if not e and k in NCC_KART:
            ks = sk.get((c, k)); kp = kdir / ks["yedek_yol"] if ks else None
            if not kp or not kp.exists() or Image.open(kp).size != KAYNAK_BOYUT:
                s["neden"].append("kaynak gorsel (YD_STIL_KAYNAK) yok / 2400x3000 degil")
            else:
                h = hazir[k]; C2 = gri(p, 2)
                s["ncc_poster"] = round(ncc_poster(C2, gri(kp, 2), sabk[k], olcek=2), 4)
                s["ncc_sahne"] = round(ncc(C2, h["R2"], h["m2"]), 4)
                x0, y0 = int(round(h["a8"][0])), int(round(h["a8"][1]))
                P8 = gri(p, 8)[y0:y0 + h["wh"][1], x0:x0 + h["wh"][0]]
                skor = {kk: ncc(P8, v) for kk, v in h["kucuk"].items()}
                s["en_yakin"] = max(skor, key=skor.get); s["en_yakin_ncc"] = round(skor[s["en_yakin"]], 4)
                if s["en_yakin"] != c:
                    s["neden"].append(f"poster bolgesi en cok {s['en_yakin']} kaynagina benziyor (kendi cifti degil)")
                if k in STIL_NCC:
                    ss = {k2: ncc(P8, h["stil"][(c, k2)]) for k2 in STIL_NCC if (c, k2) in h["stil"]}
                    if ss:
                        s["en_yakin_stil"] = max(ss, key=ss.get)
                        if s["en_yakin_stil"] != k:
                            s["neden"].append(f"poster bolgesi en cok Y{s['en_yakin_stil']:02d} stil kaynagina benziyor (cift ici stil karismasi)")
                if esik is not None:
                    if s["ncc_poster"] < esik[k]["poster_min"]:
                        s["neden"].append(f"ncc_poster {s['ncc_poster']} < {esik[k]['poster_min']}")
                    if s["ncc_sahne"] < esik[k]["sahne_min"]:
                        s["neden"].append(f"ncc_sahne {s['ncc_sahne']} < {esik[k]['sahne_min']}")
        s["olcum"] = "ncc" if k in NCC_KART else "bicim"   # Y02, Y04: yalniz JPEG + boyut; icerik Serdar'in kontak onayinda
        s["durum"] = "FAIL" if s["neden"] else ("PASS" if esik is not None else "OLCUM")
        satir.append(s)
        if n % 50 == 0 or s["neden"] or n == len(isler):
            print(f"[{n}/{len(isler)}] {dosya} {s['durum']} poster {s['ncc_poster']} sahne {s['ncc_sahne']} en yakin {s['en_yakin']}"
                  + (f" | {s['neden'][0]}" if s["neden"] else ""), flush=True)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    say = {k: sum(1 for s in satir if s["durum"] == k) for k in ("PASS", "FAIL", "OLCUM")}
    kart_ozet = {}
    for k in NCC_KART:
        npk = [s["ncc_poster"] for s in satir if s["kart_no"] == k and s["ncc_poster"] is not None and s["cift"] != a.sahne_cift]
        nsk = [s["ncc_sahne"] for s in satir if s["kart_no"] == k and s["ncc_sahne"] is not None and s["cift"] != a.sahne_cift]
        kart_ozet[str(k)] = dict(ncc_poster_min=min(npk) if npk else None, ncc_sahne_min=min(nsk) if nsk else None, n=len(npk))
    J = dict(esik=esik, esik_kaynagi=a.esik or "yok (OLCUM; PASS yok)", sablon=sab, sahne_cift=a.sahne_cift,
             sahne_ref_sha={str(k): h["ref_sha"] for k, h in hazir.items()}, sayilar=say, kart_ozet=kart_ozet,
             beklenen=len(isler), dosyalar=satir)
    (out / "QC_RAPOR.json").write_text(json.dumps(J, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "QC_RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# YD galeri QC\n\ndosya {len(isler)} | PASS {say['PASS']} | FAIL {say['FAIL']} | OLCUM {say['OLCUM']} | esik: {J['esik_kaynagi']}\n"
                f"sahne referansi: {a.sahne_cift} kartlari (onayli ornek; kendi NCC'si en dusuk degerlere katilmaz)\n\n"
                "| kart | ncc_poster en dusuk | ncc_sahne en dusuk | n |\n|---|---|---|---|\n"
                + "".join(f"| Y{int(k):02d} | {v['ncc_poster_min']} | {v['ncc_sahne_min']} | {v['n']} |\n" for k, v in kart_ozet.items())
                + "\n| dosya | durum | ncc_poster | ncc_sahne | en_yakin | metin_kapi | neden |\n|---|---|---|---|---|---|---|\n")
        f.writelines(f"| {s['dosya']} | {s['durum']} | {s['ncc_poster']} | {s['ncc_sahne']} | {s['en_yakin']} | "
                     f"{((s['metin_kapi'] or {}).get('satir_metni') or '-') if s['kart_no'] == 1 else ''} | {'; '.join(s['neden'])} |\n"
                     for s in satir)
    kontak(satir, a.kapak_dir, out, ciftler)
    print(f"QC OZET: dosya {len(isler)} PASS {say['PASS']} FAIL {say['FAIL']} OLCUM {say['OLCUM']} | "
          + " ".join(f"Y{int(k):02d} p{v['ncc_poster_min']} s{v['ncc_sahne_min']}" for k, v in kart_ozet.items()))
    return 1 if say["FAIL"] else 0


def stil_kaynak_uret(baglar, kaynak_csv, ciftler, out):
    """YD_STIL_KAYNAK.csv: yedek BAGLAR.csv (adim 5) + KAPAK_KAYNAK tur=yd. Kart 1 = KAPAK_KAYNAK kaynak_image_id (Botanical);
    6-10 = Style bagli gorsel (Starlit, Timeless, First Page, Layers, Botanical). yedek_yol = <ilan>_<CIFT>/r<rank>_<id>.jpg"""
    kk = {r["cift"]: r for r in csv.DictReader(open(kaynak_csv, encoding="utf-8-sig")) if r.get("tur") == "yd"}
    bag = {}
    for r in csv.DictReader(open(baglar, encoding="utf-8-sig")):
        bag[(r["cift"], r["stil"])] = r
    rows, hata = [], []
    for c in [r["cift"] for r in csv.DictReader(open(ciftler, encoding="utf-8-sig")) if r.get("cift")]:
        for k, stil in STIL_KART.items():
            b = bag.get((c, stil))
            if not b or not b.get("rank"):
                hata.append(f"{c} {stil} bagi yok"); continue
            if k == 1 and (c not in kk or kk[c]["kaynak_image_id"] != b["image_id"]):
                hata.append(f"{c} kapak kaynagi KAPAK_KAYNAK ile Botanical bagi ayni degil"); continue
            rows.append(dict(listing_id=b["listing_id"], cift=c, kart_no=k, stil=stil, kaynak_image_id=b["image_id"], rank=b["rank"],
                             yedek_yol=f"{b['listing_id']}_{c}/r{b['rank']}_{b['image_id']}.jpg"))
    if hata:
        for h in hata[:10]:
            print(f"::error::{h}")
        return 2
    with open(out, "w", newline="", encoding="utf-8") as f:   # LF (inceleme 27 Eki: CRLF bash okumasinda yola \r ekliyordu)
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n"); w.writeheader(); w.writerows(rows)
    print(f"YD_STIL_KAYNAK: {len(rows)} satir ({len(rows) // len(STIL_KART)} cift x {len(STIL_KART)} kart) -> {out}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="komut", required=True)
    o = sub.add_parser("olc")
    o.add_argument("--kart", required=True, action="append", type=int)
    o.add_argument("--kapak", required=True, action="append"); o.add_argument("--kaynak", required=True, action="append")
    o.add_argument("--out", required=True, help="OLCUM.json (her ornek icin kart / kutu / kirp / olcek / ncc + kart icinde sapma)")
    k = sub.add_parser("kontrol")
    for x in ("--kapak-dir", "--kaynak-dir", "--stil-kaynak", "--ciftler", "--sablon", "--out"):
        k.add_argument(x, required=True)
    k.add_argument("--sahne-cift", default="CANCER_LIBRA", help="onayli ornek cift (Serdar 27 Eki); kartlari sahne referansi")
    k.add_argument("--metin-kapi", default=""); k.add_argument("--esik", default="")
    u = sub.add_parser("stil-kaynak")
    for x in ("--baglar", "--kaynak-csv", "--ciftler", "--out"):
        u.add_argument(x, required=True)
    a = ap.parse_args(argv)
    if a.komut == "olc":
        if not len(a.kapak) == len(a.kaynak) == len(a.kart):
            print("::error::--kart, --kapak ve --kaynak sayisi ayni olmali"); return 2
        R = [dict(kart=k, kapak=Path(c).name, **olc(c, s)) for k, c, s in zip(a.kart, a.kapak, a.kaynak)]
        for r in R:
            ref = next(x for x in R if x["kart"] == r["kart"])["kutu"]
            r["kutu_sapma"] = max(abs(x - y) for x, y in zip(r["kutu"], ref))
        Path(a.out).write_text(json.dumps(dict(olcumler=R), indent=1), encoding="utf-8")
        for r in R:
            print(f"OLC Y{r['kart']:02d} {r['kapak']}: kutu {r['kutu']} kirp {r['kaynak_kirp']} olcek {r['olcek']} eslesme {r['eslesme']} "
                  f"ncc_poster {r['ncc_poster']} sapma {r['kutu_sapma']}")
        return 0
    if a.komut == "stil-kaynak":
        return stil_kaynak_uret(a.baglar, a.kaynak_csv, a.ciftler, a.out)
    return kontrol(a)


if __name__ == "__main__":
    sys.exit(main())
