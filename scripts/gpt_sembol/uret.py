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

def istek(model, c, ek):
    files = [('image[]', dosya(f'{c}_temiz')), ('image[]', dosya(f'{c}_kirmizi')), ('image[]', dosya('STIL'))]
    data = dict(model=model, prompt=ISTEM, n='1', **ek)
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
