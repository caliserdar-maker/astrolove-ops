#!/usr/bin/env python3
"""CANLI YAPI OLCUMU (O1; SALT OKUMA, Etsy'ye YAZMAZ). Plan: plan/urun-ayar docs/plan/URUN_AYAR_PLAN.md 7.1 (Serdar 8 Kas gece
"Hepsi oneriyle", Merkez Onay 3a: kodu yazmak icin onay; kosu ayri onay, ornament zinciri bittikten sonra).

mod=prob : TAM 3 istek. (1) GET /shops/{shop} (kota) (2) GET /listings/batch?includes=Inventory (her gruptan 1 ilan, en fazla 5)
           (3) GET /listings/{poster}/inventory (batch'teki poster ilani). Cikti: iki yanitin ANAHTAR YAPISI (alan yolu + tur, deger yok),
           batch yanitinda envanter donuyor mu (EVET / HAYIR), donuyorsa products semasi tek ilan envanter semasiyla ayni mi.
           Bilinen PASS: tek ilan envanterinde products[].offerings[].readiness_state_id ve products[].property_values[].property_id var.
           Senaryo 1 / 2 karari bu olcumdur; kod senaryoyu kendisi SECMEZ.
mod=olc  : --senaryo 1|2 ZORUNLU (prob sonucuyla Serdar onayinda secilir) + --prob (prob OLCUM.json) ZORUNLU. --gruplar ornament,kupa,
           sade,poster,yd. Okunur: (ornament grubu seciliyse) magaza tanimlari (readiness, iade, bolum; emsal ornament_taslak.py:124-133),
           ilan alanlari batch'ten (state, shipping_profile_id, return_policy_id, shop_section_id, taxonomy_id), envanter (senaryo 1 batch
           Inventory, senaryo 2 ilan basi GET; emsal kupa_galeri78.py:357, yd_yapi_yaz.py:163). Ilan basina: menu sayisi, menu basina
           property_id + ad + deger sayisi, urun sayisi (acik / kapali), *_on_property, offering readiness_state_id degerleri.
Istek (TEK kosu) [hesap]: 1 (magaza) + 3 (yalniz ornament grubu seciliyse) + ceil(ilan / 100) (batch) + (senaryo 2: ilan sayisi).
Kota: okuma baslamadan kalan >= tahmin + KOTA_SINIRI (etsy_common, 10); her istekten once sert taban (etsy_common._istek_oncesi).
GIZLILIK (depo public, loglar acik): ilan kimligi YALNIZ --out/OLCUM.json'a yazilir (Drive). Log, SAYIM.txt (STEP_SUMMARY) ve hata
mesajlarinda kimlik yok: logda yalniz grup kodu ve sira numarasi; her Etsy cagrisi BaseException yakalayan sarmalayicidan gecer, mesajdaki
6+ haneli sayilar maskelenip yeniden firlatilir (etsy_common HATA satiri yolu basar; baglanti / zaman asimi hatasi requests mesajinda URL).
Yazma yontemleri (_call GET disi, post_file, put_json, post_json, put, post, patch, delete) SystemExit.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from etsy_common import KOTA_SINIRI, Etsy, TokenStore, mask  # noqa: E402

GRUPLAR = ("ornament", "kupa", "sade", "poster", "yd")
BATCH = 100
TANIM_UCLARI = ("readiness-state-definitions", "policies/return", "sections")   # ornament_taslak.py:124-133
BEKLENEN = {"ornament": 78, "kupa": 78, "poster": 78, "yd": 78, "sade": 11}   # sade: ARIES sablonu DURUM'da yok (gorev-g sade_taslak.py:741)
JSON_ANAHTAR = {"ornament": "ciftler", "sade": "burclar"}   # ornament_galeri9.py:14; gorev-g sade_taslak.py:414, :451
GEREKLI_YOL = ("products[].offerings[].readiness_state_id", "products[].property_values[].property_id")
ON_PROP = ("price_on_property", "quantity_on_property", "sku_on_property", "readiness_state_on_property")
ILAN_ALAN = ("state", "shipping_profile_id", "return_policy_id", "shop_section_id", "taxonomy_id")
DERIN = 10
_RAKAM = re.compile(r"\d{6,}")


def maske(t):
    return _RAKAM.sub("<id>", str(t))


def log(m):
    print(maske(m), flush=True)


class CanliOkur(Etsy):
    """Yalniz GET. Diger her yontem (etsy_common'un kendi requests.post'unu yapan post_file dahil) SystemExit; yol yazilmaz."""
    def _call(self, method, path, **kw):
        if str(method).upper() != "GET":
            raise SystemExit(f"YASAK (salt okuma): {str(method).upper()}")
        return super()._call(method, path, **kw)

    def _yasak(self, ad):
        raise SystemExit(f"YASAK (salt okuma): {ad}")

    def post_file(self, *a, **k):
        self._yasak("post_file")

    def put_json(self, *a, **k):
        self._yasak("put_json")


    def post_json(self, *a, **k):
        self._yasak("post_json")

    def put(self, *a, **k):
        self._yasak("put")

    def post(self, *a, **k):
        self._yasak("post")

    def patch(self, *a, **k):
        self._yasak("patch")

    def delete(self, *a, **k):
        self._yasak("delete")


def oku(api, path, params=None, etiket=""):
    """Tek GET; her hata (SystemExit dahil) maskelenip yeniden firlatilir. etiket: "<grup> #<sira>" (kimlik degil)."""
    on = f"{etiket}: " if etiket else ""
    try:
        return api.get(path, params=params)
    except SystemExit as e:
        raise SystemExit(on + maske(e.code)) from None
    except KeyboardInterrupt:
        raise KeyboardInterrupt(on + "iptal") from None
    except BaseException as e:   # noqa: BLE001  baglanti / zaman asimi: mesajda URL olabilir
        raise RuntimeError(f"{on}{type(e).__name__}: {maske(e)}") from None


def kota_dur(e):
    """Kosu geneli hata (ilan hatasi degil): kota DUR'u, sinyal, 429 gunluk kota, token / yenileme hatasi -> yukari firlatilir."""
    if not isinstance(e, SystemExit):
        return False
    m = str(e.code).lower()
    return any(k in m for k in ("dur: kota", "dur: sinyal", "429", "token", "refresh", "yenile"))


