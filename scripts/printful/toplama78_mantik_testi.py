#!/usr/bin/env python3
"""toplama78.py yerel mantik testi (bilinen PASS + bilinen FAIL; Serdar 5 Kas, ornament 78 toplama). Gercek dal raporlari (iki kaynak BIRLESIK +
BEKLENEN_SONUC) ve sentetik lsjson / PNG / rclone logu ile. Her vaka beklenen sonucla karsilastirilir; biri tutmazsa cikis 1.
Kullanim: python3 -I scripts/printful/toplama78_mantik_testi.py [--kok .]"""
import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

_d = Path(__file__).resolve().parent
sys.path.insert(0, str(_d))
import toplama78 as T  # noqa: E402


def gecti(S, ad):
    return next(x for x in S if x['beklenti'] == ad)['gecti']


def kur(kok, cfg, ist, Bmod=None, Kmod=None):
    """gecici kok: cfg kaynak raporlarinin kopyalari (Bmod / Kmod ile bozulmus) -> manifest."""
    t = Path(tempfile.mkdtemp())
    c2 = copy.deepcopy(cfg)
    for i, K in enumerate(c2['kaynaklar']):
        for alan, mod in (('rapor', Bmod), ('beklenen', Kmod)):
            J = json.loads((kok / K[alan]).read_text())
            if mod:
                mod(i, J)
            (t / K[alan]).parent.mkdir(parents=True, exist_ok=True); (t / K[alan]).write_text(json.dumps(J))
    try:
        return T.manifest(c2, ist, t)
    finally:
        shutil.rmtree(t)


def md5(s):
    import hashlib
    return hashlib.md5(s.encode()).hexdigest()


def ls_kaynak(M):
    L = {}
    for x in M['dosya']:
        L.setdefault(x['kaynak'], []).append(dict(Path=x['kaynak_yol'], IsDir=False, Size=1, Hashes=dict(sha256=x['sha256'], md5=md5(x['sha256']))))
    for K in L:                                                                  # kaynakta baska dosyalar da var (GERCEK_BOY, RAPOR): kapi bozmaz
        L[K] += [dict(Path='GERCEK_BOY/x.png', IsDir=False, Hashes=dict(sha256='0' * 64, md5='0' * 32)), dict(Path='FAIL', IsDir=True)]
    return L


def ls_hedef(M):
    return [dict(Path=x['ad'], IsDir=False, Size=1, Hashes=dict(sha256=x['sha256'], md5=md5(x['sha256']))) for x in M['dosya']] + \
           [dict(Path='RAPOR', IsDir=True), dict(Path='RAPOR/MANIFEST.json', IsDir=False, Hashes=dict(sha256='1' * 64))]


