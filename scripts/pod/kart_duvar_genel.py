#!/usr/bin/env python3
"""Krem zeminli onayli galeri kartini kapak duvari zeminine tasir (Serdar 28 Eyl; 03/04/05/07/08/12/13/14).
Bu kartlarin yazilari ChatGPT pikseli (basan kur scripti yok); yeniden cizim yok, KATMAN AYRISTIRMA ile tasinir:
  eski piksel A = a*F + (1-a)*KREM  (F: on plan rengi, a: ortme)  ->  yeni = a*F' + (1-a)*B
  B: yeni zemin (duvar; kutularin ic krem alani icin yari saydam acik ton), F': kontrast icin koyulasmis yazi rengi.
Cikti formulunde krem yoktur -> kenarda krem hale olusmaz (renk anahtari degil).
Sinif (onayli karttan olculur):
  - zemin: max|A - KREM| <= 4
  - nesne (poster, panel, cerceve, kendi dolgulu kutu): cekirdek (|A-KREM| >= 40) ya da duz acik dolgu bilesenleri
    buyuk olanlar (>= 90x90 kutu, >= 15000 px); ic pikselleri aynen korunur (poster/sembol/isim degismez)
  - yazi/cizgi: kucuk cekirdek bilesenleri; satirlara gruplanir, satir rengi duvara karsi kontrast >= 4.5 olana
    dek ayni tonda koyulasir (nesne icindeki yazilar degismez)
  - kenar (cekirdege <= 2 px): F = en yakin cekirdek pikselinin rengi, a = (A-KREM).(F-KREM)/|F-KREM|^2
  - golge (notr koyulasmis krem, egimli; ya da cekirdekten uzak koyu): carpimsal, yeni = B * A / KREM
  - kutu ici krem (nesne tarafindan cevrili, >= 2000 px): B = duvar + 0.6*(KREM - duvar) (yari saydam acik ton)
Cikti: CIKIS.jpg + CIKIS.json (yazi satirlari: kutu, renk, kontrast; nesne kutulari: duvar_qc.py NCC icin).
Kullanim: kart_duvar_genel.py ESKI.jpg KAPAK_SAHNE_V9.png CIKIS.jpg ["x0,y0,x1,y1;..."]
  4. arguman: zorunlu nesne dikdortgenleri "x0,y0,x1,y1[,r]" (olculdu): rengi golgeden/kremden ayirt edilemeyen
  nesneler (07 White Frame 1556,540,2150,1269) ve sahne panelleri (06: 145,440,2855,1866,30; 09-11: 145,420,2855,1846,30;
  fotograf pikseli aynen kalir, yalniz kartin dis zemini duvar olur).
"""
import json
import os
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duvar_zemin import KREM, duvar, duvar_lum, kontrast, lum, yazi_rengi

ESKI, SAHNE, CIK = sys.argv[1:4]
ZORUNLU = [tuple(int(v) for v in k.split(',')) for k in sys.argv[4].split(';')] if len(sys.argv) > 4 and sys.argv[4] else []
A = np.asarray(Image.open(ESKI).convert('RGB')).astype(np.float32)
Dw = duvar(SAHNE); W = np.asarray(Dw).astype(np.float32)
C = np.array(KREM, np.float32)
d = np.abs(A - C).max(2)
H_, W_ = d.shape

