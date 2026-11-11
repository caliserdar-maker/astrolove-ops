#!/usr/bin/env python3
"""AY TAKVIMI ORNEK kapilari (Serdar 10 Kas 2026): tek QC betigi, olculebilir esik, PASS / FAIL, <ad>_OLCUM.json.
Girdi: ay_takvim_ornek.py 'uret' cikti klasoru (<ad>.png + <ad>_DUMP.npz + <ad>_META.json). Olcum SON DOSYADAN (PNG) ve maskelerden yapilir.

Kapilar (sert):
  1 veri     2027: 365 gun, 13 yeni ay, 12 dolunay (yeniden hesaplanir); SON DOSYADAN evre olcumu: her gunun diski var, aydinlik alan orani
             hesaplanan oranla +- 0,15, aydinlik taraf dogru yonde (buyuyen ayda sag), yeni ay / dolunay gunlerinde (ve yalniz onlarda) isaret halkasi
  2 sembol   en boy orani farki <= 0,005; olcek <= 1; son dosyada sembol rengi kucultulmus katmanla ayni (tam alfa pikselde fark <= 1 seviye;
             yari saydam kenar pikseli = katman rengi ile zemin / golgeli zemin karisimi sinirlari icinde);
             --katman verilirse: yerlesen sembol = kaynak katmanin yalniz es oranli kucultulmusu (yeniden hesap, birebir)
  3 tek doku her altin yazi ogesi ile sembol arasinda son dosyada dE00 <= 2,0; oge basina >= 200 cekirdek piksel   [EMSAL, degistirilmez]
             oge sayimi: 1 isim satiri + 1 baslik + 12 ay adi + metin satirlari
  4 kontrast ortanca kontrast >= 4,5 (her altin yazi ogesi; ogenin 6-12 px cevre bandi, son goruntu)                 [EMSAL, degistirilmez]
             bilgi: bantta ay diski / yildiz / diger cizim pikseli orani ve bunlar cikarilmis olcum. Kod parlaklik artirmaz (karar 9).
  5 yazim    iki cizim (1x sekil, k kat renk cizimi) arasi ortalama alfa farki <= 0,035                              [EMSAL, degistirilmez]
  6 bosluk   altin yazi - en yakin ay diski >= 12 px; komsu ay diskleri (isaret halkasi dahil) >= 6 px; sembol - en yakin disk >= 150 px;
             sayfa kenari >= 180 px; altin ogeler birbirine binmez
  7 altin    altin disi ogelerde (disk, halka, yorunge, rakam) altin yok; altin yazi ogelerinde duz renk yok (oge ici parlaklik yayilimi);
             altin ogelere (12 px payla) yildiz degmez
  8 isim     isim satiri <= sayfa genisliginin %86'si; buyuk harf >= 53 px
  9 metin    <= 3 satir, satir <= 35 karakter, satir genisligi <= %86; blok dikey ortalamasi +- 6 px
  10 cikti   5400x7200, 300 dpi etiketi, sRGB
Emsal esikleri: ornament_motor.py :782-791 (dE00 2,0; alfa farki 0,035), ornament_ornek4.py:51 (kontrast 4,5), ornament_motor.py :520-524 (200 piksel).
Emsali olmayan esikler (kapi 2, 6, 7, 8, 9): Merkez baslangic degeri / yerel olcum; ornekten sonra Serdar kesinlestirir.

SEMBOL GRUBU (Serdar 11 Kas; META 'grup' varsa): halka + iki kucuk burc sembolu de altin ogedir.
  2  --motor ZORUNLU: grup kaynaktan yeniden kurulur (U.grup_kur, AYAR META'dan); her ogenin yerlesen alfasi = kaynak alfanin ayni olcekle
     TEK adim yeniden kucultulmusu (birebir); toplam olcek <= 1; tam sayi yerlesim kaymasi ile hedef arasi fark <= 1 px.
     BAGIMSIZ olcum (uretim fonksiyonuna guvenmez; hedefler motor dosyalari + bu betikteki poster sabitleri, yer / boy DUMP maskelerinden): halkaya
     uydurulan cember -> olculen merkez ve olcek; kucuk sembol merkezi (u, v) ve genisligi; ana sembol alfa kutusu yeri ve genisligi; kucuk1 solda /
     kucuk2 sagda; merkeze en uzak grup pikseli = hedef yaricap; hal 'halka'da halka merkezi takvim merkezinde; grup merkezi = disk merkezi.
     Olcum payi 2 px (iki yuvarlama + kutu nicemlemesi + cember uydurma). Yerel olcum (deneme katmani): 4 ornekte en buyuk 1,10 px; izinli ayar
     araliginda 67 noktada en buyuk 1,79 px (ana sembol yeri; sembol_alan 400 x 1,3). GERCEK Drive katmaniyla olculmedi: ilk kosuda OLCUM
     'bagimsiz.fark_en_buyuk' okunur; esik ancak olcumle ve Serdar onayiyla degisir.
     Grup yerlesiminde META 'grup' alani ZORUNLU (yoksa FAIL).
     AYAR halka_kalinlik (carpan; Serdar 11 Kas): yeniden kurulum ayni carpanla yapilir (maske birebir). Bagimsiz olcumde "en uzak piksel" olcutu
     AYNI kalir (|en uzak - hedef| <= 2 px, tek nokta): grup olcegi ozgun halkadan kuruldugu icin halka pikselleri once maskeden olculen merkez cizgisi
     etrafinda 1 / carpan oraninda iceri alinir (olculerek geri alma); ham (kalin) en uzak piksel 'en_uzak_piksel_ham' alaninda BILGI.
     Halkanin maskeden OLCULEN cizgi kalinligi (ust, en buyuk, ortanca, acisal kapsam) OLCUM 'bagimsiz.halka_kalinlik' alanina BILGI olarak yazilir.
     AYAR halka_centik / logo (Serdar 11 Kas): yeniden kurulum ayni ayarla (maske birebir; logo ayarda varsa grupta 4. oge ZORUNLU, yoksa olamaz).
     Logo bagimsiz olcumde: merkezi grup ekseninde ve kucuk sembol satirinda, boyu grup olcegi x carpan (ayni 2 px olcum payi; yeni esik yok).
     BILGI (esik yok): 'bagimsiz.halka_centik' (saat 3 basamagi px; 'yumusak'ta once / sonra ve +- 3,5 derece bandi disinda degisen maske pikseli),
     'bagimsiz.logo' (genislik / yukseklik px ve mm; her kucuk sembole en yakin piksel uzakligi; 'cakisiyor' / 'ayrik'). Logo kapi 3 / 4 / 6 / 7'de
     diger grup ogeleri gibi olculur.
  3  halka ve kucuk semboller de dE00 <= 2,0, >= 200 cekirdek piksel     4  kontrast >= 4,5 onlar icin de
  5  grup ogelerinin alfa farki yalniz BILGI (yazi cizimi degil)
  6  "sembol - disk >= 150 px" GRUBUN gercek alfa siniri (alfa > 0,02) ile en yakin disk; grup - ay adi >= 12 px
  7  kucuk semboller duz_yayilim 40; halkanin yayilimi BILGI
AYAR ve MOD (Serdar 11 Kas "A"): ayara bagli her deger (isim alt siniri = ay adi boyu, hedef yaricap, kucuk sembol yeri / boyu, katsayi)
  yalniz META 'ayar'dan okunur; U.* ya da ESIK sabitinden degil. MOD cagirandan gelir (--mod; varsayilan ornek), META mod ile uyusmazsa FAIL (sert).
  mod ornek: META ayari varsayilandan farkliysa (isim, metin, hal secimi haric) kapi 0 FAIL (esik urunden okunarak gevsetilemez).
  mod deneme: SERT = kapi 1 veri (hesap) + kapi 2 + mod tutarliligi; digerleri olculur, yazilir, cikisi etkilemez (gorsel kalir).
  SERT FAIL'de o denemenin gorselleri silinir.

Kullanim: ay_takvim_kapi.py KLASOR AD [--katman K.png] [--motor MD] [--mod ornek|deneme] [--onek]   (--onek: FAIL'de gorseller KAPI_FAIL_ onekiyle yeniden adlandirilir)
          ay_takvim_kapi.py --ozet KLASOR [--kosu N --kod SHA --motor-sha SHA --ornament-sha SHA --rc a=0,b=1]   (tum orneklerin OZET.json'u)
Cikis: 0 PASS, 1 FAIL, 2 cokus."""
import argparse
import json
import sys
import traceback
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ay_takvim_ornek as U  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ESIK = dict(
    dE00=2.0, kontrast=4.5, alfa_fark=0.035, cekirdek_piksel=200,          # EMSAL (ornament); degistirilmez
    en_boy=0.005, sembol_renk=1,                                            # kapi 2
    yazi_disk=12, disk_disk=6, sembol_disk=150, kenar=180, grup_yazi=12,    # kapi 6 (px, 5400 tuval)
    grup_konum=1.0,                                                         # kapi 2: tam sayi yerlesim kaymasi ile poster degerinden hedef arasi fark (px)
    grup_konum_olculen=2.0,                                                 # kapi 2: maskeden OLCULEN yer (alfa kutusu / uydurulan cember) ile hedef arasi fark (px)
    evre_oran=0.15, evre_yon_alt=0.2, evre_yon_ust=0.8,                     # kapi 1 evre olcumu (yerel olcum: OLCUM "evre" alani)
    altin_rb=75, altin_r=140,                                               # kapi 7a: "altin benzeri" piksel = R - B > 75 ve R > 140
    yildiz_pay=12,                                                          # kapi 7c: altin oge maskesi bu kadar genisletilir, yildiz degmemeli
    duz_yayilim=40.0,                                                       # kapi 7b: cekirdek luma p95 - p5 alt esigi (yerel olcumden; asagida not)
    gen_oran=0.86, blok_merkez=6, satir=3, karakter=35)                    # kapi 8, 9 (isim alt siniri: META ayar ay_adi_cap)
