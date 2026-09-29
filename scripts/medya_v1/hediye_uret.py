#!/usr/bin/env python3
"""Kisisellestirilmis dijital HEDIYE dosyasi (satis degil; Prodigi'ye gitmez, musteriye gonderim YOK).

Girdi: Drive kart TEMP/SIPARIS_ISIM/<KOD>.md (cift, isim1, isim2, mesaj, renkler, boylar).
Isim / mesaj yalniz Drive kartinda durur: repoya, commit'e ve loga yazilmaz; kosuda ilk is
`::add-mask::` ile maskelenir. Rapor ve dosya adlarinda yalniz KOD kullanilir.

Uretim: siparis_dosyasi.pod_uret (onayli kisisellestirme hatti: kisisel-v1 render, isim buyuk
harf ve kuculmez, D duzeni, slogan dokusu Secenek 1, POD_PRINT kaynak + PLATES zemin).
Kapi: olcek, plate_slogan, sembol, kalinti, mesaj_murekkep, font_kapsami, boy_siniri ZORUNLU
True; digerleri False olamaz. Biri bile kalirsa musteri klasorune HICBIR SEY yazilmaz.
Cikti: <hedef>/AstroLoveArt_<Cift>_<Renk>_<Boy>.jpg (sRGB ICC, JPEG kalite 92, 300 dpi)
       + ONIZLEME_<KOD>.jpg (4 dosya yan yana) + KONTROL_<Renk>_<Boy>_{ISIM,SLOGAN}_100.jpg
       + <KOD>_KAPI_RAPORU.json (isimsiz).
"""
import argparse, json, sys, time, traceback
from pathlib import Path

from PIL import Image, ImageCms, ImageDraw, ImageFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
ImageFile.MAXBLOCK = 1 << 26       # optimize=True buyuk dosyada 'Suspension not allowed' vermesin
ZORUNLU = ('olcek', 'plate_slogan', 'sembol', 'kalinti', 'mesaj_murekkep', 'font_kapsami', 'boy_siniri',
           'isim_kalinti')
KALITE = 92
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def kart_oku(metin):
    d = {}
    for s in metin.splitlines():
        s = s.strip().lstrip('-*# ').strip()
        if ':' in s:
            a, b = s.split(':', 1)
            d[a.strip().lower()] = b.strip()
    for a in ('cift', 'isim1', 'isim2', 'mesaj', 'renkler', 'boylar'):
        if not d.get(a):
            raise SystemExit(f'kartta eksik alan: {a}')
    return d


def gorunen(ad):
    return '_'.join(p.capitalize() for p in ad.split('_'))


def kirp(baski, bant, x2400, pay_kat=0.6):
    k = baski.width / 2400.0
    y0, y1 = bant
    p = (y1 - y0) * pay_kat
    kutu = (int(max(x2400[0] * k, 0)), int(max((y0 - p) * k, 0)),
            int(min(x2400[1] * k, baski.width)), int(min((y1 + p) * k, baski.height)))
    return baski.crop(kutu), kutu


ESKI_FAIL_BEKLENIR = True          # onceki dosyalar lekeli (Serdar reddi); kapi onlarda FAIL vermeli
AZAMI_BAYT = 8 * 1024 * 1024      # dosya basina ust sinir: asilirsa kalite duser, cozunurluk DEGISMEZ


