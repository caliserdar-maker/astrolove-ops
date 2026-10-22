#!/usr/bin/env python3
"""Isim bandi kalintisi (GIFT_9518 bulgusu, 29 Eyl): SAHTE veri.

Gercek durum (3. iterasyonda olculdu): medyan PLATE'in isim bandinda eski yazi uclari var. Baski =
kirli plate + yeni isimler + sonsuzluk; bandin hemen ustunde altin semboller (dolguya girmemeli).
- temizliksiz baski: isim_kalinti_kapisi FAIL (plate'ten bagimsiz, yerel zemine gore)
- isim_bandi_temizle ile: PASS; yeni oge kaydina dokunulmaz, bant/sutun disi degismez,
  lekeler zemin seviyesine iner, semboller banda kopyalanmaz.
Koyu (Deep Black / Midnight Blue) ve acik (Pure White) zemin.
"""
import os
import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

KY = os.environ.get('KISISEL_YOL', '')
if KY:
    sys.path.insert(0, KY)
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import cv2
    import siparis_dosyasi as sd
    HAZIR = True
except Exception:                                                 # noqa: BLE001
    HAZIR = False

W, H = 2400, 3000
ALTIN = (214, 170, 92)
OLCUM = {'sembol_bant': [2010, 2150], 'isim_bant': [2200, 2290], 'tag_bant': [2560, 2640],
         'sol_isim': [470, 770], 'sag_isim': [1580, 1980]}
LEKELER = [(560, 2282, 10, 3), (600, 2283, 4, 2), (1745, 2203, 3, 3), (1752, 2286, 3, 1)]


def zemin(koyu):
    rng = np.random.default_rng(5)
    a = np.zeros((H, W, 3), np.float32) + ((6, 9, 28) if koyu else (246, 244, 240))
    a += rng.normal(0, 1.0, (H, W, 1))
    if koyu:                                            # yildizlar (altin degil)
        for _ in range(3000):
            y, x = rng.integers(0, H), rng.integers(0, W)
            a[y:y + 2, x:x + 2] = (200, 210, 235)
    return np.clip(a, 0, 255).astype(np.uint8)


def yaz(a, metinler, font, y=2245):
    im = Image.fromarray(a.copy())
    d = ImageDraw.Draw(im)
    for x, t in metinler:
        d.text((x, y), t, anchor='mm', fill=ALTIN, font=font)
    return np.asarray(im)


