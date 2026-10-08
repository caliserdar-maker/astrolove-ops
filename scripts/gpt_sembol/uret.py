# ChatGPT resim modeli (OpenAI API) ile ana sembol baglanti uretimi (7 Eki 2026, Serdar onayi).
# Girdi (gpt_sembol/girdi): STIL.png + her cift icin <CIFT>_temiz.png ve <CIFT>_kirmizi.png. Is listesi: gpt_sembol/is.txt
# Cikti (cikti/): <CIFT>_gpt.png + rapor.json (model, token kullanimi, tahmini maliyet, hata).
# Anahtar: ortam OPENAI_API_KEY (Drive TEMP/OPENAI_API_KEY.txt, workflow maskeler). Anahtar hicbir yere yazilmaz.
# Ust sinir: tahmini toplam maliyet BUTCE_USD'yi asarsa yeni istek atilmaz.
import os, sys, json, time, base64, requests

KEY = os.environ['OPENAI_API_KEY'].strip()
GIR = 'gpt_sembol/girdi'
OUT = 'cikti'
os.makedirs(OUT, exist_ok=True)
BUTCE = float(os.environ.get('BUTCE_USD', '5'))
MODELLER = [m.strip() for m in os.environ.get('MODELLER', 'gpt-image-2').split(',') if m.strip()]
# fiyat (USD / 1M token), openai.com/api/pricing 7 Eki 2026; tablo belirsiz oldugundan YUKSEK olan kullanilir (temkinli)
FIYAT = dict(metin_girdi=5.0, resim_girdi=8.0, resim_cikti=30.0)

ISTEM = (
    "Image 1 is the clean gold zodiac symbol. Image 2 is the same symbol with RED lines drawn at the junctions. "
    "Image 3 is the style reference.\n\n"
    "Edit Image 1 only. Every red line in Image 2 is a RIDGE: a sharp, continuous raised crest that runs straight "
    "through the junction without breaking, exactly like the ridges in Image 3. Where two strokes cross or merge, "
    "the ridge of one stroke flows continuously into the ridge of the other.\n\n"
    "Everywhere else the metal is a smooth, rounded transition: no notches, no dents, no creases, no flat spots, "
    "no dark seams at any junction.\n\n"
    "Do NOT draw the red lines. Do NOT change the outline, thickness or shape of the symbol. Do NOT change the "
    "background. Keep the same gold color and lighting as Image 3. Output the same framing as Image 1."
)

def maliyet(u):
    if not u: return None
    d = u.get('input_tokens_details') or {}
    mt = d.get('text_tokens', 0); rt = d.get('image_tokens', 0)
    if not (mt or rt): rt = u.get('input_tokens', 0)
    ct = u.get('output_tokens', 0)
    return round((mt * FIYAT['metin_girdi'] + rt * FIYAT['resim_girdi'] + ct * FIYAT['resim_cikti']) / 1e6, 4)

def dosya(ad):
    for uz, mt in (('.jpg', 'image/jpeg'), ('.png', 'image/png')):
        if os.path.exists(f'{GIR}/{ad}{uz}'): return (f'{ad}{uz}', open(f'{GIR}/{ad}{uz}', 'rb'), mt)
    raise FileNotFoundError(ad)

# Ogeler (kucuk semboller, sonsuz, harf atlasi; kirmizi hat yok): 2 resim (pafta + stil)
ISTEM_OGE = (
    "Image 1 shows gold zodiac glyphs or gold lettering on a dark navy background. Image 2 is the style reference.\n\n"
    "Edit Image 1 only. Re-render every gold element with exactly the same gold metal, surface, bevel, color and "
    "lighting as the gold symbol in Image 2: smooth, rounded, polished metal with a soft highlight running along each "
    "stroke. Where strokes meet or cross, the ridges flow continuously into each other with smooth transitions: no "
    "notches, no dents, no dark seams.\n\n"
    "Do NOT change the shape, outline, thickness, size or position of any element. Do NOT add, remove, merge or "
    "redraw any letter, mark or symbol; keep every letter exactly as it is. Do NOT change the background. "
    "Output the same framing as Image 1."
)

# Ana sembol, kirmizi hatsiz (deneme a, 8 Eki): ChatGPT hangi cizginin devam ettigine kendisi karar verir
ISTEM_A = (
    "Image 1 is a gold zodiac symbol made of two zodiac glyphs merged into one design. Image 2 is the style reference.\n\n"
    "Edit Image 1 only. Re-render the gold metal exactly like the symbol in Image 2. Every stroke has one sharp, "
    "continuous raised RIDGE along its center. Where two strokes cross, each stroke's ridge runs straight through the "
    "crossing without breaking, and the two ridges cross at a single point. Where a stroke merges into another, its "
    "ridge flows smoothly into the ridge of the stroke it joins. Everywhere else the metal is a smooth, rounded "
    "transition: no notches, no dents, no pinches, no creases, no flat spots, no dark seams at any junction.\n\n"
    "Do NOT change the outline, thickness or shape of the symbol. Do NOT connect strokes that are separate, and do "
    "NOT separate strokes that touch. Do NOT change the background. Keep the same gold color and lighting as Image 2. "
    "Output the same framing as Image 1."
)

