#!/usr/bin/env python3
"""Galeri v11 canli dogrulama (Merkez 29 Eki: pilot ve 77 ilan sonrasi). ETSY API YOK: canli okuma galeri-v11-yedek-oku
(ilan basina 4 GET, Etsy kilidiyle) + galeri-v11-yedek-indir (CDN, kilitsiz) ciktisindan; yukleme kaydi galeri-v11-yukle SONRA_<ilan>.json.
Girdiler:
  --canli   TEMP/POSTER_GALERI_V11_YEDEK/<damga> (yukleme SONRASI okuma): <ilan>_<CIFT>/GALERI.json + r<rank>_<id>.jpg
  --sonra   SONRA_<ilan>.json klasoru (TEMP/POSTER_GALERI_V11_YUKLE/KOSU/<kosu>/), birden fazla verilebilir
  --galeri  TEMP/POSTER_GALERI_V11/<damga> (<CIFT>_W01_KAPAK|W07_MB|W08_DB|W09_PW|W10_WP.jpg)
  --kart    wa-kart-v11 cikti klasoru (<CIFT>_W02_SEMBOL|W03_KISISEL|W05_SUREC|W06_GENEL.jpg, ORTAK_W04_FORMAT.jpg)
  --alt data/pod/galeri_v11_alt.csv  --ciftler data/pod/pod78_ids.csv (listing_id, cift, a, b)  --sadece virgullu listing_id
Ilan basina kapilar (biri tutmazsa FAIL):
  galeri   10 gorsel, rank 1..10 tekil; kimlik sirasi = SONRA son_ids (yuklenen gorseller W01..W10 sirasinda)
  alt      her rank alt metni = sablon (galeri_v10_liste.alt_metin, <A>/<B> = burclar)
  bag      5 renk bagi property 200: Champagne Ivory 1, Midnight Blue 7, Deep Black 8, Pure White 9, Warm Parchment 10
  state    active (GALERI.json ilan.state); video 1
  sha      kaynak dosyanin sha256'si = SONRA yukleme_kaydi sha256 (yuklenen dosya dogru kaynak)
  ncc      indirilen canli gorsel (Etsy yeniden kodlar, sha256 farkli) ile kaynak: 256x192 gri NCC; ESIKSIZ kimlik kurali: her rank'in
           en benzer kaynagi ilanin 10 kaynagi icinde kendisi olmali (argmax). min NCC raporda (dagilim).
Profil v11b (--profil v11b, Serdar 29 Eki kesin karar): rank 1 = B1 yedegindeki (--b1, TEMP/POSTER_GALERI_V11_YEDEK/20261029_121704)
  MB kapak kimligi (dokunulmamis: ayni listing_image_id), alt metni sablonla karsilastirilmaz; 2-10 kaynak W02-W10 (W01 yok);
  baglar MB 7, DB 8, PW 9, WP 10 (Champagne Ivory bagsiz); yukleme kaydinda rank 1 yok.
Profil v11b_or_ci (inceleme 30 Eki madde 5; canli karisik: 11 gorsel / 5 bag ya da 10 / 4): ilan basina. 10 gorselli ilan v11b ile ayni;
  11 gorselli ilan: 1-10 v11b kapilari (kimlik sirasi = SONRA son_ids, NCC, sha), rank 11 kimligi 1-10'dan farkli, alt metni
  --alt-ci (data/pod/galeri_ci11_alt.csv sira 11) sablonu, Champagne Ivory bagi rank 11'e (5 bag). Rank 11 dosya kimligi (sha / NCC)
  burada OLCULMEZ: galeri-ci11-yukle kendi geri okumasinda (SONRA_<ilan>.json, POSTER_GALERI_CI11/KOSU) dogrular.
Cikti --out: DOGRULA.csv (ilan basina), DOGRULA.md, DOGRULA.json. Cikis 0 = hepsi PASS, 1 = FAIL var."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import galeri_v10_liste as L  # noqa: E402

N = 10
RENK_SIRA = {"Champagne Ivory": 1, "Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}
RENK_SIRA_B = {"Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}
KAYNAK = {1: "W01_KAPAK", 2: "W02_SEMBOL", 3: "W03_KISISEL", 4: "W04_FORMAT", 5: "W05_SUREC", 6: "W06_GENEL",
          7: "W07_MB", 8: "W08_DB", 9: "W09_PW", 10: "W10_WP"}
BOY = (256, 192)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def vek(p):
    with Image.open(p) as im:
        v = np.asarray(im.convert("L").resize(BOY, Image.BILINEAR), np.float64).ravel()
    v -= v.mean()
    return v / (np.linalg.norm(v) or 1.0)


def kaynak_yol(cift, s, galeri, kart):
    if s == 4:
        return Path(kart) / "ORTAK_W04_FORMAT.jpg"
    return (Path(kart) if 2 <= s <= 6 else Path(galeri)) / f"{cift}_{KAYNAK[s]}.jpg"


def ilan(lid, r, d, sonra, sab, galeri, kart, b1_r1=None, b1_alt=None, b1_dosya=None, ci_sab=None):
    """b1_r1 / b1_alt: v11b ise B1 yedegindeki rank 1 kimligi ve alt metni (MB kapak dokunulmaz); None = v11.
    ONAR (v11 yazilmis 18 ilan, Merkez 29 Eki): rank 1 B1 kimligi degil ama yukleme kaydinda rank 1 = canli rank 1 (B1 MB kapak dosyasi
    yeniden yuklendi): alt metni B1'deki, yuklenen sha256 = B1 r1 dosyasi (b1_dosya), NCC kaynagi B1 r1; 2-10 onceki v11 kaydindan."""
    neden, olc = [], {}
    v11b = b1_r1 is not None
    j = json.loads((d / "GALERI.json").read_text(encoding="utf-8"))
    g = sorted(j.get("gorseller") or [], key=lambda x: x.get("rank") or 0)
    ci11 = ci_sab is not None and len(g) == N + 1      # v11b_or_ci: 11 gorselli ilan (rank 11 Champagne Ivory)
    n = N + 1 if ci11 else N
    ids = [x["listing_image_id"] for x in g]
    if len(g) != n or [x["rank"] for x in g] != list(range(1, n + 1)) or len(set(ids)) != n:
        neden.append(f"galeri {len(g)} gorsel / rank {[x['rank'] for x in g]}")
    if ids[:N] != sonra.get("son_ids"):
        neden.append(f"kimlik sirasi SONRA son_ids ile ayni degil ({ids[:N]} != {sonra.get('son_ids')})")
    alt = L.alt_metin(sab, r["a"], r["b"])
    kotu = [x["rank"] for x in g if x["rank"] <= N and x.get("alt_text") != alt.get(x["rank"]) and not (v11b and x["rank"] == 1)]
    if ci11 and g[N].get("alt_text") != L.alt_metin({N + 1: ci_sab}, r["a"], r["b"])[N + 1]:
        neden.append("rank 11 alt metni Champagne Ivory sablonu (galeri_ci11_alt.csv) degil")
    kay = {int(x["hedef_sira"]): x for x in sonra.get("yukleme_kaydi") or []}
    onar = bool(v11b and ids and ids[0] != b1_r1 and (kay.get(1) or {}).get("listing_image_id") == ids[0])
    if v11b and not onar and (not ids or ids[0] != b1_r1):
        neden.append(f"rank 1 B1 yedegindeki MB kapak degil ({ids[:1]} != {b1_r1})")
    elif v11b and g[0].get("alt_text") != b1_alt:   # 29 Eki inceleme D2: alt metni yazilmadi / ONAR'da B1 metni
        neden.append("rank 1 alt metni B1 yedegindekinden farkli")
    if onar:
        if not b1_dosya or not Path(b1_dosya).exists():
            neden.append("ONAR: B1 MB kapak dosyasi yok (sha256 / NCC olculemedi)")
        elif kay[1].get("sha256") != sha(b1_dosya):
            neden.append("ONAR: rank 1 yuklenen sha256 B1 MB kapak dosyasi ile ayni degil")
    if kotu:
        neden.append(f"alt metin farkli: rank {kotu}")
    rk = {x["listing_image_id"]: x["rank"] for x in g}
    b = j.get("baglar") or []
    sira = {x.get("value"): rk.get(x.get("image_id")) for x in b}
    rs = RENK_SIRA_B if v11b else RENK_SIRA
    if ci11:
        rs = dict(rs, **{"Champagne Ivory": N + 1})
    if len(b) != len(rs) or sira != rs or any(x.get("property_id") != 200 for x in b):
        neden.append(f"renk baglari {sira}")
    st = (j.get("ilan") or {}).get("state")
    if st != "active":
        neden.append(f"state {st}")
    if len(j.get("videolar") or []) != 1:
        neden.append(f"video {len(j.get('videolar') or [])}")
    kv, cv = {}, {}
    if v11b and not onar and 1 in kay:
        neden.append("rank 1 yukleme kaydinda (dokunulmaz MB kapak yeniden yuklenmis)")
    if onar and b1_dosya and Path(b1_dosya).exists() and len(ids) >= 1:
        kv[1] = vek(b1_dosya)
        c1 = d / f"r1_{ids[0]}.jpg"
        if c1.exists():
            cv[1] = vek(c1)
        else:
            neden.append("canli gorsel indirilmemis r1")
    for s in range(2 if v11b else 1, N + 1):
        p = kaynak_yol(r["cift"], s, galeri, kart)
        if not p.exists():
            neden.append(f"kaynak yok {p.name}"); continue
        if (kay.get(s) or {}).get("sha256") != sha(p):
            neden.append(f"rank {s}: yuklenen sha256 kaynak {p.name} ile ayni degil")
        if (kay.get(s) or {}).get("listing_image_id") != (ids[s - 1] if len(ids) >= s else None):
            neden.append(f"rank {s}: yuklenen kimlik canli rank {s} degil")
        kv[s] = vek(p)
        c = d / f"r{s}_{ids[s - 1]}.jpg" if len(ids) >= s else None
        if not c or not c.exists():
            neden.append(f"canli gorsel indirilmemis r{s}"); continue
        cv[s] = vek(c)
    for s, v in cv.items():
        m = {t: float(v @ k) for t, k in kv.items()}
        en = max(m, key=m.get)
        olc[s] = round(m.get(s, -1.0), 4)
        if en != s:
            neden.append(f"rank {s}: canli gorsel en cok kaynak {en}'e benziyor (NCC {m[en]:.3f} > {m.get(s, -1):.3f})")
    tur = "+".join(x for x in ("ONAR" if onar else "", "CI11" if ci11 else "") if x)
    return dict(ilan=lid, cift=r["cift"], tur=tur, durum="FAIL" if neden else "PASS", neden="; ".join(neden),
                ncc_min=min(olc.values()) if olc else None, ncc=olc, state=st)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--canli", required=True); ap.add_argument("--sonra", required=True, action="append")
    ap.add_argument("--galeri", required=True); ap.add_argument("--kart", required=True)
    ap.add_argument("--alt", required=True); ap.add_argument("--ciftler", required=True)
    ap.add_argument("--sadece", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--profil", choices=("v11", "v11b", "v11b_or_ci"), default="v11")
    ap.add_argument("--b1", default="", help="v11b / v11b_or_ci: B1 yedegi (<ilan>_<CIFT>/GALERI.json; rank 1 MB kapak kimligi)")
    ap.add_argument("--alt-ci", default=str(HERE.parents[1] / "data/pod/galeri_ci11_alt.csv"), help="v11b_or_ci: rank 11 CI alt metni")
    a = ap.parse_args(argv)
    b1_ister = a.profil in ("v11b", "v11b_or_ci")
    if b1_ister and not a.b1:
        raise SystemExit(f"{a.profil} icin --b1 gerekli")
    sab = {int(r["sira"]): r for r in csv.DictReader(open(a.alt, encoding="utf-8-sig"))}
    if sorted(sab) != list(range(1, N + 1)):
        raise SystemExit("alt metin sablonu 1..10 degil")
    ci_sab = None
    if a.profil == "v11b_or_ci":
        ci_sab = {int(r["sira"]): r for r in csv.DictReader(open(a.alt_ci, encoding="utf-8-sig"))}.get(N + 1)
        if not ci_sab or (ci_sab.get("durum") or "ONAYLI") != "ONAYLI":
            raise SystemExit("CI alt metin sablonu (sira 11, ONAYLI) yok")
    rows = {r["listing_id"]: r for r in csv.DictReader(open(a.ciftler, encoding="utf-8-sig"))}
    s = [x.strip() for x in a.sadece.split(",") if x.strip()] or list(rows)
    sonra = {}
    def kosu_no(k):   # eski kosu once: sonraki kosunun kaydi ayni hedef sirasini ezer (ONAR rank 1; 2-10 v11 kosusundan)
        n = "".join(ch for ch in Path(k).name if ch.isdigit())
        return int(n) if n else 0
    for k in sorted(a.sonra, key=kosu_no):
        for p in sorted(Path(k).rglob("SONRA_*.json")):   # KOSU/<kosu>/ilanlar/SONRA_<ilan>.json
            lid = p.stem.split("_", 1)[1]; j = json.loads(p.read_text(encoding="utf-8"))
            kay = {int(x["hedef_sira"]): x for x in (sonra.get(lid) or {}).get("yukleme_kaydi") or []}
            kay.update({int(x["hedef_sira"]): x for x in j.get("yukleme_kaydi") or []})
            sonra[lid] = dict(j, yukleme_kaydi=[kay[s_] for s_ in sorted(kay)])
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    R = []
    for lid in s:
        r = rows.get(lid)
        d = Path(a.canli) / f"{lid}_{r['cift']}" if r else None
        if not r or not d.is_dir() or lid not in sonra:
            R.append(dict(ilan=lid, cift=(r or {}).get("cift", "-"), durum="FAIL", ncc_min=None, ncc={}, state=None,
                          neden="ilan listede yok" if not r else ("canli okuma yok" if not d.is_dir() else "SONRA kaydi yok")))
        else:
            b1 = b1a = b1d = None
            if b1_ister:
                bp = Path(a.b1) / f"{lid}_{r['cift']}" / "GALERI.json"
                gb = sorted(json.loads(bp.read_text(encoding="utf-8")).get("gorseller") or [], key=lambda x: x.get("rank") or 0) if bp.exists() else []
                b1 = gb[0]["listing_image_id"] if gb else -1
                b1a = gb[0].get("alt_text") if gb else None
                b1d = bp.parent / f"r1_{b1}.jpg"
            R.append(ilan(lid, r, d, sonra[lid], sab, a.galeri, a.kart, b1, b1a if b1_ister else None, b1d, ci_sab=ci_sab))
        print(f"{lid} {R[-1]['cift']} {R[-1]['durum']} ncc_min {R[-1]['ncc_min']} {R[-1]['neden'][:200]}", flush=True)
    with open(out / "DOGRULA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "durum", "state", "ncc_min", "neden"], extrasaction="ignore")
        w.writeheader(); w.writerows(R)
    (out / "DOGRULA.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    nf = sum(1 for x in R if x["durum"] != "PASS")
    nm = [x["ncc_min"] for x in R if x["ncc_min"] is not None]
    md = [f"# Galeri v11 canli dogrulama\n", f"ilan {len(R)} | PASS {len(R) - nf} | FAIL {nf}",
          f"NCC (canli / kaynak, ilan basina en dusuk): min {min(nm) if nm else '-'} medyan {float(np.median(nm)) if nm else '-'}\n"]
    md += [f"- {x['ilan']} {x['cift']} FAIL: {x['neden']}" for x in R if x["durum"] != "PASS"]
    (out / "DOGRULA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md), flush=True)
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
