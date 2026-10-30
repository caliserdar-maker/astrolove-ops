#!/usr/bin/env python3
"""Galeri v11 B1 yedek, KILITSIZ indirme asamasi (Merkez 29 Eki). ETSY API YOK (yalniz etsystatic CDN; Etsy kilidi gerekmez).
Girdi --in: galeri_v11_yedek_oku.py ciktisi (<ilan>_<CIFT>/GALERI.json, OKUMA.csv; Drive TEMP/POSTER_GALERI_V11_YEDEK/<damga>).
Ilan basina: her gorsel url_fullxfull -> r<rank>_<listing_image_id>.jpg (boyut = JSON full_width x full_height), her video
video_url -> video_<video_id>.mp4 (bayt > 0). OZET.md galeri_v10_liste.ozet_oku bicimi: | listing_id | cift | dosya | durum | not |
(dosya = gorsel dosyasi sayisi; PASS = profilin gorsel sayisi kadar dosya, rank 1..n, + video dosyalari tam). ETA sayaci.
Profil (#60, 30 Eki; 9 gorsel varsayimi kaldirildi): --profil v10 | v11 | v11b | v11ci (galeri_v11_yedek_oku.PROFILLER: v10 9, v11 10,
v11b 10, v11ci 11 gorsel). --profil verilmezse GALERI.json "profil" alani (yedek-oku yazar) kullanilir; alan yok / ilanlar arasi farkli /
--profil ile celisirse DUR (cikis 2, indirme yok). v11b_or_ci (inceleme 30 Eki madde 5): ilan basina beklenen sayi (11 gorselli ilan
v11ci 11, digerleri v11b 10); --profil v11b_or_ci, v11b / v11ci / v11b_or_ci okumalariyla celismez. Cikis 2 = profil / girdi hatasi (is akisi
bunu yutmaz), 1 = ozet PASS degil (78/78 degil).
Cikti ayni klasore (--in) yazilir; is akisi yalniz yeni dosyalari Drive'a --immutable ile ekler. Cikis 0 = 78/78 PASS."""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
from galeri_v11_yedek_oku import BIRLESIK, PROFIL_ADLARI, PROFILLER, ilan_profili  # noqa: E402  (tek kaynak; ust duzey yalniz stdlib)

CDN = ("https://i.etsystatic.com/", "https://v.etsystatic.com/")


def indir(u, p, tekrar=4):
    if not str(u or "").startswith(CDN):
        return f"CDN disi adres ({str(u)[:40]})"
    for i in range(tekrar):
        try:
            r = requests.get(u, timeout=120); r.raise_for_status(); p.write_bytes(r.content); return None
        except Exception as e:  # noqa: BLE001
            if i == tekrar - 1:
                return f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(2 ** i)


def isler_kur(kok):
    ilanlar, isler = [], []
    for gj in sorted(kok.glob("*_*/GALERI.json")):
        j = json.loads(gj.read_text(encoding="utf-8")); d = gj.parent
        ilanlar.append((d, j))
        isler += [(g["url_fullxfull"], d / f"r{g['rank']}_{g['listing_image_id']}.jpg") for g in j.get("gorseller") or []]
        isler += [(v.get("video_url"), d / f"video_{v['video_id']}.mp4") for v in j.get("videolar") or []]
    return ilanlar, isler


