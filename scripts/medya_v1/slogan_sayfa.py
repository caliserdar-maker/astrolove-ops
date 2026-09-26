#!/usr/bin/env python3
"""Slogan temizligi ONAY SAYFASI (Serdar 2. madde, 25 Eyl 2026).

PLATES/SLOGAN_KIRPIM altindaki once/sonra x3 kirpimlarini TEK SAYFADA toplar:
5 edisyon x istenen boylar. Serdar onaylamadan plate'ler uretimde kullanilmaz.
SALT OKUR: yalniz kirpimlari indirir, birlestirir, Drive'a tek dosya yazar.
"""
import argparse, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
KIRPIM = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES/SLOGAN_KIRPIM'
CIK = 'gdrive:ASTROLOVE/TEMP/SIPARIS_ISIM/PLATES'
W = Path('_sayfa').resolve(); W.mkdir(exist_ok=True)
EDISYONLAR = ['BLUE', 'BLACK', 'PURE_WHITE', 'MODERN', 'VINTAGE']
GENISLIK = 2200


def rc(*a, timeout=900):
    r = subprocess.run(['rclone', '--timeout', '120s', '--retries', '3', *a],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f'rclone {a[:2]}: {r.stderr[-300:]}')
    return r.stdout


def _bloklar(yol):
    """Kirpimi ONCE/SONRA bloklarina ayirir.

    Piksel tahminiyle DEGIL, plate_uret.slogan_kirpim'in kendi yerlesiminden:
    y=4'te etiket, +18'de goruntu, blok bitince +26 pay, sonra ayni sey.
    Iki blok ayni serit ve ayni buyutmeden geldigi icin esit yuksekliktedir:
        H = 2h + 78  ->  h = (H - 78) / 2
    Parlakliga bakan eski ayirma PURE_WHITE'ta cokuyordu (zemin 255, etiket
    seridinden ayirt edilemiyor); bu yerlesim tum edisyonlarda ayni.
    """
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    h = (a.shape[0] - 78) // 2
    if h < 20:
        return None, None
    once, sonra = a[22:22 + h], a[h + 48:h + 48 + h]
    n = min(once.shape[0], sonra.shape[0])
    return once[:n], sonra[:n]


