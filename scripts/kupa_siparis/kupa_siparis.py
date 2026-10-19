#!/usr/bin/env python3
"""Orchard kupa siparisi -> Printful baski dosyasi (Serdar 19 Eki 2026). Musteriye DOKUNMAZ, Printful'a GONDERMEZ.

Akis (her KUPA- transaction'i icin):
  1) Girdi: Etsy receipt (yalniz GET) ya da receipt JSON dosyasi (kuru deneme).
     SKU KUPA-<CIFT>-<01-08>-<11|15> (CIFT alfabetik, ornek CANCER_LIBRA; stil no = cift.py ST8 sirasi, 01 Orange Blossom).
     Kisisellestirme 3 satir: isim1, isim2, mesaj (mesaj bossa "My favorite place is with you").
     isim1 = ciftteki ILK burc (posterde sol), isim2 = ikinci burc (sag).
  2) Kapilar: isim <= 10 harf, mesaj <= 30 karakter, tum karakterler EB Garamond'da (isimler duz, mesaj italik),
     baski_kes isim/mesaj tasmasi False. Burc tasma isareti FAIL DEGIL (1,70 mm alt sinirda on gorunus 14 px payi dar);
     karar siparis stilinin baskisinda kontrol_burc olcumuyle (Serdar + kupa oturumu 19 Eki, ozet.py 0bbdac6):
     cakisma > 0 ya da dala < 1,1 mm FAIL; 1,1-1,2 mm GOZ (baski uretilir, Serdar onayi istenir); >= 1,2 mm PASS.
     Bir kapi FAIL ise baski yok; SORU.md (Serdar'a soru) yazilir. Burc alt sinir / < 1,95 mm yalniz bilgi notu.
  3) Cikti: <cikti>/<receipt>/<transaction>/ BASKI_*.png (11 oz 2700x1050 | 15 oz 2700x1140, 300 dpi),
     ONIZLEME_*.jpg, PRINTFUL_TASLAK.json (confirm=false yuku; GONDERILMEZ), OZET.json. --drive verilirse rclone ile Drive'a.
  Baski, kupa_orchard/kod/cift.py 1. ve 1b. bolumuyle birebir ayni cagridir (ayni girdi -> ayni piksel).
  kontrol_burc.py 8 stilin 11 oz dosyasini istedigi icin 8 stil paralel uretilir; kapi yalniz siparis stilinin satirina bakar.

Kullanim:
  python3 kupa_siparis.py --kod <kupa_orchard klasoru> --receipt-json <dosya> --cikti <klasor> [--drive gdrive:ASTROLOVE/SIPARIS_KUPA]
  python3 kupa_siparis.py --kod ... --receipt-id <no> --cikti ...      (ortam: ETSY_API_KEY, ETSY_SHARED_SECRET, ETSY_SHOP_ID, TOKEN_FILE)
Printful TASLAK gonderimi bu betikte YOK (ayri adim, yazilmadi): yalniz Serdar'in o receipt icin acik onayiyla, confirm=false.
Bagimlilik: numpy 2.5.3, pillow 12.3.0, scipy 1.18.1 (kupa-orchard78 ile ayni), fonttools.
"""
import argparse
import concurrent.futures as cf
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prodigi"))
from kisisel_siparis import _kisisel_alanlar  # noqa: E402

ZODYAK = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS", "CAPRICORN",
          "AQUARIUS", "PISCES"]
# cift.py ST8 ve RENKLER ile ayni sira/deger (kupa-orchard dali)
ST8 = [("orange", "Orange Blossom"), ("fig", "Purple Fig"), ("olive", "Olive Breeze"), ("pomegranate", "Pomegranate Bloom"),
       ("almond", "Almond Blossom"), ("lemon", "Lemon Grove"), ("grape", "Blue Grape"), ("loquat", "Golden Loquat")]
RENKLER = {"orange": "10,40,24", "fig": "52,18,48", "olive": "12,24,78", "pomegranate": "100,16,24", "almond": "52,22,14",
           "lemon": "12,22,76", "grape": "16,30,90", "loquat": "62,24,10"}
# Printful (proje belgesi KUPA_URETIM 17 Eki): 11 oz varyant 1320 printfile 43 2700x1050; 15 oz 4830 printfile 44 2700x1140
PRINTFUL = {"11": {"variant_id": 1320, "printfile_id": 43, "boyut": (2700, 1050)},
            "15": {"variant_id": 4830, "printfile_id": 44, "boyut": (2700, 1140)}}
