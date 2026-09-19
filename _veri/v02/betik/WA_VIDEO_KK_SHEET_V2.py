# =====================================================================
# WA_VIDEO_KK_SHEET_V2.py — 78 VIDEO KK SAYFALARI (Claude incelemesi icin)
# (SALT OKUR — video, klasor, ilan DEGISMEZ. Etsy API'ye DOKUNMAZ.)
#
# V1 FARKI: V1 tablet icin kucuk/cok satirliydi (13 cift/sayfa, 300 px).
#           V2 Claude'un goruntuleyecegi olcude: 6 cift/sayfa,
#           ve EN ONEMLISI 45. karenin GLIF BANDI 1:1 (orijinal piksel,
#           kucultme YOK) ayri sutun olarak eklendi. Kalinti ancak
#           orada gorunur. Kucultulmus goruntude kalinti kaybolur.
#
# SUTUNLAR:
#   1) kare 0    tam kare  - poster tam mi
#   2) kare 45   tam kare  - akis ortasi, genel gorunum
#   3) kare 45   GLIF BANDI 1:1 - KALINTI KONTROLU (asil sutun)
#   4) kare 137  tam kare  - 0 ile ayni olmali (dongu dikisi)
#
# GLIF BANDI: kare yuksekliginin %50-72'si, genisligin %18-82'si.
#   Turetme: ZOOM60'ta poster yuksekligi tuvalin %60'i (ortalanmis)
#   -> poster kabaca kare y %20-80 arasinda. Glifler poster
#   yuksekliginin %60-72'sinde (B63 FR_CAN/FR_LIB kutulari).
#   -> kare y %56-63. Pay birakildi: %50-72.
#   Bu GENIS bir kirpimdir, kutu olcumu gerektirmez (hiz icin).
#
# Cikti: TEMP/KK_PURE_WHITE_V2/KK_S01..S13.png  (13 sayfa, 6 cift)
# Resume: var olan sayfa atlanir (YENIDEN=True ile bastan uret).
# Colab, tek hucre. Sure ~5 dk.
# =====================================================================
import os, sys, glob, time, subprocess, shutil
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None

# ------------------------------------------------------------- AYAR
DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'
EDITION    = 'PURE_WHITE'
SATIR_SAYFA= 6
TAM_EN     = 180           # tam kare sutun genisligi (kucuk, sadece genel bakis)
BANT_EN    = 691           # glif bandi 1:1 (kaynak kirpim tam bu genislikte)
BANT_Y     = (0.50, 0.72)  # kare yuksekliginde glif bandi
BANT_X     = (0.18, 0.82)
YENIDEN    = False
LIMIT      = None
# -------------------------------------------------------------------

KARELER = [0, 45, 137]
T0 = time.time()
def sure(sn):
    sn = int(max(0, sn)); return f"{sn//60}d {sn%60:02d}sn"

try:
    from google.colab import drive
    if not os.path.ismount('/content/drive'): drive.mount('/content/drive')
except ImportError: pass
if not shutil.which('ffmpeg'): sys.exit("HATA: ffmpeg yok")

VID_DIR = os.path.join(DRIVE_ROOT,'WALL_ART','LISTING_MEDIA','VIDEOS',
                       'V01_FIREFLY_STORY','01_EXPORTS',EDITION)
if not os.path.isdir(VID_DIR): sys.exit(f"HATA: video klasoru yok:\n  {VID_DIR}")
OUT_DIR = os.path.join(DRIVE_ROOT,'TEMP',f'KK_{EDITION}_V2')
os.makedirs(OUT_DIR, exist_ok=True)

VIDEOLAR = sorted(glob.glob(os.path.join(VID_DIR,'*.mp4')))
VIDEOLAR = [v for v in VIDEOLAR if '_HIZ_TEST' not in os.path.basename(v)]
if LIMIT: VIDEOLAR = VIDEOLAR[:LIMIT]
print(f"video bulundu: {len(VIDEOLAR)}  (beklenen 78)")
if not VIDEOLAR: sys.exit("HATA: mp4 yok")

def cift_adi(y):
    return os.path.basename(y).replace('WA_VIDEO_V01_','') \
                              .replace(f'_{EDITION}.mp4','')

def kareler_al(yol, istenen):
    p = subprocess.Popen(['ffmpeg','-loglevel','error','-i',yol,
                          '-f','rawvideo','-pix_fmt','rgb24','-'],
                         stdout=subprocess.PIPE)
    OW, OH = 1080, 1350
    hedef = sorted(set(istenen)); son = max(hedef)
    bulunan = {}; n = 0
    while n <= son:
        b = p.stdout.read(OH*OW*3)
        if len(b) < OH*OW*3: break
        if n in hedef:
            bulunan[n] = Image.fromarray(
                np.frombuffer(b, dtype=np.uint8).reshape(OH, OW, 3).copy())
        n += 1
    p.stdout.close(); p.kill(); p.wait()
    return bulunan, n

