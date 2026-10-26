#!/usr/bin/env python3
"""Poster 78 galeri v10 yukleyicisi (Merkez 26 Eki; Serdar onayi). ETSY'YE YAZAR yalniz --kuru yokken + --confirm GALERI_V10 +
--plan-damga (kuru kosunun PLAN_V10.json'una kilitli). Yazim yolu scripts/etsy/eski78_gorsel_yukle.py bir_ilan (hedef_n=9;
canlida kanitlanmis yol, Serdar 24 Eki): adim_plani (20 siniri), yukle_guvenli (cift yukleme yok), stabil_galeri, durum_uzlas
(Etsy silinen kimligi yeniden verebilir), DEVAM / kurtarma, rank'siz yukleme + ayri sira gecisi (en fazla 2), renk baglari EN SONDA
tek variation-images POST'u (sonra gorsele yazim yok), istek_en_kotu kota kapisi. CDN yedegi alinmaz: Drive yedegi
(TEMP/POSTER_KAPAK_V10_YEDEK/20261026_144404) var ve canli kimlik kumesinin yedekle ayni oldugu asagidaki kapida dogrulanir.
Girdi: galeri_v10_liste.py ciktisi (--hazir: LISTE_OZET.json + <ilan>/LISTE_<ilan>.csv, manifest.json, hedef/), durum dosyalari
(--devam DEVAM.json, --ilerleme ILERLEME.json; json-ilanlar, scripts/ops/durum_dosyasi.py ile kilit ONCESI okunmus).
Ilan basina (4 GET: ilan, galeri, renk baglari, envanter; once api.kota_kapisi):
  DEVAM: DEVAM.json'da bitmemis kayit -> kuru: rapor; yazim: kayit ayni plan_damga ile baslamissa bir_ilan devam / --kurtar.
  ZATEN: 9 gorsel, rank 1..9, alt metinler hedef sirasinda, 5 bag MB->1 DB->6 PW->7 CI->8 WP->9 (ILERLEME kimlikleri varsa onlar).
  BLOK : liste kapisi (dosya / alt metin / renk karisma / yedek) ya da state active degil; galeri 17 degil; 5 renk bagi yok
         (property 200, 5 ad, bir renk birden fazla kayitta, bagli gorsel galeride yok); canli kimlik kumesi != yedek; canli baglar
         != yedek baglar; envanter renk degerleri bag value_id'leriyle ayni degil; bes_x7=zorunlu ve envanterde 5x7 yok;
         plan 20 gorseli asar; yazimda canli durum kuru plandan farkli.
  PLAN : kuru kosuda plan girdisi (canli kimlik sirasi + baglar + hedef sha256 + alt metin + adimlar). Plan sha256 -> plan_damga.
Kota: ilana baslamadan kalan - (en kotu istek) < KOTA_SINIRI (10) ise kosu durur (ilan baslamaz). Ilk DUR'da kosu durur.
Devam: bitmemis DEVAM kaydinda aradaki kapak / bag adimlari tekrarlanir (bir_ilan ara_tekrar=True; erken bag atlanmaz). --kurtar
yalniz hata kaydi olan ilana uygulanir. --bag-onar (onay GALERI_V10_BAG): DEVAM kaydi olan ilanlarda YALNIZ renk baglari
(eski78 bag_kur, hedef_n=9, TEK variation-images cagrisi; galeri hedefle ayni degilse yazmaz), gorsele yazim yok.
Cikti --out: PLAN_V10.json (kuru), RAPOR.json, RAPOR.md, SONUC_SATIR.json; ilanlar/ (bir_ilan PLAN/YEDEK/SONRA/DEVAM)."""
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

