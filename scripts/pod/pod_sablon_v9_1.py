#!/usr/bin/env python3
"""POD sablon V9.1 - V9 katman yapisi + dort duzeltme.

1. CIFT TOZ: Katman 1 artik referansin kare kare pikselleri degil; referans
   kare 0'in temizlenmis hali, kare basina TEK SAYI parlaklik oraniyla
   olceklenir. Boylece referansin tozu panel icinde hic kalmaz; toz yalniz
   Katman 3'ten (V5) gelir ve kare basina referans toz enerjisine esitlenir.
2. KENAR: Katman 2 maskesi ikili degil; cifte ait posterin kendi kenar
   yumusatmasindan turetilen yumusak alfa. Boyama rengi cekirdekten alinip
   kenara tasinir, boylece koyu kenar cizgisi olusmaz. Maske delikleri
   kapatilir (alt dalgadaki centik).
3. KONUM: Her cift ogesinin sinir kutusu merkezi, referanstaki ayni turun
   merkezine oturtulur (tam sayi kaydirma).
4. PARLAMA: Kucuk sembollerde parlakligin ust %2'si referansin ust %2'sine
   esitlenir.

Yerel calisir, Etsy cagrisi yoktur.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK.parent / "etsy"))
from etsy_common import log  # noqa: E402
from match_video_to_cover import extract_frame, probe  # noqa: E402
from pod_sablon_v4 import (KAPAK, cift_hizala, karsilastirma,  # noqa: E402
                           kareleri_ac, kutu_olcekle, panel_kutusu,
                           rgb_yuv_doseme, yuv_ac, yuv_video_yaz)
from pod_sablon_v5 import kapak_ac, kutu_boyut  # noqa: E402
from pod_sablon_v6 import maske_panele  # noqa: E402
from pod_sablon_v8 import (gorunurluk_egrisi, katman_maskeleri,  # noqa: E402
                           kuyruk_normalize, panel_y, temiz_zemin, zamanlama)
from pod_sablon_v9 import (TEMIZ_GENIS, gradient_lut, histogram_esle,  # noqa: E402
                           isim_maskesi, luma, panel_rgb)

TOZ_TABAN = 3.0
CEKIRDEK = 0.6          # alfa bu degerin ustundeyse cekirdek (renk kaynagi)
PARLAMA_YUZDE = 98      # ust %2
OGELER = ("ana_sembol", "kucuk_burc_1", "kucuk_burc_2", "isim")


def kapat(m, en_cok_delik=60):
    """YALNIZ kucuk delikleri kapatir (centik/benek).

    Tum delikleri doldurmak yanlis: Aries gibi kollari arasinda ARKA PLAN
    kalan sekillerde o bolge de dolar; hem renk tablosu hem alfa bozulur
    (1. iterasyonda goruldu). Bu yuzden delik bilesenleri etiketlenip yalniz
    kucuk olanlar doldurulur.
    """
    dolu = ndimage.binary_fill_holes(m)
    delik = dolu & ~m
    if not delik.any():
        return m
    et, _ = ndimage.label(delik)
    kucuk = np.zeros_like(m)
    for i, dil in enumerate(ndimage.find_objects(et), start=1):
        if dil is None:
            continue
        c = et[dil] == i
        if int(c.sum()) <= en_cok_delik:
            kucuk[dil] |= c
    return m | kucuk


def kapsam_alfa(maske, rampa=2.0):
    """Alfa SEKIL KAPSAMINDAN: maske ici 1.0, sinirda `rampa` px dogrusal gecis.

    V9.1'de alfa parlakliktan turetiliyordu; metalin koyu bolgeleri yari
    saydam olup zemin siziyordu (benekli/sonuk gorunum). Burada isaretli
    uzaklik kullanilir: maske icinde >=1 px iceride alfa 1, disinda >=1 px
    disarida 0, arasinda dogrusal.
    """
    if not maske.any():
        return maske.astype(np.float32)
    ic = ndimage.distance_transform_edt(maske)
    dis = ndimage.distance_transform_edt(~maske)
    isaretli = ic - dis
    return np.clip((isaretli + rampa / 2.0) / rampa, 0.0, 1.0).astype(np.float32)


def yumusak_alfa(l, maske, genislet=3):
    """Cift posterinin kendi kenar yumusatmasindan alfa.

    alfa = (parlaklik - zemin) / (cekirdek - zemin), maske cevresinde.
    """
    bolge = ndimage.binary_dilation(maske, iterations=genislet)
    kenar_disi = bolge & ~maske
    zemin = float(np.median(l[kenar_disi])) if kenar_disi.any() else 0.0
    cekirdek = float(np.percentile(l[maske], 85)) if maske.any() else 1.0
    if cekirdek <= zemin + 1e-6:
        return maske.astype(np.float32)
    a = np.zeros_like(l, dtype=np.float32)
    a[bolge] = np.clip((l[bolge] - zemin) / (cekirdek - zemin), 0.0, 1.0)
    return a


def kaydir(dizi, dy, dx):
    cikti = np.zeros_like(dizi)
    h, w = dizi.shape[:2]
    y0, y1 = max(dy, 0), min(h + dy, h)
    x0, x1 = max(dx, 0), min(w + dx, w)
    cikti[y0:y1, x0:x1] = dizi[y0 - dy:y1 - dy, x0 - dx:x1 - dx]
    return cikti


def merkez(maske):
    ys, xs = np.where(maske)
    if not len(ys):
        return None
    return ((int(ys.min()) + int(ys.max())) / 2.0,
            (int(xs.min()) + int(xs.max())) / 2.0)


def cekirdekten_yay(renk, cekirdek):
    """Cekirdek renklerini en yakin komsuya tasir (kenarda koyu iz kalmasin)."""
    _, idx = ndimage.distance_transform_edt(~cekirdek, return_indices=True)
    return renk[idx[0], idx[1]]


def parlama_esitle(renk, alfa, ref_l, yuzde=PARLAMA_YUZDE):
    """Ust %2 parlamayi referansin ust %2'sine esitler."""
    sec = alfa > CEKIRDEK
    if not sec.any():
        return renk, None
    l = luma(renk)
    yeni_p = float(np.percentile(l[sec], yuzde))
    ref_p = float(np.percentile(ref_l, yuzde))
    if yeni_p <= 1e-6:
        return renk, None
    ust = sec & (l >= yeni_p)
    if not ust.any():
        return renk, None
    kazanc = ref_p / yeni_p
    cikti = renk.copy()
    cikti[ust] = np.clip(renk[ust] * kazanc, 0, 255)
    return cikti, {"yeni_p98_once": round(yeni_p, 1),
                   "referans_p98": round(ref_p, 1),
                   "kazanc": round(kazanc, 3), "piksel": int(ust.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="_veri/v8")
    ap.add_argument("--out", required=True)
    ap.add_argument("--alfa", choices=("parlaklik", "kapsam"),
                    default="parlaklik")
    ap.add_argument("--etiket", default="V9_1")
    a = ap.parse_args()
    veri = pathlib.Path(a.veri)
    out = pathlib.Path(a.out)
    (out / "_is").mkdir(parents=True, exist_ok=True)

    ref_video = veri / "referans_video.mp4"
    v5_video = veri / "v5_ornek_video.mp4"
    meta = probe(ref_video)
    ak = meta["streams"][0]
    vw, vh = int(ak["width"]), int(ak["height"])
    sure = float(meta["format"]["duration"])
    p, q = (ak.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = round(float(p) / float(q), 3)

    ref_kapak_a = kapak_ac(veri / "referans_kapak.png")
    kutu_kapak = panel_kutusu(ref_kapak_a)
    kutu = cift_hizala(kutu_olcekle(kutu_kapak, KAPAK[1], vh, KAPAK[0], vw))
    pw, ph = kutu_boyut(kutu)

    ref_k, ref_not, _ = katman_maskeleri(ref_kapak_a)
    ref_isim_k, _ = isim_maskesi(ref_kapak_a, ref_k["ana_sembol"],
                                 (ref_k.get("kucuk_burc_1"),
                                  ref_k.get("kucuk_burc_2")))
    ref_m = {ad: kapat(maske_panele(m, kutu_kapak, pw, ph))
             for ad, m in ref_k.items() if m.any()}
    ref_m["isim"] = kapat(maske_panele(ref_isim_k, kutu_kapak, pw, ph))

    ref_kareler = kareleri_ac(ref_video, out / "_is" / "refkare")
    v5_kareler = kareleri_ac(v5_video, out / "_is" / "v5kare")
    v5_k0 = out / "_is" / "v5_kapak0.png"
    with Image.open(v5_kareler[0]) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(v5_k0)
    v5_kapak_a = kapak_ac(v5_k0)
    cift_k, cift_not, _ = katman_maskeleri(v5_kapak_a)
    cift_isim_k, _ = isim_maskesi(v5_kapak_a, cift_k["ana_sembol"],
                                  (cift_k.get("kucuk_burc_1"),
                                   cift_k.get("kucuk_burc_2")))
    cift_m = {ad: kapat(maske_panele(m, kutu_kapak, pw, ph))
              for ad, m in cift_k.items() if m.any()}
    cift_m["isim"] = kapat(maske_panele(cift_isim_k, kutu_kapak, pw, ph))
    log(f"maske px referans { {k: int(v.sum()) for k, v in ref_m.items()} } | "
        f"cift { {k: int(v.sum()) for k, v in cift_m.items()} }")

    ref0 = panel_rgb(ref_kareler, 0, kutu).astype(np.float32)
    v5_0 = panel_rgb(v5_kareler, 0, kutu).astype(np.float32)
    v5_l = ndimage.median_filter(luma(v5_0), size=3)

    # ---- (3) KONUM: cift ogelerini referans merkezine oturt
    kaydirma = {}
    for ad in OGELER:
        if ad not in cift_m or ad not in ref_m:
            continue
        mr, mc = merkez(ref_m[ad]), merkez(cift_m[ad])
        if mr is None or mc is None:
            continue
        dy, dx = int(round(mr[0] - mc[0])), int(round(mr[1] - mc[1]))
        kaydirma[ad] = (dy, dx)
    log(f"konum kaydirmasi (dy,dx): {kaydirma}")

    # ---- (2) KENAR: yumusak alfa + cekirdekten renk
    alfa, boyali, boya_not, parlama_not = {}, {}, {}, {}
    kucuk_ref = np.zeros((ph, pw), dtype=bool)
    for ad in ("kucuk_burc_1", "kucuk_burc_2"):
        if ad in ref_m:
            kucuk_ref |= ref_m[ad]
    kaynak_of = {"ana_sembol": ref_m.get("ana_sembol"),
                 "isim": ref_m.get("isim"),
                 "kucuk_burc_1": kucuk_ref, "kucuk_burc_2": kucuk_ref}
    for ad in OGELER:
        m = cift_m.get(ad)
        kay = kaynak_of.get(ad)
        if m is None or not m.any() or kay is None or not kay.any():
            continue
        if a.alfa == "kapsam":
            al = kapsam_alfa(m)
            cek = m                      # renk TUM maskeden, cekirdekle sinirli degil
        else:
            al = yumusak_alfa(v5_l, m)
            cek = al > CEKIRDEK
            if not cek.any():
                cek = m
        lut, ref_l = gradient_lut(ref0, kay)
        eslenen = histogram_esle(v5_l[cek], ref_l)
        idx = np.clip(np.rint(eslenen), 0, 255).astype(np.int32)
        renk = np.zeros((ph, pw, 3), dtype=np.float32)
        renk[cek] = lut[idx]
        renk = cekirdekten_yay(renk, cek)       # kenara cekirdek rengi
        if ad in ("kucuk_burc_1", "kucuk_burc_2"):
            renk, parlama_not[ad] = parlama_esitle(renk, al, ref_l)
        dy, dx = kaydirma.get(ad, (0, 0))
        alfa[ad] = kaydir(al, dy, dx)
        boyali[ad] = kaydir(renk, dy, dx)
        boya_not[ad] = {"alfa_toplam": round(float(al.sum()), 1),
                        "cekirdek_px": int(cek.sum()),
                        "kaydirma": [dy, dx],
                        "ref_luma_ort": round(float(ref_l.mean()), 1),
                        "yeni_luma_ort": round(float(eslenen.mean()), 1)}
    log(f"boyama: {json.dumps(boya_not, ensure_ascii=False)}")
    log(f"parlama: {json.dumps(parlama_not, ensure_ascii=False)}")

    # konum dogrulamasi (kaydirmadan sonra)
    konum_fark = {}
    for ad in alfa:
        mr = merkez(ref_m[ad])
        mc = merkez(alfa[ad] > 0.5)
        if mr and mc:
            konum_fark[ad] = [round(mc[0] - mr[0], 1), round(mc[1] - mr[1], 1)]
    log(f"konum farki (dy,dx) kaydirma sonrasi: {konum_fark}")

    # ---- (1) KATMAN 1: temizlenmis referans kare 0 (statik) + kare orani
    temiz_bolge = np.zeros((ph, pw), dtype=bool)
    for ad in OGELER:
        for kay_m in (ref_m.get(ad), cift_m.get(ad)):
            if kay_m is not None and kay_m.any():
                temiz_bolge |= ndimage.binary_dilation(kay_m,
                                                       iterations=TEMIZ_GENIS)
    for ad, al in alfa.items():
        temiz_bolge |= ndimage.binary_dilation(al > 0.05, iterations=TEMIZ_GENIS)
    zemin0 = np.stack([temiz_zemin(ref0[..., k], temiz_bolge) for k in range(3)],
                      axis=-1)
    log(f"temiz zemin bolgesi {int(temiz_bolge.sum())} px (statik, kare 0'dan)")

    ref_veri, kare_bayt, ref_adet = yuv_ac(ref_video, out / "_is" / "ref.yuv",
                                           vw, vh)
    v5_veri, _, v5_adet = yuv_ac(v5_video, out / "_is" / "v5.yuv", vw, vh)
    adet = min(ref_adet, v5_adet, len(ref_kareler), len(v5_kareler))
    ref_y0 = panel_y(ref_veri, kare_bayt, 0, kutu, vw, vh).astype(np.float32)
    v5_y0 = panel_y(v5_veri, kare_bayt, 0, kutu, vw, vh).astype(np.float32)

    oran, ref_toz_enerji, v5_toz_enerji = [], [], []
    for i in range(adet):
        ry = panel_y(ref_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        fark = ry - ref_y0
        toz = np.clip(fark - TOZ_TABAN, 0.0, None)
        tozsuz = fark <= TOZ_TABAN            # toz disi pikseller
        oran.append(float(ry[tozsuz].mean() / max(ref_y0[tozsuz].mean(), 1e-6))
                    if tozsuz.any() else 1.0)
        ref_toz_enerji.append(float(toz.sum()))
        vy = panel_y(v5_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
        v5_toz_enerji.append(float(np.clip(vy - v5_y0 - TOZ_TABAN, 0.0, None).sum()))
    toz_olcek = [float(np.clip(r / max(v, 1e-6), 0.0, 4.0))
                 for r, v in zip(ref_toz_enerji, v5_toz_enerji)]
    log(f"kare orani araligi {min(oran):.3f}-{max(oran):.3f} | toz olcegi "
        f"{min(toz_olcek):.2f}-{max(toz_olcek):.2f} (ortalama "
        f"{float(np.mean(toz_olcek)):.2f})")

    # toz rengi: referansin kendi tozundan
    ornek = []
    for i in (30, 60, 90):
        d = panel_rgb(ref_kareler, i, kutu).astype(np.float32) - ref0
        sec = luma(d) > 12
        if sec.any():
            ornek.append(d[sec].mean(axis=0))
    toz_renk = (np.mean(ornek, axis=0) if ornek
                else np.array([255.0, 200.0, 120.0], dtype=np.float32))
    toz_renk = toz_renk / max(luma(toz_renk[None, None, :])[0, 0], 1e-6)

    # ---- egriler
    olcum = {ad: ref_m[ad] for ad in ("kucuk_burc_1", "kucuk_burc_2", "isim")
             if ad in ref_m and ref_m[ad].any()}
    ham, _ = gorunurluk_egrisi(ref_veri, kare_bayt, ref_adet, kutu, vw, vh, olcum)
    egri = {ad: kuyruk_normalize(e) for ad, e in ham.items()}
    zaman = {ad: zamanlama(e, fps) for ad, e in egri.items()}

    # ---- kompozit
    ham_yuv = out / "_is" / "yeni.yuv"
    with open(ham_yuv, "wb") as fh:
        for i in range(adet):
            taban = zemin0 * oran[i]
            for ad, al in alfa.items():
                g = egri.get(ad, [1.0] * adet)[i] if ad in egri else 1.0
                aa = (al * float(np.clip(g, 0, 1)))[..., None]
                taban = taban * (1 - aa) + boyali[ad] * aa
            vy = panel_y(v5_veri, kare_bayt, i, kutu, vw, vh).astype(np.float32)
            toz = np.clip(vy - v5_y0 - TOZ_TABAN, 0.0, None) * toz_olcek[i]
            taban = np.clip(taban + toz[..., None] * toz_renk[None, None, :],
                            0, 255)
            Y, U, V = rgb_yuv_doseme(np.rint(taban).astype(np.uint8))
            blok = ref_veri[i * kare_bayt:(i + 1) * kare_bayt].copy()
            y = blok[:vw * vh].reshape(vh, vw)
            u = blok[vw * vh:vw * vh + vw * vh // 4].reshape(vh // 2, vw // 2)
            v = blok[vw * vh + vw * vh // 4:].reshape(vh // 2, vw // 2)
            y[kutu["ust"]:kutu["ust"] + ph, kutu["sol"]:kutu["sol"] + pw] = Y
            u[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = U
            v[kutu["ust"] // 2:kutu["ust"] // 2 + ph // 2,
              kutu["sol"] // 2:kutu["sol"] // 2 + pw // 2] = V
            blok.tofile(fh)

    video = out / f"Aquarius_Aries_4570110641_video_{a.etiket}.mp4"
    yuv_video_yaz(ham_yuv, video, vw, vh, fps, sure)
    kapak = out / f"Aquarius_Aries_4570110641_kapak_{a.etiket}.png"
    k0 = out / "_is" / "yeni_kare0.png"
    extract_frame(video, k0, 0)
    with Image.open(k0) as im:
        im.convert("RGB").resize(KAPAK, Image.Resampling.LANCZOS).save(kapak)
    for gec in ("yeni.yuv", "ref.yuv", "v5.yuv"):
        (out / "_is" / gec).unlink(missing_ok=True)

    # ---- kontrol gorselleri
    zamanlar = [round(sure * i / 7, 3) for i in range(8)]
    satir = []
    for ad, yol in [("REFERANS  Aquarius + Gemini", ref_video),
                    (f"YENI {a.etiket}  Aquarius + Aries", video)]:
        g, kl = [], out / "_is" / "k8" / ad.split()[0]
        kl.mkdir(parents=True, exist_ok=True)
        for i, z in enumerate(zamanlar):
            zz = min(z, max(sure - 1.0 / fps, 0))
            pp = kl / f"{i}.png"
            extract_frame(yol, pp, zz)
            g.append((f"{zz:.2f} sn", Image.open(pp).convert("RGB")))
        satir.append((ad, g))
    b1 = karsilastirma(satir, out / f"KARE_KARSILASTIRMA_{a.etiket}.jpg")

    def kirp(img, kutu4, olcek=2, pay=12):
        y0, y1, x0, x1 = kutu4
        y0, y1 = max(y0 - pay, 0), min(y1 + pay, img.shape[0] - 1)
        x0, x1 = max(x0 - pay, 0), min(x1 + pay, img.shape[1] - 1)
        im = Image.fromarray(img[y0:y1 + 1, x0:x1 + 1].astype(np.uint8))
        return im.resize((im.width * olcek, im.height * olcek),
                         Image.Resampling.LANCZOS)

    def kutu_of(m):
        ys, xs = np.where(m)
        return [int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())]

    with Image.open(sorted((out / "_is" / "k8" / "YENI").glob("*.png"))[0]) as im:
        yeni_tam = np.asarray(im.convert("RGB"), dtype=np.uint8)
    yeni0 = yeni_tam[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]
    ref0u = ref0.astype(np.uint8)
    daire = [int(0.06 * ph), int(0.26 * ph), int(0.02 * pw), int(0.30 * pw)]
    isim_kt = kutu_of(ref_m["isim"])
    satir2 = [("REFERANS", [("ana sembol", kirp(ref0u, kutu_of(ref_m["ana_sembol"]))),
                            ("kucuk sembol", kirp(ref0u, kutu_of(ref_m["kucuk_burc_1"]))),
                            ("burc adi", kirp(ref0u, isim_kt)),
                            ("daire", kirp(ref0u, daire))]),
              (f"YENI {a.etiket}", [("ana sembol", kirp(yeni0, kutu_of(ref_m["ana_sembol"]))),
                             ("kucuk sembol", kirp(yeni0, kutu_of(ref_m["kucuk_burc_1"]))),
                             ("burc adi", kirp(yeni0, isim_kt)),
                             ("daire", kirp(yeni0, daire))])]
    b2 = karsilastirma(satir2, out / f"ALTIN_YAKIN_{a.etiket}.jpg", hucre=520)

    satir3 = []
    for ad, yol in [("REFERANS", ref_video), (f"YENI {a.etiket}", video)]:
        g = []
        for sn in (1.314, 1.971):
            pp = out / "_is" / f"{ad[:3]}_{sn}.png"
            extract_frame(yol, pp, sn)
            with Image.open(pp) as im:
                arr = np.asarray(im.convert("RGB"), dtype=np.uint8)
            pan = arr[kutu["ust"]:kutu["alt"] + 1, kutu["sol"]:kutu["sag"] + 1]
            g.append((f"{sn:.2f} sn", kirp(pan, kutu_of(ref_m["ana_sembol"]))))
        satir3.append((ad, g))
    b3 = karsilastirma(satir3, out / f"YAKIN_131_197_{a.etiket}.jpg", hucre=640)
    log(f"gorseller: KARE {b1} | ALTIN {b2} | YAKIN {b3}")

    (out / f"URETIM_SONUC_{a.etiket}.json").write_text(json.dumps(
        {"alfa_modu": a.alfa, "konum_kaydirma": kaydirma, "konum_farki": konum_fark,
         "boyama": boya_not, "parlama": parlama_not, "zamanlama": zaman,
         "kare_orani": [round(x, 4) for x in oran],
         "toz_olcek": [round(x, 3) for x in toz_olcek],
         "toz_renk": np.round(toz_renk, 4).tolist()},
        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({"konum_farki": konum_fark,
                      "toz_olcek_ort": round(float(np.mean(toz_olcek)), 3)},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
