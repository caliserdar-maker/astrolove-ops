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
  ESKI KAPAK KAPISI (Serdar 30 Eki, data/pod/yd_kapak_eski.csv; inceleme 30 Eki madde 3): UC YOLUN BASINDA (DEVAM / ZATEN / BLOK oncesi)
  yd_liste_uret.eski_kapak_neden uygulanir: ESKI ya da yenilenmis kayitla ayni olmayan kapak -> BLOK (yarim ilan da; cikis 1), yazma yok,
  ZATEN / ILERLEME PASS yazilmaz. DEVAM yolunda ayrica dosya_kapisi (JPEG / boyut / sha256 manifest) uygulanir.
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
import html
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
import toplu_oku as TO  # noqa: E402  (Serdar 31 Eki 1a: toplu kapi okumasi)
import eski78_gorsel_yukle as Y  # noqa: E402
import yd_liste_uret as LU  # noqa: E402  (eski kapak kurali, Serdar 30 Eki)
import galeri_v10_yukle as V  # noqa: E402  (yalniz jdump / oku_json / sonuc_yaz; poster yukleyicisi degismez)
from etsy_common import KOTA_SINIRI  # noqa: E402  (Serdar 15 ve 24 Eki: 10; degistirilmez)
import kupa_galeri78 as KG  # noqa: E402  (geri alma motoru: galeri_kur / canli_oku / galeri_sorun ortak; inceleme 31 Eki madde 1)

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
    adim, mx = Y.sirali_plan(cikar, yukle, hedef_n=N)   # Serdar 31 Eki 1a (istek azaltma madde 1): once sil, sirayla yukle, bag sonda
    return adim, mx, Y.sha256(liste)


def plan_girdisi(lid, man, c, adim, mx, liste_sha):
    return dict(ilan=lid, cift=man["cift"], liste_sha=liste_sha,
                canli_galeri=[[x.get("rank"), x.get("listing_image_id")] for x in c["galeri"]],
                canli_baglar=sorted([x.get("value"), x.get("value_id"), x.get("image_id")] for x in c["baglar"]),
                hedef=[[h["sira"], h["ad"], h["sha256"], h["alt"]] for h in sorted(man["hedef"], key=lambda h: h["sira"])],
                adimlar=[list(a) for a in adim], en_fazla=mx,
                en_az=KAPI_OKUMA + istek(adim, "en_az"), en_kotu=KAPI_OKUMA + istek(adim, "en_kotu") + istek_geri_al())


def istek_geri_al():
    """YD geri alma EN KOTU (inceleme 31 Eki madde 1; kupa istek_tahmini geri_alma ile ayni kalemler, O = G.OKUMA_TEKRAR):
    canli okuma (kupa_galeri78.canli_oku tekil) + N_ESKI yeniden yukleme x ((2 + 1) + (2 + O)) + N yeni gorsel silme x 4 + sira (O +
    2 x (N_ESKI x 4 + O)) + bag (4 + O) + son okuma (galeri O + var_img O)."""
    O = G.OKUMA_TEKRAR
    return KG.KAPI_OKUMA + N_ESKI * ((2 + 1) + (2 + O)) + N * 4 + (O + 2 * (N_ESKI * 4 + O)) + (4 + O) + 2 * O


def istek(adim, tur, basla=0, ilk=True):
    """plan turune gore istek sayaci (sira_bag adimi = SIRALI plan; eski DEVAM kaydi adim_plani ile kalmis olabilir)"""
    sirali = any(a[0] == "sira_bag" for a in adim)
    f = {("en_az", True): Y.istek_sirali_en_az, ("en_kotu", True): Y.istek_sirali_en_kotu,
         ("en_az", False): Y.istek_en_az, ("en_kotu", False): Y.istek_en_kotu}[(tur, sirali)]
    return f(adim, basla, ilk=ilk, n=N)


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


def ilerleme_pass(ilerleme, lid, cift, a, son_ids, tg_tamam=False):
    ilerleme.setdefault("ilanlar", {})[lid] = dict(cift=cift, set=N, hedef=N, durum="PASS", kosu=a.kosu, plan_damga=a.plan_damga,
                                                   son_ids=son_ids, **({"tek_gecis_tamam": True} if tg_tamam else {}))


