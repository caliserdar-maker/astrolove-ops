#!/usr/bin/env python3
"""KOLYE RAKIP ORNEKLEMI (Serdar 9 Kas 2026: "pet simdilik iptal, kolye istiyorum" + "ok"). SALT OKUMA, Etsy'ye yazma YOK.
Yalniz API anahtari (APIKeyStore; OAuth token indirilmez / yenilenmez), yalniz GET (SaltOkur: GET disi her istek SystemExit).

ornament_pazar.py akisinin AYNISI (o dosya DEGISMEZ; burada import edilir, IFADELER ve rapor modul duzeyinde uzerine yazilir):
kota kapisi (kalan - BUTCE >= ALT, BUTCE 80, ALT 500), 6 arama, tekillestirme, ilk 40 batch + getShop, ilk 20 yorum, TEMAS.jpg.
Bu veri TALEP OLCUMU DEGILDIR: arama sonucundaki rakip ilanlarin orneklemidir. Etsy ilan basina satis adedi vermez; "magaza
toplami" magazanin tum ilanlarinin toplam satisidir. Raporda "en cok satan" iddiasi yoktur.

Kullanim: kolye_pazar.py --out KLASOR   (ortam: ETSY_API_KEY, ETSY_SHARED_SECRET)
Cikti: ILANLAR.csv, ILK20.csv, TEMAS.jpg (ic inceleme), OZET.json, RAPOR_TASLAK.md ("# Kolye rakip orneklemi").
Log ozeti (son satirlar, ilan / musteri verisi yok): ifade basi eslesen, tekil ilan, istek, kota bas/son, fiyat ortancasi.
Kimlik suzgeci (Serdar 9 Kas): main() stdout / stderr'i KimlikSuz'den gecirir; ornament_pazar hata satirlari ve traceback'teki
rakip ilan / magaza kimlikleri '<id>' olur ('/listings/<id>', '/shops/<id>', 'listing_ids=<id>', 'shop_id <id>',
'Listing <id>', 9-12 haneli sayi; 10 haneli epoch zaman da '<id>' olur, bilerek).
'::add-mask::' satiri DEGISMEZ (runner maskelesin). Dosyaya yazim is akisinda scripts/guvenlik/sir_koru.py tee ile."""
import argparse
import csv
import json
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import ornament_pazar as OP  # noqa: E402

IFADELER = ["zodiac necklace", "zodiac couple necklace", "couples necklace", "matching couple necklaces",
            "personalized zodiac necklace", "constellation necklace"]
BASLIK = "# Kolye rakip orneklemi"
UYARI = ("Bu tablo TALEP olcumu degildir: Etsy arama sonucundaki rakip ilanlarin orneklemidir (Marketplace Insights olcumu yok). "
         "Etsy ilan basina satis adedi vermez; 'magaza toplami' magazanin TUM ilanlarinin toplam satisidir. 'En cok satan' iddiasi yoktur.")


class SaltOkur(E.Etsy):
    """GET disi her istek calisma aninda SystemExit (emsal yayina_hazir.py SaltOkur)."""
    def _call(self, method, path, **kw):
        if str(method).upper() != "GET":
            raise SystemExit(f"YASAK (salt okuma): {method} {path}")
        return super()._call(method, path, **kw)

    def post_file(self, path, *a, **k):
        raise SystemExit(f"YASAK (salt okuma): POST(file) {path}")


KIMLIK_RX = [(re.compile(r"/(listings|shops)/\d+"), r"/\1/<id>"),
             (re.compile(r"(listing_ids=)[0-9,%Cc]+"), r"\1<id>"),
             (re.compile(r"(?i)\b((?:listing|shop|user)(?:_id)?[\"']?\s*[=: ]\s*)\d{5,12}\b"), r"\1<id>"),
             (re.compile(r"(?<![\w.])\d{9,12}(?!\w|\.\d)"), "<id>")]


def kimlik_suz(satir):
    """Rakip ilan / magaza kimligini '<id>' yapar; '::add-mask::' satirina dokunmaz."""
    if "::add-mask::" in satir:
        return satir
    for rx, yeni in KIMLIK_RX:
        satir = rx.sub(yeni, satir)
    return satir


class KimlikSuz:
    """Akis sarmalayici: satir satir kimlik_suz (yarim satir tamponda bekler)."""
    def __init__(self, akis):
        self.akis, self.tampon = akis, ""

    def write(self, s):
        self.tampon += s
        *tam, self.tampon = self.tampon.split("\n")
        for x in tam:
            self.akis.write(kimlik_suz(x) + "\n")
        return len(s)

    def flush(self):
        if self.tampon:
            self.akis.write(kimlik_suz(self.tampon))
            self.tampon = ""
        self.akis.flush()

    def __getattr__(self, ad):
        return getattr(self.akis, ad)


