#!/usr/bin/env python3
"""P1-G: 78 poster ilaninda galeri rank 5 W05_SUREC kartini yeni metinli kartla degistirme (Serdar 6 Kas; pilot 4570143815 yazildi,
6 Kas DUR + panel silmesi; Secenek 2 duzeltmesi Serdar 6 Kas "kod + kuru", kuru pilot 4570155846 ARIES_VIRGO).
Is akisi .github/workflows/p1g-w05-yukle.yml (kilit_bekle + token + Drive kaydi). updateListing / PATCH YOK.
Kartlar: p1g_kart.py uret (yontem b) MANIFEST_W05.csv (durum PASS = kimlik zinciri + canli OCR + bilinen PASS + kart kapilari).

Modlar:
  plan  : ETSY YOK. --canli-dir (galeri-v11-yedek-oku <ilan>_<CIFT>/GALERI.json) + --manifest MANIFEST_W05.csv -> PLAN_W05.json + PLAN_W05.md.
          Ilan basina: eski r5 listing_image_id, galeri (rank, kimlik, alt metin), renk baglari, eski W05 alt metni (yeni gorsele AYNEN),
          dosya, sha256, istek tahmini, kota ihtiyaci (en kotu + KOTA_SINIRI). BLOK: kart PASS degil / kimlik PASS degil, W05'e renk bagi
          var, galeri + 1 > 20, rank 5 yok. plan_damga = <kosu>_<sha256 ilk 12>.
  --kuru: ETSY SALT OKUMA (yd_envanter_oku.salt_okur: yazma yontemleri kapali). Ilan basina 3 GET (ilan, galeri, renk baglari);
          canli == plan -> HAZIR | ZATEN (--onceki SONRA kaydiyla) | YARIM (--onceki ARA kaydiyla) | BLOK. Kart --dosya-dir'den okunur,
          sha256 = plan sha256 (degilse BLOK).
  yazim : --confirm W05_DEGISTIR + --plan + --plan-damga + --dosya-dir + --sadece <acik listing_id listesi> + ortam W05_KILIT=1 (is akisi
          kilit_bekle.py adimindan SONRA koyar; kilit kumesi main'deki kilit_bekle.py). Ilan basina sira:
    1 kota: kalan >= en kotu + KOTA_SINIRI (ilan baslamadan, ve ilk ilanda kalan bilinmiyorsa 3 GET sonrasi yeniden; bilinmezse KALAN)
    2 canli okuma (3 GET) == plan: galeri kimlik / sira / alt metin, rank'lar 1..n ARDISIK, rank 5'te TEK gorsel = plan eski_id,
      renk baglari = plan, W05'e bag yok, state active; galeri + 1 <= 20; yerel dosya sha256 = plan sha256 (= MANIFEST_W05).
      n ve baglar sabit degil: plandan (GALERI.json).
    3 YEDEK_<ilan>.json (plan girdisi + zaman)
    4 YUKLEME: yeni kart rank 5'e, ESKI W05 alt metniyle (eski78_gorsel_yukle.yukle_guvenli: cift yukleme yok); ARA_<ilan>.json (yeni id)
    5 YUKLEME SONRASI KAPILARI (stabil_w05: (rank, kimlik) sirali kararli okuma; paylasilan stabil_galeri DEGISMEZ):
      yukleme_durumu(): n+1 gorsel, kimlikler = plan + yeni id, yeni id alt metni = eski W05 alt metni, digerlerinin alt metni = plan, ve
        ESIT : eski W05 ve yeni ikisi rank 5, digerleri plan rank'inda (6 Kas canli olcum, 4570143815 TANI) ya da
        KAYMA: yeni 5, eski W05 6, plan 6..n -> 7..n+1 (wp_image_replace.py:7).
      Ters sira (eski 5, yeni 6), fazla / eksik gorsel, baska yer degisimi: DUR + TANI, silme yok. Yeni boyut 3000x2250;
      yuklenen dosya sha256 = MANIFEST sha256 (yukleme boyunca degismedi)
    5b renk baglari geri okunur; plandan farkliysa yalniz KAYDEDILIR (Serdar 6 Kas "Baglari yeniden yaz"): eski W05 bagsiz, silme surer
    6 SILME: eski W05, YALNIZ listing_image_id ile (iki kartin alt metni ayni); sil_guvenli: yalniz yukleme_durumu ESIT / KAYMA ise.
      Silme sonrasi kapi rank NUMARASI degil: (rank, kimlik) sirali galeri sirasi = plan sirasi, rank'lar tekil (Etsy sikistirmayabilir:
      28 Eyl 4570110641, 30 Eyl 4570110121; sikismamis ama sirasi dogru galeri PASS, Merkez 6 Kas)
    6b BAG YAZIMI: plandaki renk baglari tek variation-images cagrisiyla AYNI haliyle yeniden yazilir ve geri okunur (plana esit degilse DUR)
    7 son geri okuma (stabil_w05): n gorsel, rank'lar tekil, kimlik sirasi = plan (eski_id yerine yeni id), alt metinler ayni,
      eski id yok; baglar = plan; state active
    8 SONRA_<ilan>.json (yeni id, sha256, alt metin)
  OTOMATIK KURTARMA YOK: herhangi bir adim tutmazsa ilan DUR (yeni / eski kimlikler ARA kaydinda), kosu durur (sonrakiler KALAN).
  Yuklemeden sonraki HER DUR'da baglar plandan farkliysa once tek bag yeniden yazimi + geri okuma, sonra DUR. Her DUR'da canli galeri +
  baglar TANI_<ilan>.json'a (okunamazsa son bilinen galeri + hata); belirsiz yukleme DUR'unda da (ARA yoksa bile).
  --geri-al (tek ilan, yazim kosullari): yeni id = ARA kaydi ya da canli kimlikler eksi plan kimlikleri (TEK kimlik kalirsa; yoksa
          "yalniz elle" DUR); YALNIZ eski W05 galeride duruyorsa yeni id silinir, baglar plandan farkliysa yeniden yazilir, son sira = plan.
  --devam --onceki <dir>: canli durumu ZATEN olan ilan (rank 5 = onceki SONRA yeni id, eski id galeride yok) atlanir; yazilmaz.
  --kurtar --onceki <dir>: YALNIZ YARIM ilan (ARA kaydi var; canli galeri ARA yeni id ile yukleme_durumu ESIT ya da KAYMA):
          yalniz adim 6-8 (silme + bag yazimi + son geri okuma). Baska durumda yazma yok. --sadece tek ilan zorunlu.
Istek (kod okumasi, istek_tahmini()). GET 5xx / 429 kisa tekrarlari dahil degil (sert taban 10 her istekten once durdurur).
Cikti --out: PLAN_W05.json / .md (plan), RAPOR.json, RAPOR.md, SONUC.csv, ilanlar/{YEDEK,ARA,SONRA,TANI}_<ilan>.json."""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
from etsy_common import KOTA_SINIRI  # noqa: E402  (Serdar 15 ve 24 Eki: 10; degistirilmez)

