#!/usr/bin/env python3
"""ORNAMENT 78 TASLAK: Rusca baslik/aciklama + olcu niteligi (Serdar 8 Kas "Evet, kodla yazilsin"; yayin Serdar'da, panelde).
Kaynak metin: data/pod/ORN78_RU.csv (claude/kod/ornament_ru_uret_20261107.py ciktisi, sha256 39843f4a..., Lena paketi onayli,
KARARLAR_20261107 RU PAKETI ONAYLI). RU etiket yok (S4). Olcu: 7,6 cm / 2.99 in (S5); nitelik ve degerler OLCU_JSON'dan (Serdar onayi).
Ilan no: Drive TEMP/ORNAMENT_GALERI9_ETSY/YEDEK9.json.

mod=oku  : SALT OKUMA. Kategori (taxonomy 1857) nitelikleri (ad, id, olcekler) + ciftler icin state, mevcut RU, mevcut nitelikler.
mod=kuru : ag/token yok; taklitle yazilacak istekler.
mod=yaz  : cift basina: state draft ve baslik kimligi; PUT /shops/{shop}/listings/{id}/translations/ru (title, description);
           geri okuma (3 deneme); state okuma (draft degilse ACIL inactive + DUR); OLCU_JSON varsa PUT .../properties/{pid};
           geri okuma. updateListing (PATCH) YOK (taslagi yayina alir). Pilot: CANCER_LIBRA once, sonra Serdar'a sorulur.
"""
import argparse
import csv
import hashlib
import html
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, mask  # noqa: E402

KOK = Path(__file__).resolve().parents[2]
RU_CSV = KOK / "data" / "pod" / "ORN78_RU.csv"
RU_SHA = "39843f4af64573ea7db2da91fd7358b505aa1425156bc59ede09784445b7db34"
TAKSONOMI = 1857
KOTA_MIN = 10
KOTA_ILAN = 25
TIRE = re.compile("[‒–—―]")
RU_BEYAN = "При создании изображений мы используем инструменты искусственного интеллекта"


def norm(t):
    return " ".join(html.unescape(str(t or "")).replace("\r\n", "\n").split())


def ru_metin():
    b = open(RU_CSV, "rb").read()
    if hashlib.sha256(b).hexdigest() != RU_SHA:
        raise SystemExit(f"DUR: {RU_CSV.name} sha256 onayli paket degil")
    rows = {r["kod"]: r for r in csv.DictReader(open(RU_CSV, encoding="utf-8"))}
    if len(rows) != 78:
        raise SystemExit(f"DUR: RU satir {len(rows)}")
    for k, r in rows.items():
        if TIRE.search(r["baslik_ru"] + r["aciklama_ru"]) or RU_BEYAN not in r["aciklama_ru"] or len(r["baslik_ru"]) > 140:
            raise SystemExit(f"DUR: RU kontrol {k}")
    return rows


def en_baslik(pair):
    r = [x for x in csv.DictReader(open(KOK / "data" / "pod" / "ORNAMENT78_METIN.csv", encoding="utf-8")) if x["kod"] == pair]
    if len(r) != 1:
        raise SystemExit(f"DUR-ON: METIN {pair}")
    return html.unescape(r[0]["baslik"])


class Kilitli(Etsy):
    """Izinli yazmalar: YALNIZ api.lid icin translations/ru PUT ve properties/{pid} PUT; PATCH yalniz acil state=inactive."""
    lid = None
    pid_izin = frozenset()

    def _izin(self, method, path):
        L = self.lid
        if not L:
            raise SystemExit(f"YASAK yazma (ilan yok): {method} {path}")
        if method == "PUT" and re.match(rf"^/shops/\d+/listings/{L}/translations/ru$", path):
            return
        m = re.match(rf"^/shops/\d+/listings/{L}/properties/(\d+)$", path)
        if method == "PUT" and m and int(m.group(1)) in self.pid_izin:
            return
        if method == "PATCH" and re.match(rf"^/shops/\d+/listings/{L}$", path):
            return
        raise SystemExit(f"YASAK yazma: {method} {path}")

    def _call(self, method, path, **kw):
        if method != "GET":
            self._izin(method, path)
            if method == "PATCH" and kw.get("data") != {"state": "inactive"}:
                raise SystemExit("YASAK: PATCH yalniz acil durum (state=inactive)")
        r = super()._call(method, path, **kw)
        self.kota()
        return r

    def kota(self, esik=KOTA_MIN):
        if self.remaining is not None and str(self.remaining).isdigit() and int(self.remaining) < esik:
            raise SystemExit(f"DUR: kota {self.remaining} < {esik}")


