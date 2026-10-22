#!/usr/bin/env python3
"""
GECE ZINCIRI asama e: 78 ilana medya yukler (6 galeri gorseli sirali + 1 video +
5 dijital dosya). ETSY'YE YAZAR; STATE degistirmez (ilanlar taslak kalir, pilot
aktif kalir). Yayin komutu Mo'dan gelir; bu script YAYINLAMAZ.

Kurallar (B68/B70 dersleri + Mo, 3 Eyl):
  - Bos galeri: gorseller rank 1..6 sirasiyla yuklenir (SET01,03,04,06,07,10Y).
  - Dolu galeri (pilot): once yeni yuklenir (ayni rank), kararlilik beklenir,
    SONRA eski silinir; overwrite kullanilmaz.
  - Her yazmadan sonra geri okuma: 10 sn bekle, 3 deneme, iki ardisik okuma ayni
    olana kadar kararlilik.
  - Token: kosu basinda ve her 40 dakikada bir yenilenir; 401'de etsy_common
    zaten bir kez yeniler ve tekrarlar.
  - Kota: x-remaining-today her istekte izlenir; --quota-stop altina dusunce
    temiz cikilir (STATE korunur, resume mumkun).
  - STATE CSV: pair,listing_id,images,video,files,status,ts_utc,detail

Kullanim:
  wp_media_upload.py --state WA_WP_DRAFTS_STATE.csv --media _work/media \\
      --out _work/UPLOAD_STATE.csv [--pairs Aries_Leo,...] [--apply]
Dry-run (varsayilan) hicbir yazma cagrisi yapmaz: her ilan icin mevcut medya
sayisi ve yuklenecek dosyalar raporlanir.
"""
import argparse
import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS  # noqa: E402

GALLERY_ORDER = ["SET01", "SET03", "SET04", "SET06", "SET07", "SET10Y"]
MOCK_NAME = {"SET10Y": "WA_MOCKUP_V2_SET10_YAZILI_{pair}_FINAL.jpg"}
READBACK_WAIT = 10
READBACK_TRIES = 3
TOKEN_REFRESH_S = 40 * 60
PDF_NAME = "HOW_TO_SET_YOUR_WALLPAPER.pdf"


def utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def mock_name(scene, pair):
    return MOCK_NAME.get(scene, "WA_MOCKUP_V2_{scene}_{pair}_FINAL.jpg").format(scene=scene, pair=pair)


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                rows.append((raw[0].strip(), raw[1].strip()))
    return rows


def read_done(path):
    done = {}
    p = Path(path)
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.reader(fh):
                if len(r) >= 6 and r[0] != "pair":
                    done[r[0]] = r[5]
    return done


def append_done(path, row):
    p = Path(path)
    new = not p.exists()
    with open(p, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["pair", "listing_id", "images", "video", "files", "status", "ts_utc", "detail"])
        w.writerow(row)


