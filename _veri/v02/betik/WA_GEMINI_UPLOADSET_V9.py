# ==================================================================
# WA_GEMINI_UPLOADSET_V9
#
# ETSY_UPLOAD_SETS icindeki GEMINI_GEMINI kopyalarini kanonik
# kaynakla (MOCKUPS / TECHNICAL) esitler.
#
# VARSAYIM YOK:
#   - Hangi dosyanin degistigi MD5 KARSILASTIRMASIYLA bulunur.
#     (Drive md5Checksum alani; indirme gerekmez.)
#     Ayni olanlar ATLANIR, yalniz farkli olanlar guncellenir.
#   - Klasor yapisi OKUNUR, varsayilmaz. MB/PW cift klasorlu,
#     DB duz yapi (B58). Script ikisini de destekler.
#   - Onek-sahne eslesmesi dosya ADINDAN cozulur, galeri sirasi
#     tablosundan DEGIL. (B67 dersi: kilitli kural okunmadan
#     parametre tahmin edilmez.)
#
# GUVENLIK:
#   - Once yedek (server-side kopya, TEMP/GEMINI_YEDEK4_UPLOADSET)
#   - Yerinde guncelleme, Drive ID KORUNUR
#   - Yazma sonrasi md5 geri okuma dogrulamasi
#   - Idempotent: tekrar kosarsa "DEGISIM YOK" der
#
# CIKTI: TEMP/GEMINI_UPLOADSET_V9_LOG.csv
# ==================================================================

import os, csv, time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

UPLOADSET_ID = '1YweYO_5tpS_sviE4gqHfbuaw6gyhELtT'
MOCKUP_ID    = '1cVsAfVh1wzxURUSQ8gBWDlpWL1cxL---'
TECH_ID      = '1f0qHc_OWrxlM__laZffBkbQe_THHpQ6P'
TEMP_ID      = '12N9iS2i4byMbkH5c0Inmni_nIv2zyTzH'
MNT          = '/content/drive/MyDrive/ASTROLOVE'
LOG          = MNT + '/TEMP/GEMINI_UPLOADSET_V9_LOG.csv'
YEDEK_AD     = 'GEMINI_YEDEK4_UPLOADSET'
PAIR         = 'GEMINI_GEMINI'

EDISYON_ID = {
    'MIDNIGHT_BLUE': '1AODuYtRvI5hg3i6EdWqQvPj_WCkxNQgP',
    'DEEP_BLACK':    '1pKIZ5tbkc8NjGnCCPHNqv_uWykuVJg79',
    'PURE_WHITE':    '1E3PEAhppMwCjZ-77s578dvAZ9acEsNUI',
}
EDISYONLAR = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE']
LIFESTYLE = {'03', '06', '08', '10', '11', '12'}

svc = build('drive', 'v3')
KLASOR = 'application/vnd.google-apps.folder'


