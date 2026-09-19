# =====================================================================
# WA_DESC_AUDIT_V2.py — 390 ACIKLAMA TAM DENETIMI  (SALT OKUR)
# Tetikleyen: MIDNIGHT_BLUE / VIRGO_VIRGO aciklamasinda "Virgo & Virgin".
#
# NE YAPAR: 390 canli ilanin aciklamasini TEK TEK ceker ve B39'da
#           kilitlenen DESCRIPTION V2 desenine karsi olcer.
#           Beklenen acilis:
#             "<Sign1> & <Sign2> — Original Zodiac Pair Symbol Wall Art,
#              <Edisyon> Edition"
#
# 5 KONTROL (listing basina):
#   1) ACILIS  : ilk satir beklenen desenle BIREBIR mi
#   2) CIFT    : acilistaki iki burc, basliktaki ciftle ayni mi
#   3) YABANCI : aciklamada o cifte AIT OLMAYAN burc adi var mi
#   4) ARKETIP : Virgin/Maiden/Ram/Bull/Twins/Crab/Lion/Scales/Scorpion/
#                Archer/Goat/Water Bearer/Fish gecio mu
#   5) SIZINTI : baska edisyonun adi gecio mu (B48 blok 2 kurali)
#
# HICBIR SEY YAZMAZ. PATCH YOK. Yalniz GET + yerel CSV.
# Kaynak: tek tek listing ID sorgusu (B37 ders 5 - active endpoint
#         cache gecikmelidir, dogrulama ID ile yapilir).
# Cagri: ~4 sayfalama + 390 tekil = ~394 (kota 5000/gun).
# Hiz  : 5 QPS limiti icin 0.22 sn bekleme -> ~4-6 dk.
# Resume destekli: CSV'de olan ilan tekrar cekilmez.
# V2 FARKI: obtained_at epoch DEGIL tarih metni olabiliyor (olculdu).
#           Yas hesabi kaldirildi, token her kosuda yenileniyor.
#           obtained_at geri yazilirken dosyadaki bicim korunuyor.
# Colab, tek hucre.
# =====================================================================
import os, sys, csv, json, time, re, unicodedata
from datetime import datetime
import requests

DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'
SHOP_ID    = 39729443
TOKEN_YOL  = os.path.join(DRIVE_ROOT, 'TEMP', 'ETSY_TOKEN.json')
CSV_YOL    = os.path.join(DRIVE_ROOT, 'TEMP', 'DESC_AUDIT_390.csv')
BEKLE      = 0.22          # 5 QPS
LIMIT      = None          # hizli deneme icin 20 yapabilirsin

BURCLAR = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra',
           'Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
EDISYONLAR = ['Champagne Ivory','Midnight Blue','Warm Parchment',
              'Deep Black','Pure White']
ARKETIP = ['Virgin','Maiden','Ram','Bull','Twins','Crab','Lion','Scales',
           'Scorpion','Archer','Goat','Water Bearer','Fish','Fishes',
           'Sea-Goat','Centaur','Balance','Bow']
SABLON = "{s1} & {s2} — Original Zodiac Pair Symbol Wall Art, {ed} Edition"

T0 = time.time()
def sure(sn):
    sn = int(max(0, sn))
    return f"{sn//3600}s {(sn%3600)//60:02d}d {sn%60:02d}sn" if sn >= 3600 \
           else f"{sn//60}d {sn%60:02d}sn"

try:
    from google.colab import drive
    if not os.path.ismount('/content/drive'): drive.mount('/content/drive')
except ImportError: pass
if not os.path.isfile(TOKEN_YOL): sys.exit(f"HATA: token yok: {TOKEN_YOL}")

# ------------------------------- TOKEN -------------------------------
tk = json.load(open(TOKEN_YOL, encoding='utf-8'))
for a in ('keystring','shared_secret','refresh_token','access_token'):
    if not tk.get(a): sys.exit(f"HATA: ETSY_TOKEN.json '{a}' alani bos")

