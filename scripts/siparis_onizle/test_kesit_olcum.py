#!/usr/bin/env python3
"""kesit_olcum.py testi (18 Kas, siparis baski yardimcisi). Ag kapali (CLAUDE.md TEST AGI); musteri verisi yok, sahte isimler.
Sentetik MB 11x14 teslim dosyasi (3300x4200, 300 dpi, 4:4:4): lacivert zemin + 4 altin bant (ana, kucuk semboller, isim satiri, mesaj).
Bilinen PASS: Format Print ve Digital File. Bilinen FAIL: bilinmeyen Format, sag kenarda kirmizi 3x2 nokta, yanlis olcu, isim farki,
uretim kapisi FAIL. Bilgi: kenar disi kirmizi nokta karar vermez."""
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kesit_olcum import boyut_siniri as KO_SINIR  # noqa: E402


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok

KOK = Path(__file__).resolve().parents[2]
BETIK = KOK / "scripts/siparis_onizle/kesit_olcum.py"
HATA = []
KOK_AD = "AstroLoveArt_Cancer_Leo_Midnight_Blue"
GOLD, ZEMIN, KIRMIZI = (212, 175, 55), (20, 30, 70), (230, 20, 20)


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


def poster(W=3300, H=4200, nokta=None):
    a = np.zeros((H, W, 3), np.uint8); a[:] = ZEMIN
    s = W / 3300
    def kut(x0, y0, x1, y1):
        a[int(y0 * H / 4200):int(y1 * H / 4200), int(x0 * s):int(x1 * s)] = GOLD
    kut(1000, 600, 2300, 2000)                                   # ana sembol
    kut(300, 2750, 500, 2900); kut(2800, 2750, 3000, 2900)       # kucuk semboller (iki yanda)
    kut(500, 3100, 1200, 3220); kut(1500, 3100, 1800, 3220); kut(2100, 3100, 2800, 3220)   # isim1, sonsuz, isim2
    kut(900, 3550, 2400, 3650)                                   # mesaj
    if nokta:
        x, y = nokta
        a[y:y + 2, x:x + 3] = KIRMIZI                            # 3x2 px
    return Image.fromarray(a)


def kur(d, fmt="Print", W=3300, H=4200, nokta=None, isim1_etsy="Milo", kapi=True, isim2_etsy="Harper", mesaj_etsy="Always-and-Forever Yours",
        boy_etsy="11x14 in", renk_etsy="Midnight Blue", dpi=300, ornek=0, eksik=(), kapi_eski=False, kosu="777"):
    ur = d / "ur"; ur.mkdir(parents=True)
    json.dump(dict(cift="CANCER_LEO", isim1="Milo", isim2="Harper", tagline="Always-and-Forever Yours", olcu="11x14",
                   renk_secim="MIDNIGHT_BLUE"), open(ur / "siparis.json", "w"))
    teslim = ur / f"{KOK_AD}_11x14.jpg"
    poster(W, H, nokta).save(teslim, quality=95, subsampling=ornek, dpi=(dpi, dpi))
    bayt = teslim.stat().st_size + (1 if kapi_eski else 0)          # eski kosunun KAPI.json'u: bayt tutmaz
    json.dump({"a": {"PASS": kapi}, "g": {"PASS": True, "dosya": "AstroLoveArt_Cancer_Leo_11x14.jpg", "olcu": "11x14", "bayt": bayt},
               "PASS": kapi}, open(ur / "KAPI.json", "w"))
    json.dump({"kosu": kosu}, open(ur / "SURE.json", "w"))
    poster(800, 1200).save(ur / f"{KOK_AD}_2000.jpg", quality=90)
    for e in eksik:
        (ur / e).unlink()
    var = [dict(ad="Name under Cancer", deger=isim1_etsy), dict(ad="Name under Leo", deger=isim2_etsy),
           dict(ad="Your message", deger=mesaj_etsy), dict(ad="Color", deger=renk_etsy),
           dict(ad="Size", deger=boy_etsy), dict(ad="Format", deger=fmt)]
    json.dump({"kalemler": [{"varyasyon": var}]}, open(d / "KISISEL.json", "w"))
    return ur


AGSIZ = ("import socket, sys, runpy\ndef _y(*a, **k): raise AssertionError('ag')\n"
         "socket.socket.connect = _y; socket.create_connection = _y\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n")


def kos(bek="Print", uretim_kosu="", **kw):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); ur = kur(d, **kw)
        r = subprocess.run([sys.executable, "-I", "-c", AGSIZ, str(BETIK), str(ur), str(d / "KISISEL.json"), str(d / "out")], capture_output=True,
                           text=True, timeout=300, env={"PATH": os.environ.get("PATH", ""), "BEKLENEN_FORMAT": bek, "URETIM_KOSU": uretim_kosu})
        oz = json.load(open(d / "out/KESIT_OZET.json")) if (d / "out/KESIT_OZET.json").exists() else {}
        kesit = sorted(p.name for p in (d / "out").glob("KESIT_1x1_*.jpg")) if (d / "out").exists() else []
        return r.returncode, oz, kesit, r.stderr[-400:]


