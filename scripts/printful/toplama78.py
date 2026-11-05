#!/usr/bin/env python3
"""Ornament 78 cift toplama (Serdar 5 Kas: PLAN67 7. madde, "devam" / "Basla"; is akisi ornament-78-toplama.yml). Etsy / Printful yazimi yok,
kaynak klasorlerde silme / tasima yok (yalniz kopya). Yerel mantik testi: toplama78_mantik_testi.py. Plan: docs/ornament/PLAN_TOPLAMA78.md.
Alt komutlar (her biri bir beklenti JSON'u yazar: dict(beklenti, gecti, olculen, kaynak)):
  manifest  TOPLAMA78.json + ISTISNA78.json + kaynak BIRLESIK / BEKLENEN_SONUC -> MANIFEST.json, SHA256SUMS.txt, kopya plani (grup <= 40 dosya)
  kaynak    kaynak klasor lsjson (-R --hash --files-only) = manifest (her dosya bir kez, sha256 esit)
  hedef     hedef klasor lsjson = manifest (kokte tam 390 dosya, ad ve sha256 esit; md5 = kaynak lsjson md5; RAPOR/ disinda fazla dosya yok)
  kopya_log rclone -v loglarinda sunucu tarafi kopya sayisi = 390 (bilgi degil, kapi)
  printful  indirilen hedef dosyalari: dosya sha256 = manifest ve printful_dosya (954x954, mod, 300 dpi, sRGB) 390/390
  ozet      lsjson -> [yol, boyut, sha256] sirali liste (Drive ID icermez; once / sonra kiyasi icin)
  degismedi once / sonra ozet esit
  sonuc     beklenti JSON'larini toplar; eksik beklenti FAIL; istisna ile kabul edilen (kapi FAIL) ciftler ayri satirda
Cikis: 0 PASS, 1 FAIL, 2 cokus."""
import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

_d = Path(__file__).resolve().parent
sys.path.insert(0, str(_d))
import uretim78 as U  # noqa: E402

CIFT78, STIL, YD11 = U.CIFT78, U.STIL, U.YD11
KOYU = ('RUBY', 'SAPPHIRE', 'EMERALD')
KUME = {'YD11': sorted(YD11), 'YD67': sorted(c for c in CIFT78 if c not in YD11)}
# Serdar onayli istisnalar (KARARLAR_20261104_2, 5 Kas): (kapi, onay tarihi, kosu, dE00 azami = karardaki ust deger + 0,005 yuvarlama payi).
# ISTISNA78.json ile AYNI olmali: tek tarafli degisiklik manifest FAIL. Ikisinin ayni commit'te birlikte degismesini bu kontrol YAKALAMAZ.
ISTISNA_ONAYLI = {
    'GEMINI_VIRGO': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42001867106', 2.355),
    'GEMINI_GEMINI': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42063472397', 2.205),
    'PISCES_PISCES': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42063472397', 2.085),
    'GEMINI_SAGITTARIUS': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42063472397', 3.405),
}
# kaynak BEKLENEN_SONUC'ta olmasi gereken beklenti adlari (uretim78_beklenen.py, yeni duzen bolumleri; 15 ad)
KAYNAK_BEKLENTI = ('cl_kontrol_her_parca', 'ornek_png_drive', 'kova_tek_neden', 'printful_dosya', 'dpi_piksel_ayni', 'o2_piksel', 'kenar_on_motor',
                   'aquarius_445_464', 'eta_satirlari', 'katman_silindi', 'siparis_kaydi', 'onarimsiz_ek_fail_listesi', 'birlesik_gecti',
                   'yeni_duzen_modu', 'yd_yerel_test')
BEKLENTILER = ('manifest_78x5', 'kaynak_rapor_kume', 'istisna_kayitli', 'kaynak_beklenen', 'kaynak_drive', 'hedef_drive', 'sunucu_kopya',
               'printful_dosya', 'yerel_sha', 'kaynak_degismedi')
RAPOR_ONEK = 'RAPOR/'
GRUP_MAX = 40                                                                  # ETA icin kopya grubu en cok 40 dosya (HIZ madde 5)