# ---------------------------------------------------------------- sema (alan yolu -> turler)
def sema(d, on="", derin=0, S=None):
    """En az 6 seviye (DERIN 10) iner; listede TUM ogelerin anahtarlari birlesir ("[]"). -> {yol: [tur, ...]} (deger yok)."""
    S = {} if S is None else S
    if derin > DERIN:
        return S
    if isinstance(d, dict):
        for k, v in d.items():
            yol = f"{on}.{k}" if on else str(k)
            S.setdefault(yol, set()).add(type(v).__name__)
            sema(v, yol, derin + 1, S)
    elif isinstance(d, list):
        for x in d:
            sema(x, f"{on}[]", derin + 1, S)
    return S


def sema_json(S):
    return {k: sorted(v) for k, v in sorted(S.items())}


def alt_sema(S, kok):
    """kok altindaki yollar kok'suz (or. 'results[].inventory.' -> 'products[]...')."""
    return {k[len(kok):]: v for k, v in S.items() if k.startswith(kok)}


# ---------------------------------------------------------------- ilan listeleri
def _rakam(x):
    s = str(x or "").strip()
    return s if s.isdigit() else None


def liste_oku(grup, yol):
    """-> ([(kod, lid)], kimliksiz_sayisi). Bicim: ornament DURUM.json {"ciftler": {kod: lid}}, sade DURUM.json {"burclar": {burc: lid}};
    kupa / poster / yd CSV (listing_id + cift). Gecerli kimlik sayisi BEKLENEN'in altindaysa DUR (sessiz bos grup yok)."""
    yol = Path(yol)
    if not yol.is_file():
        raise SystemExit(f"DUR: {grup} listesi yok")
    if yol.suffix.lower() == ".json":
        D = json.loads(yol.read_text(encoding="utf-8"))
        anahtar = JSON_ANAHTAR.get(grup)
        if not anahtar or not isinstance(D, dict) or not isinstance(D.get(anahtar), dict):
            raise SystemExit(f"DUR: {grup} listesi beklenen bicimde degil ({anahtar or 'json beklenmiyor'} sozlugu yok)")
        D = D[anahtar]
        ham = [(str(k), v if not isinstance(v, dict) else v.get("listing_id")) for k, v in D.items()]
    else:
        with open(yol, encoding="utf-8-sig") as fh:
            R = list(csv.DictReader(fh))
        if R and ("listing_id" not in R[0] or "cift" not in R[0]):
            raise SystemExit(f"DUR: {grup} CSV sutunlari listing_id + cift degil")
        ham = [(r["cift"], r["listing_id"]) for r in R]
    iyi = [(k, _rakam(v)) for k, v in ham if _rakam(v)]
    if len(iyi) < BEKLENEN.get(grup, 1):
        raise SystemExit(f"DUR: {grup} listesinde {len(iyi)} gecerli kimlik (beklenen en az {BEKLENEN.get(grup, 1)})")
    return iyi, len(ham) - len(iyi)