class SaltOkur(Etsy):
    def _call(self, method, path, **kw):
        if method != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)


def oku(api, shop, out, ciftler, Y):
    R = {"nitelikler": [], "ilanlar": {}}
    props = (api.get(f"/seller-taxonomy/nodes/{TAKSONOMI}/properties") or {}).get("results") or []
    for p in props:
        R["nitelikler"].append(dict(property_id=p.get("property_id"), ad=p.get("name"), gorunen=p.get("display_name"),
                                    zorunlu=p.get("is_required"), coklu=p.get("is_multivalued"),
                                    olcekler=[(s.get("scale_id"), s.get("display_name")) for s in p.get("scales") or []],
                                    degerler=[(v.get("value_id"), v.get("name")) for v in p.get("possible_values") or []][:20]))
    for c in ciftler:
        lid = (Y.get(c) or {}).get("listing_id")
        if not str(lid).isdigit():
            R["ilanlar"][c] = {"hata": "listing id yok"}; continue
        L = api.get(f"/listings/{lid}") or {}
        ru = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
        pr = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
        R["ilanlar"][c] = dict(listing_id=lid, state=L.get("state"), ru_baslik=ru.get("title"), ru_aciklama_uzunluk=len(ru.get("description") or ""),
                               nitelik=[(p.get("property_id"), p.get("property_name"), p.get("scale_id"), p.get("values")) for p in pr])
    R["kota"] = api.remaining
    json.dump(R, open(out / "RU_OLCU_OKU.json", "w"), indent=1, ensure_ascii=False)
    print(f"OKU: {len(R['nitelikler'])} nitelik | olcu ile ilgili: "
          f"{[(n['property_id'], n['ad'], n['olcekler']) for n in R['nitelikler'] if re.search(r'width|height|depth|diameter|length|size|dimension', str(n['ad']), re.I)]}")
    for c, x in R["ilanlar"].items():
        print(f"{c}: {x}")
    return R