def sure(sn):
    sn = int(sn)
    return '%02d:%02d' % (sn // 60, sn % 60)


def cocuklar(ust):
    r, tok = [], None
    while True:
        s = svc.files().list(q="'%s' in parents and trashed=false" % ust,
                             fields='nextPageToken,files(id,name,mimeType,size,md5Checksum)',
                             pageSize=1000, pageToken=tok).execute()
        r += s.get('files', [])
        tok = s.get('nextPageToken')
        if not tok:
            break
    return r


def klasor_bul(ust, onek):
    a = [f for f in cocuklar(ust) if f['mimeType'] == KLASOR and f['name'].startswith(onek)]
    if len(a) != 1:
        raise IOError('klasor belirsiz: %s (%d)' % (onek, len(a)))
    return a[0]


def sahne_kodu(ad):
    """Dosya adindan sahne kodunu cozer. Ornek:
       '01_WA_06_MOCKUP_GEMINI_GEMINI_PURE_WHITE.jpg' -> '06' """
    p = ad.split('_')
    for i, t in enumerate(p):
        if t == 'WA' and i + 1 < len(p) and p[i + 1].isdigit():
            return p[i + 1].zfill(2)
    return None


# ---------------- 1) KESIF ----------------
print('=' * 74, flush=True)
print('1) KESIF - upload set yapisi okunuyor', flush=True)
print('=' * 74, flush=True)

HEDEF = {}          # (ed, kod) -> dosya kaydi
for ed in EDISYONLAR:
    kokler = cocuklar(EDISYON_ID[ed])
    ciftk = [f for f in kokler if f['mimeType'] == KLASOR and f['name'] == PAIR]
    if ciftk:
        yapi = 'cift klasorlu'
        dosyalar = [f for f in cocuklar(ciftk[0]['id']) if f['mimeType'] != KLASOR]
    else:
        yapi = 'duz yapi'
        dosyalar = [f for f in kokler if f['mimeType'] != KLASOR and PAIR in f['name']]

    print('\n[%s]  %s  -  %d GEMINI dosyasi' % (ed, yapi, len(dosyalar)), flush=True)
    for f in sorted(dosyalar, key=lambda x: x['name']):
        kod = sahne_kodu(f['name'])
        if kod is None:
            print('   ! sahne kodu cozulemedi: %s' % f['name'], flush=True)
            continue
        if (ed, kod) in HEDEF:
            print('   ! YINELENEN sahne %s: %s' % (kod, f['name']), flush=True)
            continue
        HEDEF[(ed, kod)] = f
        print('   %s -> sahne %s   %s' % (f['name'][:3], kod, f['name'][3:][:52]), flush=True)

print('\ntoplam hedef: %d (beklenen 36)' % len(HEDEF), flush=True)

# ---------------- 2) KANONIK KAYNAK + MD5 KARSILASTIRMA ----------------
print('\n' + '=' * 74, flush=True)
print('2) KAYNAK BULMA + MD5 KARSILASTIRMA', flush=True)
print('=' * 74, flush=True)

sahne_klasor, tech_klasor = {}, {}
isler = []
for (ed, kod), hf in sorted(HEDEF.items()):
    try:
        if kod in LIFESTYLE:
            if kod not in sahne_klasor:
                sahne_klasor[kod] = klasor_bul(MOCKUP_ID, kod + '_')
            ust = klasor_bul(sahne_klasor[kod]['id'], ed)
            onek = 'WA_%s_MOCKUP_' % kod
            kok = MNT + '/WALL_ART/LISTING_MEDIA/MOCKUPS/%s/%s/' % (sahne_klasor[kod]['name'], ed)
        else:
            if kod not in tech_klasor:
                tech_klasor[kod] = klasor_bul(TECH_ID, kod + '_')
            ust = klasor_bul(tech_klasor[kod]['id'], ed)
            onek = 'WA_%s_TECH_' % kod
            kok = MNT + '/WALL_ART/LISTING_MEDIA/TECHNICAL/%s/%s/' % (tech_klasor[kod]['name'], ed)

        aday = [f for f in cocuklar(ust['id'])
                if f['mimeType'] != KLASOR and f['name'].startswith(onek) and PAIR in f['name']]
        if len(aday) != 1:
            raise IOError('kaynak belirsiz (%d adet)' % len(aday))
        kf = aday[0]
        yerel = kok + kf['name']
        ayni = (kf.get('md5Checksum') and kf.get('md5Checksum') == hf.get('md5Checksum'))
        isler.append(dict(ed=ed, kod=kod, hedef=hf, kaynak=kf, yerel=yerel, ayni=ayni))
    except Exception as e:
        print('  ! %s %s  KAYNAK YOK: %s' % (ed, kod, str(e)[:50]), flush=True)
        isler.append(dict(ed=ed, kod=kod, hedef=hf, kaynak=None, yerel=None, ayni=None))

fark = [i for i in isler if i['ayni'] is False]
ayni = [i for i in isler if i['ayni'] is True]
hata = [i for i in isler if i['ayni'] is None]

print('\n  ayni (atlanacak) : %d' % len(ayni), flush=True)
print('  FARKLI (guncelle): %d' % len(fark), flush=True)
print('  kaynak yok       : %d' % len(hata), flush=True)
if fark:
    print('\n  guncellenecekler:', flush=True)
    for i in fark:
        print('    %-14s %s  %s' % (i['ed'], i['kod'], i['kaynak']['name'][:56]), flush=True)

if not fark:
    print('\nDEGISIM YOK - upload set zaten guncel. Islem yapilmadi.', flush=True)
    raise SystemExit(0)

# ---------------- 3) YEDEK + GUNCELLE + DOGRULA ----------------
print('\n' + '=' * 74, flush=True)
print('3) YEDEK -> GUNCELLE -> MD5 GERI OKUMA', flush=True)
print('=' * 74, flush=True)

mev = [f for f in cocuklar(TEMP_ID) if f['name'] == YEDEK_AD and f['mimeType'] == KLASOR]
if mev:
    YEDEK_ID = mev[0]['id']
else:
    YEDEK_ID = svc.files().create(
        body={'name': YEDEK_AD, 'mimeType': KLASOR, 'parents': [TEMP_ID]},
        fields='id').execute()['id']
print('yedek klasoru: %s\n' % YEDEK_ID, flush=True)

satirlar = []
t0 = time.time()
N = len(fark)
PASS = FAIL = 0

for i, it in enumerate(fark, 1):
    gec = time.time() - t0
    kalan = (gec / max(i - 1, 1)) * (N - i + 1) if i > 1 else 0
    bs = '[%d/%d] %-14s %s' % (i, N, it['ed'], it['kod'])
    hf, kf = it['hedef'], it['kaynak']

    try:
        if not os.path.exists(it['yerel']):
            raise IOError('mount yolu yok: ' + it['yerel'])

        yad = '%s__%s' % (it['ed'], hf['name'])
        if not [f for f in cocuklar(YEDEK_ID) if f['name'] == yad]:
            svc.files().copy(fileId=hf['id'], body={'name': yad, 'parents': [YEDEK_ID]},
                             fields='id').execute()

        mt = 'image/png' if hf['name'].lower().endswith('.png') else 'image/jpeg'
        svc.files().update(fileId=hf['id'],
                           media_body=MediaFileUpload(it['yerel'], mimetype=mt, resumable=True),
                           fields='id').execute()

        yeni = svc.files().get(fileId=hf['id'], fields='id,name,size,md5Checksum').execute()
        ok = yeni.get('md5Checksum') == kf.get('md5Checksum')
        satirlar.append([it['ed'], it['kod'], 'PASS' if ok else 'FAIL_MD5', hf['id'],
                         hf['name'], kf['name'], yeni.get('size'), yeni.get('md5Checksum')])
        if ok:
            PASS += 1
            print(bs + '  PASS  ID korundu %s  %.2f MB  md5 eslesti  | gecen %s kalan ~%s'
                  % (hf['id'], int(yeni.get('size', 0)) / 1048576.0, sure(gec), sure(kalan)), flush=True)
        else:
            FAIL += 1
            print(bs + '  FAIL md5  hedef=%s kaynak=%s'
                  % (yeni.get('md5Checksum'), kf.get('md5Checksum')), flush=True)
    except Exception as e:
        FAIL += 1
        satirlar.append([it['ed'], it['kod'], 'FAIL', hf['id'], hf['name'], '', '', str(e)[:50]])
        print(bs + '  FAIL: %s' % str(e)[:70], flush=True)

    with open(LOG, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['edisyon', 'sahne', 'durum', 'drive_id', 'hedef_ad',
                    'kaynak_ad', 'bayt', 'md5'])
        w.writerows(satirlar)

# ---------------- 4) SON GERI OKUMA ----------------
print('\n' + '=' * 74, flush=True)
print('4) SON GERI OKUMA - sayim + yinelenen', flush=True)
print('=' * 74, flush=True)

for ed in EDISYONLAR:
    kokler = cocuklar(EDISYON_ID[ed])
    ciftk = [f for f in kokler if f['mimeType'] == KLASOR and f['name'] == PAIR]
    if ciftk:
        ds = [f for f in cocuklar(ciftk[0]['id']) if f['mimeType'] != KLASOR]
    else:
        ds = [f for f in kokler if f['mimeType'] != KLASOR and PAIR in f['name']]
    adlar = [f['name'] for f in ds]
    yin = len(adlar) != len(set(adlar))
    print('  %-14s GEMINI dosyasi=%-3d yinelenen=%s  %s'
          % (ed, len(ds), 'VAR' if yin else 'yok',
             'OK' if (len(ds) == 12 and not yin) else 'DIKKAT'), flush=True)

print('\n' + '=' * 74, flush=True)
print('SONUC: PASS %d / FAIL %d / atlanan(ayni) %d' % (PASS, FAIL, len(ayni)), flush=True)
print('=' * 74, flush=True)
print('''
Yedekler : TEMP/%s
Log      : TEMP/GEMINI_UPLOADSET_V9_LOG.csv

Bu adimda YALNIZ ETSY_UPLOAD_SETS guncellendi.
Etsy ilanlari ve PW videolari HENUZ DOKUNULMADI - ayri adim, ayri onay.
''' % YEDEK_AD, flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
