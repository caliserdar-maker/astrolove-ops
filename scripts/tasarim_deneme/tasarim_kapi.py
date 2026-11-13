#!/usr/bin/env python3
"""TASARIM DENEME ARACI kapilari ve olcumleri, dilim 1 + 1b + D1 + D2 (Serdar 11 - 13 Kas 2026; plan bolum 5, 6). Tek QC betigi, olculebilir esik, PASS / FAIL.
Son gorsel KAYDEDILEN dosyadan okunur (ATK:3 ilkesi); maskeler bellekten gelir (ayni surec; plan 7.3 madde 2).
Ay takvimi kapi kodu (ATK = ay_takvim_kapi.py, a9b1323) ice alinmis TEK modulden kullanilir; esik degerleri ATK.ESIK'ten okunur, bu dosyada
esik DEGISTIRILMEZ ve yeni esik ONERILMEZ. Yeni olcumler esiksiz yazilir.

SERT (FAIL = secenegin gorseli silinir; taban: ay takvimi deneme modu, ATK:52; Serdar 11 Kas soru 6 "t"):
  2_sembol  sekil degismez (ATK:406-440 ile ayni kosullar): en boy farki <= 0,005; olcek <= 1; son dosyada sembol rengi kucultulmus katmanla
            ayni (tam alfa pikselde fark <= 1 seviye; baska ogenin orttugu piksel haric, ATK:415-423); yari saydam kenar sinir icinde; kaynak
            sha256 ayni ve yerlesen = kaynagin yalniz es oranli kucultulmusu (birebir).
  2_grup    ATK.grup_kapisi DEGISTIRILMEDEN, sentetik META ile (emsal ATT:1526-1528): tam oge listesi (logo ayarda varsa 4. oge), her maske
            kaynagin TEK adim kucultulmusu, bagimsiz olcum (halka cemberi, kucuk burc yeri / boyu, ana sembol yeri, en uzak piksel, logo yeri /
            boyu; pay 2 px). Takvime bagli iki alt kosulun karsiligi (Serdar soru 6 "n"): "grup merkezi = ayardaki grup_x / grup_y'nin tuval
            noktasi" ve "'halka' merkezde halka merkezi o noktada". Beklenen nokta URETIMDEN BAGIMSIZ hesaplanir (beklenen_merkez).
            BOY (Serdar 12 Kas K1: SERT KALIR): olculen halka yaricapi = halka_r x guvenli yaricap, 2 px (beklenen_boyut; uretimden bagimsiz).
            Tuvalden tasan (kirpilan) grup ogesi bu kapiyi dusurur (Serdar 12 Kas K2: DEVAM EDER); kapi sonucu ve kodu degismez, yalniz
            OLCUM ozetine ve hucre etiketine kok neden yazilir ('kok_neden'; tek tanim olc() icinde).
            SERBEST SEMBOL (dilim D1; Serdar 12 Kas, kapi paketi 3 GK1): bir sembol anahtari (sembol_oran, sembol_u, sembol_v) varsayilan
            DISINDA iken ATK.grup_kapisi cagrilmaz; serbest_grup_kapisi ayni sert kosullari AYNI paylarla (ATK.ESIK) uygular, hedefler ayardan
            gelir (sembolun olculen yeri / boyu sembol_oran, sembol_u, sembol_v'den; "en uzak grup pikseli" hedefi serbest ayarli ilk gecisten).
            Varsayilan ayarda yol ve sonuc degismez. Sonuc kaydinda 'kapi' alani hangi yolun calistigini yazar ('atk' / 'serbest').
  cikti     boyut = urun baski_px, dpi etiketi, RGB, sRGB ICC. SERT (Serdar 12 Kas K4; dilim 1'de olcerdi): FAIL veren secenek DUR verir.
  Diger sert kapilar uretim sirasinda DUR verir (tasarim_deneme.py): girdi, ortam, sabit kaynak sha256, motor / KILIT, sembol bicimi,
  buyutme yok, cerceve, renk uyumu icin >= 200 cekirdek piksel (Serdar soru 6 "m"), sembol tuval disi, isim 8 denemede sigmiyor.
OLCER (FAIL gorseli durdurmaz; OLCUM'a ve hucre etiketine yazilir):
  tasma       guvenli alan / yasak bolge (Serdar soru 6 "d", "i"): UC olcum ayri yazilir: isik payi 0; isik payi 8 px (ornament degeri O4:56,
              oranlanmadan); goruntu farki (son gorsel - altinsiz zemin > 1; O4:425-437). Deger karara baglanmadi.
  cakisma     IKI tanim ayri alanlarda (Serdar soru 6 "e"): takvim (ATK:504-518: paysiz, alfa > 0,02, piksel sayisi); ornament (O4:255-269:
              halka ve sembol 7 x 7, yazilar 5 x 5 genisletme, alfa > 0,05): cift listesi VE cift basina piksel sayisi.
  tek doku dE00, kontrast, yazim farki, duz renk, yildiz, oge sayisi, grup - yazi boslugu (12 px aynen), metin tabani, isim satiri (Serdar
  12 Kas K3: buyuk harf bandi guvenli dairenin disindaysa DUR YOK; isim olceri FAIL + tasma olcumu; sinir = tuval genisligi), metin
  genisligi, gercek olcu uyarisi (yazi mm, cizgi mm: en ince / 1. yuzdelik / ortanca AYRI; olcut secilmedi, plan soru 4).
BILGI (esik yok, kapi degil; Serdar 12 Kas): oge cifti basina cakisma pikseli (alfa > 0,02), kucuk burc - yazi en az uzakligi, yildiz sayisi;
  dilim D1 (plan K8 b): sembolun halka cemberinin disinda kalan pikseli (sembol_halka_disi_olc) ve OLCUM ozetinin 'sembol' kaydi (carpan, olcek,
  kutu, en-boy farki, olculen yer / boy farki, tam sayi yer farki, kapi 2 sembol bolumunun tam_alfa_piksel ve ortulen_piksel_haric sayilari).
KAPATILAN OGELER (dilim D2; Serdar 12 - 13 Kas 2026, kapi paketi 4; AYAR `ogeler` = acik ogeler: halka, kucuk, isimler):
  - Kapatilan halka / kucuk burc GEOMETRIDE kalir: kapi 2 grup bolumu butun grup ogeleriyle AYNEN calisir (veri['grup_oge'] = geometri listesi).
  - Onayli gevsetme (O3 madde 133): olcerler ve bilgi olcumleri yalniz BOYANAN ogelerde (tek doku, kontrast, yazim, duz renk, cakisma, yildiz,
    guvenli alan ve tuval tasmasi, grup - yazi, gercek olcu, oge cifti, kucuk burc - yazi); kapi 2 sembol bolumunun "ortulen piksel" listesine
    (diger) yalniz boyanan VE ayarda acik ogeler girer (kapatilan ogenin maskesi sembolun karsilastirma bolgesini DARALTMAZ).
  - Onayli gevsetme (GK madde 147): isimler ayarda kapaliyken isim olceri; isimler kapali ve metin_tur 'yok' iken grup - yazi olceri; ayarda
    boyanan altin oge hic yokken tek doku ve kontrast olcerleri "uygulanamaz" (PASS / FAIL sayilmaz, olcer_fail'e girmez). Tetik YALNIZ AYARDAN:
    ayarda acik oge veride yoksa bugunku davranis (FAIL ya da cokme) degismez. Oge sayisi: beklenen = ayarda acik, cizilen = boyanan.
  - "Kapatilan oge gercekten yok mu" (esik yok, kapi degil): kapali ogenin geometri maskesi (alfa > 0,02) bolgesinde son gorsel - altinsiz zemin
    farki > 1 olan piksel (goruntu_farki tanimi) ve ayni sayinin boyanan oge / sembol maskeleriyle (alfa > 0,02) ortulmeyen kisimdaki degeri.
  - Kapatilan ogede 200 cekirdek piksel ve boy esitlikleri uretimde SERT (tasarim_deneme.kapali_oge_kontrol; GK madde 158: gevsetme yok).
ARACTA OLMAYANLAR (Serdar soru 6 "l"; plan inceleme bulgusu 2): ornament'in yeni duzen kapilari (yeni_duzen.py:292-321, 351) ve ornament'e ozgu
  IoU / leke / ton / sabit bosluk kapilari yoktur. Ornament'in kucultme sinirinin (ornament_motor.py:802) aractaki karsiligi OLCERDIR: isim
  kuculme orani etikette yazar; kapi eklenmedi."""
import io
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageCms

Image.MAX_IMAGE_PIXELS = None
ISIK_PAY = (0, 8)                                       # tasma olcumu isik paylari (px): 0 ve ornament degeri 8 (O4:56 GLOW_R)
ORN_REF_CEKIRDEK, ORN_YAZI_CEKIRDEK, ORN_ALFA = 7, 5, 0.05   # ornament cakisma tanimi (O4:258, 266)
_LOGO_TEMIZLIK = {}


def _at():
    AT, ATK = sys.modules.get('ay_takvim_ornek'), sys.modules.get('ay_takvim_kapi')
    if AT is None or ATK is None or ATK.U is not AT:
        raise RuntimeError('ay takvimi modulleri yuklu degil (tasarim_deneme.baglan once cagrilmali)')
    return AT, ATK


def _td():
    TD = sys.modules.get('tasarim_deneme')
    if TD is None:
        raise RuntimeError('tasarim_deneme modulu yuklu degil (serbest grup kapisi serbest kurulum fonksiyonlarini oradan cagirir)')
    return TD


def serbest_mi(ayar):
    """Hangi grup kapisinin calisacagi KAPIDA, ayardan secilir (uretim modulunden okunmaz; inceleme D1 bulgu 4): bir sembol anahtari varsayilan
    disindaysa serbest grup kapisi. Uretim ayari yok sayip eski yoldan kurarsa serbest kapi sembolu AYARA gore olcer ve FAIL verir."""
    return not (ayar['sembol_oran'] == 1.0 and ayar['sembol_u'] == 'poster' and ayar['sembol_v'] == 'poster')