ONAY = "W05_DEGISTIR"
PLAN_AD = "PLAN_W05.json"
W05_RANK = 5
AZAMI_GORSEL = 20          # Etsy ilan basina gorsel siniri
OKUMA = 3                  # ilan, galeri, renk baglari
KILIT_ORTAM = "W05_KILIT"
KART_BOYUT = (3000, 2250)   # p1g_kart uret jpeg kapisi (3000x2250); Etsy full_width / full_height


def log(m):
    print(m, flush=True)


def jdump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class Hata(Exception):
    """yazim sirasinda kapi tutmadi: ilan DUR (otomatik kurtarma yok)"""


# ---------------------------------------------------------------- istek tahmini
def istek_tahmini():
    """GET 5xx / 429 tekrarlari HARIC (en kotu = bu kod yollarinin en kotusu; sert taban 10 her istekten once durdurur).
    O = cl_galeri_degistir.OKUMA_TEKRAR. Yazim istekleri en kotu 3 gonderim (5xx) + 1 (401); post_file tekrar=1 + 401 = 2 / deneme.
    "stabil" = stabil_w05 (en az 2, en fazla O galeri GET; paylasilan stabil_galeri ile ayni sayi). Secenek 2 (6 Kas): yukleme_durumu /
    kapi_once yalniz okunan galeriye bakar (yeni GET yok); en az degismez. Inceleme 6 Kas ORTA 2: boyut bos gelirse boyut bekleme (O)
    sonrasi silme karari icin stabil_w05 yeniden (+O, en kotu): yaz en kotu 90 -> 98, kurtar en kotu 69 -> 77, kota ihtiyaci 100 -> 108.
      kuru      : 3 GET.
      yaz en az : 3 + yukleme 1 + gorunur 1 + stabil 2 + bag farki 1 + silme 1 + bag POST 1 + bag geri 1 + son (silindi gorunur 1 +
                  stabil 2) + var_img 1 + ilan 1 = 16.
      yaz en kotu: 3 + yukleme (2 + 1 [429 okumasi]) + (2 + O) + gorunur O + stabil O + boyut O + stabil O + bag farki 1 + silme 4
                  + bag POST 4 + bag geri O
                  + son (O + O) + 1 + 1 + hata halinde bag onarimi (var_img 1 + POST 4 + geri O) + TANI 2.
      kurtar    : 3 + stabil 2 + bag farki 1 + silme 1 + bag POST 1 + bag geri 1 + son 3 + 1 + 1 = 14 (en az); en kotu O'lu (stabil O +
                  boyut O + stabil O) + onarim + TANI.
      geri al   : 3 + stabil 2 + silme 1 + silindi gorunur 1 + bag 1 + son stabil 2 = 10 (en az); en kotu: + bag yazimi (4 + O) + TANI 2."""
    O = G.OKUMA_TEKRAR
    onarim, tani = 1 + 4 + O, 2
    en_kotu = OKUMA + (2 + 1) + (2 + O) + O + O + O + O + 1 + 4 + 4 + O + O + O + 1 + 1 + onarim + tani   # boyut O + yeniden stabil O
    kurtar_kotu = OKUMA + O + O + O + 1 + 4 + 4 + O + O + O + 1 + 1 + onarim + tani
    geri_kotu = OKUMA + O + 4 + O + 1 + 4 + O + O + tani + onarim
    return dict(kuru=OKUMA, yaz_en_az=OKUMA + 1 + 1 + 2 + 1 + 1 + 1 + 1 + 1 + 2 + 1 + 1, yaz_en_kotu=en_kotu,
                kurtar_en_az=OKUMA + 2 + 1 + 1 + 1 + 1 + 1 + 2 + 1 + 1, kurtar_en_kotu=kurtar_kotu,
                geri_en_az=OKUMA + 2 + 1 + 1 + 1 + 2, geri_en_kotu=geri_kotu, okuma_tekrar=O, kota_ihtiyac=en_kotu + KOTA_SINIRI)


# ---------------------------------------------------------------- plan (Etsy yok)
def rk(x):
    """(rank, kimlik) sirasi: esit rank'ta kimlikle (Etsy esit rank'lari her okumada farkli API sirasinda donebilir; Merkez 6 Kas)"""
    return (int(x.get("rank") or 0), int(x.get("listing_image_id") or 0))


def galeri_ozet(g):
    return [[int(x.get("rank") or 0), int(x.get("listing_image_id") or 0), Y.alt_norm(x.get("alt_text"))] for x in sorted(g, key=rk)]


def bag_imza(b):
    return sorted([int(x.get("property_id") or 0), int(x.get("value_id") or 0), int(x.get("image_id") or 0)] for x in b or [])


