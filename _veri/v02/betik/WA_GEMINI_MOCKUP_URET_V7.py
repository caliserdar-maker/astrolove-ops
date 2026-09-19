# ==================================================================
# WA_GEMINI_MOCKUP_URET_V7   (V6'nin QC duzeltmesi)
#
# V6'DAKI HATA: Q1 "yeni poster eskisinden yalniz isim bolgesinde
#   farklidir" varsayimina dayaniyordu. YANLIS. B67'de yeni posterler
#   farkli JPEG kalitesiyle kaydedildi (MB 87, DB 96, PW farkli tablo),
#   bu yuzden poster HER YERDE milimetrik farkli. MB en dusuk kalitede
#   oldugu icin 5 dosyasi sahte FAIL aldi (sapma 0.004-0.008;
#   olculen JPEG gurultu tabani 0.07 - yani tabanin 10 kati altinda).
#
# V7 QC (olculmus tabana dayali, uydurma esik yok):
#   Q1 SAHNE : poster KUTUSU DISI fark, V5 referansiyla karsilastirilir.
#              B67'deki cerceve ezilmesini yakalayacak asil kontrol budur.
#              Tolerans 0.05 = olculen JPEG gurultu tabani (0.036-0.075).
#   Q2 DEGISIM : poster alaninda degisim olmali (sifirsa yanlis kaynak)
#   Q3 SPEC  : 3000x2250, RGB, JPEG q100, 4:4:4, 300 DPI
#
# 18 dosyanin TAMAMI yeniden uretilir (V6 ciktilarinin uzerine yazar).
# CIKTI TEST KLASORUNDE. Uretim klasorune KOPYALAMA YOK.
# ==================================================================

import os, glob, time, csv, gc
import numpy as np
import cv2
from PIL import Image, ImageFilter
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

Image.MAX_IMAGE_PIXELS = None

ROOT = '/content/drive/MyDrive/ASTROLOVE'
MOCK = ROOT + '/WALL_ART/LISTING_MEDIA/MOCKUPS'
OPT  = ROOT + '/WALL_ART/POSTERS/OPTIMIZED_FOR_PRODUCTION'
OUT  = ROOT + '/TEMP/GEMINI_MOCKUP_V6'
YERE = '/content/eski_poster'
PAIR = 'GEMINI_GEMINI'
os.makedirs(OUT, exist_ok=True)
os.makedirs(YERE, exist_ok=True)

EDISYONLAR = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE']
SAHNELER = ['03', '06', '08', '10', '11', '12']
TOLERANS = 0.05          # olculen JPEG gurultu tabani

# V5'te olculen sahne farki referanslari (poster kutusu disi)
V5REF = {
    ('MIDNIGHT_BLUE', '03'): 0.407, ('MIDNIGHT_BLUE', '06'): 0.418,
    ('MIDNIGHT_BLUE', '08'): 0.436, ('MIDNIGHT_BLUE', '10'): 0.418,
    ('MIDNIGHT_BLUE', '11'): None,  ('MIDNIGHT_BLUE', '12'): None,
    ('DEEP_BLACK', '03'): 0.533, ('DEEP_BLACK', '06'): 0.605,
    ('DEEP_BLACK', '08'): 0.585, ('DEEP_BLACK', '10'): 0.551,
    ('DEEP_BLACK', '11'): 0.590, ('DEEP_BLACK', '12'): 0.571,
    ('PURE_WHITE', '03'): 0.073, ('PURE_WHITE', '06'): 0.072,
    ('PURE_WHITE', '08'): 0.077, ('PURE_WHITE', '10'): 0.080,
    ('PURE_WHITE', '11'): 0.076, ('PURE_WHITE', '12'): 0.063,
}

