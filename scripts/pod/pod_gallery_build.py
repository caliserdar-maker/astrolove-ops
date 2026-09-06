#!/usr/bin/env python3
"""
78 cift POD galeri uretimi (toplu surucu) - 6 Eyl 2026. Onayli pod_gallery_sample.py'yi
import eder, ona dokunmaz.

Cift x 5 edisyon x 10 kare (11_EXTRA uretilmez): 01,02,03,04,06,07,09 kaynak kopya
(ETSY_UPLOAD_SETS; 04 PNG -> JPG q98), 05 Paper / 08 Sizes / 10 Care cift+edisyona gore
cizilir. Her kart icin QC (olculebilir esik, onayli ARIES_LEO kosusundan turetildi):
  - boyut 3000x2250 (tum kareler)
  - ust bant (y0,y1,x0,x1) = (0,27,0,2999) +-1  [yeni kartlar]
  - rozet (x0,x1,cap) = (271,401,130) +-2      [05, 10]
  - Size Guide 6 gorunen bosluk + sol kenar: |bosluk - hedef| <= 2.5 px  [08]
  - palet sapmasi (zemin/bar/baslik) <= 16      [yeni kartlar; olculen 8-14]
  - geometri max sapma <= 6 px (08'de baslik bandi haric; olculen 5)
FAIL olan cift STATE'e FAIL yazilir, kosu devam eder. STATE satiri cift basina aninda
yazilir (resume: PASS olan cift atlanir). Kontak: CONTACT_<PAIR>.jpg (5 satir x 10 kare).

Kullanim:
  pod_gallery_build.py --pairs-file P.txt --src SRC --out OUT --fonts FONTS --state STATE.csv
      [--contact-dir DIR] [--verified verified.json] [--spellcheck] [--shard i --shards n]
      [--rclone-src gdrive:.../ETSY_UPLOAD_SETS --rclone-out gdrive:.../TEMP/POD_GALLERY]
rclone verilirse cift basina kaynak indirilir, cikti yuklenir, yerel kopya silinir.
"""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pod_gallery_sample as G  # noqa: E402

FRAMES = [p for p in G.PLAN]                       # 10 kare; EXTRA yok
NEW = {"PAPER": G.card_paper, "SIZES": G.card_sizes, "CARE": G.card_care}
SRC_RANKS = sorted({what for _, what in G.PLAN if what not in NEW} | {"05", "10"})   # 01,02,03,04,05,06,07,10
TH = {"top": 1, "badge": 2, "gap": 2.5, "palette": 16, "geom": 6}
STATE_COLS = ["pair", "status", "frames", "fail", "secs", "ts_utc"]


def log(m):
    print(m, flush=True)


