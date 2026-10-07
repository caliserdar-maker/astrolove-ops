# Poster duzeyi renk olcumu (Claude, 4 Eki): 2000x3000 poster, altin cekirdek pikselleri (H 8-32, S>90, V>100, bilesen>=40px), oge bandlari bu 3 poster yerlesimine gore; medyan Lab ve ana sembole dE00.
# Kullanim: dizinde <AD>_VURGU_tam.jpg dosyalari varken python3 renk_olc.py
import numpy as np,cv2
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
def gruplar(p):
    im=np.asarray(Image.open(p).convert('RGB'))
    hsv=cv2.cvtColor(im,cv2.COLOR_RGB2HSV)
    g=(hsv[...,0]>=8)&(hsv[...,0]<=32)&(hsv[...,1]>90)&(hsv[...,2]>100)
    # yildizlari ele: kucuk bilesenler
    n,lab,st,_=cv2.connectedComponentsWithStats(g.astype(np.uint8),8)
    g=(st[:,cv2.CC_STAT_AREA]>=40)[lab]&g
    H,W=g.shape; Y,X=np.mgrid[0:H,0:W]
    ana=g&(Y>=640)&(Y<1640)&(X>=480)&(X<1520)
    cember=g&(Y>=400)&(Y<1720)&~((Y>=640)&(X>=480)&(X<1520))
    R={'ANA SEMBOL':ana,'CEMBER':cember,'KUCUK SEMBOLLER':g&(Y>=1840)&(Y<2110),
       'ISIMLER+SONSUZ':g&(Y>=2140)&(Y<2300),'TAGLINE':g&(Y>=2440)&(Y<2600)}
    L=rgb2lab(im/255.0)
    return {k:(np.median(L[m],0),np.percentile(L[m][:,0],[25,75]),int(m.sum())) for k,m in R.items()}
for p in ['CANCER_LIBRA','AQUARIUS_ARIES','SCORPIO_VIRGO']:
    r=gruplar(p+'_VURGU_tam.jpg'); a=r['ANA SEMBOL'][0]
    print('\n'+p)
    print(f"{'oge':16s} {'L':>5s} {'a':>5s} {'b':>5s} {'C':>5s} {'ton':>5s} {'dE00':>5s} px")
    for k,(m,q,n) in r.items():
        dE=float(deltaE_ciede2000(a[None],m[None])[0])
        print(f"{k:16s} {m[0]:5.1f} {m[1]:5.1f} {m[2]:5.1f} {np.hypot(m[1],m[2]):5.1f} {np.degrees(np.arctan2(m[2],m[1])):5.1f} {dE:5.2f} {n}")
