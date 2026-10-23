import json, subprocess, time, sys, os
import numpy as np
from PIL import Image
U='/root/.claude/uploads/bb073d2e-646d-54a5-b165-25c930fef029/'
ims={'orange':'abe49b5a','fig':'08de4ded','olive':'0029f708','pomegranate':'d67216ec','almond':'f7ffee5e','lemon':'11e912b5','grape':'ebfc9849','loquat':'c72c5589'}
olc={}
for l in open('olc8.txt'):
    p=l.split(); ad=p[1]; v=json.loads(' '.join(p[2:]))
    olc[ad]=v
base=json.load(open('geo_base.json'))
t0=time.time(); n=len(ims)
for i,(st,f) in enumerate(ims.items(),1):
    on=olc[st+'_on']; ar=olc[st+'_arka']
    dy=round(ar[3]-906)
    g=json.loads(json.dumps(base))
    g['on'].update(xc=(on[0]+on[1])/2, R=(on[1]-on[0])/2+3, ust=437+dy, alt=927+dy, taban_kenar=923+dy)
    g['arka'].update(xc=(ar[0]+ar[1])/2, R=(ar[1]-ar[0])/2+3, ust=437+dy, alt=927+dy, taban_kenar=923+dy)
    dxo=g['on']['xc']-398; dxa=g['arka']['xc']-855
    P=6
    g['yazi_on']=[[round(b[0]+dxo-P),round(b[1]+dy-P),round(b[2]+dxo+P),round(b[3]+dy+P)] for b in base['yazi_on']]
    g['yazi_arka']=[[round(b[0]+dxa-P-(14 if j==0 else 0)),round(b[1]+dy-P-(10 if j==0 else 0)),round(b[2]+dxa+P+(14 if j==0 else 0)),round(b[3]+dy+P+(30 if j==0 else 0))] for j,b in enumerate(base['yazi_arka'])]
    Y=g['yerlesim']
    for k in ('on_merkez_x',): Y[k]=base['yerlesim'][k]+dxo
    for k in ('nazar_x','arka_merkez_x'): Y[k]=base['yerlesim'][k]+dxa
    for k in ('sembol_y','glif_y','isim_taban','burc_taban','nazar_y','mesaj_taban','imza_taban'): Y[k]=base['yerlesim'][k]+dy
    json.dump(g,open(f'geo_{st}.json','w'),indent=1)
    # yazi rengi: isim satiri en koyu %3
    a=np.asarray(Image.open(U+f+'-image.png').convert('RGB')).astype(float)
    r=a[int(Y['isim_taban']-24):int(Y['isim_taban']), int(Y['on_merkez_x']-100):int(Y['on_merkez_x']+100)].reshape(-1,3)
    Lm=r.mean(1); renk=r[Lm<np.percentile(Lm,3)].mean(0).round().astype(int)
    renk=','.join(str(v) for v in renk)
    subprocess.run(['python3','-I','kes_suslme.py',U+f+'-image.png',f'geo_{st}.json',st.upper()],check=True,capture_output=True)
    # renk canlandirma
    for yz in ('on','arka'):
        x=np.asarray(Image.open(f'{st.upper()}_{yz}.png').convert('RGB')).astype(float)
        gr=x.mean(-1,keepdims=True); w=np.clip((255-x.min(-1,keepdims=True))/60,0,1)
        b=255*(np.clip(gr+(x-gr)*1.15,0,255)/255)**1.12
        Image.fromarray(np.clip(x*(1-w)+b*w,0,255).astype(np.uint8)).save(f'{st.upper()}R_{yz}.png')
    os.system(f'cp {st.upper()}_kes.json {st.upper()}R_kes.json')
    out=subprocess.run(['python3','-I','baski_kes.py',f'{st.upper()}R','../mock/in','Serdar','Lena','Cancer','Libra','My favorite place is with you',renk,f'B_{st}'],capture_output=True,text=True)
    son=[l for l in out.stdout.splitlines() if 'on:' in l or 'tasma' in l]
    g_=time.time()-t0
    print(f'[{i}/{n} %{100*i//n}] {st}: renk {renk} dy {dy} | {" | ".join(x.split("] ")[1] for x in son)}  (gecen {g_:.0f}s, kalan ~{g_/i*(n-i):.0f}s)', out.stderr[-300:] if out.returncode else '', flush=True)
