#!/usr/bin/env python3
"""Galeri v10 bagimsiz dogrulama (Merkez 28 Eki madde 1; Serdar onayi). ETSY SALT OKUMA: ilan basina tek GET
/listings/{id}/images (yd_envanter_oku.salt_okur: yazma yontemleri kapali). Kota tabani --kota-taban (varsayilan 515):
her istekten once kalan <= taban ise kosu durur (istekten sonra kalan tabanin altina inmez). KOTA_SINIRI (10) degismez.
Girdi (Drive'dan, Etsy kilidi oncesi indirilir): PLAN_V10.json (plan_damga), ILERLEME.json, v10 kapaklari
(TEMP/POSTER_KAPAK_V10/20261026_153710/KAPAK_<cift>.jpg), eski rank 1 yedegi (TEMP/POSTER_KAPAK_V10_YEDEK/20261026_144404/
<ilan>_<cift>/r1_*.jpg).
Ilan basina kontroller (sapma = beklenen != canli):
  ilerleme : ILERLEME durumu PASS ve plan_damga ayni
  sayi     : canli gorsel sayisi = plan hedef sayisi (9)
  rank     : canli rank dizisi 1..n
  sira     : canli kimlik sirasi = ILERLEME son_ids (yukleme sonrasi kaydedilen kimlikler)
  alt      : canli alt metin sirasi = plan hedef alt metinleri (sira 1..9; bosluk normallestirilmis)
  kapak    : rank 1 goruntusu (CDN url_570xN, API kotasi harcamaz) en yakin v10 kapagi kendi cifti VE v10 kapaga uzakligi
             eski rank 1'e uzakligindan kucuk (gri 64x96, ortalama mutlak fark 0-255).
Cikti --out: DOGRULA.json, DOGRULA.md, SAPMA.csv (ilan, cift, kontrol, beklenen, canli). Cikis 0: sapma yok; 1: sapma / DUR."""
import argparse
import csv
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))

BOYUT = (64, 96)


def log(m):
    print(m, flush=True)


def alt_norm(s):
    return " ".join((s or "").split())


def kucuk(im):
    return np.asarray(im.convert("L").resize(BOYUT, Image.LANCZOS), dtype=np.float32)


def mae(a, b):
    return round(float(np.abs(a - b).mean()), 2)


def cdn_indir(url, deneme=3):
    import requests
    for i in range(deneme):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200:
                return Image.open(io.BytesIO(r.content))
        except requests.RequestException:
            pass
        time.sleep(2 * (i + 1))
    return None


def kontrol(lid, cift, plan_g, ilr, canli, kapak_v10, eski_r1, r1_im, plan_damga):
    """-> sapma listesi [(kontrol, beklenen, canli)], kapak olcumu dict"""
    s = []
    if not ilr or ilr.get("durum") != "PASS" or ilr.get("plan_damga") != plan_damga:
        s.append(("ilerleme", f"PASS / {plan_damga}", f"{(ilr or {}).get('durum')} / {(ilr or {}).get('plan_damga')}"))
    if not plan_g:
        s.append(("plan", "plan girdisi", "yok"))
        return s, {}
    hedef = sorted(plan_g["hedef"], key=lambda h: h[0])
    n = len(hedef)
    if len(canli) != n:
        s.append(("sayi", str(n), str(len(canli))))
    rk = [x.get("rank") for x in canli]
    if rk != list(range(1, len(canli) + 1)):
        s.append(("rank", f"1..{len(canli)}", " ".join(map(str, rk))))
    ids = [x.get("listing_image_id") for x in canli]
    son = list((ilr or {}).get("son_ids") or [])
    if ids != son:
        fark = [i + 1 for i in range(max(len(ids), len(son))) if (ids[i] if i < len(ids) else None) != (son[i] if i < len(son) else None)]
        s.append(("sira", " ".join(map(str, son)), " ".join(map(str, ids)) + f" (farkli sira: {fark})"))
    alt_b = [alt_norm(h[3]) for h in hedef]
    alt_c = [alt_norm(x.get("alt_text")) for x in canli]
    if alt_c != alt_b:
        fark = [i + 1 for i in range(max(len(alt_b), len(alt_c))) if (alt_b[i] if i < len(alt_b) else None) != (alt_c[i] if i < len(alt_c) else None)]
        i0 = fark[0] - 1
        s.append(("alt", f"sira {fark}: {alt_b[i0] if i0 < len(alt_b) else '-'}"[:200], (alt_c[i0] if i0 < len(alt_c) else "-")[:200]))
    olc = {}
    if r1_im is None:
        s.append(("kapak", "rank 1 = v10 KAPAK_" + cift, "rank 1 goruntusu indirilemedi"))
        return s, olc
    c = kucuk(r1_im)
    uz = {k: mae(c, v) for k, v in kapak_v10.items()}
    en = min(uz, key=uz.get)
    olc = dict(v10=uz.get(cift), eski=mae(c, eski_r1) if eski_r1 is not None else None, en_yakin=en,
               ikinci=sorted(uz.values())[1] if len(uz) > 1 else None)
    if cift not in uz:
        s.append(("kapak", "v10 KAPAK_" + cift, "Drive'da v10 kapak yok"))
    elif en != cift:
        s.append(("kapak", "v10 KAPAK_" + cift, f"en yakin v10 kapak {en} ({uz[en]}; kendi {uz[cift]})"))
    elif olc["eski"] is not None and not olc["v10"] < olc["eski"]:
        s.append(("kapak", f"v10 kapaga uzaklik < eski r1 ({olc['eski']})", f"v10 {olc['v10']}"))
    return s, olc


