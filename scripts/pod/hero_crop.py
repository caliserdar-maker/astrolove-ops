#!/usr/bin/env python3
"""POD hero kirpma (Mo 13 Eyl 2026): oda sahnesini 4:5 kadraja daraltir.

Kural (tek): cerceve yuksekligi kadraj yuksekliginin %78'i, cerceve yatay+dikey
ortalanmis, oran 4:5. Goreli kutu ANA EDISYONDAN (MB) turetilir ve 5 edisyona
aynen uygulanir (ayni sahne sablonu). Cikti 2000x2500 JPG, sRGB, <1 MB.

Cerceve tespiti: koyu bolgelerin bagli bilesenleri (run-based CCL), portre
dikdortgen adayi (en/boy 0.55-0.95, doluluk >0.85, alan > %4) icinden en buyugu.
Kodda hero yerlesim kutusu tanimli olmadigi icin yontem "tespit"tir.

Kullanim:
  hero_crop.py --heroes MB=01.jpg,DB=01.jpg,... --out OUT [--video V.mp4]
               [--ref MB] [--ratio 0.78] [--pair "AQUARIUS • AQUARIUS"]
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_W, OUT_H = 2000, 2500
CARD_W, CARD_H = 535, 670
RATIO_TOL = 0.02
ASPECT = (0.55, 0.95)      # cerceve en/boy araligi (3:4 poster = 0.75)
FILL_MIN = 0.85            # bilesen alani / bbox alani
AREA_MIN = 0.04            # bbox alani / kadraj alani
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]


def log(m):
    print(m, flush=True)


def font(px):
    for f in FONTS:
        if pathlib.Path(f).exists():
            return ImageFont.truetype(f, px)
    return ImageFont.load_default()


# ------------------------------------------------------------------ tespit
def otsu(gray):
    h = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    p = h / h.sum()
    w0 = np.cumsum(p)
    m = np.cumsum(p * np.arange(256))
    mt = m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (mt * w0 - m) ** 2 / (w0 * (1 - w0))
    return int(np.nanargmax(var))


def bilesenler(mask):
    """Satir kosulariyla bagli bilesen: {etiket: (alan, x0, y0, x1, y1)}."""
    H, W = mask.shape
    ust, kok = {}, {}

    def bul(a):
        while kok[a] != a:
            kok[a] = kok[kok[a]]
            a = kok[a]
        return a

    def birlestir(a, b):
        ra, rb = bul(a), bul(b)
        if ra != rb:
            kok[max(ra, rb)] = min(ra, rb)

    etiket = 0
    onceki = []          # (x0, x1, etiket)
    kutu = {}
    for y in range(H):
        satir = mask[y]
        d = np.diff(np.concatenate(([0], satir.view(np.int8), [0])))
        bas, son = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        simdi = []
        for x0, x1 in zip(bas, son):
            komsu = [e for (a0, a1, e) in onceki if a0 <= x1 and x0 <= a1]
            if komsu:
                e = min(bul(k) for k in komsu)
                for k in komsu:
                    birlestir(e, k)
            else:
                etiket += 1
                e = etiket
                kok[e] = e
            simdi.append((x0, x1 - 1, e))
            a, bx0, by0, bx1, by1 = kutu.get(e, (0, W, H, 0, 0))
            kutu[e] = (a + (x1 - x0), min(bx0, x0), min(by0, y), max(bx1, x1 - 1), max(by1, y))
        onceki = simdi
    son = {}
    for e, (a, x0, y0, x1, y1) in kutu.items():
        r = bul(e)
        if r in son:
            pa, px0, py0, px1, py1 = son[r]
            son[r] = (pa + a, min(px0, x0), min(py0, y0), max(px1, x1), max(py1, y1))
        else:
            son[r] = (a, x0, y0, x1, y1)
    return son


def cerceve_bul(img, kucult=1200):
    """(x, y, w, h) tam cozunurlukte; bulunamazsa None. Aday olculeri loglanir."""
    im = img.convert("L")
    W0, H0 = im.size
    k = min(1.0, kucult / W0)
    im = im.resize((max(1, int(W0 * k)), max(1, int(H0 * k))), Image.LANCZOS)
    g = np.asarray(im, dtype=np.uint8)
    H, W = g.shape
    t = otsu(g)
    mask = g < t
    adaylar = []
    for a, x0, y0, x1, y1 in bilesenler(mask).values():
        w, h = x1 - x0 + 1, y1 - y0 + 1
        if h < 10 or w < 10:
            continue
        en_boy, doluluk, alan = w / h, a / (w * h), (w * h) / (W * H)
        # acik edisyonlarda cerceve ici acik kalir: dolu dikdortgen yerine HALKA olur.
        kenar = min(mask[y0, x0:x1 + 1].mean(), mask[y1, x0:x1 + 1].mean(),
                    mask[y0:y1 + 1, x0].mean(), mask[y0:y1 + 1, x1].mean())
        if ASPECT[0] <= en_boy <= ASPECT[1] and alan >= AREA_MIN and (doluluk >= FILL_MIN or kenar >= 0.85):
            adaylar.append((alan, en_boy, doluluk, kenar, (x0, y0, w, h)))
    if not adaylar:
        return None
    adaylar.sort(reverse=True)
    alan, en_boy, doluluk, kenar, (x0, y0, w, h) = adaylar[0]
    log(f"    cerceve adayi: alan %{alan*100:.1f} en/boy {en_boy:.3f} doluluk {doluluk:.3f} "
        f"kenar {kenar:.3f} ({'dolu' if doluluk >= FILL_MIN else 'halka'}; toplam {len(adaylar)} aday)")
    s = 1 / k
    return (int(round(x0 * s)), int(round(y0 * s)), int(round(w * s)), int(round(h * s)))


def ocr_var(path, kelimeler):
    """Kirpilmis kadrajda beklenen metinler var mi -> (bulunanlar, eksikler) | (None, None)."""
    import re
    import shutil
    if not shutil.which("tesseract"):
        return None, None
    from PIL import ImageOps
    im = Image.open(path).convert("L")
    txt = ""
    for i, v in enumerate((im, ImageOps.invert(im))):      # altin/koyu zemin icin ters cevrilmis kopya da
        t = path.parent / f"_ocr{i}.png"
        v.save(t)
        r = subprocess.run(["tesseract", str(t), "-", "--psm", "6"], capture_output=True, text=True, timeout=180)
        t.unlink(missing_ok=True)
        if r.returncode == 0:
            txt += " " + r.stdout
    txt = re.sub(r"\s+", " ", txt).upper()
    var = [k for k in kelimeler if re.sub(r"\s+", " ", k).upper() in txt]
    return var, [k for k in kelimeler if k not in var]


# ------------------------------------------------------------------ kutu
def kutu_hesapla(W, H, cerceve, oran):
    fx, fy, fw, fh = cerceve
    ch = fh / oran
    cw = ch * 0.8
    if ch > H or cw > W:
        raise SystemExit(f"HATA: hesaplanan kadraj ({cw:.0f}x{ch:.0f}) kaynaktan ({W}x{H}) buyuk")
    cx, cy = fx + fw / 2, fy + fh / 2
    x0 = min(max(cx - cw / 2, 0), W - cw)
    y0 = min(max(cy - ch / 2, 0), H - ch)
    kaydi = (abs(x0 + cw / 2 - cx) > 1, abs(y0 + ch / 2 - cy) > 1)
    return (x0 / W, y0 / H, cw / W, ch / H), kaydi


def kirp_kaydet(img, goreli, hedef):
    W, H = img.size
    x0, y0, w, h = (goreli[0] * W, goreli[1] * H, goreli[2] * W, goreli[3] * H)
    kirp = img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).convert("RGB")
    kirp = kirp.resize((OUT_W, OUT_H), Image.LANCZOS)
    for q in (92, 90, 88, 86, 84, 82, 80):
        kirp.save(hedef, "JPEG", quality=q, subsampling=0, optimize=True, progressive=False)
        if hedef.stat().st_size < 1_000_000:
            return q, hedef.stat().st_size
    return q, hedef.stat().st_size


# ------------------------------------------------------------------ video
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
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vframes", "1",
                        str(hedef)], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"HATA: ffmpeg kare: {r.stderr[-300:]}")
    return Image.open(hedef)


def video_kirp(video, kutu_px, bilgi, hedef):
    x0, y0, w, h = [int(round(v)) for v in kutu_px]
    w -= w % 2; h -= h % 2
    ses = ["-c:a", "copy"] if bilgi["ses"] else ["-an"]
    for crf in (23, 26, 29, 32):
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video),
               "-vf", f"crop={w}:{h}:{x0}:{y0},scale=1080:1350:flags=lanczos",
               "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", *ses, str(hedef)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"HATA: ffmpeg crop: {r.stderr[-400:]}")
        if hedef.stat().st_size <= 1_400_000:
            return crf, hedef.stat().st_size
    return crf, hedef.stat().st_size


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--heroes", required=True, help="ED=yol,ED=yol (ilk = referans)")
    ap.add_argument("--video", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ratio", type=float, default=0.78)
    ap.add_argument("--etsy-ref", default="", help="Serdar'in elle kirptigi kadraj: WxH")
    ap.add_argument("--ocr", default="", help="Kadrajda bulunmasi gereken metinler (virgullu)")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    heroes = [(s.split("=", 1)[0], pathlib.Path(s.split("=", 1)[1])) for s in a.heroes.split(",")]
    t0 = time.time()
    rapor = {"yontem": "tespit (hero yerlesim kutusu kodda tanimli degil; "
                       "pod_gallery_sample.POSTER_BOX yalniz 05 kartina ait, hero 01 "
                       "ETSY_UPLOAD_SETS'ten oldugu gibi kopyalaniyor)",
             "kural": {"oran": "4:5", "cerceve_yuksekligi/kadraj": a.ratio, "ortalama": "yatay+dikey"},
             "cikti": [OUT_W, OUT_H], "edisyonlar": {}}

    ref_ed, ref_p = heroes[0]
    ref_im = Image.open(ref_p)
    ref_cerceve = cerceve_bul(ref_im)
    if not ref_cerceve:
        raise SystemExit(f"HATA: {ref_ed} hero'sunda cerceve tespit edilemedi - DUR")
    goreli, kaydi = kutu_hesapla(*ref_im.size, ref_cerceve, a.ratio)
    log(f"[{ref_ed}] kaynak {ref_im.size} cerceve {ref_cerceve} -> goreli kutu "
        f"{tuple(round(v, 5) for v in goreli)} (kenar kaydirmasi: {kaydi})")
    rapor["kaynak"] = {"boyut": list(ref_im.size), "referans_edisyon": ref_ed,
                       "cerceve_px": list(ref_cerceve)}
    rapor["goreli_kutu"] = {"x": round(goreli[0], 6), "y": round(goreli[1], 6),
                            "w": round(goreli[2], 6), "h": round(goreli[3], 6)}
    rapor["kenar_kaydirmasi"] = {"x": bool(kaydi[0]), "y": bool(kaydi[1])}
    if a.etsy_ref:
        ew, eh = (int(v) for v in a.etsy_ref.lower().split("x"))
        rapor["etsy_elle_kirpma"] = {"boyut": [ew, eh], "oran": round(ew / eh, 4),
                                     "kadraj_yuksekligi_kaynaga_gore": round(eh / ref_im.size[1], 4),
                                     "hesaplanan": round(goreli[3], 4)}

    kartlar, hata, uyari = [], [], []
    for i, (ed, p) in enumerate(heroes, 1):
        im = Image.open(p)
        if im.size != ref_im.size:
            hata.append(f"{ed}: kaynak boyutu {im.size} != {ref_im.size}")
        # 1) her edisyon KENDI cercevesiyle; 2) tespit olmazsa referans (MB) kutusu
        c_src = ref_cerceve if ed == ref_ed else cerceve_bul(im)
        if c_src:
            kutu, kaydi_ed = kutu_hesapla(*im.size, c_src, a.ratio)
            kaynak = "tespit"
        else:
            kutu, kaydi_ed, kaynak = goreli, kaydi, f"{ref_ed} kutusu (tespit basarisiz)"
        hedef = out / f"hero_{ed}.jpg"
        q, boyut = kirp_kaydet(im, kutu, hedef)
        c2 = cerceve_bul(Image.open(hedef))
        olcum = kacikliK = None
        if c2:
            olcum = round(c2[3] / OUT_H, 4)
            kacikliK = {"x": round((c2[0] + c2[2] / 2 - OUT_W / 2) / OUT_W, 4),
                        "y": round((c2[1] + c2[3] / 2 - OUT_H / 2) / OUT_H, 4)}
            icinde = c2[0] >= 0 and c2[1] >= 0 and c2[0] + c2[2] <= OUT_W and c2[1] + c2[3] <= OUT_H
            if abs(olcum - a.ratio) > RATIO_TOL:
                hata.append(f"{ed}: olculen cerceve/kadraj {olcum} (hedef {a.ratio}+-{RATIO_TOL})")
            if not icinde:
                hata.append(f"{ed}: cerceve kadraj disinda {c2}")
            if max(abs(kacikliK["x"]), abs(kacikliK["y"])) > 0.02:
                uyari.append(f"{ed}: cerceve kadrajda ortali degil {kacikliK}")
        bulundu, eksik = ocr_var(hedef, [k for k in a.ocr.split(",") if k]) if a.ocr else (None, None)
        if eksik:
            uyari.append(f"{ed}: OCR'da bulunamayan metin {eksik} (geometrik kapsama gecerli)")
        rapor["edisyonlar"][ed] = {"dosya": hedef.name, "kutu_kaynagi": kaynak,
                                   "goreli_kutu": {k: round(v, 6) for k, v in zip("xywh", kutu)},
                                   "kalite": q, "bayt": boyut,
                                   "ocr_bulunan": bulundu, "ocr_eksik": eksik,
                                   "olculen_cerceve_orani": olcum, "merkez_kacikligi": kacikliK,
                                   "kaynak_cerceve_px": list(c_src or [])}
        log(f"[{i}/{len(heroes)}] {ed}: {hedef.name} q{q} {boyut/1024:.0f} KB kutu={kaynak} "
            f"cerceve/kadraj={olcum} kaciklik={kacikliK} | gecen {time.time()-t0:.0f}s")
        kartlar.append((ed, Image.open(hedef).resize((CARD_W, CARD_H), Image.LANCZOS)))

    # onizleme kartlari
    pad, ust = 12, 34
    pv = Image.new("RGB", (len(kartlar) * CARD_W + (len(kartlar) + 1) * pad,
                           CARD_H + ust + 2 * pad), (250, 250, 252))
    d = ImageDraw.Draw(pv)
    for i, (ed, c) in enumerate(kartlar):
        x = pad + i * (CARD_W + pad)
        pv.paste(c, (x, ust + pad))
        d.text((x + 4, 8), f"{ed}  {CARD_W}x{CARD_H}", font=font(20), fill=(30, 30, 40))
    pv.save(out / "preview_cards.png")

    # ---------------- video
    if a.video:
        v = pathlib.Path(a.video)
        bilgi = ffprobe(v)
        log(f"video: {bilgi}")
        k0 = kare0(v, out / "_video_frame0.png")
        vc = cerceve_bul(k0)
        rapor["video"] = {"kaynak": bilgi, "kare0_cerceve_px": list(vc or [])}
        if not vc:
            rapor["video"]["sonuc"] = "cerceve tespit edilemedi - videoya DOKUNULMADI"
            log("UYARI: video karesinde cerceve bulunamadi; video kirpilmadi")
        else:
            hero_or = ref_cerceve[3] / ref_im.size[1]
            vid_or = vc[3] / bilgi["h"]
            rapor["video"]["cerceve_yuksekligi_orani"] = {"hero": round(hero_or, 4),
                                                          "video": round(vid_or, 4)}
            vgoreli, vkaydi = kutu_hesapla(bilgi["w"], bilgi["h"], vc, a.ratio)
            rapor["video"]["goreli_kutu"] = {k: round(x, 6) for k, x in
                                             zip("xywh", vgoreli)}
            crf, vboyut = video_kirp(v, (vgoreli[0] * bilgi["w"], vgoreli[1] * bilgi["h"],
                                         vgoreli[2] * bilgi["w"], vgoreli[3] * bilgi["h"]),
                                     bilgi, out / "video_MB_cropped.mp4")
            yeni = ffprobe(out / "video_MB_cropped.mp4")
            rapor["video"]["cikti"] = {**yeni, "crf": crf}
            log(f"video kirpildi: crf{crf} {vboyut/1024:.0f} KB {yeni['w']}x{yeni['h']} "
                f"{yeni['sure']:.2f}s fps={yeni['fps']} ses={yeni['ses']}")
            # karsilastirma
            k1 = kare0(out / "video_MB_cropped.mp4", out / "_video_crop_frame0.png")
            hv = cerceve_bul(Image.open(out / f"hero_{ref_ed}.jpg"))
            vv = cerceve_bul(k1)
            if hv and vv:
                hn = [hv[0] / OUT_W, hv[1] / OUT_H, hv[2] / OUT_W, hv[3] / OUT_H]
                vn = [vv[0] / k1.width, vv[1] / k1.height, vv[2] / k1.width, vv[3] / k1.height]
                sapma = max(abs(x - y) for x, y in zip(hn, vn))
                rapor["video"]["hero_vs_video_sapma"] = round(sapma, 4)
                if sapma > 0.03:
                    hata.append(f"video/hero cerceve sapmasi %{sapma*100:.1f} (>3%)")
                log(f"hero-video cerceve sapmasi: %{sapma*100:.2f}")
            cmp_im = Image.new("RGB", (2 * 1080 + 3 * pad, 1350 + ust + 2 * pad), (250, 250, 252))
            cmp_im.paste(Image.open(out / f"hero_{ref_ed}.jpg").resize((1080, 1350), Image.LANCZOS),
                         (pad, ust + pad))
            cmp_im.paste(k1.convert("RGB").resize((1080, 1350), Image.LANCZOS), (2 * pad + 1080, ust + pad))
            dc = ImageDraw.Draw(cmp_im)
            dc.text((pad + 4, 8), f"hero_{ref_ed}.jpg (kirpilmis)", font=font(24), fill=(30, 30, 40))
            dc.text((2 * pad + 1084, 8), "video_MB_cropped.mp4 kare 0", font=font(24), fill=(30, 30, 40))
            cmp_im.save(out / "compare_hero_vs_video.png")

    rapor["hatalar"] = hata
    rapor["uyarilar"] = uyari
    (out / "crop_box.json").write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    log(json.dumps(rapor, ensure_ascii=False, indent=2))
    log(f"SONUC: {'PASS' if not hata else 'FAIL'} | {time.time()-t0:.0f}s")
    if hata:
        sys.exit(1)


if __name__ == "__main__":
    main()
