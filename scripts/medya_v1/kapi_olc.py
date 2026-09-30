#!/usr/bin/env python3
"""SALT OKUR kapi olcumu (30 Eyl 2026): verilen (cift, renk, boy, isimler, mesaj) siparislerini pod_uret ile
uretir, TUM kapilarin ayrintisini loga basar. Drive / PLATES / musteri YAZMA YOK.

--isler "CIFT:RENK:BOY[:ISIM1,ISIM2[:MESAJ]];..."   ISIM '=' ise kaynagin kendi burc adlari (kimlik render).
Kimlik render (onayli dosyanin kendi isimleri + slogani) onayli dosyayi yeniden uretmelidir; kapilarin bu
renderlardaki degeri yontemin gurultu tabanidir (WP esik kalibrasyonu).
"""
import argparse, json, sys, time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import siparis_dosyasi as sd                                     # noqa: E402

Image.MAX_IMAGE_PIXELS = None
VARSAYILAN_MESAJ = 'It Began With a Kiss in the Rain'
KAYNAK_MESAJ = 'Two Souls • One Bond'


def al(d, *ks):
    for k in ks:
        d = (d or {}).get(k) if isinstance(d, dict) else None
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--isler', default='')
    ap.add_argument('--tum', default='', help='RENK1,RENK2,..:BOY -> POD_PRINT\'teki tum ciftler (regresyon)')
    ap.add_argument('--parca', default='0/1', help='i/n: tum listenin i::n dilimi')
    ap.add_argument('--cikti', default='', help='sonuc JSONL dosyasi')
    ap.add_argument('--etiket', default='')
    a = ap.parse_args()
    sd.kisisel_hazirla()
    P_ed, P_blue = sd.EdisyonPoster(), sd.BluePoster()
    no, ciftler = sd.sayfa_no_tablosu()
    if a.tum:
        renkler, boy_ = a.tum.split(':')
        i, n_ = (int(v) for v in a.parca.split('/'))
        tum = [f'{c}:{r}:{boy_}' for c in ciftler for r in renkler.split(',')]
        isler = tum[i::n_]
    else:
        isler = [x.strip() for x in a.isler.split(';') if x.strip()]
    fo = open(a.cikti, 'w') if a.cikti else None
    T0 = time.time()
    for n, is_ in enumerate(isler, 1):
        p = is_.split(':')
        cift, renk, boy = p[0], p[1], p[2]
        if len(p) > 3 and p[3] == '=':
            isim = tuple(s for s in cift.split('_')); mesaj = KAYNAK_MESAJ; tur = 'kimlik'
        else:
            isim = tuple(p[3].split(',')) if len(p) > 3 else ('EMILY', 'JAMES')
            mesaj = p[4] if len(p) > 4 else VARSAYILAN_MESAJ; tur = 'siparis'
        r = {'etiket': a.etiket, 'cift': cift, 'renk': renk, 'boy': boy, 'tur': tur}
        try:
            x = sd.normalize({'cift': cift, 'renk': renk, 'boy': boy, 'urun': 'pod',
                              'isim1': isim[0], 'isim2': isim[1], 'mesaj': mesaj})
            x['receipt'] = f'OLC_{cift}_{renk}_{boy}_{tur}'
            x['sayfa'] = no[cift]
            yol = sd.pod_kaynak(cift, renk, boy)
            with Image.open(yol) as im:
                x['hedef_px'] = list(im.size)
            is_dir = sd.W / x['receipt']; is_dir.mkdir(parents=True, exist_ok=True)
            s = sd.pod_uret(x, yol.read_bytes(), P_blue, P_ed, is_dir)
            k = s.get('kapilar') or {}
            r.update({
                'durum': s.get('durum'), 'hata': s.get('hata'),
                'gecti': s.get('durum') == 'URETILDI' and bool(k) and sd.kapi_sonucu(k),
                'kalan': sorted(g for g, v in k.items() if v is False),
                'mesaj': {q: al(s, 'mesaj_kapisi', q) for q in ('dE', 'kontrast_orani', 'isim_rgb', 'mesaj_rgb', 'zemin_rgb')},
                'sembol': {y: {q: al(s, 'sembol_kapisi', y, q) for q in ('iou', 'fark', 'olcut', 'dx', 'dy')}
                           for y in ('sol', 'sag')},
                'temiz_ara': {q: al(s, 'temiz_ara_kapisi', q) for q in ('en_ort', 'en_tepe', 'kotu_blok', 'blok', 'ornek')},
                'kalinti': {q: al(s, 'kalinti_kapisi', q) for q in ('en_ort', 'en_tepe', 'kotu_blok')},
                'olcek': {q: al(s, 'olcek_kapisi', q) for q in ('konum_fark_px', 'kenar_fark_px', 'esik', 'fark', 'sebep', 'olcekli_deneme', 'yerlesim', 'ilk_yerlesim', 'k')},
                'leke': {q: al(s, 'leke_kapisi', q) for q in ('p99', 'en_kotu_blok_p99', 'en_kotu_blok_yeri')},
                'isim_kalinti': {q: al(s, 'isim_kalinti_kapisi', q) for q in ('kalinti_sayisi', 'kalintilar', 'esikler')},
                'isim_kenar': {q: al(s, 'isim_kenar_kapisi', q) for q in ('kesilen_harf_px', 'harf_murekkebi_koruma_icinde', 'guclu_esik')},
                'isim_bandi': {q: al(s, 'isim_bandi_temizligi', q) for q in ('kalinti_bileseni', 'degisen_px', 'satir', 'sutun')},
                'plate_slogan': al(s, 'plate_slogan_kapisi', 'glif_farkli_payi'),
            })
            yol.unlink(missing_ok=True)
        except BaseException as e:                                # noqa: BLE001
            r['durum'] = 'HATA'; r['hata'] = f'{type(e).__name__}: {str(e)[:200]}'
        g = time.time() - T0
        print('OLC', json.dumps(r, ensure_ascii=False, default=str), flush=True)
        if fo:
            fo.write(json.dumps(r, ensure_ascii=False, default=str) + '\n'); fo.flush()
        print(f"[{n}/{len(isler)}] {a.etiket} {cift} {renk} {boy} {r['tur']}: "
              f"{'PASS' if r.get('gecti') else 'FAIL'} kalan={r.get('kalan')} {r.get('hata') or ''} "
              f"| gecen {g:.0f}s | kalan ~{g / n * (len(isler) - n):.0f}s | %{100 * n // len(isler)}", flush=True)


if __name__ == '__main__':
    main()
