#!/usr/bin/env python3
"""Ornament siparis hatti TEST degerlendirmesi (plan 2.6; yalniz sahte girdiler, docs/ornament/siparis_test/Txx.json; kisi verisi yok).
- Beklenen durum (fixture _test.beklenen) ile gelen durum (ornament_siparis cikis kodu). OLCUM: COKUS disinda her sonuc kabul, sonuc rapora.
- Regresyon (_test.regresyon): uretilen 5 stil, onayli toplama dosyalariyla uretim kontrol toleransinda mi (<= 1 seviye, <= 10 piksel; Serdar 6 Kas 3a).
  Onayli dosyanin sha256'si dal SHA256SUMS ile ayni olmali (yanlis dosya kiyaslanmasin).
- Esitlik (_test.esit = Tnn): secilen stil baski dosyasinin piksel sha'si diger testinkiyle ayni (ornek: kucuk harf giris = T01).
Kullanim: siparis_test_ozet.py --sonuc SONUC.tsv --fixture DIR --onayli DIR --sums SHA256SUMS.txt --json CIKTI.json
  SONUC.tsv satiri: kod<TAB>cikis<TAB>cikti_dir<TAB>is_dir. Cikis 0 = tum beklentiler tuttu, 1 = en az bir tutmayan."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

DURUM = {0: 'PASS', 3: 'DUR_GIRDI', 4: 'DUR_SERDAR', 6: 'MOTOR_KAPI_FAIL', 2: 'COKUS'}
STIL = ('RUBY', 'SAPPHIRE', 'EMERALD', 'SADE_ALTIN', 'FILDISI')
TOL_SEVIYE, TOL_PIKSEL = 1, 10                                                # ornek78.py:30 kontrol cifti toleransi ile ayni (Serdar 6 Kas "3a")


def piksel(yol):
    import numpy as np
    from PIL import Image
    im = Image.open(yol)
    a = np.asarray(im)
    return im.mode, a, hashlib.sha256(im.mode.encode() + np.ascontiguousarray(a).tobytes()).hexdigest()


def regresyon(is_dir, cift, onayli, sums):
    import numpy as np
    r, ok = {}, True
    for s in STIL:
        f = f'{cift}_{s}_954.png'
        u, o = Path(is_dir) / 'png' / f, Path(onayli) / f
        if not u.exists() or not o.exists():
            r[s] = dict(var=False); ok = False; continue
        o_sha = hashlib.sha256(o.read_bytes()).hexdigest()
        mu, au, pu = piksel(u); mo, ao, po = piksel(o)
        ayni_boy = au.shape == ao.shape and mu == mo
        fark = int(np.abs(au.astype(int) - ao.astype(int)).max()) if ayni_boy else None
        n = int((au != ao).reshape(au.shape[0], au.shape[1], -1).any(-1).sum()) if ayni_boy else None
        e = bool(ayni_boy and fark <= TOL_SEVIYE and n <= TOL_PIKSEL and sums.get(f) == o_sha)   # Serdar 6 Kas "3a": uretim kontrol toleransi (ornek78.py TOL)
        r[s] = dict(piksel_esit=pu == po, en_buyuk_fark=fark, farkli_piksel=n, onayli_sha_sums_ile_ayni=sums.get(f) == o_sha, gecti=e)
        ok &= e
    return ok, r


def main():
    ap = argparse.ArgumentParser()
    for k in ('sonuc', 'fixture', 'onayli', 'sums', 'json'):
        ap.add_argument('--' + k, required=True)
    a = ap.parse_args()
    sums = {l.split()[1]: l.split()[0] for l in Path(a.sums).read_text().splitlines() if l.strip()}
    satir = [l.split('\t') for l in Path(a.sonuc).read_text().splitlines() if l.strip()]
    T, tutmayan = {}, []
    for kod, cikis, cdir, idir in satir:
        fx = json.loads((Path(a.fixture) / f'{kod}.json').read_text(encoding='utf-8'))
        t = fx['_test']; gelen = DURUM.get(int(cikis), f'BILINMEYEN_{cikis}')
        bek = t['beklenen']
        ok = (gelen != 'COKUS') if bek == 'OLCUM' else (gelen == bek)
        rap = Path(cdir) / 'RAPOR.json'
        R = json.loads(rap.read_text()) if rap.exists() else {}
        d = dict(beklenen=bek, gelen=gelen, tuttu=ok, neden=R.get('neden'), sert_fail=R.get('sert_fail'),
                 baski_piksel_sha=(R.get('cikti') or {}).get('baski_piksel_sha'), sure_sn=(R.get('ornek78') or {}).get('sure_sn'),
                 murekkep_r=(R.get('yeni_duzen_olcum') or {}).get('siparis_murekkep_r'),
                 bosluk=dict(tarih_isim=(R.get('yeni_duzen_olcum') or {}).get('bosluk_tarih_isim'),
                             isim_kucuk=(R.get('yeni_duzen_olcum') or {}).get('bosluk_isim_kucuk')),
                 not_=t.get('not_'))
        if t.get('raqm_ters'):                                               # bilinen FAIL testi: COKUS nedeni raqm olmali (baska cokus yanlis PASS vermesin; inceleme 6 Kas)
            lg = Path(cdir) / 'IS' / 'log_ornek78.txt'
            d['raqm_nedeni'] = lg.exists() and 'raqm durumu beklenen degil' in lg.read_text(errors='replace')
            ok = ok and d['raqm_nedeni']
        if t.get('regresyon') and gelen == 'PASS':
            rok, rr = regresyon(idir, fx['cift'], a.onayli, sums)
            d['regresyon'] = rr; d['regresyon_gecti'] = rok; ok = ok and rok
        elif t.get('regresyon'):
            d['regresyon_gecti'] = False; ok = False
        d['tuttu'] = ok
        T[kod] = d
    for kod, d in T.items():                                                  # esitlik testleri (T15 = T01)
        fx = json.loads((Path(a.fixture) / f'{kod}.json').read_text(encoding='utf-8'))
        e = fx['_test'].get('esit')
        if e:
            esit = bool(d['baski_piksel_sha']) and d['baski_piksel_sha'] == (T.get(e) or {}).get('baski_piksel_sha')
            d['esit_' + e] = esit; d['tuttu'] = d['tuttu'] and esit
    for kod, d in T.items():
        if not d['tuttu']:
            tutmayan.append(kod)
        print('TEST', kod, '| beklenen', d['beklenen'], '| gelen', d['gelen'], '| tuttu', d['tuttu'], '|', d.get('neden') or '', ('| raqm_nedeni ' + str(d['raqm_nedeni'])) if 'raqm_nedeni' in d else '', flush=True)
    sonuc = dict(test=T, tutmayan=tutmayan, toplam=len(T), not_='sahte girdiler; kisi verisi yok (ANA_2 7.3)')
    Path(a.json).write_text(json.dumps(sonuc, indent=1, ensure_ascii=False, default=str))
    print('TEST OZET', len(T), 'vaka, tutmayan', tutmayan, flush=True)
    return 1 if tutmayan or not T else 0


if __name__ == '__main__':
    sys.exit(main())
