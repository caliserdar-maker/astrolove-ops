# ==================================================================
# WA_GEMINI_SAHNE_OLCUM_V4  -  SALT OLCUM (hicbir sey uretmez)
#
# AMAC: 3 edisyon x 6 sahne = 18 mockup icin
#       (a) sahne recetesini dogrula
#       (b) poster kutusunu OLCEREK bul
#       (c) kayitli kutuyla karsilastir
#       (d) en iyi poster yerlesimini bul
#
# KUTU NASIL BULUNUYOR (tahmin degil):
#   islenmis sahne masteri ile mevcut mockup'in farki alinir.
#   Sahne masterinde yer tutucu poster, mockup'ta GEMINI posteri var.
#   Farkin ciktigi bolge = poster alani. Otsu esigi + en buyuk bilesen.
#   Bu yontem MB 11/12'nin kayitsiz koordinatlarini da verir.
#
# KAZANAN SAHNE RECETELERI (V3 taramasindan, olculmus):
#   MB : lanczos + %8 pozlama + gama 0.94 + netlik 45/1.8   (0.418)
#   DB : lanczos, islem YOK                                  (0.605)
#   PW : islem YOK, master zaten 3000                        (0.072)
#
# CIKTI: TEMP/GEMINI_TEST_V1/SAHNE_OLCUM_V4.csv + KUTU_*.png
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

# ------------------------------------------------------------------
# ESKI POSTERLER (TEMP/GEMINI_YEDEK icinden, dosya ID ile)
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# KAYITLI KUTULAR  (None = kayit yok, olculecek)
#   MB : B40, 1448 olcek  -> 3000'e cevrilir
#   DB : B47, 3000 olcek
#   PW : B54 quad'larinin sinir kutusu, 3000 olcek
# ------------------------------------------------------------------
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

# V3'te olculen kazanan sahne receteleri
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


