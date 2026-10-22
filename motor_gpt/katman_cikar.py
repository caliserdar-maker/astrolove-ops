# 78 onayli ana sembol katmanini (ChatGPT yuzeyi + alfa, RGBA PNG) cikar (8 Eki 2026, siparis hatti kaliciligi).
# Kaynak tablo: hangi ChatGPT ciktisi + hangi temiz girdi + hangi alfa klasoru posterde kullanildi.
# Cikti: katman78/<CIFT>_ana.png (+ .json konum), katman78/MANIFEST.json (sha256). Ilerleme: katman78/ilerleme.json
import os, csv, glob, json, time, hashlib, subprocess
B = '/home/claude/blender'; GS = '/home/claude/gs/gpt_sembol/girdi'; O = f'{B}/katman78'
os.makedirs(O, exist_ok=True)
A_AB = {'PISCES_VIRGO', 'CAPRICORN_LEO', 'CAPRICORN_GEMINI'}
A_A2 = {'SAGITTARIUS_SCORPIO', 'CAPRICORN_SCORPIO', 'CAPRICORN_CAPRICORN', 'CANCER_LEO', 'GEMINI_VIRGO'}
def kaynak(c):
    if c in A_AB: g = f'{B}/gpt_ab/{c}__A_gpt.png'
    elif c in A_A2: g = f'{B}/gpt_a2/{c}__A_gpt.png'
    elif c in ('ARIES_LEO', 'CANCER_LIBRA'): g = f'{B}/gpt_api1/{c}_gpt.png'
    else: g = sorted(glob.glob(f'{B}/gpt_api_all/{c}_gpt_k*.png'), key=os.path.getmtime)[-1]
    if c == 'GEMINI_VIRGO': t, kd = f'{GS}/GEMINI_VIRGO_temiz.png', 'gi_gv'
    elif c in ('ARIES_LEO', 'CANCER_LIBRA'): t, kd = f'{GS}/{c}_temiz.png', 'gi_3'
    else: t, kd = f'{B}/gi_all_girdi/{c}_temiz.png', 'gi_all'
    return g, t, kd
cs = [r['cift'] for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv'))]
IL = f'{O}/ilerleme.json'
il = json.load(open(IL)) if os.path.exists(IL) else {}
T0 = time.time(); n0 = sum(1 for c in cs if il.get(c) == 'TAMAM')
for i, c in enumerate(cs, 1):
    if il.get(c) == 'TAMAM': continue
    g, t, kd = kaynak(c)
    p = subprocess.run([f'{B}/venv/bin/python', f'{B}/gpt_birlestir2.py', c, g, t, kd, '/tmp/katman_bos', 'KILIT_GPTGIRDI.json'],
                       capture_output=True, text=True, cwd=B, env=dict(os.environ, KATMAN_YOL=f'{O}/{c}_ana.png'))
    il[c] = 'TAMAM' if p.returncode == 0 and os.path.exists(f'{O}/{c}_ana.png') else 'HATA: ' + (p.stdout + p.stderr)[-300:]
    json.dump(il, open(IL, 'w'), indent=1)
    k = sum(1 for x in cs if il.get(x) == 'TAMAM'); g_ = time.time() - T0
    print(f'[{k}/78] {c} {il[c][:5]} | gecen {g_/60:.1f} dk | kalan ~{g_/max(k-n0,1)*(78-k)/60:.1f} dk | %{100*k//78}', flush=True)
man = {}
for c in cs:
    f = f'{O}/{c}_ana.png'
    if os.path.exists(f):
        man[c] = dict(dosya=os.path.basename(f), sha256=hashlib.sha256(open(f, 'rb').read()).hexdigest(), bayt=os.path.getsize(f),
                      **json.load(open(f + '.json')))
json.dump(man, open(f'{O}/MANIFEST.json', 'w'), indent=1)
print('MANIFEST', len(man))
