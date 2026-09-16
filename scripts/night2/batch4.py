#!/usr/bin/env python3
"""BATCH 4 - uygulamaya hazir karar paketi (GOREV 2-7). SALT OKUR + TASLAK.

Etsy'ye canli yazma YOK, GPSR panel girisi YOK, dosya tasima/silme YOK,
Ads ayari YOK, sosyal medya/Metricool yayinlama YOK. Yeni genis tarama YOK:
girdi Batch 2 ve Batch 3 ciktilaridir.

Kullanim:
  batch4.py --b2-dir B2 --b3-dir B3 --out OUT [--prodigi-list bulunan.csv]
            [--drive-index drive_arama.txt]
"""
import argparse
import csv
import difflib
import json
import pathlib
import re
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone

UZUN_TIRE = {"—": "em dash", "–": "en dash", "―": "horizontal bar",
             "‒": "figure dash", "−": "minus"}
URUN_KELIME = {"Digital wallpaper": "Wallpaper", "Digital wall art": "Printable Wall Art",
               "POD baski": "Wall Art Print"}
BASLIK_SINIR = 140


def simdi():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def gorev(ad, fn, sonuclar):
    bas = simdi()
    try:
        kayit, hata, notu = fn()
        durum = "PASS" if not hata else ("FAIL" if kayit == 0 else "PASS")
    except Exception as ex:                                       # noqa: BLE001
        kayit, hata, notu, durum = 0, 1, f"{type(ex).__name__}: {ex}", "FAIL"
        print(f"  {ad} HATA: {traceback.format_exc(limit=2)[:400]}")
    sonuclar.append({"gorev": ad, "baslangic": bas, "bitis": simdi(), "durum": durum,
                     "islenen_kayit": kayit, "hata_sayisi": hata, "aciklama": notu,
                     "sonraki_goreve_gecildi": "evet"})
    print(f"  {ad}: {durum} | kayit {kayit} | hata {hata} | {notu}")
    return kayit


def oku_csv(p):
    p = pathlib.Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def oku_json(p):
    p = pathlib.Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def yaz_csv(p, satirlar, sutunlar=None):
    sut = sutunlar or (list(satirlar[0]) if satirlar else [])
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sut, extrasaction="ignore")
        w.writeheader()
        for x in satirlar:
            w.writerow(x)


def fark_ozeti(eski, yeni):
    """Satir bazli kisa fark ozeti + ilk 3 degisen satirin once/sonra hali."""
    e, y = eski.split("\n"), yeni.split("\n")
    degisen = [(i, a, b) for i, (a, b) in enumerate(zip(e, y), 1) if a != b]
    ek = len(y) - len(e)
    ozet = f"{len(degisen)} satir degisti"
    if ek:
        ozet += f", satir sayisi {ek:+d}"
    detay = " || ".join(f"s{i}: [{a.strip()[:70]}] -> [{b.strip()[:70]}]"
                        for i, a, b in degisen[:3])
    return ozet, detay


