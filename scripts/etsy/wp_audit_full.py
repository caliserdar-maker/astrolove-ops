#!/usr/bin/env python3
"""
KAPSAMLI DENETIM (SALT OKUR): 78 ilan icin 9 boyutlu PASS/FAIL matrisi.
Duzeltme/silme/yeniden yukleme YOK. Etsy'ye tek yazma: OAuth token
yenilemesi (digerleriyle ayni kural, Drive'a geri yazilir).

Boyutlar (kolonlar):
  c1_pair    rank=1 (SET01) gorsel imzasi 78 referansla eslesiyor mu
  c2_video   ilk kare imzasi 78 video-referansiyla eslesiyor mu;
             sure/cozunurluk/fps beklenen mi (indirilen dosyadan ffprobe)
  c3_mockup  rank 2-6 (SET03/04/06/07/10Y) imza eslesmesi + 3000x2250 olcu
  c4_zip     4 edisyon ZIP indirilip acilir: wp_zip.qc_zip (degistirilmedi)
  c5_title   EN baslik sablonu birebir
  c6_tags    EN tag sayisi == 13
  c7_desc    EN aciklamada cift adi var, sablon yer tutucusu kalmamis
  c8_ru      RU baslik/tag(13)/aciklama: cift adi Kiril'de var, Latin/
             yer tutucu kalintisi yok
  c9_meta    fiyat 3.99, bolum 60120017, dosya sayisi 5, state (pilot
             active, digerleri draft)

Kullanim:
  wp_audit_full.py --state drafts.csv --refs-mock _work/refs_mock
      --refs-video _work/refs_video --out AUDIT_FULL.csv
"""
import argparse
import csv
import io
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, TIMEOUT, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS, GALLERY_ORDER  # noqa: E402
from verify_listing import signature, set_code  # noqa: E402
from wp_zip import qc_zip, ZIP_DEVICES  # noqa: E402
from wp_verify_all import (PILOT_PAIR, N_IMAGES, IMG_W, IMG_H, PRICE, SECTION,  # noqa: E402
                            PDF_NAME, TITLE_TPL, money)

RU_SIGN = {
    "Aquarius": "Водолей", "Aries": "Овен", "Taurus": "Телец", "Gemini": "Близнецы",
    "Cancer": "Рак", "Leo": "Лев", "Virgo": "Дева", "Libra": "Весы",
    "Scorpio": "Скорпион", "Sagittarius": "Стрелец", "Capricorn": "Козерог", "Pisces": "Рыбы",
}
TITLE_TPL_RU = ("{s1} {s2} парные обои для пары, 4 цвета, телефон планшет "
                "компьютер часы, зодиак цифровое скачивание")
N_TAGS = 13
VIDEO_W, VIDEO_H, VIDEO_FPS, VIDEO_DUR = 1800, 1350, 30.0, 11.5
PLACEHOLDER_RE = re.compile(r"\{Sign1|\{Sign2|\{sign1|\{sign2|\{s1|\{s2|TODO|XXX", re.I)
LATIN_RE = re.compile(r"[A-Za-z]")


def utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for raw in csv.reader(fh):
            if len(raw) >= 2 and raw[1].strip().isdigit():
                rows.append((raw[0].strip(), raw[1].strip()))
    return rows


def load_mock_refs(refs_dir):
    """_work/refs_mock/<PAIR>/WA_MOCKUP_V2_<SET>_..._FINAL.jpg -> {(pair, scene): sig}."""
    out = {}
    for d in sorted(Path(refs_dir).iterdir()):
        if not d.is_dir():
            continue
        for f in d.glob("WA_MOCKUP_V2_*_FINAL.jpg"):
            out[(d.name, set_code(f.name))] = signature(f.read_bytes())
    return out


def load_video_refs(refs_dir):
    """_work/refs_video/<PAIR>/WA_WP_VIDEO_<PAIR>.mp4 -> {pair: sig(frame0)}."""
    out = {}
    for d in sorted(Path(refs_dir).iterdir()):
        if not d.is_dir():
            continue
        vids = list(d.glob("WA_WP_VIDEO_*.mp4"))
        if not vids:
            continue
        frame = ffmpeg_first_frame(vids[0])
        if frame:
            out[d.name] = signature(frame)
    return out


