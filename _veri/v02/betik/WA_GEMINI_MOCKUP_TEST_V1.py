# ==================================================================
# WA_GEMINI_MOCKUP_TEST_V1  -  SALT OLCUM (uretim dosyasi yazmaz)
#
# AMAC: 3 edisyonun 06 Hero mockup'ini ESKI posterle yeniden uretip
#       mevcut dosyayla piksel farkini olcmek.
#       Fark ~0 ise koordinat + hat recetesi DOGRULANMIS olur.
#
# KAYNAK KILITLER:
#   B39 - tum lifestyle sahneler 3:4 kaynak (OPTIMIZED/3X4)
#   B40 - MB: sahne 1448 olcek, box(640,94,1013,577), +%8 pozlama,
#         gamma 0.94, netlik 45/1.8, contain + kenar rengi dolgu
#   B47 - DB: box(1185,284,1894,1282) @3000, tam esnetme, grade YOK
#   B54 - PW: quad(1363,331)(2042,330)(2040,1233)(1362,1233) @3000,
#         tam esnetme, sahne masteri ZATEN 3000 + netli -> atla
#
# CIKTI: TEMP/GEMINI_TEST_V1/  (aday jpg + kontak png + csv)
# ==================================================================

import os, glob, time, csv, io
import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

ROOT = '/content/drive/MyDrive/ASTROLOVE'
MOCK = ROOT + '/WALL_ART/LISTING_MEDIA/MOCKUPS'
TEMP = ROOT + '/TEMP'
YEDEK = TEMP + '/GEMINI_YEDEK'
OUT  = TEMP + '/GEMINI_TEST_V1'
PAIR = 'GEMINI_GEMINI'

os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------
# EDISYON RECETELERI
# ------------------------------------------------------------------
RECETE = {
    'MIDNIGHT_BLUE': dict(
        kutu_1448 = (640, 94, 1013, 577),
        olcek     = 3000.0 / 1448.0,
        yerlesim  = 'contain_dolgu',
        pozlama   = 1.08,
        gama      = 0.94,
        netlik    = (1.8, 45, 3),      # radius, percent, threshold
        buyut     = True,
    ),
    'DEEP_BLACK': dict(
        kutu_3000 = (1185, 284, 1894, 1282),
        yerlesim  = 'esnet',
        pozlama   = None,
        gama      = None,
        netlik    = (1.8, 45, 3),
        buyut     = True,
    ),
    'PURE_WHITE': dict(
        kutu_3000 = (1362, 330, 2042, 1233),   # quad'in sinir kutusu
        yerlesim  = 'esnet',
        pozlama   = None,
        gama      = None,
        netlik    = None,              # B54: master zaten netli
        buyut     = False,
    ),
}

EDISYONLAR = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE']


def bul(desen):
    return sorted(glob.glob(desen))


