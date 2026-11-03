#!/usr/bin/env python3
"""Sosyal donem olcumu (Serdar 3 Kas "uygun"; Metricool karar verisi). SALT OKUMA: yalniz GET; Metricool'a yazma yok.
Kullanim: donem_olcum.py TOKEN.json CIKTI_DIR --bas 2026-10-12 --son 2026-11-02 [--hafta-bas 2026-10-06]
Uclar ve metrik tanimlari olcum.py'den (HESAP, GON; 19-20 Eki olculen subject/scope varyantlari):
1) Hesap gunluk: GET /v2/analytics/timelines (hafta-bas .. son, Europe/Istanbul gunleri).
2) Gonderi: GET /v2/analytics/{posts|reels}/{ag} (hafta-bas .. son); degerler okuma anindaki kumulatif degerler.
3) Takvim: GET /v2/scheduler/posts (hafta-bas -> 31 Oca 2027, 3 gunluk parcalar); provider status sayimi
   (donemde yayinlanan = status PUBLISHED, bekleyen = PENDING ve yayin > okuma ani).
Cikti: OZET.csv (platform satiri), HAFTALIK.csv, <AG>_GUNLUK.csv, <AG>_GONDERI.csv, BEKLEYEN.csv, TAKVIM_DURUM.csv,
TANIMLAR.txt, LOG.txt, HAM/*.json. Metricool bir degeri vermiyorsa "veri yok"; tahmin yok."""
import argparse
import csv
import importlib.util
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KOK = os.path.dirname(os.path.abspath(__file__))
sp = importlib.util.spec_from_file_location('olcum', os.path.join(KOK, 'olcum.py'))
O = importlib.util.module_from_spec(sp); sp.loader.exec_module(O)

TZ, IST = O.TZ, O.IST
YOK = 'veri yok'
SON_TAKVIM = datetime(2027, 1, 31)
# platform basina: gosterim (hesap timeline sutunu), takipci sutunu, dis tiklama sutunlari, gonderi gosterim alani,
# gonderi etkilesim alanlari (toplanir)
PROFIL = {
    'pinterest': dict(gosterim='gosterim', takipci='takipci', dis=['dis_tiklama'], g_gos=['gosterim'],
                      g_etk=['kaydetme', 'pin_tiklama', 'dis_tiklama']),
    'instagram': dict(gosterim='goruntulenme', takipci='takipci', dis=['web_tiklama', 'profil_link_tiklama'],
                      g_gos=['goruntulenme'], g_etk=['begeni', 'yorum', 'kaydetme', 'paylasim']),
    'facebook': dict(gosterim='sayfa_medya_izlenme', takipci='takipci', dis=['web_tiklama', 'cta_tiklama'],
                     g_gos=['gosterim', 'izlenme'], g_etk=['tepki', 'yorum', 'paylasim']),
    'threads': dict(gosterim='goruntulenme', takipci='takipci', dis=[], g_gos=['goruntulenme'],
                    g_etk=['begeni', 'yanit', 'yeniden_paylasim', 'alinti']),
    'tiktok': dict(gosterim='video_goruntulenme', takipci='takipci', dis=[], g_gos=['izlenme'],
                   g_etk=['begeni', 'yorum', 'paylasim']),
    'youtube': dict(gosterim='izlenme', takipci='abone', dis=[], g_gos=['izlenme'], g_etk=['begeni', 'yorum', 'paylasim']),
}
LOG, TANIM = [], []


def log(s):
    print(s, flush=True); LOG.append(s)


def num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def yuvarla(v):
    return YOK if v is None else (int(v) if float(v).is_integer() else round(float(v), 2))


def son_deger(s, y):
    ds = [d for d in s if d <= y]
    return s[max(ds)] if ds else None


def gunler(a, b):
    return [a + timedelta(days=i) for i in range((b - a).days + 1)]


