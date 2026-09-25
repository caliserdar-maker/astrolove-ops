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
LISTE = f'{KP}/TS77'                                  # TS77_<renk>.json (5 dosya, imzali, kullanimdan sonra silinir)
RAPOR = f'{A.A77}/_tamset'
RENKLER = ['blue', 'black', 'modern', 'pure_white', 'vintage']
TS = Path(__file__).resolve().parent / 'tam_set.py'

def liste():
    rc('copy', KP, str(W / 'ts77l'), '--include', 'TS77_*.json')
    return {r: A.liste_ac(json.loads((W / 'ts77l' / f'TS77_{r}.json').read_text())) for r in RENKLER}

TUR = 'r2'                                            # GOREV 0002: yalniz seti olmayan (FAIL) ciftler yeniden

def yapildi():
    """Kapidan gecmis seti olan ciftler (A1_77/<CIFT>/TAM_SET/SET.json)."""
    return {x.split('/')[0] for x in rc('lsf', A.A77, '-R', '--files-only', '--include', '*/TAM_SET/SET.json').split() if x}

def kucuk(c, d=None):
    d = d or W / 'TAM_SET'; ims = [Image.open(d / f) for f in ('04_bes_palet.jpg', '06_yakin_detay.jpg')]
    ims = [i.resize((round(i.width * 420 / i.height), 420), Image.LANCZOS) for i in ims]
    t = Image.new('RGB', (sum(i.width for i in ims) + 10, 450), 'white'); x = 0
    for i in ims: t.paste(i, (x, 30)); x += i.width + 10
    ImageDraw.Draw(t).text((5, 8), c, fill=(0, 0, 0)); return t

def parca(p, n):
    T0 = time.time(); L = liste()
    ciftler = sorted(x.strip('/') for x in rc('lsf', A.POD, '--dirs-only').split()); assert len(ciftler) == 78
    no = {c: i + 1 for i, c in enumerate(ciftler)}; assert no[REF_CIFT] == 28
    bitti = yapildi()
    benim = [c for c in ciftler if c != REF_CIFT and c not in bitti][p::n]
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
            if not r['gecti']:                                        # teshis: kapi ayrintilari (renk kapilari, kart 06, galeri)
                r['poster'] = d.get('poster'); r['kart06'] = (d.get('kart07') or {}).get('detay', {}).get('kapi')
                r['galeri_burc'] = [g['dosya'] for g in d.get('galeri', []) if not g['burc_kapisi']['gecti']]
                if not ((d.get('poster') or {}).get('vintage') or {}).get('gecti', True):   # E: WP x3 + sembol kaynak|yeni
                    for f in list((W / 'TAM_SET').glob('WP_x3_*.jpg')) + list((W / 'TAM_SET').glob('SEMBOL_WARM_PARCHMENT.jpg')):
                        rc('copy', str(f), f'{RAPOR}/E/{c}')
            if q.returncode and not r['gecti']: r['hata'] = (q.stdout + q.stderr)[-600:]
            if r['gecti']: kucuk(c).save(K / f'{c}.jpg', quality=88)
        except Exception as e:                                        # noqa: BLE001  cift FAIL, is durmaz
            r['gecti'] = False; r['hata'] = repr(e)[:600]
        r['sn'] = round(time.time() - ti, 1); R['cift'][c] = r
        k = i + 1; g = time.time() - t_bas
        log(f'[{k}/{len(benim)}] {c} {"PASS" if r["gecti"] else "FAIL"} {r["sn"]}s | gecen {g / 60:.1f} dk, kalan {g / k * (len(benim) - k) / 60:.1f} dk, %{100 * k / len(benim):.0f}')
    R['toplam_sn'] = round(time.time() - T0, 1)
    (W / f'parca_{TUR}_{p}.json').write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str))
    rc('copy', str(W / f'parca_{TUR}_{p}.json'), RAPOR); rc('copy', str(K), f'{RAPOR}/k')

def serit():
    """Iki kosunun raporlari birlesir (sonraki kosu ayni cifti ezer); serit 78 cift: seti olan her ciftin kart 04 + 06'si
    Drive'daki TAM_SET dosyalarindan."""
    O = W / 'ts_serit'; O.mkdir(exist_ok=True)
    try:
        rc('copy', RAPOR, str(O), '--include', 'parca_*.json')
        C = {}
        for f in sorted(O.glob('parca_[0-9]*.json')) + sorted(O.glob(f'parca_{TUR}_*.json')): C.update(json.loads(f.read_text())['cift'])
        bitti = yapildi()
        for c in bitti:                                               # seti olan cift PASS (ilk kosuda raporu kayip olanlar dahil)
            C.setdefault(c, {'gecti': True})
            if not C[c]['gecti'] and c in bitti: C[c]['gecti'] = True
        gec = sorted(c for c, r in C.items() if r['gecti']); fail = {c: r for c, r in C.items() if not r['gecti']}
        video_yok = sorted(c for c in gec if c in C and C[c].get('ozet') and not C[c]['ozet'].get('video'))
        K = O / 'k'; K.mkdir(exist_ok=True); ims = []
        for c in sorted(bitti):
            d = O / 'set' / c
            try:
                rc('copy', f'{A.A77}/{c}/TAM_SET', str(d), '--include', '04_bes_palet.jpg', '--include', '06_yakin_detay.jpg')
                ims.append(kucuk(c, d))
            except Exception as e: log(f'{c}: serit gorseli alinamadi {repr(e)[:100]}')  # noqa: BLE001
        if ims:
            w = max(i.width for i in ims); kol = 4
            for b in range(0, len(ims), 40):                          # 10 satir/sayfa (40 cift)
                parca_ims = ims[b:b + 40]; s = -(-len(parca_ims) // kol)
                T = Image.new('RGB', (w * kol, 450 * s), 'white')
                for j, im in enumerate(parca_ims): T.paste(im, ((j % kol) * w, (j // kol) * 450))
                T.save(O / f'SERIT_TAMSET_78_k04_k06_{b // 40 + 1}.jpg', quality=85)
        ozet = {'seti_olan': len(bitti), 'pass_77': len([c for c in gec if c != REF_CIFT]), 'fail': len(fail),
                'fail_liste': {c: {k: r.get(k) for k in ('hata', 'poster', 'kart06', 'galeri_burc') if r.get(k)} for c, r in fail.items()},
                'video_yok': video_yok, 'serit_cift': len(ims)}
        (O / 'RAPOR_TAMSET_78.json').write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=str))
        for f in list(O.glob('SERIT_TAMSET_78_*.jpg')) + [O / 'RAPOR_TAMSET_78.json']: rc('copy', str(f), RAPOR)
        print(json.dumps({k: v for k, v in ozet.items() if k != 'fail_liste'}, ensure_ascii=False, indent=1), flush=True)
    finally:
        for r in RENKLER:                                             # imzali liste kullanimdan sonra silinir
            try: rc('deletefile', f'{LISTE}_{r}.json')
            except Exception: pass                                    # noqa: BLE001

if __name__ == '__main__':
    if sys.argv[1:2] == ['serit']: serit()
    else: A.kisisel_hazirla(); parca(int(sys.argv[1]), int(sys.argv[2]))
