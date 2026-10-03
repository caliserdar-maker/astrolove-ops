#!/usr/bin/env python3
"""DB ton esitleme (Serdar 3 Eki) iki yonlu test: kucuk ton farki (olculen DB FAIL'leri) esitlenip kapidan GECER;
gercek renk sapmasi (koyu / gumus mesaj) ve acik zemin esitlenmez, kapida KALIR. Esikler AYNI (DE_ESIK, KONTRAST_ESIK)."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mesaj_kapisi as mk  # noqa: E402

ISIM = (238, 194, 77)                               # AQUARIUS_CAPRICORN DB 11x14 isim murekkebi (yerel olcum)
ISIM_BANT, TAG_BANT = (300, 360), (500, 540)        # 2400 biriminde (k = 1)


def poster(mesaj_rgb, zemin=(0, 0, 0)):
    im = Image.new('RGB', (2400, 800), zemin)
    d = ImageDraw.Draw(im)
    for x in range(300, 2100, 120):                 # isim / mesaj 'glifleri': kalin dikey cubuklar + yildiz
        d.rectangle((x, ISIM_BANT[0], x + 60, ISIM_BANT[1]), fill=ISIM)
        d.rectangle((x + 20, TAG_BANT[0], x + 70, TAG_BANT[1]), fill=mesaj_rgb)
    d.rectangle((150, 520, 156, 526), fill=(230, 230, 230))
    return im


def olc(im, esitle):
    if esitle:
        im, b = mk.ton_esitle(im, ISIM_BANT, TAG_BANT, 1.0)
    else:
        b = None
    return mk.kapi(im, ISIM_BANT, TAG_BANT, 1.0), b


def test():
    # 1) olculen DB sapmasi (iki yon): esitlemesiz FAIL, esitlemeli PASS
    for m in ((228, 172, 68), (243, 214, 110), (238, 195, 48)):  # AQUARIUS_CAPRICORN, LEO_SAGITTARIUS, ARIES_LEO B orani
        r0, _ = olc(poster(m), False)
        r1, b = olc(poster(m), True)
        assert not r0['gecti'] and r1['gecti'] and b['uygulandi'], (m, r0, r1, b)
    # 2) gercek sapmalar esitlemeyle de FAIL: %35 koyu, gumus, turuncu-kirmizi
    for m in ((155, 126, 50), (200, 200, 200), (230, 110, 40), (238, 194, 20), (238, 194, 160)):  # + yalniz B bozuk
        r1, b = olc(poster(m), True)
        assert not r1['gecti'], (m, r1, b)
    # 2b) soluk ve doygun mesaj (dE > DB_TON_DE_AZAMI): esitleme HIC uygulanmaz
    for m in ((238, 194, 160), (238, 194, 20)):
        _, b = olc(poster(m), True)
        assert b['uygulandi'] is False, (m, b)
    # 3) acik zemin (DB disi): uygulanmaz
    _, b = olc(poster((228, 172, 68), zemin=(230, 220, 200)), True)
    assert b['uygulandi'] is False, b
    # 4) yildiz (beyaz) degismez
    im, _ = mk.ton_esitle(poster((228, 172, 68)), ISIM_BANT, TAG_BANT, 1.0)
    assert np.asarray(im)[523, 153].tolist() == [230, 230, 230]
    print('PASS test_db_ton')


if __name__ == '__main__':
    test()