# ---------------------------------------------------------------- envanter ozeti
def env_ozet(inv):
    """-> (ozet, neden). neden dolu ise ozet None (olculemedi). Beklenmeyen tur kosuyu dusurmez (olculemedi)."""
    try:
        return _env_ozet(inv)
    except (TypeError, AttributeError, ValueError, KeyError) as e:
        return None, f"beklenmeyen tur ({type(e).__name__})"


def _env_ozet(inv):
    if not isinstance(inv, dict):
        return None, "envanter sozluk degil"
    P = inv.get("products")
    if not isinstance(P, list):
        return None, "products yok"
    menu, sira = {}, []
    acik = kapali = rsd_eksik = 0
    rsd = Counter()
    for p in P:
        if not isinstance(p, dict) or not isinstance(p.get("property_values"), list) or not isinstance(p.get("offerings"), list):
            return None, "urun bicimi beklenmeyen"
        for v in p["property_values"]:
            if not isinstance(v, dict) or "property_id" not in v:
                return None, "property_values bicimi beklenmeyen"
            pid = v["property_id"]
            if pid not in menu:
                menu[pid] = {"ad": v.get("property_name"), "degerler": set()}
                sira.append(pid)
            for x in v.get("values") or []:
                menu[pid]["degerler"].add(str(x))
        offs = [o for o in p["offerings"] if isinstance(o, dict)]
        if not offs:
            return None, "offering yok"
        rsd_eksik += sum(1 for o in offs if "readiness_state_id" not in o)
        if any(o.get("is_enabled") for o in offs):
            acik += 1
        else:
            kapali += 1
        for o in offs:
            if "readiness_state_id" in o:
                rsd[str(o.get("readiness_state_id"))] += 1
    sayilar = [len(menu[pid]["degerler"]) for pid in sira]
    carpim = math.prod(sayilar)            # varyasyonsuz ilan: 1
    oz = {"menu_sayisi": len(sira),
          "menuler": [{"property_id": pid, "ad": menu[pid]["ad"], "deger_sayisi": len(menu[pid]["degerler"])} for pid in sira],
          "urun": len(P), "acik": acik, "kapali": kapali, "carpim": carpim, "tam_carpim": len(P) == carpim,
          "on_property": {k: inv.get(k) for k in ON_PROP}, "readiness_state_id": dict(rsd), "readiness_eksik_offering": rsd_eksik}
    return oz, None


