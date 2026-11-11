#!/usr/bin/env python3
"""metricool_yedek sahte testi. AG KAPALI: socket.socket ve urllib.request.urlopen bastan engellenir; metricool_yedek.ac taklit.
Bilinen PASS: iki pencere, 3 ag, bir tekrar (tekillesir), yayinli gonderi yedege girmez, govde aynen, OZET'te metin / medya yok.
Bilinen FAIL: 401 / 403 DUR (dosya yazilmaz), liste degil DUR, 429 DUR (yeniden deneme yok), 5xx 2 yeniden denemeden sonra DUR,
zaman asimi 2 yeniden deneme; GET disi istek denenirse test kirmizi; kaynakta yazma cagrisi yok."""
import contextlib
import io
import json
import re
import socket
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

def _ag_yok(*a, **k):
    raise AssertionError('gercek ag acilmaya calisildi')


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metricool_yedek as M  # noqa: E402

M.time.sleep = lambda *_: None
TOK = {'userToken': 'SAHTETOKEN0123456789', 'userId': 1, 'blogId': 2}
METIN = 'GIZLI GONDERI METNI'
MEDYA = 'https://cdn.example/m/resim.jpg?X-Amz-Signature=abc'


def gonderi(i, ag, durum='PENDING', tarih='2026-11-12T10:00:00', **ek):
    return dict({'id': 100 + i, 'uuid': f'u-{i}', 'text': f'{METIN} {i}', 'media': [MEDYA],
                 'publicationDate': {'dateTime': tarih, 'timezone': M.TZ},
                 'providers': [{'network': ag, 'status': durum}], 'pinterestData': {'boardId': 'b'}}, **ek)


class Yanit:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Sahte:
    def __init__(self, cevap):
        self.cevap, self.cagri = cevap, []

    def __call__(self, req, timeout):
        if req.get_method() != 'GET' or req.data is not None:
            raise AssertionError(f'YAZMA CAGRISI: {req.get_method()}')
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(req.full_url).query))
        self.cagri.append(q)
        r = self.cevap(len(self.cagri), q)
        if isinstance(r, BaseException):
            raise r
        return Yanit(json.dumps(r).encode() if not isinstance(r, bytes) else r)


def _dur(f, *a):
    try:
        f(*a)
    except SystemExit as e:
        return str(e.code)
    return ''


def http(kod):
    return urllib.error.HTTPError('u', kod, 'x', {}, io.BytesIO(b'{"govde":"GIZLI GONDERI METNI"}'))


def kos(cevap, son=datetime(2026, 11, 20)):
    M.ISTEK[0] = 0
    M.SON = son
    s = Sahte(cevap)
    M.ac = s
    d = Path(tempfile.mkdtemp(prefix='mc_yedek_'))
    log = io.StringIO()
    hata = None
    with contextlib.redirect_stdout(log):
        try:
            M.calis(TOK, str(d), simdi=datetime(2026, 11, 11, 15, 0, 0))
        except SystemExit as e:
            hata = str(e.code)
    return s, d, hata, log.getvalue()


