#!/usr/bin/env python3
"""P1-G: 78 poster ilaninda galeri rank 5 W05_SUREC kartini yeni metinli kartla degistirme (Serdar 6 Kas, AŞAMA 1 hazirlik).
KOSTURMA AYRI ONAYLA. Bu asamada yukleme IS AKISI YOK (main'e girmez); betik + testler var. updateListing / PATCH YOK.
Kartlar: p1g_kart.py uret (yontem b) MANIFEST_W05.csv (durum PASS = kimlik zinciri + canli OCR + bilinen PASS + kart kapilari).

Modlar:
  plan  : ETSY YOK. --canli-dir (galeri-v11-yedek-oku <ilan>_<CIFT>/GALERI.json) + --manifest MANIFEST_W05.csv -> PLAN_W05.json + PLAN_W05.md.
          Ilan basina: eski r5 listing_image_id, galeri (rank, kimlik, alt metin), renk baglari, eski W05 alt metni (yeni gorsele AYNEN),
          dosya, sha256, istek tahmini, kota ihtiyaci (en kotu + KOTA_SINIRI). BLOK: kart PASS degil / kimlik PASS degil, W05'e renk bagi
          var, galeri + 1 > 20, rank 5 yok. plan_damga = <kosu>_<sha256 ilk 12>.
  --kuru: ETSY SALT OKUMA (yd_envanter_oku.salt_okur: yazma yontemleri kapali). Ilan basina 3 GET (ilan, galeri, renk baglari);
          canli == plan -> HAZIR | ZATEN (--onceki SONRA kaydiyla) | YARIM (--onceki ARA kaydiyla) | BLOK.
  yazim : --confirm W05_DEGISTIR + --plan + --plan-damga + --dosya-dir + --sadece <acik listing_id listesi> + ortam W05_KILIT=1 (is akisi
          kilit_bekle.py adimindan SONRA koyar; kilit kumesi main'deki kilit_bekle.py). Ilan basina sira:
    1 kota: kalan >= en kotu + KOTA_SINIRI (ilan baslamadan, ve ilk ilanda kalan bilinmiyorsa 3 GET sonrasi yeniden; bilinmezse KALAN)
    2 canli okuma (3 GET) == plan: galeri kimlik / sira / alt metin, renk baglari, state active; rank 5 = plan eski_id; W05'e bag yok;
      galeri + 1 <= 20; yerel dosya sha256 = plan sha256 (= MANIFEST_W05)
    3 YEDEK_<ilan>.json (plan girdisi + zaman)
    4 YUKLEME: yeni kart rank 5'e, ESKI W05 alt metniyle (eski78_gorsel_yukle.yukle_guvenli: cift yukleme yok); ARA_<ilan>.json (yeni id)
    5 YUKLEME SONRASI KAPILARI (stabil geri okuma): n+1 gorsel; rank 1-4 ayni; rank 5 = yeni id ve alt metni = eski W05 alt metni;
      rank 6 = eski W05; 7.. = eski 6..; yuklenen dosya sha256 = MANIFEST sha256 (yukleme boyunca degismedi)
    5b renk baglari geri okunur = plan (degistiyse silme yok, DUR)
    6 SILME: eski W05 (sil_guvenli: yalniz 5 dogrulandiysa; yeni gorsel yokken silme denemesi FAIL). Sira kontrolleri rank NUMARASI degil
      kimlik SIRASI (Etsy silmeden sonra rank'lari sikistirmayabilir)
    7 son geri okuma (stabil): n gorsel, kimlikler = eski liste (eski_id yerine yeni id), alt metinler ayni; baglar aynen; state active
    8 SONRA_<ilan>.json (yeni id, sha256, alt metin)
  OTOMATIK KURTARMA YOK: herhangi bir adim tutmazsa ilan DUR (yeni / eski kimlikler ARA kaydinda), kosu durur (sonrakiler KALAN).
  --devam --onceki <dir>: canli durumu ZATEN olan ilan (rank 5 = onceki SONRA yeni id, eski id galeride yok) atlanir; yazilmaz.
  --kurtar --onceki <dir>: YALNIZ YARIM ilan (ARA kaydi var; canli rank 5 = ARA yeni id + eski alt metin, rank 6 = eski W05, digerleri
          plan kaymasiyla ayni): yalniz adim 6-8 (silme + son geri okuma). Baska durumda yazma yok. --sadece tek ilan zorunlu.
Istek (kod okumasi, istek_tahmini()). GET 5xx / 429 kisa tekrarlari dahil degil (sert taban 10 her istekten once durdurur).
Cikti --out: PLAN_W05.json / .md (plan), RAPOR.json, RAPOR.md, SONUC.csv, ilanlar/{YEDEK,ARA,SONRA}_<ilan>.json."""
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


