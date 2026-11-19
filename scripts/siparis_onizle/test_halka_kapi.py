#!/usr/bin/env python3
"""halka_kapi testi (18 Kas V2B; 19 Kas GOREV HALKA_KALICI D5). Ag kapali, sentetik 11x14 (3300x4200) koyu mavi radyal zemin + altin yay
+ kanal basina gren; gercek goruntu YOK. Gercek fonksiyonlar kosar (halka_kapi.kapi, halka_kodla.ycc_kaydet / onizleme).
Bilinen PASS: kaynak yeni kodlamayla (YCbCr TPDF + kroma gurultusu q100) kodlanir. Bilinen FAIL: kaynaga 0.35 duzey mavi halka. ESIK KENARI:
kaynaga 0.04 duzey halka (kodlama bandi ~0.02-0.025, KODLAMA_ESIK 0.020 ile 0.025 arasi) FAIL vermeli; esik 0.025'e gevsetilirse bu test
FAIL olur. Tavan kenari: mutlak bant 0.10 ustu kaynak (halka 0.30) FAIL. Kaynak yok / boyut farkli / tur yanlis: PASS verilmez."""
import socket
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok
B = Path(__file__).resolve().parent
sys.path.insert(0, str(B)); sys.path.insert(0, str(B / "halka_yama"))
import halka_kapi as HK  # noqa: E402
import halka_kodla as KD  # noqa: E402
import zemin_duzelt as Z  # noqa: E402

HATA = []


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


def kaynak(halka, H=4200, W=3300):
    cx, cy, _ = Z.merkez("11x14"); k = W / 3300
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.hypot(xx - cx * k, yy - cy * k)
    a = np.empty((H, W, 3), np.float32)
    a[..., 0] = 4 + 6 * np.exp(-r / (900 * k)); a[..., 1] = 6 + 10 * np.exp(-r / (900 * k)); a[..., 2] = 20 + 40 * np.exp(-r / (900 * k))
    if halka:
        a[..., 2] += halka * np.sin(2 * np.pi * r / (180 * k)) * (r < 1500 * k)
    yay = (np.abs(r - 1100 * k) < 6 * k) & (yy < cy * k); a[yay] = (212, 160, 50)
    a += np.random.default_rng(3).standard_normal(a.shape).astype(np.float32) * 1.5
    return np.clip(a, 0, 255)