rc, oz, kes, err = kos()
kontrol("bilinen PASS: Format Print, temiz kenar -> cikis 0, tum kapilar PASS", rc == 0 and oz.get("PASS") is True, f"rc={rc} {err}")
kontrol("format alani 'baski', kirmizi nokta 0, kesit dosyasi yazildi",
        oz.get("girdi", {}).get("format") == "baski" and oz.get("kirmizi_nokta", {}).get("PASS") is True
        and kes == [f"KESIT_1x1_{KOK_AD}_11x14.jpg"], str(oz.get("kirmizi_nokta")))
kontrol("musteri onizlemesi 11x14 teslimden: 1571x2000, oran ayni, ad _11x14_Preview",
        oz.get("onizleme", {}).get("musteri_boyut") == [1571, 2000] and oz["onizleme"].get("musteri_oran_ayni") is True
        and oz["onizleme"].get("musteri") == f"{KOK_AD}_11x14_Preview.jpg", str(oz.get("onizleme")))
kontrol("kesit isim ve mesaji kapsiyor, teslim 3300x4200 / 300 dpi / 4:4:4, sha256 degismedi",
        oz.get("kesit", {}).get("kesit_isim_ve_mesaji_kapsiyor") is True and oz.get("teslim", {}).get("boyut") == [3300, 4200]
        and oz.get("teslim", {}).get("dpi") == [300, 300] and oz.get("teslim", {}).get("sha256_degismedi") is True)
rc, oz, kes, err = kos(fmt="Digital File", bek="Digital File")
kontrol("bilinen PASS: Format Digital File (dijital siparis beklentisiyle)", rc == 0 and oz.get("girdi", {}).get("format") == "dijital", f"rc={rc}")
rc, oz, kes, err = kos(fmt="Digital File")
kontrol("bilinen FAIL: baski siparisinde Format Digital File", rc == 1 and oz["girdi"].get("format_gecerli") is False)
rc, oz, kes, err = kos(boy_etsy="11\u2033 \u00d7 14\u2033")
kontrol("bilinen PASS: Etsy Size 11\u2033 \u00d7 14\u2033 bicimi", rc == 0 and oz["girdi"].get("olcu_ayni") is True, f"rc={rc}")
for ad, kw, alan in (("isim2 farki", dict(isim2_etsy="Harpe"), "isim2_ayni"), ("mesaj farki (tek tire)", dict(mesaj_etsy="Always-and Forever Yours"), "mesaj_ayni"),
                     ("renk farki", dict(renk_etsy="Deep Black"), "renk_ayni"), ("olcu farki", dict(boy_etsy="16x20 in"), "olcu_ayni"),
                     ("bos isim", dict(isim1_etsy=""), "isim1_ayni")):
    rc, oz, kes, err = kos(**kw)
    kontrol(f"bilinen FAIL: {ad}", rc == 1 and oz.get("girdi", {}).get(alan) is False, str(oz.get("girdi")))
for ad, kw, bolum in (("yanlis dpi (72)", dict(dpi=72), "teslim"), ("4:2:0 ornekleme", dict(ornek=2), "teslim"),
                      ("onizleme yok", dict(eksik=(f"{KOK_AD}_2000.jpg",)), "onizleme"), ("KAPI.json yok", dict(eksik=("KAPI.json",)), "uretim_kapilari"),
                      ("eski kosunun KAPI.json'u (bayt tutmaz)", dict(kapi_eski=True), "uretim_kapilari")):
    rc, oz, kes, err = kos(**kw)
    kontrol(f"bilinen FAIL: {ad}", rc == 1 and oz.get(bolum, {}).get("PASS") is False, f"rc={rc} {oz.get(bolum)} {err}")
rc, oz, kes, err = kos(eksik=(f"{KOK_AD}_11x14.jpg",))
kontrol("bilinen FAIL: teslim dosyasi yok", rc == 1 and oz.get("teslim", {}).get("PASS") is False and oz.get("kirmizi_nokta", {}).get("PASS") is False)
rc, oz, kes, err = kos(uretim_kosu="888")
kontrol("bilinen FAIL: SURE.json kosu no farkli", rc == 1 and oz.get("uretim_kapilari", {}).get("kosu_ayni") is False)
rc, oz, kes, err = kos(uretim_kosu="777")
kontrol("bilinen PASS: SURE.json kosu no ayni", rc == 0 and oz.get("uretim_kapilari", {}).get("kosu_ayni") is True)
rc, oz, kes, err = kos(fmt="Something Else")
kontrol("bilinen FAIL: bilinmeyen Format", rc == 1 and oz.get("girdi", {}).get("PASS") is False and oz["girdi"].get("format_gecerli") is False)
rc, oz, kes, err = kos(nokta=(3300 - 3, 2000))
kn = oz.get("kirmizi_nokta", {})
kontrol("bilinen FAIL: sag kenarda sentetik kirmizi 3x2 nokta", rc == 1 and kn.get("PASS") is False and kn.get("sag", {}).get("piksel", 0) > 0
        and kn["sag"]["kutu"][0] >= 3300 - 10, str(kn))
