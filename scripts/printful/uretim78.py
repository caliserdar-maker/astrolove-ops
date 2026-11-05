#!/usr/bin/env python3
"""Ornament 78 uretim yardimcilari (Serdar 4 Kas: PLAN_78_URETIM.md 9f88868 onaylari; is akisi ornament-78-uretim.yml). Kod ile ayni dosyada
yerel mantik testi: uretim78_mantik_testi.py. Alt komutlar (is akisi):
  parcalar   URETIM78_CIFTLER.json aktif bolumunden matrix parcalari (CL her parcada ilk, yalniz kontrol) -> JSON
  siparis    main'deki siparis|order akislarinda etkin kosu var mi (gh api); --dur ile varsa cikis 1
  kenar_on   kenar onarimi on olcumu (motor yolu: kirp pad 2 -> ana 1600 -> delik_kapat -> kenar_onar) -> onarimsiz motor kosacak ciftler
  onayli     onayli dosyalarda printful_dosya olcumu (BILGI)
  klasor     rclone lsjson ciktisinda ayni adli klasor var mi (FAIL)
  birlestir  parca OLCUM'larini birlestirir (CL tekillestirme, eksik parca FAIL, Drive md5 karsilastirmasi)
  dal_kapisi dala yazilacak dosya listesi: yalniz .json / .md / .txt / .log; PNG ve kaynak desenleri FAIL
Cikis: 0 PASS, 1 FAIL, 2 cokus."""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

_d = Path(__file__).resolve().parent
BURC = 'AQUARIUS ARIES CANCER CAPRICORN GEMINI LEO LIBRA PISCES SAGITTARIUS SCORPIO TAURUS VIRGO'.split()
CIFT78 = sorted('_'.join(sorted(p)) for p in itertools.combinations_with_replacement(BURC, 2))
STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
KONTROL = 'CANCER_LIBRA'
ONAYLI = ('CANCER_LIBRA', 'AQUARIUS_PISCES', 'GEMINI_VIRGO')       # Serdar 4 Kas "A": 78 kosusunda uretilmez, onayli dosyalari kullanilir
YD11 = ('TAURUS_TAURUS', 'CANCER_TAURUS', 'AQUARIUS_CANCER', 'LIBRA_LIBRA', 'AQUARIUS_AQUARIUS', 'ARIES_SCORPIO', 'LEO_SAGITTARIUS',
        'CAPRICORN_CAPRICORN', 'CANCER_LIBRA', 'AQUARIUS_PISCES', 'GEMINI_VIRGO')   # yeni duzen asama 2 ornek ciftleri (Serdar 4 Kas gece)
KONTROL_ESKI = 'CANCER_LIBRA_KONTROL_ESKI'                           # yeni duzen kosusunda eski mod CL kontrolunun OLCUM anahtari
YD_BOLUMLER = ('yeni_duzen', 'yd67')                                  # yeni duzen (YENI_DUZEN=1) bolumleri (Serdar 5 Kas, PLAN67)
KOVA_PARCA_MAX = 2                                                    # yd67: parca basina en cok 2 Kova'li cift (PLAN67 parca dagilim kurali)
ETKIN = ('queued', 'in_progress', 'waiting', 'pending', 'requested')
SIPARIS_DESEN = re.compile(r'siparis|order', re.I)
DPI, DPI_TOL = 300.0, 0.5


