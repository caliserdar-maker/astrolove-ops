#!/usr/bin/env python3
"""Prodigi Etsy kanali durumu: SALT OKUMA (yalniz GET /orders, GET /orders/{id}). Etsy'ye cagri yok, kota yok.

Kanal ayari (bagli mi, siparis 'pause' ile mi geliyor) Prodigi API'sinde alan olarak yok; kanalin IZI olculur:
- merchantReference 'etsy-' ile BASLAMAYAN siparis = kanal (router kendi siparisini etsy-<receipt>-<boy> ile acar)
- kanal siparislerinin tarihi, asamasi (stage), ayrintilari (details), sorunlari (issues), iptal/eylem alanlari
- son kanal siparisi ne zaman, kac tanesi hic ilerlemeden bekliyor (pause/onay izi)
Kisisel veri basilmaz (alici adi/adres yok); yalniz ulke kodu.
Cikti: <out>/KANAL_DURUMU.md + .json
"""
import json, sys, time
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
import order_router as R

out = Path(sys.argv[1] if len(sys.argv) > 1 else "_out/kanal"); out.mkdir(parents=True, exist_ok=True)
p = R.Prodigi(R.load_prodigi_key("live"), "live")
tum, skip, t0 = [], 0, time.time()
while skip < 500:
    st, d = p.call("GET", f"/orders?top=100&skip={skip}")
    if st != 200:
        sys.exit(f"HATA: GET /orders HTTP {st}")
    parca = d.get("orders") or []
    tum += parca
    print(f"[{len(tum)}] siparis okundu | gecen {time.time() - t0:.0f}s | hasMore={d.get('hasMore')}", flush=True)
    if not d.get("hasMore") or not parca:
        break
    skip += len(parca)


def kisa(o):
    s = o.get("status") or {}
    return {"id": o.get("id"), "created": o.get("created"), "mr": str(o.get("merchantReference") or ""),
            "stage": s.get("stage"), "details": s.get("details"),
            "issues": [(i.get("errorCode"), i.get("description")) for i in s.get("issues") or []],
            "ulke": ((o.get("recipient") or {}).get("address") or {}).get("countryCode"),
            "kalem": [(i.get("sku"), i.get("copies"), i.get("merchantReference")) for i in o.get("items") or []],
            "kargo": o.get("shippingMethod"), "callback": bool(o.get("callbackUrl")),
            "metadata_anahtar": sorted((o.get("metadata") or {}).keys())}


kanal = [kisa(o) for o in tum if not str(o.get("merchantReference") or "").startswith("etsy-")]
bizim = [kisa(o) for o in tum if str(o.get("merchantReference") or "").startswith("etsy-")]
kanal.sort(key=lambda x: x["created"] or "", reverse=True)
for k in kanal[:15]:                       # eylem alanlari (cancel / hold vb.) yalniz son 15 kanal siparisi
    st, d = p.get_order(k["id"])
    k["actions"] = {a: (v or {}).get("isAvailable") for a, v in ((d.get("order") or {}).get("actions") or {}).items()}
son = kanal[0]["created"] if kanal else None
ilerlemedi = [k for k in kanal if str(k["stage"]).lower() not in ("complete", "cancelled")
              and all(str(v).lower() in ("notstarted", "none", "") for v in (k["details"] or {}).values())]
ozet = {"olcum_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "toplam_siparis": len(tum),
        "kanal_siparis": len(kanal), "router_siparis": len(bizim), "son_kanal_siparisi": son,
        "kanal_stage": dict(Counter(str(k["stage"]) for k in kanal)),
        "kanal_ilerlemeyen_acik": [k["id"] for k in ilerlemedi],
        "son_router_siparisi": max((b["created"] or "" for b in bizim), default=None)}
(out / "KANAL_DURUMU.json").write_text(json.dumps({"ozet": ozet, "kanal": kanal, "router": bizim}, ensure_ascii=False, indent=1), encoding="utf-8")
md = ["# Prodigi Etsy kanali durumu (salt okuma)", ""] + [f"- {k}: {v}" for k, v in ozet.items()] + [
    "", "## Kanal siparisleri (yeniden eskiye)", "",
    "| id | created | ref | stage | details | issues | ulke | kalem | actions |", "|---|---|---|---|---|---|---|---|---|"]
for k in kanal:
    md.append(f"| {k['id']} | {k['created']} | {k['mr']} | {k['stage']} | {json.dumps(k['details'])} | {k['issues']} | "
              f"{k['ulke']} | {k['kalem']} | {k.get('actions', '')} |")
md += ["", "## Router siparisleri (etsy-*)", "", "| id | created | ref | stage | issues |", "|---|---|---|---|---|"]
md += [f"| {b['id']} | {b['created']} | {b['mr']} | {b['stage']} | {b['issues']} |" for b in sorted(bizim, key=lambda x: x["created"] or "", reverse=True)]
(out / "KANAL_DURUMU.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md[:12]))