def hesap(mc, out, ag, g):
    """{sutun: ({gun: deger}, tur, metric, varyant)}"""
    S = {}
    for sut, m, varyant, tur in O.HESAP[ag]:
        sec = None
        for v in varyant:
            p = dict(network=ag, metric=m, **{'from': f'{g[0]}T00:00:00', 'to': f'{g[-1]}T23:59:59', 'timezone': TZ}, **v)
            vad = '_'.join(f'{k}-{x}' for k, x in v.items()) or 'yok'
            s = O.seri(O.get(mc, out, f'{ag}_timeline_{m}_{vad}', O.TL, p))
            if s:
                sec = (s, vad); break
        S[sut] = (sec[0] if sec else {}, tur, m, sec[1] if sec else 'ERISILEMEDI')
        TANIM.append(f'  [{ag}] {sut:22s} {O.TL} metric={m} varyant={S[sut][3]} [{tur}] {len(S[sut][0])} gun')
    return S


def gonderiler(mc, out, ag, a, b, okuma):
    satir = []
    for uc, tur_, alanlar in O.GON.get(ag, []):
        j = O.get(mc, out, f'{ag}_{uc.strip("/").replace("/", "_")}', uc,
                  {'from': f'{a}T00:00:00', 'to': f'{b}T23:59:59', 'timezone': TZ})
        ls = O.liste(j)
        if ls is None:
            log(f'  {uc}: ERISILEMEDI ({str(j.get("_hata"))[:150] if isinstance(j, dict) else "liste degil"})')
            TANIM.append(f'  [{ag}] {uc}: ERISILEMEDI'); continue
        n0 = len(satir)
        for x in ls:
            if not isinstance(x, dict):
                continue
            u, i, zh = O.zaman(x)
            if u is None or not (a <= i.date() <= b):
                continue
            r = {'tur': tur_, 'yayin_istanbul': f'{i:%Y-%m-%d %H:%M}', 'gun': i.date(), 'yas_saat': round((okuma - u).total_seconds() / 3600, 1),
                 'uc': uc}
            for k, ad_ in alanlar.items():
                an, v = O.alan(x, ad_)
                r[k] = (str(v)[:80] if k in ('baslik', 'link', 'kimlik') else num(O.sayi(v))) if an else None
            satir.append(r)
        log(f'  {uc}: yanit {len(ls)} kayit, {a}..{b} icinde {len(satir) - n0}')
        TANIM.append(f'  [{ag}] {uc} ({tur_}): yanit {len(ls)}, donemde {len(satir) - n0}')
    return satir


