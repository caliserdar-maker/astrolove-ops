#!/usr/bin/env python3
"""YD 2. asama galeri (yd_liste_uret --profil yd2 + yd2_galeri_yukle) yerel testi (Merkez / Serdar 1 Kas gece). Ag / Drive / Etsy yok:
sahte Etsy test_yd_kapak_yukle.SahteYD (Style 513 / Format 514; pilot HAM gercek yapisi), HAM 1. asama SONRASINA cevrilir (rank 1 =
yeni kapak 3000x2250, alt metin = alt_metin(A, B), yeni kimlik). Senaryolar: liste HAZIR (1 DOKUNMA + 9 DEGISTIR + 12 CIKAR; kapak
CIKAR'da yok; Y01 hedefte yok; manifest profil yd2, dokunma_id, Style baglari 6-10); rank 1 eski kapak (1. asama yok) -> BLOK; set
kontrolu FAIL -> BLOK; --qc / --set-kontrol yok -> cikis 2; kuru: yeni yapi yok (Size 516 boy 0) -> BLOK, yeni yapi var -> PLAN; liste
profili yd2 degil -> on kapi DUR; yazim PASS (10 gorsel, rank 1 kimligi + alt metni ayni, rank 1'e sil / sira yazimi yok, 9 yukleme,
12 silme, baglar Starlit 6 ... Botanical 10); liste sonrasi rank 1 degismis -> BLOK; poster v11b profili etkilenmez (ayri test)."""
import contextlib
import copy
import csv
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts/etsy")); sys.path.insert(0, str(KOK / "scripts/kapak78"))
import test_yd_kapak_yukle as TK  # noqa: E402  (SahteYD, HAM)
import test_yd_liste_uret as TL  # noqa: E402
import test_galeri_v10 as T10  # noqa: E402  (Coklu)
import yd_liste_uret as L  # noqa: E402
import galeri_v10_yukle as V  # noqa: E402
import yd2_galeri_yukle as Y2  # noqa: E402

LID, CIFT = TK.LID, TK.CIFT
KAPAK_ID = 99000001
SONUC = []


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


def ham2(kapak_yeni=True):
    h = copy.deepcopy(TK.HAM)
    g = sorted(h["images"], key=lambda x: x["rank"])
    if kapak_yeni:
        g[0].update(listing_image_id=KAPAK_ID, full_width=3000, full_height=2250, alt_text=L.alt_metin("Cancer", "Libra"))
    h["images"] = g
    return h


class SahteYD2(TK.SahteYD):
    """yapi=True: envanterde Size (516) 14 boy (yeni ilan yapisi yazilmis)."""
    def __init__(self, ham, yapi=True, **k):
        super().__init__(ham=ham, **k); self.yapi = yapi; self._ham = ham

    def get(self, path, params=None, ok404=False):
        if path.endswith("/inventory"):
            self._k(); self.n_get += 1
            inv = copy.deepcopy(self._ham["inventory"])
            if self.yapi:
                inv["products"] += [dict(sku=f"s{i}", offerings=[dict(price=1)], property_values=[
                    dict(property_id=516, value_ids=[600 + i], values=[f"boy{i}"])]) for i in range(14)]
            return inv
        return super().get(path, params, ok404)


