import numpy as np, subprocess, time
from PIL import Image
B='/tmp/claude-0/-home-claude/bb073d2e-646d-54a5-b165-25c930fef029/scratchpad/orchardB/'
RENKLER={'orange':'10,40,24','fig':'52,18,48','olive':'12,24,78','pomegranate':'100,16,24','almond':'52,22,14','lemon':'12,22,76','grape':'16,30,90','loquat':'62,24,10'}
st8=['orange','fig','olive','pomegranate','almond','lemon','grape','loquat']
t0=time.time()
for i,st in enumerate(st8,1):
    s=1.095; x0,y0=85,84; K=40
    a=np.asarray(Image.open(f'sahne/{st}.png').convert('RGB').resize((2048,2048),Image.LANCZOS,box=(x0,y0,x0+2048/s,y0+2048/s)))
    ust=np.asarray(Image.fromarray(a[:200]).resize((2048,200+K),Image.LANCZOS))
    Image.fromarray(np.concatenate([ust,a[200:2048-K]],0)).save(f'sahne/{st}_k40.png')
    subprocess.run(['python3','-I',B+'kod/kapak_canva3.py',f'sahne/{st}_k40.png',f'B_{st}_baski_11oz.png',B+'geo_kapak_k40.json',f'sahne/{st}_giydir.jpg'],check=True,capture_output=True,env={'GOLGE_US':'0.4','PARLA':'0.7','PATH':'/usr/bin:/bin'})
    subprocess.run(['python3','-I',B+'kod/baslik4.py',f'sahne/{st}_giydir.jpg','Cancer','Libra',f'KAPAK_{st}.jpg'],check=True,capture_output=True,env={'RENK':RENKLER[st],'PATH':'/usr/bin:/bin'})
    g=time.time()-t0; print(f'[{i}/8 %{100*i//8}] {st} (gecen {g:.0f}s, kalan ~{g/i*(8-i):.0f}s)',flush=True)
