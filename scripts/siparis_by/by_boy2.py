#!/usr/bin/env python3
"""1st Anniversary (YD) boy yontemi, 2. tur (Serdar 31 Eki: dikey uzatma REDDEDILDI, "elips bozulmamali"). KURAL: hicbir oge tek yonde
olceklenmez; yalniz esit oranli olcek; aynalama / desen kopyasi yok; urun sembolu yapay zekadan gecmez.
Iki yontem, 8x10 (4:5) cizimden (bizim-yilimiz-v3 by_poster, KOD_REF; dosya degistirilmez):
  a) KIRP : tasarim esit olcekle yeni orani kaplayacak kadar buyur, tasan yan kenarlar kirpilir. Kapi: kirpilan bantta oge pikseli (yazi /
           sembol farki + zemin uzerindeki cizgisel ogeler: yay, cerceve, yaprak, yildiz) 0 olmali.
  b) GENISLET : tasarim olcek 1 (birebir) ortada; eksik ust / alt bant YALNIZ zeminin duz rengi / gecisi + olculu cok olcekli gren ile dolar
           (kopya / ayna yok). Renk: kenar seridinde ogeler haric sutun medyani, yatayda W/6 yumusak; dikis: 2 x m satirlik gecis, ozgun
           piksele dokunmadan. Kapali sekiller (cerceve, yay) olceklenmez. Kenar satirina oge degiyorsa (yaprak) ek o kenara konmaz
           (tamami diger kenarda); iki kenar da temasliysa FAIL (dikiste kesik gorunur). Kapi: tasarim blogu birebir.
Olcum (inceleme 31 Eki): CIKTI dosyasi ile 8x10 arasinda SIFT + RANSAC afin, x ve y olcegi ayri (fark <= %1); b icin dikis kapisi
(kanal ortalamasi, bant gecis std orani; ONERI esik). Her stil x boy icin hicbir yontem PASS degilse cikis 1.
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
        out = np.zeros((n, W, 3), np.float32)
        for s1, s2 in ((1, 3), (3, 10), (10, 30)):
            no = rng.normal(0, 1, (n, W)).astype(np.float32)
            no = cv2.GaussianBlur(no, (0, 0), s1) - cv2.GaussianBlur(no, (0, 0), s2)
            no /= max(float(no.std()), 1e-6)
            for ch in range(3):                                # kanal basina std (inceleme 31 Eki: tek parlaklik greni renksizdi)
                L = sat[..., ch]
                bp = cv2.GaussianBlur(L, (0, 0), s1) - cv2.GaussianBlur(L, (0, 0), s2)
                std = float(bp[~msk].std()) if (~msk).any() else 0.0
                out[..., ch] += no * std
        return out

    def bant(sat, msk, n, tohum, ust):
        c = renk(sat, msk)
        dol = np.repeat(c[None], n, 0) + gren(sat, msk, n, tohum)
        # ozgun kenarin yumusak rengi: yalniz kenara en yakin m/3 satir, ogeler (cerceve, yildiz) HARIC (inceleme 31 Eki: maskesiz ortalama
        # cerceve / yildiz pikselini bant rengine sizdiriyordu, Starlit dRGB ~5)
        q = max(4, m // 3)
        ks, km = (sat[-q:], msk[-q:]) if ust else (sat[:q], msk[:q])
        v = ks.copy(); v[km] = np.nan
        kn = np.nanmean(v, axis=0)
        kn = np.where(np.isnan(kn), np.nanmean(kn, axis=0), kn)
        kenar = cv2.GaussianBlur(kn[None].astype(np.float32), (0, 0), sigmaX=W / 60, sigmaY=0.1)[0]
        k = min(n, 2 * m)
        for i in range(k):                                     # dikise yakin satirlar ozgun kenar rengine yaklasir
            t = (i + 1) / (k + 1)
            j = n - 1 - i if ust else i
            dol[j] = dol[j] + (kenar - c) * (1 - t)
        return dol

    ust = bant(f[:m], ozel[:m], eu, seed, True) if eu else np.zeros((0, W, 3), np.float32)
    alt = bant(f[H - m:], ozel[H - m:], ea, seed + 1, False) if ea else np.zeros((0, W, 3), np.float32)
    out = np.clip(np.round(np.concatenate([ust, f, alt], 0)), 0, 255).astype(np.uint8)
    birebir = bool(np.array_equal(out[eu:eu + H], a))          # kurgu geregi True (bilgi; kanit degil, inceleme 31 Eki)
    kesik = (tu > esik and eu) or (ta > esik and ea)
    dk = dikis_kapisi(out, ozel, eu, ea, H)
    return out, dict(ek_ust=eu, ek_alt=ea, tasarim_birebir=birebir, kenara_degen_oge_px=dict(ust=tu, alt=ta, esik=esik), dikis=dk,
                     pass_=birebir and not kesik and dk["pass_"],
                     not_=("kenara degen oge dikiste kesik gorunur" if kesik else
                           "ek yalniz temiz kenarda (asimetrik)" if eu in (0, ek) and ek else ""))


DIKIS_ORT = 1.5            # kanal ortalamasi farki (seviye)    -- ONERI esik (bagimsiz inceleme 31 Eki); onayli dosyadan olculmedi,
DIKIS_STD = (0.85, 1.15)   # bant gecis std orani sentetik/ozgun  Serdar onayi olmadan uretim esigi degildir


def dikis_kapisi(out, ozel, eu, ea, H):
    """Eklenen bant ile ozgun blok arasindaki her dikiste, iki yanda w satir (oge pikselleri haric): kanal ortalamasi farki ve
    bant gecis (1-3, 3-10, 10-30 px) std orani. Kurgu geregi gecen olcu degil: dolgu dokusunu ozgun dokuyla kiyaslar."""
    f = out.astype(np.float32)
    W = out.shape[1]
    w = max(24, round(0.01 * H))
    tam = np.zeros(out.shape[:2], bool); tam[eu:eu + H] = cv2.dilate(ozel.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    sonuc = {}
    for ad, y in (("ust", eu if eu else None), ("alt", eu + H if ea else None)):
        if y is None:
            continue
        A, B = slice(y - w, y), slice(y, y + w)        # A ustte, B altta
        mA, mB = ~tam[A], ~tam[B]
        ort = [round(float(f[A][..., c][mA].mean() - f[B][..., c][mB].mean()), 2) for c in range(3)]
        oran = {}
        y0, y1 = max(0, y - w - 100), min(f.shape[0], y + w + 100)      # yalniz dikis cevresi (hiz)
        P = f[y0:y1]
        A2, B2 = slice(y - w - y0, y - y0), slice(y - y0, y + w - y0)
        for s1, s2 in ((1, 3), (3, 10), (10, 30)):
            L = cv2.GaussianBlur(P, (0, 0), s1) - cv2.GaussianBlur(P, (0, 0), s2)
            sa, sb = float(L[A2][mA].std()), float(L[B2][mB].std())
            sen, oz = (sa, sb) if ad == "ust" else (sb, sa)
            oran[f"{s1}-{s2}"] = round(sen / max(oz, 1e-6), 3)
        ok = max(abs(v) for v in ort) <= DIKIS_ORT and all(DIKIS_STD[0] <= v <= DIKIS_STD[1] for v in oran.values())
        sonuc[ad] = dict(satir=y, ort_fark=ort, std_oran=oran, pass_=ok)
    return dict(pass_=all(v["pass_"] for v in sonuc.values()), **sonuc)


def afin_olcek(son, master):
    """Cikti dosyasi ile 8x10 master arasinda SIFT eslesme + RANSAC afin: x ve y olcegi AYRI olculur (kurgudan bagimsiz kanit)."""
    def kucuk(i):
        k = 1200 / i.shape[1]
        return cv2.cvtColor(cv2.resize(i, (1200, round(i.shape[0] * k)), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY), k
    (g1, k1), (g2, k2) = kucuk(son), kucuk(master)
    sift = cv2.SIFT_create(4000)
    p1, d1 = sift.detectAndCompute(g1, None); p2, d2 = sift.detectAndCompute(g2, None)
    if d1 is None or d2 is None:
        return None
    es = [m for m, n in cv2.BFMatcher().knnMatch(d2, d1, k=2) if m.distance < 0.75 * n.distance]
    if len(es) < 20:
        return None
    a = np.float32([p2[m.queryIdx].pt for m in es]) / k2; b = np.float32([p1[m.trainIdx].pt for m in es]) / k1
    M, inl = cv2.estimateAffine2D(a, b, ransacReprojThreshold=2.0 / k1)
    if M is None:
        return None
    sx, sy = float(np.hypot(M[0, 0], M[1, 0])), float(np.hypot(M[0, 1], M[1, 1]))
    return dict(sx=round(sx, 5), sy=round(sy, 5), sx_sy_fark=round(abs(sx / sy - 1), 5), eslesme=int(inl.sum()))


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
            for boy in a.boylar.split(","):
                tw, th = BB.hedef_px(boy)
                for yon, fn in (("a_kirp", yontem_a), ("b_genislet", yontem_b)):
                    im, r = fn(master, bg, tw / th)
                    kayit = dict(stil=STIL[st], boy=boy, yontem=yon, **r)
                    if im is not None:
                        sx, sy = tw / im.shape[1], th / im.shape[0]
                        son = cv2.resize(im, (tw, th), interpolation=cv2.INTER_LANCZOS4 if sx > 1 else cv2.INTER_AREA)
                        ad = f"{STIL[st]}_{boy}_{yon}.jpg"
                        Image.fromarray(son).save(out / ad, quality=95, subsampling=0, dpi=(300, 300))
                        # olcum (inceleme 31 Eki): CIKTI dosyasi ile master arasinda SIFT afin; x ve y olcegi ayri olculur
                        af = afin_olcek(son, master)
                        kayit.update(dosya=ad, px=[tw, th], dpi=300, afin=af,
                                     pass_=bool(r["pass_"] and af and af["sx_sy_fark"] <= ORAN_TOL))
                        kontak.append((f"{STIL[st]} {boy} {yon}", son))
                        for kn, dk in (r.get("dikis") or {}).items():     # dikis yakin plani (gercek piksel, 1200 x 600)
                            if isinstance(dk, dict):
                                y = round(dk["satir"] * th / im.shape[0]); x0 = tw // 2 - 600
                                Image.fromarray(son[max(0, y - 300):y + 300, x0:x0 + 1200]).save(
                                    out / f"DIKIS_{STIL[st]}_{boy}_{kn}.jpg", quality=92)
                    R.append(kayit)
                    print(f"{STIL[st]} {boy} {yon}: {'PASS' if kayit['pass_'] else 'FAIL'} {kayit.get('hata') or ''} {kayit.get('not_') or ''}",
                          flush=True)
    (out / "OLCUM.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
    with open(out / "TABLO.csv", "w", encoding="utf-8") as f:
        f.write("stil,boy,yontem,sonuc,piksel,afin_sx,afin_sy,sx_sy_fark,afin_eslesme,dikis_ust,dikis_alt,kirpilan_oge_px,ek_ust_alt,not\n")
        for r in R:
            af = r.get("afin") or {}
            dk = r.get("dikis") or {}
            dd = lambda k: "" if k not in dk else ("PASS" if dk[k]["pass_"] else "FAIL") + f" ort{dk[k]['ort_fark']} std{list(dk[k]['std_oran'].values())}"
            f.write(f"{r['stil']},{r['boy']},{r['yontem']},{'PASS' if r['pass_'] else 'FAIL'},{'x'.join(map(str, r.get('px', [])))},"
                    f"{af.get('sx', '')},{af.get('sy', '')},{af.get('sx_sy_fark', '')},{af.get('eslesme', '')},\"{dd('ust')}\",\"{dd('alt')}\","
                    f"{r.get('kirpilan_oge_px', '')},{str(r.get('ek_ust', '')) + '/' + str(r.get('ek_alt', '')) if 'ek_ust' in r else ''},"
                    f"{r.get('hata') or r.get('not_') or ''}\n")
    Hk = 900
    hs = [Image.fromarray(i).resize((round(i.shape[1] * Hk / i.shape[0]), Hk), Image.LANCZOS) for _, i in kontak]
    Kt = Image.new("RGB", (sum(h.size[0] for h in hs) + 20 * len(hs), Hk), (236, 236, 236)); x = 0
    for h in hs:
        Kt.paste(h, (x, 0)); x += h.size[0] + 20
    Kt.save(out / "KONTAK_YONTEM.jpg", quality=88)
    print("OZET", sum(r["pass_"] for r in R), "/", len(R), "PASS")
    # her stil x boy icin en az bir yontem PASS olmali; yoksa cikis 1 (inceleme 31 Eki: hep 0 donuyordu)
    ok = all(any(x["pass_"] for x in R if (x["stil"], x["boy"]) == k) for k in {(x["stil"], x["boy"]) for x in R})
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