ESIK_NOT = dict(
    altin_rb='ay diski aydinlik rengi (240,226,190) R-B = 50; yerelde olculen altin cekirdek ortancasi R-B >= 100; esik arada',
    duz_yayilim='duz renkle cizilen yazi 0; yerel denemede (4 ornek, 68 oge) en dusuk altin oge yayilimi 85; esik bunun yarisinin altinda')
LUMA = np.array([0.299, 0.587, 0.114], np.float32)                           # ornament_ornek.py:43


def lum(rgb):
    return rgb @ LUMA


def kontrast(c1, c2):
    """ornament_ornek.py kontrast (:158-164): WCAG goreli parlaklik orani, 2 haneye yuvarli."""
    def L_(c):
        c = np.asarray(c, np.float64) / 255
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = sorted([L_(c1), L_(c2)])
    return round((b + 0.05) / (a + 0.05), 2)


def kontrast_olc(rgb, m, cekirdek=0.9, haric=None):
    """ornament_ornek5.py kontrast_yeni (:421-438), tur 'koyu': zemin = ogenin 6-12 px cevre bandi (son goruntu); oge = alfa >= cekirdek.
    deger: zeminin ACIK %5'i / ogenin KOYU %5'i; ortanca_bilgi: ortanca / ortanca (KAPI bu). haric: bant icinden cikarilacak maske (yalniz bilgi olcumu)."""
    ce = m >= cekirdek
    if ce.sum() < 5:
        return dict(deger=None, not_=f'alfa >= {cekirdek} murekkep yok')
    ink = (m > 0.02).astype(np.uint8)
    bant = (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) > 0) & \
           (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) == 0)
    n_bant = int(bant.sum())
    if haric is not None:
        bant = bant & ~haric
        if bant.sum() < 20:
            return dict(deger=None, not_='haric sonrasi bant bos', bant_piksel=int(bant.sum()))
    za, ea = rgb[bant].astype(np.float32), rgb[ce].astype(np.float32)
    Lz, Le = lum(za), lum(ea)
    z = np.median(za[Lz >= np.percentile(Lz, 95)], 0); e = np.median(ea[Le <= np.percentile(Le, 5)], 0)
    return dict(deger=round(float(kontrast(e, z)), 2), zemin_rgb=[int(v) for v in z], oge_rgb=[int(v) for v in e],
                ortanca_bilgi=round(float(kontrast(np.median(ea, 0), np.median(za, 0))), 2), cekirdek_piksel=int(ce.sum()),
                bant_piksel=int(bant.sum()), bant_piksel_tam=n_bant)


def evre_olc(img, liste, gunler):
    """SON DOSYADAN evre olcumu. liste: [x, y, r, dis yaricap, gun indeksi]. Disk ici (kenar cizgisi haric) piksel aydinlik renge mi
    koyu renge mi yakin -> aydinlik alan orani (beklenen: gunun oran degeri) ve aydinlik agirlik merkezinin yonu (buyuyen ayda sag).
    Isaret halkasi: r + (ISARET_DIS - ISARET_KALIN / 2) x S yaricapli cemberde aydinlik renk orani."""
    ac, ko = np.array(U.RENK_ACIK, np.float32), np.array(U.RENK_KOYU, np.float32)
    Hh, Ww = img.shape[:2]
    fark, yon_hata, halka_hata, eksik = [], [], [], []
    for x, y, r, rt, gi in liste:
        gi = int(gi)
        if not 0 <= gi < len(gunler):
            eksik.append(gi); continue
        g = gunler[gi]
        ri = r - (U.KENAR_CIZGI + 1)
        rd = r + U.ISARET_DIS * U.S
        x0, y0, x1, y1 = int(x - rd) - 2, int(y - rd) - 2, int(x + rd) + 3, int(y + rd) + 3
        if ri < 3 or x0 < 0 or y0 < 0 or x1 > Ww or y1 > Hh:
            eksik.append(gi); continue
        p = img[y0:y1, x0:x1].astype(np.float32)
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        d = np.hypot(xx - x, yy - y)
        ic = d <= ri
        acik = ((p - ac) ** 2).sum(2) < ((p - ko) ** 2).sum(2)
        oran = float(acik[ic].mean())
        fark.append(abs(oran - g['oran']))
        if ESIK['evre_yon_alt'] <= g['oran'] <= ESIK['evre_yon_ust'] and (acik & ic).any():
            sag = float((xx - x)[acik & ic].mean()) > 0
            if sag != bool(g['buyuyor']):
                yon_hata.append(gi)
        rh = r + (U.ISARET_DIS - U.ISARET_KALIN / 2.0) * U.S
        cember = np.abs(d - rh) <= 1.0
        var = bool(cember.any() and float(acik[cember].mean()) > 0.5)
        if var != bool(g['yeni'] or g['dolun']):
            halka_hata.append(gi)
    gorulen = sorted(int(v[4]) for v in liste)
    return dict(disk=len(liste), gun_tam=bool(gorulen == list(range(len(gunler)))), olculemeyen=eksik[:10],
                oran_fark_en_buyuk=round(max(fark), 4) if fark else None, oran_fark_ortalama=round(float(np.mean(fark)), 4) if fark else None,
                yon_hatasi=yon_hata[:10], halka_hatasi=halka_hata[:10],
                PASS=bool(fark and gorulen == list(range(len(gunler))) and not eksik and max(fark) <= ESIK['evre_oran'] and not yon_hata and not halka_hata))


def yatay_yayilim(a):
    """Alfa agirlikli yatay standart sapma (px): es oranli olcekte kaynak x olcek = yerlesen; kenar nicemlemesinden etkilenmez (piksel alti)."""
    w = np.asarray(a, np.float64).sum(0)
    x = np.arange(len(w)) + 0.5
    mu = float((w * x).sum() / w.sum())
    return float(np.sqrt((w * (x - mu) ** 2).sum() / w.sum()))


def halka_kalinlik_olc(m, cx, cy):
    """Halka maskesinden cizgi kalinligi (px), aci basina: 1 derecelik dilimde alfa toplami / yay uzunlugu. Doner ust (saat 12 +- 10 derece ortalamasi),
    en buyuk, ortanca (dolu dilimler) ve dolu dilim sayisi (acisal kapsam, derece). Yalniz olcum (BILGI)."""
    ys, xs = np.nonzero(m > 0)
    w = m[ys, xs].astype(np.float64)
    dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
    r = np.hypot(dx, dy)
    b = np.floor(np.degrees(np.arctan2(dy, dx)) + 180.0).astype(np.int64) % 360
    sw, sr = np.bincount(b, w, 360), np.bincount(b, w * r, 360)
    dolu = sw > 0.05
    kal = np.zeros(360)
    kal[dolu] = sw[dolu] / (np.radians(1.0) * sr[dolu] / sw[dolu])
    ust = kal[80:101]                                                         # aci -100 .. -80 derece (saat 12)
    return dict(basamak_saat3_px=round(float(kal[179] - kal[180]), 3),        # saat 3: komsu 1 derecelik dilimler ([-1, 0) ve [0, 1)) arasi kalinlik farki
                ust_px=round(float(ust.mean()), 3), ust_mm=round(float(ust.mean()) * 25.4 / U.DPI, 3), en_buyuk_px=round(float(kal.max()), 3),
                ortanca_px=round(float(np.median(kal[dolu])), 3), kapsam_derece=int(dolu.sum()))


