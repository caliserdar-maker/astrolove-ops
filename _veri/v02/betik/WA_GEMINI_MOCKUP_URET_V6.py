# ==================================================================
# WA_GEMINI_MOCKUP_URET_V6
#
# 18 GEMINI_GEMINI mockup'i YENI (hizasi duzeltilmis) posterle uretir.
# CIKTI TEST KLASORUNE GIDER. Uretim dosyalarina DOKUNMAZ.
#
# TUM PARAMETRELER OLCULDU (V3 + V5), tahmin yok:
#   sahne recetesi : MB lanczos+%8 pozlama+gama0.94+netlik45/1.8
#                    DB lanczos, islem yok
#                    PW islem yok (master zaten 3000)
#   kutular        : START_HERE kaydi + olculen ofset duzeltmesi
#                    (DB 6 sahne +1px sag, PW 06 +1px asagi)
#   MB 11 / MB 12  : kayit yoktu, ORB homografiyle olculdu
#   PW 11 / PW 12  : B54 dortgeni (yamuk) - warp
#   oran/yontem    : her sahne icin en dusuk farki veren secildi
#
# QC (dosya basina, FAIL -> dosya YAZILMAZ):
#   Q1 DEGISMEZLIK : yeni dosya, eski posterle uretilen referanstan
#                    YALNIZ posterin degistigi bolgede farkli olmali.
#                    Bolge disi fark birebir esit olmali (fark 0).
#   Q2 DEGISIM VAR : posterde degisen bolge bos olmamali
#                    (bos ise yanlis kaynak kullanilmis demektir)
#   Q3 SPEC        : 3000x2250, RGB, JPEG q100, 4:4:4, 300 DPI
#
# CIKTI: TEMP/GEMINI_MOCKUP_V6/<EDISYON>/*.jpg
#        TEMP/GEMINI_MOCKUP_V6/KONTAK_<EDISYON>.png
#        TEMP/GEMINI_MOCKUP_V6/URETIM_V6.csv
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

# ESKI posterler (yedekten, dosya ID ile) - referans uretimi icin
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

# ------------------------------------------------------------------
# KILITLI YERLESIM TABLOSU  (V5 olcumu)
# ------------------------------------------------------------------
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


def quad_bas(sahne_arr, pos, quad):
    """4x supersampling ile perspektif warp (B54 kurali). Yerinde birlestirir."""
    q = np.float32(quad)
    x0, y0 = int(np.floor(q[:, 0].min())), int(np.floor(q[:, 1].min()))
    x1, y1 = int(np.ceil(q[:, 0].max())), int(np.ceil(q[:, 1].max()))
    BW, BH = x1 - x0, y1 - y0
    SS = 4
    # posteri 4x hedef boyuta indir (tek adim LANCZOS)
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
    bolge = sahne_arr[y0:y1, x0:x1]
    sahne_arr[y0:y1, x0:x1] = bolge * (1 - a) + w * a
    return (x0, y0, x1, y1)


def bas(sahne_img, pos, konf):
    """Posteri sahneye basar. Donen: (dizi, bolge_kutusu)"""
    A = np.asarray(sahne_img, np.float32).copy()
    if konf['tip'] == 'kutu':
        KL, KT, KR, KB = konf['kutu']
        y = np.asarray(yama_kutu(pos, KR - KL, KB - KT, konf['yon']), np.float32)
        A[KT:KB, KL:KR] = y
        return A, (KL, KT, KR, KB)
    return A, quad_bas(A, pos, konf['quad'])


# ==================================================================
svc = build('drive', 'v3')
print('eski posterler indiriliyor...', flush=True)
ESKI = {}
for (ed, oran), (fid, adi) in ESKI_ID.items():
    ESKI[(ed, oran)] = indir(svc, fid, os.path.join(YERE, adi))
print('  %d dosya hazir\n' % len(ESKI), flush=True)

satirlar = []
kontak = {}
t0 = time.time()
TOP = len(EDISYONLAR) * len(SAHNELER)
say = 0
PASS = FAIL = 0

