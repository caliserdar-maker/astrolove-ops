# Lekesiz açık zeminler: (1) düz + ince tane, (2) yumuşak kenar + ince tane, (3) kağıt lifi (papirüs dokusu) + yumuşak kenar
import numpy as np
from PIL import Image, ImageFilter
N=1264; rng=np.random.default_rng(7)
yy,xx=np.mgrid[0:N,0:N]; rr=np.hypot(xx-N/2,yy-N/2)/(N/2)
def tane(s=1.0,amp=3.0):
    n=rng.normal(0,1,(N,N)); im=Image.fromarray(((n-n.min())/(n.max()-n.min())*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(s))
    a=np.array(im).astype(float); return (a-a.mean())/a.std()*amp
def lif(amp=6.0):
    # yatay ve dikey uzun lifler (papirüs şeritleri)
    h=rng.normal(0,1,(N,1)); h=np.array(Image.fromarray(((h-h.min())/(h.max()-h.min())*255).astype(np.uint8)).resize((1,N),Image.BILINEAR)).astype(float)
    hx=np.repeat(rng.normal(0,1,(N,1)),N,1); vx=np.repeat(rng.normal(0,1,(1,N)),N,0)
    hx=np.array(Image.fromarray(np.uint8(np.clip(hx*40+128,0,255))).filter(ImageFilter.GaussianBlur(1.2))).astype(float)
    vx=np.array(Image.fromarray(np.uint8(np.clip(vx*40+128,0,255))).filter(ImageFilter.GaussianBlur(1.2))).astype(float)
    m=(hx-128)*0.6+(vx-128)*0.4
    return m/m.std()*amp
def kenar(g):  # merkezden kenara yumuşak koyulaşma, 0..1
    return np.clip(rr,0,1)**2.2*g
def yap(renk,kenar_g=0.0,tane_a=2.5,lif_a=0.0,koyu=(0,0,0)):
    c=np.array(renk,float)[None,None,:]*np.ones((N,N,1))
    k=kenar(kenar_g)[...,None]; c=c*(1-k)+np.array(koyu,float)*k
    c+= tane(1.0,tane_a)[...,None]
    if lif_a: c+= lif(lif_a)[...,None]*np.array([1,0.95,0.8])
    return Image.fromarray(np.clip(c,0,255).astype(np.uint8))
var={
 'BEIGE_1_duz':        yap((232,219,197),0.00,2.0),
 'BEIGE_2_kenar':      yap((236,224,203),0.35,2.0,koyu=(190,170,140)),
 'BEIGE_3_lif':        yap((234,221,199),0.30,1.5,5.0,koyu=(192,172,142)),
 'PAPYRUS_1_duz':      yap((226,203,154),0.00,2.0),
 'PAPYRUS_2_kenar':    yap((232,210,160),0.45,2.0,koyu=(170,132,78)),
 'PAPYRUS_3_lif':      yap((230,207,158),0.40,1.5,7.0,koyu=(172,134,80)),
}
for k,v in var.items(): v.save(k+'_1264.png')
from PIL import ImageDraw, ImageFont
S=400;pad=26; f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
out=Image.new('RGB',(3*(S+pad)+pad,2*(S+50)+20),(255,255,255)); d=ImageDraw.Draw(out)
for i,k in enumerate(var):
    im=var[k].resize((S,S),Image.LANCZOS); m=Image.new('L',(S,S),0); md=ImageDraw.Draw(m)
    R=449*S/954; c=S/2; md.ellipse([c-R,c-R,c+R,c+R],fill=255); hr=34*S/954; hy=163*S/954; md.ellipse([c-hr,hy-hr,c+hr,hy+hr],fill=0)
    x=pad+(i%3)*(S+pad); y=10+(i//3)*(S+50); out.paste(im,(x,y),m); d.text((x+10,y+S+10),k,fill=(30,30,30),font=f)
out.save('ACIK_ZEMIN_V2.jpg',quality=92); print('ok')
