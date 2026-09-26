#!/usr/bin/env python3
"""V3 icin ISIMLI 24x32 baski dosyasi ureticisi (GOREV_0012 md.3).

NEDEN BU YOL (olculdu, kosu 36229382139):
  - kisisel PLATES'te `<ED>_24x32.png` = 7200x9600, yani V3'un bekledigi olcu.
  - POD_PRINT'te 24x32 YOK; 3:4 oraninin onayli baski dosyasi 18x24 (5400x9600'un
    degil, 5400x7200). Yani cifte ozel sanat (fuzyon sembolu + glifler) yalniz
    18x24'te var; plate medyan oldugu icin onlari icermez (halka + eski slogan var).
KURULUS (yalniz onayli kaynaklar):
  1. sanat = POD_PRINT/<CIFT>/<RENK>/18x24.jpg  -  PLATES/<ED>_18x24.png  (isaretli
     fark, 3B uzaklik testi; esik yok)
  2. sanat 7200x9600'e buyutulur (LANCZOS) ve GERCEK 24x32 plate'in uzerine biner
     -> zemin birebir plate oldugu icin murekkep disi fark 0 kalir (olculur)
  3. burc adlari / eski slogan cikarilir, yerine kisisel-v1 onayli render ile
     ISIMLER + MESAJ konur (wp_v2'nin olculen yerlesimi, ∞ tam sayi kaydirma)
  4. cikti: SIPARIS_<CIFT>_<ED>_24x32.png  (V3'un girdisi)

DURUST NOT: bu dosya kisisel'in siparis ureticisinin KENDI kod yolundan degil,
bu oturumda ayni onayli kaynaklardan kuruldu. kisisel 24x32 uretmeye baslayinca
bu adim gereksiz olur; V3 tarafi degismez.
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK / "etsy"))
import importlib.util                                                          # noqa: E402
_s = importlib.util.spec_from_file_location("wp_siparis", Path(__file__).resolve().parent / "wp_siparis.py")
SP = importlib.util.module_from_spec(_s); _s.loader.exec_module(SP)             # noqa: E402
V2 = SP.V2
from wp_mockup_common import imread                                            # noqa: E402
_g = importlib.util.spec_from_file_location("girdi_dogrula",
                                            Path(__file__).resolve().parent / "girdi_dogrula.py")
GD = importlib.util.module_from_spec(_g); _g.loader.exec_module(GD)             # noqa: E402
from wp_plate_pilot import BOX_NAMES                                           # noqa: E402

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
W24, H24 = V2.POSTER_W, V2.POSTER_H          # 7200 x 9600
W18, H18 = 5400, 7200                        # 18x24 @ 300 dpi (ayni 3:4 orani)


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def olcu_kontrol(im, ad, bekle):
    if (im.shape[1], im.shape[0]) != bekle:
        raise SystemExit(f"HATA: {ad} {im.shape[1]}x{im.shape[0]}, beklenen {bekle[0]}x{bekle[1]}")


def sanat_buyut(pod18, p18, ed_wp):
    """18x24'teki cifte ozel sanati (isaretli fark) 24x32'ye buyutur."""
    fark, alfa, alfa_o, tani = SP.murekkep(pod18, p18, ed_wp, "birak", "uzaklik")
    log(f"  sanat 18x24: poz {tani['poz_px']} px, neg {tani['neg_px']} px, "
        f"murekkep {tani['murekkep_bgr']} ({tani['murekkep_kaynagi']})")
    fu = cv2.resize(fark, (W24, H24), interpolation=cv2.INTER_LANCZOS4)
    au = cv2.resize(alfa_o, (W24, H24), interpolation=cv2.INTER_LANCZOS4)
    del fark, alfa, alfa_o
    return fu, np.clip(au, 0, 1), tani


def baski_kur(pod18, p18, p24, ed_wp, isim1, isim2, mesaj, P6, P7, P12, kp, geo_ref=None):
    """24x32 isimli baski dosyasi: plate + buyutulmus sanat + yeni isim/mesaj."""
    fu, au, tani = sanat_buyut(pod18, p18, ed_wp)
    poster = np.clip(np.round(p24.astype(np.float32) + fu), 0, 255).astype(np.uint8)
    dis = au <= 0
    k0 = int(np.abs(poster.astype(np.int16) - p24.astype(np.int16)).max(2)[dis].max()) if dis.any() else 0
    log(f"  buyutme sonrasi murekkep disi fark: {k0} (0 beklenir; zemin gercek 24x32 plate)")

    geo_olc, isim_m, inf_m = V2.metin_olcumu(poster, p24, ed_wp)
    log(f"  olcum: sol={geo_olc['sol']} ∞={geo_olc['sonsuz']} sag={geo_olc['sag']} "
        f"cap={geo_olc['cap']} mesaj_cap={geo_olc['mesaj_cap']} kume={geo_olc['kume']['grup']}")
    geo = geo_ref or geo_olc          # ayni ciftte TEK geometri (edisyonlar paylasir)
    if geo_ref:
        sap = {k: int(np.abs(np.asarray(geo_olc[k]) - np.asarray(geo_ref[k])).max())
               for k in ("sol", "sag", "sonsuz")}
        log(f"  geometri referanstan sapma: {json.dumps(sap)} | mesaj_cap olculen "
            f"{geo_olc['mesaj_cap']} vs referans {geo_ref['mesaj_cap']} (referans kullanildi)")
    ix = np.arange(W24)
    prof = {"sol": V2.profil(poster, isim_m & (ix < geo["sonsuz"][0]),
                             (geo["sol"][0], geo["isim_govde"][0], geo["sol"][1], geo["isim_govde"][1])),
            "sag": V2.profil(poster, isim_m & (ix > geo["sonsuz"][2]),
                             (geo["sag"][0], geo["isim_govde"][0], geo["sag"][1], geo["isim_govde"][1]))}
    prof["tag"] = prof["sol"]
    yerlesim, dx_inf, bilgi = V2.metin_katmani(P6, P7, P12, kp, geo, prof,
                                               {"sol": isim1, "sag": isim2}, mesaj)
    log(f"  yerlesim: dx_sonsuz={dx_inf} bosluk={bilgi['bosluk']} "
        f"mesaj_punto={bilgi['mesaj_punto']} mesaj_genislik={bilgi['mesaj_genislik']}")

    sx0, sy0, sx1, sy1 = geo["sonsuz"]
    inf_box = V2.kutu_maske(poster.shape, (sx0 - 6, sy0 - 6, sx1 + 6, sy1 + 6)).astype(np.float32)
    isim_box = V2.kutu_maske(poster.shape, BOX_NAMES).astype(np.float32)
    mesaj_box = V2.kutu_maske(poster.shape, SP.MESAJ_BANT).astype(np.float32)
    a_inf = au * inf_box
    alfa = au * (1 - np.clip(isim_box + mesaj_box, 0, 1))     # burc adlari + eski slogan cikti
    src = poster.astype(np.float32)
    a_ik = V2.kaydir(a_inf, dx_inf)                            # ∞ tam sayi kaydirma
    src_i = np.stack([V2.kaydir(src[..., c], dx_inf) for c in range(3)], axis=2)
    yer = a_ik > 0
    src[yer] = src_i[yer]
    alfa = np.maximum(alfa, a_ik)
    del a_inf, a_ik, src_i, inf_box, isim_box, mesaj_box, fu, au, poster
    for rgba, x, y in yerlesim:
        V2.katman_ekle(src, alfa, rgba, x, y)
    out = np.clip(np.round(alfa[..., None] * src + (1 - alfa[..., None]) * p24.astype(np.float32)),
                  0, 255).astype(np.uint8)
    d = np.abs(out.astype(np.int16) - p24.astype(np.int16)).max(2)
    k1 = int(d[alfa <= 0].max()) if (alfa <= 0).any() else 0
    log(f"  baski: murekkep disi fark {k1} (0 beklenir), murekkep {int((alfa > 0).sum())} px")
    return out, {"_geo": geo, "buyutme_disi_fark": k0, "baski_disi_fark": k1, "tani": tani,
                 "olcum": {k: geo[k] for k in ("sol", "sag", "sonsuz", "cap", "mesaj_cap")},
                 "yerlesim": {k: bilgi[k] for k in ("bosluk", "dx_sonsuz", "mesaj_punto",
                                                    "mesaj_genislik", "mesaj_sinir", "mesaj_olcek",
                                                    "satir", "isim_sinir", "isim_olcek",
                                                    "isim_kucultme", "isim_pay_px")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pod", required=True, help="POD_PRINT: <CIFT>/<RENK>/18x24.jpg")
    ap.add_argument("--plate", required=True, help="PLATES: <ED>_18x24.png + <ED>_24x32.png")
    ap.add_argument("--kisisel", required=True)
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--eslesme", required=True, help="BLUE=MIDNIGHT_BLUE,BLACK=DEEP_BLACK")
    ap.add_argument("--mesaj-sinir", type=int, default=GD.MESAJ_SINIR,
                    help=f"mesaj karakter siniri (varsayilan {GD.MESAJ_SINIR}); asan REDDEDILIR")
    ap.add_argument("--kayit", action="append", default=[],
                    help="CIFT|isim1|isim2|mesaj[|ETIKET] (birden cok kez). ETIKET verilirse "
                         "cikti adinda CIFT yerine o kullanilir (ayni cifte ikinci deneme icin).")
    a = ap.parse_args()
    es = dict(x.split("=", 1) for x in a.eslesme.split(",") if "=" in x)
    P6, P7, P12, kp = V2.kisisel_kur(a.kisisel)
    cik = Path(a.cikti); cik.mkdir(parents=True, exist_ok=True)
    rapor, geo_cift = [], {}
    for kayit in a.kayit:
        parca = [x.strip() for x in kayit.split("|")]
        if len(parca) not in (4, 5):
            raise SystemExit(f"HATA: --kayit 'CIFT|isim1|isim2|mesaj[|ETIKET]' olmali: {kayit!r}")
        cift, i1, i2, msj = parca[:4]
        etiket = parca[4] if len(parca) == 5 and parca[4] else cift
        # GOREV_0014: isim/mesaj uzunlugu + font glif kapsami URETIMDEN ONCE dogrulanir;
        # uymayan girdi REDDEDILIR (sessiz kirpma / .notdef kutusu yok).
        i1, i2, msj = GD.kayit_dogrula(i1, i2, msj, kp.FONT_DIR / P12.ISIM_FONT,
                                       kp.FONT_DIR / P6.TAG_FONT, a.mesaj_sinir)
        log(f"girdi dogrulandi: isim {len(i1)}/{len(i2)} karakter, mesaj {len(msj)} "
            f"(sinir {a.mesaj_sinir}), font glifleri tam")
        for ed, ed_wp_ust in es.items():
            ed_wp = "_".join(w.capitalize() for w in ed_wp_ust.split("_"))   # MIDNIGHT_BLUE -> Midnight_Blue
            log(f"{cift} {ed} (plaka {ed_wp})")
            pod = Path(a.pod) / cift / ed_wp_ust / "18x24.jpg"
            if not pod.exists():
                raise SystemExit(f"HATA: POD_PRINT kaynagi yok: {pod}")
            pod18 = imread(pod); olcu_kontrol(pod18, pod.name, (W18, H18))
            # plate edisyon basina AYNI dosya: her kayitta yeniden okunuyordu (HIZ)
            p18 = SP.plate_oku(SP.dosya_bul(a.plate, [ed, "18x24"], f"{ed} plate 18x24"))
            p24 = SP.plate_oku(SP.dosya_bul(a.plate, [ed, "24x32"], f"{ed} plate 24x32"))
            olcu_kontrol(p18, f"{ed}_18x24", (W18, H18)); olcu_kontrol(p24, f"{ed}_24x32", (W24, H24))
            out, bilgi = baski_kur(pod18, p18, p24, ed_wp, i1, i2, msj, P6, P7, P12, kp,
                                   geo_cift.get(cift))
            geo_cift.setdefault(cift, bilgi.pop("_geo"))
            ad = f"SIPARIS_{etiket}_{ed}_24x32.png"
            cv2.imwrite(str(cik / ad), out)
            rapor.append({"cift": cift, "etiket": etiket, "edisyon": ed, "plaka_edisyonu": ed_wp_ust,
                          "isimler": [i1, i2], "mesaj": msj, "dosya": ad, **bilgi})
            del pod18, out
    (cik / "V3_BASKI_URETIM.json").write_text(json.dumps(rapor, indent=1))
    log(f"{len(rapor)} baski dosyasi uretildi -> {cik}")
    bekle = len(a.kayit) * len(es)          # YUKSEK1: eksik cikti basarili sayilmaz
    diskte = sum(1 for r in rapor if (cik / r["dosya"]).is_file())
    if not a.kayit or len(rapor) != bekle or diskte != bekle:
        raise SystemExit(f"HATA: beklenen {bekle} baski dosyasi ({len(a.kayit)} kayit x "
                         f"{len(es)} edisyon), rapor {len(rapor)}, diskte {diskte}. DUR.")
    kot = [r for r in rapor if r["baski_disi_fark"] != 0]
    if kot:
        raise SystemExit(f"HATA: {len(kot)} dosyada murekkep disi fark 0 degil: "
                         f"{[(r['dosya'], r['baski_disi_fark']) for r in kot]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