# ------------------------------------------------------------------------------------------------ parcalar
def parcalar(J, aktif=None):
    """URETIM78_CIFTLER.json -> dict(aktif, max_parallel, parcalar=[dict(parca, ciftler (CL ilk), uretim, kenar_zorunlu, gercek_boy)]).
    Dogrulama (ValueError): bilinmeyen cift, tekrar, CL parcada yazili, '78' KAPALI (Serdar 5 Kas), 'yd67' tam 67 cift (78 - YD11), parca farki <= 1, parca basina Kova <= 2."""
    aktif = aktif or J['aktif']
    B = J[aktif]
    tum = [c for p in B['parcalar'] for c in p]
    bil = [c for c in tum if c not in CIFT78]
    if bil:
        raise ValueError(f'bilinmeyen cift: {bil}')
    if len(set(tum)) != len(tum):
        raise ValueError(f'tekrar eden cift: {sorted(c for c in set(tum) if tum.count(c) > 1)}')
    if KONTROL in tum:
        raise ValueError('CANCER_LIBRA parcaya yazilmaz (kontrol cifti otomatik eklenir)')
    cl_yeni = B.get('cl_yeni_parca')                                         # yeni duzen (Serdar 4 Kas gece karar 6): CL bu parcanin SONUNDA yeni duzende uretilir
    if cl_yeni is not None and aktif != 'yeni_duzen':
        raise ValueError("cl_yeni_parca yalniz 'yeni_duzen' bolumunde")
    if cl_yeni is not None and not (isinstance(cl_yeni, int) and 1 <= cl_yeni <= len(B['parcalar'])):
        raise ValueError(f'cl_yeni_parca gecersiz: {cl_yeni}')
    if aktif == 'yeni_duzen':
        if sorted(tum + [KONTROL]) != sorted(YD11) or cl_yeni is None:
            raise ValueError(f"'yeni_duzen' bolumu 10 cift + cl_yeni_parca (CL) olmali: eksik {sorted(set(YD11) - set(tum) - {KONTROL})}, fazla {sorted(set(tum) - set(YD11))}")
    if aktif == '78':                                                        # Serdar 5 Kas (PLAN67 soru 3): eski duzen 75 cift bolumu KAPALI
        raise ValueError("'78' bolumu kapali (eski duzen; Serdar 5 Kas): yerine 'yd67'")
    if aktif == 'yd67':                                                      # Serdar 5 Kas (PLAN67): 78 - YD11 = 67, yeni duzen
        bek = sorted(c for c in CIFT78 if c not in YD11)
        if sorted(tum) != bek or cl_yeni is not None:
            raise ValueError(f"'yd67' bolumu 67 cift olmali (78 - YD11), cl_yeni yok: eksik {sorted(set(bek) - set(tum))}, fazla {sorted(set(tum) - set(bek))}")
        n_ = [len(p) for p in B['parcalar']]
        if max(n_) - min(n_) > 1:
            raise ValueError(f"'yd67' parca cift sayisi farki en cok 1 olmali: {n_}")
        ak_ = [sum('AQUARIUS' in c.split('_') for c in p) for p in B['parcalar']]
        if max(ak_) > KOVA_PARCA_MAX:
            raise ValueError(f"'yd67' parca basina en cok {KOVA_PARCA_MAX} Kova'li cift: {ak_}")
    P = []
    for i, p in enumerate(B['parcalar']):
        ek = [KONTROL] if cl_yeni == i + 1 else []
        P.append(dict(parca=i + 1, ciftler=[KONTROL] + list(p) + ek, uretim=list(p) + ek, cl_yeni=bool(ek),
                      kenar_zorunlu=[c for c in p if 'AQUARIUS' in c.split('_')], gercek_boy=list(p) + ek))
    for p in P:
        kenar_dogrula(p)
    return dict(aktif=aktif, max_parallel=int(B.get('max_parallel', len(P))), parca_sayisi=len(P), parcalar=P,
                cift_sayisi=len(tum))


def kenar_dogrula(p):
    """ZAYIF (yapisi geregi; F 4 Kas): parcalar() listeyi ayni kaynaktan uretir, uretimde FAIL veremez; elle bozulmus girdiye karsi koruma.
    G (Kova kapisi): parcadaki her AQUARIUS ciftinin ORNEK78_KENAR_ZORUNLU listesinde olmasi; CL ilk ve tek. Hata: ValueError."""
    ak = [c for c in p['uretim'] if 'AQUARIUS' in c.split('_')]
    eks = sorted(set(ak) - set(p['kenar_zorunlu']))
    if eks:
        raise ValueError(f"parca {p['parca']}: Kova cifti kenar_zorunlu listesinde yok: {eks}")
    n_cl = 2 if p.get('cl_yeni') else 1                                     # yeni duzen: ilk CL kontrol (eski mod), son CL yeni duzen uretimi
    if not p['ciftler'] or p['ciftler'][0] != KONTROL or p['ciftler'].count(KONTROL) != n_cl or (n_cl == 2 and p['ciftler'][-1] != KONTROL):
        raise ValueError(f"parca {p['parca']}: ilk ve tek kontrol cifti CANCER_LIBRA olmali (yeni duzen CL'si yalniz sonda)")
    return True


