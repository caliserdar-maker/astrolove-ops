#!/usr/bin/env python3
"""Metricool: bekleyen video gonderilerinin videosunu kapakli videoyla degistir (Serdar onaylari 15 Eki 2026).

Olcum (15 Eki, 38712850093): PUT /v2/scheduler/posts/{id} gonderiye YENI id verir, uuid ayni kalir. Gonderi her zaman
bul() ile bulunur: uuid + tarih varsa yayin gununun +-1 gun listesinde uuid ile (kopya = DUR), yoksa id ile.

Izinli fark (Serdar 15 Eki, kontrol 38714561537 sonrasi):
  id, media[0], creationDate.* (Metricool duzenleme zamani);
  instagramData.type ve instagramData.showReelOnFeed YALNIZ ONCE'de yoksa VE gonderi Instagram'a gitmiyorsa
  (Metricool varsayilani; Instagram gonderisinde bu alanlar degisirse FAIL: Reel normal gonderiye donmemeli).
  Metin, kapak, saat, durum, ag alanlari (facebookData, instagramData, tiktokData, youtubeData...), saglayicilar,
  taslak ve otomatik yayin dahil her baska fark = FAIL.

Mod yaz (birden cok hedef ayni cift; her FAIL -> DUR, sonraki hedefe gecilmez):
  1. Her hedef bul() -> <uuid>/ONCE.json. Kapi: PENDING, yayina >= 2 sa, tek .mp4, ag dogru, cift dogru, kapak dolu.
     Bir hedef bile gecmezse HICBIR yazma yok.
  2. Kapakli video 1 kez yuklenir (metricool_5p_yaz.video_yukle) ve donusturulmus dosya olculur (kapak_basa esikleri).
  3. Hedefler sirayla: yeniden bul (ONCE ile ayni, PENDING, yayina >= 2 sa) -> PUT (ONCE govdesi, YALNIZ media[0]) ->
     uuid ile bul -> <uuid>/SONRA.json + FARK.csv; gonderideki video yeniden olculur. FAIL -> DUR.
Diger modlar: kuru (1 + yerel olcum; yazma yok), kontrol (SALT OKUMA: --once ile tam fark), geri (ONCE govdesiyle PUT).
Hedef: --hedef ag:id:uuid (virgulle birden fazla) ya da tek hedef icin --ag/--id/--uuid.
--fb-kapak (20 Eki, Serdar onayi Reels P degisimi): facebook hedeflerinde videoThumbnailUrl de degisir = --kapak dosyasi
(yeni videonun ilk karesi) Metricool'a bir kez yuklenir; FB icin izinli fark videoThumbnailUrl eklenir; PUT sonrasi
kapak URL'si ve indirilen kapak - --kapak farki (< ESIK) kapidir. Diger aglarda yalniz media[0] degisir.
--yt-kapak (20 Eki, Serdar onayi TikTok/YouTube P degisimi): ayni mekanizma youtube hedeflerinde (KAPAK_AG'ye youtube).
Cift kapisi: sko.cift_bul ayni burcu bir kez sayar (ARIES_ARIES -> None); metin/baslikta 'X and|& Y' de kabul edilir.
Token loga/dosyaya yazilmaz; presigned URL'ler maskelenir."""
import argparse, copy, csv, importlib.util, json, os, re, subprocess, sys
from datetime import datetime, timedelta

import numpy as np

D = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(D))
MIN_SAAT = 2
TZ = 'Europe/Istanbul'
IG_VARSAYILAN = ('instagramData.type', 'instagramData.showReelOnFeed')
KURAL = ('id, media[0], creationDate.*; instagramData.type / showReelOnFeed yalniz ONCE\'de yoksa ve ag instagram degilse')
KAPAK_AG = set()   # --fb-kapak: videoThumbnailUrl bu aglarda izinli ve degisir


def yukle(ad, yol):
    sp = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
    return m


def simdi_ist():
    return datetime.utcnow() + timedelta(hours=3)


