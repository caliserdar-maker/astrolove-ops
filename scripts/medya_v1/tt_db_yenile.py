#!/usr/bin/env python3
"""TAURUS_TAURUS Deep Black 11x14 yenileme (Serdar onayi 30 Eyl 2026): kaynak = Canva DAHPcxEOzDc s.76 disa aktarimi
(zemin MAHWsBpuP5A, duz siyah + yildiz). Yalniz 11X14 orani (POD 11x14) degisir; diger 12 boy 4X5/3X4/2X3/A
kaynaklidir, dokunulmaz. Bu betik Drive'a YAZMAZ; yazma workflow'da, yedek + rclone check sonrasinda.

--asama dogrula : export 3300x4200 mi, onaylanan onizlemeyle (s.76 Canva render) ayni sayfa mi, ogeler eski
                  dosyayla birebir mi (altin maske IoU, kayma). FAIL -> cikis 2 (DUR).
--asama test    : POD 11x14 uretimi (pod_print_build.fit, ayni JPEG ayarlari), zemin p50 (medyan plate),
                  EMILY / JAMES siparis testi (pod_uret, tum kapilar). FAIL -> cikis 3.
"""
import argparse, io, json, sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pod'))
Image.MAX_IMAGE_PIXELS = None

CIFT, RENK, BOY = 'TAURUS_TAURUS', 'DEEP_BLACK', '11x14'
ONIZLEME_MAD = 3.0          # export -> 396x504 ile Canva s.76 onizlemesi ortalama mutlak fark
ONIZLEME_P99 = 40.0         # ayni metrik p99 (yanlis sayfa: 163, dogru: 9; kucuk resimden duman testi)
OGE_IOU = 0.90              # altin oge maskesi (eski dosya vs export; yanlis sayfa 0.19, dogru 0.95 duman testi)
KAYMA_PX = 1.0              # oge kaymasi (tam cozunurluk)


def altin(a):
    a = a.astype(np.float32)
    L = a @ np.array([0.299, 0.587, 0.114], np.float32)
    return (L > 70) & (a[..., 0] - a[..., 2] > 40)


def dogrula(a):
    yeni = Image.open(a.export).convert('RGB')
    eski = Image.open(a.eski_orj).convert('RGB')
    r = {'export_px': list(yeni.size), 'eski_px': list(eski.size)}
    on = np.asarray(Image.open(a.onizleme).convert('RGB')).astype(np.float32)
    ku = np.asarray(yeni.resize((on.shape[1], on.shape[0]), Image.LANCZOS)).astype(np.float32)
    d = np.abs(ku - on).mean(2)
    r['onizleme_mad'] = round(float(d.mean()), 2); r['onizleme_p99'] = round(float(np.percentile(d, 99)), 1)
    k = (yeni.width // 2, yeni.height // 2)
    A = np.asarray(eski.resize(k, Image.BILINEAR)); B = np.asarray(yeni.resize(k, Image.BILINEAR))
    ma, mb = altin(A), altin(B)
    r['oge_iou'] = round(float((ma & mb).sum() / max((ma | mb).sum(), 1)), 4)
    La = np.where(ma, A @ [0.299, 0.587, 0.114], 0).astype(np.float32)
    Lb = np.where(mb, B @ [0.299, 0.587, 0.114], 0).astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(La, Lb)
    r['oge_kayma_px'] = [round(dx * 2, 2), round(dy * 2, 2)]
    ort = ma & mb
    r['oge_renk_fark_p50'] = round(float(np.median(np.abs(A[ort].astype(float) - B[ort]).mean(1))), 1) if ort.any() else None
    r['gecti'] = (yeni.size == (3300, 4200) and r['onizleme_mad'] <= ONIZLEME_MAD
                  and r['onizleme_p99'] <= ONIZLEME_P99 and r['oge_iou'] >= OGE_IOU
                  and max(abs(dx), abs(dy)) * 2 <= KAYMA_PX)
    return r


def test(a):
    import siparis_dosyasi as sd
    from pod_print_build import fit
    sizes = json.loads(Path(a.sizes).read_text())
    w, h = sizes[BOY]['w'], sizes[BOY]['h']
    r = {'hedef_px': [w, h]}
    # zincir kontrolu: eski ORIGINAL -> fit -> eski POD'u birebir veriyor mu (bilgi)
    buf = io.BytesIO()
    fit(Image.open(a.eski_orj).convert('RGB'), w, h).save(buf, 'JPEG', quality=95, subsampling=0, dpi=(300, 300), optimize=False)
    z = np.asarray(Image.open(buf).convert('RGB')).astype(int) - np.asarray(Image.open(a.eski_pod).convert('RGB')).astype(int)
    r['zincir_eski_maks_fark'] = int(np.abs(z).max())
    out = Path(a.yeni_pod); out.parent.mkdir(parents=True, exist_ok=True)
    fit(Image.open(a.export).convert('RGB'), w, h).save(out, 'JPEG', quality=95, subsampling=0, dpi=(300, 300), optimize=False)
    with Image.open(out) as c:
        r['yeni_pod_px'] = list(c.size)
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    x = sd.normalize({'cift': CIFT, 'renk': RENK, 'boy': BOY, 'urun': 'pod',
                      'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'It Began With a Kiss in the Rain'})
    plate = P_ed.plate(sd.RENK_ED[RENK], x['oran'], BOY)
    r['zemin_p50'] = {'yeni': sd.zemin_uyumu(out.read_bytes(), plate).get('p50'),
                      'eski': sd.zemin_uyumu(Path(a.eski_pod).read_bytes(), plate).get('p50'),
                      'komsu_SCORPIO_VIRGO': sd.zemin_uyumu(Path(a.komsu_pod).read_bytes(), plate).get('p50')}
    # siparis testi: pod_kaynak yerel dosyayi kullanir (POD_PRINT'e yazilmadan once)
    yer = sd.W / 'pod' / CIFT / RENK; yer.mkdir(parents=True, exist_ok=True)
    (yer / f'{BOY}.jpg').write_bytes(out.read_bytes())
    no, _ = sd.sayfa_no_tablosu()
    x['receipt'] = 'TT_DB_YENILE_TEST'; x['sayfa'] = no[CIFT]; x['hedef_px'] = [w, h]
    is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
    s = sd.pod_uret(x, out.read_bytes(), P_blue, P_ed, is_dir)
    k = s.get('kapilar') or {}
    r['siparis'] = {'durum': s.get('durum'), 'hata': s.get('hata'), 'kapilar': k,
                    'kalan': sorted(g for g, v in k.items() if v is False)}
    r['gecti'] = (r['yeni_pod_px'] == [w, h] and r['zemin_p50']['yeni'] is not None and r['zemin_p50']['yeni'] <= sd.ZEMIN_UYUM_ESIK
                  and s.get('durum') == 'URETILDI' and bool(k) and sd.kapi_sonucu(k))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asama', choices=['dogrula', 'test'], required=True)
    ap.add_argument('--export', required=True)
    ap.add_argument('--eski-orj', required=True)
    ap.add_argument('--eski-pod')
    ap.add_argument('--komsu-pod')
    ap.add_argument('--onizleme')
    ap.add_argument('--sizes')
    ap.add_argument('--yeni-pod')
    a = ap.parse_args()
    r = dogrula(a) if a.asama == 'dogrula' else test(a)
    print(a.asama.upper(), 'PASS' if r['gecti'] else 'FAIL', json.dumps(r, ensure_ascii=False, default=str), flush=True)
    sys.exit(0 if r['gecti'] else (2 if a.asama == 'dogrula' else 3))


if __name__ == '__main__':
    main()