def cember_uydur(m):
    """Halka maskesine (alfa agirlikli) en kucuk kareler cemberi (Kasa). Doner (cx, cy, r) maske koordinatinda (piksel merkezi + 0,5)."""
    ys, xs = np.nonzero(m > 0.02)
    w = m[ys, xs].astype(np.float64)
    x, y = xs + 0.5, ys + 0.5
    A = np.c_[x, y, np.ones_like(x)] * w[:, None]
    b = (x * x + y * y) * w
    (a2, b2, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = a2 / 2.0, b2 / 2.0
    return float(cx), float(cy), float(np.sqrt(c + cx * cx + cy * cy))


# kapi 2 BAGIMSIZ hedefleri (uretim kodundan OKUNMAZ; ay_takvim_ornek.KUCUK_U / KUCUK_Y degisirse burasi FAIL verir): onayli poster yeri
POSTER_KUCUK_U = {'CANCER_LIBRA': (-0.491, 0.490)}                          # kucuk sembol yatay merkezi (halka merkezine gore, R biriminde)
POSTER_KUCUK_Y = 7078.5                                                      # kucuk sembol dikey merkezi (poster pikseli; olustur_alfa_sablon.py:23)


def grup_kapisi(meta, D, katman_g, yan_json, motor, sa, sx, sy):
    """Kapi 2 grup bolumu (AYAR META'dan). Iki ayri kanit:
    (1) kaynaktan yeniden kurulum (U.grup_kur): her maske = kaynak alfanin TEK adim kucultulmusu (birebir), tam sayi yerler ayni, olcek <= 1.
    (2) BAGIMSIZ olcum (uretim fonksiyonunun hesabina guvenmez; inceleme bulgusu O1): hedefler motor dosyalarindan (cember.json, yerlesim78.json) ve
        bu betikteki poster sabitlerinden; yer / boy DUMP maskelerinden olculur: halkaya uydurulan cember (merkez, yaricap -> olculen grup olcegi),
        kucuk sembol alfa kutusu merkezi (u, v) ve genisligi, ana sembol alfa kutusu, kucuk1 solda / kucuk2 sagda, merkeze en uzak grup pikseli =
        hedef yaricap, hal 'halka'da halka merkezi takvim merkezinde, grup merkezi = disk merkezi. Olcum payi 2 px (ESIK grup_konum_olculen)."""
    AY, gb = meta['ayar'], meta['grup']
    cift = meta['cift']
    mt = U.Motor(motor)
    hedef_r = AY['grup_oran'] * AY['sembol_alan'] * U.S
    hk = float(AY.get('halka_kalinlik', 1.0))                                 # halka cizgi kalinligi carpani (AYAR; 1,0 = poster)
    hc, lg_ = AY.get('halka_centik', 'ozgun'), AY.get('logo', 'yok')          # AYAR halka_centik / logo (eski META'da yok = ozgun / yok)
    G = U.grup_kur(mt, cift, katman_g, yan_json, hedef_r, AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'], hk, hc, lg_)
    adlar = ['halka', 'kucuk1', 'kucuk2'] + (['logo'] if lg_ != 'yok' else [])  # logo ayarda varsa grupta ZORUNLU, yoksa OLAMAZ
    B = G['bilgi']
    (ex, ey), ol = B['cevre_merkez_poster'], B['olcek']
    mx, my = gb['merkez']
    pay = ESIK['grup_konum_olculen']
    out = dict(olcek=ol, hedef_yaricap=hedef_r, hedef_yaricap_meta_ayni=bool(abs(hedef_r - meta['sembol']['hedef_yaricap']) < 1e-6), oge={})
    # ---- (1) yeniden kurulum
    out['ana'] = dict(olcek=G['ana']['olcek'], olcek_meta_ayni=bool(abs(G['ana']['olcek'] - meta['sembol']['yerlesim']['olcek']) < 1e-9),
                      x_ayni=bool(mx + G['ana']['x'] == sx and my + G['ana']['y'] == sy),
                      konum_fark=round(float(max(abs(sx - mx - G['ana']['hedef'][0]), abs(sy - my - G['ana']['hedef'][1]))), 3))
    ok = out['hedef_yaricap_meta_ayni'] and out['ana']['olcek_meta_ayni'] and out['ana']['x_ayni'] and G['ana']['olcek'] <= 1.0
    ok = ok and len(gb['ogeler']) == len(G['ogeler']) == len(adlar) and [o['ad'] for o in gb['ogeler']] == adlar
    if not ok:
        out['PASS'] = False
        return out
    for i, (om, og_) in enumerate(zip(gb['ogeler'], G['ogeler'])):
        m = D[f'gm_{i}']
        ayni = bool(om['ad'] == og_['ad'] and m.shape == og_['A'].shape and np.array_equal(m, og_['A'].astype(np.float32)))
        yer = bool(om['x'] == mx + og_['x'] and om['y'] == my + og_['y'])
        fark = max(abs(om['x'] - mx - (og_['poster'][0] - ex) * ol), abs(om['y'] - my - (og_['poster'][1] - ey) * ol))
        out['oge'][om['ad']] = dict(yeniden_kucultme_birebir=ayni, yer_ayni=yer, konum_fark=round(float(fark), 3), olcek=og_['olcek'], k=og_['k'])
        ok = ok and ayni and yer and fark <= ESIK['grup_konum'] and og_['olcek'] <= 1.0
    # ---- (2) bagimsiz olcum
    C = json.loads((Path(motor) / 'cember.json').read_text())['cember']
    Yl = json.loads((Path(motor) / 'yerlesim78.json').read_text())[cift]
    dm = meta['disk']['merkez']
    bag = dict(grup_merkez_disk_merkezi=bool([mx, my] == [int(round(dm[0])), int(round(dm[1]))]))
    oh, mh = gb['ogeler'][0], D['gm_0']
    fx, fy, fr = cember_uydur(mh)
    hx, hy = oh['x'] + fx, oh['y'] + fy                                       # olculen halka merkezi (tuval) ve yaricapi
    s_m = fr / C['R']                                                         # olculen grup olcegi
    bag.update(halka_merkez=[round(hx, 2), round(hy, 2)], halka_yaricap=round(fr, 2), olculen_olcek=round(s_m, 5))
    if AY['grup_merkez'] == 'halka':
        bag['halka_merkezde_fark'] = round(float(max(abs(hx - mx), abs(hy - my))), 3)
    # takvim merkezine en uzak grup pikseli (alfa > 0,02; piksel koseleri). halka_kalinlik != 1: grup olcegi OZGUN halkadan kuruldugu icin halka
    # pikselleri once OLCULEREK ozgun kalinliga geri tasinir: her halka pikseli, maskeden olculen merkez cizgisi Rc(aci) etrafinda 1 / carpan oraninda
    # radyal olarak iceri alinir (r' = Rc + (r - Rc) / carpan; Rc = 1 derecelik dilimde alfa agirlikli ortalama yaricap, uydurulan halka merkezine gore).
    # Olcut TEK NOKTA olarak ayni kalir: |en uzak - hedef| <= 2 px (aralik / ek pay yok; inceleme Y2). carpan 1,0'da donusum uygulanmaz.
    uzak = 0.0
    for a_, x_, y_ in [(sa, sx, sy)] + [(D[f'gm_{i}'], o['x'], o['y']) for i, o in enumerate(gb['ogeler']) if i > 0 or hk == 1.0]:
        ys, xs = np.nonzero(a_ > U.GRUP_ALFA_ESIK)
        uzak = max(uzak, float(max(np.hypot(xs + x_ + dx - mx, ys + y_ + dy - my).max() for dx in (0, 1) for dy in (0, 1))))
    uzak_ham = uzak
    if hk != 1.0:
        ys, xs = np.nonzero(mh > 0)
        wq = mh[ys, xs].astype(np.float64)
        qx, qy = xs + 0.5 - fx, ys + 0.5 - fy
        qr = np.hypot(qx, qy)
        qb = np.floor(np.degrees(np.arctan2(qy, qx)) + 180.0).astype(np.int64) % 360
        sw_, sr_ = np.bincount(qb, wq, 360), np.bincount(qb, wq * qr, 360)
        rcq = np.where(sw_ > 0, sr_ / np.maximum(sw_, 1e-9), fr)
        ys, xs = np.nonzero(mh > U.GRUP_ALFA_ESIK)
        for dx in (0, 1):
            for dy in (0, 1):
                ux, uy = xs + dx - fx, ys + dy - fy
                ur = np.maximum(np.hypot(ux, uy), 1e-6)
                rc_ = rcq[np.floor(np.degrees(np.arctan2(uy, ux)) + 180.0).astype(np.int64) % 360]
                kat = (rc_ + (ur - rc_) / hk) / ur
                uzak_ham = max(uzak_ham, float(np.hypot(oh['x'] + fx + ux - mx, oh['y'] + fy + uy - my).max()))
                uzak = max(uzak, float(np.hypot(oh['x'] + fx + ux * kat - mx, oh['y'] + fy + uy * kat - my).max()))
    bag.update(en_uzak_piksel=round(uzak, 2), en_uzak_piksel_ham=round(uzak_ham, 2), en_uzak_fark=round(abs(uzak - hedef_r), 3))
    hko = halka_kalinlik_olc(mh, fx, fy)                                      # BILGI: maskeden olculen cizgi kalinligi (kapi degil)
    bag['halka_kalinlik'] = dict(carpan=hk, hedef_ust_px=round(hk * C['kalinlik'] * s_m, 3), **hko)
    if hk != 1.0:                                                             # BILGI: saat 3 basamagi (AYAR halka_centik). 'yumusak'ta ozgun kurulumla karsilastirma
        cen = dict(mod=hc, basamak_px=hko['basamak_saat3_px'], basamak_mm=round(hko['basamak_saat3_px'] * 25.4 / U.DPI, 3))
        if hc == 'yumusak':
            G0 = U.grup_kur(mt, cift, katman_g, yan_json, hedef_r, AY['grup_merkez'], AY['kucuk_u'], AY['kucuk_v'], AY['kucuk_oran'], hk, 'ozgun', 'yok')
            m0 = G0['ogeler'][0]['A'].astype(np.float32)
            ayni_yer = bool(m0.shape == mh.shape and mx + G0['ogeler'][0]['x'] == oh['x'] and my + G0['ogeler'][0]['y'] == oh['y'])
            cen.update(basamak_once_px=halka_kalinlik_olc(m0, *cember_uydur(m0)[:2])['basamak_saat3_px'], basamak_sonra_px=hko['basamak_saat3_px'], ozgun_ile_ayni_cerceve=ayni_yer)
            if ayni_yer:
                yy_, xx_ = np.nonzero(m0 != mh)
                aci = np.degrees(np.arctan2(yy_ + 0.5 - fy, xx_ + 0.5 - fx))
                dis = np.abs(aci) > U.CENTIK_ACI + 0.5                         # +- 3 derece + 0,5 derece (kucultme cekirdegi payi)
                cen.update(degisen_maske_pikseli=int(len(yy_)), band_disi_degisen_piksel=int(dis.sum()), band_derece=U.CENTIK_ACI + 0.5)
            del G0, m0
        bag['halka_centik'] = cen
    if AY['kucuk_u'] == 'poster':
        u_h = POSTER_KUCUK_U.get(cift)
    else:
        u_h = (-float(AY['kucuk_u']), float(AY['kucuk_u']))
    v_h = (POSTER_KUCUK_Y - C['cy']) / C['R'] if AY['kucuk_v'] == 'poster' else float(AY['kucuk_v'])
    ko = float(AY['kucuk_oran'])
    olc = []
    mer = []
    if u_h is None:
        bag['neden'] = 'cift icin poster kucuk sembol yeri tanimli degil'
    else:
        for i, u_ in ((1, u_h[0]), (2, u_h[1])):
            om, m, kay = gb['ogeler'][i], D[f'gm_{i}'], G['ogeler'][i]['kaynak']
            kk = U.kutu(m, 0.02)
            cxk, cyk = om['x'] + (kk[0] + kk[2]) / 2.0, om['y'] + (kk[1] + kk[3]) / 2.0
            mer.append(cxk)
            d_yer = max(abs(cxk - hx - u_ * fr), abs(cyk - hy - v_h * fr))
            d_boy = abs(yatay_yayilim(m) / (yatay_yayilim(kay) * s_m * ko) - 1.0) * (kk[2] - kk[0])   # boy: alfa agirlikli yayilim orani x genislik (px)
            bag[om['ad']] = dict(u=round((cxk - hx) / fr, 4), v=round((cyk - hy) / fr, 4), hedef_u=u_, hedef_v=round(v_h, 5), yer_fark=round(float(d_yer), 3),
                                 genislik=int(kk[2] - kk[0]), boy_fark=round(float(d_boy), 3))
            olc += [d_yer, d_boy]
        bag['kucuk1_solda_kucuk2_sagda'] = bool(mer[0] < hx < mer[1])
    if lg_ != 'yok':                                                          # logo: yer (grup ekseni, kucuk sembol satiri) ve boy; ayni olcum payi (2 px)
        om, m, kay = gb['ogeler'][3], D['gm_3'], G['ogeler'][3]['kaynak']
        kk = U.kutu(m, 0.02)
        cxl, cyl = om['x'] + (kk[0] + kk[2]) / 2.0, om['y'] + (kk[1] + kk[3]) / 2.0
        d_yer = max(abs(cxl - hx), abs(cyl - hy - v_h * fr))
        d_boy = abs(yatay_yayilim(m) / (yatay_yayilim(kay) * s_m * float(lg_)) - 1.0) * (kk[2] - kk[0])
        lb = dict(oran=float(lg_), yer_fark=round(float(d_yer), 3), boy_fark=round(float(d_boy), 3), genislik_px=int(kk[2] - kk[0]), yukseklik_px=int(kk[3] - kk[1]),
                  genislik_mm=round((kk[2] - kk[0]) * 25.4 / U.DPI, 2), yukseklik_mm=round((kk[3] - kk[1]) * 25.4 / U.DPI, 2))
        # BILGI (esik yok): logo ile her kucuk sembol arasi en yakin piksel uzakligi (alfa > 0,02 murekkep; kenar boslugu = mesafe - 1)
        x0_ = min(o['x'] for o in gb['ogeler'][1:]); y0_ = min(o['y'] for o in gb['ogeler'][1:])
        x1_ = max(o['x'] + o['gen'] for o in gb['ogeler'][1:]); y1_ = max(o['y'] + o['yuk'] for o in gb['ogeler'][1:])
        tl = np.zeros((y1_ - y0_, x1_ - x0_), np.uint8)
        tl[om['y'] - y0_:om['y'] - y0_ + m.shape[0], om['x'] - x0_:om['x'] - x0_ + m.shape[1]][m > 0.02] = 1
        dtl = cv2.distanceTransform((tl == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        for i in (1, 2):
            ok_, mk_ = gb['ogeler'][i], D[f'gm_{i}']
            dl = dtl[ok_['y'] - y0_:ok_['y'] - y0_ + mk_.shape[0], ok_['x'] - x0_:ok_['x'] - x0_ + mk_.shape[1]][mk_ > 0.02]
            bos = float(dl.min()) - 1.0
            lb[f'{ok_["ad"]}_uzaklik_px'] = round(bos, 2); lb[f'{ok_["ad"]}_uzaklik_mm'] = round(bos * 25.4 / U.DPI, 2)
            lb[f'{ok_["ad"]}_durum'] = 'cakisiyor' if bos < 0 else 'ayrik'
        bag['logo'] = lb
        olc += [d_yer, d_boy]
    # ana sembol: kaynak alfa kutusu (alfa > 0,02) sol ust kosesi ve genisligi, olculen halkaya gore
    j = yan_json or {}
    pay_x, pay_y = j.get('kaynak_x', j.get('x', 0)) - j.get('x', 0), j.get('kaynak_y', j.get('y', 0)) - j.get('y', 0)
    s_ana = (Yl['u1'] - Yl['u0']) * C['R'] / j.get('kaynak_w', j.get('w', 1))
    k2 = meta['sembol']['olcum']['kutu_alfa_002']
    ks = U.kutu(sa, 0.02)
    d_ana = max(abs(sx + ks[0] - hx - (Yl['u0'] * C['R'] + (k2[0] - pay_x) * s_ana) * s_m), abs(sy + ks[1] - hy - (Yl['v0'] * C['R'] + (k2[1] - pay_y) * s_ana) * s_m))
    d_ana_boy = abs(yatay_yayilim(sa) / (yatay_yayilim(katman_g[..., 3]) * s_ana * s_m) - 1.0) * (ks[2] - ks[0])
    bag['ana'] = dict(yer_fark=round(float(d_ana), 3), boy_fark=round(float(d_ana_boy), 3))
    olc += [d_ana, d_ana_boy, bag['en_uzak_fark']] + ([bag['halka_merkezde_fark']] if 'halka_merkezde_fark' in bag else [])
    bag['fark_en_buyuk'] = round(float(max(olc)), 3)
    bag['PASS'] = bool(u_h is not None and bag['grup_merkez_disk_merkezi'] and bag.get('kucuk1_solda_kucuk2_sagda') and max(olc) <= pay)
    out['bagimsiz'] = bag
    out['konum_fark_en_buyuk'] = max([out['ana']['konum_fark']] + [v['konum_fark'] for v in out['oge'].values()])
    out['olculen_fark_en_buyuk'] = bag['fark_en_buyuk']
    out['PASS'] = bool(ok and bag['PASS'])
    return out


def kapi_olc(klasor, ad, katman=None, motor=None, mod='ornek'):
    K = Path(klasor)
    meta = json.loads((K / f'{ad}_META.json').read_text())
    D = np.load(K / f'{ad}_DUMP.npz')
    png = K / f'{ad}.png'
    im = Image.open(png)
    img = np.asarray(im.convert('RGB'))
    Hh, Ww = img.shape[:2]
    R = {}
    AY = meta['ayar']                                                        # ayara bagli her deger buradan (U.* / ESIK'ten degil)
    mod_meta = meta.get('mod', 'ornek')                                      # mod CAGIRANDAN gelir (inceleme O5); META ile uyusmazsa FAIL
    og = meta['ogeler']
    M = [D[f'm_{i}'] for i in range(len(og))]
    T = [D[f't_{i}'] for i in range(len(og))]
    gg = [dict(o, tur='grup') for o in (meta.get('grup') or {}).get('ogeler', [])]   # grup ogeleri: halka, kucuk1, kucuk2
    GM = [D[f'gm_{i}'] for i in range(len(gg))]
    GT = [D[f'gt_{i}'] for i in range(len(gg))]
    uk = meta.get('uretim_kontrol') or {}
    ayar_fark = []
    if mod == 'ornek':                                                       # mod ornek: ayar = varsayilan (kisi adlari, metin ve hal secimi haric); esik urunden okunmaz
        vars_ = U.ayar_varsayilan(AY['yerlesim']) if AY.get('yerlesim') in U.YERLESIM else {}
        ayar_fark = sorted(k_ for k_ in U.AYAR_ANAHTAR if k_ not in ('isim1', 'isim2', 'satirlar', 'grup_merkez', 'yerlesim')
                           and AY.get(k_, {'halka_kalinlik': 1.0, 'halka_centik': 'ozgun', 'logo': 'yok'}.get(k_)) != vars_.get(k_))   # eski META'da yeni anahtar yok = varsayilan
    R['0_uretim'] = dict(kontrol=uk, mod=mod, mod_meta=mod_meta, mod_tutarli=bool(mod == mod_meta), ayar_varsayilan_disi=ayar_fark,
                         PASS=bool(all(v['PASS'] for v in uk.values()) and mod == mod_meta and not ayar_fark))

    def pencere(o, pay=0):
        return max(0, o['y'] - pay), min(Hh, o['y'] + o['yuk'] + pay), max(0, o['x'] - pay), min(Ww, o['x'] + o['gen'] + pay)

    def tuvalde(o, m, pay):
        """oge maskesi pay kadar genis pencerede (tuval koordinati)."""
        y0, y1, x0, x1 = pencere(o, pay)
        out = np.zeros((y1 - y0, x1 - x0), np.float32)
        out[o['y'] - y0:o['y'] - y0 + o['yuk'], o['x'] - x0:o['x'] - x0 + o['gen']] = m
        return out, (y0, y1, x0, x1)

    # 1 veri (yeniden hesap) + son dosyadan evre olcumu
    gunler = U.ay_verisi(U.YIL)
    R['1_veri'] = U.veri_kapisi(gunler)
    R['1_veri']['veri_PASS'] = bool(R['1_veri']['PASS'])
    R['1_veri']['evre'] = evre_olc(img, meta['disk']['liste'], gunler)
    R['1_veri']['PASS'] = bool(R['1_veri']['PASS'] and R['1_veri']['evre']['PASS'])
    # 2 sembol
    sa, srgb_ = D['sembol_a'], D['sembol_rgb']
    sm = meta['sembol']; sx, sy = sm['x'], sm['y']
    k05 = U.kutu(sa, 0.5)
    eb = (k05[2] - k05[0]) / (k05[3] - k05[1])
    kaynak_gen = sm['olcum']['kutu_alfa_05'][2] - sm['olcum']['kutu_alfa_05'][0]
    olcek_olc = (k05[2] - k05[0]) / kaynak_gen
    bolge = img[sy:sy + sa.shape[0], sx:sx + sa.shape[1]].astype(np.float32)
    tam = sa >= 0.999
    ortulen = np.zeros(sa.shape, bool)
    if mod == 'deneme':                                                      # YALNIZ mod deneme: baska altin ogenin (yazi, halka, kucuk sembol) ortdugu sembol pikseli
        for o, m in zip(og + gg, M + GM):                                    # renk karsilastirmasina girmez (binme kapi 6'da FAIL yazilir; sekil kontrolu ayni kalir).
            y0, y1 = max(sy, o['y']), min(sy + sa.shape[0], o['y'] + o['yuk'])   # mod ornek'te hicbir piksel cikarilmaz.
            x0, x1 = max(sx, o['x']), min(sx + sa.shape[1], o['x'] + o['gen'])
            if y1 > y0 and x1 > x0:
                ortulen[y0 - sy:y1 - sy, x0 - sx:x1 - sx] |= m[y0 - o['y']:y1 - o['y'], x0 - o['x']:x1 - o['x']] > 0.02
        if ortulen.any():
            ortulen = cv2.dilate(ortulen.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0   # + golge erimi
        tam = tam & ~ortulen
    renk_fark = float(np.abs(bolge[tam] - np.round(srgb_[tam])).max()) if tam.any() else None
    # yari saydam kenar: son piksel = katman rengi x a + (zemin ya da en cok DIS_GOLGE opak kadar koyulasmis zemin) x (1 - a) sinirlari icinde
    alt_b = D['altinsiz'][sy:sy + sa.shape[0], sx:sx + sa.shape[1]].astype(np.float32)
    kn = (sa > 0.02) & (sa < 0.999) & ~ortulen
    a3 = sa[..., None]
    ust_s = alt_b * (1 - a3) + srgb_ * a3 + 1.5
    alt_s = alt_b * (1 - U.DIS_GOLGE['opak']) * (1 - a3) + srgb_ * a3 - 1.5
    kenar_disi = int(((bolge > ust_s) | (bolge < alt_s)).any(2)[kn].sum())
    s2 = dict(ortulen_piksel_haric=int(ortulen.sum()), kenar_piksel=int(kn.sum()), kenar_sinir_disi_piksel=kenar_disi, en_boy_kaynak=sm['olcum']['en_boy_05'], en_boy_yerlesen=round(eb, 5), en_boy_fark=round(abs(eb - sm['olcum']['en_boy_05']), 5),
              olcek=sm['yerlesim']['olcek'], olcek_olculen=round(olcek_olc, 5), tam_alfa_piksel=int(tam.sum()), renk_fark_en_buyuk=renk_fark)
    ok2 = s2['en_boy_fark'] <= ESIK['en_boy'] and s2['olcek'] <= 1.0 and olcek_olc <= 1.0 + 1e-3 and renk_fark is not None and renk_fark <= ESIK['sembol_renk'] and kenar_disi == 0
    if katman:                                                               # kaynaktan yeniden: yalniz es oranli kucultme mi
        g, olc = U.sembol_yukle(katman)
        rgb2, a2 = U.rgba_olcek(g, s2['olcek'])
        ayni = bool(a2.shape == sa.shape and np.array_equal(a2.astype(np.float32), sa) and np.array_equal(rgb2.astype(np.float32), srgb_))
        s2.update(kaynak_sha256=olc['sha256'], kaynak_sha_ayni=bool(olc['sha256'] == sm['olcum']['sha256']), yeniden_kucultme_birebir=ayni)
        ok2 = ok2 and ayni and s2['kaynak_sha_ayni']
        if meta.get('grup') and motor:
            s2['grup'] = grup_kapisi(meta, D, g, olc.get('yan_json'), motor, sa, sx, sy)
        del g
    grup_gerekli = bool(U.YERLESIM.get(meta['yerlesim'], {}).get('grup'))     # grup yerlesiminde META 'grup' ZORUNLU (inceleme O2: alan silinerek atlanamaz)
    if meta.get('grup') or grup_gerekli:
        if not meta.get('grup'):
            s2['grup'] = dict(PASS=False, neden='grup yerlesiminde META grup alani yok')
        elif 'grup' not in s2:
            s2['grup'] = dict(PASS=False, neden='grup kapisi icin --katman ve --motor gerekli')
        ok2 = ok2 and s2['grup']['PASS']
    s2['PASS'] = bool(ok2)
    R['2_sembol'] = s2
    # 3 tek doku (son dosya; ornament de_tablo: oge ve sembol alfa >= 0.9 ortanca Lab -> CIEDE2000)
    Ls = np.median(U.labf(bolge[sa >= 0.9]), 0)
    t3, k4, y5, duz = {}, {}, {}, {}
    disk, diger, yildiz = D['disk_maske'], D['diger_maske'], D['yildiz_maske']
    for o, m, t in zip(og + gg, M + GM, T + GT):
        y0, y1, x0, x1 = pencere(o)
        b = img[y0:y1, x0:x1].astype(np.float32)
        ce = m >= 0.9
        n = int(ce.sum())
        t3[o['ad']] = dict(piksel=n, dE00=round(U.de00(Ls, np.median(U.labf(b[ce]), 0)), 3) if n >= 5 else None)
        # 4 kontrast (pencere 20 px payli; bant 12 px)
        mt, (wy0, wy1, wx0, wx1) = tuvalde(o, m, 20)
        rgbw = img[wy0:wy1, wx0:wx1]
        kk = kontrast_olc(rgbw, mt)
        dm, ym, em = disk[wy0:wy1, wx0:wx1] > 0, yildiz[wy0:wy1, wx0:wx1] > 0, diger[wy0:wy1, wx0:wx1] > 0
        ink = (mt > 0.02).astype(np.uint8)
        bant = (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) > 0) & (cv2.dilate(ink, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))) == 0)
        nb = max(int(bant.sum()), 1)
        kk['bant_disk_oran'] = round(float((bant & dm).sum()) / nb, 4)
        kk['bant_yildiz_oran'] = round(float((bant & ym).sum()) / nb, 4)
        kk['bant_diger_oran'] = round(float((bant & em).sum()) / nb, 4)
        if (bant & (dm | ym | em)).any():
            kh = kontrast_olc(rgbw, mt, haric=dm | ym | em)
            kk['haric_ortanca_bilgi'] = kh.get('ortanca_bilgi'); kk['haric_deger_bilgi'] = kh.get('deger')
        k4[o['ad']] = kk
        # 5 yazim
        murekkep = (t > 0.02) | (m > 0.02)
        y5[o['ad']] = round(float(np.abs(t - m)[murekkep].mean()), 4)
        # 7b duz renk
        Lc = lum(b[ce]) if n >= 5 else np.zeros(1)
        duz[o['ad']] = round(float(np.percentile(Lc, 95) - np.percentile(Lc, 5)), 2)
    de = [v['dE00'] for v in t3.values() if v['dE00'] is not None]
    say = {t_: sum(1 for o in og if o['tur'] == t_) for t_ in ('isim', 'baslik', 'ay', 'metin')}
    say['grup'] = len(gg)
    say_ok = bool(say['isim'] == 1 and say['baslik'] == 1 and say['ay'] == 12 and say['metin'] == meta['metin']['satir'] and len(og) + len(gg) == sum(say.values())
                  and len(gg) == ((3 + (1 if AY.get('logo', 'yok') != 'yok' else 0)) if meta.get('grup') else 0))
    R['3_tek_doku'] = dict(oge=t3, en_kotu_dE00=max(de) if de else None, en_az_piksel=min(v['piksel'] for v in t3.values()),
                           sembol_Lab=[round(float(v), 2) for v in Ls], oge_sayisi=say, oge_sayisi_tam=say_ok,
                           uyum_dE00_sonra_en_kotu_bilgi=max((o.get('uyum', {}).get('dE00_sonra', 0) for o in og + gg), default=None),
                           PASS=bool(de and len(de) == len(t3) and max(de) <= ESIK['dE00'] and min(v['piksel'] for v in t3.values()) >= ESIK['cekirdek_piksel']
                                     and say_ok))
    ko = [v.get('ortanca_bilgi') for v in k4.values()]
    R['4_kontrast'] = dict(oge=k4, en_kotu_ortanca=min(ko) if all(v is not None for v in ko) else None,
                           en_kotu_koyu5_bilgi=min((v['deger'] for v in k4.values() if v.get('deger') is not None), default=None),
                           PASS=bool(all(v is not None for v in ko) and min(ko) >= ESIK['kontrast']))
    y5g = {o['ad']: y5.pop(o['ad']) for o in gg}                               # grup ogeleri: yalniz bilgi (yazi cizimi degil)
    R['5_yazim'] = dict(oge=y5, grup_bilgi=y5g, en_kotu=max(y5.values()), PASS=bool(max(y5.values()) <= ESIK['alfa_fark']))
    # 6 bosluk (maskelerden; mesafe donusumu piksel merkezleri arasi oldugu icin kenar boslugu = mesafe - 1)
    dt = cv2.distanceTransform((disk == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    yd = {}
    altin = np.zeros((Hh, Ww), np.uint8)
    binme = 0
    grup = np.zeros((Hh, Ww), np.uint8)                                     # sembol grubu: ana sembol + halka + kucuk semboller (alfa > 0,02)
    for o, m in zip(og + gg, M + GM):
        y0, y1, x0, x1 = pencere(o)
        ink = m > 0.5
        if o['tur'] != 'grup':
            yd[o['ad']] = round(float(dt[y0:y1, x0:x1][ink].min()) - 1.0, 2) if ink.any() else None
        else:
            grup[y0:y1, x0:x1][m > 0.02] = 255
        sl = altin[y0:y1, x0:x1]
        binme += int((sl[m > 0.02] > 0).sum())
        sl[m > 0.02] = 255
    ss = altin[sy:sy + sa.shape[0], sx:sx + sa.shape[1]]
    binme += int((ss[sa > 0.02] > 0).sum())
    ss[sa > 0.02] = 255
    sd = float(dt[sy:sy + sa.shape[0], sx:sx + sa.shape[1]][sa > 0.5].min()) - 1.0
    gy = None
    if gg:                                                                   # grup (gercek alfa siniri) - disk; grup - ay adi
        grup[sy:sy + sa.shape[0], sx:sx + sa.shape[1]][sa > 0.02] = 255
        sd = float(dt[grup > 0].min()) - 1.0
        dtg = cv2.distanceTransform((grup == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        gy = {}
        for o, m in zip(og, M):
            if o['tur'] == 'ay' and (m > 0.5).any():
                y0, y1, x0, x1 = pencere(o)
                gy[o['ad']] = round(float(dtg[y0:y1, x0:x1][m > 0.5].min()) - 1.0, 2)
        del dtg
    del grup
    yd_ok = bool(all(v is not None for v in yd.values()))
    yd = {k_: (v if v is not None else -1.0) for k_, v in yd.items()}
    L = np.array(meta['disk']['liste'], np.float64)[:, :4]
    dd, cift = U.disk_disk_bosluk(L[:, :3], L[:, 3])
    n_bilesen = int(cv2.connectedComponents((disk > 0).astype(np.uint8), connectivity=8)[0] - 1)
    alan_olc = float((disk > 0).sum())                                      # maske alani META yaricaplariyla tutarli mi (+- 1 px yaricap)
    alan_alt, alan_ust = float(np.pi * ((L[:, 3] - 1) ** 2).sum()), float(np.pi * ((L[:, 3] + 1) ** 2).sum())
    tum = (disk > 0) | (diger > 0) | (altin > 0)
    ys, xs = np.nonzero(tum)
    kenar = dict(sol=int(xs.min()), ust=int(ys.min()), sag=int(Ww - 1 - xs.max()), alt=int(Hh - 1 - ys.max()))
    R['6_bosluk'] = dict(yazi_disk=yd, yazi_disk_en_az=min(yd.values()), disk_disk_en_az=round(dd, 2), disk_disk_cift=list(cift),
                         disk_bilesen=n_bilesen, disk_sayisi=int(len(L)), disk_alan=[round(alan_alt), round(alan_olc), round(alan_ust)],
                         sembol_disk=round(sd, 2), sembol_disk_olcum='grup (alfa > 0,02)' if gg else 'sembol (alfa > 0,5)',
                         grup_ay_adi=gy, grup_ay_adi_en_az=min(gy.values()) if gy else None,
                         kenar=kenar, kenar_en_az=min(kenar.values()), altin_binme_piksel=binme)
    R['6_bosluk']['PASS'] = bool(yd_ok and min(yd.values()) >= ESIK['yazi_disk'] and dd >= ESIK['disk_disk'] and n_bilesen == len(L)
                                 and (not gg or (bool(gy) and len(gy) == 12 and min(gy.values()) >= ESIK['grup_yazi']))
                                 and alan_alt <= alan_olc <= alan_ust and sd >= ESIK['sembol_disk'] and min(kenar.values()) >= ESIK['kenar'] and binme == 0)
    # 7 altin disi ogelerde altin yok / altin ogelerde duz renk yok
    altinsiz = D['altinsiz']
    yakin = cv2.dilate(altin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17))) > 0      # altin + golge erimi (8 px)
    duzbolge = ((disk > 0) | (diger > 0))
    fark = np.abs(img.astype(np.int16) - altinsiz.astype(np.int16)).max(2)
    degisen = int((fark[duzbolge & ~yakin] > 2).sum())
    ustunde = int(((altin > 0) & duzbolge).sum())
    rb = img[..., 0].astype(np.int16) - img[..., 2].astype(np.int16)
    benzer = int(((rb > ESIK['altin_rb']) & (img[..., 0] > ESIK['altin_r']) & duzbolge & (altin == 0)).sum())
    rbg = {o['ad']: round(float(np.median(rb[o['y']:o['y'] + o['yuk'], o['x']:o['x'] + o['gen']][m >= 0.9])), 1) for o, m in zip(og + gg, M + GM) if (m >= 0.9).sum() >= 5}
    halka_duz = duz.pop('halka', None)                                       # halkanin yayilimi yalniz bilgi (Serdar 11 Kas)
    yp = 2 * ESIK['yildiz_pay'] + 1
    yildiz_binme = int(((yildiz > 0) & (cv2.dilate(altin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (yp, yp))) > 0)).sum())
    R['7_altin'] = dict(altin_disi=dict(degisen_piksel=degisen, altin_ustunde_piksel=ustunde, altin_benzeri_piksel=benzer,
                                        altin_cekirdek_RB_ortanca_en_dusuk=min(rbg.values()) if rbg else None),
                        duz_renk=dict(oge=duz, en_dusuk=min(duz.values()), halka_bilgi=halka_duz), yildiz_altin_binme_piksel=yildiz_binme,
                        PASS=bool(degisen == 0 and ustunde == 0 and benzer == 0 and min(duz.values()) >= ESIK['duz_yayilim'] and yildiz_binme == 0))
    # 8 isim satiri
    oi = next(o for o in og if o['tur'] == 'isim'); mi = M[og.index(oi)]
    ki = U.kutu(mi)
    R['8_isim'] = dict(genislik=int(ki[2] - ki[0]), sinir=round(ESIK['gen_oran'] * Ww, 1), cap=oi['cap'], kuculme_orani=meta['isim']['kuculme_orani'],
                       harf=meta['isim']['harf'], cap_alt_siniri=AY['ay_adi_cap'], PASS=bool(ki[2] - ki[0] <= ESIK['gen_oran'] * Ww and oi['cap'] >= AY['ay_adi_cap']))
    # 9 metin + blok dikey ortalamasi (murekkepten: ust = isim satiri murekkep ustu; alt = son metin tabani ya da cember blogu alti)
    om = [o for o in og if o['tur'] == 'metin']
    gen = [int(U.kutu(M[og.index(o)])[2] - U.kutu(M[og.index(o)])[0]) for o in om]
    ust = oi['y'] + ki[1]
    if om:
        son = om[-1]; ks = U.kutu(M[og.index(son)])
        alt = son['taban_y']
        taban_tutarli = bool(son['y'] + ks[3] >= alt - 2 and son['y'] + ks[3] <= alt + 0.45 * son['cap'] + 2)
    else:
        cember = (disk > 0) | (diger > 0)
        for o, m in zip(og, M):
            if o['tur'] == 'ay':
                cember[o['y']:o['y'] + o['yuk'], o['x']:o['x'] + o['gen']] |= m > 0.02
        alt = float(np.nonzero(cember.any(1))[0].max() + 1)
        taban_tutarli = True
    sapma = (ust + alt) / 2.0 - Hh / 2.0
    R['9_metin'] = dict(satir=len(om), karakter=[o['karakter'] for o in om], genislik=gen, sinir=round(ESIK['gen_oran'] * Ww, 1),
                        blok_ust=round(float(ust), 1), blok_alt=round(float(alt), 1), blok_merkez_sapma=round(float(sapma), 2), taban_tutarli=taban_tutarli,
                        PASS=bool(len(om) <= ESIK['satir'] and len(om) == meta['metin']['satir'] and all(o['karakter'] <= ESIK['karakter'] for o in om)
                                  and all(g_ <= ESIK['gen_oran'] * Ww for g_ in gen) and abs(sapma) <= ESIK['blok_merkez'] and taban_tutarli))
    # 10 cikti
    dpi = im.info.get('dpi') or (0, 0)
    icc = im.info.get('icc_profile')
    try:
        icc_ad = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(__import__('io').BytesIO(icc))).strip() if icc else None
    except Exception:                                                        # noqa: BLE001
        icc_ad = None
    R['10_cikti'] = dict(boyut=[Ww, Hh], dpi=[round(float(dpi[0]), 2), round(float(dpi[1]), 2)], mod=im.mode, icc=icc_ad,
                         PASS=bool((Ww, Hh) == (U.W, U.H) and abs(dpi[0] - 300) < 0.1 and abs(dpi[1] - 300) < 0.1 and im.mode == 'RGB'
                                   and icc_ad is not None and 'sRGB' in icc_ad))
    fail = [k for k, v in R.items() if not v['PASS']]
    sert_fail = [k for k in fail if k == '2_sembol'] + ([] if R['1_veri']['veri_PASS'] else ['1_veri']) + ([] if R['0_uretim']['mod_tutarli'] else ['0_uretim'])
    gb = (meta.get('grup') or {}).get('bilgi')
    grup_ozet = None
    if gb:
        onceki = U.SEMBOL_ORAN * U.YERLESIM[meta['yerlesim']]['sembol_alan'] * U.S / meta['sembol']['olcum']['cevre_yaricap_05']   # 10 Kas turu (kural: 0,78 x alan)
        grup_ozet = dict(merkez=gb['merkez'], olcek=round(gb['olcek'], 5), ana_olcek=round(meta['sembol']['yerlesim']['olcek'], 5),
                         ana_olcek_onceki_tur=round(onceki, 5), ana_olcek_orani=round(meta['sembol']['yerlesim']['olcek'] / onceki, 4),
                         halka_merkez_kayma_px=gb['halka_merkez_kayma_px'], halka_kalinlik_px=gb['halka_kalinlik_px'], halka_kalinlik_mm=gb['halka_kalinlik_mm'],
                         halka_kalinlik_olculen=R['2_sembol'].get('grup', {}).get('bagimsiz', {}).get('halka_kalinlik'),
                         halka_centik=R['2_sembol'].get('grup', {}).get('bagimsiz', {}).get('halka_centik'), logo=R['2_sembol'].get('grup', {}).get('bagimsiz', {}).get('logo'),
                         halka_duz_yayilim=halka_duz, konum_fark_en_buyuk=R['2_sembol'].get('grup', {}).get('konum_fark_en_buyuk'),
                         olculen_fark_en_buyuk=R['2_sembol'].get('grup', {}).get('olculen_fark_en_buyuk'), k=gb['k'])
    ozet = dict(ad=ad, mod=mod, ayar=AY, sert_fail=sert_fail, grup=grup_ozet, girdap_ad=meta['disk'].get('girdap_ad'),
                uretim_kontrol_fail=sorted(k for k, v in uk.items() if not v['PASS']),
                yerlesim=meta['yerlesim'], PASS=not fail, fail=fail, en_kotu_kontrast=R['4_kontrast']['en_kotu_ortanca'],
                en_kotu_dE00=R['3_tek_doku']['en_kotu_dE00'], en_kotu_alfa_fark=R['5_yazim']['en_kotu'],
                en_kucuk_bosluk=dict(yazi_disk=R['6_bosluk']['yazi_disk_en_az'], disk_disk=R['6_bosluk']['disk_disk_en_az'],
                                     sembol_disk=R['6_bosluk']['sembol_disk'], grup_ay_adi=R['6_bosluk']['grup_ay_adi_en_az'], kenar=R['6_bosluk']['kenar_en_az']),
                en_dusuk_duz_yayilim=R['7_altin']['duz_renk']['en_dusuk'], k=meta['altin']['k'], disk_katsayisi=meta['disk']['katsayi'],
                isim_kuculme=meta['isim']['kuculme_orani'])
    return dict(ozet=ozet, esik=ESIK, esik_not=ESIK_NOT, kapi=R)


def ozet_yaz(argv):
    """Tum orneklerin tek OZET.json'u (yuklenecek klasorde) + ::notice::OZET. Gorsel uretmez; kapi karari degistirmez."""
    ap = argparse.ArgumentParser()
    ap.add_argument('--ozet', required=True); ap.add_argument('--kosu', default='0'); ap.add_argument('--kod', default='?')
    ap.add_argument('--motor-sha', default='?'); ap.add_argument('--ornament-sha', default='?'); ap.add_argument('--rc', default='')
    ap.add_argument('--mod', default='ornek', choices=U.MODLAR)
    a = ap.parse_args(argv)
    K = Path(a.ozet)
    rc = dict(x.split('=', 1) for x in a.rc.split(',') if '=' in x)
    ornek, dur = {}, {}
    for f in sorted(K.glob('*_OLCUM.json')):
        if f.name == 'SEMBOL_OLCUM.json' or f.name.endswith('_SEMBOL_OLCUM.json'):
            continue
        ornek[f.name[:-len('_OLCUM.json')]] = json.loads(f.read_text())['ozet']        # her ornegin / denemenin TAM ayari 'ayar' alaninda
    for f in sorted(K.glob('*_DUR.json')):
        dur[f.name[:-len('_DUR.json')]] = json.loads(f.read_text())
    zemin = None
    for f in sorted(K.glob('*_META.json')):
        m = json.loads(f.read_text())
        zemin = dict(yontem=m['zemin']['yontem'], olcek_profil=m['zemin']['olcek_profil'], poster_orani=m['zemin']['poster_orani'],
                     zemin_profil_sha256=m['zemin']['zemin_profil_sha256'], ref_sha256=m['zemin']['ref_sha256'], yildiz=m['zemin']['yildiz'])
        break
    sem = json.loads((K / 'SEMBOL_OLCUM.json').read_text()) if (K / 'SEMBOL_OLCUM.json').is_file() else None
    ayar_l = None
    if (K / 'AYAR.json').is_file():                                          # mod deneme: dogrulanmis TAM ayar listesi (DUR veren deneme de yeniden uretilebilsin)
        ayar_l = json.loads((K / 'AYAR.json').read_text())
    O = dict(kosu=a.kosu, mod=a.mod, ayar_listesi=ayar_l, kod_sha=a.kod, motor_sha=a.motor_sha, ornament_sha=a.ornament_sha, cikis=rc, ornek=ornek, dur=dur, zemin=zemin, sembol=sem,
             esik=ESIK, dosyalar=sorted(p.name for p in K.iterdir() if p.is_file()),
             not_='Gorsel onayi yalniz Serdar. Emsali olmayan esikler (kapi 2, 6, 7, 8, 9) baslangic degeridir.')
    (K / 'OZET.json').write_text(json.dumps(O, indent=1, default=float))
    pas = [k for k, v in ornek.items() if v['PASS']]; fail = {k: v['fail'] for k, v in ornek.items() if not v['PASS']}
    print(f"::notice title=OZET::mod {a.mod} | ornek {len(ornek)} | PASS {pas} | FAIL {fail} | DUR {sorted(dur)} | cikis {rc} | "
          f"en kotu kontrast {min((v['en_kotu_kontrast'] for v in ornek.values() if v['en_kotu_kontrast'] is not None), default=None)} | "
          f"en kotu dE00 {max((v['en_kotu_dE00'] for v in ornek.values() if v['en_kotu_dE00'] is not None), default=None)}", flush=True)
    for k, v in dur.items():
        print(f"::notice title=DUR::{k}: {v.get('kod')}: {v.get('neden')}", flush=True)
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if '--ozet' in argv:
        return ozet_yaz(argv)
    ap = argparse.ArgumentParser()
    ap.add_argument('klasor'); ap.add_argument('ad'); ap.add_argument('--katman'); ap.add_argument('--motor'); ap.add_argument('--onek', action='store_true')
    ap.add_argument('--mod', default='ornek', choices=U.MODLAR)
    a = ap.parse_args(argv)
    K = Path(a.klasor)
    r = kapi_olc(K, a.ad, a.katman, a.motor, a.mod)
    (K / f'{a.ad}_OLCUM.json').write_text(json.dumps(r, indent=1, default=float))
    o = r['ozet']
    for k, v in r['kapi'].items():
        print(f"{'PASS' if v['PASS'] else 'FAIL'} {k}", flush=True)
    satir = (f"{a.ad}: {'PASS' if o['PASS'] else 'FAIL ' + ','.join(o['fail'])} | kontrast en kotu {o['en_kotu_kontrast']} | dE00 en kotu {o['en_kotu_dE00']} | "
             f"alfa farki {o['en_kotu_alfa_fark']} | bosluk yazi-disk {o['en_kucuk_bosluk']['yazi_disk']} disk-disk {o['en_kucuk_bosluk']['disk_disk']} "
             f"sembol-disk {o['en_kucuk_bosluk']['sembol_disk']} grup-ay adi {o['en_kucuk_bosluk']['grup_ay_adi']} kenar {o['en_kucuk_bosluk']['kenar']} | "
             f"disk katsayisi {o['disk_katsayisi']}")
    if o['grup']:
        g_ = o['grup']
        satir += (f" | grup {g_['merkez']} olcek {g_['olcek']} ana olcek {g_['ana_olcek']} (onceki tura oran {g_['ana_olcek_orani']}) halka kayma {g_['halka_merkez_kayma_px']} px "
                  f"kalinlik {g_['halka_kalinlik_px']} px / {g_['halka_kalinlik_mm']} mm konum farki {g_['konum_fark_en_buyuk']} px (olculen {g_['olculen_fark_en_buyuk']} px)")
    if o['mod'] == 'deneme':                                                 # SERT: kapi 1 veri + kapi 2; digerleri yalniz yazilir (gorsel kalir)
        sert = o['sert_fail']
        print(f"::{'error' if sert else 'notice'} title=KAPI {a.ad}::mod deneme | SERT {'FAIL ' + ','.join(sert) if sert else 'PASS'} | {satir} | "
              f"uretim kontrolu FAIL {o['uretim_kontrol_fail']}", flush=True)
        if sert:
            print(f"::notice title=DUR::{a.ad}: sert kapi FAIL {','.join(sert)} (gorsel silindi)", flush=True)
            for f in sorted(K.glob(f'{a.ad}*')):
                if f.suffix in ('.png', '.jpg'):
                    f.unlink()
        return 1 if sert else 0
    print(f"::{'notice' if o['PASS'] else 'error'} title=KAPI {a.ad}::{satir}", flush=True)
    if not o['PASS']:
        print(f"::notice title=DUR::{a.ad}: kapi FAIL {','.join(o['fail'])}", flush=True)
        if a.onek:
            for f in sorted(K.glob(f'{a.ad}*')):
                if f.suffix in ('.png', '.jpg') and not f.name.startswith('KAPI_FAIL_'):
                    f.rename(f.with_name('KAPI_FAIL_' + f.name))
    return 0 if o['PASS'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        traceback.print_exc()
        print('::error title=COKUS::ay_takvim_kapi beklenmeyen hata (cikis 2)', flush=True)
        sys.exit(2)
