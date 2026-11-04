#!/usr/bin/env python3
"""P1 testleri (ag yok, Etsy yok). Bilinen PASS + bilinen FAIL. Canli metin ornegi: testdata_poster_cancer_libra.json (3 Kas
oncesi metin) + poster_metin_kuru.DEG (3-4 Kas yazimi) = 4 Kas canli bicimi."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ru_poster as R  # noqa: E402
import poster_metin_kuru as P  # noqa: E402
import p1_poster_kuru as K  # noqa: E402

D = json.loads((pathlib.Path(__file__).with_name("testdata_poster_cancer_libra.json")).read_text())
BOY = ["5×7″ (13×18cm)"] + list(P.K.BOYLAR)
BOYKOD = [P.boy_kodu(b) for b in BOY]
sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append((ad, bool(kosul)))
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {ayr}" if ayr and not kosul else ""), flush=True)


def canli_en():
    en = P.norm(D["description"])
    for a, b in P.DEG:
        en = en.replace(a, b)
    return en


def kayit(en, ru, state="active", ru_durum="var", ru_baslik=None):
    inv = {"products": [{"property_values": [{"property_id": 513, "values": [b]}]} for b in BOY]}
    return dict(listing_id="4570143815", listing=dict(listing_id=4570143815, state=state, title=D["title"], description=en,
                                                       tags=D["tags"], materials=["matte art paper", "ink"]),
                inventory=inv, ru=dict(title=D["ru"]["title"] if ru_baslik is None else ru_baslik, description=ru, tags=D["ru"]["tags"]) if ru is not None else None,
                ru_durum=ru_durum)


EN0 = canli_en()
RU0, k0 = R.kur(EN0, {"boy": BOYKOD})
k("canli bicim: EN'de go_ahead sozu tam 1", EN0.count(K.SIL_EN) == 1)
k("kur(EN_eski = canli) hala PASS (geri alma)", k0.get("pass_"), k0.get("hata"))
k("canli RU'da SIL_RU tam 1", RU0.count(K.SIL_RU) == 1)
EN1 = EN0.replace(K.SIL_EN, "")
RU1, k1 = R.kur(EN1, {"boy": BOYKOD})
k("kur(EN_yeni) PASS", k1.get("pass_"), k1.get("hata"))
k("kur(EN_yeni) == canli RU eksi SIL_RU (birebir)", RU1.strip() == RU0.replace(K.SIL_RU, "").strip())
k("yeni EN paragrafi birebir", K.YENI_EN in EN1.split("\n\n"))
k("yeni RU paragrafi birebir", K.YENI_RU in RU1.split("\n\n"))
k("SABIT yeni anahtar = YENI_EN -> YENI_RU", R.SABIT.get(K.YENI_EN) == K.YENI_RU)
# siniflama: bilinen PASS + bilinen FAIL
k("sinif: go_ahead 1 -> PLAN", K.sinif(EN0) == "PLAN")
eski = EN0.replace(K.SIL_EN, K.SIL_EN_ESKI)
k("sinif: eski varyant -> DUR_ESKI", K.sinif(eski) == "DUR_ESKI")
k("sinif: 0 eslesme -> ZATEN_ADAY", K.sinif(EN1) == "ZATEN_ADAY")
k("sinif: 2 eslesme -> FAIL", K.sinif(EN0 + "\n\n" + EN0) == "FAIL")
# plan_ilan: bilinen PASS
s, d = K.plan_ilan(kayit(EN0, RU0))
k("plan_ilan canli -> PLAN, neden yok", s["durum"] == "PLAN" and not s["neden"], s["neden"])
k("plan_ilan fark tam 1 paragraf (EN ve RU)", s["en_fark_par"] and len(s["en_fark_par"]) == 1 and len(s["ru_fark_par"]) == 1)
k("plan_ilan basliga/etikete dokunmaz (yedek = canli)", d["yedek"]["title"] == D["title"] and d["yedek"]["tags"] == D["tags"])
k("onay_ozet yeni metinden", d["onay_ozet"] == R.onay_ozet(EN1, RU1))
# plan_ilan: bilinen FAIL
s, _ = K.plan_ilan(kayit(EN0, RU0, state="draft"))
k("state draft -> DUR", s["durum"] == "DUR" and any("state" in n for n in s["neden"]))
s, _ = K.plan_ilan(kayit(EN0, RU0 + " x"))
k("canli RU sablondan farkli -> DUR", s["durum"] == "DUR" and any("kur(EN once)" in n for n in s["neden"]))
s, _ = K.plan_ilan(kayit(EN0, None, ru_durum="yok"))
k("RU yok -> DUR", s["durum"] == "DUR")
s, _ = K.plan_ilan(kayit(eski, RU0))
k("eski varyant -> DUR", s["durum"] == "DUR" and any("eski varyant" in n for n in s["neden"]))
s, _ = K.plan_ilan(dict(listing_id="1", ru_durum="okunamadi"))
k("okunamadi -> DUR", s["durum"] == "DUR")
s, _ = K.plan_ilan(kayit(EN1, RU1))
k("zaten yeni -> ZATEN_YENI", s["durum"] == "ZATEN_YENI")
# inceleme 4 Kas D-1: yarim yazim / varyantlar ZATEN_YENI sayilmaz (bilinen FAIL)
s, _ = K.plan_ilan(kayit(EN1, RU0))
k("EN yeni + RU eski (yarim) -> DUR", s["durum"] == "DUR", s)
kivrik = EN0.replace("don't hear", "don\u2019t hear")
k("kivrik kesme isareti -> sinif VARYANT", K.sinif(kivrik) == "VARYANT")
s, _ = K.plan_ilan(kayit(kivrik, RU0))
k("kivrik kesme isareti -> DUR", s["durum"] == "DUR" and any("varyant" in n for n in s["neden"]), s["neden"])
cift = EN0.replace("we go ahead with", "we go  ahead with")
s, _ = K.plan_ilan(kayit(cift, RU0))
k("cift bosluk -> DUR", s["durum"] == "DUR", s["neden"])
s, _ = K.plan_ilan(kayit(EN1, RU1, state="draft"))
k("taslak + yeni metin -> DUR (ZATEN_YENI degil)", s["durum"] == "DUR")
s, _ = K.plan_ilan(kayit(EN0, RU0, ru_baslik=""))
k("RU baslik bos -> DUR", s["durum"] == "DUR" and any("RU baslik" in n for n in s["neden"]), s["neden"])
s, _ = K.plan_ilan(kayit(EN0.replace("Every fusion symbol", "{x} Every fusion symbol", 1), RU0))
k("suslu parantez -> DUR", s["durum"] == "DUR", s["neden"])
s, _ = K.plan_ilan(kayit(EN0 + "\n\n" + EN0, RU0))
k("2+ eslesme -> DUR (neden FAIL)", s["durum"] == "DUR" and any(n.startswith("FAIL") for n in s["neden"]), s["neden"])
k("istek butcesi 20 (poster_metin_yaz.py:33)", K.ISTEK_ILAN == 20)
# main: HAM klasoru ile uc uca (1 ilan; digerleri 'ham dosya yok' -> DUR)
with tempfile.TemporaryDirectory() as t:
    t = pathlib.Path(t); (t / "HAM").mkdir()
    (t / "HAM" / "4570143815.json").write_text(json.dumps(kayit(EN0, RU0), ensure_ascii=False))
    (t / "AKTIF_SAYIM.csv").write_text("listing_id,grup,genel,go_ahead,eski\n4570143815,poster78,1,1,0\n111,yd78,1,1,0\n222,kupa,0,0,0\n")
    rc = K.main(["--ham", str(t), "--out", str(t / "o")])
    oz = json.loads((t / "o" / "OZET.json").read_text())
    k("main: 1 PLAN, 77 DUR (ham yok), 1 diger urun", rc == 0 and oz["plan"] == 1 and oz["dur"] == 77 and oz["diger_urun_eslesen"] == 1, oz)
n = sum(1 for _, v in sonuc if v)
print(f"SONUC {n}/{len(sonuc)}")
sys.exit(0 if n == len(sonuc) else 1)