OGE_AD = ('halka', 'kucuk', 'isimler')                 # ayardan kapatilabilen ogeler (tasarim_deneme.OGE_AD ile ayni; kapi kendi kopyasini okur)


def acik_ogeler(ayar):
    """AYARDA acik ogeler (kume). `ogeler` anahtari olmayan ayar (dilim D2 oncesi kayit) = hepsi acik."""
    return set(ayar.get('ogeler', OGE_AD))


def ayarda_acik(ayar, ad):
    """Altin oge adi (isimler, metin_N, halka, kucuk1, kucuk2, logo) AYARA gore acik mi. Metin ve logo `ogeler` ile kapanmaz."""
    a = acik_ogeler(ayar)
    if ad == 'isimler':
        return 'isimler' in a
    if ad == 'halka':
        return 'halka' in a
    if ad in ('kucuk1', 'kucuk2'):
        return 'kucuk' in a
    return True


def beklenen_merkez(urun, ayar):
    """Grup merkezinin BEKLENEN tuval noktasi, uretim kodundan BAGIMSIZ: urun girdisi ve ayardan dogrudan (yuvarlakta guvenli dairenin
    merkezi + grup_x / grup_y x guvenli yaricap). Uretim baska bir nokta kullanirsa kapi 2 sert FAIL verir."""
    g = urun['guvenli']
    if urun['sekil'] == 'yuvarlak':
        bx, by, br = float(g['cx']), float(g['cy']), float(g['r'])
    else:
        bx, by = (g['x0'] + g['x1']) / 2.0, (g['y0'] + g['y1']) / 2.0
        br = min(g['x1'] - g['x0'], g['y1'] - g['y0']) / 2.0
    return [bx + float(ayar['grup_x']) * br, by + float(ayar['grup_y']) * br]


def beklenen_boyut(urun, ayar):
    """Grubun BEKLENEN boyu, uretim kodundan BAGIMSIZ (urun girdisi ve ayardan dogrudan; bagimsiz inceleme 1. tur, bulgu 2):
    halka_r modunda halka yaricapi = halka_r x guvenli yaricap (plan 3.3 tanimi); grup_r modunda grubun cevre (hedef) yaricapi =
    grup_r x guvenli yaricap. Uretim baska bir olcek kullanirsa kapi 2 sert FAIL verir. Doner (mod, px)."""
    g = urun['guvenli']
    br = float(g['r']) if urun['sekil'] == 'yuvarlak' else min(g['x1'] - g['x0'], g['y1'] - g['y0']) / 2.0
    if ayar.get('halka_r') is not None:
        return 'halka_r', float(ayar['halka_r']) * br
    return 'grup_r', float(ayar['grup_r']) * br


def tuvale(a, x, y, W, H):
    """Oge alfasini tuval boyunda maskeye yazar (tasan kisim kesilir)."""
    m = np.zeros((H, W), np.float32)
    h, w = a.shape
    xa, ya, xb, yb = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if xb > xa and yb > ya:
        m[ya:yb, xa:xb] = a[ya - y:yb - y, xa - x:xb - x]
    return m