def yapi_etiketi(oz):
    return f"{oz['menu_sayisi']} menu " + "x".join(str(m["deger_sayisi"]) for m in oz["menuler"]) if oz else "olculemedi"


def tahmin(n_ilan, ornament_var, senaryo):
    """TEK kosu istek tahmini [hesap]."""
    t = 1 + (len(TANIM_UCLARI) if ornament_var else 0) + math.ceil(n_ilan / BATCH)
    return t + (n_ilan if senaryo == 2 else 0)


def kota_kapi(api, gerek):
    kalan = api.remaining
    if kalan is None or not str(kalan).isdigit():
        raise SystemExit("DUR: kalan kota okunamadi (okuma baslamadi)")
    if int(kalan) < gerek + KOTA_SINIRI:
        raise SystemExit(f"DUR: kota {kalan} < tahmini istek {gerek} + {KOTA_SINIRI} (okuma baslamadi; --gruplar ile bolun)")


def _batch_sonuc(j):
    if not isinstance(j, dict) or not isinstance(j.get("results"), list):
        raise SystemExit("DUR: batch yaniti beklenen bicimde degil (results listesi yok)")
    return {str(x.get("listing_id")): x for x in j["results"] if isinstance(x, dict)}


def _inv_anahtar(L):
    """Batch ilaninda envanter anahtari (buyuk/kucuk harf olculmedi): 'inventory' adli sozluk."""
    for k, v in (L or {}).items():
        if str(k).lower() == "inventory" and isinstance(v, dict):
            return k
    return None


# ---------------------------------------------------------------- modlar
def _yaz(out, O, sayim, baslik):
    json.dump(O, open(out / "OLCUM.json", "w"), indent=1, ensure_ascii=False)
    (out / "SAYIM.txt").write_text("\n".join(sayim) + "\n")
    (out / "OZET.md").write_text(baslik)


def prob(api, shop, G, out):
    secim = [(g, G[g][0]) for g in GRUPLAR if G.get(g)]
    if not any(g == "poster" for g, _ in secim):
        raise SystemExit("DUR: prob poster grubunu ister (3 menulu tek ilan envanteri)")
    O = {"mod": "prob", "not": "istek sayisi hatasiz yol icindir; 5xx / 401 tekrarlari dahil degil (10'luk pay karsilar)"}
    try:
        oku(api, f"/shops/{shop}", etiket="magaza")
        O["kota_bas"] = api.remaining
        kota_kapi(api, 3)
        sec = secim[:5]
        ids = [kl[1] for _, kl in sec]
        O.update(istenen=len(ids), gruplar=[g for g, _ in sec])
        log(f"prob: batch {len(ids)} ilan (gruplar {','.join(O['gruplar'])})")
        j, hata = None, None
        try:
            j = oku(api, "/listings/batch", params={"listing_ids": ",".join(ids), "includes": "Inventory"}, etiket="prob batch")
        except (SystemExit, RuntimeError) as e:
            if kota_dur(e):
                raise
            hata = maske(e.code if isinstance(e, SystemExit) else e)[:200]
        B = {}
        if j is not None:
            try:
                B = _batch_sonuc(j)
            except SystemExit as e:
                hata = str(e.code)
        O["batch_hata"] = hata
        O["sema_batch"] = sema_json(sema(j)) if j is not None else {}
        poster_id = dict(sec)["poster"][1]
        donen = {g: (B.get(lid) is not None) for g, (_, lid) in sec}
        env_var = {g: bool(_inv_anahtar(B.get(lid)) and isinstance((B[lid].get(_inv_anahtar(B[lid])) or {}).get("products"), list))
                   for g, (_, lid) in sec if B.get(lid) is not None}
        O["donen"] = sum(donen.values())
        O["grup_envanter"] = {g: env_var.get(g) for g in donen}       # None: ilan batch'te donmedi
        if hata:
            O["batch_envanter"] = "HAYIR (batch hatasi)"
        elif env_var and all(env_var.values()) and all(donen.values()):
            O["batch_envanter"] = "EVET"
        elif any(env_var.values()):
            O["batch_envanter"] = "KISMI"
        else:
            O["batch_envanter"] = "HAYIR"
        inv = oku(api, f"/listings/{poster_id}/inventory", etiket="prob poster")     # batch karari bundan once kayitli
        Si = sema(inv)
        O["sema_envanter"] = sema_json(Si)
        L = B.get(poster_id) or {}
        a = _inv_anahtar(L)
        pb = sema(L.get(a)) if a else {}
        O["batch_envanter_anahtar"] = a
        O["products_sema_ayni"] = (sema_json(pb) == sema_json(Si)) if a else None       # ayni poster ilaninin iki ucu
        O["yalniz_batch"], O["yalniz_tek"] = (sorted(set(pb) - set(Si)), sorted(set(Si) - set(pb))) if a else ([], [])
        O["gerekli_yol"] = {y: (y in Si) for y in GEREKLI_YOL}
    finally:
        O["istek"], O["kota_son"] = api.calls, api.remaining
        sayim = [f"mod prob | istek {O['istek']} | batch {O.get('donen')}/{O.get('istenen')} | batch envanter {O.get('batch_envanter')}",
                 f"products semasi ayni (ayni poster ilani): {O.get('products_sema_ayni')}",
                 f"gerekli yollar: {sum((O.get('gerekli_yol') or {}).values())}/{len(GEREKLI_YOL)}"]
        _yaz(out, O, sayim, "# CANLI YAPI prob\n\n" + "\n".join(f"- {s}" for s in sayim) + f"\n- {O['not']}\n")
        for s in sayim:
            log(s)
    if not all(O["gerekli_yol"].values()):
        raise SystemExit("FAIL: tek ilan envanterinde gerekli yol yok (prob semasi beklenen degil)")
    return O


