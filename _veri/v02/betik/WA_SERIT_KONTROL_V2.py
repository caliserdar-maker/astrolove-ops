# =====================================================================
# WA_SERIT_KONTROL_V1  —  PURE_WHITE, 78 CIFT  (SALT OKUR)
# Amac: serit yontemi ne yakaliyor? Fusion serit icine siziyor mu?
# Kaynak: WA_VIDEO_V01_BATCH_V4.py (kutu olcumu / esik / M0 AYNEN kopya)
# YAZDIGI TEK SEY: TEMP/SERIT_KONTROL_<EDITION>.csv
# Video, klasor, ilan DEGISMEZ. Etsy API'ye DOKUNMAZ.
# Resume destekli, ETA sayacli.
#
# 17 Agu 2026 kosusu (PURE_WHITE): 78/78, sure 5 dk.
#   fusion kesisimi 0/78 | TEMIZ 77 | SIZINTI 1 (GEMINI_GEMINI)
#   14 ciftte eski sabit kutu sol glifi kirpiyordu.
# B65'te kayitli. Sonraki her edisyonda URETIMDEN ONCE kosulur.
# EDITION satirini degistirerek CI / WP / MB / DB icin kullan.
# =====================================================================
import os, sys, time, gc, csv, glob
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
try:    import psutil; _PS=psutil.Process()
except Exception: _PS=None

# ------------------------------------------------------------- AYAR
DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'
EDITION    = 'PURE_WHITE'
LIMIT      = None          # hizli deneme icin 5 yapabilirsin
SERIT_PAY  = 28            # Mo olcumu: Y0 -28 / Y1 +28
SIL_PAY    = 6             # Mo olcumu: silme kutusu +6 px
MIN_ALAN   = 30            # BATCH_V4 tam_glif ile ayni

CI_TH  = 18
FR_FUS = (120/1037, 150/1355, 920/1037, 820/1355)
FR_CAN = (270/1037, 848/1355, 400/1037, 955/1355)
FR_LIB = (650/1037, 845/1355, 810/1037, 955/1355)
# -------------------------------------------------------------------

T0=time.time()
def sure(sn):
    sn=int(max(0,sn))
    return f"{sn//3600}s {(sn%3600)//60:02d}d {sn%60:02d}sn" if sn>=3600 \
           else f"{sn//60}d {sn%60:02d}sn"
def ram():
    return '' if _PS is None else f" | RAM {_PS.memory_info().rss/1e9:.1f} GB"

try:
    from google.colab import drive
    if not os.path.ismount('/content/drive'): drive.mount('/content/drive')
except ImportError: pass
if not os.path.isdir(DRIVE_ROOT): sys.exit(f"HATA: DRIVE_ROOT yok: {DRIVE_ROOT}")
OPT_KOK = os.path.join(DRIVE_ROOT,'WALL_ART','POSTERS','OPTIMIZED_FOR_PRODUCTION')
if not os.path.isdir(OPT_KOK): sys.exit(f"HATA: OPTIMIZED yok:\n  {OPT_KOK}")
SRC_DIR = os.path.join(DRIVE_ROOT,'TEMP','WA_HERO_ZOOM_V4',EDITION)
if not os.path.isdir(SRC_DIR): sys.exit(f"HATA: ZOOM60 klasoru yok:\n  {SRC_DIR}")
CSV_YOL = os.path.join(DRIVE_ROOT,'TEMP',f'SERIT_KONTROL_{EDITION}.csv')

def cift_adi(p):
    return os.path.basename(p).replace('WA_06_MOCKUP_','') \
                              .replace(f'_{EDITION}_ZOOM60.png','')
CIFTLER = sorted(cift_adi(p) for p in glob.glob(os.path.join(SRC_DIR,'*ZOOM60.png')))
print(f"ortam hazir | edisyon={EDITION} | kaynak {len(CIFTLER)} cift",flush=True)

# ===================== BATCH_V4'TEN AYNEN KOPYA ======================
def es(prof,u):
    return np.interp(np.linspace(0,1,u), np.linspace(0,1,len(prof)), prof)