def plan_ilan(lid, cift, j, m):
    """j: GALERI.json, m: MANIFEST_W05 satiri -> (girdi | None, neden listesi)"""
    neden = []
    if not m:
        return None, ["MANIFEST_W05'te satir yok"]
    if m.get("durum") != "PASS" or m.get("kimlik") != "PASS" or m.get("bilinen_pass") != "PASS" or m.get("canli_ocr") != "PASS":
        neden.append(f"kart PASS degil (durum {m.get('durum')}, kimlik {m.get('kimlik')}, bilinen {m.get('bilinen_pass')}, "
                     f"canli OCR {m.get('canli_ocr')})")
    if str(j.get("listing_id")) != lid or j.get("cift") != cift:
        neden.append("GALERI.json ilan / cift farkli")
    if m.get("cift") != cift or m.get("dosya") != f"{cift}_W05_SUREC.jpg":
        neden.append(f"MANIFEST_W05 satiri cift / dosya ilanla eslesmiyor ({m.get('cift')}, {m.get('dosya')})")
    g = galeri_ozet(j.get("gorseller") or [])
    if [r for r, _, _ in g] != list(range(1, len(g) + 1)):
        neden.append(f"galeri rank 1..n degil {[r for r, _, _ in g]}")
    r5 = [x for x in g if x[0] == W05_RANK]
    if not r5:
        return None, neden + ["rank 5 yok"]
    eski_id, eski_alt = r5[0][1], r5[0][2]
    ham = next((x.get("alt_text") or "" for x in j.get("gorseller") or [] if int(x.get("rank") or 0) == W05_RANK), "")
    if ham != eski_alt or re.search(r"&[A-Za-z#0-9]+;", ham):
        neden.append("eski W05 ham alt metni normalize / HTML varliksiz metinle ayni degil (yeni gorsele AYNEN gidemez)")
    bag = bag_imza(j.get("baglar"))
    if any(b[2] == eski_id for b in bag):
        neden.append("W05 (rank 5) gorseline renk / varyasyon bagi var")
    if len(g) + 1 > AZAMI_GORSEL:
        neden.append(f"galeri {len(g)} + 1 > {AZAMI_GORSEL}")
    if not eski_alt:
        neden.append("eski W05 alt metni bos")
    t = istek_tahmini()
    return dict(ilan=lid, cift=cift, galeri=g, baglar=bag, eski_id=eski_id, alt=eski_alt, n=len(g),
                dosya=m.get("dosya"), sha256=m.get("sha256"), en_az=t["yaz_en_az"], en_kotu=t["yaz_en_kotu"],
                kota_ihtiyac=t["kota_ihtiyac"]), neden


def plan_sha(girdiler):
    return hashlib.sha256(jdump(girdiler).encode()).hexdigest()


def plan_kur(canli_dir, manifest, ciftler, out, kosu):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    M = {r["ilan"]: r for r in csv.DictReader(open(manifest, encoding="utf-8"))}
    R = [r for r in csv.DictReader(open(ciftler, encoding="utf-8-sig")) if r.get("listing_id", "").strip()]
    girdiler, satir = {}, []
    for r in R:
        lid, cift = r["listing_id"].strip(), r["cift"]
        p = Path(canli_dir) / f"{lid}_{cift}" / "GALERI.json"
        if not p.exists():
            satir.append(dict(ilan=lid, cift=cift, durum="BLOK", neden=["canli okuma (GALERI.json) yok"])); continue
        gd, neden = plan_ilan(lid, cift, json.loads(p.read_text(encoding="utf-8")), M.get(lid))
        if gd is None or neden:
            satir.append(dict(ilan=lid, cift=cift, durum="BLOK", neden=neden)); continue
        girdiler[lid] = gd
        satir.append(dict(ilan=lid, cift=cift, durum="PLAN", neden=[], n=gd["n"], eski_id=gd["eski_id"], en_kotu=gd["en_kotu"]))
    t = istek_tahmini()
    n = len(girdiler)
    damga = f"{kosu}_{plan_sha(girdiler)[:12]}"
    P = dict(plan_damga=damga, kosu=kosu, istek_tahmini=t, ilan_plan=n, toplam_en_az=n * t["yaz_en_az"],
             toplam_en_kotu=n * t["yaz_en_kotu"], kota_ilan_basina=t["kota_ihtiyac"],
             w05_bagli=sum(1 for s in satir if any("bagi var" in x for x in s["neden"])), girdiler=girdiler, satirlar=satir)
    (out / PLAN_AD).write_text(json.dumps(P, indent=1, ensure_ascii=False), encoding="utf-8")
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    md = (f"# W05 degisim plani ({damga})\n\nilan {len(satir)} | " + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
          + f" | W05'e bagli varyasyon {P['w05_bagli']}\n"
          + f"istek (kod okumasi) ilan basina en az {t['yaz_en_az']} / en kotu {t['yaz_en_kotu']}; toplam en az {P['toplam_en_az']} / "
            f"en kotu {P['toplam_en_kotu']}; kota ilan basina en kotu + {KOTA_SINIRI} = {t['kota_ihtiyac']}\n"
          + "sira: yeni kart rank 5'e (eski W05 alt metniyle) -> geri okuma -> eski W05 silinir -> son geri okuma (ilan gorselsiz kalmaz)\n\n"
          + "".join(f"- {s['ilan']} {s['cift']} {s['durum']}" + (f": {'; '.join(s['neden'])}" if s["neden"] else "") + "\n" for s in satir))
    (out / "PLAN_W05.md").write_text(md, encoding="utf-8")
    log(f"::notice::W05 plan: {len(satir)} ilan | " + " ".join(f"{k} {v}" for k, v in sorted(say.items()))
        + f" | W05 bagli {P['w05_bagli']} | toplam istek en az {P['toplam_en_az']} en kotu {P['toplam_en_kotu']}")
    return 0 if say.get("PLAN", 0) == len(satir) else 1


def plan_yukle(yol, damga):
    p = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+_[0-9a-f]{12}", damga or ""):
        raise SystemExit("DUR: plan_damga bicimi <kosu>_<sha256 ilk 12>")
    if p.get("plan_damga") != damga or plan_sha(p.get("girdiler") or {})[:12] != damga.split("_", 1)[1]:
        raise SystemExit(f"DUR: {PLAN_AD} plan_damga / sha256 ile ayni degil; yazma yok")
    return p


