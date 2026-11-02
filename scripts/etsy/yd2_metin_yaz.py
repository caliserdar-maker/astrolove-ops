#!/usr/bin/env python3
"""YD (1st Anniversary) 2. ASAMA metin yazimi (Serdar 2 Kas "ok"; Merkez GOREV YD2-YUKLE madde 5). Yalniz EN baslik + aciklama;
RU / ceviriye dokunulmaz (Lena onayindan sonra ayri is). Gece taslagi docs/yd2/CANCER_LIBRA_METIN_TASLAK.txt KULLANILMAZ.

Degisiklik (birebir, onayli 31 Eki D1-D6): her ESKI parca canli aciklamada TAM 1 kez bulunmali, YENI ile degisir; 0 ya da 2+
eslesmede o ilanin metni YAZILMAZ (rapor). Baslik: yalniz "Paper Anniversary Card" -> "Paper Anniversary Gift" (tam 1 kez); baslikta
yoksa baslik degismez (rapor), 2+ ise ilan yazilmaz.
Kapilar (yazimdan ONCE, yeni metin): "5x7", "8x10", "Digital card", "Shipped print", "card" (kelime, buyuk / kucuk harf) yok; "5 x 7"
yalniz SIZES satirinda; uzun / orta tire yok; etsy_common.RU_YASAK (kagit / omur / OBA ... yasaklari) yok; AI beyani var (ortak kapi
Etsy._call ayrica denetler). Kaynak kapisi: canli aciklama (html.unescape, CRLF -> LF) = 26 Eki yedegi (--ham <lid>.json) ile ayni;
degilse KAYMA (yazim yok). Kisi adi: canli metindeki ornek isimler (Emma, James; 26 Eki'den beri canli, D1-D6 dokunmaz) BILGI olarak
raporlanir (Merkez kapisi "kisi adi yok"; Serdar karari pilot raporunda).
updateListing bir TASLAGI yayina alir (CLAUDE.md 7 Eyl): yazmadan once state okunur, yalniz active ilana yazilir, sonra geri okunur
(state active, baslik + aciklama beklenen). Geri okuma tutmazsa otomatik geri alma (yedekteki eski baslik + aciklama, etsy_common
geri_alma_izni sha kapisi) ve kosu durur.
Modlar: kontrol (SALT OKUMA, ilan basina 1 GET) | yaz (--onay SERDAR_YD2_METIN; ilan basina 3: GET + PATCH + GET; AI beyan kapisi
yayin denetimi eklerse +1) | geri-al (--onay SERDAR_YD2_METIN_GERI_AL; --yedek-dir YEDEK_METIN_<lid>.json).
Kota: KOTA_SINIRI 10 (etsy_common); ilana baslamadan kalan >= ILAN_UST + KOTA_SINIRI.
Cikti <out>: SONUC.json, SONUC.csv, YENI_<lid>.txt (yeni metin), YEDEK_METIN_<lid>.json (eski baslik + aciklama + sha)."""
import argparse
import csv
import html
import json
import os
import pathlib
import re
import sys
import time
import traceback

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402

