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


# ------------------------------------------------------- GOREV_0014 YUKSEK1
def t_bos_cikti():
    """--edisyonlar ',' hic JPEG uretmeden exit 0 + bos rapor veriyordu."""
    m = durur(SP.main, ["--baski", ".", "--plate", ".", "--temiz", ".", "--cikti", ".",
                        "--edisyonlar", ","])
    kontrol("main: bos --edisyonlar DURduruyor (eskiden exit 0)",
            "edisyonlar bos" in (m or ""), (m or "")[:70])
    m2 = durur(SP.main, ["--baski", ".", "--plate", ".", "--temiz", ".", "--cikti", ".",
                         "--edisyonlar", "BLUE,BLUE"])
    kontrol("main: yinelenen edisyon DURduruyor", "yinelenen" in (m2 or ""), (m2 or "")[:70])
    m3 = durur(SP.main, ["--baski", ".", "--plate", ".", "--temiz", ".", "--cikti", ".",
                         "--ciftler", " , "])
    kontrol("main: bos cift listesi DURduruyor", "cift listesi bos" in (m3 or ""), (m3 or "")[:70])


def t_bos_kapi():
    """all([]) == True oldugu icin BOS kapi 'gecti' sayiliyordu."""
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        K = V2.kapilar({}, None, {"kutular": {}}, "", "X", Path(td) / "K", ["BLUE"])
        kontrol("kapilar: hic dosya yokken gecti=False",
                K["gecti"] is False and bool(K["bos_kapi"]),
                f"bos_kapi={[x['kapi'] for x in K['bos_kapi']][:4]}")
        kontrol("kapilar: eksik dosya (3 cihaz) kayda gecer",
                len(K["eksik_dosya"]) == len(V2.CIHAZLAR),
                f"eksik={len(K['eksik_dosya'])}")


# ------------------------------- GOREV_0014 ORTA: edisyonlar geometriyi paylasir
def _sahte_urun(duzen_per_ed, cikti):
    """kapilar icin en kucuk gercek girdi: cihaz basina kucuk JPEG + plaka PNG."""
    urun = {}
    for ed, duzen in duzen_per_ed.items():
        for dev in V2.CIHAZLAR:
            W, H = V2.DEVICES[dev]
            im = np.full((H, W, 3), 200, np.uint8)
            yol = Path(cikti) / f"{ed}_{dev}.jpg"; plaka = Path(cikti) / f"P_{ed}_{dev}.png"
            cv2.imwrite(str(yol), im); cv2.imwrite(str(plaka), im)
            urun[(ed, dev)] = {"yol": str(yol), "plaka": str(plaka), "geom": None,
                               "kapi1": {"gecti": True}, "kutu_duzen": duzen}
    return urun


def t_geometri_paylasim():
    import tempfile as _t
    duzen = {"sol": [1500, 3900, 3000, 4500], "sag": [4200, 3900, 5700, 4500],
             "sonsuz": [3400, 4000, 3800, 4400], "mesaj": [1600, 6000, 5600, 6300]}
    baska = dict(duzen, mesaj=[1600, 6000, 5660, 6300])      # farkli mesaj kutusu (60 px)
    with _t.TemporaryDirectory() as td:
        u = _sahte_urun({"BLUE": duzen, "BLACK": duzen}, td)
        K = V2.kapilar(u, None, {"kutular": duzen}, "", "X", Path(td) / "K1", ["BLUE", "BLACK"])
        kontrol("geometri_paylasim: ayni duzen -> sapma 0 gecer",
                all(x["gecti"] for x in K["geometri_paylasim"])
                and len(K["geometri_paylasim"]) == 2 * len(V2.CIHAZLAR),
                f"kayit={len(K['geometri_paylasim'])} sapma=0")
        u2 = _sahte_urun({"BLUE": duzen, "BLACK": baska}, td)
        K2 = V2.kapilar(u2, None, {"kutular": duzen}, "", "X", Path(td) / "K2", ["BLUE", "BLACK"])
        kot = [x for x in K2["geometri_paylasim"] if not x["gecti"]]
        kontrol("geometri_paylasim: edisyonlar farkli duzen kullandi -> FAIL",
                bool(kot) and K2["gecti"] is False, f"sapma={kot[0]['sapma_px'] if kot else '-'}")


# --------------------------------- GOREV_0014 YUKSEK2: kirpma yok (olcekle ya da reddet)
class _P12:
    """kisisel-v1 render yerine: genisligi len(isim)*cap*olcek ile oranli plaka."""
    BIRIM = 60.0

    @staticmethod
    def plaka(isim, prof, cap, olcek):
        from PIL import Image as _I
        w = max(int(round(len(isim) * cap * olcek / _P12.BIRIM * 100)), 4)
        h = max(int(round(cap * olcek)), 4)
        a = np.zeros((h + 20, w + 20, 4), np.uint8)
        a[10:10 + h, 10:10 + w] = 255                      # kenarda 10 px bosluk
        return _I.fromarray(a), None