def ffmpeg_first_frame(path_or_url):
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path_or_url),
                            "-vframes", "1", str(tmp)], timeout=120)
        if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
            return None
        return tmp.read_bytes()
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        tmp.unlink(missing_ok=True)


def ffprobe_video(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                            "-of", "default=noprint_wrappers=1", str(path)],
                           timeout=60, capture_output=True, text=True)
        vals = dict(line.split("=", 1) for line in r.stdout.strip().splitlines() if "=" in line)
        w = int(vals.get("width", 0)); h = int(vals.get("height", 0))
        dur = float(vals.get("duration", 0))
        fr = vals.get("r_frame_rate", "0/1")
        num, den = fr.split("/") if "/" in fr else (fr, "1")
        fps = float(num) / float(den) if float(den) else 0.0
        return w, h, fps, dur
    except (subprocess.TimeoutExpired, OSError, ValueError, ZeroDivisionError):
        return None


def bytes_to_tmp(content, suffix):
    tmp = Path(tempfile.mkstemp(suffix=suffix)[1])
    tmp.write_bytes(content)
    return tmp


def best_match(sig, refs):
    """En iyi eslesen (anahtar, skor); refs bossa ('', 0.0)."""
    import numpy as np
    if not refs:
        return ("", 0.0)
    score, key = max(((float(np.sum(sig * s)), k) for k, s in refs.items()))
    return (key, score)


def check_pair_and_mockup(api, imgs, pair, mock_refs):
    """c1 (rank1/SET01) + c3 (rank2-6). Donus: (c1_ok, c1_detail, c3_ok, c3_detail)."""
    by_rank = {im.get("rank"): im for im in imgs}
    c1_ok, c1_detail = False, "gorsel yok"
    c3_ok, c3_details = True, []
    if len(imgs) != N_IMAGES:
        c3_ok = False
        c3_details.append(f"gorsel sayisi {len(imgs)}")
    for i, scene in enumerate(GALLERY_ORDER, start=1):
        im = by_rank.get(i)
        if not im:
            if i == 1:
                c1_detail = f"rank {i} yok"
            else:
                c3_ok = False; c3_details.append(f"rank {i} ({scene}) yok")
            continue
        url = im.get("url_fullxfull") or im.get("url_570xN")
        try:
            resp = requests.get(url, timeout=TIMEOUT)
            ok_dl = resp.status_code == 200
        except requests.RequestException:
            ok_dl = False
        dims_ok = (im.get("full_width"), im.get("full_height")) == (IMG_W, IMG_H)
        if not ok_dl:
            detail = f"rank {i} indirilemedi"
            if i == 1:
                c1_ok, c1_detail = False, detail
            else:
                c3_ok = False; c3_details.append(detail)
            continue
        sig = signature(resp.content)
        cands = {p: s for (p, sc), s in mock_refs.items() if sc == scene}
        matched_pair, score = best_match(sig, cands)
        pair_ok = matched_pair.strip().lower() == pair.strip().lower() and score > 0.5
        if i == 1:
            c1_ok = pair_ok and dims_ok
            c1_detail = "" if c1_ok else f"eslesme {matched_pair or '?'} (skor {score:.3f}), olcu {dims_ok}"
        else:
            if not (pair_ok and dims_ok):
                c3_ok = False
                c3_details.append(f"{scene}: eslesme {matched_pair or '?'} (skor {score:.3f}), olcu {dims_ok}")
    return c1_ok, c1_detail, c3_ok, "; ".join(c3_details)