def yedek_yol(a, lid, cift, x):
    """Geri alma icin adim 5 yedeginden eski gorsel (r<rank>_<id>.jpg): yerelde yoksa Drive'dan (--yedek-uzak, rclone); JPEG imzasi +
    yedek lsjson boyutu (--yedek-liste) kapisi (YD yedeginde sha256 yok)."""
    rel = f"{lid}_{cift}/r{x['rank']}_{x['listing_image_id']}.jpg"
    p = Path(a.yedek_dir) / rel
    if not p.exists() and a.yedek_uzak:
        import subprocess
        p.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([os.environ.get("RCLONE", "rclone"), "copyto", f"{a.yedek_uzak}/{rel}", str(p), "-q"], capture_output=True, timeout=300)
    bek = (V.oku_json(a.yedek_liste, []) if a.yedek_liste else None)
    boy = {x["Path"]: int(x.get("Size") or 0) for x in bek} if isinstance(bek, list) else {}
    if not p.exists() or p.read_bytes()[:3] != b"\xff\xd8\xff" or (boy and boy.get(rel) != p.stat().st_size):
        raise Y.Dur(f"geri alma: yedek dosyasi {rel} yok / JPEG degil / boyut yedek listesiyle ayni degil")
    return p


def geri_al(api, shop, lid, cift, man, a, out):
    """YD GERI ALMA (inceleme 31 Eki madde 1, kritik: sirali planda eski 13 once silinir; hata aninda ilan tek gorselle kalabiliyordu).
    Eski hal HAM'dan (sha256 = manifest ham_sha): 13 gorsel ayni sira + alt metin, Style baglari eski siralara. Yerinde kalan eski gorsel
    korunur, silinmis olan adim 5 yedeginden yeniden yuklenir, yeni yuklenenler silinir (kupa_galeri78.galeri_kur, esnek; ayni motor).
    Tekrar kosulabilir: onceki geri almada yeniden yuklenen eski gorsel (GERI_<ilan>.json geri_yuklenen) yerinde kalir.
    -> sorun listesi (bos = geri alindi)"""
    try:
        hp = Path(a.ham_dir or "") / f"{lid}.json"
        if not a.ham_dir or not hp.exists() or LU.sha(hp) != man.get("ham_sha"):
            return [f"geri alma: HAM/{lid}.json yok ya da sha256 manifest ile ayni degil; elle bakilmali"]
        h = json.loads(hp.read_text(encoding="utf-8"))
        eski = sorted(h.get("images") or [], key=lambda x: x.get("rank") or 0)
        if [x.get("listing_image_id") for x in eski] != man.get("yedek_galeri"):
            return ["geri alma: HAM galerisi manifest yedek_galeri ile ayni degil; elle bakilmali"]
        if hasattr(api, "kapat"):
            api.kapat()                                   # tohumlu istemci: geri alma okumalari canli
        K = KG.Kayit(Path(out) / "geri", lid, drive=a.devam_hedef_kok and f"{a.devam_hedef_kok}/GERI_{lid}.json" or "")
        K.p.parent.mkdir(parents=True, exist_ok=True)
        if K.p.exists():
            K.d = json.loads(K.p.read_text(encoding="utf-8"))
        else:
            K.d = dict(cift=cift, yuklenen={}, silinen=[], geri_yuklenen={})
        c = KG.canli_oku(api, shop, lid)
        canli = {x.get("listing_image_id") for x in c["galeri"]}
        eski_ids = {x["listing_image_id"] for x in eski}
        geri_yk = set((K.d.get("geri_yuklenen") or {}).values())
        hedef = {}
        for x in eski:
            s_, i_ = x["rank"], x["listing_image_id"]
            hd = dict(alt=x.get("alt_text") or "", ad=f"YEDEK_r{s_}_{i_}.jpg")
            if i_ in canli:
                hd["id"] = i_
            elif (K.d.get("geri_yuklenen") or {}).get(hd["ad"]) not in canli:
                hd["yol"] = yedek_yol(a, lid, cift, x)
            hedef[s_] = hd
        sira = {x["listing_image_id"]: x["rank"] for x in eski}
        vi = h.get("variation_images") or []
        bag_sira = {b["value"]: sira[b["image_id"]] for b in vi if b.get("image_id") in sira}
        stil_vid = {b["value"]: c["stil"].get(b["value"]) for b in vi}      # CANLI envanter ad -> deger kimligi (madde 7)
        if len(bag_sira) != len(vi) or not set(bag_sira) <= set(c["stil"]):
            return ["geri alma: HAM Style baglari canli envanterle eslenemedi; elle bakilmali"]
        sil = sorted(canli - eski_ids - geri_yk)
        son = KG.galeri_kur(api, shop, lid, c, hedef, sil, bag_sira, stil_vid, K, "geri_yuklenen", esnek=True)
        bek = [son[k] for k in sorted(son)]
        g = G.kararli(lambda: G.galeri(api, lid), lambda g: [x.get("listing_image_id") for x in g] == bek)
        sorun = [f"geri alma galeri: {x}" for x in KG.galeri_sorun(g, son, {k: v["alt"] for k, v in hedef.items()})]
        hb = {stil_vid[ad]: son[k] for ad, k in bag_sira.items()}
        vm = G.kararli(lambda: G.var_img(api, shop, lid), lambda vm: {x.get("value_id"): x.get("image_id") for x in vm} == hb)
        if {x.get("value_id"): x.get("image_id") for x in vm} != hb:
            sorun.append("geri alma: Style baglari eski siralara donmedi")
        K.d.update(durum="GERI_ALINDI" if not sorun else "BASARISIZ", son_sira=bek); K.yaz()
        return sorun
    except (Y.Dur, KG.Geri, SystemExit, Exception) as e:   # noqa: BLE001
        return [f"geri alma hatasi: {str(getattr(e, 'code', None) or e)[:200]}"]


