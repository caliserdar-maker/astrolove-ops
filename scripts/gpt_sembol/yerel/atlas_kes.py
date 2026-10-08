# Atlas paftalarini motor cizimlerinden kes: atlas/girdi/<pafta>_temiz.png (uzun kenar 1536) + gs girdisine jpg.
import json, os
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
B = '/home/claude/blender/'; O = B + 'atlas/'; GS = '/home/claude/gs/gpt_sembol/girdi/'
J = json.load(open(O + 'atlas.json'))
os.makedirs(O + 'girdi', exist_ok=True)
acik = {}
for p in J['paftalar']:
    t = p['tur']
    if t not in acik: acik[t] = Image.open(f'{O}{t}/SV_BLENDER_tam.png').convert('RGB')
    x0, y0, x1, y1 = p['kutu']
    im = acik[t].crop((x0, y0, x1, y1))
    s = 1536 / max(im.size); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    p['olcek'] = s
    im.save(f'{O}girdi/{p["ad"]}_temiz.png')
    im.save(f'{GS}{p["ad"]}_temiz.jpg', quality=95, subsampling=0)
    print(p['ad'], im.size)
json.dump(J, open(O + 'atlas.json', 'w'), ensure_ascii=False, indent=1)