# ---------------------------------------------------------------- canli durum ve kapilar
def canli_durum(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    return dict(state=L.get("state"), galeri=G.galeri(api, lid), baglar=G.var_img(api, shop, lid))


def sira(oz):
    """galeri ozeti -> [(kimlik, alt metin)] rank sirasinda; rank'lar kesin artan ve tekil degilse None. Etsy silmeden sonra rank'lari
    sikistirmayabilir (28 Eyl 4570110641, 30 Eyl 4570110121; kapak_yukle_78.py:296, cl_galeri_degistir.py:207): rank NUMARASI degil SIRA."""
    r = [x[0] for x in oz]
    if r != sorted(r) or len(set(r)) != len(r):
        return None
    return [(x[1], x[2]) for x in oz]


def stabil_w05(api, lid, tekrar=None):
    """Canli galeri (rank, kimlik) sirali; ardisik iki okuma (kimlik, rank, alt metin) ayni cikana kadar (en fazla O). Olmazsa DUR.
    Paylasilan eski78_gorsel_yukle.stabil_galeri DEGISMEZ: o imzayi API sirasinda kurar, esit rank'li galeride sira okumadan okumaya
    degisirse kararli olmaz (test_w05_degistir karisik)."""
    onceki = None
    for i in range(tekrar or G.OKUMA_TEKRAR):
        if i:
            G.time.sleep(G.OKUMA_BEKLE)
        g = sorted(G.galeri(api, lid), key=rk)
        imza = [(x.get("listing_image_id"), x.get("rank"), Y.alt_norm(x.get("alt_text"))) for x in g]
        if imza == onceki:
            return g
        onceki = imza
    raise Y.Dur("canli galeri okumasi kararli degil (ardisik iki (rank, kimlik) sirali okuma ayni cikmadi); yazim yok")


def yukleme_durumu(g, gd, yid):
    """yukleme sonrasi canli galeri -> ("ESIT" | "KAYMA" | None, neden). Tanima YALNIZ kimlikle (eski ve yeni kartin alt metni ayni).
    Ortak: n + 1 gorsel, her kimlik tek, kimlikler = plan + yeni id, yeni id alt metni = eski W05 alt metni, digerleri = plan alt metni.
      ESIT : yeni ve eski W05 rank 5, diger plan kimlikleri plan rank'inda (6 Kas canli olcum).
      KAYMA: yeni rank 5, eski W05 rank 6, plan rank < 5 ayni, plan rank > 5 -> +1 (wp_image_replace.py:7).
    Ters sira (eski 5, yeni 6), fazla / eksik gorsel, baska yer degisimi -> None."""
    plan_r = {i: r for r, i, _ in gd["galeri"]}
    plan_a = {i: a for _, i, a in gd["galeri"]}
    eski = gd["eski_id"]
    if plan_r.get(eski) != W05_RANK:
        return None, f"planda eski W05 rank'i {plan_r.get(eski)} (5 degil); plan bozuk"
    if not yid or yid in plan_r:
        return None, f"yeni kimlik yok ya da plan kimligi ({yid})"
    kim = [int(x.get("listing_image_id") or 0) for x in g]
    if len(g) != gd["n"] + 1 or len(set(kim)) != len(kim) or set(kim) != set(plan_r) | {yid}:
        return None, (f"yukleme sonrasi gorsel sayisi / kimlikler plan + yeni id degil ({len(g)} gorsel, {gd['n'] + 1} beklenir; "
                      f"plan disi {sorted(set(kim) - set(plan_r) - {yid})[:5]}, eksik {sorted(set(plan_r) - set(kim))[:5]})")
    r = {int(x.get("listing_image_id") or 0): int(x.get("rank") or 0) for x in g}
    a = {int(x.get("listing_image_id") or 0): Y.alt_norm(x.get("alt_text")) for x in g}
    if a[yid] != gd["alt"]:
        return None, "yeni gorselin alt metni eski W05 alt metni degil"
    if any(a[i] != plan_a[i] for i in plan_a):
        return None, "diger gorsellerin alt metni plandan farkli"
    digerleri = [i for i in plan_r if i != eski]
    if r[yid] == W05_RANK and r[eski] == W05_RANK and all(r[i] == plan_r[i] for i in digerleri):
        return "ESIT", ""
    if r[yid] == W05_RANK and r[eski] == W05_RANK + 1 and all(
            r[i] == (plan_r[i] if plan_r[i] < W05_RANK else plan_r[i] + 1) for i in digerleri):
        return "KAYMA", ""
    return None, (f"yukleme sonrasi rank'lar ESIT (yeni ve eski 5, digerleri yerinde) ya da KAYMA (yeni 5, eski 6, digerleri +1) degil "
                  f"(yeni {r[yid]}, eski {r[eski]}, rank'lar {[x[0] for x in galeri_ozet(g)]})")


def son_beklenen(gd, yid):
    return [(yid if i == gd["eski_id"] else i, a) for _, i, a in gd["galeri"]]


def kapi_once(c, gd):
    s = []
    if c["state"] != "active":
        s.append(f"state {c['state']} (active degil)")
    oz = galeri_ozet(c["galeri"])
    if sira(oz) != [(i, a) for _, i, a in gd["galeri"]] or len(oz) < W05_RANK or oz[W05_RANK - 1][1] != gd["eski_id"]:
        s.append("canli galeri (kimlik sirasi / alt metin / rank 5 = eski W05) plandan farkli")
    if [x[0] for x in oz] != list(range(1, gd["n"] + 1)):
        s.append(f"canli rank'lar 1..{gd['n']} ardisik degil ({[x[0] for x in oz][:14]})")
    if [x[1] for x in oz if x[0] == W05_RANK] != [gd["eski_id"]]:
        s.append("rank 5'te tek gorsel yok ya da kimligi plandaki eski W05 degil")
    ham = [x.get("alt_text") for x in c["galeri"] if x.get("listing_image_id") == gd["eski_id"]]
    if ham != [gd["alt"]]:
        s.append("canli eski W05 HAM alt metni plandaki metinle birebir ayni degil (yeni gorsele AYNEN gidemez)")
    if bag_imza(c["baglar"]) != gd["baglar"]:
        s.append("canli renk baglari plandan farkli")
    if any(b[2] == gd["eski_id"] for b in bag_imza(c["baglar"])):
        s.append("W05'e renk bagi var")
    if len(c["galeri"]) + 1 > AZAMI_GORSEL:
        s.append(f"galeri {len(c['galeri'])} + 1 > {AZAMI_GORSEL}")
    return s


def durum_tur(c, gd, onceki):
    """ZATEN (onceki SONRA ya da ARA yeni id eski W05'in yerinde, eski id yok, digerleri ayni, rank'lar tekil, baglar = plan, state
    active) | ZATEN_EKSIK (galeri ZATEN ama baglar / state plandan farkli: inceleme 6 Kas KRITIK 1; yazim yok, BLOK) |
    YARIM (ARA yeni id ile yukleme_durumu ESIT ya da KAYMA) | None"""
    q = sira(galeri_ozet(c["galeri"]))
    for ad in ("SONRA", "ARA"):
        x = (onceki or {}).get(ad)
        if x and q is not None and q == son_beklenen(gd, x["yeni_id"]):
            return "ZATEN" if bag_imza(c["baglar"]) == gd["baglar"] and c.get("state") == "active" else "ZATEN_EKSIK"
    ara = (onceki or {}).get("ARA")
    if ara and yukleme_durumu(c["galeri"], gd, ara["yeni_id"])[0]:
        return "YARIM"
    return None


def sonrasi_sorun(g, gd, yid, yol, iz=None):
    s = []
    tur, neden = yukleme_durumu(g, gd, yid)
    if iz is not None:
        iz["yukleme"] = tur
    if not tur:
        s.append(neden)
    b = boyut_sorun(g, yid)
    if b:
        s.append(b)
    if Y.sha256(yol) != gd["sha256"]:
        s.append("yuklenen dosya sha256 MANIFEST_W05 sha256 ile ayni degil")
    return s


def boyut(g, yid):
    y = [x for x in g if x.get("listing_image_id") == yid]
    return (y[0].get("full_width"), y[0].get("full_height")) if y else (None, None)


def boyut_sorun(g, yid):
    b = boyut(g, yid)
    return "" if b == KART_BOYUT else f"yeni gorsel boyutu {b[0]}x{b[1]} ({KART_BOYUT[0]}x{KART_BOYUT[1]} beklenir; okunamazsa da silme yok)"


def boyut_bekle(api, lid, g, yid):
    """boyut alani bos gelirse (Etsy yeni gorselde gec doldurabilir; olculmedi) kararli yeniden okuma, sonra silme karari tek okumaya
    dayanmasin diye stabil_w05 yeniden (inceleme 6 Kas ORTA 2); -> son galeri"""
    if boyut(g, yid) != (None, None):
        return g
    G.kararli(lambda: G.galeri(api, lid), lambda x: boyut(x, yid) != (None, None))
    return stabil_w05(api, lid)


def bag_farki(api, shop, lid, gd, iz):
    """silmeden ONCE renk baglari okunur; plandan farkliysa YALNIZ kaydedilir (iz["bag_farki"]); eski W05 bagsiz oldugu icin silme surer.
    (rank yazimi bag silebilir: 19 Eyl olcumu eski78_gorsel_yukle.py:110; Serdar 6 Kas "Baglari yeniden yaz")"""
    b = bag_imza(G.var_img(api, shop, lid))
    iz["bag_farki"] = None if b == gd["baglar"] else dict(canli=b, plan=gd["baglar"])
    if iz["bag_farki"]:
        log(f"    {lid} yukleme sonrasi renk baglari plandan farkli ({len(b)} / {len(gd['baglar'])}); silmeden sonra yeniden yazilacak")


def bag_yaz(api, shop, lid, gd):
    """plandaki baglar tek variation-images cagrisiyla AYNI haliyle yazilir ve (kararli) geri okunur; esit degilse Hata"""
    hedef = [dict(property_id=p, value_id=v, image_id=i) for p, v, i in gd["baglar"]]
    api.post_json(f"/shops/{shop}/listings/{lid}/variation-images", {"variation_images": hedef})
    vi = G.kararli(lambda: G.var_img(api, shop, lid), lambda v: bag_imza(v) == gd["baglar"])
    if bag_imza(vi) != gd["baglar"]:
        raise Hata(f"bag yeniden yazimi geri okumasi plana esit degil ({len(vi)} / {len(gd['baglar'])} bag)")


def bag_onar(api, shop, lid, gd):
    """yuklemeden sonraki bir DUR'da: baglar plandan farkliysa tek yeniden yazim + geri okuma. -> not listesi (hata yutulmaz, yazilir)"""
    try:
        if bag_imza(G.var_img(api, shop, lid)) == gd["baglar"]:
            return []
        bag_yaz(api, shop, lid, gd)
        return ["renk baglari plandan farkliydi: yeniden yazildi, geri okuma plana esit"]
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        return [f"bag onarimi basarisiz: {str(getattr(e, 'code', None) or e)[:200]}"]


def tani_yaz(api, shop, lid, out, gd, son_g=None, hata="", yid=None, iz=None):
    """her DUR'da (bag onarimindan ONCE, hata anindaki) canli galeri + baglar TANI_<ilan>.json'a (okunamazsa son bilinen galeri + hata).
    Hicbir durumda hata firlatmaz (DUR yolundaki bag onarimi atlanmasin)."""
    x = dict(ilan=lid, hata=hata, yeni_id=yid, eski_id=gd.get("eski_id"), plan_galeri=gd.get("galeri"), plan_baglar=gd.get("baglar"),
             bag_farki_yukleme_sonrasi=(iz or {}).get("bag_farki", "olculmedi"))
    try:
        x.update(canli_galeri=galeri_ozet(G.galeri(api, lid)), canli_baglar=bag_imza(G.var_img(api, shop, lid)))
    except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        x["okuma_hatasi"] = str(getattr(e, "code", None) or e)[:200]
        try:
            x["son_bilinen_galeri"] = galeri_ozet(son_g) if son_g else None
        except Exception:   # noqa: BLE001
            x["son_bilinen_galeri"] = None
    try:
        kaydet(out, "TANI", lid, x)
    except Exception as e:   # noqa: BLE001
        log(f"    {lid} TANI yazilamadi: {str(e)[:120]}")
    return x


def sil_guvenli(api, shop, lid, gd, yid, g):
    """eski W05'i YALNIZ yukleme_durumu ESIT ya da KAYMA ise ve YALNIZ kimligiyle siler (ilan gorselsiz / eksik kalmaz). -> tur"""
    tur, neden = yukleme_durumu(g, gd, yid) if yid else (None, "yeni kimlik yok")
    if not tur:
        raise Hata(f"silme kapisi: yeni gorsel / eski W05 ESIT ya da KAYMA durumunda dogrulanmadi (yeni {yid}): {neden[:160]}; "
                   "eski W05 silinmedi")
    sil_404(api, shop, lid, gd["eski_id"])
    return tur


def sil_404(api, shop, lid, iid):
    """DELETE ok404 (5xx tekrarinda ilk istek islenmis olabilir; galeri_ci11.py:259 deseni); sonuc son okumada dogrulanir"""
    api.delete(f"/shops/{shop}/listings/{lid}/images/{iid}", ok404=True)


def son_okuma(api, shop, lid, gd, yid):
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: gd["eski_id"] not in [x.get("listing_image_id") for x in g])
    g = stabil_w05(api, lid)
    vi = G.var_img(api, shop, lid)
    L = api.get(f"/listings/{lid}") or {}
    s = []
    if sira(galeri_ozet(g)) != son_beklenen(gd, yid):
        s.append("son geri okuma: (rank, kimlik) sirali galeri (n gorsel, rank'lar tekil, eski W05 yerine yeni, digerleri ayni) "
                 f"beklenenden farkli ({[x[:2] for x in galeri_ozet(g)][:13]})")
    if bag_imza(vi) != gd["baglar"]:
        s.append("son geri okuma: renk baglari degisti")
    if L.get("state") != "active":
        s.append(f"son geri okuma: state {L.get('state')}")
    return g, s


