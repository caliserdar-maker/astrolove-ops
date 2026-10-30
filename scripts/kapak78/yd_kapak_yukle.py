#!/usr/bin/env python3
"""YD (1st Anniversary) 78 ilan: kapak + yeni 10'lu galeri yukleyicisi, TEK SEFERDE (plan v3 adim 7; Serdar 27 Eki). ETSY'YE YAZAR
yalniz --kuru yokken + --confirm YD_KAPAK + --plan-damga (kuru kosunun PLAN_YD.json'una kilitli). Kuru kosu, pilot ve yukleme ayri
Serdar onayiyla (poster galerisi 78/78 sonrasi).
Galeri (rank): 1 kapak (bagsiz), 2 sembol, 3 kisisellestirme, 4 format (ORTAK), 5 surec (cifte ozel), 6 Starlit, 7 Timeless, 8 First Page,
9 Layers, 10 Botanical. Style (513) baglari yeni kartlara: Starlit->6 ... Botanical->10. Eski 13 gorselin hepsi silinir (adim 5 yedegi).
Yazim yolu scripts/etsy/eski78_gorsel_yukle.py bir_ilan; poster v10 ile AYNI genellestirme, YD profili (hedef_n=10, degerler=Style 513,
cdn=False, ara_tekrar=True): adim_plani aynen (kapak yukle -> kapak rank 1 -> her stil kartindan once bagsiz bir eski gorsel sil ->
5 stil karti -> erken bag -> diger yuklemeler (her birinden once bir eski sil) -> kalan eski silinir -> sira -> son bag; en fazla 14
gorsel), yukle_guvenli (cift yukleme yok), stabil_galeri, durum_uzlas, DEVAM / kurtarma, sira gecisi (en fazla 2), bag_kur onarimi,
istek_en_kotu kota kapisi. CDN yedegi alinmaz: adim 5 Drive yedegi (TEMP/YD_KAPAK_V1_YEDEK) liste kapisinda dogrulanir.
Girdi: yd_liste_uret.py liste ciktisi (--hazir: LISTE_OZET.json + <ilan>/LISTE_<ilan>.csv, manifest.json, hedef/NN_N.jpg),
durum dosyalari (--devam DEVAM.json, --ilerleme ILERLEME.json; durum_dosyasi.py ile kilit sonrasi okunur; ILERLEME set = hedef = 10).
Ilan basina degerlendirme SIRASI (plan v3 adim 7): once DEVAM, sonra ZATEN, en son BLOK (liste kapisi dahil; BLOK yalniz ilk kosuda, yarim ilan BLOK'a dusmez).
  DEVAM: DEVAM.json'da bitmemis kayit -> kuru: rapor (kayitli plan_damga ile); yazim: bir_ilan kayitli plan + LISTE sha256 ile devam /
         --kurtar (bu kosunun plan_damga'si farkli olabilir). Yarim ilanin PASS disi sonucu cikis 1.
  ZATEN: rank 1 alt metni = yeni alt metin VE rank 1 kimligi kayitta (DEVAM yuklenen / ILERLEME son_ids[0]) VE galeri hedefle ayni
         (10, rank 1..10, alt metinler hedef sirasinda, 5 bag sira 6..10). Yeni alt metin var ama kayit yok (ya da galeri farkli) -> BLOK (elle).
  BLOK : liste kapisi (QC / dosya / sha / yedek / alt metin) ya da state active degil | galeri 13 degil | Style bagi 5 degil, property
         513 degil, tekrarli ya da bagli gorsel galeride yok | kapak (rank 1) bagli | Botanical bagli gorsel KAPAK_KAYNAK kaynak_image_id
         degil | canli kimlik kumesi yedekten (HAM) farkli | canli baglar yedekten farkli | envanter Style degerleri bag value_id'leriyle
         ayni degil | 10 dosyadan biri JPEG / karta gore boyut degil ya da sha256 manifest + tasima MANIFEST ile ayni degil | plan 20
         gorseli asar | yazimda canli durum kuru plandan farkli.
  PLAN : kuru kosuda plan girdisi (canli kimlik sirasi + baglar + hedef sha256 + alt metin + adimlar). Plan sha256 -> plan_damga.
Kota: ilana baslamadan kalan - (en kotu istek) < KOTA_SINIRI (10) ise kosu durur (ilan baslamaz). Ilk DUR'da kosu durur.
Cikti --out: PLAN_YD.json (kuru), RAPOR.json, RAPOR.md, SONUC_SATIR.json; ilanlar/ (bir_ilan PLAN/YEDEK/SONRA/DEVAM)."""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy")); sys.path.insert(0, str(KOK / "kapak78"))
import cl_galeri_degistir as G  # noqa: E402
import eski78_gorsel_yukle as Y  # noqa: E402
import yd_liste_uret as LU  # noqa: E402  (eski kapak kurali, Serdar 30 Eki)
import galeri_v10_yukle as V  # noqa: E402  (yalniz jdump / oku_json / sonuc_yaz; poster yukleyicisi degismez)
from etsy_common import KOTA_SINIRI  # noqa: E402  (Serdar 15 ve 24 Eki: 10; degistirilmez)

