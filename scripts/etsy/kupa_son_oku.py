#!/usr/bin/env python3
"""KUPA taslak SON OKUMA (salt okuma; Serdar 18 Eki). Yazma yok (SaltOkur: her yazma cagrisi programi durdurur).
Okunan: state, secenek (envanter urun) sayisi, gorsel sayisi + rank, video, kisisellestirme, stil kapaklari, kota.
Ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE, LISTING_ID, OUT. Cikti: OUT/KUPA_SON_OKU.json
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import TokenStore, mask  # noqa: E402
from kupa_taslak import SaltOkur  # noqa: E402


def main():
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = SaltOkur(store)
    shop, lid = os.environ["ETSY_SHOP_ID"], int(os.environ["LISTING_ID"])
    L = api.get(f"/listings/{lid}") or {}
    inv = api.get(f"/listings/{lid}/inventory") or {}
    ims = sorted(((api.get(f"/listings/{lid}/images") or {}).get("results") or []), key=lambda x: x.get("rank") or 0)
    vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
    per = (api.get(f"/listings/{lid}/personalization", ok404=True) or {}).get("personalization_questions") or []
    vis = (api.get(f"/shops/{shop}/listings/{lid}/variation-images", ok404=True) or {}).get("results") or []
    R = dict(listing_id=lid, state=L.get("state"), secenek=len(inv.get("products") or []),
             gorsel=len(ims), gorsel_rank=[x.get("rank") for x in ims], video=len(vids),
             video_durum=[(v.get("video_id"), v.get("video_state")) for v in vids],
             kisisellestirme=[dict(soru=q.get("question_text"), tip=q.get("question_type"), zorunlu=q.get("required"),
                                   max=q.get("max_allowed_characters"), talimat=q.get("instructions")) for q in per],
             stil_kapak=len(vis), kota=api.remaining, cagri=api.calls)
    json.dump(R, open(out / "KUPA_SON_OKU.json", "w"), indent=1, ensure_ascii=False)
    print(f"::warning::SON OKUMA {lid} state={R['state']} | secenek {R['secenek']} | gorsel {R['gorsel']} {R['gorsel_rank']} | "
          f"video {R['video']} {R['video_durum']} | kisisel {[(q['tip'], q['zorunlu'], q['max']) for q in R['kisisellestirme']]} | "
          f"stil kapak {R['stil_kapak']} | kota {R['kota']}")


if __name__ == "__main__":
    main()
