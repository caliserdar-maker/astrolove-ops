#!/usr/bin/env python3
"""wp_siparis birim testleri - kucuk dizilerle, saniyeler icinde (Drive/Actions yok).

Buyuk sentetik testler (test_siparis.py, test_medyan_plate.py) dakikalar suruyor;
bu dosya kritik kurallari saniyede kilitler ve regresyonu yakalar.
"""
import importlib.util, sys, tempfile
from pathlib import Path

import numpy as np
import cv2

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
_s = importlib.util.spec_from_file_location("wp_siparis", KOK / "wp_kisisel" / "wp_siparis.py")
SP = importlib.util.module_from_spec(_s); _s.loader.exec_module(SP)
V2 = SP.V2
from wp_plate_pilot import INK_RGB                                            # noqa: E402

GECTI, KALDI = [], []


def kontrol(ad, kosul, ayrinti=""):
    (GECTI if kosul else KALDI).append(ad)
    print(("PASS " if kosul else "FAIL ") + ad + (f" | {ayrinti}" if ayrinti else ""))


def durur(fn, *a, **k):
    """fn SystemExit ile durursa mesaji doner, durmazsa None."""
    try:
        fn(*a, **k)
    except SystemExit as e:
        return str(e)
    return None


# ---------------------------------------------------------------- uc_grup
def t_uc_grup():
    # GERCEK olcum (run 36154187069, ARIES_LEO): sol isim iki parcaya bolunmus
    sol, orta, sag, b = V2.uc_grup([(1941, 2580), (2626, 3045), (3472, 4077), (4498, 5290)])
    kontrol("uc_grup: gercek olcum (bosluk 46/427/421)",
            (sol, orta, sag) == ((1941, 3045), (3472, 4077), (4498, 5290)), f"grup={b['grup']}")
    # iki yanda da bolunme
    sol, orta, sag, _ = V2.uc_grup([(100, 300), (340, 600), (1000, 1200), (1600, 1800), (1840, 2000)])
    kontrol("uc_grup: iki isim de bolunmus",
            (sol, orta, sag) == ((100, 600), (1000, 1200), (1600, 2000)))
    # 2 kume -> DUR
    kontrol("uc_grup: 2 kume DURduruyor",
            "en az 3 kume" in (durur(V2.uc_grup, [(100, 300), (1000, 1200)]) or ""))
    # belirsiz ayrim (bosluklar birbirine yakin) -> DUR
    # bosluklar 90 / 100 / 100 -> secilen (100) < 2 x kalan (90): ayrim belirsiz
    m = durur(V2.uc_grup, [(0, 100), (190, 290), (390, 490), (590, 690)])
    kontrol("uc_grup: belirsiz bosluk DURduruyor", "belirsiz" in (m or ""), (m or "")[:70])


# ---------------------------------------------------------------- isaret ayrimi
def t_murekkep():
    """YILDIZ REGRESYONU: eski murekkegin altindan cikan yildiz YENI murekkep
    sayilmamali. 1B izdusum bunu kaciriyordu (olcum 25 Eyl: 53 poster px)."""
    ed = "Midnight_Blue"
    r, g, b = INK_RGB[ed]
    zemin = (48, 22, 12)                      # BGR koyu lacivert
    ink = (b, g, r)                           # BGR altin
    yildiz = (235, 238, 245)                  # BGR beyaz yildiz
    plate = np.zeros((1, 4, 3), np.uint8); baski = np.zeros((1, 4, 3), np.uint8)
    plate[0, 0] = zemin;  baski[0, 0] = ink        # 0: YENI murekkep  -> poz
    plate[0, 1] = ink;    baski[0, 1] = zemin      # 1: eski oge silinmis -> neg
    plate[0, 2] = ink;    baski[0, 2] = yildiz     # 2: eski murekkep altindan YILDIZ -> neg
    plate[0, 3] = zemin;  baski[0, 3] = zemin      # 3: degisiklik yok
    for isaret, bekle in (("uzaklik", [1, 0, 0, 0]), ("izdusum", None)):
        fark, alfa, alfa_o, tani = SP.murekkep(baski, plate, ed, "birak", isaret)
        poz = (alfa_o > 0).astype(int).ravel().tolist()
        if bekle is not None:
            kontrol(f"murekkep/{isaret}: yildiz YENI murekkep sayilmiyor", poz == bekle,
                    f"poz={poz} (beklenen {bekle})")
        else:
            kontrol("murekkep/izdusum: yildizi YANLIS siniflandiriyor (bilinen kusur)",
                    poz[2] == 1, f"poz={poz}")
    # hayalet gecir: negatif de aktarilir ama OLCUM maskesi yine yalniz pozitif
    fark, alfa, alfa_o, _ = SP.murekkep(baski, plate, ed, "gecir", "uzaklik")
    kontrol("murekkep: 'gecir' aktarimi genisletir, olcumu genisletmez",
            (alfa > 0).sum() == 3 and (alfa_o > 0).sum() == 1,
            f"aktarim={int((alfa > 0).sum())} olcum={int((alfa_o > 0).sum())}")


