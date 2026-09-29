#!/usr/bin/env python3
"""PLATE ISIM BANDI TEMIZLIGI (Serdar onayi 29 Eyl 2026): MB, DB, PW, CI x 13 boy = 52 plate.

Bulgu (plate_isim_leke.py): medyan plate'lerin isim bandinda eski burc yazisi uclari kaldi (plate
temizligi yalniz slogan bandini kapsiyordu). Yontem: siparis hattindaki isim_bandi_temizle (bandin
ustu/alti seritlerinin capraz karisimi + bandin kendi murekkepsiz tonu), plate'te yeni oge YOK
(bos koruma maskesi). Bant = isim bandi +- %25 (sembol / tagline bandina tasmadan), sutun = eski
isimlerin uzanimi +- 60 px (2400) -> kenar sus yildizlari bolge disinda kalir.

Sira: 1) PLATES yedegi (PLATES_YEDEK_ISIM_<damga>, 52 dosya) 2) plate basina temizlik + QC
3) QC PASS olan plate PLATES'e yazilir 4) renk basina sahte isimli (EMILY / JAMES) 1 test siparisi.
QC (plate): bantta 0 kalinti (isim_kalinti_kapisi, ham koruma, bos maske) VE leke olcumu 0 bilesen,
bant disi BIREBIR ayni (piksel farki 0). QC (siparis): tum kapilar PASS (plate_slogan, isim_kalinti,
isim_kenar dahil). WP bu iste YOK.
"""
import argparse, json, sys, time
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402
from plate_isim_leke import leke_olc, BOYLAR, KAYNAK_CIFT        # noqa: E402

Image.MAX_IMAGE_PIXELS = None
RENKLER = ('MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE', 'CHAMPAGNE_IVORY')
KISA = {'MIDNIGHT_BLUE': 'MB', 'DEEP_BLACK': 'DB', 'PURE_WHITE': 'PW', 'CHAMPAGNE_IVORY': 'CI'}
TEST = {'cift': 'ARIES_SCORPIO', 'boy': '11x14', 'isim1': 'EMILY', 'isim2': 'JAMES',
        'mesaj': 'Written in the Stars'}


