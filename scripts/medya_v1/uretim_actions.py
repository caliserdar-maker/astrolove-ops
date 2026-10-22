#!/usr/bin/env python3
"""medya-v1: Kova-Kova paketini Actions'ta (kisisel-pilot kosucusu) uretir ve Drive'a yazar.
Girdiler Drive'dan (salt okuma): 5 renk Kova kaynak klasoru, referans ilan dokumu (_girdi/etsy),
baslangic ZIP (referans kopyalari + eski paket kanit icin). Kod: scripts/medya_v1/uretim (yerelde dogrulandi).
Cikti: gdrive:ASTROLOVE/TEMP/POD_KISISEL/AQUARIUS_AQUARIUS_v1/{images,video,copy,REVIEW,QC}
Etsy/Prodigi erisimi YOK."""
import hashlib, os, shutil, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
W = Path('_uretim').resolve(); W.mkdir(exist_ok=True)
DR = 'gdrive:ASTROLOVE/TEMP/POD_KISISEL/AQUARIUS_AQUARIUS_v1'
SRC = {'MB': '1JhCxwiQ0A5iWye-nNeIHflOeNtf0C9Pw', 'DB': '11HiAmTHIHk8mvlgez2ocbmPTVI-hrAUC', 'WP': '1LNrzYenIN2hn1_zbS3xpgJ60Ot7tl9Mh',
       'CI': '1HqiEgzD6clmfCf8d5Vsuv0ivgzlwFh29', 'PW': '1oYo-7cikB7lw8MPfYgK3locVyAVv6XmK'}
ZIP_ID = '1WpPbP86Em0WNMTj9muUyvADbOa3Axxd4'
def sh(cmd, **kw): print('+', cmd if isinstance(cmd, str) else ' '.join(cmd), flush=True); return subprocess.run(cmd, check=True, shell=isinstance(cmd, str), **kw)
t0 = time.time()
sh([sys.executable, '-m', 'pip', 'install', '-q', 'scipy', 'opencv-python-headless', 'imageio-ffmpeg', 'pillow', 'numpy'])
import imageio_ffmpeg
bindir = W / 'bin'; bindir.mkdir(exist_ok=True)
ff = bindir / 'ffmpeg'
if not ff.exists(): ff.symlink_to(imageio_ffmpeg.get_ffmpeg_exe())
os.environ['PATH'] = f'{bindir}:{os.environ["PATH"]}'
fd = W / 'fonts'; fd.mkdir(exist_ok=True)
for rel, name in (('montserrat/Montserrat%5Bwght%5D.ttf', 'Montserrat[wght].ttf'), ('ebgaramond/EBGaramond%5Bwght%5D.ttf', 'EBGaramond[wght].ttf')):
    sh(['curl', '-sfL', '-o', str(fd / name), f'https://raw.githubusercontent.com/google/fonts/main/ofl/{rel}'])
os.environ['FONT_DIR'] = str(fd) + '/'
for f in (REPO / 'scripts/medya_v1/uretim').glob('*.py'): shutil.copy(f, W / f.name)
(W / 'paket/copy').mkdir(parents=True, exist_ok=True)
for f in (REPO / 'scripts/medya_v1/copy').iterdir(): shutil.copy(f, W / 'paket/copy' / f.name)
for i, (c, fid) in enumerate(SRC.items(), 1):
    sh(['rclone', 'copy', 'gdrive:', str(W / 'src' / c), '--drive-root-folder-id', fid])
    el = time.time() - t0; print(f'[girdi {i}/5] %{20*i} gecen {el:.0f}s', flush=True)
sh(['rclone', 'copy', f'{DR}/_girdi/etsy/REF_4570143815', str(W / 'etsy/REF_4570143815')])
z = W / '_zip'; z.mkdir(exist_ok=True)
sh(['rclone', 'backend', 'copyid', 'gdrive:', ZIP_ID, str(z) + '/'])
sh(f'unzip -q -o {z}/*.zip -d {z}/x')
shutil.copytree(z / 'x/workspace/references/centered', W / 'refs_centered', dirs_exist_ok=True)
(W / 'eski').mkdir(exist_ok=True)
shutil.copytree(z / 'x/workspace/production_run/completed/AQUARIUS_AQUARIUS/images', W / 'eski/images', dirs_exist_ok=True)
print('GIRDI SHA256 (ilk 12):', flush=True)
for p in sorted(list((W / 'src').rglob('*.*')) + list((W / 'refs_centered').glob('*')) + list((W / 'etsy').rglob('*.jpg'))):
    print(' ', hashlib.sha256(p.read_bytes()).hexdigest()[:12], p.relative_to(W), flush=True)
