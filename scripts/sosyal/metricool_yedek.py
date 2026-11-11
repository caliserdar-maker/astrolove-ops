#!/usr/bin/env python3
"""METRICOOL BEKLEYEN GONDERI YEDEGI (Serdar 11 Kas 2026 "Evet": Starter'a dusmeden once tam yedek). SALT OKUMA, yalniz GET.
Uc nokta: GET /v2/scheduler/posts?start&end&timezone (emsal scripts/sosyal/analiz/pin_takvim_uygula.py pencere(); 5 gunluk
pencereler). AG SUZGECI YOK: tum saglayicilar. Pencere: kosu ani (Europe/Istanbul) -> 2027-04-01T00:00 (2027-03-31 dahil).

Bekleyen = providers[] icinde en az bir saglayicinin durumu YAYINLANMAMIS (PUBLISHED / PUBLISHING disi: PENDING,
AWAITING_CONFIRMATION, ERROR, DRAFT, bos) ya da gonderi draft=true. Ag basina durum sayimi OZET.json'a yazilir (aglar arasi fark
raporda gorunur). Gonderi govdesi API yanitindaki haliyle (alan cikarmadan) YEDEK.json'a girer; iki pencerede gelen ayni gonderi
uuid (yoksa id) ile tekillesir.
Cikti: YEDEK.json (_okuma UTC, _pencere, _adet, gonderiler) ve OZET.json (yalniz sayilar ve zamanlar; metin / medya adresi YOK).
Hata: 401 / 403 -> DUR "API kapali ya da yetki yok"; yanit liste degil -> DUR; diger 4xx (429 dahil) -> DUR; 5xx ve zaman asimi /
baglanti hatasi -> en cok 2 yeniden deneme, sonra DUR. Hata metninde yanit govdesi YAZILMAZ (gonderi icerigi / token sizmasin).
stdout'a yalniz sayilar yazilir.
Kullanim: metricool_yedek.py TOKEN.json OUT   (TOKEN.json: userToken, userId, blogId)
          metricool_yedek.py --sinif YEDEK.json SIR.json...   (Drive oncesi tarama; cikis 0 = temiz ya da yalniz medya imzasi)
Pencere 5 gunde >= 50 satir donerse (sayfalama / kirpilma suphesi) ayni aralik 1 gunluk parcalarla da okunur; 1 gunde de >= 50
ise gun OZET.kirpilma_suphesi_gun'e yazilir (DUR degil)."""
import http.client
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

API = 'https://app.metricool.com/api'
YOL = '/v2/scheduler/posts'
TZ = 'Europe/Istanbul'
IST = timezone(timedelta(hours=3))
SON = datetime(2027, 4, 1)            # 2027-03-31 dahil
GUN = 5
BEKLE = 1.1                           # emsal metricool_pin_baslik.BEKLE
TEKRAR = 2                            # yalniz 5xx ve zaman asimi
KIRPILMA = 50                         # 5 gunluk pencere >= 50 satir: sayfalama / kirpilma suphesi -> 1 gunluk parcalara bol
YAYINLI = {'PUBLISHED', 'PUBLISHING'}
ISTEK = [0]


def ac(req, timeout):                 # testler bunu degistirir
    return urllib.request.urlopen(req, timeout=timeout)


