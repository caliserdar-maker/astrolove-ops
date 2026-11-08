#!/usr/bin/env python3
"""ORNAMENT 78 TASLAK: Rusca baslik/aciklama + olcu niteligi (Serdar 8 Kas "Evet, kodla yazilsin"; yayin Serdar'da, panelde).
Kaynak metin: data/pod/ORN78_RU.csv (claude/kod/ornament_ru_uret_20261107.py ciktisi, sha256 39843f4a..., Lena paketi onayli,
KARARLAR_20261107 RU PAKETI ONAYLI). RU etiket yok (S4). Olcu: 7,6 cm / 2.99 in (S5); nitelik ve degerler OLCU_JSON'dan (Serdar onayi).
Ilan no: Drive TEMP/ORNAMENT_GALERI9_ETSY/YEDEK9.json.
Inceleme 8 Kas (ad6ff444) duzeltmeleri: OLCU_JSON zorunlu + sha sabit; RU yoksa POST, varsa PUT; RU geri okuma tam (bicim kaybi FAIL);
olcu karsilastirma sayisal + ham properties ciktiya; coklu yazimda CANCER_LIBRA pilotu once salt okumayla dogrulanir.

mod=oku  : SALT OKUMA. Kategori (taxonomy 1857) nitelikleri (ad, id, olcekler) + ciftler icin state, mevcut RU, mevcut nitelikler.
mod=yaz  : cift basina: state draft ve baslik kimligi; PUT /shops/{shop}/listings/{id}/translations/ru (title, description);
           (RU yoksa POST); geri okuma (3 deneme); state okuma (draft degilse ACIL inactive + DUR); PUT .../properties/{pid};
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
OLCU_SHA = "b72f770f6a06ae275f4bd28d8235703c297ea63df15ee2ffaaae076996e2db66"  # docs/ornament/ORN_OLCU.json (Serdar 8 Kas: W 2.99 in, H 2.99 in, D 0.1 in)
PILOT = "CANCER_LIBRA"
TAKSONOMI = 1857
KOTA_MIN = 10
KOTA_ILAN = 25
TIRE = re.compile("[‒–—―]")
RU_BEYAN = "При создании изображений мы используем инструменты искусственного интеллекта"


def norm(t):
    return " ".join(html.unescape(str(t or "")).replace("\r\n", "\n").split())


def tam(t):
    return html.unescape(str(t or "")).replace("\r\n", "\n").strip()


def ru_esit(g, r):
    """'tam': birebir; 'bicim': yalniz bosluk/satir sonu farki (FAIL sayilir); False: farkli."""
    g = g or {}
    if tam(g.get("title")) == tam(r["baslik_ru"]) and tam(g.get("description")) == tam(r["aciklama_ru"]):
        return "tam"
    if norm(g.get("title")) == norm(r["baslik_ru"]) and norm(g.get("description")) == norm(r["aciklama_ru"]):
        return "bicim"
    return False


def olcu_yukle(yol):
    if not yol or not Path(yol).exists():
        raise SystemExit(f"DUR: OLCU_JSON yok ({yol}); olcu yazilmadan RU de yazilmaz")
    b = open(yol, "rb").read()
    if hashlib.sha256(b).hexdigest() != OLCU_SHA:
        raise SystemExit("DUR: OLCU_JSON sha256 onayli degil")
    o = json.loads(b)
    if not o or any(not x.get("values") or not str(x.get("property_id", "")).isdigit() for x in o):
        raise SystemExit("DUR: OLCU_JSON bos ya da eksik")
    return o


def sayi(v):
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def olcu_esit(pr, OLCU):
    have = {int(p.get("property_id")): p for p in pr if str(p.get("property_id", "")).isdigit()}
    for o in OLCU:
        p = have.get(int(o["property_id"]))
        if p is None:
            return False
        a = [sayi(v) for v in p.get("values") or []]
        b = [sayi(v) for v in o["values"]]
        if None in a or len(a) != len(b) or any(abs(x - y) > 1e-6 for x, y in zip(a, b)):
            return False
        if o.get("scale_id") and p.get("scale_id") != o["scale_id"]:
            return False
    return True


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
    """Izinli yazmalar: YALNIZ api.lid icin translations/ru PUT/POST ve properties/{pid} PUT; PATCH yalniz acil state=inactive."""
    lid = None
    pid_izin = frozenset()

    def _izin(self, method, path):
        L = self.lid
        if not L:
            raise SystemExit(f"YASAK yazma (ilan yok): {method} {path}")
        if method in ("PUT", "POST") and re.match(rf"^/shops/\d+/listings/{L}/translations/ru$", path):
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
    # 1) RU (yoksa POST, varsa PUT; pod_listing_create:614 olculmus yol)
    tp = f"/shops/{shop}/listings/{lid}/translations/ru"
    mevcut = api.get(tp, ok404=True)
    if ru_esit(mevcut, r) == "tam":
        R["ru"] = "zaten var"
    else:
        yol = "PUT" if mevcut is not None else "POST"
        R["ru_yol"] = yol
        (api.put if yol == "PUT" else api.post)(tp, {"title": r["baslik_ru"], "description": r["aciklama_ru"]})
        durum(f"1 RU yazildi ({yol})")
        sonuc = False
        for d in range(3):
            time.sleep(0 if not d else 10)
            sonuc = ru_esit(api.get(tp, ok404=True), r)
            if sonuc == "tam":
                break
        R["ru"] = "PASS" if sonuc == "tam" else ("FAIL bicim (satir sonu/bosluk farki)" if sonuc == "bicim" else "FAIL")
        if sonuc != "tam":
            kaydet(); raise SystemExit(f"FAIL: {pair} RU geri okuma farkli ({R['ru']})")
    # 2) olcu
    for o in OLCU:
        b = {"value_ids": ",".join(str(i) for i in o.get("value_ids", [])), "values": ",".join(str(v) for v in o["values"])}
        if o.get("scale_id"):
            b["scale_id"] = o["scale_id"]
        api.put(f"/shops/{shop}/listings/{lid}/properties/{o['property_id']}", b)
        durum(f"2 olcu {o['property_id']}")
    pr = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    R["properties_ham"] = [p for p in pr if int(p.get("property_id") or 0) in api.pid_izin]
    print(f"{pair} properties ham: {R['properties_ham']}", flush=True)
    K = {"RU": R["ru"] in ("PASS", "zaten var"),
         "olcu": bool(OLCU) and olcu_esit(pr, OLCU),
         "state draft": durum("3 son").get("state") == "draft"}
    R["kontrol"] = K; R["kota_son"] = api.remaining; kaydet()
    kotu = [k for k, v in K.items() if not v]
    print(f"::warning::{pair} {lid} ru_olcu | kontrol {len(K) - len(kotu)}/{len(K)} | FAIL {kotu} | kota {R['kota_bas']} -> {R['kota_son']}")
    if kotu:
        raise SystemExit(f"FAIL kontrol {pair}: {kotu}")
    return R


def pilot_dogru(api, shop, Y, RU, OLCU):
    """Salt okuma: CANCER_LIBRA taslak, RU tam ve olcu esit mi."""
    lid = (Y.get(PILOT) or {}).get("listing_id")
    if not str(lid).isdigit():
        return False, "pilot listing id yok"
    st = (api.get(f"/listings/{lid}") or {}).get("state")
    ru = ru_esit(api.get(f"/shops/{shop}/listings/{lid}/translations/ru", ok404=True), RU[PILOT])
    pr = (api.get(f"/shops/{shop}/listings/{lid}/properties") or {}).get("results") or []
    ol = olcu_esit(pr, OLCU)
    return (st == "draft" and ru == "tam" and ol), f"state={st} ru={ru} olcu={ol}"


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
    shop = os.environ.get("ETSY_SHOP_ID", "39729443")
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    if a.mod == "oku":
        oku(SaltOkur(store), shop, out, ciftler, Y); return
    OLCU = olcu_yukle(os.environ.get("OLCU_JSON"))
    api = Kilitli(store)
    if ciftler != [PILOT]:
        if os.environ.get("PILOT_ONAY") != "1":
            raise SystemExit("DUR: once CANCER_LIBRA pilotu (PILOT_ONAY=1 Serdar onayindan sonra)")
        ok, neden = pilot_dogru(api, shop, Y, RU, OLCU)
        print(f"PILOT {PILOT}: {neden}", flush=True)
        if not ok:
            raise SystemExit(f"DUR: pilot {PILOT} dogrulanmadi ({neden})")
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
