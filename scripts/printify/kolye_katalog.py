#!/usr/bin/env python3
"""Printify KOLYE katalog SALT OKUMA (Serdar 9 Kas 2026 "kolye istiyorum" + "ok"). Yalniz standart kutuphane (urllib).
YALNIZ GET, YALNIZ PY_IZIN'deki /catalog uclari (printify_kupa_oku.py:25-33 ve pet_katalog.py ile ayni liste, tam eslesme; baska yol,
host ya da yontem DUR). Urun, taslak, siparis, yukleme, mockup OLUSTURULMAZ. Etsy'ye dokunmaz.
Printify katalog API'si MALIYET VERMEZ (maliyet yalniz urun taslagi acilip silinerek okunur: bu iste YASAK) -> "API vermedi".

Kullanim:
  kolye_katalog.py oku <ham>      env PRINTIFY_API_KEY (zorunlu; yok / bos / icte bosluk -> DUR). Ham yanitlar (anahtar maskeli).
  kolye_katalog.py rapor <cikti>  AG YOK; <cikti>/ham'dan KOLYE_KATALOG.csv, KOLYE_KARGO.csv, KOLYE_KATALOG.md + log ozeti.
Aday: blueprint BASLIGINDA \\b(necklace|pendant)\\b (aciklama degil); zorunlu 778 (Oval Necklace), 9114 (Oval Pendant), 2947
(Birthstone Circle Charm (Engraving); baslikta necklace / pendant yok, zorunlu listeyle aday; Serdar 9 Kas) biri listede yoksa DUR; aday > 40 DUR;
saglayicilar okunduktan sonra istek tahmini > 600 ise aga devam etmeden DUR. Bekleme 0,65 sn (~92 istek/dk; resmi sinir 100/dk).
429: ustel bekleme, en cok 4 deneme, sonra DUR. 401 / 403: DUR "anahtar ya da kapsam". Diger 4xx: alan "API vermedi", aday surer.
Teknik (baskili / kazimali / belirsiz): decoration_methods alani varsa ondan, yoksa blueprint aciklamasindan, emin degilse belirsiz."""
import csv
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPException
from pathlib import Path

API = "https://api.printify.com"
UA = "AstroLoveArt-katalog-okuma"
PY_IZIN = [
    r"/v1/catalog/blueprints\.json",
    r"/v1/catalog/blueprints/\d+\.json",
    r"/v1/catalog/blueprints/\d+/print_providers\.json",
    r"/v1/catalog/blueprints/\d+/print_providers/\d+/(variants|shipping)\.json",
    r"/v1/catalog/print_providers/\d+\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping\.json",
    r"/v2/catalog/blueprints/\d+/print_providers/\d+/shipping/[a-z_]+\.json",
]
ULKELER = "US CA GB DE FR IT ES NL AU TR".split()
# Serdar 9 Kas: iki urun arasinda kararsiz, ikisi de arastirilsin -> uc zorunlu blueprint. Ad uyusmazsa UYARI (DUR degil).
ZORUNLU = {778: "Oval Necklace", 9114: "Oval Pendant", 2947: "Birthstone Circle Charm (Engraving)"}
AZAMI_ADAY = 40
AZAMI_TAHMIN = 600
SAGLAYICI_BASI = 8          # variants + shipping v1 + shipping v2 + yontem basina shipping (~4) + print_providers/{id}
BEKLE = 0.65
ADAY_RX = re.compile(r"\b(?:necklace|pendant)\b", re.I)
KAZIMA_RX = re.compile(r"engrav|photograv|\betch(?:ed|ing)?\b", re.I)          # "laser-cut", "stretch", "sketch" eslesmez
BASKI_RX = re.compile(r"sublimat|\bprinted\b|\bprinting\b|\buv[- ]print|\bdtg\b|full[- ]colou?r", re.I)   # "print area / provider" eslesmez
BICIM = re.compile(r"^\S+$")
YOK = "API vermedi"
ISTEKLER = []
GONDERIM = [0]               # HTTP gonderimi (429 / 5xx / baglanti tekrarlari dahil); sert ust sinir AZAMI_TAHMIN
SIRLAR = []


def maskele(m):
    for s in SIRLAR:
        if s:
            m = m.replace(s, "***")
    return m


def kisa(m, n):
    return maskele(str(m))[:n]


