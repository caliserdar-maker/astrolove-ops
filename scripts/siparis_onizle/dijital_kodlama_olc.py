"""Dijital teslim kodlama olcumu (21 Kas 2026, GOREV_CEO_DENETIM_SIPARIS_HATTI_DIJITAL madde 1). SAHTE isimli uretimin kodlama
oncesi kaynaklari (<KOK>_<OLCU>_REF.png, halka_yama OLCU_HEPSI) her olcude ADAYLAR sirasiyla (en yuksek kaliteden asagi) YCbCr
titresimli kodlanir (halka_kodla.ycc_kaydet ile ayni yol, nicemleme tablolari degisir). Her olcude 20 MB'in (SINIR) altina giren ilk aday ve
bir sonraki aday halka_kapi ile olculur (baski: kodlama bandi <= 0.020 ve mutlak bant <= 0.10). Kapi GEVSETILMEZ: sigmayan olcu raporda FAIL.
Musteri verisi YOK. Kullanim: dijital_kodlama_olc.py REF_KLASORU KOK OLCU1,OLCU2,... CIKTI_JSON [--aday A1,A2]"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK)); sys.path.insert(0, str(KOK / "halka_yama"))
import halka_kapi as HK  # noqa: E402
import halka_kodla  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SINIR = 20_000_000
PAY = 19_500_000          # 0.5 MB pay: dpi yazimi / tohum farki (olculur; uretim kapisi yine 20 MB)
# aday adi: L<luma kalitesi>_C<kroma duz adimi>; L100 = tablolar tum 1 (bugunku baski yolu)
ADAYLAR = ["L100_C1", "L98_C1", "L95_C1", "L92_C1", "L95_C2", "L90_C2", "L90_C3", "L85_C3", "L80_C4", "L75_C5"]


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def agirlik(ref):
    """Zemin agirligi (1 zemin, 0 oge): altin (R-B > 40) ve parlak (L > 120) pikseller 7 px genisletilip oge sayilir. Uretimdeki oge
    maskesinin yaklasigi (yalniz bayt / halka olcumu icin; uretim kendi maskesini kullanir)."""
    import cv2
    a = ref.astype(np.int16)
    m = (((a[..., 0] - a[..., 2]) > 40) | (a.max(-1) > 120)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((15, 15), np.uint8))
    return (1 - m).astype(np.float32)


def kodla(F, ag, yol, aday, seed=1119):
    L, C = aday.split("_"); lq, cq = int(L[1:]), int(C[1:])
    rng = np.random.default_rng([11, seed])
    halka_kodla.ycc_kaydet(F, yol, rng, agirlik=ag, qtables=halka_kodla.tablolar(lq, cq))
    return os.path.getsize(yol)


def olc(ref_dir, kok, olculer, aday_listesi):
    out = {}
    for i, o in enumerate(olculer, 1):
        t0 = time.time()
        rp = Path(ref_dir) / f"{kok}_{o}_REF.png"
        if not rp.exists():
            out[o] = dict(hata="REF yok"); log(o, "REF yok"); continue
        R = np.asarray(Image.open(rp).convert("RGB"))
        F = R.astype(np.float32); ag = agirlik(R); del R
        satir = dict(px=list(F.shape[1::-1]), adaylar={})
        with tempfile.TemporaryDirectory() as td:
            ilk = None
            for a in aday_listesi:
                y = f"{td}/{kok}_{o}_{a}.jpg"
                b = kodla(F, ag, y, a)
                d = dict(bayt=b, mb=round(b / 1e6, 2), sigar=b < PAY)
                if b < PAY and (ilk is None or len([k for k, v in satir["adaylar"].items() if v.get("halka")]) < 2):
                    h = HK.kapi(y, o, f"{td}/h", "baski", kaynak=str(rp))
                    d["halka"] = dict(mutlak=h.get("halka_bant"), kodlama=h.get("kodlama_bant"), kodlama_esik=h.get("kodlama_esik"),
                                      tavan=h.get("tavan"), PASS=h.get("PASS"), hata=h.get("hata"))
                    ilk = ilk or a
                satir["adaylar"][a] = d
                os.remove(y)
                if ilk and len([k for k, v in satir["adaylar"].items() if v.get("halka")]) >= 2:
                    break
        sec = next((a for a, v in satir["adaylar"].items() if v.get("halka", {}).get("PASS")), None)
        satir.update(ilk_sigan=ilk, secilen=sec, PASS=sec is not None, sure_s=round(time.time() - t0, 1))
        out[o] = satir
        log(f"[{i}/{len(olculer)}] {o} ilk_sigan {ilk} secilen {sec} | {satir['sure_s']} s",
            {a: (v["mb"], (v.get("halka") or {}).get("mutlak"), (v.get("halka") or {}).get("kodlama")) for a, v in satir["adaylar"].items()})
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    adaylar = a[a.index("--aday") + 1].split(",") if "--aday" in a else ADAYLAR
    r = olc(a[0], a[1], [x for x in a[2].split(",") if x], adaylar)
    json.dump(dict(sinir=SINIR, pay=PAY, adaylar=adaylar, olculer=r), open(a[3], "w"), indent=1)
    sys.exit(0)