# ------------------------------------------------------------------------------------------------ siparis
def siparis_akislari(adlar):
    return sorted(a for a in adlar if SIPARIS_DESEN.search(a))


def siparis_aktif(akislar, kosular):
    """akislar: main'deki dosya adlari (siparis|order); kosular: actions/runs kayitlari (path, status). Etkin olanlar."""
    ak = set(akislar)
    return [dict(id=k.get('id'), path=k.get('path'), status=k.get('status'), name=k.get('name')) for k in kosular
            if Path(str(k.get('path') or '')).name in ak and k.get('status') in ETKIN]


def gh_json(yol):
    r = subprocess.run(['gh', 'api', yol], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f'gh api {yol}: {r.stderr.strip()[:200]}')
    return json.loads(r.stdout)


def siparis_kontrol(depo):
    adlar = [x['name'] for x in gh_json(f'repos/{depo}/contents/.github/workflows?ref=main')]
    ak = siparis_akislari(adlar)
    kos = []
    for st in ETKIN:
        sayfa = 1
        while True:
            d = gh_json(f'repos/{depo}/actions/runs?status={st}&per_page=100&page={sayfa}')
            kos += d.get('workflow_runs', [])
            if len(d.get('workflow_runs', [])) < 100:
                break
            sayfa += 1
    return dict(akislar=ak, akis_kaynagi='main: .github/workflows (siparis|order)', etkin=siparis_aktif(ak, kos), zaman=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))


# ------------------------------------------------------------------------------------------------ kenar on olcumu
def _kkt():
    s = importlib.util.spec_from_file_location('kkt', _d / 'kova_kapi_testi.py'); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def kenar_olc(yol, ana):
    """motor yolu (ornament_motor.py kucuk / ana; kova_kapi_testi.hazirla + delik_kapat + kenar_onar): n0, degisen piksel."""
    k = _kkt()
    g = k.hazirla(yol, ana)
    gd, _ = k.o5.delik_kapat(g)
    _, ky = k.o5.kenar_onar(gd)
    return dict(n0=ky['n0'], degisen_piksel=ky['degisen_piksel'], alfa_farki_en_buyuk=ky['alfa_farki_en_buyuk'], boyut=ky['boyut'])


def kenar_olc_ham(yol):
    """BILINEN FAIL karsilastirmasi: yolu atlayan ham olcum (kirp ve delik_kapat yok)."""
    import numpy as np
    from PIL import Image
    k = _kkt()
    g = np.asarray(Image.open(yol).convert('RGBA'), np.float32); g[..., 3] /= 255.0
    _, ky = k.o5.kenar_onar(g)
    return dict(n0=ky['n0'], degisen_piksel=ky['degisen_piksel'])


def kenar_on_olcum(K, ciftler):
    K = Path(K); S = {}
    burclar = sorted({b.lower() for c in ciftler for b in c.split('_')})
    for b in burclar:
        S[b] = kenar_olc(K / f'{b}_symbol_gold.png', False)
    for c in ciftler:
        S[f'{c}_ana'] = kenar_olc(K / f'{c}_ana.png', True)
    onarimsiz = sorted(c for c in ciftler if S[f'{c}_ana']['degisen_piksel'] or any(S[b.lower()]['degisen_piksel'] for b in c.split('_')))
    return dict(kaynak=S, onarimsiz_motor_ciftleri=onarimsiz, yol='kirp pad 2 -> ana > 1600 ise 1600 -> delik_kapat -> kenar_onar (ornament_motor ile ayni)')


# ------------------------------------------------------------------------------------------------ printful dosya / dpi
def piksel_sha(yol):
    import numpy as np                                                       # gec import: hazirlik / birlestir adimlari pip oncesi kosar (F 4 Kas)
    from PIL import Image
    im = Image.open(yol)
    return hashlib.sha256(im.mode.encode() + np.ascontiguousarray(np.asarray(im)).tobytes()).hexdigest()