rc, oz, kes, err = kos(nokta=(5, 1000))
kontrol("bilinen FAIL: sol kenarda kirmizi nokta", rc == 1 and oz.get("kirmizi_nokta", {}).get("sol", {}).get("piksel", 0) > 0)
rc, oz, kes, err = kos(nokta=(3300 - 13, 2000))
kontrol("sinir (Merkez tanimi 10 px): kenardan 10 px iceride nokta kenar seridinde sayilmaz, bilgi sayacinda gorunur",
        rc == 0 and oz.get("kirmizi_nokta", {}).get("tum_goruntu_piksel", 0) > 0)
rc, oz, kes, err = kos(nokta=(1600, 2300))
kontrol("bilgi: kenar disi kirmizi nokta karar vermez (PASS), sayilir", rc == 0 and oz.get("kirmizi_nokta", {}).get("PASS") is True
        and oz["kirmizi_nokta"].get("tum_goruntu_piksel", 0) > 0, str(oz.get("kirmizi_nokta")))
rc, oz, kes, err = kos(W=2400, H=3000)
kontrol("bilinen FAIL: yanlis olcu (2400x3000)", rc == 1 and oz.get("teslim", {}).get("PASS") is False)
rc, oz, kes, err = kos(isim1_etsy="Mila")
kontrol("bilinen FAIL: isim1 Etsy okumasiyla harf harf ayni degil", rc == 1 and oz.get("girdi", {}).get("isim1_ayni") is False)
rc, oz, kes, err = kos(kapi=False)
kontrol("bilinen FAIL: uretim kapisi FAIL", rc == 1 and oz.get("uretim_kapilari", {}).get("PASS") is False)
kontrol("boyut siniri (Serdar karar 1): Print 100 MB, Digital File 20 MB, bilinmeyen 20 MB",
        KO_SINIR("Print") == 100_000_000 and KO_SINIR("Digital File") == 20_000_000 and KO_SINIR("") == 20_000_000)
# onizleme denetimi (V2B ORTA bulgu): gercek fonksiyon, bilinen PASS + bilinen FAIL (kendi urettigi dosyaya bagli degil)
sys.path.insert(0, str(BETIK.parent)); import kesit_olcum as KO  # noqa: E402
with tempfile.TemporaryDirectory() as td:
    td = Path(td); tes = td / "t.jpg"; poster().save(tes, quality=95, subsampling=0)
    with Image.open(tes) as a:
        a.resize((1571, 2000), Image.LANCZOS).save(td / "iyi.jpg", quality=92)
        a.resize((1257, 1600), Image.LANCZOS).save(td / "kucuk.jpg", quality=92)
    poster(800, 1200).resize((1333, 2000)).save(td / "ana23.jpg", quality=92)                        # 2:3 ana kopyadan (yanlis kaynak)
    p2 = poster(nokta=None); Image.fromarray(np.asarray(p2)[::-1].copy()).resize((1571, 2000)).save(td / "baska.jpg", quality=92)  # ayni oran, baska icerik
    Image.new("RGB", (1571, 2000), ZEMIN).save(td / "bos.jpg", quality=92)
    KO.onizleme_yap(tes, td / "yap.jpg")
    with Image.open(td / "yap.jpg") as q:
        kontrol("onizleme_yap: 1571x2000, 300 dpi, kroma tablosu tum 1, 4:4:4", q.size == (1571, 2000) and tuple(round(v) for v in q.info.get("dpi", (0, 0))) == (300, 300)
                and set(q.quantization[1]) == {1} and q.layer[0][1:3] == q.layer[1][1:3], str((q.size, q.info.get("dpi"))))
    kontrol("onizleme_yap ciktisi denetimden gecer", KO.onizleme_denetle(tes, td / "yap.jpg")["musteri_PASS"] is True)
    d = KO.onizleme_denetle(tes, td / "iyi.jpg")
    kontrol("onizleme denetimi bilinen PASS: teslimden 1571x2000", d["musteri_PASS"] is True and d["musteri_icerik_fark"] < 4, str(d))
    for ad, f in (("uzun kenar 1600", "kucuk.jpg"), ("2:3 ana kopyadan", "ana23.jpg"), ("ayni oran baska icerik (ters)", "baska.jpg"), ("duz zemin", "bos.jpg")):
        d = KO.onizleme_denetle(tes, td / f)
        kontrol(f"onizleme denetimi bilinen FAIL: {ad}", d["musteri_PASS"] is False, str(d))

print("kesit_olcum testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
