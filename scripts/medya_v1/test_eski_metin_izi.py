"""ESKI METIN IZI kapisi (1 Eki 2026, siparis 4188621967): yeni mesajin arkasinda eski motto izi.
Sentetik: kaynak = eski slogan; cikti = zemin + yeni mesaj + eski sloganin `a` gri seviye izi. Koyu duz,
dokulu acik zemin. Iz yok -> PASS; 2 seviye ve ustu iz -> FAIL; yeni metin eski glifin uzerine binse de olcum
yalniz yeni maskenin DISINDA."""
import io
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from scripts.medya_v1 import test_plate_slogan as tps

sd = getattr(tps, 'sd', None)


@unittest.skipUnless(tps.HAZIR, 'kisisel-v1 modulleri yok (KISISEL_YOL)')
class EskiMetinIzi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.font = str(Path(tps.KY).parents[1] / 'assets' / 'fonts' / 'Cinzel.ttf')

    def durum(self, koyu, doku, a):
        kaynak, renk = tps.sayfa(koyu, doku, self.font)
        z = np.asarray(tps.zemin(koyu, doku)).astype(np.float32)
        # eski slogan glif maskesi (yumusak) -> a seviye iz
        m = Image.new('L', (tps.W, tps.H), 0)
        ImageDraw.Draw(m).text((1200, 2650), 'Two Souls  One Bond', font=ImageFont.truetype(self.font, 62),
                               fill=255, anchor='mm')
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)[..., None] / 255.0
        yon = 1.0 if koyu else -1.0
        c = z + yon * a * m
        cikti = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8))
        yeni = Image.new('L', (tps.W, tps.H), 0)
        ImageDraw.Draw(cikti).text((1200, 2660), 'A King and his Crab', font=ImageFont.truetype(self.font, 66),
                                   fill=renk, anchor='mm')
        ImageDraw.Draw(yeni).text((1200, 2660), 'A King and his Crab', font=ImageFont.truetype(self.font, 66),
                                  fill=255, anchor='mm')
        b = io.BytesIO(); kaynak.save(b, 'PNG')
        return sd.eski_metin_izi_kapisi(cikti, b.getvalue(), [2610, 2690], [780, 1620], np.asarray(yeni) > 8)

    def yildizli(self, a, tx):
        """Bandin iki yaninda tasarim yildizi (kaynak + cikti ayni; siparis 4188621967 DB 11x14: x 281 / 2094)."""
        kaynak, renk = tps.sayfa(True, False, self.font)
        z = np.asarray(tps.zemin(True, False)).astype(np.float32)
        m = Image.new('L', (tps.W, tps.H), 0)
        ImageDraw.Draw(m).text((1200, 2650), 'Two Souls  One Bond', font=ImageFont.truetype(self.font, 62),
                               fill=255, anchor='mm')
        m = np.asarray(m.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)[..., None] / 255.0
        cikti = Image.fromarray(np.clip(z + a * m, 0, 255).astype(np.uint8))
        yeni = Image.new('L', (tps.W, tps.H), 0)
        for im, f in ((cikti, renk), (yeni, 255)):
            ImageDraw.Draw(im).text((1200, 2660), 'A King and his Crab', font=ImageFont.truetype(self.font, 66),
                                    fill=f, anchor='mm')
        kaynak = kaynak.copy()
        for im in (kaynak, cikti):
            for x in (281, 2094):
                ImageDraw.Draw(im).ellipse((x - 6, 2642, x + 6, 2657), fill=renk)
        b = io.BytesIO(); kaynak.save(b, 'PNG')
        bi = {'olcum': {'tag_bant': [2610, 2690]}, 'plate_slogan_kapisi': {'tag_x': tx}}
        return sd._iz_kapisi(cikti, b.getvalue(), bi, {'yeni': np.asarray(yeni) > 8})

    def test_yildiz_eski_glif_sayilmaz(self):
        # eski sabit pencere [300, 2100] (+40) yildizlari eski glif sayiyordu: iz yokken FAIL (hata kaniti)
        self.assertFalse(self.yildizli(0, None)['gecti'])
        r0 = self.yildizli(0, [780, 1620])
        self.assertTrue(r0['gecti'], r0); self.assertEqual(r0['x_kaynagi'], 'plate_slogan_kapisi')
        r2 = self.yildizli(2, [780, 1620])                        # gercek iz hala yakalanir
        self.assertFalse(r2['gecti'], r2)

    def test_koyu(self):
        olc = {a: self.durum(True, False, a) for a in (0, 1, 1.5, 2, 3, 6)}
        print('koyu', {a: (r.get('fazla'), r['gecti']) for a, r in olc.items()})
        self.assertTrue(olc[0]['gecti']); self.assertFalse(olc[2]['gecti'])
        self.assertFalse(olc[3]['gecti']); self.assertFalse(olc[6]['gecti'])

    def test_dokulu_acik(self):
        olc = {a: self.durum(False, True, a) for a in (0, 1, 1.5, 2, 3, 6)}
        print('acik', {a: (r.get('fazla'), r['gecti']) for a, r in olc.items()})
        self.assertTrue(olc[0]['gecti']); self.assertFalse(olc[3]['gecti']); self.assertFalse(olc[6]['gecti'])

    def test_plate_iz_temizligi(self):
        import plate_iz_temizle as pit
        for koyu, doku, ed in ((True, False, 'black'), (False, True, 'vintage')):
            kaynak, renk = tps.sayfa(koyu, doku, self.font)
            z = np.asarray(tps.zemin(koyu, doku)).astype(np.float32)
            m = Image.new('L', (tps.W, tps.H), 0)
            ImageDraw.Draw(m).text((1200, 2650), 'Two Souls  One Bond', font=ImageFont.truetype(self.font, 62),
                                   fill=255, anchor='mm')
            m = np.asarray(m.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)[..., None] / 255
            plate = np.clip(z + (1 if koyu else -1) * 5 * m, 0, 255).astype(np.uint8)
            b = io.BytesIO(); kaynak.save(b, 'PNG'); kb = b.getvalue()
            yeni, M, _ = pit.temizle(plate, [kb], ed)
            bos = np.zeros(plate.shape[:2], bool)
            once = sd.eski_metin_izi_kapisi(Image.fromarray(plate), kb, [2610, 2690], [780, 1620], bos)
            sonra = sd.eski_metin_izi_kapisi(Image.fromarray(yeni), kb, [2610, 2690], [780, 1620], bos)
            self.assertFalse(once['gecti']); self.assertTrue(sonra['gecti'], sonra)
            fark = np.abs(yeni.astype(int) - plate.astype(int)).max(2) > 0
            self.assertEqual(int((fark & ~M).sum()), 0)


if __name__ == '__main__':
    unittest.main()