ONAY = {"yaz": "SERDAR_YD2_METIN", "geri-al": "SERDAR_YD2_METIN_GERI_AL"}
ILAN_UST = 1 + 1 + 1 + 1 + 1 + 1     # GET + PATCH + GET (+ yayin beyan GET) + geri alma PATCH + GET
D = [
    ("D1", "1. Choose your style and your format.", "1. Choose your style, your format and your size."),
    ("D2", ' The card always says "Happy First Anniversary".', ""),
    ("D3", "- Digital card and digital file: sent in Etsy Messages as soon as you approve your preview.",
     "- Digital File: sent to you as a download link via Etsy Messages as soon as you approve your preview."),
    ("D4", "- Shipped print: made and shipped within 4 to 7 days after your approval, with free shipping worldwide. Estimated delivery: "
           "US 3 to 8 days, UK and Australia 5 to 10 days, EU 5 to 12 days, other countries 7 to 21 days.",
     "- Print: made and shipped within 4 to 7 days after your approval, with free shipping worldwide. You can see the estimated "
     "delivery time for your country at checkout."),
    ("D5", "FORMATS\n- Digital card 5x7: a single-sided flat card sent as a digital file, to print at home or at a print shop. Nothing is "
           "shipped.\n- Digital file 8x10: an 8x10 inch, 300 dpi JPG for your own printing. Nothing is shipped.\n- Shipped print 8x10: "
           "printed on premium matte art paper with long-lasting inks and shipped to you by our production partner.",
     "FORMATS\n- Digital File: one print ready 300 dpi JPG in the style and size you choose, for your own printing. Nothing is "
     "shipped.\n- Print: printed on matte art paper and shipped to you unframed by our production partner.\n\nSIZES\n14 sizes, from "
     "5 x 7 to 24 x 36 inches, plus A4 to A2. Every style and size comes as a print or a digital file."),
    ("D6", "Print your card at home or at a print shop and give a paper gift made only for the two of you.",
     "A print of your two signs, your names and your date is a paper gift made only for the two of you."),
]
BASLIK = ("Paper Anniversary Card", "Paper Anniversary Gift")
SIZES_SATIR = "14 sizes, from 5 x 7 to 24 x 36 inches, plus A4 to A2. Every style and size comes as a print or a digital file."
YASAK = [("5x7", re.compile(r"5x7")), ("8x10", re.compile(r"8x10")), ("Digital card", re.compile(r"digital card", re.I)),
         ("Shipped print", re.compile(r"shipped print", re.I)), ("card", re.compile(r"\bcards?\b", re.I)),
         ("tire", re.compile("[–—]"))]
ORNEK_ISIM = re.compile(r"\b(Emma|James)\b")


class Kayma(Exception):
    pass


class Fail(Exception):
    pass


def norm(t):
    return html.unescape(t or "").replace("\r\n", "\n").strip()


def donustur(desc, title):
    """-> (yeni_desc, yeni_title, notlar, neden). neden bos degilse yazilmaz."""
    neden, notlar = [], []
    y = desc
    for ad, eski, yeni in D:
        n = y.count(eski)
        if n != 1:
            neden.append(f"{ad} eslesme {n} (1 beklenir)")
            continue
        y = y.replace(eski, yeni)
    nb = title.count(BASLIK[0])
    if nb == 0:
        yt = title; notlar.append("baslikta 'Paper Anniversary Card' yok; baslik degismedi")
    elif nb == 1:
        yt = title.replace(*BASLIK)
    else:
        yt = title; neden.append(f"baslikta 'Paper Anniversary Card' {nb} kez")
    if not neden:
        for ad, rx in YASAK:
            if rx.search(y):
                neden.append(f"sonuc metninde yasak: {ad}")
            if rx.search(yt):
                neden.append(f"sonuc basliginda yasak: {ad}")
        s57 = [ln for ln in y.split("\n") if "5 x 7" in ln]
        if s57 != [SIZES_SATIR]:
            neden.append(f"'5 x 7' SIZES satiri disinda ({len(s57)} satir)")
        if E.RU_YASAK.search(y) or E.RU_YASAK.search(yt):
            neden.append("sonuc metninde etsy_common.RU_YASAK ifadesi")
        if not E.beyan_var(y, "en"):
            neden.append("sonuc metninde AI beyani yok")
        if ORNEK_ISIM.search(y):
            notlar.append("BILGI: ornek isimler (Emma, James) canli metinde var; D1-D6 dokunmaz")
    return y, yt, notlar, neden


