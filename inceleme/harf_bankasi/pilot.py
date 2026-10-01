"""MB 11x14 pilotu: SERDAR / LENA bankadan vs onayli plaka_ss; piksel farki, olcek kapisi, sure."""
import json, sys, time
import numpy as np
from PIL import Image
sys.path.insert(0, '.')
from harf_bankasi import HarfBankasi, plaka_banka, sd, pilot12, SS
from kisisel_pilot import cap_icin_boyut
from pilot6 import ISIM_W, ISIM_FONT
sd._mod = lambda ad, _m=sd._mod: sys.modules.get(ad) or _m(ad)
K = 3307 / 2400.0                                                 # MB 11x14 hedef / 2400
PROF = np.linspace(np.array((231, 167, 48), np.float32), np.array((150, 100, 30), np.float32), 50)
fp = pilot12.FONT_DIR / ISIM_FONT
isimler = ('SERDAR', 'LENA')
tam = {m: cap_icin_boyut(fp, pilot12.govde(m, fp, ISIM_W), 85, ISIM_W) for m in isimler}
s4 = {m: max(int(round(tam[m] * K * SS)), 4 * SS) for m in isimler}
R = {'k': round(K, 4), 'tam_2400': tam, 's4': s4}
t = time.perf_counter(); bankalar = {v: HarfBankasi(v) for v in set(s4.values())}; R['banka_uretim_sn'] = round(time.perf_counter() - t, 3)
pl = {}
for m in isimler:
    t = time.perf_counter(); a = sd.plaka_ss(m, PROF, 0, 1.0, tam=tam[m] * K)[0]; ta = time.perf_counter() - t
    t = time.perf_counter(); b = plaka_banka(bankalar[s4[m]], m, PROF); tb = time.perf_counter() - t
    A, B = np.asarray(a).astype(int), np.asarray(b).astype(int)
    ayni_boy = A.shape == B.shape
    d = np.abs(A - B) if ayni_boy else None
    R[m] = {'mevcut_sn': round(ta, 3), 'banka_sn': round(tb, 3), 'boyut': [list(A.shape[:2]), list(B.shape[:2])],
            'piksel_fark_max': int(d.max()) if ayni_boy else None, 'farkli_piksel': int((d.max(axis=2) > 0).sum()) if ayni_boy else None,
            'bayt_ayni': bool(ayni_boy and not d.any())}
    pl[m] = (a, b)
# olcek kapisi: iki yontemle MB 11x14 isim satiri (ayni yerlesim), bant (2244, 2356)
o = sd.plaka_ss('O', PROF, 0, 1.0, tam=90 * K)[0]           # sonsuz yerine (iki yontemde ayni)
def satir(sol, sag):
    W, H = 3307, int(round(3048 * K))
    t = Image.new('RGBA', (W, H), (0, 6, 32, 255))
    x = 330 * K
    for p in (sol, o, sag):
        t.alpha_composite(p, (int(round(x)), int(round(2290 * K - p.height / 2)))); x += p.width + 150 * K
    return t.convert('RGB')
mevcut = satir(pl['SERDAR'][0], pl['LENA'][0]); banka = satir(pl['SERDAR'][1], pl['LENA'][1])
sd.olcek_kur(3307)
sd.olcek_kur(2400)
p2400 = Image.fromarray(np.asarray(mevcut.resize((2400, round(mevcut.height / K)), Image.BOX)))
g_m = sd.olcek_kapisi_baski(mevcut, p2400, (2244, 2356), esit=True)
g_b = sd.olcek_kapisi_baski(banka, p2400, (2244, 2356), esit=True)
from siparis_dosyasi import satir_olc_alt
sd.olcek_kur(3307); gm = satir_olc_alt(mevcut, (2244, 2356), K); gb = satir_olc_alt(banka, (2244, 2356), K); sd.olcek_kur(2400)
R['kapi_banka_vs_mevcut'] = sd.olcek_kapisi(gb, gm, 1.0)
R['satir_piksel_fark_max'] = int(np.abs(np.asarray(mevcut).astype(int) - np.asarray(banka).astype(int)).max())
print(json.dumps({k: v for k, v in R.items() if k != 'kapi_banka_vs_mevcut'}, ensure_ascii=False))
kb = R['kapi_banka_vs_mevcut']; print('KAPI banka vs mevcut', kb.get('gecti'), kb.get('konum_fark_px'), kb.get('kenar_fark_px'), kb.get('sebep')); print('KAPI esit', g_m.get('gecti'), g_m.get('sebep'), g_b.get('gecti'), g_b.get('konum_fark_px'))
# 1:1 kesit: mevcut | banka (isim bandi), ayrica fark x8
y0, y1 = int(round(2290 * K - 110)), int(round(2290 * K + 110))
km, kb_ = mevcut.crop((0, y0, 3307, y1)), banka.crop((0, y0, 3307, y1))
fark = Image.fromarray(np.clip(np.abs(np.asarray(km).astype(int) - np.asarray(kb_).astype(int)) * 8, 0, 255).astype(np.uint8))
x0, x1 = int(300 * K), int(2100 * K)
kes = [im.crop((x0, 0, x1, y1 - y0)) for im in (km, kb_, fark)]
tuval = Image.new('RGB', (kes[0].width * 3 + 40, kes[0].height), (128, 128, 128))
for i, im in enumerate(kes):
    tuval.paste(im, (i * (kes[0].width + 20), 0))
tuval.save('KESIT_mevcut_banka_fark8_MB_11x14.png')
json.dump(R, open('PILOT_SONUC.json', 'w'), indent=1, ensure_ascii=False, default=str)