ONAY = Y.ONAY_YD
ONAY_BAG = "YD_KAPAK_BAG"
N = Y.HEDEF_YD
STIL_PID = 513
STILLER = ("Starlit", "Timeless", "First Page", "Layers", "Botanical")
STIL_SIRA = {"Starlit": 6, "Timeless": 7, "First Page": 8, "Layers": 9, "Botanical": 10}   # Serdar 27 Eki
N_ESKI = 13        # canli YD galerisi (YD_OZET 78/78); hepsi yedeklenip silinir
KART_BOYUT = {k: (3000, 2250) for k in range(1, N + 1)}   # Merkez 27 Eki karar e: tum kartlar 4:3
KAPI_OKUMA = 4     # ilan, galeri, variation-images, envanter


def log(m):
    print(m, flush=True)


def stil_degerleri(api, lid):
    """bir_ilan / bag_kur degerler: envanterden Style (513) -> {ad: (513, value_id)}; Format (514) disarida."""
    inv = api.get(f"/listings/{lid}/inventory") or {}
    return stil_inv(inv)


def stil_inv(inv):
    out = {}
    for pr in inv.get("products") or []:
        for pv in pr.get("property_values") or []:
            if pv.get("property_id") != STIL_PID:
                continue
            for vid, val in zip(pv.get("value_ids") or [], pv.get("values") or []):
                if val in STILLER:
                    out.setdefault(val, (STIL_PID, vid))
    return out


def canli_durum(api, shop, lid):
    L = api.get(f"/listings/{lid}") or {}
    g = G.galeri(api, lid)
    vi = G.var_img(api, shop, lid)
    inv = api.get(f"/listings/{lid}/inventory") or {}
    return dict(state=L.get("state"), galeri=g, baglar=vi, rv=stil_inv(inv))


def kayit_kimlik(dv, il):
    """rank 1 icin kayitli kimlikler: DEVAM yuklenen + ILERLEME son_ids[0]"""
    k = {v for v in ((dv or {}).get("yuklenen") or {}).values() if v}
    s = (il or {}).get("son_ids") or []
    if s:
        k.add(s[0])
    return k


def hedef_galeri(c, man):
    """canli galeri hedefle ayni mi (yukleme sonrasi): 10, rank 1..10, alt metinler hedef sirasinda, 5 Style bagi sira 6..10'a"""
    g = c["galeri"]
    if len(g) != N or [x.get("rank") for x in g] != list(range(1, N + 1)):
        return False
    alt = [Y.alt_norm(h["alt"]) for h in sorted(man["hedef"], key=lambda h: h["sira"])]
    if [Y.alt_norm(x.get("alt_text")) for x in g] != alt:
        return False
    rk = {x.get("listing_image_id"): x.get("rank") for x in g}
    b = {x.get("value"): rk.get(x.get("image_id")) for x in c["baglar"]}
    return len(c["baglar"]) == 5 and b == STIL_SIRA


