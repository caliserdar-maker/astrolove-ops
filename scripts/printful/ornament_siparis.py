#!/usr/bin/env python3
"""ORNAMENT SIPARIS HATTI surucusu (Serdar 6 Kas gece "A"; plan claude/AstroLove_ORNAMENT_SIPARIS_PLAN_20261105.md v2; KARARLAR_20261106).
Hat YALNIZ DOSYA uretir: Printful / Etsy / musteriye gonderim yok, Printful API yok, Etsy API yok (Serdar 5 Kas aksam).
Akis (bir siparis kalemi):
  1. Ham GIRDI.json -> siparis_girdi.dogrula. DUR ise dosya uretilmez: DUR.json + RAPOR.json, cikis 3 (DUR_GIRDI) / 4 (DUR_SERDAR).
  2. Onayli uretim zinciri AYNEN, tek cift: ornek78.py (motor RUBY/SAPPHIRE/EMERALD + ORN_DUMP + ornament_sade + ornament_fildisi), YENI_DUZEN=1,
     ORN_SIPARIS_GIRDI = bicimlenmis girdi (motor isim / tarih yolu, T_ref, siparis kapilari). 5 stil uretilir; musteriye secilen stil.
  3. Siniflama: DUR_GIRDI isim_sigmadi (yerlesim o4 kapisi ya da murekkep_r_le_336) / MOTOR_KAPI_FAIL (musteri kusuru degil; musteriye soru yok) /
     COKUS / PASS. Sert kapilar ornek78 'kapi.sert' (motor kapi_sert + SADE_1 teknik kapi + fildisi + printful dosya + dpi); hepsi PASS olmadan dosya yok.
  4. PASS: baski dosyasi (954, 300 dpi), onizleme taslagi (tek karo, etiketsiz; K4 karari bekliyor), KONTROL_1e1, GERCEK_BOY (5 stil),
     RAPOR.json, ELLE_SIPARIS.txt.
Gizlilik (ANA_2 7.3; depo public): bu betik stdout'a musteri metni YAZMAZ; alt sureclerin ciktisi yalniz is klasorundeki log dosyalarina.
Kamuya acik log satirlari OZET_PUBLIC.txt'ye yazilir; is akisi bunu gizlilik_tara.py'den gecirmeden basmaz.
Cikis: 0 PASS, 3 DUR_GIRDI, 4 DUR_SERDAR, 6 MOTOR_KAPI_FAIL, 2 COKUS / yapilandirma."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_d = Path(__file__).resolve().parent
PY = sys.executable
STIL_DOSYA_AD = {'RUBY': 'Ruby', 'SAPPHIRE': 'Sapphire', 'EMERALD': 'Emerald', 'SADE_ALTIN': 'Sade_Altin', 'FILDISI': 'Fildisi'}
ISIM_KAPILARI = ('koyu_yd_murekkep_r_le_336',)                               # musterinin isim / tarih uzunluguna bagli sert kapi (plan 2.1b)
GORSELLI_DUR = ('halka_yakin_330',)                         # bu DUR_SERDAR'larda baski / onizleme / KONTROL_1e1 TASLAK uretilir (Serdar gorselle karar verir)
HALKA_YAKIN = 330                                                             # Serdar 6 Kas "2 evet": murekkep r 330-336 PASS degil DUR_SERDAR (gorsel); 330 tahmin, olculmedi
KONTROL_SATIR = (584, 806)                                                    # KONTROL_1e1: kucuk isaret ustu (SABIT 594) - 10 ile tarih alti (795) + 11


def yukle(ad, dosya):
    s = importlib.util.spec_from_file_location(ad, _d / dosya); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Ozet:
    """kamuya acik ozet satirlari (yalniz kod, kapi adi, sayi). Musteri metni buraya yazilmaz."""

    def __init__(self, yol):
        self.yol = Path(yol); self.t0 = time.time(); self.yol.write_text('')

    def __call__(self, *a):
        with self.yol.open('a') as f:
            f.write(f'[{time.time() - self.t0:7.1f}s] ' + ' '.join(str(x) for x in a) + '\n')


KONTROL_ESKI = 'CANCER_LIBRA_KONTROL_ESKI'                               # uretim78.KONTROL_ESKI ile ayni (yeni duzen kosusunda eski mod CL kontrol kaydi)


def siniflama(R, cift, mo=None):
    """ornek78 OLCUM.json (+ musteri ciftinin motor OLCUM.json) -> (durum, neden, fail_listesi).
    Doner durum: PASS / DUR_GIRDI / DUR_SERDAR / MOTOR_KAPI_FAIL / COKUS."""
    if R.get('kontrol_pass') is False:                                        # CL kontrol cifti FAIL: ornek78 siparis ciftini kosmadan durur (cikis 3)
        return 'MOTOR_KAPI_FAIL', 'ortam_kontrol_CL', ['kontrol_CL']
    r = (R.get('cift') or {}).get(cift)
    if not r:
        return 'COKUS', 'cift_kaydi_yok', []
    mo_hata = r.get('motor_olcum') or {}
    if mo_hata.get('hata') == 'yeni_duzen_kapi':                                   # motor yerlesim o4.kapi (yasak alan / cakisma): isim ya da tarih sigmadi
        return 'DUR_GIRDI', 'isim_sigmadi_yerlesim_o4', ['yerlesim_o4_kapi']
    if r.get('cokus') or 2 in (r.get('cikis_kodlari') or {}).values():
        return 'COKUS', 'alt_surec_cokus', []
    if r.get('eksik'):
        return 'MOTOR_KAPI_FAIL', 'eksik_stil', list(r['eksik'])
    sert = (r.get('kapi') or {}).get('sert')
    if not sert:
        return 'COKUS', 'sert_kapi_yok', []
    fail = sorted(k for k, v in sert.items() if not v)
    if R.get('kontrol_pass') is not True:                                    # CL kontrol cifti (ortam dogrulamasi, onayli 6daab364) gecmeden PASS yok
        return 'MOTOR_KAPI_FAIL', 'ortam_kontrol_CL', fail
    ks = ((R.get('cift') or {}).get(KONTROL_ESKI) or {}).get('kapi', {}).get('sert')
    if not ks or not all(ks.values()):                                       # kontrol kaydinin sert kapilari da sart (3. inceleme bulgu 3; sikilastirma)
        return 'MOTOR_KAPI_FAIL', 'ortam_kontrol_CL_sert', fail
    yo = ((mo or {}).get('yeni_duzen') or {}).get('olcum') or {}
    if not fail:
        rr = yo.get('siparis_murekkep_r')
        if not rr:
            return 'MOTOR_KAPI_FAIL', 'murekkep_r_olcum_yok', []
        if max(rr.values()) > HALKA_YAKIN:                                    # halkaya yakin (Serdar 6 Kas "2 evet"): kimse bakmadan gecmez
            return 'DUR_SERDAR', 'halka_yakin_330', []
        return 'PASS', None, []
    fs = set(fail)
    if fs <= set(ISIM_KAPILARI):                                               # yalniz isim kapisi: musteriye soru (T1)
        return 'DUR_GIRDI', 'isim_sigmadi_murekkep_r', fail
    return 'MOTOR_KAPI_FAIL', 'sert_kapi_fail', fail


def onizleme_yap(png, stil, cikti, o4, ornek78):
    """K4 karari bekliyor: tek karo, etiketsiz; 76 mm kesim dairesi + delik (o4.onizleme, KESIM_R resmi sablon). SADE_ALTIN beyaz zeminde dis cizgiyle."""
    import numpy as np
    from PIL import Image
    im = Image.open(png)
    if im.mode == 'RGBA':
        b = Image.new('RGB', im.size, (255, 255, 255)); b.paste(im, (0, 0), im); im = b
    if stil == 'SADE_ALTIN':
        im = ornek78.sinir_ciz(im)
    o4.onizleme([np.asarray(im.convert('RGB'))], ara=0).save(cikti, quality=95, dpi=(300, 300))


def kontrol_yap(png, cikti):
    """isim satirinin tamami (iki isim + logo + iki kucuk isaret) ve tarih: ust 1:1, alt 3x (NEAREST)."""
    from PIL import Image
    im = Image.open(png)
    if im.mode == 'RGBA':
        b = Image.new('RGB', im.size, (255, 255, 255)); b.paste(im, (0, 0), im); im = b
    k = im.crop((100, KONTROL_SATIR[0], 854, KONTROL_SATIR[1]))
    b3 = k.resize((k.width * 3, k.height * 3), Image.NEAREST)
    o = Image.new('RGB', (b3.width, k.height + 20 + b3.height), 'white')
    o.paste(k, (0, 0)); o.paste(b3, (0, k.height + 20))
    o.save(cikti)


ELLE = """AstroLoveArt ornament siparisi: Printful'a ELLE siparis adimlari (Serdar verir; otomatik gonderim yok)
1. Musteri onizlemesi (K4, Serdar 6 Kas "C" + "dosyalari ben yuklerim"): Serdar baski dosyasini Printful'a KENDISI yukler ve Printful'un urun gorselini (mockup) indirir; onizleme Etsy Messages ile o gorselle gider. _Preview_TASLAK.jpg yalniz ic kontroldur, musteriye gitmez. Musteri onayi gelmeden baski siparisi verilmez.
2. Printful > Orders > New order > manual. Urun: Ceramic Ornament (double-sided, 900), sekil Circle.
3. Baski dosyasi: {dosya} (954 x 954 px, 300 dpi). Iki yuze AYNI dosya (ORNAMENT_KARAR 6).
4. Printful onizlemesinde isim satiri ve tarih tam gorunuyor mu bak; kesim dairesinin disina tasan oge olmamali. Musteriye giden urun gorseli bu ekrandan.
5. Kargo adresi Etsy siparisinden; ad ve adreste duz kesme isareti yaz (Etsy HTML kodu &#039; kopyalanmaz), posta kodu 5 hane (ANA_3 10).
6. Siparis verildikten sonra: Etsy'de "shipped" ve takip numarasi Printful kargo e-postasindan; Complete order (astrolove-siparis).
"""


def main():
    ap = argparse.ArgumentParser()
    for k in ('girdi', 'kaynak', 'motor', 'zemin', 'son', 'onayli', 'font', 'cikti'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--is', dest='is_klasor', required=True, help='is klasoru (musteri verili ara dosyalar; dala / artifact\'a girmez)')
    a = ap.parse_args()
    O, W = Path(a.cikti), Path(a.is_klasor)
    O.mkdir(parents=True, exist_ok=True); W.mkdir(parents=True, exist_ok=True)
    oz = Ozet(O / 'OZET_PUBLIC.txt')
    bek = os.environ.get('ORN_BEKLENEN_RAQM')
    if bek not in ('0', '1'):
        oz('YAPILANDIRMA ORN_BEKLENEN_RAQM yok'); return 2
    sg = yukle('siparis_girdi', 'siparis_girdi.py')
    RAPOR = dict(hat='ornament_siparis (plan v2)', zaman=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 pinler={k: os.environ.get(k) for k in ('MOTOR_COMMIT', 'TEK_DOKU_COMMIT', 'ACIK_COMMIT', 'ONAY_COMMIT', 'GITHUB_SHA')},
                 beklenen_raqm=bek, gece_varsayimlari='K1 RAQM (onayli dosyalarla ayni, Serdar 6 Kas), K7 istisna ciftleri DUR, K8 1c (isim-tarih 25-45), r 330-336 DUR_SERDAR, K3 / K9 DUR_SERDAR (KARARLAR_20261106)')
    # 1. girdi
    try:
        ham = json.loads(Path(a.girdi).read_text(encoding='utf-8'))
        G = sg.dogrula(ham)
    except sg.Dur as d:
        RAPOR.update(durum=d.kod, neden=d.neden, alan=d.alan)
        (O / 'DUR.json').write_text(json.dumps(dict(durum=d.kod, neden=d.neden, alan=d.alan), indent=1))
        (O / 'RAPOR.json').write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False))
        oz('GIRDI', d.kod, d.neden, d.alan); return 3 if d.kod == 'DUR_GIRDI' else 4
    except Exception:                                                          # noqa: BLE001  (icerik yazilmaz)
        RAPOR.update(durum='DUR_SERDAR', neden='girdi_bicim', alan='girdi')
        (O / 'RAPOR.json').write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False)); oz('GIRDI DUR_SERDAR girdi_bicim'); return 4
    cift, stil = G['cift'], G['stil']
    NORMAL = W / 'NORMAL.json'
    NORMAL.write_text(json.dumps(G, ensure_ascii=False, indent=1), encoding='utf-8')
    RAPOR.update(cift=cift, stil=stil, girdi_sha256=sha(NORMAL))
    oz('GIRDI PASS')                                                          # cift / stil adi yazilmaz (Ruby, Leo gibi isimlerle gizlilik yanlis alarmi)
    # 2. onayli zincir (tek cift)
    o_png, rp = W / 'png', W / 'rapor'
    env = dict(os.environ, YENI_DUZEN='1', ORN_SIPARIS_GIRDI=str(NORMAL), ORNEK78_CIFTLER='CANCER_LIBRA,' + cift, GERCEK_BOY_CIFTLER=cift,
               ORNEK78_DRIVE_EK=str(W / 'drive_ek'),
               ORNEK78_KENAR_ZORUNLU=cift if 'AQUARIUS' in cift.split('_') else '')   # CL ilk = kontrol cifti (eski mod, onayli kiyas); Kova kenar kapisi uretimle ayni
    env.pop('ORNEK78_PARCA', None)
    t0 = time.time()
    with open(W / 'log_ornek78.txt', 'w') as lf:                              # alt surec ciktisi YALNIZ dosyaya (kamuya acik loga degil)
        k = subprocess.run([PY, '-I', str(_d / 'ornek78.py'), '--kaynak', a.kaynak, '--motor', a.motor, '--zemin', a.zemin, '--son', a.son,
                            '--onayli', a.onayli, '--cikti', str(o_png), '--rapor', str(rp), '--font', a.font],
                           env=env, stdout=lf, stderr=subprocess.STDOUT).returncode
    RAPOR['ornek78'] = dict(cikis=k, sure_sn=round(time.time() - t0, 1))
    oz('ZINCIR ornek78 cikis', k, 'sure_sn', RAPOR['ornek78']['sure_sn'])
    R = json.loads((rp / 'OLCUM.json').read_text()) if (rp / 'OLCUM.json').exists() else {}
    gbk = None
    gbf = sorted(rp.glob(f'GERCEK_BOY_{cift}_*_300dpi.png'))
    if gbf:                                                                    # gercek boy olcek kontrolu (ornament-78-uretim.yml:323 ile ayni betik)
        with open(W / 'log_gercek_boy.txt', 'w') as lf:
            gbk = subprocess.run([PY, '-I', str(_d / 'gercek_boy_kontrol.py')] + [str(x) for x in gbf] + ['--json', str(W / 'GERCEK_BOY_KONTROL.json')],
                                 stdout=lf, stderr=subprocess.STDOUT).returncode
    mo_c = W / 'png' / '_is' / cift / 'motor' / 'OLCUM.json'
    mo = json.loads(mo_c.read_text()) if mo_c.exists() else {}
    durum, neden, fail = siniflama(R, cift, mo)
    gorselli = durum == 'DUR_SERDAR' and neden in GORSELLI_DUR                 # Serdar'a gorselle giden DUR (halka yakin): ciktilar TASLAK uretilir
    if (durum == 'PASS' or gorselli) and gbk != 0:                             # sert (siparis kipinde sikilastirma): gercek boy dosyasi yoksa ya da FAIL ise PASS / gorselli DUR yok
        durum, neden, fail = 'MOTOR_KAPI_FAIL', 'gercek_boy_kontrol', ['gercek_boy_kontrol']
    RAPOR['gercek_boy_kontrol_cikis'] = gbk
    rc = (R.get('cift') or {}).get(cift) or {}
    RAPOR.update(durum=durum, neden=neden, sert_fail=fail, sert=(rc.get('kapi') or {}).get('sert'), bilgi=(rc.get('kapi') or {}).get('bilgi'),
                 siparis_motor=mo.get('siparis'), yeni_duzen_olcum=((mo.get('yeni_duzen') or {}).get('olcum')),
                 yeni_duzen_kapi=((mo.get('yeni_duzen') or {}).get('kapi')), kucultme=rc.get('kucultme'), koyu=rc.get('koyu'), sade=rc.get('sade'),
                 yerlesim_cakisma=(mo.get('cakisma') or [])[:8], yerlesim_yasak=mo.get('yasak'))
    RAPOR['kontrol_pass'] = R.get('kontrol_pass'); RAPOR['kontrol'] = R.get('kontrol')
    oz('SINIF', durum, neden or '', 'fail', ','.join(fail), 'kontrol_CL', R.get('kontrol_pass'))
    if durum != 'PASS' and not (durum == 'DUR_SERDAR' and neden in GORSELLI_DUR):
        (O / 'DUR.json').write_text(json.dumps(dict(durum=durum, neden=neden, fail=fail), indent=1))
        (O / 'RAPOR.json').write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False, default=str))
        return {'DUR_GIRDI': 3, 'DUR_SERDAR': 4, 'MOTOR_KAPI_FAIL': 6}.get(durum, 2)
    # 3. PASS ciktilari
    o4 = yukle('o4', 'ornament_ornek4.py')
    ornek78 = yukle('ornek78_mod', 'ornek78.py')
    b1, b2 = (b.capitalize() for b in cift.split('_'))
    taban = f'AstroLoveArt_{b1}_{b2}_{STIL_DOSYA_AD[stil]}_Ornament' + ('' if durum == 'PASS' else '_SERDAR_ONAYI_BEKLER')
    kaynak_png = o_png / f'{cift}_{stil}_954.png'
    baski = O / f'{taban}.png'
    shutil.copyfile(kaynak_png, baski)
    onizleme_yap(baski, stil, O / f'{taban}_Preview_TASLAK.jpg', o4, ornek78)
    ek = '' if durum == 'PASS' else '_SERDAR_ONAYI_BEKLER'
    kontrol_yap(baski, O / f'KONTROL_1e1{ek}.png')
    for gb in rp.glob('GERCEK_BOY_*_300dpi.png'):
        shutil.copyfile(gb, O / f'GERCEK_BOY_5STIL_300dpi{ek}.png')
    u78 = yukle('u78', 'uretim78.py')
    RAPOR['cikti'] = dict(baski=baski.name, baski_sha256=sha(baski), baski_piksel_sha=u78.piksel_sha(baski),
                          printful=(rc.get('printful_dosya') or {}).get(stil), onizleme=f'{taban}_Preview_TASLAK.jpg',
                          dosya_adi_not='stil adi ic kod (Sade_Altin, Fildisi); ilandaki Ingilizce stil adiyla eslenmesi dogrulanmadi',
                          onizleme_not='ic kontrol: tek karo, 76 mm kesim + delik (o4.onizleme); musteri onizlemesi Printful urun gorseli, Serdar yukler (K4, Serdar 6 Kas)',
                          diger_stiller_piksel_sha={s: u78.piksel_sha(o_png / f'{cift}_{s}_954.png') for s in STIL_DOSYA_AD if (o_png / f'{cift}_{s}_954.png').exists()})
    if durum != 'PASS':                                                        # gorselli DUR_SERDAR: ELLE_SIPARIS YOK; Serdar onayindan sonra Merkez ayrica isler
        (O / 'DUR.json').write_text(json.dumps(dict(durum=durum, neden=neden, fail=fail, gorsel_var=True), indent=1))   # dosya adi yok: burc / stil adi gizlilik taramasinda yanlis alarm (5. inceleme)
        (O / 'RAPOR.json').write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False, default=str))
        oz('DUR_SERDAR gorsel yazildi')
        return 4
    (O / 'ELLE_SIPARIS.txt').write_text(ELLE.format(dosya=baski.name))
    (O / 'RAPOR.json').write_text(json.dumps(RAPOR, indent=1, ensure_ascii=False, default=str))
    oz('PASS cikti yazildi')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001  (traceback musteri metni icerebilir: yalniz dosyaya)
        import traceback
        p = Path(os.environ.get('ORN_SIPARIS_IS', '/tmp')) / 'traceback_siparis.txt'
        try:
            p.write_text(traceback.format_exc())
        except Exception:                                                      # noqa: BLE001
            pass
        print('COKUS ornament_siparis (ayrinti is klasorunde)', flush=True)
        sys.exit(2)