def b(ad, gecti, olculen, kaynak):
    return dict(beklenti=ad, gecti=bool(gecti), olculen=olculen, kaynak=kaynak)


def oku(p):
    return json.loads(Path(p).read_text())


def hedef_ad(cift, stil):
    return f'{cift}_{stil}_954.png'


# ------------------------------------------------------------------------------------------------ manifest
def _istisna_kontrol(c, i, v, dusen, kosu):
    """FAIL cifti icin istisna kaydi: tek dusen kapi = istisna kapisi, eksik / cokus yok, kosu ayni, koyu 3 stil dE00_ham_maks <= azami."""
    dE = {s: ((v.get('koyu') or {}).get(s) or {}).get('dE00_ham_maks') for s in KOYU}
    kayit = dict(dusen_kapilar=dusen, eksik=v.get('eksik'), cokus=v.get('cokus'), istisna=(i or {}).get('kapi'), dE00_ham_maks=dE,
                 dE00_azami=(i or {}).get('dE00_azami'))
    ok = bool(i) and dusen == [i.get('kapi')] and not v.get('eksik') and not v.get('cokus') and str(i.get('kosu')) == kosu
    az = (i or {}).get('dE00_azami')
    ok = ok and isinstance(az, (int, float)) and all(isinstance(x, (int, float)) for x in dE.values()) and max(dE.values()) <= az
    kayit['gecti'] = bool(ok)
    return kayit