def kutu_olc(sahne_arr, mock_arr):
    """islenmis sahne ile mockup farkindan poster alanini bulur."""
    d = np.abs(sahne_arr - mock_arr).mean(axis=2)
    d8 = np.clip(d, 0, 255).astype(np.uint8)
    _, mask = cv2.threshold(d8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, alan = st[i]
    bilesen = (lab == i).astype(np.uint8) * 255
    cnt, _ = cv2.findContours(bilesen, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rect = cv2.minAreaRect(max(cnt, key=cv2.contourArea))
    aci = rect[2]
    if aci > 45:
        aci -= 90
    return dict(kutu=(int(x), int(y), int(x + w), int(y + h)),
                alan=int(alan), doluluk=float(alan) / (w * h),
                aci=float(aci), koseler=cv2.boxPoints(rect).tolist())


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

        sd = sorted(glob.glob(MOCK + '/' + kod + '_*'))
        if not sd:
            print('[%d/%d] %s %s  SAHNE KLASORU YOK' % (say, TOP, ed, kod), flush=True)
            continue
        SD = sd[0]
        mas = sorted(glob.glob(SD + '/00_MASTER/WA_' + kod + '_SCENE_MASTER_' + ed + '.*'))
        mev = sorted(glob.glob(SD + '/' + ed + '/WA_' + kod + '_MOCKUP_' + PAIR + '_' + ed + '.*'))
        if not mas or not mev:
            print('[%d/%d] %-14s %s  EKSIK  master=%d mockup=%d'
                  % (say, TOP, ed, kod, len(mas), len(mev)), flush=True)
            satirlar.append([ed, kod, 'EKSIK', '', '', '', '', '', '', '', ''])
            continue

        sahne = sahne_uret(mas[0], r)
        S = np.asarray(sahne, np.float32)
        M = np.asarray(Image.open(mev[0]).convert('RGB'), np.float32)
        if S.shape != M.shape:
            print('[%d/%d] %-14s %s  OLCU FARKLI %s vs %s'
                  % (say, TOP, ed, kod, S.shape, M.shape), flush=True)
            continue

        olcum = kutu_olc(S, M)
        if olcum is None:
            print('[%d/%d] %-14s %s  KUTU BULUNAMADI' % (say, TOP, ed, kod), flush=True)
            continue
        OL, OT, OR_, OB = olcum['kutu']
        KW, KH = OR_ - OL, OB - OT

        # kayitli kutu
        kay = KAYIT[ed][kod]
        if kay is None:
            kay_txt, sapma = 'KAYIT YOK', ''
        else:
            if ed == 'MIDNIGHT_BLUE':
                kay = tuple(int(round(v * MB_OLCEK)) for v in kay)
            sapma = max(abs(a - b) for a, b in zip(kay, olcum['kutu']))
            kay_txt = str(kay)

        # sahne uyumu (poster disi)
        dis = np.ones(M.shape[:2], bool)
        dis[OT:OB, OL:OR_] = False
        sahne_fark = float(np.abs(S - M).mean(axis=2)[dis].mean())

        # poster yerlesimi: 2 oran x 3 yontem
        hedef = M[OT:OB, OL:OR_]
        en = (1e9, '', '')
        for oran in ('3X4', '2X3'):
            pos = Image.open(POSTER[(ed, oran)]).convert('RGB')
            for tur in ('esnet', 'esnet_bicubic', 'contain'):
                y = np.asarray(yama_uret(pos, KW, KH, tur), np.float32)
                sk = float(np.abs(y - hedef).mean())
                if sk < en[0]:
                    en = (sk, oran, tur)
        p_fark, p_oran, p_tur = en

        satirlar.append([ed, kod, str(olcum['kutu']), '%dx%d' % (KW, KH),
                         kay_txt, sapma, round(olcum['doluluk'], 3),
                         round(olcum['aci'], 2), round(sahne_fark, 3),
                         p_oran + '/' + p_tur, round(p_fark, 3)])

        print('[%d/%d] %-14s %s  kutu=%-26s %dx%d  kayit_sapma=%-4s doluluk=%.2f aci=%+.1f  sahne=%5.2f  poster=%s/%s %5.2f  | gecen %s kalan ~%s'
              % (say, TOP, ed, kod, str(olcum['kutu']), KW, KH, str(sapma),
                 olcum['doluluk'], olcum['aci'], sahne_fark, p_oran, p_tur, p_fark,
                 sure(gec), sure(kalan)), flush=True)

with open(OUT + '/SAHNE_OLCUM_V4.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['edisyon', 'sahne', 'olculen_kutu', 'olcu', 'kayitli_kutu',
                'kayit_sapma_px', 'doluluk', 'aci', 'sahne_fark',
                'poster_oran_yontem', 'poster_fark'])
    w.writerows(satirlar)

print('\n' + '=' * 78, flush=True)
print('OZET', flush=True)
print('=' * 78, flush=True)
print('%-14s %-4s %-6s %-9s %-8s %-8s %-14s %-7s' %
      ('edisyon', 'sah', 'sapma', 'doluluk', 'aci', 'sahne', 'poster', 'fark'), flush=True)
for s in satirlar:
    if s[2] == 'EKSIK':
        print('%-14s %-4s  EKSIK DOSYA' % (s[0], s[1]), flush=True)
    else:
        print('%-14s %-4s %-6s %-9s %-8s %-8s %-14s %-7s' %
              (s[0], s[1], s[5], s[6], s[7], s[8], s[9], s[10]), flush=True)

print('''
OKUMA:
  sapma   = olculen kutu ile START_HERE kaydinin px farki
            0-3 px  -> kayit dogru
            buyukse -> kayit yanlis, OLCULEN kutu kullanilir
  doluluk = 1.00 duz dikdortgen; dusukse egik/perspektif
  aci     = 0 duz; sifir degilse perspektif warp gerekir
  sahne   = poster disi alan farki (gurultu tabani ~0.05)
  poster  = en iyi oran/yontem ve farki

  MB 11 ve MB 12'de kayit yoktu; olculen kutu tek kaynaktir.
''', flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