def dosya_sha(yol):
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def _icc_srgb(icc):
    if not icc:
        return True, None
    try:
        from PIL import ImageCms
        import io
        ad = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))).strip()
    except Exception as e:                                                   # noqa: BLE001
        return False, f'okunamadi {type(e).__name__}'
    return ('srgb' in ad.lower()), ad


def printful_dosya(yol, stil):
    """Printful 900 Circle (ORNAMENT_KARAR 6): 954x954; RGB (koyu 3 stil, FILDISI) ya da RGBA (SADE_ALTIN, seffaf zemin karari A);
    ICC yok ya da sRGB; dpi 300 +- 0,5."""
    from PIL import Image
    im = Image.open(yol)
    dpi = im.info.get('dpi')
    mod_bek = 'RGBA' if stil == 'SADE_ALTIN' else 'RGB'
    icc_ok, icc_ad = _icc_srgb(im.info.get('icc_profile'))
    k = dict(boyut=list(im.size), boyut_954=im.size == (954, 954), mod=im.mode, mod_beklenen=mod_bek, mod_ok=im.mode == mod_bek,
             dpi=[round(float(x), 4) for x in dpi] if dpi else None,
             dpi_300=bool(dpi) and all(abs(float(x) - DPI) <= DPI_TOL for x in dpi), icc=icc_ad, icc_ok=icc_ok)
    k['gecti'] = bool(k['boyut_954'] and k['mod_ok'] and k['dpi_300'] and k['icc_ok'])
    return k


def _varsayilan_yazici(yol, im):
    kw = dict(dpi=(DPI, DPI))
    if im.info.get('icc_profile'):
        kw['icc_profile'] = im.info['icc_profile']
    im.save(yol, **kw)


def dpi_yaz(yol, yazici=None):
    """piksel degistirmeden dpi 300 yazar (zaten 300 ise yeniden kaydetmez). Doner dict(yazildi, piksel_once, piksel_sonra, piksel_ayni, dosya_sha)."""
    from PIL import Image
    yol = Path(yol)
    im = Image.open(yol); im.load()
    dpi = im.info.get('dpi')
    p0 = piksel_sha(yol)
    if dpi and all(abs(float(x) - DPI) <= DPI_TOL for x in dpi):
        return dict(yazildi=False, piksel_once=p0, piksel_sonra=p0, piksel_ayni=True, dosya_sha=dosya_sha(yol), not_='zaten 300 dpi')
    (yazici or _varsayilan_yazici)(yol, im)
    p1 = piksel_sha(yol)
    return dict(yazildi=True, piksel_once=p0, piksel_sonra=p1, piksel_ayni=p0 == p1, dosya_sha=dosya_sha(yol))


# ------------------------------------------------------------------------------------------------ cift sonu kancasi
def eta_satiri(i, n, gecen):
    kalan = gecen / i * (n - i) if i else 0.0
    return f'ETA {i}/{n} gecen {gecen:.0f} sn kalan {kalan:.0f} sn yuzde {100.0 * i / n:.1f}'


def cift_fail_mi(r):
    return bool(r.get('eksik') or r.get('cokus') or not all(((r.get('kapi') or {}).get('sert') or {'x': False}).values()))


def yukle(sahne, kok_id, rclone='rclone', yerel=None, deneme=3, bekle=5):
    """sahne klasorunu (Drive yapisinda) tek kopya cagrisiyla hedefe; yerel verilirse oraya kopyalar (test). Doner dict(ok, deneme, hata)."""
    if yerel:
        shutil.copytree(sahne, yerel, dirs_exist_ok=True)
        return dict(ok=True, deneme=1, hata=None, hedef='yerel')
    son = None
    for d in range(1, deneme + 1):
        r = subprocess.run([rclone, 'copy', str(sahne), 'gdrive:', '--drive-root-folder-id', kok_id, '-q'], capture_output=True, text=True)
        if r.returncode == 0:
            return dict(ok=True, deneme=d, hata=None, hedef='drive')
        son = (r.stderr or '').strip()[-300:]
        time.sleep(bekle * d)
    return dict(ok=False, deneme=deneme, hata=son, hedef='drive')