def log(m):
    print(maskele(str(m)), flush=True)


def yaz(p, veri):
    p.write_text(maskele(json.dumps(veri, indent=1, ensure_ascii=False)), encoding="utf-8")


class YonlendirmeYok(urllib.request.HTTPRedirectHandler):
    """30x takip edilmez (Authorization baska hosta tasinmasin; hedef izin listesinden gecmez)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_ACICI = urllib.request.build_opener(YonlendirmeYok)


def ac(req, timeout=60):
    return _ACICI.open(req, timeout=timeout)


def _yol_ok(yol):
    return isinstance(yol, str) and yol.startswith("/") and "//" not in yol and "://" not in yol and ".." not in yol


def _govde(e):
    try:
        return e.read().decode(errors="replace")
    except (OSError, HTTPException) as x:
        return f"govde okunamadi {type(x).__name__}"


def json_coz(b):
    t = b.decode(errors="replace") if isinstance(b, (bytes, bytearray)) else str(b)
    try:
        return json.loads(t)
    except ValueError:
        return {"_hata": "json", "_metin": kisa(t, 300)}


def anahtar_al():
    k = os.environ.get("PRINTIFY_API_KEY", "").replace("﻿", "").strip()
    if not k:
        raise SystemExit("DUR: Printify anahtari yok ya da bos (PRINTIFY_API_KEY)")
    if not BICIM.match(k):
        raise SystemExit("DUR: Printify anahtari gecersiz (icte bosluk / satir sonu)")
    SIRLAR[:] = [k]
    return k


def istek(yontem, yol, anahtar, params=None):
    """YALNIZ GET + PY_IZIN (tam eslesme). -> (http, json). 401/403 ve 4 denemeden sonra 429 DUR; diger 4xx {"_hata": kod}."""
    if str(yontem).upper() != "GET":
        raise SystemExit(f"DUR: Printify'da GET disi istek ({yontem} {yol})")
    if not _yol_ok(yol) or not any(re.fullmatch(p, yol) for p in PY_IZIN):
        raise SystemExit(f"DUR: Printify izinsiz uc (istek atilmadi): GET {yol}")
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    kod, j = 0, {"_hata": 0}
    for deneme in range(4):
        if GONDERIM[0] >= AZAMI_TAHMIN:
            raise SystemExit(f"DUR: HTTP gonderimi {GONDERIM[0]} >= {AZAMI_TAHMIN} (sert ust sinir, tekrarlar dahil)")
        GONDERIM[0] += 1
        time.sleep(BEKLE)
        req = urllib.request.Request(API + yol + q, headers={"Authorization": f"Bearer {anahtar}", "User-Agent": UA,
                                                             "Accept": "application/json"}, method="GET")
        try:
            with ac(req, timeout=60) as r:
                kod, j = r.status, json_coz(r.read())
        except urllib.error.HTTPError as e:
            kod = e.code
            if kod in (401, 403):
                ISTEKLER.append({"yol": yol + q, "http": kod})
                raise SystemExit(f"DUR: Printify {kod}: anahtar ya da kapsam (catalog.read / print_providers.read): GET {yol}")
            if kod == 429:
                if deneme < 3:
                    b = 5 * 2 ** deneme
                    log(f"  GET {yol} HTTP 429, {b}s bekleniyor (deneme {deneme + 1}/4)")
                    time.sleep(b)
                    continue
                ISTEKLER.append({"yol": yol + q, "http": kod})
                raise SystemExit(f"DUR: Printify 429: 4 denemeden sonra hiz siniri: GET {yol}")
            if kod >= 500 and deneme < 3:
                time.sleep(5 * (deneme + 1))
                continue
            j = {"_hata": kod, "_metin": kisa(_govde(e), 300)}
        except (OSError, HTTPException) as e:      # URLError, ssl, baglanti kopmasi
            if deneme < 3:
                time.sleep(10)
                continue
            kod, j = 0, {"_hata": 0, "_metin": type(e).__name__}
        break
    ISTEKLER.append({"yol": yol + q, "http": kod})
    return kod, j


def get(yol, anahtar, params=None):
    return istek("GET", yol, anahtar, params)


def liste(x):
    return [e for e in x if isinstance(e, dict)] if isinstance(x, list) else []


def sozluk(x):
    return x if isinstance(x, dict) else {}


# ---------------------------------------------------------------------------------------------------------------- oku
def adaylar(bps):
    a = {}
    for b in liste(bps):
        if isinstance(b.get("id"), int) and ADAY_RX.search(str(b.get("title") or "")):
            a[b["id"]] = {"baslik": b.get("title"), "neden": "baslik"}
    return a


def oku(ham):
    anahtar = anahtar_al()
    ham.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        return _oku(ham, anahtar, t0)
    finally:
        yaz(ham / "_istekler.json", {"istekler": ISTEKLER, "http_gonderim": GONDERIM[0]})
        log(f"ISTEK toplam {len(ISTEKLER)} (yalniz GET) | HTTP gonderim {GONDERIM[0]} (tekrarlar dahil) | sure {int(time.time() - t0)}s")


def _oku(ham, anahtar, t0):  # noqa: C901
    k, bps = get("/v1/catalog/blueprints.json", anahtar)
    yaz(ham / "blueprints.json", bps)
    if k != 200 or not isinstance(bps, list):
        raise SystemExit(f"DUR: blueprint listesi okunamadi (HTTP {k})")
    a = adaylar(bps)
    var = {b.get("id"): b.get("title") for b in liste(bps)}
    eksik = [f"{z} ({ad})" for z, ad in ZORUNLU.items() if z not in var]
    if eksik:
        yaz(ham / "_adaylar.json", {str(i): v for i, v in a.items()})
        raise SystemExit(f"DUR: zorunlu blueprint katalogda yok: {', '.join(eksik)}")
    for z, ad in ZORUNLU.items():
        if str(var[z] or "").strip().casefold() != ad.casefold():
            log(f"UYARI: zorunlu blueprint {z} katalog adi {str(var[z])[:80]!r}, beklenen {ad!r} (DUR degil)")
        a.setdefault(z, {"baslik": var[z], "neden": "zorunlu"})
    yaz(ham / "_adaylar.json", {str(i): v for i, v in sorted(a.items())})
    log(f"ADAY {len(a)}: " + json.dumps({str(i): v["baslik"] for i, v in sorted(a.items())}, ensure_ascii=False))
    if len(a) > AZAMI_ADAY:
        raise SystemExit(f"DUR: aday {len(a)} > {AZAMI_ADAY}; aga devam edilmedi, liste ham/_adaylar.json")
    ciftler = []
    for i, bid in enumerate(sorted(a), 1):
        _, bp = get(f"/v1/catalog/blueprints/{bid}.json", anahtar)
        yaz(ham / f"bp_{bid}.json", bp)
        _, pps = get(f"/v1/catalog/blueprints/{bid}/print_providers.json", anahtar)
        yaz(ham / f"bp_{bid}_print_providers.json", pps)
        ciftler += [(bid, p["id"]) for p in liste(pps) if isinstance(p.get("id"), int)]
        log(f"[aday {i}/{len(a)}] {bid} | saglayici {len(liste(pps))} | gecen {int(time.time() - t0)}s")
    tahmin = GONDERIM[0] + SAGLAYICI_BASI * len(ciftler)
    log(f"TAHMIN istek: {GONDERIM[0]} gonderildi + {SAGLAYICI_BASI} x {len(ciftler)} (aday x saglayici) = {tahmin} (sinir {AZAMI_TAHMIN})")
    yaz(ham / "_tahmin.json", {"yapilan": GONDERIM[0], "cift": len(ciftler), "tahmin": tahmin})
    if tahmin > AZAMI_TAHMIN:
        raise SystemExit(f"DUR: istek tahmini {tahmin} > {AZAMI_TAHMIN}; aga devam edilmedi")
    pp_okundu = set()
    for n, (bid, pid) in enumerate(ciftler, 1):
        _, v = get(f"/v1/catalog/blueprints/{bid}/print_providers/{pid}/variants.json", anahtar, {"show-out-of-stock": 1})
        yaz(ham / f"bp_{bid}_pp_{pid}_variants.json", v)
        _, s1 = get(f"/v1/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json", anahtar)
        yaz(ham / f"bp_{bid}_pp_{pid}_shipping_v1.json", s1)
        _, s2 = get(f"/v2/catalog/blueprints/{bid}/print_providers/{pid}/shipping.json", anahtar)
        yaz(ham / f"bp_{bid}_pp_{pid}_shipping_v2.json", s2)
        for d in liste(sozluk(s2).get("data")):
            yk = re.sub(r"[^a-z_]", "", str(sozluk(d.get("attributes")).get("name") or d.get("id") or "").lower())
            if yk:
                _, m = get(f"/v2/catalog/blueprints/{bid}/print_providers/{pid}/shipping/{yk}.json", anahtar)
                yaz(ham / f"bp_{bid}_pp_{pid}_shipping_v2_{yk}.json", m)
        if pid not in pp_okundu:
            pp_okundu.add(pid)
            _, info = get(f"/v1/catalog/print_providers/{pid}.json", anahtar)
            yaz(ham / f"pp_{pid}.json", info)
        if n % 5 == 0 or n == len(ciftler):
            g = time.time() - t0
            log(f"[saglayici {n}/{len(ciftler)} %{100 * n // len(ciftler)}] istek {len(ISTEKLER)} | gecen {int(g)}s")
    return 0


# -------------------------------------------------------------------------------------------------------------- rapor
def jy(ham, ad):
    p = ham / ad
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def duz(h):
    t = re.sub(r"<br\s*/?>|</p>|</li>", "\n", str(h or ""), flags=re.I)
    return re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


def _dekor(x, bul):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("decoration_methods", "decoration_method"):
                bul += [str(i) for i in (v if isinstance(v, list) else [v])]
            _dekor(v, bul)
    elif isinstance(x, list):
        for v in x:
            _dekor(v, bul)
    return bul


def teknik(bp, varyant_jsonlari):
    """-> (baskili / kazimali / belirsiz, kaynak)."""
    dm = _dekor(bp, []) + [m for v in varyant_jsonlari for m in _dekor(v, [])]
    if dm:
        k = any(KAZIMA_RX.search(m) for m in dm)
        b = any(BASKI_RX.search(m) or re.search(r"sublim|print", m, re.I) for m in dm)
        return ("kazimali" if k and not b else "baskili" if b and not k else "belirsiz"), "decoration_methods: " + ", ".join(sorted(set(dm)))
    ac_ = duz(sozluk(bp).get("description")) + " " + str(sozluk(bp).get("title") or "")
    k, b = bool(KAZIMA_RX.search(ac_)), bool(BASKI_RX.search(ac_))
    if k != b:
        return ("kazimali" if k else "baskili"), "aciklama metni"
    return "belirsiz", "aciklama metni (" + ("ikisi de" if k else "hicbiri") + ")"


def _ph(v):
    return [(str(p.get("position")), p.get("width"), p.get("height")) for p in liste(v.get("placeholders"))]


def rapor(cikti):  # noqa: C901
    ham = cikti / "ham"
    a = jy(ham, "_adaylar.json") or {}
    ist_j = jy(ham, "_istekler.json") or {}
    ist = ist_j.get("istekler", []) if isinstance(ist_j, dict) else ist_j
    satir, kargo, ozet = [], [], []
    for bid in sorted(a, key=int):
        bp = sozluk(jy(ham, f"bp_{bid}.json"))
        pps = liste(jy(ham, f"bp_{bid}_print_providers.json"))
        vjs = [sozluk(jy(ham, f"bp_{bid}_pp_{p.get('id')}_variants.json")) for p in pps]
        tk, tk_k = teknik(bp, vjs)
        enk, saglayici, boylar, renkler = None, [], set(), set()
        for p, vj in zip(pps, vjs):
            pid = p.get("id")
            konum = sozluk(sozluk(jy(ham, f"pp_{pid}.json")).get("location"))
            yer = ", ".join(str(konum.get(k)) for k in ("country", "region", "city") if konum.get(k)) or YOK
            saglayici.append(f"{pid} {p.get('title')} ({yer})")
            vs = liste(vj.get("variants"))
            for v in vs:
                o = sozluk(v.get("options"))
                ph = _ph(v)
                boylar.add(str(o.get("size") or "")); renkler.add(str(o.get("color") or ""))
                for _, w, h in ph:
                    if isinstance(w, int) and isinstance(h, int) and (enk is None or w * h < enk[0] * enk[1]):
                        enk = (w, h)
                satir.append({"blueprint_id": bid, "baslik": bp.get("title") or a[bid].get("baslik") or YOK, "marka": bp.get("brand") or YOK,
                              "model": bp.get("model") or YOK, "teknik": tk, "teknik_kaynak": tk_k, "saglayici_id": pid,
                              "saglayici": p.get("title") or YOK, "konum": yer, "varyant_id": v.get("id"), "varyant": v.get("title") or YOK,
                              "boy": o.get("size") or YOK, "renk": o.get("color") or YOK,
                              "placeholder_px": "; ".join(f"{pos}={w}x{h}" for pos, w, h in ph) or YOK,
                              "stok": v.get("is_available") if v.get("is_available") is not None else YOK, "maliyet": YOK})
            if not vs:
                satir.append({"blueprint_id": bid, "baslik": bp.get("title") or YOK, "marka": bp.get("brand") or YOK,
                              "model": bp.get("model") or YOK, "teknik": tk, "teknik_kaynak": tk_k, "saglayici_id": pid,
                              "saglayici": p.get("title") or YOK, "konum": yer, "varyant_id": YOK, "varyant": YOK, "boy": YOK,
                              "renk": YOK, "placeholder_px": YOK, "stok": YOK, "maliyet": YOK})
            s1 = sozluk(jy(ham, f"bp_{bid}_pp_{pid}_shipping_v1.json"))
            sure = sozluk(s1.get("handling_time"))
            prof = liste(s1.get("profiles"))
            for ulke in ULKELER:
                pr = [x for x in prof if ulke in (x.get("countries") or [])]
                row = not pr
                pr = pr or [x for x in prof if "REST_OF_THE_WORLD" in (x.get("countries") or [])]
                ilk = [sozluk(x.get("first_item")) for x in pr]
                ek = [sozluk(x.get("additional_items")) for x in pr]
                c = lambda L: "-".join(f"{v / 100:g}" for v in sorted({i.get("cost") for i in L if isinstance(i.get("cost"), int)})) or YOK
                kargo.append({"blueprint_id": bid, "saglayici_id": pid, "kaynak": "v1", "ulke": ulke, "ilk_adet": c(ilk), "ek_adet": c(ek),
                              "para": ",".join(sorted({str(i.get("currency")) for i in ilk if i.get("currency")})) or YOK,
                              "teslim": f"hazirlik {sure.get('value')} {sure.get('unit')}" if sure else YOK,
                              "not": ("REST_OF_THE_WORLD profili" if row else "") if pr else ("profil yok" if not prof else "ulke profilde yok")})
            for f in sorted(ham.glob(f"bp_{bid}_pp_{pid}_shipping_v2_*.json")):
                yk = f.stem.split("shipping_v2_", 1)[1]
                ul = {}
                for d in liste(sozluk(jy(ham, f.name)).get("data")):
                    at = sozluk(d.get("attributes"))
                    cc = at.get("country")
                    cc = sozluk(cc).get("code") if isinstance(cc, dict) else cc
                    if cc not in ULKELER and cc != "REST_OF_THE_WORLD":
                        continue
                    sc = sozluk(at.get("shippingCost") or at.get("shipping_cost"))
                    fi, ai = sozluk(sc.get("firstItem") or at.get("firstItem")), sozluk(sc.get("additionalItems") or at.get("additionalItems"))
                    ht = sozluk(at.get("handlingTime") or at.get("handling_time"))
                    u = ul.setdefault(cc, {"ilk": set(), "ek": set(), "para": set(), "teslim": set()})
                    if fi.get("amount") is not None:
                        u["ilk"].add(fi.get("amount"))
                    if ai.get("amount") is not None:
                        u["ek"].add(ai.get("amount"))
                    if fi.get("currency"):
                        u["para"].add(str(fi.get("currency")))
                    if ht:
                        u["teslim"].add(f"{ht.get('from')}-{ht.get('to')}")
                for ulke in ULKELER:
                    u, row = ul.get(ulke), False
                    if not u and ul.get("REST_OF_THE_WORLD"):
                        u, row = ul["REST_OF_THE_WORLD"], True
                    yuz = lambda S_: "-".join(f"{v / 100:g}" for v in sorted(x for x in S_ if isinstance(x, (int, float)))) or YOK
                    kargo.append({"blueprint_id": bid, "saglayici_id": pid, "kaynak": f"v2:{yk}",
                                  "ulke": ulke, "ilk_adet": yuz(u["ilk"]) if u else YOK, "ek_adet": yuz(u["ek"]) if u else YOK,
                                  "para": ",".join(sorted(u["para"])) if u and u["para"] else YOK,
                                  "teslim": ("kargo suresi " + ",".join(sorted(u["teslim"])) + " gun") if u and u["teslim"] else YOK,
                                  "not": ("REST_OF_THE_WORLD" if row else "") if u else "veri yok"})
        us = [k for k in kargo if k["blueprint_id"] == bid and k["kaynak"] == "v1" and k["ulke"] == "US"]
        ozet.append({"id": bid, "baslik": bp.get("title") or a[bid].get("baslik") or YOK, "marka": bp.get("brand") or YOK,
                     "model": bp.get("model") or YOK, "teknik": tk, "teknik_kaynak": tk_k, "saglayici": saglayici,
                     "varyant": sum(1 for s in satir if s["blueprint_id"] == bid and s["varyant_id"] != YOK),
                     "boy": sorted(b for b in boylar if b), "renk": sorted(r for r in renkler if r),
                     "en_kucuk_ph": f"{enk[0]}x{enk[1]}" if enk else YOK,
                     "kargo_us": "; ".join(f"{k['saglayici_id']}: {k['ilk_adet']} (+{k['ek_adet']}) {k['para']}" for k in us) or YOK,
                     "neden": a[bid].get("neden")})
    SA = ["blueprint_id", "baslik", "marka", "model", "teknik", "teknik_kaynak", "saglayici_id", "saglayici", "konum", "varyant_id", "varyant",
          "boy", "renk", "placeholder_px", "stok", "maliyet"]
    KA = ["blueprint_id", "saglayici_id", "kaynak", "ulke", "ilk_adet", "ek_adet", "para", "teslim", "not"]
    for ad, al, v in (("KOLYE_KATALOG.csv", SA, satir), ("KOLYE_KARGO.csv", KA, kargo)):
        with open(cikti / ad, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=al)
            w.writeheader()
            w.writerows(v)
    L = ["# Printify kolye katalogu (salt okuma)", "",
         f"Kaynak: Printify katalog API (yalniz GET). Istek {len(ist)} (HTTP gonderim {sozluk(ist_j).get('http_gonderim', YOK)}). Aday {len(ozet)} (baslikta necklace / pendant + zorunlu {', '.join(map(str, ZORUNLU))}).",
         "Maliyet: API vermedi (Printify katalog API'si maliyet vermez; urun taslagi acip okumak bu iste yasak, ayri onay).",
         "Kargo v1 ve v2: ilk adet / ek adet (sent / 100; eski kupa okumasinda v1 ve v2 ayni deger, olcum). v1 'hazirlik' = handling_time; "
         "v2 'kargo suresi' = handlingTime from-to (ulkeye gore degisir). Ulke profili yoksa REST_OF_THE_WORLD (not sutunu).",
         "Teknik: decoration_methods alani varsa ondan, yoksa blueprint aciklamasindan; emin degilse 'belirsiz'.", ""]
    for o in ozet:
        L += [f"- **{o['id']} {o['baslik']}** ({o['marka']} / {o['model']}) | teknik {o['teknik']} ({o['teknik_kaynak']}) | maliyet {YOK}",
              f"  saglayici {len(o['saglayici'])}: {'; '.join(o['saglayici']) or YOK} | varyant {o['varyant']} | boy {', '.join(o['boy']) or YOK} | "
              f"renk {', '.join(o['renk'][:8]) or YOK}",
              f"  en kucuk baski alani {o['en_kucuk_ph']} px | kargo US v1: {o['kargo_us']}"]
    (cikti / "KOLYE_KATALOG.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    log(f"OZET printify | istek {len(ist)} | HTTP gonderim {sozluk(ist_j).get('http_gonderim', YOK)} | aday {len(ozet)}")
    log("OZET printify | blueprint | baslik | teknik | saglayici | en kucuk placeholder px")
    for o in ozet:
        log(f"OZET printify | {o['id']} | {o['baslik']} | {o['teknik']} | {len(o['saglayici'])} | {o['en_kucuk_ph']}")
    return 0 if ozet else 1


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("oku", "rapor"):
        sys.exit(__doc__)
    sys.exit(oku(Path(sys.argv[2])) if sys.argv[1] == "oku" else rapor(Path(sys.argv[2])))