def zaten(c, man, kayit):
    """-> (zaten mi, BLOK nedeni ya da None). Yeni alt metinli kapak + kayit + hedef galeri = ZATEN (plan v3 adim 7)."""
    g = c["galeri"]
    if not g or Y.alt_norm(g[0].get("alt_text")) != Y.alt_norm(man["hedef"][0]["alt"]):
        return False, None
    if g[0].get("listing_image_id") not in kayit:
        return False, "rank 1 yeni alt metinli ama kimligi kayitta (DEVAM / ILERLEME) yok; elle bakilmali"
    if not hedef_galeri(c, man):
        return False, "rank 1 kayitli yeni kapak ama galeri hedefle ayni degil; elle bakilmali"
    return True, None


def kapilar(c, man):
    neden = []
    if c["state"] != "active":
        neden.append(f"state {c['state']} (active degil)")
    g = c["galeri"]; ids = [x.get("listing_image_id") for x in g]
    if len(g) != N_ESKI:
        neden.append(f"canli galeri {len(g)} gorsel ({N_ESKI} beklenir)")
    b = c["baglar"]; adlar = [x.get("value") for x in b]
    if len(b) != 5 or sorted(map(str, adlar)) != sorted(STILLER):
        neden.append(f"canli Style bagi {len(b)} kayit / adlar {sorted(set(map(str, adlar)))} (5 stil beklenir)")
    if len(set(adlar)) != len(adlar):
        neden.append("bir stil birden fazla gorselde (variation-images tekrar)")
    if any(x.get("property_id") != STIL_PID for x in b):
        neden.append("bag property 513 (Style) degil")
    if any(x.get("image_id") not in ids for x in b):
        neden.append("bagli gorsel canli galeride yok")
    if g and g[0].get("listing_image_id") in {x.get("image_id") for x in b}:
        neden.append("kapak (rank 1) bagli (bagsiz beklenir)")
    bot = next((x.get("image_id") for x in b if x.get("value") == "Botanical"), None)
    if bot != man.get("botanical_id"):
        neden.append(f"Botanical bagli gorsel {bot} KAPAK_KAYNAK kaynak_image_id {man.get('botanical_id')} degil")
    if sorted(ids) != sorted(man["yedek_ids"]):
        neden.append(f"canli kimlik kumesi yedekten farkli (+{len(set(ids) - set(man['yedek_ids']))} "
                     f"-{len(set(man['yedek_ids']) - set(ids))}); silinecek gorselin yedegi olmayabilir")
    canli_bag = {x.get("value"): x.get("image_id") for x in b}
    if canli_bag != {k: v["image_id"] for k, v in man["yedek_baglar"].items()}:
        neden.append("canli Style baglari yedekteki baglardan farkli")
    for ad in STILLER:
        bag_vid = next((x.get("value_id") for x in b if x.get("value") == ad), None)
        if ad not in c["rv"] or c["rv"][ad][1] != bag_vid:
            neden.append(f"envanter Style degeri ({ad}) bag value_id ile ayni degil")
    return neden


def dosya_kapisi(hazir, lid, man, eski=None):
    """eski: yd_liste_uret.eski_kapak_oku tablosu (None = depodaki data/pod/yd_kapak_eski.csv). ESKI kapakli ilan BLOK (Serdar 30 Eki)."""
    neden = []
    if sorted(h["sira"] for h in man["hedef"]) != list(range(1, N + 1)):
        return [f"manifest hedef siralari 1..{N} degil"]
    k1 = next((h for h in man["hedef"] if h["sira"] == 1), {})
    neden += LU.eski_kapak_neden(man.get("cift"), k1.get("sha256"), LU.eski_kapak_oku() if eski is None else eski)
    for h in man["hedef"]:
        p = hazir / lid / "hedef" / h["ad"]
        if not p.exists():
            neden.append(f"hedef dosya {h['ad']} yok"); continue
        try:
            with Image.open(p) as im:
                f, bt = im.format, im.size
        except Exception:  # noqa: BLE001
            f, bt = None, None
        bek = KART_BOYUT[h["sira"]]
        if p.read_bytes()[:3] != b"\xff\xd8\xff" or f != "JPEG" or bt != bek:
            neden.append(f"{h['ad']} ({h['kaynak']}) JPEG {bek[0]}x{bek[1]} degil ({f} {bt})")
        s = Y.sha256(p)
        if not h.get("sha256") or s != h["sha256"] or s != h.get("tasima_sha256"):
            neden.append(f"{h['ad']} ({h['kaynak']}) sha256 manifest / tasima MANIFEST (esleme tablosu) ile ayni degil")
    return neden