def manifest(cfg, istisna, kok):
    """Doner (M, beklentiler). M = dict(dosya=[dict(cift, stil, ad, kaynak, kosu, kaynak_yol, sha256, istisna_kapi)], plan=[...], istisna_fail=[...])."""
    kok = Path(kok)
    S = []
    dosya, gor, kume_ol, ist_ol, bek_ol = [], {}, {}, {}, {}
    kume_ok = ist_ok = bek_ok = True
    I = {x['cift']: x for x in istisna.get('istisna', [])}
    if len(I) != len(istisna.get('istisna', [])):
        ist_ok = False; ist_ol['tekrar_kayit'] = True
    kod = {c: dict(kapi=v[0], onay_tarihi=v[1], kosu=v[2], dE00_azami=v[3]) for c, v in ISTISNA_ONAYLI.items()}
    dosyada = {c: dict(kapi=x.get('kapi'), onay_tarihi=x.get('onay_tarihi'), kosu=x.get('kosu'), dE00_azami=x.get('dE00_azami')) for c, x in I.items()}
    ist_ol['dosya_kod_ayni'] = dosyada == kod
    if dosyada != kod:
        ist_ok = False; ist_ol['dosya'] = dosyada; ist_ol['kod'] = kod
    eksik_karar = sorted(c for c, x in I.items() if not str(x.get('karar') or '').strip())
    if eksik_karar:
        ist_ok = False; ist_ol['karar_yok'] = eksik_karar
    fail_hepsi, ist_fail = {}, []
    for K in cfg['kaynaklar']:
        ad, kosu = K['ad'], str(K['kosu'])
        B = oku(kok / K['rapor'])
        yuk = {}
        for x in B.get('yukleme', []):
            if x.get('kontrol'):
                continue
            c = x.get('cift')
            if c in yuk:
                kume_ok = False; kume_ol.setdefault('rapor_cift_tekrar', []).append(f'{ad}:{c}')
            if not (x.get('yukleme') or {}).get('ok'):
                kume_ok = False; kume_ol.setdefault('yukleme_ok_degil', []).append(f'{ad}:{c}')
            yuk[c] = [y for y in (x.get('yukleme') or {}).get('dosyalar', []) if y['yol'].endswith('_954.png')]
        bek = KUME[K['kume']]
        kume_ol[ad] = dict(rapor=len(yuk), beklenen=len(bek), eksik=sorted(set(bek) - set(yuk)), fazla=sorted(set(yuk) - set(bek)),
                           drive_gecti=(B.get('drive') or {}).get('gecti'), kontrol_hepsi=B.get('kontrol_hepsi'),
                           eksik_parca=B.get('eksik_parca'), cokus=B.get('cokus'))
        if sorted(yuk) != bek or (B.get('drive') or {}).get('gecti') is not True or B.get('kontrol_hepsi') is not True \
                or B.get('eksik_parca') or B.get('cokus'):
            kume_ok = False
        fail = set(B.get('fail') or [])
        for c in sorted(fail):
            fail_hepsi[c] = ad
        for c in bek:
            if c not in yuk:
                continue
            v = (B.get('cift') or {}).get(c) or {}
            sert = (v.get('kapi') or {}).get('sert') or {}
            dusen = sorted(k for k, x in sert.items() if not x)
            fail_mi = c in fail
            if fail_mi != U.cift_fail_mi(v):
                ist_ok = False; ist_ol.setdefault('fail_listesi_tutarsiz', []).append(c)
            if fail_mi:
                kayit = dict(_istisna_kontrol(c, I.get(c), v, dusen, kosu), kaynak=ad)
                ist_ok = ist_ok and kayit['gecti']
                ist_ol.setdefault('fail_cift', {})[c] = kayit
                if I.get(c):
                    ist_fail.append(dict(cift=c, kapi=I[c]['kapi'], kapi_durumu='FAIL', dE00_ham_maks=kayit['dE00_ham_maks'],
                                         dE00_azami=I[c].get('dE00_azami'), onay_tarihi=I[c].get('onay_tarihi'), kosu=kosu))
            elif c in I:
                ist_ok = False; ist_ol.setdefault('kullanilmayan_istisna', []).append(c)
            yollar = {Path(y['yol']).name: y for y in yuk[c]}
            for s in STIL:
                n = hedef_ad(c, s)
                y = yollar.get(n)
                bek_yol = f'FAIL/{c}/{n}' if fail_mi else n
                if not y or y['yol'] != bek_yol or len(yuk[c]) != 5 or not y.get('sha256'):
                    kume_ok = False; kume_ol.setdefault('dosya_hatasi', []).append(dict(cift=c, stil=s, bulunan=(y or {}).get('yol'), beklenen=bek_yol))
                    continue
                if n in gor:
                    kume_ok = False; kume_ol.setdefault('iki_kaynakta', []).append(n)
                    continue
                gor[n] = ad
                dosya.append(dict(cift=c, stil=s, ad=n, kaynak=ad, kosu=kosu, kaynak_yol=y['yol'], sha256=y['sha256'],
                                  istisna_kapi=(I[c]['kapi'] if fail_mi and c in I else None)))
        Bk = oku(kok / K['beklenen']) if K.get('beklenen') else None
        bo = dict(dosya=K.get('beklenen'))
        if not Bk:
            bek_ok = False; bo['yok'] = True
        else:
            adlar = [x['beklenti'] for x in Bk.get('beklentiler', [])]
            dus = [x['beklenti'] for x in Bk.get('beklentiler', []) if not x['gecti']]
            bo['dusen'] = dus
            bo['ad_tam'] = sorted(adlar) == sorted(KAYNAK_BEKLENTI)
            bg = next((x for x in Bk['beklentiler'] if x['beklenti'] == 'birlesik_gecti'), None)
            ol = (bg or {}).get('olculen') or {}
            bf = sorted(ol.get('fail') or [])
            ok_ = bo['ad_tam'] and dus in ([], ['birlesik_gecti'])
            if dus == ['birlesik_gecti']:                                       # tek dusen birlesik_gecti; nedeni yalniz istisna ciftleri
                ok_ = ok_ and bf == sorted(fail) and bool(fail) and set(fail) <= set(I) and not ol.get('eksik_parca') and not ol.get('cokus')
            bo['birlesik_fail'] = bf
            if not ok_:
                bek_ok = False
        bek_ol[ad] = bo
    eksik_ist = sorted(set(I) - set(fail_hepsi))
    if eksik_ist:
        ist_ok = False; ist_ol['raporda_fail_degil'] = eksik_ist
    cifts = sorted({x['cift'] for x in dosya})
    say = {c: sum(1 for x in dosya if x['cift'] == c) for c in cifts}
    sha_tekil = len({x['sha256'] for x in dosya})
    m_ok = (len(dosya) == 390 and cifts == CIFT78 and all(v == 5 for v in say.values()) and len({x['ad'] for x in dosya}) == 390
            and sha_tekil == 390)
    S.append(b('manifest_78x5', m_ok and kume_ok, dict(dosya=len(dosya), cift=len(cifts), eksik_cift=sorted(set(CIFT78) - set(cifts)),
               bes_degil=sorted(c for c, v in say.items() if v != 5), sha_tekil=sha_tekil),
               'kaynak BIRLESIK yukleme kayitlari (_954.png); 390 ad ve 390 tekil sha256'))
    S.append(b('kaynak_rapor_kume', kume_ok, kume_ol, 'BIRLESIK yukleme cift kumesi = YD11 / YD67; drive.gecti, kontrol_hepsi, yukleme.ok, eksik parca / cokus yok'))
    S.append(b('istisna_kayitli', ist_ok, ist_ol, 'ISTISNA78.json + toplama78.ISTISNA_ONAYLI + BIRLESIK fail / kapi.sert / koyu dE00_ham_maks'))
    S.append(b('kaynak_beklenen', bek_ok, bek_ol, 'kaynak BEKLENEN_SONUC: 15 beklenti adi tam; yalniz birlesik_gecti dusebilir, nedeni yalniz istisna ciftleri'))
    plan = []
    for K in cfg['kaynaklar']:
        gr = {}
        for x in sorted(dosya, key=lambda x: x['ad']):
            if x['kaynak'] == K['ad']:
                d = str(Path(x['kaynak_yol']).parent)
                gr.setdefault('' if d == '.' else d, []).append(x['ad'])
        for d in sorted(gr):
            L = gr[d]
            for j in range(0, len(L), GRUP_MAX):
                plan.append(dict(kaynak=K['ad'], dizin=d, dosya=L[j:j + GRUP_MAX]))
    M = dict(dosya=sorted(dosya, key=lambda x: x['ad']), plan=plan, istisna=sorted(c for c in I),
             istisna_fail=sorted(ist_fail, key=lambda x: x['cift']))
    return M, S


