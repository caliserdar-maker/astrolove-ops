#!/usr/bin/env python3
"""Onaylanan dijital aciklamayi kalan dijital ilanlara uygular (Mo 14 Eyl 2026).

Sablon: 4552211376'da onaylanan metin. Ilan basina SADECE uc sey degisir:
  1) acilis cumlesindeki iki burc adi  (ILANIN BASLIGINDAN dogrulanir)
  2) THE ARTWORK'teki edisyon cumlesi  ("This is the <EDITION> edition, <TARIF>.")
  3) PREFER IT READY TO HANG'deki POD linki (DIGITAL_POD_MAP.csv'deki eslemeden)
Baska hicbir kelime degismez; uretilen metinde uzun tire varsa o ilan ATLANIR.

Ilan basina: yedek (tum alanlar + envanter + galeri + varyasyon + video) ->
yalniz description PATCH -> geri okuma (aciklama birebir [HTML kacislari cozulerek],
baslik/etiket/materials/fiyat/envanter/bolum/gorseller/varyasyon/video ayni,
state active, uzun tire yok). Gecmeyen ilan atlanir, kosu surer.
Kota --quota-min altina inince DURUR; durum CSV'si her ilanda yazilir (resume).

Kullanim:
  digital_desc_batch.py --map DIGITAL_POD_MAP.csv --template T.txt --out OUT
      --state S.csv [--skip 4552211376] [--limit N] [--apply] [--quota-min 200]
"""
import argparse
import csv
import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log, mask  # noqa: E402
import pod_desc_set as DS  # noqa: E402
from pod_desc_batch import basliktan_burclar  # noqa: E402

CAPA_BURC = "merges the Aquarius and Aquarius glyphs"
CAPA_EDISYON = ("This is the Champagne Ivory edition, a warm ivory background with "
                "bronze toned artwork.")