def profil_sec(arg, jler):
    """(profil, hata). arg bos ise GALERI.json 'profil' alanlari tek ve gecerli olmali; arg verilmisse alanla celismemeli."""
    kayit = {j.get("profil") for j in jler}
    if arg:
        diger = sorted(map(str, kayit - {arg, None, *BIRLESIK.get(arg, ())}))
        return (arg, None) if not diger else (None, f"--profil {arg} ama GALERI.json profil {diger}")
    if len(kayit) != 1 or None in kayit:
        return None, f"--profil yok ve GALERI.json profil alani tek degil / eksik ({sorted(map(str, kayit))})"
    p = kayit.pop()
    return (p, None) if p in PROFIL_ADLARI else (None, f"GALERI.json profil {p!r} bilinmiyor")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="kok", required=True); ap.add_argument("--is", dest="is_", type=int, default=8)
    ap.add_argument("--profil", default="", choices=["", *PROFIL_ADLARI], help="bos = GALERI.json 'profil' alani")
    a = ap.parse_args(argv)
    kok = Path(a.kok)
    ilanlar, isler = isler_kur(kok)
    if not ilanlar:
        print("::error::GALERI.json yok"); return 2
    profil, hata_p = profil_sec(a.profil, [j for _, j in ilanlar])
    if hata_p:
        print(f"::error::profil: {hata_p}"); return 2
    def beklenen(j):
        return PROFILLER[ilan_profili(profil, len(j.get("gorseller") or []))]["gorsel"]
    print(f"profil {profil}: ilan basina " + (f"{PROFILLER[profil]['gorsel']} gorsel" if profil in PROFILLER else
                                              " / ".join(f"{x} {PROFILLER[x]['gorsel']}" for x in BIRLESIK[profil])), flush=True)
    t0, hata = time.time(), {}
    with ThreadPoolExecutor(a.is_) as ex:
        for n, ((_, p), h) in enumerate(zip(isler, ex.map(lambda x: indir(*x), isler)), 1):
            if h:
                hata[str(p)] = h
            if n % 50 == 0 or n == len(isler):
                g = time.time() - t0
                print(f"INDIR {n}/{len(isler)} %{100 * n // len(isler)} gecen {g:.0f} sn kalan {g / n * (len(isler) - n):.0f} sn", flush=True)
    satir, top_bek = [], 0
    for d, j in ilanlar:
        neden, say = [], 0
        g = j.get("gorseller") or []
        BEKLENEN = beklenen(j)
        if len(g) != BEKLENEN or sorted(x.get("rank") for x in g) != list(range(1, BEKLENEN + 1)):
            neden.append(f"JSON'da {len(g)} gorsel / rank {sorted(x.get('rank') for x in g)} (beklenen {BEKLENEN}, 1..{BEKLENEN})")
        for x in g:
            p = d / f"r{x['rank']}_{x['listing_image_id']}.jpg"
            if str(p) in hata or not p.exists():
                neden.append(f"r{x['rank']} indirilemedi ({hata.get(str(p), 'yok')})"); continue
            try:
                with Image.open(p) as im:
                    bt = im.size
            except Exception:  # noqa: BLE001
                neden.append(f"r{x['rank']} okunamadi"); continue
            if bt != (x["full_width"], x["full_height"]):
                neden.append(f"r{x['rank']} boyut {bt[0]}x{bt[1]} != {x['full_width']}x{x['full_height']}"); continue
            say += 1
        for v in j.get("videolar") or []:
            p = d / f"video_{v['video_id']}.mp4"
            if str(p) in hata or not p.exists() or p.stat().st_size == 0:
                neden.append(f"video {v['video_id']} indirilemedi ({hata.get(str(p), 'yok')})")
        satir.append([j["listing_id"], j["cift"], say, "PASS" if not neden and say == BEKLENEN else "FAIL", "; ".join(neden)])
        top_bek += BEKLENEN
    gecti = sum(1 for s in satir if s[3] == "PASS")
    with open(kok / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# Poster 78 galeri v11 yedegi (dosyalar, profil {profil})\n\nilan PASS {gecti}/{len(satir)} | gorsel dosyasi {sum(s[2] for s in satir)} "
                f"(beklenen {top_bek}) | indirme hatasi {len(hata)}\n\n"
                "| listing_id | cift | dosya | durum | not |\n|---|---|---|---|---|\n")
        f.writelines(f"| {' | '.join(map(str, s))} |\n" for s in satir)
    print(f"YEDEK OZET: ilan PASS {gecti}/{len(satir)} | hata {len(hata)}", flush=True)
    return 0 if gecti == len(satir) == 78 else 1


if __name__ == "__main__":
    sys.exit(main())
