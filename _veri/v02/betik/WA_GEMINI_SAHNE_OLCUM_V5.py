# ==================================================================
# WA_GEMINI_SAHNE_OLCUM_V5  -  SALT OLCUM (hicbir sey uretmez)
#
# V4 IPTAL. V4'un kutu bulma yontemi (sahne-mockup farki) HATALIYDI:
#   sahne masterindeki yer tutucu poster gercek postere cok benziyor,
#   fark yalniz sembolde cikti -> 18/18 yanlis kutu.
#   Kanit: MB 06'nin dogru kutusu V3'te ispatlandi (ofset 0/0, 0.234),
#   V4 ayni sahne icin bambaska kutu verdi.
#
# V5 = V3'un CALISAN yontemi, 18 mockup'a uygulanmis:
#   KAYITLI KUTU VARSA -> posteri kutuya yerlestir, farki ve ofseti olc
#   KAYIT YOKSA (MB 11, MB 12) -> ORB homografi;
#       oran secimi "en cok eslesme" ile DEGIL (B67'yi bozan buydu),
#       WARP SONRASI PIKSEL FARKI ile yapilir.
#
# KAZANAN SAHNE RECETELERI (V3, olculmus):
#   MB : lanczos + %8 pozlama + gama 0.94 + netlik 45/1.8
#   DB : lanczos, islem YOK
#   PW : islem YOK
#
# CIKTI: TEMP/GEMINI_TEST_V1/SAHNE_OLCUM_V5.csv
# ==================================================================

import os, glob, time, csv
import numpy as np
import cv2
from PIL import Image, ImageFilter
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

Image.MAX_IMAGE_PIXELS = None

ROOT = '/content/drive/MyDrive/ASTROLOVE'
MOCK = ROOT + '/WALL_ART/LISTING_MEDIA/MOCKUPS'
OUT  = ROOT + '/TEMP/GEMINI_TEST_V1'
YERE = '/content/eski_poster'
PAIR = 'GEMINI_GEMINI'
os.makedirs(OUT, exist_ok=True)
os.makedirs(YERE, exist_ok=True)

SAHNELER = ['03', '06', '08', '10', '11', '12']
EDISYONLAR = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE']