# ---------------------------------------------------------------- TEK GECIS (F-B madde 2, Serdar 31 Eki 1a)
# Ilan basina tek okuma + sirayla: 1) envanter PUT (yd_yapi_yaz; 14 boy x 2 format x 5 stil, Style bagi YAZILMAZ) 2) galeri (sirali,
# Style bagi EN SON tek kez) 3) baslik + aciklama TEK PATCH (state active okunur; AI beyan kapisi etsy_common._call) 4) video EN SON
# (yeni active olmadan eski silinmez: video hatasi ilani bozmaz -> DUR, geri alma yok). 1-3 hatasinda geri alma: galeri (geri_al) +
# envanter (yd_yapi_yaz.geri_al_gerekirse, YEDEK_<ilan>.json ham envanter) + metin (eski baslik / aciklama PATCH). Kargo profili ilan
# basina YAZILMAZ: kosu basinda profil duzeyinde bir kez (yd_yapi_yaz profil modu). Girdiler kuru planin parcasidir (sha256 plan girdisinde).
def tg_girdi(a, lid):
    """-> dict(yapi, metin, video) ya da None (tek gecis kapali). Sha'lar plan girdisine girer (canli == plan kapisi)."""
    if not a.tek_gecis:
        return None
    import yd_yapi_yaz as YY
    yp = Path(a.yapi_plan) / f"KURU_{lid}.json"
    if not yp.exists():
        raise Y.Dur(f"tek gecis: yapi plani KURU_{lid}.json yok")
    k = YY.plan_yukle(a.yapi_plan, [lid], [])[0][lid]
    m = (V.oku_json(a.metin_json, {}) if a.metin_json else {}).get(lid)
    if m is not None:
        mh = tg_metin_kapisi(m)
        if mh:
            raise Y.Dur("tek gecis metin kapisi: " + "; ".join(mh))
    vm = (V.oku_json(Path(a.video_dir) / "VIDEO_MANIFEST.json", {}) if a.video_dir else {}).get(lid)
    vy = None
    if vm:
        vy = Path(a.video_dir) / vm["dosya"]
        if not vy.exists() or Y.sha256(vy) != vm.get("sha256"):
            raise Y.Dur(f"tek gecis: video {vm.get('dosya')} yok ya da sha256 manifestten farkli")
    return dict(k=k, yapi_sha=Y.sha256(yp), metin=m, metin_sha=hashlib.sha256(V.jdump(m).encode()).hexdigest() if m else None,
                video=vy, video_sha=(vm or {}).get("sha256"))


