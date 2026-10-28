#!/usr/bin/env python3
"""Kupa kapagi 4:3 alternatifleri (Merkez 28 Eki, Serdar karari): CANCER_LIBRA orange. Etsy yok, toplu uretim yok.
Sorun: kupa_kapak43.py kapaginin Etsy arama kirpiminda (4:5 orta) sag kupanin mesaji kesiliyor, sol kulp gorunmuyor.
  A) sahne kucultulur, kenarlar sahnenin kendi pikselleriyle dolar (ayna / uzatma / AI yok)
  B) kupalar birbirine yaklastirilir (ayni sahne olcegi)
  C) mevcut kapak (karsilastirma)
Once OLCULUR (2048 kare sahne; 4:3 kirpim y 226-1762, 3000 / 2048 = 1.4648 buyutme; 4:5 orta kirpim cikti x 600-2400 = sahne x 409.6-1638.4):
  kulplar: govde disinda y 950-1450 bandinda sutun basina > 25 beyaz piksel (lum > 225, doygunluk < 15) -> en sol / en sag x
  govdeler: geo_kapak_k40.json (sol / sag xl, xr); baski bolgesi: kare kapak - bos sahne farki > 25 (y >= 780); baslik: ayni fark, y < 780
A ve B yalniz olcum kapisi gecerse uretilir:
  A: gereken olcek k = kirpim / icerik; k ile kuculen 2048 kare sahne 4:3 tuvali (2048 x 1536) kaplamali (2048 k >= 2048 ve 2048 k >= 1536),
     yoksa eksik alan icin sahnede piksel yok -> URETILMEZ.
  B: bosluk sifira insa bile kulpla icerik genisligi <= kirpim olmali; degilse kupalar ust uste biner -> URETILMEZ.
Cikti <out>: C_KAPAK_3000x2250.jpg, C_ARAMA_4x5.jpg, C_MAGAZA_1x1.jpg, OLCUM_CIZIM.jpg (kirpim ve icerik sinirlari), KONTAK_KUPA_KAPAK_ALT.jpg
(< 300 KB, A / B / C yan yana; A ve B uretilmediyse olcum paneli), OLCUM.json (kontroller PASS / FAIL).
Kullanim: kupa_kapak_alt.py <kapak 4:3 jpg> <kare kapak jpg> <bos sahne png> <geo json> <out>"""
import io
import json
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
    cs = ((lum > 225) & (sat < 15))[950:1450].sum(0)
    sol_k = min(x for x in range(0, int(geo["sol"][0])) if cs[x] > 25)
    sag_k = max(x for x in range(int(geo["sag"][1]), S) if cs[x] > 25)
    d = np.abs(k - s).max(2) > 25
    db = d.copy(); db[:780] = False; ys, xs = np.nonzero(db)
    baski = {}
    for ad in ("sol", "sag"):                      # baski yalniz govde icinde (golge / parlaklik farki govde disinda da cikiyor)
        m = (xs >= geo[ad][0]) & (xs <= geo[ad][1])
        baski[ad] = [int(xs[m].min()), int(xs[m].max())]
    dt = d.copy(); dt[780:] = False; dt[:Y0] = False; ys, xs = np.nonzero(dt)
    baslik = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return dict(kulp_sol_x=sol_k, kulp_sag_x=sag_k, govde_sol=[geo["sol"][0], geo["sol"][1]], govde_sag=[geo["sag"][0], geo["sag"][1]],
                govde_arasi=round(geo["sag"][0] - geo["sol"][1], 1), baski=baski, baslik=baslik)


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
                  neden="kuculen kare sahne 4:3 tuvali kaplamiyor; eksik kenarlar icin sahnede piksel yok (ayna / uzatma / AI yasak)")
    # B
    sifir = icerik - O["govde_arasi"]
    R["B"] = dict(bosluk_sifir_icerik=round(sifir, 1), yalniz_govdeler=round(O["govde_sag"][1] - O["govde_sol"][0] - O["govde_arasi"], 1),
                  gereken_ust_uste=round(sifir - (kx1 - kx0), 1), uretildi=sifir <= kx1 - kx0,
                  neden="bosluk sifirken bile icerik kirpimdan genis; kupalar ust uste binmeli ve bosalan yerin arkasi icin sahnede piksel yok")
    # C kontrolleri
    a = np.asarray(C).astype(int)
    kenar = {ad: int(sum(1 for s_ in sr if (np.ptp(s_, axis=0) <= 6).all())) for ad, sr in
             (("ust", a[:8]), ("alt", a[-8:]), ("sol", a[:, :8].transpose(1, 0, 2)), ("sag", a[:, -8:].transpose(1, 0, 2)))}
    kes = lambda x0, x1: x0 >= kx0 and x1 <= kx1
    R["C"] = dict(boyut=list(C.size), boyut_ok=C.size == (OUT_W, OUT_H), kenar_tek_renk_satir=kenar,
                  arama_45=dict(baslik=kes(O["baslik"][0], O["baslik"][2]), sol_kupa_kulp_dahil=kes(O["kulp_sol_x"], O["govde_sol"][1]),
                                sag_kupa_kulp_dahil=kes(O["govde_sag"][0], O["kulp_sag_x"]), isimler_sol_baski=kes(*O["baski"]["sol"]),
                                mesaj_sag_baski=kes(*O["baski"]["sag"])))
    R["C"]["sonuc"] = "PASS" if R["C"]["boyut_ok"] and not any(kenar.values()) and all(R["C"]["arama_45"].values()) else "FAIL"
    C.save(out / "C_KAPAK_3000x2250.jpg", quality=92)
    c45 = C.crop((round(K45[0]), 0, round(K45[1]), OUT_H)); c45.save(out / "C_ARAMA_4x5.jpg", quality=90)
    c11 = C.crop((round(K11[0]), 0, round(K11[1]), OUT_H)); c11.save(out / "C_MAGAZA_1x1.jpg", quality=90)
    # olcum cizimi: kirpim kutulari + icerik sinirlari (cikti pikseli)
    m = C.copy(); d = ImageDraw.Draw(m); f = font(46)
    for (x0, x1), renk, ad in ((K45, (0, 90, 255), "4:5 arama"), (K11, (0, 170, 0), "1:1 magaza")):
        d.rectangle([x0, 4, x1, OUT_H - 5], outline=renk, width=10); d.text((x0 + 14, 14 if renk[2] else 70), ad, fill=renk, font=f)
    cx = lambda x: x * OL
    for x, ad in ((O["kulp_sol_x"], "sol kulp"), (O["kulp_sag_x"], "sag kulp"), (O["baski"]["sag"][1], "mesaj sonu")):
        d.line([cx(x), 900, cx(x), 2000], fill=(230, 0, 0), width=8); d.text((cx(x) + 10, 2010 if "kulp" in ad else 840), ad, fill=(230, 0, 0), font=f)
    m.save(out / "OLCUM_CIZIM.jpg", quality=85)

    def panel(harf, satirlar):
        p = Image.new("RGB", (900, 675), (245, 240, 231)); dd = ImageDraw.Draw(p)
        dd.text((30, 30), f"{harf}: URETILMEDI", fill=(150, 0, 0), font=font(44)); y = 110
        for t in satirlar:
            dd.text((30, y), t, fill=(40, 34, 32), font=font(27)); y += 44
        return p
    pa = panel("A", [f"Kulpla icerik {icerik} px, 4:5 kirpim {kx1 - kx0:.0f} px (sahne).", f"Gereken olcek {k:.3f}: sahne {S * k:.0f} px.",
                     f"Tuval 2048 x 1536; kaplanan genislik %{100 * k:.0f},", f"yukseklik %{100 * min(1, S * k / KH):.0f}.",
                     "Eksik kenar icin sahnede piksel yok;", "ayna / uzatma / AI yasak."])
    pb = panel("B", [f"Govde arasi bosluk {O['govde_arasi']} px.", f"Bosluk 0 iken icerik {sifir:.0f} px > {kx1 - kx0:.0f} px.",
                     f"Kupalar {sifir - (kx1 - kx0):.0f} px ust uste binmeli.", f"Yalniz govdeler {R['B']['yalniz_govdeler']:.0f} px.",
                     "Bosalan yerin arkasi icin", "sahnede piksel yok."])
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
