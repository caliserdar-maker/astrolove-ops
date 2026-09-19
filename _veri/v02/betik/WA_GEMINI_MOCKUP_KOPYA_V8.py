# ==================================================================
# WA_GEMINI_MOCKUP_KOPYA_V8
#
# 18 GEMINI_GEMINI mockup'ini TEST klasorunden URETIM klasorune tasir.
#
# GUVENLIK KURALLARI (START_HERE'den):
#   - Drive dosya ID'leri KORUNUR (files().update, yerinde guncelleme).
#     Yeni dosya olusturulmaz, yinelenen olusmaz.
#   - Once YEDEK alinir (server-side kopya, TEMP/GEMINI_YEDEK3_MOCKUP).
#   - Yazma sonrasi GERI OKUMA + SHA-256 karsilastirmasi yapilir.
#     "Upload istegi OK" PASS demek DEGILDIR (B43 dersi).
#   - Idempotent: dogrulanmis dosya tekrar kosuda ATLANIR.
#   - Klasor onek eslesmesi daima alt cizgiyle ("06_"), yalin "06" ASLA (B43).
#
# KAYNAK : TEMP/GEMINI_MOCKUP_V6/<EDISYON>/WA_XX_MOCKUP_GEMINI_GEMINI_<ED>.jpg
# HEDEF  : MOCKUPS/<sahne>/<EDISYON>/ ayni adli mevcut dosya
#
# CIKTI  : TEMP/GEMINI_KOPYA_V8_LOG.csv
# ==================================================================

import os, io, csv, time, hashlib
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

ROOT_ID   = '1XFyBXuRdu6K564YvaB6ZvskvA85asMWP'
MOCKUP_ID = '1cVsAfVh1wzxURUSQ8gBWDlpWL1cxL---'
TEMP_ID   = '12N9iS2i4byMbkH5c0Inmni_nIv2zyTzH'
KAYNAK    = '/content/drive/MyDrive/ASTROLOVE/TEMP/GEMINI_MOCKUP_V6'
LOG       = '/content/drive/MyDrive/ASTROLOVE/TEMP/GEMINI_KOPYA_V8_LOG.csv'
YEDEK_AD  = 'GEMINI_YEDEK3_MOCKUP'
PAIR      = 'GEMINI_GEMINI'

EDISYONLAR = ['MIDNIGHT_BLUE', 'DEEP_BLACK', 'PURE_WHITE']
SAHNELER   = ['03', '06', '08', '10', '11', '12']

svc = build('drive', 'v3')


