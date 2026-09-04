#!/usr/bin/env python3
"""
KAPSAM OLCUMU (SALT OKUR) - 4 Eyl 2026 Mo gorevi.

Amac: Etsy'ye 3 Eyl'de yuklenen medyanin, Drive'daki GUNCEL uretimle ne
kadar ortustugunu olcmek; boylece "kac ilanda gorsel degisecek, kac ilanda
dosya degisecek" sorusu tahminle degil olcumle yanitlansin.

HICBIR YAZMA YOK: Drive yalniz listelenir (indirme bile yok), Etsy yalniz
GET edilir. Tek yazma OAuth token yenilemesidir (TokenStore -> Drive).

  1) ZIP TAZELIGI  Drive'daki 1248 wallpaper (FINAL_V2), 312 ZIP (DELIVERY)
                   ve 468 galeri gorselinin (MOCKUP_V2) degistirme zamani
                   esik ile karsilastirilir (varsayilan 3 Eyl 19:00:36 UTC =
                   TEMP/WP_UPLOAD_STATE.csv'deki son yukleme satiri).
                   Esikten SONRA degisen dosya, Etsy'dekinden yenidir.
  2) ETSY TARAFI   Ilan basina gorsel sayisi, video sayisi, state, dosya
                   adlari ve boyutlari; ZIP adi/boyutu Drive'daki guncel
                   ZIP ile karsilastirilir.
  3) RAPOR         Cift bazinda CSV + ozet tablo.

Kullanim:
  wp_scope_audit.py --state drafts.csv --wp-json wp.json --zip-json zip.json
      --mock-json mock.json --cutoff "2026-09-03T19:00:36Z" --out SCOPE.csv
"""
import argparse
import collections
import csv
import datetime as dt
import json
import re
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from wp_mockup_common import EDITIONS  # noqa: E402

QUOTA_STOP = 500  # x-remaining-today bu esigin altina inerse temiz cikis


TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$")


def parse_ts(s):
    """rclone lsjson ModTime / RFC3339 -> aware datetime (UTC). Saniye alti
    basamaklar (rclone ns verebilir) atilir; saat dilimi yoksa UTC varsayilir."""
    m = TS_RE.match((s or "").strip())
    if not m:
        return None
    base, tz = m.group(1).replace(" ", "T"), (m.group(2) or "Z")
    tz = "+00:00" if tz == "Z" else (tz if ":" in tz else tz[:3] + ":" + tz[3:])
    try:
        return dt.datetime.fromisoformat(base + tz).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def load_listing(path):
    """rclone lsjson -R ciktisi -> {PAIR: [(name, size, modtime), ...]}"""
    out = collections.defaultdict(list)
    if not path or not Path(path).exists():
        return out
    for r in json.loads(Path(path).read_text()):
        if r.get("IsDir"):
            continue
        rel = r.get("Path", "")
        pair = rel.split("/", 1)[0].upper() if "/" in rel else ""
        out[pair].append((r.get("Name", ""), int(r.get("Size") or 0), parse_ts(r.get("ModTime"))))
    return out


def span(items, cutoff):
    """(adet, en eski, en yeni, esikten sonra degisen adet)."""
    ts = [t for _, _, t in items if t]
    after = sum(1 for t in ts if t > cutoff)
    return len(items), (min(ts) if ts else None), (max(ts) if ts else None), after


