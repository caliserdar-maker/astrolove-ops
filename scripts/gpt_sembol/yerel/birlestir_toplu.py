# Gece toplu birlestirme (7-8 Eki 2026): API ciktilarini (gpt-sembol-veri-<no> dallari) toplar, girdi hatti bitince
# her cifti postere yerlestirir (gpt_birlestir2), sekil kapisini olcer, FAIL olanlari bir kez API'ye geri yollar.
# Kapi: yeni alfa / kaynak alfa IoU >= 0.90 (onayli 3 cift: 0.895-0.961; 0.895 CANCER_LIBRA gozle temizdi -> esik 0.88)
import os, re, json, time, subprocess, glob, csv, io, tarfile, urllib.request
B = '/home/claude/blender'; GS = '/home/claude/gs'; REPO = '/home/claude/astrolove-ops'
API = 'https://api.github.com/repos/caliserdar-maker/astrolove-ops/actions/runs?branch=gpt-sembol&per_page=50'
CIK = f'{B}/gpt_api_all'; GB = f'{B}/gb_all'; GD = f'{B}/gi_all'; GG = f'{B}/gi_all_girdi'
ESIK = 0.88
os.makedirs(CIK, exist_ok=True); os.makedirs(GB, exist_ok=True)
QC = f'{B}/qc_toplu.json'
qc = json.load(open(QC)) if os.path.exists(QC) else {}
alinan = set(qc.get('_alinan_kosular', []))
tekrar = set(qc.get('_tekrar', []))
bitti_set = {'GEMINI_VIRGO', 'ARIES_LEO', 'CANCER_LIBRA'}
LISTE = [r['cift'] for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv')) if r['cift'] not in bitti_set]
T0 = time.time()
def log(*a):
    with open(f'{B}/birlestir_toplu.log', 'a') as f: print(time.strftime('%H:%M:%S'), *a, file=f, flush=True)
def kaydet():
    qc['_alinan_kosular'] = sorted(alinan); qc['_tekrar'] = sorted(tekrar)
    json.dump(qc, open(QC, 'w'), indent=1, ensure_ascii=False)

def ciktilari_al():
    try:
        runs = json.load(urllib.request.urlopen(API, timeout=60))['workflow_runs']
    except Exception as e:
        log('API okunamadi', e); return
    for r in runs:
        if r['status'] != 'completed' or r['run_number'] < 2 or r['run_number'] in alinan: continue
        dal = f"gpt-sembol-veri-{r['run_number']}"
        p = subprocess.run(['git', '-C', REPO, 'fetch', '-q', 'origin', dal], capture_output=True, text=True)
        if p.returncode:
            log('dal yok', dal, r['conclusion'], p.stderr[-200:]); alinan.add(r['run_number']); continue
        d = f'{CIK}/k{r["run_number"]}'; os.makedirs(d, exist_ok=True)
        t = subprocess.run(['git', '-C', REPO, 'archive', 'FETCH_HEAD'], capture_output=True).stdout
        tarfile.open(fileobj=io.BytesIO(t)).extractall(d)
        rap = json.load(open(f'{d}/rapor.json'))
        for s in rap['sonuc']:
            c = s['cift']
            if s.get('durum') == 'TAMAM':
                os.replace(f'{d}/{c}_gpt.png', f'{CIK}/{c}_gpt_k{r["run_number"]}.png')
                qc.setdefault(c, {}).setdefault('api', []).append(dict(kosu=r['run_number'], usd=s.get('usd')))
            else:
                qc.setdefault(c, {}).setdefault('api_hata', []).append(dict(kosu=r['run_number'], durum=s.get('durum'), kod=s.get('kod')))
        alinan.add(r['run_number']); kaydet()
        log('alindi', dal, r['conclusion'], 'toplam_usd', rap.get('toplam_usd'))

def girdi_bitti():
    return os.path.exists(f'{B}/toplu_gpt.log') and 'BITTI' in open(f'{B}/toplu_gpt.log').read()

def birlestir(c, gpt):
    d = f'{GB}/{c}'
    subprocess.run(['rm', '-rf', d])
    p = subprocess.run([f'{B}/venv/bin/python', f'{B}/gpt_birlestir2.py', c, gpt, f'{GG}/{c}_temiz.png', GD, GB, 'KILIT_GPTGIRDI.json'],
                       capture_output=True, text=True, cwd=B)
    m = re.search(r'yeni alfa / eski alfa IoU ([0-9.]+)', p.stdout)
    iou = float(m.group(1)) if m else None
    ok = p.returncode == 0 and os.path.exists(f'{d}/{c}_GPT_2000.jpg')
    return ok, iou, (p.stdout + p.stderr)[-600:]

def tekrar_gonder(ciftler):
    """sekil kapisi FAIL: ayni girdilerle bir kez daha API"""
    with open(f'{GS}/gpt_sembol/is.txt', 'w') as f: f.write('# gpt-sembol tekrar (sekil kapisi)\n' + '\n'.join(ciftler) + '\n')
    for c in ciftler:
        for t in ('temiz', 'kirmizi'):
            if not os.path.exists(f'{GS}/gpt_sembol/girdi/{c}_{t}.jpg'):
                subprocess.run([f'{B}/venv/bin/python', '-c', f"from PIL import Image; Image.open('{GG}/{c}_{t}.png').convert('RGB').save('{GS}/gpt_sembol/girdi/{c}_{t}.jpg', quality=95, subsampling=0)"])
    msg = f'gpt-sembol tekrar: {len(ciftler)} cift (sekil kapisi)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01TQ6T5qTE31RqB6ueSLiZsz'
    subprocess.run(f'cd {GS} && git add gpt_sembol && git commit -qm "{msg}" && git push -q origin gpt-sembol', shell=True)
    log('TEKRAR gonderildi', ciftler)

bekleyen_tekrar = []
son_olay = time.time()
while True:
    ciktilari_al()
    yapildi = False
    # API hatasi alan (resim yok) cift: bir kez tekrar
    for c in LISTE:
        st = qc.get(c, {})
        if st.get('api_hata') and not glob.glob(f'{CIK}/{c}_gpt_k*.png') and st.get('son') is None:
            if c not in tekrar: bekleyen_tekrar.append(c); tekrar.add(c); st['son'] = 'TEKRAR_BEKLIYOR'
            else: st['son'] = 'FAIL_KALICI'
            qc[c] = st; kaydet()
    if girdi_bitti():      # bellek: render ile birlestirme ayni anda kosmaz
        for c in LISTE:
            st = qc.get(c, {})
            if st.get('son') in ('PASS', 'FAIL_KALICI'): continue
            den = st.get('denenen', [])
            yeni = sorted([a for a in glob.glob(f'{CIK}/{c}_gpt_k*.png') if a not in den], key=os.path.getmtime)
            if not yeni: continue
            g = yeni[-1]; t0 = time.time()
            ok, iou, kuyruk = birlestir(c, g)
            st['denenen'] = den + [g]
            st.setdefault('olcum', []).append(dict(gpt=os.path.basename(g), ok=ok, iou=iou))
            if ok and iou is not None and iou >= ESIK:
                st['son'] = 'PASS'; st['iou'] = iou
            elif c not in tekrar:
                bekleyen_tekrar.append(c); tekrar.add(c); st['son'] = 'TEKRAR_BEKLIYOR'
            else:
                st['son'] = 'FAIL_KALICI'; st['hata'] = kuyruk
            qc[c] = st; kaydet(); yapildi = True; son_olay = time.time()
            n_bit = sum(1 for x in LISTE if qc.get(x, {}).get('son') in ('PASS', 'FAIL_KALICI'))
            gec = time.time() - T0
            log(f'[{n_bit}/{len(LISTE)}] {c} {st["son"]} IoU {iou} | {time.time()-t0:.0f} sn | gecen {gec/60:.0f} dk | '
                f'kalan ~{gec/max(n_bit,1)*(len(LISTE)-n_bit)/60:.0f} dk | %{100*n_bit//len(LISTE)}')
            break
        bekleyen_ilk = [c for c in LISTE if not qc.get(c, {}).get('denenen') and qc.get(c, {}).get('son') is None]
        if bekleyen_tekrar and (len(bekleyen_tekrar) >= 5 or not bekleyen_ilk or time.time() - son_olay > 600):
            tekrar_gonder(bekleyen_tekrar); bekleyen_tekrar = []; son_olay = time.time()
    if all(qc.get(c, {}).get('son') in ('PASS', 'FAIL_KALICI') for c in LISTE):
        log('BITTI', 'PASS', sum(qc[c]['son'] == 'PASS' for c in LISTE), 'FAIL', [c for c in LISTE if qc[c]['son'] != 'PASS']); break
    if girdi_bitti() and not yapildi and time.time() - son_olay > 2400:
        log('ZAMAN ASIMI: 40 dk yeni olay yok', [c for c in LISTE if qc.get(c, {}).get('son') not in ('PASS', 'FAIL_KALICI')]); break
    if not yapildi: time.sleep(45)