def cift_sonu(cift, r, O, RP, DE, w, parca, gercek_boy_fn=None, onizleme_fn=None, env=None, kontrol=None):
    """ornek78 cift sonu: dosya listesi (PASS kok / FAIL FAIL/<CIFT>/), gercek boy, onizleme, yakin plan, parca ara OLCUM tek yukleme;
    katman.pkl ve dump/ silinir. Kontrol cifti (CL) PNG'leri yuklenmez. Doner kayit; yukleme hatasi cifti FAIL yapar (yukleme_hata)."""
    env = env if env is not None else os.environ
    O, RP, DE, w = Path(O), Path(RP), Path(DE), Path(w)
    k = dict(cift=cift, kontrol=(cift == KONTROL) if kontrol is None else bool(kontrol))   # yeni duzen: sondaki CL kontrol degil (yuklenir)
    sahne = w / '_sahne'
    if sahne.exists():
        shutil.rmtree(sahne)
    sahne.mkdir(parents=True)
    dosyalar = []
    if not k['kontrol']:
        if gercek_boy_fn and cift in [x for x in env.get('GERCEK_BOY_CIFTLER', '').split(',') if x]:   # F 4 Kas: once gercek boy, sonra FAIL siniflandirma
            gb = gercek_boy_fn(cift)
            if gb is None:
                r.setdefault('kapi', {}).setdefault('sert', {})['gercek_boy_var'] = False
                k['gercek_boy'] = None
            else:
                (sahne / 'GERCEK_BOY').mkdir(exist_ok=True); shutil.copyfile(gb, sahne / 'GERCEK_BOY' / Path(gb).name)
                dosyalar.append((f'GERCEK_BOY/{Path(gb).name}', dosya_sha(gb))); k['gercek_boy'] = Path(gb).name
        fail = cift_fail_mi(r)
        hedef = sahne / 'FAIL' / cift if fail else sahne
        hedef.mkdir(parents=True, exist_ok=True)
        for s in STIL:
            f = O / f'{cift}_{s}_954.png'
            if f.exists():
                shutil.copyfile(f, hedef / f.name); dosyalar.append((f.name if not fail else f'FAIL/{cift}/{f.name}', dosya_sha(f)))
        if onizleme_fn:
            oz = onizleme_fn(cift)
            if oz:
                (sahne / 'ONIZLEME').mkdir(exist_ok=True); shutil.copyfile(oz, sahne / 'ONIZLEME' / Path(oz).name)
                dosyalar.append((f'ONIZLEME/{Path(oz).name}', dosya_sha(oz)))
        for f in sorted(DE.glob(f'YAKIN_{cift}_*.png')):
            (sahne / 'YAKIN').mkdir(exist_ok=True); shutil.copyfile(f, sahne / 'YAKIN' / f.name); dosyalar.append((f'YAKIN/{f.name}', dosya_sha(f)))
        k['fail_klasoru'] = fail
    if (RP / 'OLCUM_PARCA.json').exists():
        (sahne / 'RAPOR' / f'PARCA_{parca}').mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RP / 'OLCUM_PARCA.json', sahne / 'RAPOR' / f'PARCA_{parca}' / 'OLCUM_PARCA.json')
    y = yukle(sahne, env.get('ORNEK78_DRIVE_KOK_ID', ''), rclone=env.get('ORNEK78_RCLONE', 'rclone'), yerel=env.get('ORNEK78_YEREL_DRIVE') or None,
              bekle=float(env.get('ORNEK78_RCLONE_BEKLE', '5')))
    k['yukleme'] = dict(y, dosyalar=[dict(yol=a, sha256=b) for a, b in dosyalar])
    if not y['ok'] and not k['kontrol']:
        r.setdefault('kapi', {}).setdefault('sert', {})['yukleme_hata'] = False
    for p in (w / 'katman.pkl',):
        if p.exists():
            p.unlink()
    for p in (w / 'dump', sahne):
        if p.exists():
            shutil.rmtree(p)
    k['temizlik'] = dict(katman_pkl_var=(w / 'katman.pkl').exists(), dump_var=(w / 'dump').exists())
    return k


# ------------------------------------------------------------------------------------------------ birlestirme / Drive / dal
def klasor_tekligi(lsjson):
    """rclone lsjson (dizinler; Path alani) -> ayni yolda birden cok klasor."""
    say = {}
    for d in lsjson:
        if d.get('IsDir'):
            say[d['Path']] = say.get(d['Path'], 0) + 1
    tekrar = sorted(p for p, n in say.items() if n > 1)
    return dict(tekrar=tekrar, gecti=not tekrar)


