#!/usr/bin/env python3
"""Duvar kagidi kisisellestirme ORNEGI (Serdar 25 Eyl 2026).

Tasarim DEGISMEZ: kaynak dosyadaki kucuk burc glifleri ve sonsuzluk isareti
BIREBIR kalir; yalniz burc adlari yerine iki isim, "Two Souls . One Bond"
yerine kisa mesaj yazilir. Render kodu medya-v1'de onaylanan kisisel-v1
kodudur (Cinzel 500 isimler, EB Garamond Italic slogan, altin doku);
doku profili KAYNAK DOSYANIN KENDI yazisindan olculur.

Kapilar (her dosyada, olculur):
  boy     : yeni yazinin govde yuksekligi kaynaktakini ASMAZ (sigmazsa kuculur)
  kalinti : eski yazi silinen alanda yuksek gecirgen artik <= temiz serit referansi
  sembol  : glif + sonsuzluk bolgeleri kaynakla BIREBIR (kayit oncesi fark 0)
  cakisma : yeni yazi glif/sonsuzluk bolgelerine girmez
"""
import argparse, json, sys, time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import olcum

Image.MAX_IMAGE_PIXELS = None
T0 = time.time()
PAY = 6              # temizlik maskesi genisletme payi (px)
KAPI_PAY = 3         # kalinti kapisinda yeni yazinin etrafinda birakilan pay
BLOK = 16
# Kalinti tabani: JPEG q95'te tek bir niceleme adimi ~1-2 birim/255'tir; bu
# esigin altindaki artik kaynak dosyanin KENDI gurultusunden ayirt edilemez.
TABAN_BLOK = 2.0
TABAN_P999 = 4.0


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


def kisisel_kur(kok):
    sys.path.insert(0, str(Path(kok) / "scripts" / "kisisel"))
    import pilot6, pilot7, pilot12
    import kisisel_pilot as kp
    return pilot6, pilot7, pilot12, kp


def profil(im_a, hp, kutu):
    """Kaynak yazinin satir medyan RGB profili (altin dokusu); KATI yazi maskesi."""
    mask, _ = olcum.yazi_maskesi(hp, kutu)
    x0, y0, x1, y1 = kutu
    sat = []
    for y in range(y0, y1):
        m = mask[y, x0:x1]
        if m.sum() >= 3:
            sat.append(np.median(im_a[y, x0:x1][m], axis=0))
    if len(sat) < 4:
        raise RuntimeError("altin profili cikarilamadi")
    return np.asarray(sat, np.float32)


def temizle(im_a, mask, bolgeler, yaricap):
    """Eski yaziyi KAYNAK DOSYANIN KENDI zeminiyle kapatir (Telea inpaint)."""
    m = np.zeros(mask.shape, np.uint8)
    for (x0, y0, x1, y1) in bolgeler:
        m[y0:y1, x0:x1] |= mask[y0:y1, x0:x1].astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * PAY + 1,) * 2)
    m = cv2.dilate(m, k)
    return cv2.inpaint(im_a, m, yaricap, cv2.INPAINT_TELEA), m.astype(bool)


def govde_kutu(plaka_im):
    """Plakanin govde bandi (alfa > 40 satirlari) ve murekkep merkezi."""
    a = np.asarray(plaka_im)[..., 3]
    m = a > 40
    ys = np.nonzero(m.any(1))[0]
    sat = m.sum(1).astype(np.float32)
    ok = sat >= olcum.GOVDE_ORAN * np.median(sat[sat > 0])
    en, kos, i = 0, (int(ys[0]), int(ys[-1] + 1)), 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j < len(ok) and ok[j]:
                j += 1
            if j - i > en:
                en, kos = j - i, (i, j)
            i = j
        else:
            i += 1
    sut = m.sum(0).astype(np.float32)
    merkez = float((sut * np.arange(len(sut))).sum() / max(sut.sum(), 1))
    return kos, merkez