def fmt(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S") if t else "-"


def read_state(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.reader(fh):
            if len(r) >= 2 and r[0] and r[0].lower() != "pair":
                rows.append((r[0].strip(), r[1].strip()))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True, help="cift,listing_id CSV")
    ap.add_argument("--wp-json", default="")
    ap.add_argument("--zip-json", default="")
    ap.add_argument("--mock-json", default="")
    ap.add_argument("--cutoff", default="2026-09-03T19:00:36Z",
                    help="Etsy yukleme bitis ani (UTC); bundan sonrasi Etsy'dekinden yeni")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--skip-etsy", action="store_true", help="yalniz Drive tarafi (1. madde)")
    a = ap.parse_args()

    cutoff = parse_ts(a.cutoff)
    log(f"esik (Etsy yukleme bitisi): {fmt(cutoff)} UTC")
    wp, zp, mk = (load_listing(a.wp_json), load_listing(a.zip_json), load_listing(a.mock_json))
    log(f"Drive: FINAL_V2 {sum(len(v) for v in wp.values())} dosya / {len(wp)} klasor; "
        f"DELIVERY {sum(len(v) for v in zp.values())} / {len(zp)}; "
        f"MOCKUP_V2 {sum(len(v) for v in mk.values())} / {len(mk)}")

    pairs = read_state(a.state)
    if a.limit:
        pairs = pairs[:a.limit]
    log(f"{len(pairs)} ilan olculecek")

    api = None
    if not a.skip_etsy:
        keystring = os.environ.get("ETSY_API_KEY", ""); shared = os.environ.get("ETSY_SHARED_SECRET", "")
        mask(keystring); mask(shared)
        store = TokenStore(os.environ["TOKEN_FILE"], keystring, shared)
        if store.needs_refresh():
            store.refresh()
        api = Etsy(store)
    shop_id = os.environ.get("ETSY_SHOP_ID", "")

    rows, keys_logged = [], False
    t0 = time.time()
    for i, (pair, lid) in enumerate(pairs):
        up = pair.upper()
        row = {"pair": pair, "listing_id": lid}
        notlar = []
        for tag, src, expect in (("wp", wp, 16), ("zip", zp, 4), ("mock", mk, 6)):
            n, lo, hi, after = span(src.get(up, []), cutoff)
            row[f"{tag}_adet"] = n
            row[f"{tag}_en_eski"] = fmt(lo)
            row[f"{tag}_en_yeni"] = fmt(hi)
            row[f"{tag}_esikten_sonra"] = after
            row[f"{tag}_taze"] = "EVET" if after else "hayir"
            if n != expect:
                notlar.append(f"{tag} adet {n} (beklenen {expect})")
        row["notlar"] = "; ".join(notlar)

        if api is not None:
            try:
                imgs = (api.get(f"/listings/{lid}/images", ok404=True) or {}).get("results", [])
                vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results", [])
                fls = (api.get(f"/shops/{shop_id}/listings/{lid}/files", ok404=True) or {}).get("results", [])
                lst = api.get(f"/listings/{lid}", ok404=True) or {}
            except SystemExit as e:
                log(f"DURDU: {e}")
                break
            if fls and not keys_logged:
                log(f"Etsy dosya alanlari: {sorted(fls[0].keys())}")
                keys_logged = True
            row["etsy_gorsel"] = len(imgs)
            row["etsy_video"] = len(vids)
            row["etsy_dosya"] = len(fls)
            row["etsy_state"] = lst.get("state", "?")
            # dosya adi + boyut
            names, sizes = [], []
            for f in sorted(fls, key=lambda x: x.get("rank", 0)):
                nm = f.get("filename", "")
                sz = f.get("size_bytes") or f.get("filesize") or ""
                names.append(nm); sizes.append(str(sz))
            row["etsy_dosya_adlari"] = "|".join(names)
            row["etsy_dosya_boyutlari"] = "|".join(sizes)
            # ZIP adi/boyutu Drive'daki guncel ZIP ile eslesiyor mu
            drive_zip = {n: s for n, s, _ in zp.get(up, [])}
            mism = []
            for ed in EDITIONS:
                want = f"AstroLove_{pair}_{ed}.zip"
                f = next((x for x in fls if x.get("filename") == want), None)
                if f is None:
                    mism.append(f"{want}: Etsy'de yok"); continue
                if want not in drive_zip:
                    mism.append(f"{want}: Drive'da yok"); continue
                esz = f.get("size_bytes")
                if isinstance(esz, int) and esz != drive_zip[want]:
                    mism.append(f"{want}: boyut Etsy {esz} vs Drive {drive_zip[want]}")
            row["zip_eslesme"] = "ESLESIYOR" if not mism else "FARKLI"
            row["zip_fark"] = "; ".join(mism)
            row["kota_kalan"] = api.remaining
            if api.remaining is not None and str(api.remaining).isdigit() and int(api.remaining) < QUOTA_STOP:
                log(f"DURDU: gunluk kota {api.remaining} < {QUOTA_STOP}")
                rows.append(row)
                break

        rows.append(row)
        el = time.time() - t0
        log(f"[{i+1}/{len(pairs)}] {pair} {lid} | "
            f"etsy g{row.get('etsy_gorsel','-')} v{row.get('etsy_video','-')} "
            f"d{row.get('etsy_dosya','-')} {row.get('etsy_state','-')} | "
            f"zip {row.get('zip_eslesme','-')} | mock taze {row['mock_taze']} "
            f"zip taze {row['zip_taze']} wp taze {row['wp_taze']} | "
            f"kota {row.get('kota_kalan','-')} | gecen {el/60:.1f} dk "
            f"kalan {el/(i+1)*(len(pairs)-i-1)/60:.1f} dk %{100*(i+1)/len(pairs):.0f}")

    cols = list(dict.fromkeys(k for r in rows for k in r))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    log(f"{a.out}: {len(rows)} satir")
    summary(rows, cutoff)
    return 0


def summary(rows, cutoff):
    n = len(rows)
    lines = [f"## kapsam olcumu ({n} ilan, esik {fmt(cutoff)} UTC)", ""]
    lines.append("| olcum | adet |")
    lines.append("|---|---|")
    q = [
        ("galeri (MOCKUP_V2) esikten SONRA uretilmis -> GORSEL DEGISECEK",
         sum(1 for r in rows if r.get("mock_taze") == "EVET")),
        ("ZIP (DELIVERY) esikten SONRA uretilmis -> DOSYA DEGISECEK",
         sum(1 for r in rows if r.get("zip_taze") == "EVET")),
        ("wallpaper (FINAL_V2) esikten SONRA uretilmis",
         sum(1 for r in rows if r.get("wp_taze") == "EVET")),
        ("Etsy ZIP adi+boyutu Drive ile ESLESIYOR",
         sum(1 for r in rows if r.get("zip_eslesme") == "ESLESIYOR")),
        ("Etsy ZIP FARKLI", sum(1 for r in rows if r.get("zip_eslesme") == "FARKLI")),
        ("Etsy gorsel sayisi 6", sum(1 for r in rows if r.get("etsy_gorsel") == 6)),
        ("Etsy gorsel sayisi 6 DEGIL", sum(1 for r in rows if r.get("etsy_gorsel") not in (6, None))),
        ("Etsy video var", sum(1 for r in rows if (r.get("etsy_video") or 0) > 0)),
        ("Etsy dosya sayisi 5", sum(1 for r in rows if r.get("etsy_dosya") == 5)),
    ]
    for label, v in q:
        lines.append(f"| {label} | {v} |")
    st = collections.Counter(r.get("etsy_state") for r in rows if r.get("etsy_state"))
    lines += ["", "state dagilimi: " + ", ".join(f"{k}={v}" for k, v in sorted(st.items()))]
    aykiri = [r for r in rows if r.get("etsy_gorsel") not in (6, None)
              or r.get("etsy_dosya") not in (5, None) or r.get("zip_eslesme") == "FARKLI"
              or r.get("notlar")]
    if aykiri:
        lines += ["", "### aykiri ilanlar", "",
                  "| pair | listing_id | gorsel | dosya | video | state | zip | not |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in aykiri:
            lines.append(f"| {r['pair']} | {r['listing_id']} | {r.get('etsy_gorsel','-')} | "
                         f"{r.get('etsy_dosya','-')} | {r.get('etsy_video','-')} | "
                         f"{r.get('etsy_state','-')} | {r.get('zip_eslesme','-')} | "
                         f"{(r.get('zip_fark') or r.get('notlar') or '')[:160]} |")
    for ln in lines:
        log(ln)
    s = os.environ.get("GITHUB_STEP_SUMMARY")
    if s:
        with open(s, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