def log(m):
    print(m, flush=True)


def jdump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


class Hata(Exception):
    """yazim sirasinda kapi tutmadi: ilan DUR (otomatik kurtarma yok)"""


# ---------------------------------------------------------------- istek tahmini
def istek_tahmini():
    """O = cl_galeri_degistir.OKUMA_TEKRAR. Yazim istekleri en kotu 3 gonderim (5xx) + 1 (401); post_file tekrar=1 + 401 = 2 / deneme.
      kuru      : 3 GET.
      yaz en az : 3 + yukleme 1 + gorunur 1 + stabil 2 + bag 1 + silme 1 + son (silindi gorunur 1 + stabil 2) + var_img 1 + ilan 1 = 14.
      yaz en kotu: 3 + yukleme (2 + 1 [429 okumasi]) + (2 + O) + gorunur O + stabil O + bag 1 + silme 4 + son (O + O) + 1 + 1.
      kurtar    : 3 + stabil O + bag 1 + silme 4 + son (O + O) + 1 + 1 (en az 12)."""
    O = G.OKUMA_TEKRAR
    en_kotu = OKUMA + (2 + 1) + (2 + O) + O + O + 1 + 4 + O + O + 1 + 1
    return dict(kuru=OKUMA, yaz_en_az=OKUMA + 1 + 1 + 2 + 1 + 1 + 1 + 2 + 1 + 1, yaz_en_kotu=en_kotu,
                kurtar_en_az=OKUMA + 2 + 1 + 1 + 1 + 2 + 1 + 1, kurtar_en_kotu=OKUMA + O + 1 + 4 + O + O + 1 + 1, okuma_tekrar=O,
                kota_ihtiyac=en_kotu + KOTA_SINIRI)


# ---------------------------------------------------------------- plan (Etsy yok)
def galeri_ozet(g):
    return [[int(x.get("rank") or 0), int(x.get("listing_image_id") or 0), Y.alt_norm(x.get("alt_text"))]
            for x in sorted(g, key=lambda y: y.get("rank") or 0)]


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


def kayma(gd, yid):
    """yukleme sonrasi beklenen sira: 1-4 ayni, 5 = yeni (eski W05 alt metni), 6 = eski W05, 7.. = eski 6.."""
    q = [(i, a) for _, i, a in gd["galeri"]]
    return q[:W05_RANK - 1] + [(yid, gd["alt"])] + q[W05_RANK - 1:]


def son_beklenen(gd, yid):
    return [(yid if i == gd["eski_id"] else i, a) for _, i, a in gd["galeri"]]


def kapi_once(c, gd):
    s = []
    if c["state"] != "active":
        s.append(f"state {c['state']} (active degil)")
    oz = galeri_ozet(c["galeri"])
    if sira(oz) != [(i, a) for _, i, a in gd["galeri"]] or len(oz) < W05_RANK or oz[W05_RANK - 1][1] != gd["eski_id"]:
        s.append("canli galeri (kimlik sirasi / alt metin / rank 5 = eski W05) plandan farkli")
    if bag_imza(c["baglar"]) != gd["baglar"]:
        s.append("canli renk baglari plandan farkli")
    if any(b[2] == gd["eski_id"] for b in bag_imza(c["baglar"])):
        s.append("W05'e renk bagi var")
    if len(c["galeri"]) + 1 > AZAMI_GORSEL:
        s.append(f"galeri {len(c['galeri'])} + 1 > {AZAMI_GORSEL}")
    return s


def durum_tur(c, gd, onceki):
    """ZATEN (onceki SONRA ya da ARA yeni id 5. sirada, eski id yok, digerleri ayni) | YARIM (ARA yeni id 5., eski W05 6.) | None"""
    q = sira(galeri_ozet(c["galeri"]))
    for ad in ("SONRA", "ARA"):
        x = (onceki or {}).get(ad)
        if x and q is not None and q == son_beklenen(gd, x["yeni_id"]):
            return "ZATEN"
    ara = (onceki or {}).get("ARA")
    if ara and q is not None and q == kayma(gd, ara["yeni_id"]):
        return "YARIM"
    return None