# Yontem A + uc kurali (8 Eki 2026 gece, CANCER_LIBRA / CAPRICORN_LIBRA): ChatGPT uclari kaynaktan uzatiyordu
ISTEM_A2 = ISTEM_A + (
    "\n\nThe stroke ENDS (tips) must keep exactly the same length, shape and position as in Image 1. Do NOT extend, lengthen, "
    "sharpen further or move any tip. Do NOT bring two tips closer together and NEVER join them; the empty gap between nearby "
    "tips must stay exactly as wide as in Image 1. Keep the whole symbol inside the frame with the same margins as Image 1."
)

ISTEM_A3 = ISTEM_A2 + (
    "\n\nTrace the outline of Image 1 exactly: every stroke keeps exactly the same width, curve and position as in Image 1 along "
    "its whole length. Only the surface (metal shading) changes."
)

def istek(model, c, ek):
    if c.endswith('__A3'):
        files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya('STIL'))]
        data = dict(model=model, prompt=ISTEM_A3, n='1', **ek)
        return gonder(files, data)
    if c.endswith('__A2'):
        files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya('STIL'))]
        data = dict(model=model, prompt=ISTEM_A2, n='1', **ek)
        return gonder(files, data)
    if c.endswith('__A'):
        files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya('STIL'))]
        data = dict(model=model, prompt=ISTEM_A, n='1', **ek)
        return gonder(files, data)
    if os.path.exists(f'{GIR}/{c}_kirmizi.jpg') or os.path.exists(f'{GIR}/{c}_kirmizi.png'):
        files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya(f'{c}_kirmizi')), ('image[]', dosya('STIL'))]
        data = dict(model=model, prompt=ISTEM, n='1', **ek)
    else:
        files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya('STIL'))]
        data = dict(model=model, prompt=ISTEM_OGE, n='1', **ek)
    return gonder(files, data)

def gonder(files, data):
    for dene in range(6):                      # hiz siniri (429, kota disi): bekle ve tekrar dene
        r = requests.post('https://api.openai.com/v1/images/edits', headers={'Authorization': f'Bearer {KEY}'},
                          data=data, files=files, timeout=600)
        if r.status_code == 429 and 'quota' not in r.text.lower() and 'billing' not in r.text.lower():
            time.sleep(60); [f[1][1].seek(0) for f in files]; continue
        return r
    return r

isler = [l.strip() for l in open('gpt_sembol/is.txt') if l.strip() and not l.startswith('#')]
rapor = dict(isler=isler, sonuc=[], toplam_usd=0.0, butce_usd=BUTCE)
T0 = time.time()
model_ok = None
for i, c in enumerate(isler, 1):
    if rapor['toplam_usd'] >= BUTCE:
        rapor['sonuc'].append(dict(cift=c, durum='ATLANDI_BUTCE')); continue
    t0 = time.time(); kayit = dict(cift=c)
    adaylar = [model_ok] if model_ok else MODELLER
    for model in adaylar:
        # tam ayar -> sade ayar (model desteklemeyen parametreyi reddederse)
        for ek in (dict(size='auto', quality='high'),):
            r = istek(model, c, ek)
            if r.status_code == 200: break
            kayit.setdefault('denemeler', []).append(dict(model=model, ek=list(ek), kod=r.status_code, hata=r.text[:400]))
            if r.status_code in (401, 429) or 'billing' in r.text.lower() or 'quota' in r.text.lower(): break
        if r.status_code == 200: break
        if r.status_code in (401, 429): break
    if r.status_code == 200:
        j = r.json(); model_ok = model
        open(f'{OUT}/{c}_gpt.png', 'wb').write(base64.b64decode(j['data'][0]['b64_json']))
        u = j.get('usage'); m = maliyet(u)
        rapor['toplam_usd'] = round(rapor['toplam_usd'] + (m or 0), 4)
        kayit.update(durum='TAMAM', model=model, ayar=list(ek), usage=u, usd=m, sn=round(time.time() - t0, 1))
    else:
        kayit.update(durum='HATA', kod=r.status_code)
    rapor['sonuc'].append(kayit)
    gec = time.time() - T0
    print(f'[{i}/{len(isler)}] {c} {kayit["durum"]} | {time.time()-t0:.0f} sn | gecen {gec/60:.1f} dk | '
          f'kalan ~{gec/i*(len(isler)-i)/60:.1f} dk | %{100*i/len(isler):.0f} | toplam ${rapor["toplam_usd"]}', flush=True)
    json.dump(rapor, open(f'{OUT}/rapor.json', 'w'), indent=1, ensure_ascii=False)
    if kayit['durum'] == 'HATA' and kayit['kod'] in (401, 429): break
json.dump(rapor, open(f'{OUT}/rapor.json', 'w'), indent=1, ensure_ascii=False)
sys.exit(0 if all(s.get('durum') == 'TAMAM' for s in rapor['sonuc']) else 1)
