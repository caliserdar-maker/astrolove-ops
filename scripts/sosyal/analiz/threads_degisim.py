#!/usr/bin/env python3
"""Threads kapak degisimi ENVANTER + ESLEME (20 Eki 2026). SALT OKUMA: Metricool'a ve Threads'e YAZMA YOK, yalniz GET.
1) /v2/scheduler/posts (bugun -> UFUK, 5 gunluk pencereler): providers[network=threads] PENDING ve yayini simdiden sonra
   olan gonderiler: id, uuid, tarih, tur (medya sayisi / threadsData.type), metin basi, link, medya URL'leri.
2) Aile: medya yolu instagram/v6/<CIFT>/ = IG_V6 poster karuseli (slayt 3-4 poster); metinde mug/cup -> kupa;
   anniversary/our year -> yildonumu; yoksa bilinmiyor. Cift: metindeki "A & B" ve medya klasoru (ikisi karsilastirilir).
   Poster ilan kimligi data/pod/pod78_ids.csv.
3) Eski / yeni gorunum OLCUMU: her slayt (4:5 orta kirpim, gri 64x80) ile ayni ciftin
   eski Etsy ilk gorseli (KAPAK_P2_78/YEDEK/<ilan>_*.jpg) ve yeni kapak (KAPAK_A oncelikli, yoksa KAPAK/) ortalama mutlak
   gri farki. ESIK 12: bir slayt yeni kapaga <= ESIK -> "degismemeli"; eski kapaga <= ESIK -> "degismeli";
   hicbiri -> "belirsiz" (karusel ilan ilk gorselini kullanmiyor; kararin kapsami Serdar'da).
4) Yeni medya adayi: poster KAPAK_P2_78 BASLIK_A/KAPAK_A/<ilan>_<CIFT>.jpg, yoksa KAPAK/; kupa KUPA_KAPAK_78/KAPAK/*<CIFT>*;
   yildonumu KAPAK_Y1_78/KAPAK/*<CIFT>*; video: aday yok.
Cikti: ESLEME.csv, OZET.txt, KONTAK_*.jpg (slaytlar | eski | yeni), HAM_scheduler_*.json.
Kullanim: threads_degisim.py TOKEN.json CIKTI IS --p2-ls LS.json --p2-dir DIR --kupa-ls LS.json --y1-ls LS.json --pod78 CSV"""
import argparse
import csv
import importlib.util
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yukle(ad, dosya):
    sp = importlib.util.spec_from_file_location(ad, os.path.join(KOK, dosya))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


mpb = yukle('mpb', 'metricool_pin_baslik.py')
sko = yukle('sko', 'sosyal_kapak_oku.py')      # indir, gorsel_mi, kisa (degistirilmez)

TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
UFUK = datetime(2027, 2, 1)
ESIK = 12        # ortalama mutlak gri fark
NCC_ESIK = 0.90  # yapisal benzerlik; koyu lacivert slaytin koyu kapaga dusuk fark vermesini ayirir
BURC = ('ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN',
        'AQUARIUS', 'PISCES')


def liste(j):
    v = mpb.veri(j) if j is not None else None
    if isinstance(v, dict):
        v = next((x for x in v.values() if isinstance(x, list)), [])
    return v or []


def th(p):
    return next((x for x in p.get('providers') or [] if (x.get('network') or '').lower() == 'threads'), None)


def metin_cift(t):
    b = '|'.join(BURC)
    m = re.search(r'\b(' + b + r')\s*(?:&|and)\s*(' + b + r')\b', (t or '').upper())
    return '_'.join(sorted((m.group(1), m.group(2)))) if m else ''


def yol_cift(u):
    m = re.search(r'/([A-Z]+_[A-Z]+)/[^/]+$', sko.kisa(u))
    return m.group(1) if m and all(x in BURC for x in m.group(1).split('_')) else ''


def aile_bul(t, medya):
    tl = (t or '').lower()
    if re.search(r'\bmugs?\b|\bcups?\b', tl):
        return 'kupa', 'metinde mug/cup'
    if re.search(r'anniversary|our year', tl):
        return 'yildonumu', 'metinde anniversary/our year'
    if medya and all('/instagram/v6/' in m for m in medya):
        return 'poster', 'medya instagram/v6 (IG_V6 poster karuseli)'
    return 'bilinmiyor', 'metin/medya kuralina uymadi'