zemin = d <= 4
# golge: kremin notr koyulasmasi (kanal oranlari esit, 0.3 < oran < 0.99) ve dis zemine bagli.
# Nesneye dahil edilmez; duvara carpimsal tasinir (onayli karttaki golge krem tonuyla kalmaz). Duz kutu dolgusu
# gradyansiz oldugu icin golge sayilmaz, korunur.
q = A / C; qm = q.mean(2); qs = q.max(2) - q.min(2)
gy, gx = np.gradient(ndi.gaussian_filter(A.mean(2), 3))
golgemsi = (d > 4) & (qs < 0.04) & (qm > 0.3) & (qm < 0.99)
# yalniz DIS zemine (kart kenarina bagli krem) degen bilesenler golgedir; cizgilerle cevrili kutu ici dolgu degildir
_zl, _ = ndi.label(zemin)
_dis = np.isin(_zl, np.setdiff1d(np.unique(np.r_[_zl[0], _zl[-1], _zl[:, 0], _zl[:, -1]]), [0]))
_gl, _gn = ndi.label(golgemsi)
_deg = np.unique(_gl[ndi.binary_dilation(_dis, iterations=2) & golgemsi])
golgemsi = np.isin(_gl, _deg[_deg > 0])
cekirdek = (d >= 40) & ~golgemsi
# duz acik dolgu: kremden farkli (4..40; kreme cok yakin beyaz cerceve dahil) ve yerel olarak duz
yumus = ndi.uniform_filter(A.mean(2), 5); duz = np.abs(A.mean(2) - yumus) < 2.5
dolgu = (d > 4) & (d < 40) & duz & ~golgemsi

# nesneler: (cekirdek | dolgu) bilesenleri, buyuk olanlar
lab, n = ndi.label(ndi.binary_closing(cekirdek | dolgu, np.ones((3, 3))))
nesne = np.zeros_like(zemin); nesne_kutu = []; dikdortgen = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    m = lab[sl] == i
    if h >= 90 and w >= 90 and m.sum() >= 15000:     # buyuk basliktaki birlesik harfler nesne sayilmaz
        nesne[sl] |= m
        nesne_kutu.append((sl[1].start, sl[0].start, w, h))
        if ndi.binary_fill_holes(m).mean() >= 0.9:     # dikdortgen nesne (poster, cerceve, panel): kutunun tamami
            dikdortgen.append(sl)
nesne = (ndi.binary_fill_holes(nesne) & ~zemin & ~golgemsi) | nesne  # nesne ici krem/golge olmayan her sey nesne
for z in ZORUNLU:
    x0, y0, x1, y1 = z[:4]
    zm = Image.new('L', (x1 - x0, y1 - y0), 0)       # r verilirse yuvarlak kose (sahne paneli, kart_cila_kur ile ayni)
    from PIL import ImageDraw as _D
    _D.Draw(zm).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=z[4] if len(z) > 4 else 0, fill=255)
    zm = np.asarray(zm) > 0
    nesne[y0:y1, x0:x1] |= zm; golgemsi[y0:y1, x0:x1] &= ~zm
    nesne_kutu.append((x0, y0, x1 - x0, y1 - y0))
# dikdortgen nesnenin kutusu tamamen nesnedir (kreme cok yakin beyaz cerceve kenari zemin sayilip yirtilmaz)
for sl in dikdortgen:
    nesne[sl] |= ~golgemsi[sl] & ~zemin[sl]     # kutu ici krem (08 boy kutulari) nesne degil, yari saydam ton alir


# kutu ici krem: zemin bilesenleri, goruntu kenarina degmeyen ve buyuk olanlar
zl, zn = ndi.label(zemin)
kenar_id = set(np.unique(np.r_[zl[0], zl[-1], zl[:, 0], zl[:, -1]]))
ic = np.zeros_like(zemin)
for i, sl in enumerate(ndi.find_objects(zl), 1):
    if i in kenar_id:
        continue
    m = zl[sl] == i
    if m.sum() >= 2000:
        # yalniz cizgi/dolgu ile cevrili krem (kutu ici); golge icinde kalan krem cepleri kutu ici degildir
        mm = np.zeros_like(zemin); mm[sl] = m
        halka = ndi.binary_dilation(mm, iterations=3) & ~mm
        # ... ve cevresi cogunlukla nesne (kutu cizgisi/dolgusu) olmali: buyuk harf ici bosluk (orn. baslikta 'D') kutu degil
        if (halka & golgemsi).sum() < 0.4 * halka.sum() and (halka & nesne).sum() >= 0.5 * halka.sum():
            ic[sl] |= m
