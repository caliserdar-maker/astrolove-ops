#!/usr/bin/env python3
"""
GALERI YENILEME (3 ILANLIK ORNEK) - 4 Eyl 2026 Mo gorevi.

ETSY'YE YAZAR. Yaptigi tek sey ilanin 6 GALERI GORSELINI yenilemek ve
mevcut VIDEOYU silmektir. ZIP/PDF dosyalarina, fiyata, metne, state'e
DOKUNMAZ; yayinlama (state=active) cagrisi YOKTUR.

Sira (Mo kurali): once yukle, sonra sil. Ters yapilirsa ilan gorselsiz kalir.
Etsy ilan basina en fazla 10 gorsel tutar; 6 eski + 6 yeni = 12 sigmaz, bu
yuzden 3'er parca halinde yurutulur:

    6 eski -> +3 yeni (9) -> -3 eski (6) -> +3 yeni (9) -> -3 eski (6)

Yeni gorseller her turda mevcut listenin SONUNA (rank = mevcut+1) eklenir;
eskiler bastan silindiginde kalanlar kilitli sirayi korur:
    SET01 -> SET03 -> SET04 -> SET06 -> SET07 -> SET10Y

Her yazmadan sonra kararlilik beklenir (iki ardisik okuma ayni). Ilan bitince
geri okuma: gorsel 6, video 0, dosya 5 ve sira dogru. Sira, Etsy'nin donen
gorsel URL'si indirilip Drive'daki kaynakla piksel duzeyinde karsilastirilarak
dogrulanir - ad degil, ICERIK eslesmesi.

Ilk ilan pilottur; pilotta yukleme hata verirse kosu DURUR, digerlerine
gecilmez. Herhangi bir ilanda geri okuma tutmazsa yine DURULUR.

Varsayilan DRY-RUN: --apply verilmeden hicbir yazma cagrisi yapilmaz.
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_media_upload import GALLERY_ORDER, mock_name  # noqa: E402

CHUNK = 3               # tur basina yuklenecek/silinecek gorsel
IMG_LIMIT = 10          # Etsy ilan basina gorsel siniri
READBACK_WAIT = 10
READBACK_TRIES = 4
QUOTA_STOP = 500
PIX_MAD_MAX = 6.0       # Etsy yeniden kodladigi icin bayt esitligi beklenmez


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Gal:
    def __init__(self, api, shop, apply_):
        self.api, self.shop, self.apply = api, shop, apply_

    def images(self, lid):
        r = self.api.get(f"/listings/{lid}/images", ok404=True) or {}
        return sorted(((x.get("rank") or 0, x.get("listing_image_id"),
                        x.get("full_width"), x.get("full_height"),
                        x.get("url_fullxfull") or "")
                       for x in r.get("results", [])), key=lambda t: t[0])

    def videos(self, lid):
        r = self.api.get(f"/listings/{lid}/videos", ok404=True) or {}
        return [v.get("video_id") for v in r.get("results", [])]

    def files(self, lid):
        r = self.api.get(f"/shops/{self.shop}/listings/{lid}/files", ok404=True) or {}
        return [f.get("listing_file_id") for f in r.get("results", [])]

    def state(self, lid):
        return (self.api.get(f"/listings/{lid}", ok404=True) or {}).get("state", "?")

    def stable(self, fn, lid, want=None):
        """Iki ardisik okuma ayni (ve want saglanmis) olana kadar bekler."""
        prev = None
        for _ in range(READBACK_TRIES):
            time.sleep(READBACK_WAIT)
            cur = fn(lid)
            if prev is not None and cur == prev and (want is None or want(cur)):
                return cur
            prev = cur
        return prev

    def upload_image(self, lid, path, rank):
        with open(path, "rb") as fh:
            r = self.api.post_file(f"/shops/{self.shop}/listings/{lid}/images",
                                   files={"image": (Path(path).name, fh, "image/jpeg")},
                                   data={"rank": str(rank)})
        return r.get("listing_image_id")

    def delete_image(self, lid, image_id):
        self.api.delete(f"/shops/{self.shop}/listings/{lid}/images/{image_id}")

    def delete_video(self, lid, video_id):
        self.api.delete(f"/shops/{self.shop}/listings/{lid}/videos/{video_id}")


# ------------------------------------------------------------------ karsilastirma
def fetch(url, tries=3):
    for k in range(tries):
        try:
            r = requests.get(url, timeout=90)
            if r.status_code == 200:
                return r.content
        except requests.RequestException:
            pass
        time.sleep(2 * (k + 1))
    return None


def compare(url, src_path):
    """Etsy'den donen gorseli kaynakla piksel duzeyinde karsilastirir.
    Etsy yeniden kodlar/olceklendirir; bayt esitligi beklenmez. Olcut:
    ayni olcude ise dogrudan, degilse kaynak Etsy olcusune INTER_AREA ile
    indirilip ortalama mutlak fark."""
    data = fetch(url)
    if data is None:
        return dict(sonuc="INDIRILEMEDI", detay=url[:120])
    a = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    b = cv2.imread(str(src_path), cv2.IMREAD_COLOR)
    if a is None or b is None:
        return dict(sonuc="OKUNAMADI", detay="")
    ah, aw = a.shape[:2]
    bh, bw = b.shape[:2]
    olcek = "ayni" if (aw, ah) == (bw, bh) else f"kaynak {bw}x{bh} -> etsy {aw}x{ah}"
    if (aw, ah) != (bw, bh):
        b = cv2.resize(b, (aw, ah), interpolation=cv2.INTER_AREA)
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))
    mad, p99 = float(d.mean()), float(np.percentile(d, 99))
    return dict(sonuc="ESLESIYOR" if mad <= PIX_MAD_MAX else "FARKLI",
                etsy_olcu=f"{aw}x{ah}", olcek=olcek,
                fark_ort=round(mad, 3), fark_p99=round(p99, 1))


# ------------------------------------------------------------------ ilan islemi
def do_listing(g, pair, lid, mock_dir, rapor):
    up = pair.upper()
    imgs = [Path(mock_dir) / up / mock_name(s, pair) for s in GALLERY_ORDER]
    eksik = [p.name for p in imgs if not p.exists()]
    if eksik:
        return "FAIL", f"eksik kaynak gorsel: {eksik}"

    st = g.state(lid)
    before_i, before_v, before_f = g.images(lid), g.videos(lid), g.files(lid)
    log(f"  once: gorsel {len(before_i)}, video {len(before_v)}, dosya {len(before_f)}, state {st}")
    if not g.apply:
        return "DRY", (f"plan: {len(before_v)} video silinecek; "
                       f"{len(before_i)} eski gorsel {len(imgs)} yenisiyle "
                       f"{CHUNK}'er parca halinde degistirilecek; dosyalara dokunulmayacak")

    # --- 1) video sil (kapsam disi birakildi)
    for vid in before_v:
        log(f"  video siliniyor: {vid}")
        g.delete_video(lid, vid)
    if before_v:
        vs = g.stable(g.videos, lid, want=lambda c: len(c) == 0)
        if vs:
            return "FAIL", f"video silinmedi, kalan {len(vs)}"

    # --- 2) gorseller: parca parca once yukle sonra sil
    old_ids = [i[1] for i in before_i]
    cur = before_i
    ni = oi = 0
    while ni < len(imgs):
        parca = imgs[ni:ni + CHUNK]
        base = len(cur)
        if base + len(parca) > IMG_LIMIT:
            return "FAIL", f"gorsel siniri asilir: {base}+{len(parca)} > {IMG_LIMIT}"
        for j, p in enumerate(parca):
            r = base + 1 + j
            log(f"  yukleniyor rank {r}: {p.name}")
            g.upload_image(lid, p, r)
        cur = g.stable(g.images, lid, want=lambda c: len(c) == base + len(parca))
        if len(cur) != base + len(parca):
            return "FAIL", f"yukleme sonrasi gorsel {len(cur)}, beklenen {base + len(parca)}"
        son = (ni + CHUNK >= len(imgs))
        n_del = (len(old_ids) - oi) if son else len(parca)
        for oid in old_ids[oi:oi + n_del]:
            log(f"  eski gorsel siliniyor: {oid}")
            g.delete_image(lid, oid)
        oi += n_del
        hedef = base + len(parca) - n_del
        cur = g.stable(g.images, lid, want=lambda c: len(c) == hedef)
        if len(cur) != hedef:
            return "FAIL", f"silme sonrasi gorsel {len(cur)}, beklenen {hedef}"
        ni += len(parca)

    # --- 3) geri okuma
    after_i, after_v, after_f = g.images(lid), g.videos(lid), g.files(lid)
    det = []
    if len(after_i) != len(imgs):
        det.append(f"gorsel {len(after_i)} (beklenen {len(imgs)})")
    if len(after_v) != 0:
        det.append(f"video {len(after_v)} (beklenen 0)")
    if len(after_f) != 5:
        det.append(f"dosya {len(after_f)} (beklenen 5)")

    # --- 4) sira + icerik: her rank'i kaynagiyla piksel duzeyinde karsilastir
    for k, (rank, iid, w, h, url) in enumerate(after_i):
        src = imgs[k] if k < len(imgs) else None
        c = compare(url, src) if (url and src) else dict(sonuc="URL_YOK")
        c.update(pair=pair, listing_id=lid, rank=rank, sahne=GALLERY_ORDER[k] if k < len(GALLERY_ORDER) else "?",
                 kaynak=src.name if src else "", image_id=iid)
        rapor.append(c)
        log(f"  rank {rank} {c['sahne']}: {c['sonuc']} "
            + (f"fark ort {c.get('fark_ort')} p99 {c.get('fark_p99')} "
               f"({c.get('olcek')})" if "fark_ort" in c else str(c.get('detay', ''))))
        if c["sonuc"] != "ESLESIYOR":
            det.append(f"rank {rank} {c['sahne']}: {c['sonuc']}")
    return ("PASS" if not det else "FAIL"), "; ".join(det)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listings", required=True, help="cift:listing_id virgullu, ILK sirada pilot")
    ap.add_argument("--mock-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cmp-out", default="")
    ap.add_argument("--apply", action="store_true", help="yazma cagrilarini gercekten yap")
    a = ap.parse_args()

    hedefler = []
    for item in a.listings.split(","):
        item = item.strip()
        if not item:
            continue
        pair, lid = item.split(":", 1)
        hedefler.append((pair.strip(), lid.strip()))
    if not hedefler:
        raise SystemExit("HATA: --listings bos")

    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    g = Gal(api, os.environ.get("ETSY_SHOP_ID", ""), a.apply)
    log(f"{'UYGULA' if a.apply else 'DRY-RUN'} | {len(hedefler)} ilan | ilk ilan pilot")

    rows, rapor = [], []
    t0 = time.time()
    durdu = ""
    for i, (pair, lid) in enumerate(hedefler):
        log(f"\n[{i+1}/{len(hedefler)}] {pair} {lid}")
        try:
            status, detail = do_listing(g, pair, lid, a.mock_dir, rapor)
        except SystemExit as e:                      # API hatasi: temiz dur
            status, detail = "FAIL", str(e)[:300]
        rows.append([pair, lid, status, utc(), detail, api.remaining])
        el = time.time() - t0
        log(f"[{i+1}/{len(hedefler)}] {pair}: {status}" + (f" | {detail}" if detail else "")
            + f" | kota {api.remaining} | gecen {el/60:.1f} dk "
            f"kalan {el/(i+1)*(len(hedefler)-i-1)/60:.1f} dk %{100*(i+1)/len(hedefler):.0f}")
        if status == "FAIL":
            durdu = (f"{pair} ({lid}) FAIL -> kalan {len(hedefler)-i-1} ilana GECILMEDI"
                     + (" [PILOT]" if i == 0 else ""))
            log(f"DURDU: {durdu}")
            break
        if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < QUOTA_STOP:
            durdu = f"kota {api.remaining} < {QUOTA_STOP}"
            log(f"DURDU: {durdu}")
            break

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pair", "listing_id", "status", "ts_utc", "detail", "kota_kalan"])
        w.writerows(rows)
    if a.cmp_out and rapor:
        cols = list(dict.fromkeys(k for r in rapor for k in r))
        with open(a.cmp_out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rapor:
                w.writerow(r)

    n_pass = sum(1 for r in rows if r[2] == "PASS")
    lines = [f"## galeri yenileme ({'uygulandi' if a.apply else 'DRY-RUN'}): "
             f"{n_pass}/{len(hedefler)} ilan PASS", ""]
    lines += ["| pair | listing_id | sonuc | detay |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[4][:200]} |")
    if durdu:
        lines += ["", f"**DURDU:** {durdu}"]
    if rapor:
        lines += ["", "### gorsel karsilastirmasi (Etsy'den indirilen vs Drive kaynagi)", "",
                  "| pair | rank | sahne | sonuc | etsy olcu | fark ort | fark p99 |",
                  "|---|---|---|---|---|---|---|"]
        for c in rapor:
            lines.append(f"| {c.get('pair')} | {c.get('rank')} | {c.get('sahne')} | {c.get('sonuc')} | "
                         f"{c.get('etsy_olcu','-')} | {c.get('fark_ort','-')} | {c.get('fark_p99','-')} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    return 0 if (n_pass == len(hedefler) and not durdu) else 1


if __name__ == "__main__":
    sys.exit(main())