class _P6:
    TAG_FONT, TAG_W = "sahte.ttf", 700

    @staticmethod
    def cap_punto(fp, tag_w, cap):
        return max(int(round(cap * 1.4)), 8)

    @staticmethod
    def ciz_cap(fp, tag_w, punto, metin):
        from PIL import Image as _I
        w = max(int(round(len(metin) * punto * 0.62)), 4)
        a = np.zeros((punto + 20, w + 20, 4), np.uint8)
        a[10:10 + punto, 10:10 + w] = 255
        return _I.fromarray(a), 0, 0


class _P7:
    @staticmethod
    def kuyruk_duzlestir(prof):
        return None, None

    @staticmethod
    def altin_sekil(cr, p1, cu_ct):
        return cr


class _kp:
    FONT_DIR = Path(".")


def _geo(cap=200, mesaj_cap=150):
    orta = SP.POSTER_W // 2
    return {"cap": cap, "mesaj_cap": mesaj_cap,
            "sol": [1500, 3000], "sag": [4200, 5700],
            "sonsuz": [orta - 200, 4000, orta + 200, 4400],
            "isim_govde": [3900, 4500], "mesaj_govde": [6000, 6300]}


def t_isim_kirpilmaz():
    prof = {"sol": None, "sag": None, "tag": None}
    yer, dx, b = V2.metin_katmani(_P6, _P7, _P12, _kp, _geo(), prof,
                                  {"sol": "MIA", "sag": "LEO"}, "Where it all began")
    kontrol("metin_katmani: normal isimler olceklenmez (olcek 1.0)",
            b["isim_olcek"] == 1.0 and b["satir"] <= b["isim_sinir"],
            f"satir={b['satir']} sinir={b['isim_sinir']}")
    # 11 harf, en genis harflerle: eskiden olcek sabit 1.0 idi -> tuval disi KIRPILIYORDU
    yer2, dx2, b2 = V2.metin_katmani(_P6, _P7, _P12, _kp, _geo(), prof,
                                     {"sol": "W" * 11, "sag": "W" * 11}, "Where it all began")
    kontrol("metin_katmani: 11 harf WWWWWWWWWWW kuculur ve SIGAR (kirpma yok)",
            b2["isim_olcek"] < 1.0 and b2["satir"] <= b2["isim_sinir"] and b2["isim_pay_px"] >= 0,
            f"olcek={b2['isim_olcek']} satir={b2['satir']}/{b2['isim_sinir']} "
            f"pay={b2['isim_pay_px']} adim={len(b2['isim_kucultme'])}")
    # taban olcege inildigi halde sigmiyorsa REDDEDILIR
    m = durur(V2.metin_katmani, _P6, _P7, _P12, _kp, _geo(cap=900), prof,
              {"sol": "W" * 40, "sag": "W" * 40}, "kisa")
    kontrol("metin_katmani: tabana inince bile sigmiyorsa REDDEDILIR",
            "REDDEDILDI" in (m or "") and "kirpma yapilmaz" in (m or ""), (m or "")[:90])


def t_mesaj_sigar():
    prof = {"sol": None, "sag": None, "tag": None}
    m35 = "W" * 35                                   # 35 karakter, en genis harf
    yer, dx, b = V2.metin_katmani(_P6, _P7, _P12, _kp, _geo(mesaj_cap=400), prof,
                                  {"sol": "MIA", "sag": "LEO"}, m35)
    kontrol("metin_katmani: 35 karakter mesaj kuculur ve sinira SIGAR",
            b["mesaj_genislik"] <= b["mesaj_sinir"],
            f"genislik={b['mesaj_genislik']} sinir={b['mesaj_sinir']} punto={b['mesaj_punto']} "
            f"olcek={b['mesaj_olcek']}")
    mm = durur(V2.metin_katmani, _P6, _P7, _P12, _kp, _geo(), prof,
               {"sol": "MIA", "sag": "LEO"}, "W" * 2000)
    kontrol("metin_katmani: sigmayan mesaj REDDEDILIR (taban punto)",
            "REDDEDILDI" in (mm or ""), (mm or "")[:90])


