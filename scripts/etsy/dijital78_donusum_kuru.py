#!/usr/bin/env python3
"""390 -> 78 dijital ilan MTO donusumu: KURU KOSU (Etsy'ye HICBIR cagri yok).

Girdi (salt okur):
  --kalan   Drive TEMP/DIJITAL_78/DIJITAL_78_KALAN_ILANLAR.csv (25 Eyl 2026)
  --kalacak Drive TEMP/DIJITAL_78/KALACAK.csv (20 Eyl 2026, yalniz karsilastirma)
Cikti: DONUSUM_KURU_KOSU.csv (78), DONUSUM_PASIF_LISTE.csv (312),
       DONUSUM_EKSIK.csv, DONUSUM_QC.json (PASS/FAIL).

Kaynaklar (tahmin yok):
  baslik/etiket sablonu  -> Drive SEO_DIJITAL_WALLPAPER, bolum A
  fiyat 14.99 / 6.99     -> dijital-78_GOREV_0013 md.2 (karar dokumani)
  eski fiyat 9.99        -> docs/operations/DIJITAL_78_PLAN_20260920.md
  ZIP ici yapi + boyut   -> ayni dosya + Drive ZIP_OPT_OZET.md
  MTO alanlari           -> Drive MTO_DIJITAL_KURALLARI
"""
import argparse, csv, json, pathlib, sys

EDISYONLAR = ["Midnight Blue", "Deep Black", "Pure White",
              "Champagne Ivory", "Warm Parchment"]
FIYAT_YENI, FIYAT_ESKI = "14.99", "9.99"
BASLIK = ("{A} and {B} Personalized Zodiac Couple Wall Art, "
          "Names and Message, Digital Files")
BASLIK_SINIR = 140
ETIKET = ["{a} wall art", "{b} zodiac", "personalized art", "custom couple print",
          "zodiac couple print", "couple names art", "printable wall art",
          "digital wall art", "zodiac wall art", "astrology wall art",
          "anniversary gift", "couple gift", "custom message art"]
ETIKET_SINIR = 20
ZIP_AD = "AstroLove_{S1}_{S2}_{ED}_ALL_SIZES.zip"
ZIP_ICI = "5 JPG (2:3 7200x10800, 3:4 7200x9600, 4:5 7200x9000, 11:14 6600x8400, A 9934x14044) + Print and Care Guide PDF"
KISISELLESTIRME = "First name (30) | Second name (30) | Short message (80)"
KORUMALI = {"4552582170": "Leo+Pisces CI", "4555411521": "Aries+Scorpio DB",
            "4553832904": "Capricorn+Libra MB"}


def cift_parcala(s):
    a, b = [p.strip() for p in s.split("+")]
    return a, b


def sebep(orders, fav, visits, ed):
    if orders > 0:
        return f"siparis ({orders})"
    if fav > 0:
        return f"favori ({fav})"
    if visits > 0:
        return f"ziyaret ({visits})"
    if ed == "Midnight Blue":
        return "esitlik -> Midnight Blue"
    return "BELIRSIZ: tum olcutler 0, edisyon Midnight Blue degil"