ONAY = Y.ONAY_V10
ONAY_BAG = "GALERI_V10_BAG"
N = Y.HEDEF_V10
RENKLER = ("Midnight Blue", "Deep Black", "Pure White", "Champagne Ivory", "Warm Parchment")
RENK_SIRA = {"Midnight Blue": 1, "Deep Black": 6, "Pure White": 7, "Champagne Ivory": 8, "Warm Parchment": 9}
RENK_PID, BOY_PID = 200, 513
KAPI_OKUMA = 4     # ilan, galeri, variation-images, envanter
BES_X7 = re.compile(r"^\s*5\s*[x×]\s*7(\D|$)")


def log(m):
    print(m, flush=True)


def jdump(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def canli_durum(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    g = G.galeri(api, lid)
    vi = G.var_img(api, shop, lid)
    inv = api.get(f"/listings/{lid}/inventory") or {}
    rv, boy = {}, set()
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            for vid, val in zip(pv.get("value_ids") or [None] * len(pv.get("values") or []), pv.get("values") or []):
                if pv.get("property_id") == RENK_PID and val in RENKLER:
                    rv.setdefault(val, (pv.get("property_id"), vid))
                if pv.get("property_id") == BOY_PID:
                    boy.add(val)
    return dict(state=L.get("state"), galeri=g, baglar=vi, rv=rv, bes_x7=any(BES_X7.match(str(b)) for b in boy))


def kapilar(c, man, bes_x7):
    neden = []
    if c["state"] != "active":
        neden.append(f"state {c['state']} (active degil)")
    g = c["galeri"]; ids = [x.get("listing_image_id") for x in g]
    if len(g) != 17:
        neden.append(f"canli galeri {len(g)} gorsel (17 beklenir)")
    b = c["baglar"]; adlar = [x.get("value") for x in b]
    if len(b) != 5 or sorted(map(str, adlar)) != sorted(RENKLER):
        neden.append(f"canli renk bagi {len(b)} kayit / adlar {sorted(set(map(str, adlar)))} (5 renk beklenir)")
    if len(set(adlar)) != len(adlar):
        neden.append("bir renk birden fazla gorselde (variation-images tekrar)")
    if any(x.get("property_id") != RENK_PID for x in b):
        neden.append("renk bagi property 200 degil")
    if any(x.get("image_id") not in ids for x in b):
        neden.append("bagli gorsel canli galeride yok")
    if sorted(ids) != sorted(man["yedek_ids"]):
        neden.append(f"canli kimlik kumesi yedekten farkli (+{len(set(ids) - set(man['yedek_ids']))} "
                     f"-{len(set(man['yedek_ids']) - set(ids))})")
    canli_bag = {x.get("value"): x.get("image_id") for x in b}
    if canli_bag != {k: v["image_id"] for k, v in man["yedek_baglar"].items()}:
        neden.append("canli renk baglari yedekteki baglardan farkli")
    for ad in RENKLER:
        bag_vid = next((x.get("value_id") for x in b if x.get("value") == ad), None)
        if ad not in c["rv"] or c["rv"][ad][1] != bag_vid:
            neden.append(f"envanter renk degeri ({ad}) bag value_id ile ayni degil")
    if bes_x7 == "zorunlu" and not c["bes_x7"]:
        neden.append("bes_x7=zorunlu ama envanterde 5x7 boy yok")
    return neden


def zaten(c, man, kayit_ids=None):
    g = c["galeri"]
    if len(g) != N or [x.get("rank") for x in g] != list(range(1, N + 1)):
        return False
    alt_bek = [Y.alt_norm(h["alt"]) for h in sorted(man["hedef"], key=lambda h: h["sira"])]
    if [Y.alt_norm(x.get("alt_text")) for x in g] != alt_bek:
        return False
    if kayit_ids and [x.get("listing_image_id") for x in g] != list(kayit_ids):
        return False
    rk = {x.get("listing_image_id"): x.get("rank") for x in g}
    b = {x.get("value"): rk.get(x.get("image_id")) for x in c["baglar"]}
    return len(c["baglar"]) == 5 and b == RENK_SIRA


def plan_kur(hazir, lid, man):
    liste = hazir / lid / f"LISTE_{lid}.csv"
    hedef, cikar = Y.liste_oku(liste, N)
    yukle = [r for r in hedef if r["islem"] == "DEGISTIR"]
    if len(yukle) != N or len(cikar) != 17:
        raise Y.Dur(f"LISTE {len(yukle)} DEGISTIR / {len(cikar)} CIKAR (9 / 17 beklenir)")
    for h in man["hedef"]:
        p = hazir / lid / "hedef" / h["ad"]
        if not p.exists() or Y.sha256(p) != h["sha256"]:
            raise Y.Dur(f"hedef dosya {h['ad']} yok ya da sha256 manifestten farkli")
    bagli0 = {v["image_id"] for v in man["yedek_baglar"].values()}
    kapak = next(r for r in yukle if int(r["hedef_sira"]) == 1)
    adim, mx = Y.adim_plani(17, cikar, bagli0, yukle, set(RENK_SIRA.values()), kapak_degisir=kapak, hedef_n=N)
    return adim, mx, Y.sha256(liste)


def plan_girdisi(lid, man, c, adim, mx, liste_sha):
    return dict(ilan=lid, cift=man["cift"], liste_sha=liste_sha,
                canli_galeri=[[x.get("rank"), x.get("listing_image_id")] for x in c["galeri"]],
                canli_baglar=sorted([x.get("value"), x.get("value_id"), x.get("image_id")] for x in c["baglar"]),
                hedef=[[h["sira"], h["ad"], h["sha256"], h["alt"]] for h in sorted(man["hedef"], key=lambda h: h["sira"])],
                adimlar=[list(a) for a in adim], en_fazla=mx,
                en_az=KAPI_OKUMA + Y.istek_en_az(adim, n=N), en_kotu=KAPI_OKUMA + Y.istek_en_kotu(adim, n=N))


def plan_sha(girdiler):
    return hashlib.sha256(jdump(girdiler).encode()).hexdigest()


def plan_yukle(yol, damga):
    p = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+_[0-9a-f]{12}", damga or ""):
        raise SystemExit("DUR: plan_damga bicimi <kuru_kosu>_<sha256 ilk 12>")
    if p.get("plan_damga") != damga or plan_sha(p.get("girdiler") or {})[:12] != damga.split("_", 1)[1]:
        raise SystemExit("DUR: PLAN_V10.json plan_damga / sha256 ile ayni degil; yazma yok")
    return p


def oku_json(p, bos):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).exists() else bos


def calistir(api, shop, a):
    hazir, out = Path(a.hazir), Path(a.out)
    ilan_out = out / "ilanlar"; ilan_out.mkdir(parents=True, exist_ok=True)
    oz = json.loads((hazir / "LISTE_OZET.json").read_text(encoding="utf-8"))
    devam = oku_json(a.devam, {"ilanlar": {}}); ilerleme = oku_json(a.ilerleme, {"ilanlar": {}})
    yazim = not a.kuru
    plan = plan_yukle(a.plan, a.plan_damga) if yazim else None
    if yazim and plan.get("bes_x7") != a.bes_x7:
        raise SystemExit(f"DUR: kuru plan bes_x7={plan.get('bes_x7')}, bu kosu {a.bes_x7}; yazma yok")
    if yazim and not oz.get("yazim"):
        raise SystemExit("DUR: liste --yazim ile uretilmemis (alt metin onayi denetlenmedi); yazma yok")
    t0 = time.time()
    satir, girdiler, dur = [], {}, None
    for lid, o in oz["ilanlar"].items():
        s = dict(ilan=lid, cift=o["cift"], durum="", neden=[], en_az=None, en_kotu=None, istek=None)
        satir.append(s)
        if dur:
            s.update(durum="KALAN", neden=[dur]); continue
        if o["durum"] != "HAZIR":
            s.update(durum="BLOK", neden=list(o["neden"])); continue
        man = json.loads((hazir / lid / "manifest.json").read_text(encoding="utf-8"))
        dv = (devam.get("ilanlar") or {}).get(lid)
        bitmemis = bool(dv) and dv.get("son_ids") is not None and dv.get("adim", 0) < len(dv.get("plan") or [])
        if yazim and a.azami_dk and (time.time() - t0) / 60 > a.azami_dk:
            dur = f"zaman butcesi {a.azami_dk} dk doldu; ilan baslamadi"; s.update(durum="KALAN", neden=[dur]); continue
        c0 = api.calls; basladi = False
        try:
            api.kota_kapisi(f"ilan {lid}")
            if bitmemis:
                adim = [tuple(x) for x in dv["plan"]]
                s["en_kotu"] = Y.istek_en_kotu(adim, dv.get("adim", 0), ilk=False, n=N)
                s["en_az"] = Y.istek_en_az(adim, dv.get("adim", 0), ilk=False, n=N)
                if not yazim:
                    s.update(durum="DEVAM", neden=[f"DEVAM kaydi adim {dv.get('adim', 0)}/{len(adim)}"
                                                   + (" (hata kaydi: kurtar gerekir)" if dv.get("hata") else "")])
                    continue
                if str(dv.get("uretim_kosu") or "") != a.plan_damga:
                    s.update(durum="BLOK", neden=[f"DEVAM kaydi baska planla basladi ({dv.get('uretim_kosu')}); yazma yok"]); continue
            else:
                c = canli_durum(api, shop, lid)
                kayit_ids = ((ilerleme.get("ilanlar") or {}).get(lid) or {}).get("son_ids")
                if zaten(c, man, kayit_ids):
                    s.update(durum="ZATEN", istek=api.calls - c0)
                    if yazim and (ilerleme.get("ilanlar") or {}).get(lid, {}).get("durum") != "PASS" and (dv or {}).get("durum") != "FAIL":
                        ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=o["cift"], set=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                                       son_ids=[x.get("listing_image_id") for x in c["galeri"]])
                    continue
                neden = kapilar(c, man, a.bes_x7)
                if neden:
                    s.update(durum="BLOK", neden=neden, istek=api.calls - c0); continue
                adim, mx, lsha = plan_kur(hazir, lid, man)
                if mx > G.IMG_LIMIT:
                    s.update(durum="BLOK", neden=[f"plan {mx} gorsel (> {G.IMG_LIMIT})"]); continue
                gd = plan_girdisi(lid, man, c, adim, mx, lsha)
                s.update(en_az=gd["en_az"], en_kotu=gd["en_kotu"])
                if not yazim:
                    girdiler[lid] = gd; s.update(durum="PLAN", istek=api.calls - c0); continue
                if (plan.get("girdiler") or {}).get(lid) != gd:
                    s.update(durum="BLOK", neden=["canli durum / dosyalar kuru plandan farkli; yazma yok"], istek=api.calls - c0); continue
            # yazim: ilana baslamadan kota (kalan - en kotu < sinir -> kosu durur, ilan baslamaz)
            gerek = s["en_kotu"] - (KAPI_OKUMA if not bitmemis else 0) + KOTA_SINIRI
            if api.remaining is not None and int(api.remaining) < gerek:
                dur = f"kota: kalan {api.remaining} < en kotu {gerek - KOTA_SINIRI} + {KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            dvp = ilan_out / f"DEVAM_{lid}.json"
            if bitmemis:   # bitmis kayit kopyalanmaz: ilan yeni plan ile ilk kez baslar (canli = yedek kapisi gecti)
                dvp.write_text(json.dumps(dv, indent=1), encoding="utf-8")
            elif dvp.exists():
                dvp.unlink()
            basladi = True
            if a.devam_hedef_kok:
                os.environ["DEVAM_HEDEF"] = f"{a.devam_hedef_kok}/DEVAM_{lid}.json"
            try:
                R = Y.bir_ilan(api, shop, lid, hazir / lid / f"LISTE_{lid}.csv", hazir / lid / "hedef", hazir / lid / "manifest.json",
                               ilan_out, kuru=False, kurtar=a.kurtar and bitmemis and bool(dv.get("hata")), uretim_kosu=a.plan_damga,
                               hedef_n=N, cdn=False, ara_tekrar=True)
            finally:
                os.environ.pop("DEVAM_HEDEF", None)
                if dvp.exists():
                    d = json.loads(dvp.read_text(encoding="utf-8"))
                    bitti = bool(d.get("plan")) and d.get("adim") == len(d["plan"])
                    devam.setdefault("ilanlar", {})[lid] = dict(d, cift=o["cift"], durum="DUR" if not bitti else "BITTI")
            s.update(durum=R["sonuc"], neden=R.get("sorun") or [], istek=api.calls - c0)
            if lid in (devam.get("ilanlar") or {}):
                devam["ilanlar"][lid]["durum"] = R["sonuc"]   # PASS / FAIL (son geri okuma); exception'da DUR / BITTI kalir
            if R["sonuc"] == "PASS":
                ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=o["cift"], set=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                               son_ids=R.get("son_ids"))
            else:
                dur = f"ilan {lid} {R['sonuc']}; kosu durdu"
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani, Etsy / ag hatasi: kosu durur
            m = str(getattr(e, "code", None) or e)[:300]
            if not basladi and m.startswith("DUR: kota"):   # kota tabani / esigi ilan baslamadan: istek gonderilmedi
                dur = m; s.update(durum="KALAN", neden=[m], istek=api.calls - c0)
                log(f"{lid} {o['cift']} KALAN | {m[:140]}"); continue
            s.update(durum="DUR", neden=[m], istek=api.calls - c0)
            dur = f"ilan {lid} DUR; kosu durdu"
            if yazim:
                eski = (ilerleme.get("ilanlar") or {}).get(lid) or {}
                if eski.get("durum") != "PASS":
                    ilerleme.setdefault("ilanlar", {})[lid] = dict(eski, cift=o["cift"], set=eski.get("set") or "-", durum="DUR",
                                                                   kosu=a.kosu, plan_damga=a.plan_damga)
        log(f"{lid} {o['cift']} {s['durum']}" + (f" | en az {s['en_az']} en kotu {s['en_kotu']}" if s["en_kotu"] else "")
            + (f" | {s['neden'][0][:140]}" if s["neden"] else "") + f" | kota {api.remaining}")
    return satir, girdiler, devam, ilerleme


