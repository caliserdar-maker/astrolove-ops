# 78 poster onizleme sayfasi (8 Eki 2026 sabahi icin). Kucuk resim 400x600, buyuk 1000x1500.
import os, json, csv, html
from PIL import Image
B = '/home/claude/blender'
OUT = '/tmp/claude-0/-home-claude-astrolove-ops/f112981d-1cac-52e8-aa68-65cb1fcbc2fc/scratchpad/galeri78'
os.makedirs(f'{OUT}/k', exist_ok=True); os.makedirs(f'{OUT}/b', exist_ok=True)
qc = json.load(open(f'{B}/qc_toplu.json'))
satir = list(csv.DictReader(open(f'{B}/isim_tagline_78.csv')))
test = {'GEMINI_VIRGO': 0.939, 'ARIES_LEO': 0.926, 'CANCER_LIBRA': 0.895}
ogeler = []
for r in satir:
    c = r['cift']
    if c in test:
        src = f'{B}/gb_api/{c}/{c}_GPT_2000.jpg'; durum, iou, not_ = 'PASS', test[c], 'deneme (onayli)'
    else:
        q = qc.get(c, {}); src = f'{B}/gb_all/{c}/{c}_GPT_2000.jpg'
        durum = q.get('son', 'YOK'); iou = q.get('iou') or (q.get('olcum') or [{}])[-1].get('iou')
        not_ = 'yeniden uretildi' if len(q.get('api', [])) > 1 or q.get('api_hata') else ''
        if durum != 'PASS' and not os.path.exists(src): src = None
    if src and os.path.exists(src):
        im = Image.open(src).convert('RGB')
        im.resize((1000, 1500), Image.LANCZOS).save(f'{OUT}/b/{c}.jpg', quality=86)
        im.resize((400, 600), Image.LANCZOS).save(f'{OUT}/k/{c}.jpg', quality=82)
        var = True
    else:
        var = False
    ogeler.append(dict(c=c, ad=c.replace('_', ' + ').title(), isim=f"{r['sol_isim']} & {r['sag_isim']}",
                       durum=durum, iou=iou, not_=not_, var=var))