def calistir(api, a):
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    if plan.get("plan_damga") != a.plan_damga:
        raise SystemExit(f"DUR: plan_damga {plan.get('plan_damga')} != {a.plan_damga}")
    ilr = (json.loads(Path(a.ilerleme).read_text(encoding="utf-8")).get("ilanlar") or {})
    ilanlar = [r for r in csv.DictReader(open(a.ciftler, encoding="utf-8"))]
    kapak = {}
    for p in sorted(Path(a.kapak_dir).glob("KAPAK_*.jpg")):
        kapak[p.stem[len("KAPAK_"):]] = kucuk(Image.open(p))
    satir, sapma, dur = [], [], None
    for r in ilanlar:
        lid, cift = r["listing_id"], r["cift"]
        s = dict(ilan=lid, cift=cift, durum="", sapma=[], kapak={})
        satir.append(s)
        if dur:
            s["durum"] = "KALAN"; continue
        try:
            api.kota_kapisi(f"ilan {lid}")
            res = api.get(f"/listings/{lid}/images", ok404=True) or {}
        except SystemExit as e:
            dur = str(e); s["durum"] = "DUR"; s["sapma"] = [("kota/istek", "-", dur)]; log(f"{lid} {cift} DUR: {dur}"); continue
        canli = sorted(res.get("results") or [], key=lambda x: x.get("rank") or 0)
        s["canli"] = [[x.get("rank"), x.get("listing_image_id"), alt_norm(x.get("alt_text"))] for x in canli]
        r1 = canli[0] if canli else {}
        r1_im = cdn_indir(r1.get("url_570xN")) if r1.get("url_570xN") else None
        eski = next(iter(sorted((Path(a.yedek_dir) / f"{lid}_{cift}").glob("r1_*.jpg"))), None)
        eski_k = kucuk(Image.open(eski)) if eski else None
        sp, olc = kontrol(lid, cift, (plan.get("girdiler") or {}).get(lid), ilr.get(lid), canli, kapak, eski_k, r1_im, a.plan_damga)
        s.update(durum="SAPMA" if sp else "PASS", sapma=sp, kapak=olc)
        sapma += [(lid, cift) + tuple(x) for x in sp]
        log(f"{lid} {cift} {s['durum']} | n {len(canli)} | kapak {olc} | kota {api.remaining}"
            + (f" | {sp[0][0]}: {sp[0][2][:100]}" if sp else ""))
    return satir, sapma, dur


def rapor(satir, sapma, dur, api, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    v10 = [s["kapak"].get("v10") for s in satir if s["kapak"].get("v10") is not None]
    es = [s["kapak"].get("eski") for s in satir if s["kapak"].get("eski") is not None]
    ik = [s["kapak"].get("ikinci") for s in satir if s["kapak"].get("ikinci") is not None]
    ozet = dict(plan_damga=a.plan_damga, galeri_damga=a.galeri_damga, ilan=len(satir), sayilar=say, sapma=len(sapma), dur=dur,
                istek=api.calls, kalan_kota=api.remaining, kota_taban=a.kota_taban,
                kapak_mae=dict(v10_max=max(v10) if v10 else None, v10_ort=round(float(np.mean(v10)), 2) if v10 else None,
                               eski_min=min(es) if es else None, ikinci_en_yakin_min=min(ik) if ik else None))
    (out / "DOGRULA.json").write_text(json.dumps(dict(ozet=ozet, ilanlar=satir), indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "SAPMA.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["ilan", "cift", "kontrol", "beklenen", "canli"]); w.writerows(sapma)
    md = [f"# Galeri v10 dogrulama (plan {a.plan_damga}, galeri {a.galeri_damga})", "",
          f"ilan {len(satir)} | {say} | sapma satiri {len(sapma)} | istek {api.calls} | kalan kota {api.remaining} (taban {a.kota_taban})",
          f"kapak MAE (0-255, gri 64x96): v10 en buyuk {ozet['kapak_mae']['v10_max']}, ort {ozet['kapak_mae']['v10_ort']}; "
          f"eski r1 en kucuk {ozet['kapak_mae']['eski_min']}; ikinci en yakin v10 kapak en kucuk {ozet['kapak_mae']['ikinci_en_yakin_min']}",
          (f"DUR: {dur}" if dur else ""), "", "| ilan | cift | kontrol | beklenen | canli |", "|---|---|---|---|---|"]
    md += [f"| {x[0]} | {x[1]} | {x[2]} | {str(x[3])[:120]} | {str(x[4])[:120]} |" for x in sapma] or ["| - | - | - | - | - |"]
    (out / "DOGRULA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log(md[2]); log(md[3])
    return 0 if not sapma and not dur and say.get("PASS", 0) == len(satir) else 1


def arg(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--plan-damga", required=True)
    ap.add_argument("--galeri-damga", default=""); ap.add_argument("--ilerleme", required=True)
    ap.add_argument("--ciftler", required=True); ap.add_argument("--kapak-dir", required=True)
    ap.add_argument("--yedek-dir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--kota-taban", type=int, default=515)
    return ap.parse_args(argv)


def main(argv=None):
    a = arg(argv)
    from etsy_common import Etsy, TokenStore, mask
    from yd_envanter_oku import salt_okur
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    salt_okur(api)
    # Merkez 28 Eki: kota 515'in altina inilmez. Sert taban her istekten once kalan < taban+1 ise durur; istek sonrasi kalan >= taban.
    # Yalniz bu kosuya ozgu ve KOTA_SINIRI'ndan (10) siki; etsy_common degismez.
    api.esik = api.sert_taban = max(int(a.kota_taban) + 1, api.sert_taban or 0)
    log(f"kota tabani bu kosu: {a.kota_taban} (istek oncesi kalan >= {api.sert_taban})")
    satir, sapma, dur = calistir(api, a)
    return rapor(satir, sapma, dur, api, a)


if __name__ == "__main__":
    sys.exit(main())