SKU_RE = re.compile(r"^KUPA-([A-Z]+)_([A-Z]+)-(0[1-8])-(11|15)$")
VARSAYILAN_MESAJ = "My favorite place is with you"
ISIM_AZAMI, MESAJ_AZAMI = 10, 30
ISIM_IZINLI = " -'’."                 # harf disinda isimde izinli isaretler (harf sayisina girmez)
ENV = {"GOLGE_US": "0.4", "PARLA": "0.7"}   # cift.py ENV (baski_kes okumaz; birebirlik icin ayni)
DENEME_ENV = ("BURC_MIN",)            # yalniz kapi denemesi icin baski_kes'e gecer (OZET.json "deneme_ortam")
METIN_KAPI = ("isim1_uzunluk", "isim2_uzunluk", "isim1_isaret", "isim2_isaret", "mesaj_uzunluk", "karakter_ebgaramond")
t0 = time.time()


def log(m):
    print(f"[{time.time() - t0:5.1f}s] {m}", flush=True)


def piksel(p):
    """ozet.py ile ayni piksel ozeti (cozulmus RGB sha256, ilk 16)."""
    return hashlib.sha256(np.ascontiguousarray(np.asarray(Image.open(p).convert("RGB"))).tobytes()).hexdigest()[:16]


# ------------------------------------------------------------------ girdi
def receipt_oku(a):
    if a.receipt_json:
        return json.load(open(a.receipt_json, encoding="utf-8"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "etsy"))
    from etsy_common import Etsy, TokenStore, mask

    class SaltOkur(Etsy):
        def _call(self, method, path, **kw):
            if method != "GET":
                raise SystemExit(f"YASAK (salt okuma): {method} {path}")
            r = super()._call(method, path, **kw)
            if self.remaining is not None and int(self.remaining) < 10:     # kota tabani 10 (Serdar 15 Eki)
                raise SystemExit(f"DUR: kota {self.remaining} < 10")
            return r

    k, s = os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")
    mask(k)
    mask(s)
    store = TokenStore(os.environ["TOKEN_FILE"], k, s)
    if store.needs_refresh():
        store.refresh()
    return SaltOkur(store).get(f"/shops/{os.environ['ETSY_SHOP_ID']}/receipts/{a.receipt_id}")


def sku_coz(sku):
    m = SKU_RE.match((sku or "").strip())
    if not m:
        return None, f"SKU bicimi gecersiz: {sku!r}"
    b1, b2, no, boy = m.groups()
    if b1 not in ZODYAK or b2 not in ZODYAK:
        return None, f"bilinmeyen burc: {b1}_{b2}"
    if [b1, b2] != sorted([b1, b2]):
        return None, f"cift anahtari alfabetik degil: {b1}_{b2}"
    st, ad = ST8[int(no) - 1]
    return {"cift": f"{b1}_{b2}", "burc1": b1.title(), "burc2": b2.title(), "no": no, "stil": st, "stil_ad": ad,
            "boy": boy}, None


def metin_coz(t):
    alanlar = _kisisel_alanlar(t)
    if not alanlar:
        return None, "kisisellestirme yok"
    ham = html.unescape(alanlar[0][1]).replace("\r\n", "\n").replace("\r", "\n")
    satirlar = [x.strip() for x in ham.split("\n")]
    while satirlar and not satirlar[-1]:
        satirlar.pop()
    if len(satirlar) < 2 or not satirlar[0] or not satirlar[1]:
        return None, f"en az 2 satir (isim1, isim2) gerekli: {ham!r}"
    if len(satirlar) > 3:
        return None, f"3 satirdan fazla: {ham!r}"
    mesaj = satirlar[2] if len(satirlar) == 3 and satirlar[2] else VARSAYILAN_MESAJ
    return {"isim1": satirlar[0], "isim2": satirlar[1], "mesaj": mesaj, "mesaj_bos": mesaj == VARSAYILAN_MESAJ and
            (len(satirlar) < 3 or not satirlar[2]), "ham": ham}, None


# ------------------------------------------------------------------ kapilar
def karakter_kapisi(kod, m):
    fnt = Path(kod) / "varlik" / "font"
    duz = TTFont(fnt / "EBGaramond[wght].ttf").getBestCmap()
    ita = TTFont(fnt / "EBGaramond-Italic[wght].ttf").getBestCmap()
    # on yuz isimleri BUYUK harf, imza "isim1 & isim2" oldugu gibi (duz); mesaj italik
    eksik = sorted({c for c in m["isim1"] + m["isim2"] + m["isim1"].upper() + m["isim2"].upper() + "&·"
                    if not c.isspace() and ord(c) not in duz}
                   | {c for c in m["mesaj"] if not c.isspace() and ord(c) not in ita})
    return not eksik, eksik


