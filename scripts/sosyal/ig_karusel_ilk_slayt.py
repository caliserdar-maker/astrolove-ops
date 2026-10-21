#!/usr/bin/env python3
"""IG karusel ILK SLAYT ornegi (20 Eki 2026, yalniz CANCER_LIBRA; Metricool'a yazma yok). 1080x1350 (4:5), iki surum:
  A  PIN_P2a_v2 kurali 4:5'e: duvar (data/pod/kapak_sahne_v9.png -> leke_azalt GUCLU -> aydinlat ACIK-3, pin ile ayni
     duvar_zemin yolu), ustte tek satir "CANCER & LIBRA" (P2a_v2 gibi tek satir; EB Garamond wght 430, #162641),
     altinda cercevesiz poster + PIN_V2 golgesi.
  B  A'nin aynisi; yalniz baslik "Cancer & Libra, as one?" (mevcut karusel sorusu). Sigmazsa YALNIZ baslik kuculur.
Poster: onayli P2a_v2.jpg (3000x2250) icindeki poster kutusu (787, 326, 2212, 2140) = 1425x1814 (P0 11:14 posterinin
yalniz olceklenmis hali, NCC 0.9999); burada yalniz LANCZOS ile kuculur (olcek <= 1), AI yok, cerceve yok.
Olculer P2a_v2'den oransal: baslik 192 px / poster 1814 px, baslik murekkep alti - poster ust arasi 80 / 1814, ust ve alt
pay esit. IG profil izgarasi 4:5'i ortadan 3:4 kirpar (her yandan 33.75 px): baslik ve poster x [34+PAY, 1046-PAY].
Cikti: A.jpg, B.jpg, ONIZLEME_IZGARA.jpg (iki surumun 3:4 orta kirpimi yan yana), ONIZLEME_AKIS.jpg (4:5 tam), OLCUM.txt.
Kullanim: ig_karusel_ilk_slayt.py --p2a P2a_v2.jpg --font EBGaramond[wght].ttf --out DIR

TOPLU (21 Eki 2026, Serdar karari: ilk slayt = A, baslik TEK SATIR "<BURC> & <BURC>", poster en buyuk kalir):
  --kapak KAPAK_DIR --kapak-a KAPAK_A_DIR --out DIR [--ciftler A_B,C_D]
  Kaynak: cifte Etsy'ye yuklenen onayli kapak (KAPAK_P2_78_20261019: BASLIK_A/KAPAK_A'da varsa o, yoksa KAPAK;
  dosya <listing>_<CIFT>.jpg, 3000x2250). Poster kutusu her kapakta koyu bolgeden OLCULUR ve KUTU ile ayni olmali.
  Yerlesim (poster boyu/yeri, baslik boyu, taban cizgisi) A kurali (CANCER & LIBRA ile bulunan) ve 78 ciftte ayni;
  izgara guvenli alanina sigmayan baslik YALNIZ kendisi 0,5 px adimla kuculur (en az oran), KONTROL'e yazilir.
  Cikti: IG_ILK_<CIFT>.jpg, KONTAK_1..N.jpg (sayfa basina 16, cift adi etiketli), KONTROL.csv, OZET.txt."""
import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(KOK, 'sosyal', 'video_v9'))
import acilis_p as AP  # noqa: E402  (satir, golge, lum, G_P, RENK: PIN_V2 kurali ile ayni)
from duvar_zemin import AYDINLIK, LEKE, aydinlat, leke_azalt  # noqa: E402

W, H = 1080, 1350
KUTU = (787, 326, 2212, 2140)                 # P2a_v2 poster kutusu
P2A_BASLIK, P2A_ARA, P2A_POSTER_H = 192, 80, 1814
IZGARA_KES = (W - H * 3 / 4) / 2              # 33.75 px
PAY = 20
X0, X1 = IZGARA_KES + PAY, W - IZGARA_KES - PAY
BASLIK = {'A': 'CANCER & LIBRA', 'B': 'Cancer & Libra, as one?'}
YASAK = ('.', '+', '=')


def duvar45():
    sc = Image.open(os.path.join(KOK, 'data/pod/kapak_sahne_v9.png')).convert('RGB')
    D = leke_azalt(sc.resize((1213, 910), Image.LANCZOS).resize((2 * W, 2 * H), Image.LANCZOS), LEKE['guclu'])
    return aydinlat(D, *AYDINLIK['acik3']).resize((W, H), Image.LANCZOS)


