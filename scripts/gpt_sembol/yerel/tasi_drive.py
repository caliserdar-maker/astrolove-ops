# 78 baski dosyasini 10'luk partilerle Drive'a tasir: gecici yetim dal poster-tasi -> Actions rclone copy + check.
import os, csv, json, time, subprocess, shutil, urllib.request
B = '/home/claude/blender'; T = '/home/claude/tasi'
API = 'https://api.github.com/repos/caliserdar-maker/astrolove-ops/actions/runs?branch=poster-tasi&per_page=20'
def log(*a):
    with open(f'{B}/tasi_drive.log', 'a') as f: print(time.strftime('%H:%M:%S'), *a, file=f, flush=True)
def sh(c, **k): return subprocess.run(c, shell=True, capture_output=True, text=True, **k)
cs = [r['cift'] for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv'))]
kay = {c: (f'{B}/gb_api/{c}/{c}_GPT_7200x10800.jpg' if c in ('GEMINI_VIRGO', 'ARIES_LEO', 'CANCER_LIBRA')
           else f'{B}/gb_all/{c}/{c}_GPT_7200x10800.jpg') for c in cs}
if os.environ.get('KAYNAK_DIR'): kay = {c: f"{B}/{os.environ['KAYNAK_DIR']}/{c}/{c}_7200x10800.jpg" for c in cs}   # renk uyumlu surum
eksik = [c for c, p in kay.items() if not os.path.exists(p)]
if eksik: log('EKSIK', eksik); raise SystemExit(1)
bitti = set(open(f'{B}/tasi_bitti.txt').read().split()) if os.path.exists(f'{B}/tasi_bitti.txt') else set()
kalan = [c for c in cs if c not in bitti]
if os.environ.get('TASI_LISTE'): kalan = os.environ['TASI_LISTE'].split(','); bitti = set()   # yeniden yukleme (ayni ad ustune yazar)
T0 = time.time()
for i in range(0, len(kalan), 10):
    parti = kalan[i:i + 10]
    shutil.rmtree(f'{T}/tasi', ignore_errors=True); os.makedirs(f'{T}/tasi')
    for c in parti: os.link(kay[c], f'{T}/tasi/{c}_7200x10800.jpg')
    sh('rm -rf .git && git init -q -b poster-tasi && git remote add origin https://github.com/caliserdar-maker/astrolove-ops && '
       'git add -A && git -c user.name=claude -c user.email=noreply@anthropic.com commit -qm "poster-tasi parti"', cwd=T)
    sha = sh('git rev-parse HEAD', cwd=T).stdout.strip()
    t0 = time.time()
    p = sh('git push -q -f origin poster-tasi', cwd=T)
    if p.returncode: log('PUSH HATA', p.stderr[-300:]); raise SystemExit(1)
    log('push', len(parti), f'{time.time()-t0:.0f} sn', sha[:7])
    while True:
        time.sleep(30)
        try: runs = json.load(urllib.request.urlopen(API, timeout=60))['workflow_runs']
        except Exception as e: log('api', e); continue
        r = [x for x in runs if x['head_sha'] == sha]
        if r and r[0]['status'] == 'completed':
            if r[0]['conclusion'] != 'success': log('KOSU FAIL', r[0]['html_url']); raise SystemExit(1)
            break
    if not os.environ.get('TASI_LISTE'):
        with open(f'{B}/tasi_bitti.txt', 'a') as f: f.write('\n'.join(parti) + '\n')
    n = len(bitti) + i + len(parti); g = time.time() - T0
    log(f'[{n}/78] Drive tamam | gecen {g/60:.0f} dk | kalan ~{g/(i+len(parti))*(len(kalan)-i-len(parti))/60:.0f} dk | %{100*n//78}')
sh('git push -q origin --delete poster-tasi', cwd=T)
log('BITTI, gecici dal silindi')