def rclone(*args):
    r = subprocess.run(["rclone", *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"rclone {' '.join(args[:2])}: rc={r.returncode} {r.stderr.strip()[-300:]}")


# ------------------------------------------------------------------ QC
def qc_card(p, what, pal):
    """Yeni kart QC -> hata listesi (bos = PASS)."""
    errs = []
    im = Image.open(p)
    if im.size != (G.W, G.H):
        errs.append(f"boyut {im.size}")
        return errs
    mp = G.measure(p)
    pdev = max(abs(mp[k][i] - pal[k][i]) for k in ("bg", "bar", "ink") for i in range(3))
    if pdev > TH["palette"]:
        errs.append(f"palet {pdev}")
    g = G.geometry(p, rows=(what != "SIZES"))
    top = g.get("top")
    if not top or any(abs(top[i] - G.GEOM_REF["top"][i]) > TH["top"] for i in range(4)):
        errs.append(f"ust bant {top[:4] if top else None}")
    devs = []
    for k, ref in G.GEOM_REF.items():
        v = g.get(k)
        if v is None or k == "top":
            if v is None and k in ("kicker", "rule", "pair", "rule_x", "bar", "bar_text"):
                errs.append(f"{k} olculemedi")
            continue
        if k == "bar_text":
            # bar serif bandinin alt siniri metnin alt uzantisina bagli (08'de 2077, 04'te 2094): ust sinirlar + caps bandi
            if len(v) < 2:
                errs.append(f"bar metin bantlari {v}"); continue
            devs += [abs(v[0][0] - ref[0][0]), abs(v[1][0] - ref[1][0]), abs(v[1][1] - ref[1][1])]
        elif k == "title":
            if what != "SIZES":
                devs.append(abs(v[0] - ref[0]))
        elif k == "badge":
            if what != "SIZES" and any(abs(x - y) > TH["badge"] for x, y in zip(v, ref)):
                errs.append(f"rozet {v}")
        elif isinstance(v, tuple):
            devs += [abs(x - y) for x, y in zip(v, ref)]
        else:
            devs.append(abs(v - ref[0]))
    if what != "SIZES" and g.get("badge") is None:
        errs.append("rozet olculemedi")
    if devs and max(devs) > TH["geom"]:
        errs.append(f"geometri {max(devs)}")
    if what == "SIZES":
        gaps = G.sizes_gaps(p)
        keys = ["kenar->cetvel", "cetvel->kutu1", "kutu1->kutu2", "kutu2->kutu3", "kutu3->kutu4", "kutu4->kutu5", "kutu5->kenar"]
        if not all(k in gaps for k in keys):
            errs.append("bosluk olculemedi")
        else:
            bad = {k: gaps[k] for k in keys if abs(gaps[k] - gaps["hedef bosluk"]) > TH["gap"]}
            if bad:
                errs.append(f"bosluk {bad}")
    return errs


# ------------------------------------------------------------------ uretim
def build_pair(pair, src_root, out_root, F, contact_dir):
    """Donus: (n_frames, [hata])."""
    errs, n = [], 0
    pair_txt = " • ".join(pair.split("_"))
    for ed in G.EDITIONS:
        src, out = Path(src_root) / ed / pair, Path(out_root) / pair / ed
        if not src.exists():
            errs.append(f"{ed}: kaynak yok"); continue
        out.mkdir(parents=True, exist_ok=True)
        try:
            pal = G.palette(G.find_src(src, "10"))
            c05 = Image.open(G.find_src(src, "05")).convert("RGB")
        except FileNotFoundError as e:
            errs.append(f"{ed}: {e}"); continue
        x, y, w, h = G.POSTER_BOX
        poster = c05.crop((x, y, x + w, y + h))
        for outno, what in FRAMES:
            if what in NEW:
                p = out / f"{outno}_{what}_{pair}_{ed}.jpg"
                G.save_jpg(NEW[what](pal, F, poster, pair_txt), p, 95)
                e = qc_card(p, what, pal)
                if e:
                    errs.append(f"{ed}/{outno}_{what}: " + "; ".join(e))
            else:
                try:
                    s = G.find_src(src, what)
                except FileNotFoundError as e:
                    errs.append(f"{ed}: {e}"); continue
                p = out / f"{outno}_{s.stem.split('_', 1)[1]}.jpg"
                if s.suffix.lower() == ".png":
                    G.save_jpg(Image.open(s).convert("RGB"), p, 98)
                else:
                    shutil.copyfile(s, p)
                if Image.open(p).size != (G.W, G.H):
                    errs.append(f"{ed}/{outno}: boyut {Image.open(p).size}")
            n += 1
    if contact_dir:
        contact(Path(out_root) / pair, pair, Path(contact_dir) / f"CONTACT_{pair}.jpg", F)
    return n, errs


def contact(pair_dir, pair, out_p, F):
    """5 edisyon x 10 kare kontak sayfasi."""
    from PIL import ImageDraw
    cols, tw, th = 10, 300, 225
    eds = [e for e in G.EDITIONS if (pair_dir / e).exists()]
    sheet = Image.new("RGB", (cols * tw, len(eds) * (th + 30) + 50), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((16, 12), pair, font=F.f("sans", 28, 600), fill=(0, 0, 0))
    for r, ed in enumerate(eds):
        y0 = 50 + r * (th + 30)
        d.text((16, y0 + th + 4), ed, font=F.f("sans", 18, 500), fill=(0, 0, 0))
        for i, f in enumerate(sorted((pair_dir / ed).glob("*.jpg"))[:cols]):
            im = Image.open(f).convert("RGB")
            im.thumbnail((tw - 6, th - 6))
            sheet.paste(im, (i * tw + 3, y0))
    out_p.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_p, "JPEG", quality=85)


# ------------------------------------------------------------------ durum
def read_state(path):
    st = {}
    if Path(path).exists():
        with open(path, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                st[r["pair"]] = r
    return st


def write_state(path, st):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=STATE_COLS)
        w.writeheader()
        for k in sorted(st):
            w.writerow({c: st[k].get(c, "") for c in STATE_COLS})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pairs-file", required=True)
    ap.add_argument("--src", required=True, help="SRC/<ED>/<PAIR>/")
    ap.add_argument("--out", required=True, help="OUT/<PAIR>/<ED>/01..10.jpg")
    ap.add_argument("--fonts", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--contact-dir", default="")
    ap.add_argument("--verified", default="")
    ap.add_argument("--spellcheck", action="store_true")
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--rclone-src", default="", help="gdrive:.../ETSY_UPLOAD_SETS (cift basina indir)")
    ap.add_argument("--rclone-out", default="", help="gdrive:.../TEMP/POD_GALLERY (cift basina yukle, yereli sil)")
    ap.add_argument("--force", action="store_true", help="PASS olan ciftleri de yeniden uret")
    a = ap.parse_args()

    pairs = [l.strip().upper() for l in Path(a.pairs_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    pairs = sorted(dict.fromkeys(pairs))
    mine = [p for i, p in enumerate(pairs) if i % a.shards == a.shard]
    if a.verified:
        G.VERIFIED = json.loads(Path(a.verified).read_text())
        log(f"kaynak filtresi: {sum(G.VERIFIED.values())}/{len(G.VERIFIED)} satir kaynakli")
    if a.spellcheck:
        G.spellcheck()
    F = G.Fonts(a.fonts)
    st = read_state(a.state)
    todo = [p for p in mine if a.force or st.get(p, {}).get("status") != "PASS"]
    log(f"shard {a.shard}/{a.shards}: {len(mine)} cift, {len(todo)} islenecek (PASS atlanir), esikler {TH}")
    t0 = time.time()
    n_pass = n_fail = 0
    for i, pair in enumerate(todo, 1):
        tp = time.time()
        src_root = Path(a.src)
        if a.rclone_src:
            for ed in G.EDITIONS:
                d = src_root / ed / pair
                d.mkdir(parents=True, exist_ok=True)
                try:
                    rclone("copy", f"{a.rclone_src}/{ed}/{pair}", str(d), "--include", "{" + ",".join(SRC_RANKS) + "}_WA_*", "--transfers", "8", "-q")
                except RuntimeError as e:
                    log(f"  {pair} {ed}: {e}")
        try:
            n, errs = build_pair(pair, src_root, a.out, F, a.contact_dir)
        except Exception as e:                       # tek cift kosuyu durdurmasin
            n, errs = 0, [f"istisna {type(e).__name__}: {str(e)[:200]}"]
        ok = not errs and n == len(FRAMES) * len(G.EDITIONS)
        if not ok and n != len(FRAMES) * len(G.EDITIONS):
            errs.append(f"kare {n}/{len(FRAMES) * len(G.EDITIONS)}")
        if a.rclone_out and n:
            try:
                rclone("copy", str(Path(a.out) / pair), f"{a.rclone_out}/{pair}", "--transfers", "8", "-q")
                if a.contact_dir and (Path(a.contact_dir) / f"CONTACT_{pair}.jpg").exists():
                    rclone("copyto", str(Path(a.contact_dir) / f"CONTACT_{pair}.jpg"), f"{a.rclone_out}/_CONTACT/CONTACT_{pair}.jpg", "-q")
            except RuntimeError as e:
                ok = False; errs.append(str(e))
        secs = round(time.time() - tp, 1)
        st[pair] = dict(pair=pair, status="PASS" if ok else "FAIL", frames=n, fail=" | ".join(errs)[:900], secs=secs,
                        ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        write_state(a.state, st)
        n_pass += ok; n_fail += (not ok)
        if a.rclone_src or a.rclone_out:
            for ed in G.EDITIONS:
                shutil.rmtree(src_root / ed / pair, ignore_errors=True)
            if a.rclone_out:
                shutil.rmtree(Path(a.out) / pair, ignore_errors=True)
        el = time.time() - t0
        log(f"[{i}/{len(todo)}] {pair:<24} {'PASS' if ok else 'FAIL'} {n} kare {secs}s | gecen {el:.0f}s kalan~{el / i * (len(todo) - i):.0f}s | {'; '.join(errs)[:160]}")
    log(f"shard {a.shard}: PASS {n_pass} FAIL {n_fail} sure {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