def sha_listesi(M):
    return ''.join(f"{x['sha256']}  {x['ad']}\n" for x in M['dosya'])


def manifest_csv(M):
    f = io.StringIO(); w = csv.writer(f, lineterminator='\n')
    w.writerow(['cift', 'stil', 'dosya', 'sha256', 'kaynak_kosu', 'kaynak_yol', 'istisna_kapi', 'kapi_durumu'])
    for x in M['dosya']:
        w.writerow([x['cift'], x['stil'], x['ad'], x['sha256'], x['kosu'], x['kaynak_yol'], x['istisna_kapi'] or '',
                    'FAIL (istisna ile kabul)' if x['istisna_kapi'] else 'PASS'])
    return f.getvalue()


def istisna_satirlari(M):
    out = []
    for x in M.get('istisna_fail', []):
        d = x['dE00_ham_maks']
        out.append(f"ISTISNA ile kabul (kapi FAIL): {x['cift']} | kapi {x['kapi']} FAIL | dE00_ham_maks {min(d.values()):.3f}-{max(d.values()):.3f}"
                   f" (esik 2, azami {x['dE00_azami']}) | onay {x['onay_tarihi']} | kosu {x['kosu']}")
    return out


# ------------------------------------------------------------------------------------------------ Drive kiyaslari
def _dosyalar(lsjson, alan='sha256'):
    D = {}
    for d in lsjson:
        if d.get('IsDir'):
            continue
        h = d.get('Hashes') or {}
        D.setdefault(d['Path'], []).append(h.get(alan) or h.get(alan.upper()) or (h.get('SHA-256') if alan == 'sha256' else None))
    return D