CAPA_LINK = "https://www.etsy.com/listing/4570110121/aquarius-and-aquarius-zodiac-wall-art"
BURC_KALIP = "merges the {a} and {b} glyphs"
EDISYON_KALIP = "This is the {ed} edition, {tarif}."
TARIF = {
    "Champagne Ivory": "a warm ivory background with bronze toned artwork",
    "Pure White": "a pure white background with radiant gold toned artwork",
    "Warm Parchment": "a warm parchment background with sepia and copper toned artwork",
    "Midnight Blue": "a deep navy background with warm gold toned artwork and fine star details",
    "Deep Black": "a deep black background with warm gold toned artwork",
}
SUTUN = ["digital_id", "pair", "edisyon", "burclar", "pod_link", "sonuc", "not", "yedek",
         "kota", "ts_utc"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sablon_dogrula(sablon):
    for capa in (CAPA_BURC, CAPA_EDISYON, CAPA_LINK):
        if sablon.count(capa) != 1:
            raise SystemExit(f"HATA: sablonda capa {capa[:50]!r} {sablon.count(capa)} kez - DUR")
    if CAPA_EDISYON != EDISYON_KALIP.format(ed="Champagne Ivory", tarif=TARIF["Champagne Ivory"]):
        raise SystemExit("HATA: edisyon capasi TARIF tablosuyla uyusmuyor - DUR")


def metin_uret(sablon, burclar, edisyon, link):
    if edisyon not in TARIF:
        raise SystemExit(f"HATA: bilinmeyen edisyon {edisyon!r}")
    yeni = sablon.replace(CAPA_BURC, BURC_KALIP.format(a=burclar[0], b=burclar[1]))
    yeni = yeni.replace(CAPA_EDISYON, EDISYON_KALIP.format(ed=edisyon, tarif=TARIF[edisyon]))
    yeni = yeni.replace(CAPA_LINK, link)
    tire = {DS.UZUN_TIRE[c]: yeni.count(c) for c in DS.UZUN_TIRE if c in yeni}
    if tire:
        raise SystemExit(f"HATA: uretilen metinde uzun tire: {tire} - DUR")
    for beklenen in (BURC_KALIP.format(a=burclar[0], b=burclar[1]),
                     EDISYON_KALIP.format(ed=edisyon, tarif=TARIF[edisyon]), link):
        if yeni.count(beklenen) != 1:
            raise SystemExit(f"HATA: uretilen metinde {beklenen[:40]!r} {yeni.count(beklenen)} kez")
    return yeni


def islet(api, shop, lid, L, yeni, out, apply_et):
    """Tek ilan: yedek + (gerekirse) PATCH + geri okuma. L onceden okunmus ilan."""
    once = {"ozet": DS.ozet(L), "description": L.get("description"),
            "galeri": DS.galeri(api, lid), "varyasyon_gorselleri": DS.var_img(api, shop, lid),
            "videolar": DS.videolar(api, lid), "envanter_fiyat": DS.envanter(api, lid)}
    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    yedek = f"backup_digital_{lid}_{zaman}.json"
    (out / yedek).write_text(json.dumps({"alindi_utc": zaman, "listing_id": lid,
                                         "tam_listing": L, **once}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    if DS.esit(L.get("description") or "", yeni) != "farkli":
        return "DEGISIM YOK", "aciklama zaten ayni", yedek
    if L.get("state") != "active":
        return "ATLANDI", f"state={L.get('state')} (active degil)", yedek
    if not apply_et:
        return "DRY-RUN", f"eski {len(L.get('description') or '')} -> yeni {len(yeni)} karakter", yedek
    api.patch(f"/shops/{shop}/listings/{lid}", {"description": yeni})
    time.sleep(2)
    L2 = api.get(f"/listings/{lid}") or {}
    yazilan = L2.get("description") or ""
    metin = DS.esit(yazilan, yeni)
    kontrol = {
        "aciklama_birebir": metin in ("tam", "sondaki_newline", "html_kacis"),
        "uzun_tire_yok": not any(c in yazilan for c in DS.UZUN_TIRE),
        "baslik_ayni": L2.get("title") == L.get("title"),
        "etiketler_ayni": (L2.get("tags") or []) == (L.get("tags") or []),
        "materials_ayni": (L2.get("materials") or []) == (L.get("materials") or []),
        "fiyat_ayni": (L2.get("price") or {}) == (L.get("price") or {}),
        "envanter_fiyat_ayni": DS.envanter(api, lid) == once["envanter_fiyat"],
        "bolum_ayni": L2.get("shop_section_id") == L.get("shop_section_id"),
        "gorseller_ayni": DS.galeri(api, lid) == once["galeri"],
        "varyasyon_gorselleri_ayni": DS.var_img(api, shop, lid) == once["varyasyon_gorselleri"],
        "video_ayni": DS.videolar(api, lid) == once["videolar"],
        "state_active": L2.get("state") == "active",
    }
    kotu = [k for k, v in kontrol.items() if not v]
    return ("PASS", f"metin {metin}", yedek) if not kotu else ("FAIL", f"kontrol: {kotu}", yedek)


def hedefler(path, skip, limit):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lid = (r.get("digital_id") or "").strip()
            if lid.isdigit() and lid not in skip:
                out.append(r)
    out.sort(key=lambda r: (r.get("pair", ""), r.get("edisyon", "")))
    return out[:limit] if limit else out


def durum_yaz(path, satirlar):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN, extrasaction="ignore")
        w.writeheader()
        for s in satirlar:
            w.writerow({k: s.get(k, "") for k in SUTUN})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--skip", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=30)
    ap.add_argument("--state-remote", default="",
                    help="verilirse durum CSV'si her ilandan sonra rclone ile buraya kopyalanir")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sablon = pathlib.Path(a.template).read_text(encoding="utf-8")
    sablon_dogrula(sablon)
    ilanlar = hedefler(a.map, {x for x in a.skip.split(",") if x}, a.limit)
    satirlar = []
    if pathlib.Path(a.state).exists():
        satirlar = list(csv.DictReader(open(a.state, newline="", encoding="utf-8")))
    bitti = {r["digital_id"] for r in satirlar if r.get("sonuc") in ("PASS", "DEGISIM YOK")}
    log(f"{len(ilanlar)} ilan | sablon {len(sablon)} karakter | tamamlanmis {len(bitti)}")

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    t0, durdu = time.time(), None

    for i, r in enumerate(ilanlar, 1):
        lid, pair, ed = r["digital_id"], r.get("pair", ""), r.get("edisyon", "")
        gecen = time.time() - t0
        kalan = gecen / (i - 1) * (len(ilanlar) - i + 1) if i > 1 else 0
        log(f"[{i}/{len(ilanlar)} %{(i-1)/len(ilanlar)*100:.0f}] {pair} / {ed} ({lid}) | "
            f"gecen {gecen/60:.1f} dk, kalan ~{kalan/60:.1f} dk | kota {api.remaining}")
        if lid in bitti:
            log("    zaten islenmis, atlandi")
            continue
        if api.remaining is not None and str(api.remaining).isdigit() \
                and int(api.remaining) < a.quota_min:
            durdu = (f"kota {api.remaining} < {a.quota_min}; {i-1}/{len(ilanlar)} ilandan sonra "
                     f"durdu")
            log(f"DUR: {durdu}")
            break
        satir = {"digital_id": lid, "pair": pair, "edisyon": ed, "ts_utc": simdi()}
        try:
            if (r.get("eslesme") or "") != "AYNI":
                raise SystemExit(f"esleme {r.get('eslesme')!r} (AYNI degil)")
            link = (r.get("link_url") or "").strip()
            if not link.startswith("https://www.etsy.com/listing/"):
                raise SystemExit(f"POD linki gecersiz: {link[:60]!r}")
            L = api.get(f"/listings/{lid}") or {}
            baslik = L.get("title") or ""
            burclar = basliktan_burclar(baslik, pair)
            if not burclar:
                raise SystemExit(f"basliktan burc cikarilamadi: {baslik[:70]!r}")
            if ed.lower() not in baslik.lower():
                raise SystemExit(f"baslikta edisyon yok ({ed!r}): {baslik[:70]!r}")
            yeni = metin_uret(sablon, burclar, ed, link)
            durum, notu, yedek = islet(api, shop, lid, L, yeni, out, a.apply)
            satir.update({"burclar": " + ".join(burclar), "pod_link": link, "sonuc": durum,
                          "not": notu, "yedek": yedek})
            log(f"    {satir['burclar']} / {ed} -> {durum} ({notu})")
        except SystemExit as ex:
            satir.update({"sonuc": "ATLANDI", "not": str(ex)[:150]})
            log(f"    ATLANDI: {ex}")
        except Exception as ex:                       # bir ilan kosuyu durdurmaz
            satir.update({"sonuc": "ATLANDI", "not": f"{type(ex).__name__}: {str(ex)[:120]}"})
            log(f"    ATLANDI: {type(ex).__name__}: {ex}")
        satir["kota"] = api.remaining
        satirlar = [x for x in satirlar if x.get("digital_id") != lid] + [satir]
        durum_yaz(a.state, satirlar)
        if a.state_remote:
            subprocess.run(["rclone", "copyto", a.state, a.state_remote],
                           capture_output=True, text=True)

    durum_yaz(a.state, satirlar)
    say = {}
    for x in satirlar:
        say[x.get("sonuc", "?")] = say.get(x.get("sonuc", "?"), 0) + 1
    islenen = {x.get("digital_id") for x in satirlar}
    ozet = {"hedef": len(ilanlar), "sonuclar": say, "durdu": durdu,
            "atlanan": sorted(x["digital_id"] for x in satirlar
                              if x.get("sonuc") in ("ATLANDI", "FAIL")),
            "islenmemis": sorted(x["digital_id"] for x in ilanlar
                                 if x["digital_id"] not in islenen),
            "sure_dk": round((time.time() - t0) / 60, 1), "kota": api.remaining,
            "api_cagrisi": api.calls}
    (out / "DIGITAL_DESC_OZET.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                                encoding="utf-8")
    log(f"OZET: {json.dumps(ozet, ensure_ascii=False)}")
    if getattr(st, "updated", False):
        st.write()


if __name__ == "__main__":
    main()
