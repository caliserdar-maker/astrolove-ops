#!/usr/bin/env python3
"""1st Anniversary (YD) Starlit 12x18 ORNEK 3 (Merkez 31 Eki, Serdar karari a: yeni yuksek cozunurluklu zemin). ETSY YOK, toplu uretim yok.
Kural (Serdar 31 Eki): hicbir oge tek yonde uzatilmaz / basilmaz; yalniz esit oranli olcek; desen kopyasi / aynalama yok; urun sembolu yapay
zekadan gecmez (Real-ESRGAN YALNIZ zemin dokusuna uygulanir).
Adimlar (12x18 = 3600x5400, 300 dpi; 8x10 karsilastirma 2400x3000 ayni ayarlarla):
  1) zemin: Canva Starlit 2:3 doku (2400x3600, TEMP/YD_ZEMIN_YENI/1_Starlit_2x3_kaynak.png). 12x18: Real-ESRGAN x2plus (resmi agirlik,
     spandrel ile, CPU, karolu) 4800x7200 -> esit olcekle 3600x5400 (INTER_AREA). 8x10: kaynagin ortasindan 2400x3000 (olcek yok).
  2) ince cerceve: 8x10 zeminindeki cizginin OLCULEN profili (renk, kalinlik) ile kodla; dort kenar payi ESIT = 8x10 yan payi (89 px @2400)
     x olcek (12x18: 1.5 -> 134 px). (8x10'da ust / alt pay 56 / 48 idi; Merkez: dort kenar esit.)
  3) yay: 8x10 cemberi (merkez 1187,1251, yaricap 936 @2400; bagimsiz inceleme olcumu 31 Eki) esit olcekle, alt aciklik 60-120 derece
     (olculen bos aci araligi) kodla tam daire yayi; profil (tepe parlaklik, kalinlik, renk) 8x10 zemindeki yaydan olculur; uclar yumusak.
  4) tepe buyuk yildiz isiltisi: 8x10 zeminden kesilir (yerel zemin cikarilip yalniz isik katmani, toplamali), esit olcekle ayni yere.
  5) sembol, burc isaretleri, isimler, baslik, tarih: by_poster (KOD_REF, degistirilmeden) 8x10 yerlesiminin esit olcekli hali, dikeyde
     ortali (12x18'de 8x10 blok 3600x4500, ust / alt 450 px). 12x18: by_poster SCALE=BY_SCALE (vars. 2: 4800x6000) cizilir, esit olcekle 3600x4500'e (INTER_AREA)
     -> 3600x4500; yalniz ogelerin degistirdigi pikseller (fark > 2, 3 px yumusak maske) zemine aktarilir (zemin bit duzeyinde korunur).
Kullanim: by_ornek3.py --kod <bizim-yilimiz> --zemin <2:3 png> --esrgan <x2plus.pth> --out <dir> [--pair CANCER_LIBRA --n1 EMMA --n2 JAMES]"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ESKI = "z/Baski_2400x3000_Buyutulmus/1_Starlit_8x10_300ppi.png"
YAY = dict(cx=1187.0, cy=1251.0, r=936.0, bos=(60.0, 120.0))     # @2400x3000 (31 Eki olcum)
CERCEVE_PAY = 89                                                   # @2400 yan pay (31 Eki olcum: 89 / 90)
YILDIZ = (1040, 180, 1340, 480)
BY_SCALE = int(os.environ.get("BY_SCALE", "2"))                    # by_poster cizim olcegi (12x18 icin sonra esit olcekle 3600x4500)                                    # @2400 tepe yildiz kirpim kutusu (x0, y0, x1, y1)


# ---------------------------------------------------------------- Real-ESRGAN (yalniz zemin)
def esrgan(img, agirlik, karo=384, pay=24):
    import torch
    from spandrel import ModelLoader
    torch.set_num_threads(os.cpu_count() or 4)
    m = ModelLoader().load_from_file(agirlik).eval()
    s = m.scale
    a = img.astype(np.float32) / 255.0
    H, W = a.shape[:2]
    out = np.zeros((H * s, W * s, 3), np.float32)
    n = 0
    top = ((H + karo - 1) // karo) * ((W + karo - 1) // karo)
    for y in range(0, H, karo):
        for x in range(0, W, karo):
            y0, x0 = max(0, y - pay), max(0, x - pay)
            y1, x1 = min(H, y + karo + pay), min(W, x + karo + pay)
            t = torch.from_numpy(a[y0:y1, x0:x1].transpose(2, 0, 1)[None])
            with torch.no_grad():
                r = m(t)[0].numpy().transpose(1, 2, 0)
            yy, xx = (y - y0) * s, (x - x0) * s
            hh, ww = min(karo, H - y) * s, min(karo, W - x) * s
            out[y * s:y * s + hh, x * s:x * s + ww] = r[yy:yy + hh, xx:xx + ww]
            n += 1
            if n % 20 == 0 or n == top:
                print(f"ESRGAN {n}/{top} karo", flush=True)
    return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), s


# ---------------------------------------------------------------- 8x10 zeminden olcum
def olc(eski):
    a = eski.astype(np.float32)
    g = a.mean(2)
    # cerceve: sol kenar dikey cizgi, satir 1000-2000, x 70-110
    p = g[1000:2000, 70:110].mean(0); z = np.median(p[:8])
    i = int(np.argmax(p)); prof = p - z
    yar = np.where(prof >= prof[i] / 2)[0]
    cer_renk = a[1000:2000, 70 + i].mean(0); cer_zemin = a[1000:2000, 70:76].reshape(-1, 3).mean(0)
    cer = dict(x=70 + i, fwhm=float(yar.max() - yar.min() + 1), renk=cer_renk.tolist(), zemin=cer_zemin.tolist(),
               opaklik=float(np.clip((cer_renk - cer_zemin).sum() / max(1.0, (np.array([235, 215, 170]) - cer_zemin).sum()), 0, 1)))
    # yay: 0 ve 180 derecede radyal profil (parlak ve temiz kisimlar)
    pr, rk = [], []
    for ang in (0.0, 180.0, 200.0, 340.0):
        t = np.radians(ang); v = []
        for d in np.arange(-15, 16):
            x = YAY["cx"] + (YAY["r"] + d) * np.cos(t); y = YAY["cy"] + (YAY["r"] + d) * np.sin(t)
            v.append(a[int(round(y)), int(round(x))])
        v = np.array(v); gv = v.mean(1); pr.append(gv); rk.append(v[int(np.argmax(gv))])
    pr = np.array(pr); zz = np.median(pr[:, :5]); tepe = pr.max(1) - zz
    yar = [np.where(p - zz >= (p.max() - zz) / 2)[0] for p in pr]
    yay = dict(fwhm=float(np.median([y.max() - y.min() + 1 for y in yar])), tepe_renk=np.median(np.array(rk), 0).tolist(),
               tepe_fark=float(np.median(tepe)))
    return dict(cerceve=cer, yay=yay)


# ---------------------------------------------------------------- cizim (esit olcek k = genislik / 2400)
def cerceve(img, k, o):
    H, W = img.shape[:2]
    pay = round(CERCEVE_PAY * k)
    sig = max(0.6, o["cerceve"]["fwhm"] * k / 2.355)
    m = np.zeros((H, W), np.float32)
    cv2.rectangle(m, (pay, pay), (W - 1 - pay, H - 1 - pay), 1.0, 1, lineType=cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), sig); m /= max(m.max(), 1e-6)
    renk = np.array(o["cerceve"]["renk"], np.float32); zem = np.array(o["cerceve"]["zemin"], np.float32)
    ek = (renk - zem)[None, None]                                    # olculen fark katmani (toplamali; zemin dokusu korunur)
    out = img.astype(np.float32) + m[..., None] * ek
    return np.clip(out, 0, 255).astype(np.uint8), dict(pay_px=pay, sigma=round(sig, 2))


def yay(img, k, oy, o):
    H, W = img.shape[:2]
    cx, cy, r = YAY["cx"] * k, YAY["cy"] * k + oy, YAY["r"] * k
    sig = max(0.8, o["yay"]["fwhm"] * k / 2.355)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy) - r
    ang = (np.degrees(np.arctan2(yy - cy, xx - cx)) + 360) % 360
    b0, b1 = YAY["bos"]
    # aciklik kenarinda 12 derecelik yumusak sonum (8x10'daki yay uclari gibi incelir)
    uz = np.minimum(np.abs(((ang - b0 + 180) % 360) - 180), np.abs(((ang - b1 + 180) % 360) - 180))
    icerde = (ang > b0) & (ang < b1)
    sonum = np.where(icerde, 0.0, np.clip(uz / 12.0, 0, 1))
    cekirdek = np.exp(-0.5 * (d / sig) ** 2)
    hale = 0.18 * np.exp(-0.5 * (d / (sig * 6)) ** 2)                 # hafif isik halesi
    m = (cekirdek + hale) * sonum
    renk = np.array(o["yay"]["tepe_renk"], np.float32)
    out = img.astype(np.float32)
    out = out + m[..., None] * (renk[None, None] - out) * 0.92
    return np.clip(out, 0, 255).astype(np.uint8), dict(merkez=[round(cx, 1), round(cy, 1)], r=round(r, 1), sigma=round(sig, 2))


def yildiz(img, k, oy, eski):
    x0, y0, x1, y1 = YILDIZ
    p = eski[y0:y1, x0:x1].astype(np.float32)
    zem = cv2.medianBlur(eski[y0:y1, x0:x1], 31).astype(np.float32)    # yerel zemin (yildiz ince: medyan onu siler)
    isik = np.clip(p - zem, 0, 255)
    isik[isik.max(2) < 6] = 0                                           # doku gurultusu disarida
    w, h = round((x1 - x0) * k), round((y1 - y0) * k)
    isik = cv2.resize(isik, (w, h), interpolation=cv2.INTER_CUBIC if k > 1 else cv2.INTER_AREA)
    X, Y = round(x0 * k), round(y0 * k + oy)
    out = img.astype(np.float32)
    out[Y:Y + h, X:X + w] = 255 - (255 - out[Y:Y + h, X:X + w]) * (255 - np.clip(isik, 0, 255)) / 255   # ekran karisimi
    return np.clip(out, 0, 255).astype(np.uint8), dict(kutu=[X, Y, X + w, Y + h])


# ---------------------------------------------------------------- by_poster ogeleri
def by_poster(kod, scale, pair, n1, n2):
    os.environ.update(BY_ROOT=str(kod), PAIR=pair, NAME1=n1, NAME2=n2, DATE="12 JUNE 2025", HEADING="Paper Anniversary", LINE="",
                      SCALE=str(scale), STYLE="1", OUT="/tmp/_by_ornek3")
    spec = importlib.util.spec_from_file_location(f"by_poster_s{scale}", Path(kod, "kod", "by_poster.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    asil = m.gold_layer

    def gold_layer(tex, k=1.0):
        """by_poster.gold_layer ile ayni; YALNIZ doku ortalamasi SCALE'den bagimsiz (31 Eki olcum: by_poster float32
        'a.reshape(-1, 3).mean(0)' SCALE 2'de 28,8 M pikselde R ortalamasini 149 buluyor (SCALE 1: 231,6; float64 dogru deger 224,4)
        -> SCALE 2'de altin koyu / zeytin). Onayli 8x10 gorunumu icin SCALE 1'deki deger kullanilir. by_poster.py degistirilmedi."""
        t = np.array(Image.open(tex).convert("RGB"))
        if m.SCALE > 1:
            t = cv2.resize(t, None, fx=m.SCALE, fy=m.SCALE, interpolation=cv2.INTER_CUBIC)
        tile = np.concatenate([np.concatenate([t, t[:, ::-1]], 1), np.concatenate([t[::-1], t[::-1, ::-1]], 1)], 0)
        reps = (m.H // tile.shape[0] + 1, m.W // tile.shape[1] + 1, 1)
        a = np.tile(tile, reps)[:m.H, :m.W].astype(np.float32)
        low = cv2.GaussianBlur(a, (0, 0), m.P(60)) + 1e-3
        # ortalama, onayli 8x10 (SCALE 1) ciktisinin kullandigi degerin AYNISI: 2400x3000 dosemede by_poster'in float32 ortalamasi
        t1 = np.array(Image.open(tex).convert("RGB"))
        d1 = np.concatenate([np.concatenate([t1, t1[:, ::-1]], 1), np.concatenate([t1[::-1], t1[::-1, ::-1]], 1)], 0)
        a1 = np.tile(d1, (3000 // d1.shape[0] + 1, 2400 // d1.shape[1] + 1, 1))[:3000, :2400].astype(np.float32)
        mean = a1.reshape(-1, 3).mean(0)
        a = np.clip(a / low, 0.6, 1.6) * (0.75 * mean + 0.25 * low) * np.array(k if isinstance(k, tuple) else (k, k, k), np.float32)
        return np.clip(a, 0, 255)
    if scale == 1:
        g1, g2 = asil, gold_layer
        tx = f"{m.Z}/Altin_1024x1024/1_Starlit_Altin_1024.png"
        if np.abs(g1(tx) - g2(tx)).max() > 0.5:
            raise SystemExit("DUR: gold_layer kopyasi SCALE 1'de by_poster'dan farkli")
    m.gold_layer = gold_layer
    return m


def ogeler(bp, blok):
    """blok: HxW (by_poster W,H) zemin -> ogeler cizilmis hali"""
    bp.bgimg = lambda name: Image.fromarray(blok)
    return np.asarray(bp.starlit().convert("RGB"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True); ap.add_argument("--zemin", required=True); ap.add_argument("--esrgan", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--n1", default="EMMA"); ap.add_argument("--n2", default="JAMES")
    ap.add_argument("--esrgan-hazir", default="", help="onceden buyutulmus 3600x5400 zemin (yerel deneme)")
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    kaynak = np.asarray(Image.open(a.zemin).convert("RGB"))
    if kaynak.shape[:2] != (3600, 2400):
        raise SystemExit(f"DUR: zemin kaynagi {kaynak.shape[1]}x{kaynak.shape[0]} (2400x3600 beklenir)")
    eski = np.asarray(Image.open(Path(a.kod, ESKI)).convert("RGB"))
    o = olc(eski)
    rap = dict(olcum_8x10=o, kaynak=dict(boyut=[2400, 3600]))
    # ---- 12x18
    if a.esrgan_hazir:
        z12 = np.asarray(Image.open(a.esrgan_hazir).convert("RGB")); s = 2
    else:
        z2, s = esrgan(kaynak, a.esrgan)
        z12 = cv2.resize(z2, (3600, 5400), interpolation=cv2.INTER_AREA)       # esit olcek (x ve y ayni oran)
        # ESRGAN kapisi: (a) geri kucultulunce kaynaga sadik (ortalama mutlak fark), (b) karo sinirinda dikis yok (sinir satir / sutun
        # gradyani komsu satirlarin medyanina gore)
        geri = cv2.resize(z2, (2400, 3600), interpolation=cv2.INTER_AREA).astype(np.float32)
        ort = float(np.abs(geri - kaynak.astype(np.float32)).mean())
        g = z2.astype(np.float32).mean(2)
        dy = np.abs(np.diff(g, axis=0)).mean(1); dx = np.abs(np.diff(g, axis=1)).mean(0)
        sin_y = [dy[y * s - 1] / max(np.median(dy[y * s - 6:y * s + 5]), 1e-3) for y in range(384, 3600, 384)]
        sin_x = [dx[x * s - 1] / max(np.median(dx[x * s - 6:x * s + 5]), 1e-3) for x in range(384, 2400, 384)]
        dikis = float(max(sin_y + sin_x))
        rap["esrgan_kapi"] = dict(geri_ort_fark=round(ort, 3), karo_siniri_en_buyuk_oran=round(dikis, 3),
                                  pass_=ort <= 3.0 and dikis <= 1.5)
        if not rap["esrgan_kapi"]["pass_"]:
            raise SystemExit(f"DUR: ESRGAN kapisi {rap['esrgan_kapi']}")
    Image.fromarray(z12).save(out / "ZEMIN_12x18_esrgan.png")
    k, oy = 1.5, 450
    z, rc = cerceve(z12, k, o); z, ry = yay(z, k, oy, o); z, rs = yildiz(z, k, oy, eski)
    bp = by_poster(a.kod, BY_SCALE, a.pair, a.n1, a.n2)
    blok = z[oy:oy + 4500]
    buyuk = cv2.resize(blok, (2400 * BY_SCALE, 3000 * BY_SCALE), interpolation=cv2.INTER_LANCZOS4)
    ciz = cv2.resize(ogeler(bp, buyuk), (3600, 4500), interpolation=cv2.INTER_AREA)
    geri = cv2.resize(buyuk, (3600, 4500), interpolation=cv2.INTER_AREA)
    fark = (np.abs(ciz.astype(np.int16) - geri.astype(np.int16)).max(2) > 2).astype(np.float32)
    mk = cv2.GaussianBlur(cv2.dilate(fark, np.ones((5, 5), np.uint8)), (0, 0), 1.5)[..., None]
    son = z.copy()
    son[oy:oy + 4500] = np.clip(blok * (1 - mk) + ciz * mk, 0, 255).astype(np.uint8)
    Image.fromarray(son).save(out / "STARLIT_12x18.jpg", quality=95, subsampling=0, dpi=(300, 300))
    rap["12x18"] = dict(boyut=[3600, 5400], esrgan_olcek=s, esit_olcek=k, dikey_ofset=oy, cerceve=rc, yay=ry, yildiz=rs,
                        oge_alani_px=int((fark > 0).sum()))
    # ---- 8x10 (ayni ayarlar, olcek 1)
    z8 = kaynak[300:3300].copy()
    z8, rc8 = cerceve(z8, 1.0, o); z8, ry8 = yay(z8, 1.0, 0, o); z8, rs8 = yildiz(z8, 1.0, 0, eski)
    bp1 = by_poster(a.kod, 1, a.pair, a.n1, a.n2)
    s8 = ogeler(bp1, z8)
    Image.fromarray(s8).save(out / "STARLIT_8x10.jpg", quality=95, subsampling=0, dpi=(300, 300))
    rap["8x10"] = dict(boyut=[2400, 3000], kaynak_kirpim="satir 300:3300 (olcek yok)", cerceve=rc8, yay=ry8, yildiz=rs8)
    # ---- kontak (ayni yukseklik, yalniz kucultme)
    h = 1500
    a12 = Image.fromarray(son).resize((round(3600 * h / 5400), h), Image.LANCZOS)
    a8 = Image.fromarray(s8).resize((round(2400 * h / 3000), h), Image.LANCZOS)
    kt = Image.new("RGB", (a12.width + a8.width + 60, h + 40), (230, 230, 230)); kt.paste(a12, (20, 20)); kt.paste(a8, (a12.width + 40, 20))
    kt.save(out / "KONTAK_ORNEK3.jpg", quality=88)
    kt.resize((kt.width * 450 // kt.height, 450), Image.LANCZOS).save(out / "ONIZLEME_KUCUK.jpg", quality=70)
    (out / "OLCUM.json").write_text(json.dumps(rap, indent=1), encoding="utf-8")
    print(json.dumps(rap, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