def png_yaz(dizin, M, bozuk=None):
    """her manifest dosyasi icin printful uyumlu PNG; manifest sha'si bu dosyalarin sha'sina cevrilir (sentetik)."""
    from PIL import Image
    M2 = copy.deepcopy(M)
    dizin.mkdir(parents=True, exist_ok=True)
    for i, x in enumerate(M2['dosya']):
        mod = 'RGBA' if x['stil'] == 'SADE_ALTIN' else 'RGB'
        boy, dpi = (954, 954), (300, 300)
        if bozuk == 'boy' and i == 0:
            boy = (950, 954)
        if bozuk == 'mod' and x['stil'] == 'RUBY' and i < 5:
            mod = 'RGBA'
        if bozuk == 'dpi' and i == 1:
            dpi = (72, 72)
        Image.new(mod, boy, (i % 255, 10, 20) if mod == 'RGB' else (i % 255, 10, 20, 255)).save(dizin / x['ad'], dpi=dpi)
        x['sha256'] = T.U.dosya_sha(dizin / x['ad'])
    return M2


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--kok', default='.')
    a = ap.parse_args()
    kok = Path(a.kok).resolve()
    cfg = json.loads((kok / 'docs/ornament/TOPLAMA78.json').read_text())
    ist = json.loads((kok / 'docs/ornament/ISTISNA78.json').read_text())
    V = []

    def vaka(ad, olculen, beklenen):
        V.append(dict(vaka=ad, olculen=olculen, beklenen=beklenen, tuttu=olculen == beklenen))
        print('OK ' if olculen == beklenen else 'HATA', ad, '| olculen', olculen, 'beklenen', beklenen, flush=True)

    def kod_ile(ek, fn):                                                        # ISTISNA_ONAYLI gecici degisiklik (geri alinir)
        eski = dict(T.ISTISNA_ONAYLI)
        T.ISTISNA_ONAYLI.update(ek)
        try:
            return fn()
        finally:
            T.ISTISNA_ONAYLI.clear(); T.ISTISNA_ONAYLI.update(eski)

    # --- bilinen PASS: gercek raporlar
    M, S = T.manifest(cfg, ist, kok)
    vaka('PASS gercek manifest (4 beklenti)', all(x['gecti'] for x in S), True)
    vaka('PASS 390 dosya', len(M['dosya']), 390)
    vaka('PASS kopya gruplari <= 40 dosya, toplam 390', (max(len(g['dosya']) for g in M['plan']), sum(len(g['dosya']) for g in M['plan'])), (40, 390))
    vaka('PASS FAIL ciftleri FAIL/<CIFT>/ yolundan', sorted({x['cift'] for x in M['dosya'] if x['kaynak_yol'].startswith('FAIL/')}),
         sorted(T.ISTISNA_ONAYLI))
    vaka('PASS istisna_kapi yalniz 4 ciftte', sorted({x['cift'] for x in M['dosya'] if x['istisna_kapi']}), sorted(T.ISTISNA_ONAYLI))
    vaka('PASS istisna satirlari 4, hepsi "kapi ... FAIL"', (len(T.istisna_satirlari(M)), all(' FAIL |' in l for l in T.istisna_satirlari(M))), (4, True))
    vaka('PASS CSV: 20 satir FAIL (istisna ile kabul)', T.manifest_csv(M).count('FAIL (istisna ile kabul)'), 20)

    # --- bilinen FAIL: istisna katmani
    i2 = copy.deepcopy(ist); i2['istisna'] = [x for x in i2['istisna'] if x['cift'] != 'GEMINI_SAGITTARIUS']
    vaka('FAIL istisna dosyasinda GS yok', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'][0]['kapi'] = 'bosluk_20_20_20'
    vaka('FAIL istisna kapi adi yanlis', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'].append(dict(cift='LEO_TAURUS', kapi='koyu_dE00_son_ham_le_2', onay_tarihi='2026-11-05', kosu='42063472397',
                                                       dE00_azami=2.1, karar='x'))
    vaka('FAIL dosyada fazla istisna (koddan farkli)', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'][1]['onay_tarihi'] = '2026-11-06'
    vaka('FAIL onay tarihi koddan farkli', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'][1]['dE00_azami'] = 9.9
    vaka('FAIL azami dosyada koddan farkli', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'][2]['karar'] = ''
    vaka('FAIL karar alani bos', gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli'), False)
    i2 = copy.deepcopy(ist); i2['istisna'][0]['kosu'] = '42063472397'
    vaka('FAIL istisna kosusu kaynak kosusundan farkli',
         kod_ile({'GEMINI_VIRGO': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42063472397', 2.355)},
                 lambda: gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli')), False)
    i2 = copy.deepcopy(ist); i2['istisna'].append(dict(cift='LEO_TAURUS', kapi='koyu_dE00_son_ham_le_2', onay_tarihi='2026-11-05', kosu='42063472397',
                                                       dE00_azami=2.1, karar='x'))
    vaka('FAIL istisna PASS cifte (kullanilmayan; dosya + kod birlikte)',
         kod_ile({'LEO_TAURUS': ('koyu_dE00_son_ham_le_2', '2026-11-05', '42063472397', 2.1)},
                 lambda: gecti(T.manifest(cfg, i2, kok)[1], 'istisna_kayitli')), False)

    def dE_yuksek(i, B):                                                       # istisna cifti degeri azami ustunde (ayni kapi, daha kotu)
        if 'GEMINI_GEMINI' in B.get('cift', {}):
            B['cift']['GEMINI_GEMINI']['koyu']['SAPPHIRE']['dE00_ham_maks'] = 9.9
    vaka('FAIL istisna ciftinde dE00 azami ustunde', gecti(kur(kok, cfg, ist, dE_yuksek)[1], 'istisna_kayitli'), False)

    def dE_yok(i, B):
        if 'PISCES_PISCES' in B.get('cift', {}):
            del B['cift']['PISCES_PISCES']['koyu']['RUBY']['dE00_ham_maks']
    vaka('FAIL istisna ciftinde dE00 degeri yok', gecti(kur(kok, cfg, ist, dE_yok)[1], 'istisna_kayitli'), False)

    def ek_kapi(i, B):                                                         # FAIL ciftinde ikinci kapi da duser
        if 'GEMINI_GEMINI' in B.get('cift', {}):
            B['cift']['GEMINI_GEMINI']['kapi']['sert']['printful_dosya_RUBY'] = False
    vaka('FAIL istisna ciftinde ek kapi FAIL', gecti(kur(kok, cfg, ist, ek_kapi)[1], 'istisna_kayitli'), False)

    def yeni_fail(i, B):                                                       # istisnasiz yeni FAIL cifti (kok yolu FAIL/'a tasinmis)
        if 'LEO_TAURUS' in B.get('cift', {}):
            B['cift']['LEO_TAURUS']['kapi']['sert']['koyu_dE00_son_ham_le_2'] = False; B['fail'] = sorted(B['fail'] + ['LEO_TAURUS'])
            for x in B['yukleme']:
                if x['cift'] == 'LEO_TAURUS':
                    for y in x['yukleme']['dosyalar']:
                        if y['yol'].endswith('_954.png'):
                            y['yol'] = 'FAIL/LEO_TAURUS/' + y['yol']
    vaka('FAIL istisnasiz yeni FAIL cifti', gecti(kur(kok, cfg, ist, yeni_fail)[1], 'istisna_kayitli'), False)

    def fail_tutarsiz(i, B):                                                   # fail listesinde var ama kapi.sert hepsi True
        if 'GEMINI_GEMINI' in B.get('cift', {}):
            B['cift']['GEMINI_GEMINI']['kapi']['sert']['koyu_dE00_son_ham_le_2'] = True
    vaka('FAIL fail listesi kapi.sert ile tutarsiz', gecti(kur(kok, cfg, ist, fail_tutarsiz)[1], 'istisna_kayitli'), False)

    # --- bilinen FAIL: kume / dosya / kaynak rapor durumu
    def cift_eksik(i, B):
        if i == 1:
            B['yukleme'] = [x for x in B['yukleme'] if x['cift'] != 'VIRGO_VIRGO']
    S2 = kur(kok, cfg, ist, cift_eksik)[1]
    vaka('FAIL kaynakta 1 cift eksik (manifest + kume)', (gecti(S2, 'manifest_78x5'), gecti(S2, 'kaynak_rapor_kume')), (False, False))

    def stil_eksik(i, B):
        if i == 1:
            for x in B['yukleme']:
                if x['cift'] == 'ARIES_LEO':
                    x['yukleme']['dosyalar'] = [y for y in x['yukleme']['dosyalar'] if 'FILDISI' not in y['yol']]
    vaka('FAIL bir ciftte stil eksik', gecti(kur(kok, cfg, ist, stil_eksik)[1], 'manifest_78x5'), False)

    def iki_kaynak(i, B):                                                      # YD11 ciftinin kaydi YD67 raporuna da girmis
        if i == 1:
            B['yukleme'].append(dict(cift='TAURUS_TAURUS', kontrol=False, yukleme=dict(ok=True, dosyalar=[dict(yol=f'TAURUS_TAURUS_{s}_954.png', sha256='a' * 64) for s in T.STIL])))
    vaka('FAIL cift iki kaynakta', gecti(kur(kok, cfg, ist, iki_kaynak)[1], 'kaynak_rapor_kume'), False)

    def ayni_sha(i, B):
        if i == 1:
            for x in B['yukleme']:
                if x['cift'] == 'ARIES_LEO':
                    for y in x['yukleme']['dosyalar']:
                        if y['yol'].endswith('_954.png'):
                            y['sha256'] = 'b' * 64
    vaka('FAIL iki dosyada ayni sha256', gecti(kur(kok, cfg, ist, ayni_sha)[1], 'manifest_78x5'), False)

    def drive_false(i, B):
        if i == 0:
            B['drive']['gecti'] = False
    vaka('FAIL kaynak BIRLESIK drive.gecti False', gecti(kur(kok, cfg, ist, drive_false)[1], 'kaynak_rapor_kume'), False)

    def kontrol_false(i, B):
        if i == 1:
            B['kontrol_hepsi'] = False
    vaka('FAIL kaynak BIRLESIK kontrol_hepsi False', gecti(kur(kok, cfg, ist, kontrol_false)[1], 'kaynak_rapor_kume'), False)

    def yukleme_ok_false(i, B):
        if i == 1:
            B['yukleme'][3]['yukleme']['ok'] = False
    vaka('FAIL kaynak yukleme.ok False', gecti(kur(kok, cfg, ist, yukleme_ok_false)[1], 'kaynak_rapor_kume'), False)

    def kontrol_sayilir(i, B):                                                  # kontrol kaydi yukleme listesinde: atlanir, PASS kalir
        if i == 0:
            B['yukleme'].append(dict(cift='CANCER_LIBRA', kontrol=True, yukleme=dict(ok=True, dosyalar=[])))
    vaka('PASS kontrol kaydi atlanir', all(x['gecti'] for x in kur(kok, cfg, ist, kontrol_sayilir)[1]), True)

    # --- bilinen FAIL: kaynak BEKLENEN_SONUC
    def bek_ek(i, J):
        if i == 0:
            for x in J['beklentiler']:
                if x['beklenti'] == 'printful_dosya':
                    x['gecti'] = False
    vaka('FAIL kaynak beklentide printful_dosya FAIL', gecti(kur(kok, cfg, ist, None, bek_ek)[1], 'kaynak_beklenen'), False)

    def bek_cokus(i, J):
        if i == 1:
            for x in J['beklentiler']:
                if x['beklenti'] == 'birlesik_gecti':
                    x['olculen']['cokus'] = ['ARIES_LEO']
    vaka('FAIL birlesik_gecti nedeni cokus', gecti(kur(kok, cfg, ist, None, bek_cokus)[1], 'kaynak_beklenen'), False)

    def bek_kisa(i, J):                                                        # yalniz birlesik_gecti birakilmis
        if i == 1:
            J['beklentiler'] = [x for x in J['beklentiler'] if x['beklenti'] == 'birlesik_gecti']
    vaka('FAIL kaynak beklenti listesi eksik', gecti(kur(kok, cfg, ist, None, bek_kisa)[1], 'kaynak_beklenen'), False)

    # --- kaynak Drive
    L = ls_kaynak(M)
    vaka('PASS kaynak lsjson', T.kaynak_dogrula(M, L)['gecti'], True)
    K0 = M['dosya'][3]['kaynak']
    L2 = copy.deepcopy(L); L2[M['dosya'][0]['kaynak']] = [d for d in L2[M['dosya'][0]['kaynak']] if d['Path'] != M['dosya'][0]['kaynak_yol']]
    vaka('FAIL kaynakta dosya eksik', T.kaynak_dogrula(M, L2)['gecti'], False)
    L2 = copy.deepcopy(L); L2[K0].append(dict(Path=M['dosya'][3]['kaynak_yol'], IsDir=False, Hashes=dict(sha256=M['dosya'][3]['sha256'])))
    vaka('FAIL kaynakta ayni adli iki dosya', T.kaynak_dogrula(M, L2)['gecti'], False)
    L2 = copy.deepcopy(L); x = next(d for d in L2[K0] if d['Path'] == M['dosya'][3]['kaynak_yol']); x['Hashes']['sha256'] = 'c' * 64
    vaka('FAIL kaynak sha farkli', T.kaynak_dogrula(M, L2)['gecti'], False)
    L2 = copy.deepcopy(L); x = next(d for d in L2[K0] if d['Path'] == M['dosya'][3]['kaynak_yol']); x['Hashes'] = {'md5': 'x'}
    vaka('FAIL kaynak sha256 yok', T.kaynak_dogrula(M, L2)['gecti'], False)
    L2 = {k: v for k, v in L.items() if k != K0}
    vaka('FAIL kaynak lsjson yok', T.kaynak_dogrula(M, L2)['gecti'], False)

    # --- hedef Drive
    H = ls_hedef(M)
    vaka('PASS hedef lsjson (RAPOR/ haric, md5 kiyasli)', T.hedef_dogrula(M, H, L)['gecti'], True)
    vaka('FAIL hedef kaynak lsjson verilmemis', T.hedef_dogrula(M, H, None)['gecti'], False)
    vaka('FAIL hedef 389 dosya', T.hedef_dogrula(M, H[1:], L)['gecti'], False)
    vaka('FAIL hedef fazla dosya', T.hedef_dogrula(M, H + [dict(Path='FAIL/GEMINI_VIRGO/x.png', IsDir=False, Hashes=dict(sha256='d' * 64))], L)['gecti'], False)
    H2 = copy.deepcopy(H); H2[5]['Hashes']['sha256'] = 'e' * 64
    vaka('FAIL hedef sha farkli', T.hedef_dogrula(M, H2, L)['gecti'], False)
    H2 = copy.deepcopy(H); del H2[6]['Hashes']['sha256']
    vaka('FAIL hedef sha256 yok', T.hedef_dogrula(M, H2, L)['gecti'], False)
    H2 = copy.deepcopy(H); H2[8]['Hashes']['md5'] = 'f' * 32
    vaka('FAIL hedef md5 kaynaktan farkli', T.hedef_dogrula(M, H2, L)['gecti'], False)
    H2 = copy.deepcopy(H); H2.append(copy.deepcopy(H2[7]))
    vaka('FAIL hedef ayni adli iki dosya', T.hedef_dogrula(M, H2, L)['gecti'], False)
    H2 = copy.deepcopy(H); H2[9]['Path'] = 'FAIL/' + H2[9]['Path']
    vaka('FAIL hedefte dosya alt klasorde', T.hedef_dogrula(M, H2, L)['gecti'], False)

    # --- sunucu tarafi kopya logu
    lg = [f"2026/11/05 18:00:{i % 60:02d} INFO  : {x['ad']}: Copied (server-side copy)\n" for i, x in enumerate(M['dosya'])]
    vaka('PASS kopya logu 390 sunucu tarafi', T.kopya_log(M, [''.join(lg[:200]), ''.join(lg[200:])])['gecti'], True)
    vaka('FAIL kopya logu 389', T.kopya_log(M, [''.join(lg[1:])])['gecti'], False)
    vaka('FAIL kopya logunda indir-yukle (Copied (new))', T.kopya_log(M, [''.join(lg), f"INFO  : {M['dosya'][0]['ad']}: Copied (new)\n"])['gecti'], False)
    vaka('FAIL kopya logunda tekrar', T.kopya_log(M, [''.join(lg) + lg[0]])['gecti'], False)

    # --- printful + yerel sha
    t = Path(tempfile.mkdtemp())
    try:
        Mp = png_yaz(t / 'iyi', M)
        s1, s2 = T.printful_yerel(Mp, t / 'iyi')
        vaka('PASS printful 390 + yerel sha', (s1['gecti'], s2['gecti']), (True, True))
        (t / 'iyi' / 'fazla.png').write_bytes(b'x')
        vaka('FAIL indirilen klasorde fazla dosya', T.printful_yerel(Mp, t / 'iyi')[0]['gecti'], False)
        (t / 'iyi' / 'fazla.png').unlink()
        Mx = copy.deepcopy(Mp); Mx['dosya'][2]['sha256'] = 'f' * 64
        vaka('FAIL yerel sha farkli', T.printful_yerel(Mx, t / 'iyi')[0]['gecti'], False)
        (t / 'iyi' / Mp['dosya'][4]['ad']).unlink()
        vaka('FAIL yerel dosya eksik', T.printful_yerel(Mp, t / 'iyi')[0]['gecti'], False)
        vaka('FAIL indirme klasoru yok', T.printful_yerel(Mp, t / 'yok')[1]['gecti'], False)
        for bz in ('boy', 'mod', 'dpi'):
            Mb = png_yaz(t / bz, M, bz)
            vaka(f'FAIL printful {bz}', T.printful_yerel(Mb, t / bz)[1]['gecti'], False)
    finally:
        shutil.rmtree(t)

    # --- once / sonra
    O = {k: T.ozet(v) for k, v in L.items()}
    vaka('PASS kaynak degismedi', T.degismedi(O, copy.deepcopy(O))['gecti'], True)
    O2 = copy.deepcopy(O); O2[K0] = O2[K0][1:]
    vaka('FAIL kaynakta dosya silinmis', T.degismedi(O, O2)['gecti'], False)
    O2 = copy.deepcopy(O); O2[K0][0][2] = '9' * 64
    vaka('FAIL kaynakta dosya degismis', T.degismedi(O, O2)['gecti'], False)
    vaka('FAIL once bos', T.degismedi({}, {})['gecti'], False)

    # --- sonuc: eksik beklenti, istisna satirlari
    t = Path(tempfile.mkdtemp())
    try:
        (t / 'MANIFEST.json').write_text(json.dumps(M))
        for ad in T.BEKLENTILER[:-1]:
            (t / f'B_{ad}.json').write_text(json.dumps(T.b(ad, True, 1, 'test')))
        vaka('FAIL sonuc: kaynak_degismedi beklentisi yok', T.sonuc(t)['hepsi_gecti'], False)
        (t / f'B_{T.BEKLENTILER[-1]}.json').write_text(json.dumps(T.b(T.BEKLENTILER[-1], True, 1, 'test')))
        R = T.sonuc(t)
        vaka('PASS sonuc: 10 beklenti + 4 istisna (kapi FAIL) satiri', (R['hepsi_gecti'], len(R['istisna_kapi_fail']), len(R['istisna_satirlari'])),
             (True, 4, 4))
    finally:
        shutil.rmtree(t)

    hata = [v['vaka'] for v in V if not v['tuttu']]
    print('TOPLAMA78 MANTIK', 'PASS' if not hata else 'FAIL', '| vaka', len(V), '| tutmayan', hata)
    return 0 if not hata else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:                                                          # noqa: BLE001
        import traceback
        traceback.print_exc()
        sys.exit(2)
