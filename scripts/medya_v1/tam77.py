#!/usr/bin/env python3
"""77 cift TAM SET (Serdar onayi 25 Eyl, Aries+Leo onayli kodla). Surucu: her cift icin tam_set.py ayri surecte (--a77).

  tam77.py <parca> <toplam>   : liste (KP/TS77_LISTE.json, 5 renk x 78 sayfa imzali) -> bu parcanin sayfalari ONCE indirilir
                                (imzali URL suresi), sonra cift cift tam_set; kapidan gecen set A1_77/<CIFT>/TAM_SET + SET.json.
  tam77.py serit              : parca raporlari -> PASS/FAIL, FAIL listesi, kart 06 + kart 04 seridi; imzali liste silinir.
Kapilar tam_set ile ayni; FAIL olan cift duzeltilmez, yuklenmez, listelenir. Etsy'ye erisim YOK."""
import json, shutil, subprocess, sys, time
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_poster as A
from a1_poster import rc, log, W, KP, REF_CIFT

Image.MAX_IMAGE_PIXELS = None
LISTE = f'{KP}/TS77_LISTE.json'
RAPOR = f'{A.A77}/_tamset'
RENKLER = ['blue', 'black', 'modern', 'pure_white', 'vintage']
TS = Path(__file__).resolve().parent / 'tam_set.py'

def liste():
    rc('copy', LISTE, str(W)); L = json.loads((W / 'TS77_LISTE.json').read_text())
    return {r: A.liste_ac(L[r]) for r in RENKLER}

def kucuk(c):
    d = W / 'TAM_SET'; ims = [Image.open(d / f) for f in ('04_bes_palet.jpg', '06_yakin_detay.jpg')]
    ims = [i.resize((round(i.width * 420 / i.height), 420), Image.LANCZOS) for i in ims]
    t = Image.new('RGB', (sum(i.width for i in ims) + 10, 450), 'white'); x = 0
    for i in ims: t.paste(i, (x, 30)); x += i.width + 10
    ImageDraw.Draw(t).text((5, 8), c, fill=(0, 0, 0)); return t

def parca(p, n):
    T0 = time.time(); L = liste()
    ciftler = sorted(x.strip('/') for x in rc('lsf', A.POD, '--dirs-only').split()); assert len(ciftler) == 78
    no = {c: i + 1 for i, c in enumerate(ciftler)}; assert no[REF_CIFT] == 28
    benim = [c for c in ciftler if c != REF_CIFT][p::n]
    H = W / 'ham77'; H.mkdir(exist_ok=True); R = {'parca': p, 'toplam_is': n, 'cift': {}}
    for sayfa in sorted({28, *[no[c] for c in benim]}):                 # imzali URL'ler: once hepsi indirilir
        for r in RENKLER:
            u = L[r][str(sayfa)]; A.maskele(u)
            try: (H / f'{r}_{sayfa}.png').write_bytes(A.indir(u))
            except Exception as e: log(f'{r}_{sayfa} indirilemedi {repr(e)[:120]}')  # noqa: BLE001
    log(f'parca {p}/{n}: {len(benim)} cift, sayfalar indi ({round(time.time() - T0)} s)')
    K = W / 'tam77_k'; K.mkdir(exist_ok=True); t_bas = time.time()
    for i, c in enumerate(benim):
        ti = time.time(); r = {'sayfa': no[c]}
        for d in ('ham', 'TAM_SET', 'k3', 'hi'): shutil.rmtree(W / d, ignore_errors=True)
        (W / 'ham').mkdir()
        eksik = [f'{rr}_{s}' for rr in RENKLER for s in (28, no[c]) if not (H / f'{rr}_{s}.png').exists()]
        try:
            if eksik: raise RuntimeError(f'Canva sayfasi indirilemedi: {eksik}')
            for rr in RENKLER:
                for s in (28, no[c]): shutil.copyfile(H / f'{rr}_{s}.png', W / 'ham' / f'{rr}_{s}.png')
            q = subprocess.run([sys.executable, str(TS), c, '--a77', '--ham-hazir'], capture_output=True, text=True, timeout=1500)
            rap = W / 'TAM_SET' / 'RAPOR_TAM_SET.json'
            if not rap.exists(): raise RuntimeError('tam_set raporu yok: ' + (q.stdout + q.stderr)[-600:])
            d = json.loads(rap.read_text()); r['ozet'] = d.get('ozet'); r['gecti'] = bool(d.get('gecti'))
            if q.returncode and not r['gecti']: r['hata'] = (q.stdout + q.stderr)[-600:]
            if r['gecti']: kucuk(c).save(K / f'{c}.jpg', quality=88)
        except Exception as e:                                        # noqa: BLE001  cift FAIL, is durmaz
            r['gecti'] = False; r['hata'] = repr(e)[:600]
        r['sn'] = round(time.time() - ti, 1); R['cift'][c] = r
        k = i + 1; g = time.time() - t_bas
        log(f'[{k}/{len(benim)}] {c} {"PASS" if r["gecti"] else "FAIL"} {r["sn"]}s | gecen {g / 60:.1f} dk, kalan {g / k * (len(benim) - k) / 60:.1f} dk, %{100 * k / len(benim):.0f}')
    R['toplam_sn'] = round(time.time() - T0, 1)
    (W / f'parca_{p}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(W / f'parca_{p}.json'), RAPOR); rc('copy', str(K), f'{RAPOR}/k')

def serit():
    O = W / 'ts_serit'; O.mkdir(exist_ok=True)
    try:
        rc('copy', RAPOR, str(O))
        C = {}
        for f in sorted(O.glob('parca_*.json')): C.update(json.loads(f.read_text())['cift'])
        gec = sorted(c for c, r in C.items() if r['gecti']); fail = {c: (r.get('hata') or r.get('ozet')) for c, r in C.items() if not r['gecti']}
        video_yok = sorted(c for c in gec if not (C[c].get('ozet') or {}).get('video'))
        ims = [Image.open(O / 'k' / f'{c}.jpg') for c in gec if (O / 'k' / f'{c}.jpg').exists()]
        if ims:
            w = max(i.width for i in ims); kol = 4; sat = -(-len(ims) // kol)
            for b in range(0, sat, 10):                                  # 10 satir/sayfa (40 cift)
                parca_ims = ims[b * kol:(b + 10) * kol]; s = -(-len(parca_ims) // kol)
                T = Image.new('RGB', (w * kol, 450 * s), 'white')
                for j, im in enumerate(parca_ims): T.paste(im, ((j % kol) * w, (j // kol) * 450))
                T.save(O / f'SERIT_TAMSET_77_k04_k06_{b // 10 + 1}.jpg', quality=85)
        ozet = {'toplam': len(C), 'pass': len(gec), 'fail': len(fail), 'fail_liste': fail, 'video_yok': video_yok,
                'is_sn_maks': max((json.loads(f.read_text())['toplam_sn'] for f in O.glob('parca_*.json')), default=None)}
        (O / 'RAPOR_TAMSET_77.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=str))
        for f in list(O.glob('SERIT_*.jpg')) + [O / 'RAPOR_TAMSET_77.json']: rc('copy', str(f), RAPOR)
        print(json.dumps(ozet, ensure_ascii=False, indent=1, default=str), flush=True)
    finally:
        try: rc('deletefile', LISTE)                                  # imzali liste kullanimdan sonra silinir
        except Exception: pass                                        # noqa: BLE001

if __name__ == '__main__':
    if sys.argv[1:2] == ['serit']: serit()
    else: A.kisisel_hazirla(); parca(int(sys.argv[1]), int(sys.argv[2]))