POSTER_ID = {
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

MB_OLCEK = 3000.0 / 1448.0
KAYIT = {
    'MIDNIGHT_BLUE': {'03': (627, 79, 959, 519), '06': (640, 94, 1013, 577),
                      '08': (723, 219, 983, 566), '10': (775, 58, 1084, 453),
                      '11': None, '12': None},
    'DEEP_BLACK':    {'03': (1189, 147, 1819, 1007), '06': (1185, 284, 1894, 1282),
                      '08': (1177, 253, 1842, 1173), '10': (1218, 213, 1836, 1055),
                      '11': (1140, 352, 2159, 1863), '12': (1446, 429, 1995, 1121)},
    'PURE_WHITE':    {'03': (1239, 307, 1911, 1218), '06': (1362, 330, 2042, 1233),
                      '08': (1261, 276, 1954, 1215), '10': (1167, 191, 1843, 1113),
                      '11': (1109, 674, 1909, 1781), '12': (1253, 481, 1758, 1118)},
}

RECETE = {
    'MIDNIGHT_BLUE': dict(poz=1.08, gama=0.94, net=(1.8, 45, 3)),
    'DEEP_BLACK':    dict(poz=None, gama=None, net=None),
    'PURE_WHITE':    dict(poz=None, gama=None, net=None),
}


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


def yama_uret(pos, KW, KH, tur):
    if tur == 'esnet':
        return pos.resize((KW, KH), Image.LANCZOS)
    if tur == 'esnet_bicubic':
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


def homografi_ara(pos_yol, M_uint8):
    """ORB + RANSAC. poster -> mockup homografisi. Kucultulmus ozniteliklerle."""
    pos = cv2.imread(pos_yol, cv2.IMREAD_COLOR)
    if pos is None:
        return None
    HED = 1200.0
    s = HED / max(pos.shape[:2])
    kucuk = cv2.resize(pos, (int(pos.shape[1] * s), int(pos.shape[0] * s)), interpolation=cv2.INTER_AREA)
    g1 = cv2.cvtColor(kucuk, cv2.COLOR_BGR2GRAY)
    g2 = cv2.cvtColor(M_uint8, cv2.COLOR_RGB2GRAY)

    orb = cv2.ORB_create(nfeatures=8000)
    k1, d1 = orb.detectAndCompute(g1, None)
    k2, d2 = orb.detectAndCompute(g2, None)
    if d1 is None or d2 is None or len(k1) < 20 or len(k2) < 20:
        return None
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    ham = bf.knnMatch(d1, d2, k=2)
    iyi = [m for m, n in ham if m.distance < 0.75 * n.distance]
    if len(iyi) < 20:
        return None
    src = np.float32([k1[m.queryIdx].pt for m in iyi]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in iyi]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None:
        return None
    ic = int(mask.sum())

    # kucuk -> tam olcek
    S = np.array([[s, 0, 0], [0, s, 0], [0, 0, 1]], np.float64)
    H_tam = H.dot(S)

    warp = cv2.warpPerspective(pos, H_tam, (M_uint8.shape[1], M_uint8.shape[0]))
    beyaz = np.full(pos.shape[:2], 255, np.uint8)
    mw = cv2.warpPerspective(beyaz, H_tam, (M_uint8.shape[1], M_uint8.shape[0]))
    mw = cv2.erode(mw, np.ones((9, 9), np.uint8))
    ic_maske = mw > 200
    if ic_maske.sum() < 5000:
        return None
    fark = float(np.abs(cv2.cvtColor(warp, cv2.COLOR_BGR2RGB).astype(np.float32)
                        - M_uint8.astype(np.float32)).mean(axis=2)[ic_maske].mean())

    h, w = pos.shape[:2]
    kose = cv2.perspectiveTransform(
        np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2), H_tam).reshape(4, 2)
    return dict(inlier=ic, esles=len(iyi), fark=fark,
                koseler=[(round(float(x), 1), round(float(y), 1)) for x, y in kose],
                kutu=(int(kose[:, 0].min()), int(kose[:, 1].min()),
                      int(kose[:, 0].max()), int(kose[:, 1].max())),
                alan_px=int(ic_maske.sum()))


# ==================================================================
svc = build('drive', 'v3')
POSTER = {}
print('eski posterler indiriliyor...', flush=True)
for (ed, oran), (fid, adi) in POSTER_ID.items():
    POSTER[(ed, oran)] = indir(svc, fid, os.path.join(YERE, adi))
print('  %d dosya hazir\n' % len(POSTER), flush=True)

satirlar = []
t0 = time.time()
TOP = len(EDISYONLAR) * len(SAHNELER)
say = 0