def ilan_isle(api, shop, lid, ham_dir, out, mod):
    R = dict(listing_id=lid, sonuc="", neden="", notlar="", istek_once=api.calls, baslik_degisti=False)
    try:
        if mod != "kontrol" and api.remaining is not None and api.remaining < ILAN_UST + E.KOTA_SINIRI:
            R.update(sonuc="KOTA", neden=f"kalan {api.remaining} < {ILAN_UST + E.KOTA_SINIRI}"); return R
        L = api.get(f"/listings/{lid}") or {}
        st, d0, t0 = L.get("state"), norm(L.get("description")), html.unescape(L.get("title") or "")
        R.update(state_once=st)
        if mod == "geri-al":
            yd = json.loads((pathlib.Path(ham_dir) / f"YEDEK_METIN_{lid}.json").read_text(encoding="utf-8"))
            if st != "active":
                raise Kayma(f"state {st}")
            E.geri_alma_izni(lid, yd["description"], yd["description_sha"])
            api.patch(f"/shops/{shop}/listings/{lid}", {"title": yd["title"], "description": yd["description"]})
            L1 = api.get(f"/listings/{lid}") or {}
            ok = L1.get("state") == "active" and norm(L1.get("description")) == norm(yd["description"])
            R.update(sonuc="GERI_ALINDI" if ok else "FAIL", neden="" if ok else "geri alma okumasi tutmadi"); return R
        hp = pathlib.Path(ham_dir) / f"{lid}.json"
        h = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}
        dh = norm((h.get("listing") or {}).get("description"))
        if not dh:
            raise Kayma("26 Eki yedeginde aciklama yok")
        if d0 != dh:
            raise Kayma("canli aciklama 26 Eki yedeginden farkli")
        yeni, yt, notlar, neden = donustur(d0, t0)
        R["notlar"] = "; ".join(notlar)
        (out / f"YENI_{lid}.txt").write_text(f"{yt}\n\n{yeni}\n", encoding="utf-8")
        if neden:
            R.update(sonuc="BLOK", neden="; ".join(neden)); return R
        if st != "active":
            raise Kayma(f"state {st} (yalniz active ilana yazilir; updateListing taslagi yayina alir)")
        if mod == "kontrol":
            R.update(sonuc="PLAN", baslik_degisti=yt != t0); return R
        (out / f"YEDEK_METIN_{lid}.json").write_text(json.dumps(dict(listing_id=lid, title=t0, description=d0,
                                                                     description_sha=E.ozet(d0)), ensure_ascii=False, indent=1),
                                                     encoding="utf-8")
        govde = {"description": yeni}
        if yt != t0:
            govde["title"] = yt
        R["yazildi"] = sorted(govde)   # inceleme O2: PATCH'ten ONCE (5xx / zaman asimi: Etsy uygulamis olabilir -> geri alma denenir)
        api.patch(f"/shops/{shop}/listings/{lid}", govde)
        L1 = api.get(f"/listings/{lid}") or {}
        if L1.get("state") != "active":
            raise Fail(f"yazim sonrasi state {L1.get('state')}")
        if norm(L1.get("description")) != norm(yeni):
            raise Fail("geri okuma: aciklama beklenen degil")
        if html.unescape(L1.get("title") or "") != yt:
            raise Fail("geri okuma: baslik beklenen degil")
        R.update(sonuc="TAMAM", baslik_degisti=yt != t0)
    except Kayma as e:
        R.update(sonuc="KAYMA", neden=str(e)[:300])
    except (Exception, SystemExit) as e:   # noqa: BLE001  (HTTP / kota tabani / beyan kapisi)
        R.update(sonuc="FAIL", neden=f"{type(e).__name__}: {str(e)[:300]}", iz=traceback.format_exc()[-800:])
        yp = out / f"YEDEK_METIN_{lid}.json"
        if mod == "yaz" and R.get("yazildi") and yp.exists():
            try:
                yd = json.loads(yp.read_text(encoding="utf-8"))
                E.geri_alma_izni(lid, yd["description"], yd["description_sha"])
                api.patch(f"/shops/{shop}/listings/{lid}", {"title": yd["title"], "description": yd["description"]})
                L2 = api.get(f"/listings/{lid}") or {}
                R["geri_alma"] = "TAMAM" if norm(L2.get("description")) == norm(yd["description"]) else "OKUMA TUTMADI"
            except (Exception, SystemExit) as e2:   # noqa: BLE001
                R["geri_alma"] = f"FAIL {type(e2).__name__}: {str(e2)[:200]}"
    R.update(istek=api.calls - R.pop("istek_once"), kota_sonra=api.remaining)
    return R