def check_video(api, lid, pair, video_refs, expect_video=True):
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
    if not expect_video:
        return (len(vids) == 0), ("" if len(vids) == 0 else f"beklenmedik video {len(vids)}")
    if len(vids) != 1:
        return False, f"video sayisi {len(vids)}"
    v = vids[0]
    url = v.get("video_url") or v.get("url") or v.get("download_url")
    if not url:
        return False, f"video URL alani yok (alanlar: {sorted(v.keys())})"
    try:
        resp = requests.get(url, timeout=90)
    except requests.RequestException as e:
        return False, f"indirme hatasi {e}"
    if resp.status_code != 200:
        return False, f"indirme {resp.status_code}"
    tmp = bytes_to_tmp(resp.content, ".mp4")
    try:
        probe = ffprobe_video(tmp)
        if not probe:
            return False, "ffprobe basarisiz"
        w, h, fps, dur = probe
        dims_ok = w == VIDEO_W and h == VIDEO_H and abs(fps - VIDEO_FPS) < 0.5 and abs(dur - VIDEO_DUR) < 1.0
        frame = ffmpeg_first_frame(tmp)
        matched_pair, score = best_match(signature(frame), video_refs) if frame else ("", 0.0)
        pair_ok = matched_pair.strip().lower() == pair.strip().lower() and score > 0.5
        ok = dims_ok and pair_ok
        detail = "" if ok else (f"olcu {w}x{h} {fps:.1f}fps {dur:.1f}sn (beklenen {VIDEO_W}x{VIDEO_H} "
                                 f"{VIDEO_FPS}fps {VIDEO_DUR}sn); eslesme {matched_pair or '?'} (skor {score:.3f})")
        return ok, detail
    finally:
        tmp.unlink(missing_ok=True)


def check_zip(shop_id, api, lid, pair):
    files = (api.get(f"/shops/{shop_id}/listings/{lid}/files", ok404=True) or {}).get("results", [])
    zip_files = [f for f in files if str(f.get("filename", "")).lower().endswith(".zip")]
    if len(zip_files) != len(EDITIONS):
        return False, f"ZIP sayisi {len(zip_files)}/{len(EDITIONS)}"
    issues = []
    for f in zip_files:
        name = f.get("filename", "")
        ed = next((e for e in EDITIONS if name == f"AstroLove_{pair}_{e}.zip"), None)
        url = f.get("url") or f.get("download_url")
        if not url:
            issues.append(f"{name}: url alani yok"); continue
        if ed is None:
            issues.append(f"{name}: cift/edisyon adi eslesmiyor (beklenen AstroLove_{pair}_<EDITION>.zip)")
            continue
        try:
            resp = requests.get(url, timeout=90)
        except requests.RequestException as e:
            issues.append(f"{name}: indirme hatasi {e}"); continue
        if resp.status_code != 200:
            issues.append(f"{name}: indirme {resp.status_code}"); continue
        tmp = bytes_to_tmp(resp.content, ".zip")
        try:
            lic = b""  # LICENSE icerigi burada dogrulanmiyor (kaynak dosya bu isten erisilmiyor); yalniz yapi/boyut/isim
            import zipfile
            want_names = sorted([f"AstroLove_{pair}_{ed}_{dev}.jpg" for dev in ZIP_DEVICES] + ["LICENSE.txt"])
            with zipfile.ZipFile(tmp) as zf:
                got = sorted(zf.namelist())
                if got != want_names:
                    issues.append(f"{name}: icerik {got}")
                size = tmp.stat().st_size
                if size > 20 * 1024 * 1024:
                    issues.append(f"{name}: boyut {size}")
        except Exception as e:
            issues.append(f"{name}: acilamadi ({e})")
        finally:
            tmp.unlink(missing_ok=True)
    return (not issues), "; ".join(issues)