def get(tok, start, end, _son=[0.0]):
    """Tek GET. Yontem sabit GET; govde yok."""
    q = {'start': start, 'end': end, 'timezone': TZ, 'userId': str(tok['userId']), 'blogId': str(tok['blogId'])}
    url = f'{API}{YOL}?{urllib.parse.urlencode(q)}'
    for deneme in range(TEKRAR + 1):
        b = BEKLE - (time.time() - _son[0])
        if b > 0:
            time.sleep(b)
        req = urllib.request.Request(url, method='GET', headers={'X-Mc-Auth': tok['userToken'], 'Accept': 'application/json'})
        ISTEK[0] += 1
        sinif = None
        try:
            with ac(req, 60) as y:
                g = y.read()
            _son[0] = time.time()
        except urllib.error.HTTPError as e:
            _son[0] = time.time()
            if e.code in (401, 403):
                raise SystemExit(f'DUR: HTTP {e.code} (API kapali ya da yetki yok) GET {YOL} {start}')
            if 500 <= e.code < 600:
                sinif = f'HTTP {e.code} (5xx)'
            else:
                raise SystemExit(f'DUR: HTTP {e.code} (beklenmeyen 4xx) GET {YOL} {start}')
        except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError, http.client.HTTPException) as e:
            _son[0] = time.time()
            sinif = f'zaman asimi / baglanti ({type(e).__name__})'
        if sinif is None:
            try:
                j = json.loads(g) if g else None
            except ValueError:
                raise SystemExit(f'DUR: yanit JSON degil GET {YOL} {start}')
            v = j.get('data') if isinstance(j, dict) else j
            if not isinstance(v, list):
                raise SystemExit(f'DUR: yanit liste degil ({type(v).__name__}) GET {YOL} {start}')
            return v
        if deneme < TEKRAR:
            print(f'{sinif}: {10 * (deneme + 1)} sn sonra yeniden ({deneme + 1}/{TEKRAR})', flush=True)
            time.sleep(10 * (deneme + 1))
    raise SystemExit(f'DUR: {sinif}, {TEKRAR} yeniden denemeden sonra GET {YOL} {start}')


def durumlar(p):
    return [((pr.get('network') or '?').lower(), (pr.get('status') or '').upper()) for pr in (p.get('providers') or [])]


def bekleyen(p):
    d = durumlar(p)
    return bool(p.get('draft')) or not d or any(x not in YAYINLI for _, x in d)   # saglayicisiz da bekleyen


def anahtar(p):
    for k in ('uuid', 'id'):
        if p.get(k) not in (None, ''):
            return f'{k}:{p[k]}'
    return 'json:' + json.dumps(p, sort_keys=True, ensure_ascii=False)


def medyali(p):
    return bool(p.get('media')) or bool(p.get('videoThumbnailUrl'))