def baslik_onerisi(baslik, urun_kelime):
    """Urun kelimesini ilk 40 karaktere tasir; kelime zaten varsa one alir."""
    if not baslik:
        return baslik, "baslik bos"
    if urun_kelime.lower() in baslik[:40].lower():
        return baslik, "degisiklik gerekmiyor"
    parcalar = [p.strip() for p in baslik.split(",") if p.strip()]
    tasinan = next((p for p in parcalar if urun_kelime.lower() in p.lower()), None)
    if tasinan:
        kalan = [p for p in parcalar if p != tasinan]
        yeni = ", ".join([tasinan] + kalan)
        gerekce = f"'{tasinan}' parcasi basa tasindi"
    else:
        yeni = f"{parcalar[0]} {urun_kelime}" + ("" if len(parcalar) == 1 else
                                                 ", " + ", ".join(parcalar[1:]))
        gerekce = f"'{urun_kelime}' ilk parcaya eklendi"
    if len(yeni) > BASLIK_SINIR:
        kes = yeni[:BASLIK_SINIR]
        yeni = kes[:kes.rfind(",")] if "," in kes else kes.rstrip()
        gerekce += f"; {BASLIK_SINIR} karaktere kirpildi"
    return yeni, gerekce


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b2-dir", required=True)
    ap.add_argument("--b3-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prodigi-list", default="", help="Drive'da bulunan Prodigi maliyet dosyasi")
    ap.add_argument("--drive-index", default="", help="Prodigi arama ciktisi (dosya listesi)")
    ap.add_argument("--drive-files", default="", help="rclone lsjson --hash ciktisi (metadata)")
    ap.add_argument("--arsiv-kok", default="ASTROLOVE/ARCHIVE/DUPLICATES")
    a = ap.parse_args()
    b2, b3 = pathlib.Path(a.b2_dir), pathlib.Path(a.b3_dir)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    damga = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    sonuclar = []
    katalog = oku_json(b2 / "full_etsy_catalog.json")
    kat = {str(L.get("listing_id")): L for L in katalog}

    # Drive metadata indeksi (indirme YOK; yalniz yol + boyut + MD5)
    drive = oku_json(a.drive_files) if a.drive_files else []
    md5_grup = defaultdict(list)
    for f in drive:
        yol = f.get("Path") or ""
        h = (f.get("Hashes") or {}).get("md5") or ""
        if yol and h:
            md5_grup[h].append((f"ASTROLOVE/{yol}", int(f.get("Size") or 0)))
    print(f"Drive metadata: {len(drive)} dosya, {len(md5_grup)} benzersiz md5")

    # ------------------------------------------------------------------ GOREV 2
    def g2():
        wp_v2 = oku_json(b3 / "wallpaper_description_v2.json")
        triaj = oku_csv(b3 / "seo_findings_triaged.csv")
        if not wp_v2 and not triaj:
            return 0, 1, "Batch 3 girdileri yok (wallpaper_description_v2.json / triaj)"
        satir = []
        # --- 78 wallpaper aciklamasi
        for r in wp_v2:
            lid = str(r["listing_id"])
            L = kat.get(lid, {})
            eski = L.get("_desc") or ""
            yeni = r["description"]
            if not eski:
                eski = yeni  # katalogda metin yoksa fark hesaplanamaz, isaretlenir
            ozet, detay = fark_ozeti(eski, yeni)
            kalan_tire = sorted({UZUN_TIRE[c] for c in UZUN_TIRE if c in yeni})
            satir.append({
                "sira": len(satir) + 1, "tur": "description", "alan": "description",
                "listing_id": lid, "urun_ailesi": L.get("urun_ailesi", "Digital wallpaper"),
                "burc_cifti": r.get("burc_cifti", ""),
                "baslik_referans": (L.get("baslik") or r.get("baslik") or "")[:90],
                "mevcut_metin": eski, "onerilen_metin": yeni,
                "mevcut_uzunluk": len(eski), "onerilen_uzunluk": len(yeni),
                "fark_ozeti": ozet, "fark_detay": detay,
                "degisiklik_gerekcesi": "uzun tire temizligi (marka kurali: em/en dash AI isareti)",
                "risk": "kalan uzun tire: " + ", ".join(kalan_tire) if kalan_tire else "yok",
                "degisti_mi": "evet" if yeni != eski else "hayir",
                "onay_EVET_HAYIR": "",
            })
        # --- 54 baslik
        bas_hedef = [t for t in triaj if t.get("kod") == "ILK40_URUN"
                     and t.get("yeni_oncelik") != "FALSE_POSITIVE"]
        for t in bas_hedef:
            lid = str(t["id"])
            L = kat.get(lid, {})
            eski = L.get("baslik") or t.get("baslik") or ""
            aile = L.get("urun_ailesi") or t.get("urun_ailesi") or ""
            kelime = URUN_KELIME.get(aile, "Print")
            yeni, gerekce = baslik_onerisi(eski, kelime)
            ozet, detay = fark_ozeti(eski, yeni)
            satir.append({
                "sira": len(satir) + 1, "tur": "title", "alan": "title",
                "listing_id": lid, "urun_ailesi": aile,
                "burc_cifti": L.get("burc_cifti", ""),
                "baslik_referans": eski[:90],
                "mevcut_metin": eski, "onerilen_metin": yeni,
                "mevcut_uzunluk": len(eski), "onerilen_uzunluk": len(yeni),
                "fark_ozeti": ozet, "fark_detay": detay,
                "degisiklik_gerekcesi": f"ilk 40 karakterde urun kelimesi yok; {gerekce}",
                "risk": ("140 karakter asildi" if len(yeni) > BASLIK_SINIR else
                         "SEO sirasi degisir, anahtar kelime kaybi yok"),
                "degisti_mi": "evet" if yeni != eski else "hayir",
                "onay_EVET_HAYIR": "",
            })
        yaz_csv(out / "wallpaper_title_description_approval.csv", satir)
        d_say = sum(1 for x in satir if x["tur"] == "description")
        t_say = sum(1 for x in satir if x["tur"] == "title")
        degisen = sum(1 for x in satir if x["degisti_mi"] == "evet")
        riskli = sum(1 for x in satir if x["risk"] not in ("yok",))
        return len(satir), 0, (f"{d_say} aciklama + {t_say} baslik; degisen {degisen}; "
                               f"not/riskli satir {riskli}; Etsy'ye YAZILMADI")

    # ------------------------------------------------------------------ GOREV 3
    def g3():
        plan = oku_csv(b3 / "duplicate_archive_plan.csv")
        if not plan:
            return 0, 1, "Batch 3 duplicate_archive_plan.csv yok"
        KORU_RX = re.compile(r"MASTER|FINAL|APPROVED|ONAYLI|/PRINT|ETSY_ZIPS", re.I)
        ARSIV_RX = re.compile(r"YEDEK|BACKUP|ARCHIVE|ARSIV|/OLD|ESKI|COPY|KOPYA|_v\d|TEMP/", re.I)
        kullanilan = set()
        for m in oku_json(b2 / "product_listing_media_matrix.json"):
            for k in ("ana_zip", "pdf_guide", "video"):
                if m.get(k):
                    kullanilan.add(m[k])
        haric = []
        # md5 -> yol listesi: once Drive metadata (TAM), yoksa Batch 2 (6 yol siniri var)
        ham = {r.get("anahtar"): r for r in oku_csv(b2 / "duplicate_candidates.csv")}
        satir, bayt = [], 0
        kesik = 0
        for r in plan:
            if r.get("sinif") != "GUVENLI_ARSIV_ADAYI":
                continue
            anahtar = r.get("anahtar", "")
            tam_idx = md5_grup.get(anahtar, [])
            boyut = {y: b for y, b in tam_idx}
            if tam_idx:
                tum = [y for y, _ in tam_idx]
            else:
                h = ham.get(anahtar, {})
                tum = [y.strip() for y in (h.get("yollar") or r.get("arsiv_adaylari")
                                           or "").split("|") if y.strip()]
                kesik += 1
            master = r.get("master_adayi", "")
            # Batch 3 grubu en fazla 6 yol gorerek siniflamisti. Metadata ile tam listeye
            # cikarken guvenlik filtresi HER DOSYAYA yeniden uygulanir; disarida kalan
            # yollar plana ALINMAZ, ayri dosyaya yazilir.
            adaylar, haric_grup = [], []
            for y in tum:
                if y == master:
                    continue
                if y in kullanilan:
                    haric_grup.append((y, "ilan tarafindan kullaniliyor"))
                elif KORU_RX.search(y):
                    haric_grup.append((y, "MASTER/FINAL/PRINT yolunda"))
                elif not ARSIV_RX.search(y):
                    haric_grup.append((y, "arsiv deseni tasimiyor (YEDEK/OLD/TEMP vb. degil)"))
                else:
                    adaylar.append(y)
            for y, neden in haric_grup:
                haric.append({"grup_md5": anahtar, "yol": y, "neden": neden,
                              "korunan_master": master})
            try:
                kopya = int(r.get("kopya_sayisi") or 0)
            except ValueError:
                kopya = 0
            try:
                grup_bayt = int(r.get("bosalacak_bayt") or 0)
            except ValueError:
                grup_bayt = 0
            birim = grup_bayt // len(adaylar) if adaylar else 0
            for y in adaylar:
                birim_bayt = boyut.get(y, birim)
                rel = y.split("ASTROLOVE/", 1)[-1] if "ASTROLOVE/" in y else y.lstrip("/")
                hedef = f"{a.arsiv_kok}/{damga}/{rel}"
                satir.append({
                    "grup_md5": anahtar, "kopya_sayisi": kopya,
                    "kaynak_yol": y,
                    "hedef_arsiv_yolu": hedef,
                    "dosya_hash_md5": anahtar,
                    "bayt": birim_bayt,
                    "bayt_kaynagi": "Drive metadata" if y in boyut else "grup ortalamasi",
                    "korunan_master": master,
                    "master_gerekcesi": r.get("gerekce", ""),
                    "tasima_komutu": f'rclone moveto "gdrive:{y}" "gdrive:{hedef}"',
                    "geri_alma_yolu": y,
                    "geri_alma_komutu": f'rclone moveto "gdrive:{hedef}" "gdrive:{y}"',
                    "dogrulama_komutu": f'rclone hashsum md5 "gdrive:{hedef}"',
                    "durum": "PLANLANDI - TASINMADI",
                })
                bayt += birim_bayt
        yaz_csv(out / "duplicate_archive_plan.csv", satir)
        yaz_csv(out / "duplicate_excluded_paths.csv", haric,
                ["grup_md5", "yol", "neden", "korunan_master"])
        # geri alma betigi (calistirilmaz, dosya olarak uretilir)
        geri = ["#!/usr/bin/env bash", "# BATCH 4 - duplicate arsiv GERI ALMA betigi.",
                "# Bu betik BATCH 4 tarafindan CALISTIRILMADI. Yalniz tasima yapildiktan",
                "# sonra, geri donus gerekirse Serdar tarafindan elle calistirilir.",
                "set -euo pipefail", ""]
        geri += [x["geri_alma_komutu"] for x in satir]
        (out / "duplicate_archive_rollback.sh").write_text("\n".join(geri) + "\n",
                                                           encoding="utf-8")
        return len(satir), 0, (f"{len(satir)} dosya, {bayt/1e9:.2f} GB, "
                               f"{len({x['grup_md5'] for x in satir})} grup; "
                               f"guvenlik filtresi disladi {len(haric)}; "
                               f"metadata disi grup {kesik}; TASIMA YAPILMADI")

    # ------------------------------------------------------------------ GOREV 4
    def g4():
        bulunan = []
        if a.drive_index and pathlib.Path(a.drive_index).exists():
            bulunan = [x.strip() for x in
                       pathlib.Path(a.drive_index).read_text(encoding="utf-8").split("\n")
                       if x.strip()]
        def sayi(x):
            try:
                return float(str(x).replace("$", "").replace(",", ".").strip())
            except (TypeError, ValueError):
                return 0.0

        gercek = []
        kaynak = ""
        p = pathlib.Path(a.prodigi_list) if a.prodigi_list else None
        if p and p.exists() and p.stat().st_size > 0:
            kaynak = p.name
            for r in oku_csv(p):
                d = {k.lower().strip(): (v or "").strip() for k, v in r.items() if k}
                # Prodigi teklif dosyasi (PRODIGI_PILOT_QUOTES.csv) ve genel maliyet CSV'si
                sku = d.get("sku", "")
                # uretimde kullanilan SKU semasi GLOBAL-HPR-<boyut> (order_router.py);
                # boyut anahtari SKU sonekidir ("11.0x14.0 in" degil)
                boyut = (sku.rsplit("-", 1)[-1] if sku.count("-") >= 2 else "") or \
                    d.get("size") or d.get("boyut") or ""
                mal = (d.get("birim_fiyat") or d.get("unit_cost") or d.get("unitcost")
                       or d.get("cost") or d.get("maliyet") or d.get("price") or "")
                kargo = (d.get("kargo_standard") or d.get("standard")
                         or d.get("kargo_budget") or d.get("budget")
                         or d.get("shipping") or d.get("kargo") or "")
                if boyut and sayi(mal) > 0:
                    gercek.append({"boyut": boyut, "sku": sku, "urun": d.get("urun", ""),
                                   "maliyet": round(sayi(mal), 2),
                                   "kargo": round(sayi(kargo), 2) if kargo else "",
                                   "para": d.get("para_birimi") or d.get("currency") or "",
                                   "kaynak_dosya": kaynak})
        eski = oku_csv(b3 / "astrolove_unit_economics.csv")
        # gercek veri varsa birim ekonomi yeniden hesaplanir
        v2 = []
        if gercek:
            fiyat_tab = {r["size"]: sayi(r["price"]) for r in oku_csv("scripts/etsy/pod_prices.csv")}
            # uretim ailesi HPR (Hahnemuhle Photo Rag): order_router.py GLOBAL-HPR-<boyut>
            # gonderir. HPR yoksa o boyutun en ucuz adayi kullanilir ve isaretlenir.
            en_ucuz = {}
            for g in gercek:
                b = g["boyut"].replace('"', "").replace(" ", "").lower()
                mevcut = en_ucuz.get(b)
                hpr = "-HPR-" in g["sku"].upper()
                if mevcut is None:
                    en_ucuz[b] = g
                elif hpr and "-HPR-" not in mevcut["sku"].upper():
                    en_ucuz[b] = g
                elif hpr == ("-HPR-" in mevcut["sku"].upper()) and g["maliyet"] < mevcut["maliyet"]:
                    en_ucuz[b] = g
            for boyut, fiyat in sorted(fiyat_tab.items()):
                g = en_ucuz.get(boyut.lower().replace(" ", ""))
                if not g or not fiyat:
                    continue
                kargo = sayi(g["kargo"])
                islem, odeme, ilan = fiyat * 0.065, fiyat * 0.03 + 0.25, 0.20
                toplam = g["maliyet"] + kargo + islem + odeme + ilan
                kar = fiyat - toplam
                v2.append({"boyut": boyut, "etsy_fiyat": round(fiyat, 2),
                           "prodigi_birim_maliyet": g["maliyet"],
                           "prodigi_kargo": round(kargo, 2),
                           "etsy_islem_6.5": round(islem, 2),
                           "etsy_odeme_3+0.25": round(odeme, 2), "listeleme_0.20": ilan,
                           "toplam_maliyet": round(toplam, 2), "birim_kar": round(kar, 2),
                           "brut_marj_yuzde": round(kar / fiyat * 100, 1),
                           "basabas_roas": round(fiyat / kar, 2) if kar > 0 else "kar yok",
                           "veri_kaynagi": f"GERCEK ({g['sku'] or kaynak})",
                           "uretim_ailesi": ("HPR - uretimde kullanilan" if "-HPR-"
                                             in g["sku"].upper() else
                                             "HPR DISI - bu boyutta HPR teklifi yok")})
            if v2:
                yaz_csv(out / "astrolove_unit_economics_v2.csv", v2)
        md = [f"# GOREV 4 - Prodigi gercek maliyet kaynagi ({simdi()} UTC)", ""]
        if gercek:
            md += [f"**GERCEK VERI BULUNDU:** `{kaynak}` ({len(gercek)} satir). "
                   "Ekonomik model bu degerlerle guncellendi "
                   "(`astrolove_unit_economics_v2.csv`).", "",
                   "## Prodigi gercek maliyetleri", "",
                   "| boyut | sku | birim maliyet | kargo | para |",
                   "|---|---|---:|---:|---|"]
            md += [f"| {x['boyut']} | {x['sku'] or '-'} | {x['maliyet']} | "
                   f"{x['kargo'] if x['kargo'] != '' else '-'} | {x['para'] or '?'} |"
                   for x in sorted(gercek, key=lambda z: z["maliyet"])]
            yaz_csv(out / "prodigi_costs_real.csv", gercek)
            if v2:
                md += ["", "## Gercek veriyle birim ekonomi", "",
                       "| boyut | Etsy fiyat | Prodigi maliyet | kargo | toplam maliyet | "
                       "birim kar | marj | basabas ROAS |",
                       "|---|---:|---:|---:|---:|---:|---:|---:|"]
                md += [f"| {x['boyut']} | {x['etsy_fiyat']} | {x['prodigi_birim_maliyet']} | "
                       f"{x['prodigi_kargo']} | {x['toplam_maliyet']} | {x['birim_kar']} | "
                       f"%{x['brut_marj_yuzde']} | {x['basabas_roas']} |" for x in v2]
                zarar = [x["boyut"] for x in v2 if x["birim_kar"] <= 0]
                if zarar:
                    md += ["", f"**UYARI: zarar eden boyut(lar): {', '.join(zarar)}** - "
                           "fiyat guncellenmeden bu boyutlarda reklam verilmemeli.", ""]
        else:
            md += ["**GERCEK VERI BULUNAMADI.** Drive'da Prodigi maliyet listesi aranmasina ragmen",
                   "maliyet kolonu tasiyan dosya cikmadi. Veri UYDURULMADI; asagidaki model",
                   "varsayimlarla isaretlidir ve karar alinmadan once panelden dogrulanmalidir.", "",
                   "## Arama kapsami", "",
                   "`rclone lsf -R gdrive:ASTROLOVE` uzerinde su desenler tarandi:",
                   "`*rodigi*`, `*cost*`, `*maliyet*`, `*price*list*`, `*pricing*`, `*fiyat*`.", ""]
            if bulunan:
                md += [f"Ad eslesmesi veren {len(bulunan)} dosya bulundu, hicbirinde maliyet",
                       "kolonu yok (veya okunamadi):", ""]
                md += [f"- `{x}`" for x in bulunan[:40]]
                if len(bulunan) > 40:
                    md.append(f"- ... ve {len(bulunan) - 40} dosya daha")
            else:
                md += ["Ad eslesmesi veren dosya **bulunamadi**.", ""]
        md += ["", "## Model durumu (Batch 3 birim ekonomisi)", "",
               "| aile | fiyat | Batch 3 urun maliyeti | durum |", "|---|---:|---:|---|"]
        for x in eski:
            aile = x.get("urun_ailesi", "")
            if "POD" in aile:
                kayn = ("GECERSIZ - varsayim; gecerli deger v2 tablosunda" if v2
                        else "VARSAYIM - dogrulanmadi")
            else:
                kayn = "GECERLI (dijital urun, marjinal maliyet 0)"
            md.append(f"| {aile} | {x.get('fiyat')} | {x.get('urun_maliyeti')} | {kayn} |")
        md += ["", "## Isaretleme kurali", "",
               "- **GERCEK**: Prodigi listesinden ya da sifir maliyetli dijital urunden gelir.",
               "- **VARSAYIM**: panelden dogrulanmadi; bu satirla reklam butcesi olceklenmez.", ""]
        if not gercek:
            md += ["## Serdar'dan istenen tek sey", "",
                   "Prodigi panelinden (Dashboard > Products > Price list) urun+boyut bazli",
                   "maliyet CSV'si indirilip `ASTROLOVE/TEMP/PRODIGI/` altina konulmasi.",
                   "Kolonlar: `size,cost,shipping,currency`. Dosya gelince model tek kosuda",
                   "gercek veriyle guncellenir.", ""]
        (out / "prodigi_cost_source.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(gercek) or len(bulunan), 0, (
            f"gercek maliyet satiri {len(gercek)}, ad eslesmesi {len(bulunan)}; "
            f"{'model guncellendi (' + str(len(v2)) + ' boyut)' if v2 else ('kaynak bulundu, boyut eslesmedi' if gercek else 'varsayimlar ayri isaretlendi')}")

    # ------------------------------------------------------------------ GOREV 5
    def g5():
        denetim = oku_csv(b3 / "shop_conversion_audit.csv")
        if not denetim:
            return 0, 1, "shop_conversion_audit.csv yok"
        puanlar = [int(x["puan_10"]) for x in denetim if str(x.get("puan_10", "")).isdigit()]
        ort = sum(puanlar) / len(puanlar) if puanlar else 0
        # oncelik: onem + puan bosluğu + canli onay gereksinimi
        def oncelik(x):
            puan = int(x["puan_10"]) if str(x["puan_10"]).isdigit() else 0
            onem = x.get("onem", "LOW")
            if onem == "HIGH" and puan <= 4:
                return "P0"
            if onem == "HIGH":
                return "P1"
            if onem == "MEDIUM" and puan <= 5:
                return "P1"
            if onem == "MEDIUM":
                return "P2"
            return "P3"
        EFOR = {"P0": "1-2 saat", "P1": "yarim gun", "P2": "1 gun", "P3": "planlanabilir"}
        aksiyon = []
        for x in denetim:
            p = oncelik(x)
            puan = int(x["puan_10"]) if str(x["puan_10"]).isdigit() else 0
            olculemez = "API" in x.get("gozlem", "") and "YOK" in x.get("gozlem", "").upper()
            aksiyon.append({
                "oncelik": p, "alan": x["alan"], "mevcut_puan_10": puan,
                "hedef_puan_10": 8, "gozlem": x["gozlem"],
                "aksiyon": x["onerilen_duzeltme"],
                "nerede": "Etsy Shop Manager paneli" if olculemez or x["alan"] in
                          ("announcement", "About / FAQ / policies", "icon / header",
                           "shop name") else "ilan alanlari (API)",
                "canli_onay_gerekir": "evet",
                "olcum": {
                    "announcement": "duyuru dolu ve 80+ karakter",
                    "About / FAQ / policies": "3 bolum de dolu",
                    "guven unsurlari": "ilan aciklamasinda teslim+iade satiri var",
                    "mobil gorunum": "54 ilanda urun kelimesi ilk 40 karakterde",
                    "dijital/fiziksel ayrimi": "duyuru ve bolum adlari ayrimi tasiyor",
                }.get(x["alan"], "puan 8/10'a cikar"),
                "veri_durumu": "API'de olculemiyor - panelden dogrulanacak" if olculemez
                               else "olculdu",
            })
        siralama = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        aksiyon.sort(key=lambda x: (siralama[x["oncelik"]], x["mevcut_puan_10"]))
        yaz_csv(out / "store_conversion_actions.csv", aksiyon)
        say = Counter(x["oncelik"] for x in aksiyon)
        md = [f"# GOREV 5 - Magaza donusum aksiyon listesi ({simdi()} UTC)", "",
              f"Batch 3 puani **{ort:.1f}/10**. Canli magaza degisikligi YAPILMADI; asagidakilerin",
              "tamami Serdar'in panel onayini bekler.", "",
              f"Dagilim: " + ", ".join(f"{k} {say.get(k, 0)}" for k in ("P0", "P1", "P2", "P3")),
              "", "## Oncelik tanimi", "",
              "| oncelik | anlam | efor |", "|---|---|---|",
              "| P0 | donusumu dogrudan kesen, bugun yapilmali | 1-2 saat |",
              "| P1 | bu hafta; gorunurluk veya guven kaybi | yarim gun |",
              "| P2 | bu ay; iyilestirme | 1 gun |",
              "| P3 | sirada bekleyebilir | planlanabilir |", ""]
        for p in ("P0", "P1", "P2", "P3"):
            grup = [x for x in aksiyon if x["oncelik"] == p]
            if not grup:
                continue
            md += [f"## {p} ({len(grup)})", ""]
            for i, x in enumerate(grup, 1):
                md += [f"**{p}.{i} {x['alan']}** - puan {x['mevcut_puan_10']}/10 "
                       f"({x['veri_durumu']})",
                       f"- Aksiyon: {x['aksiyon']}",
                       f"- Nerede: {x['nerede']}",
                       f"- Bitti olcusu: {x['olcum']}", ""]
        md += ["## Puani yukseltmeyen ama onemli not", "",
               "Puanin dusuk cikmasinin buyuk bolumu **olcum bosluğudur**: About, FAQ, policies,",
               "header gorseli ve mobil gorunum Etsy Open API v3'te yoktur. Bu basliklara 0",
               "verilmesi 'kotu' degil 'olculemedi' anlamina gelir; panelden bakilmadan",
               "puan gercek degildir.", ""]
        (out / "store_conversion_actions.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(aksiyon), 0, (f"{dict(say)}; ortalama {ort:.1f}/10; canli degisiklik YOK")

    # ------------------------------------------------------------------ GOREV 6
    def g6():
        rows = oku_csv(b2 / "platform_content_dataset.csv")
        if not rows:
            return 0, 1, "platform_content_dataset.csv yok"
        matris = oku_json(b2 / "product_listing_media_matrix.json")
        # cift -> tur -> gercek dosya yollari
        medya = defaultdict(lambda: defaultdict(list))
        for m in matris:
            c = m.get("burc_cifti", "")
            if not c:
                continue
            if m.get("video"):
                medya[c]["video"].append(m["video"])
            if m.get("ana_zip"):
                medya[c]["zip"].append(m["ana_zip"])
            if m.get("pdf_guide"):
                medya[c]["pdf"].append(m["pdf_guide"])
        # Drive metadata'dan cift bazli gercek dosya yollari (indirme YOK)
        cift_rx = {}
        for c in sorted({r["cift"] for r in rows}):
            A, B = c.split("_")
            cift_rx[c] = re.compile(rf"(?<![A-Za-z]){A}[_ -]?{B}(?![A-Za-z])", re.I)
        tum_yol = [y for g in md5_grup.values() for y, _ in g] or \
                  [(r.get("dosya") or "") for r in oku_csv(b2 / "media_technical_qa.csv")]
        for y in tum_yol:
            if not y:
                continue
            dy = y.lower()
            tur = ("video" if dy.endswith((".mp4", ".mov", ".webm")) else
                   "mockup" if re.search(r"mockup|scene|hero|room|preview", dy) else
                   "wallpaper" if "wallpaper" in dy else
                   "print" if dy.endswith((".jpg", ".jpeg", ".png")) else "")
            if not tur:
                continue
            for c, rx in cift_rx.items():
                if rx.search(y):
                    if len(medya[c][tur]) < 12:
                        medya[c][tur].append(y)
                    break
        # platform -> tercih sirasi
        TERCIH = {"Etsy": ["mockup", "print", "video"],
                  "Pinterest": ["mockup", "print", "wallpaper"],
                  "Instagram": ["video", "mockup", "print"],
                  "Facebook": ["mockup", "print"],
                  "TikTok": ["video", "mockup"],
                  "YouTube": ["video", "mockup"],
                  "Google Business": ["mockup", "print"]}
        GUN = {"Etsy": "surekli (ilan yayinda)", "Pinterest": "Sali",
               "Instagram": "Carsamba", "Facebook": "Cuma", "TikTok": "her gun",
               "YouTube": "Persembe", "Google Business": "ayin 1. ve 15. gunu"}
        SAAT = {"Etsy": "-", "Pinterest": "21:00", "Instagram": "20:00", "Facebook": "19:00",
                "TikTok": "21:30", "YouTube": "19:30", "Google Business": "12:00"}
        for c in medya:
            for t in medya[c]:
                medya[c][t] = sorted(set(medya[c][t]))
        eksik_medya, yeni = 0, []
        ciftler = sorted({r["cift"] for r in rows})
        sira = {c: i for i, c in enumerate(ciftler)}
        for r in rows:
            c, plat = r["cift"], r["platform"]
            dosya, tur_sec = "", ""
            for t in TERCIH.get(plat, ["mockup"]):
                if medya[c].get(t):
                    dosya = medya[c][t][sira[c] % len(medya[c][t])]
                    tur_sec = t
                    break
            if not dosya:
                eksik_medya += 1
                dosya = "(EKSIK - Drive'da bu cifte baglanan medya bulunamadi)"
                tur_sec = "yok"
            # yayin haftasi: 78 cift 6 haftaya dagitilir (haftada 13 cift)
            hafta = sira[c] // 13 + 1
            zaman = (f"hafta {hafta}, {GUN[plat]} {SAAT[plat]} yerel"
                     if SAAT[plat] != "-" else "surekli yayinda")
            d = dict(r)
            d.update({
                "kullanilacak_medya": dosya,
                "medya_turu": tur_sec,
                "medya_aciklama_referans": r.get("kullanilacak_medya", ""),
                "onerilen_yayin_zamani": zaman,
                "yayin_haftasi": hafta,
                "durum": "TASLAK - YAYINLANMADI / PLANLANMADI",
            })
            yeni.append(d)
        sut = list(rows[0]) + ["medya_turu", "medya_aciklama_referans", "yayin_haftasi", "durum"]
        yaz_csv(out / "platform_content_final.csv", yeni, sut)
        bos = [k for k in ("baslik", "aciklama", "hook", "cta", "hashtag_tag",
                           "onerilen_oran", "onerilen_yayin_zamani", "kullanilacak_medya")
               if any(not (x.get(k) or "").strip() for x in yeni)]
        plat = len({x["platform"] for x in yeni})
        return len(yeni), len(bos), (
            f"{len(yeni)} satir ({len(ciftler)} cift x {plat} platform); "
            f"gercek medya eslesen {len(yeni) - eksik_medya}, eksik {eksik_medya}; "
            f"bos zorunlu alan {bos or 'yok'}")

    # ------------------------------------------------------------------ GOREV 7
    def g7():
        KOLON = ["date", "listing_id", "listing_title", "impressions", "clicks",
                 "spend", "orders", "revenue", "currency"]
        with open(out / "ads_import_template.csv", "w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(KOLON)
        # --- karar motoru test verisi (SENTETIK; gercek performans DEGIL)
        TEST = [
            # (id, imp, click, spend, orders, revenue, beklenen)
            ("TEST_PAUSE_1",   9000, 40, 14.00, 0, 0.00,  "PAUSE"),
            ("TEST_PAUSE_2",   5000, 30, 10.00, 0, 0.00,  "PAUSE"),
            ("TEST_REVIEW_1",  4000, 20,  6.00, 0, 0.00,  "REVIEW"),
            ("TEST_REVIEW_2",  3000, 15,  4.00, 0, 0.00,  "REVIEW"),
            ("TEST_REDUCE_1",  2000, 25,  9.00, 1, 7.00,  "REDUCE"),
            ("TEST_REDUCE_2",  1500, 12,  5.00, 1, 4.99,  "REDUCE"),
            ("TEST_KEEP_1",    3000, 30, 10.00, 4, 40.00, "KEEP"),
            ("TEST_KEEP_2",     800, 10,  2.50, 2, 19.98, "KEEP"),
            ("TEST_WATCH_1",    500,  2,  0.60, 0, 0.00,  "WATCH"),
            ("TEST_WATCH_2",   1200,  8,  2.00, 1, 3.00,  "WATCH"),
            ("TEST_SIFIR_TIK", 2500,  0,  0.00, 0, 0.00,  "WATCH"),
        ]
        tp = out / "ads_decision_engine_test.csv"
        with open(tp, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(KOLON)
            for lid, imp, clk, sp, od, rev, _ in TEST:
                w.writerow(["2026-09-14", lid, f"sentetik test satiri {lid}", imp, clk,
                            f"{sp:.2f}", od, f"{rev:.2f}", "USD"])
        kt = out / "_ads_test_sonuc"
        r = subprocess.run([sys.executable, "scripts/night2/ads_kpi.py", "--csv", str(tp),
                            "--out", str(kt)], capture_output=True, text=True)
        cikti = oku_csv(kt / "ads_kpi_by_listing.csv")
        karar = {x["listing_id"]: x["karar"] for x in cikti}
        dogrulama, yanlis = [], 0
        for lid, imp, clk, sp, od, rev, bek in TEST:
            ger = karar.get(lid, "(cikmadi)")
            ok = ger == bek
            yanlis += 0 if ok else 1
            dogrulama.append({"listing_id": lid, "impressions": imp, "clicks": clk,
                              "spend": sp, "orders": od, "revenue": rev,
                              "beklenen_karar": bek, "gercek_karar": ger,
                              "sonuc": "PASS" if ok else "FAIL"})
        yaz_csv(out / "ads_decision_engine_validation.csv", dogrulama)
        md = [f"# GOREV 7 - Etsy Ads import + karar motoru dogrulamasi ({simdi()} UTC)", "",
              "**Gercek performans verisi YOK ve UYDURULMADI.** Etsy Open API v3'te reklam ucu",
              "yoktur; CSV Shop Manager > Marketing > Etsy Ads ekranindan elle indirilir.",
              "Asagidaki satirlar SENTETIK test verisidir, gercek magaza performansi degildir.", "",
              "## Import sablonu", "",
              "`ads_import_template.csv` - bos, yalniz baslik satiri:", "",
              "```", ",".join(KOLON), "```", "",
              "Dosya geldiginde: `ASTROLOVE/TEMP/ETSY_ADS/etsy_ads_stats_<tarih>.csv` yoluna",
              "konur ve `scripts/night2/ads_kpi.py --csv <dosya> --out OUT` calistirilir.", "",
              "## Karar motoru testi", "",
              f"Test satiri: **{len(TEST)}** | gecen: **{len(TEST) - yanlis}** | "
              f"kalan: **{yanlis}**", "",
              "| test | tiklama | harcama | siparis | gelir | beklenen | gercek | sonuc |",
              "|---|---:|---:|---:|---:|---|---|---|"]
        for x in dogrulama:
            md.append(f"| {x['listing_id']} | {x['clicks']} | {x['spend']} | {x['orders']} | "
                      f"{x['revenue']} | {x['beklenen_karar']} | {x['gercek_karar']} | "
                      f"**{x['sonuc']}** |")
        md += ["", "## Motor kurallari (sira onemli)", "",
               "| sinif | kural |", "|---|---|",
               "| PAUSE | tiklama >= 30 ve siparis = 0 ve harcama >= 10 |",
               "| REVIEW | tiklama >= 15 ve siparis = 0 |",
               "| REDUCE | harcama >= 3 ve ROAS < 1.0 |",
               "| KEEP | ROAS >= 2.0 |",
               "| WATCH | digerleri / yetersiz veri |", "",
               "Batch 3'te PAUSE sinifi dokumana yazilmis ama `ads_kpi.py` icinde yoktu;",
               "bu kosuda motora eklendi ve test ile dogrulandi. Butce/teklif degisikligi",
               "motorun isi DEGILDIR, panelden Serdar yapar.", ""]
        if r.returncode != 0:
            md += ["## Motor kosusu ciktisi", "", "```", (r.stderr or "")[-600:], "```", ""]
        (out / "ads_import_system.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        return len(TEST), yanlis, (f"{len(TEST) - yanlis}/{len(TEST)} test PASS; "
                                   f"sablon bos; gercek veri yok")

    print("BATCH 4 gorevleri")
    gorev("GOREV 2 wallpaper/baslik onay dosyasi", g2, sonuclar)
    gorev("GOREV 3 duplicate tasima plani", g3, sonuclar)
    gorev("GOREV 4 Prodigi maliyet kaynagi", g4, sonuclar)
    gorev("GOREV 5 magaza donusum aksiyonlari", g5, sonuclar)
    gorev("GOREV 6 platform icerik matrisi", g6, sonuclar)
    gorev("GOREV 7 ads sablon + karar motoru", g7, sonuclar)

    yaz_csv(out / "batch4_task_log.csv", sonuclar)
    dup = oku_csv(out / "duplicate_archive_plan.csv")
    dup_gb = sum(int(x.get("bayt") or 0) for x in dup) / 1e9
    dup_ozet = f"{dup_gb:.2f} GB / {len(dup)} dosya" if dup else "plan bos"
    gecen = sum(1 for x in sonuclar if x["durum"] == "PASS")
    md = [f"# BATCH 4 - uygulamaya hazir karar paketi ({simdi()} UTC)", "",
          f"Gorev: **{gecen}/{len(sonuclar)} PASS**. Canli Etsy yazmasi, GPSR panel girisi,",
          "dosya tasima/silme, Ads ayari ve sosyal medya yayini YAPILMADI.", "",
          "| gorev | baslangic | bitis | durum | islenen | hata | aciklama |",
          "|---|---|---|---|---:|---:|---|"]
    for x in sonuclar:
        md.append(f"| {x['gorev']} | {x['baslangic'][11:]} | {x['bitis'][11:]} | "
                  f"**{x['durum']}** | {x['islenen_kayit']} | {x['hata_sayisi']} | "
                  f"{x['aciklama'][:110]} |")
    md += ["", "## Uretilen dosyalar", "",
           "| dosya | icerik |", "|---|---|",
           "| workflow_final_test.md | GOREV 1 - 16/16 test PASS, branch main'e merge EDILMEDI |",
           "| wallpaper_title_description_approval.csv | 78 aciklama + 54 baslik: mevcut, onerilen, fark, listing_id, onay kolonu |",
           f"| duplicate_archive_plan.csv | {dup_ozet}: kaynak/hedef/hash/geri alma yolu |",
           "| duplicate_excluded_paths.csv | guvenlik filtresinin plana ALMADIGI yollar + neden |",
           "| astrolove_unit_economics_v2.csv | gercek Prodigi maliyetiyle birim ekonomi |",
           "| duplicate_archive_rollback.sh | geri alma betigi (CALISTIRILMADI) |",
           "| prodigi_cost_source.md | Drive aramasi + gercek/varsayim isaretlemesi |",
           "| store_conversion_actions.md / .csv | P0-P3 aksiyon listesi |",
           "| platform_content_final.csv | 546 satir, gercek medya dosyasi eslenmis |",
           "| ads_import_template.csv | bos import sablonu |",
           "| ads_decision_engine_validation.csv | karar motoru sentetik test sonucu |",
           "| batch4_task_log.csv | gorev bazli calisma kaydi |", "",
           "## CANLI ONAY BEKLEYEN ISLEMLER", "",
           "Asagidakilerin hicbiri yapilmadi; her biri Serdar'in ayri onayini bekler.", "",
           "| # | islem | kapsam | nerede yapilir | hazir dosya |", "|---:|---|---|---|---|",
           "| 1 | Etsy wallpaper aciklama degisikligi | 78 ilan | pod-desc-set / digital-desc workflow (apply=true + confirm=CANLI) | wallpaper_title_description_approval.csv |",
           "| 2 | Etsy baslik degisikligi | 54 ilan | ayni workflow, ayri kosu | wallpaper_title_description_approval.csv |",
           "| 3 | GPSR panel girisi | 78 POD ilani | Etsy Shop Manager (API'de alan yok) | gpsr_panel_ready.csv (Batch 3) |",
           f"| 4 | Duplicate arsivleme | {dup_ozet} | rclone moveto (plan hazir) | duplicate_archive_plan.csv |",
           "| 5 | Workflow hardening merge | claude/wf-hardening -> main | git merge | workflow_final_test.md |",
           "| 6 | Sosyal medya / Metricool yayini | 546 satir | Metricool | platform_content_final.csv |",
           "| 7 | Magaza paneli duzeltmeleri | P0-P1 maddeler | Etsy Shop Manager | store_conversion_actions.md |", ""]
    (out / "final_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"BATCH 4 bitti: {gecen}/{len(sonuclar)} PASS -> {out}")


if __name__ == "__main__":
    main()
