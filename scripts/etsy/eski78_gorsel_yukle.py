#!/usr/bin/env python3
"""ESKI 78 galeri cerceve temizligi: YENI KARTLARI YUKLER + RANK 6 SILER + ALT METIN. ETSY'YE YAZAR (Serdar onayi gerekir).
Girdi: Drive TEMP/ESKI78_GORSEL_20261017/<CIFT>/rNN.jpg + _QC.json (PASS) + _canli/<CIFT>/galeri.json (uretim anindaki canli galeri).
Ilan basina:
  on kosul: state active; canli galeri = uretimdeki galeri (18 gorsel, ayni id ve sira); dokunulan rank'ler (1-13) renk bagli degil;
            _QC.json PASS. Degilse o ilan icin DUR (yazma yok).
  yedek: tum gorseller + manifest (cl_galeri_degistir.yedek_al) -> Drive (ilk yedegin ustune yazilmaz).
  yukleme: rank 1, 2, 3, 5, 7, 8, 9, 10, 12, 13 sirayla uploadListingImage(rank, overwrite=true, alt_text);
           her yuklemeden sonra galeri okunur: o rank'te yeni id, toplam 18. overwrite eskiyi silmezse (19, eski id duruyor) eski silinir.
  silme: eski rank 6 gorseli (Four classic frames) deleteListingImage.
  geri okuma: 17 gorsel; sira = beklenen id listesi; alt metinler beklenen; renk baglari ayni; state/baslik/etiket/aciklama/envanter/
              video ayni; her yeni gorsel CDN'den indirilip yerel kartla NCC >= 0.999.
Ilk FAIL'de DUR. Tekrar kosu: rapor.json PASS olan ilan atlanir.
Kullanim: eski78_gorsel_yukle.py --kaynak DIR --out OUT --yedek-drive gdrive:... --confirm ESKI78_GORSEL [--ciftler ...] [--limit N]"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cl_galeri_degistir as G  # noqa: E402
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOTA_MIN = 10  # Serdar 15 Eki: Etsy kota tabani 10
YUKLE = [1, 2, 3, 5, 7, 8, 9, 10, 12, 13]
SIL = 6


def alt_metin(a, b):
    """Serdar 17 Eki onayli alt metinler (rank 6 duser). None = canli alt metin aynen."""
    return {1: f"Personalized {a} and {b} zodiac couple wall art, shown framed for display, frame not included",
            2: "Choose a digital file or an art print of the couple design",
            3: "Two zodiac signs united in one shared symbol, an original AstroLoveArt design",
            5: "Zodiac couple poster as an anniversary or wedding gift, frame not included",
            7: None,
            8: "Champagne Ivory print in a calm bedroom, frame not included",
            9: "Deep Black print above a desk, frame not included",
            10: "Pure White print in a dining room, frame not included",
            12: "Matte art paper detail of the zodiac couple print",
            13: "Order process: preview, approval, made to order printing and delivery"}


def log(m):
    print(m, flush=True)


def gri(b):
    im = Image.open(io.BytesIO(b) if isinstance(b, bytes) else b).convert("L")
    return np.asarray(im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)).astype(np.float32)


def ncc(a, b):
    if a.shape != b.shape:
        return -1.0
    a, b = a - a.mean(), b - b.mean(); return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))


def cdn_ncc(url, yerel):
    for k in range(3):
        try:
            r = requests.get(url, timeout=120); r.raise_for_status(); return round(ncc(gri(r.content), gri(yerel)), 5)
        except Exception:                                       # noqa: BLE001
            time.sleep(3 * (k + 1))
    return -1.0


def drive_kopya(yerel, hedef):
    if subprocess.run(["rclone", "lsf", hedef], capture_output=True, text=True).stdout.strip():
        hedef += time.strftime("_tekrar_%Y%m%d_%H%M%S", time.gmtime())
    r = subprocess.run(["rclone", "copy", str(yerel), hedef, "-q"], capture_output=True, text=True)
    c = subprocess.run(["rclone", "check", str(yerel), hedef, "--one-way", "-q"], capture_output=True, text=True)
    if r.returncode or c.returncode:
        raise SystemExit(f"HATA: yedek Drive'a yazilamadi ({hedef}). YAZMA YOK. DUR.")


def kota(api):
    try:
        if int(api.remaining) < KOTA_MIN:
            raise SystemExit(f"DUR: KOTA {api.remaining} < {KOTA_MIN}")
    except (TypeError, ValueError):
        pass


def bir_ilan(api, shop, lid, c, a, b, kay, out, yedek_drive):
    o = out / f"{lid}_{c}"; o.mkdir(parents=True, exist_ok=True)
    qc = json.loads((kay / c / "_QC.json").read_text())
    if not qc.get("PASS"):
        raise SystemExit(f"DUR {c}: uretim QC PASS degil")
    uretim = json.loads((kay / "_canli" / c / "galeri.json").read_text())
    u_ids = [x["listing_image_id"] for x in uretim["gorseller"]]
    g0 = G.galeri(api, lid)
    if [x.get("listing_image_id") for x in g0] != u_ids or len(u_ids) != 18:
        raise SystemExit(f"DUR {c}: canli galeri uretimden sonra degisti ya da 18 degil ({len(g0)})")
    man = G.yedek_al(api, shop, lid, o)
    if yedek_drive:
        drive_kopya(o / "yedek", f"{yedek_drive}/{lid}_{c}")
    kor0 = man["korunan"]
    if kor0["state"] != "active":
        raise SystemExit(f"DUR {c}: state {kor0['state']}")
    bag0 = sorted((v.get("value_id"), v.get("image_id")) for v in man["variation_images"])
    bagli = {i for _, i in bag0}
    dokun = {u_ids[r - 1] for r in YUKLE + [SIL]}
    if bagli & dokun:
        raise SystemExit(f"DUR {c}: dokunulacak gorsel renk bagli {sorted(bagli & dokun)}")
    alt0 = [x.get("alt_text") or "" for x in g0]
    AL = alt_metin(a, b)
    ids = list(u_ids); yeni_id = {}; yol = []
    for r in YUKLE:
        alt = AL[r] if AL[r] is not None else alt0[r - 1]
        p = kay / c / f"r{r:02d}.jpg"
        with open(p, "rb") as fh:
            y = api.post_file(f"/shops/{shop}/listings/{lid}/images", files={"image": (f"r{r:02d}.jpg", fh, "image/jpeg")},
                              data={"rank": str(r), "overwrite": "true", "alt_text": alt})
        kota(api)
        yid = (y or {}).get("listing_image_id")
        if not yid or yid in u_ids:
            raise SystemExit(f"DUR {c}: r{r} yukleme id {yid}")
        eski = ids[r - 1]; ids[r - 1] = yid; yeni_id[r] = yid
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == ids)
        gi = [x.get("listing_image_id") for x in g]
        if gi != ids:
            if len(gi) == 19 and eski in gi:                     # overwrite eskiyi silmedi
                G.gorsel_sil(api, shop, lid, eski); yol.append(f"r{r}: eski silindi")
                g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == ids)
                gi = [x.get("listing_image_id") for x in g]
            if gi != ids:
                raise SystemExit(f"DUR {c}: r{r} sonrasi galeri beklenmedik {gi}")
    # rank 6 sil
    G.gorsel_sil(api, shop, lid, u_ids[SIL - 1]); kota(api)
    bek = [i for i in ids if i != u_ids[SIL - 1]]
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == bek)
    sorun = []
    gi = [x.get("listing_image_id") for x in g]
    if gi != bek:
        sorun.append(f"sira/id {gi}")
    alt_bek = []
    for r in range(1, 19):
        if r == SIL:
            continue
        alt_bek.append(AL[r] if r in AL and AL[r] is not None else alt0[r - 1])
    alt_son = [x.get("alt_text") or "" for x in g]
    if alt_son != alt_bek:
        sorun.append("alt metin: " + "; ".join(f"r{i + 1} {s!r} != {e!r}" for i, (s, e) in enumerate(zip(alt_son, alt_bek)) if s != e)[:400])
    bag1 = sorted((v.get("value_id"), v.get("image_id")) for v in G.var_img(api, shop, lid))
    if bag1 != bag0:
        sorun.append("renk baglari")
    kor1 = G.korunanlar(api, shop, lid)
    for k in ("state", "title", "tags", "desc_sha", "inv_sha", "n_urun", "video_ids"):
        if kor1.get(k) != kor0.get(k):
            sorun.append(f"korunan {k}")
    url = {x.get("listing_image_id"): x.get("url_fullxfull") for x in g}
    nccs = {}
    for r, yid in yeni_id.items():
        nccs[r] = cdn_ncc(url.get(yid), kay / c / f"r{r:02d}.jpg")
        if nccs[r] < 0.999:
            sorun.append(f"r{r} NCC {nccs[r]}")
    rap = dict(cift=c, listing_id=lid, sonuc="PASS" if not sorun else "FAIL", sorun=sorun, yol=yol, gorsel=len(gi),
               silinen_r6=u_ids[SIL - 1], yeni_id=yeni_id, ncc=nccs, renk_bagi=len(bag1), kota=api.remaining)
    (o / "rapor.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
    return rap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", required=True); ap.add_argument("--out", required=True); ap.add_argument("--yedek-drive", default="")
    ap.add_argument("--confirm", default=""); ap.add_argument("--ciftler", default="HEPSI"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", default="data/pod/pod78_ids.csv")
    a = ap.parse_args()
    if a.confirm != "ESKI78_GORSEL":
        raise SystemExit("HATA: --confirm ESKI78_GORSEL gerekir.")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]; out = Path(a.out); out.mkdir(parents=True, exist_ok=True); kay = Path(a.kaynak)
    rows = list(csv.DictReader(open(a.ids)))
    if a.ciftler != "HEPSI":
        sec = a.ciftler.split(); rows = sorted((r for r in rows if r["cift"] in sec), key=lambda r: sec.index(r["cift"]))
    tamam = {p.parent.name.split("_", 1)[1] for p in out.glob("*/rapor.json") if json.loads(p.read_text())["sonuc"] == "PASS"}
    is_ = [r for r in rows if r["cift"] not in tamam]
    if a.limit:
        is_ = is_[:a.limit]
    log(f"onceki PASS (atlanir): {len(tamam)} | bu kosu: {len(is_)}")
    sonuc, t0 = [], time.time()
    for i, r in enumerate(is_, 1):
        try:
            rap = bir_ilan(api, shop, r["listing_id"].strip(), r["cift"], r["a"], r["b"], kay, out, a.yedek_drive)
        except SystemExit as e:
            rap = dict(cift=r["cift"], listing_id=r["listing_id"], sonuc="DUR", sorun=[str(e.code)[:400]])
            (out / f"{r['listing_id']}_{r['cift']}").mkdir(parents=True, exist_ok=True)
            (out / f"{r['listing_id']}_{r['cift']}" / "rapor_dur.json").write_text(json.dumps(rap, indent=1, ensure_ascii=False))
        sonuc.append(rap); g = time.time() - t0
        log(f"[{i}/{len(is_)}] {r['cift']} {rap['sonuc']} {rap['sorun'] or ''} | gecen {g / 60:.1f} dk | kalan ~{g / i * (len(is_) - i) / 60:.1f} dk | "
            f"%{100 * i // len(is_)} | kota {api.remaining}")
        if rap["sonuc"] != "PASS":
            break
    n = sum(1 for r in sonuc if r["sonuc"] == "PASS")
    print(f"::warning::ESKI78 GORSEL YUKLE PASS {n}/{len(sonuc)} (onceki {len(tamam)}) | "
          + "; ".join(f"{r['cift']} {r['sonuc']} {r['sorun']}" for r in sonuc if r["sonuc"] != "PASS")[:800] + f" | kota {api.remaining}")
    return 0 if sonuc and n == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
