#!/usr/bin/env python3
"""DESEN YENIDEN URETIM (SALT OKUMA; PLAN.md KAYIT 22 Eki yontemi). Etsy'ye / Drive'a yazma YOK (cikti klasoru haric).
Musteri desen listesi kaynaktan yeniden uretilir; DEGERLER HICBIR YERE YAZILMAZ: her desen yalniz tuzlu sha256 olarak
<out>/HASH.txt'ye (Drive sahip-ozel TEMP) gider, log'a yalniz tur basina sayi.
Kaynaklar: Etsy getShopReceipts (tum makbuzlar) -> receipt_id, alici adi (+ parcalar), Personalization degerleri (+ satir /
virgul parcalari), message_from_buyer, gift_message, shipments tracking_code; turetilmis SIPARIS_<son4>, "A / B", "A_B".
Drive: --drive-json (rclone lsjson ciktilari) -> musteri klasoru kimlikleri. Test makbuzlari disarida.
Kullanim: desen_uret.py --tuz HEX --out OUT [--drive-json a.json,b.json]"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "etsy"))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

TEST = re.compile(r"^(9000000\d{3}|999001|900000000\d|99000\d{5}|4000000001|1000000001)$")


def norm(v):
    return " ".join(str(v or "").split()).casefold()


def parcalar(v):
    v = str(v or "")
    out = {v}
    for ayirici in ("\n", ",", ";"):
        out |= {p for p in v.split(ayirici)}
    out |= {w for w in re.split(r"[^\w']+", v) if len(w) >= 3}
    return {p.strip() for p in out if len(p.strip()) >= 3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuz", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--drive-json", default="")
    a = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{16,64}", a.tuz):
        raise SystemExit("HATA: tuz hex olmali")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api, shop = Etsy(store), os.environ["ETSY_SHOP_ID"]
    desen, tur = set(), Counter()

    def ekle(t, v):
        n = norm(v)
        if len(n) >= 3 and n not in desen:
            desen.add(n); tur[t] += 1

    ofs, makbuz, test = 0, 0, 0
    while True:
        d = api.get(f"/shops/{shop}/receipts", params={"limit": 100, "offset": ofs}) or {}
        r = d.get("results") or []
        for rc in r:
            rid = str(rc.get("receipt_id") or "")
            if TEST.match(rid):
                test += 1
                continue
            makbuz += 1
            ekle("receipt", rid); ekle("siparis_klasor", f"SIPARIS_{rid[-4:]}")
            for p in parcalar(rc.get("name")):
                ekle("alici_adi", p)
            for alan in ("message_from_buyer", "gift_message"):
                for p in parcalar(rc.get(alan)):
                    ekle("mesaj", p)
            for sh in rc.get("shipments") or []:
                ekle("takip", sh.get("tracking_code"))
            for t in rc.get("transactions") or []:
                isim = []
                for v in t.get("variations") or []:
                    if "personal" in str(v.get("formatted_name") or "").casefold():
                        val = str(v.get("formatted_value") or "")
                        for p in parcalar(val):
                            ekle("kisisellestirme", p)
                        isim += [x.strip() for x in re.split(r"[\n,;]", val) if x.strip()]
                if len(isim) >= 2:
                    a1, a2 = isim[0], isim[1]
                    for f in (str.upper, str.title):
                        ekle("isim_cifti", f"{f(a1)} / {f(a2)}"); ekle("isim_cifti", f"{f(a1)}_{f(a2)}")
        ofs += len(r)
        if not r or ofs >= (d.get("count") or 0):
            break
    for jf in [x for x in a.drive_json.split(",") if x]:
        for e in json.load(open(jf)):
            if e.get("IsDir") and e.get("ID"):
                ekle("drive_kimlik", e["ID"])
    with open(out / "HASH.txt", "w") as f:
        for n in sorted(desen):
            f.write(hashlib.sha256((a.tuz + n).encode()).hexdigest() + "\n")
    print(f"DESEN_URET makbuz {makbuz} (test disarida {test}) | desen {len(desen)} | tur {dict(tur)} | istek {api.calls} | kota {api.remaining}")


if __name__ == "__main__":
    main()
