#!/usr/bin/env python3
"""77 POD ilanina onaylanan aciklamayi uygular (Mo 14 Eyl 2026).

Metin, onaylanan sablonun birebir aynisidir; SADECE acilis cumlesindeki iki burc
adi degisir:  "merges the <SIGN1> and <SIGN2> glyphs"
Burc adlari cift adindan turetilir ve ILANIN BASLIGINDAN dogrulanir: basliktaki
yazim ve sira kullanilir. Baslikta iki ad bulunamazsa o ilan ATLANIR.

Ilan basina: yedek (tum alanlar) -> yalniz description PATCH -> geri okuma
(aciklama birebir [HTML kacislari cozulerek], baslik/etiket/fiyat/envanter
fiyati/bolum/gorseller/varyasyon baglantilari/video ayni, state active,
uzun tire yok). Gecmezse o ilan atlanir, kosu surer.

Kullanim:
  pod_desc_batch.py --pod-state POD.csv --template T.txt --out OUT --state S.csv
      [--skip 4570110121] [--limit N] [--apply] [--quota-min 400]
"""
import argparse
import csv
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import Etsy, TokenStore, log  # noqa: E402
import pod_desc_set as DS  # noqa: E402

BURCLAR = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
           "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
CAPA = "merges the {a} and {b} glyphs"
SABLON_BURC = ("Aquarius", "Aquarius")        # sablon dosyasindaki cift
SUTUN = ["pair", "listing_id", "burclar", "sonuc", "not", "yedek", "kota", "ts_utc"]


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def pod_state(path, skip, limit):
    out = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if (r.get("stage") or "") == "verified" and (r.get("listing_id") or "").isdigit() \
                    and r["listing_id"] not in skip:
                out.append((r["pair"], r["listing_id"]))
    out.sort()
    return out[:limit] if limit else out


def basliktan_burclar(baslik, cift):
    """Basliktaki yazim ve sirayla iki burc adi; cift adiyla uyusmazsa None."""
    bulunan = []
    i = 0
    while i < len(baslik) and len(bulunan) < 2:
        for b in BURCLAR:
            if baslik.startswith(b, i) and not baslik[i + len(b):i + len(b) + 1].isalpha():
                bulunan.append(b)
                i += len(b) - 1
                break
        i += 1
    beklenen = [p.capitalize() for p in cift.split("_")]
    if len(bulunan) != 2 or sorted(bulunan) != sorted(beklenen):
        return None
    return tuple(bulunan)


def metin_uret(sablon, burclar):
    eski = CAPA.format(a=SABLON_BURC[0], b=SABLON_BURC[1])
    if sablon.count(eski) != 1:
        raise SystemExit(f"HATA: sablonda capa {eski!r} {sablon.count(eski)} kez - DUR")
    yeni = sablon.replace(eski, CAPA.format(a=burclar[0], b=burclar[1]))
    tire = {DS.UZUN_TIRE[c]: yeni.count(c) for c in DS.UZUN_TIRE if c in yeni}
    if tire:
        raise SystemExit(f"HATA: uretilen metinde uzun tire: {tire} - DUR")
    return yeni


def durum_yaz(path, satirlar):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SUTUN)
        w.writeheader()
        for s in satirlar:
            w.writerow({k: s.get(k, "") for k in SUTUN})