def kalinti_olc(yol):
    """SONRA blogunda kalan slogan izini OLCER.

    ONEMLI (26 Eyl olcumu): maskeyi "ONCE'de koyu olan piksel" diye kurmak
    YANLIS sonuc verir - bandin icinde slogan DISI, temizlenMEmesi gereken
    ogeler de koyudur (Champagne 30x40'ta kirpimin ust/alt satirlarinda
    ONCE=SONRA=177). O maske ile olculen fark (15.2) slogan kalintisi degil,
    o ogelerin kendisidir. Dogru maske DEGISEN pikseldir: |ONCE - SONRA|.
    Kalinti = SONRA'nin o maskede yerel zeminden sapmasi; yerel zemin satir
    bazli medyandir, cunku bantta dusey gradyan var (209.5 -> 204.5).
    """
    import cv2
    once, sonra = _bloklar(yol)
    if once is None:
        return {'hata': 'blok ayrilamadi'}
    degisim = np.abs(once - sonra)
    m = cv2.dilate((degisim > 8).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if m.sum() < 200 or (~m).sum() < 200:
        return {'hata': 'temizlenen alan bulunamadi'}
    # Yerel zemin: her satirda maske DISI piksellerin medyani (gradyani izler).
    zemin = np.zeros_like(sonra)
    for y in range(sonra.shape[0]):
        d = sonra[y][~m[y]]
        zemin[y] = np.median(d) if d.size >= 20 else np.median(sonra[y])
    sap_s = np.abs(sonra - zemin)[m]
    sap_o = np.abs(once - zemin)[m]
    return {'temizlenen_oran': round(float(m.mean()), 4),
            'ONCE_sapma_ort': round(float(sap_o.mean()), 2),
            'SONRA_sapma_ort': round(float(sap_s.mean()), 2),
            'SONRA_sapma_p99': round(float(np.percentile(sap_s, 99)), 2),
            'SONRA_sapma_tepe': round(float(sap_s.max()), 2),
            'iyilesme_orani': round(float(sap_s.mean() / max(sap_o.mean(), 1e-6)), 3)}


def kalinti_olc2(yol):
    """DOKU-BAGISIK kalinti olcumu (26 Eyl, Serdar onayli yeni olcut).

    Eski olcut zemini SATIR MEDYANI aliyordu; dokulu edisyonda doku da
    "kalinti" sayiliyordu. Burada zemin dokuyu IZLEYEN medyandir (yaricap 41,
    glif kalinligindan buyuk), ve olcum maske ICI ile DISI arasinda yapilir:
    maskenin disina hic dokunulmadigi icin orasi zeminin kendi dokusudur.
      fark = ic_p99 - dis_p99   -> zeminin kendi dokusunun USTUNDE kalan iz.
    Olculen (26 Eyl): PURE_WHITE +4, BLUE +16, MODERN +143. WP'de zemin
    dokusu p99 81'e ciktigi icin bu olcut de WP'yi ayirt EDEMEZ - orada
    sonuc 'olculemedi' olarak dondurulur, temiz sayilmaz.
    """
    import cv2
    once, sonra = _bloklar(yol)
    if once is None:
        return {'hata': 'blok ayrilamadi'}
    m = cv2.dilate((np.abs(once - sonra) > 10).astype(np.uint8),
                   np.ones((5, 5), np.uint8)) > 0
    if m.sum() < 200 or (~m).sum() < 200:
        return {'hata': 'temizlenen alan bulunamadi'}
    z = cv2.medianBlur(np.clip(sonra, 0, 255).astype(np.uint8), 41).astype(np.float32)
    ic, dis = np.abs(sonra - z)[m], np.abs(sonra - z)[~m]
    o_ic = np.abs(once - z)[m]
    ic99, dis99 = float(np.percentile(ic, 99)), float(np.percentile(dis, 99))
    d = {'ONCE_ic_ort': round(float(o_ic.mean()), 2),
         'SONRA_ic_ort': round(float(ic.mean()), 2),
         'ic_p99': round(ic99, 1), 'dis_p99': round(dis99, 1),
         'FARK': round(ic99 - dis99, 1)}
    # Zemin dokusu glif sinyaliyle ayni buyuklukteyse olcut ayirt edemez.
    d['sonuc'] = ('olculemedi (zemin dokusu cok guclu)' if dis99 > 40
                  else 'TEMIZ' if d['FARK'] <= 4 else 'IZ VAR')
    return d


def kenar_olc(yol):
    """SOBEL kenar enerjisi olcutu (GOREV_0014: Codex'in bagimsiz yontemi).

    Sapma tabanli olcut (kalinti_olc2) ile ayni sonucu vermiyor: Codex 08:11
    sayfasinda 10 blogun 9'unda iz gordu, benim olcutum BLUE/PURE_WHITE'i
    temiz sayiyordu. Iki olcut farkli seye duyarli:
      - sapma: kalintinin PARLAKLIK farki (dokuya karisir)
      - kenar : kalintinin KENAR enerjisi (harf konturu dokudan keskindir)
    Kural (GOREV_0014): iki olcut de temiz demeden TEMIZ yazilmaz.
    """
    import cv2
    once, sonra = _bloklar(yol)
    if once is None:
        return {'hata': 'blok ayrilamadi'}
    m = cv2.dilate((np.abs(once - sonra) > 10).astype(np.uint8),
                   np.ones((5, 5), np.uint8)) > 0
    if m.sum() < 200 or (~m).sum() < 200:
        return {'hata': 'temizlenen alan bulunamadi'}
    def enerji(a):
        gx = cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3)
        return np.abs(gx) + np.abs(gy)
    e_s, e_o = enerji(sonra), enerji(once)
    ic, dis = float(e_s[m].mean()), float(e_s[~m].mean())
    o_ic = float(e_o[m].mean())
    # Duz zeminde (PURE_WHITE, DEEP_BLACK) cevre kenar enerjisi ~0 oldugu icin
    # oran patliyor (olculdu: PURE_WHITE 42.8, BLACK 146.7 - ikisi de anlamsiz).
    # O yuzden iki olcut: oran YALNIZ dokulu zeminde, duz zeminde MUTLAK fark.
    duz = dis < 1.0
    oran = ic / max(dis, 1e-6)
    d = {'SONRA_ic_kenar': round(ic, 2), 'SONRA_dis_kenar': round(dis, 2),
         'ONCE_ic_kenar': round(o_ic, 2), 'oran': round(oran, 3),
         'SONRA/ONCE': round(ic / max(o_ic, 1e-6), 3), 'zemin': 'duz' if duz else 'dokulu'}
    d['sonuc'] = ('TEMIZ' if ic <= dis + KENAR_MUTLAK else 'IZ VAR') if duz else \
                 ('TEMIZ' if oran <= KENAR_ESIK else 'IZ VAR')
    return d


