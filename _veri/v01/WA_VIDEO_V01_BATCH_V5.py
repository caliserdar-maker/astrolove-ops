# =====================================================================
# WA_VIDEO_V01_BATCH_V5 — PURE_WHITE, 78 VIDEO (TAM KOSU)
# Onayli hat: WA_VIDEO_V01_PILOT_H5 (B62/B63/B64). Hareket DEGISMEDI.
#
# V4'TEN TEK FARK — GLIF YAKALAMA (17 Agu aksam, olculdu):
#   ESKI: sabit FR_CAN/FR_LIB kutulari (Cancer-Libra'dan turetilmis oran).
#         Genis glifler kutu disina tasiyordu -> 15/78 kalinti FAIL.
#   YENI: yatay serit + orta cizgi.
#         Y0 = min(B_CAN[1],B_LIB[1]) - 28
#         Y1 = max(B_CAN[3],B_LIB[3]) + 28
#         XM = Wp//2 ; merkezi solda = sol glif, sagda = sag glif
#         KENAR KURALI: serit ust/alt kenarini KESEN bilesen ALINMAZ.
#         silme kutusu = yakalanan maskenin gercek sinirlari + 6 px
#   OLCUM (WA_SERIT_KONTROL_V1, 78/78 PW):
#         kalinti 15 FAIL -> 0 ; fusion kesisim 0/78 ; 77 cift TEMIZ.
#         14 ciftte eski kutu sol glifi kirpiyordu (ARIES_SAGITTARIUS
#         157 px yakalanmis, gercegi 907).
#         KENAR KURALI yalniz GEMINI_GEMINI'yi etkiliyor: glifin altindaki
#         yazi satiri (5 parca, y951-989) seride giriyordu. Kural sonrasi
#         sol 1130 / sag 1139 = %0.8 fark (11 ayni-burc cifti bandi %0-1.5).
#   GUVENLIK: silme kutusu B_FUS ile kesisirse HATA verir, video yazilmaz.
#
# Hizlandirmalar V4'ten aynen: tek gecis kodlama, 0-152 kare, ROI kompozit.
# Olculen: 45 sn/video -> 78 video ~1 saat.
# Resume destekli, CSV aninda flush, ETA sayacli.
# DIKKAT: mevcut 78 PW mp4 dosyasinin UZERINE yazar. CSV yeni (V5).
# Colab, tek hucre. Etsy API'ye DOKUNMAZ.
# =====================================================================
import os, sys, time, gc, csv, glob, subprocess, shutil, socket
socket.setdefaulttimeout(120)
import numpy as np, cv2
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
try:    import psutil; _PS=psutil.Process()
except Exception: _PS=None

# ------------------------------------------------------------- AYAR
DRIVE_ROOT = '/content/drive/MyDrive/ASTROLOVE'
EDITION    = 'PURE_WHITE'
SURUM      = 'V5'
LIMIT      = None         # TAM KOSU: 78 cift
KIYAS      = False        # kalite kapisi gecti, tekrar kosulmaz
KIYAS_CIFT = 'CANCER_LIBRA'
KESIM      = (15, 152)
CRF        = 12
PRESET     = 'slow'
OW,OH,FPS,NF = 1080,1350,30,225
ROI_PAY    = 40

SERIT_PAY  = 28           # serit dikey payi   (olculdu, 17 Agu)
SIL_PAY    = 6            # silme kutusu payi  (olculdu, 17 Agu)
MIN_ALAN   = 30           # V4 tam_glif ile ayni

CI_PB     = (982,448,2019,1803)
CI_TH     = 18
CI_CEK    = np.array([182,140, 78],np.float32)
CI_HALO   = np.array([198,162,112],np.float32)
FR_FUS = (120/1037, 150/1355, 920/1037, 820/1355)
FR_CAN = (270/1037, 848/1355, 400/1037, 955/1355)
FR_LIB = (650/1037, 845/1355, 810/1037, 955/1355)
# -------------------------------------------------------------------

T0 = time.time()
def log(m): print(f"[{time.time()-T0:7.1f}s] {m}", flush=True)
def sure(sn):
    sn=int(max(0,sn))
    return f"{sn//3600}s {(sn%3600)//60:02d}d {sn%60:02d}sn" if sn>=3600 \
           else f"{sn//60}d {sn%60:02d}sn"
def ram():
    if _PS is None: return ''
    return f" | RAM {_PS.memory_info().rss/1e9:.1f} GB"

try:
    from google.colab import drive
    if not os.path.ismount('/content/drive'): drive.mount('/content/drive')
except ImportError: pass
if not os.path.isdir(DRIVE_ROOT): sys.exit(f"HATA: DRIVE_ROOT yok: {DRIVE_ROOT}")
for exe in ('ffmpeg','ffprobe'):
    if not shutil.which(exe): sys.exit(f"HATA: {exe} yok")