# ---------------------------------------------------------------- SERT: kapi 2
def sembol_kapisi(img, altinsiz, S, diger, katman, s_olc):
    """Kapi 2 sembol bolumu, ATK:406-440 ile ayni kosullar (deneme modu: baska ogenin orttugu sembol pikseli renk karsilastirmasina girmez).
    S: dict(rgb, a, x, y, bilgi). diger: [(x, y, maske)] sembol disindaki altin ogeler. Doner (sonuc, kaynak katman g, yan json)."""
    AT, ATK = _at()
    E = ATK.ESIK
    sa, srgb_ = S['a'].astype(np.float32), S['rgb'].astype(np.float32)
    sx, sy = S['x'], S['y']
    k05 = AT.kutu(sa, 0.5)
    eb = (k05[2] - k05[0]) / (k05[3] - k05[1])
    kaynak_gen = s_olc['kutu_alfa_05'][2] - s_olc['kutu_alfa_05'][0]
    olcek_olc = (k05[2] - k05[0]) / kaynak_gen
    bolge = img[sy:sy + sa.shape[0], sx:sx + sa.shape[1]].astype(np.float32)
    s2 = dict(en_boy_kaynak=s_olc['en_boy_05'], en_boy_yerlesen=round(eb, 5), en_boy_fark=round(abs(eb - s_olc['en_boy_05']), 5),
              olcek=S['bilgi']['olcek'], olcek_olculen=round(olcek_olc, 5))
    if bolge.shape[:2] != sa.shape:
        s2.update(PASS=False, neden='sembol bolgesi tuvalle ayni boyda degil')
        return s2, None, None
    tam = sa >= 0.999
    ortulen = np.zeros(sa.shape, bool)
    for x_, y_, m in diger:                                                   # ATK:415-423
        y0, y1 = max(sy, y_), min(sy + sa.shape[0], y_ + m.shape[0])
        x0, x1 = max(sx, x_), min(sx + sa.shape[1], x_ + m.shape[1])
        if y1 > y0 and x1 > x0:
            ortulen[y0 - sy:y1 - sy, x0 - sx:x1 - sx] |= m[y0 - y_:y1 - y_, x0 - x_:x1 - x_] > 0.02
    if ortulen.any():
        ortulen = cv2.dilate(ortulen.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0
    tam = tam & ~ortulen
    renk_fark = float(np.abs(bolge[tam] - np.round(srgb_[tam])).max()) if tam.any() else None
    alt_b = altinsiz[sy:sy + sa.shape[0], sx:sx + sa.shape[1]].astype(np.float32)
    kn = (sa > 0.02) & (sa < 0.999) & ~ortulen
    a3 = sa[..., None]
    ust_s = alt_b * (1 - a3) + srgb_ * a3 + 1.5
    alt_s = alt_b * (1 - AT.DIS_GOLGE['opak']) * (1 - a3) + srgb_ * a3 - 1.5
    kenar_disi = int(((bolge > ust_s) | (bolge < alt_s)).any(2)[kn].sum())
    s2.update(ortulen_piksel_haric=int(ortulen.sum()), kenar_piksel=int(kn.sum()), kenar_sinir_disi_piksel=kenar_disi,
              tam_alfa_piksel=int(tam.sum()), renk_fark_en_buyuk=renk_fark)
    ok = bool(s2['en_boy_fark'] <= E['en_boy'] and s2['olcek'] <= 1.0 and olcek_olc <= 1.0 + 1e-3 and renk_fark is not None
              and renk_fark <= E['sembol_renk'] and kenar_disi == 0)
    g, olc = AT.sembol_yukle(katman)                                          # kaynaktan yeniden: yalniz es oranli kucultme mi (ATK:435-440)
    rgb2, a2 = AT.rgba_olcek(g, s2['olcek'])
    ayni = bool(a2.shape == sa.shape and np.array_equal(a2.astype(np.float32), sa) and np.array_equal(rgb2.astype(np.float32), srgb_))
    s2.update(kaynak_sha256=olc['sha256'], kaynak_sha_ayni=bool(olc['sha256'] == s_olc['sha256']), yeniden_kucultme_birebir=ayni)
    s2['PASS'] = bool(ok and ayni and s2['kaynak_sha_ayni'])
    return s2, g, olc.get('yan_json')


def grup_kapisi(veri, g, yan_json):
    """Kapi 2 grup bolumu: ATK.grup_kapisi AYNEN, arac tarafindan kurulan sentetik META ile. hedef yaricap = grup_oran x sembol_alan x S
    (ATK:219) olacak bicimde grup_oran 1,0 ve sembol_alan = hedef / S verilir (uretim ayni ifadeyi kullanir). META 'disk.merkez' = BEKLENEN
    merkez (bagimsiz hesap): ATK:249 "grup merkezi = disk merkezi" kosulu boylece "grup merkezi = ayardaki nokta" olur; 'halka' merkezde
    halka merkezi de o noktada olculur (ATK:255-256).
    BOY (bagimsiz inceleme 1. tur, bulgu 2): ATK'nin "en uzak piksel = hedef yaricap" kosulunda hedef, ay takviminde AYARDAN gelir. Aracin
    halka_r modunda hedef uretimin ilk gecisinden turedigi icin o kosul uretimi kendisiyle karsilastirir; bu yuzden ek kosul: maskeden OLCULEN
    halka yaricapi (ATK cember_uydur; 'bagimsiz.halka_yaricap') = halka_r x guvenli yaricap, ayni olcum payi (ESIK grup_konum_olculen, 2 px).
    grup_r modunda sembol_alan uretimden ALINMAZ, ayardan hesaplanir (hedef = grup_r x guvenli yaricap) ve en uzak piksel onunla karsilastirilir."""
    AT, ATK = _at()
    AY, S = veri['ayar'], veri['sembol']
    bm = beklenen_merkez(veri['urun'], AY)
    mod, bpx = beklenen_boyut(veri['urun'], AY)
    if serbest_mi(AY):                                                        # dilim D1 (Serdar 12 Kas, GK1): serbest ayarda ATK.grup_kapisi CAGRILMAZ
        out = serbest_grup_kapisi(veri, g, yan_json, bm)
        return _boyut_kosulu(out, mod, bpx, [int(veri['merkez'][0]), int(veri['merkez'][1])], bm)
    sembol_alan = veri['sembol_alan'] if mod == 'halka_r' else bpx / AT.S
    ogeler = [dict(ad=o['ad'], x=int(o['x']), y=int(o['y']), gen=int(o['A'].shape[1]), yuk=int(o['A'].shape[0])) for o in veri['grup_oge']]
    meta = dict(cift=veri.get('cift', 'CANCER_LIBRA'),
                ayar=dict(grup_oran=1.0, sembol_alan=sembol_alan, grup_merkez=AY['grup_merkez'], kucuk_u=AY['kucuk_u'], kucuk_v=AY['kucuk_v'],
                          kucuk_oran=AY['kucuk_oran'], halka_kalinlik=AY['halka_kalinlik'], halka_centik=AY['halka_centik'], logo=AY['logo']),
                grup=dict(merkez=[int(veri['merkez'][0]), int(veri['merkez'][1])], ogeler=ogeler),
                sembol=dict(hedef_yaricap=veri['hedef_r'], yerlesim=dict(olcek=S['bilgi']['olcek']), olcum=dict(kutu_alfa_002=veri['s_olc']['kutu_alfa_002'])),
                disk=dict(merkez=bm))
    D = {f'gm_{i}': o['A'].astype(np.float32) for i, o in enumerate(veri['grup_oge'])}
    out = ATK.grup_kapisi(meta, D, g, yan_json, str(veri['motor']), S['a'].astype(np.float32), S['x'], S['y'])
    out['kapi'] = 'atk'
    return _boyut_kosulu(out, mod, bpx, meta['grup']['merkez'], bm)


def _boyut_kosulu(out, mod, bpx, uretim_merkez, bm):
    """Kapi 2 grup bolumunun arac eki (iki yolda da AYNI kod): beklenen / uretim merkezi kaydi ve boy kosulu (Serdar 12 Kas K1: SERT):
    halka_r modunda olculen halka yaricapi = halka_r x guvenli yaricap; grup_r modunda en uzak piksel = grup_r x guvenli yaricap; pay
    ESIK grup_konum_olculen (2 px)."""
    _, ATK = _at()
    out['beklenen_merkez'] = [round(float(v), 3) for v in bm]
    out['uretim_merkez'] = uretim_merkez
    bag = out.get('bagimsiz') or {}
    olculen = bag.get('halka_yaricap') if mod == 'halka_r' else bag.get('en_uzak_piksel')
    fark = abs(float(olculen) - bpx) if olculen is not None else None
    pay = ATK.ESIK['grup_konum_olculen']
    out['boyut_bagimsiz'] = dict(mod=mod, beklenen_px=round(bpx, 3), olculen_px=olculen, fark=round(fark, 3) if fark is not None else None, pay_px=pay,
                                 PASS=bool(fark is not None and fark <= pay))
    out['atk_PASS'] = bool(out['PASS'])                                       # grup kapisinin (ATK ya da serbest) kendi sonucu (boy kosulu haric)
    out['PASS'] = bool(out['PASS'] and out['boyut_bagimsiz']['PASS'])
    return out


def serbest_grup_kapisi(veri, g, yan_json, bm):
    """SERBEST GRUP KAPISI (dilim D1; Serdar 12 Kas 2026, kapi paketi 3: GK1 + K1 b4). Yalniz bir sembol anahtari varsayilan DISINDA iken
    calisir; o zaman ATK.grup_kapisi cagrilmaz. ATK.grup_kapisi'nin (ATK:209-360; halka_kalinlik 1,0 ve 'ozgun' dali) HER sert kosulu burada
    AYNI payla vardir (ESIK grup_konum 1 px, grup_konum_olculen 2 px: ATK.ESIK'ten okunur, burada deger yazilmaz); hedefler poster goreli
    degil AYARDAN gelir. Kosullar:
      (1) yeniden kurulum (TD.grup_kur_serbest, kapinin kendi Motor'u ve kendi ilk gecisiyle): hedef yaricap = kayit (ATK:228); ana sembol
          olcegi = kayit, ana tam sayi yer esitligi, ana olcek <= 1 (ATK:230-233); oge listesi ve sirasi (ATK:223, 234); her grup ogesi: maske
          birebir, tam sayi yer esit, yer - hedef farki <= 1 px, olcek <= 1 (ATK:238-244). Ana sembolun tam sayi yer - hedef farki yalniz
          YAZILIR (ATK:232; sert degil).
      (2) bagimsiz olcum: grup merkezi = beklenen nokta (ATK:249); halka merkezi o noktada <= 2 px (ATK:255-256); en uzak grup pikseli =
          hedef <= 2 px (ATK:257-264; hedef SERBEST ayarli ilk gecisten); cift icin poster kucuk burc yeri tanimli (ATK:300-309, 355); kucuk
          burc yer ve boy <= 2 px, 1 solda 2 sagda (ATK:310-321); logo yer ve boy <= 2 px (ATK:322-343); ana sembolun OLCULEN yeri ve boyu
          <= 2 px (ATK:345-352 ifadesi; beklenen olcek x sembol_oran, beklenen yer sembol_u / sembol_v'den: AYARA gore denetim budur).
    Donen sozluk ATK.grup_kapisi ile ayni alan adlarini tasir (oge, ana, bagimsiz, konum_fark_en_buyuk, olculen_fark_en_buyuk, PASS)."""
    AT, ATK = _at()
    TD = _td()
    E = ATK.ESIK
    AY, S = veri['ayar'], veri['sembol']
    cift = veri.get('cift', 'CANCER_LIBRA')
    hk, lg_ = float(AY['halka_kalinlik']), AY['logo']
    if AY['halka_r'] is None or AY['grup_merkez'] != 'halka' or hk != 1.0 or AY['halka_centik'] != 'ozgun':
        return dict(kapi='serbest', PASS=False, neden='serbest grup kapisi yalniz halka_r + halka merkez, halka_kalinlik 1,0, ozgun icin tanimli')
    sa, sx, sy = S['a'].astype(np.float32), S['x'], S['y']
    gb = [dict(ad=o['ad'], x=int(o['x']), y=int(o['y'])) for o in veri['grup_oge']]
    D = [o['A'].astype(np.float32) for o in veri['grup_oge']]
    mx, my = int(veri['merkez'][0]), int(veri['merkez'][1])
    mt = AT.Motor(veri['motor'])                                              # ATK:218: kapi kendi Motor'unu kurar
    _, bpx = beklenen_boyut(veri['urun'], AY)                                 # halka_r x guvenli yaricap (uretimden bagimsiz)
    ig = TD.ilk_gecis(mt, g, yan_json, AY)                                    # kapinin KENDI ilk gecisi, serbest ayarla (K1 b4)
    hedef_r = 1.0 * ((bpx / ig['R'] * ig['er']) / AT.S) * AT.S                # uretimle ayni ifade (TD.olcek_kontrol, TD.grup_hesapla)
    hedef_kur = 1.0 * ((bpx / ig['R'] * ig['er_poster']) / AT.S) * AT.S
    G = TD.grup_kur_serbest(mt, g, yan_json, AY, hedef_kur)
    adlar = ['halka', 'kucuk1', 'kucuk2'] + (['logo'] if lg_ != 'yok' else [])  # logo ayarda varsa grupta ZORUNLU, yoksa OLAMAZ (ATK:223)
    B = G['bilgi']
    (ex, ey), ol = B['cevre_merkez_poster'], B['olcek']
    pay = E['grup_konum_olculen']
    out = dict(kapi='serbest', olcek=ol, hedef_yaricap=hedef_r, hedef_yaricap_meta_ayni=bool(abs(hedef_r - veri['hedef_r']) < 1e-6), oge={},
               ilk_gecis=dict(er=ig['er'], er_poster=ig['er_poster'], er_sembol=ig.get('er_sembol')))
    # ---- (1) yeniden kurulum
    out['ana'] = dict(olcek=G['ana']['olcek'], olcek_meta_ayni=bool(abs(G['ana']['olcek'] - S['bilgi']['olcek']) < 1e-9),
                      x_ayni=bool(mx + G['ana']['x'] == sx and my + G['ana']['y'] == sy),
                      konum_fark=round(float(max(abs(sx - mx - G['ana']['hedef'][0]), abs(sy - my - G['ana']['hedef'][1]))), 3))
    ok = out['hedef_yaricap_meta_ayni'] and out['ana']['olcek_meta_ayni'] and out['ana']['x_ayni'] and G['ana']['olcek'] <= 1.0
    ok = ok and len(gb) == len(G['ogeler']) == len(adlar) and [o['ad'] for o in gb] == adlar
    if not ok:                                                                # ATK:235-237 ile ayni erken donus; neden yazilir (alanlar sessizce bos kalmaz)
        out['PASS'] = False
        out['neden'] = 'yeniden kurulum on kosulu FAIL (hedef yaricap / ana olcek / ana tam sayi yer / oge listesi): oge ve bagimsiz olcum yapilmadi'
        return out
    for om, m, og_ in zip(gb, D, G['ogeler']):
        ayni = bool(om['ad'] == og_['ad'] and m.shape == og_['A'].shape and np.array_equal(m, og_['A'].astype(np.float32)))
        yer = bool(om['x'] == mx + og_['x'] and om['y'] == my + og_['y'])
        fark = max(abs(om['x'] - mx - (og_['poster'][0] - ex) * ol), abs(om['y'] - my - (og_['poster'][1] - ey) * ol))
        out['oge'][om['ad']] = dict(yeniden_kucultme_birebir=ayni, yer_ayni=yer, konum_fark=round(float(fark), 3), olcek=og_['olcek'], k=og_['k'])
        ok = ok and ayni and yer and fark <= E['grup_konum'] and og_['olcek'] <= 1.0
    # ---- (2) bagimsiz olcum
    C = json.loads((Path(veri['motor']) / 'cember.json').read_text())['cember']
    Yl = json.loads((Path(veri['motor']) / 'yerlesim78.json').read_text())[cift]
    bag = dict(grup_merkez_disk_merkezi=bool([mx, my] == [int(round(bm[0])), int(round(bm[1]))]))
    oh, mh = gb[0], D[0]
    fx, fy, fr = ATK.cember_uydur(mh)
    hx, hy = oh['x'] + fx, oh['y'] + fy                                       # olculen halka merkezi (tuval) ve yaricapi
    s_m = fr / C['R']                                                         # olculen grup olcegi
    bag.update(halka_merkez=[round(hx, 2), round(hy, 2)], halka_yaricap=round(fr, 2), olculen_olcek=round(s_m, 5))
    bag['halka_merkezde_fark'] = round(float(max(abs(hx - mx), abs(hy - my))), 3)
    uzak = 0.0                                                                # grup merkezine en uzak grup pikseli (alfa > 0,02; piksel koseleri)
    for a_, x_, y_ in [(sa, sx, sy)] + [(m, o['x'], o['y']) for m, o in zip(D, gb)]:
        ys, xs = np.nonzero(a_ > AT.GRUP_ALFA_ESIK)
        uzak = max(uzak, float(max(np.hypot(xs + x_ + dx - mx, ys + y_ + dy - my).max() for dx in (0, 1) for dy in (0, 1))))
    bag.update(en_uzak_piksel=round(uzak, 2), en_uzak_piksel_ham=round(uzak, 2), en_uzak_fark=round(abs(uzak - hedef_r), 3))
    hko = ATK.halka_kalinlik_olc(mh, fx, fy)                                  # BILGI: maskeden olculen cizgi kalinligi (kapi degil)
    bag['halka_kalinlik'] = dict(carpan=hk, hedef_ust_px=round(hk * C['kalinlik'] * s_m, 3), **hko)
    if AY['kucuk_u'] == 'poster':
        u_h = ATK.POSTER_KUCUK_U.get(cift)
    else:
        u_h = (-float(AY['kucuk_u']), float(AY['kucuk_u']))
    v_h = (ATK.POSTER_KUCUK_Y - C['cy']) / C['R'] if AY['kucuk_v'] == 'poster' else float(AY['kucuk_v'])
    ko = float(AY['kucuk_oran'])
    olc, mer = [], []
    if u_h is None:
        bag['neden'] = 'cift icin poster kucuk sembol yeri tanimli degil'
    else:
        for i, u_ in ((1, u_h[0]), (2, u_h[1])):
            om, m, kay = gb[i], D[i], G['ogeler'][i]['kaynak']
            kk = AT.kutu(m, 0.02)
            cxk, cyk = om['x'] + (kk[0] + kk[2]) / 2.0, om['y'] + (kk[1] + kk[3]) / 2.0
            mer.append(cxk)
            d_yer = max(abs(cxk - hx - u_ * fr), abs(cyk - hy - v_h * fr))
            d_boy = abs(ATK.yatay_yayilim(m) / (ATK.yatay_yayilim(kay) * s_m * ko) - 1.0) * (kk[2] - kk[0])
            bag[om['ad']] = dict(u=round((cxk - hx) / fr, 4), v=round((cyk - hy) / fr, 4), hedef_u=u_, hedef_v=round(v_h, 5),
                                 yer_fark=round(float(d_yer), 3), genislik=int(kk[2] - kk[0]), boy_fark=round(float(d_boy), 3))
            olc += [d_yer, d_boy]
        bag['kucuk1_solda_kucuk2_sagda'] = bool(mer[0] < hx < mer[1])
    if lg_ != 'yok':                                                          # logo: yer (grup ekseni, kucuk sembol satiri) ve boy; ayni olcum payi
        om, m, kay = gb[3], D[3], G['ogeler'][3]['kaynak']
        kk = AT.kutu(m, 0.02)
        cxl, cyl = om['x'] + (kk[0] + kk[2]) / 2.0, om['y'] + (kk[1] + kk[3]) / 2.0
        d_yer = max(abs(cxl - hx), abs(cyl - hy - v_h * fr))
        d_boy = abs(ATK.yatay_yayilim(m) / (ATK.yatay_yayilim(kay) * s_m * float(lg_)) - 1.0) * (kk[2] - kk[0])
        lb = dict(oran=float(lg_), yer_fark=round(float(d_yer), 3), boy_fark=round(float(d_boy), 3), genislik_px=int(kk[2] - kk[0]), yukseklik_px=int(kk[3] - kk[1]),
                  genislik_mm=round((kk[2] - kk[0]) * 25.4 / AT.DPI, 2), yukseklik_mm=round((kk[3] - kk[1]) * 25.4 / AT.DPI, 2))
        # BILGI (esik yok; ATK:329-341 ile ayni alanlar): logo ile her kucuk sembol arasi en yakin piksel uzakligi (alfa > 0,02; kenar boslugu = mesafe - 1)
        x0_ = min(o['x'] for o in gb[1:]); y0_ = min(o['y'] for o in gb[1:])
        x1_ = max(o['x'] + q.shape[1] for o, q in zip(gb[1:], D[1:])); y1_ = max(o['y'] + q.shape[0] for o, q in zip(gb[1:], D[1:]))
        tl = np.zeros((y1_ - y0_, x1_ - x0_), np.uint8)
        tl[om['y'] - y0_:om['y'] - y0_ + m.shape[0], om['x'] - x0_:om['x'] - x0_ + m.shape[1]][m > 0.02] = 1
        dtl = cv2.distanceTransform((tl == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        for i in (1, 2):
            ok_, mk_ = gb[i], D[i]
            dl = dtl[ok_['y'] - y0_:ok_['y'] - y0_ + mk_.shape[0], ok_['x'] - x0_:ok_['x'] - x0_ + mk_.shape[1]][mk_ > 0.02]
            bos = float(dl.min()) - 1.0
            lb[f'{ok_["ad"]}_uzaklik_px'] = round(bos, 2); lb[f'{ok_["ad"]}_uzaklik_mm'] = round(bos * 25.4 / AT.DPI, 2)
            lb[f'{ok_["ad"]}_durum'] = 'cakisiyor' if bos < 0 else 'ayrik'
        bag['logo'] = lb
        olc += [d_yer, d_boy]
    # ana sembol: OLCULEN yer ve boy, hedef AYARDAN (ATK:345-352 ifadesi; beklenen olcek x sembol_oran; beklenen yer sembol_u / sembol_v).
    # Beklenen alfa > 0,02 kutusu sol ust kosesi = halka merkezi + [kaynak kutusu sol ustu + (k2 - pay) x s_ana x c] x olculen olcek;
    # kaynak kutusu sol ustu (cember merkezine gore, poster px): 'poster' = u0 x R + kw x s_ana x (1 - c) / 2; sayi = u x R - kw x s_ana x c / 2.
    # c = 1 ve 'poster' iken ATK:350-351 ile AYNI sayi. Bu hedef uretim kodundan OKUNMAZ.
    j = yan_json or {}
    pay_x, pay_y = j.get('kaynak_x', j.get('x', 0)) - j.get('x', 0), j.get('kaynak_y', j.get('y', 0)) - j.get('y', 0)
    kw, kh = j.get('kaynak_w', j.get('w', 1)), j.get('kaynak_h', j.get('h', 1))
    s_ana = (Yl['u1'] - Yl['u0']) * C['R'] / kw
    c = float(AY['sembol_oran'])
    bx = Yl['u0'] * C['R'] + kw * s_ana * (1.0 - c) / 2.0 if AY['sembol_u'] == 'poster' else float(AY['sembol_u']) * C['R'] - kw * s_ana * c / 2.0
    by = Yl['v0'] * C['R'] + kh * s_ana * (1.0 - c) / 2.0 if AY['sembol_v'] == 'poster' else float(AY['sembol_v']) * C['R'] - kh * s_ana * c / 2.0
    k2 = veri['s_olc']['kutu_alfa_002']
    ks = AT.kutu(sa, 0.02)
    d_ana = max(abs(sx + ks[0] - hx - (bx + (k2[0] - pay_x) * s_ana * c) * s_m), abs(sy + ks[1] - hy - (by + (k2[1] - pay_y) * s_ana * c) * s_m))
    d_ana_boy = abs(ATK.yatay_yayilim(sa) / (ATK.yatay_yayilim(g[..., 3]) * s_ana * s_m * c) - 1.0) * (ks[2] - ks[0])
    bag['ana'] = dict(yer_fark=round(float(d_ana), 3), boy_fark=round(float(d_ana_boy), 3), beklenen_olcek=round(float(s_ana * s_m * c), 6))
    olc += [d_ana, d_ana_boy, bag['en_uzak_fark'], bag['halka_merkezde_fark']]
    bag['fark_en_buyuk'] = round(float(max(olc)), 3)
    bag['PASS'] = bool(u_h is not None and bag['grup_merkez_disk_merkezi'] and bag.get('kucuk1_solda_kucuk2_sagda') and max(olc) <= pay)
    out['bagimsiz'] = bag
    out['konum_fark_en_buyuk'] = max([out['ana']['konum_fark']] + [v['konum_fark'] for v in out['oge'].values()])
    out['olculen_fark_en_buyuk'] = bag['fark_en_buyuk']
    out['PASS'] = bool(ok and bag['PASS'])
    return out


def sembol_halka_disi_olc(sa, sx, sy, halka_a, halka_x, halka_y):
    """BILGI (esik yok, kapi degil; Serdar 12 Kas, plan K8 b): sembol maskesinin (alfa > 0,02) halka cemberinin DISINDA kalan piksel sayisi.
    Halka cemberi = halka maskesine uydurulan cember (ATK.cember_uydur; merkez ve yaricap); piksel merkezi cember yaricapindan uzaksa
    disaridadir. Doner dict(piksel, halka_yaricap_px)."""
    _, ATK = _at()
    fx, fy, fr = ATK.cember_uydur(halka_a)
    ys, xs = np.nonzero(sa > 0.02)
    d = np.hypot(xs + 0.5 + sx - (halka_x + fx), ys + 0.5 + sy - (halka_y + fy))
    return dict(piksel=int((d > fr).sum()), halka_yaricap_px=round(float(fr), 2))


# ---------------------------------------------------------------- OLCER: olcum yardimcilari
def sirt_genislik(m_bin, ss):
    """Ikili maske (ss kat ornekli) -> sirt genislikleri (asil px). ornament_ornek4.py sirt_genislik (O4:164-168) ile ayni satirlar."""
    dt = cv2.distanceTransform(m_bin, cv2.DIST_L2, 5)
    r = (dt > 0) & (cv2.dilate(dt, np.ones((3, 3), np.uint8)) <= dt)
    return 2 * (dt[r] - 0.5) / ss


def cizgi_olc(a):
    """Yerlesen alfadan cizgi kalinligi (px): en ince ve 1. yuzdelik (O4:184-185 kalibi: 4 kat INTER_CUBIC, alfa > 0,5, sirt genislikleri)."""
    a4 = cv2.resize(np.ascontiguousarray(a, np.float32), (a.shape[1] * 4, a.shape[0] * 4), interpolation=cv2.INTER_CUBIC)
    wh = sirt_genislik((a4 > 0.5).astype(np.uint8), 4)
    if not wh.size:
        return dict(en_ince_px=None, p1_px=None)
    return dict(en_ince_px=round(float(wh.min()), 3), p1_px=round(float(np.percentile(wh, 1)), 3))


def guvenli_disi(urun, W, H, pay, ek=1):
    """Guvenli alanin DISI (pay kadar iceriden; O4:219-224 kalibi) + yasak bolgeler. ek: yasak bolge siniri payi; maske olcumunde 1 (O4:222-223:
    delik r + 1, y < ust + 1), goruntu farki olcumunde 0 (O4:431-433: delik r, y < ust). Doner (disi maske, [(ad, maske, halka_haric)])."""
    yy, xx = np.mgrid[0:H, 0:W]
    g = urun['guvenli']
    if urun['sekil'] == 'yuvarlak':
        disi = np.hypot(xx + 0.5 - g['cx'], yy + 0.5 - g['cy']) > g['r'] - pay
    else:
        disi = (xx + 0.5 < g['x0'] + pay) | (xx + 0.5 > g['x1'] - pay) | (yy + 0.5 < g['y0'] + pay) | (yy + 0.5 > g['y1'] - pay)
    yasak = []
    for i, y in enumerate(urun['yasak'], 1):
        if y['tur'] == 'daire':
            m = np.hypot(xx + 0.5 - y['cx'], yy + 0.5 - y['cy']) <= y['r'] + ek
        elif y['tur'] == 'kutu':
            m = (xx >= y['x0']) & (xx <= y['x1']) & (yy >= y['y0']) & (yy <= y['y1'])
        else:
            m = yy < y['y'] + ek
        yasak.append((y.get('ad', f"{y['tur']}_{i}"), m, bool(y.get('halka_haric', False))))
    return disi, yasak


def tasma_olc(urun, M, son, altinsiz, tuval_kesilen):
    """Guvenli alan / yasak bolge tasmasi, UC olcum (Serdar soru 6 "i": isik payi degeri karara baglanmadi):
    isik_0 / isik_8: oge maskesi (alfa > 0,02), isik payi kadar genisletilip (O4:249) guvenli alan disi + yasak bolgeyle kesisim, oge basina;
    goruntu_farki: son gorsel ile altinsiz zemin farki > 1 olan pikseller (dis golge dahil), guvenli yaricapin disi (pay yok) + yasak bolgeler
    (sinir payi yok; 'halka_haric' bolgede halka maskesi isik payi (8 px) kadar genisletilip haric tutulur): O4:425-433 goruntu_yasak ile ayni.
    M: {ad: tuval boyu maske}. Doner dict; PASS = uc olcum de 0 ve tuval disi 0."""
    H, W = son.shape[:2]
    pay = float(urun['guvenli_pay_px'])
    disi, yasak = guvenli_disi(urun, W, H, pay)
    out = dict(oge={}, guvenli_pay_px=pay)
    top = {}
    for isik in ISIK_PAY:
        K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * isik + 1,) * 2) if isik else None
        t = 0
        for ad, m in M.items():
            mg = (m > 0.02).astype(np.uint8)
            if K is not None:
                mg = cv2.dilate(mg, K)
            mg = mg > 0
            n = int((mg & disi).sum())
            for _, ym, halka_haric in yasak:
                if halka_haric and ad == 'halka':
                    continue
                n += int((mg & ym).sum())
            out['oge'].setdefault(ad, {})[f'isik_{isik}'] = n
            t += n
        top[f'isik_{isik}'] = t
    fark = np.abs(son.astype(np.float32) - altinsiz.astype(np.float32)).max(2) > 1.0
    disi0, yasak0 = guvenli_disi(urun, W, H, 0.0, ek=0)
    if 'halka' in M:
        halka_b = cv2.dilate((M['halka'] > 0.02).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * ISIK_PAY[1] + 1,) * 2)) > 0
    else:
        halka_b = np.zeros((H, W), bool)
    n = int((fark & disi0).sum())
    for _, ym, halka_haric in yasak0:
        n += int((fark & ym & ~(halka_b if halka_haric else np.zeros((H, W), bool))).sum())
    top['goruntu_farki'] = n
    top['tuval_disi'] = int(sum(tuval_kesilen.values()))
    out.update(toplam=top, tuval_disi_oge={k_: v for k_, v in tuval_kesilen.items() if v},
               PASS=bool(all(v == 0 for v in top.values())))
    return out