def metin_kapilari(kod, m):
    k = {}
    for i in ("isim1", "isim2"):
        s = m[i]
        harf = sum(c.isalpha() for c in s)
        diger = sorted({c for c in s if not c.isalpha() and c not in ISIM_IZINLI})
        k[f"{i}_uzunluk"] = ("PASS" if harf <= ISIM_AZAMI else "FAIL", f"{s!r} {harf} harf (azami {ISIM_AZAMI})")
        if diger:
            k[f"{i}_isaret"] = ("FAIL", f"harf disi karakter {diger}")
    k["mesaj_uzunluk"] = ("PASS" if len(m["mesaj"]) <= MESAJ_AZAMI else "FAIL",
                          f"{len(m['mesaj'])} karakter (azami {MESAJ_AZAMI})")
    ok, eksik = karakter_kapisi(kod, m)
    k["karakter_ebgaramond"] = ("PASS" if ok else "FAIL", "tamam" if ok else f"fontta yok: {eksik}")
    return k


# ------------------------------------------------------------------ baski (cift.py 1 ve 1b ile ayni cagri)
def baski_kes(kod, st, sem, m, s, cikti, d_in=None):
    env = dict(ENV, PATH=os.environ.get("PATH", "/usr/bin:/bin"))
    env.update({k: os.environ[k] for k in DENEME_ENV if k in os.environ})
    if d_in:
        env["D_IN"] = d_in
    k = Path(kod) / "kod"
    r = subprocess.run([sys.executable, "-I", str(k / "baski_kes.py"), str(Path(kod) / "varlik" / "kes" / (st.upper() + "R")),
                        sem, m["isim1"], m["isim2"], s["burc1"], s["burc2"], m["mesaj"], RENKLER[st], cikti],
                       capture_output=True, text=True, env=env, cwd=str(k))
    if r.returncode:
        raise RuntimeError(f"baski_kes {st}: {r.stderr[-800:]}")
    return [ln.split("] ", 1)[1] for ln in r.stdout.splitlines() if ("on:" in ln or "arka:" in ln or "tasma" in ln)]


def tasma_oku(satirlar):
    t = next((x for x in satirlar if "tasma:" in x), "")
    m = re.search(r"tasma: isim (\w+), burc (\w+), mesaj (\w+)", t)
    burc = re.search(r"burc cap ([\d.]+) mm", " ".join(satirlar))
    return (dict(zip(("isim", "burc", "mesaj"), m.groups())) if m else None), (float(burc.group(1)) if burc else None)