def set_kontrol(d, durum="PASS"):
    with open(d / "SET.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["dosya", "cift", "kart", "bayt", "genislik", "yukseklik", "sha256", "durum", "neden"])
        for k in range(1, 11):
            ad = L.kaynak_ad(CIFT, k)
            w.writerow([ad, CIFT, k, 1, 3000, 2250, L.sha(d / "kapak" / ad), durum if k == 6 else "PASS", ""])


def liste(d, h, ek=("--set-kontrol",), durum="PASS", out="hazir"):
    TL.galeri_kur(d, ham=h); set_kontrol(d, durum)
    args = ["liste", "--ciftler", str(d / "yd.csv"), "--kaynak", str(KOK / "docs/yd_kapak/KAPAK_KAYNAK.csv"), "--ham-dir", str(d / "HAM"),
            "--kapak-dir", str(d / "kapak"), "--alt", str(d / "ALT.csv"), "--yedek-ozet", str(d / "OZET.md"),
            "--yedek-liste", str(d / "yl.json"), "--out", str(d / out), "--profil", "yd2"]
    if ek == ("--set-kontrol",):
        args += ["--set-kontrol", str(d / "SET.csv")]
    with contextlib.redirect_stdout(io.StringIO()):
        rc = L.main(args)
    return rc, (json.loads((d / out / "LISTE_OZET.json").read_text()) if rc == 0 else None)


def kos(api, hazir, out, kuru=True, plan=None, damga=""):
    args = ["--hazir", str(hazir), "--out", str(out), "--bes-x7", "yok", "--kosu", "333",
            "--devam", str(out / "DEVAM.json"), "--ilerleme", str(out / "ILERLEME.json")]
    args += ["--kuru"] if kuru else ["--confirm", "YD_GALERI_V2", "--plan", str(plan), "--plan-damga", damga]
    a = V.arg(args)
    try:
        Y2.on_kapi(a)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = V.sonlandir(api, "1", a)
    except SystemExit as e:
        return 9, dict(hata=str(e.code))
    return rc, json.loads((Path(out) / "RAPOR.json").read_text())


def main():
    V.profil_kur("yd2", Y2.ek_kapi)
    t0 = Path(tempfile.mkdtemp(prefix="yd2_"))
    try:
        d = t0 / "a"; d.mkdir(); h = ham2()
        rc, oz = liste(d, h)
        ilan = (oz or {}).get("ilanlar", {}).get(LID, {})
        kontrol(f"liste yd2: HAZIR, profil yd2, qc SET_KONTROL ({ilan.get('neden')})",
                rc == 0 and oz["profil"] == "yd2" and oz["qc_ad"] == "SET_KONTROL" and ilan.get("durum") == "HAZIR")
        hz = d / "hazir"
        rows = list(csv.DictReader(open(hz / LID / f"LISTE_{LID}.csv")))
        r1 = next(x for x in rows if x["hedef_sira"] == "1")
        cik = [x["simdi_id"] for x in rows if x["islem"] == "CIKAR"]
        kontrol("liste yd2: sira 1 DOKUNMA (yeni kapak kimligi, alt metni canli), 9 DEGISTIR, 12 CIKAR, kapak CIKAR'da yok",
                r1["islem"] == "DOKUNMA" and r1["simdi_id"] == str(KAPAK_ID) and r1["hedef_alt"] == L.alt_metin("Cancer", "Libra")
                and sum(x["islem"] == "DEGISTIR" for x in rows) == 9 and len(cik) == 12 and str(KAPAK_ID) not in cik)
        m = json.loads((hz / LID / "manifest.json").read_text())
        kontrol("liste yd2: manifest profil yd2, dokunma_id, Style baglari Starlit 6 .. Botanical 10, Y01 hedefte yok (9 dosya)",
                m["profil"] == "yd2" and m["dokunma_id"] == KAPAK_ID and m["renk_bag_sayisi"] == 5
                and {v["value"]: v["image_id"] for v in m["variation_images"]} == L.STIL_SIRA
                and not (hz / LID / "hedef" / "01_1.jpg").exists() and len(list((hz / LID / "hedef").glob("*.jpg"))) == 9)
        d2 = t0 / "b"; d2.mkdir(); rc, oz2 = liste(d2, ham2(kapak_yeni=False))
        kontrol("liste yd2: rank 1 eski kapak (1. asama yok) -> BLOK", oz2["ilanlar"][LID]["durum"] == "BLOK"
                and any("1. asama" in n for n in oz2["ilanlar"][LID]["neden"]))
        d3 = t0 / "c"; d3.mkdir(); rc, oz3 = liste(d3, ham2(), durum="FAIL")
        kontrol("liste yd2: set kontrolu Y06 FAIL -> BLOK", oz3["ilanlar"][LID]["durum"] == "BLOK"
                and any("SET_KONTROL" in n for n in oz3["ilanlar"][LID]["neden"]))
        d4 = t0 / "d"; d4.mkdir()
        kontrol("liste yd2: --qc / --set-kontrol yok -> cikis 2", liste(d4, ham2(), ek=())[0] == 2)

        o1 = t0 / "o1"; o1.mkdir()
        rc, R = kos(T10.Coklu({LID: SahteYD2(h, yapi=False)}), hz, o1)
        s = (R.get("ilanlar") or [{}])[0]
        kontrol("kuru yd2: yeni yapi yok (Size 516 boy 0) -> BLOK (galeri yeni yapidan once yuklenmez)",
                s.get("durum") == "BLOK" and any("boy sayisi" in n for n in s.get("neden") or []))
        o2 = t0 / "o2"; o2.mkdir()
        api = T10.Coklu({LID: SahteYD2(h)})
        rc, R = kos(api, hz, o2)
        s = (R.get("ilanlar") or [{}])[0]
        kontrol(f"kuru yd2: yeni yapi var -> PLAN (en az {s.get('en_az')} / en kotu {s.get('en_kotu')})",
                rc == 0 and s.get("durum") == "PLAN")
        shutil.copyfile(o2 / "PLAN_YD2.json", t0 / "PLAN.json")
        f = SahteYD2(h); api = T10.Coklu({LID: f})
        o3 = t0 / "o3"; o3.mkdir()
        rc, R3 = kos(api, hz, o3, kuru=False, plan=t0 / "PLAN.json", damga=R["plan_damga"])
        gal = sorted(f.img, key=lambda x: x["rank"]); rk = {x["listing_image_id"]: x["rank"] for x in gal}
        kontrol(f"yazim yd2: PASS, 10 gorsel, rank 1 ayni kimlik ve alt metin (rc {rc}, {R3.get('sayilar')})",
                rc == 0 and R3["sayilar"].get("PASS") == 1 and len(gal) == 10 and gal[0]["listing_image_id"] == KAPAK_ID
                and gal[0]["alt_text"] == L.alt_metin("Cancer", "Libra"))
        kontrol(f"yazim yd2: ara galeri en fazla {f.max_n} gorsel (<= 20, Etsy siniri)", f.max_n <= 20)
        kontrol("yazim yd2: rank 1'e sil / sira yazimi yok, 9 yukleme, 12 silme",
                not any(y[0] in ("sil", "sira") and y[1] == KAPAK_ID for y in f.yaz if len(y) > 1)
                and f.n_yukle == 9 and len(f.silinenler) == 12 and KAPAK_ID not in f.silinenler)
        kontrol("yazim yd2: Style baglari Starlit 6, Timeless 7, First Page 8, Layers 9, Botanical 10",
                {k: rk.get(v) for k, v in f.bag.items()} == L.STIL_SIRA)
        h5 = ham2(); h5["images"][0]["listing_image_id"] = 99000002
        o5 = t0 / "o5"; o5.mkdir()
        rc, R5 = kos(T10.Coklu({LID: SahteYD2(h5)}), hz, o5)
        s5 = (R5.get("ilanlar") or [{}])[0]
        kontrol("kuru yd2: liste sonrasi canli rank 1 degismis -> BLOK", s5.get("durum") == "BLOK"
                and any("DOKUNMA kapagi" in n or "yedekten farkli" in n for n in s5.get("neden") or []))
        oz["profil"] = "v1"; (hz / "LISTE_OZET.json").write_text(json.dumps(oz))
        o6 = t0 / "o6"; o6.mkdir()
        rc, R6 = kos(T10.Coklu({LID: SahteYD2(h)}), hz, o6)
        kontrol("on kapi: liste profili yd2 degil -> DUR (Etsy istegi yok)", rc == 9 and "liste profili" in R6.get("hata", ""))
    finally:
        shutil.rmtree(t0, ignore_errors=True)
    bad = [a for a, ok in SONUC if not ok]
    print(f"yd2 galeri testleri: {len(SONUC) - len(bad)}/{len(SONUC)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