def oz(yol, oran=4 / 5, w=64):
    im = Image.open(yol).convert('L')
    W, H = im.size
    if W / H > oran:
        bw = int(H * oran); im = im.crop(((W - bw) // 2, 0, (W + bw) // 2, H))
    else:
        bh = int(W / oran); im = im.crop((0, (H - bh) // 2, W, (H + bh) // 2))
    return np.asarray(im.resize((w, int(round(w / oran)))), np.float32)


def fark(a, b):
    """(ortalama mutlak fark, NCC)"""
    x, y = a - a.mean(), b - b.mean()
    n = float(np.sqrt((x * x).sum() * (y * y).sum()))
    return round(float(np.abs(a - b).mean()), 1), round(float((x * y).sum() / n) if n else 0.0, 3)


def ayni(f):
    return f[0] <= ESIK and f[1] >= NCC_ESIK


def yazf(fs):
    return ' / '.join(f'{d}~{c}' for d, c in fs) or '-'


def ls(yol):
    return json.load(open(yol)) if yol and os.path.exists(yol) else []


def yaz(out, ad, baslik, satirlar):
    with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(baslik); w.writerows(satirlar)
    print(f'CSV {ad}: {len(satirlar)} satir', flush=True)


def kontak(out, satirlar, sayfa=15, h=150):
    """Satir: 4 slayt | eski kapak | yeni kapak (h px yukseklik), soldaki etiket tarih + cift + karar."""
    for s in range(0, len(satirlar), sayfa):
        par = satirlar[s:s + sayfa]
        tuval = Image.new('RGB', (260 + 6 * (int(h * 4 / 5) + 8), len(par) * (h + 8) + 8), 'white')
        d = ImageDraw.Draw(tuval)
        for i, (etiket, yollar) in enumerate(par):
            y = 8 + i * (h + 8)
            d.text((6, y + 4), etiket, fill='black')
            for k, yl in enumerate(yollar):
                x = 260 + k * (int(h * 4 / 5) + 8)
                if yl and os.path.exists(yl):
                    try:
                        im = Image.open(yl).convert('RGB'); im.thumbnail((int(h * 4 / 5) if k < 4 else h * 2, h))
                        tuval.paste(im, (x, y))
                    except Exception:
                        d.text((x, y + 4), 'okunamadi', fill='red')
                else:
                    d.text((x, y + 4), '-', fill='gray')
        ad = f'KONTAK_{s // sayfa + 1}.jpg'
        tuval.save(os.path.join(out, ad), quality=85)
        print(f'KONTAK {ad}: {len(par)} satir (sutunlar: slayt1-4 | eski Etsy ilk gorsel | yeni kapak)', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti'); ap.add_argument('isd')
    for k in ('p2-ls', 'p2-dir', 'kupa-ls', 'y1-ls', 'pod78'):
        ap.add_argument('--' + k, default='')
    a = ap.parse_args()
    out, isd = a.cikti, a.isd
    os.makedirs(out, exist_ok=True); os.makedirs(isd, exist_ok=True)
    mc = mpb.MC(json.load(open(a.token)))
    simdi = datetime.now(IST)
    o = [f'Okuma: {simdi:%Y-%m-%d %H:%M} (Europe/Istanbul), blogId {mc.b}, ufuk {UFUK:%Y-%m-%d}, uc GET /v2/scheduler/posts']

    # --- aday dosyalar
    ilan = {r['cift'].strip().upper(): r['listing_id'].strip() for r in csv.DictReader(open(a.pod78, encoding='utf-8-sig'))}
    p2 = ls(a.p2_ls)
    kap_a, kap, eski = {}, {}, {}
    for f in p2:
        yp, ad = f.get('Path', ''), f.get('Name', '')
        m = re.fullmatch(r'(\d+)_([A-Z]+_[A-Z]+)\.jpg', ad)
        if m and yp.startswith('BASLIK_A/KAPAK_A/'):
            kap_a[m.group(2)] = yp
        elif m and yp.startswith('KAPAK/'):
            kap[m.group(2)] = yp
        m = re.fullmatch(r'(\d+)_(\d+)\.jpe?g', ad)
        if m and yp.startswith('YEDEK/'):
            eski.setdefault(m.group(1), []).append(yp)
    kupa = {f['Name']: f.get('Path', f['Name']) for f in ls(a.kupa_ls) if re.search(r'\.(jpe?g|png)$', f['Name'], re.I)}
    y1 = {f['Name']: f.get('Path', f['Name']) for f in ls(a.y1_ls) if re.search(r'\.(jpe?g|png)$', f['Name'], re.I)}
    o.append(f'Aday dosyalar: poster KAPAK_A {len(kap_a)}, KAPAK {len(kap)}, eski Etsy ilk gorsel (YEDEK) ilan {len(eski)} '
             f'(coklu {sum(1 for v in eski.values() if len(v) > 1)}); kupa KAPAK {len(kupa)}; yildonumu KAPAK {len(y1)}; '
             f'pod78 ilan {len(ilan)}')
    print(o[-1], flush=True)

    # --- zamanlayici
    ps, t = {}, datetime(simdi.year, simdi.month, simdi.day)
    while t < UFUK:
        e = min(t + timedelta(days=5), UFUK)
        try:
            j = mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ})
        except SystemExit as ex:
            j = {'_hata': str(ex)[:300]}; print(f'SCHEDULER {t:%Y-%m-%d}: HATA {str(ex)[:150]}', flush=True)
        json.dump(j, open(os.path.join(out, f'HAM_scheduler_{t:%Y%m%d}.json'), 'w'), ensure_ascii=False, indent=1, default=str)
        for p in liste(j):
            if th(p):
                ps[str(p.get('uuid') or p.get('id'))] = p
        t = e
    durum, gelecek = Counter(), []
    for p in ps.values():
        pd = p.get('publicationDate') or {}
        try:
            z = datetime.fromisoformat(pd.get('dateTime') or '').replace(tzinfo=ZoneInfo(pd.get('timezone') or TZ)).astimezone(IST)
        except (ValueError, KeyError):
            continue
        if z <= simdi:
            continue
        st = th(p).get('status') or ''
        durum[st] += 1
        if st == 'PENDING':
            gelecek.append((z, p))
    gelecek.sort(key=lambda x: x[0])
    o.append(f'Gelecek Threads gonderileri durum: {dict(durum)}; bekleyen (PENDING) {len(gelecek)}; '
             f'ilk {gelecek[0][0]:%Y-%m-%d %H:%M} son {gelecek[-1][0]:%Y-%m-%d %H:%M}' if gelecek else 'Bekleyen Threads gonderisi yok')
    print(o[-1], flush=True)
    if gelecek:
        p0 = gelecek[0][1]
        o.append(f'Ornek alanlar: {sorted(p0)}; provider {sorted(th(p0))}; threadsData {p0.get("threadsData")}; '
                 f'ag sayisi/gonderi {dict(Counter(len(p.get("providers") or []) for _, p in gelecek))}')

    # --- esleme + olcum
    sat, kon, boy = [], [], Counter()
    for n, (z, p) in enumerate(gelecek, 1):
        md = [m.get('url') if isinstance(m, dict) else m for m in p.get('media') or []]
        md = [m for m in md if m]
        txt = p.get('text') or ''
        af, af_neden = aile_bul(txt, md)
        mc_, yc = metin_cift(txt), (yol_cift(md[0]) if md else '')
        cift = mc_ or yc
        notlar = [] if not (mc_ and yc and mc_ != yc) else [f'metin cifti {mc_} != medya klasoru {yc}']
        il = ilan.get(cift, '') if af == 'poster' else ''
        # aday
        aday, aday_kaynak = '', ''
        if af == 'poster':
            if cift in kap_a:
                aday, aday_kaynak = kap_a[cift], 'KAPAK_P2_78/BASLIK_A/KAPAK_A'
            elif cift in kap:
                aday, aday_kaynak = kap[cift], 'KAPAK_P2_78/KAPAK'
            if aday and il and not os.path.basename(aday).startswith(il + '_'):
                notlar.append(f'aday ilan {os.path.basename(aday).split("_")[0]} != pod78 {il}')
        elif af == 'kupa':
            aday = next((v for k, v in sorted(kupa.items()) if cift and cift in k.upper()), '')
            aday_kaynak = 'KUPA_KAPAK_78/KAPAK' if aday else ''
        elif af == 'yildonumu':
            aday = next((v for k, v in sorted(y1.items()) if cift and cift in k.upper()), '')
            aday_kaynak = 'KAPAK_Y1_78/KAPAK' if aday else ''
        tur = 'video' if any(re.search(r'\.(mp4|mov)$', sko.kisa(m), re.I) for m in md) else \
            ('karusel' if len(md) > 1 else ('tek gorsel' if md else 'metin'))
        # olcum (yalniz poster: eski + yeni referans var)
        f_eski, f_yeni, yollar = [], [], []
        ref_e = os.path.join(a.p2_dir, eski[il][0]) if il in eski and a.p2_dir else ''
        ref_y = os.path.join(a.p2_dir, aday) if aday and af == 'poster' and a.p2_dir else ''
        oe = oz(ref_e) if ref_e and os.path.exists(ref_e) and sko.gorsel_mi(ref_e) else None
        oy = oz(ref_y) if ref_y and os.path.exists(ref_y) and sko.gorsel_mi(ref_y) else None
        if oy is not None:
            boy['yeni kapak ' + 'x'.join(map(str, sko.gorsel_mi(ref_y)))] += 1
        if oe is not None:
            boy['eski ilk gorsel ' + 'x'.join(map(str, sko.gorsel_mi(ref_e)))] += 1
        for k, u in enumerate(md[:4]):
            y = os.path.join(isd, f'{n:03d}_{k + 1}.img')
            kod = sko.indir(u, y) if not os.path.exists(y) else '200|'
            if not kod.startswith('200') or not sko.gorsel_mi(y):
                notlar.append(f'slayt {k + 1} indirilemedi ({kod.split("|")[0]})'); yollar.append(''); continue
            yollar.append(y)
            boy['slayt ' + 'x'.join(map(str, sko.gorsel_mi(y)))] += 1
            s = oz(y)
            if oe is not None:
                f_eski.append(fark(s, oe))
            if oy is not None:
                f_yeni.append(fark(s, oy))
        if tur == 'video':
            karar, neden = 'belirsiz', 'video: yeni acilis henuz yok'
        elif any(ayni(f) for f in f_yeni):
            i = next(i for i, f in enumerate(f_yeni) if ayni(f))
            karar, neden = 'degismemeli', f'slayt {i + 1} yeni kapakla ayni (fark {f_yeni[i][0]}, NCC {f_yeni[i][1]})'
        elif any(ayni(f) for f in f_eski):
            i = next(i for i, f in enumerate(f_eski) if ayni(f))
            karar, neden = 'degismeli', f'slayt {i + 1} eski Etsy ilk gorseliyle ayni (fark {f_eski[i][0]}, NCC {f_eski[i][1]})'
        elif af == 'poster' and f_eski and f_yeni:
            karar, neden = 'belirsiz', (f'hicbir slayt eski ilk gorsel (en yakin fark {min(f[0] for f in f_eski)}, en yuksek NCC '
                                        f'{max(f[1] for f in f_eski)}) ya da yeni kapakla (fark {min(f[0] for f in f_yeni)}, NCC '
                                        f'{max(f[1] for f in f_yeni)}) ayni degil; karusel ilan ilk gorselini kullanmiyor')
        else:
            karar, neden = 'belirsiz', 'olcum referansi yok (' + ', '.join(x for x, v in (('eski', oe), ('yeni', oy)) if v is None) + ')'
        pr = th(p)
        sat.append([p.get('id'), p.get('uuid', ''), f'{z:%Y-%m-%d %H:%M}', (p.get('publicationDate') or {}).get('timezone', ''),
                    pr.get('status'), tur, len(md), (p.get('threadsData') or {}).get('type', ''), len(p.get('providers') or []),
                    re.sub(r'\s+', ' ', txt)[:90], pr.get('publicUrl') or '', ' | '.join(md), af, af_neden, cift, mc_, yc, il,
                    ' | '.join(eski.get(il, [])), yazf(f_eski), yazf(f_yeni),
                    karar, neden, aday, aday_kaynak, '; '.join(notlar)])
        kon.append((f'{z:%m-%d %H:%M} {cift}\n{af} -> {karar}', yollar + [''] * (4 - len(yollar)) + [ref_e, ref_y]))
        print(f'{n:3d} {z:%Y-%m-%d %H:%M} {cift} {af} {tur} -> {karar} | eski {sat[-1][19]} | yeni {sat[-1][20]} | {aday}', flush=True)
    yaz(out, 'ESLEME.csv', ['gonderi_id', 'uuid', 'tarih', 'tz', 'durum', 'tur', 'medya_sayisi', 'threadsData.type', 'ag_sayisi',
                            'metin_basi', 'link', 'medya_urller', 'aile', 'aile_kaniti', 'cift', 'metin_cifti', 'medya_klasor_cifti',
                            'poster_ilan_id', 'eski_etsy_ilk_gorsel', 'fark~ncc_eski_slayt1-4', 'fark~ncc_yeni_slayt1-4', 'karar',
                            'karar_nedeni', 'yeni_medya_adayi', 'aday_kaynak', 'not'], sat)
    kontak(out, kon)

    # --- ozet
    o.append(f'Aile: {dict(Counter(r[12] for r in sat))}; tur: {dict(Counter(r[5] for r in sat))}; '
             f'medya sayisi: {dict(Counter(r[6] for r in sat))}; medya host: '
             f'{dict(Counter(re.sub(r"^https?://([^/]+)/.*$", r"\1", u) for r in sat for u in r[11].split(" | ") if u))}')
    o.append(f'Karar: {dict(Counter(r[21] for r in sat))}; ayni = fark <= {ESIK} VE NCC >= {NCC_ESIK} '
             f'(gri 64x80, 4:5 orta kirpim)')

    def sl(r, k, i):
        p_ = r[k].split(' / ')
        return tuple(map(float, p_[i].split('~'))) if r[k] != '-' and len(p_) > i else None
    for i in range(4):
        for k, ad in ((19, 'eski ilk gorsel'), (20, 'yeni kapak')):
            v = [x for x in (sl(r, k, i) for r in sat) if x]
            if v:
                d_, c_ = sorted(x[0] for x in v), sorted(x[1] for x in v)
                o.append(f'  slayt {i + 1} ~ {ad}: n {len(v)}; fark min {d_[0]} medyan {d_[len(d_) // 2]} max {d_[-1]}; '
                         f'NCC min {c_[0]} medyan {c_[len(c_) // 2]} max {c_[-1]}')
    o.append(f'Boyut: {dict(boy)}')
    o.append(f'Aday: {dict(Counter(r[24] or "yok" for r in sat))}; ayni cift tekrar: '
             f'{[c for c, k in Counter(r[14] for r in sat).items() if k > 1]}')
    o.append(f'Notlu satir: {sum(1 for r in sat if r[25])}; ' + '; '.join(f'{r[2]} {r[14]}: {r[25]}' for r in sat if r[25])[:1500])
    o += ['UYGULAMA YONTEMI (yalniz ayri onayla; bu kosu yazmadi):',
          '  1) Yeni gorsel herkese acik URL olmali: astrolove-media GitHub Pages (instagram/v6 gibi yeni klasor) ya da Metricool',
          '     S3 yuklemesi; Drive linki kullanilmaz. Yukleme sonrasi URL 200 + image/jpeg prob.',
          '  2) Her degisecek gonderi: GET /v2/scheduler/posts/{id} -> govdenin TAMAMI korunur, yalniz media[] (ve ayni sirada',
          '     mediaAltText[]) degisir -> PUT /v2/scheduler/posts/{id} -> GET ile geri okuma: metin, publicationDate, providers,',
          '     threadsData ayni; media yeni (metricool_pin_baslik.py GET->PUT->GET deseni, IZINLI_FARK disi fark = FAIL).',
          '  3) Yalniz providers[threads].status == PENDING; yayina 60 dk kalan gonderiye dokunulmaz. Gonderide baska ag varsa',
          '     (ag_sayisi > 1) media degisikligi o aglari da etkiler: ayri karar.',
          '  4) Once 1 gonderi (tek), geri okuma PASS ise kalanlar; her PUT sonrasi ESLEME.csv satiri ONCE/SONRA ile yazilir.',
          '  5) Karusel slayt sirasi: hangi slaytin yeni kapakla degisecegi (slayt 3 sahne / slayt 4 yakin plan / 5. slayt eklemek)',
          '     tasarim karari; slayt ve yeni kapak boyutlari yukarida (Boyut satiri).']
    open(os.path.join(out, 'OZET.txt'), 'w').write('\n'.join(o) + '\n')
    print('\n'.join(o), flush=True)


if __name__ == '__main__':
    main()
