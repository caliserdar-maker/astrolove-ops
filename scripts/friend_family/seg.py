import numpy as np, cv2
from PIL import Image
def yukle(ad): return np.asarray(Image.open(f"cg_{ad}.png").convert("RGB")).astype(np.float32)
def hsv(A): return cv2.cvtColor(np.clip(A,0,255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
BOLGE=(70, 900, 190, 930)   # y0,y1,x0,x1: sembol bolgesi (isimlerin ustu)
def ham(ad, A):
    h=hsv(A); H,S,V=h[...,0],h[...,1],h[...,2]
    if ad=="kagit": m=(V<130)&(A[...,1]>A[...,0])
    elif ad=="nakis": m=((H<12)|(H>170))&(S>90)&(V>90)
    elif ad=="mozaik": m=(H>100)&(H<130)&(S>110)&(V>60)
    elif ad=="vitray": m=((H>140)|(H<8))&(S>60)&(V<170)
    elif ad=="ahsap": m=None
    return m
def temizle(m, ad):
    y0,y1,x0,x1=BOLGE; b=np.zeros_like(m); b[y0:y1,x0:x1]=m[y0:y1,x0:x1]
    b=cv2.morphologyEx(b.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(b,8)
    keep=np.zeros_like(b)
    for i in range(1,n):
        if st[i,4]>800: keep[lab==i]=1
    return keep
if __name__=="__main__":
    ana=np.asarray(Image.open("ana.png"))[...,3]>127
    ys,xs=np.where(ana); ana=ana[ys.min():ys.max()+1, xs.min():xs.max()+1]
    for ad in ["kagit","nakis","mozaik","vitray"]:
        A=yukle(ad); m=temizle(ham(ad,A),ad)
        ys,xs=np.where(m); y0,y1,x0,x1=ys.min(),ys.max(),xs.min(),xs.max()
        o=cv2.resize(ana.astype(np.uint8),(x1-x0+1,y1-y0+1),interpolation=cv2.INTER_AREA)>0
        mm=m[y0:y1+1,x0:x1+1]>0
        iou=(o&mm).sum()/(o|mm).sum()
        print(ad,"bbox",x0,x1,y0,y1,"en/boy",round((x1-x0)/(y1-y0),3),"orijinal en/boy",round(ana.shape[1]/ana.shape[0],3),"IoU",round(iou,3))
        np.save(f"m_{ad}.npy",m)