# ---------------------------------------------------------------- girdi cozumleme
def t_dosya_bul():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "SIPARIS_ARIES_LEO_MIDNIGHT_BLUE_24X32.png").write_bytes(b"x")
        (d / "SIPARIS_ARIES_LEO_MIDNIGHT_BLUE_24X32.json").write_text("{}")   # yan dosya
        f = SP.dosya_bul(d, ["MIDNIGHT_BLUE", "24x32"], "baski")
        kontrol("dosya_bul: yan dosya (json) eslesmeyi bozmuyor", f.suffix == ".png", f.name)
        # GERCEK dosya adi kucuk x ile: PURE_WHITE_24x32.png (26 Eyl olcumu).
        # Eski buyuk harfli glob bunu KACIRIYORDU - regresyon testi.
        (d / "PURE_WHITE_24x32.png").write_bytes(b"x")
        f = SP.dosya_bul(d, ["PURE_WHITE", "24X32"], "plate")
        kontrol("dosya_bul: buyuk/kucuk harf duyarsiz (PURE_WHITE_24x32.png)",
                f.name == "PURE_WHITE_24x32.png", f.name)
        (d / "SIPARIS_ARIES_LEO_MIDNIGHT_BLUE_24X32_v2.png").write_bytes(b"x")
        m = durur(SP.dosya_bul, d, ["MIDNIGHT_BLUE", "24x32"], "baski")
        kontrol("dosya_bul: iki goruntu -> DUR", "2 goruntu eslesmesi" in (m or ""), (m or "")[:70])
        m = durur(SP.dosya_bul, d, ["WARM_PARCHMENT", "24x32"], "baski")
        kontrol("dosya_bul: eslesme yok -> DUR", "0 goruntu eslesmesi" in (m or ""))
        # cift adi TAM BOLUT olarak suzulur: CANCER_LIBRA, CANCER_LIBRA_UZUN'u
        # yakalamamali (kosu 36230639918 bu yuzden dustu) - regresyon testi.
        (d / "SIPARIS_CANCER_LIBRA_BLACK_24x32.png").write_bytes(b"x")
        (d / "SIPARIS_CANCER_LIBRA_UZUN_BLACK_24x32.png").write_bytes(b"x")
        f = SP.baski_bul(d, "BLACK", "CANCER_LIBRA")
        kontrol("baski_bul: cift+edisyon siniri (UZUN varyanti karismaz)",
                f.name == "SIPARIS_CANCER_LIBRA_BLACK_24x32.png", f.name)
        f = SP.baski_bul(d, "BLACK", "CANCER_LIBRA_UZUN")
        kontrol("baski_bul: UZUN varyanti dogru secilir",
                f.name == "SIPARIS_CANCER_LIBRA_UZUN_BLACK_24x32.png", f.name)
        m = durur(SP.baski_bul, d, "BLACK", "YOK_OLAN")
        kontrol("baski_bul: bulunamazsa denenen kaliplari yazar",
                "Denenen kaliplar" in (m or ""), (m or "")[:60])