def oku(yol):
    with open(yol, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kalan", required=True)
    p.add_argument("--kalacak")
    p.add_argument("--out", default="_out")
    a = p.parse_args()
    cikti = pathlib.Path(a.out)
    cikti.mkdir(parents=True, exist_ok=True)

    kalan = oku(a.kalan)
    kuru, pasif, eksik, qc = [], [], [], {}
    tum_id, sorun = [], []

    for r in kalan:
        cift = r["pair"].strip()
        s1, s2 = cift_parcala(cift)
        kid = r["keep_listing_id"].strip()
        ed = r["edition"].strip()
        orders, fav, vis = (int(r["orders"]), int(r["favorites"]), int(r["visits"]))
        kapat = [x.strip() for x in r["deactivate_ids"].split(";") if x.strip()]
        baslik = BASLIK.format(A=s1, B=s2)
        etiketler = [t.format(a=s1.lower(), b=s2.lower()) for t in ETIKET]
        uzun = [t for t in etiketler if len(t) > ETIKET_SINIR]
        zipler = [ZIP_AD.format(S1=s1, S2=s2, ED=e.replace(" ", "_"))
                  for e in EDISYONLAR]
        ek = []
        if len(kapat) != 4:
            ek.append("PASIF_SAYI")
        if len(baslik) > BASLIK_SINIR:
            ek.append("BASLIK_UZUN")
        if uzun:
            ek.append("ETIKET_UZUN")
        sb = sebep(orders, fav, vis, ed)
        if sb.startswith("BELIRSIZ"):
            ek.append("SEBEP_BELIRSIZ")
        kuru.append({
            "cift": cift, "tur": "dijital_wall_art", "korunan_listing_id": kid,
            "mevcut_edisyon": ed, "korunma_sebebi": sb, "siparis": orders,
            "favori": fav, "ziyaret": vis, "yeni_baslik": baslik,
            "baslik_karakter": len(baslik), "etiket_1": etiketler[0],
            "etiket_2": etiketler[1], "etiket_sayisi": len(etiketler),
            "eski_fiyat_usd": FIYAT_ESKI, "yeni_fiyat_usd": FIYAT_YENI,
            "teslim_renk_sayisi": len(EDISYONLAR),
            "teslim_renkler": "; ".join(EDISYONLAR),
            "teslim_dosya_sayisi": len(zipler), "teslim_dosyalar": "; ".join(zipler),
            "zip_ici": ZIP_ICI, "when_made": "made_to_order", "listing_type": "download",
            "kisisellestirme": KISISELLESTIRME,
            "pasife_alinacak_idler": ";".join(kapat),
            "eksik_kodlari": ",".join(ek) or "-",
        })
        tum_id.append(kid)
        for i, pid in enumerate(kapat, 1):
            pasif.append({
                "cift": cift, "pasife_alinacak_listing_id": pid, "sira": i,
                "korunan_listing_id": kid, "korunan_edisyon": ed,
                "islem": "deactivateListing (YAZMA - ayri onay)",
                "pin": "PIN_ESLEME.csv: bu ilanin pini kirilacak",
                "edisyon": "ENVANTER.csv'den eslenecek (bu CSV'de yok)",
            })
            tum_id.append(pid)

    # ---- QC (olculebilir esikler)
    qc["kalan_satir"] = len(kuru)
    qc["pasif_satir"] = len(pasif)
    qc["havuz_toplam"] = len(tum_id)
    qc["havuz_tekil"] = len(set(tum_id))
    qc["mukerrer_id"] = len(tum_id) - len(set(tum_id))
    dag = {}
    for r in kuru:
        dag[r["mevcut_edisyon"]] = dag.get(r["mevcut_edisyon"], 0) + 1
    qc["edisyon_dagilimi"] = dag
    qc["baslik_en_uzun"] = max(r["baslik_karakter"] for r in kuru)
    qc["etiket_uzun_cift"] = sum(1 for r in kuru if "ETIKET_UZUN" in r["eksik_kodlari"])
    qc["sebep_belirsiz"] = sum(1 for r in kuru if "SEBEP_BELIRSIZ" in r["eksik_kodlari"])
    qc["korumali_korundu"] = {k: (k in set(r["korunan_listing_id"] for r in kuru))
                              for k in KORUMALI}
    qc["siparis_toplam"] = sum(r["siparis"] for r in kuru)

    gecti = (qc["kalan_satir"] == 78 and qc["pasif_satir"] == 312
             and qc["havuz_toplam"] == 390 and qc["mukerrer_id"] == 0
             and sum(dag.values()) == 78 and qc["baslik_en_uzun"] <= BASLIK_SINIR
             and qc["sebep_belirsiz"] == 0
             and all(qc["korumali_korundu"].values()))
    qc["SONUC"] = "PASS" if gecti else "FAIL"

    # ---- 20 Eyl KALACAK.csv ile karsilastirma
    if a.kalacak:
        eski = {r["cift"].strip().upper(): r for r in oku(a.kalacak)}
        fark = []
        for r in kuru:
            k = r["cift"].replace(" + ", "_").upper()
            e = eski.get(k)
            if e and e["kalan_listing_id"].strip() != r["korunan_listing_id"]:
                fark.append(f'{r["cift"]}: 20Eyl {e["kalan_listing_id"]}'
                            f' ({e["kalan_edisyon"]}) != 25Eyl {r["korunan_listing_id"]}'
                            f' ({r["mevcut_edisyon"]})')
        qc["kalacak_eslesmeyen_cift"] = len(fark)
        qc["kalacak_fark_ornek"] = fark[:5]
        if fark:
            eksik.append({
                "kod": "E01", "konu": "Iki kalan-ilan listesi celisiyor",
                "etki": f"{len(fark)} cift",
                "ayrinti": "KALACAK.csv (20 Eyl) ile DIJITAL_78_KALAN_ILANLAR.csv "
                           "(25 Eyl) farkli ilan tutuyor; views degerleri de farkli. "
                           "Bu kosu 25 Eyl dosyasini esas aldi (GOREV_0013 md.2).",
                "kim": "Claude/Serdar: hangi liste baglayici?",
                "kaynak": "TEMP/DIJITAL_78/KALACAK.csv + DIJITAL_78_KALAN_ILANLAR.csv",
            })

    eksik += [
        {"kod": "E02", "konu": "digital-desc-batch.yml hala AKTIF",
         "etki": "78 korunan ilan",
         "ayrinti": "AKTIF: cron '0 */4 * * *', zamanlanmis kosuda APPLY=true ve onay "
                    "kapisi muaf. Son iki kosu olculdu (36111401150 / 36228955842): "
                    "aciklama adimi 0 sn -> yapacak ilan kalmamis, Etsy'ye 0 yazma. "
                    "Ama cron duruyor ve uyguladigi metin ESKI instant-download "
                    "aciklamasi; durum CSV'si sifirlanirsa MTO metnini geri yazar. "
                    "Donusumden once kapatilmali (kapatma ayri onay).",
         "kim": "Serdar onayi -> cron kaldirma",
         "kaynak": ".github/workflows/digital-desc-batch.yml"},
        {"kod": "E03", "konu": "78 wallpaper ilani bu CSV'de yok",
         "etki": "78 ilan",
         "ayrinti": "Havuz 390 yalniz dijital poster ilanlari. Wallpaper 78 ilani "
                    "(eski fiyat 6.65 -> yeni 6.99) ayri; listing_id'leri ENVANTER.csv'de.",
         "kim": "Claude: kapsam karari (ayri kuru kosu)",
         "kaynak": "docs/operations/DIJITAL_78_PLAN_20260920.md"},
        {"kod": "E04", "konu": "Wallpaper Watch cihazi uretilmiyor",
         "etki": "78 wallpaper ilani",
         "ayrinti": "WP_LISTING_TEMPLATE 4 cihaz / 16 JPG / 4 ZIP vaat ediyor; V3 hatti "
                    "Phone+Tablet+Desktop (3 cihaz) uretiyor. Watch eksik.",
         "kim": "dijital-78 (V3) + Claude karari",
         "kaynak": "docs/WP_LISTING_TEMPLATE.md + WP_SIPARIS_URETIM.json"},
        {"kod": "E05", "konu": "Kisisellestirilmis baski dosyasi 5 boy degil",
         "etki": "78 korunan ilan",
         "ayrinti": "Teslim edilen ZIP 5 boy iceriyor; kisisel/V3 hatti bugun yalniz "
                    "24x32 (3:4) isimli dosya uretiyor. Diger 4 oran icin isimli "
                    "uretim yok.",
         "kim": "kisisel oturumu",
         "kaynak": "docs/operations/DIJITAL_78_V3_20260920.md"},
        {"kod": "E06", "konu": "Kisisellestirilmis ZIP ad kurali yok",
         "etki": "78 korunan ilan",
         "ayrinti": "Mevcut ad AstroLove_<S1>_<S2>_<EDISYON>_ALL_SIZES.zip; siparise "
                    "ozel isimli surumun adi kararlastirilmadi. Dosya adi siniri 70 "
                    "karakter (en uzun mevcut 63).",
         "kim": "Claude/Serdar",
         "kaynak": "docs/operations/DIJITAL_78_PLAN_20260920.md"},
        {"kod": "E07", "konu": "MTO teslimat siniri 5 dosya x 20 MB",
         "etki": "78 korunan ilan",
         "ayrinti": "5 edisyon = 5 ZIP: sinira tam oturuyor, 6. dosya yeri YOK. "
                    "jpegtran optimizasyonundan sonra en buyuk ZIP 18.48 MB (esik alti), "
                    "ama isim/mesaj eklenince bayt tekrar olculmeli.",
         "kim": "dijital-78: uretim sonrasi olcum",
         "kaynak": "Drive ZIP_OPT_OZET.md + MTO_DIJITAL_KURALLARI"},
        {"kod": "E08", "konu": "Mesaj karakter siniri celisiyor",
         "etki": "tum ilanlar",
         "ayrinti": "MTO_DIJITAL_KURALLARI onerisi: mesaj 80 karakter. GOREV_0014 "
                    "testi 35 karakter mesaj istiyor. Tek sinir kararlastirilmali.",
         "kim": "Claude",
         "kaynak": "Drive MTO_DIJITAL_KURALLARI + dijital-78_GOREV_0014"},
        {"kod": "E09", "konu": "Galeri kartlari",
         "etki": "78 korunan ilan",
         "ayrinti": "Her korunan ilan icin 10 kart (dijital) gerekli; hazir olup "
                    "olmadigi bu kosuda dogrulanmadi (Drive A1_77/<CIFT>/SET.json).",
         "kim": "medya oturumu",
         "kaynak": "dijital-78_RAPOR_0009"},
        {"kod": "E10", "konu": "updateListing taslagi yayina alir",
         "etki": "78 korunan ilan",
         "ayrinti": "Her ilanin state'i YAZMADAN ONCE okunacak; taslak kalmasi "
                    "gerekenler guncellenmeyecek (CLAUDE.md).",
         "kim": "dijital-78 (uygulama kosusu)",
         "kaynak": "CLAUDE.md"},
        {"kod": "E11", "konu": "Secim olcutu yeniden dogrulanamiyor",
         "etki": "78 cift",
         "ayrinti": "CSV yalniz KORUNAN ilanin siparis/favori/ziyaret degerini veriyor; "
                    "312 dusen ilanin degerleri yok. Korunma sebebi tutarlilik ile "
                    "turetildi, en-yuksek oldugu yeniden olculmedi.",
         "kim": "Claude: gerekirse per-ilan salt-okuma turu",
         "kaynak": "DIJITAL_78_KALAN_ILANLAR.csv"},
    ]

    def yaz(ad, satirlar):
        yol = cikti / ad
        with open(yol, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(satirlar[0].keys()))
            w.writeheader()
            w.writerows(satirlar)
        print(f"{ad}: {len(satirlar)} satir -> {yol}")

    yaz("DONUSUM_KURU_KOSU.csv", kuru)
    yaz("DONUSUM_PASIF_LISTE.csv", pasif)
    yaz("DONUSUM_EKSIK.csv", eksik)
    (cikti / "DONUSUM_QC.json").write_text(
        json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(qc, ensure_ascii=False, indent=2))
    return 0 if qc["SONUC"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
