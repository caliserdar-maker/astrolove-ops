#!/usr/bin/env python3
"""POD hero kirpma (Mo 14 Eyl 2026, 2. surum): oda sahnesini 4:5 kadraja daraltir.

Kural: cerceve yuksekligi kadrajin %<ratio>'si, cerceve tam ortali, oran 4:5.
HER EDISYON KENDI cercevesini bulur; bulamazsa DURULUR (baska edisyonun kutusu
ASLA kullanilmaz).

Tespit (sirasiyla):
  1. SABLON ESLEME: edisyonun baskisi (poster dosyasi) hero icinde cok olcekli
     cv2.matchTemplate (TM_CCOEFF_NORMED) ile aranir; skor esigin altindaysa
  2. CANNY + en buyuk dikdortgen kontur.
  Ikisi de basarisizsa SystemExit (DUR).
Bulunan baski dikdortgeni disa dogru kenar gecisi taranarak cerceve payi kadar
buyutulur (pay bulunamazsa baski dikdortgeni kullanilir, raporlanir).

BAGIMSIZ DOGRULAMA (ciktida, tespitten bagimsiz): cercevenin 4 kenari
gri profil gradyaniyla olculur; 4 kenar da kadraj icinde, olculen
cerceve/kadraj orani hedef +-0.02 ve merkez kacikligi <= %0.5 degilse FAIL.

Kullanim:
  hero_crop.py --heroes ED=yol,... --posters ED=yol[;yol2],... --out OUT
               [--video V.mp4 --video-poster P.jpg] [--ratio 0.80] [--ocr "A,B"]
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_W, OUT_H = 2000, 2500
CARD_W, CARD_H = 535, 670
RATIO_TOL = 0.02          # olculen cerceve/kadraj sapmasi
OFFSET_TOL = 0.005        # merkez kacikligi (kadraj boyutunun orani)
TM_MIN = 0.45             # sablon eslesme esigi (TM_CCOEFF_NORMED)
TM_W = 1000               # eslestirme calisma genisligi
SCALE_LO, SCALE_HI = 0.12, 0.92    # baski yuksekligi / hero yuksekligi tarama araligi
PAY_MAX = 0.15            # cerceve payi taramasi: baski boyutunun orani
GRAD_MIN = 6.0            # anlamli kenar gecisi (gri seviye/px)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def log(m):
    print(m, flush=True)


def font(px):
    for f in FONTS:
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


# Kaynaklar kendi uretimimiz (Drive); baski dosyalari 200+ MP oldugu icin PIL'in
# "decompression bomb" siniri kaldirilir, buyuk JPEG'ler draft() ile dusuk
# cozunurlukte cozulur (bellek ve sure icin).
Image.MAX_IMAGE_PIXELS = None


def gri(path_or_im, en_fazla=None):
    if isinstance(path_or_im, Image.Image):
        im = path_or_im
    else:
        im = Image.open(path_or_im)
        if en_fazla:
            im.draft("L", (en_fazla, en_fazla))
    return np.asarray(im.convert("L"), dtype=np.uint8)


# ------------------------------------------------------------ 1) sablon esleme
def sablon_esle(hero_g, poster_g):
    """(skor, (x, y, w, h)) tam cozunurlukte; cok olcekli TM_CCOEFF_NORMED."""
    H, W = hero_g.shape
    k = TM_W / W
    h = cv2.resize(hero_g, (TM_W, max(1, int(H * k))), interpolation=cv2.INTER_AREA)
    Hs, Ws = h.shape
    oran = poster_g.shape[1] / poster_g.shape[0]           # en/boy

    def dene(fr):
        th = int(round(fr * Hs))
        tw = int(round(th * oran))
        if th < 24 or tw < 24 or th >= Hs or tw >= Ws:
            return None
        t = cv2.resize(poster_g, (tw, th), interpolation=cv2.INTER_AREA)
        r = cv2.matchTemplate(h, t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        return mx, (loc[0], loc[1], tw, th)

    en = None
    kaba = np.arange(SCALE_LO, SCALE_HI, 0.02)
    for fr in kaba:
        s = dene(float(fr))
        if s and (en is None or s[0] > en[0]):
            en, en_fr = s, float(fr)
    if en is None:
        return 0.0, None
    for fr in np.arange(max(SCALE_LO, en_fr - 0.025), min(SCALE_HI, en_fr + 0.025), 0.004):
        s = dene(float(fr))
        if s and s[0] > en[0]:
            en, en_fr = s, float(fr)
    skor, (x, y, w, hh) = en
    s = 1 / k
    return skor, (int(round(x * s)), int(round(y * s)), int(round(w * s)), int(round(hh * s)))


# ------------------------------------------------------------ 2) canny yedek
def canny_kutu(hero_g):
    """En buyuk dikdortgen kontur (portre, alan > %4). Bulunamazsa None."""
    H, W = hero_g.shape
    k = TM_W / W
    g = cv2.resize(hero_g, (TM_W, max(1, int(H * k))), interpolation=cv2.INTER_AREA)
    g = cv2.GaussianBlur(g, (5, 5), 0)
    kenar = cv2.Canny(g, 40, 140)
    kenar = cv2.dilate(kenar, np.ones((3, 3), np.uint8), iterations=1)
    cnts, _ = cv2.findContours(kenar, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    Hs, Ws = g.shape
    en = None
    for c in cnts:
        yak = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(yak) != 4 or not cv2.isContourConvex(yak):
            continue
        x, y, w, h = cv2.boundingRect(yak)
        if h < 10 or (w * h) / (Ws * Hs) < 0.04 or not 0.5 <= w / h <= 0.95:
            continue
        if en is None or w * h > en[0]:
            en = (w * h, (x, y, w, h))
    if not en:
        return None
    s = 1 / k
    x, y, w, h = en[1]
    return (int(round(x * s)), int(round(y * s)), int(round(w * s)), int(round(h * s)))


# ------------------------------------------------------------ cerceve payi
def koyu_bant(prof, bas, yon, limit):
    """Baski kenarindan disa dogru KOYU BANT (cerceve) uzanimi.

    Gradyan tepesi yumusak/golgeli kenarlarda zayifliyor (14 Eyl olcumu: CI'da
    pay 8 px olculdu, gercegi ~25 px). Bunun yerine bant olcumu: pencerenin dis
    ucu duvar referansi alinir, baski kenarindan itibaren duvardan belirgin koyu
    kalan bitisik dizi cerceve bandidir; sinir yerel gradyanla keskinlestirilir.
    Donus: (pay, {duvar, koyu, esik})."""
    idx = [bas + yon * i for i in range(1, limit + 1)]
    idx = [i for i in idx if 0 <= i < len(prof)]
    if len(idx) < 6:
        return 0, {}
    v = np.array([prof[i] for i in idx], dtype=np.float64)
    duvar = float(np.median(v[-max(3, len(v) // 4):]))       # pencerenin dis ucu = duvar
    koyu = float(v.min())
    if duvar - koyu < 2 * GRAD_MIN:                          # belirgin koyu bant yok
        return 0, {"duvar": round(duvar, 1), "koyu": round(koyu, 1)}
    esik = koyu + 0.5 * (duvar - koyu)
    # sablon dikdortgeni birkac px icerde/disarida olabilir: koyu bandin baslangici
    # kucuk bir bosluk icinde aranir, sonra bitisik koyu dizi izlenir.
    bosluk = max(6, int(0.03 * len(v)))
    bas_i = next((i for i in range(min(bosluk, len(v))) if v[i] < esik), None)
    if bas_i is None:
        return 0, {"duvar": round(duvar, 1), "koyu": round(koyu, 1), "esik": round(esik, 1),
                   "not": "koyu bant baslangici bulunamadi"}
    n = bas_i
    while n < len(v) and v[n] < esik:
        n += 1
    d = np.abs(np.diff(v))
    a, b = max(0, n - 4), min(len(d), n + 4)                 # sinirin yerel gradyanla rotusu
    if b > a:
        n = a + int(np.argmax(d[a:b])) + 1
    return n, {"duvar": round(duvar, 1), "koyu": round(koyu, 1), "esik": round(esik, 1)}


def cerceve_payi(g, rect):
    """Baski dikdortgeninden disa dogru cerceve kenarini ara -> (kutu, paylar)."""
    x, y, w, h = rect
    sut = g[max(0, y + int(0.2 * h)):y + int(0.8 * h), :].mean(0)
    sat = g[:, max(0, x + int(0.2 * w)):x + int(0.8 * w)].mean(1)
    paylar, ayrinti = {}, {}
    lim_x, lim_y = max(8, int(PAY_MAX * w)), max(8, int(PAY_MAX * h))
    for ad, prof, bas, yon, lim in (("sol", sut, x, -1, lim_x), ("sag", sut, x + w, +1, lim_x),
                                    ("ust", sat, y, -1, lim_y), ("alt", sat, y + h, +1, lim_y)):
        pay, bilgi = koyu_bant(prof, bas, yon, lim)
        paylar[ad], ayrinti[ad] = pay, bilgi
    # 14 Eyl olcumu: paylar dort kenarda tutarsiz cikabiliyor (bir kenar 0-1 px,
    # karsi kenar 17-36 px) ve asimetri kutu merkezini kaydiriyor. Bu yuzden:
    #   - anlamli bant bulan kenar sayisi 3'ten azsa baski CERCEVESIZ sayilir (pay 0),
    #   - aksi halde TEK SIMETRIK pay = bulunan paylarin medyani, dort kenara esit.
    # Boylece kutu merkezi dogrudan sablon eslemenin merkezine oturur.
    # Cerceve bandi UNIFORM'dur; tek yonlu golge bir-iki kenarda sahte genis bant
    # verir. Bu yuzden anlamli paylar once medyanla TUTARLILIK suzgecinden gecer
    # (medyanin +-%40'i disi atilir); geriye 3 kenar kalmazsa baski cercevesizdir.
    en_az = max(3, int(0.004 * max(w, h)))
    aday = sorted(v for v in paylar.values() if v >= en_az)
    med = float(np.median(aday)) if aday else 0.0
    tutarli = [v for v in aday if 0.6 * med <= v <= 1.4 * med]
    cerceveli = len(tutarli) >= 3
    pay = int(round(float(np.median(tutarli)))) if cerceveli else 0
    olcum = {"ham": paylar, "en_az_px": en_az, "aday": aday, "tutarli": tutarli,
             "cerceveli": cerceveli, "uygulanan_pay": pay}
    log(f"    cerceve bandi: ham={paylar} aday={aday} tutarli={tutarli} -> "
        f"{'cerceveli' if cerceveli else 'CERCEVESIZ'} simetrik pay={pay} px")
    if not pay:
        return rect, olcum
    return (x - pay, y - pay, w + 2 * pay, h + 2 * pay), olcum


def cerceve_bul(hero_path, poster_paths):
    """(kutu, bilgi) - bulunamazsa SystemExit."""
    g = gri(hero_path)
    en = (0.0, None, None)
    for p in poster_paths:
        pg = gri(p, 1600)                      # sablon: en fazla ~1600 px kenar
        if max(pg.shape) > 1800:
            k = 1600 / max(pg.shape)
            pg = cv2.resize(pg, (0, 0), fx=k, fy=k, interpolation=cv2.INTER_AREA)
        skor, rect = sablon_esle(g, pg)
        log(f"    sablon {pathlib.Path(p).name}: skor {skor:.3f} kutu {rect}")
        if skor > en[0]:
            en = (skor, rect, p)
    bilgi = {"sablon_skoru": round(en[0], 4), "sablon": pathlib.Path(en[2]).name if en[2] else None,
             "esik": TM_MIN}
    if en[1] and en[0] >= TM_MIN:
        kutu, paylar = cerceve_payi(g, en[1])
        bilgi.update({"yontem": "sablon esleme", "baski_px": list(en[1]), "cerceve_payi_px": paylar})
        return kutu, bilgi
    log(f"    sablon skoru esigin ({TM_MIN}) altinda -> Canny yedegi")
    rect = canny_kutu(g)
    if not rect:
        raise SystemExit(f"HATA: {hero_path}: cerceve bulunamadi (sablon {en[0]:.3f} < {TM_MIN}, "
                         f"Canny dikdortgen yok) - DUR")
    kutu, paylar = cerceve_payi(g, rect)
    bilgi.update({"yontem": "canny", "baski_px": list(rect), "cerceve_payi_px": paylar})
    return kutu, bilgi


# ------------------------------------------------- bagimsiz kenar dogrulamasi
def kenar_olc(g, beklenen):
    """Ciktidaki cercevenin 4 kenarini gradyanla olc (tespitten bagimsiz).
    Donus: (sol, ust, sag, alt) | None."""
    H, W = g.shape
    bx, by, bw, bh = beklenen
    px, py = int(0.05 * W), int(0.05 * H)
    sut = g[max(0, by + int(0.25 * bh)):min(H, by + int(0.75 * bh)), :].mean(0)
    sat = g[:, max(0, bx + int(0.25 * bw)):min(W, bx + int(0.75 * bw))].mean(1)
    olcum = []
    for prof, hedef, pen, dis in ((sut, bx, px, "min"), (sat, by, py, "min"),
                                  (sut, bx + bw, px, "max"), (sat, by + bh, py, "max")):
        d = np.abs(np.diff(prof.astype(np.float64)))
        a, b = max(0, hedef - pen), min(len(d), hedef + pen)
        if b <= a:
            return None
        alt = d[a:b]
        # Cercevesiz acik baskida duvar-baski gecisi zayif olabilir: mutlak esik
        # yerine GURULTUYE gore esik (pencere medyaninin 3 kati, en az 3 gri).
        gurultu = float(np.median(alt)) if len(alt) else 0.0
        if alt.max() < max(3.0, 3.0 * gurultu):
            return None
        aday = np.flatnonzero(alt >= 0.6 * alt.max())
        j = aday[0] if dis == "min" else aday[-1]      # en distaki guclu gecis
        olcum.append(a + int(j) + 0.5)
    return tuple(olcum)


# ------------------------------------------------------------------ kirpma
def kutu_hesapla(W, H, cerceve, oran):
    fx, fy, fw, fh = cerceve
    ch = fh / oran
    cw = ch * 0.8
    if ch > H or cw > W:
        raise SystemExit(f"HATA: hesaplanan kadraj ({cw:.0f}x{ch:.0f}) kaynaktan ({W}x{H}) buyuk - DUR")
    cx, cy = fx + fw / 2, fy + fh / 2
    x0, y0 = cx - cw / 2, cy - ch / 2
    if x0 < 0 or y0 < 0 or x0 + cw > W or y0 + ch > H:
        raise SystemExit(f"HATA: kadraj goruntu disina tasiyor (cerceve tam ortali olamaz) - DUR")
    return (x0 / W, y0 / H, cw / W, ch / H)


def kirp_kaydet(img, goreli, hedef):
    W, H = img.size
    x0, y0, w, h = (goreli[0] * W, goreli[1] * H, goreli[2] * W, goreli[3] * H)
    kirp = img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).convert("RGB")
    kirp = kirp.resize((OUT_W, OUT_H), Image.LANCZOS)
    for q in (92, 90, 88, 86, 84, 82, 80):
        kirp.save(hedef, "JPEG", quality=q, subsampling=0, optimize=True)
        if hedef.stat().st_size < 1_000_000:
            return q, hedef.stat().st_size
    return q, hedef.stat().st_size


def dogrula(hedef_yol, cerceve, goreli, kaynak_boyut, oran, W=OUT_W, H=OUT_H):
    """Ciktida bagimsiz kenar olcumu -> (olcum sozlugu, hatalar)."""
    g = gri(hedef_yol)
    sw, sh = kaynak_boyut
    olc = goreli[2] * sw / W                       # kaynak px / cikti px
    fx, fy, fw, fh = cerceve
    bek = (int(round((fx - goreli[0] * sw) / olc)), int(round((fy - goreli[1] * sh) / (goreli[3] * sh / H))),
           int(round(fw / olc)), int(round(fh / (goreli[3] * sh / H))))
    k = kenar_olc(g, bek)
    if not k:
        return {"beklenen_px": list(bek), "olculen": None}, [f"{hedef_yol.name}: kenarlar olculemedi (DUR)"]
    sol, ust, sag, alt = k
    hata = []
    if not (0 <= sol < sag <= W and 0 <= ust < alt <= H):
        hata.append(f"{hedef_yol.name}: cerceve kadraj disinda {k}")
    o = (alt - ust) / H
    kx, ky = ((sol + sag) / 2 - W / 2) / W, ((ust + alt) / 2 - H / 2) / H
    if abs(o - oran) > RATIO_TOL:
        hata.append(f"{hedef_yol.name}: olculen cerceve/kadraj {o:.4f} (hedef {oran}+-{RATIO_TOL})")
    if abs(kx) > OFFSET_TOL or abs(ky) > OFFSET_TOL:
        hata.append(f"{hedef_yol.name}: merkez kacikligi x={kx*100:.2f}% y={ky*100:.2f}% (sinir "
                    f"+-{OFFSET_TOL*100:.1f}%)")
    return {"beklenen_px": list(bek), "olculen_kenarlar": [round(v, 1) for v in k],
            "olculen_cerceve_orani": round(o, 4),
            "merkez_kacikligi": {"x": round(kx, 4), "y": round(ky, 4)}}, hata


def geri_haritala(goreli, kaynak_boyut, olculen, cikti_boyut):
    """Ciktida OLCULEN kenarlari kaynak piksel koordinatlarindaki cerceve kutusuna cevir."""
    sw, sh = kaynak_boyut
    cw, ch = cikti_boyut
    sol, ust, sag, alt = olculen
    kx, ky = goreli[2] * sw / cw, goreli[3] * sh / ch
    return (goreli[0] * sw + sol * kx, goreli[1] * sh + ust * ky,
            (sag - sol) * kx, (alt - ust) * ky)


# ------------------------------------------------------------------ ocr/video
def ocr_var(path, kelimeler):
    import re
    import shutil
    from PIL import ImageOps
    if not shutil.which("tesseract") or not kelimeler:
        return None, None
    im = Image.open(path).convert("L")
    txt = ""
    for i, v in enumerate((im, ImageOps.invert(im))):
        t = path.parent / f"_ocr{i}.png"
        v.save(t)
        r = subprocess.run(["tesseract", str(t), "-", "--psm", "6"], capture_output=True, text=True, timeout=180)
        t.unlink(missing_ok=True)
        if r.returncode == 0:
            txt += " " + r.stdout
    txt = re.sub(r"\s+", " ", txt).upper()
    var = [k for k in kelimeler if re.sub(r"\s+", " ", k).upper() in txt]
    return var, [k for k in kelimeler if k not in var]


def ffprobe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
                        "-show_format", str(path)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"HATA: ffprobe: {r.stderr[-300:]}")
    d = json.loads(r.stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    return {"w": int(v["width"]), "h": int(v["height"]), "codec": v["codec_name"],
            "fps": v.get("r_frame_rate"), "sure": float(d["format"]["duration"]),
            "ses": [s["codec_name"] for s in a], "boyut": int(d["format"]["size"])}


def kare0(video, hedef):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vframes", "1", str(hedef)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"HATA: ffmpeg kare: {r.stderr[-300:]}")
    return Image.open(hedef)


def video_kirp(video, kutu_px, bilgi, hedef):
    x0, y0, w, h = [int(round(v)) for v in kutu_px]
    w -= w % 2
    h -= h % 2
    ses = ["-c:a", "copy"] if bilgi["ses"] else ["-an"]
    for crf in (23, 26, 29, 32):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                            "-vf", f"crop={w}:{h}:{x0}:{y0},scale=1080:1350:flags=lanczos",
                            "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", *ses, str(hedef)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"HATA: ffmpeg crop: {r.stderr[-400:]}")
        if hedef.stat().st_size <= 1_400_000:
            return crf, hedef.stat().st_size
    return crf, hedef.stat().st_size


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heroes", required=True, help="ED=yol,ED=yol")
    ap.add_argument("--posters", required=True, help="ED=yol[;yol2],... (edisyonun baski dosyasi)")
    ap.add_argument("--video", default="")
    ap.add_argument("--video-poster", default="", help="video edisyonunun baski dosyasi/dosyalari")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ratio", type=float, default=0.80)
    ap.add_argument("--etsy-ref", default="")
    ap.add_argument("--ocr", default="")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    heroes = [(s.split("=", 1)[0], pathlib.Path(s.split("=", 1)[1])) for s in a.heroes.split(",")]
    posters = {s.split("=", 1)[0]: [pathlib.Path(x) for x in s.split("=", 1)[1].split(";")]
               for s in a.posters.split(",")}
    t0 = time.time()
    rapor = {"yontem": "sablon esleme (cv2.matchTemplate, cok olcekli) + kenar payi; yedek Canny. "
                       "Her edisyon kendi cercevesini bulur; bulunamazsa DURULUR.",
             "kural": {"oran": "4:5", "cerceve_yuksekligi/kadraj": a.ratio, "ortalama": "tam ortali",
                       "merkez_kaciklik_siniri": OFFSET_TOL},
             "cikti": [OUT_W, OUT_H], "edisyonlar": {}}
    kartlar, hata, uyari = [], [], []

    for i, (ed, p) in enumerate(heroes, 1):
        if ed not in posters:
            raise SystemExit(f"HATA: {ed} icin baski dosyasi verilmedi - DUR")
        im = Image.open(p)
        log(f"[{i}/{len(heroes)}] {ed}: {p.name} {im.size}")
        cerceve, bilgi = cerceve_bul(p, posters[ed])
        hedef = out / f"hero_{ed}.jpg"
        gecisler, h2, olcum, goreli, q, boyut = [], [], {}, None, 0, 0
        # IKI GECIS: 1) tespit kutusuyla kirp, 2) ciktida OLCULEN kenarlari kaynaga
        # geri haritalayip duzeltilmis kutuyla bir kez daha kirp. Son PASS/FAIL,
        # son ciktida yapilan taze olcumdur.
        for gecis in (1, 2):
            goreli = kutu_hesapla(*im.size, cerceve, a.ratio)
            q, boyut = kirp_kaydet(im, goreli, hedef)
            olcum, h2 = dogrula(hedef, cerceve, goreli, im.size, a.ratio)
            gecisler.append({"gecis": gecis, "cerceve_px": [round(v, 1) for v in cerceve],
                             "olculen_cerceve_orani": olcum.get("olculen_cerceve_orani"),
                             "merkez_kacikligi": olcum.get("merkez_kacikligi"),
                             "hata": h2})
            log(f"    gecis {gecis}: cerceve={[round(v) for v in cerceve]} "
                f"oran={olcum.get('olculen_cerceve_orani')} kaciklik={olcum.get('merkez_kacikligi')}")
            if gecis == 2 or not h2 or not olcum.get("olculen_kenarlar"):
                break
            cerceve = geri_haritala(goreli, im.size, olcum["olculen_kenarlar"], (OUT_W, OUT_H))
        hata += h2
        bulundu, eksik = ocr_var(hedef, [k for k in a.ocr.split(",") if k])
        if eksik:
            uyari.append(f"{ed}: OCR'da bulunamayan metin {eksik}")
        rapor["edisyonlar"][ed] = {"dosya": hedef.name, "sonuc": "PASS" if not h2 else "FAIL",
                                   "tespit": bilgi, "cerceve_px": [round(v, 1) for v in cerceve],
                                   "goreli_kutu": {k: round(v, 6) for k, v in zip("xywh", goreli)},
                                   "kalite": q, "bayt": boyut, "gecisler": gecisler,
                                   "dogrulama": olcum, "ocr_bulunan": bulundu, "ocr_eksik": eksik}
        log(f"    {ed}: {'PASS' if not h2 else 'FAIL ' + str(h2)} | {boyut/1024:.0f} KB q{q} "
            f"| gecen {time.time()-t0:.0f}s")
        kartlar.append((ed, Image.open(hedef).resize((CARD_W, CARD_H), Image.LANCZOS),
                        olcum.get("merkez_kacikligi"), olcum.get("olculen_cerceve_orani"), not h2))

    # onizleme kartlari (kaciklik yazili)
    pad, ust, altyazi = 12, 34, 46
    pv = Image.new("RGB", (len(kartlar) * CARD_W + (len(kartlar) + 1) * pad,
                           CARD_H + ust + altyazi + 2 * pad), (250, 250, 252))
    d = ImageDraw.Draw(pv)
    for i, (ed, c, kac, o, gecti) in enumerate(kartlar):
        x = pad + i * (CARD_W + pad)
        pv.paste(c, (x, ust + pad))
        d.text((x + 4, 8), f"{ed}  {CARD_W}x{CARD_H}   {'PASS' if gecti else 'FAIL'}", font=font(20),
               fill=(20, 110, 60) if gecti else (170, 30, 30))
        t1 = f"kaciklik x={kac['x']*100:+.2f}%  y={kac['y']*100:+.2f}%" if kac else "kaciklik olculemedi"
        d.text((x + 4, ust + pad + CARD_H + 6), t1, font=font(18), fill=(40, 40, 60))
        d.text((x + 4, ust + pad + CARD_H + 26), f"cerceve/kadraj = {o}", font=font(18), fill=(40, 40, 60))
    pv.save(out / "preview_cards.png")

    if a.video:
        v = pathlib.Path(a.video)
        vbilgi = ffprobe(v)
        log(f"video: {vbilgi}")
        vp = [pathlib.Path(x) for x in a.video_poster.split(";") if x] or posters[heroes[0][0]]
        k0yol = out / "_video_frame0.png"
        kare0(v, k0yol)
        vcerceve, vinfo = cerceve_bul(k0yol, vp)
        vgecisler, vh, volcum, vgoreli, crf, vboyut = [], [], {}, None, 0, 0
        for gecis in (1, 2):
            vgoreli = kutu_hesapla(vbilgi["w"], vbilgi["h"], vcerceve, a.ratio)
            crf, vboyut = video_kirp(v, (vgoreli[0] * vbilgi["w"], vgoreli[1] * vbilgi["h"],
                                         vgoreli[2] * vbilgi["w"], vgoreli[3] * vbilgi["h"]),
                                     vbilgi, out / "video_MB_cropped.mp4")
            k1 = kare0(out / "video_MB_cropped.mp4", out / "_video_crop_frame0.png")
            volcum, vh = dogrula(out / "_video_crop_frame0.png", vcerceve, vgoreli,
                                 (vbilgi["w"], vbilgi["h"]), a.ratio, W=k1.width, H=k1.height)
            vgecisler.append({"gecis": gecis, "cerceve_px": [round(x, 1) for x in vcerceve],
                              "olculen_cerceve_orani": volcum.get("olculen_cerceve_orani"),
                              "merkez_kacikligi": volcum.get("merkez_kacikligi"), "hata": vh})
            log(f"    video gecis {gecis}: oran={volcum.get('olculen_cerceve_orani')} "
                f"kaciklik={volcum.get('merkez_kacikligi')}")
            if gecis == 2 or not vh or not volcum.get("olculen_kenarlar"):
                break
            vcerceve = geri_haritala(vgoreli, (vbilgi["w"], vbilgi["h"]),
                                     volcum["olculen_kenarlar"], (k1.width, k1.height))
        hata += vh
        yeni = ffprobe(out / "video_MB_cropped.mp4")
        k1 = kare0(out / "video_MB_cropped.mp4", out / "_video_crop_frame0.png")
        rapor["video"] = {"kaynak": vbilgi, "sonuc": "PASS" if not vh else "FAIL", "tespit": vinfo,
                          "cerceve_px": [round(x, 1) for x in vcerceve],
                          "goreli_kutu": {k: round(x, 6) for k, x in zip("xywh", vgoreli)},
                          "cikti": {**yeni, "crf": crf}, "gecisler": vgecisler, "dogrulama": volcum}
        log(f"video: {vinfo['yontem']} skor={vinfo['sablon_skoru']} crf{crf} {vboyut/1024:.0f} KB "
            f"DOGRULAMA {volcum.get('olculen_cerceve_orani')} kaciklik={volcum.get('merkez_kacikligi')}")
        cmp_im = Image.new("RGB", (2 * 1080 + 3 * pad, 1350 + ust + 2 * pad), (250, 250, 252))
        cmp_im.paste(Image.open(out / f"hero_{heroes[0][0]}.jpg").resize((1080, 1350), Image.LANCZOS),
                     (pad, ust + pad))
        cmp_im.paste(k1.convert("RGB").resize((1080, 1350), Image.LANCZOS), (2 * pad + 1080, ust + pad))
        dc = ImageDraw.Draw(cmp_im)
        dc.text((pad + 4, 8), f"hero_{heroes[0][0]}.jpg (kirpilmis)", font=font(24), fill=(30, 30, 40))
        dc.text((2 * pad + 1084, 8), "video_MB_cropped.mp4 kare 0", font=font(24), fill=(30, 30, 40))
        cmp_im.save(out / "compare_hero_vs_video.png")

    if a.etsy_ref:
        ew, eh = (int(x) for x in a.etsy_ref.lower().split("x"))
        rapor["etsy_elle_kirpma"] = {"boyut": [ew, eh], "oran": round(ew / eh, 4)}
    rapor["hatalar"] = hata
    rapor["uyarilar"] = uyari
    (out / "crop_box.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    log(json.dumps(rapor, ensure_ascii=False, indent=2))
    log(f"SONUC: {'PASS' if not hata else 'FAIL'} | {time.time()-t0:.0f}s")
    if hata:
        sys.exit(1)


if __name__ == "__main__":
    main()