def tani_not(out, lid, tani, notlar):
    try:
        kaydet(out, "TANI", lid, dict(tani, bag_onarimi=notlar))
    except Exception:   # noqa: BLE001
        pass


def kaydet(out, ad, lid, x):
    (out / f"{ad}_{lid}.json").write_text(json.dumps(dict(x, ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())), indent=1,
                                                     ensure_ascii=False), encoding="utf-8")


def yaz_ilan(api, shop, lid, gd, yol, out):
    """-> dict(sonuc PASS | DUR, sorun, yeni_id). Otomatik kurtarma YOK (DUR'da yalniz bag onarimi + TANI)."""
    kaydet(out, "YEDEK", lid, gd)
    yid, g, iz, yuklendi = None, None, {}, False
    try:
        if Y.sha256(yol) != gd["sha256"]:
            raise Hata("yerel dosya sha256 plan / MANIFEST_W05 ile ayni degil; yukleme yok")
        yuklendi = True   # bu noktadan sonra yukleme olmus olabilir (belirsiz yukleme dahil)
        yid, _ = Y.yukle_guvenli(api, shop, lid, yol, gd["dosya"], gd["alt"], {i for _, i, _ in gd["galeri"]}, rank=W05_RANK)
        kaydet(out, "ARA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], adim="yuklendi, eski W05 silinmedi"))
        log(f"    {lid} yuklendi: {yid} (rank {W05_RANK})")
        G.kararli(lambda: G.galeri(api, lid), lambda g: any(x.get("listing_image_id") == yid for x in g))
        g = stabil_w05(api, lid)
        g = boyut_bekle(api, lid, g, yid)
        s = sonrasi_sorun(g, gd, yid, yol, iz)
        if s:
            raise Hata("; ".join(s))
        log(f"    {lid} yukleme sonrasi {iz.get('yukleme')}")
        bag_farki(api, shop, lid, gd, iz)
        kaydet(out, "ARA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], adim="yuklendi, eski W05 silinmedi",
                                     yukleme=iz.get("yukleme"), bag_farki_yukleme_sonrasi=iz.get("bag_farki")))
        sil_guvenli(api, shop, lid, gd, yid, g)
        bag_yaz(api, shop, lid, gd)
        g, s = son_okuma(api, shop, lid, gd, yid)
        if s:
            raise Hata("; ".join(s))
        kaydet(out, "SONRA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], alt=gd["alt"],
                                      galeri=galeri_ozet(g), yukleme=iz.get("yukleme"), bag_farki_yukleme_sonrasi=iz.get("bag_farki")))
        return dict(sonuc="PASS", sorun=[] if not iz.get("bag_farki") else ["yukleme sonrasi bag farki vardi; yeniden yazildi (SONRA)"],
                    yeni_id=yid)
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        tani = tani_yaz(api, shop, lid, out, gd, g, m, yid, iz)
        notlar = bag_onar(api, shop, lid, gd) if yuklendi else []
        if notlar:
            tani_not(out, lid, tani, notlar)
        return dict(sonuc="DUR", sorun=[m] + notlar + [f"OTOMATIK KURTARMA YOK: yeni id {yid}, eski W05 {gd['eski_id']}; TANI kaydi; "
                                                       "secenekler --kurtar / --geri-al / elle (Serdar karari)"], yeni_id=yid)