def t_olcu_kontrolu():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td); (d / "b").mkdir(); (d / "p").mkdir()
        cv2.imwrite(str(d / "b" / "X_MIDNIGHT_BLUE_24X32.png"), np.zeros((10, 10, 3), np.uint8))
        cv2.imwrite(str(d / "p" / "MIDNIGHT_BLUE_24X32.png"), np.zeros((10, 10, 3), np.uint8))
        m = durur(SP.kaynak_oku, d / "b", d / "p", "Midnight_Blue")
        kontrol("kaynak_oku: yanlis olcu -> DUR", "beklenen 7200x9600" in (m or ""), (m or "")[:70])


# ---------------------------------------------------------------- halka guard
def t_murekkep_rengi():
    """INK_RGB'de olmayan edisyonda (PURE_WHITE/BLACK/BLUE) renk OLCULUR, tahmin edilmez."""
    ed = "BLUE"
    zemin, ink = (48, 22, 12), (63, 184, 244)          # BGR
    plate = np.full((1, 100, 3), zemin, np.uint8)
    baski = plate.copy(); baski[0, :5] = ink            # %5 murekkep
    f = baski.astype(np.float32) - plate.astype(np.float32)
    olculen = SP.murekkep_rengi(baski, plate, f, ed)
    kontrol("murekkep_rengi: bilinmeyen edisyonda olculuyor",
            np.allclose(olculen, np.array(ink, np.float32)), f"olculen={olculen.tolist()}")
    _, _, alfa_o, tani = SP.murekkep(baski, plate, ed, "birak", "uzaklik")
    kontrol("murekkep: bilinmeyen edisyonda KeyError yok, poz dogru",
            int((alfa_o > 0).sum()) == 5 and tani["murekkep_kaynagi"] == "olculdu",
            f"poz={int((alfa_o > 0).sum())} kaynak={tani['murekkep_kaynagi']}")


def t_kapilar_klasor():
    """kapilar cikti klasorunu OLUSTURMADAN json yaziyordu: 18 wallpaper uretilmis
    ama kapilar ve seritler yazilamamisti (kosu 36232634310, FileNotFoundError)."""
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        yol = Path(td) / "KAPI_CANCER_LIBRA"          # YOK
        K = V2.kapilar({}, None, {"kutular": {}}, "", "CANCER_LIBRA", yol, ["BLUE"])
        kontrol("kapilar: olmayan cikti klasorunu olusturur",
                (yol / "WP_V2_KAPILAR.json").exists() and isinstance(K, dict))


def t_halka_guard():
    from wp_plate_pilot import BOX_NAMES
    alfa = np.zeros((SP.POSTER_H, SP.POSTER_W), np.float32)
    x0, y0, x1, y1 = V2.BOX_SYMBOL_CORE
    alfa[y0:y1, x0:x1] = 1                                  # sembol var, halka YOK
    ny0, ny1 = BOX_NAMES[1] + 50, BOX_NAMES[3] - 50         # isim satiri: 3 kume
    for cx0, cx1 in ((1800, 2900), (3300, 3900), (4300, 5400)):
        alfa[ny0:ny1, cx0:cx1] = 1
    mb = SP.MESAJ_BANT                                      # mesaj bandi
    alfa[mb[1] + 150:mb[3] - 150, 2600:4600] = 1
    m = durur(SP.kutular_olc, alfa, False)
    kontrol("kutular_olc: --halka yokken halkasiz maske DURduruyor",
            "halka" in (m or "") and "HATA" in (m or ""), (m or "")[:80])
    m2 = durur(SP.kutular_olc, alfa, True)                  # --halka verildi
    kontrol("kutular_olc: --halka verilince halka aranmiyor, gecer", m2 is None, (m2 or "")[:80])


if __name__ == "__main__":
    for t in (t_uc_grup, t_murekkep, t_murekkep_rengi, t_dosya_bul, t_olcu_kontrolu,
              t_kapilar_klasor, t_halka_guard):
        t()
    print(f"\nTOPLAM {len(GECTI) + len(KALDI)} kontrol, {len(GECTI)} PASS, {len(KALDI)} FAIL")
    sys.exit(1 if KALDI else 0)
