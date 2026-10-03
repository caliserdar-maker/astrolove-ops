#!/usr/bin/env python3
"""GOREV_0022: dijital teslim - renk basina 1 cok sayfali PDF (Etsy Messages kanali).

Her PDF: 5 sayfa (4x5, 3x4, 2x3, 11x14, A serisi) + PRINT GUIDE son sayfa(lar).
Sayfa = onayli baski JPEG'i BIREBIR (img2pdf: JPEG akisi yeniden kodlanmaz/orneklenmez);
dogrulama: PDF'teki her goruntu akisinin SHA-256'si kaynak JPEG ile ayni olmali.
Sinir: dosya basina < 100 MB (hedef < 60 MB, asarsa uyari). Ad: AstroLove_<CIFT>_<Renk_Adi>.pdf.
Musteri adi dosya adina GIRMEZ. Onay: ciktilar siparis_onay.py hazirla'ya verilir.

Girdi: --kaynak altinda renk basina klasor ya da kisisel ZIP'i (<CIFT>_<RENK>.zip);
JPEG adinda oran anahtari (4x5, 3x4, 2x3, 11x14, A/A2/a_series) bulunur.
--atla RENK,... : kapisi FAIL olan renkler (yazilmaz, raporlanir).
"""
import argparse, hashlib, io, json, re, sys, zipfile
from pathlib import Path

import img2pdf
from pypdf import PdfReader, PdfWriter

RENKLER = ("MIDNIGHT_BLUE", "DEEP_BLACK", "PURE_WHITE", "CHAMPAGNE_IVORY", "WARM_PARCHMENT")
ORANLAR = ("4x5", "3x4", "2x3", "11x14", "A")
AZAMI, HEDEF = 100 * 1024 * 1024, 60 * 1024 * 1024


def renk_adi(r):
    return "_".join(w.capitalize() for w in r.split("_"))


def oran_bul(ad):
    a = ad.lower()
    for o in ("11x14", "4x5", "3x4", "2x3"):
        if o in a:
            return o
    if re.search(r"(^|[_\-])(a[1-5]|a_series|a)([_\-.]|$)", a):
        return "A"
    return None


def jpegler(kaynak, cift, renk):
    """{oran: bytes} - klasor ya da ZIP'ten. Oran basina TAM 1 dosya, yoksa DUR."""
    d, z = Path(kaynak) / renk, Path(kaynak) / f"{cift}_{renk}.zip"
    ogeler = []
    if d.is_dir():
        ogeler = [(p.name, p.read_bytes()) for p in sorted(d.iterdir()) if p.suffix.lower() in (".jpg", ".jpeg")]
    elif z.is_file():
        with zipfile.ZipFile(z) as a:
            ogeler = [(n, a.read(n)) for n in sorted(a.namelist()) if n.lower().endswith((".jpg", ".jpeg"))]
    else:
        raise SystemExit(f"HATA: {renk} kaynagi yok ({d} / {z}). DUR.")
    out = {}
    for ad, b in ogeler:
        o = oran_bul(Path(ad).name)
        if o is None:
            raise SystemExit(f"HATA: {renk}/{ad}: oran anahtari bulunamadi. DUR.")
        if o in out:
            raise SystemExit(f"HATA: {renk}: {o} icin birden fazla dosya. DUR.")
        if b[:2] != b"\xff\xd8":
            raise SystemExit(f"HATA: {renk}/{ad} JPEG degil. DUR.")
        out[o] = b
    eksik = [o for o in ORANLAR if o not in out]
    if eksik:
        raise SystemExit(f"HATA: {renk}: eksik oran {eksik}. DUR.")
    return out


def goruntu_ozetleri(pdf_bayt, n):
    """Ilk n sayfadaki goruntu akislarinin HAM (DCT) baytlarinin SHA-256'si."""
    r = PdfReader(io.BytesIO(pdf_bayt))
    oz = []
    for s in r.pages[:n]:
        xo = s["/Resources"]["/XObject"]
        akis = [xo[k].get_object() for k in xo]
        if len(akis) != 1 or akis[0].get("/Filter") != "/DCTDecode":
            return None
        oz.append(hashlib.sha256(akis[0]._data).hexdigest())   # ham DCT akisi (kodlanmis JPEG)
    return oz, len(r.pages)


def pdf_kur(jp, rehber_bayt):
    sirali = [jp[o] for o in ORANLAR]
    govde = img2pdf.convert(sirali)
    w = PdfWriter()
    w.append(PdfReader(io.BytesIO(govde)))
    rehber = PdfReader(io.BytesIO(rehber_bayt))
    w.append(rehber)
    buf = io.BytesIO(); w.write(buf)
    return buf.getvalue(), len(rehber.pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaynak", required=True)
    ap.add_argument("--rehber", required=True, help="PRINT GUIDE PDF (son sayfa olarak eklenir)")
    ap.add_argument("--cift", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--atla", default="", help="kapisi FAIL olan renkler (yazilmaz)")
    a = ap.parse_args()
    rb = Path(a.rehber).read_bytes()
    if rb[:4] != b"%PDF":
        raise SystemExit("HATA: rehber PDF degil. DUR.")
    atla = {x.strip().upper() for x in a.atla.split(",") if x.strip()}
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rapor, hata = {"cift": a.cift, "renkler": {}}, []
    for renk in RENKLER:
        if renk in atla:
            rapor["renkler"][renk] = {"durum": "YAZILMADI (kapi FAIL)"}
            continue
        jp = jpegler(a.kaynak, a.cift, renk)
        pdf, rsayfa = pdf_kur(jp, rb)
        oz = goruntu_ozetleri(pdf, len(ORANLAR))
        kaynak_oz = [hashlib.sha256(jp[o]).hexdigest() for o in ORANLAR]
        birebir = bool(oz) and oz[0] == kaynak_oz
        sayfa = oz[1] if oz else None
        ad = f"AstroLove_{a.cift.upper()}_{renk_adi(renk)}.pdf"
        k = {"dosya": ad, "bayt": len(pdf), "MB": round(len(pdf) / 1e6, 2), "sayfa": sayfa,
             "rehber_sayfa": rsayfa, "goruntu_birebir": birebir,
             "hedef_60MB": len(pdf) < HEDEF, "gecti": birebir and len(pdf) < AZAMI
             and sayfa == len(ORANLAR) + rsayfa}
        if k["gecti"]:
            (out / ad).write_bytes(pdf)
        else:
            hata.append(f"{renk}: {k}")
        rapor["renkler"][renk] = k
    rapor["SONUC"] = "PASS" if not hata else "FAIL"
    (out / "PDF_PAKET_RAPOR.json").write_text(json.dumps(rapor, indent=1, ensure_ascii=False))
    print(json.dumps(rapor, ensure_ascii=False))
    return 0 if not hata else 1


if __name__ == "__main__":
    sys.exit(main())