def tek_satir(font, metin, boy):
    """satir(): siki kirpilmis maske + taban cizgisi (maske ustunden)."""
    return AP.satir(font, metin, boy)


def yerlesim(font):
    """En buyuk poster yuksekligi ph: blok (baslik murekkebi + ara + poster) ust/alt PAY_DIKEY esit, A basligi ve poster
    izgara guvenli alaninda. B basligi ayni boyutta sigmazsa yalniz o kuculur."""
    for ph in range(1300, 400, -2):
        T = P2A_BASLIK * ph / P2A_POSTER_H
        ara = round(P2A_ARA * ph / P2A_POSTER_H)
        m, bl = tek_satir(font, BASLIK['A'], T)
        pw = round(ph * (KUTU[2] - KUTU[0]) / (KUTU[3] - KUTU[1]))
        blok = bl + ara + ph                      # taban cizgisinden (A: caps, murekkep alti = taban) posterin altina
        pay_dikey = round(108 / 2250 * H)         # P2a_v2 ust pay orani (108 / 2250)
        if blok + 2 * pay_dikey <= H and m.shape[1] <= X1 - X0 and pw <= X1 - X0:
            return ph, pw, T, ara, pay_dikey
    raise SystemExit('yerlesim sigmadi')


def ciz(D, font, metin, T, taban_y, ph, pw, px, py, P):
    im = AP.golge(D, (px, py, px + pw, py + ph), [(dx * ph / 990, dy * ph / 990, sg * ph / 990, g) for dx, dy, sg, g in AP.G_P])
    Pk = P.resize((pw, ph), Image.LANCZOS)
    im.paste(Pk, (px, py))
    arr = np.asarray(im).astype(np.float32)
    boy = T
    while True:
        m, bl = tek_satir(font, metin, boy)
        if m.shape[1] <= X1 - X0:
            break
        boy -= 0.5
    x = round((W - m.shape[1]) / 2)
    y = round(taban_y - bl)
    h_, w_ = m.shape
    arr[y:y + h_, x:x + w_] = arr[y:y + h_, x:x + w_] * (1 - m[..., None]) + np.array(AP.RENK, np.float32) * m[..., None]
    return np.clip(arr, 0, 255).astype(np.uint8), (x, y, x + w_, y + h_), boy, Pk


def ncc(a, b):
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))


def kutu_olc(arr):
    """Poster kutusu: koyu (max kanal < 70) piksel orani; sutun > 0.6 (y 400-2050), satir > 0.8 (bulunan x araliginda)."""
    k = arr.max(axis=2) < 70
    sx = k[400:2050].mean(axis=0)
    xs = np.where(sx > 0.6)[0]
    if not len(xs):
        return None
    x0, x1 = int(xs[0]), int(xs[-1]) + 1
    sy = k[:, x0:x1].mean(axis=1)
    ys = np.where(sy > 0.8)[0]
    return (x0, int(ys[0]), x1, int(ys[-1]) + 1) if len(ys) else None