def cakisma_takvim(sira):
    """Ay takvimi tanimi (ATK:504-518): ogeler sirayla tuvale yazilir; alfa > 0,02 pikseli daha once yazilmis bir ogeye denk gelirse sayilir
    (paysiz). sira: [(ad, tuval maskesi)] yazilar, grup ogeleri, EN SON sembol. Doner piksel sayisi."""
    altin = None
    binme = 0
    for _, m in sira:
        ink = m > 0.02
        if altin is None:
            altin = np.zeros(m.shape, bool)
        binme += int((altin & ink).sum())
        altin |= ink
    return binme


def cakisma_ornament(M):
    """Ornament tanimi (O4:255-269): referans ogeler (halka, sembol) 7 x 7 genisletilir, diger her ogeyle (alfa > 0,05) kesisim; halka /
    sembol cifti; kalan ogeler (yazilar, kucuk burclar, logo) kendi aralarinda 5 x 5 genisletmeyle. Ornament yalniz cift listesi doner;
    burada cift basina piksel sayisi da yazilir (genisletilmis ilk maske ile ikinci maskenin kesisimi). Doner {cift: piksel}."""
    out = {}
    ref = [r for r in ('halka', 'sembol') if r in M]
    kr = np.ones((ORN_REF_CEKIRDEK,) * 2, np.uint8)
    ky = np.ones((ORN_YAZI_CEKIRDEK,) * 2, np.uint8)
    for r in ref:
        rm = cv2.dilate((M[r] > ORN_ALFA).astype(np.uint8), kr) > 0
        for ad in M:
            if ad not in ref:
                n = int((rm & (M[ad] > ORN_ALFA)).sum())
                if n:
                    out[f'{r}/{ad}'] = n
    if len(ref) == 2:
        n = int(((cv2.dilate((M['halka'] > ORN_ALFA).astype(np.uint8), kr) > 0) & (M['sembol'] > ORN_ALFA)).sum())
        if n:
            out['halka/sembol'] = n
    yazi = [k_ for k_ in M if k_ not in ('halka', 'sembol')]
    for i, a1 in enumerate(yazi):
        d1 = cv2.dilate((M[a1] > ORN_ALFA).astype(np.uint8), ky) > 0
        for a2 in yazi[i + 1:]:
            n = int((d1 & (M[a2] > ORN_ALFA)).sum())
            if n:
                out[f'{a1}/{a2}'] = n
    return out