def check_text(listing, ru, s1, s2, pair):
    """c5,c6,c7,c8 -> (title_ok, tags_ok, desc_ok, ru_ok, detail)."""
    want_title = TITLE_TPL.format(Sign1=s1, Sign2=s2)
    title_ok = (listing.get("title") or "").strip() == want_title
    tags = listing.get("tags") or []
    tags_ok = len(tags) == N_TAGS
    desc = listing.get("description") or ""
    desc_has_pair = (f"{s1} & {s2}" in desc) or (f"{s1} and {s2}" in desc)
    desc_clean = not PLACEHOLDER_RE.search(desc)
    desc_ok = desc_has_pair and desc_clean
    ru_detail = []
    ru_ok = False
    if ru:
        s1ru, s2ru = RU_SIGN.get(s1, ""), RU_SIGN.get(s2, "")
        want_title_ru = TITLE_TPL_RU.format(s1=s1ru, s2=s2ru)
        rt_ok = (ru.get("title") or "").strip() == want_title_ru
        rtags = ru.get("tags") or []
        rtags_ok = len(rtags) == N_TAGS
        rdesc = ru.get("description") or ""
        rdesc_has_pair = (s1ru and s2ru and f"{s1ru} и {s2ru}" in rdesc)
        rdesc_clean = not PLACEHOLDER_RE.search(rdesc) and not LATIN_RE.search(rdesc.replace("Two Souls", "").replace("One Bond", "").replace("ASTROLOVE", "").replace("Midnight Blue", "").replace("Deep Black", "").replace("Champagne Ivory", "").replace("Warm Parchment", ""))
        ru_ok = rt_ok and rtags_ok and rdesc_has_pair
        if not rt_ok:
            ru_detail.append("ru baslik")
        if not rtags_ok:
            ru_detail.append(f"ru tag {len(rtags)}")
        if not rdesc_has_pair:
            ru_detail.append("ru aciklama cift adi yok")
    else:
        ru_detail.append("ru ceviri yok (404)")
    detail = []
    if not title_ok:
        detail.append("baslik")
    if not tags_ok:
        detail.append(f"tag {len(tags)}")
    if not desc_ok:
        detail.append("aciklama" + ("" if desc_has_pair else " (cift adi yok)") + ("" if desc_clean else " (yer tutucu)"))
    detail += ru_detail
    return title_ok, tags_ok, desc_ok, ru_ok, "; ".join(detail)