def plate_temizle(yol, olcum):
    im = Image.open(yol)
    bilgi_png = {q: im.info[q] for q in ('dpi', 'icc_profile') if q in im.info}
    A = np.asarray(im.convert('RGB'))
    H, Wd = A.shape[:2]
    bos = np.zeros((H, Wd), bool)
    out, t = sd.isim_bandi_temizle(A.astype(np.float32), bos, olcum, ham=True)
    B = np.clip(np.round(out), 0, 255).astype(np.uint8)
    r0, r1 = t['satir']; c0, c1 = t['sutun']
    dis = np.ones((H, Wd), bool); dis[r0:r1, c0:c1] = False
    dis_fark = int((B[dis] != A[dis]).any(axis=-1).sum()) if B.ndim == 3 else int((B[dis] != A[dis]).sum())
    yeni_im = Image.fromarray(B, 'RGB')
    kap = sd.isim_kalinti_kapisi(yeni_im, bos, olcum, ham=True)
    once = sd.isim_kalinti_kapisi(Image.fromarray(A, 'RGB'), bos, olcum, ham=True)
    return yeni_im, bilgi_png, {'satir': [r0, r1], 'sutun': [c0, c1], 'degisen_px': t['degisen_px'],
                                'bant_disi_farkli_px': dis_fark,
                                'kalinti_once': once.get('kalinti_sayisi'), 'kalinti_sonra': kap.get('kalinti_sayisi'),
                                'kalinti_kapisi': kap.get('gecti'), 'kalinti_hata': kap.get('hata')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kok', required=True, help='rapor klasoru (Drive)')
    ap.add_argument('--damga', required=True)
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    liste = {x['Name'] for x in json.loads(sd.rc('lsjson', sd.PLATES, '--files-only'))}
    adlar = [f'{sd.RENK_ED[r].upper()}{sd.PLATE_EK}_{b}.png' for r in RENKLER for b in BOYLAR]
    eksik = [x for x in adlar if x not in liste]
    d = sd.W / '_plate_isim_temiz'; d.mkdir(parents=True, exist_ok=True)
    rapor = {'damga': a.damga, 'yedek': f'{sd.SIP}/PLATES_YEDEK_ISIM_{a.damga}', 'eksik': eksik,
             'plate': {}, 'test': {}}
    # 1) YEDEK (once, tamami): yedek dogrulanmadan hicbir plate yazilmaz
    yedek = rapor['yedek']
    for ad in adlar:
        if ad in liste:
            sd.rc('copyto', f'{sd.PLATES}/{ad}', f'{yedek}/{ad}', timeout=1800)
    yedek_var = {x['Name'] for x in json.loads(sd.rc('lsjson', yedek, '--files-only'))}
    rapor['yedek_sayisi'] = len(yedek_var)
    if any(ad not in yedek_var for ad in adlar if ad in liste):
        raise SystemExit('YEDEK eksik: hicbir plate yazilmadi')
    print(f'yedek: {len(yedek_var)} plate -> PLATES_YEDEK_ISIM_{a.damga}', flush=True)
    # 2-3) temizlik + QC + yazma
    n, T0, toplam = 0, time.time(), len(RENKLER) * len(BOYLAR)
    for renk in RENKLER:
        ed = sd.RENK_ED[renk]
        for boy in BOYLAR:
            n += 1
            ad = f'{ed.upper()}{sd.PLATE_EK}_{boy}.png'
            r = {'plate': ad}
            if ad not in liste:
                r['durum'] = 'YOK'
            else:
                try:
                    sd.rc('copy', f'{sd.PLATES}/{ad}', str(d), timeout=1800)
                    kaynak = sd.pod_kaynak(KAYNAK_CIFT, renk, boy)
                    o, _duz, _m = P_ed.olc(kaynak, d / ad)
                    im, info, q = plate_temizle(d / ad, o)
                    r.update(q)
                    yeni = d / f'yeni_{ad}'
                    im.save(yeni, 'PNG', **info)
                    r['leke_sonra'] = leke_olc(yeni, o)['bilesen']
                    gecti = (q['kalinti_kapisi'] is True and q['bant_disi_farkli_px'] == 0
                             and r['leke_sonra'] == 0)
                    r['qc'] = 'PASS' if gecti else 'FAIL'
                    if gecti:
                        sd.rc('copyto', str(yeni), f'{sd.PLATES}/{ad}', timeout=1800)
                        (sd.W / 'plates').mkdir(parents=True, exist_ok=True)
                        (sd.W / 'plates' / ad).write_bytes(yeni.read_bytes())   # test siparisi yeni plate'i kullanir
                        r['durum'] = 'YAZILDI'
                    else:
                        r['durum'] = 'YAZILMADI (QC FAIL)'
                    yeni.unlink(missing_ok=True)
                except BaseException as e:                        # noqa: BLE001
                    r['durum'] = 'HATA'
                    r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
                (d / ad).unlink(missing_ok=True)
            rapor['plate'][f'{renk}/{boy}'] = r
            g = time.time() - T0
            print(f"[{n}/{toplam}] {KISA[renk]} {boy}: {r['durum']} kalinti {r.get('kalinti_once')}->"
                  f"{r.get('kalinti_sonra')} leke_sonra={r.get('leke_sonra')} bant_disi={r.get('bant_disi_farkli_px')} "
                  f"{r.get('hata', '')}| gecen {g:.0f}s | kalan ~{g / n * (toplam - n):.0f}s | %{100 * n // toplam}",
                  flush=True)
    # 4) renk basina 1 sahte isimli test siparisi (yeni plate ile)
    no, _ = sd.sayfa_no_tablosu()
    for renk in RENKLER:
        x = sd.normalize({'cift': TEST['cift'], 'renk': renk, 'boy': TEST['boy'], 'urun': 'pod',
                          'isim1': TEST['isim1'], 'isim2': TEST['isim2'], 'mesaj': TEST['mesaj']})
        x['receipt'] = f'PLATE_TEST_{KISA[renk]}'
        x['sayfa'] = no[TEST['cift']]
        yol = sd.pod_kaynak(TEST['cift'], renk, TEST['boy'])
        with Image.open(yol) as im:
            x['hedef_px'] = list(im.size)
        is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
        try:
            s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
            k = s.get('kapilar') or {}
            t = {'durum': s.get('durum'), 'kapilar': k, 'gecti': s.get('durum') == 'URETILDI' and sd.kapi_sonucu(k)
                 and all(k.get(g) is True for g in ('plate_slogan', 'isim_kalinti', 'isim_kenar')),
                 'plate_slogan_payi': (s.get('plate_slogan_kapisi') or {}).get('glif_farkli_payi'),
                 'isim_kalinti': (s.get('isim_kalinti_kapisi') or {}).get('kalinti_sayisi'),
                 'hata': s.get('hata')}
            sd.rc('copy', str(is_dir), f'{a.kok}/{x["receipt"]}', '--include', 'KONTROL/**',
                  '--include', 'ONIZLEME_*', timeout=1800)
        except BaseException as e:                                # noqa: BLE001
            t = {'durum': 'HATA', 'gecti': False, 'hata': f'{type(e).__name__}: {str(e)[:200]}'}
        rapor['test'][renk] = t
        print(f"TEST {KISA[renk]} {TEST['cift']} {TEST['boy']}: {'PASS' if t['gecti'] else 'FAIL'} "
              f"kapilar={t.get('kapilar')} {t.get('hata') or ''}", flush=True)
    pl = rapor['plate'].values()
    rapor['ozet'] = {'yazildi': sum(r['durum'] == 'YAZILDI' for r in pl),
                     'qc_fail': [r['plate'] for r in pl if r.get('qc') == 'FAIL'],
                     'hata': [r['plate'] for r in pl if r['durum'] == 'HATA'],
                     'yok': [r['plate'] for r in pl if r['durum'] == 'YOK'],
                     'test_pass': [KISA[r] for r, t in rapor['test'].items() if t['gecti']]}
    satir = [f'# PLATE ISIM BANDI TEMIZLIGI ({a.damga})', '',
             f"Yedek: PLATES_YEDEK_ISIM_{a.damga} ({rapor['yedek_sayisi']} plate). Ozet: {json.dumps(rapor['ozet'])}",
             '', '| renk | ' + ' | '.join(BOYLAR) + ' |', '|---|' + '---|' * len(BOYLAR)]
    for renk in RENKLER:
        h = []
        for boy in BOYLAR:
            r = rapor['plate'][f'{renk}/{boy}']
            h.append(f"{r.get('qc', r['durum'])} {r.get('kalinti_once')}->{r.get('kalinti_sonra')}")
        satir.append(f'| {KISA[renk]} | ' + ' | '.join(h) + ' |')
    satir += ['', '## Test siparisleri (EMILY / JAMES, ' + f"{TEST['cift']} {TEST['boy']})", '']
    satir += [f"- {KISA[r]}: {'PASS' if t['gecti'] else 'FAIL'} {t.get('kapilar')}" for r, t in rapor['test'].items()]
    (d / 'PLATE_ISIM_TEMIZLIK.md').write_text('\n'.join(satir) + '\n')
    (d / 'PLATE_ISIM_TEMIZLIK.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(d), a.kok, '--include', 'PLATE_ISIM_TEMIZLIK.*')
    print('\n'.join(satir))


if __name__ == '__main__':
    main()