def sure(sn):
    sn = int(sn)
    return '%02d:%02d' % (sn // 60, sn % 60)


# ==================================================================
# ASAMA 1 - KESIF (hicbir sey uretilmez)
# ==================================================================
print('=' * 62, flush=True)
print('ASAMA 1 - KESIF', flush=True)
print('=' * 62, flush=True)

sahne_dizin = bul(MOCK + '/06_*')
if not sahne_dizin:
    raise SystemExit('DURDU: 06 sahne klasoru bulunamadi -> ' + MOCK)
SD = sahne_dizin[0]
print('sahne klasoru : ' + os.path.basename(SD), flush=True)

print('\nyedek klasor icerigi (ilk 40):', flush=True)
yedek_hepsi = bul(YEDEK + '/**/*.*')
if not yedek_hepsi:
    print('  ! bos veya yok: ' + YEDEK, flush=True)
for p in yedek_hepsi[:40]:
    print('  ' + p.replace(ROOT, '') + '  (%.2f MB)' % (os.path.getsize(p) / 1048576.0), flush=True)
print('  toplam %d dosya' % len(yedek_hepsi), flush=True)

DOSYA = {}
eksik = []

for ed in EDISYONLAR:
    master = bul(SD + '/00_MASTER/WA_06_SCENE_MASTER_' + ed + '.*')
    mevcut = bul(SD + '/' + ed + '/WA_06_MOCKUP_' + PAIR + '_' + ed + '.*')
    # eski poster: yedekte, edisyon adi + 3X4 gecen dosya
    poster = [p for p in yedek_hepsi
              if ed in p.upper()
              and '3X4' in p.upper()
              and p.lower().endswith(('.jpg', '.jpeg', '.png'))]

    DOSYA[ed] = dict(master=master, mevcut=mevcut, poster=poster)

    print('\n[' + ed + ']', flush=True)
    for ad, lst in (('sahne master', master), ('mevcut mockup', mevcut), ('eski poster ', poster)):
        if lst:
            print('  %s : %s' % (ad, os.path.basename(lst[0])), flush=True)
            if len(lst) > 1:
                print('      ! %d aday var, ilki kullanilacak' % len(lst), flush=True)
        else:
            print('  %s : YOK' % ad, flush=True)
            eksik.append(ed + ' / ' + ad.strip())

if eksik:
    print('\n' + '=' * 62, flush=True)
    print('DURDU - EKSIK DOSYA VAR, olcum yapilmadi:', flush=True)
    for e in eksik:
        print('  - ' + e, flush=True)
    print('Yukaridaki yedek listesini Claude\'a gonder.', flush=True)
    raise SystemExit(0)

print('\nkesif TAMAM - tum dosyalar bulundu\n', flush=True)


# ==================================================================
# ASAMA 2 - YENIDEN URETIM VE OLCUM
# ==================================================================
print('=' * 62, flush=True)
print('ASAMA 2 - YENIDEN URETIM + OLCUM', flush=True)
print('=' * 62, flush=True)

satirlar = []
t0 = time.time()
N = len(EDISYONLAR)

for i, ed in enumerate(EDISYONLAR, 1):
    r = RECETE[ed]
    d = DOSYA[ed]

    # --- sahne ---
    sahne = Image.open(d['master'][0]).convert('RGB')
    ham_olcu = sahne.size
    if r['buyut'] and sahne.size != (3000, 2250):
        sahne = sahne.resize((3000, 2250), Image.LANCZOS)
    elif sahne.size != (3000, 2250):
        sahne = sahne.resize((3000, 2250), Image.LANCZOS)

    a = np.asarray(sahne, np.float32)
    if r['pozlama']:
        a = np.clip(a * r['pozlama'], 0, 255)
    if r['gama']:
        a = np.clip(255.0 * ((a / 255.0) ** r['gama']), 0, 255)
    sahne = Image.fromarray(a.astype(np.uint8))
    if r['netlik']:
        rad, pct, th = r['netlik']
        sahne = sahne.filter(ImageFilter.UnsharpMask(radius=rad, percent=pct, threshold=th))

    # --- kutu ---
    if 'kutu_1448' in r:
        l, t, rr, b = r['kutu_1448']
        s = r['olcek']
        kutu = (int(round(l * s)), int(round(t * s)), int(round(rr * s)), int(round(b * s)))
    else:
        kutu = r['kutu_3000']
    KL, KT, KR, KB = kutu
    KW, KH = KR - KL, KB - KT

    # --- poster ---
    pos = Image.open(d['poster'][0]).convert('RGB')
    pw, ph = pos.size

    if r['yerlesim'] == 'esnet':
        yama = pos.resize((KW, KH), Image.LANCZOS)
        dolgu_px = 0
    else:
        # contain: orani koru, kenar rengiyle doldur
        olc = min(KW / float(pw), KH / float(ph))
        nw, nh = int(round(pw * olc)), int(round(ph * olc))
        kucuk = pos.resize((nw, nh), Image.LANCZOS)
        ke = np.asarray(pos, np.float32)
        serit = np.concatenate([
            ke[:, :8].reshape(-1, 3), ke[:, -8:].reshape(-1, 3),
            ke[:8, :].reshape(-1, 3), ke[-8:, :].reshape(-1, 3)])
        renk = tuple(int(v) for v in np.median(serit, axis=0))
        yama = Image.new('RGB', (KW, KH), renk)
        yama.paste(kucuk, ((KW - nw) // 2, (KH - nh) // 2))
        dolgu_px = max(KW - nw, KH - nh)

    aday = sahne.copy()
    aday.paste(yama, (KL, KT))

    # --- mevcut dosya ---
    mev = Image.open(d['mevcut'][0]).convert('RGB')
    if mev.size != aday.size:
        satirlar.append([ed, 'OLCU_FARKLI', str(mev.size), str(aday.size), '', '', '', '', '', ''])
        print('[%d/%N] %s  OLCU FARKLI %s vs %s' % (i, ed, mev.size, aday.size), flush=True)
        continue

    A = np.asarray(aday, np.float32)
    B = np.asarray(mev, np.float32)
    F = np.abs(A - B).mean(axis=2)

    maske = np.zeros(F.shape, bool)
    maske[KT:KB, KL:KR] = True

    p_ort, p_max = float(F[maske].mean()), float(F[maske].max())
    s_ort, s_max = float(F[~maske].mean()), float(F[~maske].max())

    # gurultu tabani: mevcut dosyayi q100 yeniden kodla, kendisiyle karsilastir
    buf = io.BytesIO()
    mev.save(buf, 'JPEG', quality=100, subsampling=0)
    buf.seek(0)
    tab = np.abs(np.asarray(Image.open(buf).convert('RGB'), np.float32) - B).mean(axis=2)
    g_ort = float(tab.mean())

    # --- ciktilar ---
    aday.save(OUT + '/ADAY_WA_06_MOCKUP_' + PAIR + '_' + ed + '.jpg',
              'JPEG', quality=100, subsampling=0, dpi=(300, 300))

    kutu_gen = (KL - 60, KT - 60, KR + 60, KB + 60)
    k1 = mev.crop(kutu_gen)
    k2 = aday.crop(kutu_gen)
    k3 = Image.fromarray(np.clip(F[kutu_gen[1]:kutu_gen[3], kutu_gen[0]:kutu_gen[2]] * 8, 0, 255)
                         .astype(np.uint8)).convert('RGB')
    h = 900
    o = h / float(k1.size[1])
    k1 = k1.resize((int(k1.size[0] * o), h), Image.LANCZOS)
    k2 = k2.resize((int(k2.size[0] * o), h), Image.LANCZOS)
    k3 = k3.resize((int(k3.size[0] * o), h), Image.LANCZOS)
    kon = Image.new('RGB', (k1.size[0] * 3 + 40, h), (255, 255, 255))
    kon.paste(k1, (0, 0)); kon.paste(k2, (k1.size[0] + 20, 0)); kon.paste(k3, (k1.size[0] * 2 + 40, 0))
    kon.save(OUT + '/KONTAK_' + ed + '.png')

    satirlar.append([ed, str(ham_olcu), str(kutu), r['yerlesim'], dolgu_px,
                     round(s_ort, 3), round(s_max, 1),
                     round(p_ort, 3), round(p_max, 1), round(g_ort, 3)])

    gec = time.time() - t0
    kalan = gec / i * (N - i)
    print('[%d/%d] %-15s sahne_ort=%6.2f  poster_ort=%6.2f  gurultu=%5.2f  | gecen %s  kalan ~%s  %%%d'
          % (i, N, ed, s_ort, p_ort, g_ort, sure(gec), sure(kalan), i * 100 // N), flush=True)

# --- csv ---
with open(OUT + '/GEMINI_TEST_V1.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['edisyon', 'master_olcu', 'kutu', 'yerlesim', 'dolgu_px',
                'sahne_ort_fark', 'sahne_max_fark',
                'poster_ort_fark', 'poster_max_fark', 'gurultu_tabani'])
    w.writerows(satirlar)

print('\n' + '=' * 62, flush=True)
print('SONUC TABLOSU', flush=True)
print('=' * 62, flush=True)
print('%-15s %10s %10s %10s' % ('edisyon', 'sahne', 'poster', 'gurultu'), flush=True)
for s in satirlar:
    if s[1] == 'OLCU_FARKLI':
        print('%-15s  OLCU FARKLI' % s[0], flush=True)
    else:
        print('%-15s %10s %10s %10s' % (s[0], s[5], s[7], s[9]), flush=True)

print('''
OKUMA:
  sahne  = poster DISI alanin ortalama farki (0-255)
  poster = poster alaninin ortalama farki
  gurultu= ayni dosyanin q100 yeniden kodlama farki (referans taban)

  Her iki fark da gurultu tabanina yakinsa RECETE DOGRU.
  sahne buyukse  -> aydinlatma/netlik yanlis
  poster buyukse -> koordinat veya yerlesim yanlis

Cikti klasoru: TEMP/GEMINI_TEST_V1
  KONTAK_*.png  = sol mevcut | orta aday | sag fark x8
''', flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