def isim_plakalari(P12, isimler, prof, cap, olcek):
    return {y: P12.plaka(isimler[y], prof[y], cap, olcek)[0] for y in ("sol", "sag")}


def blok_tasi(kaynak_a, hedef_a, mask, kutu, dx, tuy=3):
    """Ogeyi (glif / sonsuzluk) KAYNAKTAN birebir alip yatayda tasir.

    Murekkep pikselleri kaynaktakinin AYNISIDIR (olcek/aynalama yok); yalniz
    ince bir zemin halkasi yumusatilarak yeni zemine karisir.
    """
    x0, y0, x1, y1 = kutu
    H, W = mask.shape
    hx0 = x0 + dx
    if hx0 < 0:                              # tasinan blok tuval disina tasarsa kirpilir
        x0, hx0 = x0 - hx0, 0
    if hx0 + (x1 - x0) > W:
        x1 -= hx0 + (x1 - x0) - W
    blok = kaynak_a[y0:y1, x0:x1].astype(np.float32)
    m = mask[y0:y1, x0:x1].astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tuy + 1,) * 2)
    md = cv2.dilate(m, k)
    mg = cv2.GaussianBlur(md.astype(np.float32), (0, 0), tuy / 2.0)
    mg[cv2.erode(md, k) > 0] = 1.0          # cekirdekte birebir kopya (yumusatma yok)
    mg = mg[:, :, None]
    hedef = hedef_a[y0:y1, hx0:hx0 + (x1 - x0)].astype(np.float32)
    hedef_a[y0:y1, hx0:hx0 + (x1 - x0)] = np.clip(blok * mg + hedef * (1 - mg), 0, 255).astype(np.uint8)
    cekirdek = (cv2.erode(md, k) > 0) & (m > 0)   # kapida karsilastirilan piksel
    return {"kutu": [x0, y0, x1, y1], "dx": int(dx), "cekirdek": cekirdek,
            "yeni_kutu": [hx0, y0, hx0 + (x1 - x0), y1]}


def isim_yerlesimi(P12, isimler, prof, o, W, kenar):
    """Onayli poster kurali: satir = sol + bosluk + sonsuzluk + bosluk + sag,
    olculen bosluklar ve satir merkezi korunur; sigmazsa iki isim BIRLIKTE kuculur."""
    g_sol = o["sonsuz"][0] - o["sol"][1]
    g_sag = o["sag"][0] - o["sonsuz"][1]
    w_inf = o["sonsuz"][1] - o["sonsuz"][0]
    merkez = (o["sol"][0] + o["sag"][1]) / 2
    olcek, adim = 1.0, []
    for _ in range(8):
        pl = {y: P12.plaka(isimler[y], prof[y], o["cap"], olcek)[0] for y in ("sol", "sag")}
        w = {y: pl[y].width for y in pl}
        toplam = w["sol"] + g_sol + w_inf + g_sag + w["sag"]
        x0 = merkez - toplam / 2
        tasma = max(kenar - x0, (x0 + toplam) - (W - kenar), 0)
        if tasma <= 0:
            break
        hedef = (W - 2 * kenar) - g_sol - g_sag - w_inf
        olcek *= max(min(hedef / max(w["sol"] + w["sag"], 1), 0.99), 0.3)
        adim.append(round(olcek, 3))
    x0 = int(round(merkez - toplam / 2))
    yer = {"sol": x0, "inf": x0 + w["sol"] + g_sol,
           "sag": x0 + w["sol"] + g_sol + w_inf + g_sag}
    return olcek, pl, yer, {"bosluk": [int(g_sol), int(g_sag)], "kenar": int(kenar),
                            "satir": int(toplam), "satir_merkez": round(merkez, 1),
                            "kucultme": adim}