def kontak(yollar, etiketler, font, out, sayfa=16, sutun=4):
    tw, th, et = 270, 338, 34
    adlar = []
    for p in range(0, len(yollar), sayfa):
        parca = list(zip(yollar[p:p + sayfa], etiketler[p:p + sayfa]))
        satir_ = (len(parca) + sutun - 1) // sutun
        tv = Image.new('RGB', (sutun * (tw + 12) + 12, satir_ * (th + et + 12) + 12), 'white')
        d = ImageDraw.Draw(tv)
        f = ImageFont.truetype(font, 20); f.set_variation_by_axes([430])
        for i, (y, e) in enumerate(parca):
            x0, y0 = 12 + (i % sutun) * (tw + 12), 12 + (i // sutun) * (th + et + 12)
            tv.paste(Image.open(y).convert('RGB').resize((tw, th), Image.LANCZOS), (x0, y0))
            d.text((x0 + tw / 2, y0 + th + 6), e, font=f, fill=(20, 20, 20), anchor='ma')
        ad = f'KONTAK_{p // sayfa + 1}.jpg'
        tv.save(os.path.join(out, ad), quality=90)
        adlar.append(ad)
    return adlar


def toplu(o):
    import csv
    import time
    from collections import Counter
    dosya = {}
    for kod, d in (('KAPAK', o.kapak), ('KAPAK_A', o.kapak_a)):   # KAPAK_A sonra: varsa onu ezer (Etsy'ye yuklenen)
        for ad in sorted(os.listdir(d)):
            if ad.lower().endswith('.jpg') and '_' in ad:
                lid, cift = ad[:-4].split('_', 1)
                dosya[cift] = (kod, lid, os.path.join(d, ad))
    ciftler = [c for c in o.ciftler.split(',') if c] if o.ciftler else sorted(dosya)
    eksik = [c for c in ciftler if c not in dosya]
    ph, pw, T, ara, _ = yerlesim(o.font)
    mA, blA = tek_satir(o.font, BASLIK['A'], T)
    taban_y = round((H - (blA + ara + ph)) / 2 + blA)
    py, px = taban_y + ara, round((W - pw) / 2)
    D = duvar45()
    satirlar, t0 = [], time.time()
    for i, c in enumerate([c for c in ciftler if c in dosya], 1):
        kod, lid, yol = dosya[c]
        sat, ok = {}, True

        def k(ad, kosul, deger):
            nonlocal ok
            ok &= bool(kosul)
            sat[ad] = deger
            if not kosul:
                sat.setdefault('fail', []).append(ad)

        a, b = c.split('_')
        metin = f'{a} & {b}'
        src = np.asarray(Image.open(yol).convert('RGB'))
        bul = kutu_olc(src)
        k('kaynak_kutu', bul == KUTU and src.shape[:2] == (2250, 3000), f'{bul} {src.shape[1]}x{src.shape[0]}')
        P = Image.fromarray(src).crop(KUTU)
        k('olcek', ph / P.height <= 1, round(ph / P.height, 4))
        k('yasak_karakter_yok', not any(x in metin for x in YASAK), metin)
        k('baslik_metni', metin.split(' & ') == [a, b] and metin.isupper() and (a != b or metin.count(a) == 2), metin)
        arr, bk, boy, Pk = ciz(D, o.font, metin, T, taban_y, ph, pw, px, py, P)
        hedef = os.path.join(o.out, f'IG_ILK_{c}.jpg')
        Image.fromarray(arr).save(hedef, quality=95, subsampling=0)
        J = np.asarray(Image.open(hedef).convert('RGB'))
        k('poster_ncc', ncc(J[py:py + ph, px:px + pw], np.asarray(Pk)) >= 0.999, round(ncc(J[py:py + ph, px:px + pw], np.asarray(Pk)), 5))
        kenar = J[py:py + ph, px:px + pw].astype(int); Pa = np.asarray(Pk).astype(int)
        fk = float(np.mean([np.abs(kenar[:3] - Pa[:3]).mean(), np.abs(kenar[-3:] - Pa[-3:]).mean(),
                            np.abs(kenar[:, :3] - Pa[:, :3]).mean(), np.abs(kenar[:, -3:] - Pa[:, -3:]).mean()]))
        k('cerceve_yok_kenar_fark', fk < 3, round(fk, 2))
        paylar = {}
        for g, (gx0, gx1) in {'izgara': (IZGARA_KES, W - IZGARA_KES), 'akis': (0, W)}.items():
            for n, (a0, b0, a1, b1) in {'baslik': bk, 'poster': (px, py, px + pw, py + ph)}.items():
                paylar[f'{g}_{n}'] = round(min(a0 - gx0, gx1 - a1, b0, H - b1), 1)
        for x, v in paylar.items():
            k(f'pay_{x}', v >= PAY, v)
        k('baslik_poster_bosluk', py - bk[3] > 0, py - bk[3])
        Dl = AP.lum(np.asarray(D).astype(np.float64)[bk[1]:bk[3], bk[0]:bk[2]])
        kon = (float(np.percentile(Dl, 5)) + 0.05) / (float(AP.lum(np.array(AP.RENK))) + 0.05)
        k('kontrast', kon >= 4.5, round(kon, 2))
        r = dict(cift=c, kaynak=kod, listing_id=lid, baslik=metin, baslik_px=round(boy, 1), baslik_kural_px=round(T, 1),
                 baslik_kucultme=round(boy / T, 4), baslik_kutu=bk, poster_kutu=(px, py, px + pw, py + ph), **sat,
                 sonuc='PASS' if ok else 'FAIL', fail=' '.join(sat.get('fail', [])))
        satirlar.append(r)
        g = time.time() - t0
        print(f'{i}/{len(ciftler)} %{100 * i // len(ciftler)} gecen {g:.0f}s kalan ~{g / i * (len(ciftler) - i):.0f}s {c} {r["sonuc"]} '
              f'baslik {boy:.1f}px ({boy / T:.4f}) {r["fail"]}', flush=True)
    alan = list(dict.fromkeys(x for r in satirlar for x in r))
    with open(os.path.join(o.out, 'KONTROL.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, alan); w.writeheader(); w.writerows(satirlar)
    kt = kontak([os.path.join(o.out, f'IG_ILK_{r["cift"]}.jpg') for r in satirlar], [r['cift'] for r in satirlar], o.font, o.out)
    fail = [r['cift'] for r in satirlar if r['sonuc'] != 'PASS']
    kuc = sorted((r for r in satirlar if r['baslik_kucultme'] < 1), key=lambda r: r['baslik_kucultme'])
    oz = [f'IG KARUSEL ILK SLAYT A x{len(satirlar)} (1080x1350; Metricool yazma 0): {len(satirlar) - len(fail)} PASS / {len(fail)} FAIL, eksik {eksik}',
          f'kaynak: {dict(Counter(r["kaynak"] for r in satirlar))} (KAPAK_P2_78_20261019, Etsy yuklenen surum); poster kutusu {KUTU} her kapakta olculdu',
          f'yerlesim (78 ciftte ayni): poster {pw}x{ph} @({px}, {py}), olcek {ph / (KUTU[3] - KUTU[1]):.4f}; baslik kurali {T:.1f} px, taban y {taban_y}',
          f'baslik kucultulen {len(kuc)}: ' + ', '.join(f'{r["cift"]} {r["baslik_px"]}px (x{r["baslik_kucultme"]})' for r in kuc),
          'en kucuk pay: ' + ', '.join(f'{x} {min(r["pay_" + x] for r in satirlar)}' for x in ('izgara_baslik', 'izgara_poster', 'akis_baslik', 'akis_poster')),
          f'poster NCC min {min(r["poster_ncc"] for r in satirlar)}; kenar fark max {max(r["cerceve_yok_kenar_fark"] for r in satirlar)}; kontrast min {min(r["kontrast"] for r in satirlar)}',
          f'kontak: {kt}', f'FAIL: {fail}']
    open(os.path.join(o.out, 'OZET.txt'), 'w').write('\n'.join(oz) + '\n')
    print('\n'.join(oz))
    sys.exit(0 if not fail and not eksik else 1)


def main():
    ap = argparse.ArgumentParser()
    for k in ('font', 'out'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--p2a'); ap.add_argument('--kapak'); ap.add_argument('--kapak-a'); ap.add_argument('--ciftler', default='')
    o = ap.parse_args()
    os.makedirs(o.out, exist_ok=True)
    if o.kapak:
        return toplu(o)
    P = Image.open(o.p2a).convert('RGB').crop(KUTU)
    ph, pw, T, ara, pay_dikey = yerlesim(o.font)
    mA, blA = tek_satir(o.font, BASLIK['A'], T)
    blok = blA + ara + ph
    taban_y = round((H - blok) / 2 + blA)
    py = taban_y + ara
    px = round((W - pw) / 2)
    D = duvar45()
    sat, ok = [], True

    def k(ad, kosul, ayrinti):
        nonlocal ok
        ok &= bool(kosul)
        sat.append(f"{'PASS' if kosul else 'FAIL'} {ad}: {ayrinti}")

    olcek = ph / P.height
    k('poster olcek <= 1', olcek <= 1, f'kaynak {P.width}x{P.height} -> {pw}x{ph} (olcek {olcek:.4f}, oran {pw / ph:.4f} / kaynak {P.width / P.height:.4f})')
    sonuc = {}
    for s, metin in BASLIK.items():
        k(f'{s} yasak karakter yok (. + =)', not any(c in metin for c in YASAK), repr(metin))
        arr, bk, boy, Pk = ciz(D, o.font, metin, T, taban_y, ph, pw, px, py, P)
        Image.fromarray(arr).save(os.path.join(o.out, f'{s}.jpg'), quality=95, subsampling=0)
        J = np.asarray(Image.open(os.path.join(o.out, f'{s}.jpg')).convert('RGB'))
        n = ncc(J[py:py + ph, px:px + pw], np.asarray(Pk))
        k(f'{s} poster pikseli = kaynak (cercevesiz)', n >= 0.999, f'NCC {n:.5f} (JPEG sonrasi), kutu ({px}, {py}, {px + pw}, {py + ph})')
        kenar = J[py:py + ph, px:px + pw].astype(int)
        halka = np.concatenate([kenar[:3].reshape(-1, 3), kenar[-3:].reshape(-1, 3), kenar[:, :3].reshape(-1, 3), kenar[:, -3:].reshape(-1, 3)])
        kh = np.concatenate([np.asarray(Pk)[:3].reshape(-1, 3), np.asarray(Pk)[-3:].reshape(-1, 3), np.asarray(Pk)[:, :3].reshape(-1, 3), np.asarray(Pk)[:, -3:].reshape(-1, 3)]).astype(int)
        k(f'{s} cerceve yok (poster kenar 3 px = kaynak kenari)', np.abs(halka - kh).mean() < 3, f'ortalama fark {np.abs(halka - kh).mean():.2f}')
        for ad, (gx0, gx1) in {'izgara 3:4': (IZGARA_KES, W - IZGARA_KES), 'akis 4:5': (0, W)}.items():
            for nesne, (a0, b0, a1, b1) in {'baslik': bk, 'poster': (px, py, px + pw, py + ph)}.items():
                sol, sag, ust, alt = a0 - gx0, gx1 - a1, b0, H - b1
                k(f'{s} {ad} {nesne} kesilmez', min(sol, sag, ust, alt) >= PAY,
                  f'kutu ({a0}, {b0}, {a1}, {b1}); pay sol {sol:.1f} sag {sag:.1f} ust {ust} alt {alt} (>= {PAY})')
        k(f'{s} baslik - poster cakismaz', bk[3] < py, f'baslik murekkep alti {bk[3]}, poster ust {py}, bosluk {py - bk[3]}')
        Dl = AP.lum(np.asarray(D).astype(np.float64)[bk[1]:bk[3], bk[0]:bk[2]])
        kon = (float(np.percentile(Dl, 5)) + 0.05) / (float(AP.lum(np.array(AP.RENK))) + 0.05)
        k(f'{s} kontrast >= 4.5', kon >= 4.5, f'{kon:.2f}:1 (#162641, duvar %5 parlakligi baslik kutusunda)')
        sonuc[s] = dict(boy=boy, kutu=bk, J=J)
        sat.append(f'INFO {s}: baslik "{metin}" {boy:.1f} px (A kurali {T:.1f} px, kucultme {boy / T:.4f}), kutu {bk}')
    # onizlemeler: izgara (3:4 orta kirpim) ve akis (4:5 tam), A | B yan yana, 1/2 olcek
    x0, x1 = round(IZGARA_KES), round(W - IZGARA_KES)
    iz = [Image.fromarray(sonuc[s]['J'][:, x0:x1]).resize(((x1 - x0) // 2, H // 2), Image.LANCZOS) for s in 'AB']
    tuval = Image.new('RGB', (iz[0].width * 2 + 30, iz[0].height + 20), 'white')
    for i, t in enumerate(iz):
        tuval.paste(t, (10 + i * (t.width + 10), 10))
    tuval.save(os.path.join(o.out, 'ONIZLEME_IZGARA.jpg'), quality=92)
    ak = [Image.fromarray(sonuc[s]['J']).resize((W // 2, H // 2), Image.LANCZOS) for s in 'AB']
    tuval = Image.new('RGB', (W + 30, H // 2 + 20), 'white')
    for i, t in enumerate(ak):
        tuval.paste(t, (10 + i * (t.width + 10), 10))
    tuval.save(os.path.join(o.out, 'ONIZLEME_AKIS.jpg'), quality=92)
    bas = [f'IG KARUSEL ILK SLAYT (CANCER_LIBRA, 1080x1350; Metricool yazma 0): {"PASS" if ok else "FAIL"}',
           f'Poster kaynagi: P2a_v2.jpg kutu {KUTU} ({P.width}x{P.height}); duvar kapak_sahne_v9 leke_azalt guclu + acik3',
           f'Yerlesim: poster {pw}x{ph} @({px}, {py}); baslik taban y {taban_y}; ara {ara} px; kural baslik {T:.1f} px '
           f'(P2a_v2 192/1814); IG izgara 3:4 kirpimi her yandan {IZGARA_KES} px; guvenli x [{X0}, {X1}]',
           f'Golge (PIN_V2, olcek {ph / 990:.3f}): ' + str([[round(dx * ph / 990, 1), round(dy * ph / 990, 1), round(sg * ph / 990, 1), g] for dx, dy, sg, g in AP.G_P])]
    open(os.path.join(o.out, 'OLCUM.txt'), 'w').write('\n'.join(bas + sat) + '\n')
    print('\n'.join(bas + sat))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
