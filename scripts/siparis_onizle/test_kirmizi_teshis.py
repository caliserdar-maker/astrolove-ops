"""kirmizi_teshis testi (21 Kas; ag YOK; sahte isimli MB altin kesiti, uretim dijital tablosu L85_C3).
Bilinen durumlar: koyu sacak beyaz yildizda (A ve B sacak), parlak kirmizi yildiz yaninda (A sacak, B FAIL 'parlak'), koyu kume ton ~24 altin
kenarinda (A ve B' sacak; eski B >= 28 maskesinde uzak), ic koyu nokta (A ve B FAIL; neden alan > 5 ise 'alan'). Tutarlilik: teshisin B sayilari ==
kesit_olcum.kirmizi_tara(dijital=True) (gercek kapi)."""
import io
import socket
import sys
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
import kesit_olcum as K  # noqa: E402
import kirmizi_teshis as T  # noqa: E402

SONUC = []


def kontrol(ad, ok, ek=""):
    SONUC.append(bool(ok)); print(("PASS " if ok else "FAIL ") + ad + (f" [{ek}]" if ek and not ok else ""))


A0 = np.asarray(Image.open(KOK / "test_veri" / "mb_altin_sahte_isim.jpg").convert("RGB")).copy()


def kodla(a):
    bb = io.BytesIO(); Image.fromarray(a).save(bb, "JPEG", qtables=KD.tablolar(85, 3), subsampling=0)
    return np.asarray(Image.open(bb).convert("RGB")).astype(np.int16), Image.open(bb)


durumlar = {
    "sacak_yildiz": lambda a: (a.__setitem__((slice(1000, 1002), slice(400, 403)), (235, 235, 230)),
                               a.__setitem__((slice(1002, 1004), slice(401, 403)), (95, 15, 15))),
    "parlak_yildiz": lambda a: (a.__setitem__((slice(1000, 1002), slice(400, 403)), (235, 235, 230)),
                                a.__setitem__((slice(1003, 1005), slice(401, 403)), (220, 40, 40))),
    "ton24_kenar": lambda a: (a.__setitem__((slice(1030, 1040), slice(200, 212)), (215, 115, 40)),
                              a.__setitem__((slice(1040, 1042), slice(204, 206)), (95, 15, 15))),
    "ic_koyu": lambda a: a.__setitem__((slice(1020, 1022), slice(650, 653)), (85, 15, 15)),
    "capraz_yildiz": lambda a: (a.__setitem__((slice(1000, 1002), slice(400, 402)), (235, 235, 230)),     # yildiz; sacak capraz (2,2) uzakta
                                a.__setitem__((slice(1003, 1005), slice(403, 405)), (95, 15, 15))),
}
sonuc = {}
for ad, f in durumlar.items():
    a = A0.copy(); f(a); arr, im = kodla(a)
    t = T.teshis(arr); g = K.kirmizi_tara(im, dijital=True)
    sonuc[ad] = t
    kontrol(f"tutarlilik ({ad}): teshis B_FAIL == kapi ton_kume_buyuk, B sacak == kapi ton_sacak_bilgi",
            t["B_FAIL"] == g.get("ton_kume_buyuk", 0) and sum(c["B_sacak"] for c in t["kumeler"]) == g.get("ton_sacak_bilgi", 0),
            f"teshis {t['B_FAIL']} kapi {g.get('ton_kume_buyuk')} {g.get('ton_sacak_bilgi')}")
k = sonuc["sacak_yildiz"]["kumeler"]
kontrol("bilinen PASS: koyu sacak beyaz yildizda -> A ve B sacak, maske beyaz", len(k) >= 1 and all(c["A_sacak"] and c["B_sacak"] for c in k)
        and any("beyaz" in c["maske_2px"] for c in k), str(k))
k = sonuc["parlak_yildiz"]["kumeler"]
kontrol("bilinen FAIL nedeni: parlak kirmizi yildiz yaninda -> A sacak, B FAIL 'parlak', max_R > 130",
        any(c["A_sacak"] and not c["B_sacak"] and c["B_FAIL_nedeni"] == "parlak" and c["max_R"] > 130 for c in k), str(k))
k = sonuc["ton24_kenar"]["kumeler"]
kontrol("B' (22 Kas): ton ~24 altin kenari -> A ve B' sacak (altin ton >= 20); eski B (>= 28) maskesinde uzak", any(c["A_sacak"] and c["B_sacak"]
        and "altin_B" not in c["maske_2px"] for c in k), str(k))
k = sonuc["ic_koyu"]["kumeler"]
kontrol("bilinen FAIL: ic koyu nokta (oge 2 px icinde yok) -> A ve B FAIL", len(k) >= 1 and all(not c["A_sacak"] and not c["B_sacak"] and c["maske_2px"] == []
        and c["B_FAIL_nedeni"] in ("oge_uzak", "alan") for c in k), str(k))
k = sonuc["capraz_yildiz"]["kumeler"]
kontrol("capraz (2,2) uzaklik: kare olcude 2 (kapi ile ayni) -> A ve B sacak (22 Kas: L2 2.83 yanlis 'uzak' sayiyordu)",
        len(k) >= 1 and all(c["uzaklik_kare"]["beyaz"] <= 2 and c["A_sacak"] and c["B_sacak"] for c in k), str(k))
print(f"SONUC: {sum(SONUC)}/{len(SONUC)} PASS")
sys.exit(0 if all(SONUC) else 1)