def tg_metin_kapisi(m):
    """KURUDA metin kapisi (inceleme 31 Eki madde 5): bos degil, baslik <= 140, AI beyani (EN), CLAUDE.md yasak ifade / uzun-orta tire yok
    (kupa_galeri78.yasak_bul ile ayni liste). -> sorun listesi"""
    import etsy_common as EC
    t, d = (m or {}).get("title") or "", (m or {}).get("description") or ""
    h = []
    if not t.strip() or not d.strip():
        h.append("title / description bos")
    if len(t) > 140:
        h.append(f"baslik {len(t)} karakter (> 140)")
    if d and not EC.beyan_var(d, "en"):
        h.append("aciklamada AI beyani yok")
    y = KG.yasak_bul(t + "\n" + d)
    if y or any(c in t + d for c in "\u2014\u2013"):
        h.append(f"yasak ifade / tire {y[:5]}")
    return h


def tg_istek():
    """tek gecis ek EN KOTU: envanter (yd_yapi_yaz.ILAN_UST: okuma + PUT + geri okuma + kendi geri almasi) + metin (ilan GET + PATCH 4 +
    geri almada PATCH 4) + video (kupa_galeri78 video_kur en kotu)"""
    import yd_yapi_yaz as YY
    O = G.OKUMA_TEKRAR
    env = YY.OKUMA + 4 + YY.TEKRAR + (1 + 4 + YY.TEKRAR)      # okuma + PUT (3 gonderim + 401) + geri okuma; geri alma GET + PUT + geri okuma
    return env + (1 + 4 + 1 + 4) + (1 + (2 + O) + KG.VIDEO_DENEME + 4 + O)   # metin (GET + PATCH; geri GET + PATCH) + video


class TgK:
    """video_kur icin hafif kayit (kupa Kayit arayuzu: d + yaz)"""
    def __init__(self, p):
        self.p, self.d = Path(p), {}

    def yaz(self, ids=None, uzak=True):
        self.p.write_text(json.dumps(self.d, indent=1, ensure_ascii=False), encoding="utf-8")