def plan_kur(hazir, lid, man):
    liste = hazir / lid / f"LISTE_{lid}.csv"
    hedef, cikar = Y.liste_oku(liste, N)
    yukle = [r for r in hedef if r["islem"] == "DEGISTIR"]
    if len(yukle) != N or sorted(cikar) != sorted(man["yedek_ids"]) or len(cikar) != N_ESKI:
        raise Y.Dur(f"LISTE {len(yukle)} DEGISTIR / {len(cikar)} CIKAR ({N} / {N_ESKI} beklenir; CIKAR = yedek kimlikleri)")
    rv = {ad: (STIL_PID, v["value_id"]) for ad, v in man["yedek_baglar"].items()}
    hbag = Y.renk_sira(man, hedef, rv)
    if hbag != STIL_SIRA:
        raise Y.Dur(f"manifest Style bag siralari {hbag} (beklenen {STIL_SIRA})")
    bagli0 = {v["image_id"] for v in man["yedek_baglar"].values()}
    kapak = next(r for r in yukle if int(r["hedef_sira"]) == 1)
    adim, mx = Y.adim_plani(N_ESKI, cikar, bagli0, yukle, set(hbag.values()), kapak_degisir=kapak, hedef_n=N)
    return adim, mx, Y.sha256(liste)


def plan_girdisi(lid, man, c, adim, mx, liste_sha):
    return dict(ilan=lid, cift=man["cift"], liste_sha=liste_sha,
                canli_galeri=[[x.get("rank"), x.get("listing_image_id")] for x in c["galeri"]],
                canli_baglar=sorted([x.get("value"), x.get("value_id"), x.get("image_id")] for x in c["baglar"]),
                hedef=[[h["sira"], h["ad"], h["sha256"], h["alt"]] for h in sorted(man["hedef"], key=lambda h: h["sira"])],
                adimlar=[list(a) for a in adim], en_fazla=mx,
                en_az=KAPI_OKUMA + Y.istek_en_az(adim, n=N), en_kotu=KAPI_OKUMA + Y.istek_en_kotu(adim, n=N))


def plan_sha(girdiler):
    return hashlib.sha256(V.jdump(girdiler).encode()).hexdigest()


def plan_yukle(yol, damga):
    p = json.loads(Path(yol).read_text(encoding="utf-8"))
    if not re.fullmatch(r"\d+_[0-9a-f]{12}", damga or ""):
        raise SystemExit("DUR: plan_damga bicimi <kuru_kosu>_<sha256 ilk 12>")
    if p.get("plan_damga") != damga or plan_sha(p.get("girdiler") or {})[:12] != damga.split("_", 1)[1] or p.get("urun") != "yd":
        raise SystemExit("DUR: PLAN_YD.json plan_damga / sha256 / urun ile ayni degil; yazma yok")
    return p


def devam_basla(adim, n):
    """durum_uzlas(ara_tekrar=True) son TAMAMLANAN sil / yukle adimindan sonra baslar (aradaki kapak / bag tekrarlanir): kota tahmini
    o adimdan (inceleme 27 Eki: kayitli adim'dan tahmin eksik kaliyordu)."""
    return max([i + 1 for i in range(min(n, len(adim))) if adim[i][0] in ("sil", "yukle")], default=0)


def ilerleme_pass(ilerleme, lid, cift, a, son_ids):
    ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=cift, set=N, hedef=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                   son_ids=son_ids)