class Media:
    """Etsy medya okuma/yazma; her yazmadan sonra kararlilik + geri okuma."""

    def __init__(self, api, shop_id, apply_):
        self.api = api
        self.shop = shop_id
        self.apply = apply_

    def images(self, lid):
        r = self.api.get(f"/listings/{lid}/images", ok404=True) or {}
        return sorted(((x.get("rank"), x.get("listing_image_id"), x.get("full_width"), x.get("full_height"))
                       for x in r.get("results", [])), key=lambda t: t[0] or 0)

    def videos(self, lid):
        r = self.api.get(f"/listings/{lid}/videos", ok404=True) or {}
        return [(v.get("video_id"), v.get("video_state")) for v in r.get("results", [])]

    def files(self, lid):
        r = self.api.get(f"/shops/{self.shop}/listings/{lid}/files", ok404=True) or {}
        return [(f.get("listing_file_id"), f.get("filename"), f.get("size_bytes")) for f in r.get("results", [])]

    def stable(self, fn, lid, want=None):
        """Iki ardisik okuma ayni (ve varsa want kosulu saglanmis) olana kadar bekler."""
        prev = None
        for _ in range(READBACK_TRIES):
            time.sleep(READBACK_WAIT)
            cur = fn(lid)
            if prev is not None and cur == prev and (want is None or want(cur)):
                return cur
            prev = cur
        return prev

    def upload_image(self, lid, path, rank):
        if not self.apply:
            return None
        with open(path, "rb") as fh:
            r = self.api.post_file(f"/shops/{self.shop}/listings/{lid}/images",
                                   files={"image": (Path(path).name, fh, "image/jpeg")},
                                   data={"rank": str(rank)})
        return r.get("listing_image_id")

    def delete_image(self, lid, image_id):
        if self.apply:
            self.api.delete(f"/shops/{self.shop}/listings/{lid}/images/{image_id}")

    def upload_video(self, lid, path):
        if not self.apply:
            return None
        with open(path, "rb") as fh:
            r = self.api.post_file(f"/shops/{self.shop}/listings/{lid}/videos",
                                   files={"video": (Path(path).name, fh, "video/mp4")},
                                   data={"name": Path(path).name})
        return r.get("video_id")

    def delete_video(self, lid, video_id):
        if self.apply:
            self.api.delete(f"/shops/{self.shop}/listings/{lid}/videos/{video_id}")

    def upload_file(self, lid, path, rank):
        if not self.apply:
            return None
        mime = "application/pdf" if str(path).lower().endswith(".pdf") else "application/zip"
        with open(path, "rb") as fh:
            r = self.api.post_file(f"/shops/{self.shop}/listings/{lid}/files",
                                   files={"file": (Path(path).name, fh, mime)},
                                   data={"name": Path(path).name, "rank": str(rank)})
        return r.get("listing_file_id")

    def delete_file(self, lid, file_id):
        if self.apply:
            self.api.delete(f"/shops/{self.shop}/listings/{lid}/files/{file_id}")


def pair_media(media_root, pair):
    """Bir cift icin yuklenecek dosyalar: 6 mockup, 1 video, 4 ZIP + PDF."""
    up = pair.upper()
    imgs = [Path(media_root) / "mock" / up / mock_name(s, pair) for s in GALLERY_ORDER]
    vid = Path(media_root) / "video" / up / f"WA_WP_VIDEO_{up}.mp4"
    zips = [Path(media_root) / "zip" / up / f"AstroLove_{pair}_{ed}.zip" for ed in EDITIONS]
    pdf = Path(media_root) / PDF_NAME
    return imgs, vid, zips + [pdf]