def kurtar_ilan(api, shop, lid, gd, yid, out):
    """YARIM ilan: yalniz silme + bag yazimi + son geri okuma (canli galeri ARA yeni id ile yukleme_durumu ESIT ya da KAYMA)."""
    g, iz = None, {}
    try:
        g = stabil_w05(api, lid)
        tur, neden = yukleme_durumu(g, gd, yid)
        if not tur:
            raise Hata(f"kurtar: canli galeri YARIM (ESIT / KAYMA) beklenen durumda degil; yazma yok: {neden[:160]}")
        iz["yukleme"] = tur
        g = boyut_bekle(api, lid, g, yid)
        b = boyut_sorun(g, yid)
        if b:
            raise Hata(f"kurtar: {b}")
        bag_farki(api, shop, lid, gd, iz)
        sil_guvenli(api, shop, lid, gd, yid, g)
        bag_yaz(api, shop, lid, gd)
        g, s = son_okuma(api, shop, lid, gd, yid)
        if s:
            raise Hata("; ".join(s))
        kaydet(out, "SONRA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], alt=gd["alt"],
                                      galeri=galeri_ozet(g), kurtar=True, yukleme=iz.get("yukleme"),
                                      bag_farki_yukleme_sonrasi=iz.get("bag_farki")))
        return dict(sonuc="PASS", sorun=[], yeni_id=yid)
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        tani = tani_yaz(api, shop, lid, out, gd, g, m, yid, iz)
        notlar = bag_onar(api, shop, lid, gd)
        if notlar:
            tani_not(out, lid, tani, notlar)
        return dict(sonuc="DUR", sorun=[m] + notlar, yeni_id=yid)