def drive_karsilastir(lsjson, beklenen):
    """lsjson (-R --hash, dosyalar: Path, Hashes.sha256 ya da md5) ile parca kayitlarindaki (yol, sha256) listesi: sayi ve sha esitligi."""
    drv = {}
    for d in lsjson:
        if not d.get('IsDir'):
            drv.setdefault(d['Path'], []).append((d.get('Hashes') or {}).get('sha256') or (d.get('Hashes') or {}).get('SHA-256'))
    eks, fark, cift_ad, shasiz = [], [], [], []
    for yol, sha in beklenen:
        v = drv.get(yol)
        if not v:
            eks.append(yol)
        elif len(v) > 1:
            cift_ad.append(yol)
        elif not v[0] or not sha:
            shasiz.append(yol)                                               # F 4 Kas: sha yoksa kiyas atlanmaz, FAIL
        elif v[0] != sha:
            fark.append(yol)
    uretim = sum(len(v) for p, v in drv.items() if not p.startswith('RAPOR/'))   # RAPOR/ disi Drive dosyasi sayisi = beklenen (fazla dosya FAIL)
    return dict(beklenen=len(beklenen), drive_uretim=uretim, drive=sum(len(v) for v in drv.values()), eksik=eks, sha_farkli=fark, ayni_adli=cift_ad,
                sha_yok=shasiz, sayi_esit=uretim == len(beklenen), gecti=not (eks or fark or cift_ad or shasiz) and uretim == len(beklenen))


def birlestir(parca_olcum, parca_sayisi, kontrol_ad=KONTROL):
    """parca_olcum: {n: R ya da None}. CL tekillestirme (kontrol parca basina), eksik parca FAIL. kontrol_ad: atlanacak OLCUM anahtari
    (yeni duzen kosusunda KONTROL_ESKI; o kosuda 'CANCER_LIBRA' anahtari yeni duzen uretimidir ve birlesime girer)."""
    eksik = sorted(n for n in range(1, parca_sayisi + 1) if not parca_olcum.get(n))
    B = dict(cift={}, kontrol_parca={}, eksik_parca=eksik, kenar_onarim_uyari=[], kucultme=[], kenar_onarimsiz_ek_fail={}, yukleme=[], cokus=[])
    for n in sorted(k for k, v in parca_olcum.items() if v):
        R = parca_olcum[n]
        B['kontrol_parca'][n] = dict(kontrol_pass=R.get('kontrol_pass'), kontrol=R.get('kontrol'))
        for c, v in R.get('cift', {}).items():
            if c == kontrol_ad:
                continue
            if c in B['cift']:
                raise ValueError(f'cift iki parcada: {c}')
            B['cift'][c] = dict(v, parca=n)
            if v.get('kenar_onarimsiz_ek_fail'):
                B['kenar_onarimsiz_ek_fail'][c] = v['kenar_onarimsiz_ek_fail']
        u = R.get('kenar_onarim_uyari')
        if isinstance(u, list):
            B['kenar_onarim_uyari'] += [x for x in u if x.get('cift') != kontrol_ad]
        B['kucultme'] += [x for x in (R.get('kucultme') or []) if x.get('cift') != kontrol_ad]
        B['yukleme'] += [x for x in (R.get('cift_sonu') or []) if not x.get('kontrol')]
        B['cokus'] += [c for c in (R.get('cikis') or {}).get('cokus_ciftler', []) if c != kontrol_ad]
    B['fail'] = sorted(c for c, v in B['cift'].items() if cift_fail_mi(v))
    B['kontrol_hepsi'] = bool(B['kontrol_parca']) and all(v.get('kontrol_pass') is True for v in B['kontrol_parca'].values())
    B['gecti'] = bool(not eksik and B['kontrol_hepsi'] and not B['fail'] and not B['cokus'])
    return B


DAL_IZIN = ('.json', '.md', '.txt', '.log')
DAL_RED = re.compile(r'\.png$|YAKIN_|_symbol_gold|_ana\.|GERCEK_BOY_.*\.png|ONIZLEME.*\.png', re.I)