ESKI_ID = {
    ('MIDNIGHT_BLUE', '3X4'): ('1QA9PAwypdabr19p5ZcoTmF3ySoFnJ35c',
        'OPT__MIDNIGHT_BLUE__3X4__WA_POSTER_GEMINI_GEMINI_MIDNIGHT_BLUE_3X4.jpg'),
    ('MIDNIGHT_BLUE', '2X3'): ('13SRpdSJwl16Bz57om5HCWq0kkx8E_Ov3',
        'OPT__MIDNIGHT_BLUE__2X3__WA_POSTER_GEMINI_GEMINI_MIDNIGHT_BLUE_2X3.jpg'),
    ('DEEP_BLACK', '3X4'): ('17Woz7A5L2C_M2jjzDUjht6z-3ZnbgFBG',
        'OPT__DEEP_BLACK__3X4__WA_POSTER_GEMINI_GEMINI_DEEP_BLACK_3X4.jpg'),
    ('DEEP_BLACK', '2X3'): ('13o3O5ViZ8PKcJP_eXCvzob8Clqjgx_6e',
        'OPT__DEEP_BLACK__2X3__WA_POSTER_GEMINI_GEMINI_DEEP_BLACK_2X3.jpg'),
    ('PURE_WHITE', '3X4'): ('1Js8OKlaQWNIqy_4kPARg0GseJofBdcIc',
        'OPT__PURE_WHITE__3X4__GEMINI_GEMINI.jpg'),
    ('PURE_WHITE', '2X3'): ('11wmjKQ2hUu6GBvbcf3QQcHw_WjQWSCcv',
        'OPT__PURE_WHITE__2X3__GEMINI_GEMINI.jpg'),
}

RECETE = {
    'MIDNIGHT_BLUE': dict(poz=1.08, gama=0.94, net=(1.8, 45, 3)),
    'DEEP_BLACK':    dict(poz=None, gama=None, net=None),
    'PURE_WHITE':    dict(poz=None, gama=None, net=None),
}

K = {}
K[('MIDNIGHT_BLUE', '03')] = dict(tip='kutu', kutu=(1299, 164, 1987, 1075), oran='3X4', yon='contain')
K[('MIDNIGHT_BLUE', '06')] = dict(tip='kutu', kutu=(1326, 195, 2099, 1195), oran='3X4', yon='contain')
K[('MIDNIGHT_BLUE', '08')] = dict(tip='kutu', kutu=(1498, 454, 2037, 1173), oran='3X4', yon='esnet')
K[('MIDNIGHT_BLUE', '10')] = dict(tip='kutu', kutu=(1606, 120, 2246, 939),  oran='3X4', yon='contain')
K[('MIDNIGHT_BLUE', '11')] = dict(tip='quad', oran='3X4',
    quad=[(1713.5, 481.0), (2666.6, 416.3), (2590.1, 1899.6), (1617.7, 1759.0)])
K[('MIDNIGHT_BLUE', '12')] = dict(tip='quad', oran='2X3',
    quad=[(1672.3, 746.2), (2147.2, 719.9), (2099.0, 1475.7), (1620.2, 1446.3)])
K[('DEEP_BLACK', '03')] = dict(tip='kutu', kutu=(1190, 147, 1820, 1007), oran='3X4', yon='esnet_bicubic')
K[('DEEP_BLACK', '06')] = dict(tip='kutu', kutu=(1186, 284, 1895, 1282), oran='3X4', yon='esnet_bicubic')
K[('DEEP_BLACK', '08')] = dict(tip='kutu', kutu=(1178, 253, 1843, 1173), oran='3X4', yon='esnet_bicubic')
K[('DEEP_BLACK', '10')] = dict(tip='kutu', kutu=(1219, 213, 1837, 1055), oran='3X4', yon='esnet_bicubic')
K[('DEEP_BLACK', '11')] = dict(tip='kutu', kutu=(1141, 352, 2160, 1863), oran='2X3', yon='esnet_bicubic')
K[('DEEP_BLACK', '12')] = dict(tip='kutu', kutu=(1447, 429, 1996, 1121), oran='3X4', yon='esnet_bicubic')
K[('PURE_WHITE', '03')] = dict(tip='kutu', kutu=(1239, 307, 1911, 1218), oran='3X4', yon='esnet')
K[('PURE_WHITE', '06')] = dict(tip='kutu', kutu=(1362, 331, 2042, 1234), oran='3X4', yon='contain')
K[('PURE_WHITE', '08')] = dict(tip='kutu', kutu=(1261, 276, 1954, 1215), oran='3X4', yon='esnet')
K[('PURE_WHITE', '10')] = dict(tip='kutu', kutu=(1167, 191, 1843, 1113), oran='3X4', yon='esnet')
K[('PURE_WHITE', '11')] = dict(tip='quad', oran='3X4',
    quad=[(1113, 674), (1908, 674), (1909, 1781), (1109, 1781)])
