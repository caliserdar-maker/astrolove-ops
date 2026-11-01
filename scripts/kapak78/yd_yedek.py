#!/usr/bin/env python3
"""YD (1st Anniversary) 78 ilan galeri yedegi (plan v3 adim 5; Merkez 27 Eki). ETSY API YOK, Etsy'ye yazma yok, kilit yok.
Girdi: TEMP/YD_ENVANTER_20261026/HAM/<listing_id>.json (yd_envanter_oku.py ciktisi; images = Etsy gorsel kayitlari, url_fullxfull,
full_width / full_height; variation_images = Style bagi) + data/pod/yd78_ids.csv (78 ilan).
Islem (yedek_mb_kontrol.py A kismiyla ayni yontem; paylasilan dosyaya dokunmamak icin buraya kopyalandi, Merkez 27 Eki):
<out>/<listing_id>_<CIFT>/r<rank>_<image_id>.jpg + GALERI.json (gorseller + baglar aynen) + <out>/OZET.md (ilan basina 13 dosya, boyut = JSON; JSON uzun kenari 3000'i asarsa CDN ayni oranda 3000'e kucultur) + <out>/BAGLAR.csv (listing_id, cift, stil, value_id, image_id,
rank). Indirme etsystatic CDN'den (Etsy API degil).
Kapilar: yd78 listesindeki her ilanin HAM dosyasi var ve listing_id ayni; yoksa o ilan FAIL (OZET'e yazilir). Cikis: 78/78 PASS ise 0.
VIDEO (Serdar 1 Kas 6d, inceleme madde 11): HAM videos[].video_url -> <out>/<listing_id>_<CIFT>/v_<video_id>.mp4 (MP4 imzasi 'ftyp', boyut > 0)
+ <out>/VIDEO_OZET.csv (listing_id, cift, video_id, boyut, durum, not). yd_kapak_yukle tek geciste eski video bu dosya yedek listesinde
yoksa silinmez. Video FAIL'i OZET.md galeri satirini degistirmez (liste kapisi ayni), cikis 1 verir."""
import argparse
import csv
import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image

BEKLENEN = 13
CDN_UST = 3000     # etsystatic url_fullxfull uzun kenar ust siniri (olcum: kosu 40491659087, 78 ilanin rank 2-8'i, 546/546
                   # JSON 3200x2400 -> CDN 3000x2250; rank 1 ve 9-13 JSON ile ayni)


def boyut_ok(bt, w, h):
    """CDN dosyasi JSON boyutunda ya da JSON > 3000 ise ayni oranda uzun kenar 3000 (+-1 px)"""
    if not isinstance(w, int) or not isinstance(h, int):
        return False
    if bt == (w, h):
        return True
    if max(w, h) <= CDN_UST:
        return False
    o = CDN_UST / max(w, h)
    return max(bt) == CDN_UST and abs(bt[0] - w * o) <= 1 and abs(bt[1] - h * o) <= 1


def indir(u, p, tekrar=4):
    for i in range(tekrar):
        try:
            r = requests.get(u, timeout=90); r.raise_for_status(); p.write_bytes(r.content); return None
        except Exception as e:  # noqa: BLE001
            if i == tekrar - 1:
                return f"{type(e).__name__}: {str(e)[:80]}"
            time.sleep(2 ** i)


