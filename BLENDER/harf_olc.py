import numpy as np,cv2,sys
from PIL import Image
Image.MAX_IMAGE_PIXELS=None
t=np.asarray(Image.open(sys.argv[1]+'/SV_BLENDER_tam.png'))
z=np.load('alfa_ogeler.npz'); K=dict(zip([str(a) for a in z['_ad']],z['_konum']))
for ad in ['tagline','isim1','isim2']:
    x,y=K[ad]; a=z[ad]; h,w=a.shape
    m=cv2.erode((a>250).astype(np.uint8),np.ones((3,3),np.uint8))
    n,l,st,_=cv2.connectedComponentsWithStats(m)
    lab=cv2.cvtColor(t[y:y+h,x:x+w].astype(np.float32)/255,cv2.COLOR_RGB2Lab)
    d={}
    for i in range(1,n):
        if st[i][4]<2000: continue
        d.setdefault(int(st[i][4]),[]).append(float(np.median(lab[...,0][l==i])))
    tum=[v for vs in d.values() for v in vs]
    ayni=[max(vs)-min(vs) for vs in d.values() if len(vs)>1]
    print(ad,'harf L fark (tum)',round(max(tum)-min(tum),1),'| ayni harf ici max fark',round(max(ayni),1) if ayni else '-')