def bag_onar(api, shop, a):
    """DEVAM kaydi olan ilanlarda yalniz renk baglari (eski78 bag_kur, hedef_n=9). Kayitsiz ilan ATLA."""
    hazir, out = Path(a.hazir), Path(a.out) / "ilanlar"; out.mkdir(parents=True, exist_ok=True)
    oz = json.loads((hazir / "LISTE_OZET.json").read_text(encoding="utf-8"))
    devam = oku_json(a.devam, {"ilanlar": {}}); ilerleme = oku_json(a.ilerleme, {"ilanlar": {}})
    satir, dur = [], None
    for lid, o in oz["ilanlar"].items():
        s = dict(ilan=lid, cift=o["cift"], durum="", neden=[], en_az=None, en_kotu=Y.BAG_ISTEK, istek=None)
        satir.append(s)
        dv = (devam.get("ilanlar") or {}).get(lid)
        if dur:
            s.update(durum="KALAN", neden=[dur]); continue
        if not dv or not dv.get("plan"):
            s.update(durum="ATLA", neden=["DEVAM kaydi yok (bag onarimi yalniz yuklenmis ilanda)"]); continue
        if str(dv.get("uretim_kosu") or "") != a.plan_damga:
            s.update(durum="BLOK", neden=[f"DEVAM kaydi baska planla ({dv.get('uretim_kosu')})"]); continue
        dvp = out / f"DEVAM_{lid}.json"; dvp.write_text(json.dumps(dv, indent=1), encoding="utf-8")
        c0 = api.calls
        try:
            api.kota_kapisi(f"ilan {lid}")
            R = Y.bag_kur(api, shop, lid, hazir / lid / f"LISTE_{lid}.csv", hazir / lid / "manifest.json", dvp, out, yaz=True, hedef_n=N)
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
            R = dict(sonuc="DUR", sorun=[str(getattr(e, "code", None) or e)[:300]])
        s.update(durum=R["sonuc"], neden=R.get("sorun") or [], istek=api.calls - c0)
        if R["sonuc"] == "PASS":
            d = dict(dv, adim=len(dv["plan"]), bekleyen=None, durum="PASS")
            if d.get("hata"):
                d.setdefault("hata_gecmis", []).append(d.pop("hata"))
            devam["ilanlar"][lid] = d
            ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=o["cift"], set=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                           son_ids=[x["listing_image_id"] for x in R.get("galeri") or []])
        else:
            dur = f"ilan {lid} {R['sonuc']}; kosu durdu"
        log(f"{lid} {o['cift']} bag onarimi {s['durum']}" + (f" | {s['neden'][0][:140]}" if s["neden"] else "") + f" | kota {api.remaining}")
    return satir, {}, devam, ilerleme