def pear(a,b):
    a=a-a.mean(); b=b-b.mean()
    d=np.sqrt(float((a*a).sum())*float((b*b).sum()))
    return float((a*b).sum()/d) if d>0 else -1.0
def eksen(mp,pp,bas_ara,uz_ara):
    en=(-2.,None,None); N=len(mp)
    for u in uz_ara:
        if u<8 or u>N: continue
        ref=es(pp,u); ref=ref-ref.mean(); rn=float(np.sqrt((ref*ref).sum()))
        if rn<=0: continue
        for b0 in bas_ara:
            if b0<0 or b0+u>N: continue
            sg=mp[b0:b0+u]; sg=sg-sg.mean(); sn=float(np.sqrt((sg*sg).sum()))
            if sn<=0: continue
            r=float((ref*sg).sum()/(rn*sn))
            if r>en[0]: en=(r,b0,u)
    return en
def poster_yolu(ed,pair):
    for c in (os.path.join(OPT_KOK,ed,'3X4',f'WA_POSTER_{pair}_{ed}_3X4.jpg'),
              os.path.join(OPT_KOK,ed,'3X4',f'{pair}.jpg')):
        if os.path.isfile(c): return c
    h=sorted(glob.glob(os.path.join(OPT_KOK,ed,'3X4',f'*{pair}*.jpg')))
    return h[0] if len(h)==1 else None