# obtained_at bicim degisken olabilir (epoch float VEYA "YYYY-MM-DD HH:MM:SS").
# Yas hesabi yerine HER KOSUDA yenile: 1 cagri, belirsizlik yok.
_oa = tk.get('obtained_at')
_str_bicim = None
if isinstance(_oa, str):
    for _f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
               '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            datetime.strptime(_oa, _f); _str_bicim = _f; break
        except ValueError:
            continue
    if _str_bicim is None: _str_bicim = '%Y-%m-%d %H:%M:%S'

print("token yeniliyor...", flush=True)
rr = requests.post('https://api.etsy.com/v3/public/oauth/token',
                   data={'grant_type':'refresh_token',
                         'client_id': tk['keystring'],
                         'refresh_token': tk['refresh_token']}, timeout=60)
if rr.status_code != 200:
    sys.exit(f"HATA: token yenilenemedi {rr.status_code} {rr.text[:200]}")
y = rr.json()
tk['access_token']  = y['access_token']
tk['refresh_token'] = y.get('refresh_token', tk['refresh_token'])
tk['expires_in']    = y.get('expires_in', 3600)
# obtained_at: dosyada hangi bicimde ise AYNI bicimde geri yaz
tk['obtained_at'] = (datetime.now().strftime(_str_bicim) if _str_bicim
                     else time.time())