def tag_plakasi(P6, P7, kp, metin, prof, cap, sinir):
    fp = kp.FONT_DIR / P6.TAG_FONT
    punto = P6.cap_punto(fp, P6.TAG_W, cap)
    cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, metin)
    olcek = 1.0
    if cr.width > sinir:
        olcek = sinir / cr.width
        punto = max(int(round(punto * olcek)), 4)
        cr, cu, ct = P6.ciz_cap(fp, P6.TAG_W, punto, metin)
    p1, _ = P7.kuyruk_duzlestir(prof)
    return P7.altin_sekil(cr, p1, (cu, ct)), {"punto": punto, "genislik": cr.width,
                                              "olcek": round(olcek, 3), "sinir": int(sinir)}


def hp_harita(a):
    g = olcum.luma(a)
    return np.abs(g - cv2.GaussianBlur(g, (0, 0), 15))


def blok_maks(h, m):
    """Maskeli alanda 16x16 blok ortalamalarinin en buyugu (+ yeri)."""
    H, W = h.shape
    en, yer = 0.0, None
    for y in range(0, H - BLOK + 1, BLOK):
        for x in range(0, W - BLOK + 1, BLOK):
            mm = m[y:y + BLOK, x:x + BLOK]
            if mm.mean() > 0.5:
                v = float(h[y:y + BLOK, x:x + BLOK].mean())
                if v > en:
                    en, yer = v, (x, y)
    return en, yer


def kalinti_kapisi(temiz_a, temiz_maske, ref_kutular, kenar=0):
    """Eski yazi silindikten SONRA, yeni yazi eklenmeden ONCE olculur:
    temizlenen alandaki yuksek gecirgen artik, ayni gorseldeki temiz bir
    seritten (ayni yukseklik, ayni x araligi) buyuk olamaz."""
    h = hp_harita(temiz_a)
    if kenar > 0:                            # Serdar 25 Eyl: kenar payi bandi olcume girmez
        temiz_maske = temiz_maske.copy()
        temiz_maske[:, :kenar] = False
        temiz_maske[:, temiz_maske.shape[1] - kenar:] = False
    r_blok, r_p999 = 0.0, 0.0
    for (x0, y0, x1, y1) in ref_kutular:     # ayni satirlarda / hemen yanindaki TEMIZ pencereler
        if x1 - x0 < BLOK or y1 - y0 < BLOK:
            continue
        ref = h[y0:y1, x0:x1]
        v, _ = blok_maks(ref, np.ones(ref.shape, bool))
        r_blok = max(r_blok, v)
        r_p999 = max(r_p999, float(np.percentile(ref, 99.9)))
    if temiz_maske.sum() < 50:
        return {"gecti": False, "not": "temizlenen alan yok"}
    a_blok, a_yer = blok_maks(h, temiz_maske)
    a_p999 = float(np.percentile(h[temiz_maske], 99.9))
    return {"gecti": bool(a_blok <= max(r_blok, TABAN_BLOK)
                          and a_p999 <= max(r_p999 * 1.2, TABAN_P999)),
            "blok": round(a_blok, 2), "blok_ref": round(r_blok, 2), "blok_yeri": a_yer,
            "p999": round(a_p999, 2), "p999_ref": round(r_p999, 2),
            "piksel": int(temiz_maske.sum()), "pencere": len(ref_kutular)}


def yanyana(eski, yeni, yol, hedef_h=1600):
    """Serdar incelemesi icin "eski | yeni" yan yana gorsel."""
    o = hedef_h / eski.height
    a = eski.resize((int(eski.width * o), hedef_h), Image.LANCZOS)
    b = yeni.resize((int(yeni.width * o), hedef_h), Image.LANCZOS)
    ara = 24
    t = Image.new("RGB", (a.width + b.width + ara, hedef_h), (245, 245, 245))
    t.paste(a, (0, 0)); t.paste(b, (a.width + ara, 0))
    t.save(yol, quality=92, subsampling=1)
    return t.size


