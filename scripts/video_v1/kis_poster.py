"""kisisel-v1 onayli isim kodu (pilot16.oran_kur + poster_kur) ile 4x5 poster: argv = SOL SAG TAGLINE CIKTI"""
import json, sys, time
sys.path.insert(0, '.')
from PIL import Image
import pilot12, pilot16
import giris_dogrula as gd
from pilot11 import OUT
t0 = time.time()
pilot12.profil_yukle(OUT / 'ref' / 'names')
olc = json.load(open(OUT / 'ORANLAR' / 'OLCUM_4x5.json'))['4x5']
s, S = pilot16.oran_kur('4x5', olc, Image.open(OUT / 'hazir' / 'bg.png'))
S['prof'] = pilot12.PROFIL
out = []
for sol, sag, tag, yol in [a.split('|') for a in sys.argv[1:]]:
    r = gd.siparis_dogrula(sol, sag, tag, None)
    p, bilgi, merkez, x, yeni = pilot16.poster_kur(s, S, {'sol': r['sol']['deger'], 'sag': r['sag']['deger']}, tag)
    bk = pilot16.blok_kapisi(p, S, s, yeni)
    p.save(yol); out.append({'cift': [sol, sag], 'tag': tag, 'bilgi': bilgi, 'blok_kapisi': {k: v for k, v in bk.items() if k != 'kotu'} if isinstance(bk, dict) else bk})
    print(f'{sol}|{sag} {time.time()-t0:.0f}s punto={bilgi["punto"]} satir_merkez={bilgi["satir_merkez"]}', flush=True)
json.dump(out, open(sys.argv[-1].split('|')[-1] + '.json', 'w'), indent=1, default=str)