def kaynak_dogrula(M, ls):
    """ls: {kaynak_ad: lsjson}. Manifestteki her kaynak yolu tam bir kez ve sha256 esit."""
    ol, ok = {}, True
    for K in sorted({x['kaynak'] for x in M['dosya']}):
        D = _dosyalar(ls.get(K) or [])
        r = dict(eksik=[], tekrar=[], sha_farkli=[], sha_yok=[], lsjson_var=K in ls)
        for x in M['dosya']:
            if x['kaynak'] != K:
                continue
            v = D.get(x['kaynak_yol'])
            if not v:
                r['eksik'].append(x['kaynak_yol'])
            elif len(v) > 1:
                r['tekrar'].append(x['kaynak_yol'])
            elif not v[0]:
                r['sha_yok'].append(x['kaynak_yol'])
            elif v[0] != x['sha256']:
                r['sha_farkli'].append(x['kaynak_yol'])
        r['gecti'] = r['lsjson_var'] and not (r['eksik'] or r['tekrar'] or r['sha_farkli'] or r['sha_yok'])
        ok = ok and r['gecti']; ol[K] = r
    ok = ok and bool(ol)
    return b('kaynak_drive', ok, ol, 'rclone lsjson -R --hash (kaynak klasorler) = MANIFEST')


def hedef_dogrula(M, ls, kaynak_ls=None):
    """hedef kok = manifest (ad, sha256). kaynak_ls verilirse md5 de kaynak lsjson md5'i ile kiyaslanir (ikinci, bagimsiz ozet)."""
    D = _dosyalar(ls)
    Dm = _dosyalar(ls, 'md5')
    bek = {x['ad']: x['sha256'] for x in M['dosya']}
    kok = {p: v for p, v in D.items() if not p.startswith(RAPOR_ONEK)}
    r = dict(beklenen=len(bek), kok_dosya=sum(len(v) for v in kok.values()),
             eksik=sorted(set(bek) - set(kok)), fazla=sorted(set(kok) - set(bek)),
             tekrar=sorted(p for p, v in kok.items() if len(v) > 1),
             sha_farkli=sorted(p for p, v in kok.items() if p in bek and len(v) == 1 and v[0] and v[0] != bek[p]),
             sha_yok=sorted(p for p, v in kok.items() if p in bek and not all(v)))
    md5_farkli = md5_yok = []
    if kaynak_ls is not None:
        km = {}
        for x in M['dosya']:
            v = _dosyalar(kaynak_ls.get(x['kaynak']) or [], 'md5').get(x['kaynak_yol']) or [None]
            km[x['ad']] = v[0]
        md5_yok = sorted(p for p in bek if not km.get(p) or not (Dm.get(p) or [None])[0])
        md5_farkli = sorted(p for p in bek if p not in md5_yok and (Dm.get(p) or [None])[0] != km[p])
        r['md5_kiyas'] = True
    r['md5_farkli'], r['md5_yok'] = md5_farkli, md5_yok
    ok = len(bek) == 390 and r['kok_dosya'] == 390 and not (r['eksik'] or r['fazla'] or r['tekrar'] or r['sha_farkli'] or r['sha_yok']
                                                             or md5_farkli or md5_yok) and kaynak_ls is not None
    return b('hedef_drive', ok, r, 'rclone lsjson -R --hash (hedef klasor) sha256 = MANIFEST, md5 = kaynak lsjson md5')


KOPYA_DESEN = re.compile(r'INFO\s*:\s*(.+?): Copied \(server-side copy\)')


def kopya_log(M, loglar):
    """rclone -v loglari: her manifest dosyasi icin tam bir 'Copied (server-side copy)' satiri; 'Copied (new)' (indir-yukle) yok."""
    ad = []
    yeni = 0
    for t in loglar:
        for l in t.splitlines():
            m = KOPYA_DESEN.search(l)
            if m:
                ad.append(Path(m.group(1).strip()).name)
            elif 'Copied (new)' in l or 'Copied (replaced' in l:
                yeni += 1
    bek = sorted(x['ad'] for x in M['dosya'])
    ok = sorted(ad) == bek and yeni == 0
    return b('sunucu_kopya', ok, dict(sunucu_tarafi=len(ad), beklenen=len(bek), eksik=sorted(set(bek) - set(ad))[:20],
                                      tekrar=sorted({a for a in ad if ad.count(a) > 1})[:20], sunucu_disi=yeni),
             'rclone copy -v log (Copied (server-side copy)) = MANIFEST')