json.dump(tk, open(TOKEN_YOL,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"token yenilendi (obtained_at bicimi korundu: "
      f"{'metin' if _str_bicim else 'epoch'}).", flush=True)

BASLIK = {'x-api-key': f"{tk['keystring']}:{tk['shared_secret']}",
          'Authorization': f"Bearer {tk['access_token']}"}

def cek(url, par=None, deneme=3):
    for d in range(deneme):
        r = requests.get(url, headers=BASLIK, params=par, timeout=60)
        if r.status_code == 200: return r.json()
        if r.status_code == 429:
            sys.exit(f"DUR: 429 kota. retry-after={r.headers.get('retry-after')} "
                     f"(B61 dersi: bosuna deneme yapilmaz)")
        if d == deneme-1:
            raise RuntimeError(f"{r.status_code} {r.text[:200]}")
        time.sleep(1.5*(d+1))

# --------------------------- ILAN LISTESI ----------------------------
print("aktif ilanlar listeleniyor...", flush=True)
ILANLAR = []; ofs = 0
while True:
    y = cek(f'https://api.etsy.com/v3/application/shops/{SHOP_ID}/listings/active',
            {'limit':100, 'offset':ofs})
    par = y.get('results', [])
    ILANLAR += [(p['listing_id'], p.get('title','')) for p in par]
    if len(par) < 100: break
    ofs += 100; time.sleep(BEKLE)
print(f"aktif ilan: {len(ILANLAR)}  (beklenen 390)\n", flush=True)

# ------------------------------ OLCUM --------------------------------
def bosluk(s):
    s = unicodedata.normalize('NFKC', s or '')
    return re.sub(r'\s+', ' ', s).strip()

def gecen(kelimeler, metin):
    """metinde gecen kelimeleri (kelime siniri ile) sayar"""
    o = {}
    for k in kelimeler:
        n = len(re.findall(r'(?<![A-Za-z])' + re.escape(k) + r'(?![A-Za-z])',
                           metin, re.IGNORECASE))
        if n: o[k] = n
    return o

def sirali_burc(metin):
    """metinde gectikleri SIRAYA gore burc adlari"""
    b = []
    for m in re.finditer(r'(?<![A-Za-z])(' + '|'.join(BURCLAR) + r')(?![A-Za-z])',
                         metin, re.IGNORECASE):
        b.append((m.start(), m.group(1).capitalize()))
    return [x[1] for x in sorted(b)]

def olc(lid, baslik_metni):
    r = {'listing_id': lid}
    y = cek(f'https://api.etsy.com/v3/application/listings/{lid}')
    d = y.get('results') or y
    if isinstance(d, list): d = d[0]
    baslik = d.get('title') or baslik_metni or ''
    desc   = d.get('description') or ''
    r['baslik'] = baslik[:70]
    r['desc_uzunluk'] = len(desc)

    bulgu = []

    # --- baslikten beklenen cift + edisyon ---
    bb = sirali_burc(baslik)
    ed = next((e for e in EDISYONLAR if e.lower() in baslik.lower()), None)
    if len(bb) < 2: bulgu.append(f"BASLIK: burc adi {len(bb)} adet (2 bekleniyor)")
    if ed is None:  bulgu.append("BASLIK: edisyon adi yok")
    s1, s2 = (bb + ['?','?'])[:2]
    r['cift'] = f"{s1}_{s2}".upper()
    r['edisyon'] = ed or '?'

    ilk = next((x for x in (desc or '').splitlines() if x.strip()), '')
    r['acilis'] = bosluk(ilk)[:110]
    beklenen = SABLON.format(s1=s1, s2=s2, ed=ed) if (ed and '?' not in (s1,s2)) else ''
    r['beklenen'] = beklenen[:110]

    # 1) ACILIS birebir
    if beklenen:
        if bosluk(ilk) != bosluk(beklenen):
            # nedeni daralt
            g_cift = f"{s1} & {s2}"
            if g_cift.lower() not in bosluk(ilk).lower():
                bulgu.append("ACILIS: cift adi YANLIS")
            elif f"{ed} Edition".lower() not in bosluk(ilk).lower():
                bulgu.append("ACILIS: edisyon adi yanlis")
            else:
                bulgu.append("ACILIS: kalip sapmasi")

    # 2) CIFT capraz eslesme (acilistaki ilk iki burc)
    ab = sirali_burc(ilk)
    if len(ab) >= 2 and (ab[0], ab[1]) != (s1, s2):
        bulgu.append(f"CIFT: baslik {s1}&{s2} / acilis {ab[0]}&{ab[1]}")
    elif len(ab) < 2:
        bulgu.append(f"CIFT: aciliste {len(ab)} burc adi")

    # 3) YABANCI burc
    izin = {s1, s2}
    yab = {k: n for k, n in gecen(BURCLAR, desc).items() if k not in izin}
    if yab:
        bulgu.append("YABANCI BURC: " + ', '.join(f"{k}x{n}" for k, n in yab.items()))
    r['yabanci'] = ', '.join(f"{k}x{n}" for k, n in yab.items())

    # 4) ARKETIP kelime
    ark = gecen(ARKETIP, desc)
    if ark:
        bulgu.append("ARKETIP: " + ', '.join(f"{k}x{n}" for k, n in ark.items()))
    r['arketip'] = ', '.join(f"{k}x{n}" for k, n in ark.items())

    # 5) EDISYON sizintisi
    siz = [e for e in EDISYONLAR if e != ed and e.lower() in desc.lower()]
    if siz: bulgu.append("SIZINTI: " + ', '.join(siz))
    r['sizinti'] = ', '.join(siz)

    r['bulgular'] = ' | '.join(bulgu)
    r['bulgu_sayisi'] = len(bulgu)
    r['sonuc'] = 'TEMIZ' if not bulgu else 'HATA'
    return r

# ------------------------------- KOSU --------------------------------
SUTUN = ['listing_id','sonuc','bulgu_sayisi','edisyon','cift','bulgular',
         'acilis','beklenen','yabanci','arketip','sizinti','desc_uzunluk','baslik']
yapilan = {}
if os.path.exists(CSV_YOL):
    with open(CSV_YOL, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('sonuc'): yapilan[str(row['listing_id'])] = row
    print(f"RESUME: {len(yapilan)} ilan zaten olculmus, atlanacak.", flush=True)
else:
    with open(CSV_YOL,'w',newline='',encoding='utf-8') as f:
        csv.writer(f).writerow(SUTUN)

hedef = [(i,t) for i,t in ILANLAR if str(i) not in yapilan]
if LIMIT: hedef = hedef[:LIMIT]
N = len(hedef)
print(f"OLCULECEK: {N} ilan | SALT OKUR - hicbir sey degistirilmez")
print(f"CSV: {CSV_YOL}\n" + "-"*72, flush=True)

t0 = time.time(); satirlar = list(yapilan.values()); hata = 0
for i, (lid, bas) in enumerate(hedef, 1):
    try:
        r = olc(lid, bas)
        if r['sonuc'] == 'HATA': hata += 1
        ozet = f"{r['sonuc']:5s} | {r['edisyon']:16s} | {r['cift']:24s}"
        if r['bulgular']: ozet += f" | {r['bulgular'][:80]}"
    except Exception as e:
        r = {'listing_id': lid, 'sonuc':'CEKILEMEDI',
             'bulgular': f"{type(e).__name__}: {e}", 'bulgu_sayisi':0}
        hata += 1; ozet = f"CEKILEMEDI | {r['bulgular'][:70]}"
    satirlar.append(r)
    with open(CSV_YOL,'a',newline='',encoding='utf-8') as f:
        csv.DictWriter(f, fieldnames=SUTUN, extrasaction='ignore').writerow(r)
        f.flush(); os.fsync(f.fileno())
    gec = time.time()-t0; kal = (gec/i)*(N-i)
    if i <= 5 or i % 25 == 0 or r['sonuc'] != 'TEMIZ':
        print(f"{i}/{N} (%{100*i/N:5.1f}) | {ozet}")
        print(f"        gecen {sure(gec)} | kalan ~{sure(kal)}", flush=True)
    time.sleep(BEKLE)

# ------------------------------- OZET --------------------------------
def g(r,k,d=''): return (r.get(k) or d)
hatali = [r for r in satirlar if g(r,'sonuc') != 'TEMIZ']

print("\n" + "="*72)
print(f"BITTI: {len(satirlar)} ilan | TEMIZ {len(satirlar)-len(hatali)} | HATA {len(hatali)}")
print(f"Toplam sure {sure(time.time()-t0)}")

print("\n--- 1. EDISYON BASINA SAYIM (78 bekleniyor) ---")
sayim = {}
for r in satirlar: sayim[g(r,'edisyon','?')] = sayim.get(g(r,'edisyon','?'),0)+1
for e in EDISYONLAR + ['?']:
    if e in sayim: print(f"  {e:18s} {sayim[e]:3d}" + ("" if sayim[e]==78 else "   <-- 78 DEGIL"))

print("\n--- 2. BULGU TURUNE GORE DAGILIM ---")
tur = {}
for r in hatali:
    for b in g(r,'bulgular').split(' | '):
        if b: tur[b.split(':')[0]] = tur.get(b.split(':')[0],0)+1
for k,v in sorted(tur.items(), key=lambda x:-x[1]): print(f"  {k:16s} {v:3d} ilan")

print("\n--- 3. HATALI ILANLAR (tam liste) ---")
if not hatali: print("  YOK - 390 aciklama desene birebir uyuyor.")
for r in sorted(hatali, key=lambda r:(g(r,'edisyon'), g(r,'cift'))):
    print(f"  {g(r,'listing_id')} | {g(r,'edisyon'):16s} | {g(r,'cift'):24s}")
    print(f"      {g(r,'bulgular')}")
    if g(r,'acilis') and g(r,'acilis') != g(r,'beklenen'):
        print(f"      VAR    : {g(r,'acilis')}")
        print(f"      OLMALI : {g(r,'beklenen')}")

print("\n--- 4. AYNI BURC CIFTLERI (12 cift x 5 edisyon = 60 ilan) ---")
ayni = [r for r in satirlar
        if len(g(r,'cift').split('_'))==2 and g(r,'cift').split('_')[0]==g(r,'cift').split('_')[1]]
ah = [r for r in ayni if g(r,'sonuc')!='TEMIZ']
print(f"  toplam {len(ayni)} ilan | hatali {len(ah)}")
if ayni:
    oran_ayni = 100.0*len(ah)/len(ayni)
    digerleri = [r for r in satirlar if r not in ayni]
    dh = [r for r in digerleri if g(r,'sonuc')!='TEMIZ']
    oran_diger = 100.0*len(dh)/max(len(digerleri),1)
    print(f"  ayni burc hata orani  : %{oran_ayni:.1f}")
    print(f"  diger ciftler         : %{oran_diger:.1f}")
    print("  -> oranlar yakinsa hipotez CURUR, ayni burc ozel degil.")

print(f"\nCSV: {CSV_YOL}")
print("HICBIR ILAN DEGISTIRILMEDI. Duzeltme ayri onay ister.")