def is_isle(kod, sem, s, m, d):
    """8 stil 11 oz (kontrol_burc girdisi) + siparis 15 oz ise 1b. Doner: kapilar, bilgi notlari, baski_kes satirlari."""
    (d / "baski").mkdir(parents=True, exist_ok=True)
    kap, notlar = {}, []
    with cf.ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        isler = {st: ex.submit(baski_kes, kod, st, sem, m, s, str(d / "baski" / f"B_{st}")) for st, _ in ST8}
        if s["boy"] == "15":
            is15 = ex.submit(baski_kes, kod, s["stil"], sem, m, s, str(d / "baski" / f"T15_{s['stil']}"), "3.35")
        olcum = {st: f.result() for st, f in isler.items()}
        o15 = is15.result() if s["boy"] == "15" else None
    log(f"8 stil 11 oz{' + 15 oz' if o15 else ''} baski tamam")
    sat = o15 if o15 else olcum[s["stil"]]
    tasma, burc_mm = tasma_oku(sat)
    kap["baski_tasma"] = ("PASS" if tasma and tasma["isim"] == tasma["mesaj"] == "False" else "FAIL",
                          f"isim {tasma and tasma['isim']}, mesaj {tasma and tasma['mesaj']}")
    if tasma and tasma["burc"] == "True":
        notlar.append("burc alt sinirda (on gorunus payi dar); karar kontrol_burc olcumu")
    if burc_mm is not None and burc_mm < 1.95 - 1e-6:
        notlar.append(f"burc {burc_mm:.2f} mm < 1,95")
    # kontrol_burc.py (degistirilmeden): siparisin isim ve mesaji AYNEN
    r = subprocess.run([sys.executable, "-I", str(Path(kod) / "kod" / "kontrol_burc.py"), str(d), s["burc1"], s["burc2"], sem,
                        m["isim1"], m["isim2"], m["mesaj"]], capture_output=True, text=True,
                       env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    if r.returncode:
        kap["kontrol_burc"] = ("FAIL", f"kontrol_burc hata: {r.stderr[-400:]}")
    else:
        satir = next((x for x in (d / "kontrol" / "burc_mesafe.txt").read_text().splitlines() if x.split()[0] == s["stil"]), "")
        cak = int(satir.split("cakisma px ")[1].split(",")[0])
        dal = float(satir.split("dala en kisa ")[1].split(" mm")[0])
        kap["kontrol_burc"] = ("FAIL" if cak or dal < 1.1 else "GOZ" if dal < 1.2 else "PASS",
                               f"dala {dal:.2f} mm, cakisma {cak} px")
    log(f"kontrol_burc: {kap['kontrol_burc']}")
    return kap, notlar, sat


def cikti_yaz(d, s, ad):
    """Siparis stilinin baski dosyasini Printful boyutunda yazar (15 oz: cift.py 1b, dikeyde ortalayarak 2700x1140)."""
    b = d / "baski"
    if s["boy"] == "11":
        png = d / f"BASKI_{ad}_11oz_2700x1050.png"
        shutil.copyfile(b / f"B_{s['stil']}_baski_11oz.png", png)
        oniz = b / f"B_{s['stil']}_onizleme.jpg"
    else:
        a = np.asarray(Image.open(b / f"T15_{s['stil']}_baski_11oz.png").convert("RGB"))
        t = np.full((1140, 2700, 3), 255, np.uint8)
        t[45:45 + 1050] = a
        png = d / f"BASKI_{ad}_15oz_2700x1140.png"
        Image.fromarray(t).save(png, dpi=(300, 300))
        oniz = b / f"T15_{s['stil']}_onizleme.jpg"
    jpg = d / f"ONIZLEME_{ad}_{s['boy']}oz.jpg"
    shutil.copyfile(oniz, jpg)
    w, h = Image.open(png).size
    assert (w, h) == PRINTFUL[s["boy"]]["boyut"], f"boyut {w}x{h} != {PRINTFUL[s['boy']]['boyut']}"
    return png, jpg


def printful_yuk(rc, t, s, png):
    """Printful POST /orders?confirm=false govdesi. GONDERILMEZ. E-posta/telefon BILEREK yok (Printful aliciya
    bildirim gondermesin). Dosya URL'si Serdar onayi aninda gonderim adiminda doldurulur."""
    p = PRINTFUL[s["boy"]]
    return {"_confirm": False, "_gonderildi": False,
            "external_id": f"{rc.get('receipt_id')}-{t.get('transaction_id')}",
            "recipient": {"name": rc.get("name"), "address1": rc.get("first_line"), "address2": rc.get("second_line") or "",
                          "city": rc.get("city"), "state_code": rc.get("state") or "", "zip": rc.get("zip"),
                          "country_code": rc.get("country_iso")},
            "items": [{"variant_id": p["variant_id"], "quantity": int(t.get("quantity") or 1),
                       "external_id": str(t.get("transaction_id")), "name": t.get("title", "")[:100],
                       "files": [{"type": "default", "url": None, "_yerel": png.name}],
                       "_printfile_id": p["printfile_id"], "_boyut": "x".join(map(str, p["boyut"]))}]}


def musteri_mesaji(kap):
    """Musterinin metni duzeltmesi gereken FAIL (metin kapisi)."""
    return any(v[0] == "FAIL" for k, v in kap.items() if k in METIN_KAPI)


def soru_yaz(d, rc, t, kap, sebep=None, musteri=False):
    sat = [f"# Serdar'a soru: receipt {rc.get('receipt_id')} transaction {t.get('transaction_id')}", "",
           f"SKU: {t.get('sku')}", "Baski URETILMEDI (kapi FAIL). Musteriye yazilmadi; karar Serdar'in.", ""]
    if musteri:
        sat += ["MUSTERI MESAJI GEREKIYOR: metin kurala uymuyor. Mesaj yalniz TASLAK olarak hazirlanir;",
                "gonderim yalniz Serdar'in bu siparise ozel acik onayiyla.", ""]
    if sebep:
        sat.append(f"- girdi: {sebep}")
    sat += [f"- {k}: {v[0]} ({v[1]})" for k, v in kap.items() if v[0] == "FAIL"]
    (d / "SORU.md").write_text("\n".join(sat) + "\n", encoding="utf-8")


def drive_yaz(d, hedef, rid):
    r = subprocess.run(["rclone", "copy", str(d), f"{hedef}/{rid}/{d.name}", "-q", "--include", "BASKI_*.png",
                        "--include", "ONIZLEME_*.jpg", "--include", "PRINTFUL_TASLAK.json", "--include", "OZET.json",
                        "--include", "SORU.md", "--include", "kontrol/burc_mesafe.txt"], capture_output=True, text=True)
    return r.returncode == 0, r.stderr[-300:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kod", required=True, help="kupa-orchard dalindaki kupa_orchard klasoru")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--receipt-json")
    g.add_argument("--receipt-id")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--drive", help="rclone hedefi, ornek gdrive:ASTROLOVE/SIPARIS_KUPA")
    a = ap.parse_args()
    kod = str(Path(a.kod).resolve())
    rc = receipt_oku(a)
    rid = str(rc.get("receipt_id"))
    kupa = [t for t in rc.get("transactions") or [] if str(t.get("sku") or "").startswith("KUPA-")]
    log(f"receipt {rid}: {len(kupa)} kupa kalemi")
    genel = []
    for i, t in enumerate(kupa, 1):
        d = Path(a.cikti).resolve() / rid / str(t.get("transaction_id"))
        d.mkdir(parents=True, exist_ok=True)
        ozet = {"receipt_id": rid, "transaction_id": t.get("transaction_id"), "sku": t.get("sku"), "kapilar": {}, "notlar": [],
                "deneme_ortam": {k: os.environ[k] for k in DENEME_ENV if k in os.environ}}
        s, hata = sku_coz(t.get("sku"))
        m, hata2 = metin_coz(t) if s else (None, None)
        if hata or hata2:
            ozet.update(durum="FAIL", sebep=hata or hata2, musteri_mesaji_gerekiyor=bool(hata2))
            soru_yaz(d, rc, t, {}, hata or hata2, musteri=bool(hata2))
        else:
            ozet.update(sku_coz=s, metin={k: m[k] for k in ("isim1", "isim2", "mesaj", "mesaj_bos")})
            kap = metin_kapilari(kod, m)
            if all(v[0] == "PASS" for v in kap.values()):
                sem = d / "sembol"
                r = subprocess.run(["bash", str(Path(kod) / "kod" / "sembol_al.sh"), s["cift"], str(sem)],
                                   capture_output=True, text=True, cwd=kod)
                if r.returncode:
                    kap["sembol"] = ("FAIL", r.stderr[-300:])
                else:
                    k2, notlar, sat = is_isle(kod, str(sem), s, m, d)
                    kap.update(k2)
                    ozet["notlar"], ozet["baski_kes"] = notlar, sat
            ozet["kapilar"] = {k: {"durum": v[0], "ayrinti": v[1]} for k, v in kap.items()}
            if all(v[0] != "FAIL" for v in kap.values()):
                ad = f"AstroLoveArt_{s['burc1']}_{s['burc2']}_{s['stil_ad'].replace(' ', '_')}"
                png, jpg = cikti_yaz(d, s, ad)
                yuk = printful_yuk(rc, t, s, png)
                (d / "PRINTFUL_TASLAK.json").write_text(json.dumps(yuk, indent=1, ensure_ascii=False), encoding="utf-8")
                ozet.update(durum="GOZ" if any(v[0] == "GOZ" for v in kap.values()) else "PASS", baski=png.name, onizleme=jpg.name,
                            piksel=piksel(png), printful={"variant_id": PRINTFUL[s["boy"]]["variant_id"],
                                                          "printfile_id": PRINTFUL[s["boy"]]["printfile_id"]})
            else:
                ozet.update(durum="FAIL", musteri_mesaji_gerekiyor=musteri_mesaji(kap))
                soru_yaz(d, rc, t, kap, musteri=ozet["musteri_mesaji_gerekiyor"])
        if a.drive:
            ok, err = drive_yaz(d, a.drive, rid)
            ozet["drive"] = "tamam" if ok else f"HATA {err}"
        (d / "OZET.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False), encoding="utf-8")
        genel.append(ozet)
        g_ = time.time() - t0
        log(f"[{i}/{len(kupa)} %{100 * i // len(kupa)}] {t.get('sku')} -> {ozet['durum']} {ozet.get('piksel', '')} "
            f"{'; '.join(ozet['notlar'])} (gecen {g_:.0f}s, kalan ~{g_ / i * (len(kupa) - i):.0f}s)")
    (Path(a.cikti).resolve() / rid / "OZET.json").write_text(json.dumps(genel, indent=1, ensure_ascii=False), encoding="utf-8")
    sys.exit(1 if any(o["durum"] == "FAIL" for o in genel) else 0)


if __name__ == "__main__":
    main()