# ------------------------------ SERIT --------------------------------
TAM_BOY  = int(TAM_EN * 1350/1080)
_bw = (BANT_X[1]-BANT_X[0]) * 1080
_bh = (BANT_Y[1]-BANT_Y[0]) * 1350
BANT_BOY = int(BANT_EN * _bh/_bw)
AD_EN    = 170
SATIR_H  = max(TAM_BOY, BANT_BOY) + 30
BASLIKLAR = ['kare 0', 'kare 45', 'kare 45 — GLIF BANDI 1:1 (kalinti)', 'kare 137']
SUTUN_X   = [AD_EN, AD_EN+TAM_EN, AD_EN+TAM_EN*2, AD_EN+TAM_EN*2+BANT_EN]
SAYFA_EN  = AD_EN + TAM_EN*3 + BANT_EN

def bant_kirp(im):
    W, H = im.size
    return im.crop((int(BANT_X[0]*W), int(BANT_Y[0]*H),
                    int(BANT_X[1]*W), int(BANT_Y[1]*H)))

def serit_yap(pair, kares, toplam):
    im = Image.new('RGB', (SAYFA_EN, SATIR_H), (255,255,255))
    dr = ImageDraw.Draw(im)
    dr.text((8, 12), pair.replace('_',' &\n'), fill=(15,15,15))
    dr.text((8, SATIR_H-40), f"{toplam} kare", fill=(130,130,130))
    def koy(x, img, w, h):
        if img is None:
            dr.rectangle([x,0,x+w-1,h-1], outline=(200,60,60))
            dr.text((x+10, h//2), "KARE YOK", fill=(200,60,60)); return
        im.paste(img.resize((w,h), Image.LANCZOS) if img.size != (w,h) else img, (x,0))
        dr.rectangle([x,0,x+w-1,h-1], outline=(210,210,210))
    koy(SUTUN_X[0], kares.get(0),   TAM_EN,  TAM_BOY)
    koy(SUTUN_X[1], kares.get(45),  TAM_EN,  TAM_BOY)
    koy(SUTUN_X[2], bant_kirp(kares[45]) if 45 in kares else None,
        BANT_EN, BANT_BOY)
    koy(SUTUN_X[3], kares.get(137), TAM_EN,  TAM_BOY)
    dr.line([(0,SATIR_H-1),(SAYFA_EN,SATIR_H-1)], fill=(170,170,170))
    return im

# ------------------------------ KOSU ---------------------------------
sayfa_sayisi = (len(VIDEOLAR)+SATIR_SAYFA-1)//SATIR_SAYFA
print(f"sayfa: {sayfa_sayisi} | {SATIR_SAYFA} cift/sayfa | {SAYFA_EN} px genis")
print(f"glif bandi: {int(_bw)}x{int(_bh)} px kaynak, 1:1 gosterim")
print(f"cikti: {OUT_DIR}\n" + "-"*72, flush=True)

t0=time.time(); uretilen=[]; sorunlu=[]
for s in range(sayfa_sayisi):
    yol_s = os.path.join(OUT_DIR, f'KK_S{s+1:02d}.png')
    if os.path.exists(yol_s) and not YENIDEN:
        print(f"sayfa {s+1}/{sayfa_sayisi} zaten var, atlandi", flush=True)
        uretilen.append(yol_s); continue
    grup = VIDEOLAR[s*SATIR_SAYFA:(s+1)*SATIR_SAYFA]
    sayfa = Image.new('RGB', (SAYFA_EN, 32+SATIR_H*len(grup)), (255,255,255))
    dr = ImageDraw.Draw(sayfa)
    dr.text((8,8), f"{EDITION} KK V2 — SAYFA {s+1}/{sayfa_sayisi}", fill=(15,15,15))
    for x, b in zip(SUTUN_X, BASLIKLAR):
        dr.text((x+6, 8), b, fill=(95,95,95))
    for i, v in enumerate(grup):
        pair = cift_adi(v)
        try:
            kares, toplam = kareler_al(v, KARELER)
            eksik=[k for k in KARELER if k not in kares]
            if eksik or toplam < 138: sorunlu.append(f"{pair}: {toplam} kare, eksik {eksik}")
        except Exception as e:
            kares, toplam = {}, 0
            sorunlu.append(f"{pair}: {type(e).__name__} {e}")
        sayfa.paste(serit_yap(pair, kares, toplam), (0, 32+i*SATIR_H))
        n = s*SATIR_SAYFA+i+1
        gec=time.time()-t0; kal=(gec/n)*(len(VIDEOLAR)-n)
        print(f"{n}/{len(VIDEOLAR)} (%{100*n/len(VIDEOLAR):5.1f}) | {pair:24s} "
              f"| {toplam} kare | gecen {sure(gec)} | kalan ~{sure(kal)}", flush=True)
    sayfa.save(yol_s, optimize=True)
    uretilen.append(yol_s)
    print(f"  -> {os.path.basename(yol_s)} ({os.path.getsize(yol_s)/1e6:.1f} MB)", flush=True)

print("\n"+"="*72)
print(f"BITTI: {len(uretilen)} sayfa | {len(VIDEOLAR)} video | {sure(time.time()-t0)}")
print("\n--- KARE OKUMA SORUNU ---")
if not sorunlu: print("  YOK - tum videolarin kareleri okundu.")
for x in sorunlu: print(f"  {x}")
print(f"\nToplam boyut: {sum(os.path.getsize(y) for y in uretilen)/1e6:.1f} MB")
print("\nSayfalar hazir. Claude bu dosyalari Drive'dan kendisi bulup indirecek.")
print("Yapman gereken: bittigini soylemek.")
