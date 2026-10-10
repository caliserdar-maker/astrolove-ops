#!/usr/bin/env python3
"""78 POD ilaninin kategori nitelikleri ve mevcut degerleri (SALT OKUR, etsy-arama, 10 Eki 2026 aksam).

Yalniz Etsy.get: aktif ilanlar, getPropertiesByTaxonomyId, getListingProperties. Etsy'ye yazmaz.
Cikti: 46_NITELIK_SECENEK.csv, 46b_NITELIK_MEVCUT.csv, 46_OKUMA_NOTU.txt
"""
import csv
import html
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
from seo_live_snapshot import list_active, zodiac_pair  # noqa: E402
from arama_oku import taxonomy_paths  # noqa: E402


def guvenli_get(api, path, hatalar, **kw):
    try:
        return api.get(path, ok404=True, **kw) or {}
    except SystemExit as e:  # etsy_common hatada SystemExit atar; kosu durmaz, hata kaydedilir
        hatalar.append(f"{path}: {e}")
        return {}


def run(api, shop, out):
    out.mkdir(parents=True, exist_ok=True)
    hatalar = []
    ilanlar = [x for x in list_active(api, shop) if x.get("listing_type") == "physical"]
    log(f"aktif POD ilan {len(ilanlar)} | kota {api.remaining}")
    agac = guvenli_get(api, "/seller-taxonomy/nodes", hatalar).get("results") or []
    adlar = taxonomy_paths(agac)
    tax_ids = sorted({x.get("taxonomy_id") for x in ilanlar if x.get("taxonomy_id")})
    secenek, tax_props = [], {}
    for tid in tax_ids:
        props = guvenli_get(api, f"/seller-taxonomy/nodes/{tid}/properties", hatalar).get("results") or []
        tax_props[tid] = props
        for p in props:
            ad = p.get("display_name") or p.get("name") or ""
            degerler = [html.unescape(str(v.get("name") or "")) for v in (p.get("possible_values") or [])]
            temel = {"taxonomy_id": tid, "kategori_adi": adlar.get(tid, ""), "property_id": p.get("property_id"),
                     "nitelik_adi": ad, "zorunlu": "evet" if p.get("is_required") else "hayir",
                     "coklu": "evet" if p.get("is_multivalued") else "hayir"}
            if degerler:
                secenek += [dict(temel, secenek_degeri=d) for d in degerler]
            else:
                secenek.append(dict(temel, secenek_degeri="(secenek listesi yok, serbest/olcu)"))
    mevcut, bos_say = [], {}
    for i, x in enumerate(sorted(ilanlar, key=lambda r: zodiac_pair(html.unescape(r.get("title") or ""))), 1):
        lid, tid = x.get("listing_id"), x.get("taxonomy_id")
        cift = zodiac_pair(html.unescape(x.get("title") or ""))
        res = guvenli_get(api, f"/shops/{shop}/listings/{lid}/properties", hatalar).get("results") or []
        dolu = {}
        for r in res:
            vals = [html.unescape(str(v)) for v in (r.get("values") or []) if str(v).strip()]
            dolu[r.get("property_id")] = (r.get("property_name") or "", " | ".join(vals))
        bos = 0
        for p in tax_props.get(tid, []):
            pid = p.get("property_id")
            ad = p.get("display_name") or p.get("name") or ""
            deger = dolu.pop(pid, (ad, ""))[1] or "bos"
            bos += deger == "bos"
            mevcut.append({"listing_id": lid, "cift": cift, "taxonomy_id": tid, "nitelik_adi": ad, "mevcut_deger": deger})
        for pid, (ad, deger) in dolu.items():  # kategori listesinde olmayan ama ilanda olan nitelik
            mevcut.append({"listing_id": lid, "cift": cift, "taxonomy_id": tid, "nitelik_adi": f"{ad} (kategori listesinde yok)",
                           "mevcut_deger": deger or "bos"})
        bos_say[lid] = (cift, bos, len(tax_props.get(tid, [])))
        if i % 20 == 0 or i == len(ilanlar):
            log(f"ilerleme {i}/{len(ilanlar)} ({100 * i // len(ilanlar)}%) | kota {api.remaining}")
    for fn, rows, cols in (("46_NITELIK_SECENEK.csv", secenek,
                            ["taxonomy_id", "kategori_adi", "property_id", "nitelik_adi", "zorunlu", "coklu", "secenek_degeri"]),
                           ("46b_NITELIK_MEVCUT.csv", mevcut, ["listing_id", "cift", "taxonomy_id", "nitelik_adi", "mevcut_deger"])):
        with open(out / fn, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
    dag = Counter(b for _, b, _ in bos_say.values())
    nitelik_bos = Counter(r["nitelik_adi"] for r in mevcut if r["mevcut_deger"] == "bos")
    satir = [
        "46 OKUMA NOTU (etsy-arama, salt okur; Etsy'ye yazma 0)",
        f"Okuma zamani: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"API: yalniz GET, {api.calls} cagri, kalan kota {api.remaining}",
        f"Aktif POD ilan: {len(ilanlar)}; taxonomy_id: {', '.join(f'{t} ({adlar.get(t, "")})' for t in tax_ids)}",
        f"Kategori nitelik sayisi: {', '.join(f'{t}: {len(tax_props[t])}' for t in tax_ids)}",
        f"46_NITELIK_SECENEK.csv: {len(secenek)} satir (+1 baslik)",
        f"46b_NITELIK_MEVCUT.csv: {len(mevcut)} satir (+1 baslik)",
        "Bos nitelik sayisi dagilimi (ilan basina bos -> ilan sayisi): "
        + ", ".join(f"{k} bos -> {v} ilan" for k, v in sorted(dag.items())),
        "Nitelik bazinda bos ilan sayisi: " + ", ".join(f"{k}: {v}" for k, v in nitelik_bos.most_common()),
        f"API hatalari: {len(hatalar)}",
    ] + [f"  - {h}" for h in hatalar] + ["", "Ilan basina bos nitelik (listing_id | cift | bos / kategori nitelik sayisi):"]
    satir += [f"{lid} | {c} | {b}/{n}" for lid, (c, b, n) in bos_say.items()]
    (out / "46_OKUMA_NOTU.txt").write_text("\n".join(satir) + "\n", encoding="utf-8")
    log(f"SONUC: {len(ilanlar)} ilan, {len(secenek)} secenek satiri, {len(mevcut)} mevcut satiri, API hata {len(hatalar)}; Etsy yazma 0")
    return 0 if ilanlar and not hatalar else 1


def main():
    key, secret, shop = (os.environ.get(k, "") for k in ("ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_SHOP_ID"))
    if not key or not secret or not shop or not os.environ.get("TOKEN_FILE"):
        raise SystemExit("HATA: Etsy ortam degiskenleri eksik")
    mask(key)
    mask(secret)
    store = TokenStore(os.environ["TOKEN_FILE"], key, secret)
    if store.needs_refresh():
        store.refresh()
    return run(Etsy(store), shop, Path(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
