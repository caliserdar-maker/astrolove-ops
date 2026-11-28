"""D paftalari: her galeri gorseli icin ESKI (sol) / YENI (sag) tam gorsel (genislik 1600) ve her poster kutusu icin 1:1 yakin
kirpinti (ust = eski, alt = yeni; sembol bandi ve yazi bandi ayri). Kutusuz gorselde (r10 / r11) Canva baslik bolgesi 1:1.
Etiket yazisi yok (font bagimliligi yok); dosya adi icerigi soyler. Kullanim:
  python pafta.py --eski DIR --yeni DIR --is is.json --cikti DIR
"""
import argparse, json, os
from PIL import Image

BASLIK = (900, 300, 2100, 470)          # degistir.py BASLIK_BOLGE ile ayni
ARA = 16


def yan_yana(a, b, gen=1600):
    w = (gen - ARA) // 2
    h = round(a.height * w / a.width)
    P = Image.new('RGB', (gen, h), 'white')
    P.paste(a.resize((w, h), Image.LANCZOS), (0, 0)); P.paste(b.resize((w, h), Image.LANCZOS), (w + ARA, 0))
    return P


def ust_alt(a, b):
    P = Image.new('RGB', (a.width, a.height * 2 + ARA), 'white')
    P.paste(a, (0, 0)); P.paste(b, (0, a.height + ARA))
    return P


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--eski', required=True); ap.add_argument('--yeni', required=True)
    ap.add_argument('--is', dest='is_json', required=True); ap.add_argument('--cikti', required=True)
    a = ap.parse_args()
    os.makedirs(a.cikti, exist_ok=True)
    yaz = []
    for f, kutular in json.load(open(a.is_json)).items():
        e = Image.open(os.path.join(a.eski, f)).convert('RGB')
        y = Image.open(os.path.join(a.yeni, f.replace('.jpg', '_YENI_TUM_ALTIN.jpg'))).convert('RGB')
        k = f[:-4]
        yol = os.path.join(a.cikti, f'PAFTA_{k}_eski_sol_yeni_sag.jpg')
        yan_yana(e, y).save(yol, quality=90); yaz.append(yol)
        if not kutular:
            yol = os.path.join(a.cikti, f'YAKIN_{k}_baslik_eski_ust_yeni_alt.jpg')
            ust_alt(e.crop(BASLIK), y.crop(BASLIK)).save(yol, quality=92); yaz.append(yol)
        for i, (kt, _z) in enumerate(kutular):
            x0, y0, x1, y1 = kt
            h = y1 - y0
            for ad, (p0, p1) in {'sembol': (0.10, 0.62), 'yazi': (0.62, 0.95)}.items():
                b = (x0, y0 + int(p0 * h), x1, y0 + int(p1 * h))
                yol = os.path.join(a.cikti, f'YAKIN_{k}_k{i + 1}_{ad}_eski_ust_yeni_alt.jpg')
                ust_alt(e.crop(b), y.crop(b)).save(yol, quality=92); yaz.append(yol)
    for p in yaz:
        print('PAFTA', os.path.basename(p), Image.open(p).size)


if __name__ == '__main__':
    main()
