import sys, math
from PIL import Image, ImageDraw
import numpy as np
src, out, wmax, renk = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
im = Image.open(src).convert("RGB"); a = np.array(im)
bolge = a[1120:1370, 850:2150].astype(int)
ys, xs = np.nonzero(bolge.sum(2) < 600)
zemin = tuple(int(v) for v in np.median(a[1200:1220, 300:400].reshape(-1,3), 0))
d = ImageDraw.Draw(im); d.rectangle([850, 1120, 2150, ys.max()+1120+4], fill=zemin)
S = 4; W, H = im.size
lay = Image.new("L", (W*S, H*S), 0); ld = ImageDraw.Draw(lay)
def bez(p0,p1,p2,p3,t):
    u=1-t
    return np.array([u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0],
                     u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]])
cx = 1500; y0 = 1145; tip = ys.max()+1120-2
xl = int(xs.min()+850); xr = int(xs.max()+850)
n = 600
for x0 in (xl, xr):
    P = [(x0,y0),(x0,y0+120),(cx+(x0-cx)*0.08,y0+55),(cx,tip)]
    pts = np.array([bez(*P, i/n) for i in range(n+1)])
    tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1)[:,None]
    nor = np.stack([-tan[:,1], tan[:,0]], 1)
    t = np.linspace(0,1,n+1)
    w = wmax * np.sin(np.pi*t)**0.8          # iki ucta sifir: keskin uc
    L = pts + nor*w[:,None]/2; R = pts - nor*w[:,None]/2
    poly = [tuple(p*S) for p in L] + [tuple(p*S) for p in R[::-1]]
    ld.polygon(poly, fill=255)
lay = lay.resize((W,H), Image.LANCZOS)
rgb = tuple(int(renk[i:i+2],16) for i in (0,2,4))
im = Image.composite(Image.new("RGB",(W,H),rgb), im, lay)
im.save(out, quality=95)
im.crop((850,1100,2150,1420)).save(out.replace('.jpg','_ok.png'))