def _grup_ozet(S):
    olcu = [s for s in S if "envanter" in s]
    return {"ilan": len(S), "olculemedi": len(S) - len(olcu),
            "olculemedi_neden": dict(Counter(s["olculemedi"] for s in S if "olculemedi" in s)),
            "state": dict(Counter(str(s.get("state")) for s in S if "state" in s)),
            "yapi": dict(Counter(yapi_etiketi(s.get("envanter")) for s in olcu)),
            "urun_min": min((s["envanter"]["urun"] for s in olcu), default=None),
            "urun_max": max((s["envanter"]["urun"] for s in olcu), default=None),
            "tam_carpim_degil": sum(1 for s in olcu if not s["envanter"]["tam_carpim"]),
            "readiness_eksik_offering": sum(s["envanter"]["readiness_eksik_offering"] for s in olcu),
            "return_policy_id": dict(Counter(str(s.get("return_policy_id")) for s in S if "return_policy_id" in s)),
            "shop_section_id": dict(Counter(str(s.get("shop_section_id")) for s in S if "shop_section_id" in s)),
            "readiness_state_id": dict(sum((Counter(s["envanter"]["readiness_state_id"]) for s in olcu), Counter()))}


def olc(api, shop, G, out, senaryo, P):
    if P.get("mod") != "prob" or not isinstance(P.get("sema_envanter"), dict):
        raise SystemExit("DUR: --prob gecerli bir prob OLCUM.json degil")
    g_ = P.get("gerekli_yol")
    if not isinstance(g_, dict) or set(g_) != set(GEREKLI_YOL) or not all(g_.values()):
        raise SystemExit("DUR: --prob basarili degil (gerekli yollar yok; FAIL prob ile olc kosulmaz)")
    if senaryo == 1 and P.get("batch_envanter") != "EVET":
        raise SystemExit("DUR: senaryo 1 icin prob batch envanter EVET olmali")
    prob_yol = set(alt_sema(P["sema_envanter"], "products[]"))
    satir, sira_ilan = [], []
    for g in GRUPLAR:
        for n, (kod, lid) in enumerate(G.get(g) or [], 1):
            sira_ilan.append((g, n, kod, lid))
    ids = list(dict.fromkeys(x[3] for x in sira_ilan))
    orn = bool(G.get("ornament"))
    tah = tahmin(len(ids), orn, senaryo)
    O = {"mod": "olc", "senaryo": senaryo, "tahmin": tah, "prob_sha256": P.get("_sha256"), "yinelenen_kimlik": len(sira_ilan) - len(ids),
         "gruplar": {g: {"kaynak": len(G.get(g) or []), "kimliksiz": G.get("_kimliksiz", {}).get(g, 0)} for g in GRUPLAR if g in G},
         "uyari": "olc, prob semasiyla kuruldu; prob olcumu olmadan gercek kosuda kullanilmaz. Istek tahmini hatasiz yol icindir "
                  "(5xx / 401 tekrarlari dahil degil; 10'luk pay karsilar)", "ilanlar": satir, "magaza": {}, "uyarilar": []}
    try:
        oku(api, f"/shops/{shop}", etiket="magaza")
        O["kota_bas"] = api.remaining
        kota_kapi(api, tah)
        log(f"olc senaryo {senaryo} | ilan {len(ids)} | tahmini istek {tah}")
        if orn:
            for u in TANIM_UCLARI:
                j = oku(api, f"/shops/{shop}/{u}", etiket=f"tanim {u}") or {}
                O["magaza"][u] = j.get("results")
                if isinstance(j.get("count"), int) and isinstance(j.get("results"), list) and j["count"] != len(j["results"]):
                    O["uyarilar"].append(f"{u}: count {j['count']} != donen {len(j['results'])} (sayfalama yok)")
        B = {}
        for i in range(0, len(ids), BATCH):
            par = {"listing_ids": ",".join(ids[i:i + BATCH])}
            if senaryo == 1:
                par["includes"] = "Inventory"
            B.update(_batch_sonuc(oku(api, "/listings/batch", params=par, etiket=f"batch {i // BATCH + 1}")))
            log(f"batch {min(i + BATCH, len(ids))}/{len(ids)}")
        env_bel = {}
        t0 = time.time()
        for k, (g, n, kod, lid) in enumerate(sira_ilan, 1):
            L = B.get(lid)
            s = {"grup": g, "sira": n, "kod": kod, "listing_id": lid}
            if L is None:
                s["olculemedi"] = "batch donmedi"
            else:
                s.update({a_: L.get(a_) for a_ in ILAN_ALAN})
                inv, neden = None, None
                if senaryo == 1:
                    a_ = _inv_anahtar(L)
                    inv = L.get(a_) if a_ else None
                elif lid in env_bel:
                    inv, neden = env_bel[lid]
                else:
                    try:
                        inv = oku(api, f"/listings/{lid}/inventory", etiket=f"{g} #{n}")
                    except (SystemExit, RuntimeError) as e:
                        if kota_dur(e):
                            raise
                        neden = "GET hatasi: " + maske(e.code if isinstance(e, SystemExit) else e)[:160]
                    env_bel[lid] = (inv, neden)
                oz, n2 = (None, neden) if neden else env_ozet(inv)
                if n2:
                    s["olculemedi"] = n2
                else:
                    s["envanter"] = oz
                    s["sema_ortak"] = len(set(alt_sema(sema(inv), "products[]")) & prob_yol)
            satir.append(s)
            if k % 10 == 0 or k == len(sira_ilan):
                g_ = time.time() - t0
                log(f"ETA: {k}/{len(sira_ilan)} ilan | gecen {g_ / 60:.1f} dk | kalan {g_ / k * (len(sira_ilan) - k) / 60:.1f} dk | %{100 * k // len(sira_ilan)}")
    finally:
        O["istek"], O["kota_son"] = api.calls, api.remaining
        O["ozet"] = {g: _grup_ozet([s for s in satir if s["grup"] == g]) for g in GRUPLAR if any(s["grup"] == g for s in satir)}
        md = [f"# CANLI YAPI olc (senaryo {senaryo})", "", f"- istek {O['istek']} (tahmin {tah})", f"- {O['uyari']}"] + \
             [f"- uyari: {x}" for x in O["uyarilar"]] + [""]
        sayim = [f"mod olc | senaryo {senaryo} | istek {O['istek']} / tahmin {tah} | ilan {len(satir)}/{len(sira_ilan)}"]
        for g, z in O["ozet"].items():
            md += [f"## {g}", f"- ilan {z['ilan']}, olculemedi {z['olculemedi']} {z['olculemedi_neden'] or ''}", f"- state {z['state']}",
                   f"- yapi {z['yapi']}", f"- urun min {z['urun_min']} / max {z['urun_max']}; tam carpim olmayan {z['tam_carpim_degil']}",
                   f"- readiness_state_id olmayan offering {z['readiness_eksik_offering']}",
                   f"- return_policy_id {z['return_policy_id']}", f"- shop_section_id {z['shop_section_id']}",
                   f"- readiness_state_id {z['readiness_state_id']}", ""]
            sayim.append(f"{g}: ilan {z['ilan']} | olculemedi {z['olculemedi']} | yapi turu {len(z['yapi'])} | urun {z['urun_min']}-{z['urun_max']}")
        _yaz(out, O, sayim, "\n".join(md))
        for s_ in sayim:
            log(s_)
    olcu = [s for s in satir if "envanter" in s]
    if satir and not olcu:
        raise SystemExit("DUR: hicbir ilanin envanteri olculemedi (sema prob semasindan tamamen farkli)")
    if olcu and all(s["sema_ortak"] == 0 for s in olcu):
        raise SystemExit("DUR: envanter semasi prob semasiyla hic ortak degil")
    return O


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", choices=["prob", "olc"], required=True)
    ap.add_argument("--senaryo", type=int, choices=[1, 2])
    ap.add_argument("--prob", help="olc icin prob kosusunun OLCUM.json'u (zorunlu)")
    ap.add_argument("--gruplar", default=",".join(GRUPLAR))
    for g in GRUPLAR:
        ap.add_argument(f"--{g}", help=f"{g} ilan listesi (json / csv)")
    ap.add_argument("--out", default="_out")
    a = ap.parse_args(argv)
    if a.mod == "olc" and (a.senaryo is None or not a.prob):
        raise SystemExit("DUR: olc icin --senaryo 1|2 ve --prob zorunlu (senaryo prob sonucuyla Serdar onayinda secilir)")
    gr = [x.strip() for x in a.gruplar.split(",") if x.strip()]
    if not gr or any(x not in GRUPLAR for x in gr) or len(set(gr)) != len(gr):
        raise SystemExit(f"DUR: --gruplar yalniz {','.join(GRUPLAR)}")
    G, kimliksiz = {}, {}
    for g in gr:
        yol = getattr(a, g)
        if not yol:
            raise SystemExit(f"DUR: --{g} listesi verilmedi")
        G[g], kimliksiz[g] = liste_oku(g, yol)
        log(f"liste {g}: {len(G[g])} ilan, kimliksiz {kimliksiz[g]}")
    G["_kimliksiz"] = kimliksiz
    P = None
    if a.mod == "olc":
        b = Path(a.prob).read_bytes()
        P = json.loads(b); P["_sha256"] = hashlib.sha256(b).hexdigest()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k); mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    api = CanliOkur(store)
    shop = os.environ.get("ETSY_SHOP_ID", "")
    if not shop.isdigit():
        raise SystemExit("DUR: ETSY_SHOP_ID yok")
    if a.mod == "prob":
        return prob(api, shop, G, out)
    return olc(api, shop, G, out, a.senaryo, P)


if __name__ == "__main__":
    main()