def kontrast_ger(yol, cik, pay=18.0):
    """Kirpimi yerel zemin etrafinda +-pay seviyeye gerer: goz kalintiyi boyle gorur.

    Kontrast germeden 15-20 seviyelik bir kontur acik zeminde zor secilir;
    onay sayfasinda "gormedim" ile "yok" karismasin diye gerilmis kopya da konur.
    """
    a = np.asarray(Image.open(yol).convert('L')).astype(np.float32)
    z = float(np.median(a[a > np.percentile(a, 20)])) if a.mean() > 128 else float(np.median(a))
    g = np.clip((a - (z - pay)) / (2 * pay) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(g).save(cik)
    return cik


ESIK_P99 = 10.0          # leke kapisiyla ayni esik: bant disi p99 <= 10
KENAR_ESIK = 1.25        # Sobel, DOKULU zemin: ic kenar enerjisi / cevre
KENAR_MUTLAK = 2.0       # Sobel, DUZ zemin: ic <= dis + bu (oran patliyor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--boylar', default='30x40,A3')
    a = ap.parse_args()
    boylar = [x.strip() for x in a.boylar.split(',') if x.strip()]
    rc('copy', KIRPIM, str(W), '--include', '*.jpg')
    # ONEMLI: bir plate once GECER (SLOGAN_<ed>_<boy>) sonraki kosuda KALIR
    # (SLOGAN_KALDI_<ed>_<boy>) - ya da tersi. Iki ad da Drive'da kalir ve
    # yanlisini secmek ESKI kosunun sonucunu yeni sanmaya yol acar (26 Eyl'de
    # tam bunu yasadik). Her zaman DAHA YENI dosya secilir.
    def yeni_olan(ed, boy):
        adlar = [W / f'SLOGAN_{ed}_{boy}_x3.jpg', W / f'SLOGAN_KALDI_{ed}_{boy}_x3.jpg']
        varlar = [f for f in adlar if f.exists()]
        if not varlar:
            return None, False
        f = max(varlar, key=lambda x: x.stat().st_mtime)
        return f, f.name.startswith('SLOGAN_KALDI_')
    satirlar, eksik, olcumler = [], [], {}
    for boy in boylar:
        for ed in EDISYONLAR:
            f, kaldi = yeni_olan(ed, boy)
            if f is None:
                eksik.append(f'{ed}_{boy}')
                continue
            o = kalinti_olc(f)
            olcumler[f'{ed}_{boy}'] = o
            if 'hata' in o:
                et = f'{ed}  {boy}   |  OLCULEMEDI: {o["hata"]}'
            else:
                sonuc = 'TEMIZ' if o['SONRA_sapma_p99'] <= ESIK_P99 else 'KONTUR KALDI'
                o2 = kalinti_olc2(f)
                olcumler[f'{ed}_{boy}_DOKU_BAGISIK'] = o2
                o3 = kenar_olc(f)
                olcumler[f'{ed}_{boy}_KENAR'] = o3
                ek = ('' if 'hata' in o2 else
                      f'   || sapma: FARK {o2["FARK"]:+} -> {o2["sonuc"]}')
                ek += ('' if 'hata' in o3 else
                       f'   || kenar: oran {o3["oran"]} (esik {KENAR_ESIK})'
                       f' -> {o3["sonuc"]}')
                if 'hata' not in o2 and 'hata' not in o3:
                    ek += ('   ==> TEMIZ' if (o2['sonuc'] == 'TEMIZ'
                                              and o3['sonuc'] == 'TEMIZ')
                           else '   ==> TEMIZ DEGIL')
                et = (f'{ed}  {boy}   |  {sonuc}   temizlenen %{o["temizlenen_oran"] * 100:.1f}'
                      f'   sapma {o["ONCE_sapma_ort"]} -> {o["SONRA_sapma_ort"]}'
                      f'   p99 {o["SONRA_sapma_p99"]} (esik {ESIK_P99:.0f}){ek}')
            if kaldi:
                et += '   [plate KAPIDA KALDI]'
            ger = kontrast_ger(f, W / (f.stem + '_ger.png'))
            satirlar.append((et, Image.open(f).convert('RGB'),
                             Image.open(ger).convert('RGB')))
    if not satirlar:
        raise SystemExit(f'hic kirpim yok (eksik: {eksik})')
    parcalar = []
    for ad, im, gi in satirlar:
        if im.width != GENISLIK:
            im = im.resize((GENISLIK, round(im.height * GENISLIK / im.width)), Image.LANCZOS)
            gi = gi.resize((GENISLIK, round(gi.height * GENISLIK / gi.width)), Image.LANCZOS)
        parcalar.append((ad, im, gi))
    bas = 100
    yuk = bas + sum(i.height + g.height + 58 for _, i, g in parcalar) + 20
    t = Image.new('RGB', (GENISLIK + 40, yuk), 'white')
    d = ImageDraw.Draw(t)
    d.text((20, 14), 'SLOGAN TEMIZLIGI - ONAY SAYFASI   (her blokta ustte ONCE, altta SONRA, x3)',
           fill='black')
    d.text((20, 32), f'{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")} UTC'
                     + (f'   EKSIK: {", ".join(eksik)}' if eksik else ''), fill='black')
    d.text((20, 54), 'SAPMA = temizlenen piksellerin yerel zeminden farki (0-255). '
                     'Kucuk = temiz. Olcum yalniz DEGISEN piksellerde.', fill='black')
    d.text((20, 72), 'Alttaki soluk kopya KONTRAST GERILMIS (+-18 seviye): '
                     'ciplak gozle secilmeyen kontur burada gorunur.', fill='black')
    y = bas
    for ad, im, gi in parcalar:
        d.text((20, y), ad, fill='black')
        t.paste(im, (20, y + 16))
        t.paste(gi, (20, y + 16 + im.height + 4)); y += im.height + gi.height + 58
    ad = 'SLOGAN_ONAY_SAYFASI.jpg'
    t.save(W / ad, quality=94)
    rc('copy', str(W / ad), CIK, timeout=900)
    import json
    # _DOKU_BAGISIK kayitlari ayri bir olcut; onlarda SONRA_sapma_p99 yok.
    gecen = [k for k, v in olcumler.items()
             if not k.endswith(('_DOKU_BAGISIK', '_KENAR')) and 'hata' not in v
             and v['SONRA_sapma_p99'] <= ESIK_P99]
    ek_k = {k for k in olcumler if k.endswith(('_DOKU_BAGISIK', '_KENAR'))}
    db = {k: v for k, v in olcumler.items() if k.endswith('_DOKU_BAGISIK')}
    db_temiz = [k for k, v in db.items() if v.get('sonuc') == 'TEMIZ']
    kn = {k: v for k, v in olcumler.items() if k.endswith('_KENAR')}
    kn_temiz = [k for k, v in kn.items() if v.get('sonuc') == 'TEMIZ']
    # GOREV_0014: iki olcut de temiz demeden TEMIZ sayilmaz.
    ikisi = sorted({k[:-14] for k in db_temiz} & {k[:-6] for k in kn_temiz})
    print(json.dumps({'dosya': ad, 'px': list(t.size), 'blok': len(parcalar),
                      'esik_p99': ESIK_P99, 'temiz': gecen,
                      'temiz_sayi': f'{len(gecen)}/{len(olcumler) - len(ek_k)}',
                      'doku_bagisik_temiz': f'{len(db_temiz)}/{len(db)}',
                      'kenar_temiz': f'{len(kn_temiz)}/{len(kn)}',
                      'IKI_OLCUT_DE_TEMIZ': ikisi,
                      'eksik': eksik, 'olcumler': olcumler}, indent=1))


if __name__ == '__main__':
    main()