def geri_al_ilan(api, shop, lid, gd, onc, out):
    """yeni id = ARA kaydi ya da (canli - plan kimlikleri) TEK kimlik; YALNIZ eski W05 galerideyse yeni id silinir; baglar plandan farkliysa
    yeniden yazilir; son sira = plan. Baska durumda yazma yok ("yalniz elle")."""
    g, yid = None, None
    try:
        g = stabil_w05(api, lid)
        canli = [x.get("listing_image_id") for x in g]
        plan_ids = {i for _, i, _ in gd["galeri"]}
        aday = [i for i in canli if i not in plan_ids]
        ara = (onc or {}).get("ARA")
        if ara:
            if str(ara.get("ilan")) != str(lid):
                raise Hata("geri al: ARA kaydi baska ilanin; yalniz elle")
            yid = ara["yeni_id"]
            if yid not in canli:
                raise Hata(f"geri al: ARA yeni id {yid} galeride yok; yalniz elle")
        elif len(aday) == 1:
            yid = aday[0]
        else:
            raise Hata(f"geri al: plan disi kimlik {len(aday)} (tek degil); yalniz elle")
        if gd["eski_id"] not in canli:
            raise Hata("geri al: eski W05 galeride yok (silinmis); yeni gorsel silinmez, yalniz elle")
        oz = galeri_ozet(g)
        if [(i, a) for _, i, a in oz if i != yid] != [(i, a) for _, i, a in gd["galeri"]]:
            raise Hata("geri al: yeni id disindaki galeri (kimlik sirasi / alt metin) plandan farkli; yalniz elle")
        if [a for _, i, a in oz if i == yid] != [gd["alt"]]:
            raise Hata("geri al: aday gorselin alt metni eski W05 alt metni degil (bu kosunun yuklemesi oldugu dogrulanmadi); yalniz elle")
        sil_404(api, shop, lid, yid)
        G.kararli(lambda: G.galeri(api, lid), lambda g: yid not in [x.get("listing_image_id") for x in g])
        notlar = bag_onar(api, shop, lid, gd)
        if any("basarisiz" in n for n in notlar):
            raise Hata("; ".join(notlar))
        g = stabil_w05(api, lid)
        if sira(galeri_ozet(g)) != [(i, a) for _, i, a in gd["galeri"]]:
            raise Hata("geri al: son sira plan (eski hal) degil")
        if [x[0] for x in galeri_ozet(g)] != list(range(1, gd["n"] + 1)):
            notlar = notlar + [f"UYARI: geri alma sonrasi rank'lar 1..{gd['n']} ardisik degil (Etsy sikistirmadi; sira = plan); "
                               "kapi_once bu ilani BLOK eder, yeniden yazim icin elle (Serdar karari)"]
        kaydet(out, "GERI", lid, dict(ilan=lid, silinen_yeni_id=yid, eski_id=gd["eski_id"], galeri=galeri_ozet(g), notlar=notlar))
        return dict(sonuc="PASS", sorun=notlar, yeni_id=yid)
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        tani = tani_yaz(api, shop, lid, out, gd, g, m, yid)
        notlar = bag_onar(api, shop, lid, gd)
        if notlar:
            tani_not(out, lid, tani, notlar)
        return dict(sonuc="DUR", sorun=[m] + notlar, yeni_id=yid)


# ---------------------------------------------------------------- kosu
def onceki_oku(d, lid):
    x = {}
    for ad in ("SONRA", "ARA"):
        p = Path(d) / f"{ad}_{lid}.json" if d else None
        if p and p.exists():
            x[ad] = json.loads(p.read_text(encoding="utf-8"))
        elif p and (Path(d) / "ilanlar" / f"{ad}_{lid}.json").exists():
            x[ad] = json.loads((Path(d) / "ilanlar" / f"{ad}_{lid}.json").read_text(encoding="utf-8"))
    return x


def calistir(api, shop, a):
    out = Path(a.out); io_ = out / "ilanlar"; io_.mkdir(parents=True, exist_ok=True)
    plan = plan_yukle(a.plan, a.plan_damga)
    yazim = not a.kuru
    sa = [x for x in (a.sadece or "").split(",") if x]
    G_ = plan.get("girdiler") or {}
    bilinmeyen = [x for x in sa if x not in G_]
    if bilinmeyen:
        raise SystemExit(f"DUR: --sadece planda olmayan ilan: {bilinmeyen}")
    lids = sa or sorted(G_)
    t = istek_tahmini()
    satir, dur, t0 = [], None, time.time()
    for n, lid in enumerate(lids, 1):
        gd = G_[lid]
        s = dict(ilan=lid, cift=gd["cift"], durum="", neden=[], istek=None, yeni_id="")
        satir.append(s)
        c0 = api.calls
        try:
            if dur:
                s.update(durum="KALAN", neden=[dur]); continue
            yol = Path(a.dosya_dir) / gd["dosya"] if a.dosya_dir else None
            if not a.geri_al and (yol is None or not yol.exists() or Y.sha256(yol) != gd["sha256"]):
                s.update(durum="BLOK", neden=["yerel W05 dosyasi yok ya da sha256 plandan farkli"]); continue
            gerek = (t["kurtar_en_kotu"] if a.kurtar else t["geri_en_kotu"] if a.geri_al else t["yaz_en_kotu"]) + KOTA_SINIRI
            if api.remaining is not None and int(api.remaining) < (gerek if yazim else OKUMA + KOTA_SINIRI):
                dur = f"kota: kalan {api.remaining} < {gerek if yazim else OKUMA + KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            api.kota_kapisi(f"ilan {lid}")
            c = canli_durum(api, shop, lid)
            if yazim and (api.remaining is None or int(api.remaining) < gerek - OKUMA):   # ilk ilanda kalan 3 GET'ten sonra bilinir
                dur = f"kota: okuma sonrasi kalan {api.remaining} < {gerek - OKUMA}; yazim baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            onc = onceki_oku(a.onceki, lid) if a.onceki else {}
            if a.geri_al:
                if not yazim:
                    s.update(durum="GERI_AL_KURU", neden=["--geri-al kuru: yazim yok"]); continue
                Rz = geri_al_ilan(api, shop, lid, gd, onc, io_)
                s.update(durum="GERI_ALINDI" if Rz["sonuc"] == "PASS" else "DUR", neden=Rz["sorun"], yeni_id=Rz.get("yeni_id") or "")
                if Rz["sonuc"] != "PASS":
                    dur = f"ilan {lid} DUR; kosu durdu"
                continue
            tur = durum_tur(c, gd, onc)
            if tur == "ZATEN_EKSIK":
                s.update(durum="BLOK", neden=[f"galeri yazilmis (5 = onceki yeni gorsel, eski W05 yok) ama renk baglari / state plandan farkli "
                                              f"(bag {len(c['baglar'])} / {len(gd['baglar'])}, state {c.get('state')}); yazim yok, elle (Serdar karari)"],
                         yeni_id=(onc.get("SONRA") or onc.get("ARA"))["yeni_id"])
                continue
            if tur == "ZATEN":
                s.update(durum="ZATEN", neden=["5. sira = onceki kosunun yeni gorseli; eski W05 yok"],
                         yeni_id=(onc.get("SONRA") or onc.get("ARA"))["yeni_id"])
                if yazim and not (a.devam or a.kurtar):
                    s["neden"].append("--devam verilmedi"); s["durum"] = "BLOK"
                continue
            if a.kurtar:
                if tur != "YARIM":
                    s.update(durum="BLOK", neden=["--kurtar: ilan YARIM durumda degil (ARA kaydi + canli ESIT / KAYMA tutmadi); yazma yok"]); continue
                if not yazim:
                    s.update(durum="YARIM", neden=["--kurtar ile silme + son okuma yapilabilir"]); continue
                Rz = kurtar_ilan(api, shop, lid, gd, onc["ARA"]["yeni_id"], io_)
            else:
                if tur == "YARIM":
                    s.update(durum="BLOK", neden=["YARIM: yeni gorsel yuklenmis, eski W05 duruyor; --kurtar ile"]); continue
                neden = kapi_once(c, gd)
                if neden:
                    s.update(durum="BLOK", neden=neden); continue
                if not yazim:
                    s.update(durum="HAZIR"); continue
                Rz = yaz_ilan(api, shop, lid, gd, yol, io_)
            s.update(durum=Rz["sonuc"], neden=Rz["sorun"], yeni_id=Rz.get("yeni_id") or "")
            if Rz["sonuc"] != "PASS":
                dur = f"ilan {lid} {Rz['sonuc']}; kosu durdu"
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani / ag (yazim oncesi okuma)
            m = str(getattr(e, "code", None) or e)[:300]
            s.update(durum="KALAN" if m.startswith("DUR: kota") else "DUR", neden=[m])
            dur = f"ilan {lid} {s['durum']}; kosu durdu"
            if yazim and s["durum"] == "DUR":
                try:
                    tani_yaz(api, shop, lid, io_, gd, None, m)
                except Exception:   # noqa: BLE001
                    pass
        finally:
            if s["istek"] is None:
                s["istek"] = api.calls - c0
            e = time.time() - t0
            log(f"{lid} {gd['cift']} {s['durum']} | istek {s['istek']}" + (f" | {s['neden'][0][:140]}" if s["neden"] else ""))
            log(f"ETA: {n}/{len(lids)} ilan | gecen {e / 60:.1f} dk | kalan {e / n * (len(lids) - n) / 60:.1f} dk | %{100 * n // len(lids)}")
    return satir