def islet(api, shop, lid, yeni, out, apply_et):
    """Tek ilan: yedek + (gerekirse) PATCH + geri okuma. Donus: (durum, not, yedek_adi)."""
    L = api.get(f"/listings/{lid}") or {}
    once = {"ozet": DS.ozet(L), "description": L.get("description"),
            "galeri": DS.galeri(api, lid), "varyasyon_gorselleri": DS.var_img(api, shop, lid),
            "videolar": DS.videolar(api, lid), "envanter_fiyat": DS.envanter(api, lid)}
    zaman = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    yedek = f"backup_desc_{lid}_{zaman}.json"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pod-state", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--skip", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--quota-min", type=int, default=400)
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sablon = pathlib.Path(a.template).read_text(encoding="utf-8")
    ciftler = pod_state(a.pod_state, {x for x in a.skip.split(",") if x}, a.limit)
    satirlar = []
    if pathlib.Path(a.state).exists():
        satirlar = list(csv.DictReader(open(a.state, newline="", encoding="utf-8")))
    bitti = {r["pair"] for r in satirlar if r.get("sonuc") in ("PASS", "DEGISIM YOK")}
    log(f"{len(ciftler)} ilan | sablon {len(sablon)} karakter | tamamlanmis {len(bitti)}")

    st = TokenStore(os.environ["TOKEN_FILE"], os.environ.get("ETSY_API_KEY"),
                    os.environ.get("ETSY_SHARED_SECRET"))
    api = Etsy(st)
    shop = os.environ["ETSY_SHOP_ID"]
    t0 = time.time()

    for i, (pair, lid) in enumerate(ciftler, 1):
        gecen = time.time() - t0
        kalan = gecen / (i - 1) * (len(ciftler) - i + 1) if i > 1 else 0
        log(f"[{i}/{len(ciftler)} %{(i-1)/len(ciftler)*100:.0f}] {pair} ({lid}) | "
            f"gecen {gecen/60:.1f} dk, kalan ~{kalan/60:.1f} dk | kota {api.remaining}")
        if pair in bitti:
            log("    zaten islenmis, atlandi")
            continue
        satir = {"pair": pair, "listing_id": lid, "ts_utc": simdi()}
        try:
            if api.remaining is not None and str(api.remaining).isdigit() \
                    and int(api.remaining) < a.quota_min:
                log(f"DUR: kota {api.remaining} < {a.quota_min}. Kalan ilanlar islenmedi.")
                break
            L = api.get(f"/listings/{lid}") or {}
            burclar = basliktan_burclar(L.get("title") or "", pair)
            if not burclar:
                satir.update({"sonuc": "ATLANDI",
                              "not": f"basliktan burc cikarilamadi: {(L.get('title') or '')[:70]!r}"})
            else:
                yeni = metin_uret(sablon, burclar)
                durum, notu, yedek = islet(api, shop, lid, yeni, out, a.apply)
                satir.update({"burclar": " + ".join(burclar), "sonuc": durum, "not": notu,
                              "yedek": yedek})
            satir["kota"] = api.remaining
            log(f"    {satir.get('burclar', '-')} -> {satir['sonuc']} ({satir.get('not', '')})")
        except SystemExit as ex:
            satir.update({"sonuc": "ATLANDI", "not": f"HATA: {str(ex)[:150]}", "kota": api.remaining})
            log(f"    ATLANDI: {ex}")
        except Exception as ex:                       # bir ilan kosuyu durdurmaz
            satir.update({"sonuc": "ATLANDI", "not": f"{type(ex).__name__}: {str(ex)[:120]}",
                          "kota": api.remaining})
            log(f"    ATLANDI: {type(ex).__name__}: {ex}")
        satirlar = [r for r in satirlar if r["pair"] != pair] + [satir]
        durum_yaz(a.state, satirlar)

    durum_yaz(a.state, satirlar)
    say = {}
    for r in satirlar:
        say[r.get("sonuc", "?")] = say.get(r.get("sonuc", "?"), 0) + 1
    ozet = {"ilan": len(ciftler), "sonuclar": say,
            "atlanan": sorted(r["pair"] for r in satirlar if r.get("sonuc") in ("ATLANDI", "FAIL")),
            "islenmemis": sorted(p for p, _ in ciftler if p not in {r["pair"] for r in satirlar}),
            "sure_dk": round((time.time() - t0) / 60, 1), "kota": api.remaining,
            "api_cagrisi": api.calls}
    (out / "desc_batch_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    log("OZET: " + json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