EXP_KOK = os.path.join(DRIVE_ROOT,'WALL_ART','LISTING_MEDIA','VIDEOS',
                       'V01_FIREFLY_STORY','01_EXPORTS')
if not os.path.isdir(EXP_KOK): sys.exit(f"HATA: 01_EXPORTS yok:\n  {EXP_KOK}")
OPT_KOK = os.path.join(DRIVE_ROOT,'WALL_ART','POSTERS','OPTIMIZED_FOR_PRODUCTION')
if not os.path.isdir(OPT_KOK): sys.exit(f"HATA: OPTIMIZED yok:\n  {OPT_KOK}")
SRC_DIR = os.path.join(DRIVE_ROOT,'TEMP','WA_HERO_ZOOM_V4',EDITION)
if not os.path.isdir(SRC_DIR): sys.exit(f"HATA: ZOOM60 klasoru yok:\n  {SRC_DIR}")
OUT_DIR = os.path.join(EXP_KOK,EDITION); os.makedirs(OUT_DIR,exist_ok=True)
CSV_YOL = os.path.join(DRIVE_ROOT,'TEMP',f'VIDEO_BATCH_{EDITION}_{SURUM}_STATE.csv')

def cift_adi(p):
    return os.path.basename(p).replace('WA_06_MOCKUP_','') \
                              .replace(f'_{EDITION}_ZOOM60.png','')
CIFTLER = sorted(cift_adi(p) for p in glob.glob(os.path.join(SRC_DIR,'*ZOOM60.png')))
log(f"ortam hazir | edisyon={EDITION} | kaynak {len(CIFTLER)} cift | CPU {os.cpu_count()}")

# ============================ ARACLAR ================================
def rgb2hsv(c):
    r,g,b=[float(x) for x in c]; mx,mn=max(r,g,b),min(r,g,b); d=mx-mn
    if d==0: h=0.0
    elif mx==r: h=(60*((g-b)/d))%360
    elif mx==g: h=(60*((b-r)/d)+120)%360
    else:       h=(60*((r-g)/d)+240)%360
    return h, (d/mx if mx>0 else 0.0), mx