def rapor(satir, a, api, out):
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    mod = "kuru" if a.kuru else ("kurtar" if a.kurtar else "geri_al" if a.geri_al else "yazim")
    R = dict(mod=mod, kosu=a.kosu, plan_damga=a.plan_damga, sayilar=say, istek_tahmini=istek_tahmini(), istek=api.calls, ilanlar=satir)
    (out / "RAPOR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "RAPOR.md").write_text(f"# W05 degisim {mod} ({a.kosu}, plan {a.plan_damga})\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                                  + f" | istek {api.calls}\n\n" + "".join(f"- {s['ilan']} {s['cift']} {s['durum']} istek {s['istek']}"
                                                                         + (f": {'; '.join(s['neden'])[:220]}" if s["neden"] else "") + "\n"
                                                                         for s in satir), encoding="utf-8")
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ilan", "cift", "durum", "neden", "istek", "yeni_id"], extrasaction="ignore")
        w.writeheader(); w.writerows(dict(s, neden="; ".join(s["neden"])[:300]) for s in satir)
    log(f"W05_DEGISTIR {mod}: " + " ".join(f"{k}={v}" for k, v in sorted(say.items())) + f" | istek {api.calls}")
    return R


def arg(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alt = ap.add_subparsers(dest="komut")
    p = alt.add_parser("plan")
    p.add_argument("--canli-dir", required=True); p.add_argument("--manifest", required=True); p.add_argument("--out", required=True)
    p.add_argument("--ciftler", default=str(KOK.parents[0] / "data" / "pod" / "pod78_ids.csv"))
    p.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    e = alt.add_parser("etsy")
    e.add_argument("--plan", required=True); e.add_argument("--plan-damga", required=True); e.add_argument("--out", required=True)
    e.add_argument("--kuru", action="store_true"); e.add_argument("--confirm", default="")
    e.add_argument("--onay", default="", help="yazim: W05-YAZ-<sadece> (is akisi onay girdisi; kip + ilan birebir)")
    e.add_argument("--dosya-dir", default=""); e.add_argument("--sadece", default="")
    e.add_argument("--devam", action="store_true"); e.add_argument("--kurtar", action="store_true"); e.add_argument("--onceki", default="")
    e.add_argument("--geri-al", action="store_true", help="tek ilan: yeni id'yi sil (yalniz eski W05 galerideyse), baglari plana dondur")
    e.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    a = ap.parse_args(argv)
    if a.komut is None:
        ap.error("komut: plan | etsy")
    if a.komut == "etsy" and a.kuru and not (a.dosya_dir or a.geri_al):
        raise SystemExit("DUR: kuru kipte --dosya-dir (kart sha256 = plan kontrolu) zorunlu")
    if a.komut == "etsy" and not a.kuru:
        sa = [x for x in (a.sadece or "").split(",") if x]
        if a.confirm != ONAY or not (a.dosya_dir or a.geri_al) or not sa or any(not x.isdigit() for x in sa):
            raise SystemExit(f"DUR: yazim icin --confirm {ONAY} + --dosya-dir + --sadece <acik listing_id listesi>; varsayilan kuru")
        if a.onay != f"W05-YAZ-{','.join(sa)}":
            raise SystemExit("DUR: --onay W05-YAZ-<sadece> (kip + ilan birebir) degil")
        if os.environ.get(KILIT_ORTAM) != "1":
            raise SystemExit(f"DUR: yazim yalniz Etsy kilidi alinmis is akisinda ({KILIT_ORTAM}=1, kilit_bekle.py adimindan sonra)")
        if a.kurtar and (len(sa) != 1 or not a.onceki):
            raise SystemExit("DUR: --kurtar yalniz tek ilan (--sadece) ve --onceki (ARA kaydi) ile")
        if a.geri_al and (len(sa) != 1 or a.kurtar or a.devam):
            raise SystemExit("DUR: --geri-al yalniz tek ilan (--sadece), --kurtar / --devam olmadan")
        if (a.devam or a.kurtar) and not a.onceki:
            raise SystemExit("DUR: --devam / --kurtar icin --onceki <onceki kosu ciktisi>")
    return a


def sonlandir(api, shop, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir = calistir(api, shop, a)
    rapor(satir, a, api, out)
    if a.kuru:
        return 1 if any(s["durum"] in ("DUR", "BLOK", "KALAN") for s in satir) else 0
    return 1 if any(s["durum"] not in ("PASS", "ZATEN", "GERI_ALINDI") for s in satir) else 0


def main(argv=None):
    a = arg(argv)
    if a.komut == "plan":
        return plan_kur(a.canli_dir, a.manifest, a.ciftler, a.out, a.kosu)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    if a.kuru:
        from yd_envanter_oku import salt_okur
        salt_okur(api)
    return sonlandir(api, shop, a)


if __name__ == "__main__":
    sys.exit(main())
