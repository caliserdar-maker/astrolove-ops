#!/usr/bin/env python3
"""Kupa kapagi 4:3 alternatifleri (Merkez 28 Eki, Serdar karari): CANCER_LIBRA orange. Etsy yok, toplu uretim yok.
Sorun: kupa_kapak43.py kapaginin Etsy arama kirpiminda (4:5 orta) sag kupanin mesaji kesiliyor, sol kulp gorunmuyor.
  A) sahne kucultulur, kenarlar sahnenin kendi pikselleriyle dolar (ayna / uzatma / AI yok)
  B) kupalar birbirine yaklastirilir (ayni sahne olcegi)
  C) mevcut kapak (karsilastirma)
Once OLCULUR (2048 kare sahne; 4:3 kirpim y 226-1762, 3000 / 2048 = 1.4648 buyutme; 4:5 orta kirpim cikti x 600-2400 = sahne x 409.6-1638.4):
  kulplar: govde disinda y 950-1450 bandinda sutun basina > 25 acik piksel (lum > 190, doygunluk < 15) -> en sol / en sag x
    (sag kulbun dis kenari golgede: lum > 225 esigi 1986 veriyordu, gradyanla kenar ~2004-2009; inceleme 28 Eki)
  govdeler: geo_kapak_k40.json (sol / sag xl, xr); baski bordur dahil: kare kapak - bos sahne farki > 25 (y >= 780, govde icinde,
    sutunda >= 20 piksel); baslik: ayni fark, y < 780
  metin: koyu (max < 90) ve dusuk doygun (< 35) piksel satir kumeleri, govde icinde; sol kupa y >= 1400 kumeleri = isimler
    (EMILY JAMES, CANCER LIBRA), sag kupa y >= 1250 ilk kume = mesaj, sonrakiler = isimler; x araligi govde merkezinden 30 px
    bosluga kadar yayilim (bordur yapragi bitisikse ust sinir)
A ve B yalniz olcum kapisi gecerse uretilir:
  A: gereken olcek k = kirpim / icerik; mevcut 4:3 kapak sahnenin 2048 px genisliginin TAMAMINI kullaniyor (kirpim yalniz dikey),
     k < 1 iken yatayda sahnede olmayan piksel gerekir -> URETILMEZ (kirpim disi dikey pikseller yalniz yuksekligi kurtarir).
  B: bosluk sifira insa bile kulpla icerik genisligi <= kirpim olmali; degilse kupalar ust uste biner -> istendigi gibi URETILEMEZ.
Cikti <out>: C_KAPAK_3000x2250.jpg, C_ARAMA_4x5.jpg, C_MAGAZA_1x1.jpg, OLCUM_CIZIM.jpg (kirpim ve icerik sinirlari), KONTAK_KUPA_KAPAK_ALT.jpg
(< 300 KB, A / B / C yan yana; A ve B uretilmediyse olcum paneli), OLCUM.json (kontroller PASS / FAIL).
Kullanim: kupa_kapak_alt.py <kapak 4:3 jpg> <kare kapak jpg> <bos sahne png> <geo json> <out>"""
import io
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

S, Y0, KH, OUT_W, OUT_H = 2048, 226, 1536, 3000, 2250
OL = OUT_W / S
K45 = (OUT_W - OUT_H * 4 / 5) / 2, (OUT_W + OUT_H * 4 / 5) / 2           # cikti x 600 - 2400
K11 = (OUT_W - OUT_H) / 2, (OUT_W + OUT_H) / 2                           # cikti x 375 - 2625