def rapor(satir, girdiler, a, api, out):
    say = {}
    for s in satir:
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    nedenler = {}
    for s in satir:
        if s["durum"] in ("BLOK", "DUR", "KALAN", "FAIL"):
            for n in s["neden"] or ["-"]:
                k = re.sub(r"\d{6,}", "#", n)[:120]
                nedenler[k] = nedenler.get(k, 0) + 1
    ek = [s["en_kotu"] for s in satir if s["en_kotu"]]
    ea = [s["en_az"] for s in satir if s["en_az"]]
    R = dict(mod="kuru" if a.kuru else ("bag" if a.bag_onar else "yazim"), kosu=a.kosu, bes_x7=a.bes_x7, sayilar=say, blok_nedenleri=nedenler,
             en_kotu_ilan=max(ek) if ek else None, en_az_ilan=min(ea) if ea else None, en_kotu_toplam=sum(ek), en_az_toplam=sum(ea),
             istek=api.calls, kalan_kota=api.remaining, ilanlar=satir)
    if a.kuru:
        sh = plan_sha(girdiler); R["plan_damga"] = f"{a.kosu}_{sh[:12]}"
        (out / "PLAN_V10.json").write_text(json.dumps(dict(plan_damga=R["plan_damga"], kosu=a.kosu, bes_x7=a.bes_x7, girdiler=girdiler),
                                                      indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "RAPOR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# Galeri v10 {R['mod']} ({a.kosu})\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                + f"\n\nIstek (kod okumasi): ilan basina en az {R['en_az_ilan']} / en kotu {R['en_kotu_ilan']}; toplam en az "
                  f"{R['en_az_toplam']} / en kotu {R['en_kotu_toplam']} | bu kosu istek {api.calls}, kalan kota {api.remaining}\n"
                + (f"plan_damga: {R.get('plan_damga')}\n" if a.kuru else "") + "\n## Nedenler\n"
                + "".join(f"- {v} ilan: {k}\n" for k, v in sorted(nedenler.items(), key=lambda x: -x[1])) + "\n## Ilanlar\n"
                + "".join(f"- {s['ilan']} {s['cift']} {s['durum']} en_az {s['en_az']} en_kotu {s['en_kotu']}"
                          + (f": {'; '.join(s['neden'])[:200]}" if s["neden"] else "") + "\n" for s in satir))
    log(f"GALERI_V10 {R['mod']}: " + " ".join(f"{k}={v}" for k, v in sorted(say.items()))
        + f" | en kotu ilan {R['en_kotu_ilan']} toplam {R['en_kotu_toplam']} | istek {api.calls} kalan kota {api.remaining}"
        + (f" | plan_damga {R['plan_damga']}" if a.kuru else ""))
    return R


SONUC_ALAN = ["ilan", "cift", "durum", "neden", "kosu", "plan_damga", "en_az", "en_kotu", "istek"]


def sonuc_yaz(yol, satir, a):
    """SONUC.csv: ilan basina son durum (KALAN satiri onceki kaydi degistirmez)."""
    p = Path(yol)
    eski = list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() and p.stat().st_size else []
    kay = {r["ilan"]: r for r in eski}
    for s in satir:
        if s["durum"] == "KALAN" and s["ilan"] in kay:
            continue
        kay[s["ilan"]] = dict(ilan=s["ilan"], cift=s["cift"], durum=s["durum"], neden="; ".join(s["neden"])[:300], kosu=a.kosu,
                              plan_damga=a.plan_damga, en_az=s["en_az"] or "", en_kotu=s["en_kotu"] or "", istek=s["istek"] or "")
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SONUC_ALAN, extrasaction="ignore"); w.writeheader()
        w.writerows(kay[k] for k in sorted(kay))