def maskeye_yaz(hedef, alfa, x, y):
    """Plakayi maskeye islerken tuval disinda kalan kismi KIRPAR."""
    h, w = alfa.shape
    H, W = hedef.shape
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x1 > x0 and y1 > y0:
        hedef[y0:y1, x0:x1] |= alfa[y0 - y:y1 - y, x0 - x:x1 - x]
    return [x, y, x + w, y + h]


def ink_merkez(mask, kutu):
    x0, y0, x1, y1 = kutu
    sut = mask[y0:y1, x0:x1].sum(0).astype(np.float32)
    return x0 + float((sut * np.arange(x1 - x0)).sum() / max(sut.sum(), 1))


def dosya_isle(yol, cihaz, isimler, mesaj, cikti, P6, P7, P12, kp, kenar, olcum_hazir=None):
    t0 = time.time()
    im = Image.open(yol).convert("RGB")
    o, mask, hp = olcum_hazir if olcum_hazir else olcum.olc(im, cihaz)
    a = np.asarray(im)
    W, H = im.size

    def kirp(k):
        return (max(k[0], 0), max(k[1], 0), min(k[2], W), min(k[3], H))

    prof = {y: profil(a, hp, (o[y][0], o["isim_bant"][0], o[y][1], o["isim_bant"][1]))
            for y in ("sol", "sag")}
    tprof = profil(a, hp, (o["tag_kutu"][0], o["tag_bant"][0], o["tag_kutu"][2], o["tag_bant"][1]))

    olcek, pl, yer, duzen = isim_yerlesimi(P12, isimler, prof, o, W, kenar)
    duzen["kenar_kaynak"] = "MIDNIGHT_BLUE"  # dokulu zeminde kendi olcumu guvenilir degil
    sinir = W - 2 * kenar                    # mesaj da sanat eserinin kendi genislik zarfina sigar
    tg, tbilgi = tag_plakasi(P6, P7, kp, mesaj, tprof, o["tag_cap"], sinir)

    # yeni isim murekkep merkezleri -> glif ve sonsuzluk bu merkezlere gore kayar
    yeni_merkez, yeni_kutu, govde = {}, {}, {}
    for y in ("sol", "sag"):
        (gy0, gy1), mx = govde_kutu(pl[y])
        px = int(yer[y])
        py = int(round((o["isim_govde"][0] + o["isim_govde"][1]) / 2 - (gy0 + gy1) / 2))
        yeni_merkez[y] = px + mx
        yeni_kutu[y] = (px, py)
        govde[y] = int(gy1 - gy0)

    # tasinacak ogeler: sonsuzluk + iki kucuk glif (piksel olarak kaynaktan)
    tasi = []
    inf_kutu = kirp((o["sonsuz"][0] - PAY, o["isim_bant"][0] - PAY,
                     o["sonsuz"][1] + PAY, o["isim_bant"][1] + PAY))
    tasi.append((inf_kutu, int(yer["inf"]) - o["sonsuz"][0]))
    glif = o.get("glif")
    if glif:
        gb = glif["bant"]
        gk = sorted(glif["kutular"], key=lambda k: k[0])
        if len(gk) == 2:
            for y, k in zip(("sol", "sag"), gk):
                kutu = kirp((k[0] - PAY, gb[0] - PAY, k[1] + PAY, gb[1] + PAY))
                dx = int(round(yeni_merkez[y] - ink_merkez(mask, kutu)))
                tasi.append((kutu, dx))

    # 1) eski yazi ve tasinan ogelerin ESKI yeri kaynagin kendi zeminiyle temizlenir
    yaricap = max(3, o["cap"] // 8)
    bolgeler = [kirp((o["sol"][0] - PAY, o["isim_bant"][0] - PAY, o["sol"][1] + PAY, o["isim_bant"][1] + PAY)),
                kirp((o["sag"][0] - PAY, o["isim_bant"][0] - PAY, o["sag"][1] + PAY, o["isim_bant"][1] + PAY)),
                kirp((o["tag_kutu"][0] - PAY, o["tag_bant"][0] - PAY, o["tag_kutu"][2] + PAY, o["tag_bant"][1] + PAY))]
    bolgeler += [k for k, _ in tasi]
    kati = mask.copy()                       # kenar maskesi + KATI govde (kalin cizgi ici)
    for k in bolgeler:
        km, _ = olcum.yazi_maskesi(hp, k, oran=0.15)
        kati |= km
    temiz_a, temiz_maske = temizle(a, kati, bolgeler, yaricap)
    temiz_kopya = temiz_a.copy()             # kalinti kapisi bu goruntude olculur

    # 2) tasinan ogeler birebir kopyalanir
    tasima = []
    for kutu, dx in tasi:
        tasima.append(blok_tasi(a, temiz_a, kati, kutu, dx))

    # 3) yeni isimler ve mesaj
    t = Image.fromarray(temiz_a).convert("RGBA")
    yeni_maske = np.zeros((H, W), bool)
    kutular = {}
    for y in ("sol", "sag"):
        p = pl[y]
        px, py = yeni_kutu[y]
        t.alpha_composite(p, (px, py))
        kutular[y] = maskeye_yaz(yeni_maske, np.asarray(p)[..., 3] > 8, px, py)
    (tgy0, tgy1), tmx = govde_kutu(tg)
    tx = int(round((o["tag_kutu"][0] + o["tag_kutu"][2]) / 2 - tmx))
    ty = int(round((o["tag_govde"][0] + o["tag_govde"][1]) / 2 - (tgy0 + tgy1) / 2))
    t.alpha_composite(tg, (tx, ty))
    kutular["tag"] = maskeye_yaz(yeni_maske, np.asarray(tg)[..., 3] > 8, tx, ty)

    son = t.convert("RGB")
    son_a = np.asarray(son)

    # 4) kapilar
    tasinan_maske = np.zeros((H, W), bool)
    sembol_fark, cak = 0, False
    for tt in tasima:
        x0, y0, x1, y1 = tt["kutu"]
        c = tt["cekirdek"]
        hx0 = x0 + tt["dx"]
        kaynak = a[y0:y1, x0:x1][c]
        hedefb = son_a[y0:y1, hx0:hx0 + (x1 - x0)][c]
        sembol_fark = max(sembol_fark, int(np.abs(kaynak.astype(np.int16) - hedefb.astype(np.int16)).max()))
        yk = np.zeros((H, W), bool)
        yk[y0:y1, hx0:hx0 + (x1 - x0)] = c
        tasinan_maske |= yk
        cak = cak or bool((yeni_maske & yk).any())

    kapi_cap = {y: govde[y] for y in ("sol", "sag")}
    # referans: ayni satirlarda, yazinin yaninda kalan TEMIZ pencereler + ust serit
    ib, tb = o["isim_bant"], o["tag_bant"]
    ref_h = ib[1] - ib[0]
    ref_y1 = max(((o.get("glif") or {}).get("bant") or [ib[0]])[0] - 20, ref_h + 1)
    ref_kutular = [kirp((o["sol"][0], ref_y1 - ref_h, o["sag"][1], ref_y1)),
                   kirp((max(o["sol"][0] - 8 - 3 * ref_h, 0), ib[0], max(o["sol"][0] - 8, 1), ib[1])),
                   kirp((min(o["sag"][1] + 8, W - 1), ib[0], min(o["sag"][1] + 8 + 3 * ref_h, W), ib[1])),
                   kirp((max(o["tag_kutu"][0] - 8 - 3 * ref_h, 0), tb[0], max(o["tag_kutu"][0] - 8, 1), tb[1])),
                   kirp((min(o["tag_kutu"][2] + 8, W - 1), tb[0], min(o["tag_kutu"][2] + 8 + 3 * ref_h, W), tb[1]))]
    yeni_tag_cap = int(tgy1 - tgy0)

    kapi = {
        "boy": {"gecti": all(kapi_cap[y] <= o["cap"] for y in ("sol", "sag")) and yeni_tag_cap <= o["tag_cap"],
                "cap": o["cap"], "yeni_cap": kapi_cap, "tag_cap": o["tag_cap"], "yeni_tag_cap": yeni_tag_cap},
        "kalinti": kalinti_kapisi(temiz_kopya, temiz_maske, ref_kutular, kenar),
        "sembol": {"gecti": sembol_fark == 0, "maks_fark": sembol_fark, "oge": len(tasima),
                   "dx": [tt["dx"] for tt in tasima]},
        "cakisma": {"gecti": not cak},
    }
    kapi["gecti"] = all(v["gecti"] for v in kapi.values() if isinstance(v, dict))

    cikti.mkdir(parents=True, exist_ok=True)
    yeni_yol = cikti / Path(yol).name
    son.save(yeni_yol, quality=95, subsampling=0)
    tekrar = np.asarray(Image.open(yeni_yol).convert("RGB"))
    jf = 0
    for tt in tasima:
        x0, y0, x1, y1 = tt["kutu"]; c = tt["cekirdek"]; hx0 = x0 + tt["dx"]
        jf = max(jf, int(np.abs(a[y0:y1, x0:x1][c].astype(np.int16)
                                - tekrar[y0:y1, hx0:hx0 + (x1 - x0)][c].astype(np.int16)).max()))
    kapi["sembol"]["jpeg_sonrasi_maks_fark"] = jf
    kars = cikti / f"KARSILASTIRMA_{Path(yol).stem}.jpg"
    yanyana(im, son, kars)

    return {"dosya": Path(yol).name, "cihaz": cihaz, "olcum": o, "olcek": round(olcek, 3),
            "duzen": duzen, "tagline": tbilgi, "kutular": kutular, "kapi": kapi,
            "cikti": [str(yeni_yol), str(kars)], "sure_sn": round(time.time() - t0, 1)}


def yerlesim_dogrula(olcumler, esik=2.0):
    """Ayni cihazda 4 rengin YERLESIMI ayni mi? (Serdar 25 Eyl kurali)

    Karsilastirma capasi sonsuzluk isaretinin merkezidir: simetrik ve yuksek
    kontrastli oldugu icin doku esigine duyarli DEGILDIR. Kenar tabanli kutular
    (isim kutusu, glif kutusu) dokulu zeminde esik yukseldigi icin 10-25 px
    daralir; bunlar yalniz BILGI olarak raporlanir.
    """
    rapor = {}
    for cihaz, kayit in olcumler.items():
        inf = {r: (o["sonsuz"][0] + o["sonsuz"][1]) / 2 for r, o in kayit.items()}
        ref = inf.get("Midnight_Blue")
        if ref is None:
            rapor[cihaz] = {"gecti": False, "not": "Midnight_Blue dosyasi yok"}
            continue
        sapma = {r: round(v - ref, 1) for r, v in inf.items()}
        en = max(abs(v) for v in sapma.values())
        rapor[cihaz] = {
            "gecti": bool(en <= esik), "sonsuz_merkez_sapma": sapma, "maks": round(en, 1),
            "kenar_mb": kayit["Midnight_Blue"].get("sanat_kenar"),
            "kenar_kendi": {r: o.get("sanat_kenar") for r, o in kayit.items()},
            "isim_kutu_sapma": {r: [o["sol"][0] - kayit["Midnight_Blue"]["sol"][0],
                                    o["sag"][1] - kayit["Midnight_Blue"]["sag"][1]]
                                for r, o in kayit.items()},
        }
    return rapor


def renk_adi(ad):
    for r in ("Midnight_Blue", "Deep_Black", "Champagne_Ivory", "Warm_Parchment"):
        if r in ad:
            return r
    return "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--girdi", required=True, help="kaynak JPG klasoru")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--kisisel", required=True, help="kisisel-v1 arsiv koku")
    ap.add_argument("--isimler", default="EMILY,JAMES")
    ap.add_argument("--mesaj", default="It Began With a Kiss in the Rain")
    ap.add_argument("--rapor", default="WP_KISISEL_RAPOR.json")
    ap.add_argument("--eski", default="", help="onceki ciktilar (fark kontrolu icin)")
    a = ap.parse_args()
    P6, P7, P12, kp = kisisel_kur(a.kisisel)
    sol, sag = a.isimler.split(",")
    isimler = {"sol": sol.strip(), "sag": sag.strip()}
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    dosyalar = []
    for p in sorted(Path(a.girdi).rglob("*.jpg")):
        if "Watch" in p.name:
            continue
        cihaz = next((c for c in ("phone", "tablet", "desktop") if c in p.stem.lower()), None)
        if cihaz:
            dosyalar.append((p, cihaz))

    # 1. GECIS: olcum (yerlesim dogrulamasi icin)
    olcumler, ham = {}, {}
    for p, cihaz in dosyalar:
        try:
            o, m, hp = olcum.olc(Image.open(p).convert("RGB"), cihaz)
            ham[p] = (o, m, hp)
            olcumler.setdefault(cihaz, {})[renk_adi(p.name)] = o
        except Exception as e:                                     # noqa: BLE001
            log(f"olcum HATA {p.name}: {e!r}")
    dog = yerlesim_dogrula(olcumler)
    (cikti / "YERLESIM_DOGRULAMA.json").write_text(json.dumps(dog, indent=1))
    for cihaz, d in dog.items():
        log(f"yerlesim {cihaz}: gecti={d['gecti']} maks_sapma={d.get('maks')} kenar_mb={d.get('kenar_mb')}")
    if not all(d["gecti"] for d in dog.values()):
        log("DUR: 4 renkte yerlesim sapmasi 2 px'i asiyor")
        return 2

    # 2. GECIS: uretim (kenar payi ayni cihazin Midnight_Blue olcumunden)
    sonuc = []
    for i, (p, cihaz) in enumerate(dosyalar, 1):
        kenar = dog[cihaz]["kenar_mb"]
        try:
            r = dosya_isle(p, cihaz, isimler, a.mesaj, cikti / p.parent.name,
                           P6, P7, P12, kp, kenar, ham.get(p))
        except Exception as e:                                     # noqa: BLE001
            r = {"dosya": p.name, "cihaz": cihaz, "hata": repr(e), "kapi": {"gecti": False}}
        if a.eski:
            onceki = Path(a.eski) / p.parent.name / p.name
            if onceki.exists() and "hata" not in r:
                x = np.asarray(Image.open(onceki).convert("RGB")).astype(np.int16)
                y = np.asarray(Image.open(r["cikti"][0]).convert("RGB")).astype(np.int16)
                r["onceki_fark"] = int(np.abs(x - y).max()) if x.shape == y.shape else -1
        sonuc.append(r)
        log(f"{i}/{len(dosyalar)} {p.name} kapi={r['kapi']['gecti']} "
            f"fark={r.get('onceki_fark', '-')} sure={r.get('sure_sn')}")
    (cikti / a.rapor).write_text(json.dumps(sonuc, indent=1))
    gecen = sum(1 for r in sonuc if r["kapi"]["gecti"])
    degisen = [r["dosya"] for r in sonuc if r.get("onceki_fark", 0) not in (0, None)]
    log(f"TOPLAM {gecen}/{len(sonuc)} kapidan gecti | onceki ciktidan farkli: {len(degisen)}")
    for d in degisen:
        log(f"  farkli: {d}")
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