def sonrasi_sorun(g, gd, yid, yol):
    s = []
    q = sira(galeri_ozet(g))
    if q is None:
        s.append("yukleme sonrasi rank'lar kesin artan / tekil degil")
    elif q != kayma(gd, yid):
        s.append("yukleme sonrasi sira beklenenden farkli (1-4 ayni, 5 yeni + eski W05 alt metni, 6 eski W05, 7.. eski 6..)")
    yeni = [x for x in g if x.get("listing_image_id") == yid]
    if yeni and (yeni[0].get("full_width"), yeni[0].get("full_height")) not in ((3000, 2250), (None, None)):
        s.append(f"yeni gorsel boyutu {yeni[0].get('full_width')}x{yeni[0].get('full_height')} (3000x2250 beklenir)")
    if Y.sha256(yol) != gd["sha256"]:
        s.append("yuklenen dosya sha256 MANIFEST_W05 sha256 ile ayni degil")
    return s


def bag_kapisi(api, shop, lid, gd):
    """silmeden ONCE: renk baglari plandaki ile ayni (rank yazimi bag silebilir, 19 Eyl olcumu eski78_gorsel_yukle.py:110)"""
    if bag_imza(G.var_img(api, shop, lid)) != gd["baglar"]:
        raise Hata("yukleme sonrasi renk baglari plandan farkli; eski W05 silinmedi")


def sil_guvenli(api, shop, lid, gd, yid, g):
    """eski W05'i YALNIZ yeni gorsel 5. sirada ve eski W05 6. sirada dogrulandiysa siler (ilan gorselsiz / eksik kalmaz)."""
    q = sira(galeri_ozet(g)) or []
    if not yid or len(q) <= W05_RANK or q[W05_RANK - 1][0] != yid or q[W05_RANK][0] != gd["eski_id"]:
        raise Hata(f"silme kapisi: yeni gorsel 5. sirada / eski W05 6. sirada dogrulanmadi (yeni {yid}, sira {[x[0] for x in q][:7]}); "
                   "eski W05 silinmedi")
    G.gorsel_sil(api, shop, lid, gd["eski_id"])


def son_okuma(api, shop, lid, gd, yid):
    g = G.kararli(lambda: G.galeri(api, lid), lambda g: gd["eski_id"] not in [x.get("listing_image_id") for x in g])
    g = Y.stabil_galeri(api, lid)
    vi = G.var_img(api, shop, lid)
    L = api.get(f"/listings/{lid}") or {}
    s = []
    if sira(galeri_ozet(g)) != son_beklenen(gd, yid):
        s.append("son geri okuma: galeri sirasi (eski W05 yerine yeni, digerleri ayni) beklenenden farkli")
    if bag_imza(vi) != gd["baglar"]:
        s.append("son geri okuma: renk baglari degisti")
    if L.get("state") != "active":
        s.append(f"son geri okuma: state {L.get('state')}")
    return g, s


def kaydet(out, ad, lid, x):
    (out / f"{ad}_{lid}.json").write_text(json.dumps(dict(x, ts_utc=time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())), indent=1,
                                                     ensure_ascii=False), encoding="utf-8")


def yaz_ilan(api, shop, lid, gd, yol, out):
    """-> dict(sonuc PASS | DUR, sorun, yeni_id). Otomatik kurtarma YOK."""
    kaydet(out, "YEDEK", lid, gd)
    yid = None
    try:
        if Y.sha256(yol) != gd["sha256"]:
            raise Hata("yerel dosya sha256 plan / MANIFEST_W05 ile ayni degil; yukleme yok")
        yid, _ = Y.yukle_guvenli(api, shop, lid, yol, gd["dosya"], gd["alt"], {i for _, i, _ in gd["galeri"]}, rank=W05_RANK)
        kaydet(out, "ARA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], adim="yuklendi, eski W05 silinmedi"))
        log(f"    {lid} yuklendi: {yid} (rank {W05_RANK})")
        G.kararli(lambda: G.galeri(api, lid), lambda g: any(x.get("listing_image_id") == yid for x in g))
        g = Y.stabil_galeri(api, lid)
        s = sonrasi_sorun(g, gd, yid, yol)
        if s:
            raise Hata("; ".join(s))
        bag_kapisi(api, shop, lid, gd)
        sil_guvenli(api, shop, lid, gd, yid, g)
        g, s = son_okuma(api, shop, lid, gd, yid)
        if s:
            raise Hata("; ".join(s))
        kaydet(out, "SONRA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], alt=gd["alt"],
                                      galeri=galeri_ozet(g)))
        return dict(sonuc="PASS", sorun=[], yeni_id=yid)
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        m = str(getattr(e, "code", None) or e)[:300]
        return dict(sonuc="DUR", sorun=[m, f"OTOMATIK KURTARMA YOK: yeni id {yid}, eski W05 {gd['eski_id']}; ARA kaydi + --kurtar ya da elle"],
                    yeni_id=yid)