def kaydet(im, yol):
    """sRGB JPEG, 300 dpi. Kalite 92'den baslar; 8 MB asilirsa 2'ser dusurulur (en az 80)."""
    rgb = im.convert('RGB')
    for q in range(KALITE, 79, -2):
        rgb.save(yol, 'JPEG', quality=q, subsampling=0, optimize=True,
                 dpi=(sd.DPI, sd.DPI), icc_profile=SRGB)
        if Path(yol).stat().st_size <= AZAMI_BAYT:
            return q
    raise SystemExit(f'{Path(yol).name}: kalite 80 ile de 8 MB ustu')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kod', required=True)
    ap.add_argument('--kart', default='')
    ap.add_argument('--hedef', required=True, help='orn. gdrive:ASTROLOVE/MUSTERI/<KOD>')
    a = ap.parse_args()
    kart = a.kart or f'{sd.SIP}/{a.kod}.md'
    yerel = sd.W / f'{a.kod}.md'
    sd.rc('copyto', kart, str(yerel))
    d = kart_oku(yerel.read_text(encoding='utf-8'))
    yerel.unlink()
    for v in (d['isim1'], d['isim2'], d['isim1'].upper(), d['isim2'].upper(), d['mesaj']):
        print(f'::add-mask::{v}', flush=True)
    renkler = [x.strip().upper() for x in d['renkler'].split(',') if x.strip()]
    boylar = [x.strip() for x in d['boylar'].split(',') if x.strip()]
    no, _ = sd.sayfa_no_tablosu()
    cift = d['cift'].upper()
    if cift not in no:
        raise SystemExit(f'cift POD_PRINT\'te yok: {cift}')
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    cik = sd.W / a.kod; cik.mkdir(parents=True, exist_ok=True)
    rapor = {'kod': a.kod, 'cift': cift, 'kosu': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'mesaj_karakter': len(d['mesaj']), 'dosyalar': []}
    goruntuler, T0, n = [], time.time(), 0
    toplam = len(renkler) * len(boylar)
    eski_dir = sd.W / f'{a.kod}_ESKI'; eski_dir.mkdir(parents=True, exist_ok=True)
    try:                                         # onceki teslim adaylari: ayni kapi olculur
        sd.rc('copy', a.hedef, str(eski_dir), '--max-depth', '1', '--include', 'AstroLoveArt_*.jpg',
              timeout=1800)
    except RuntimeError:
        pass
    for renk in renkler:
        for boy in boylar:
            n += 1
            x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod',
                              'isim1': d['isim1'].upper(), 'isim2': d['isim2'].upper(),
                              'mesaj': d['mesaj']})
            x['receipt'] = f'{a.kod}_{renk}_{boy}'
            x['sayfa'] = no[cift]
            yol = sd.pod_kaynak(cift, renk, boy)
            with Image.open(yol) as im:
                x['hedef_px'] = list(im.size)
            is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
            sd._TANI = {}
            try:
                r = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
            except BaseException as e:                            # noqa: BLE001
                r = {'durum': 'HATA', 'hata': f'{type(e).__name__}: {e}', 'iz': traceback.format_exc()[-1200:]}
            k = r.get('kapilar') or {}
            eksik = [g for g in ZORUNLU if k.get(g) is not True]
            yanlis = [g for g, v in k.items() if v is False]
            gecti = r.get('durum') == 'URETILDI' and not eksik and not yanlis
            ad = f'AstroLoveArt_{gorunen(cift)}_{gorunen(renk)}_{boy}.jpg'
            s = {'dosya': ad, 'renk': renk, 'boy': boy, 'durum': r.get('durum'), 'hata': r.get('hata'),
                 'gecti': gecti, 'kalan_kapilar': sorted(set(eksik) | set(yanlis)), 'kapilar': k,
                 'olcek': {q: (r.get('olcek_kapisi') or {}).get(q) for q in ('konum_fark_px', 'kenar_fark_px')},
                 'plate_slogan_payi': (r.get('plate_slogan_kapisi') or {}).get('glif_farkli_payi'),
                 'baski_px': r.get('baski_px'), 'gorsel_dpi': r.get('gorsel_dpi'), 'metin_dpi': r.get('metin_dpi'),
                 'isim_kalinti': {q: (r.get('isim_kalinti_kapisi') or {}).get(q)
                                  for q in ('gecti', 'kalinti_sayisi', 'kalintilar', 'hata')},
                 'isim_bandi_temizligi': r.get('isim_bandi_temizligi')}
            T = sd._TANI or {}
            eski = eski_dir / ad
            if eski.exists() and r.get('plate') and r.get('olcum'):
                with Image.open(eski) as ei:             # ayni kapi, onceki (onaylanmayan) dosyada
                    eski_im = ei.convert('RGB')
                ek_ = sd.isim_kalinti_kapisi(eski_im, T.get('yeni'), r['olcum'])
                s['eski_dosya_isim_kalinti'] = {q: ek_.get(q) for q in ('gecti', 'kalinti_sayisi',
                                                                        'kalintilar', 'hata')}
                # kontrol noktalari: eski dosyanin her kalinti bileseni yeni dosyada ayni yerde olculur
                if T.get('baski') is not None:
                    nokta = []
                    for z in ek_.get('kalintilar') or []:
                        x, y = z['x'] + z['w'] // 2, z['y'] + z['h'] // 2
                        nokta.append({'x': x, 'y': y, 'eski': sd.nokta_olc(eski_im, x, y),
                                      'yeni': sd.nokta_olc(T['baski'], x, y)})
                    s['kalinti_noktalari'] = nokta
                    if nokta:                            # isimlerin solundaki leke (en soldaki)
                        s['sol_leke'] = min(nokta, key=lambda q: q['x'])
                    # Serdar'in bildirdigi noktalar (MB 11x14 ISIM kirpimi koordinatlari)
                    if renk == 'MIDNIGHT_BLUE' and boy == '11x14':
                        kx, ky = 206, 3022
                        s['bildirilen_noktalar'] = [
                            {'kirpim': [px, py], 'eski': sd.nokta_olc(eski_im, px + kx, py + ky),
                             'yeni': sd.nokta_olc(T['baski'], px + kx, py + ky)}
                            for px, py in ((730, 174), (2113, 80), (2121, 175))]
            if gecti and T.get('baski') is not None:
                baski = T['baski']
                s['jpeg_kalite'] = kaydet(baski, cik / ad)
                with Image.open(cik / ad) as chk:
                    s['dogrulama'] = {'px': list(chk.size), 'dpi': [round(v) for v in chk.info.get('dpi', (0, 0))],
                                      'icc_srgb': chk.info.get('icc_profile') == SRGB,
                                      'MB': round((cik / ad).stat().st_size / 1e6, 2)}
                o = r.get('olcum') or {}
                kok = f'KONTROL_{gorunen(renk)}_{boy}'
                try:
                    ki, s['isim_kirpim_px'] = kirp(baski, o['isim_bant'], (150, 2250))
                    ks, s['slogan_kirpim_px'] = kirp(baski, o['tag_bant'], (250, 2150))
                    kaydet(ki, cik / f'{kok}_ISIM_100.jpg')
                    kaydet(ks, cik / f'{kok}_SLOGAN_100.jpg')
                except Exception as e:                            # noqa: BLE001
                    s['gecti'] = False
                    s['hata'] = f'kontrol kirpimi: {type(e).__name__}: {e}'
                goruntuler.append((f'{gorunen(renk)} {boy}', baski))
            rapor['dosyalar'].append(s)
            g = time.time() - T0
            ik, ek2 = s['isim_kalinti'], s.get('eski_dosya_isim_kalinti') or {}
            print(f"    sol_leke={s.get('sol_leke')} bildirilen={s.get('bildirilen_noktalar')}", flush=True)
            print(f"[{n}/{toplam}] {renk} {boy}: {'PASS' if gecti else 'FAIL'} kalan={s['kalan_kapilar']} "
                  f"olcek={s['olcek']} plate={s['plate_slogan_payi']} "
                  f"isim_kalinti yeni={'PASS' if ik.get('gecti') else 'FAIL'}({ik.get('kalinti_sayisi')}) "
                  f"eski={'-' if not ek2 else ('PASS' if ek2.get('gecti') else 'FAIL')}({ek2.get('kalinti_sayisi')}) "
                  f"hata={s['hata'] or ''} "
                  f"| gecen {g:.0f}s | kalan ~{g / n * (toplam - n):.0f}s | %{100 * n // toplam}", flush=True)
    hepsi = all(s['gecti'] for s in rapor['dosyalar']) and len(rapor['dosyalar']) == toplam
    # Kapi dogrulamasi (GIFT_9518, 29 Eyl): onaylanmayan onceki dosyalarda isim_kalinti FAIL
    # vermeli; PASS verirse kapi lekeyi goremiyor demektir -> hicbir sey yazilmaz.
    kor = [s['dosya'] for s in rapor['dosyalar']
           if (s.get('eski_dosya_isim_kalinti') or {}).get('gecti') is True]
    rapor['kapi_eski_dosyada_kor'] = kor
    if kor and ESKI_FAIL_BEKLENIR:
        hepsi = False
    # kontrol noktalari: yeni dosyada hicbiri esigi asmamali
    kalan_nokta = [(s['dosya'], q) for s in rapor['dosyalar']
                   for q in (s.get('kalinti_noktalari') or []) + (s.get('bildirilen_noktalar') or [])
                   if q['yeni'] >= sd.ISIM_KALINTI_ESIK]
    rapor['kalan_noktalar'] = kalan_nokta
    if kalan_nokta:
        hepsi = False
    rapor['hepsi_gecti'] = hepsi
    if hepsi:                                    # onizleme: 4 dosya yan yana, ayni yukseklik
        H = 1500
        parca = [(e, im.resize((round(im.width * H / im.height), H), Image.LANCZOS)) for e, im in goruntuler]
        W = sum(p.width for _, p in parca) + 40 * (len(parca) + 1)
        tuv = Image.new('RGB', (W, H + 110), (236, 236, 236))
        dr = ImageDraw.Draw(tuv); x0 = 40
        for e, p in parca:
            tuv.paste(p, (x0, 40)); dr.text((x0, H + 60), e, fill=(20, 20, 20)); x0 += p.width + 40
        kaydet(tuv, cik / f'ONIZLEME_{a.kod}.jpg')
    (cik / f'{a.kod}_KAPI_RAPORU.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    if not hepsi:
        sd.rc('copy', str(cik), f'{sd.SIP}/{a.kod}_TANI', '--include', '*.json', timeout=1800)
        print(json.dumps(rapor['dosyalar'], ensure_ascii=False, indent=1, default=str))
        raise SystemExit(f'{a.kod}: kapi FAIL - musteri klasorune yazilmadi')
    yedek = f"{a.hedef}/YEDEK_{time.strftime('%Y%m%d_%H%M', time.gmtime())}"
    for z in json.loads(sd.rc('lsjson', a.hedef, '--files-only')):   # eskiler YEDEK_ alt klasorune
        sd.rc('moveto', f"{a.hedef}/{z['Name']}", f"{yedek}/{z['Name']}", timeout=1800)
    rapor['yedek'] = yedek.split(':', 1)[1]
    (cik / f'{a.kod}_KAPI_RAPORU.json').write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str))
    sd.rc('copy', str(cik), a.hedef, timeout=1800)
    ust, ad_k = a.hedef.rsplit('/', 1)
    klasor = [z for z in json.loads(sd.rc('lsjson', ust, '--dirs-only')) if z['Name'] == ad_k]
    dosyalar = json.loads(sd.rc('lsjson', a.hedef, '--files-only'))
    oniz = [z for z in dosyalar if z['Name'] == f'ONIZLEME_{a.kod}.jpg']
    print(f"{a.kod}: 4/4 PASS | klasor {a.hedef.split(':', 1)[1]} id={klasor[0]['ID'] if klasor else '?'} "
          f"| onizleme id={oniz[0]['ID'] if oniz else '?'} | {len(dosyalar)} dosya", flush=True)
    print(json.dumps(rapor['dosyalar'], ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