def calistir(api, shop, a):
    hazir, out = Path(a.hazir), Path(a.out)
    ilan_out = out / "ilanlar"; ilan_out.mkdir(parents=True, exist_ok=True)
    oz = json.loads((hazir / "LISTE_OZET.json").read_text(encoding="utf-8"))
    if oz.get("urun") != "yd" or oz.get("n_hedef") != N:
        raise SystemExit(f"DUR: LISTE_OZET yd_liste_uret.py (urun yd, {N}) ciktisi degil")
    devam = V.oku_json(a.devam, {"ilanlar": {}}); ilerleme = V.oku_json(a.ilerleme, {"ilanlar": {}})
    yazim = not a.kuru
    plan = plan_yukle(a.plan, a.plan_damga) if yazim else None
    t0 = time.time()
    satir, girdiler, dur = [], {}, None
    for lid, o in oz["ilanlar"].items():
        s = dict(ilan=lid, cift=o["cift"], durum="", neden=[], en_az=None, en_kotu=None, istek=None)
        satir.append(s)
        if dur:
            s.update(durum="KALAN", neden=[dur]); continue
        dv = (devam.get("ilanlar") or {}).get(lid)
        bitmemis = bool(dv) and dv.get("son_ids") is not None and dv.get("adim", 0) < len(dv.get("plan") or [])
        s["yarim"] = bitmemis or (dv or {}).get("durum") in ("FAIL", "DUR")   # yarim / son okumasi tutmamis ilanin PASS disi
        # her sonucu cikis 1 (inceleme 27 Eki: BLOK ile yesil bitmesin)
        mp = hazir / lid / "manifest.json"
        if not bitmemis and o["durum"] != "HAZIR" and not mp.exists():
            s.update(durum="BLOK", neden=list(o["neden"])); continue
        if yazim and a.azami_dk and (time.time() - t0) / 60 > a.azami_dk:
            dur = f"zaman butcesi {a.azami_dk} dk doldu; ilan baslamadi"; s.update(durum="KALAN", neden=[dur]); continue
        c0 = api.calls; basladi = False
        uretim = a.plan_damga
        try:
            man = json.loads(mp.read_text(encoding="utf-8"))   # yoksa (yarim ilanda HAM eksik) DUR; kosu durumu sonlandir'da yazilir
            api.kota_kapisi(f"ilan {lid}")
            if bitmemis:                                                    # 1) DEVAM (liste kapisi BLOK'u uygulanmaz)
                adim = [tuple(x) for x in dv["plan"]]
                b = devam_basla(adim, dv.get("adim", 0))
                s["en_kotu"] = Y.istek_en_kotu(adim, b, ilk=False, n=N)
                s["en_az"] = Y.istek_en_az(adim, b, ilk=False, n=N)
                uretim = str(dv.get("uretim_kosu") or "")
                if not re.fullmatch(r"\d+_[0-9a-f]{12}", uretim):
                    raise Y.Dur(f"DEVAM kaydi plan_damga'si gecersiz ({uretim[:30]}); elle bakilmali")
                if not yazim:
                    s.update(durum="DEVAM", neden=[f"DEVAM kaydi adim {dv.get('adim', 0)}/{len(adim)}, plan {uretim}"
                                                   + (" (hata kaydi: kurtar gerekir)" if dv.get("hata") else "")])
                    continue
                if uretim != a.plan_damga:   # kayitli plan + LISTE sha256 + ids0 bir_ilan'da kilitli; yeni kuru damgasi yarim ilani durdurmaz
                    log(f"{lid} DEVAM: kayitli plan {uretim} ile surer (bu kosu {a.plan_damga})")
            else:
                c = canli_durum(api, shop, lid)
                il = (ilerleme.get("ilanlar") or {}).get(lid)
                z, zneden = zaten(c, man, kayit_kimlik(dv, il))           # 2) ZATEN (liste kapisindan ONCE)
                if z:
                    s.update(durum="ZATEN", istek=api.calls - c0)
                    if yazim and (il or {}).get("durum") != "PASS" and (dv or {}).get("durum") != "FAIL":
                        ilerleme_pass(ilerleme, lid, o["cift"], a, [x.get("listing_image_id") for x in c["galeri"]])
                    continue
                if o["durum"] != "HAZIR":                                   # 3) BLOK: liste kapisi
                    s.update(durum="BLOK", neden=list(o["neden"]), istek=api.calls - c0); continue
                neden = ([zneden] if zneden else []) + kapilar(c, man) + dosya_kapisi(hazir, lid, man)   # 3) BLOK: canli
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
            gerek = s["en_kotu"] - (KAPI_OKUMA if not bitmemis else 0) + KOTA_SINIRI
            if api.remaining is not None and int(api.remaining) < gerek:
                dur = f"kota: kalan {api.remaining} < en kotu {gerek - KOTA_SINIRI} + {KOTA_SINIRI}; ilan baslamadi"
                s.update(durum="KALAN", neden=[dur]); continue
            dvp = ilan_out / f"DEVAM_{lid}.json"
            if bitmemis:
                dvp.write_text(json.dumps(dv, indent=1), encoding="utf-8")
            elif dvp.exists():
                dvp.unlink()
            basladi = True
            if a.devam_hedef_kok:
                os.environ["DEVAM_HEDEF"] = f"{a.devam_hedef_kok}/DEVAM_{lid}.json"
            try:
                R = Y.bir_ilan(api, shop, lid, hazir / lid / f"LISTE_{lid}.csv", hazir / lid / "hedef", hazir / lid / "manifest.json",
                               ilan_out, kuru=False, kurtar=a.kurtar and bitmemis and bool(dv.get("hata")), uretim_kosu=uretim,
                               hedef_n=N, cdn=False, ara_tekrar=True, degerler=stil_degerleri)
            finally:
                os.environ.pop("DEVAM_HEDEF", None)
                if dvp.exists():
                    d = json.loads(dvp.read_text(encoding="utf-8"))
                    bitti = bool(d.get("plan")) and d.get("adim") == len(d["plan"])
                    devam.setdefault("ilanlar", {})[lid] = dict(d, cift=o["cift"], durum="DUR" if not bitti else "BITTI")
            s.update(durum=R["sonuc"], neden=R.get("sorun") or [], istek=api.calls - c0)
            if lid in (devam.get("ilanlar") or {}):
                devam["ilanlar"][lid]["durum"] = R["sonuc"]
            if R["sonuc"] == "PASS":
                ilerleme_pass(ilerleme, lid, o["cift"], a, R.get("son_ids"))
            else:
                dur = f"ilan {lid} {R['sonuc']}; kosu durdu"
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani, Etsy / ag hatasi: kosu durur
            m = str(getattr(e, "code", None) or e)[:300]
            if not basladi and m.startswith("DUR: kota"):
                dur = m; s.update(durum="KALAN", neden=[m], istek=api.calls - c0)
                log(f"{lid} {o['cift']} KALAN | {m[:140]}"); continue
            s.update(durum="DUR", neden=[m], istek=api.calls - c0)
            dur = f"ilan {lid} DUR; kosu durdu"
            if yazim:
                eski = (ilerleme.get("ilanlar") or {}).get(lid) or {}
                if eski.get("durum") != "PASS":
                    ilerleme.setdefault("ilanlar", {})[lid] = dict(eski, cift=o["cift"], set=eski.get("set") or "-", hedef=N, durum="DUR",
                                                                   kosu=a.kosu, plan_damga=a.plan_damga)
        log(f"{lid} {o['cift']} {s['durum']}" + (f" | en az {s['en_az']} en kotu {s['en_kotu']}" if s["en_kotu"] else "")
            + (f" | {s['neden'][0][:140]}" if s["neden"] else "") + f" | kota {api.remaining}")
    return satir, girdiler, devam, ilerleme