K[('PURE_WHITE', '12')] = dict(tip='quad', oran='3X4',
    quad=[(1260.6, 481.0), (1752.5, 481.0), (1758.2, 1117.3), (1253.0, 1118.3)])


def sure(sn):
    sn = int(sn)
    return '%02d:%02d' % (sn // 60, sn % 60)


def indir(svc, fid, hedef):
    if os.path.exists(hedef) and os.path.getsize(hedef) > 0:
        return hedef
    with open(hedef, 'wb') as f:
        dl = MediaIoBaseDownload(f, svc.files().get_media(fileId=fid))
        bitti = False
        while not bitti:
            _, bitti = dl.next_chunk()
    return hedef


def sahne_uret(yol, r):
    im = Image.open(yol).convert('RGB')
    if im.size != (3000, 2250):
        im = im.resize((3000, 2250), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    if r['poz']:
        a = np.clip(a * r['poz'], 0, 255)
    if r['gama']:
        a = np.clip(255.0 * ((a / 255.0) ** r['gama']), 0, 255)
    im = Image.fromarray(a.astype(np.uint8))
    if r['net']:
        rad, pct, th = r['net']
        im = im.filter(ImageFilter.UnsharpMask(radius=rad, percent=pct, threshold=th))
    return im


def yama_kutu(pos, KW, KH, yon):
    if yon == 'esnet':
        return pos.resize((KW, KH), Image.LANCZOS)
    if yon == 'esnet_bicubic':
        return pos.resize((KW, KH), Image.BICUBIC)
    pw, ph = pos.size
    olc = min(KW / float(pw), KH / float(ph))
    nw, nh = int(round(pw * olc)), int(round(ph * olc))
    kucuk = pos.resize((nw, nh), Image.LANCZOS)
    ke = np.asarray(pos, np.float32)
    serit = np.concatenate([ke[:, :8].reshape(-1, 3), ke[:, -8:].reshape(-1, 3),
                            ke[:8, :].reshape(-1, 3), ke[-8:, :].reshape(-1, 3)])
    renk = tuple(int(v) for v in np.median(serit, axis=0))
    y = Image.new('RGB', (KW, KH), renk)
    y.paste(kucuk, ((KW - nw) // 2, (KH - nh) // 2))
    return y


def quad_bas(A, pos, quad):
    q = np.float32(quad)
    x0, y0 = int(np.floor(q[:, 0].min())), int(np.floor(q[:, 1].min()))
    x1, y1 = int(np.ceil(q[:, 0].max())), int(np.ceil(q[:, 1].max()))
    BW, BH, SS = x1 - x0, y1 - y0, 4
    p = pos.resize((BW * SS, BH * SS), Image.LANCZOS)
    P = cv2.cvtColor(np.asarray(p, np.uint8), cv2.COLOR_RGB2BGR)
    src = np.float32([[0, 0], [P.shape[1], 0], [P.shape[1], P.shape[0]], [0, P.shape[0]]])
    dst = np.float32([[(x - x0) * SS, (y - y0) * SS] for x, y in quad])
    H = cv2.getPerspectiveTransform(src, dst)
    w = cv2.warpPerspective(P, H, (BW * SS, BH * SS), flags=cv2.INTER_LANCZOS4)
    m = cv2.warpPerspective(np.full(P.shape[:2], 255, np.uint8), H, (BW * SS, BH * SS),
                            flags=cv2.INTER_LANCZOS4)
    w = cv2.resize(w, (BW, BH), interpolation=cv2.INTER_AREA)
    m = cv2.resize(m, (BW, BH), interpolation=cv2.INTER_AREA)
    w = cv2.cvtColor(w, cv2.COLOR_BGR2RGB).astype(np.float32)
    a = (m.astype(np.float32) / 255.0)[:, :, None]
    A[y0:y1, x0:x1] = A[y0:y1, x0:x1] * (1 - a) + w * a
    return (x0, y0, x1, y1)


def bas(sahne_img, pos, konf):
    A = np.asarray(sahne_img, np.float32).copy()
    if konf['tip'] == 'kutu':
        KL, KT, KR, KB = konf['kutu']
        A[KT:KB, KL:KR] = np.asarray(yama_kutu(pos, KR - KL, KB - KT, konf['yon']), np.float32)
        return A, (KL, KT, KR, KB)
    return A, quad_bas(A, pos, konf['quad'])


# ==================================================================
svc = build('drive', 'v3')
print('eski posterler hazirlaniyor...', flush=True)
ESKI = {}
for (ed, oran), (fid, adi) in ESKI_ID.items():
    ESKI[(ed, oran)] = indir(svc, fid, os.path.join(YERE, adi))
print('  %d dosya\n' % len(ESKI), flush=True)

satirlar, kontak = [], {}
t0 = time.time()
TOP = len(EDISYONLAR) * len(SAHNELER)
say = PASS = FAIL = 0

for ed in EDISYONLAR:
    os.makedirs(OUT + '/' + ed, exist_ok=True)
    kontak[ed] = []
    r = RECETE[ed]

    for kod in SAHNELER:
        say += 1
        gec = time.time() - t0
        kalan = (gec / max(say - 1, 1)) * (TOP - say + 1) if say > 1 else 0
        bs = '[%d/%d] %-14s %s' % (say, TOP, ed, kod)
        konf = K[(ed, kod)]

        try:
            SD = sorted(glob.glob(MOCK + '/' + kod + '_*'))[0]
            mas = sorted(glob.glob(SD + '/00_MASTER/WA_' + kod + '_SCENE_MASTER_' + ed + '.*'))[0]
            mev = sorted(glob.glob(SD + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.*'))[0]
            yeni_yol = sorted(glob.glob(OPT + '/' + ed + '/' + konf['oran'] + '/*' + PAIR + '*.jpg'))[0]
        except Exception as e:
            print(bs + '  FAIL kaynak: %s' % e, flush=True)
            satirlar.append([ed, kod, 'FAIL_KAYNAK', '', '', '', '', str(e)[:50]])
            FAIL += 1
            continue

        sahne = sahne_uret(mas, r)
        M = np.asarray(Image.open(mev).convert('RGB'), np.float32)

        p = Image.open(ESKI[(ed, konf['oran'])]).convert('RGB')
        A_eski, bkutu = bas(sahne, p, konf)
        del p; gc.collect()

        p = Image.open(yeni_yol).convert('RGB')
        A_yeni, _ = bas(sahne, p, konf)
        del p; gc.collect()

        BL, BT, BR, BB = bkutu
        dis = np.ones(M.shape[:2], bool)
        dis[BT:BB, BL:BR] = False

        # Q1 - sahne (poster kutusu disi)
        sahne_fark = float(np.abs(A_yeni - M).mean(axis=2)[dis].mean())
        ref = V5REF[(ed, kod)]
        if ref is None:
            q1, ref_txt = True, 'ref yok'
            sapma = 0.0
        else:
            sapma = sahne_fark - ref
            q1 = abs(sapma) <= TOLERANS
            ref_txt = '%.3f' % ref

        # Q2 - poster degisimi
        dfark = np.abs(A_yeni - A_eski).mean(axis=2)
        degm = dfark > 2.0
        deg_alan = int(degm.sum())
        q2 = deg_alan > 0
        pos_fark = float(dfark[BT:BB, BL:BR].mean())

        if not (q1 and q2):
            print(bs + '  FAIL  Q1=%s Q2=%s  sahne=%.3f (ref %s, sapma %+.3f)  degisen=%d'
                  % (q1, q2, sahne_fark, ref_txt, sapma, deg_alan), flush=True)
            satirlar.append([ed, kod, 'FAIL', str(bkutu), round(sahne_fark, 3),
                             ref_txt, round(pos_fark, 3), deg_alan])
            FAIL += 1
            del A_eski, A_yeni, M, dfark; gc.collect()
            continue

        cikti = OUT + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.jpg'
        Image.fromarray(np.clip(A_yeni, 0, 255).astype(np.uint8)).save(
            cikti, 'JPEG', quality=100, subsampling=0, dpi=(300, 300))
        with Image.open(cikti) as im:
            q3 = (im.size == (3000, 2250) and im.mode == 'RGB')
        mb = os.path.getsize(cikti) / 1048576.0

        ys, xs = np.where(degm)
        dbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

        satirlar.append([ed, kod, 'PASS' if q3 else 'FAIL_SPEC', str(bkutu),
                         round(sahne_fark, 3), ref_txt, round(pos_fark, 3), deg_alan])
        PASS += 1
        print(bs + '  PASS  sahne=%.3f (ref %s, sapma %+.3f)  poster_fark=%.3f  degisen=%d px  %.2f MB  | gecen %s kalan ~%s'
              % (sahne_fark, ref_txt, sapma, pos_fark, deg_alan, mb, sure(gec), sure(kalan)), flush=True)

        k1 = Image.fromarray(M.astype(np.uint8)).crop(bkutu)
        k2 = Image.fromarray(np.clip(A_yeni, 0, 255).astype(np.uint8)).crop(bkutu)
        k3 = Image.fromarray(np.clip(dfark[BT:BB, BL:BR] * 8, 0, 255).astype(np.uint8)).convert('RGB')
        h = 360
        o = h / float(k1.size[1])
        no = (max(int(k1.size[0] * o), 1), h)
        kontak[ed].append((k1.resize(no, Image.LANCZOS), k2.resize(no, Image.LANCZOS),
                           k3.resize(no, Image.LANCZOS)))
        del A_eski, A_yeni, M, dfark; gc.collect()

    if kontak[ed]:
        gw = max(s[0].size[0] for s in kontak[ed])
        sayfa = Image.new('RGB', (gw * 3 + 60, 380 * len(kontak[ed])), (250, 250, 250))
        for i, (a, b, c) in enumerate(kontak[ed]):
            sayfa.paste(a, (0, i * 380)); sayfa.paste(b, (gw + 20, i * 380))
            sayfa.paste(c, (gw * 2 + 40, i * 380))
        sayfa.save(OUT + '/KONTAK_' + ed + '.png')
        print('  kontak: KONTAK_%s.png\n' % ed, flush=True)

with open(OUT + '/URETIM_V7.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['edisyon', 'sahne', 'durum', 'bolge', 'sahne_fark',
                'v5_referans', 'poster_alani_fark', 'degisen_px'])
    w.writerows(satirlar)

print('=' * 78, flush=True)
print('SONUC: PASS %d / FAIL %d / toplam %d' % (PASS, FAIL, TOP), flush=True)
print('=' * 78, flush=True)
print('%-14s %-4s %-6s %-8s %-8s %-9s %s' %
      ('edisyon', 'sah', 'durum', 'sahne', 'ref', 'poster', 'degisen'), flush=True)
for s in satirlar:
    print('%-14s %-4s %-6s %-8s %-8s %-9s %s' % (s[0], s[1], s[2], s[4], s[5], s[6], s[7]), flush=True)

print('''
OKUMA:
  sahne  = poster kutusu DISI fark. V5 referansiyla ayni olmali.
           B67'de yasanan cerceve ezilmesini yakalayacak kontrol budur.
  poster = poster alaninda eski/yeni fark. Sifir olmamali.
  MB 11/12'de V5 referansi yok (ORB yoluyla olculmuslerdi).

  Cikti: TEMP/GEMINI_MOCKUP_V6   -   uretim klasorune KOPYALANMADI.
  Simdi KONTAK_*.png dosyalarina bak: sol mevcut | orta yeni | sag fark x8
''', flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