def dal_kapisi(dosyalar):
    red = [f for f in dosyalar if DAL_RED.search(f) or not f.lower().endswith(DAL_IZIN)]
    return dict(red=red, gecti=not red)


# ------------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='k', required=True)
    p = sp.add_parser('parcalar'); p.add_argument('--json', required=True); p.add_argument('--aktif'); p.add_argument('--cikti', required=True)
    p = sp.add_parser('siparis'); p.add_argument('--depo', required=True); p.add_argument('--cikti', required=True); p.add_argument('--dur', action='store_true')
    p = sp.add_parser('kenar_on'); p.add_argument('--kaynak', required=True); p.add_argument('--ciftler', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('onayli'); p.add_argument('--klasor', nargs='+', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('klasor'); p.add_argument('--lsjson', required=True)
    p = sp.add_parser('birlestir'); p.add_argument('--parca_dir', required=True); p.add_argument('--parca_sayisi', type=int, required=True)
    p.add_argument('--drive_lsjson'); p.add_argument('--cikti', required=True); p.add_argument('--kontrol_ad', default=KONTROL)
    p = sp.add_parser('dal_kapisi'); p.add_argument('dosya', nargs='*')
    a = ap.parse_args()
    if a.k == 'parcalar':
        P = parcalar(json.loads(Path(a.json).read_text()), a.aktif)
        Path(a.cikti).write_text(json.dumps(P, indent=1)); print(json.dumps(dict(aktif=P['aktif'], parca=P['parca_sayisi'], cift=P['cift_sayisi'])))
        return 0
    if a.k == 'siparis':
        S = siparis_kontrol(a.depo); Path(a.cikti).write_text(json.dumps(S, indent=1))
        print('siparis akislari', len(S['akislar']), '| etkin', S['etkin'])
        return 1 if (a.dur and S['etkin']) else 0
    if a.k == 'kenar_on':
        S = kenar_on_olcum(a.kaynak, [c for c in a.ciftler.split(',') if c]); Path(a.cikti).write_text(json.dumps(S, indent=1))
        print('onarimsiz motor ciftleri', S['onarimsiz_motor_ciftleri'])
        return 0
    if a.k == 'onayli':
        S = {}
        for k in a.klasor:
            for f in sorted(Path(k).glob('*_954.png')):
                st = next(s for s in STIL if f.name.endswith(f'_{s}_954.png'))
                S[f.name] = printful_dosya(f, st)
        Path(a.cikti).write_text(json.dumps(dict(bilgi='onayli dosyalar DEGISMEZ (Serdar 4 Kas karar 4); olcum yalniz bilgi', dosya=S), indent=1))
        print('onayli printful bilgi', {k: v['gecti'] for k, v in S.items()})
        return 0
    if a.k == 'klasor':
        K = klasor_tekligi(json.loads(Path(a.lsjson).read_text())); print(json.dumps(K))
        return 0 if K['gecti'] else 1
    if a.k == 'birlestir':
        PO = {}
        for n in range(1, a.parca_sayisi + 1):
            f = Path(a.parca_dir) / f'PARCA_{n}' / 'OLCUM.json'
            PO[n] = json.loads(f.read_text()) if f.exists() else None
        B = birlestir(PO, a.parca_sayisi, a.kontrol_ad)
        if a.drive_lsjson:
            bek = [(y['yol'], y['sha256']) for x in B['yukleme'] for y in (x.get('yukleme') or {}).get('dosyalar', [])]
            B['drive'] = drive_karsilastir(json.loads(Path(a.drive_lsjson).read_text()), bek)
            B['gecti'] = bool(B['gecti'] and B['drive']['gecti'])
        Path(a.cikti).write_text(json.dumps(B, indent=1, ensure_ascii=False, default=str))
        print('birlestir', dict(gecti=B['gecti'], eksik_parca=B['eksik_parca'], fail=B['fail'], cokus=B['cokus'], kontrol=B['kontrol_hepsi'],
                                drive=(B.get('drive') or {}).get('gecti')))
        return 0 if B['gecti'] else 1
    if a.k == 'dal_kapisi':
        K = dal_kapisi(a.dosya); print(json.dumps(K))
        return 0 if K['gecti'] else 1
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