def do_pair(m, pair, lid, media_root, want_video):
    imgs, vid, files = pair_media(media_root, pair)
    missing = [str(p) for p in imgs + files if not p.exists()] + ([str(vid)] if want_video and not vid.exists() else [])
    if missing:
        return "FAIL", 0, 0, 0, f"eksik dosya: {len(missing)} ({Path(missing[0]).name}...)"
    before_i, before_v, before_f = m.images(lid), m.videos(lid), m.files(lid)
    log(f"  once: gorsel {len(before_i)}, video {len(before_v)}, dosya {len(before_f)}")
    if not m.apply:
        return "DRY", len(before_i), len(before_v), len(before_f), \
            f"yuklenecek: {len(imgs)} gorsel, {1 if want_video else 0} video, {len(files)} dosya"
    # --- gorseller: rank sirasiyla yukle; dolu galeride eskiyi SONRA sil
    old_ids = [i[1] for i in before_i]
    for rank, p in enumerate(imgs, start=1):
        m.upload_image(lid, p, rank)
    cur = m.stable(m.images, lid, want=lambda c: len(c) >= len(imgs))
    for oid in old_ids:
        m.delete_image(lid, oid)
    if old_ids:
        cur = m.stable(m.images, lid, want=lambda c: len(c) == len(imgs))
    # --- video: Etsy ilan basina 1 video tutar; eskisi varsa once yeni, sonra sil
    vids_after = before_v
    if want_video:
        old_v = [v[0] for v in before_v]
        m.upload_video(lid, vid)
        vids_after = m.stable(m.videos, lid, want=lambda c: len(c) >= 1)
        for ov in old_v:
            if ov not in [v[0] for v in vids_after] or len(vids_after) > 1:
                m.delete_video(lid, ov)
        vids_after = m.stable(m.videos, lid, want=lambda c: len(c) == 1)
    # --- dijital dosyalar
    old_f = [f[0] for f in before_f]
    for rank, p in enumerate(files, start=1):
        m.upload_file(lid, p, rank)
    fs = m.stable(m.files, lid, want=lambda c: len(c) >= len(files))
    for of in old_f:
        m.delete_file(lid, of)
    if old_f:
        fs = m.stable(m.files, lid, want=lambda c: len(c) == len(files))
    ni, nv, nf = len(cur or []), len(vids_after or []), len(fs or [])
    ok = ni == len(imgs) and nf == len(files) and (nv == 1 if want_video else True)
    return ("PASS" if ok else "FAIL"), ni, nv, nf, ("" if ok else f"beklenen {len(imgs)}/1/{len(files)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="cift,listing_id CSV")
    ap.add_argument("--media", required=True, help="mock/ video/ zip/ + PDF koku")
    ap.add_argument("--out", required=True, help="yukleme STATE CSV (resume)")
    ap.add_argument("--pairs", default="", help="virgullu alt kume (bos = hepsi)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true", help="ETSY'YE YAZ")
    ap.add_argument("--no-video", action="store_true", help="video yuklemeyi atla (asama c hazir degilse)")
    ap.add_argument("--quota-stop", type=int, default=300, help="kalan kota bu degerin altina dusunce temiz cik")
    a = ap.parse_args()
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    if not shop_id:
        raise SystemExit("HATA: ETSY_SHOP_ID yok")
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)
    m = Media(api, shop_id, a.apply)
    rows = read_state(a.state)
    if a.pairs:
        want = {p.strip() for p in a.pairs.split(",") if p.strip()}
        rows = [r for r in rows if r[0] in want]
    done = read_done(a.out)
    todo = [r for r in rows if done.get(r[0]) != "PASS"]
    if a.limit:
        todo = todo[:a.limit]
    log(f"{len(rows)} ilan, {len(todo)} islenecek ({'APPLY' if a.apply else 'DRY-RUN'}); "
        f"video {'atlanir' if a.no_video else 'yuklenir'}")
    t0 = time.time(); last_token = time.time(); fails = []
    for i, (pair, lid) in enumerate(todo):
        if time.time() - last_token > TOKEN_REFRESH_S:
            store.refresh(); last_token = time.time()
        log(f"[{i + 1}/{len(todo)}] {pair} ({lid})")
        try:
            status, ni, nv, nf, detail = do_pair(m, pair, lid, a.media, not a.no_video)
        except SystemExit as e:
            status, ni, nv, nf, detail = "FAIL", 0, 0, 0, str(e)[:200]
        append_done(a.out, [pair, lid, ni, nv, nf, status, utc(), detail])
        if status == "FAIL":
            fails.append(pair)
        el = time.time() - t0; rem = el / (i + 1) * (len(todo) - i - 1)
        log(f"  {pair}: {status} | gorsel {ni} video {nv} dosya {nf} {detail} | {i + 1}/{len(todo)} "
            f"gecen {el / 60:.1f} dk kalan {rem / 60:.1f} dk %{100 * (i + 1) / len(todo):.0f} | kota {api.remaining}")
        try:
            if api.remaining is not None and int(api.remaining) < a.quota_stop:
                log(f"KOTA {api.remaining} < {a.quota_stop}: temiz cikiliyor (resume STATE'te).")
                break
        except (TypeError, ValueError):
            pass
    log(f"SONUC asama e: {len(todo) - len(fails)}/{len(todo)} PASS" + (f" | FAIL: {','.join(fails)}" if fails else "")
        + f" | api cagri {api.calls} | kalan kota {api.remaining}")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## medya yukleme ({'APPLY' if a.apply else 'DRY-RUN'}): {len(todo) - len(fails)}/{len(todo)} PASS\n\n"
                     + (f"FAIL: {', '.join(fails)}\n" if fails else "") + f"- kalan kota: {api.remaining}\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