def hsv2rgb(h,s,v):
    c=v*s; x=c*(1-abs(((h/60)%2)-1)); m=v-c
    r,g,b=[(c,x,0),(x,c,0),(0,c,x),(0,x,c),(x,0,c),(c,0,x)][int(h//60)%6]
    return np.array([r+m,g+m,b+m],np.float32)

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

# ============================ URETIM =================================
def uret(PAIR, ED, ad_eki=''):
    r={'cift':PAIR}
    SRC=os.path.join(SRC_DIR,f'WA_06_MOCKUP_{PAIR}_{ED}_ZOOM60.png')
    if not os.path.isfile(SRC): raise FileNotFoundError(SRC)
    hero_tam=np.array(Image.open(SRC).convert('RGB'))

    if ED=='CHAMPAGNE_IVORY':
        PB_TAM, skor_k = CI_PB, 1.0
    else:
        pp=poster_yolu(ED,PAIR)
        if pp is None: raise FileNotFoundError(f"poster yok: {ED}/{PAIR}")
        PB_TAM, skor_k = kutu_olc(hero_tam, pp)
        if skor_k<0.95: raise ValueError(f"kutu skoru dusuk: {skor_k:.4f}")
    r['kutu_skor']=round(skor_k,4)

    KX=(hero_tam.shape[1]-int(hero_tam.shape[0]*0.8))//2
    hero=hero_tam[:, KX:KX+int(hero_tam.shape[0]*0.8)]
    PB=(PB_TAM[0]-KX,PB_TAM[1],PB_TAM[2]-KX,PB_TAM[3])
    if PB[0]<0 or PB[2]>hero.shape[1]:
        raise ValueError(f"poster 4:5 kirpimin disina tasiyor: {PB}")
    poster=hero[PB[1]:PB[3],PB[0]:PB[2]]; Hp,Wp=poster.shape[:2]

    g=cv2.cvtColor(poster,cv2.COLOR_RGB2GRAY).astype(np.float32)
    bgm=cv2.medianBlur(g.astype(np.uint8),151).astype(np.float32)
    kagit_V=float(np.median(bgm)); koyu = kagit_V<=128
    d = np.clip(g-bgm,0,255) if koyu else np.clip(bgm-g,0,255)
    def kutu(fr):
        return (int(fr[0]*Wp),int(fr[1]*Hp),int(fr[2]*Wp),int(fr[3]*Hp))
    B_FUS,B_CAN,B_LIB = kutu(FR_FUS),kutu(FR_CAN),kutu(FR_LIB)
    dfus=d[B_FUS[1]:B_FUS[3],B_FUS[0]:B_FUS[2]].astype(np.uint8)
    otsu,_=cv2.threshold(dfus,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    TH = CI_TH if ED=='CHAMPAGNE_IVORY' else int(max(12,min(60,otsu)))
    r['polarite']='KOYU' if koyu else 'ACIK'; r['esik']=TH
    M0=cv2.morphologyEx((d>TH).astype(np.uint8),cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))

    def bil(b):
        x0,y0,x1,y1=b; s0=np.zeros_like(M0); s0[y0:y1,x0:x1]=M0[y0:y1,x0:x1]
        n,lab,st,_=cv2.connectedComponentsWithStats(s0,8); o=[]
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if a>=60: o.append(((lab==i).astype(np.uint8),a/(w*h),
                                float(np.nonzero(lab==i)[0].mean())))
        return o
    hep=bil(B_FUS)
    if len(hep)<1: raise ValueError(f"fusion bileseni yok: {len(hep)}")
    CEMBER=np.clip(sum(b[0] for b in hep if b[1]<0.030),0,1).astype(np.uint8)
    ciz=[b for b in hep if b[1]>=0.030]; ciz.sort(key=lambda t:t[2])
    if len(ciz)<1: raise ValueError(f"gercek cizgi bileseni yok: {len(ciz)}")

    # ============ GLIF YAKALAMA: SERIT + ORTA CIZGI (V5) ============
    _n,_lab,_st,_cen = cv2.connectedComponentsWithStats(M0,8)
    Y0=max(0, min(B_CAN[1],B_LIB[1])-SERIT_PAY)
    Y1=min(Hp, max(B_CAN[3],B_LIB[3])+SERIT_PAY)
    XM=Wp//2
    _sub=_lab[Y0:Y1,:]
    _cnt=np.bincount(_sub.ravel(),minlength=_n)
    _xs=np.tile(np.arange(Wp,dtype=np.float64),(Y1-Y0,1))
    _sx=np.bincount(_sub.ravel(),weights=_xs.ravel(),minlength=_n)
    M_CAN=np.zeros_like(M0); M_LIB=np.zeros_like(M0); _red=0
    for i in range(1,_n):
        if _cnt[i]==0 or _st[i][4]<MIN_ALAN: continue
        bx0,by0,bw,bh,ba=_st[i]
        if by0<Y0 or by0+bh>Y1:            # KENAR KURALI: serit disina bagli
            _red+=1; continue
        m=np.zeros_like(M0); m[Y0:Y1,:]=(_sub==i).astype(np.uint8)
        if (_sx[i]/_cnt[i])<XM: M_CAN=np.maximum(M_CAN,m)
        else:                   M_LIB=np.maximum(M_LIB,m)
    G_C=int(M_CAN.sum()); G_L=int(M_LIB.sum())
    if G_C<200 or G_L<200: raise ValueError(f"glif px dusuk: {G_C}/{G_L}")
    r['serit']=f"{Y0}-{Y1}"; r['red_bilesen']=_red
    r['glif_c']=G_C; r['glif_l']=G_L
    del _sub,_xs,_cnt,_sx
    # ===============================================================

    NT=88000; N_C=int(round(NT*G_C/(G_C+G_L))); N_L=NT-N_C

    if len(ciz)>=2:
        F_LIB=ciz[0][0]
        F_CAN=np.clip(sum(b[0] for b in ciz[1:]),0,1).astype(np.uint8)
        AYRIM='BILESEN'
    else:
        F_ALL=ciz[0][0]
        sut=F_ALL.sum(axis=0).astype(np.int64); kum=np.cumsum(sut)
        top=int(kum[-1]); kes=int(np.searchsorted(kum, top*G_C/(G_C+G_L)))
        kes=int(np.clip(kes, B_FUS[0]+10, B_FUS[2]-10))
        F_CAN=F_ALL.copy(); F_CAN[:,kes:]=0
        F_LIB=F_ALL.copy(); F_LIB[:,:kes]=0
        if int(F_CAN.sum())<200 or int(F_LIB.sum())<200:
            raise ValueError("geometrik kesim dengesiz")
        AYRIM=f'GEOMETRIK_x{kes}'
    r['ayrim']=AYRIM

    _fm=np.clip(F_CAN+F_LIB,0,1)
    kagit_rgb=np.median(poster[M0==0].reshape(-1,3),0).astype(np.float32)
    murek_rgb=np.median(poster[_fm>0].reshape(-1,3),0).astype(np.float32)
    Hi,Si,Vi=rgb2hsv(murek_rgb); Vp=float(max(kagit_rgb))
    if Vp>128: Vc=min(Vi*1.72, Vp-30.0)
    else:      Vc=min(255.0, max(Vi*1.10, Vp+90.0))
    CEK_T=np.clip(hsv2rgb(Hi,Si,Vc),0,255)
    HAL_T=np.clip(hsv2rgb(Hi,Si*0.76,min(255.0,Vc*1.09)),0,255)
    if ED=='CHAMPAGNE_IVORY': CEK_RENK,ALTIN = CI_CEK.copy(),CI_HALO.copy()
    else:                     CEK_RENK,ALTIN = CEK_T,HAL_T
    r['cekirdek']='-'.join(str(x) for x in CEK_RENK.astype(int))

    # ===================== B62 KILIDI (AYNEN) ========================
    rng=np.random.default_rng(20260816)
    def bulut(m,n,norm=True,renk=False):
        yy,xx=np.nonzero(m); i=rng.choice(len(yy),n,replace=len(yy)<n)
        p=np.stack([xx[i],yy[i]],1).astype(np.float32)
        c=poster[yy[i],xx[i]].astype(np.float32) if renk else None
        if norm: p-=p.mean(0); p/=max(np.abs(p).max(),1e-6)
        return (p,c) if renk else p
    def acisal(a,b):
        fa=np.arctan2(a[:,1]-a[:,1].mean(),a[:,0]-a[:,0].mean())
        fb=np.arctan2(b[:,1]-b[:,1].mean(),b[:,0]-b[:,0].mean())
        return np.argsort(fa),np.argsort(fb)
    S_C,C_C=bulut(M_CAN,N_C,norm=False,renk=True)
    S_L,C_L=bulut(M_LIB,N_L,norm=False,renk=True)
    T_C=bulut(F_CAN,N_C,False); T_L=bulut(F_LIB,N_L,False)
    a1,b1=acisal(S_C,T_C); a2,b2=acisal(S_L,T_L)
    S_C,T_C=S_C[a1],T_C[b1]; S_L,T_L=S_L[a2],T_L[b2]

    s=OW/hero.shape[1]; pl,pt=PB[0]*s, PB[1]*s
    ekr=lambda p: np.stack([pl+p[:,0]*s, pt+p[:,1]*s],1)
    BAS=np.concatenate([ekr(S_C),ekr(S_L)],0)
    SON=np.concatenate([ekr(T_C),ekr(T_L)],0)
    GRP=np.concatenate([np.zeros(N_C),np.ones(N_L)]).astype(np.float32)
    KOL=np.where(GRP<0.5,-1.0,1.0).astype(np.float32)
    J=rng.normal(0,1,(NT,4)).astype(np.float32)
    SRZ=rng.uniform(0,2*np.pi,NT).astype(np.float32)
    FAZ=rng.uniform(0,2*np.pi,NT).astype(np.float32)   # KULLANILMIYOR, SILINMEZ
    HIZ=rng.uniform(0.10,0.26,NT).astype(np.float32)
    BOY=(rng.uniform(0.55,1.25,NT)).astype(np.float32)
    VAR=(rng.beta(1.3,2.2,NT)*0.58).astype(np.float32)
    DX=SON[:,0]-BAS[:,0]; DY=SON[:,1]-BAS[:,1]
    DN=np.maximum(np.hypot(DX,DY),1e-5)
    PERPX=(-DY/DN).astype(np.float32); PERPY=(DX/DN).astype(np.float32)
    SAL=(4.0+np.abs(J[:,0])*4.5).astype(np.float32)
    SALW=(0.055+np.abs(J[:,1])*0.045).astype(np.float32)
    KEM=(46+np.abs(J[:,2])*14).astype(np.float32)

    TABLO=cv2.resize(hero,(OW,OH),interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    if ED=='CHAMPAGNE_IVORY':
        TH_SIL=TH
        _sil=cv2.dilate((M_CAN|M_LIB).astype(np.uint8),np.ones((5,5),np.uint8),2)
        _pos_bos=cv2.inpaint(poster,_sil,7,cv2.INPAINT_TELEA)
        r['sil_fus']=0
    else:
        TH_SIL=max(8,int(TH*0.45))
        # ---- silme kutusu = yakalanan maskenin gercek sinirlari + 6 px (V5) ----
        def sil_kutu(m):
            yy,xx=np.nonzero(m)
            return (max(0,int(xx.min())-SIL_PAY), max(0,int(yy.min())-SIL_PAY),
                    min(Wp,int(xx.max())+1+SIL_PAY), min(Hp,int(yy.max())+1+SIL_PAY))
        K_CAN=sil_kutu(M_CAN); K_LIB=sil_kutu(M_LIB)
        _sf=0
        for K in (K_CAN,K_LIB):
            _sf+=max(0,min(K[2],B_FUS[2])-max(K[0],B_FUS[0])) * \
                 max(0,min(K[3],B_FUS[3])-max(K[1],B_FUS[1]))
        r['sil_fus']=int(_sf)
        if _sf>0:
            raise ValueError(f"silme kutusu fusion ile kesisiyor: {_sf} px "
                             f"(sembol dokunulmaz - B62 md.7)")
        _ds=(d>TH_SIL).astype(np.uint8); _gm=np.zeros_like(M0)
        for b in (K_CAN,K_LIB): _gm[b[1]:b[3],b[0]:b[2]]=_ds[b[1]:b[3],b[0]:b[2]]
        _gm=cv2.morphologyEx(_gm,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        _sil=cv2.dilate(_gm,np.ones((5,5),np.uint8),iterations=3)
        _pos_bos=cv2.inpaint(poster,_sil,9,cv2.INPAINT_TELEA)
    _g2=cv2.cvtColor(_pos_bos,cv2.COLOR_RGB2GRAY).astype(np.float32)
    _b2=cv2.medianBlur(_g2.astype(np.uint8),151).astype(np.float32)
    _d2=np.clip(_g2-_b2,0,255) if koyu else np.clip(_b2-_g2,0,255)
    kal=int(((_d2>TH_SIL)&((M_CAN|M_LIB)>0)).sum())
    kal_y=100.0*kal/max(G_C+G_L,1); r['kalinti_yuzde']=round(kal_y,2)
    _hero_bos=hero.copy(); _hero_bos[PB[1]:PB[3],PB[0]:PB[2]]=_pos_bos
    TABLO_BOS=cv2.resize(_hero_bos,(OW,OH),interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    def tuv(m,b=0.0):
        o=np.zeros((OH,OW),np.float32)
        rr=cv2.resize((m*255).astype(np.uint8),(int(Wp*s),int(Hp*s)),
                      interpolation=cv2.INTER_AREA).astype(np.float32)/255
        o[int(pt):int(pt)+rr.shape[0],int(pl):int(pl)+rr.shape[1]]=rr
        return cv2.GaussianBlur(o,(0,0),b) if b>0 else o
    CM=tuv(cv2.dilate(CEMBER,np.ones((5,5),np.uint8),2))
    KORU=np.minimum(cv2.GaussianBlur(1.0-np.clip(CM,0,1),(0,0),1.2),1.0-np.clip(CM,0,1))
    _ink=d*_fm
    SEM_A=tuv(np.clip((_ink/max(_ink.max(),1e-6))*1.25,0,1),0.6)[...,None]
    _sc=np.zeros_like(poster,np.float32); _sc[_fm>0]=poster[_fm>0]
    _full=np.zeros_like(hero,np.float32); _full[PB[1]:PB[3],PB[0]:PB[2]]=_sc
    SEM_C=cv2.resize(_full,(OW,OH),interpolation=cv2.INTER_AREA).astype(np.float32)
    SEM_C=np.clip(np.nan_to_num(SEM_C/np.maximum(tuv(_fm,0.0)[...,None],1e-4)),0,255)
    ss=lambda x:(lambda y:y*y*y*(y*(y*6-15)+10))(np.clip(x,0,1))

    rx0=max(0,int(pl)-ROI_PAY); rx1=min(OW,int(pl+Wp*s)+ROI_PAY)
    ry0=max(0,int(pt)-ROI_PAY); ry1=min(OH,int(pt+Hp*s)+ROI_PAY)
    _dis=np.ones((OH,OW),bool); _dis[ry0:ry1,rx0:rx1]=False
    _fark=float(np.abs(TABLO-TABLO_BOS)[_dis].max())
    if _fark>0.0: raise ValueError(f"ROI disinda fark {_fark} - pay yetersiz")
    RH,RW=ry1-ry0,rx1-rx0
    r['roi']=f"{RW}x{RH}"; r['roi_yuzde']=round(100.0*RW*RH/(OW*OH),1)

    TABLO_R     = np.ascontiguousarray(TABLO[ry0:ry1,rx0:rx1])
    TABLO_BOS_R = np.ascontiguousarray(TABLO_BOS[ry0:ry1,rx0:rx1])
    KORU_R      = np.ascontiguousarray(KORU[ry0:ry1,rx0:rx1])
    SEM_A_R     = np.ascontiguousarray(SEM_A[ry0:ry1,rx0:rx1])
    SEM_C_R     = np.ascontiguousarray(SEM_C[ry0:ry1,rx0:rx1])
    DOK_R       = 1.0-np.clip(SEM_A_R[...,0]*1.15,0,1)

    SON_=os.path.join(OUT_DIR,f'WA_VIDEO_V01_{PAIR}_{ED}{ad_eki}.mp4')

    # ---------------- TEK GECIS KODLAMA ----------------
    pr=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo',
     '-pix_fmt','rgb24','-s',f'{OW}x{OH}','-framerate',str(FPS),'-i','-',
     '-c:v','libx264','-crf',str(CRF),'-preset',PRESET,'-profile:v','high',
     '-pix_fmt','yuv420p','-color_primaries','bt709','-color_trc','bt709',
     '-colorspace','bt709','-movflags','+faststart','-an',SON_],
     stdin=subprocess.PIPE)

    TABLO_U8=np.clip(TABLO,0,255).astype(np.uint8)
    buf=TABLO_U8.copy(); TABLO_BYTES=TABLO_U8.tobytes()
    IZ_R=np.zeros((RH,RW),np.float32)
    _byi=(np.clip(BAS[:,1],0,OH-1).astype(np.int32)-ry0)
    _bxi=(np.clip(BAS[:,0],0,OW-1).astype(np.int32)-rx0)
    KAL0=np.zeros((RH,RW),np.float32); np.add.at(KAL0,(_byi,_bxi),1.0)
    KAL0=np.maximum(cv2.GaussianBlur(KAL0,(0,0),2.0),1e-6)

    for f in range(KESIM[1]+1):          # 153'ten sonrasi kesiliyor: uretilmez
        if f>=146:                       # bu kareler her zaman ham TABLO
            pr.stdin.write(TABLO_BYTES); continue
        yol=np.clip((f-8)/140,0,1); yol=0.66*yol+0.34*ss(yol)
        tr=np.clip((yol-VAR)/(1-VAR.max()+1e-6),0,1)
        t=0.58*tr+0.42*ss(tr)
        zarf=np.sin(np.clip(t,0,1)*np.pi)**1.15
        toz=zarf*(1.0-ss(np.clip((t-0.74)/0.26,0,1)))
        ax=BAS[:,0]+(SON[:,0]-BAS[:,0])*t + KOL*KEM*np.sin(t*np.pi)
        ay=BAS[:,1]+(SON[:,1]-BAS[:,1])*t - 22*np.sin(t*np.pi)
        px=ax+PERPX*SAL*toz*np.sin(SRZ+f*SALW)+np.sin(SRZ*1.7+f*0.09)*1.5
        py=ay+PERPY*SAL*toz*np.sin(SRZ+f*SALW)-toz*6.0+np.cos(SRZ*1.7+f*0.082)*1.5
        px=np.clip(px,pl+6,pl+Wp*s-6); py=np.clip(py,pt+6,pt+Hp*s-6)
        yerles=float(ss(np.clip((f-112)/30,0,1)))
        sonum=ss(np.clip((f-140)/30,0,1))
        cik=np.clip(np.hypot(px-BAS[:,0],py-BAS[:,1])/4.0,0,1)
        alfa=cik*(1.0-sonum)
        blink=np.ones(NT,np.float32)*0.42*BOY*alfa*(0.55+0.45*np.clip(t,0,1))
        iy=(np.clip(py,0,OH-1).astype(np.int32)-ry0)
        ix=(np.clip(px,0,OW-1).astype(np.int32)-rx0)
        acc=np.zeros((RH,RW),np.float32); np.add.at(acc,(iy,ix),blink)
        IZ_R=IZ_R*(0.80-0.35*yerles)+acc          # IZ her karede birikir

        if f<KESIM[0]:                   # kesilecek kare: yalniz IZ guncellendi
            continue
        if f<=16:                        # yazilir ama ham TABLO
            pr.stdin.write(TABLO_BYTES); continue

        bas_=acc*KORU_R; kuy=np.clip(IZ_R-acc,0,None)*KORU_R
        geri=ss(np.clip((f-112)/26,0,1))
        _w=(1.0-cik).astype(np.float32)
        KAL=np.zeros((RH,RW),np.float32); np.add.at(KAL,(_byi,_bxi),_w)
        KAL=cv2.GaussianBlur(KAL,(0,0),2.0)
        KALm=np.maximum(np.clip(KAL/KAL0,0,1),geri)[...,None]
        kare=TABLO_BOS_R*(1.0-KALm)+TABLO_R*KALm
        ch=cv2.GaussianBlur(bas_,(0,0),1.1); hh=cv2.GaussianBlur(bas_,(0,0),4.5)
        kt=cv2.GaussianBlur(kuy,(0,0),1.8)
        ch=ch*DOK_R; hh=hh*DOK_R; kt=kt*DOK_R
        A1=np.clip(ch*0.92,0,1.0)[...,None]; A2=np.clip(hh*0.10,0,1.0)[...,None]
        A3=np.clip(kt*0.58,0,1.0)[...,None]
        kare=kare*(1-A3*0.62)+ALTIN*(A3*0.62)
        kare=kare*(1-A2*0.68)+ALTIN*(A2*0.68)
        kare=kare*(1-A1*0.78)+CEK_RENK*(A1*0.78)
        on=float(1.0-ss(np.clip((f-112)/34,0,1)))
        if on>0.01 and float(np.max(bas_))>1e-4:
            ma=SEM_A_R*on; kare=kare*(1-ma)+SEM_C_R*ma
        buf[ry0:ry1,rx0:rx1]=np.clip(kare,0,255).astype(np.uint8)
        pr.stdin.write(buf.tobytes())
    pr.stdin.close(); pr.wait()
    if pr.returncode!=0: raise RuntimeError(f"ffmpeg hatasi: {pr.returncode}")

    # -------- B62 MADDE 11 DOGRULAMA — AKIS TABANLI --------
    sm=np.zeros((OH,OW),bool)
    _r=cv2.resize((_fm*255).astype(np.uint8),(int((PB[2]-PB[0])*s),
                  int((PB[3]-PB[1])*s)),interpolation=cv2.INTER_AREA)>96
    sm[int(pt):int(pt)+_r.shape[0], int(pl):int(pl)+_r.shape[1]]=_r
    gm=np.zeros((OH,OW),bool)
    _rg=cv2.resize(((M_CAN|M_LIB)*255).astype(np.uint8),(int((PB[2]-PB[0])*s),
                   int((PB[3]-PB[1])*s)),interpolation=cv2.INTER_AREA)>96
    gm[int(pt):int(pt)+_rg.shape[0], int(pl):int(pl)+_rg.shape[1]]=_rg
    _tb=TABLO_BOS.mean(2)

    p=subprocess.Popen(['ffmpeg','-loglevel','error','-i',SON_,'-f','rawvideo',
                        '-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    fr0=None; onceki=None; sonk=None; n=0
    tonlar=[]; sv=[]; tn=[]; seri=[]; dds=[]
    while True:
        b=p.stdout.read(OH*OW*3)
        if len(b)<OH*OW*3: break
        fx=np.frombuffer(b,dtype=np.uint8).reshape(OH,OW,3).astype(np.float32)
        if n==0: fr0=fx.copy()
        sv.append(fx[sm].mean()); tn.append(fx[sm].mean(0))
        seri.append(int((np.abs(fx.mean(2)-_tb)[gm]>12).sum()))
        if onceki is not None: dds.append(float(np.abs(fx-onceki).mean()))
        if 20<=n<90 and (n-20)%6==0:
            a=np.abs(fx-fr0).sum(2)>40
            if a.sum()>500:
                pxc=fx[a]; tonlar.append(pxc[:,1].mean()/max(pxc[:,0].mean(),1e-6))
        onceki=fx; sonk=fx; n+=1
    p.stdout.close(); p.wait()

    toz_gr=float(np.mean(tonlar)) if tonlar else 0.0
    sv=np.array(sv); genlik=float(sv.max()-sv[0])
    tn=np.array(tn); gr=tn[:,1]/np.maximum(tn[:,0],1e-6)
    dg=float(np.abs(fr0-sonk).max())
    _s0=max(seri[0],1); _ser=[v/_s0 for v in seri]
    kay_max=float(max(_ser)); kay_bos=next((i for i,v in enumerate(_ser) if v<0.10),-1)
    dds=np.array(dds)
    donma=int((dds<0.02).sum())
    # DURAKSAMA PENCERESI = 17-111 (olcumden turetildi, 17 Agu).
    # 0-16 ve 146+ bilerek ham TABLO (B62 madde 10, dongu dikisi).
    # 112-137 YERLESME FAZI: geri/yerles/on egrileri 112'de basliyor,
    # toz soner ve glif geri doner - kare farkinin dusmesi TASARIMDIR.
    _orta=dds[17:112]; donma_orta=int((_orta<0.02).sum())
    mb=os.path.getsize(SON_)/1e6
    TEST=[("toz tonu 0.68-0.90", f"{toz_gr:.3f}",        0.68<=toz_gr<=0.90),
          ("kaynak koy.<1.25",   f"{kay_max:.2f}x",      kay_max<1.25),
          ("kaynak bosalir",     f"kare {kay_bos}",      kay_bos>=0),
          ("kalinti <%5",        f"%{kal_y:.1f}",        kal_y<5.0),
          ("sembol genlik <5",   f"{genlik:+.1f}",       abs(genlik)<5),
          ("ton sapma <0.06",    f"{gr.max()-gr.min():.3f}", (gr.max()-gr.min())<0.06),
          ("dongu farki <60",    f"{dg:.0f}",            dg<60),
          ("akis duraksama =0",  f"{donma_orta} (toplam {donma})", donma_orta==0),
          ("sure",               f"{n/30:.2f} sn",       abs(n/30-4.60)<0.2),
          ("oran",               f"{OW}x{OH}",           (OW,OH)==(1080,1350)),
          ("dosya <5 MB",        f"{mb:.2f} MB",         mb<5)]
    kalanlar=[a for a,_,ok in TEST if not ok]
    r.update({'sonuc':'PASS' if not kalanlar else 'FAIL','fail_test':'|'.join(kalanlar),
              'toz_gr':round(toz_gr,3),'kaynak_max':round(kay_max,2),
              'kaynak_bos':kay_bos,'sembol_genlik':round(genlik,1),
              'ton_sapma':round(float(gr.max()-gr.min()),3),
              'dongu':round(dg,0),'duraksama':donma,'duraksama_akis':donma_orta,
              'kare':n,'sn':round(n/30,2),'mb':round(mb,2),
              'dosya':os.path.basename(SON_),'yol':SON_,'testler':TEST})
    del TABLO,TABLO_BOS,SEM_C,SEM_A,hero,hero_tam,poster,fr0,onceki,sonk
    gc.collect()
    return r

# ================== ADIM 1: KALITE KAPISI (opsiyonel) ================
if KIYAS:
    print("="*72); print(f"KALITE KAPISI — {KIYAS_CIFT}"); print("="*72,flush=True)
    ts=time.time(); rr=uret(KIYAS_CIFT,EDITION,ad_eki='_HIZ_TEST'); dt=time.time()-ts
    print(f"\n  sure : {dt:.1f} sn/video")
    print(f"  ROI  : {rr['roi']} (%{rr['roi_yuzde']})   kare: {rr['kare']}\n")
    for ad,dgr,ok in rr['testler']:
        print(f"    {'PASS' if ok else 'FAIL'}  {ad:22s} {dgr}")
    print(f"\n  Dosya:\n  {rr['yol']}")
    if rr['sonuc']!='PASS': sys.exit("DUR: olcumler gecmedi.")
    print("\n  Olcumler GECTI.\n",flush=True)

# ============================== KOSU =================================
SUTUN=['cift','sonuc','fail_test','ayrim','polarite','esik','serit','red_bilesen',
       'glif_c','glif_l','sil_fus','kutu_skor','cekirdek','roi','roi_yuzde',
       'kalinti_yuzde','toz_gr','kaynak_max','kaynak_bos','sembol_genlik',
       'ton_sapma','dongu','duraksama','duraksama_akis','kare','sn','mb',
       'dosya','sure_sn']
yapilan=set()
if os.path.exists(CSV_YOL):
    with open(CSV_YOL,'r',encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row.get('sonuc') in ('PASS','FAIL'): yapilan.add(row['cift'])
    print(f"RESUME: {len(yapilan)} cift zaten uretilmis, atlanacak.",flush=True)
else:
    with open(CSV_YOL,'w',newline='',encoding='utf-8') as f:
        csv.writer(f).writerow(SUTUN)

hedef=[c for c in CIFTLER if c not in yapilan]
if LIMIT: hedef=hedef[:LIMIT]
N=len(hedef)
print(f"\nURETILECEK: {N} cift | edisyon={EDITION} | surum={SURUM}")
print(f"Cikti: {OUT_DIR}   (mevcut mp4 dosyalarinin UZERINE yazar)")
print(f"Durum: {CSV_YOL}")
print(f"Tahmini sure: ~{sure(N*46)}\n"+"-"*72,flush=True)

t0=time.time(); ok=0; fail=0; hata=0
for i,PAIR in enumerate(hedef,1):
    ts=time.time()
    try:
        r=uret(PAIR,EDITION); r['sure_sn']=round(time.time()-ts,1)
        ok+= r['sonuc']=='PASS'; fail+= r['sonuc']=='FAIL'
        ozet=(f"{r['sonuc']:4s} | {r['ayrim']:14s} | glif {r['glif_c']}/{r['glif_l']} "
              f"| kal %{r['kalinti_yuzde']:.1f} | {r['mb']:.2f} MB | {r['sure_sn']:.0f} sn")
        if r['red_bilesen']: ozet+=f" | red {r['red_bilesen']}"
        if r['fail_test']:   ozet+=f" | {r['fail_test']}"
    except Exception as e:
        r={'cift':PAIR,'sonuc':'HATA','fail_test':f"{type(e).__name__}: {e}",
           'sure_sn':round(time.time()-ts,1)}
        hata+=1; ozet=f"HATA | {r['fail_test'][:60]}"
    with open(CSV_YOL,'a',newline='',encoding='utf-8') as f:
        csv.DictWriter(f,fieldnames=SUTUN,extrasaction='ignore').writerow(r)
        f.flush(); os.fsync(f.fileno())
    gec=time.time()-t0; kal=(gec/i)*(N-i)
    print(f"{i}/{N} (%{100*i/N:5.1f}) | {PAIR:24s} | {ozet}")
    print(f"        gecen {sure(gec)} | kalan ~{sure(kal)}{ram()}",flush=True)
    gc.collect()

print("\n"+"="*72)
print(f"BITTI: {N} cift | PASS {ok} | FAIL {fail} | HATA {hata}")
print(f"Toplam sure {sure(time.time()-t0)}")
print(f"CSV: {CSV_YOL}")