def sure(sn):
    sn = int(sn)
    return '%02d:%02d' % (sn // 60, sn % 60)


def cocuklar(ust):
    """Bir klasorun tum cocuklari. LISTE dondurur (kopya-farkindali, B56)."""
    r, tok = [], None
    while True:
        s = svc.files().list(q="'%s' in parents and trashed=false" % ust,
                             fields='nextPageToken,files(id,name,mimeType,size)',
                             pageSize=1000, pageToken=tok).execute()
        r += s.get('files', [])
        tok = s.get('nextPageToken')
        if not tok:
            break
    return r


def klasor_bul(ust, onek):
    a = [f for f in cocuklar(ust)
         if f['mimeType'] == 'application/vnd.google-apps.folder' and f['name'].startswith(onek)]
    if len(a) != 1:
        raise IOError('klasor belirsiz: onek=%s bulunan=%d' % (onek, len(a)))
    return a[0]


def dosya_bul(ust, ad):
    a = [f for f in cocuklar(ust) if f['name'] == ad]
    if len(a) == 0:
        raise IOError('dosya yok: ' + ad)
    if len(a) > 1:
        raise IOError('YINELENEN dosya: %s (%d adet)' % (ad, len(a)))
    return a[0]


def sha_yerel(yol):
    h = hashlib.sha256()
    with open(yol, 'rb') as f:
        for p in iter(lambda: f.read(1 << 20), b''):
            h.update(p)
    return h.hexdigest()


def sha_uzak(fid):
    b = io.BytesIO()
    dl = MediaIoBaseDownload(b, svc.files().get_media(fileId=fid))
    bitti = False
    while not bitti:
        _, bitti = dl.next_chunk()
    return hashlib.sha256(b.getvalue()).hexdigest(), len(b.getvalue())


# ---------------- ON KONTROL ----------------
print('=' * 70, flush=True)
print('ON KONTROL', flush=True)
print('=' * 70, flush=True)

isler, eksik = [], []
for ed in EDISYONLAR:
    for kod in SAHNELER:
        ad = 'WA_%s_MOCKUP_%s_%s.jpg' % (kod, PAIR, ed)
        yerel = '%s/%s/%s' % (KAYNAK, ed, ad)
        if not os.path.exists(yerel) or os.path.getsize(yerel) == 0:
            eksik.append(yerel)
        else:
            isler.append((ed, kod, ad, yerel))
print('kaynak dosya: %d/18 hazir' % len(isler), flush=True)
if eksik:
    for e in eksik:
        print('  EKSIK: ' + e, flush=True)
    raise SystemExit('DURDU - once V7 kosulmali')

# yedek klasoru (varsa yeniden olusturma - B56 kopya dersi)
mevcut = [f for f in cocuklar(TEMP_ID)
          if f['name'] == YEDEK_AD and f['mimeType'] == 'application/vnd.google-apps.folder']
if mevcut:
    YEDEK_ID = mevcut[0]['id']
    print('yedek klasoru mevcut: %s' % YEDEK_ID, flush=True)
else:
    YEDEK_ID = svc.files().create(
        body={'name': YEDEK_AD, 'mimeType': 'application/vnd.google-apps.folder',
              'parents': [TEMP_ID]}, fields='id').execute()['id']
    print('yedek klasoru olusturuldu: %s' % YEDEK_ID, flush=True)

# daha once dogrulananlar
bitmis = set()
if os.path.exists(LOG):
    with open(LOG) as f:
        for s in csv.DictReader(f):
            if s.get('durum') == 'PASS':
                bitmis.add((s['edisyon'], s['sahne']))
    print('onceki kosudan dogrulanmis: %d' % len(bitmis), flush=True)

# hedef dosyalari coz
print('\nhedef dosyalar araniyor...', flush=True)
hedefler = {}
sahne_klasor = {}
for kod in SAHNELER:
    sahne_klasor[kod] = klasor_bul(MOCKUP_ID, kod + '_')
    print('  %s -> %s' % (kod, sahne_klasor[kod]['name']), flush=True)

for ed, kod, ad, yerel in isler:
    ek = klasor_bul(sahne_klasor[kod]['id'], ed)
    hedefler[(ed, kod)] = dosya_bul(ek['id'], ad)

print('  18/18 hedef dosya bulundu, hepsi tekil\n', flush=True)

# ---------------- KOPYALAMA ----------------
print('=' * 70, flush=True)
print('YEDEK -> GUNCELLE -> GERI OKU -> SHA-256', flush=True)
print('=' * 70, flush=True)

satirlar = []
t0 = time.time()
N = len(isler)
PASS = FAIL = ATLA = 0

for i, (ed, kod, ad, yerel) in enumerate(isler, 1):
    gec = time.time() - t0
    kalan = (gec / max(i - 1, 1)) * (N - i + 1) if i > 1 else 0
    bs = '[%d/%d] %-14s %s' % (i, N, ed, kod)

    if (ed, kod) in bitmis:
        print(bs + '  ATLA (onceki kosuda dogrulandi)', flush=True)
        ATLA += 1
        continue

    h = hedefler[(ed, kod)]
    try:
        # 1) yedek (server-side kopya)
        yad = '%s__%s__%s' % (ed, kod, ad)
        var = [f for f in cocuklar(YEDEK_ID) if f['name'] == yad]
        if not var:
            svc.files().copy(fileId=h['id'],
                             body={'name': yad, 'parents': [YEDEK_ID]},
                             fields='id').execute()

        # 2) yerinde guncelle - ID KORUNUR
        svc.files().update(fileId=h['id'],
                           media_body=MediaFileUpload(yerel, mimetype='image/jpeg',
                                                      resumable=True),
                           fields='id,name,size').execute()

        # 3) geri oku + SHA-256
        ys = sha_yerel(yerel)
        us, ubayt = sha_uzak(h['id'])
        ybayt = os.path.getsize(yerel)
        ok = (ys == us) and (ybayt == ubayt)

        satirlar.append([ed, kod, 'PASS' if ok else 'FAIL_SHA', h['id'],
                         ybayt, ubayt, ys[:16], us[:16]])
        if ok:
            PASS += 1
            print(bs + '  PASS  ID korundu %s  %.2f MB  SHA eslesti  | gecen %s kalan ~%s'
                  % (h['id'], ybayt / 1048576.0, sure(gec), sure(kalan)), flush=True)
        else:
            FAIL += 1
            print(bs + '  FAIL SHA  yerel=%d uzak=%d' % (ybayt, ubayt), flush=True)

    except Exception as e:
        FAIL += 1
        satirlar.append([ed, kod, 'FAIL', h.get('id', ''), '', '', str(e)[:60], ''])
        print(bs + '  FAIL: %s' % str(e)[:80], flush=True)

    # her adimda log yaz (kosu kesilirse kaldigi yerden devam)
    with open(LOG, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['edisyon', 'sahne', 'durum', 'drive_id',
                    'yerel_bayt', 'uzak_bayt', 'yerel_sha', 'uzak_sha'])
        w.writerows(satirlar)

# ---------------- SON DOGRULAMA ----------------
print('\n' + '=' * 70, flush=True)
print('SON GERI OKUMA (klasor sayimi + yinelenen kontrolu)', flush=True)
print('=' * 70, flush=True)

for kod in SAHNELER:
    for ed in EDISYONLAR:
        ek = klasor_bul(sahne_klasor[kod]['id'], ed)
        cs = [f for f in cocuklar(ek['id']) if f['mimeType'] != 'application/vnd.google-apps.folder']
        adlar = [f['name'] for f in cs]
        yinelenen = len(adlar) != len(set(adlar))
        hedef_ad = 'WA_%s_MOCKUP_%s_%s.jpg' % (kod, PAIR, ed)
        kac = adlar.count(hedef_ad)
        durum = 'OK' if (kac == 1 and not yinelenen) else 'DIKKAT'
        print('  %s %s/%-14s dosya=%-4d GEMINI=%d yinelenen=%s  %s'
              % ('' if durum == 'OK' else '!!', kod, ed, len(cs), kac,
                 'VAR' if yinelenen else 'yok', durum), flush=True)

print('\n' + '=' * 70, flush=True)
print('SONUC: PASS %d / FAIL %d / ATLA %d / toplam %d' % (PASS, FAIL, ATLA, N), flush=True)
print('=' * 70, flush=True)
print('''
Yedekler : TEMP/%s
Log      : TEMP/GEMINI_KOPYA_V8_LOG.csv

Bu adimda YALNIZ MOCKUPS klasoru guncellendi.
ETSY_UPLOAD_SETS ve Etsy ilanlari HENUZ DOKUNULMADI - ayri adim, ayri onay.
''' % YEDEK_AD, flush=True)
print('BITTI - toplam %s' % sure(time.time() - t0), flush=True)