with tempfile.TemporaryDirectory() as t:
    td = Path(t); o = td / "o"; rng = np.random.default_rng(1)
    temiz = kaynak(0.0); KD.kaynak_yaz(temiz, td / "temiz.jpg"); ref = td / "temiz_REF.png"
    KD.ycc_kaydet(temiz, td / "yeni.jpg", rng)
    r = HK.kapi(td / "yeni.jpg", "11x14", o, "baski", kaynak=ref)
    kontrol("bilinen PASS: yeni kodlama, kodlama bandi <= 0.020 ve tavan alti", r["PASS"] is True, str({k: r.get(k) for k in ("halka_bant", "kodlama_bant")}))
    for ad, h, bek_kod in (("bilinen FAIL: 0.35 duzey halka", 0.35, None), ("ESIK KENARI FAIL: 0.04 duzey halka (esik gevsetilirse bu test duser)", 0.04, (0.020, 0.025))):
        KD.ycc_kaydet(kaynak(h), td / "kotu.jpg", np.random.default_rng(2))
        r = HK.kapi(td / "kotu.jpg", "11x14", o, "baski", kaynak=ref)
        kb = r.get("kodlama_bant") or 0
        kontrol(ad, r["PASS"] is False and kb > HK.KODLAMA_ESIK["baski"] and (bek_kod is None or bek_kod[0] < kb < bek_kod[1]), str(kb))
    kontrol("esikler: kodlama baski 0.020, onizleme 0.040; tavan 0.10 (olcumle; gevsetme testte yakalanir)",
            HK.KODLAMA_ESIK == {"baski": 0.020, "onizleme": 0.040} and HK.TAVAN == {"baski": 0.10, "onizleme": 0.10})
    cok = kaynak(0.30); KD.kaynak_yaz(cok, td / "cok.jpg"); KD.ycc_kaydet(cok, td / "cok.jpg", np.random.default_rng(4))
    r = HK.kapi(td / "cok.jpg", "11x14", o, "baski", kaynak=td / "cok_REF.png")
    kontrol("TAVAN FAIL: kaynaginda halka olan dosya (kodlama temiz olsa bile) mutlak bant > 0.10", r["PASS"] is False and (r.get("halka_bant") or 0) > 0.10
            and (r.get("kodlama_bant") or 1) <= HK.KODLAMA_ESIK["baski"], str({k: r.get(k) for k in ("halka_bant", "kodlama_bant")}))
    r = HK.kapi(td / "yeni.jpg", "11x14", o, "baski")
    kontrol("kaynak verilmezse PASS verilmez", r["PASS"] is False and r.get("kodlama_bant") is None)
    r = HK.kapi(td / "yeni.jpg", "11x14", o, "onizleme", kaynak=ref)
    kontrol("tur onizleme ama boyut baski: FAIL", r["PASS"] is False and "hata" in r)
    r = HK.kapi(td / "yeni.jpg", "11x14", o, "yanlis", kaynak=ref)
    kontrol("tur yanlis: FAIL", r["PASS"] is False and "hata" in r)
    # onizleme: uretim yolu (kayan nokta LANCZOS + ayni kodlama, kaynak=True) PASS; eski yol (8 bit LANCZOS + q92) FAIL
    KD.onizleme(temiz, td / "on.jpg", np.random.default_rng(5), kaynak=True)
    r = HK.kapi(td / "on.jpg", "11x14", o, "onizleme", kaynak=td / "on_REF.png")
    kontrol("onizleme bilinen PASS: uretim yolu (kodlama bandi <= 0.03)", r["PASS"] is True and Image.open(td / "on.jpg").size == (1571, 2000), str(r.get("kodlama_bant")))
    Image.fromarray(np.clip(np.rint(temiz), 0, 255).astype(np.uint8)).resize((1571, 2000), Image.LANCZOS).save(td / "on_eski.jpg", quality=92, subsampling=0)
    r = HK.kapi(td / "on_eski.jpg", "11x14", o, "onizleme", kaynak=td / "on_REF.png")
    kontrol("onizleme bilinen FAIL: eski yol (8 bit LANCZOS + q92)", r["PASS"] is False and (r.get("kodlama_bant") or 0) > HK.KODLAMA_ESIK["onizleme"], str(r.get("kodlama_bant")))
    Image.open(ref).resize((100, 100)).save(td / "kucuk_REF.png")
    r = HK.kapi(td / "yeni.jpg", "11x14", o, "baski", kaynak=td / "kucuk_REF.png")
    kontrol("kaynak boyutu farkli: FAIL", r["PASS"] is False and "hata" in r)
    kontrol("kontrol goruntusu yazildi (baski yarim boy)", Image.open(o / "KONTROL_maviHP25_yeni.jpg").size == (1650, 2100))
with tempfile.TemporaryDirectory() as t2:                      # inceleme G ORTA 10: TAVAN kenari (0.10-0.12 FAIL, 0.08-0.10 PASS)
    td2 = Path(t2)
    for ad, h, ara, bek in (("TAVAN KENARI FAIL (0.10-0.12; tavan gevsetilirse test duser)", 0.19, (0.10, 0.12), False),
                            ("TAVAN KENARI PASS (0.08-0.10)", 0.15, (0.08, 0.10), True)):
        src = kaynak(h); KD.kaynak_yaz(src, td2 / "k.jpg"); KD.ycc_kaydet(src, td2 / "k.jpg", np.random.default_rng(6))
        r = HK.kapi(td2 / "k.jpg", "11x14", td2 / "o", "baski", kaynak=td2 / "k_REF.png")
        hb = r.get("halka_bant") or 0
        kontrol(ad, r["PASS"] is bek and ara[0] < hb < ara[1] and (r.get("kodlama_bant") or 1) <= HK.KODLAMA_ESIK["baski"], f"halka_bant {hb} kodlama {r.get('kodlama_bant')}")
kontrol("olcuye duyarli esik: 5x7 (1500x2100) baski 0.030; 8x10 (2400x3000) ve 11x14 baski 0.020; onizleme her olcude 0.040",
        HK.kodlama_esigi("baski", 1500, 2100) == 0.030 and HK.kodlama_esigi("baski", 2400, 3000) == 0.020 and HK.kodlama_esigi("baski", 3300, 4200) == 0.020
        and HK.kodlama_esigi("onizleme", 1500, 2000) == 0.040)
print("halka_kapi testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