def kutu_olc(hero_rgb, ppath):
    S,INSET,FINE=5,0.15,10
    mg=cv2.cvtColor(hero_rgb,cv2.COLOR_RGB2GRAY); mf=mg.astype(np.float32)
    ms=cv2.resize(mg,(3000//S,2250//S),interpolation=cv2.INTER_AREA).astype(np.float32)
    pim=Image.open(ppath); pim.draft('L',(900,1200))
    pg=pim.convert('L').resize((768,1024),Image.LANCZOS)
    pa=np.asarray(pg,np.float32); PS,PR=pa.mean(0),pa.mean(1)
    def sp(A,t,h):
        a=max(0,t+int(round(h*INSET))); b=min(A.shape[0],max(a+2,t+int(round(h*(1-INSET)))))
        return A[a:b,:].mean(0)
    def rp(A,l,w):
        a=max(0,l+int(round(w*INSET))); b=min(A.shape[1],max(a+2,l+int(round(w*(1-INSET)))))
        return A[:,a:b].mean(1)
    l,w,t,h=140,202,90,270; onc=None
    for _ in range(3):
        _,l,w=eksen(sp(ms,t,h),PS,range(100,340),range(150,261))
        _,t,h=eksen(rp(ms,l,w),PR,range(20,200),range(200,331))
        if (l,w,t,h)==onc: break
        onc=(l,w,t,h)
    L,T,W,H=l*S,t*S,w*S,h*S; onc=None
    for _ in range(2):
        _,L,W=eksen(sp(mf,T,H),PS,range(L-FINE,L+FINE+1),range(W-FINE,W+FINE+1))
        _,T,H=eksen(rp(mf,L,W),PR,range(T-FINE,T+FINE+1),range(H-FINE,H+FINE+1))
        if (L,T,W,H)==onc: break
        onc=(L,T,W,H)
    ref=np.asarray(pg.resize((W,H),Image.LANCZOS),np.float32)
    return (L,T,L+W,T+H), pear(mf[T:T+H,L:L+W].ravel(),ref.ravel())

# ============================ OLCUM ==================================
def olc(PAIR, ED):
    r={'cift':PAIR}
    SRC=os.path.join(SRC_DIR,f'WA_06_MOCKUP_{PAIR}_{ED}_ZOOM60.png')
    if not os.path.isfile(SRC): raise FileNotFoundError(SRC)
    hero_tam=np.array(Image.open(SRC).convert('RGB'))
    pp=poster_yolu(ED,PAIR)
    if pp is None: raise FileNotFoundError(f"poster yok: {ED}/{PAIR}")
    PB_TAM, skor_k = kutu_olc(hero_tam, pp)
    if skor_k<0.95: raise ValueError(f"kutu skoru dusuk: {skor_k:.4f}")
    r['kutu_skor']=round(skor_k,4)

    KX=(hero_tam.shape[1]-int(hero_tam.shape[0]*0.8))//2
    hero=hero_tam[:, KX:KX+int(hero_tam.shape[0]*0.8)]
    PB=(PB_TAM[0]-KX,PB_TAM[1],PB_TAM[2]-KX,PB_TAM[3])
    poster=hero[PB[1]:PB[3],PB[0]:PB[2]]; Hp,Wp=poster.shape[:2]

    g=cv2.cvtColor(poster,cv2.COLOR_RGB2GRAY).astype(np.float32)
    bgm=cv2.medianBlur(g.astype(np.uint8),151).astype(np.float32)
    koyu = float(np.median(bgm))<=128
    d = np.clip(g-bgm,0,255) if koyu else np.clip(bgm-g,0,255)
    def kutu(fr):
        return (int(fr[0]*Wp),int(fr[1]*Hp),int(fr[2]*Wp),int(fr[3]*Hp))
    B_FUS,B_CAN,B_LIB = kutu(FR_FUS),kutu(FR_CAN),kutu(FR_LIB)
    dfus=d[B_FUS[1]:B_FUS[3],B_FUS[0]:B_FUS[2]].astype(np.uint8)
    otsu,_=cv2.threshold(dfus,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    TH = CI_TH if ED=='CHAMPAGNE_IVORY' else int(max(12,min(60,otsu)))
    M0=cv2.morphologyEx((d>TH).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    r['esik']=TH; r['Wp']=Wp; r['Hp']=Hp

    _n,_lab,_st,_cen = cv2.connectedComponentsWithStats(M0,8)

    # ---- ESKI YOL (sabit kutu) : karsilastirma icin ----
    def tam_glif(b):
        o=np.zeros_like(M0)
        for i in range(1,_n):
            if _st[i][4]<MIN_ALAN: continue
            cx,cy=_cen[i]
            if b[0]<=cx<b[2] and b[1]<=cy<b[3]:
                o=np.maximum(o,(_lab==i).astype(np.uint8))
        if o.sum()==0: o[b[1]:b[3],b[0]:b[2]]=M0[b[1]:b[3],b[0]:b[2]]
        return o
    eski_c=int(tam_glif(B_CAN).sum()); eski_l=int(tam_glif(B_LIB).sum())

    # ---- YENI YOL (serit + orta cizgi) ----
    Y0=max(0, min(B_CAN[1],B_LIB[1])-SERIT_PAY)
    Y1=min(Hp, max(B_CAN[3],B_LIB[3])+SERIT_PAY)
    XM=Wp//2
    # --- V2 YAMA: yatay sinir = fusion kutusu (B_FUS). Parsomen/kagit
    # kenar artefaktlari bu sinirin disinda kalir. Gercek glifler icinde.
    X0 = B_FUS[0]; X1 = B_FUS[2]
    r['Y0']=Y0; r['Y1']=Y1; r['XM']=XM

    sub=_lab[Y0:Y1,:]
    cnt=np.bincount(sub.ravel(), minlength=_n)
    xs=np.tile(np.arange(Wp,dtype=np.float64),(Y1-Y0,1))
    sx=np.bincount(sub.ravel(), weights=xs.ravel(), minlength=_n)

    M_SOL=np.zeros_like(M0); M_SAG=np.zeros_like(M0)
    n_sol=n_sag=0; maks=0; tasan_n=0; tasan_px=0; fus_kes=0; notlar=[]
    for i in range(1,_n):
        if cnt[i]==0 or _st[i][4]<MIN_ALAN: continue
        cx=sx[i]/cnt[i]
        if not (X0 <= cx < X1): continue   # V2 YAMA: kenar artefakti
        bx0,by0,bw,bh,ba=_st[i]; bx1,by1=bx0+bw,by0+bh
        maks=max(maks,int(ba))
        # bilesen seridin disina tasiyor mu? (= serit disi bir seye bagli)
        ust=by0<Y0; alt=by1>Y1
        kes=max(0,min(bx1,B_FUS[2])-max(bx0,B_FUS[0]))*max(0,min(by1,B_FUS[3])-max(by0,B_FUS[1]))
        if ust or alt or kes>0:
            tasan_n+=1; tasan_px+=int(cnt[i]); fus_kes+=int(kes)
            notlar.append(f"{'SOL' if cx<XM else 'SAG'}:alan{int(ba)}"
                          f"{'/ust' if ust else ''}{'/alt' if alt else ''}"
                          f"{'/fus' if kes>0 else ''}")
        m=np.zeros_like(M0); m[Y0:Y1,:]=(sub==i).astype(np.uint8)
        if cx<XM: M_SOL=np.maximum(M_SOL,m); n_sol+=1
        else:     M_SAG=np.maximum(M_SAG,m); n_sag+=1

    sol=int(M_SOL.sum()); sag=int(M_SAG.sum())
    r['sol_px']=sol; r['sag_px']=sag
    r['oran']=round(max(sol,sag)/max(min(sol,sag),1),2)
    r['eski_sol']=eski_c; r['eski_sag']=eski_l
    r['degisim_yuzde']=round(100.0*((sol+sag)-(eski_c+eski_l))/max(eski_c+eski_l,1),1)
    r['sol_bilesen']=n_sol; r['sag_bilesen']=n_sag; r['maks_bilesen']=maks
    r['tasan_bilesen']=tasan_n; r['tasan_px']=tasan_px; r['fus_kesisim_px']=fus_kes

    # ---- silme kutusu = yakalanan maskenin gercek sinirlari + 6 px ----
    def sil_kutu(m):
        yy,xx=np.nonzero(m)
        if len(yy)==0: return None
        return (max(0,int(xx.min())-SIL_PAY), max(0,int(yy.min())-SIL_PAY),
                min(Wp,int(xx.max())+1+SIL_PAY), min(Hp,int(yy.max())+1+SIL_PAY))
    KS=sil_kutu(M_SOL); KG=sil_kutu(M_SAG)
    r['sil_sol']=str(KS); r['sil_sag']=str(KG)
    sk=0
    for K in (KS,KG):
        if K is None: continue
        sk+=max(0,min(K[2],B_FUS[2])-max(K[0],B_FUS[0]))*max(0,min(K[3],B_FUS[3])-max(K[1],B_FUS[1]))
    r['sil_fus_kesisim']=int(sk)

    # ---- ayni burc dogal kontrolu ----
    p=PAIR.split('_'); ayni = len(p)==2 and p[0]==p[1]
    r['ayni_burc']='E' if ayni else 'H'
    r['fark_yuzde']=round(100.0*abs(sol-sag)/max(sol,sag,1),1) if ayni else ''

    if tasan_n>0 or sk>0:            r['durum']='SIZINTI'
    elif sol<200 or sag<200:         r['durum']='DUSUK'
    else:                            r['durum']='TEMIZ'
    r['not']=' '.join(notlar[:4])
    del hero_tam,hero,poster,_lab,M0,M_SOL,M_SAG,sub,xs
    gc.collect()
    return r

# ============================== KOSU =================================
SUTUN=['cift','durum','kutu_skor','esik','Wp','Hp','Y0','Y1','XM',
       'sol_px','sag_px','oran','eski_sol','eski_sag','degisim_yuzde',
       'sol_bilesen','sag_bilesen','maks_bilesen','tasan_bilesen','tasan_px',
       'fus_kesisim_px','sil_sol','sil_sag','sil_fus_kesisim',
       'ayni_burc','fark_yuzde','not','sure_sn']
yapilan={}
if os.path.exists(CSV_YOL):
    with open(CSV_YOL,'r',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('durum'): yapilan[row['cift']]=row
    print(f"RESUME: {len(yapilan)} cift zaten olculmus, atlanacak.",flush=True)
else:
    with open(CSV_YOL,'w',newline='',encoding='utf-8') as f:
        csv.writer(f).writerow(SUTUN)

hedef=[c for c in CIFTLER if c not in yapilan]
if LIMIT: hedef=hedef[:LIMIT]
N=len(hedef)
print(f"\nOLCULECEK: {N} cift | VIDEO URETILMEZ")
print(f"Durum dosyasi: {CSV_YOL}\n"+"-"*72,flush=True)

t0=time.time(); satirlar=list(yapilan.values()); siz=0; hata=0
for i,PAIR in enumerate(hedef,1):
    ts=time.time()
    try:
        r=olc(PAIR,EDITION); r['sure_sn']=round(time.time()-ts,1)
        siz+= r['durum']=='SIZINTI'
        ozet=(f"{r['durum']:8s} | sol {r['sol_px']:5d} sag {r['sag_px']:5d} "
              f"oran {r['oran']:.2f} | eski {r['eski_sol']}/{r['eski_sag']} "
              f"({r['degisim_yuzde']:+.0f}%)")
        if r['not']: ozet+=f" | {r['not']}"
    except Exception as e:
        r={'cift':PAIR,'durum':'HATA','not':f"{type(e).__name__}: {e}",
           'sure_sn':round(time.time()-ts,1)}
        hata+=1; ozet=f"HATA | {r['not'][:60]}"
    satirlar.append(r)
    with open(CSV_YOL,'a',newline='',encoding='utf-8') as f:
        csv.DictWriter(f,fieldnames=SUTUN,extrasaction='ignore').writerow(r)
        f.flush(); os.fsync(f.fileno())
    gec=time.time()-t0; kal=(gec/i)*(N-i)
    print(f"{i}/{N} (%{100*i/N:5.1f}) | {PAIR:24s} | {ozet}")
    print(f"        gecen {sure(gec)} | kalan ~{sure(kal)}{ram()}",flush=True)
    gc.collect()

# ============================== OZET =================================
def gv(r,k,d=0):
    v=r.get(k,d)
    try: return float(v)
    except (TypeError,ValueError): return d

print("\n"+"="*72)
print(f"BITTI: {N} cift olculdu | SIZINTI {siz} | HATA {hata}")
print(f"Toplam sure {sure(time.time()-t0)}")

print("\n--- 1. SIZINTI (fusion serit icine giriyor) ---")
s=[r for r in satirlar if r.get('durum')=='SIZINTI']
if not s: print("  YOK - 78 ciftte serit yalniz kucuk glifleri yakaliyor.")
for r in sorted(s,key=lambda r:-gv(r,'tasan_px')):
    print(f"  {r['cift']:24s} tasan {int(gv(r,'tasan_px')):5d} px | "
          f"fus kesisim {int(gv(r,'fus_kesisim_px')):6d} | {r.get('not','')}")

print("\n--- 2. AYNI BURC CIFTLERI (sol/sag esit olmali) ---")
for r in sorted([x for x in satirlar if x.get('ayni_burc')=='E'],
                key=lambda r:-gv(r,'fark_yuzde')):
    print(f"  {r['cift']:24s} sol {int(gv(r,'sol_px')):5d} sag {int(gv(r,'sag_px')):5d}"
          f" | fark %{gv(r,'fark_yuzde'):.1f} | {r.get('durum','')}")

print("\n--- 3. EN DENGESIZ 10 CIFT ---")
for r in sorted([x for x in satirlar if x.get('durum') not in (None,'HATA')],
                key=lambda r:-gv(r,'oran'))[:10]:
    print(f"  {r['cift']:24s} oran {gv(r,'oran'):.2f} | "
          f"sol {int(gv(r,'sol_px')):5d} sag {int(gv(r,'sag_px')):5d} | {r.get('durum','')}")

print("\n--- 4. EN BUYUK BILESEN (isim yazisi kacti mi) ---")
mx=sorted([x for x in satirlar if x.get('durum') not in (None,'HATA')],
          key=lambda r:-gv(r,'maks_bilesen'))[:5]
for r in mx:
    print(f"  {r['cift']:24s} maks bilesen {int(gv(r,'maks_bilesen')):6d} px")
print(f"  (Mo olcumu: 1841. Isim blogu ~3000+ olur.)")

print(f"\nCSV: {CSV_YOL}")
