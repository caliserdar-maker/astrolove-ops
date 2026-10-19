import numpy as np, time
from PIL import Image
from scipy import ndimage
o=np.asarray(Image.open('sahne/orange.png').convert('RGB')).astype(float)
H,W=o.shape[:2]; yy,xx=np.mgrid[0:H,0:W]
yan=((xx<375)|(xx>1555))&(yy>520)&(yy<1240)
t0=time.time()
for i,st in enumerate(['pomegranate','loquat','almond','fig','olive','lemon','grape'],1):
    a=np.asarray(Image.open(f'sahne2/{st}.png').convert('RGB')).astype(float)
    d=np.abs(ndimage.gaussian_filter(a,(2,2,0))-ndimage.gaussian_filter(o,(2,2,0))).max(-1)
    m=ndimage.binary_opening((d>14)&yan,iterations=2)
    lab,n=ndimage.label(m); sz=ndimage.sum(np.ones_like(d),lab,range(1,n+1))
    m=np.isin(lab,np.where(np.asarray(sz)>400)[0]+1)
    m=ndimage.binary_fill_holes(ndimage.binary_dilation(m,iterations=18))&yan
    w=ndimage.gaussian_filter(m.astype(float),8)
    out=o*(1-w[...,None])+a*w[...,None]
    # duzenleme kutusu alt sinirindaki duz cizgi (kulp ustu): meyve satiri ile kulp arasindaki duvar renkli serit inpaint
    iz=np.zeros((H,W),bool)
    for xs in (slice(200,380),slice(1545,1760)):
        for y0 in range(830,900):
            ust=np.abs(a[y0-1,xs]-o[y0-1,xs]).max(-1)>30
            ayni=np.abs(a[y0,xs]-o[y0,xs]).max(-1)<6
            duvar=(o[y0,xs].mean(-1)>200)&(o[y0,xs].mean(-1)<238)
            mm=ust&ayni&duvar
            if mm.sum()>8:
                for y in range(y0,y0+6):
                    dv=(np.abs(a[y,xs]-o[y,xs]).max(-1)<6)&(o[y,xs].mean(-1)>200)&(o[y,xs].mean(-1)<238)
                    iz[y,xs]|=dv&ndimage.binary_dilation(mm,iterations=3)
    if iz.any():
        import cv2
        iz=ndimage.binary_dilation(iz,iterations=2)
        out8=np.clip(out,0,255).astype(np.uint8)
        out=cv2.inpaint(out8[...,::-1].copy(),(iz*255).astype(np.uint8),6,cv2.INPAINT_TELEA)[...,::-1].astype(float)
    print(st,'iz px',int(iz.sum()))
    Image.fromarray(np.clip(out,0,255).astype(np.uint8)).save(f'sahne/{st}.png')
    g=time.time()-t0; print(f'[{i}/7 %{100*i//7}] {st} (gecen {g:.0f}s, kalan ~{g/i*(7-i):.0f}s)',flush=True)
