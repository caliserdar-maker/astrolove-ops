#!/usr/bin/env python3
"""1st Anniversary (YD) boy yontemi, 2. tur (Serdar 31 Eki: dikey uzatma REDDEDILDI, "elips bozulmamali"). KURAL: hicbir oge tek yonde
olceklenmez; yalniz esit oranli olcek; aynalama / desen kopyasi yok; urun sembolu yapay zekadan gecmez.
Iki yontem, 8x10 (4:5) cizimden (bizim-yilimiz-v3 by_poster, KOD_REF; dosya degistirilmez):
  a) KIRP : tasarim esit olcekle yeni orani kaplayacak kadar buyur, tasan yan kenarlar kirpilir. Kapi: kirpilan bantta oge pikseli (yazi /
           sembol farki + zemin uzerindeki cizgisel ogeler: yay, cerceve, yaprak, yildiz) 0 olmali.
  b) UZAT : tasarim olcek 1 (birebir) ortada; eksik ust / alt bant YALNIZ zeminin duz rengi / gecisi + olculu cok olcekli gren ile dolar
           (kopya / ayna yok). Renk: kenar seridinde ogeler haric sutun medyani, yatayda W/6 yumusak; dikis: 2 x m satirlik gecis, ozgun
           piksele dokunmadan. Kapali sekiller (cerceve, yay) olceklenmez. Kenar satirina oge degiyorsa (yaprak) ek o kenara konmaz
           (tamami diger kenarda); iki kenar da temasliysa FAIL (dikiste kesik gorunur). Kapi: tasarim blogu birebir.
Olcum (her ornek): yay ve sembol cevre kutusu en / boy orani 8x10 ile (son ornek master olcegine indirilerek) +-%1; x ve y olcegi esit.
Kullanim: by_boy2.py --kod <bizim-yilimiz> --pair CANCER_LIBRA --stiller 1,2 --boylar 12x18,A2 --scale 2 --out <dir>"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import by_boy as BB  # noqa: E402  BOY, hedef_px

STIL = {"1": "1_Starlit", "2": "2_Timeless", "3": "3_FirstPage", "4": "4_Layers", "5": "5_Botanical"}
OGE_ESIK = 28
CIZGI_ESIK = 18
ORAN_TOL = 0.01


def maskeler(a, bg):
    d = np.abs(a.astype(np.int16) - bg.astype(np.int16)).max(2) > OGE_ESIK          # yazi, sembol (cizilen ogeler)
    g = cv2.cvtColor(bg, cv2.COLOR_RGB2GRAY).astype(np.float32)
    s = max(8.0, a.shape[1] / 96)
    z = np.abs(g - cv2.GaussianBlur(g, (0, 0), s)) > CIZGI_ESIK                       # zemindeki yay, cerceve, yaprak, yildiz
    z = cv2.morphologyEx(z.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)).astype(bool)
    return d, z


def kutu_orani(m):
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if n < 2:
        return None, None
    i = 1 + int(np.argmax(st[1:, 4]))
    x, y, w, h = (int(v) for v in st[i, :4])
    return w / h, [x, y, w, h]


def yontem_a(a, bg, r):
    H, W = a.shape[:2]
    s = (W / r) / H
    nw, nh = round(W * s), round(H * s)
    kes = (nw - W) // 2
    d, z = maskeler(a, bg)
    bant = int(np.ceil(kes / s))
    oge = int(d[:, :bant].sum() + z[:, :bant].sum() + d[:, W - bant:].sum() + z[:, W - bant:].sum())
    im = cv2.resize(a, (nw, nh), interpolation=cv2.INTER_LANCZOS4)[:, kes:kes + W] if oge == 0 else None
    return im, dict(olcek=round(s, 4), kirpilan_bant_px_her_yan=bant, kirpilan_oge_px=oge, pass_=oge == 0,
                    hata=None if oge == 0 else f"kirpilan bantta {oge} oge pikseli (yazi / sembol / yay / cerceve / yaprak)")


def yontem_b(a, bg, r, seed=7):
    H, W = a.shape[:2]
    Ht = round(W / r); ek = Ht - H
    f = a.astype(np.float32)
    d, z = maskeler(a, bg)
    ozel = d | z
    m = max(12, round(0.02 * H))
    tu, ta = int(ozel[:3].sum()), int(ozel[H - 3:].sum())
    esik = round(0.02 * W)            # kenar satirlarinda bu kadar oge pikseli = gercek temas (yildiz kirintisi degil)
    if tu > esik and ta > esik:
        eu = ek // 2                  # iki kenar da temasli: esit; dikiste kesik gorunur (rapor)
    elif ta > esik:
        eu = ek                       # alt kenara oge degiyor (yaprak): ek yalniz ustte, alt kenar 8x10'daki gibi kalir
    elif tu > esik:
        eu = 0
    else:
        eu = ek // 2
    ea = ek - eu

    def renk(sat, msk):
        v = sat.copy(); v[msk] = np.nan
        med = np.nanmedian(v, axis=0)
        gen = np.nanmedian(med, axis=0)
        med = np.where(np.isnan(med), gen, med)
        return cv2.GaussianBlur(med[None].astype(np.float32), (0, 0), sigmaX=W / 6, sigmaY=0.1)[0]

    def gren(sat, msk, n, tohum):
        """cok olcekli gren: kaynak seridin bant gecis std'leri (sigma 1-3, 3-10, 10-30) olculur, ayni std'li sentetik gurultu."""
        rng = np.random.default_rng(tohum)
        L = sat.mean(2)
        out = np.zeros((n, W), np.float32)
        for s1, s2 in ((1, 3), (3, 10), (10, 30)):
            bp = cv2.GaussianBlur(L, (0, 0), s1) - cv2.GaussianBlur(L, (0, 0), s2)
            std = float(bp[~msk].std()) if (~msk).any() else 0.0
            no = rng.normal(0, 1, (n, W)).astype(np.float32)
            no = cv2.GaussianBlur(no, (0, 0), s1) - cv2.GaussianBlur(no, (0, 0), s2)
            out += no / max(float(no.std()), 1e-6) * std
        return out[..., None]

    def bant(sat, msk, n, tohum, ust):
        c = renk(sat, msk)
        dol = np.repeat(c[None], n, 0) + gren(sat, msk, n, tohum)
        kenar = cv2.GaussianBlur(sat.mean(0, keepdims=True), (0, 0), sigmaX=W / 60, sigmaY=0.1)[0]   # ozgun kenarin yumusak rengi
        k = min(n, 2 * m)
        for i in range(k):                                     # dikise yakin satirlar ozgun kenar rengine yaklasir
            t = (i + 1) / (k + 1)
            j = n - 1 - i if ust else i
            dol[j] = dol[j] + (kenar - c) * (1 - t)
        return dol

    ust = bant(f[:m], ozel[:m], eu, seed, True) if eu else np.zeros((0, W, 3), np.float32)
    alt = bant(f[H - m:], ozel[H - m:], ea, seed + 1, False) if ea else np.zeros((0, W, 3), np.float32)
    out = np.clip(np.round(np.concatenate([ust, f, alt], 0)), 0, 255).astype(np.uint8)
    birebir = bool(np.array_equal(out[eu:eu + H], a))
    kesik = (tu > esik and eu) or (ta > esik and ea)
    return out, dict(ek_ust=eu, ek_alt=ea, tasarim_birebir=birebir, kenara_degen_oge_px=dict(ust=tu, alt=ta, esik=esik),
                     pass_=birebir and not kesik,
                     not_=("kenara degen oge dikiste kesik gorunur" if kesik else
                           "ek yalniz temiz kenarda (asimetrik)" if eu in (0, ek) and ek else ""))


def aile_png(kod, stil, scale, tmp, pair):
    kod = str(Path(kod).resolve())          # kosu 41189786727: goreli yol cwd=kod ile ikilendi
    env = dict(os.environ); env.update(BY_ROOT=str(Path(kod).resolve()), PAIR=pair, STYLE=stil, NAME1="EMILY", NAME2="JAMES",
                                      DATE="12 JUNE 2025", HEADING="Paper Anniversary", LINE="", SCALE=str(scale), OUT=str(tmp))
    r = subprocess.run([sys.executable, str(Path(kod, "kod", "by_poster.py"))], env=env, cwd=kod, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"DUR: by_poster: {(r.stderr or r.stdout)[-300:]}")
    return np.asarray(Image.open(Path(tmp, f"{STIL[stil]}_8x10.jpg")).convert("RGB"))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True)
    ap.add_argument("--pair", default="CANCER_LIBRA")
    ap.add_argument("--stiller", default="1,2")
    ap.add_argument("--boylar", default="12x18,A2")
    ap.add_argument("--scale", default="2")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R, kontak = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for st in a.stiller.split(","):
            master = aile_png(a.kod, st, a.scale, tmp, a.pair)
            H, W = master.shape[:2]
            bg = np.asarray(Image.open(Path(a.kod, "z", "Baski_2400x3000_Buyutulmus", f"{STIL[st]}_8x10_300ppi.png")).convert("RGB")
                            .resize((W, H), Image.LANCZOS))
            Image.fromarray(master).save(out / f"{STIL[st]}_8x10.jpg", quality=95, subsampling=0, dpi=(300, 300))
            kontak.append((f"{STIL[st]} 8x10", master))
            d0, z0 = maskeler(master, bg)
            for boy in a.boylar.split(","):
                tw, th = BB.hedef_px(boy)
                for yon, fn in (("a_kirp", yontem_a), ("b_uzat", yontem_b)):
                    im, r = fn(master, bg, tw / th)
                    kayit = dict(stil=STIL[st], boy=boy, yontem=yon, **r)
                    if im is not None:
                        sx, sy = tw / im.shape[1], th / im.shape[0]
                        son = cv2.resize(im, (tw, th), interpolation=cv2.INTER_LANCZOS4 if sx > 1 else cv2.INTER_AREA)
                        ad = f"{STIL[st]}_{boy}_{yon}.jpg"
                        Image.fromarray(son).save(out / ad, quality=95, subsampling=0, dpi=(300, 300))
                        # olcum: sondaki yay / sembol kutusu (master genisligine indirip; b'de dikey kayma eu)
                        k = cv2.resize(son, (W, round(th * W / tw)), interpolation=cv2.INTER_AREA)
                        dy = r.get("ek_ust", 0) if yon == "b_uzat" else 0
                        olc = {}
                        for oad, m0 in (("yay_cerceve", z0), ("sembol_yazi", d0)):
                            r0, b0 = kutu_orani(m0)
                            if yon == "b_uzat" and b0:
                                ms = np.zeros(k.shape[:2], bool); ms[dy:dy + H] = m0[:k.shape[0] - dy]
                                r1, b1 = kutu_orani(ms)
                            else:
                                r1, b1 = r0, b0
                            olc[oad] = dict(oran_8x10=round(r0, 4) if r0 else None, oran_ornek=round(r1, 4) if r1 else None,
                                            fark=round(abs(r1 / r0 - 1), 5) if r0 and r1 else None)
                        kayit.update(dosya=ad, px=[tw, th], dpi=300, olcek_x=round(sx, 5), olcek_y=round(sy, 5),
                                     tek_yonlu_olcek=round(abs(sx / sy - 1), 5), olcum=olc,
                                     pass_=bool(r["pass_"] and abs(sx / sy - 1) <= 0.002
                                                and all(v["fark"] is not None and v["fark"] <= ORAN_TOL for v in olc.values())))
                        kontak.append((f"{STIL[st]} {boy} {yon}", son))
                    R.append(kayit)
                    print(f"{STIL[st]} {boy} {yon}: {'PASS' if kayit['pass_'] else 'FAIL'} {kayit.get('hata') or ''} {kayit.get('not_') or ''}",
                          flush=True)
    (out / "OLCUM.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    with open(out / "TABLO.csv", "w", encoding="utf-8") as f:
        f.write("stil,boy,yontem,sonuc,piksel,tek_yonlu_olcek,yay_oran_fark,sembol_oran_fark,kirpilan_oge_px,kenara_degen_oge_px,not\n")
        for r in R:
            o = r.get("olcum") or {}
            f.write(f"{r['stil']},{r['boy']},{r['yontem']},{'PASS' if r['pass_'] else 'FAIL'},{'x'.join(map(str, r.get('px', [])))},"
                    f"{r.get('tek_yonlu_olcek', '')},{(o.get('yay_cerceve') or {}).get('fark', '')},{(o.get('sembol_yazi') or {}).get('fark', '')},"
                    f"{r.get('kirpilan_oge_px', '')},\"{r.get('kenara_degen_oge_px', '')}\",{r.get('hata') or r.get('not_') or ''}\n")
    Hk = 900
    hs = [Image.fromarray(i).resize((round(i.shape[1] * Hk / i.shape[0]), Hk), Image.LANCZOS) for _, i in kontak]
    Kt = Image.new("RGB", (sum(h.size[0] for h in hs) + 20 * len(hs), Hk), (236, 236, 236)); x = 0
    for h in hs:
        Kt.paste(h, (x, 0)); x += h.size[0] + 20
    Kt.save(out / "KONTAK_YONTEM.jpg", quality=88)
    print("OZET", sum(r["pass_"] for r in R), "/", len(R), "PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