for ed in EDISYONLAR:
    r = RECETE[ed]
    for kod in SAHNELER:
        say += 1
        gec = time.time() - t0
        kalan = (gec / max(say - 1, 1)) * (TOP - say + 1) if say > 1 else 0
        bas = '[%d/%d] %-14s %s' % (say, TOP, ed, kod)

        sd = sorted(glob.glob(MOCK + '/' + kod + '_*'))
        if not sd:
            print(bas + '  SAHNE KLASORU YOK', flush=True); continue
        SD = sd[0]
        mas = sorted(glob.glob(SD + '/00_MASTER/WA_' + kod + '_SCENE_MASTER_' + ed + '.*'))
        mev = sorted(glob.glob(SD + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.*'))
        if not mas or not mev:
            print(bas + '  EKSIK  master=%d mockup=%d' % (len(mas), len(mev)), flush=True)
            satirlar.append([ed, kod, 'EKSIK', '', '', '', '', '', ''])
            continue

        Mimg = Image.open(mev[0]).convert('RGB')
        M = np.asarray(Mimg, np.float32)
        M8 = np.asarray(Mimg, np.uint8)

        kay = KAYIT[ed][kod]

        # ---------- YOL A: KAYITLI KUTU VAR ----------
        if kay is not None:
            if ed == 'MIDNIGHT_BLUE':
                kay = tuple(int(round(v * MB_OLCEK)) for v in kay)
            KL, KT, KR, KB = kay
            KW, KH = KR - KL, KB - KT

            S = np.asarray(sahne_uret(mas[0], r), np.float32)
            dis = np.ones(M.shape[:2], bool)
            dis[KT:KB, KL:KR] = False
            sahne_fark = float(np.abs(S - M).mean(axis=2)[dis].mean())
            del S

            hedef = M[KT:KB, KL:KR]
            en = (1e9, '', '', None)
            for oran in ('3X4', '2X3'):
                pos = Image.open(POSTER[(ed, oran)]).convert('RGB')
                for tur in ('esnet', 'esnet_bicubic', 'contain'):
                    y = np.asarray(yama_uret(pos, KW, KH, tur), np.float32)
                    sk = float(np.abs(y - hedef).mean())
                    if sk < en[0]:
                        en = (sk, oran, tur, y)
            p_fark, p_oran, p_tur, eniyi_y = en

            ofs = []
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    h2 = M[KT + dy:KB + dy, KL + dx:KR + dx]
                    if h2.shape == eniyi_y.shape:
                        ofs.append((float(np.abs(eniyi_y - h2).mean()), dx, dy))
            ofs.sort()
            of_sk, of_dx, of_dy = ofs[0]

            satirlar.append([ed, kod, 'KAYIT', str(kay), round(sahne_fark, 3),
                             p_oran + '/' + p_tur, round(p_fark, 3),
                             '%+d/%+d' % (of_dx, of_dy), round(of_sk, 3)])
            print(bas + '  KAYIT %-22s sahne=%5.2f  poster=%-14s %6.3f  ofset=%+d/%+d %6.3f  | gecen %s kalan ~%s'
                  % (str(kay), sahne_fark, p_oran + '/' + p_tur, p_fark,
                     of_dx, of_dy, of_sk, sure(gec), sure(kalan)), flush=True)

        # ---------- YOL B: KAYIT YOK -> ORB HOMOGRAFI ----------
        else:
            print(bas + '  KAYIT YOK -> ORB homografi araniyor...', flush=True)
            eniyi = None
            for oran in ('3X4', '2X3'):
                h = homografi_ara(POSTER[(ed, oran)], M8)
                if h is None:
                    print('        %s : homografi bulunamadi' % oran, flush=True)
                    continue
                print('        %s : inlier=%-5d fark=%6.3f  kutu=%s'
                      % (oran, h['inlier'], h['fark'], str(h['kutu'])), flush=True)
                if eniyi is None or h['fark'] < eniyi[1]['fark']:
                    eniyi = (oran, h)
            if eniyi is None:
                satirlar.append([ed, kod, 'ORB_BASARISIZ', '', '', '', '', '', ''])
                continue
            oran, h = eniyi
            satirlar.append([ed, kod, 'OLCULDU', str(h['kutu']), '',
                             oran + '/warp', round(h['fark'], 3),
                             str(h['koseler']), h['inlier']])
            print('        >> SECILEN: %s  fark=%.3f  koseler=%s'
                  % (oran, h['fark'], str(h['koseler'])), flush=True)

with open(OUT + '/SAHNE_OLCUM_V5.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['edisyon', 'sahne', 'kaynak', 'kutu', 'sahne_fark',
                'poster_oran_yontem', 'poster_fark', 'ofset_veya_koseler', 'ek'])
    w.writerows(satirlar)

print('\n' + '=' * 78, flush=True)
print('OZET', flush=True)
print('=' * 78, flush=True)
print('%-14s %-4s %-8s %-8s %-16s %-8s %-10s' %
      ('edisyon', 'sah', 'kaynak', 'sahne', 'poster', 'fark', 'ofset'), flush=True)
for s in satirlar:
    print('%-14s %-4s %-8s %-8s %-16s %-8s %-10s' %
          (s[0], s[1], s[2], s[4], s[5], s[6], str(s[7])[:10]), flush=True)

print('''
OKUMA:
  sahne  = poster disi alan farki. Gurultu tabani ~0.05.
           V3'te 06 icin MB 0.42 / DB 0.61 / PW 0.07 olculmustu.
           Diger sahneler de bu bantta ise recete tum sahnelerde gecerli.
  poster = kayitli kutuya yerlestirmenin farki
  ofset  = +0/+0 ise kayitli kutu DOGRU
  MB 11/12 satirlarinda kutu ve koseler ILK KEZ olculdu.
''', flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
