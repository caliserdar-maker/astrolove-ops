"""halka_kodla.tablolar / ycc_kaydet(qtables) ve dijital_kodlama_olc testi (21 Kas, dijital 20 MB). Ag YOK, sentetik goruntu.
1) qtables=None: bugunku q100 yolu ile BAYT BAYT ayni (d2b414ee + halka_yama 19 Kas davranisi; ayni rng).
2) tablolar(95, 2): kayitli dosyanin luma tablosu standart q95, kroma tablolari duz 2; tablolar(100, 1) tum 1.
3) Bilinen FAIL: ayni kaynak Pillow standart q95 (kroma tablosu standart) kodlamasi halka_kapi kodlama bandini yukseltir; L95_C2 daha dusuk.
4) dijital_kodlama_olc.olc: sigmayan aday (bayt >= PAY) halka olcusune girmez; sigan ilk aday ve sonraki olculur; PASS yoksa secilen None
   (sahte kapi ile; gercek kodlama fonksiyonu kosar)."""
import io
import os
import socket
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "halka_yama"))


def _ag_yok(*a, **k):
    raise OSError("test: ag kapali")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok

import halka_kodla as KD  # noqa: E402
import halka_kapi as HK  # noqa: E402
import dijital_kodlama_olc as DK  # noqa: E402

SONUC = []


def kontrol(ad, ok):
    SONUC.append(bool(ok)); print(("PASS " if ok else "FAIL ") + ad)


def zemin(w=1100, h=1400, seed=3):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32); d = np.hypot(x - w / 2, y - h * 0.4) / max(w, h)
    F = np.stack([6 + 8 * (1 - d), 12 + 14 * (1 - d), 40 + 40 * (1 - d)], -1)
    return F + r.standard_normal((h, w)).astype(np.float32)[..., None] * 1.5


def eski_ycc_kaydet(rgb, yol, rng, agirlik=None, kroma_sigma=KD.KROMA_SIGMA):
    """19 Kas surumunun aynen kopyasi (karsilastirma tabani)."""
    H = rgb.shape[0]; ycc8 = np.empty(rgb.shape, np.uint8)
    for y0 in range(0, H, 1200):
        s = rgb[y0:y0 + 1200].astype(np.float32) @ KD.YCC.T; s[..., 1:] += 128
        ag = None if agirlik is None else np.asarray(agirlik[y0:y0 + 1200], np.float32)[..., None]
        tp = rng.random(s.shape, dtype=np.float32) - rng.random(s.shape, dtype=np.float32)
        s += tp if ag is None else tp * ag
        if kroma_sigma:
            g = rng.standard_normal(s[..., 1:].shape, dtype=np.float32) * kroma_sigma
            s[..., 1:] += g if ag is None else g * ag
        ycc8[y0:y0 + 1200] = np.clip(np.rint(s), 0, 255).astype(np.uint8)
    Image.fromarray(ycc8, 'YCbCr').save(yol, 'JPEG', quality=100, subsampling=0, dpi=(300, 300))


