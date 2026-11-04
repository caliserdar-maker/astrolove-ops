#!/usr/bin/env python3
"""Kaynak leke kapisi testi (Serdar 4 Kas "A" + O1; KALITE 3: bilinen PASS + bilinen FAIL). Motorun yolu birebir (ornament_motor.py):
  kirp (pad 2) -> (ana ise genislik > 1600 ise 1600'e olcek) -> o5.delik_kapat -> [o5.kenar_onar] -> o5.leke_ic_kaynak (olcum=False, pay 24)
  kapi sayisi = ic & alfa < 0.9. Pay, esik, olcum bolgesi DEGISMEZ (KALITE 4).
Mod KAPALI (kenar_onar kapali, delik_kapat acik; yalniz test parametresi):
  bilinen PASS: --pass kaynaklari (CANCER_LIBRA sembol kaynaklari) -> 0 piksel.
  bilinen FAIL (i): her kaynakta ic yapay leke (en kalin murekkep noktasi, yaricap r, alfa 0.5) -> disk icinde sayilan > 0.
  bilinen FAIL (ii) kenar satiri: kenara degen murekkepte (dort kenar) merkez kenardan 1 px disk; sayim yalniz disk ve kenardan ilk 3 px (y 0-2).
     --kenar_zorunlu kaynaklarinda (gercek Kova boyutu) > 0 olmali; digerlerinde 0 FAIL degildir, "kenar bandi kor (ice px)" bilgi.
  Yapay leke delik_kapat SONRASINA (kapinin olctugu goruntuye) konur; delik_kapat ONCESINE konan ic leke onarilir (bilgi: ham_ic_onarildi).
  Sayim disk maskesi icinde yapilir (kaynagin kendi lekesi sayilmaz). Leke konacak yer yoksa test FAIL (varsayilan deger yok).
Mod ACIK (kenar_onar acik): kapi sonucu bilgi; olculenler n0, degisen piksel, en buyuk alfa farki, degisen piksellerin kenara uzakligi,
  yapay kenar lekesinin kenar_onar ile gizlenip gizlenmedigi. Yeni esik yok, "kabul" yok.
--kenar_zorunlu kaynaginda (gercek Kova) onarim kapaliyken kapi sayisi > 0 olmali: mod_kapali.onarimsiz_kapi_iddia (bilinen FAIL iddiasi;
  0 ise test FAIL). Diger kaynaklarin onarimsiz sayisi bilgi (gercek_kova_onarimsiz_leke_px; AQUARIUS_PISCES_ana 0 FAIL sayilmaz).
Cikis: 0 test_gecti, 1 test FAIL, 2 cokus.
Kullanim: kova_kapi_testi.py --pass cancer.png libra.png [--pass_ana CANCER_LIBRA_ana.png] [--kaynak aquarius.png] [--ana X_ana.png]
  [--kenar_zorunlu aquarius] --cikti DIR"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

_d = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('altin', _d / 'ornament_altin.py'); al = importlib.util.module_from_spec(_s); _s.loader.exec_module(al)
o5, o1 = al.o5, al.o1


def hazirla(yol, ana):
    g = np.asarray(Image.open(yol).convert('RGBA'), np.float32); g[..., 3] /= 255.0
    g = o1.kirp(g, g[..., 3], pad=2)
    if ana and g.shape[1] > 1600:
        r_, a_ = o1.rgba_olcek(g, 1600 / g.shape[1]); g = np.dstack([r_, a_])
    return g


def say(g, disk=None):
    ic, t = o5.leke_ic_kaynak(g[..., 3])
    m = ic & (g[..., 3] < 0.9)
    return int(m.sum()) if disk is None else int((m & disk).sum()), t


def disk_m(shape, cx, cy, r):
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def leke_koy(g, d):
    g2 = g.copy(); g2[..., 3][d] = 0.5
    return g2


def yer_ic(A, r):
    dt = cv2.distanceTransform(np.pad((A > 0.9).astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]   # tuval siniri arka plan (tam dolu kaynakta kose secilmesin)
    if dt.max() < r + 2:
        return None
    cy, cx = np.unravel_index(int(dt.argmax()), dt.shape)
    return int(cx), int(cy)


def yer_kenar(A, r):
    """kenara degen murekkep (kapi esigi alfa > 0.5; kenar satiri kenar yumusatmasi olabilir): dort kenar (ust, alt, sol, sag) sirayla;
    kenardan itibaren 2r+3 piksel murekkep olan en uzun araligin ortasi. Merkez kenardan 1 px icerde. Doner (cx, cy, kenar) ya da None."""
    H, W = A.shape
    for ad in ('ust', 'alt', 'sol', 'sag'):
        if ad == 'ust':
            dolu = (A[:2 * r + 3] > 0.5).all(0)
        elif ad == 'alt':
            dolu = (A[H - 2 * r - 3:] > 0.5).all(0)
        elif ad == 'sol':
            dolu = (A[:, :2 * r + 3] > 0.5).all(1)
        else:
            dolu = (A[:, W - 2 * r - 3:] > 0.5).all(1)
        idx = np.nonzero(dolu)[0]
        if not len(idx):
            continue
        br = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1); en = max(br, key=len)
        if len(en) < 2 * r + 1:
            continue
        m = int(en[len(en) // 2])
        return {'ust': (m, 1), 'alt': (m, H - 2), 'sol': (1, m), 'sag': (W - 2, m)}[ad] + (ad,)
    return None


def kenar_bant(shape, kenar):
    """sayim bolgesi: gorev tanimi 'y 0-2' = kenardan ilk 3 piksel (ust/alt satir, sol/sag sutun)."""
    b = np.zeros(shape, bool)
    if kenar == 'ust':
        b[:3] = True
    elif kenar == 'alt':
        b[-3:] = True
    elif kenar == 'sol':
        b[:, :3] = True
    else:
        b[:, -3:] = True
    return b


def kaynak_test(yol, ana, kenar_zorunlu, bilinen_pass):
    ad = Path(yol).stem
    g0 = hazirla(yol, ana)
    gd, _ = o5.delik_kapat(g0)
    A = gd[..., 3]; H, W = A.shape
    r = max(6, int(round(W / 600)))
    n_k, tanim = say(gd)
    R = dict(kaynak=Path(yol).name, tur='ana' if ana else 'kucuk', boyut=[H, W], olcum=tanim, yaricap=r,
             kenara_degen_murekkep=dict(ust=bool((A[0] > 0.5).any()), alt=bool((A[-1] > 0.5).any())))
    K = dict(kapi_sayisi=n_k)
    if bilinen_pass:
        K['bilinen_pass'] = dict(beklenen=0, olculen=n_k, gecti=bool(n_k == 0))
    else:
        K['gercek_kaynak_onarimsiz_leke_px_bilgi'] = n_k
    # (i) ic yapay leke
    y = yer_ic(A, r)
    if y is None:
        K['bilinen_fail_ic'] = dict(gecti=False, not_='leke konacak yer yok (FAIL)')
    else:
        d = disk_m(A.shape, y[0], y[1], r); n_i, _ = say(leke_koy(gd, d), d)
        K['bilinen_fail_ic'] = dict(merkez=list(y), yaricap=r, disk_px=int(d.sum()), disk_icinde_sayilan=n_i, gecti=bool(n_i > 0))
        # bilgi: ayni leke delik_kapat ONCESINE konursa onarilir mi
        g0b = g0.copy(); d0 = disk_m(g0.shape, y[0], y[1], r); g0b[..., 3][d0] = 0.5
        gdb, _ = o5.delik_kapat(g0b); n_h, _ = say(gdb, d0)
        K['bilgi_ham_ic_leke_delik_kapat_sonrasi'] = n_h
    # (ii) kenar satiri
    yk = yer_kenar(A, r)
    if yk is None:
        K['bilinen_fail_kenar'] = dict(gecti=not kenar_zorunlu, not_='kenara degen dolu murekkep yok, leke konamadi' +
                                       (' (zorunlu kaynak: FAIL)' if kenar_zorunlu else ' (bilgi; zorunlu degil)'))
    else:
        d = disk_m(A.shape, yk[0], yk[1], r); bnt = d & kenar_bant(A.shape, yk[2]); n_e, _ = say(leke_koy(gd, d), bnt)
        K['bilinen_fail_kenar'] = dict(merkez=[yk[0], yk[1]], kenar=yk[2], yaricap=r, disk_px=int(d.sum()), sayim_bolgesi='disk ve kenardan ilk 3 px',
                                       bolge_px=int(bnt.sum()), disk_icinde_sayilan=n_e,
                                       zorunlu=bool(kenar_zorunlu), gecti=bool(n_e > 0) if kenar_zorunlu else True,
                                       not_=None if (kenar_zorunlu or n_e > 0) else f'kenar bandi kor (ice {tanim["ice_px"]} px); bilgi, FAIL degil')
    if kenar_zorunlu:                                                        # O1 (Serdar 4 Kas, sikilastirma): onarim KAPALIYKEN gercek Kova bilinen FAIL
        K['onarimsiz_kapi_iddia'] = dict(iddia='onarim kapaliyken kapi sayisi > 0 (bilinen FAIL)', olculen=n_k, gecti=bool(n_k > 0))
    R['mod_kapali'] = K
    # Mod ACIK
    g2, k_ = o5.kenar_onar(gd)
    n_a, _ = say(g2)
    Ac = dict(kenar_onar=k_, kapi_sayisi_onarim_sonrasi_bilgi=n_a)
    if yk is not None:
        d = disk_m(A.shape, yk[0], yk[1], r); bnt = d & kenar_bant(A.shape, yk[2]); gl = leke_koy(gd, d)
        gl2, kl = o5.kenar_onar(gl); n_l, _ = say(gl2, bnt)
        Ac['yapay_kenar_lekesi'] = dict(onarim_oncesi_bolgede=K['bilinen_fail_kenar']['disk_icinde_sayilan'], onarim_sonrasi_bolgede=n_l,
                                        gizlendi=bool(K['bilinen_fail_kenar']['disk_icinde_sayilan'] > 0 and n_l == 0),
                                        disk_icinde_alfa_farki_en_buyuk=round(float(np.abs(gl2[..., 3] - gl[..., 3])[d].max()), 4),
                                        not_='kenar_onar sayi 0 olana kadar onarir: gizlendi yapisi geregi True beklenir (zayif; bilgi)')
    R['mod_acik_bilgi'] = Ac
    gec = [v['gecti'] for k, v in K.items() if isinstance(v, dict) and 'gecti' in v]
    R['gecti'] = bool(all(gec))
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pass', dest='pas', nargs='+', required=True); ap.add_argument('--kaynak', nargs='*', default=[])
    ap.add_argument('--ana', nargs='*', default=[]); ap.add_argument('--pass_ana', nargs='*', default=[]); ap.add_argument('--kenar_zorunlu', nargs='*', default=[])
    ap.add_argument('--cikti', required=True)
    a = ap.parse_args(); O = Path(a.cikti); O.mkdir(parents=True, exist_ok=True)
    zor = {z.lower() for z in a.kenar_zorunlu}
    T = []
    for y in a.pas:
        T.append(kaynak_test(y, False, Path(y).stem.split('_')[0].lower() in zor, True))
    for y in a.kaynak:
        T.append(kaynak_test(y, False, Path(y).stem.split('_')[0].lower() in zor, False))
    for y in a.pass_ana:                                                     # ana yolu (1600 olcek) bilinen PASS
        T.append(kaynak_test(y, True, False, True))
    for y in a.ana:
        T.append(kaynak_test(y, True, False, False))
    eksik = [z for z in zor if not any(t['kaynak'].lower().startswith(z) for t in T)]
    R = dict(yol='kirp pad 2 -> (ana 1600) -> delik_kapat -> [kenar_onar] -> leke_ic_kaynak(olcum=False, pay 24)', kaynaklar=T,
             kenar_zorunlu=sorted(zor), kenar_zorunlu_eksik=eksik)
    R['gercek_kova_onarimsiz_leke_px'] = {t['kaynak']: t['mod_kapali']['kapi_sayisi'] for t in T if t['kaynak'].lower().startswith('aquarius')}
    R['test_gecti'] = bool(all(t['gecti'] for t in T) and not eksik)
    (O / 'KOVA_KAPI_TESTI.json').write_text(json.dumps(R, indent=1, ensure_ascii=False))
    for t in T:
        K = t['mod_kapali']
        print(t['kaynak'], t['boyut'], 'gecti', t['gecti'], '| kapi', K['kapi_sayisi'],
              '| ic', K['bilinen_fail_ic'].get('disk_icinde_sayilan'), '| kenar', K['bilinen_fail_kenar'].get('disk_icinde_sayilan'),
              K['bilinen_fail_kenar'].get('not_') or '', '| acik n0', t['mod_acik_bilgi']['kenar_onar']['n0'],
              'degisen', t['mod_acik_bilgi']['kenar_onar']['degisen_piksel'], 'gizlendi', t['mod_acik_bilgi'].get('yapay_kenar_lekesi', {}).get('gizlendi'),
              flush=True)
    print('TEST', 'PASS' if R['test_gecti'] else 'FAIL', '| eksik zorunlu', eksik, flush=True)
    return 0 if R['test_gecti'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
