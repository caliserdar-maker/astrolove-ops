"""11 oz tek kupa sahnesinden 15 oz sahne: genislik 8,5/8,2 olcegi + govde ortasi dikey uzatma (oranlar Printful olculerinden)."""
import json, numpy as np
from PIL import Image
B='../orchardB/'
im=Image.open(B+'ORCHARD_OrangeBlossom_sahne_tek_on.png').convert('RGB')
g=json.load(open(B+'geo_tek_on.json'))['sol']; xl,xr,yt,yb,et,eb=g
k=8.5/8.2
W=im.width
im2=im.resize((round(W*k),round(W*k)),Image.LANCZOS)
xl2,xr2,yt2,yb2,et2,eb2=[v*k for v in g]
Hb=yb2-yt2; Db=xr2-xl2
oran11=(yb-yt)/(xr-xl)
hedef=oran11*(11.9/8.5)/(9.6/8.2)*Db
ek=round(hedef-Hb)
a=np.asarray(im2)
y0,y1=round(yt2+Hb*0.42),round(yt2+Hb*0.58)
orta=np.asarray(Image.fromarray(a[y0:y1]).resize((a.shape[1],y1-y0+ek),Image.LANCZOS))
b=np.concatenate([a[:y0],orta,a[y1:]],0)
Image.fromarray(b).save('kart/sahne15.png')
json.dump({'sol':[round(xl2,1),round(xr2,1),round(yt2,1),round(yb2+ek,1),round(et2,1),round(eb2,1)]},open('kart/geo15.json','w'))
print('ek',ek,'boyut',b.shape,'H/D 11',round(oran11,3),'15',round((Hb+ek)/Db,3))