def main():
    F = zemin()
    with tempfile.TemporaryDirectory() as td:
        a, b = f"{td}/a.jpg", f"{td}/b.jpg"
        KD.ycc_kaydet(F, a, np.random.default_rng(7)); eski_ycc_kaydet(F, b, np.random.default_rng(7))
        kontrol("1 qtables=None bayt bayt eski q100 yolu", Path(a).read_bytes() == Path(b).read_bytes())
        KD.ycc_kaydet(F, b, np.random.default_rng(7), qtables=KD.tablolar(95, 2))
        kontrol("1b bilinen FAIL: L95_C2 dosyasi q100'den farkli ve kucuk", Path(a).read_bytes() != Path(b).read_bytes()
                and os.path.getsize(b) < os.path.getsize(a))
        q = Image.open(b).quantization
        bb = io.BytesIO(); Image.new("RGB", (8, 8)).save(bb, "JPEG", quality=95); q95 = list(Image.open(bb).quantization[0])
        kontrol("2 L95_C2: luma standart q95, kroma duz 2", list(q[0]) == q95 and set(q[1]) == {2} and set(q[2]) == {2})
        kontrol("2b tablolar(100,1) tum 1", all(set(t) == {1} for t in KD.tablolar(100, 1)))
        kontrol("2c ycc_tablolari L95_C2'de tum_1 False", KD.ycc_tablolari(b)["tum_1"] is False)
        # 3) halka: 16x20 olceginde degil (yavas); halka_kapi olcu kontrolu boyut ister -> 5x7 (1500x2100) sentetik
        F5 = zemin(1500, 2100, 4); ref = f"{td}/S_5x7_REF.png"
        Image.fromarray(np.clip(np.rint(F5), 0, 255).astype(np.uint8)).save(ref)
        y1, y2 = f"{td}/l95c2.jpg", f"{td}/std95.jpg"
        KD.ycc_kaydet(F5, y1, np.random.default_rng(9), qtables=KD.tablolar(95, 2))
        Image.fromarray(np.clip(np.rint(F5), 0, 255).astype(np.uint8)).save(y2, quality=95, subsampling=0, dpi=(300, 300))
        h1 = HK.kapi(y1, "5x7", f"{td}/h", "baski", kaynak=ref); h2 = HK.kapi(y2, "5x7", f"{td}/h", "baski", kaynak=ref)
        print("   kodlama bandi L95_C2", h1.get("kodlama_bant"), "standart q95", h2.get("kodlama_bant"))
        kontrol("3 bilinen FAIL: standart q95 (kroma tablosu standart) kodlama bandi L95_C2'den yuksek",
                h1.get("kodlama_bant") is not None and h2.get("kodlama_bant") is not None and h2["kodlama_bant"] > h1["kodlama_bant"])
        # 4) secim mantigi: sahte kapi (ilk olculen FAIL, ikinci PASS) ve PAY'i kucultup ilk adaylari sigmaz yapma
        cagri = []

        def sahte_kapi(y, o, c, tur, kaynak=None):
            cagri.append(Path(y).name)
            return dict(halka_bant=0.05, kodlama_bant=0.01 if len(cagri) > 1 else 0.05, kodlama_esik=0.02, tavan=0.1, PASS=len(cagri) > 1)
        eski_kapi, eski_pay = DK.HK.kapi, DK.PAY
        try:
            DK.HK.kapi = sahte_kapi
            KD.ycc_kaydet(F5, f"{td}/olc.jpg", np.random.default_rng(1), qtables=KD.tablolar(95, 1))
            DK.PAY = os.path.getsize(f"{td}/olc.jpg") + 1            # L100_C1, L98_C1 sigmaz; L95_C1 ve sonrasi sigar
            r = DK.olc(td, "S", ["5x7"], DK.ADAYLAR)["5x7"]
            olculen = [k for k, v in r["adaylar"].items() if v.get("halka")]
            kontrol("4 sigmayan adaylar olculmez, ilk sigan + sonraki olculur",
                    r["adaylar"]["L100_C1"]["sigar"] is False and "halka" not in r["adaylar"]["L100_C1"] and len(olculen) == 2
                    and r["ilk_sigan"] == olculen[0])
            kontrol("4b ilk olculen FAIL, ikinci PASS -> secilen ikinci", r["secilen"] == olculen[1] and r["PASS"] is True)
            cagri.clear()
            DK.HK.kapi = lambda *a_, **k_: dict(halka_bant=0.2, kodlama_bant=0.05, kodlama_esik=0.02, tavan=0.1, PASS=False)
            r = DK.olc(td, "S", ["5x7"], DK.ADAYLAR)["5x7"]
            kontrol("4c bilinen FAIL: hic PASS yok -> secilen None, PASS False", r["secilen"] is None and r["PASS"] is False)
            DK.PAY = 1
            r = DK.olc(td, "S", ["5x7"], DK.ADAYLAR)["5x7"]
            kontrol("4d hicbir aday sigmaz -> olcum yok, PASS False", r["ilk_sigan"] is None and r["PASS"] is False
                    and not any(v.get("halka") for v in r["adaylar"].values()))
        finally:
            DK.HK.kapi, DK.PAY = eski_kapi, eski_pay
    # 5) teslim_tablolari: yalniz TESLIM_TUR=dijital ve tablodaki olcu tablo alir; baski ve tabloda olmayan olcu q100 (None)
    eski_tt, eski_tab = os.environ.get("TESLIM_TUR"), dict(KD.DIJITAL_KODLAMA)
    try:
        KD.DIJITAL_KODLAMA.clear(); KD.DIJITAL_KODLAMA["16x20"] = "L95_C2"
        os.environ["TESLIM_TUR"] = "dijital"
        kontrol("5 dijital + tablodaki olcu -> L95_C2 tablolari", KD.teslim_tablolari("16x20") == KD.tablolar(95, 2)
                and KD.kodlama_adi("16x20") == "L95_C2")
        kontrol("5b dijital + tabloda olmayan olcu -> None (q100; 20 MB kapisi karar verir)", KD.teslim_tablolari("A2") is None
                and KD.kodlama_adi("A2") == "L100_C1")
        os.environ["TESLIM_TUR"] = "baski"
        kontrol("5c bilinen FAIL yolu: baski -> her olcude None (q100, baski degismez)", KD.teslim_tablolari("16x20") is None)
        os.environ.pop("TESLIM_TUR")
        kontrol("5d TESLIM_TUR yok -> None", KD.teslim_tablolari("16x20") is None)
    finally:
        KD.DIJITAL_KODLAMA.clear(); KD.DIJITAL_KODLAMA.update(eski_tab)
        if eski_tt is None:
            os.environ.pop("TESLIM_TUR", None)
        else:
            os.environ["TESLIM_TUR"] = eski_tt
    print(f"SONUC: {sum(SONUC)}/{len(SONUC)} PASS")
    return 0 if all(SONUC) else 1


if __name__ == "__main__":
    sys.exit(main())