# ------------------------- GOREV_0014 ORTA: 35 karakter + aksanli harf kapsami
def t_girdi_dogrula():
    _g = importlib.util.spec_from_file_location("girdi_dogrula", Path(__file__).resolve().parent / "girdi_dogrula.py")
    GD = importlib.util.module_from_spec(_g); _g.loader.exec_module(GD)
    kontrol("mesaj_dogrula: 35 karakter gecer", GD.mesaj_dogrula("W" * 35) == "W" * 35)
    kontrol("mesaj_dogrula: 36 karakter REDDEDILIR",
            "REDDEDILDI" in (durur(GD.mesaj_dogrula, "W" * 36) or ""))
    kontrol("isim_dogrula: 31 karakter REDDEDILIR",
            "REDDEDILDI" in (durur(GD.isim_dogrula, "A" * 31) or ""))
    kontrol("isim_dogrula: bos isim DURduruyor", "bos" in (durur(GD.isim_dogrula, "  ") or ""))
    font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if font.exists():
        kontrol("font_kapsami: aksanli harfler (U-umlaut, E-accent, dotless i) tam",
                GD.eksik_glifler(font, "ÜÉIıiŞğ") == [], f"eksik={GD.eksik_glifler(font, 'ÜÉIıiŞğ')}")
        # cmap'te OLMAYAN karakterler (olculdu: DejaVuSans'ta CJK ve PUA yok)
        eksik = GD.eksik_glifler(font, "AB\u4e2d\ue123")
        kontrol("font_kapsami: fontta olmayan karakter YAKALANIR",
                eksik == ["\u4e2d", "\ue123"], f"{eksik}")
        kontrol("font_kapsami_dogrula: eksik glif REDDEDILIR",
                "REDDEDILDI" in (durur(GD.font_kapsami_dogrula, font, "A\u4e2d") or ""))
        kontrol("font_kapsami: cmap format sirasi (12 tercih)",
                GD.cmap_altlari(font)[1][0][0] == 12, f"{[x[0] for x in GD.cmap_altlari(font)[1]]}")
    else:
        kontrol("font_kapsami: test fontu yok (atlandi)", True, str(font))


# ------------------------------------------------- GOREV_0014 HIZ: esdeger matematik
def t_hizli_referans():
    """murekkep 'hizli' yolu (cebirsel sadelestirme) referans yolla BIREBIR ayni
    maskeyi vermeli - hiz icin karar degismez."""
    rng = np.random.default_rng(11)
    ayni = True
    ayrinti = ""
    for ed in ("Midnight_Blue", "Warm_Parchment", "BILINMEYEN"):
        for _ in range(2):
            plate = rng.integers(0, 256, (140, 160, 3), dtype=np.uint8)
            baski = plate.copy()
            m = rng.random((140, 160)) < 0.3
            baski[m] = rng.integers(0, 256, (int(m.sum()), 3), dtype=np.uint8)
            cikti = []
            for yol in ("referans", "hizli"):
                for hayalet in ("birak", "gecir"):
                    f, a, ao, tn = SP.murekkep(baski, plate, ed, hayalet, "uzaklik", yol=yol)
                    cikti.append((np.asarray(f).copy(), np.asarray(a).copy(), ao.copy(),
                                  tn["poz_px"], tn["neg_px"], tn["yonsuz_px"]))
            yarim = len(cikti) // 2
            for r, h in zip(cikti[:yarim], cikti[yarim:]):
                for i in range(3):
                    if not np.array_equal(r[i], h[i]):
                        ayni = False; ayrinti = f"{ed}: dizi {i} farkli"
                if r[3:] != h[3:]:
                    ayni = False; ayrinti = f"{ed}: sayimlar {r[3:]} != {h[3:]}"
    kontrol("murekkep: hizli yol referans yolla BIREBIR ayni (6 senaryo)", ayni, ayrinti)


def t_sadece_olcum():
    rng = np.random.default_rng(3)
    plate = rng.integers(0, 256, (80, 90, 3), dtype=np.uint8)
    baski = plate.copy(); baski[10:20, 10:20] = 250
    f, a, ao, tn = SP.murekkep(baski, plate, "Midnight_Blue", "birak", "uzaklik")
    f2, a2, ao2, tn2 = SP.murekkep(baski, plate, "Midnight_Blue", "birak", "uzaklik",
                                   sadece_olcum=True)
    kontrol("murekkep: sadece_olcum ayni olcum maskesini verir, fark/alfa uretmez",
            np.array_equal(ao, ao2) and f2 is None and a2 is None and tn == tn2,
            f"poz={tn['poz_px']}")


if __name__ == "__main__":
    for t in (t_uc_grup, t_murekkep, t_murekkep_rengi, t_dosya_bul, t_olcu_kontrolu,
              t_kapilar_klasor, t_halka_guard, t_bos_cikti, t_bos_kapi, t_geometri_paylasim,
              t_isim_kirpilmaz, t_mesaj_sigar, t_girdi_dogrula, t_hizli_referans,
              t_sadece_olcum):
        t()
    print(f"\nTOPLAM {len(GECTI) + len(KALDI)} kontrol, {len(GECTI)} PASS, {len(KALDI)} FAIL")
    sys.exit(1 if KALDI else 0)