def arg(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hazir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--devam", default=""); ap.add_argument("--ilerleme", default="")
    ap.add_argument("--sonuc", default="", help="yazim: SONUC.csv (anahtar ilan) guncellenir")
    ap.add_argument("--bes-x7", required=True, choices=("zorunlu", "yok"))
    ap.add_argument("--kuru", action="store_true"); ap.add_argument("--confirm", default="")
    ap.add_argument("--plan", default=""); ap.add_argument("--plan-damga", default="")
    ap.add_argument("--kurtar", action="store_true", help="DEVAM kaydinda hata olan ilanlarda kayitli plan + canli galeriyle surdur")
    ap.add_argument("--bag-onar", action="store_true", help=f"yalniz renk baglari (--confirm {ONAY_BAG} + --plan-damga)")
    ap.add_argument("--kosu", default=os.environ.get("GITHUB_RUN_ID", "0"))
    ap.add_argument("--azami-dk", type=float, default=0, help="yazim: bu sureden sonra yeni ilana baslanmaz (0 = sinirsiz)")
    ap.add_argument("--devam-hedef-kok", default="", help="her yazimdan once / sonra DEVAM_<ilan>.json kopyasi (rclone hedefi)")
    a = ap.parse_args(argv)
    if a.bag_onar:
        if a.kuru or a.confirm != ONAY_BAG or not re.fullmatch(r"\d+_[0-9a-f]{12}", a.plan_damga or ""):
            raise SystemExit(f"DUR: bag onarimi icin --confirm {ONAY_BAG} + --plan-damga (kuru degil)")
    elif not a.kuru and (a.confirm != ONAY or not a.plan or not a.plan_damga):
        raise SystemExit(f"DUR: yazim icin --confirm {ONAY} + --plan + --plan-damga")
    return a


def main(argv=None):
    a = arg(argv)
    from etsy_common import Etsy, TokenStore, mask
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", ""); mask(k); mask(s)
    st = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if st.needs_refresh():
        st.refresh()
    api = Etsy(st); shop = os.environ["ETSY_SHOP_ID"]
    if a.kuru:   # kuru: yazma yontemleri kapali (yd_envanter_oku.salt_okur)
        from yd_envanter_oku import salt_okur
        salt_okur(api)
    return sonlandir(api, shop, a)


def sonlandir(api, shop, a):
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    satir, girdiler, devam, ilerleme = (bag_onar if a.bag_onar else calistir)(api, shop, a)
    R = rapor(satir, girdiler, a, api, out)
    if not a.kuru:
        if a.devam:
            Path(a.devam).write_text(json.dumps(devam, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        if a.ilerleme:
            Path(a.ilerleme).write_text(json.dumps(ilerleme, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "SONUC_SATIR.json").write_text(json.dumps(satir, indent=1, ensure_ascii=False), encoding="utf-8")
        if a.sonuc:
            sonuc_yaz(a.sonuc, satir, a)
    kotu = [s for s in satir if s["durum"] in ("DUR", "FAIL")]
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main())