ic &= ~nesne                                    # nesnenin kendi kreme yakin pikselleri (beyaz cerceve) kutu ici degildir
ic = ndi.binary_dilation(ic, iterations=3) & ~nesne & ~cekirdek | (ic)
B = W.copy()
T = W + 0.6 * (C - W)
B[ic] = T[ic]
# ic alanin yazi kenarlari da ayni zemini gorsun: ic bolgeye yakin pikseller icin B = T
ic_yakin = ndi.binary_dilation(ic, iterations=6)
B[ic_yakin] = T[ic_yakin]

# yazi/cizgi cekirdegi = nesne disi cekirdek; satirlar
yazi = cekirdek & ~nesne
sat_lab, sat_n = ndi.label(ndi.binary_dilation(yazi, structure=np.ones((5, 25))))
sat_lab = sat_lab * yazi
Fp_oran = np.ones((sat_n + 1, 3), np.float32)
satirlar = []
for i, sl in enumerate(ndi.find_objects(sat_lab), 1):
    if sl is None:
        continue
    m = sat_lab[sl] == i
    renkler = A[sl][m]
    F = np.median(renkler[renkler.mean(1) <= np.percentile(renkler.mean(1), 30)], 0)
    kutu = (sl[1].start, sl[0].start, sl[1].stop, sl[0].stop)
    zb = B[sl[0].start:sl[0].stop, sl[1].start:sl[1].stop]
    lw = float(np.percentile(lum(zb.reshape(-1, 3)), 5))
    cizgi = (kutu[3] - kutu[1]) <= 6 and (kutu[2] - kutu[0]) >= 150     # ince ayirici cizgi (yazi degil): degismez
    F2 = F.copy() if cizgi else np.array(yazi_rengi(F, lw), np.float32)
    Fp_oran[i] = np.where(F > 1, F2 / np.maximum(F, 1), 1)
    satirlar.append(dict(kutu=[int(v) for v in kutu], renk=[int(v) for v in F2], onayli_renk=[int(v) for v in F],
                         kontrast=round(kontrast(float(lum(F2)), lw), 2), acik=bool(cizgi), zemin_lum=lw,
                         yukseklik=int(kutu[3] - kutu[1])))

# en yakin cekirdek pikseli (renk + satir kimligi)
uz, (iy, ix) = ndi.distance_transform_edt(~cekirdek, return_indices=True)
F_px = A[iy, ix]
oran_px = Fp_oran[sat_lab[iy, ix]]
v = F_px - C
a = np.clip(((A - C) * v).sum(2) / np.maximum((v * v).sum(2), 1), 0, 1)[..., None]

out = B.copy()
kenar = (~zemin) & (uz <= 2) & ~nesne
out[kenar] = (a * (F_px * oran_px) + (1 - a) * B)[kenar]
cek_yazi = yazi
out[cek_yazi] = (A * Fp_oran[sat_lab])[cek_yazi]
golge = (~zemin) & (uz > 2) & ~nesne & (A.mean(2) < C.mean())
out[golge] = (B * (A / C))[golge]
diger = (~zemin) & (uz > 2) & ~nesne & ~golge
out[diger] = (A + (B - C))[diger]
out[nesne] = A[nesne]
Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8)).save(CIK, quality=95, subsampling=0)
# poster = ici degismeyen nesneler (NCC ile onayli kartla birebir olculur); kutu ici krem tasiyanlar (08) 'kutu'
_poster = [k for k in nesne_kutu if not ic[k[1]:k[1] + k[3], k[0]:k[0] + k[2]].any()]
_kutu = [k for k in nesne_kutu if k not in _poster]
json.dump(dict(satirlar=satirlar, poster=[list(map(int, k)) for k in _poster], kutu=[list(map(int, k)) for k in _kutu],
               ic_alan_px=int(ic.sum())),
          open(os.path.splitext(CIK)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
kk = [s for s in satirlar if not s['acik']]
print(f"{os.path.basename(CIK)}: nesne {len(nesne_kutu)} | yazi satiri {len(satirlar)} (koyu {len(kk)}) | "
      f"koyulasan {sum(1 for s in kk if s['renk'] != s['onayli_renk'])} | kontrast min "
      f"{min((s['kontrast'] for s in kk), default=0):.2f} | kutu ici krem {int(ic.sum())} px")