def yaz(api, shop, out, pair, Y, RU, OLCU):
    R = {"cift": pair, "adimlar": []}
    rf = out / f"RU_{pair}.json"

    def kaydet():
        json.dump(R, open(rf, "w"), indent=1, ensure_ascii=False, default=str)

    lid = (Y.get(pair) or {}).get("listing_id")
    if not str(lid).isdigit():
        raise SystemExit(f"DUR-ON: {pair} listing id yok")
    lid = int(lid)
    r = RU[pair]
    api.lid, api.pid_izin = lid, frozenset(int(o["property_id"]) for o in OLCU)
    api.get(f"/shops/{shop}")
    R["kota_bas"] = api.remaining
    api.kota(KOTA_ILAN + 10)

    def durum(adim, acil=True):
        L = api.get(f"/listings/{lid}") or {}
        st = L.get("state")
        R["adimlar"].append((adim, st, api.remaining)); kaydet()
        print(f"{pair} {adim}: state={st} kota={api.remaining}", flush=True)
        if st == "active" and acil:
            st2 = "?"
            try:
                api.patch(f"/shops/{shop}/listings/{lid}", {"state": "inactive"})
                st2 = (api.get(f"/listings/{lid}") or {}).get("state")
            except BaseException as e:  # noqa: BLE001
                st2 = f"hata {type(e).__name__}: {str(e)[:200]}"
            finally:
                R["adimlar"].append((adim + " ACIL inactive", st2)); kaydet()
                print(f"::error::ACIL: {pair} {adim} sonrasi active -> inactive (simdi {st2}). DUR.", flush=True)
                if st2 != "inactive":
                    print(f"::error::ACIL BASARISIZ: {pair} listing {lid} hala {st2}; Etsy panelinden elle inactive yapilmali.", flush=True)
                raise SystemExit(2)
        if st != "draft":
            kaydet(); raise SystemExit(f"DUR: {pair} state {st} ({adim}); dokunulmadi")
        return L

    L = durum("0 baslangic", acil=False)
    if html.unescape(L.get("title") or "") != en_baslik(pair):
        kaydet(); raise SystemExit(f"DUR: {pair} {lid} baslik METIN ile ayni degil (kimlik)")
    # 1) RU
    mevcut = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
    if norm(mevcut.get("title")) == norm(r["baslik_ru"]) and norm(mevcut.get("description")) == norm(r["aciklama_ru"]):
        R["ru"] = "zaten var"
    else:
        api.put(f"/shops/{shop}/listings/{lid}/translations/ru", {"title": r["baslik_ru"], "description": r["aciklama_ru"]})
        durum("1 RU yazildi")
        ok = False
        for d in range(3):
            time.sleep(0 if not d else 10)
            g = api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True) or {}
            if norm(g.get("title")) == norm(r["baslik_ru"]) and norm(g.get("description")) == norm(r["aciklama_ru"]):
                ok = True; break
        R["ru"] = "PASS" if ok else "FAIL"
        if not ok:
            kaydet(); raise SystemExit(f"FAIL: {pair} RU geri okuma farkli")
    # 2) olcu
    for o in OLCU:
        b = {"value_ids": ",".join(str(i) for i in o.get("value_ids", [])), "values": ",".join(str(v) for v in o["values"])}
        if o.get("scale_id"):
            b["scale_id"] = o["scale_id"]
        api.put(f"/shops/{shop}/listings/{lid}/properties/{o['property_id']}", b)
        durum(f"2 olcu {o['property_id']}")
    pr = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    have = {p.get("property_id"): (p.get("scale_id"), [str(v) for v in p.get("values") or []]) for p in pr}
    K = {"RU": R["ru"] in ("PASS", "zaten var"),
         "olcu": all(have.get(int(o["property_id"])) is not None and [str(v) for v in o["values"]] == have[int(o["property_id"])][1]
                     and (not o.get("scale_id") or have[int(o["property_id"])][0] == o["scale_id"]) for o in OLCU),
         "state draft": durum("3 son").get("state") == "draft"}
    R["kontrol"] = K; R["kota_son"] = api.remaining; kaydet()
    kotu = [k for k, v in K.items() if not v]
    print(f"::warning::{pair} {lid} ru_olcu | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["oku", "yaz"])
    ap.add_argument("--ciftler", default="CANCER_LIBRA")
    a = ap.parse_args()
    out = Path(os.environ.get("OUT", "_out")); out.mkdir(parents=True, exist_ok=True)
    ciftler = [c.strip().upper() for c in re.split(r"[,\s]+", a.ciftler) if c.strip()]
    Y = json.load(open(os.environ["YEDEK"]))
    RU = ru_metin()
    bil = [c for c in ciftler if c not in RU]
    if bil:
        raise SystemExit(f"DUR: bilinmeyen cift {bil}")
    OLCU = json.load(open(os.environ["OLCU_JSON"])) if os.environ.get("OLCU_JSON") and Path(os.environ["OLCU_JSON"]).exists() else []
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out, ciftler, Y); return
    if os.environ.get("PILOT_ONAY") != "1" and ciftler != ["CANCER_LIBRA"]:
        raise SystemExit("DUR: once CANCER_LIBRA pilotu (PILOT_ONAY=1 Serdar onayindan sonra)")
    api = Kilitli(store)
    t0 = time.time()
    for i, c in enumerate(ciftler, 1):
        api.lid = None
        yaz(api, shop, out, c, Y, RU, OLCU)
        g = time.time() - t0
        print(f"ETA [{i}/{len(ciftler)}] {c} | gecen {g:.0f} sn | kalan ~{g / i * (len(ciftler) - i):.0f} sn | %{100 * i // len(ciftler)} | kota {api.remaining}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if isinstance(e.code, str):
            print(f"::error::{e.code[:900]}")
            raise SystemExit(1)
        raise