def olc(kb, yol, kapak):
    """Videonun ilk kare / parlaklik / kare / sure olcumu (kapak_basa ile ayni esikler)."""
    v = kb.probe(yol)
    W, H = v['w'], v['h']
    K = kb.kapak_dizi(kapak, W, H)
    n = int(round(kb.KONTROL_SN * v['fps'])) + 1
    ilk = kb.kareler(yol, W, H, n)
    parl = [float(f.mean()) for f in ilk]
    q = {'boyut_px': f'{W}x{H}', 'kare': v['kare'], 'video_sn': v['video_sn'], 'ses_sn': v['ses_sn'], 'bayt': v['boyut'],
         'kapak_parlaklik': round(float(K.mean()), 1), 'ilk_kare_fark': round(float(np.abs(ilk[0] - K).mean()), 2),
         'min_parlaklik_0_1.5': round(min(parl), 1)}
    q['kapilar'] = {'ilk_kare': q['ilk_kare_fark'] < kb.ESIK, 'min_parlaklik': min(parl) >= float(K.mean()) / 2,
                    'kare': v['kare'] == 720, 'sure': abs(v['video_sn'] - 24.0) <= 0.05,
                    'ses': v['ses_sn'] is not None and abs(v['ses_sn'] - 24.0) <= 0.05}
    q['sonuc'] = 'PASS' if all(q['kapilar'].values()) else 'FAIL'
    return q


def kapak_fark(kb, url, kapak, yol):
    """URL'deki kapak gorseli - yerel --kapak: ortalama mutlak RGB farki (kapak boyutunda). Hata -> metin."""
    hc = subprocess.run(['curl', '-sL', '-m', '120', '-o', yol, '-w', '%{http_code}', url], capture_output=True, text=True).stdout
    if hc != '200':
        return f'indirilemedi http {hc}'
    try:
        K = np.asarray(__import__('PIL.Image', fromlist=['Image']).open(kapak).convert('RGB'), np.float32)
        return round(float(np.abs(kb.kapak_dizi(yol, K.shape[1], K.shape[0]) - K).mean()), 2)
    finally:
        os.remove(yol)


def durum(p, ag):
    pr = [x for x in p.get('providers') or [] if (x.get('network') or '').lower() == ag]
    return (pr[0].get('status') or '') if len(pr) == 1 and len(p.get('providers') or []) == 1 else f'AG? {p.get("providers")}'