def tg_envanter(api, shop, lid, tg, out, R_):
    import yd_yapi_yaz as YY
    k = tg["k"]
    if k.get("durum") == "ZATEN":
        return None
    L, inv, vi = YY.oku(api, shop, lid)
    s = YY.kapi(k, L, inv, vi)
    R_.update(tg_envanter=s)
    if s["envanter"] != "yaz":
        return None
    R_["adet"] = s["adet"]                       # PUT uygulanip hata donse de geri alma bilsin (inceleme madde 1)
    (Path(out) / f"YEDEK_YAPI_{lid}.json").write_text(json.dumps({"listing_id": lid, "listing": L, "inventory": inv, "variation_images": vi},
                                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    R_.setdefault("yazilan", [])
    YY.envanter_yaz(api, lid, YY.adet_uygula(k["envanter_yuk"], s["adet"]), k["envanter_yuk"], k["boy_ozellik"]["property_id"], R_, "envanter")
    return s["adet"]


def tg_metin(api, shop, lid, m, R_):
    if not m:
        return None
    L = api.get(f"/listings/{lid}") or {}
    if L.get("state") != "active":
        raise Y.Dur(f"tek gecis metin: state {L.get('state')} (active degil); updateListing cagrilmadi")
    eski = dict(title=L.get("title"), description=L.get("description"))
    if L.get("title") == m["title"] and html.unescape(L.get("description") or "") == m["description"]:
        return None
    R_["tg_metin_eski"] = eski
    api.patch(f"/shops/{shop}/listings/{lid}", {"title": m["title"], "description": m["description"]})   # TEK PATCH
    return eski


def tg_geri(api, shop, lid, tg, adet, out, R_, metin_eski):
    """tek gecis geri alma: metin + envanter (Style bagi YAZILMAZ: eski bag eski gorsel kimliklerine; galeri geri_al baglari canli deger
    kimlikleriyle EN SON kurar; inceleme 31 Eki madde 3). PUT / PATCH uygulanip hata donmus olsa da (kayit istekten ONCE) calisir
    (madde 1-2). -> sorun listesi (bos degilse ilan GERI_ALINDI sayilmaz)."""
    import yd_yapi_yaz as YY
    sorun = []
    me = R_.get("tg_metin_eski") or metin_eski
    if me:
        try:
            L = api.get(f"/listings/{lid}") or {}
            if L.get("title") != me["title"] or html.unescape(L.get("description") or "") != html.unescape(me["description"] or ""):
                api.patch(f"/shops/{shop}/listings/{lid}", {"title": html.unescape(me["title"] or ""),
                                                             "description": html.unescape(me["description"] or "")})
        except (Exception, SystemExit) as e:   # noqa: BLE001
            sorun.append(f"metin geri alma: {str(getattr(e, 'code', None) or e)[:150]}")
    if "envanter" in (R_.get("yazilan") or []):
        q = R_.get("adet") if R_.get("adet") is not None else adet
        try:
            k = tg["k"]; ham = k["envanter_ham_yedek"]
            inv_c = api.get(f"/listings/{lid}/inventory") or {}
            if not (YY.imza(inv_c) == YY.imza(ham) and YY.menu_ham(inv_c) == YY.menu_ham(ham)):
                YY.envanter_yaz(api, lid, YY.adet_uygula(YY.geri_govde(ham), q), ham, None, R_, "geri_envanter")
        except (Exception, SystemExit) as e:   # noqa: BLE001
            sorun.append(f"envanter geri alma: {str(getattr(e, 'code', None) or e)[:150]} (YEDEK_YAPI_{lid}.json ile geri-al)")
    return sorun


def calistir(api, shop, a):
    hazir, out = Path(a.hazir), Path(a.out)
    ilan_out = out / "ilanlar"; ilan_out.mkdir(parents=True, exist_ok=True)
    oz = json.loads((hazir / "LISTE_OZET.json").read_text(encoding="utf-8"))
    if oz.get("urun") != "yd" or oz.get("n_hedef") != N:
        raise SystemExit(f"DUR: LISTE_OZET yd_liste_uret.py (urun yd, {N}) ciktisi degil")
    devam = V.oku_json(a.devam, {"ilanlar": {}}); ilerleme = V.oku_json(a.ilerleme, {"ilanlar": {}})
    yazim = not a.kuru
    plan = plan_yukle(a.plan, a.plan_damga) if yazim else None
    eski_tablo = LU.eski_kapak_oku()       # Serdar 30 Eki: ESKI kapak listesi (kosu basina bir kez)
    t0 = time.time()
    satir, girdiler, dur = [], {}, None
    # TOPLU kapi okumasi (Serdar 31 Eki 1a, madde 4): DEVAM disi ilanlar 100'luk parcada 2 istekte; ilan basina tohumlu istemci (ilan,
    # galeri, video, envanter toplu yanittan; variation-images ilk okumada), ilk yazimda kapanir. DEVAM ilanlari canli okunur.
    # KURU: kosu basi toplu okuma. YAZIM: ilan basina yazmadan HEMEN once taze toplu okuma (inceleme 31 Eki madde 4: kosu basi anlik
    # goruntu yazim kararinda kullanilmaz; kupa ile ayni). Kota once okunur (madde 11: ilk toplu GET kor gidiyordu). Toplu hata -> tekil.
    toplu_ids = [lid for lid, o in oz["ilanlar"].items() if not ((devam.get("ilanlar") or {}).get(lid) or {}).get("plan")]
    onb = {}
    if oz["ilanlar"]:
        KG.kota_oku(api, shop)
    if toplu_ids and not yazim and int(api.remaining) - 2 * (-(-len(toplu_ids) // TO.TOPLU_N)) >= KOTA_SINIRI:
        c_t = api.calls
        try:
            onb = TO.toplu(api, toplu_ids)
        except Exception as e:   # noqa: BLE001  (madde 12) kota DUR'u yukari, digeri tekil okumaya duser
            if "kota" in str(getattr(e, "code", None) or e).lower():
                raise
            log(f"UYARI: toplu kapi okumasi hata ({str(e)[:120]}); tekil okuma"); onb = {}
        log(f"toplu kapi okumasi: {len(onb)}/{len(toplu_ids)} ilan, {api.calls - c_t} istek | kota {api.remaining}")
    api0 = api
    esit_kalan = 2 if not yazim else 0      # madde 5: kuruda ilk 2 ilanda toplu == tekil olcumu
    sira_ilan = list(oz["ilanlar"].items())
    if a.tek_gecis:                          # inceleme 31 Eki madde 8: pilot her zaman ilk (yd_yapi_yaz.plan_yukle sirasi), ilk FAIL kosuyu durdurur
        import yd_yapi_yaz as YY
        once = [x for x in YY.plan_yukle(a.yapi_plan, [], [])[1] if x in oz["ilanlar"]]
        sira_ilan = sorted(sira_ilan, key=lambda kv: once.index(kv[0]) if kv[0] in once else len(once))
    for lid, o in sira_ilan:
        api = TO.Tohumlu(api0, lid, onb.pop(lid, None))
        s = dict(ilan=lid, cift=o["cift"], durum="", neden=[], en_az=None, en_kotu=None, istek=None)
        satir.append(s)
        if dur:
            s.update(durum="KALAN", neden=[dur]); continue
        dv = (devam.get("ilanlar") or {}).get(lid)
        bitmemis = bool(dv) and dv.get("son_ids") is not None and dv.get("adim", 0) < len(dv.get("plan") or []) \
            and dv.get("durum") != "GERI_ALINDI"                     # geri alinmis ilan surdurulmez (yeni kuru gerekir; canli != plan)
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
            k1 = next((h for h in man.get("hedef") or [] if h.get("sira") == 1), {})
            ek = LU.eski_kapak_neden(o["cift"], k1.get("sha256"), eski_tablo)   # 0) ESKI KAPAK: DEVAM / ZATEN / BLOK'tan ONCE
            if man.get("cift") not in (None, o["cift"]):
                ek.append(f"manifest cifti {man.get('cift')} != liste {o['cift']}")
            if ek:
                s.update(durum="BLOK", neden=ek); continue
            api.kota_kapisi(f"ilan {lid}")
            if bitmemis:                                                    # 1) DEVAM (liste kapisi BLOK'u uygulanmaz)
                adim = [tuple(x) for x in dv["plan"]]
                b = devam_basla(adim, dv.get("adim", 0))
                s["en_kotu"] = istek(adim, "en_kotu", b, ilk=False) + istek_geri_al()
                s["en_az"] = istek(adim, "en_az", b, ilk=False)
                uretim = str(dv.get("uretim_kosu") or "")
                if not re.fullmatch(r"\d+_[0-9a-f]{12}", uretim):
                    raise Y.Dur(f"DEVAM kaydi plan_damga'si gecersiz ({uretim[:30]}); elle bakilmali")
                dk = dosya_kapisi(hazir, lid, man, eski_tablo)              # DEVAM: dosya kapisi (inceleme 30 Eki madde 3)
                if dk:
                    s.update(durum="BLOK", neden=dk); continue
                if not yazim:
                    s.update(durum="DEVAM", neden=[f"DEVAM kaydi adim {dv.get('adim', 0)}/{len(adim)}, plan {uretim}"
                                                   + (" (hata kaydi: kurtar gerekir)" if dv.get("hata") else "")])
                    continue
                if uretim != a.plan_damga:   # kayitli plan + LISTE sha256 + ids0 bir_ilan'da kilitli; yeni kuru damgasi yarim ilani durdurmaz
                    log(f"{lid} DEVAM: kayitli plan {uretim} ile surer (bu kosu {a.plan_damga})")
            else:
                if yazim:      # yazmadan hemen once taze toplu okuma (2 istek); yanitta yoksa tekil
                    api = TO.Tohumlu(api0, lid, TO.toplu(api0, [lid]).get(lid))
                tohum = api.tohum
                c = canli_durum(api, shop, lid)
                if esit_kalan and tohum:      # madde 5: plan toplu yanittan; son okuma tekil -> gosterim farki her ilani FAIL ederdi
                    esit_kalan -= 1
                    ct = canli_durum(api0, shop, lid)
                    fk = [k for k in ("state", "galeri", "baglar", "rv") if c[k] != ct[k]]
                    s["toplu_tekil"] = "ESIT" if not fk else f"FARK {fk}"
                    if fk:
                        s.update(durum="BLOK", neden=[f"toplu okuma tekil okumayla ayni degil: {fk}; toplu yol kullanilmaz"], istek=api.calls - c0)
                        continue
                il = (ilerleme.get("ilanlar") or {}).get(lid)
                z, zneden = zaten(c, man, kayit_kimlik(dv, il))           # 2) ZATEN (liste kapisindan ONCE)
                if z and a.tek_gecis and not (il or {}).get("tek_gecis_tamam"):   # inceleme 31 Eki madde 4: video / envanter / metin eksik
                    s.update(durum="BLOK", neden=["galeri hedefte ama tek gecis (envanter / metin / video) tamamlanmamis (onceki video hatasi ya da "
                                                  "yalniz galeri kosusu); ayri kosu ya da elle bakilmali"], istek=api.calls - c0)
                    continue
                if z:
                    s.update(durum="ZATEN", istek=api.calls - c0)
                    if yazim and (il or {}).get("durum") != "PASS" and (dv or {}).get("durum") != "FAIL":
                        ilerleme_pass(ilerleme, lid, o["cift"], a, [x.get("listing_image_id") for x in c["galeri"]])
                    continue
                if o["durum"] != "HAZIR":                                   # 3) BLOK: liste kapisi
                    s.update(durum="BLOK", neden=list(o["neden"]), istek=api.calls - c0); continue
                neden = ([zneden] if zneden else []) + kapilar(c, man) + dosya_kapisi(hazir, lid, man, eski_tablo)   # 3) BLOK: canli
                if neden:
                    s.update(durum="BLOK", neden=neden, istek=api.calls - c0); continue
                adim, mx, lsha = plan_kur(hazir, lid, man)
                if mx > G.IMG_LIMIT:
                    s.update(durum="BLOK", neden=[f"plan {mx} gorsel (> {G.IMG_LIMIT})"]); continue
                gd = plan_girdisi(lid, man, c, adim, mx, lsha)
                try:
                    tg = tg_girdi(a, lid)
                except Y.Dur as e:
                    s.update(durum="BLOK", neden=[str(e)], istek=api.calls - c0); continue
                if tg:
                    gd.update(tek_gecis=dict(yapi_sha=tg["yapi_sha"], metin_sha=tg["metin_sha"], video_sha=tg["video_sha"]),
                              en_kotu=gd["en_kotu"] + tg_istek())
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
            tg = tg_girdi(a, lid) if not bitmemis else None      # DEVAM ilaninda tek gecis yok (galeri surdurulur)
            if bitmemis and a.tek_gecis:
                s["neden"].append("DEVAM: yalniz galeri surduruldu; tek gecis (envanter / metin / video) yapilmadi -> sonraki tek gecis kosusunda BLOK")
            tgR, adet, metin_eski = {}, None, None
            try:
                if tg:
                    adet = tg_envanter(api, shop, lid, tg, ilan_out, tgR)                       # 1) envanter (bag yok)
                R = Y.bir_ilan(api, shop, lid, hazir / lid / f"LISTE_{lid}.csv", hazir / lid / "hedef", hazir / lid / "manifest.json",
                               ilan_out, kuru=False, kurtar=a.kurtar and bitmemis and bool(dv.get("hata")), uretim_kosu=uretim,
                               hedef_n=N, cdn=False, ara_tekrar=True, degerler=stil_degerleri, sirali=True)   # 2) galeri, bag sonda
                if tg and R["sonuc"] == "PASS":
                    try:
                        metin_eski = tg_metin(api, shop, lid, tg["metin"], tgR)                 # 3) baslik + aciklama tek PATCH
                    except (Exception, SystemExit) as e:   # noqa: BLE001
                        R = dict(R, sonuc="FAIL", sorun=(R.get("sorun") or []) + [f"tek gecis metin: {str(getattr(e, 'code', None) or e)[:200]}"])
                    if R["sonuc"] == "PASS" and tg["video"]:
                        try:                                                                    # 4) video EN SON (eski, yeni active olmadan silinmez)
                            vk = TgK(ilan_out / f"VIDEO_{lid}.json")
                            R["video"] = KG.video_kur(api, shop, lid, tg["video"], [], vk, "video_yeni")
                        except (Exception, SystemExit) as e:   # noqa: BLE001
                            R = dict(R, sonuc="DUR_VIDEO", sorun=(R.get("sorun") or []) + [f"tek gecis video (galeri / envanter / metin yazildi, eski video "
                                                                                            f"yerinde): {str(getattr(e, 'code', None) or e)[:200]}"])
                if tg and R["sonuc"] not in ("PASS", "DUR_VIDEO"):
                    R = dict(R, tg_geri=tg_geri(api, shop, lid, tg, adet, ilan_out, tgR, metin_eski))
            except (Exception, SystemExit):
                if tg:
                    tgR["tg_geri"] = tg_geri(api, shop, lid, tg, adet, ilan_out, tgR, metin_eski)
                raise
            finally:
                os.environ.pop("DEVAM_HEDEF", None)
                if dvp.exists():
                    d = json.loads(dvp.read_text(encoding="utf-8"))
                    bitti = bool(d.get("plan")) and d.get("adim") == len(d["plan"])
                    devam.setdefault("ilanlar", {})[lid] = dict(d, cift=o["cift"], durum="DUR" if not bitti else "BITTI")
            s.update(durum=R["sonuc"], neden=R.get("sorun") or [], istek=api.calls - c0)
            if R.get("tg_geri"):
                s["neden"] += [f"tek gecis geri alma: {x}" for x in R["tg_geri"]] or ["tek gecis envanter / metin geri alindi"]
            if R["sonuc"] == "DUR_VIDEO":
                s["durum"] = "DUR"; R = dict(R, sonuc="DUR")
            elif R["sonuc"] != "PASS":            # GERI ALMA (inceleme 31 Eki madde 1): eski 13 + baglar yedekten
                gs = geri_al(api, shop, lid, o["cift"], man, a, out) + list(R.get("tg_geri") or [])
                s.update(durum="FAIL" if not gs else "DUR", neden=s["neden"] + (["GERI ALINDI (eski 13 gorsel + Style baglari)"] if not gs else gs),
                         istek=api.calls - c0)
                R = dict(R, sonuc=s["durum"])
                if lid in (devam.get("ilanlar") or {}) and not gs:
                    devam["ilanlar"][lid].update(durum="GERI_ALINDI", geri_alma="TAMAM")
            if lid in (devam.get("ilanlar") or {}):
                devam["ilanlar"][lid]["durum"] = R["sonuc"] if devam["ilanlar"][lid].get("durum") != "GERI_ALINDI" else "GERI_ALINDI"
            if R["sonuc"] == "PASS":
                ilerleme_pass(ilerleme, lid, o["cift"], a, R.get("son_ids"), tg_tamam=bool(tg))
            else:
                dur = f"ilan {lid} {R['sonuc']}; kosu durdu"
        except (Y.Dur, SystemExit, Exception) as e:   # noqa: BLE001 kota tabani, Etsy / ag hatasi: kosu durur
            m = str(getattr(e, "code", None) or e)[:300]
            if not basladi and m.startswith("DUR: kota"):
                dur = m; s.update(durum="KALAN", neden=[m], istek=api.calls - c0)
                log(f"{lid} {o['cift']} KALAN | {m[:140]}"); continue
            s.update(durum="DUR", neden=[m], istek=api.calls - c0)
            if basladi and yazim and not m.startswith("DUR: kota"):      # yazim sirasinda hata: geri alma (kota tabaninda yok: istek yok)
                gs = geri_al(api, shop, lid, o["cift"], man, a, out) + list(locals().get("tgR", {}).get("tg_geri") or [])
                s["neden"] += ["GERI ALINDI (eski 13 gorsel + Style baglari)"] if not gs else gs
                if not gs:
                    s["durum"] = "FAIL"
                    devam.setdefault("ilanlar", {}).setdefault(lid, {}).update(durum="GERI_ALINDI", geri_alma="TAMAM", cift=o["cift"])
            dur = f"ilan {lid} {s['durum']}; kosu durdu"
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
    ap.add_argument("--ham-dir", default="", help="geri alma: HAM/<ilan>.json klasoru (sha256 = manifest ham_sha)")
    ap.add_argument("--tek-gecis", action="store_true", help="F-B madde 2: envanter + galeri + metin + video ilan basina tek geciste")
    ap.add_argument("--yapi-plan", default="", help="tek gecis: yd_yapi_kuru cikti klasoru (KURU_<ilan>.json, PLAN.csv)")
    ap.add_argument("--metin-json", default="", help="tek gecis: {ilan: {title, description}} (Serdar onayli metin; yoksa metin yazilmaz)")
    ap.add_argument("--video-dir", default="", help="tek gecis: VIDEO_MANIFEST.json {ilan: {dosya, sha256}} + mp4'ler (yoksa video yok)")
    ap.add_argument("--yedek-dir", default="_yedek", help="geri alma: adim 5 yedegi yerel klasor (yoksa --yedek-uzak'tan iner)")
    ap.add_argument("--yedek-uzak", default="", help="geri alma: TEMP/YD_KAPAK_V1_YEDEK/<damga> (rclone)")
    ap.add_argument("--yedek-liste", default="", help="geri alma: yedek lsjson (boyut kapisi)")
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