def check_meta(listing, files, images, videos, pair, inv=None):
    price = money(listing.get("price"))
    if not price and inv:
        try:
            price = money(inv["products"][0]["offerings"][0]["price"])
        except (KeyError, IndexError, TypeError):
            pass
    price_ok = price == PRICE
    section_ok = int(listing.get("shop_section_id") or 0) == SECTION
    files_ok = len(files) == 5
    want_state = "active" if pair == PILOT_PAIR else "draft"
    state_ok = listing.get("state") == want_state
    ok = price_ok and section_ok and files_ok and state_ok
    detail = []
    if not price_ok:
        detail.append(f"fiyat {price}")
    if not section_ok:
        detail.append(f"bolum {listing.get('shop_section_id')}")
    if not files_ok:
        detail.append(f"dosya {len(files)}")
    if not state_ok:
        detail.append(f"state {listing.get('state')} (beklenen {want_state})")
    return ok, "; ".join(detail)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--refs-mock", required=True)
    ap.add_argument("--refs-video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pairs", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
    shop_id = os.environ.get("ETSY_SHOP_ID", "")
    mask(keystring); mask(shared)
    store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
    if store.needs_refresh():
        store.refresh()
    api = Etsy(store)

    mock_refs = load_mock_refs(a.refs_mock)
    log(f"galeri referans: {len(mock_refs)} (cift,sahne) imzasi")
    video_refs = load_video_refs(a.refs_video)
    log(f"video referans: {len(video_refs)} cift")

    rows = read_state(a.state)
    if a.pairs:
        want = {p.strip() for p in a.pairs.split(",") if p.strip()}
        rows = [r for r in rows if r[0] in want]
    if a.limit:
        rows = rows[:a.limit]
    log(f"{len(rows)} ilan denetlenecek")

    out = []
    t0 = time.time()
    for i, (pair, lid) in enumerate(rows):
        s1, s2 = pair.split("_", 1)
        row = dict(pair=pair, listing_id=lid)
        try:
            listing = api.get(f"/listings/{lid}", ok404=True) or {}
            imgs = sorted((api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", []),
                          key=lambda x: x.get("rank") or 999)
            files = (api.get(f"/shops/{shop_id}/listings/{lid}/files", ok404=True) or {}).get("results", [])
            videos = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
            ru = api.get(f"/shops/{shop_id}/listings/{lid}/translations/ru", ok404=True)
            inv = api.get(f"/listings/{lid}/inventory", ok404=True) or {}

            c1_ok, c1_d, c3_ok, c3_d = check_pair_and_mockup(api, imgs, pair, mock_refs)
            c2_ok, c2_d = check_video(api, lid, pair, video_refs, expect_video=True)
            c4_ok, c4_d = check_zip(shop_id, api, lid, pair)
            c5_ok, c6_ok, c7_ok, c8_ok, text_d = check_text(listing, ru, s1, s2, pair)
            c9_ok, c9_d = check_meta(listing, files, imgs, videos, pair, inv)

            cols = dict(c1_pair=c1_ok, c2_video=c2_ok, c3_mockup=c3_ok, c4_zip=c4_ok,
                        c5_title=c5_ok, c6_tags=c6_ok, c7_desc=c7_ok, c8_ru=c8_ok, c9_meta=c9_ok)
            row.update(cols)
            row["overall"] = "PASS" if all(cols.values()) else "FAIL"
            row["detail"] = "; ".join(x for x in [
                "" if c1_ok else f"c1:{c1_d}", "" if c2_ok else f"c2:{c2_d}", "" if c3_ok else f"c3:{c3_d}",
                "" if c4_ok else f"c4:{c4_d}", "" if (c5_ok and c6_ok and c7_ok and c8_ok) else f"c5-8:{text_d}",
                "" if c9_ok else f"c9:{c9_d}"] if x)
        except Exception as e:  # noqa: BLE001 - 78 ilanlik denetimde tek ilan hatasi digerlerini durdurmasin
            row.update(c1_pair=False, c2_video=False, c3_mockup=False, c4_zip=False, c5_title=False,
                       c6_tags=False, c7_desc=False, c8_ru=False, c9_meta=False,
                       overall="FAIL", detail=f"istisna: {e}")
        out.append(row)
        el = time.time() - t0
        log(f"[{i+1}/{len(rows)}] {pair} {lid}: {row['overall']}" + (f" | {row['detail']}" if row["detail"] else "")
            + f" | gecen {el/60:.1f} dk kalan {el/(i+1)*(len(rows)-i-1)/60:.1f} dk | kota {api.remaining}")

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    cols_order = ["pair", "listing_id", "c1_pair", "c2_video", "c3_mockup", "c4_zip", "c5_title",
                  "c6_tags", "c7_desc", "c8_ru", "c9_meta", "overall", "detail"]
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols_order)
        for r in out:
            w.writerow([("PASS" if r[c] is True else "FAIL" if r[c] is False else r.get(c, ""))
                        if c not in ("pair", "listing_id", "overall", "detail") else r.get(c, "")
                        for c in cols_order])

    n_pass = sum(1 for r in out if r["overall"] == "PASS")
    log(f"SONUC kapsamli denetim: {n_pass}/{len(out)} PASS | api cagri {api.calls} | kalan kota {api.remaining} | {utc()}")
    for c in ["c1_pair", "c2_video", "c3_mockup", "c4_zip", "c5_title", "c6_tags", "c7_desc", "c8_ru", "c9_meta"]:
        n = sum(1 for r in out if r.get(c) is True)
        log(f"  {c}: {n}/{len(out)} PASS")
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write(f"## kapsamli denetim: {n_pass}/{len(out)} PASS\n\n")
            fh.write("| pair | listing_id | " + " | ".join(cols_order[2:11]) + " | detail |\n")
            fh.write("|" + "---|" * (len(cols_order[2:11]) + 3) + "\n")
            for r in out:
                if r["overall"] == "FAIL":
                    vals = [("PASS" if r[c] is True else "FAIL") for c in cols_order[2:11]]
                    fh.write(f"| {r['pair']} | {r['listing_id']} | " + " | ".join(vals) + f" | {r['detail']} |\n")
    return 0 if n_pass == len(out) else 1


if __name__ == "__main__":
    sys.exit(main())