def printful_yerel(M, dizin):
    """indirilen hedef dosyalari: dosya sha256 = manifest; printful_dosya (uretim78) her dosyada gecti."""
    dizin = Path(dizin)
    sha_f, sha_yok, pf = [], [], {}
    for x in M['dosya']:
        f = dizin / x['ad']
        if not f.exists():
            sha_yok.append(x['ad']); continue
        if U.dosya_sha(f) != x['sha256']:
            sha_f.append(x['ad'])
        pf[x['ad']] = U.printful_dosya(f, x['stil'])
    fazla = sorted(p.name for p in dizin.iterdir() if p.is_file() and p.name not in {x['ad'] for x in M['dosya']}) if dizin.exists() else []
    gec = [k for k, v in pf.items() if v['gecti']]
    dus = {k: v for k, v in pf.items() if not v['gecti']}
    s1 = b('yerel_sha', len(M['dosya']) == 390 and not sha_f and not sha_yok and not fazla,
           dict(dosya=len(M['dosya']) - len(sha_yok), sha_farkli=sha_f, eksik=sha_yok, fazla=fazla), 'indirilen hedef dosyalar sha256 = MANIFEST')
    s2 = b('printful_dosya', len(gec) == 390 and len(pf) == 390, dict(gecti=len(gec), toplam=len(pf), dusen=dus),
           'uretim78.printful_dosya (954x954; RGB, SADE_ALTIN RGBA; 300 dpi +- 0,5; ICC yok ya da sRGB; PRINTFUL_ORNAMENT.md 900 Circle)')
    return s1, s2


def ozet(lsjson):
    return sorted([d['Path'], d.get('Size'), (d.get('Hashes') or {}).get('sha256')] for d in lsjson if not d.get('IsDir'))


def degismedi(once, sonra):
    fark = {k: dict(once=len(once.get(k) or []), sonra=len(sonra.get(k) or []), ayni=once.get(k) == sonra.get(k)) for k in sorted(set(once) | set(sonra))}
    ok = bool(once) and set(once) == set(sonra) and all(v['ayni'] and v['once'] > 0 for v in fark.values())
    return b('kaynak_degismedi', ok, fark, 'kaynak klasor ozeti (yol, boyut, sha256) kopyadan once = sonra')


def sonuc(dizin):
    dizin = Path(dizin)
    R, eksik = [], []
    for ad in BEKLENTILER:
        f = dizin / f'B_{ad}.json'
        if f.exists():
            R.append(oku(f))
        else:
            eksik.append(ad); R.append(b(ad, False, 'beklenti dosyasi yok', 'sonuc'))
    M = oku(dizin / 'MANIFEST.json') if (dizin / 'MANIFEST.json').exists() else {}
    return dict(beklentiler=R, eksik=eksik, hepsi_gecti=all(x['gecti'] for x in R),
                istisna_kapi_fail=M.get('istisna_fail', []), istisna_satirlari=istisna_satirlari(M) if M else [])


def yaz_b(dizin, x):
    Path(dizin).mkdir(parents=True, exist_ok=True)
    Path(dizin, f"B_{x['beklenti']}.json").write_text(json.dumps(x, indent=1, ensure_ascii=False, default=str))
    print('PASS' if x['gecti'] else 'FAIL', x['beklenti'], '|', json.dumps(x['olculen'], default=str, ensure_ascii=False)[:300], flush=True)
    return x['gecti']


def _ls_arg(liste):
    return {x.split('=', 1)[0]: oku(x.split('=', 1)[1]) for x in liste}