@unittest.skipUnless(HAZIR, 'siparis_dosyasi ice aktarilamadi')
class IsimKalintiTesti(unittest.TestCase):
    font = str(Path(KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf') if KY else ''

    def kos(self, koyu):
        f = ImageFont.truetype(self.font, 88)
        pl = zemin(koyu).copy()
        for x, y, w, h in LEKELER:                      # KIRLI PLATE: eski yazi uclari
            pl[y:y + h, x:x + w] = (164, 126, 32)
        yeni = [(820, 'LIZ'), (1200, '~'), (1580, 'ZACH')]
        semb = yaz(pl, [(620, 'M'), (1780, 'M')], ImageFont.truetype(self.font, 150), y=2080)
        baski = yaz(semb, yeni, f).astype(np.float32)
        yk = yaz(np.zeros_like(pl), yeni, f).max(axis=2) > 12
        sk = yaz(np.zeros_like(pl), [(620, 'M'), (1780, 'M')],
                 ImageFont.truetype(self.font, 150), y=2080).max(axis=2) > 12
        Y = cv2.dilate((yk | sk).astype(np.uint8),
                       cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))) > 0
        b_eski = Image.fromarray(np.clip(baski, 0, 255).astype(np.uint8))
        k_eski = sd.isim_kalinti_kapisi(b_eski, Y, OLCUM)
        yeni_out, bilgi = sd.isim_bandi_temizle(baski, Y, OLCUM)
        b_yeni = Image.fromarray(np.clip(yeni_out, 0, 255).astype(np.uint8))
        k_yeni = sd.isim_kalinti_kapisi(b_yeni, Y, OLCUM)
        self.assertFalse(k_eski['gecti'], k_eski)
        self.assertGreaterEqual(k_eski['kalinti_sayisi'], 3, k_eski)
        self.assertTrue(bilgi['uygulandi'], bilgi)
        self.assertTrue(k_yeni['gecti'], k_yeni)
        Bn, Be = np.asarray(b_yeni), np.asarray(b_eski)
        self.assertTrue((Bn[Y] == Be[Y]).all())                         # yeni oge kaydi aynen
        r0, r1 = bilgi['satir']; c0, c1 = bilgi['sutun']
        dis = np.ones((H, W), bool); dis[r0:r1, c0:c1] = False
        self.assertTrue((Bn[dis] == Be[dis]).all())                     # bolge disi aynen
        for x, y, w, h in LEKELER:                                      # lekeler gitti
            self.assertLess(sd.nokta_olc(b_yeni, x + w // 2, y + h // 2, yeni=Y), sd.ISIM_KALINTI_ESIK)
            self.assertGreater(sd.nokta_olc(b_eski, x + w // 2, y + h // 2, yeni=Y), sd.ISIM_KALINTI_ESIK)
        # yeni harfe bitisik nokta: harf olcumden cikar (pencere harfe tasiyor)
        ys, xs = np.nonzero(yk)
        self.assertLess(sd.nokta_olc(b_yeni, int(xs.min()) - 4, int(ys.max()) - 2, yeni=Y), sd.ISIM_KALINTI_ESIK)
        # sembol altin murekkebi banda kopyalanmadi: bantta yeni disi altin yok (kapi zaten PASS)
        return k_eski, k_yeni

    def kos_ham(self, koyu):
        """4. iterasyon: koruma = HAM harf maskesi; harfe 2-3 px bitisik SOLUK iz (MB olcumu:
        37,22,27 / zemin 0,6,32) temizlenir, harf kenari kesilmez."""
        f = ImageFont.truetype(self.font, 88)
        pl = zemin(koyu).copy()
        yeni = [(820, 'LIZ'), (1200, '~'), (1580, 'ZACH')]
        yk = yaz(np.zeros_like(pl), yeni, f).max(axis=2) > 8
        ys, xs = np.nonzero(yk[:, :900])
        # L ic kosesi: ayak ustunde, harften 2 px yukarida; I sag alti: govdenin 2 px sagi
        ic = [(int(xs.min()) + 20, int(ys.max()) - 16, 8, 2), (int(xs.min()) + 60, int(ys.max()) - 6, 3, 3)]
        soluk = np.array((37, 22, 27) if koyu else (236, 226, 200), np.uint8)
        for x, y, w, h in ic:
            bolge = pl[y:y + h, x:x + w]
            bolge[~yk[y:y + h, x:x + w]] = soluk
        baski = yaz(pl, yeni, f).astype(np.float32)
        Y = yk.copy()
        b_eski = Image.fromarray(np.clip(baski, 0, 255).astype(np.uint8))
        k_eski = sd.isim_kalinti_kapisi(b_eski, Y, OLCUM, ham=True)
        out, bilgi = sd.isim_bandi_temizle(baski, Y, OLCUM, ham=True)
        b_yeni = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        k_yeni = sd.isim_kalinti_kapisi(b_yeni, Y, OLCUM, ham=True)
        self.assertFalse(k_eski['gecti'], k_eski)
        self.assertTrue(k_yeni['gecti'], k_yeni)
        self.assertTrue(bilgi['kenar']['gecti'], bilgi['kenar'])
        self.assertTrue((np.asarray(b_yeni)[Y] == np.asarray(b_eski)[Y]).all())
        for x, y, w, h in ic:
            kutu = (x - 2, y - 2, x + w + 2, y + h + 2)
            self.assertGreater(sd.iz_olc(b_eski, kutu, Y)['iz_px'], 0)
            self.assertEqual(sd.iz_olc(b_yeni, kutu, Y)['iz_px'], 0, sd.iz_olc(b_yeni, kutu, Y))
        # kenar kapisi kesilen harfi yakalar: korumayi 2 px daralt -> harf kenari dolguyla kesilir
        dar = cv2.erode(Y.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        _o, b2 = sd.isim_bandi_temizle(baski, dar, OLCUM, ham=True)
        self.assertFalse(b2['kenar']['gecti'], b2['kenar'])

    def test_ham_acik_sik_harf(self):
        """29 Eyl CI bulgusu: acik sicak zemin (R-B 35) + koyu kahve sik harfler (M, N ici dar zemin).
        Temiz baskida iki kapi da PASS olmali (yerel zemin harfe cekilmemeli); leke yine yakalanmali."""
        f = ImageFont.truetype(self.font, 150)             # 150: eski (harf dahil medyan) olcut 25 bilesen FAIL
        pl = np.zeros((H, W, 3), np.float32) + (241, 224, 206)
        pl += np.random.default_rng(3).normal(0, 1.0, (H, W, 1))
        pl = np.clip(pl, 0, 255).astype(np.uint8)
        yeni = [(800, 'EMMNWY'), (1200, '~'), (1650, 'MMWNM')]
        im = Image.fromarray(pl.copy()); d = ImageDraw.Draw(im)
        for x, t in yeni:
            d.text((x, 2245), t, anchor='mm', fill=(92, 58, 28), font=f)
        baski = np.asarray(im).astype(np.float32)
        Y = yaz(np.zeros_like(pl), yeni, f).max(axis=2) > 8
        out, bilgi = sd.isim_bandi_temizle(baski, Y, OLCUM, ham=True)
        b = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
        self.assertTrue(bilgi['kenar']['gecti'], bilgi['kenar'])
        k = sd.isim_kalinti_kapisi(b, Y, OLCUM, ham=True)
        self.assertTrue(k['gecti'], k)
        # leke hala yakalanir (acik zeminde soluk kahve)
        lek = baski.copy(); lek[2280:2283, 1000:1008] = (205, 180, 150)
        k2 = sd.isim_kalinti_kapisi(Image.fromarray(lek.astype(np.uint8)), Y, OLCUM, ham=True)
        self.assertFalse(k2['gecti'], k2)

    def test_parsomen_doku(self):
        """30 Eyl WP AQUARIUS_CANCER: dokulu parsomende (1) temiz baskida kapi PASS (doku iz sayilmaz),
        (2) temizlik dokuyu bozmaz (kalinti yoksa degisen ~0, parlak leke yok), (3) gercek leke yakalanir
        ve temizlenir."""
        import cv2
        rng = np.random.default_rng(11)
        doku = np.zeros((H, W), np.float32)
        for s_, a_ in ((3, 10), (9, 9), (25, 8), (70, 7)):
            g = rng.normal(0, 1, (H // s_ + 2, W // s_ + 2)).astype(np.float32)
            doku += a_ * cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC)
        pl = np.clip(np.dstack([222 + doku, 193 + 0.9 * doku, 138 + 0.8 * doku]), 0, 255).astype(np.uint8)
        f = ImageFont.truetype(self.font, 110)
        yeni = [(800, 'EMILY'), (1200, '~'), (1650, 'JAMES')]
        im = Image.fromarray(pl.copy()); d = ImageDraw.Draw(im)
        for x, t in yeni:
            d.text((x, 2245), t, anchor='mm', fill=(150, 88, 30), font=f)
        baski = np.asarray(im).astype(np.float32)
        Y = yaz(np.zeros_like(pl), yeni, f).max(axis=2) > 8
        k0 = sd.isim_kalinti_kapisi(Image.fromarray(baski.astype(np.uint8)), Y, OLCUM, ham=True)
        self.assertTrue(k0['gecti'], {q: k0.get(q) for q in ('kalinti_sayisi', 'esikler')})
        out, bilgi = sd.isim_bandi_temizle(baski, Y, OLCUM, ham=True)
        self.assertTrue(bilgi['kenar']['gecti'], bilgi['kenar'])
        fark = np.abs(out - baski).max(axis=2)
        self.assertLess(int((fark > 3).sum()), 200, bilgi)                  # doku yerinde
        self.assertLess(float(out.max()), 256)
        # gercek leke: koyu kahve eski yazi ucu (14x6)
        lek = baski.copy(); lek[2270:2276, 1000:1014] = (120, 70, 25)
        k1 = sd.isim_kalinti_kapisi(Image.fromarray(lek.astype(np.uint8)), Y, OLCUM, ham=True)
        self.assertFalse(k1['gecti'], k1)
        o2, b2 = sd.isim_bandi_temizle(lek, Y, OLCUM, ham=True)
        k2 = sd.isim_kalinti_kapisi(Image.fromarray(np.clip(o2, 0, 255).astype(np.uint8)), Y, OLCUM, ham=True)
        self.assertTrue(k2['gecti'], {q: k2.get(q) for q in ('kalinti_sayisi', 'kalintilar', 'esikler')})
        self.assertLess(int((np.abs(o2 - lek).max(axis=2) > 3).sum()), 2500, b2)

    def test_ham_koyu(self):
        self.kos_ham(True)

    def test_ham_acik(self):
        self.kos_ham(False)

    def test_koyu(self):
        self.kos(True)

    def test_acik(self):
        self.kos(False)


if __name__ == '__main__':
    unittest.main()