def kurtar_ilan(api, shop, lid, gd, yid, out):
    """YARIM ilan: yalniz silme + son geri okuma (yeni gorsel rank 5'te ve eski W05 rank 6'da dogrulanarak)."""
    try:
        g = Y.stabil_galeri(api, lid)
        if sira(galeri_ozet(g)) != kayma(gd, yid):
            raise Hata("kurtar: canli galeri YARIM beklenen durumda degil; yazma yok")
        bag_kapisi(api, shop, lid, gd)
        sil_guvenli(api, shop, lid, gd, yid, g)
        g, s = son_okuma(api, shop, lid, gd, yid)
        if s:
            raise Hata("; ".join(s))
        kaydet(out, "SONRA", lid, dict(ilan=lid, yeni_id=yid, eski_id=gd["eski_id"], sha256=gd["sha256"], alt=gd["alt"],
                                      galeri=galeri_ozet(g), kurtar=True))
        return dict(sonuc="PASS", sorun=[], yeni_id=yid)
    except (Hata, Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
        return dict(sonuc="DUR", sorun=[str(getattr(e, "code", None) or e)[:300]], yeni_id=yid)


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
            if yazim and (yol is None or not yol.exists() or Y.sha256(yol) != gd["sha256"]):
                s.update(durum="BLOK", neden=["yerel W05 dosyasi yok ya da sha256 plandan farkli"]); continue
            gerek = (t["kurtar_en_kotu"] if a.kurtar else t["yaz_en_kotu"]) + KOTA_SINIRI
            if api.remaining is not None and int(api.remaining) < (gerek if yazim else OKUMA + KOTA_SINIRI):
                dur = f"kota: kalan {api.remaining} < {gerek if yazim else OKUMA + KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            api.kota_kapisi(f"ilan {lid}")
            c = canli_durum(api, shop, lid)
            if yazim and (api.remaining is None or int(api.remaining) < gerek - OKUMA):   # ilk ilanda kalan 3 GET'ten sonra bilinir
                dur = f"kota: okuma sonrasi kalan {api.remaining} < {gerek - OKUMA}; yazim baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            onc = onceki_oku(a.onceki, lid) if a.onceki else {}
            tur = durum_tur(c, gd, onc)
            if tur == "ZATEN":
                s.update(durum="ZATEN", neden=["5. sira = onceki kosunun yeni gorseli; eski W05 yok"],
                         yeni_id=(onc.get("SONRA") or onc.get("ARA"))["yeni_id"])
                if yazim and not (a.devam or a.kurtar):
                    s["neden"].append("--devam verilmedi"); s["durum"] = "BLOK"
                continue
            if a.kurtar:
                if tur != "YARIM":
                    s.update(durum="BLOK", neden=["--kurtar: ilan YARIM durumda degil (ARA kaydi + canli kayma tutmadi); yazma yok"]); continue
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
    mod = "kuru" if a.kuru else ("kurtar" if a.kurtar else "yazim")
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
    e.add_argument("--dosya-dir", default=""); e.add_argument("--sadece", default="")
    e.add_argument("--devam", action="store_true"); e.add_argument("--kurtar", action="store_true"); e.add_argument("--onceki", default="")
    e.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    a = ap.parse_args(argv)
    if a.komut is None:
        ap.error("komut: plan | etsy")
    if a.komut == "etsy" and not a.kuru:
        sa = [x for x in (a.sadece or "").split(",") if x]
        if a.confirm != ONAY or not a.dosya_dir or not sa or any(not x.isdigit() for x in sa):
            raise SystemExit(f"DUR: yazim icin --confirm {ONAY} + --dosya-dir + --sadece <acik listing_id listesi>; varsayilan kuru")
        if os.environ.get(KILIT_ORTAM) != "1":
            raise SystemExit(f"DUR: yazim yalniz Etsy kilidi alinmis is akisinda ({KILIT_ORTAM}=1, kilit_bekle.py adimindan sonra)")
        if a.kurtar and (len(sa) != 1 or not a.onceki):
            raise SystemExit("DUR: --kurtar yalniz tek ilan (--sadece) ve --onceki (ARA kaydi) ile")
        if (a.devam or a.kurtar) and not a.onceki:
            raise SystemExit("DUR: --devam / --kurtar icin --onceki <onceki kosu ciktisi>")
    return a


def sonlandir(api, shop, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir = calistir(api, shop, a)
    rapor(satir, a, api, out)
    if a.kuru:
        return 1 if any(s["durum"] in ("DUR", "BLOK", "KALAN") for s in satir) else 0
    return 1 if any(s["durum"] not in ("PASS", "ZATEN") for s in satir) else 0


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