if len(sys.argv) > 1 and sys.argv[1] == 'genel':
    # ciftten bagimsiz 4 genel kart (onayli Kova-Kova kart 02/06/08/10 stilinden) -> REVIEW/GENEL
    (W / 'out').mkdir(exist_ok=True)
    subprocess.run([sys.executable, '-u', 'cards.py', '2', '6', '8', '10'], cwd=W, check=True)
    subprocess.run([sys.executable, '-u', 'genel.py'], cwd=W, check=True)
    sh(['rclone', 'copy', str(W / 'paket/GENEL'), f'{DR}/REVIEW/GENEL', '--include', '*.jpg', '--include', '*.png', '--include', '*.json'])
    sh(['rclone', 'lsl', f'{DR}/REVIEW/GENEL'])
    print(f'bitti {time.time()-t0:.0f}s genel', flush=True); sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == 'kart':
    # yalniz secilen kartlar (ornek: kart 3 7): uret, paket gorseli + REVIEW yan yana, Drive'daki ayni adlarin ustune yaz
    ns = sys.argv[2:]
    # kart 7 detay paneli: yuksek cozunurluklu baski dosyasi (TEMP/POD_PRINT/AQUARIUS_AQUARIUS/MIDNIGHT_BLUE/30x40.jpg)
    (W / 'hires').mkdir(exist_ok=True)
    (W / 'out').mkdir(exist_ok=True)   # tam hatta master.py aciyordu; kart modunda yok (kosu 36104778417 hatasi)
    sh(['rclone', 'backend', 'copyid', 'gdrive:', '17wv3lIJkgw2Ymx1xHyFh_c0vtLa2NgAz', str(W / 'hires/MB_30x40.jpg')])
    print('hires sha256', hashlib.sha256((W / 'hires/MB_30x40.jpg').read_bytes()).hexdigest()[:12], flush=True)
    for cmd in (['cards.py'] + ns, ['tek_kart.py'] + ns):
        subprocess.run([sys.executable, '-u'] + cmd, cwd=W, check=True)
    qc = W / 'paket/QC'; qc.mkdir(parents=True, exist_ok=True)
    lg = W / f'out/cards_log_{"_".join(ns)}.json'; shutil.copy(lg, qc / lg.name)
    for sub in ('images', 'REVIEW', 'copy', 'QC'):
        sh(['rclone', 'copy', str(W / 'paket' / sub), f'{DR}/{sub}'])
    sh(['rclone', 'lsl', DR, '--include', '03_*', '--include', '07_*', '--include', 'P03_*', '--include', 'P07_*', '--include', lg.name])
    print(f'bitti {time.time()-t0:.0f}s kart {ns}', flush=True); sys.exit(0)
r = subprocess.run([sys.executable, '-u', 'run_all.py', 'uretim'], cwd=W)
if r.returncode == 0:
    sh(['rclone', 'copy', str(W / 'paket'), DR, '--transfers', '8'])   # teslim once yazilir, QC sonra
    r = subprocess.run([sys.executable, '-u', 'run_all.py', 'qc'], cwd=W)
qc = W / 'paket/QC'; qc.mkdir(parents=True, exist_ok=True)
for f in (W / 'out').glob('qc_*.json'): shutil.copy(f, qc / f.name)
for f in ('iz_tarama.json', 'master_meta.json', 'video_plan.json', 'video_states_meta.json', 'cards_log_2_3_4_5_6_7_8_9_10.json'):
    if (W / 'out' / f).exists(): shutil.copy(W / 'out' / f, qc / f)
sh(['rclone', 'copy', str(W / 'paket'), DR, '--transfers', '8'])
sh(['rclone', 'lsf', '-R', DR, '--exclude', '_girdi/**'])
print(f'bitti {time.time()-t0:.0f}s pipeline cikis={r.returncode}', flush=True)
sys.exit(r.returncode)
