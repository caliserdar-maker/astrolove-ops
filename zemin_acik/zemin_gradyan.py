# BEIGE / AGED_PAPYRUS: ince tane + merkezden kenara belirgin koyulaşan radyal gradyan (lekesiz). 2 güç: G1 orta, G2 güçlü.
import numpy as np
from PIL import Image, ImageFilter
N=1264; rng=np.random.default_rng(7)
yy,xx=np.mgrid[0:N,0:N]; rr=np.hypot(xx-N/2,yy-N/2)/(N/2)
def tane(amp=2.0):
    n=rng.normal(0,1,(N,N)); im=Image.fromarray(((n-n.min())/(n.max()-n.min())*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    a=np.array(im).astype(float); return (a-a.mean())/a.std()*amp
def yap(merkez,kenar,us,guc):
    t=np.clip(rr/1.0,0,1)**us*guc          # 0 merkez, guc kenarda
    c=np.array(merkez,float)*(1-t[...,None])+np.array(kenar,float)*t[...,None]
    c+=tane(2.0)[...,None]
    return Image.fromarray(np.clip(c,0,255).astype(np.uint8))
var={
 'BEIGE_G1':   yap((240,230,210),(176,152,118),1.8,0.75),
 'BEIGE_G2':   yap((242,232,212),(150,124,90), 1.6,0.90),
 'PAPYRUS_G1': yap((236,216,168),(160,120,66), 1.8,0.75),
 'PAPYRUS_G2': yap((238,218,170),(128,92,46), 1.6,0.90),
}
for k,v in var.items(): v.save(k+'_1264.png')
print('ok')