json.dump(ogeler, open(f'{OUT}/veri.json', 'w'), ensure_ascii=False)
n_pass = sum(o['durum'] == 'PASS' for o in ogeler)
sorun = [o for o in ogeler if o['durum'] != 'PASS']
usd = qc.get('_usd_toplam')
kartlar = []
for o in ogeler:
    cls = 'ok' if o['durum'] == 'PASS' else 'kotu'
    etiket = 'Geçti' if o['durum'] == 'PASS' else ('Kontrol et' if o['var'] else 'Üretilemedi')
    iou = f"{o['iou']:.3f}" if isinstance(o['iou'], (int, float)) else '–'
    img = (f'<button class="ac" data-c="{o["c"]}" aria-label="{html.escape(o["ad"])} büyüt"><img loading="lazy" src="k/{o["c"]}.jpg" alt="{html.escape(o["ad"])} posteri" width="400" height="600"></button>'
           if o['var'] else '<div class="bos">Resim yok</div>')
    kartlar.append(f'''<li class="kart {cls}" data-durum="{cls}">{img}
<div class="alt"><span class="ad">{html.escape(o["ad"])}</span><span class="chip {cls}">{etiket}</span></div>
<div class="olc"><span>{html.escape(o["isim"])}</span><span class="num">şekil {iou}</span></div>{f'<div class="not">{o["not_"]}</div>' if o["not_"] else ''}</li>''')
sorun_html = ''.join(f'<li><b>{html.escape(o["ad"])}</b>: {"resim yok" if not o["var"] else "şekil ölçümü eşik altında"}</li>' for o in sorun) or '<li>Yok</li>'
sayfa = f'''<title>AstroLoveArt 78 Poster</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Yerlesim: ozet bandi, sonra posterlerin duzgun izgarasi; tek koyu gorunum (posterlerin lacivert zemini) */
:root {{
  --zemin: #0b1022; --yuzey: #131a33; --cizgi: #263056; --metin: #ece4cf; --soluk: #9fa3b8;
  --altin: #d8b25c; --iyi: #7fc49a; --kotu: #e58a6f;
  --f-bas: "Cormorant Garamond", "EB Garamond", Georgia, serif;
  --f-govde: "IBM Plex Sans", system-ui, sans-serif;
  color-scheme: dark;
}}
body {{ background: var(--zemin); color: var(--metin); font-family: var(--f-govde); font-size: 15px; }}
.sar {{ max-width: 1280px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 48px; display: grid; gap: 28px; }}
h1 {{ font-family: var(--f-bas); font-weight: 600; font-size: clamp(30px, 5vw, 44px); margin: 0; letter-spacing: .01em; text-wrap: balance; color: var(--altin); }}
.ozet {{ display: grid; gap: 14px; }}
.sayi {{ display: flex; flex-wrap: wrap; gap: 10px 28px; color: var(--soluk); font-variant-numeric: tabular-nums; }}
.sayi b {{ color: var(--metin); font-weight: 600; }}
.sorun {{ border: 1px solid var(--cizgi); border-radius: 8px; padding: 12px 16px; background: var(--yuzey); }}
.sorun h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: var(--soluk); margin: 0 0 6px; font-weight: 500; }}
.sorun ul {{ margin: 0; padding-left: 18px; display: grid; gap: 4px; }}
.filtre {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.filtre button {{ font: inherit; color: var(--metin); background: transparent; border: 1px solid var(--cizgi); border-radius: 999px; padding: 6px 14px; cursor: pointer; }}
.filtre button[aria-pressed="true"] {{ background: var(--altin); color: var(--zemin); border-color: var(--altin); }}
button:focus-visible {{ outline: 2px solid var(--altin); outline-offset: 2px; }}
ul.izgara {{ list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 200px), 1fr)); gap: 22px 18px; }}
.kart {{ display: grid; gap: 6px; min-width: 0; }}
.ac {{ padding: 0; border: 0; background: none; cursor: zoom-in; display: block; }}
.ac img, .bos {{ width: 100%; height: auto; aspect-ratio: 2 / 3; display: block; border-radius: 3px; }}
.bos {{ display: grid; place-items: center; background: var(--yuzey); color: var(--soluk); border: 1px dashed var(--cizgi); }}
.kart.kotu .ac img {{ outline: 2px solid var(--kotu); outline-offset: 2px; }}
.alt, .olc {{ display: flex; justify-content: space-between; gap: 8px; align-items: baseline; min-width: 0; }}
.ad {{ font-weight: 500; overflow-wrap: anywhere; }}
.olc {{ color: var(--soluk); font-size: 13px; }}
.num {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
.not {{ font-size: 12px; color: var(--altin); }}
.chip {{ font-size: 12px; border-radius: 999px; padding: 2px 8px; white-space: nowrap; border: 1px solid currentColor; }}
.chip.ok {{ color: var(--iyi); }} .chip.kotu {{ color: var(--kotu); }}
.perde {{ position: fixed; inset: 0; background: rgb(5 8 18 / .92); display: grid; place-items: center; padding: 16px; z-index: 10; }}
.perde img {{ max-height: calc(100% - 56px); width: auto; max-width: 100%; }}
.perde .ust {{ position: absolute; top: calc(env(safe-area-inset-top, 0px) + 10px); left: 16px; right: 16px; display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
.perde button {{ font: inherit; color: var(--metin); background: var(--yuzey); border: 1px solid var(--cizgi); border-radius: 6px; padding: 6px 12px; cursor: pointer; }}
</style>
<div class="sar">
<header class="ozet">
<h1>78 Çift Poster: ChatGPT Bağlantılı Sürüm</h1>
<div class="sayi"><span><b>{n_pass}</b> / 78 geçti</span><span><b>{len(sorun)}</b> kontrol gerekli</span>{f'<span>API harcaması <b>${usd}</b></span>' if usd else ''}<span>Baskı dosyası: 7200 × 10800 px, JPEG q100</span></div>
<section class="sorun"><h2>Kontrol gerekenler</h2><ul>{sorun_html}</ul></section>
<div class="filtre" role="group" aria-label="Filtre"><button id="f-hepsi" aria-pressed="true" data-f="hepsi">Tümü</button><button id="f-kotu" aria-pressed="false" data-f="kotu">Yalnız kontrol gerekenler</button></div>
</header>
<ul class="izgara">{''.join(kartlar)}</ul>
</div>
<div class="perde" id="perde" hidden><div class="ust"><span id="p-ad"></span><button id="p-kapat">Kapat</button></div><img id="p-img" alt=""></div>
<script>
const perde = document.getElementById('perde'), pimg = document.getElementById('p-img'), pad = document.getElementById('p-ad');
document.querySelectorAll('.ac').forEach(b => b.addEventListener('click', () => {{
  pimg.src = 'b/' + b.dataset.c + '.jpg'; pimg.alt = b.getAttribute('aria-label'); pad.textContent = b.closest('.kart').querySelector('.ad').textContent;
  perde.hidden = false; document.getElementById('p-kapat').focus();
}}));
const kapat = () => {{ perde.hidden = true; pimg.removeAttribute('src'); }};
document.getElementById('p-kapat').addEventListener('click', kapat);
perde.addEventListener('click', e => {{ if (e.target === perde) kapat(); }});
document.addEventListener('keydown', e => {{ if (e.key === 'Escape' && !perde.hidden) kapat(); }});
document.querySelectorAll('.filtre button').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('.filtre button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  document.querySelectorAll('.kart').forEach(k => k.hidden = b.dataset.f === 'kotu' && k.dataset.durum !== 'kotu');
}}));
</script>
'''
open(f'{OUT}/index.html', 'w').write(sayfa)
print('PASS', n_pass, 'sorun', [o['c'] for o in sorun])
