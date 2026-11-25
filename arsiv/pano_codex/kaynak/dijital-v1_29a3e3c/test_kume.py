#!/usr/bin/env python3
"""1. ASAMA yerel testi: isim satiri ayrimi "en buyuk iki bosluk" kurali.

(a) Gercek olcum tekrari: run 36154187069'da ARIES_LEO posterinden OLCULEN
    kumeler kurala verilir.
(b) Uc isimlerle satir: isimler kisisel-v1'in KENDI render koduyla (Cinzel 500,
    tracking -0.0388) poster olceginde cizilir, olculen ∞ genisligi ve olculen
    bosluklarla satir kurulur, gercek metin_olcumu() calistirilir.
Uretim yok, Drive yok, Actions yok.
"""
import importlib.util, json, sys
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
spec = importlib.util.spec_from_file_location("wp_v2", KOK / "wp_kisisel" / "wp_v2.py")
V2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(V2)
from wp_plate_pilot import BOX_NAMES, INK_RGB, REF_TAGLINE      # noqa: E402

# run 36154187069, ARIES_LEO Midnight_Blue, BOX_NAMES icinde OLCULEN kumeler
GERCEK = [(1941, 2580), (2626, 3045), (3472, 4077), (4498, 5290)]
CIFTLER = [("MAXIMILIANA", "CHRISTOPHER"), ("MIA", "LEO"), ("ISABELLA", "NOAH"),
           ("ARIES", "LEO"), ("EMILY", "JAMES")]
W_INF, G = 605, 424          # olculen ∞ genisligi ve isim-∞ boslugu (427/421 -> 424)


def satir_kur(P12, prof, sol_ad, sag_ad, cap, ed):
    """Poster olceginde sentetik isim satiri (gercek render + olculen ∞/bosluk)."""
    r, g, b = INK_RGB[ed]
    median = np.full((V2.POSTER_H, V2.POSTER_W, 3), 24, np.uint8)
    median[REF_TAGLINE[1] + 40:REF_TAGLINE[3] - 40, REF_TAGLINE[0] + 60:REF_TAGLINE[2] - 60] = (b, g, r)
    poster = median.copy()
    SINIR = V2.POSTER_W - 2 * 576                 # mesaj kenar payiyla ayni kullanilabilir genislik
    olcek, kucultme = 1.0, 0
    for _ in range(8):
        pl = {k: P12.plaka(ad, prof, cap, olcek)[0] for k, ad in (("sol", sol_ad), ("sag", sag_ad))}
        ws = {k: V2.plaka_murekkep(pl[k])[1] - V2.plaka_murekkep(pl[k])[0] for k in pl}
        toplam = ws["sol"] + G + W_INF + G + ws["sag"]
        if toplam <= SINIR:
            break
        olcek *= max(min((SINIR - G * 2 - W_INF) / (ws["sol"] + ws["sag"]), 0.99), 0.3)
        kucultme += 1
    x = int(round(V2.POSTER_W / 2 - toplam / 2))
    yorta = (BOX_NAMES[1] + BOX_NAMES[3]) // 2
    for k in ("sol", "inf", "sag"):
        if k == "inf":
            # ∞ yerine olculen genislikte bagli bir sekil (kume olcumu icin genislik onemli)
            poster[yorta - 60:yorta + 60, x:x + W_INF] = (b, g, r)
            x += W_INF + G
            continue
        a = np.asarray(pl[k]); m0, m1 = V2.plaka_murekkep(pl[k])
        al = a[..., 3:4].astype(np.float32) / 255.0
        y0 = yorta - a.shape[0] // 2
        blok = poster[y0:y0 + a.shape[0], x:x + (m1 - m0)]
        src = a[:, m0:m1, :3][..., ::-1].astype(np.float32)
        poster[y0:y0 + a.shape[0], x:x + (m1 - m0)] = (src * al[:, m0:m1] + blok * (1 - al[:, m0:m1])).astype(np.uint8)
        x += (m1 - m0) + G
    return poster, median, round(olcek, 3)


def main():
    kis = sys.argv[1] if len(sys.argv) > 1 else "."
    P6, P7, P12, kp = V2.kisisel_kur(kis)
    ed = "Midnight_Blue"
    prof = np.tile(np.array([[INK_RGB[ed][0], INK_RGB[ed][1], INK_RGB[ed][2]]], np.float32), (400, 1))
    sonuc, hata = [], 0

    sol, orta, sag, bilgi = V2.uc_grup(GERCEK)
    ok = (sol, orta, sag) == ((1941, 3045), (3472, 4077), (4498, 5290))
    hata += 0 if ok else 1
    sonuc.append({"durum": "GERCEK poster olcumu (run 36154187069)", "kume": GERCEK,
                  "bosluk": bilgi["bosluk"], "sol": list(sol), "sonsuz": list(orta), "sag": list(sag),
                  "grup": bilgi["grup"], "gecti": bool(ok)})

    for cap in (380, 440, 500):
        for sa, sg in CIFTLER:
            poster, median, olcek = satir_kur(P12, prof, sa, sg, cap, ed)
            try:
                geo, _, _ = V2.metin_olcumu(poster, median, ed)
                k = geo["kume"]
                ok = len(k["grup"]) == 3 and k["grup"][1] == 1 and \
                    abs((geo["sonsuz"][2] - geo["sonsuz"][0]) - W_INF) <= 2
                sonuc.append({"durum": f"{sa}/{sg} cap={cap} olcek={olcek}", "kume": k["kume"], "bosluk": k["bosluk"],
                              "sol": geo["sol"], "sonsuz": geo["sonsuz"][:1] + geo["sonsuz"][2:3],
                              "sag": geo["sag"], "grup": k["grup"], "gecti": bool(ok)})
            except SystemExit as e:
                ok = False
                sonuc.append({"durum": f"{sa}/{sg} cap={cap} olcek={olcek}", "hata": str(e), "gecti": False})
            hata += 0 if ok else 1
            del poster, median

    for s in sonuc:
        print(("PASS " if s["gecti"] else "FAIL ") + s["durum"] + ": " +
              json.dumps({k: v for k, v in s.items() if k not in ("durum", "gecti")}, ensure_ascii=False))
    print(f"\nTOPLAM {len(sonuc)} durum, {len(sonuc) - hata} PASS, {hata} FAIL")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