def calis(tok, out, simdi=None):
    simdi = simdi or datetime.now(IST).replace(tzinfo=None, microsecond=0)
    okuma = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    gon, cakisma, tekrar, ham, t = {}, 0, 0, 0, simdi
    pencereler, dict_disi, pen_ham, supheli = 0, 0, [], []

    def oku(a, b):
        return get(tok, f'{a:%Y-%m-%dT%H:%M:%S}', f'{b:%Y-%m-%dT%H:%M:%S}')
    while t < SON:
        e = min(t + timedelta(days=GUN), SON)
        satirlar = oku(t, e)
        pen_ham.append(len(satirlar))
        if len(satirlar) >= KIRPILMA:          # kirpilma suphesi: ayni pencere 1 gunluk parcalarla yeniden okunur (birlesim)
            g = t
            while g < e:
                h = min(g + timedelta(days=1), e)
                parca = oku(g, h)
                if len(parca) >= KIRPILMA:
                    supheli.append(f'{g:%Y-%m-%d}:{len(parca)}')
                satirlar = satirlar + parca
                g = h
        for p in satirlar:
            ham += 1
            if not isinstance(p, dict):
                dict_disi += 1
                continue
            if not bekleyen(p):
                continue
            k = anahtar(p)
            if k in gon:
                tekrar += 1
                cakisma += gon[k] != p
                continue
            gon[k] = p
        pencereler += 1
        t = e
        print(f'pencere {pencereler} | {t:%Y-%m-%d} | bekleyen {len(gon)} | istek {ISTEK[0]}', flush=True)
    liste = sorted(gon.values(), key=lambda p: ((p.get('publicationDate') or {}).get('dateTime') or ''))
    os.makedirs(out, exist_ok=True)
    pen = {'bas': f'{simdi:%Y-%m-%dT%H:%M:%S}', 'son': f'{SON:%Y-%m-%dT%H:%M:%S}', 'timezone': TZ, 'gun': GUN, 'adet': pencereler}
    with open(os.path.join(out, 'YEDEK.json'), 'w', encoding='utf-8') as f:
        json.dump({'_okuma': okuma, '_pencere': pen, '_adet': len(liste), 'gonderiler': liste}, f, ensure_ascii=False, indent=1)
    ag, durum = Counter(), Counter()
    for p in liste:
        for n, d in durumlar(p):
            durum[f'{n}:{d or "BOS"}'] += 1
            if d not in YAYINLI:
                ag[n] += 1
    zam = [z for z in ((p.get('publicationDate') or {}).get('dateTime') for p in liste) if z]
    oz = {'_okuma': okuma, '_pencere': pen, 'toplam': len(liste), 'ag_bazinda_bekleyen': dict(sorted(ag.items())),
          'ag_durum_sayimi': dict(sorted(durum.items())), 'draft_true': sum(1 for p in liste if p.get('draft')),
          'saglayicisiz': sum(1 for p in liste if not p.get('providers')),
          'en_erken': min(zam) if zam else None, 'en_gec': max(zam) if zam else None,
          'medya_adresi_iceren': sum(1 for p in liste if medyali(p)), 'istek': ISTEK[0], 'ham_satir': ham,
          'tekrar_atlanan': tekrar, 'farkli_icerikli_tekrar': cakisma, 'dict_disi_atlanan': dict_disi,
          'pencere_ham': pen_ham, 'pencere_ham_en_buyuk': max(pen_ham) if pen_ham else 0, 'kirpilma_esigi': KIRPILMA,
          'kirpilma_suphesi_gun': supheli, 'zaman_notu': 'en_erken / en_gec publicationDate.dateTime metni (timezone alani ayri)'}
    with open(os.path.join(out, 'OZET.json'), 'w', encoding='utf-8') as f:
        json.dump(oz, f, ensure_ascii=False, indent=1)
    print(f"OZET | toplam {oz['toplam']} | ag {json.dumps(oz['ag_bazinda_bekleyen'])} | en erken {oz['en_erken']} | en gec "
          f"{oz['en_gec']} | medyali {oz['medya_adresi_iceren']} | istek {oz['istek']}", flush=True)
    print('OZET | durum ' + json.dumps(oz['ag_durum_sayimi']), flush=True)
    print(f"OZET | pencere ham en buyuk {oz['pencere_ham_en_buyuk']} | kirpilma suphesi {len(supheli)} gun | dict disi {dict_disi}", flush=True)
    return oz


def sinif(yol, sir_jsonlar):
    """Drive oncesi tarama siniflamasi (sir_koru.bulgu; sir_koru DEGISMEZ). Imzali satirda imza degeri cikarilip kalan satir
    yeniden taranir. Donus: {sinif: satir}; izinli yalniz 'presigned-url'."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'guvenlik'))
    import sir_koru as SK
    sirlar = set()
    for j in sir_jsonlar:
        sirlar |= SK.sir_json(j)
    if not sirlar:
        raise SystemExit('DUR: sir listesi bos (--sir-json okunamadi)')
    say = Counter()
    for s in open(yol, encoding='utf-8', errors='ignore').read().splitlines():
        b = SK.bulgu(s, sirlar)
        if b == 'presigned-url':
            b = SK.bulgu(re.sub(r'(?i)X-Amz-[A-Za-z-]+=[^&"\s]*', '', s), sirlar) or b
        if b:
            say[b] += 1
    return dict(say)


def main():
    if len(sys.argv) >= 4 and sys.argv[1] == '--sinif':          # --sinif YEDEK.json SIR.json [SIR.json ...]
        s = sinif(sys.argv[2], sys.argv[3:])
        print('TARAMA YEDEK.json ' + (' '.join(f'{k}={v}' for k, v in sorted(s.items())) or 'TEMIZ'), flush=True)
        sys.exit(0 if set(s) <= {'presigned-url'} else 1)
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    tok = json.load(open(sys.argv[1]))
    for k in ('userToken', 'userId', 'blogId'):
        if not tok.get(k):
            raise SystemExit(f'DUR: kimlikte {k} yok')
    calis(tok, sys.argv[2])


if __name__ == '__main__':
    main()