def takvim(mc, out, bas, okuma_ist):
    ps, t, hata = {}, datetime.combine(bas, datetime.min.time()), 0
    while t < SON_TAKVIM:
        e = min(t + timedelta(days=3), SON_TAKVIM)
        try:
            ls = O.mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': f'{t:%Y-%m-%dT%H:%M:%S}', 'end': f'{e:%Y-%m-%dT%H:%M:%S}',
                                                                    'timezone': TZ}))
        except SystemExit as x:
            log(f'  scheduler {t:%Y-%m-%d}: HATA {str(x)[:200]}'); ls = None; hata += 1
        ls = ls if isinstance(ls, list) else []
        if len(ls) >= 100:
            log(f'  scheduler {t:%Y-%m-%d}: {len(ls)} kayit UYARI: 100 ve ustu, yanit kesilmis olabilir')
        for p in ls:
            ps[str(p.get('id'))] = p
        t = e
    O.ham(out, 'scheduler_posts', list(ps.values()))
    sat = []
    for p in ps.values():
        pd = p.get('publicationDate') or {}
        try:
            z = datetime.fromisoformat(str(pd.get('dateTime'))[:19]).replace(tzinfo=ZoneInfo(pd.get('timezone') or TZ)).astimezone(IST)
        except ValueError:
            continue
        for pr in p.get('providers') or []:
            sat.append((z, (pr.get('network') or '').lower(), pr.get('status') or ''))
    log(f'  scheduler: {len(ps)} benzersiz gonderi, {len(sat)} (gonderi, ag) satiri, hata parca {hata}')
    return sat, hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('token'); ap.add_argument('cikti')
    ap.add_argument('--bas', required=True); ap.add_argument('--son', required=True)
    ap.add_argument('--hafta-bas', default='', help='haftalik egilimin ilk gunu (bos: son - 27 gun; 4 tam hafta)')
    a = ap.parse_args()
    out = a.cikti; os.makedirs(out, exist_ok=True)
    mc = O.mpb.MC(json.load(open(a.token)))
    B, S_ = date.fromisoformat(a.bas), date.fromisoformat(a.son)
    HB = date.fromisoformat(a.hafta_bas) if a.hafta_bas else S_ - timedelta(days=27)
    HAFTA = [(HB + timedelta(days=7 * k), HB + timedelta(days=7 * k + 6)) for k in range(4)]
    ilk = min(B, HB)
    g = gunler(ilk, S_)
    okuma = datetime.now(timezone.utc)
    okuma_ist = okuma.astimezone(IST)
    log(f'OKUMA {okuma:%Y-%m-%dT%H:%M:%SZ} UTC ({okuma_ist:%Y-%m-%d %H:%M} Istanbul); blogId {mc.b}')
    log(f'DONEM {B}..{S_} ({(S_ - B).days + 1} gun); HAFTALAR ' + ', '.join(f'H{k + 1} {x}..{y}' for k, (x, y) in enumerate(HAFTA)))
    TANIM.extend([f'DONEM OLCUMU (scripts/sosyal/analiz/donem_olcum.py; yalniz GET). Donem {B}..{S_}, Europe/Istanbul gunleri.',
                  f'Okuma {okuma:%Y-%m-%dT%H:%M:%SZ} UTC. Haftalar: ' + ', '.join(f'H{k + 1} {x}..{y}' for k, (x, y) in enumerate(HAFTA)),
                  'Hesap metrikleri gunluk degerlerin toplami; takipci = ilk/son gunun degeri (birikimli seviye).',
                  'Gonderi metrikleri okuma anindaki KUMULATIF degerler; yeni gonderiler daha az birikmistir (yas_saat).',
                  'Etkilesim (gonderi alanlari toplami): ' + '; '.join(f'{k}=' + '+'.join(v['g_etk']) for k, v in PROFIL.items()),
                  'Gosterim (hesap timeline): ' + '; '.join(f'{k}={v["gosterim"]}' for k, v in PROFIL.items()),
                  '"veri yok": Metricool vermedi (HTTP hata, bos yanit ya da alan yok). Tahmin yok.', ''])
    log('--- TAKVIM (/v2/scheduler/posts)')
    tsat, thata = takvim(mc, out, ilk, okuma_ist)
    with open(os.path.join(out, 'TAKVIM_DURUM.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['ag', 'status', 'donemde_yayin_tarihli', 'okumadan_sonra', 'tum'])
        c = Counter((ag, st) for _, ag, st in tsat)
        for (ag, st), n in sorted(c.items()):
            w.writerow([ag, st, sum(1 for z, x, s in tsat if x == ag and s == st and B <= z.date() <= S_),
                        sum(1 for z, x, s in tsat if x == ag and s == st and z > okuma_ist), n])
    bek = sorted((z, ag) for z, ag, st in tsat if st == 'PENDING' and z > okuma_ist)
    with open(os.path.join(out, 'BEKLEYEN.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(['yayin_istanbul', 'ag'])
        for z, ag in bek:
            w.writerow([f'{z:%Y-%m-%d %H:%M}', ag])

    ozet, haft = [], []
    for ag in PROFIL:
        log(f'--- {ag.upper()}')
        P = PROFIL[ag]
        S = hesap(mc, out, ag, g)
        gs = gonderiler(mc, out, ag, ilk, S_, okuma)
        with open(os.path.join(out, f'{ag.upper()}_GUNLUK.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(['tarih_istanbul'] + list(S))
            for d in g:
                w.writerow([str(d)] + [yuvarla(S[c][0].get(d)) if d in S[c][0] else YOK for c in S])
        kol = sorted({k for r in gs for k in r} - {'gun'})
        with open(os.path.join(out, f'{ag.upper()}_GONDERI.csv'), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n'); w.writerow(kol)
            for r in sorted(gs, key=lambda r: r['yayin_istanbul']):
                w.writerow([YOK if r.get(k) is None else r.get(k) for k in kol])

        def top(sut, a_, b_):
            s = S.get(sut, ({},))[0]
            v = [s[d] for d in gunler(a_, b_) if d in s]
            return (sum(v) if v else None), len(v)

        def seviye(sut, ilk_mi):
            s = S.get(sut, ({},))[0]
            ds = sorted(x for x in s if B <= x <= S_)
            return (s[ds[0] if ilk_mi else ds[-1]], str(ds[0] if ilk_mi else ds[-1])) if ds else (None, '')

        GD = [r for r in gs if B <= r['gun'] <= S_]

        def gtop(alanlar, R):
            v = [r[k] for r in R for k in alanlar if r.get(k) is not None]
            return sum(v) if v else None
        gos, gos_n = top(P['gosterim'], B, S_)
        tb, tbg = seviye(P['takipci'], True)
        ts, tsg = seviye(P['takipci'], False)
        dis = {d: top(d, B, S_)[0] for d in P['dis']}
        g_gos = gtop(P['g_gos'][:1], GD)
        g_etk = gtop(P['g_etk'], GD)
        n = len(GD)
        bk = [z for z, x in bek if x == ag]
        yay = sum(1 for z, x, s in tsat if x == ag and s == 'PUBLISHED' and B <= z.date() <= S_)
        satir = dict(platform=ag, gonderi_analitik=n, gonderi_takvim_published=yay,
                     gosterim_hesap=yuvarla(gos), gosterim_metrik=S[P['gosterim']][2],
                     gosterim_gun=gos_n, gonderi_gosterim_toplam=yuvarla(g_gos), gonderi_gosterim_alan=P['g_gos'][0],
                     etkilesim_toplam=yuvarla(g_etk), etkilesim_tanim='+'.join(P['g_etk']),
                     takipci_bas=yuvarla(tb), takipci_bas_gun=tbg, takipci_son=yuvarla(ts), takipci_son_gun=tsg,
                     dis_tiklama=('; '.join(f'{d}={yuvarla(v)}' for d, v in dis.items()) if dis else YOK + ' (Metricool metrigi yok)'),
                     gonderi_basi_gosterim=yuvarla(g_gos / n) if n and g_gos is not None else YOK,
                     gonderi_basi_etkilesim=yuvarla(g_etk / n) if n and g_etk is not None else YOK,
                     bekleyen=len(bk), bekleyen_son=f'{bk[-1]:%Y-%m-%d %H:%M}' if bk else '',
                     kaynak='/v2/analytics/timelines; /v2/analytics/posts|reels/' + ag + '; /v2/scheduler/posts')
        ozet.append(satir)
        for k, (x, y) in enumerate(HAFTA):
            R = [r for r in gs if x <= r['gun'] <= y]
            hg, hn = top(P['gosterim'], x, y)
            haft.append(dict(platform=ag, hafta=f'H{k + 1}', bas=str(x), son=str(y), gonderi=len(R), gosterim_hesap=yuvarla(hg),
                             gosterim_gun=hn, gonderi_gosterim=yuvarla(gtop(P['g_gos'][:1], R)), etkilesim=yuvarla(gtop(P['g_etk'], R)),
                             takipci_son=yuvarla(son_deger(S[P['takipci']][0], y))))
        log(f'  OZET {json.dumps(satir, ensure_ascii=False, default=str)}')
    for ad, R in (('OZET.csv', ozet), ('HAFTALIK.csv', haft)):
        with open(os.path.join(out, ad), 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(R[0]), lineterminator='\n'); w.writeheader(); w.writerows(R)
    log(f'BEKLEYEN (yayin > okuma, PENDING): {len(bek)}; ' + str(dict(Counter(x for _, x in bek))))
    open(os.path.join(out, 'LOG.txt'), 'w').write('\n'.join(LOG) + '\n')
    open(os.path.join(out, 'TANIMLAR.txt'), 'w').write('\n'.join(TANIM) + '\n')
    return 1 if thata else 0


if __name__ == '__main__':
    raise SystemExit(main())