def video_yedek(ilanlar, kok):
    """6d: ilan videolari (CDN, Etsy API degil). -> FAIL sayisi"""
    satir = []
    for k in ilanlar:
        d = kok / f"{k['listing_id']}_{k['cift']}"; d.mkdir(parents=True, exist_ok=True)
        for v in k.get("videos") or []:
            p = d / f"v_{v.get('video_id')}.mp4"
            h = indir(v.get("video_url") or "", p) if v.get("video_url") else "video_url yok"
            b = p.read_bytes()[:12] if p.exists() else b""
            if not h and (len(b) < 8 or b[4:8] != b"ftyp"):
                h = "MP4 imzasi yok (ftyp)"
            if h and p.exists():
                p.unlink()        # inceleme 1 Kas madde 1: gecersiz dosya yedek klasorunde kalip "yedek var" sanilmasin
            satir.append([k["listing_id"], k["cift"], v.get("video_id"), p.stat().st_size if p.exists() else 0, "FAIL" if h else "PASS", h or ""])
    with open(kok / "VIDEO_OZET.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "video_id", "boyut", "durum", "not"]); w.writerows(satir)
    fail = sum(1 for x in satir if x[4] != "PASS")
    print(f"VIDEO YEDEK: {len(satir) - fail}/{len(satir)} PASS")
    return fail


def yedek(ilanlar, kok, beklenen=BEKLENEN, baslik="YD 78 galeri yedegi (plan v3 adim 5)"):
    isler, satir = [], []
    for k in ilanlar:
        d = kok / f"{k['listing_id']}_{k['cift']}"; d.mkdir(parents=True, exist_ok=True)
        (d / "GALERI.json").write_text(json.dumps(dict(gorseller=k["gorseller"], baglar=k["baglar"]), ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        for g in k["gorseller"]:
            isler.append((g["url_fullxfull"], d / f"r{g['rank']}_{g['listing_image_id']}.jpg"))
    t0, hata = time.time(), {}
    with ThreadPoolExecutor(8) as ex:
        for n, (p, h) in enumerate(zip([i[1] for i in isler], ex.map(lambda a: indir(*a), isler)), 1):
            if h:
                hata[str(p)] = h
            if n % 100 == 0 or n == len(isler):
                g = time.time() - t0
                print(f"YEDEK {n}/{len(isler)} %{100 * n // len(isler)} gecen {g:.0f} sn kalan {g / n * (len(isler) - n):.0f} sn", flush=True)
    toplam = kucuk_top = 0
    for k in ilanlar:
        d = kok / f"{k['listing_id']}_{k['cift']}"
        neden = []
        if len(k["gorseller"]) != beklenen:
            neden.append(f"JSON'da {len(k['gorseller'])} gorsel (beklenen {beklenen})")
        say = kucuk = 0
        for g in k["gorseller"]:
            p = d / f"r{g['rank']}_{g['listing_image_id']}.jpg"
            if str(p) in hata or not p.exists():
                neden.append(f"r{g['rank']} indirilemedi ({hata.get(str(p), 'yok')})"); continue
            try:
                with Image.open(p) as im:
                    bt = im.size; im.load()            # inceleme 27 Eki: yarim inmis dosya da yakalansin
            except Exception:  # noqa: BLE001
                neden.append(f"r{g['rank']} okunamadi"); continue
            say += 1
            if bt != (g["full_width"], g["full_height"]):
                kucuk += 1
            if not boyut_ok(bt, g["full_width"], g["full_height"]):
                neden.append(f"r{g['rank']} boyut {bt[0]}x{bt[1]} != {g['full_width']}x{g['full_height']}")
        toplam += say; kucuk_top += kucuk
        satir.append([k["listing_id"], k["cift"], say, "PASS" if not neden and say == beklenen else "FAIL", "; ".join(neden), kucuk])
    gecti = sum(1 for s in satir if s[3] == "PASS")
    with open(kok / "OZET.md", "w", encoding="utf-8") as f:
        f.write(f"# {baslik}\n\nilan PASS {gecti}/{len(satir)} | dosya {toplam} (beklenen {beklenen * len(satir)}) | CDN kucultmesi "
                f"{kucuk_top} dosya (JSON > 3000 px; yedek bu dosyalarda 3000 px kopya)\n\n"
                "| listing_id | cift | dosya | durum | not | cdn_kucuk |\n|---|---|---|---|---|---|\n")
        f.writelines(f"| {' | '.join(map(str, s))} |\n" for s in satir)
    print(f"YEDEK OZET: ilan PASS {gecti}/{len(satir)} | dosya {toplam} | CDN kucultmesi {kucuk_top}")
    return gecti, len(satir), toplam


def ilanlar_oku(ham_dir, ciftler):
    rows = [r for r in csv.DictReader(open(ciftler, encoding="utf-8-sig")) if r.get("listing_id")]
    ilan, eksik = [], []
    for r in rows:
        p = pathlib.Path(ham_dir) / f"{r['listing_id']}.json"
        if not p.exists():
            eksik.append((r["listing_id"], r["cift"], "HAM dosyasi yok")); continue
        h = json.loads(p.read_text(encoding="utf-8"))
        if str((h.get("listing") or {}).get("listing_id")) != r["listing_id"]:
            eksik.append((r["listing_id"], r["cift"], "HAM listing_id farkli")); continue
        g = sorted(h.get("images") or [], key=lambda x: x.get("rank") or 0)
        ilan.append(dict(listing_id=r["listing_id"], cift=r["cift"], gorseller=g, baglar=h.get("variation_images") or [], videos=h.get("videos") or []))
    return rows, ilan, eksik


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ham-dir", required=True); ap.add_argument("--ciftler", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows, ilan, eksik = ilanlar_oku(a.ham_dir, a.ciftler)
    gecti, n, dosya = yedek(ilan, out) if ilan else (0, 0, 0)
    vfail = video_yedek(ilan, out) if ilan else 0
    if eksik:
        with open(out / "OZET.md", "a", encoding="utf-8") as f:
            f.writelines(f"| {lid} | {c} | 0 | FAIL | {neden} |\n" for lid, c, neden in eksik)
    with open(out / "BAGLAR.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "cift", "stil", "value_id", "image_id", "rank"])
        for k in ilan:
            rk = {x.get("listing_image_id"): x.get("rank") for x in k["gorseller"]}
            for b in k["baglar"]:
                w.writerow([k["listing_id"], k["cift"], b.get("value"), b.get("value_id"), b.get("image_id"), rk.get(b.get("image_id"), "")])
    print(f"YD YEDEK: ilan PASS {gecti}/{len(rows)} | dosya {dosya} (beklenen {BEKLENEN * len(rows)}) | HAM eksik {len(eksik)}")
    return 0 if gecti == len(rows) and not eksik and not vfail else 1


if __name__ == "__main__":
    sys.exit(main())