def _sayi(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def dagilim(degerler):
    """-> {n, en_dusuk, c1, ortanca, c3, en_yuksek}; n < 2 ise yalniz olan."""
    d = sorted(v for v in (_sayi(x) for x in degerler) if v is not None)
    if not d:
        return {"n": 0}
    if len(d) == 1:
        return {"n": 1, "en_dusuk": d[0], "ortanca": d[0], "en_yuksek": d[0]}
    c1, c2, c3 = statistics.quantiles(d, n=4, method="inclusive")
    return {"n": len(d), "en_dusuk": d[0], "c1": round(c1, 2), "ortanca": round(statistics.median(d), 2), "c3": round(c3, 2),
            "en_yuksek": d[-1]}


def _dag_metin(g):
    if not g.get("n"):
        return "veri yok"
    if g["n"] == 1:
        return f"n 1: {g['ortanca']:g}"
    return f"n {g['n']}: en dusuk {g['en_dusuk']:g} | c1 {g['c1']:g} | ortanca {g['ortanca']:g} | c3 {g['c3']:g} | en yuksek {g['en_yuksek']:g}"


def oku_csv(yol):
    with open(yol, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def istatistik(satirlar, ozet):
    para = {}
    for s in satirlar:
        if s.get("para_birimi") and _sayi(s.get("fiyat")) is not None:
            para.setdefault(s["para_birimi"], []).append(s["fiyat"])
    magaza, magaza_yorum = {}, {}
    for s in satirlar:                          # magaza duzeyi alanlar magaza_id'ye gore tekil (cok ilanli magaza sismesin)
        if s.get("magaza_id") and s.get("magaza_toplam_satis") not in ("", None):
            magaza[s["magaza_id"]] = s["magaza_toplam_satis"]
        if s.get("magaza_id") and s.get("magaza_yorum") not in ("", None):
            magaza_yorum[s["magaza_id"]] = s["magaza_yorum"]
    kis = [s.get("kisisellestirilebilir") for s in satirlar if s.get("kisisellestirilebilir") not in ("", None)]
    return {
        "ifade_eslesen": {q: (ozet.get("ifadeler") or {}).get(q, {}).get("toplam_eslesen") for q in IFADELER},
        "ifade_donen": {q: (ozet.get("ifadeler") or {}).get(q, {}).get("donen") for q in IFADELER},
        "tekil_ilan": len(satirlar),
        "fiyat": {pb: dagilim(v) for pb, v in sorted(para.items())},
        "favori": dagilim(s.get("favori") for s in satirlar),
        "ilan_yorum_ilk20": dagilim(s.get("ilan_yorum") for s in satirlar),
        "magaza_yorum_ilk40": dagilim(magaza_yorum.values()),
        "magaza_toplami_ilk40": dagilim(magaza.values()),
        "kisisellestirme": {"evet": sum(1 for k in kis if str(k) == "True"), "alan_dolu": len(kis), "tekil_ilan": len(satirlar)},
    }


def rapor(out):
    satirlar, ilk = oku_csv(out / "ILANLAR.csv"), oku_csv(out / "ILK20.csv")
    oz = json.loads((out / "OZET.json").read_text(encoding="utf-8"))
    st = istatistik(satirlar, oz)
    y = [BASLIK, "", UYARI, "",
         f"Okuma: {oz.get('baslangic_utc')} - {oz.get('bitis_utc', '')} UTC | Etsy istek {oz.get('etsy_istek')}/{OP.BUTCE} | "
         f"kota {oz.get('kota_baslangic')} -> {oz.get('kota_bitis')} (Etsy API, x-remaining-today)", "",
         "## Ifade basi (findAllListingsActive, sort_on=score, limit=100)", "", "| ifade | eslesen (count) | donen |", "|---|---|---|"]
    y += [f"| {q} | {st['ifade_eslesen'][q]} | {st['ifade_donen'][q]} |" for q in IFADELER]
    y += ["", f"Tekil ilan (6 aramanin birlesimi): {st['tekil_ilan']}", "", "## Dagilimlar (tekil ilanlar; bos alan sayilmaz)", ""]
    for pb, g in st["fiyat"].items():
        y.append(f"- fiyat {pb}: {_dag_metin(g)}")
    if not st["fiyat"]:
        y.append("- fiyat: veri yok")
    y += [f"- favori (num_favorers): {_dag_metin(st['favori'])}",
          f"- ilan yorum sayisi (yalniz ilk 20 icin okundu): {_dag_metin(st['ilan_yorum_ilk20'])}",
          f"- magaza yorum sayisi (ilk 40 ilanin tekil magazalari): {_dag_metin(st['magaza_yorum_ilk40'])}",
          f"- magaza toplami (magazanin TUM satisi, ilk 40 ilanin tekil magazalari; ilan satisi DEGIL): {_dag_metin(st['magaza_toplami_ilk40'])}",
          f"- kisisellestirme: {st['kisisellestirme']['evet']}/{st['kisisellestirme']['alan_dolu']} ilan is_personalizable=True "
          f"(alan dolu {st['kisisellestirme']['alan_dolu']}/{st['kisisellestirme']['tekil_ilan']})",
          "", "## Ilk 20 (favori azalan, esitlikte magaza toplami azalan)", "", "| # | Baslik | Fiyat | Favori | Magaza toplami |",
          "|---|---|---|---|---|"]
    for s in ilk:
        b = str(s.get("baslik") or "").replace("|", "/")[:80]
        y.append(f"| {s.get('sira')} | {b} | {s.get('fiyat')} {s.get('para_birimi')} | {s.get('favori')} | {s.get('magaza_toplam_satis')} |")
    y += ["", "Kaynak: Etsy Open API v3 (yalniz GET, API anahtari). Bos hucre = API vermedi. TEMAS.jpg yalniz ic inceleme icindir."]
    (out / "RAPOR_TASLAK.md").write_text("\n".join(y) + "\n", encoding="utf-8")
    return st


def log_ozet(oz, st=None):
    """B3: tek satirlar; ilan kimligi, baslik, magaza adi YOK."""
    E.log("OZET pazar | ifade basi eslesen: " + json.dumps(
        {q: (oz.get("ifadeler") or {}).get(q, {}).get("toplam_eslesen") for q in IFADELER}, ensure_ascii=False))
    E.log(f"OZET pazar | tekil ilan {oz.get('tekil_ilan')} | istek {oz.get('etsy_istek')} | kota {oz.get('kota_baslangic')} -> "
          f"{oz.get('kota_bitis')} | durum {oz.get('durum')}")
    if st is not None:
        E.log("OZET pazar | fiyat ortancasi: " + ("; ".join(f"{pb} {g.get('ortanca')} (n {g.get('n')})" for pb, g in st["fiyat"].items())
                                                   or "veri yok"))


def _gecici_rapor(ilk, ozet):
    return BASLIK + "\n\n(rapor kolye_pazar.rapor ile yazilir)\n"


def calis(out, api, indir=None):
    if not isinstance(api, SaltOkur):
        raise SystemExit("DUR: istemci SaltOkur degil (GET disi istek korumasi yok)")
    eski = (OP.IFADELER, OP.rapor_taslak)
    OP.IFADELER = IFADELER                      # ornament_pazar.calis IFADELER'i modulden okur (ornament_pazar.py:126)
    OP.rapor_taslak = _gecici_rapor             # ornament baslikli taslak yazilmaz; kolye raporu asagida
    kod, st = None, None
    try:
        kod = OP.calis(out, api, indir=indir)
        st = rapor(out) if kod == 0 else None
        return kod
    finally:                                    # istisnada (429, butce, 403 arama) da ozet satirlari ve OZET.json yazilir
        OP.IFADELER, OP.rapor_taslak = eski
        oz = json.loads((out / "OZET.json").read_text(encoding="utf-8")) if (out / "OZET.json").exists() else {}
        oz.setdefault("etsy_istek", api.calls)
        oz.setdefault("kota_bitis", OP.tam(api.remaining))
        if kod is None:
            oz.setdefault("durum", "HATA (kosu yarida kesildi; ara sonuc ornament_pazar icinde tutulur, yazilamadi)")
            out.mkdir(parents=True, exist_ok=True)
            if not (out / "OZET.json").exists():
                (out / "OZET.json").write_text(json.dumps(oz, ensure_ascii=False, indent=1), encoding="utf-8")
        log_ozet(oz, st)


def main():
    sys.stdout, sys.stderr = KimlikSuz(sys.stdout), KimlikSuz(sys.stderr)
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    api = SaltOkur(E.APIKeyStore(os.environ.get("ETSY_API_KEY", ""), os.environ.get("ETSY_SHARED_SECRET", "")))
    return calis(Path(a.out), api)


if __name__ == "__main__":
    sys.exit(main())
