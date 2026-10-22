#!/usr/bin/env python3
"""SALT OKUMA (Etsy API kotasi harcamaz; statik OAS dosyasi): siparisteki kisisellestirme cevaplari hangi
alanda geliyor (1a) ve siparise dosya yukleyen uc var mi (1b). Cikti: OAS_KISISEL.md + OAS_KISISEL.json."""
import json
import sys
from pathlib import Path

import requests

OAS = "https://www.etsy.com/openapi/generated/oas/3.0.0.json"
out = Path(sys.argv[1] if len(sys.argv) > 1 else "_out/oas_kisisel"); out.mkdir(parents=True, exist_ok=True)
d = requests.get(OAS, timeout=120).json()
S = d["components"]["schemas"]


def sema(ad):
    return next((S[k] for k in S if k == ad or k.endswith("_" + ad) or k.endswith(ad)), None), \
        next((k for k in S if k == ad or k.endswith("_" + ad) or k.endswith(ad)), None)


def coz(x, derinlik=0):
    """$ref'leri 2 seviye acarak alan -> (tip, aciklama)."""
    if derinlik > 3 or not isinstance(x, dict):
        return x
    if "$ref" in x:
        return coz(S.get(x["$ref"].split("/")[-1], {}), derinlik + 1)
    if "allOf" in x:
        return coz(x["allOf"][0], derinlik + 1)
    return x


bulgu = {"oas": OAS}
tr, tr_ad = sema("ShopReceiptTransaction")
alanlar = {}
for k, v in (tr or {}).get("properties", {}).items():
    v2 = coz(v)
    alanlar[k] = {"tip": v2.get("type"), "aciklama": (v2.get("description") or v.get("description") or "")[:300]}
    if v2.get("type") == "array":
        it = coz(v2.get("items") or {})
        alanlar[k]["oge_alanlari"] = {kk: (coz(vv).get("type"), (coz(vv).get("description") or "")[:200])
                                      for kk, vv in (it.get("properties") or {}).items()}
bulgu["transaction_sema"] = tr_ad
bulgu["transaction_alanlari"] = alanlar
bulgu["kisisel_izli_alanlar"] = {k: v for k, v in alanlar.items() if any(t in k.lower() for t in ("personaliz", "variation", "custom"))}
# tum semalarda 'personaliz' gecen alan
bulgu["personaliz_gecen_sema_alanlari"] = sorted({f"{sk}.{pk}" for sk, sv in S.items() for pk in (sv.get("properties") or {})
                                                  if "personaliz" in pk.lower()})
# uclar
uc = []
for p, ops in d["paths"].items():
    for m, op in ops.items():
        if not isinstance(op, dict):
            continue
        metin = (p + " " + str(op.get("operationId")) + " " + (op.get("summary") or "")).lower()
        if "/receipts" in p or "/transactions" in p:
            uc.append({"yontem": m.upper(), "yol": p, "op": op.get("operationId"), "grup": "receipt/transaction"})
        elif m in ("post", "put") and any(t in metin for t in ("file", "upload", "attach")):
            ct = list(((op.get("requestBody") or {}).get("content") or {}).keys())
            uc.append({"yontem": m.upper(), "yol": p, "op": op.get("operationId"), "grup": "dosya/yukleme", "icerik": ct})
bulgu["uclar"] = uc
Path(out / "OAS_KISISEL.json").write_text(json.dumps(bulgu, ensure_ascii=False, indent=1), encoding="utf-8")
md = ["# OAS kisisellestirme (salt okuma, API kotasi yok)", "", f"- kaynak: {OAS}", f"- transaction semasi: {tr_ad}", "",
      "## 1a Transaction'daki kisisellestirme/varyasyon alanlari", ""]
for k, v in bulgu["kisisel_izli_alanlar"].items():
    md.append(f"- `{k}` ({v['tip']}): {v['aciklama']}")
    for kk, (t, a) in (v.get("oge_alanlari") or {}).items():
        md.append(f"  - `{k}[].{kk}` ({t}): {a}")
md += ["", f"- 'personaliz' gecen tum sema alanlari: {bulgu['personaliz_gecen_sema_alanlari']}", "",
       "## Receipt/transaction uclari", ""] + [f"- {u['yontem']} {u['yol']} ({u['op']})" for u in uc if u["grup"] == "receipt/transaction"]
md += ["", "## 1b Dosya/yukleme uclari (tum API)", ""] + [f"- {u['yontem']} {u['yol']} ({u['op']}) {u.get('icerik')}" for u in uc if u["grup"] == "dosya/yukleme"]
md += ["", "## Transaction alanlarinin tamami", "", ", ".join(alanlar)]
Path(out / "OAS_KISISEL.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(md))