# ------------------------------------------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest='k', required=True)
    p = sp.add_parser('manifest'); p.add_argument('--cfg', required=True); p.add_argument('--istisna', required=True); p.add_argument('--kok', required=True)
    p.add_argument('--cikti', required=True)
    p = sp.add_parser('kaynak'); p.add_argument('--manifest', required=True); p.add_argument('--lsjson', nargs='+', required=True, help='ad=dosya')
    p.add_argument('--cikti', required=True)
    p = sp.add_parser('hedef'); p.add_argument('--manifest', required=True); p.add_argument('--lsjson', required=True)
    p.add_argument('--kaynak_lsjson', nargs='+', required=True, help='ad=dosya'); p.add_argument('--cikti', required=True)
    p = sp.add_parser('kopya_log'); p.add_argument('--manifest', required=True); p.add_argument('--log', nargs='+', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('printful'); p.add_argument('--manifest', required=True); p.add_argument('--dizin', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('ozet'); p.add_argument('--lsjson', nargs='+', required=True, help='ad=dosya'); p.add_argument('--cikti', required=True)
    p = sp.add_parser('degismedi'); p.add_argument('--once', required=True); p.add_argument('--sonra', required=True); p.add_argument('--cikti', required=True)
    p = sp.add_parser('sonuc'); p.add_argument('--cikti', required=True)
    a = ap.parse_args()
    if a.k == 'manifest':
        M, S = manifest(oku(a.cfg), oku(a.istisna), a.kok)
        c = Path(a.cikti); c.mkdir(parents=True, exist_ok=True)
        (c / 'MANIFEST.json').write_text(json.dumps(M, indent=1, ensure_ascii=False))
        (c / 'SHA256SUMS.txt').write_text(sha_listesi(M))
        (c / 'MANIFEST_csv.txt').write_text(manifest_csv(M))
        pd = c / 'plan'; pd.mkdir(exist_ok=True)
        for i, g in enumerate(M['plan'], 1):
            (pd / f'{i:02d}.txt').write_text(''.join(f + '\n' for f in g['dosya']))
            (pd / f'{i:02d}.yol').write_text(f"{g['kaynak']}/{g['dizin']}".rstrip('/') + '\n')
        ok = all([yaz_b(c, x) for x in S])
        print('manifest dosya', len(M['dosya']), '| plan grubu', len(M['plan']), '| istisna', M['istisna'])
        for l in istisna_satirlari(M):
            print(l)
        return 0 if ok else 1
    if a.k == 'kaynak':
        return 0 if yaz_b(a.cikti, kaynak_dogrula(oku(a.manifest), _ls_arg(a.lsjson))) else 1
    if a.k == 'hedef':
        return 0 if yaz_b(a.cikti, hedef_dogrula(oku(a.manifest), oku(a.lsjson), _ls_arg(a.kaynak_lsjson))) else 1
    if a.k == 'kopya_log':
        return 0 if yaz_b(a.cikti, kopya_log(oku(a.manifest), [Path(f).read_text(errors='ignore') for f in a.log])) else 1
    if a.k == 'printful':
        s1, s2 = printful_yerel(oku(a.manifest), a.dizin)
        g1, g2 = yaz_b(a.cikti, s1), yaz_b(a.cikti, s2)
        return 0 if (g1 and g2) else 1
    if a.k == 'ozet':
        O = {k: ozet(v) for k, v in _ls_arg(a.lsjson).items()}
        Path(a.cikti).write_text(json.dumps(O, indent=0)); print('ozet', {k: len(v) for k, v in O.items()})
        return 0
    if a.k == 'degismedi':
        return 0 if yaz_b(Path(a.cikti), degismedi(oku(a.once), oku(a.sonra))) else 1
    if a.k == 'sonuc':
        R = sonuc(a.cikti)
        Path(a.cikti, 'TOPLAMA_SONUC.json').write_text(json.dumps(R, indent=1, ensure_ascii=False, default=str))
        for x in R['beklentiler']:
            print('PASS' if x['gecti'] else 'FAIL', x['beklenti'])
        for l in R['istisna_satirlari']:
            print(l)
        print('TOPLAMA78', 'PASS' if R['hepsi_gecti'] else 'FAIL', '| eksik', R['eksik'], '| istisna ile kabul (kapi FAIL)', len(R['istisna_kapi_fail']))
        return 0 if R['hepsi_gecti'] else 1
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
