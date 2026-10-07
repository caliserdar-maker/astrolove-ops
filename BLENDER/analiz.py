import numpy as np,cv2,json,sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
def yukle(p): 
    im=Image.open(p).convert('RGB')
    if im.size!=(2000,3000): im=im.resize((2000,3000),Image.LANCZOS)
    return np.asarray(im).astype(np.float32)/255
OG={'ana':(780,1620,500,1500),'cember':(420,1100,180,420),'kucuk1':(1840,2070,460,700),'kucuk2':(1840,2070,1380,1620),
    'isim1':(2130,2290,290,880),'sonsuz':(2160,2260,980,1180),'isim2':(2130,2300,1280,1720),'tagline':(2480,2630,350,1660)}
def maske(c):
    hsv=cv2.cvtColor(c,cv2.COLOR_RGB2HSV); m=((hsv[...,1]>0.35)&(hsv[...,2]>0.35)).astype(np.uint8)
    return m
def olc(I):
    r={}
    for ad,(y0,y1,x0,x1) in OG.items():
        c=I[y0:y1,x0:x1]; m=maske(c); mi=cv2.erode(m,np.ones((3,3),np.uint8))>0
        lab=cv2.cvtColor(c,cv2.COLOR_RGB2Lab); L,a,b=lab[...,0],lab[...,1],lab[...,2]
        C=np.hypot(a,b); h=np.degrees(np.arctan2(b,a))
        mf=m.astype(np.float32)
        def nb(x,s): return cv2.GaussianBlur(x*mf,(0,0),s)/np.maximum(cv2.GaussianBlur(mf,(0,0),s),1e-3)
        leke=nb(L,2.5)-nb(L,10)       # 2.5-10 px (2000 olcek) = 9-36 px tam: leke boyu
        ince=L-cv2.GaussianBlur(L,(0,0),1)
        # kenar: dis 1 px halka ve ic
        kenar=(m>0)&~(cv2.erode(m,np.ones((3,3),np.uint8))>0)
        # golge: ogenin 3-10 px sag-alt zemin vs uzak zemin
        mm=cv2.dilate(m,np.ones((3,3),np.uint8)); sh=np.zeros_like(m); sh[4:,4:]=mm[:-4,:-4]
        band=(cv2.dilate(sh,np.ones((7,7),np.uint8))>0)&(cv2.dilate(m,np.ones((5,5),np.uint8))==0)
        uzak=cv2.dilate(m,np.ones((41,41),np.uint8))==0
        r[ad]=dict(L5_50_95=np.percentile(L[mi],[5,50,95]).round(1).tolist() if mi.any() else None,
                   C=round(float(np.median(C[mi])),1) if mi.any() else None, ton=round(float(np.median(h[mi])),1) if mi.any() else None,
                   leke=round(float(np.std(leke[mi])),2) if mi.any() else None, ince=round(float(np.std(ince[mi])),2) if mi.any() else None,
                   kenar_L=round(float(np.median(L[kenar])),1), golge=round(float(np.median(L[band])-np.median(L[uzak])),2) if band.any() and uzak.any() else None,
                   parlak_yuzde=round(float((L[mi]>90).mean()*100),1) if mi.any() else None)
    return r
out={}
for ad,p in [('REF','/tmp/claude-0/REF/ref.png'),('D2','c_son/SV_BLENDER_2000.jpg'),('D2_beneksiz','c_c60f37/SV_BLENDER_2000.jpg')]:
    out[ad]=olc(yukle(p))
json.dump(out,open('analiz.json','w'),indent=1)
for og in OG:
    print(og)
    for ad in out: print('  ',ad.ljust(12),out[ad][og])
