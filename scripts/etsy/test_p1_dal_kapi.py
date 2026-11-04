#!/usr/bin/env python3
"""p1_dal_kapi testi: bilinen PASS + bilinen FAIL (izin disi dosya, HAM yolu, alt klasor, yasak anahtar ic ice, stage disi yol)."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import p1_dal_kapi as D  # noqa: E402

sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append((ad, bool(kosul)))
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {ayr}" if ayr and not kosul else ""), flush=True)


def kur(ek=None):
    t = pathlib.Path(tempfile.mkdtemp()) / "docs" / "p1" / "P1_KURU_X"; t.mkdir(parents=True)
    for f in ("FARK.csv", "DUR.csv", "DIGER_URUNLER.csv", "LOG.txt"):
        (t / f).write_text("a\n", encoding="utf-8")
    (t / "OZET.json").write_text(json.dumps({"plan": 78}), encoding="utf-8")
    (t / "ONCE_SONRA.json").write_text(json.dumps({"1": {"en_once": "price list sku in text", "boylar": ["8x10"],
                                                         "yedek": {"title": "t", "tags": ["a"]}}}), encoding="utf-8")
    if ek:
        ek(t)
    return t


t = kur()
k("izinli 6 dosya (metinde 'price'/'sku' kelimesi serbest) -> PASS", D.main([str(t)]) == 0)
k("izin disi dosya -> FAIL", D.main([str(kur(lambda t: (t / "x.json").write_text("{}")))]) == 1)
k("HAM alt klasoru -> FAIL", D.main([str(kur(lambda t: ((t / "HAM").mkdir(), (t / "HAM" / "1.json").write_text("{}"))))]) == 1)
k("ic ice yasak anahtar (products/price) -> FAIL",
  D.main([str(kur(lambda t: (t / "ONCE_SONRA.json").write_text(json.dumps({"1": {"inventory": {"products": [{"Price": 1}]}}}))))]) == 1)
k("liste icinde SKU anahtari -> FAIL", D.main([str(kur(lambda t: (t / "OZET.json").write_text(json.dumps({"a": [{"SKU": "x"}]}))))]) == 1)
t = kur(); st = t.parent.parent.parent / "st.txt"
st.write_text(f"{t.as_posix()}/FARK.csv\nscripts/x.py\n", encoding="utf-8")
k("stage'de klasor disi yol -> FAIL", D.main([str(t), "--staged", str(st)]) == 1)
st.write_text(f"{t.as_posix()}/FARK.csv\n{t.as_posix()}/OZET.json\n", encoding="utf-8")
k("stage yalniz klasor -> PASS", D.main([str(t), "--staged", str(st)]) == 0)
k("klasor yok -> FAIL", D.main(["/yok/yok"]) == 1)
k("CSV'de price/sku sutunu -> FAIL", D.main([str(kur(lambda t: (t / "FARK.csv").write_text("listing_id,price,sku\n1,2,3\n")))]) == 1)
k("sembolik bag LOG.txt -> FAIL", D.main([str(kur(lambda t: ((t / "LOG.txt").unlink(), (t / "LOG.txt").symlink_to("/etc/hostname"))))]) == 1)
n = sum(1 for _, v in sonuc if v)
print(f"SONUC {n}/{len(sonuc)}")
sys.exit(0 if n == len(sonuc) else 1)