def bag_onar(api, shop, a):
    """DEVAM kaydi olan ilanlarda yalniz Style baglari (eski78 bag_kur, hedef_n=10, degerler Style). Kayitsiz ilan ATLA."""
    hazir, out = Path(a.hazir), Path(a.out) / "ilanlar"; out.mkdir(parents=True, exist_ok=True)
    oz = json.loads((hazir / "LISTE_OZET.json").read_text(encoding="utf-8"))
    devam = V.oku_json(a.devam, {"ilanlar": {}}); ilerleme = V.oku_json(a.ilerleme, {"ilanlar": {}})
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
            R = Y.bag_kur(api, shop, lid, hazir / lid / f"LISTE_{lid}.csv", hazir / lid / "manifest.json", dvp, out, yaz=True, hedef_n=N,
                          degerler=stil_degerleri)
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001
            R = dict(sonuc="DUR", sorun=[str(getattr(e, "code", None) or e)[:300]])
        s.update(durum=R["sonuc"], neden=R.get("sorun") or [], istek=api.calls - c0)
        if R["sonuc"] == "PASS":
            d = dict(dv, adim=len(dv["plan"]), bekleyen=None, durum="PASS")
            if d.get("hata"):
                d.setdefault("hata_gecmis", []).append(d.pop("hata"))
            devam["ilanlar"][lid] = d
            ilerleme_pass(ilerleme, lid, o["cift"], a, [x["listing_image_id"] for x in R.get("galeri") or []])
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
    R = dict(urun="yd", mod="kuru" if a.kuru else ("bag" if a.bag_onar else "yazim"), kosu=a.kosu, sayilar=say, blok_nedenleri=nedenler,
             en_kotu_ilan=max(ek) if ek else None, en_az_ilan=min(ea) if ea else None, en_kotu_toplam=sum(ek), en_az_toplam=sum(ea),
             istek=api.calls, kalan_kota=api.remaining, ilanlar=satir)
    if a.kuru:
        sh = plan_sha(girdiler); R["plan_damga"] = f"{a.kosu}_{sh[:12]}"
        (out / "PLAN_YD.json").write_text(json.dumps(dict(urun="yd", plan_damga=R["plan_damga"], kosu=a.kosu, girdiler=girdiler),
                                                     indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "RAPOR.json").write_text(json.dumps(R, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(out / "RAPOR.md", "w", encoding="utf-8") as f:
        f.write(f"# YD kapak {R['mod']} ({a.kosu})\n\n" + " | ".join(f"{k} {v}" for k, v in sorted(say.items()))
                + f"\n\nIstek (kod okumasi): ilan basina en az {R['en_az_ilan']} / en kotu {R['en_kotu_ilan']}; toplam en az "
                  f"{R['en_az_toplam']} / en kotu {R['en_kotu_toplam']} | bu kosu istek {api.calls}, kalan kota {api.remaining}\n"
                + (f"plan_damga: {R.get('plan_damga')}\n" if a.kuru else "") + "\n## Nedenler\n"
                + "".join(f"- {v} ilan: {k}\n" for k, v in sorted(nedenler.items(), key=lambda x: -x[1])) + "\n## Ilanlar\n"
                + "".join(f"- {s['ilan']} {s['cift']} {s['durum']} en_az {s['en_az']} en_kotu {s['en_kotu']}"
                          + (f": {'; '.join(s['neden'])[:200]}" if s["neden"] else "") + "\n" for s in satir))
    log(f"YD_KAPAK {R['mod']}: " + " ".join(f"{k}={v}" for k, v in sorted(say.items()))
        + f" | en kotu ilan {R['en_kotu_ilan']} toplam {R['en_kotu_toplam']} | istek {api.calls} kalan kota {api.remaining}"
        + (f" | plan_damga {R['plan_damga']}" if a.kuru else ""))
    return R


def arg(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hazir", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--devam", default=""); ap.add_argument("--ilerleme", default="")
    ap.add_argument("--sonuc", default="", help="yazim: SONUC.csv (anahtar ilan) guncellenir")
    ap.add_argument("--kuru", action="store_true"); ap.add_argument("--confirm", default="")
    ap.add_argument("--plan", default=""); ap.add_argument("--plan-damga", default="")
    ap.add_argument("--kurtar", action="store_true", help="DEVAM kaydinda hata olan ilanlarda kayitli plan + canli galeriyle surdur")
    ap.add_argument("--bag-onar", action="store_true", help=f"yalniz Style baglari (--confirm {ONAY_BAG} + --plan-damga)")
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
            V.sonuc_yaz(a.sonuc, satir, a)
    kotu = [s for s in satir if s["durum"] in ("DUR", "FAIL") or (s.get("yarim") and s["durum"] not in ("PASS", "ZATEN", "DEVAM", "KALAN"))]
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main())
