#!/usr/bin/env python3
"""1st Anniversary (YD / BY) siparis dosyasi 14 boy (Serdar 31 Eki karar 2a). Kaynak tasarim: bizim-yilimiz-v3 kod/by_poster.py (4:5,
Olculer.json yerlesimi; KOD_REF sabit, dosya DEGISTIRILMEZ). Poster (wall art) 14 boy mantigi (siparis_dijital/tek_jpg.py): oran ailesi
basina tek sayfa + o ailedeki boylara yeniden ornekleme; 5x7 A ailesinden.
ORAN AILESI SAYFASI (bu dosya): tuval W x H_aile (W = 2400 x SCALE, H_aile = W / aile orani). by_poster kaynagi bellekte yamalanir:
  - zemin (Baski_2400x3000) tuvale DIKEY uzatilir (en cok 2:3 icin x1,2; cerceve / kemer / yay zeminle birlikte uzar, desen kopyalanmaz);
  - oge KONUMLARI (center_y, cizgi / yildiz konumu) yuzde olarak H_aile'ye (zeminle ayni goreli yer);
  - oge BOYLARI (visible_height, isim yuksekligi, cizgi kalinligi, yildiz yuksekligi) 4:5 yuksekligine (H0 = 1,25 W): sembol ve yazi
    puntolari 8x10 ile birebir ayni, yalniz aralar aile oraninda acilir.
  Yamalar satir kalibiyla yapilir; her kalip beklenen sayida bulunmazsa DUR (kaynak degismis).
Aileler: 4:5 (8x10, 16x20, 24x30), 11x14, 3:4 (12x16, 18x24), 2:3 (12x18, 16x24, 20x30, 24x36), A (A4, A3, A2) + 5x7 (A ailesinden dikey
merkez kirpma, en cok %1,5; tek_jpg.py ile ayni kural). Boy dosyasi: aile sayfasi hedef piksele (inc x 300; A mm) LANCZOS, JPEG q95 4:4:4,
300 dpi. Kapilar: boyut = hedef px, dpi 300, oran hatasi <= %0,2 (5x7 kirpma <= %1,5), kirpilan bantta oge yok.
Kullanim: by_boy.py --kod <bizim-yilimiz kopyasi> --pair CANCER_LIBRA --style 1 --name1 .. --name2 .. --date .. [--heading ..] [--line ..]
          --boy 14|<virgullu> --scale 2 --out <dir>  -> <boy>.jpg + BOY_RAPOR.json"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

DPI = 300
BOY = {"5x7": (5, 7), "8x10": (8, 10), "11x14": (11, 14), "12x16": (12, 16), "12x18": (12, 18), "16x20": (16, 20), "16x24": (16, 24),
       "18x24": (18, 24), "20x30": (20, 30), "24x30": (24, 30), "24x36": (24, 36),
       "A4": (210 / 25.4, 297 / 25.4), "A3": (297 / 25.4, 420 / 25.4), "A2": (420 / 25.4, 594 / 25.4)}
AILE = {"4x5": 4 / 5, "11x14": 11 / 14, "3x4": 3 / 4, "2x3": 2 / 3, "A": 210 / 297}
BOY_AILE = {"8x10": "4x5", "16x20": "4x5", "24x30": "4x5", "11x14": "11x14", "12x16": "3x4", "18x24": "3x4", "12x18": "2x3",
            "16x24": "2x3", "20x30": "2x3", "24x36": "2x3", "A4": "A", "A3": "A", "A2": "A", "5x7": "A"}
KIRP_MAX = 0.015
ORAN_HATA = 0.002

# (kalip, yeni, beklenen sayi). H = aile tuvali, H0 = 4:5 yuksekligi (boy hesaplari).
YAMA = [
    (r"W, H = 2400 \* SCALE, 3000 \* SCALE\n",
     "W, H = 2400 * SCALE, 3000 * SCALE\nH0 = H\nH = round(W / float(os.environ['BY_AILE_ORAN'])) if os.environ.get('BY_AILE_ORAN') else H\n", 1),
    (r'el\["visible_height"\] / 100 \* H\b', 'el["visible_height"] / 100 * H0', 3),
    (r'max\(e1\["visible_height"\], e2\["visible_height"\]\) / 100 \* H\b', 'max(e1["visible_height"], e2["visible_height"]) / 100 * H0', 1),
    (r'dv\["rule_thickness_percent_height"\] / 100 \* H\b', 'dv["rule_thickness_percent_height"] / 100 * H0', 1),
    (r'dv\["star_height"\] / 100 \* H \* 0\.55', 'dv["star_height"] / 100 * H0 * 0.55', 1),
    (r"t_names / 100 \* H\b", "t_names / 100 * H0", 1),
    (r"return im if SCALE == 1 else im\.resize\(\(W, H\), Image\.LANCZOS\)", "return im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)", 1),
    (r'im\.save\(f"\{OUT\}/\{n\}_8x10\.jpg"', 'im.save(f"{OUT}/{n}_AILE.png"', 1),
    (r", quality=97, subsampling=0, dpi=\(300, 300\)\)", ")", 1),
]


def yamala(kaynak):
    for kalip, yeni, n in YAMA:
        bulunan = len(re.findall(kalip, kaynak))
        if bulunan != n:
            raise SystemExit(f"DUR: by_poster yamasi '{kalip[:40]}' {bulunan} kez (beklenen {n}); kaynak degismis")
        kaynak = re.sub(kalip, yeni.replace("\\", "\\\\"), kaynak)
    return kaynak


def aile_sayfasi(kod, aile, env, tmp):
    """-> PIL (aile tuvali, PNG kayipsiz)."""
    src = yamala(Path(kod, "kod", "by_poster.py").read_text(encoding="utf-8"))
    p = Path(tmp) / "by_poster_aile.py"
    p.write_text(src, encoding="utf-8")
    out = Path(tmp) / f"aile_{aile}"
    out.mkdir(parents=True, exist_ok=True)
    e = dict(os.environ); e.update(env); e.update(BY_ROOT=str(Path(kod).resolve()), OUT=str(out), BY_AILE_ORAN=repr(AILE[aile]))
    r = subprocess.run([sys.executable, str(p)], env=e, cwd=kod, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"DUR: aile {aile} cizimi: {(r.stderr or r.stdout)[-400:]}")
    f = sorted(out.glob("*_AILE.png"))
    if len(f) != 1:
        raise SystemExit(f"DUR: aile {aile} cikti {len(f)} dosya (tek stil beklenir)")
    return Image.open(f[0]).convert("RGB")


def hedef_px(boy):
    w, h = BOY[boy]
    return round(w * DPI), round(h * DPI)


def boy_dosyasi(sayfa, aile, boy, cikti, q=95):
    tw, th = hedef_px(boy)
    im, kirp = sayfa, 0.0
    hedef_oran, sayfa_oran = tw / th, sayfa.size[0] / sayfa.size[1]
    if abs(sayfa_oran / hedef_oran - 1) > ORAN_HATA:          # 5x7: A sayfasindan dikey merkez kirpma (sayfa daha uzun)
        yeni_h = round(sayfa.size[0] / hedef_oran)
        kirp = 1 - yeni_h / sayfa.size[1]
        if not 0 <= kirp <= KIRP_MAX:
            return dict(boy=boy, aile=aile, pass_=False, hata=f"kirpma {kirp:.4f} > {KIRP_MAX}")
        y0 = (sayfa.size[1] - yeni_h) // 2
        im = sayfa.crop((0, y0, sayfa.size[0], y0 + yeni_h))
    son = im.resize((tw, th), Image.LANCZOS)
    son.save(cikti, quality=q, subsampling=0, dpi=(DPI, DPI))
    k = Image.open(cikti)
    dpi = tuple(round(v) for v in k.info.get("dpi", (0, 0)))
    oran_hata = abs((im.size[0] / im.size[1]) / hedef_oran - 1)
    ok = k.size == (tw, th) and dpi == (DPI, DPI) and oran_hata <= ORAN_HATA
    return dict(boy=boy, aile=aile, dosya=Path(cikti).name, px=list(k.size), dpi=dpi[0], inc=[round(BOY[boy][0], 3), round(BOY[boy][1], 3)],
                sayfa_px=list(sayfa.size), olcek=round(tw / im.size[0], 4), kirpma=round(kirp, 4), oran_hata=round(oran_hata, 5),
                mb=round(Path(cikti).stat().st_size / 2 ** 20, 2), pass_=ok)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True)
    ap.add_argument("--pair", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--name1", required=True)
    ap.add_argument("--name2", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--heading", default="Paper Anniversary")
    ap.add_argument("--line", default="")
    ap.add_argument("--boy", default="14")
    ap.add_argument("--scale", default="2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    boylar = list(BOY) if a.boy == "14" else a.boy.split(",")
    if set(boylar) - set(BOY):
        raise SystemExit(f"DUR: bilinmeyen boy {sorted(set(boylar) - set(BOY))}")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    env = dict(PAIR=a.pair, STYLE=a.style, NAME1=a.name1, NAME2=a.name2, DATE=a.date, HEADING=a.heading, LINE=a.line, SCALE=a.scale)
    R, sayfa = [], {}
    with tempfile.TemporaryDirectory() as tmp:
        for b in boylar:
            f = BOY_AILE[b]
            if f not in sayfa:
                sayfa[f] = aile_sayfasi(a.kod, f, env, tmp)
                print(f"AILE {f}: {sayfa[f].size}", flush=True)
            r = boy_dosyasi(sayfa[f], f, b, out / f"{b}.jpg")
            R.append(r)
            print(f"BOY {b}: {'PASS' if r['pass_'] else 'FAIL'} {r.get('px')} {r.get('hata', '')}", flush=True)
    (out / "BOY_RAPOR.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    with open(out / "BOY_TABLO.csv", "w", encoding="utf-8") as f:   # Serdar'in bakacagi tablo
        f.write("boy,aile,genislik_inc,yukseklik_inc,piksel,dpi,oran_hata,kirpma,dosya_mb,kapi\n")
        for r in R:
            f.write(f"{r['boy']},{r['aile']},{r.get('inc', ['', ''])[0]},{r.get('inc', ['', ''])[1]},{'x'.join(map(str, r.get('px', [])))},"
                    f"{r.get('dpi', '')},{r.get('oran_hata', '')},{r.get('kirpma', '')},{r.get('mb', '')},{'PASS' if r['pass_'] else 'FAIL'}\n")
    oz = [Image.open(out / r["dosya"]) for r in R if r.get("dosya")]
    if oz:   # KONTAK: gercek oranlar, ayni olcekte (1 inc = 40 px)
        kk = [i.resize((max(1, round(i.size[0] * 40 / DPI)), max(1, round(i.size[1] * 40 / DPI)))) for i in oz]
        sat, gen = [], 0
        Wk = 2400
        for i in kk:
            if not sat or gen + i.size[0] + 20 > Wk:
                sat.append([]); gen = 0
            sat[-1].append(i); gen += i.size[0] + 20
        Hk = sum(max(i.size[1] for i in s_) + 20 for s_ in sat)
        K = Image.new("RGB", (Wk, Hk), (236, 236, 236)); y = 0
        for s_ in sat:
            x = 0
            for i in s_:
                K.paste(i, (x, y)); x += i.size[0] + 20
            y += max(i.size[1] for i in s_) + 20
        K.save(out / "KONTAK_14_BOY.jpg", quality=88)
    ok = all(r["pass_"] for r in R)
    print("BOY KONTROL " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