def bul(mc, mpb, pid, uuid, tarih):
    """Gonderi: uuid + tarih varsa HER ZAMAN tarih +-1 gun listesinde uuid ile (kopya kontrolu: birden fazla -> DUR);
    yoksa id ile tekil GET. (govde, yol) ya da (None, sebep)."""
    if not uuid or not tarih:
        if pid:
            p = mc.istek('GET', f'/v2/scheduler/posts/{pid}', yok404=True)
            if p is not mpb.YOK and p is not None:
                p = mpb.veri(p)
                if not uuid or str(p.get('uuid')) == str(uuid):
                    return p, 'id'
        return None, 'id ile bulunamadi, uuid/tarih yok'
    t = datetime.fromisoformat(tarih)
    liste = mpb.veri(mc.istek('GET', '/v2/scheduler/posts', {'start': (t - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                                                            'end': (t + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S'),
                                                            'timezone': TZ})) or []
    m = [x for x in liste if str(x.get('uuid')) == str(uuid)]
    if len(m) > 1:
        raise SystemExit(f'DUR: uuid {uuid} icin {len(m)} gonderi (kopya?): {[x.get("id") for x in m]}')
    return (m[0], 'uuid') if m else (None, f'uuid {uuid} listede yok ({len(liste)} gonderi)')


def cift_esit(sko, p, cift):
    """sko.cift_bul ayni burcu bir kez sayar (ARIES_ARIES -> None): once onu, sonra metin/baslikta 'X and|& Y' dener."""
    c = sko.cift_bul(p)
    if c is not None and '_'.join(x.upper() for x in c) == cift:
        return True
    b = '|'.join(sko.BURCLAR)
    for t in (p.get('text'), (p.get('youtubeData') or {}).get('title')):
        m = re.search(r'\b(' + b + r')\s*(?:&|and)\s*(' + b + r')\b', (t or '').lower())
        if m and '_'.join(sorted((m.group(1).upper(), m.group(2).upper()))) == cift:
            return True
    return False


def deger(x, yol):
    """'a.b[0].c' yolundaki deger (yoksa '<yok>')."""
    for parca in re.findall(r'[^.\[\]]+|\[\d+\]', yol):
        if parca.startswith('['):
            i = int(parca[1:-1])
            x = x[i] if isinstance(x, list) and i < len(x) else '<yok>'
        else:
            x = x.get(parca, '<yok>') if isinstance(x, dict) else '<yok>'
        if x == '<yok>':
            break
    return x


def izinli(yol, once, ag, medya=True):
    if yol == 'id' or yol.startswith('creationDate.') or (medya and yol == 'media[0]'):
        return True
    if medya and yol == 'videoThumbnailUrl' and ag in KAPAK_AG:
        return True
    if yol in IG_VARSAYILAN:
        return ag != 'instagram' and deger(once, yol) == '<yok>'
    return False


def fark_tablosu(mpb, sko, once, simdi, ag, cikti, medya=True):
    """Alan alan fark: (satirlar, izinsiz). <cikti>/FARK.csv yazar. URL'ler sorgusuz."""
    def k(v):
        return sko.kisa(v) if isinstance(v, str) and v.startswith('http') else json.dumps(v, ensure_ascii=False, default=str)[:300]
    satir = [{'alan': y, 'once': k(deger(once, y)), 'simdi': k(deger(simdi, y)), 'izinli': izinli(y, once, ag, medya)}
             for y in mpb.fark(once, simdi)]
    os.makedirs(cikti, exist_ok=True)
    with open(os.path.join(cikti, 'FARK.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, ['alan', 'once', 'simdi', 'izinli']); w.writeheader(); [w.writerow(r) for r in satir]
    return satir, [r['alan'] for r in satir if not r['izinli']]


def main():
    a = argparse.ArgumentParser()
    for k in ('token', 'cift', 'mod', 'cikti'):
        a.add_argument('--' + k, required=True)
    a.add_argument('--ag', default=''); a.add_argument('--id', default=''); a.add_argument('--uuid', default='')
    a.add_argument('--hedef', default='', help='ag:id:uuid[,ag:id:uuid...]')
    a.add_argument('--video', default=''); a.add_argument('--kapak', default=''); a.add_argument('--once', default='')
    a.add_argument('--fb-kapak', action='store_true')
    a.add_argument('--yt-kapak', action='store_true')
    o = a.parse_args()
    if o.fb_kapak:
        KAPAK_AG.add('facebook')
    if o.yt_kapak:
        KAPAK_AG.add('youtube')
    os.makedirs(o.cikti, exist_ok=True)
    yz = yukle('yz', os.path.join(D, 'metricool_5p_yaz.py'))
    sko = yukle('sko', os.path.join(D, 'sosyal_kapak_oku.py'))
    mpb = yz.mpb
    mc = mpb.MC(json.load(open(o.token)))
    hedefler = [dict(zip(('ag', 'id', 'uuid'), (h.split(':') + ['', ''])[:3])) for h in o.hedef.split(',') if h.strip()] \
        or [{'ag': o.ag, 'id': o.id, 'uuid': o.uuid}]
    if any(h['ag'] not in ('facebook', 'instagram', 'tiktok', 'youtube') for h in hedefler):
        sys.exit(f'DUR: ag hatali {hedefler}')
    ad = 'KONTROL_RAPOR.json' if o.mod == 'kontrol' else 'DEGISTIR_RAPOR.json'
    rapor = {'cift': o.cift, 'mod': o.mod, 'hedefler': hedefler, 'izinli_fark': KURAL,
             'basla': simdi_ist().strftime('%Y-%m-%dT%H:%M:%S'), 'adimlar': [], 'gonderiler': {}}

    def kaydet():
        json.dump(rapor, open(os.path.join(o.cikti, ad), 'w'), ensure_ascii=False, indent=1)

    def dur(neden):
        rapor['sonuc'] = f'DUR: {neden}'
        kaydet()
        print(f'DUR: {neden}', flush=True)
        sys.exit(1)

    def adim(ad_, **k):
        rapor['adimlar'].append(dict(ad=ad_, **k)); kaydet()
        print(f'ADIM {ad_}: ' + json.dumps(k, ensure_ascii=False, default=str)[:1200], flush=True)

    def bul_(*x):
        try:
            return bul(mc, mpb, *x)
        except SystemExit as e:   # uuid kopyasi
            dur(str(e).replace('DUR: ', ''))

    def bitir(kapi):
        rapor['kapilar'] = kapi
        rapor['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL: ' + ', '.join(k for k, v in kapi.items() if not v)
        kaydet(); print('SONUC', rapor['sonuc'], flush=True)
        sys.exit(0 if rapor['sonuc'] == 'PASS' else 1)

    # --- kontrol / geri (tek hedef): ONCE.json'dan uuid ve tarih ---
    if o.mod in ('kontrol', 'geri'):
        h = hedefler[0]
        if not o.once:
            dur(f'{o.mod}: --once gerekli')
        ref = json.load(open(o.once))
        uuid = h['uuid'] or str(ref.get('uuid') or '')
        if h['uuid'] and str(ref.get('uuid')) != h['uuid']:
            dur(f"ONCE uuid {ref.get('uuid')} != --uuid {h['uuid']}")
        tarih = (ref.get('publicationDate') or {}).get('dateTime')
        simdi, yol = bul_(h['id'], uuid, tarih)
        if simdi is None:
            dur(f'gonderi bulunamadi: {yol}')
        adim('bul', yol=yol, id_once=ref.get('id'), id_simdi=simdi.get('id'), uuid=simdi.get('uuid'), durum=durum(simdi, h['ag']))
        if o.mod == 'kontrol':
            json.dump(simdi, open(os.path.join(o.cikti, 'SIMDI.json'), 'w'), ensure_ascii=False, indent=1)
            satir, izinsiz = fark_tablosu(mpb, sko, ref, simdi, h['ag'], o.cikti)
            adim('fark', alan_sayisi=len(satir), izinsiz=izinsiz, tablo=satir)
            bitir({'izinsiz_fark_yok': not izinsiz, 'uuid_ayni': str(simdi.get('uuid')) == uuid,
                   'durum_PENDING': durum(simdi, h['ag']) == 'PENDING'})
        if durum(simdi, h['ag']) != 'PENDING':
            dur(f"geri: durum {durum(simdi, h['ag'])}")
        if datetime.fromisoformat(tarih) - simdi_ist() < timedelta(hours=MIN_SAAT):
            dur(f'geri: yayina {MIN_SAAT} saatten az')
        govde = copy.deepcopy(ref); govde['id'] = simdi.get('id')
        mc.istek('PUT', f"/v2/scheduler/posts/{simdi.get('id')}", govde=govde)
        son, yol = bul_('', uuid, tarih)
        if son is None:
            dur(f'geri sonrasi bulunamadi: {yol}')
        json.dump(son, open(os.path.join(o.cikti, 'GERI_SONRA.json'), 'w'), ensure_ascii=False, indent=1)
        satir, izinsiz = fark_tablosu(mpb, sko, ref, son, h['ag'], o.cikti, medya=False)
        adim('geri', id_simdi=son.get('id'), media=[sko.kisa(x) for x in son.get('media') or []], izinsiz=izinsiz)
        bitir({'once_ile_ayni': not izinsiz, 'durum_PENDING': durum(son, h['ag']) == 'PENDING'})

    # --- kuru / yaz: 1) tum hedeflerin ONCE kapisi (yazma oncesi) ---
    kb = yukle('kb', os.path.join(KOK, 'sosyal', 'video_v9', 'kapak_basa.py'))
    onceler = []
    for h in hedefler:
        once, yol = bul_(h['id'], h['uuid'], '')
        if once is None:
            dur(f"{h['ag']} {h['id']} bulunamadi: {yol}")
        uuid = str(once.get('uuid') or '')
        d = os.path.join(o.cikti, uuid or str(once.get('id')))
        os.makedirs(d, exist_ok=True)
        json.dump(once, open(os.path.join(d, 'ONCE.json'), 'w'), ensure_ascii=False, indent=1)
        zaman = datetime.fromisoformat((once.get('publicationDate') or {}).get('dateTime'))
        c = sko.cift_bul(once)
        medya = once.get('media') or []
        kapi = {'durum_PENDING': durum(once, h['ag']) == 'PENDING',
                'saat_tz_istanbul': (once.get('publicationDate') or {}).get('timezone') == TZ,
                f'yayina_>=_{MIN_SAAT}_sa': zaman - simdi_ist() >= timedelta(hours=MIN_SAAT),
                'tek_mp4_medya': len(medya) == 1 and isinstance(medya[0], str) and medya[0].split('?')[0].endswith('.mp4'),
                'cift': cift_esit(sko, once, o.cift),
                'kapak_alani': bool(once.get('videoThumbnailUrl')), 'uuid': bool(uuid) and (not h['uuid'] or uuid == h['uuid'])}
        rapor['gonderiler'][uuid] = {'ag': h['ag'], 'id_once': once.get('id'), 'yayin': zaman.isoformat(), 'once_kapi': kapi}
        adim('once', ag=h['ag'], yol=yol, id=once.get('id'), uuid=uuid, yayin=str(zaman), durum=durum(once, h['ag']), cift=c,
             medya=[sko.kisa(m) for m in medya], kapak=sko.kisa(once.get('videoThumbnailUrl') or ''), kapilar=kapi)
        if not all(kapi.values()):
            dur(f"ONCE kapisi {h['ag']}: " + ', '.join(k for k, v in kapi.items() if not v) + ' (hicbir gonderiye yazilmadi)')
        onceler.append((h, once, uuid, zaman, d))
    if len({u for _, _, u, _, _ in onceler}) != len(onceler):
        dur('ayni uuid iki kez hedefte')
    if o.mod == 'kuru':
        q = olc(kb, o.video, o.kapak)
        adim('kuru_yerel_olcum', **q)
        bitir({'yerel_olcum': q['sonuc'] == 'PASS'})

    # 2) 1 yukleme + donusturulmus dosya olcumu
    yeni_url, yk = yz.video_yukle(mc, o.video)
    adim('yukleme', url=sko.kisa(yeni_url), boyut=yk['boyut'], prob=yk['prob'])
    if not sko.kisa(yeni_url).endswith('.mp4'):
        dur(f'yeni URL .mp4 degil: {sko.kisa(yeni_url)} (hicbir gonderiye yazilmadi)')
    indir = os.path.join(o.cikti, '_donusturulmus.mp4')
    hc = subprocess.run(['curl', '-sL', '-m', '300', '-o', indir, '-w', '%{http_code}', yeni_url], capture_output=True, text=True).stdout
    if hc != '200':
        dur(f'donusturulmus dosya indirilemedi http {hc} (hicbir gonderiye yazilmadi)')
    q = olc(kb, indir, o.kapak)
    os.remove(indir)
    adim('donusturulmus_olcum', **q)
    if q['sonuc'] != 'PASS':
        dur('donusturulmus dosya kapisi: ' + ', '.join(k for k, v in q['kapilar'].items() if not v) + ' (hicbir gonderiye yazilmadi)')
    kapak_url = ''
    if any(h['ag'] in KAPAK_AG for h, *_ in onceler):
        kapak_url, kk = yz.video_yukle(mc, o.kapak, 'image/jpeg', 'jpg')
        kf = kapak_fark(kb, kapak_url, o.kapak, os.path.join(o.cikti, '_kapak.jpg'))
        adim('kapak_yukleme', url=sko.kisa(kapak_url), boyut=kk['boyut'], prob=kk['prob'], fark=kf)
        if not isinstance(kf, float) or kf >= kb.ESIK:
            dur(f'yuklenen kapak farki {kf} (hicbir gonderiye yazilmadi)')

    # 3) hedefler sirayla; ilk FAIL -> DUR
    for i, (h, once, uuid, zaman, d) in enumerate(onceler, 1):
        g = rapor['gonderiler'][uuid]
        tekrar, _ = bul_(str(once.get('id')), uuid, zaman.isoformat())
        f0 = mpb.fark(once, tekrar) if tekrar else ['OKUNAMADI']
        if f0 or durum(tekrar, h['ag']) != 'PENDING' or simdi_ist() + timedelta(hours=MIN_SAAT) > zaman:
            g['sonuc'] = 'YAZILMADI'
            dur(f"{h['ag']} PUT oncesi: fark {f0}, durum {durum(tekrar, h['ag']) if tekrar else '-'}, yayin {zaman} "
                f"({i - 1}/{len(onceler)} yazildi)")
        yeni = copy.deepcopy(once)
        yeni['media'][0] = yeni_url
        beklenen = ['media[0]']
        if h['ag'] in KAPAK_AG:
            yeni['videoThumbnailUrl'] = kapak_url
            beklenen = sorted(['media[0]', 'videoThumbnailUrl'])
        if sorted(mpb.fark(once, yeni)) != beklenen:
            dur(f'govde farki beklenmedik: {mpb.fark(once, yeni)}')
        y = mc.istek('PUT', f"/v2/scheduler/posts/{once.get('id')}", govde=yeni, yok404=True)
        if y is mpb.YOK:
            g['sonuc'] = 'PUT 404'
            dur(f"{h['ag']} PUT 404 (yayinlanmis olabilir) ({i - 1}/{len(onceler)} yazildi)")
        sonra, yol = bul_('', uuid, zaman.isoformat())
        if sonra is None:
            g['sonuc'] = 'PUT sonrasi bulunamadi'
            dur(f"{h['ag']} PUT sonrasi bulunamadi: {yol}")
        json.dump(sonra, open(os.path.join(d, 'SONRA.json'), 'w'), ensure_ascii=False, indent=1)
        satir, izinsiz = fark_tablosu(mpb, sko, once, sonra, h['ag'], d)
        m_sonra = (sonra.get('media') or [''])[0]
        m2 = os.path.join(o.cikti, '_gonderideki.mp4')
        hc = subprocess.run(['curl', '-sL', '-m', '300', '-o', m2, '-w', '%{http_code}', m_sonra], capture_output=True, text=True).stdout
        q2 = olc(kb, m2, o.kapak) if hc == '200' else {'sonuc': f'INDIRILEMEDI http {hc}'}
        if os.path.exists(m2):
            os.remove(m2)
        kapi = {'izinsiz_fark_yok': not izinsiz, 'media0_yeni': m_sonra.split('?')[0] == yeni_url.split('?')[0],
                'durum_PENDING': durum(sonra, h['ag']) == 'PENDING', 'uuid_ayni': str(sonra.get('uuid')) == uuid,
                'gonderideki_video_PASS': q2['sonuc'] == 'PASS'}
        if h['ag'] in KAPAK_AG:
            t_sonra = sonra.get('videoThumbnailUrl') or ''
            kf2 = kapak_fark(kb, t_sonra, o.kapak, os.path.join(o.cikti, '_kapak2.jpg')) if t_sonra else 'kapak yok'
            kapi['kapak_yeni'] = t_sonra.split('?')[0] == kapak_url.split('?')[0]
            kapi['kapak_ilk_kare_fark'] = isinstance(kf2, float) and kf2 < kb.ESIK
            q2['kapak_fark'] = kf2
        g.update(id_sonra=sonra.get('id'), fark=satir, kapilar=kapi, gonderideki_video=q2,
                 sonuc='PASS' if all(kapi.values()) else 'FAIL')
        adim('sonra', ag=h['ag'], id_yeni=sonra.get('id'), tablo=satir, izinsiz=izinsiz, kapilar=kapi)
        if g['sonuc'] != 'PASS':
            dur(f"{h['ag']} FAIL: " + ', '.join(k for k, v in kapi.items() if not v) + f' ({i}/{len(onceler)} yazildi, sonrakilere gecilmedi)')
    bitir({f"{rapor['gonderiler'][u]['ag']}_{u}": rapor['gonderiler'][u]['sonuc'] == 'PASS' for _, _, u, _, _ in onceler})


if __name__ == '__main__':
    main()