def font(n):
    for f in ("DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, n)
        except OSError:
            pass
    return ImageFont.load_default()


def olc(kare, sahne, geo):
    s = np.asarray(sahne.convert("RGB")).astype(int); k = np.asarray(kare.convert("RGB")).astype(int)
    lum, sat = s.mean(2), s.max(2) - s.min(2)
    cs = ((lum > 190) & (sat < 15))[950:1450].sum(0)
    sol_k = min(x for x in range(0, int(geo["sol"][0])) if cs[x] > 25)
    sag_k = max(x for x in range(int(geo["sag"][1]), S) if cs[x] > 25)
    d = np.abs(k - s).max(2) > 25
    db = d.copy(); db[:780] = False; ys, xs = np.nonzero(db)
    baski = {}
    for ad in ("sol", "sag"):                      # baski yalniz govde icinde (golge / parlaklik farki govde disinda da cikiyor)
        x0, x1 = int(geo[ad][0]), int(geo[ad][1])
        sx = np.nonzero(db[:, x0:x1 + 1].sum(0) >= 20)[0] + x0          # tek pikselli aykiri sutunlar disarida
        baski[ad] = [int(sx.min()), int(sx.max())]
    koyu = (k.max(2) < 90) & ((k.max(2) - k.min(2)) < 35)
    metin = {}
    for ad, y_alt in (("sol", 1400), ("sag", 1250)):
        x0, x1 = int(geo[ad][0]), int(geo[ad][1])
        rows = np.nonzero(koyu[780:int(geo[ad][3]), x0:x1].sum(1) > 6)[0] + 780
        kume, bas, onc = [], rows[0], rows[0]
        for r in rows[1:]:
            if r - onc > 6:
                kume.append((bas, onc)); bas = r
            onc = r
        kume.append((bas, onc))
        for i, (a, b) in enumerate([c for c in kume if c[0] >= y_alt and c[1] - c[0] >= 8]):   # < 8 px: gurultu / alt uzanti parcasi
            cs_ = koyu[a:b + 1].sum(0); ink = np.nonzero(cs_[x0:x1] > 0)[0] + x0
            if not len(ink):
                continue
            c = int(ink[np.argmin(abs(ink - (x0 + x1) / 2))]); L = R_ = c
            for yon in (-1, 1):
                x, g = c, 0
                while x0 < x < x1 and g < 30:
                    x += yon; g = 0 if cs_[x] else g + 1
                    if cs_[x]:
                        L, R_ = min(L, x), max(R_, x)
            ad_m = "isim" if ad == "sol" else ("mesaj" if i == 0 else "isim")
            metin.setdefault(f"{ad}_{ad_m}", []).append([L, int(a), R_, int(b)])
    dt = d.copy(); dt[780:] = False; dt[:Y0] = False; ys, xs = np.nonzero(dt)
    baslik = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return dict(kulp_sol_x=sol_k, kulp_sag_x=sag_k, govde_sol=[geo["sol"][0], geo["sol"][1]], govde_sag=[geo["sag"][0], geo["sag"][1]],
                govde_arasi=round(geo["sag"][0] - geo["sol"][1], 1), baski=baski, metin=metin, baslik=baslik)


def main():
    kapak, kare, sahne, geo_p, out = sys.argv[1:6]
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    geo = json.loads(Path(geo_p).read_text())
    C = Image.open(kapak).convert("RGB")
    O = olc(Image.open(kare), Image.open(sahne), geo)
    kx0, kx1 = K45[0] / OL, K45[1] / OL                                        # sahne pikselinde 4:5 kirpim
    icerik = O["kulp_sag_x"] - O["kulp_sol_x"]
    R = dict(olcum=O, kirpim_45_sahne_x=[round(kx0, 1), round(kx1, 1)], kirpim_genislik=round(kx1 - kx0, 1), icerik_genislik=icerik)
    # A
    k = (kx1 - kx0) / icerik
    R["A"] = dict(gereken_olcek=round(k, 4), kuculen_sahne=round(S * k), tuval=[S, KH],
                  kaplanan_genislik_orani=round(S * k / S, 3), kaplanan_yukseklik_orani=round(min(1, S * k / KH), 3),
                  uretildi=S * k >= S and S * k >= KH,
                  neden="sahne zaten tam genislikte (4:3 kirpim yalniz dikey); kucultme yatayda sahnede olmayan piksel ister (ayna / uzatma / AI yasak)",
                  kulpsuz_govde_olcek=round((kx1 - kx0) / (O["govde_sag"][1] - O["govde_sol"][0]), 4))
    # B
    sifir = icerik - O["govde_arasi"]
    R["B"] = dict(bosluk_sifir_icerik=round(sifir, 1), yalniz_govdeler=round(O["govde_sag"][1] - O["govde_sol"][0] - O["govde_arasi"], 1),
                  gereken_ust_uste=round(sifir - (kx1 - kx0), 1), uretildi=sifir <= kx1 - kx0,
                  neden="yalniz iki govde yan yana bile kirpimdan genis; kupalar ust uste binmeli -> istendigi gibi uretilemez")
    # C kontrolleri
    a = np.asarray(C).astype(int)
    # kenar seridi: tam satir / sutunu tek renk (ptp <= 6) 8 px serit; C fotograf kirpimi oldugu icin bilgi amacli (A / B uretilseydi anlamli)
    kenar = {ad: int(sum(1 for s_ in sr if (np.ptp(s_, axis=0) <= 6).all())) for ad, sr in
             (("ust", a[:8]), ("alt", a[-8:]), ("sol", a[:, :8].transpose(1, 0, 2)), ("sag", a[:, -8:].transpose(1, 0, 2)))}

    def kontrol(k0, k1):                        # sahne pikselinde kirpim; her oge icin icerde mi + tasma (cikti px, + = disarida)
        oge = dict(baslik=(O["baslik"][0], O["baslik"][2]), sol_kulp=(O["kulp_sol_x"],) * 2, sol_govde=(O["govde_sol"][0], O["govde_sol"][1]),
                   sag_govde=(O["govde_sag"][0], O["govde_sag"][1]), sag_kulp=(O["kulp_sag_x"],) * 2)
        for ad, kutular in O["metin"].items():
            oge[ad] = (min(b[0] for b in kutular), max(b[2] for b in kutular))
        return {ad: dict(icerde=bool(x0 >= k0 and x1 <= k1), tasma_px=round(max(k0 - x0, x1 - k1, 0) * OL)) for ad, (x0, x1) in oge.items()}
    R["C"] = dict(boyut=list(C.size), boyut_ok=C.size == (OUT_W, OUT_H), kenar_tek_renk_satir=kenar,
                  arama_45=kontrol(kx0, kx1), magaza_11_bilgi=kontrol(K11[0] / OL, K11[1] / OL))
    R["C"]["sonuc"] = "PASS" if R["C"]["boyut_ok"] and not any(kenar.values()) and all(v["icerde"] for v in R["C"]["arama_45"].values()) else "FAIL"
    shutil.copyfile(kapak, out / "C_KAPAK_3000x2250.jpg")                    # mevcut kapagin bayt kopyasi (yeniden kodlama yok)
    c45 = C.crop((round(K45[0]), 0, round(K45[1]), OUT_H)); c45.save(out / "C_ARAMA_4x5.jpg", quality=90)
    c11 = C.crop((round(K11[0]), 0, round(K11[1]), OUT_H)); c11.save(out / "C_MAGAZA_1x1.jpg", quality=90)
    # olcum cizimi: kirpim kutulari + icerik sinirlari (cikti pikseli)
    m = C.copy(); d = ImageDraw.Draw(m); f = font(46)
    for (x0, x1), renk, ad in ((K45, (0, 90, 255), "4:5 arama"), (K11, (0, 170, 0), "1:1 magaza")):
        d.rectangle([x0, 4, x1, OUT_H - 5], outline=renk, width=10); d.text((x0 + 14, 14 if renk[2] else 70), ad, fill=renk, font=f)
    cx = lambda x: x * OL
    for x, ad in ((O["kulp_sol_x"], "sol kulp"), (O["kulp_sag_x"], "sag kulp"), (O["baski"]["sag"][1], "mesaj sonu")):
        d.line([cx(x), 900, cx(x), 2000], fill=(230, 0, 0), width=8)
        tx = cx(x) - d.textlength(ad, font=f) - 10 if cx(x) > OUT_W / 2 else cx(x) + 10           # sag etiketler cizginin solunda (kenarda kesilmez)
        d.text((tx, 2010 if "kulp" in ad else 840), ad, fill=(230, 0, 0), font=f)
    m.save(out / "OLCUM_CIZIM.jpg", quality=85)

    def panel(harf, satirlar):
        p = Image.new("RGB", (900, 675), (245, 240, 231)); dd = ImageDraw.Draw(p)
        dd.text((30, 30), f"{harf}: URETILMEDI", fill=(150, 0, 0), font=font(44)); y = 110
        for t in satirlar:
            dd.text((30, y), t, fill=(40, 34, 32), font=font(27)); y += 44
        return p
    pa = panel("A", ["Sahne zaten tam genislikte (4:3 kirpim", "yalniz dikey); kucultme yatayda",
                     "sahnede olmayan piksel ister.", f"Kulpla icerik {icerik} px, 4:5 kirpim {kx1 - kx0:.0f} px:",
                     f"olcek {k:.3f}, kaplanan genislik %{100 * k:.0f}.", f"Kulpsuz govdeler bile olcek {R['A']['kulpsuz_govde_olcek']:.3f}."])
    pb = panel("B", [f"Govde arasi bosluk {O['govde_arasi']:.0f} px.", f"Yalniz iki govde yan yana {R['B']['yalniz_govdeler']:.0f} px",
                     f"> 4:5 kirpim {kx1 - kx0:.0f} px.", f"Kulplarla bosluk 0 iken {sifir:.0f} px:",
                     f"kupalar {sifir - (kx1 - kx0):.0f} px ust uste binmeli.", "Istendigi gibi uretilemez."])
    # kontak: satir 1 C (tam, 4:5, 1:1), satir 2 A paneli, B paneli, olcum cizimi
    th = 450
    def kucuk(im):
        return im.resize((round(im.width * th / im.height), th), Image.LANCZOS)
    sat1 = [kucuk(C), kucuk(c45), kucuk(c11)]; sat2 = [kucuk(pa), kucuk(pb), kucuk(m)]
    Wk = max(sum(i.width for i in s_) + 10 * (len(s_) + 1) for s_ in (sat1, sat2))
    T = Image.new("RGB", (Wk, 2 * th + 3 * 10 + 80), "white"); dd = ImageDraw.Draw(T)
    dd.text((10, 8), "C: mevcut kapak  |  4:5 arama kirpimi  |  1:1 magaza kirpimi", fill=(0, 0, 0), font=font(26))
    dd.text((10, th + 48), "A ve B: uretilmedi (olcum)  |  olcum cizimi (mavi 4:5, yesil 1:1, kirmizi kulp / mesaj sinirlari)", fill=(0, 0, 0), font=font(26))
    for r, s_ in enumerate((sat1, sat2)):
        x = 10
        for im in s_:
            T.paste(im, (x, 40 + r * (th + 40))); x += im.width + 10
    for q in (85, 80, 75, 70, 65, 60):
        b = io.BytesIO(); T.save(b, "JPEG", quality=q)
        if b.tell() < 300 * 1024:
            break
    (out / "KONTAK_KUPA_KAPAK_ALT.jpg").write_bytes(b.getvalue()); R["kontak_kb"] = round(b.tell() / 1024, 1)
    (out / "OLCUM.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False))
    return 0 if R["kontak_kb"] < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