def cift_px_olc(M):
    """BILGI (esik yok, kapi degil; Serdar 12 Kas): oge cifti basina cakisma = iki maskenin (alfa > 0,02) kesisim piksel sayisi. Doner {a/b: piksel}
    (butun ciftler, 0 dahil; ad sirasi M'nin sirasi)."""
    Bm = {ad: M[ad] > 0.02 for ad in M}
    adlar = list(Bm)
    return {f'{a1}/{a2}': int((Bm[a1] & Bm[a2]).sum()) for i_, a1 in enumerate(adlar) for a2 in adlar[i_ + 1:]}


def kucuk_yazi_olc(M, yazi_adlari):
    """BILGI (esik yok, kapi degil; Serdar 12 Kas): kucuk1 / kucuk2 maskelerinin (alfa > 0,02) her yazi ogesinin maskesine en az uzakligi (px;
    piksel merkezleri arasi: binme varsa 0, bitisik 1). Doner {kucukN/yazi: px}; murekkebi olmayan maske atlanir."""
    out = {}
    for ya in yazi_adlari:
        by = M[ya] > 0.02
        if not by.any():
            continue
        dty = cv2.distanceTransform((~by).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
        for kad in ('kucuk1', 'kucuk2'):
            bk = (M[kad] > 0.02) if kad in M else None
            if bk is not None and bk.any():
                out[f'{kad}/{ya}'] = round(float(dty[bk].min()), 2)
    return out


def cikti_olc(png, urun):
    """Cikti kapisi (ATK:593-601 kalibi; boyut ve dpi urun girdisinden). SERT (Serdar 12 Kas K4; dilim 1'de olcerdi)."""
    im = Image.open(png)
    W, H = int(urun['baski_px'][0]), int(urun['baski_px'][1])
    dpi_b = 25.4 * W / float(urun['gercek_mm'][0])
    dpi = im.info.get('dpi') or (0, 0)
    icc = im.info.get('icc_profile')
    try:
        icc_ad = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip() if icc else None
    except Exception:                                                        # noqa: BLE001
        icc_ad = None
    r = dict(boyut=[im.size[0], im.size[1]], beklenen_boyut=[W, H], dpi=[round(float(dpi[0]), 2), round(float(dpi[1]), 2)],
             beklenen_dpi=round(dpi_b, 2), mod=im.mode, icc=icc_ad)
    r['PASS'] = bool(im.size == (W, H) and abs(dpi[0] - dpi_b) < 0.1 and abs(dpi[1] - dpi_b) < 0.1 and im.mode == 'RGB'
                     and icc_ad is not None and 'sRGB' in icc_ad)
    return r


def logo_temizlik_olc(mt):
    """BILGI (esik yok): AT.logo_kaynak'in temizlik adiminin ham kesime farki. Kesim ve olcek adimlari AT:1163-1168 ile ayni satirlar;
    temizlik AT:1169-1170 (mt.temizle). Doner degisen piksel, IoU (alfa > 127) ve boyut. Kosu basina bir kez hesaplanir."""
    AT, _ = _at()
    anahtar = str(mt.md)
    if anahtar not in _LOGO_TEMIZLIK:
        y0_, y1_, x0_, x1_ = AT.LOGO_KUTU
        lg = np.asarray(Image.open(mt.md / 'girdi' / 'LOGO_1.png').convert('L'))[y0_:y1_, x0_:x1_].astype(np.float32)
        ys, xs = np.nonzero(lg > 8)
        lg = lg[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        lg = cv2.resize(lg, None, fx=AT.LOGO_OLCEK, fy=AT.LOGO_OLCEK, interpolation=cv2.INTER_AREA)
        ham = np.pad(np.clip(lg, 0, 255).astype(np.uint8), 40)
        l8, bilgi = mt.temizle(ham.copy())
        a, b = ham > 127, l8 > 127
        _LOGO_TEMIZLIK[anahtar] = dict(poster_boy_px=[int(lg.shape[1]), int(lg.shape[0])], degisen_piksel=int((ham != l8).sum()),
                                       en_buyuk_fark=int(np.abs(ham.astype(np.int16) - l8.astype(np.int16)).max()),
                                       murekkep_piksel_ham=int(a.sum()), murekkep_piksel_temiz=int(b.sum()),
                                       iou_alfa_127=round(float((a & b).sum() / max((a | b).sum(), 1)), 5),
                                       temizle_bilgi={k_: (v if isinstance(v, (int, float, str, bool)) else str(v)) for k_, v in (bilgi or {}).items()})
    return _LOGO_TEMIZLIK[anahtar]


# ---------------------------------------------------------------- tum kapilar
def olc(veri):
    """Bir secenegin butun kapilari ve olcumleri. veri: tasarim_deneme.secenek_uret'in kurdugu sozluk. Doner dict(ozet, oge, kapi, esik)."""
    AT, ATK = _at()
    E = ATK.ESIK
    urun, AY, S = veri['urun'], veri['ayar'], veri['sembol']
    png = Path(veri['png'])
    im = Image.open(png)
    img = np.asarray(im.convert('RGB'))
    altinsiz, yildiz = veri['altinsiz'], veri['yildiz_maske']
    Hh, Ww = altinsiz.shape[:2]                                               # cizim tuvali (maskelerin koordinati)
    dosya_boyut_farki = bool(img.shape[:2] != (Hh, Ww))
    if dosya_boyut_farki:                                                     # kaydedilen dosya tuvalle ayni boyda degil: cikti kapisi FAIL verir (SERT,
        t_ = np.zeros((Hh, Ww, 3), np.uint8)                                  # Serdar 12 Kas K4); olcumler dosyanin sol ust koseden tuvale oturtulmus
        h_, w_ = min(Hh, img.shape[0]), min(Ww, img.shape[1])                 # haliyle yapilir (eksik bolge siyah, fazla bolge olcum disi); cokme yok
        t_[:h_, :w_] = img[:h_, :w_]
        img = t_
    # dilim D2: gg_tum = GEOMETRI listesi (kapi 2 grup bolumu; kapatilan halka / kucuk burc icinde); gg = BOYANAN grup ogeleri (uretimin altin
    # cizimine verdigi liste; `boyanan` isareti olmayan eski veri = hepsi boyanmis). Olcerler ve bilgi olcumleri yalniz boyanan ogelerde.
    og, gg_tum = veri['ogeler'], veri['grup_oge']
    gg = [o for o in gg_tum if o.get('boyanan', True)]
    acik = acik_ogeler(AY)
    isim_kapali = 'isimler' not in acik                                       # "uygulanamaz" tetigi YALNIZ ayardan
    sa, sx, sy = S['a'], S['x'], S['y']
    mmpx = float(urun['gercek_mm'][0]) / float(urun['baski_px'][0])
    alt = urun.get('alt_sinir')
    sert, olcer = {}, {}

    # ---- SERT kapi 2
    diger = [(o['x'], o['y'], o['A']) for o in og + gg if ayarda_acik(AY, o['ad'])]   # yalniz boyanan VE ayarda acik (kapali oge bolgeyi daraltmaz)
    s2, g, yan = sembol_kapisi(img, altinsiz, S, diger, veri['katman'], veri['s_olc'])
    sert['2_sembol'] = s2
    if g is not None:
        sert['2_grup'] = grup_kapisi(veri, g, yan)
        del g
    else:
        sert['2_grup'] = dict(PASS=False, neden='sembol kapisi kaynak katmani okuyamadi')

    def pencere(o, pay=0):
        h, w = o['A'].shape
        return max(0, o['y'] - pay), min(Hh, o['y'] + h + pay), max(0, o['x'] - pay), min(Ww, o['x'] + w + pay)

    def pencerede(o, pay):
        y0, y1, x0, x1 = pencere(o, pay)
        out = np.zeros((y1 - y0, x1 - x0), np.float32)
        h, w = o['A'].shape
        out[o['y'] - y0:o['y'] - y0 + h, o['x'] - x0:o['x'] - x0 + w] = o['A']
        return out, (y0, y1, x0, x1)

    # ---- OLCER: tek doku, kontrast, yazim, duz renk (ATK:453-499 dongusu ile ayni olcumler)
    bolge = img[sy:sy + sa.shape[0], sx:sx + sa.shape[1]].astype(np.float32)
    Ls = np.median(AT.labf(bolge[sa >= 0.9]), 0)
    t3, k4, y5, duz = {}, {}, {}, {}
    for o in og + gg:
        m, t = o['A'], o['atest']
        y0, y1, x0, x1 = pencere(o)
        b = img[y0:y1, x0:x1].astype(np.float32)
        ce = m >= 0.9
        n = int(ce.sum())
        t3[o['ad']] = dict(piksel=n, dE00=round(AT.de00(Ls, np.median(AT.labf(b[ce]), 0)), 3) if n >= 5 else None)
        mt_, (wy0, wy1, wx0, wx1) = pencerede(o, 20)
        k4[o['ad']] = ATK.kontrast_olc(img[wy0:wy1, wx0:wx1], mt_)
        murekkep = (t > 0.02) | (m > 0.02)
        y5[o['ad']] = round(float(np.abs(t - m)[murekkep].mean()), 4)
        Lc = ATK.lum(b[ce]) if n >= 5 else np.zeros(1)
        duz[o['ad']] = round(float(np.percentile(Lc, 95) - np.percentile(Lc, 5)), 2)
    de = [v['dE00'] for v in t3.values() if v['dE00'] is not None]
    beklenen = [ad_ for ad_ in ['isimler'] + [f'metin_{i + 1}' for i in range(len(AY['satirlar']))] + ['halka', 'kucuk1', 'kucuk2']
                + (['logo'] if AY['logo'] != 'yok' else []) if ayarda_acik(AY, ad_)]   # beklenen = AYARDA acik ogeler
    cizilen = [o['ad'] for o in og + gg]                                      # cizilen = boyanan ogeler
    olcer['oge_sayisi'] = dict(beklenen=beklenen, cizilen=cizilen, PASS=bool(beklenen == cizilen))
    if not beklenen:                                                          # ayarda boyanan altin oge HIC yok (ayardan): olculecek oge yok
        en_az = None
        olcer['tek_doku'] = dict(uygulanamaz=True, PASS=None, neden='ayarda boyanan altin oge yok', oge=t3, sembol_Lab=[round(float(v), 2) for v in Ls])
        olcer['kontrast'] = dict(uygulanamaz=True, PASS=None, neden='ayarda boyanan altin oge yok', oge=k4)
    else:
        en_az = min(t3.items(), key=lambda kv: kv[1]['piksel'])
        olcer['tek_doku'] = dict(oge=t3, en_kotu_dE00=max(de) if de else None, en_az_piksel=en_az[1]['piksel'], en_az_piksel_oge=en_az[0],
                                 sembol_Lab=[round(float(v), 2) for v in Ls],
                                 PASS=bool(de and len(de) == len(t3) and max(de) <= E['dE00'] and en_az[1]['piksel'] >= E['cekirdek_piksel']))
        ko = [v.get('ortanca_bilgi') for v in k4.values()]
        olcer['kontrast'] = dict(oge=k4, en_kotu_ortanca=min(ko) if all(v is not None for v in ko) else None,
                                 PASS=bool(all(v is not None for v in ko) and min(ko) >= E['kontrast']))
    y5g = {o['ad']: y5.pop(o['ad']) for o in gg}                               # grup ogeleri yalniz bilgi (ATK:498)
    olcer['yazim'] = dict(oge=y5, grup_bilgi=y5g, en_kotu=max(y5.values()) if y5 else None, PASS=bool(not y5 or max(y5.values()) <= E['alfa_fark']))
    halka_duz = duz.pop('halka', None)                                        # halkanin yayilimi yalniz bilgi (ATK:560)
    olcer['duz_renk'] = dict(oge=duz, en_dusuk=min(duz.values()) if duz else None, halka_bilgi=halka_duz,
                             PASS=bool(not duz or min(duz.values()) >= E['duz_yayilim']))

    # ---- tuval boyu maskeler
    M = {o['ad']: tuvale(o['A'], o['x'], o['y'], Ww, Hh) for o in og + gg}
    M['sembol'] = tuvale(sa, sx, sy, Ww, Hh)
    altin = np.zeros((Hh, Ww), np.uint8)
    for m in M.values():
        altin[m > 0.02] = 255
    # yildiz (ATK:561-566; kapi payi 12 px AYNEN, engel payi uretimde AYNEN: Serdar soru 6 "j")
    yp = 2 * E['yildiz_pay'] + 1
    yb = int(((yildiz > 0) & (cv2.dilate(altin, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (yp, yp))) > 0)).sum())
    olcer['yildiz'] = dict(yildiz_altin_binme_piksel=yb, kapi_payi_px=E['yildiz_pay'], **veri['yildiz'], PASS=bool(yb == 0))
    # grup - yazi boslugu (ATK:521-530 "grup - ay adi" olcumunun karsiligi; esik 12 px AYNEN; Serdar soru 6 "g")
    grup = np.zeros((Hh, Ww), np.uint8)
    for ad in ['sembol'] + [o['ad'] for o in gg]:
        grup[M[ad] > 0.02] = 255
    dtg = cv2.distanceTransform((grup == 0).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    gy = {}
    for o in og:
        ink = M[o['ad']] > 0.5
        gy[o['ad']] = round(float(dtg[ink].min()) - 1.0, 2) if ink.any() else None
    gyv = [v for v in gy.values() if v is not None]
    if isim_kapali and AY['metin_tur'] == 'yok':                              # ayarda HIC yazi yok (ayardan): olculecek yazi yok
        olcer['grup_yazi'] = dict(uygulanamaz=True, PASS=None, neden='ayarda yazi yok (isimler kapali, metin_tur yok)', oge=gy, en_az=None, esik_px=E['grup_yazi'])
    else:
        olcer['grup_yazi'] = dict(oge=gy, en_az=min(gyv) if gyv else None, esik_px=E['grup_yazi'],
                                  PASS=bool(gyv and len(gyv) == len(gy) and min(gyv) >= E['grup_yazi']))
    del dtg, grup
    # cakisma: iki tanim (Serdar soru 6 "e")
    sira = [(o['ad'], M[o['ad']]) for o in og + gg] + [('sembol', M['sembol'])]
    ct = cakisma_takvim(sira)
    co = cakisma_ornament(M)
    olcer['cakisma'] = dict(takvim_binme_piksel=ct, ornament_cift=co, ornament_cift_sayisi=len(co), ornament_piksel_toplam=int(sum(co.values())),
                            PASS=bool(ct == 0 and not co))
    # tasma: uc olcum (Serdar soru 6 "d", "i")
    olcer['tasma'] = tasma_olc(urun, M, img, altinsiz, veri['tuval_kesilen'])
    olcer['tuval_tasma'] = veri['kontrol']['tasma']
    # cikti (SERT: Serdar 12 Kas K4; FAIL veren secenek DUR verir)
    sert['cikti'] = cikti_olc(png, urun)
    sert['cikti']['tuval_boyut_farki'] = dosya_boyut_farki
    if dosya_boyut_farki or [Ww, Hh] != [int(urun['baski_px'][0]), int(urun['baski_px'][1])]:
        sert['cikti']['PASS'] = False
    # BILGI (esik yok, kapi degil; Serdar 12 Kas): oge cifti basina cakisma ve kucuk burc - yazi en az uzakligi
    cift_px = cift_px_olc(M)
    ky = kucuk_yazi_olc(M, [o['ad'] for o in og])
    ky_isim = [v for k_, v in ky.items() if k_.endswith('/isimler')]
    ky_metin = [v for k_, v in ky.items() if '/metin_' in k_]
    halka_o = next((o for o in gg_tum if o['ad'] == 'halka'), None)           # halka kapaliyken de GEOMETRI maskesiyle (bugunku gibi)
    try:
        halka_disi = sembol_halka_disi_olc(sa, sx, sy, halka_o['A'], halka_o['x'], halka_o['y']) if halka_o is not None else None
    except Exception:                                                        # noqa: BLE001  (halka maskesine cember uydurulamadi: bilgi yazilmaz)
        halka_disi = None
    # "kapatilan oge gercekten yok mu" (esik yok, kapi degil; Serdar 12 Kas, O3 madde 133): ayarda kapali her grup ogesinin GEOMETRI maskesi
    # (alfa > 0,02) bolgesinde son gorsel - altinsiz zemin farki > 1 olan piksel (tasma olcumundeki goruntu_farki tanimi); ayrica o bolgenin, o oge
    # DISINDAKI boyanan ogelerin ve sembolun maskeleriyle (alfa > 0,02) ortulmeyen kisminda ayni sayi.
    yok_mu = {}
    kap_g = [o for o in gg_tum if not ayarda_acik(AY, o['ad'])]
    if kap_g:
        fark_m = np.abs(img.astype(np.float32) - altinsiz.astype(np.float32)).max(2) > 1.0
        for o in kap_g:
            mk = tuvale(o['A'], o['x'], o['y'], Ww, Hh) > 0.02
            ortu = np.zeros((Hh, Ww), bool)
            for ad_, m_ in M.items():
                if ad_ != o['ad']:
                    ortu |= m_ > 0.02
            yok_mu[o['ad']] = dict(maske_piksel=int(mk.sum()), goruntu_farki=int((fark_m & mk).sum()), ortulmeyen_piksel=int((mk & ~ortu).sum()),
                                   ortulmeyen_goruntu_farki=int((fark_m & mk & ~ortu).sum()), boyanmis=bool(o.get('boyanan', True)))
        del fark_m
    if isim_kapali:                                                           # isim satiri kurulmaz: geometri maskesi yok; veride isim ogesi varsa yazilir
        yok_mu['isimler'] = dict(maske_piksel=None, goruntu_farki=None, ortulmeyen_piksel=None, ortulmeyen_goruntu_farki=None,
                                 boyanmis=bool(any(o['tur'] == 'isim' for o in og)), not_='isim satiri kurulmaz: geometri maskesi yok')
    bilgi = dict(cift_px=cift_px, kucuk_yazi_uzaklik=ky, sembol_halka_disi=halka_disi, kapali_yok_mu=yok_mu,
                 not_='cift_px: iki maskenin (alfa > 0,02) kesisim pikseli; kucuk_yazi_uzaklik: piksel merkezleri arasi en az uzaklik (0 = binme)')
    # isim satiri, metin genisligi, metin tabani
    isim = veri['isim']
    if isim_kapali:                                                           # Serdar 13 Kas (GK madde 147): isimler AYARDA kapali -> isim olceri uygulanamaz
        kuculme, isim_dis = None, None
        olcer['isim'] = dict(uygulanamaz=True, PASS=None, neden='isimler ayarda kapali')
    else:                                                                     # isim ayarda acik: bugunku kod AYNEN (veride isim yoksa bugunku gibi coker)
        oi = next(o for o in og if o['tur'] == 'isim')
        ki = AT.kutu(oi['A'])
        kuculme = round(isim['cap'] / isim['cap_baslangic'], 4)
        alt_px = alt['yazi_mm'] / mmpx if alt else None
        isim_dis = bool(isim.get('guvenli_disinda'))                          # K3: buyuk harf bandi guvenli dairenin disinda (sinir = tuval genisligi)
        olcer['isim'] = dict(genislik=int(ki[2] - ki[0]), sinir=round(isim['sinir'], 1), cap_px=round(isim['cap'], 2), cap_mm=round(isim['cap'] * mmpx, 3),
                             kuculme_orani=kuculme, deneme=isim['deneme'], alt_sinir_px=round(alt_px, 2) if alt_px else None, guvenli_disinda=isim_dis,
                             PASS=bool(ki[2] - ki[0] <= isim['sinir'] and (alt_px is None or isim['cap'] >= alt_px) and not isim_dis))
    olcer['metin_genis'] = veri['kontrol']['metin_genis']
    om = [o for o in og if o['tur'] == 'metin']
    if om:
        son_o = om[-1]
        ks = AT.kutu(son_o['A'])
        alt_y = son_o['taban_y']
        olcer['metin_taban'] = dict(murekkep_alt=int(son_o['y'] + ks[3]), taban_y=round(float(alt_y), 2),
                                    PASS=bool(son_o['y'] + ks[3] >= alt_y - 2 and son_o['y'] + ks[3] <= alt_y + 0.45 * son_o['cap'] + 2))
    else:
        olcer['metin_taban'] = dict(PASS=True, not_='metin yok')

    # ---- oge olcumleri ve gercek olcu uyarisi (mm = px x gercek mm / baski alani px)
    oge = {}

    def kayit(ad, a, x, y, tur, ortanca_px, ek=None):
        k_ = AT.kutu(a, 0.5) if (a > 0.5).any() else AT.kutu(a, 0.02)
        c = cizgi_olc(a)
        r = dict(tur=tur, kutu=[int(x + k_[0]), int(y + k_[1]), int(x + k_[2]), int(y + k_[3])], genislik_px=int(k_[2] - k_[0]), yukseklik_px=int(k_[3] - k_[1]),
                 genislik_mm=round((k_[2] - k_[0]) * mmpx, 3), yukseklik_mm=round((k_[3] - k_[1]) * mmpx, 3),
                 cizgi=dict(en_ince_px=c['en_ince_px'], p1_px=c['p1_px'], ortanca_px=round(float(ortanca_px), 3) if ortanca_px is not None else None))
        for q in ('en_ince', 'p1', 'ortanca'):
            v = r['cizgi'][q + '_px']
            r['cizgi'][q + '_mm'] = round(v * mmpx, 4) if v is not None else None
        r['isaret'] = []
        if alt:
            for q in ('en_ince', 'p1', 'ortanca'):
                v = r['cizgi'][q + '_mm']
                r['cizgi'][q + '_sinir_alti'] = bool(v is not None and v < alt['cizgi_mm'])
                if r['cizgi'][q + '_sinir_alti']:
                    r['isaret'].append(f"cizgi {q} {v} mm < {alt['cizgi_mm']}")
        if ek:
            r.update(ek)
        oge[ad] = r
        return r

    kayit('sembol', sa, sx, sy, 'sembol', 2.0 * veri['D_ana'], dict(olcek=S['bilgi']['olcek']))
    for o in og:
        ek = dict(karakter=len(o['metin']), buyuk_harf_px=round(o['cap'], 2), buyuk_harf_mm=round(o['cap'] * mmpx, 3), k=int(o['k']),
                  cekirdek_piksel=o['uyum']['piksel'])
        if any(ch.islower() for ch in o['metin']):                            # kucuk harf (x) yuksekligi yalniz karisik harfli metinde, fontun 'x' glifinden
            Ax, _ = AT.metin_alfa('x', o['font'], o['cap'], o['wght'], o['ref'])
            kx = AT.kutu(Ax, 0.5)
            ek.update(kucuk_harf_px=int(kx[3] - kx[1]), kucuk_harf_mm=round((kx[3] - kx[1]) * mmpx, 3))
        r = kayit(o['ad'], o['A'], o['x'], o['y'], o['tur'], 2.0 * o['yari_kal'], ek)
        if alt:
            r['yazi_sinir_alti'] = bool(r['buyuk_harf_mm'] < alt['yazi_mm'])
            if r['yazi_sinir_alti']:
                r['isaret'].insert(0, f"yazi {r['buyuk_harf_mm']} mm < {alt['yazi_mm']}")
    gb = veri['grup_bilgi']
    for o in gg:
        ek = dict(k=int(o['k']), olcek=o['olcek'], cekirdek_piksel=o['uyum']['piksel'])
        if o['ad'] == 'halka':
            fx, fy, fr = ATK.cember_uydur(o['A'])
            hk = ATK.halka_kalinlik_olc(o['A'], fx, fy)                       # px alanlari; mm alani U.DPI ile oldugu icin kullanilmaz
            nominal = gb['cember']['kalinlik'] * gb['olcek'] * float(gb.get('halka_carpan', 1.0))
            ek.update(nominal_kalinlik_px=round(nominal, 3), nominal_kalinlik_mm=round(nominal * mmpx, 4), yaricap_px=round(fr, 2), yaricap_mm=round(fr * mmpx, 3),
                      olculen=dict(ust_px=hk['ust_px'], en_buyuk_px=hk['en_buyuk_px'], ortanca_px=hk['ortanca_px'], kapsam_derece=hk['kapsam_derece'],
                                   ust_mm=round(hk['ust_px'] * mmpx, 4), ortanca_mm=round(hk['ortanca_px'] * mmpx, 4)))
        if o['ad'] == 'logo':
            kl = AT.kutu(o['A'], 0.5)
            ek.update(carpan=AY['logo'], logo_isim_buyuk_harf_orani=round((kl[3] - kl[1]) / isim['cap'], 3) if isim.get('cap') else None,
                      temizlik=logo_temizlik_olc(veri['mt']),
                      bilgi=gb.get('logo'))
        kayit(o['ad'], o['A'], o['x'], o['y'], 'grup', 2.0 * o['yari_kal'], ek)
    for ad, v in olcer['tasma']['oge'].items():
        if v.get('isik_0'):
            oge[ad]['isaret'].append(f"tasma {v['isik_0']} px")
    yazi_mm = [oge[o['ad']]['buyuk_harf_mm'] for o in og]

    def enk(q):
        v = [r['cizgi'][q + '_mm'] for r in oge.values() if r['cizgi'][q + '_mm'] is not None]
        return min(v) if v else None
    sinir_alti = dict(yazi=sum(1 for o in og if oge[o['ad']].get('yazi_sinir_alti')),
                      cizgi_en_ince=sum(1 for r in oge.values() if r['cizgi'].get('en_ince_sinir_alti')),
                      cizgi_p1=sum(1 for r in oge.values() if r['cizgi'].get('p1_sinir_alti')),
                      cizgi_ortanca=sum(1 for r in oge.values() if r['cizgi'].get('ortanca_sinir_alti')))
    olcer['gercek_olcu'] = dict(alt_sinir=alt, sinir_alti=sinir_alti, mm_px=round(mmpx, 6), mm_kaynak=urun['mm_kaynak'],
                                not_=None if alt else 'sinir tanimsiz', PASS=bool(not alt or not any(sinir_alti.values())))

    sert_fail = [k_ for k_, v in sert.items() if not v['PASS']]
    uygulanamaz = [k_ for k_, v in olcer.items() if v.get('uygulanamaz')]     # PASS / FAIL sayilmaz (yalniz ayarda kapali ogeye bagli olcerler)
    olcer_fail = [k_ for k_, v in olcer.items() if not v.get('uygulanamaz') and not v['PASS']]
    tt = olcer['tasma']['toplam']
    # K2 etiketi (Serdar 12 Kas; kapi sonucu ve kodu DEGISMEZ, yeni olcum yok): sert FAIL listesi tek basina '2_grup' VE yeniden kurulumda
    # dusen ogelerin (ATK:240-244 kosullari) HEPSI tuvalde kirpilmis ise kok neden yazilir; aksi halde yazilmaz.
    kok_neden = None
    if sert_fail == ['2_grup']:
        g2 = sert['2_grup']
        dusen = [ad for ad, v in (g2.get('oge') or {}).items()
                 if not (v['yeniden_kucultme_birebir'] and v['yer_ayni'] and v['konum_fark'] <= E['grup_konum'] and v['olcek'] <= 1.0)]
        kirpilan = set(veri.get('tuval_kirpilan') or [])
        if dusen and all(ad in kirpilan for ad in dusen):
            kok_neden = f"grup ogesi tuvalden tasiyor: {', '.join(dusen)}; konum farki {g2.get('konum_fark_en_buyuk')} px"
    ozet = dict(ad=png.stem, durum='DUR' if sert_fail else 'tamam', sert_fail=sert_fail, olcer_fail=olcer_fail,
                yazi_en_kucuk_mm=min(yazi_mm) if yazi_mm else None, isim_kuculme=kuculme,
                cizgi_mm=dict(en_ince=enk('en_ince'), p1=enk('p1'), ortanca=enk('ortanca')), sinir_alti=sinir_alti,
                tasma_px=dict(isik_0=tt['isik_0'], isik_8=tt['isik_8'], goruntu_farki=tt['goruntu_farki'], tuval_disi=tt['tuval_disi']),
                cakisma=dict(takvim_px=ct, ornament_cift=len(co), ornament_px=int(sum(co.values())), ornament_ciftler=co),
                cift_px=dict(cift_px),
                kucuk_yazi_px=dict(isim=min(ky_isim) if ky_isim else None, metin=min(ky_metin) if ky_metin else None),
                kok_neden=kok_neden, isim_guvenli_disinda=isim_dis, yildiz_sayi=int(veri['yildiz']['sayi']),
                # dilim D1: sembol ozeti (BILGI + kapi 2'nin sembole ait OLCULEN farklari; esik burada yok)
                sembol=dict(oran=AY['sembol_oran'], u=AY['sembol_u'], v=AY['sembol_v'], olcek=round(float(S['bilgi']['olcek']), 6),
                            kutu_px=[int(S['bilgi']['kutu_05'][2] - S['bilgi']['kutu_05'][0]), int(S['bilgi']['kutu_05'][3] - S['bilgi']['kutu_05'][1])],
                            en_boy_fark=sert['2_sembol'].get('en_boy_fark'),
                            yer_fark=((sert['2_grup'].get('bagimsiz') or {}).get('ana') or {}).get('yer_fark'),
                            boy_fark=((sert['2_grup'].get('bagimsiz') or {}).get('ana') or {}).get('boy_fark'),
                            tam_sayi_yer_fark=(sert['2_grup'].get('ana') or {}).get('konum_fark'),
                            tam_alfa_piksel=sert['2_sembol'].get('tam_alfa_piksel'), ortulen_piksel_haric=sert['2_sembol'].get('ortulen_piksel_haric'),
                            halka_disi_px=halka_disi['piksel'] if halka_disi else None, grup_kapisi=sert['2_grup'].get('kapi')),
                grup_yazi_en_az_px=olcer['grup_yazi']['en_az'], cikti='PASS' if sert['cikti']['PASS'] else 'FAIL',
                kapi2_fark_en_buyuk=sert['2_grup'].get('olculen_fark_en_buyuk'), kapi2_konum_fark=sert['2_grup'].get('konum_fark_en_buyuk'),
                kapi2_boyut_fark=(sert['2_grup'].get('boyut_bagimsiz') or {}).get('fark'),
                en_az_cekirdek=dict(oge=en_az[0], piksel=en_az[1]['piksel']) if en_az else None, yildiz_binme_px=yb,
                en_kotu_dE00=olcer['tek_doku'].get('en_kotu_dE00'), en_kotu_kontrast=olcer['kontrast'].get('en_kotu_ortanca'),
                # dilim D2: acik / kapali ogeler (ayardan), "uygulanamaz" olcerler, kapali ogede cekirdek piksel sayimi ve boy esitligi (uretim
                # kaydi), "gercekten yok mu" olcumu
                ogeler=dict(acik=[q for q in OGE_AD if q in acik], kapali=[q for q in OGE_AD if q not in acik]), uygulanamaz=uygulanamaz,
                kapali_oge=veri.get('kapali_oge') or {}, kapali_yok_mu=yok_mu)
    return dict(ozet=ozet, not_='yerel, deneme sembolü; kapı sonucu gerçek katman için kanıt değildir', mm_kaynak=urun['mm_kaynak'],
                oge=oge, kapi=dict(sert=sert, olcer=olcer), bilgi=bilgi, esik={k_: E[k_] for k_ in ('dE00', 'kontrast', 'alfa_fark', 'cekirdek_piksel', 'en_boy',
                                                                                     'sembol_renk', 'grup_yazi', 'grup_konum', 'grup_konum_olculen',
                                                                                     'yildiz_pay', 'duz_yayilim')},
                isik_pay_px=list(ISIK_PAY))


if __name__ == '__main__':
    print(json.dumps(dict(not_='bu dosya tasarim_deneme.py tarafindan cagrilir; tek basina komutu yok'), ensure_ascii=False))
    sys.exit(0)