def testler():  # noqa: C901
    t = []
    # A: iki pencere (11-16 Kas, 16-20 Kas), 3 ag, u-2 iki pencerede (tekrar), u-9 yayinli
    p1 = [gonderi(1, 'instagram'), gonderi(2, 'pinterest', tarih='2026-11-16T00:00:00'), gonderi(9, 'facebook', 'PUBLISHED')]
    p2 = [gonderi(2, 'pinterest', tarih='2026-11-16T00:00:00'), gonderi(3, 'tiktok', 'AWAITING_CONFIRMATION', tarih='2026-11-19T09:00:00'),
          dict(gonderi(4, 'youtube', 'PUBLISHED'), draft=True)]
    s, d, h, log = kos(lambda n, q: {'data': p1 if n == 1 else p2})
    y = json.loads((d / 'YEDEK.json').read_text())
    oz_m = (d / 'OZET.json').read_text()
    oz = json.loads(oz_m)
    t.append(('PASS: hata yok, iki pencere, iki istek', h is None and len(s.cagri) == 2 and oz['istek'] == 2 and oz['_pencere']['adet'] == 2))
    t.append(('PASS: pencere sinirlari 5 gun ve SON', [(q['start'], q['end']) for q in s.cagri] ==
              [('2026-11-11T15:00:00', '2026-11-16T15:00:00'), ('2026-11-16T15:00:00', '2026-11-20T00:00:00')]
              and all(q['timezone'] == M.TZ and q['userId'] == '1' and q['blogId'] == '2' for q in s.cagri)))
    t.append(('PASS: bekleyen 4 (tekrar tekil, yayinli disarida, draft=true iceride)', y['_adet'] == 4
              and sorted(g['uuid'] for g in y['gonderiler']) == ['u-1', 'u-2', 'u-3', 'u-4'] and oz['tekrar_atlanan'] == 1))
    t.append(('PASS: govde aynen (alan cikarilmadi)', next(g for g in y['gonderiler'] if g['uuid'] == 'u-1') == p1[0]))
    t.append(('PASS: YEDEK basliklari', set(y) == {'_okuma', '_pencere', '_adet', 'gonderiler'} and y['_okuma'].endswith('Z')))
    t.append(('PASS: ag bazinda (ag suzgeci yok)', oz['ag_bazinda_bekleyen'] == {'instagram': 1, 'pinterest': 1, 'tiktok': 1}
              and oz['ag_durum_sayimi'].get('youtube:PUBLISHED') == 1 and oz['draft_true'] == 1))
    t.append(('PASS: en erken / en gec, medyali', oz['en_erken'] == '2026-11-12T10:00:00' and oz['en_gec'] == '2026-11-19T09:00:00'
              and oz['medya_adresi_iceren'] == 4 and oz['toplam'] == 4))
    t.append(('FAIL: OZET.json ve log metin / medya adresi / token icermez', METIN not in oz_m + log and 'cdn.example' not in oz_m + log
              and 'X-Amz' not in oz_m + log and TOK['userToken'] not in oz_m + log))
    # B: 401 / 403
    for kod in (401, 403):
        s, d, h, log = kos(lambda n, q: http(kod))
        t.append((f'FAIL: {kod} -> DUR (API kapali), tek istek, dosya yok, govde loga yok', h is not None and f'HTTP {kod}' in h
                  and 'API kapali' in h and len(s.cagri) == 1 and not list(d.iterdir()) and METIN not in h + log))
    # C: liste degil
    for ad, c in (('dict', {'data': {'a': 1}}), ('None', None), ('metin', b'<html>')):
        s, d, h, _ = kos(lambda n, q: c)
        t.append((f'FAIL: yanit {ad} -> DUR', h is not None and ('liste degil' in h or 'JSON degil' in h) and not list(d.iterdir())))
    # D: 429 yeniden denenmez; 5xx ve zaman asimi en cok 2 yeniden deneme
    s, d, h, _ = kos(lambda n, q: http(429))
    t.append(('FAIL: 429 -> DUR, yeniden deneme yok', h is not None and 'HTTP 429' in h and len(s.cagri) == 1))
    s, d, h, _ = kos(lambda n, q: http(503))
    t.append(('FAIL: 503 x3 -> DUR (2 yeniden deneme)', h is not None and '5xx' in h and len(s.cagri) == 3))
    s, d, h, _ = kos(lambda n, q: TimeoutError('t'))
    t.append(('FAIL: zaman asimi x3 -> DUR', h is not None and 'zaman asimi' in h and len(s.cagri) == 3))
    s, d, h, _ = kos(lambda n, q: http(502) if n == 1 else {'data': p1 if n == 2 else p2})
    t.append(('PASS: 502 bir kez -> yeniden deneme basarili', h is None and len(s.cagri) == 3 and json.loads((d / 'YEDEK.json').read_text())['_adet'] == 4))
    # F: coklu saglayici, saglayicisiz, uuid'siz, dict disi
    p3 = [dict(gonderi(5, 'facebook'), providers=[{'network': 'facebook', 'status': 'PUBLISHED'}, {'network': 'threads', 'status': 'PENDING'}]),
          dict(gonderi(6, 'x'), providers=[]), {k: v for k, v in gonderi(7, 'youtube').items() if k != 'uuid'}, 'bozuk', 42]
    s, d, h, _ = kos(lambda n, q: {'data': p3}, son=datetime(2026, 11, 14))
    oz = json.loads((d / 'OZET.json').read_text())
    t.append(('PASS: coklu saglayici (biri PUBLISHED) + saglayicisiz + uuidsiz yedekte, dict disi sayilir', h is None
              and oz['toplam'] == 3 and oz['ag_bazinda_bekleyen'] == {'threads': 1, 'youtube': 1} and oz['saglayicisiz'] == 1
              and oz['dict_disi_atlanan'] == 2 and oz['ag_durum_sayimi'].get('facebook:PUBLISHED') == 1))
    # G: kirpilma suphesi -> 1 gunluk parcalar; parcalarla gelen yeni gonderi de yedege girer
    cok = [gonderi(1000 + i, 'pinterest') for i in range(M.KIRPILMA)]
    s, d, h, _ = kos(lambda n, q: {'data': cok if n == 1 else ([gonderi(2000, 'instagram')] if n == 2 else [])}, son=datetime(2026, 11, 14))
    oz = json.loads((d / 'OZET.json').read_text())
    t.append(('PASS: 5 gunluk pencere >= 50 -> 1 gunluk parcalar okunur, birlesim', h is None and len(s.cagri) == 1 + 3
              and oz['toplam'] == M.KIRPILMA + 1 and oz['pencere_ham_en_buyuk'] == M.KIRPILMA and oz['kirpilma_suphesi_gun'] == []))
    s, d, h, _ = kos(lambda n, q: {'data': cok}, son=datetime(2026, 11, 12, 15))
    oz = json.loads((d / 'OZET.json').read_text())
    t.append(('PASS: 1 gunluk parca da >= 50 -> kirpilma_suphesi_gun dolu (DUR degil)', h is None and len(oz['kirpilma_suphesi_gun']) == 1))
    # H: kismi okuma (IncompleteRead) yeniden denenir
    import http.client as hc
    s, d, h, _ = kos(lambda n, q: hc.IncompleteRead(b'x') if n == 1 else {'data': []}, son=datetime(2026, 11, 13))
    t.append(('PASS: IncompleteRead -> yeniden deneme', h is None and len(s.cagri) == 2))
    # I: Drive oncesi siniflama (--sinif)
    sj = Path(tempfile.mkdtemp(prefix='mc_sj_')) / 'mc.json'
    sj.write_text(json.dumps(TOK))
    for ad, icerik, beklenen, gecer in (
            ('temiz', '{"text": "hi"}', {}, True), ('yalniz imza', '{"m": "https://s3/a.jpg?X-Amz-Signature=abc"}', {'presigned-url': 1}, True),
            ('imza + api_key ayni satir', '{"m": "https://s3/a.jpg?X-Amz-Signature=abc&api_key=SECRETVALUE99"}', {'anahtar-deseni': 1}, False),
            ('imza + token ayni satir', '{"m": "https://s3/a.jpg?X-Amz-Signature=abc&t=' + TOK['userToken'] + '"}', {'sir-degeri': 1}, False),
            ('token metinde', '{"text": "' + TOK['userToken'] + '"}', {'sir-degeri': 1}, False),
            ('add-mask', '::add-mask::xyzxyzxyz', {'add-mask': 1}, False)):
        f = sj.parent / 'Y.json'
        f.write_text(icerik + '\n')
        sn = M.sinif(str(f), [str(sj)])
        t.append((f"{'PASS' if gecer else 'FAIL'}: --sinif {ad}", sn == beklenen and (set(sn) <= {'presigned-url'}) == gecer))
    t.append(('FAIL: --sinif sir listesi bos -> DUR', 'sir listesi bos' in _dur(M.sinif, str(f), [])))
    # E: yazma cagrisi denenirse test kirmizi (sahte istemci GET disini reddeder)
    s = Sahte(lambda n, q: {'data': []})
    try:
        s(urllib.request.Request('https://x', data=b'{}', method='PUT'), 1)
        yakalandi = False
    except AssertionError:
        yakalandi = True
    t.append(('FAIL: sahte istemci GET disini reddeder', yakalandi))
    kaynak = (Path(__file__).resolve().parent / 'metricool_yedek.py').read_text()
    t.append(('PASS: kaynakta yazma yontemi / govde yok', not re.search(r"""['"](POST|PUT|DELETE|PATCH)['"]|data=""", kaynak)
              and kaynak.count("method='GET'") == 1))
    return t


def main():
    t = testler()
    for ad, ok in t:
        print(('PASS ' if ok else 'FAIL ') + ad)
    n = sum(bool(ok) for _, ok in t)
    print(f'metricool_yedek testleri TOPLAM: {n}/{len(t)} PASS')
    sys.exit(0 if n == len(t) else 1)


if __name__ == '__main__':
    main()
