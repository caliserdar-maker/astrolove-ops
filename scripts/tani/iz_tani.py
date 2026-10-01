"""SALT OKUR tani (1 Eki 2026, siparis 4188621967): eski_metin_izi kapisi kucuk boylarda (16x20 / 11x14 / A2) neden
FAIL, 24x36 neden PASS? Kapi ic ayrintisi: R (eski glif, yeni maske disi) piksellerinde cikti sapmasinin dagilimi,
parlak (yeni yazi / sizinti) ve silik (hayalet) katkilarinin ayrimi. Test isimleri (EMILY / JAMES), gercek mesaj bandi.
Etsy / musteri / PLATES yazimi YOK."""
import io, json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, 'scripts/medya_v1')
import siparis_dosyasi as sd                                      # noqa: E402
import cv2                                                        # noqa: E402

Image.MAX_IMAGE_PIXELS = None
CIK = Path(os.environ.get('CIK', 'iz_tani')).resolve(); CIK.mkdir(parents=True, exist_ok=True)
RENK = os.environ.get('RENK', 'DEEP_BLACK')
ORANLAR = os.environ.get('ORANLAR', '11x14,2x3').split(',')
SONUC = {}


def ayrinti(cikti, kaynak, tag_bant, tag_x, yeni_maske, ad):
    from pilot6 import LUMA
    eu = sd._mod('edisyon_uret')
    sd.olcek_kur(2400)

    def n24(im):
        im = im if isinstance(im, Image.Image) else Image.open(io.BytesIO(im) if isinstance(im, (bytes, bytearray)) else im)
        im = im.convert('RGB')
        return np.asarray(im.resize((2400, round(im.height * 2400 / im.width)), Image.LANCZOS)).astype(np.float32) @ LUMA
    Ls, Lo = n24(kaynak), n24(cikti)
    h = min(Ls.shape[0], Lo.shape[0])
    y0, y1 = max(int(tag_bant[0]) - 12, 0), min(int(tag_bant[1]) + 12, h)
    x0, x1 = max(int(tag_x[0]) - 40, 0), min(int(tag_x[1]) + 40, 2400)
    G = eu.edisyon_maske(Ls, float(np.median(Ls)) > 128)[y0:y1, x0:x1]
    ym = np.asarray(yeni_maske).astype(np.uint8)
    r = {'yeni_shape': list(ym.shape), 'cikti_px': list(cikti.size)}
    ym = cv2.resize(ym, (2400, round(ym.shape[0] * 2400 / ym.shape[1])), interpolation=cv2.INTER_NEAREST) > 0
    N0 = np.zeros_like(G); hh = min(ym.shape[0], y1) - y0
    if hh > 0:
        N0[:hh] = ym[y0:y0 + hh, x0:x1]
    N = cv2.dilate(N0.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    No = eu.edisyon_maske(Lo, float(np.median(Lo)) > 128)[y0:y1, x0:x1]      # ciktinin KENDI murekkebi

    def sap(L):
        return L - cv2.medianBlur(np.clip(L, 0, 255).astype(np.uint8), 21).astype(np.float32)
    ds, do = sap(Ls[y0:y1, x0:x1]), sap(Lo[y0:y1, x0:x1])
    R = G & ~N
    B = ~cv2.dilate(G.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~N
    yon = 1.0 if float(np.median(ds[G])) >= 0 else -1.0
    v = yon * do[R]
    parlak = v > 20
    No_d = cv2.dilate(No.astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    R2 = G & ~(N | No_d)
    r.update({'bant': [y0, y1], 'x': [x0, x1], 'R_px': int(R.sum()), 'fazla': round(float(v.mean() - (yon * do[B]).mean()), 2),
              'parlak_px': int(parlak.sum()), 'parlak_katki': round(float(v[parlak].sum() / max(R.sum(), 1)), 2),
              'silik_ort': round(float(v[~parlak].mean()), 3) if (~parlak).any() else None,
              'parlak_yeni_murekkep_icinde': int((R & No & (yon * do > 20)).sum()),
              'yeni_maske_disi_murekkep_px': int((No & ~N).sum()),
              'R_ciktinin_murekkebi_haric_px': int(R2.sum()),
              'fazla_cikti_murekkebi_haric': round(float((yon * do[R2]).mean() - (yon * do[B & ~No_d]).mean()), 2) if R2.sum() > 200 else None})
    if parlak.any():
        ys, xs = np.nonzero(R & (yon * do > 20))
        r['parlak_kutu'] = [int(ys.min() + y0), int(ys.max() + y0), int(xs.min() + x0), int(xs.max() + x0)]
    # gorsel: ust cikti x8 (zemin ustu), orta R kirmizi / N yesil / cikti murekkebi mavi, alt kaynak
    def g8(L):
        return np.clip(np.abs(L) * 8 if yon > 0 else (255 - L) * 8, 0, 255).astype(np.uint8)
    a = np.dstack([g8(Lo[y0:y1, x0:x1])] * 3)
    o = np.zeros(a.shape, np.uint8); o[..., 1][N0] = 160; o[..., 2][No & ~N] = 255; o[..., 0][R] = 120; o[..., 0][R & (yon * do > 20)] = 255
    s = np.dstack([np.clip(Ls[y0:y1, x0:x1] if yon > 0 else 255 - Ls[y0:y1, x0:x1], 0, 255).astype(np.uint8)] * 3)
    Image.fromarray(np.concatenate([a, o, s], 0)).save(CIK / f'IZ_TANI_{ad}.png')
    return r


orig = sd._iz_kapisi


def sar(baski, kb, bi, ek):
    res = orig(baski, kb, bi, ek)
    o = bi.get('olcum') or {}
    try:
        d = ayrinti(baski, kb, o['tag_bant'], o.get('tag_x') or [300, 2100], ek.get('yeni'), f'{RENK}_{bi.get("oran")}_{baski.size[0]}')
    except Exception as e:                                        # noqa: BLE001
        d = {'hata': f'{type(e).__name__}: {e}'}
    d['kapi'] = {q: res.get(q) for q in ('fazla', 'iz_ort', 'taban_ort', 'eski_glif_px', 'gecti')}
    d['tag_bant'] = o.get('tag_bant'); d['tag_x'] = o.get('tag_x')
    print('IZ_TANI', baski.size, json.dumps(d), flush=True)
    SONUC[str(baski.size)] = d
    (CIK / f'IZ_TANI_{RENK}_{baski.size[0]}.json').write_text(json.dumps(d, indent=1))
    return res


sd._iz_kapisi = sar
sd.kisisel_hazirla()
no, _ = sd.sayfa_no_tablosu()
sip = {'cift': 'CANCER_LEO', 'isim1': 'EMILY', 'isim2': 'JAMES', 'mesaj': 'A King and his Crab', 'sayfa': no['CANCER_LEO']}
klas = CIK / RENK; klas.mkdir(exist_ok=True)
for oran in ORANLAR:
    renk, oran_, kayit, _ = sd._dijital_is((RENK, oran, sip, klas, CIK))
    print('KAYIT', oran, json.dumps({q: kayit.get(q) for q in ('durum', 'hata', 'kapilar', 'eski_metin_izi_kapisi')}, default=str), flush=True)
    for j in klas.glob('*.jpg'):
        j.unlink()
