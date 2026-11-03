#!/usr/bin/env python3
"""SALT OKUMA (Etsy'ye yazim YOK): 78 wall art (poster) ilaninin canli videosu + 1. gorsel (kapak) kaydi (Merkez 3 Kas, Serdar Soru 10 A).
Istek: /listings/batch (100'luk, includes=Images,Videos); batch video vermezse ilan basina /listings/{id}/videos. Kare indirme / olcum
BURADA YAPILMAZ (KILIT SURESI): wa_video_kare.py kilitsiz ayri is akisinda. Cikti --out: VIDEO_KAYIT.json, OZET.json."""
import argparse, csv, json, os, pathlib, sys
KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402

ONAR18 = {"4570110121", "4570110641", "4570125580", "4570126104", "4570112095", "4570127160", "4570113157", "4570113675", "4570128546",
          "4570114301", "4570150148", "4570136319", "4570151370", "4570151950", "4570152410", "4570152820", "4570031205", "4570153208"}


class SaltOku(E.Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)


def calis(api, ids, out):
    sira = list(ids)
    L = {}
    for i in range(0, len(sira), 100):
        j = api.get("/listings/batch", params={"listing_ids": ",".join(sira[i:i + 100]), "includes": "Images,Videos"}) or {}
        for x in j.get("results") or []:
            L[str(x["listing_id"])] = x
    kayit, tekil = {}, 0
    for lid in ids:
        x = L.get(lid) or {}
        vids = x.get("videos")
        if vids is None:
            vids = (api.get(f"/listings/{lid}/videos", ok404=True) or {}).get("results") or []
            tekil += 1
        if isinstance(vids, dict):
            vids = vids.get("results") or list(vids.values())
        img = sorted(x.get("images") or [], key=lambda k: k.get("rank") or 0)
        k1 = img[0] if img else {}
        kayit[lid] = dict(cift=ids[lid], state=x.get("state"), onar18=lid in ONAR18,
                          videolar=[{k: v.get(k) for k in v if not isinstance(v.get(k), (dict, list))} for v in vids if isinstance(v, dict)],
                          kapak=dict(listing_image_id=k1.get("listing_image_id"), rank=k1.get("rank"), url_fullxfull=k1.get("url_fullxfull"),
                                     full_width=k1.get("full_width"), full_height=k1.get("full_height"), alt_text=k1.get("alt_text")))
    out.mkdir(parents=True, exist_ok=True)
    (out / "VIDEO_KAYIT.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    oz = dict(ilan=len(ids), videolu=sum(1 for v in kayit.values() if v["videolar"]), video_tekil_okuma=tekil, istek=api.calls, kota=api.remaining)
    (out / "OZET.json").write_text(json.dumps(oz, indent=1), encoding="utf-8")
    print(f"::notice::WA VIDEO OKU: {oz}", flush=True)
    return oz


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args(argv)
    ids = {r["listing_id"].strip(): r["cift"] for r in csv.DictReader(open(KOK.parents[1] / "data/pod/pod78_ids.csv", encoding="utf-8-sig"))}
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s)
    st = E.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = SaltOku(st)
    calis(api, ids, pathlib.Path(a.out))


if __name__ == "__main__":
    main()