def calis(api, shop, a, out):
    ids = [x for x in a.sadece.split(",") if x]
    haric = {x for x in a.haric.split(",") if x}
    yd78 = [r["listing_id"] for r in csv.DictReader(open(a.liste, encoding="utf-8-sig"))]
    if set(ids) - set(yd78):
        raise SystemExit(f"DUR: YD listesinde olmayan ilan {sorted(set(ids) - set(yd78))}")
    sec = [x for x in (ids or yd78) if x not in haric]
    if a.mod == "geri-al" and not ids:   # inceleme O4: yalniz YEDEK_METIN dosyasi olan ilanlar
        var = {p.stem.split("_")[-1] for p in pathlib.Path(a.yedek_dir).glob("YEDEK_METIN_*.json")}
        sec = [x for x in sec if x in var]
    sonuc, t0, fail_seri = [], time.time(), 0
    for i, lid in enumerate(sec, 1):
        r = ilan_isle(api, shop, lid, a.ham_dir if a.mod != "geri-al" else a.yedek_dir, out, a.mod)
        sonuc.append(r)
        gec = time.time() - t0
        print(f"[{i}/{len(sec)}] %{100 * i // len(sec)} {lid} {r['sonuc']} {r.get('neden', '')} | istek {api.calls} kota {api.remaining} | "
              f"gecen {gec:.0f} sn kalan ~{gec / i * (len(sec) - i):.0f} sn", flush=True)
        fail_seri = fail_seri + 1 if r["sonuc"] in ("FAIL", "BLOK", "KAYMA") else 0
        # inceleme O1: yazan modda her FAIL'de kosu durur (otomatik geri alma TAMAM olsa da); O3: kontrol modu 78'in hepsini tarar
        if r["sonuc"] == "KOTA" or (a.mod != "kontrol" and (r["sonuc"] == "FAIL" or fail_seri >= 3)):
            break
    say = {}
    for r in sonuc:
        say[r["sonuc"]] = say.get(r["sonuc"], 0) + 1
    oz = dict(mod=a.mod, secilen=len(sec), sayim=say, istek=api.calls, kota_son=api.remaining, kota_siniri=E.KOTA_SINIRI,
              yapilmadi=[x for x in sec if x not in {r["listing_id"] for r in sonuc}])
    (out / "SONUC.json").write_text(json.dumps(dict(ozet=oz, ilanlar=sonuc), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    with open(out / "SONUC.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["listing_id", "sonuc", "baslik_degisti", "state_once", "istek", "kota_sonra", "geri_alma", "neden", "notlar"])
        for r in sonuc:
            w.writerow([r["listing_id"], r["sonuc"], r.get("baslik_degisti"), r.get("state_once"), r.get("istek"), r.get("kota_sonra"),
                        r.get("geri_alma", ""), r.get("neden", ""), r.get("notlar", "")])
    print(f"::notice::YD2 METIN {a.mod}: {say} | istek {api.calls} | kota {api.remaining}", flush=True)
    iyi = {"kontrol": {"PLAN"}, "yaz": {"TAMAM"}, "geri-al": {"GERI_ALINDI"}}[a.mod]
    return 0 if sonuc and all(r["sonuc"] in iyi for r in sonuc) and len(sonuc) == len(sec) else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mod", required=True, choices=["kontrol", "yaz", "geri-al"])
    ap.add_argument("--ham-dir", default="", help="26 Eki okuma yedegi HAM/<lid>.json (kaynak kapisi)")
    ap.add_argument("--yedek-dir", default="", help="geri-al: YEDEK_METIN_<lid>.json klasoru")
    ap.add_argument("--liste", default=str(KOK.parents[1] / "data/pod/yd78_ids.csv"))
    ap.add_argument("--sadece", default=""); ap.add_argument("--haric", default="")
    ap.add_argument("--onay", default=""); ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.mod in ONAY and a.onay != ONAY[a.mod]:
        raise SystemExit(f"DUR: {a.mod} icin --onay {ONAY[a.mod]}")
    if a.mod == "geri-al" and not a.yedek_dir:
        raise SystemExit("DUR: geri-al icin --yedek-dir")
    if a.mod != "geri-al" and not a.ham_dir:
        raise SystemExit("DUR: --ham-dir (26 Eki yedegi) gerekli")
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    E.mask(k); E.mask(s)
    store = E.TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    return calis(E.Etsy(store), os.environ["ETSY_SHOP_ID"], a, out)


if __name__ == "__main__":
    sys.exit(main())