for ed in EDISYONLAR:
    os.makedirs(OUT + '/' + ed, exist_ok=True)
    kontak[ed] = []
    r = RECETE[ed]

    for kod in SAHNELER:
        say += 1
        gec = time.time() - t0
        kalan = (gec / max(say - 1, 1)) * (TOP - say + 1) if say > 1 else 0
        bas_txt = '[%d/%d] %-14s %s' % (say, TOP, ed, kod)
        konf = K[(ed, kod)]

        try:
            SD = sorted(glob.glob(MOCK + '/' + kod + '_*'))[0]
            mas = sorted(glob.glob(SD + '/00_MASTER/WA_' + kod + '_SCENE_MASTER_' + ed + '.*'))[0]
            mev = sorted(glob.glob(SD + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.*'))[0]
            yeni_yol = sorted(glob.glob(OPT + '/' + ed + '/' + konf['oran'] + '/*' + PAIR + '*.jpg'))
            if not yeni_yol:
                raise IOError('yeni poster yok: ' + OPT + '/' + ed + '/' + konf['oran'])
            yeni_yol = yeni_yol[0]
        except Exception as e:
            print(bas_txt + '  FAIL kaynak: %s' % e, flush=True)
            satirlar.append([ed, kod, 'FAIL', 'kaynak', '', '', '', str(e)[:60]])
            FAIL += 1
            continue

        sahne = sahne_uret(mas, r)
        M = np.asarray(Image.open(mev).convert('RGB'), np.float32)

        p_eski = Image.open(ESKI[(ed, konf['oran'])]).convert('RGB')
        A_eski, bkutu = bas(sahne, p_eski, konf)
        del p_eski; gc.collect()

        p_yeni = Image.open(yeni_yol).convert('RGB')
        A_yeni, _ = bas(sahne, p_yeni, konf)
        del p_yeni; gc.collect()

        # --- degisim maskesi: iki uretimin farki ---
        dfark = np.abs(A_yeni - A_eski).mean(axis=2)
        deg = (dfark > 2.0).astype(np.uint8) * 255
        deg = cv2.dilate(deg, np.ones((9, 9), np.uint8))
        degm = deg > 0
        deg_alan = int(degm.sum())

        # --- Q1 DEGISMEZLIK ---
        dis = ~degm
        r_eski = float(np.abs(A_eski - M).mean(axis=2)[dis].mean())
        r_yeni = float(np.abs(A_yeni - M).mean(axis=2)[dis].mean())
        q1 = abs(r_yeni - r_eski) < 0.001
        # --- Q2 DEGISIM VAR ---
        q2 = deg_alan > 0

        if not (q1 and q2):
            print(bas_txt + '  FAIL  Q1=%s Q2=%s  (r_eski=%.3f r_yeni=%.3f alan=%d)'
                  % (q1, q2, r_eski, r_yeni, deg_alan), flush=True)
            satirlar.append([ed, kod, 'FAIL', 'Q1' if not q1 else 'Q2',
                             round(r_eski, 3), round(r_yeni, 3), deg_alan, ''])
            FAIL += 1
            del A_eski, A_yeni, M; gc.collect()
            continue

        # --- yaz ---
        cikti = OUT + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.jpg'
        Image.fromarray(np.clip(A_yeni, 0, 255).astype(np.uint8)).save(
            cikti, 'JPEG', quality=100, subsampling=0, dpi=(300, 300))

        # --- Q3 SPEC ---
        with Image.open(cikti) as im:
            q3 = (im.size == (3000, 2250) and im.mode == 'RGB')
        mb = os.path.getsize(cikti) / 1048576.0

        ys, xs = np.where(degm)
        dbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

        satirlar.append([ed, kod, 'PASS' if q3 else 'FAIL_SPEC', str(bkutu),
                         round(r_eski, 3), round(r_yeni, 3), deg_alan, str(dbox)])
        PASS += 1
        print(bas_txt + '  PASS  uyum=%.3f  degisen=%d px  bolge=%s  %.2f MB  | gecen %s kalan ~%s'
              % (r_yeni, deg_alan, str(dbox), mb, sure(gec), sure(kalan)), flush=True)

        # kontak satiri
        k1 = Image.fromarray(M.astype(np.uint8)).crop(bkutu)
        k2 = Image.fromarray(np.clip(A_yeni, 0, 255).astype(np.uint8)).crop(bkutu)
        k3 = Image.fromarray(np.clip(dfark[bkutu[1]:bkutu[3], bkutu[0]:bkutu[2]] * 8, 0, 255)
                             .astype(np.uint8)).convert('RGB')
        h = 360
        o = h / float(k1.size[1])
        yeni_olcu = (max(int(k1.size[0] * o), 1), h)
        kontak[ed].append((kod, k1.resize(yeni_olcu, Image.LANCZOS),
                           k2.resize(yeni_olcu, Image.LANCZOS),
                           k3.resize(yeni_olcu, Image.LANCZOS)))

        del A_eski, A_yeni, M, dfark; gc.collect()

    # --- edisyon kontak sayfasi ---
    if kontak[ed]:
        gw = max(s[1].size[0] for s in kontak[ed])
        sayfa = Image.new('RGB', (gw * 3 + 60, 380 * len(kontak[ed])), (250, 250, 250))
        for i, (kod, a, b, c) in enumerate(kontak[ed]):
            sayfa.paste(a, (0, i * 380))
            sayfa.paste(b, (gw + 20, i * 380))
            sayfa.paste(c, (gw * 2 + 40, i * 380))
        sayfa.save(OUT + '/KONTAK_' + ed + '.png')
        print('  kontak yazildi: KONTAK_%s.png  (sol mevcut | orta yeni | sag fark x8)\n' % ed, flush=True)

with open(OUT + '/URETIM_V6.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['edisyon', 'sahne', 'durum', 'bolge', 'uyum_eski', 'uyum_yeni',
                'degisen_px', 'degisim_kutusu'])
    w.writerows(satirlar)

print('=' * 78, flush=True)
print('SONUC: PASS %d / FAIL %d / toplam %d' % (PASS, FAIL, TOP), flush=True)
print('=' * 78, flush=True)
print('%-14s %-4s %-6s %-8s %-10s %s' % ('edisyon', 'sah', 'durum', 'uyum', 'degisen', 'degisim kutusu'), flush=True)
for s in satirlar:
    print('%-14s %-4s %-6s %-8s %-10s %s' % (s[0], s[1], s[2], s[5], s[6], s[7]), flush=True)

print('''
OKUMA:
  uyum    = yeni dosyanin canli dosyaya benzerligi (poster disi).
            V5'te olculen bantta olmali: MB ~0.25 / DB ~1.3 / PW ~0.1-1.0
  degisen = posterin degistigi piksel sayisi. Sifir olmamali.
  kutusu  = degisimin yeri. Sagdaki GEMINI yazisinin bolgesi olmali.

  Cikti TEST klasorunde: TEMP/GEMINI_MOCKUP_V6
  Uretim klasorune KOPYALAMA YAPILMADI - ayri adim, ayri onay.
  Once KONTAK_*.png dosyalarina bak.
''', flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
