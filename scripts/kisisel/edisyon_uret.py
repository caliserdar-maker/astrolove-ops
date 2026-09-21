#!/usr/bin/env python3
"""
Edisyon uretimi (Black, Pure White, Modern, Vintage) - D/E/F adimlari.

Blue hatti (pilot16) aynen kullanilir; edisyona ozel uc nokta:
  1. ZEMIN: her edisyonun oran-ici sayfa render'i (Canva kopyasindan zemin
     disindaki ogeler silinerek alindi). Tuval olcusu referans sayfayla
     birebir ayni oldugu icin hizalama BIRIMDIR (olcek 1.0, dx 0, dy 0);
     edisyona ozel hiza sabiti yoktur, uretimde arama yapilmaz.
  2. DOKU: yazi profili edisyonun KENDI sayfa 28'indeki CANCER/LIBRA
     isimlerinden cikarilir (Serdar karari 21 Eyl 2026).
  3. ISIM KAPISI (Claude karari, Serdar onayli 21 Eyl 2026):
     - sekil: Blue'nun oran ici onayli isim satiriyla RENKTEN BAGIMSIZ
       karsilastirma (murekkep maskesi; kayma <= 1 px, IoU >= 0.95)
     - doku: edisyonun kendi sayfa 28'indeki isimlerle (ortalama RGB,
       parlaklik std, dikey profil farki <= 5)
     Serdar bir edisyonu onaylayana kadar ciktilar ONAY BEKLIYOR sayilir.

Kapi esikleri Blue ile ayni; hicbiri gevsetilmez. Girdi kapisi her kosuda
calisir (bayat/eksik girdi -> kosu HATA ile durur).
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from kisisel_pilot import FONT_DIR, NEW_LEFT, NEW_RIGHT, TAGLINES, rc, DEST
from pilot6 import LUMA, MUREKKEP, kumeler, ONAYLI_DIR, ISIM_FONT, ISIM_W
from pilot12 import (KENAR_ORAN, NORM_W, ORANLAR, OUT, REF_SAYFA,
                     TAG_TABAN_CAP, TAG_TABAN_SINIR, norm)
import pilot12
import pilot16
from pilot16 import (BLOK, BLOK_ORT, BLOK_TEPE, GENISLET, KAPI_PAY,
                     blok_kapisi, delta_kes, oge_ve_yildiz, poster_kur)

Image.MAX_IMAGE_PIXELS = None

EDISYONLAR = ["black", "pure_white", "modern", "vintage"]
YOL = OUT / "EDISYONLAR"
DEST_E = DEST + "/EDISYONLAR"
SABIT_YOL = Path(__file__).resolve().parent / "ORAN_SABITLERI.json"

CIFTLER = [("JACQUELINE", "QUINN", None, "Written in the Stars Long Before Us"),
           (NEW_LEFT, NEW_RIGHT, None, TAGLINES["A"])]

# --- edisyon kapi esikleri (Serdar onayi 21 Eyl 2026) ---
SEKIL_KAYMA = 1        # px
SEKIL_IOU = 0.95
DOKU_FARK = 5.0        # ortalama RGB / parlaklik std / dikey profil
BOSLUK_PAY = 2         # olculen bosluk ile kilitli bosluk arasindaki azami fark
T0 = time.time()


def log(*a):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')} +{time.time() - T0:6.1f}s]",
          *a, flush=True)


def sabitler():
    return json.loads(SABIT_YOL.read_text(encoding="utf-8"))["oranlar"]


# ------------------------------------------------------------- murekkep

def acik_zemin(a):
    """Zemin acik mi? (yazi koyu) - Pure White / Modern / Vintage acik."""
    return float(np.median(a @ LUMA)) > 128


def murekkep(a):
    """Yon farkindali murekkep maskesi: koyu zeminde parlak, acikta koyu yazi."""
    L = a @ LUMA
    z = float(np.median(L))
    if z > 128:
        alt = float(np.percentile(L, 0.5))
        return L < z - max(12.0, (z - alt) * 0.35)
    return L > MUREKKEP


def profil_cikar(ref_a, bant, x_araligi):
    """Bir isim kutusundan satir satir medyan RGB profili (altin_isim girdisi)."""
    y0, y1 = bant
    x0, x1 = x_araligi
    kes = ref_a[y0:y1, x0:x1]
    m = murekkep(kes)
    prof = []
    for y in range(kes.shape[0]):
        mr = m[y]
        if mr.sum() >= 3:
            prof.append(np.median(kes[y][mr], axis=0).tolist())
        elif prof:
            prof.append(prof[-1])
    if not prof:
        raise SystemExit("PROFIL: isim kutusunda murekkep bulunamadi")
    return np.asarray(prof, np.float32)


def doku_ozeti(a, m):
    """Bir yazi kirpiminin dokusu: ortalama RGB, parlaklik std, dikey profil."""
    px = a[m]
    prof = []
    for y in range(a.shape[0]):
        if m[y].sum() >= 3:
            prof.append(np.median(a[y][m[y]], axis=0))
    return {"ort_rgb": px.mean(axis=0), "parlaklik_std": float((px @ LUMA).std()),
            "profil": np.asarray(prof, np.float32), "px": int(m.sum())}


def profil_farki(p1, p2):
    """Iki dikey profili ayni uzunluga gerip ortalama mutlak fark."""
    n = min(len(p1), len(p2))
    if n < 4:
        return 999.0
    i1 = np.linspace(0, len(p1) - 1, n).round().astype(int)
    i2 = np.linspace(0, len(p2) - 1, n).round().astype(int)
    return float(np.abs(p1[i1] - p2[i2]).mean())


# ----------------------------------------------------------- girdi kapisi

def girdi_kapisi(ed, oran, ham_yol, zemin_yol, o28, sabit):
    """Bayat/eksik girdiyi kosu basinda yakalar (Blue'daki kapinin edisyon hali).

    Blue'da kapi OLCUM.json'un 4 sayfadan olculdugunu dogruluyordu; edisyonlarda
    olcum tek sayfadan (28) yapildigi icin bosluk ORAN_SABITLERI'ndeki kilitli
    degerden alinir ve olculen bosluk onunla karsilastirilir.
    """
    hata = []
    tuval = tuple(sabit["tuval"])
    with Image.open(ham_yol) as im:
        hs = im.size
    with Image.open(zemin_yol) as im:
        zs = im.size
    if hs != tuval:
        hata.append(f"referans sayfa {hs}, oran tuvali {tuval} (bayat kopya)")
    if zs != tuval:
        hata.append(f"zemin {zs}, oran tuvali {tuval} (bayat ya da yanlis zemin)")
    # isim satiri bulundu mu: sol isim < sonsuz < sag isim, ucu de bos degil
    sira = [o28.get("sol_isim"), o28.get("sonsuz"), o28.get("sag_isim")]
    if any(not v or v[1] <= v[0] for v in sira):
        hata.append(f"isim satiri bulunamadi: {sira}")
    elif not (sira[0][1] <= sira[1][0] and sira[1][1] <= sira[2][0]):
        hata.append(f"isim satiri sirasi bozuk: {sira}")
    if tuple(o28["kaynak_boyut"]) != tuval:
        hata.append(f"olculen kaynak {tuple(o28['kaynak_boyut'])}, tuval {tuval}")
    olculen = (o28["bosluk"][0] + o28["bosluk"][1]) / 2
    kilit = sabit["bosluk"]
    if abs(olculen - kilit) > BOSLUK_PAY:
        hata.append(f"olculen bosluk {olculen:.1f}, kilitli {kilit} "
                    f"(fark {abs(olculen - kilit):.1f} > {BOSLUK_PAY})")
    if hata:
        for h in hata:
            log(f"GIRDI KAPISI {ed} {oran}: {h}")
        return False
    log(f"girdi kapisi GECTI: {ed} {oran} (tuval {tuval}, bosluk {olculen:.1f}/{kilit})")
    return True


# ------------------------------------------------------------ oran kurulum

def oran_kur(ed, oran, o28, sabit):
    """pilot16.oran_kur'un edisyon hali: zemin oran-ici sayfa render'i."""
    t0 = time.time()
    ham = Image.open(YOL / ed / "ham" / f"{oran}_p{REF_SAYFA}.jpg").convert("RGB")
    ref, _ = norm(ham)
    zem = Image.open(YOL / ed / "zemin" / f"{oran}.png").convert("RGB")
    zemin, _ = norm(zem)
    if zemin.size != ref.size:
        zemin = zemin.resize(ref.size, Image.LANCZOS)

    ref_a = np.asarray(ref).astype(np.float32)
    zemin_a = np.asarray(zemin).astype(np.float32)
    fark = np.abs(ref_a - zemin_a).max(axis=2)

    ib, sb, tb = o28["isim_bant"], o28["sembol_bant"], o28["tag_bant"]
    pay = GENISLET + 8
    bolge = [(0, max(sb[0] - pay, 0), NORM_W, min(tb[1] + pay, ref.height))]
    hedef = {"sonsuz": pilot16.kume_kutusu(fark, ib, *o28["sonsuz"]),
             "sembol_sol": pilot16.kume_kutusu(fark, sb, *o28["sembol"][0]),
             "sembol_sag": pilot16.kume_kutusu(fark, sb, *o28["sembol"][1]),
             "isim_sol": pilot16.kume_kutusu(fark, ib, *o28["sol_isim"]),
             "isim_sag": pilot16.kume_kutusu(fark, ib, *o28["sag_isim"]),
             "tagline": (o28["tag_x"][0], tb[0], o28["tag_x"][1], tb[1])}
    luma_maske = murekkep(ref_a)
    bil, alfa, genis, yildiz, yildiz_n = oge_ve_yildiz(fark, bolge, hedef, luma_maske)

    a3 = alfa[..., None]
    temiz_a = ref_a * (1 - a3) + zemin_a * a3

    oge = {}
    for ad, b in bil.items():
        if ad == "tagline":
            continue
        d, m = delta_kes(ref_a, zemin_a, b, alfa)
        g = b["gorsel"]
        oge[ad] = {"delta": d, "maske": m, "kutu": b["kutu"], "gorsel": g,
                   "w": g[2] - g[0], "h": g[3] - g[1],
                   "pay": (g[0] - b["kutu"][0], g[1] - b["kutu"][1])}

    prof = {"sol": profil_cikar(ref_a, ib, o28["sol_isim"]),
            "sag": profil_cikar(ref_a, ib, o28["sag_isim"])}
    pilot12.PROFIL = prof

    cap = {"sol": hedef["isim_sol"][3] - hedef["isim_sol"][1],
           "sag": hedef["isim_sag"][3] - hedef["isim_sag"][1]}
    s = {"oran": oran, "edisyon": ed, "tuval": list(ham.size),
         "bosluk": sabit["bosluk"],
         "kenar_payi": int(round(NORM_W * KENAR_ORAN)),
         "kullanilabilir": int(NORM_W - 2 * round(NORM_W * KENAR_ORAN)),
         "cap": cap, "tag_cap": tb[1] - tb[0],
         "tag_sinir": int(round(TAG_TABAN_SINIR * (tb[1] - tb[0]) / TAG_TABAN_CAP)),
         "sonsuz_w": oge["sonsuz"]["w"],
         "isim_y": (ib[0] + ib[1]) / 2,
         "isim_bant": list(ib), "sembol_bant": list(sb), "tag_bant": list(tb),
         "tag_y": (tb[0] + tb[1]) / 2,
         "kutular": {a: list(b["kutu"]) for a, b in oge.items()},
         "maske_px": int(genis.sum()), "yildiz_bileseni": yildiz_n,
         "acik_zemin": bool(acik_zemin(ref_a)),
         "kurulum_sn": round(time.time() - t0, 1)}
    S = {"ref": ref, "zemin_a": zemin_a, "temiz_a": temiz_a, "oge": oge,
         "prof": prof, "alfa": alfa, "genis": genis, "yildiz": yildiz}
    return s, S


# -------------------------------------------------------------- isim kapisi

def isim_kapisi(poster, ref, oran, kirpimlar, o28):
    """Sekil: Blue onayli satiriyla renkten bagimsiz. Doku: edisyonun kendisi."""
    onayli = Image.open(ONAYLI_DIR / f"ISIM_SATIRI_{oran}.png").convert("RGB")
    x0, y0 = kirpimlar[oran]["kirpim"][:2]
    yeni = poster.convert("RGB").crop((x0, y0, x0 + onayli.width, y0 + onayli.height))
    mo = murekkep(np.asarray(onayli).astype(np.float32))
    mn = murekkep(np.asarray(yeni).astype(np.float32))
    ko, kn = kumeler(mo, 12), kumeler(mn, 12)
    if len(ko) < 3 or len(kn) < 3:
        return {"gecti": False, "sebep": f"kume {len(ko)}/{len(kn)}"}
    kayma = max(abs(ko[0][0] - kn[0][0]), abs(ko[-1][1] - kn[-1][1]))
    iou = float((mo & mn).sum()) / max(float((mo | mn).sum()), 1.0)
    # Dikey kayma: edisyonun isim bandi kendi tasariminda birkac px kayik
    # olabilir (olculdu: Modern 4x5 bandi Blue'dan 2 px asagida). Sekil
    # olcusunu bu tasarim farki bozmasin diye tam sayi (dx, dy) kaldirilip
    # hizali IoU da raporlanir; esik degismez.
    en_iou, en_dx, en_dy = iou, 0, 0
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            a = np.roll(np.roll(mn, -dy, axis=0), -dx, axis=1)
            r = float((mo & a).sum()) / max(float((mo | a).sum()), 1.0)
            if r > en_iou:
                en_iou, en_dx, en_dy = r, dx, dy

    # doku: uretilen isim satiri vs edisyonun kendi sayfa 28 isimleri
    ra = np.asarray(ref).astype(np.float32)
    ib = o28["isim_bant"]
    kaynak = {}
    for y, xr in (("sol", o28["sol_isim"]), ("sag", o28["sag_isim"])):
        kes = ra[ib[0]:ib[1], xr[0]:xr[1]]
        kaynak[y] = doku_ozeti(kes, murekkep(kes))
    ya = np.asarray(yeni).astype(np.float32)
    uretilen = doku_ozeti(ya, mn)
    ref_rgb = np.mean([kaynak["sol"]["ort_rgb"], kaynak["sag"]["ort_rgb"]], axis=0)
    ref_std = np.mean([kaynak["sol"]["parlaklik_std"], kaynak["sag"]["parlaklik_std"]])
    d_rgb = float(np.abs(uretilen["ort_rgb"] - ref_rgb).max())
    d_std = float(abs(uretilen["parlaklik_std"] - ref_std))
    d_prof = min(profil_farki(uretilen["profil"], kaynak[y]["profil"])
                 for y in ("sol", "sag"))
    doku_gecti = max(d_rgb, d_std, d_prof) <= DOKU_FARK
    sekil_gecti = kayma <= SEKIL_KAYMA and iou >= SEKIL_IOU
    return {"gecti": bool(sekil_gecti and doku_gecti),
            "sekil": {"gecti": bool(sekil_gecti), "kayma_px": int(kayma),
                      "iou": round(iou, 4), "iou_hizali": round(en_iou, 4),
                      "hiza": [en_dx, en_dy],
                      "murekkep_px": [int(mo.sum()), int(mn.sum())]},
            "doku": {"gecti": bool(doku_gecti), "ort_rgb_fark": round(d_rgb, 2),
                     "parlaklik_std_fark": round(d_std, 2),
                     "profil_fark": round(d_prof, 2)},
            "esik": {"kayma": SEKIL_KAYMA, "iou": SEKIL_IOU, "doku": DOKU_FARK}}


def blue_taban(oran, kirpimlar):
    """Blue'nun KENDI posteri ayni kapidan gecerse IoU kac? (olculen taban)

    Onayli ISIM_SATIRI_<oran>.png bir referans render'dir, uretilen posterin
    birebir kirpimi degil; bu yuzden Blue'nun onayli kapiyi (kayma <=1,
    ic fark <=3) GECEN posteri bile IoU'da 1.0 vermez. Edisyon sonuclari bu
    tabanla birlikte okunmalidir.
    """
    p = OUT / "ORANLAR" / f"ALTIN_{oran}.jpg"
    if not p.exists():
        return None
    onayli = Image.open(ONAYLI_DIR / f"ISIM_SATIRI_{oran}.png").convert("RGB")
    x0, y0 = kirpimlar[oran]["kirpim"][:2]
    yeni = Image.open(p).convert("RGB").crop(
        (x0, y0, x0 + onayli.width, y0 + onayli.height))
    mo = murekkep(np.asarray(onayli).astype(np.float32))
    mn = murekkep(np.asarray(yeni).astype(np.float32))
    iou = float((mo & mn).sum()) / max(float((mo | mn).sum()), 1.0)
    en = iou
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            a = np.roll(np.roll(mn, -dy, axis=0), -dx, axis=1)
            en = max(en, float((mo & a).sum()) / max(float((mo | a).sum()), 1.0))
    return {"iou": round(iou, 4), "iou_hizali": round(en, 4)}


def iz_kontrol(poster, s, ed, oran):
    y0 = max(s["sembol_bant"][0] - 20, 0)
    y1 = min(s["isim_bant"][1] + 20, poster.height)
    k = poster.crop((0, y0, NORM_W, y1))
    k = k.resize((k.width * 3, k.height * 3), Image.LANCZOS)
    k = ImageEnhance.Brightness(k).enhance(2.5)
    k = k.resize((k.width // 2, k.height // 2), Image.LANCZOS)
    dd = ImageDraw.Draw(k)
    from kisisel_pilot import font_yukle
    dd.text((14, 8), f"{ed} {oran} - 3x buyutme, 2.5x parlaklik",
            fill=(255, 220, 140) if not s["acik_zemin"] else (40, 30, 20),
            font=font_yukle(FONT_DIR / ISIM_FONT, 28, ISIM_W))
    return k


# -------------------------------------------------------------------- akis

def girdileri_indir(yerel):
    if yerel:
        return
    for ed in EDISYONLAR:
        (YOL / ed / "ham").mkdir(parents=True, exist_ok=True)
        (YOL / ed / "zemin").mkdir(parents=True, exist_ok=True)
        rc("copy", f"{DEST_E}/{ed}/ham", str(YOL / ed / "ham"), timeout=300)
        for oran in ORANLAR:
            rc("copy", f"{DEST}/HAZIR/zemin_{ed}_{oran}.png",
               str(YOL / ed / "zemin"), timeout=300)
            p = YOL / ed / "zemin" / f"zemin_{ed}_{oran}.png"
            if p.exists():
                p.rename(YOL / ed / "zemin" / f"{oran}.png")
    log("girdiler indi")


def kiyas(posterler, ed):
    """Bir edisyonun bes orani yan yana (isim satiri bandi)."""
    kes = []
    for oran in ORANLAR:
        if oran not in posterler:
            continue
        p, s = posterler[oran]
        y0 = max(s["sembol_bant"][0] - 10, 0)
        y1 = min(s["isim_bant"][1] + 10, p.height)
        k = p.crop((0, y0, NORM_W, y1)).resize((700, int(700 * (y1 - y0) / NORM_W)),
                                               Image.LANCZOS)
        kes.append((oran, k))
    if not kes:
        return None
    h = sum(k.height + 34 for _, k in kes)
    out = Image.new("RGB", (700, h), (18, 18, 22))
    d = ImageDraw.Draw(out)
    from kisisel_pilot import font_yukle
    f = font_yukle(FONT_DIR / ISIM_FONT, 22, ISIM_W)
    y = 0
    for oran, k in kes:
        d.text((8, y + 6), f"{ed} {oran}", fill=(230, 210, 160), font=f)
        out.paste(k, (0, y + 30))
        y += k.height + 34
    return out


def kos(a):
    YOL.mkdir(parents=True, exist_ok=True)
    girdileri_indir(a.yerel)
    sab = sabitler()
    kirpimlar = json.loads((ONAYLI_DIR / "ISIM_SATIRI_KIRPIM.json").read_text(
        encoding="utf-8"))
    from pilot11 import sayfa_olc
    if not a.yerel:
        (OUT / "ORANLAR").mkdir(parents=True, exist_ok=True)
        for oran in ORANLAR:
            rc("copy", f"{DEST}/ORANLAR/ALTIN_{oran}.jpg", str(OUT / "ORANLAR"),
               timeout=300)

    sonuc = {"_blue_taban": {o: blue_taban(o, kirpimlar) for o in ORANLAR}}
    log(f"Blue tabani: {json.dumps(sonuc['_blue_taban'], ensure_ascii=False)}")
    for ed in (a.edisyon or EDISYONLAR):
        sonuc[ed] = {}
        posterler = {}
        for oran in ORANLAR:
            ham_yol = YOL / ed / "ham" / f"{oran}_p{REF_SAYFA}.jpg"
            zem_yol = YOL / ed / "zemin" / f"{oran}.png"
            if not ham_yol.exists() or not zem_yol.exists():
                sonuc[ed][oran] = {"durum": "GIRDI YOK",
                                   "ham": ham_yol.exists(), "zemin": zem_yol.exists()}
                log(f"{ed} {oran}: GIRDI YOK (ham={ham_yol.exists()} "
                    f"zemin={zem_yol.exists()})")
                continue
            try:
                o28 = sayfa_olc(ham_yol)
            except (SystemExit, Exception) as e:                  # noqa: BLE001
                sonuc[ed][oran] = {"durum": "OLCUM YAPILAMADI", "sebep": str(e)[:200]}
                log(f"{ed} {oran}: OLCUM YAPILAMADI - {str(e)[:160]}")
                continue
            if not girdi_kapisi(ed, oran, ham_yol, zem_yol, o28, sab[oran]):
                sonuc[ed][oran] = {"durum": "GIRDI KAPISI KALDI"}
                continue
            s, S = oran_kur(ed, oran, o28, sab[oran])
            log(f"{ed} {oran}: kurulum {s['kurulum_sn']} sn, acik_zemin "
                f"{s['acik_zemin']}, yildiz {s['yildiz_bileseni']}, maske "
                f"{s['maske_px']} px, cap {s['cap']}")
            kayit = {"durum": "URETILDI", "kurulum_sn": s["kurulum_sn"],
                     "acik_zemin": s["acik_zemin"], "cap": s["cap"],
                     "bosluk": s["bosluk"], "ciftler": []}
            t_poster = []
            for sol, sag, ulke, tag in CIFTLER:
                t0 = time.time()
                poster, bilgi, _, _, yeni_genis = poster_kur(
                    s, S, {"sol": sol, "sag": sag}, tag)
                kapi = blok_kapisi(poster, S, s, yeni_genis)
                t_poster.append(time.time() - t0)
                satir = {"cift": f"{sol} - {sag}", "ulke": ulke,
                         "punto": bilgi["punto"], "olcek": bilgi["olcek"],
                         "blok_kapisi": kapi}
                if (sol, sag) == (NEW_LEFT, NEW_RIGHT):
                    ik = isim_kapisi(poster, S["ref"], oran, kirpimlar, o28)
                    satir["isim_kapisi"] = ik
                    kayit["isim_kapisi"] = ik
                    posterler[oran] = (poster, s)
                    pilot12.kaydet(poster, YOL / ed / f"ALTIN_{oran}.jpg")
                    iz_kontrol(poster, s, ed, oran).save(
                        YOL / ed / f"IZ_KONTROL_{ed}_{oran}.jpg", quality=88)
                kayit["ciftler"].append(satir)
                log(f"{ed} {oran} {sol}+{sag}: punto {bilgi['punto']} olcek "
                    f"%{bilgi['olcek'] * 100:.0f} blok kapisi "
                    f"{'GECTI' if kapi['gecti'] else 'KALDI'} "
                    f"({kapi['blok']} blok, en_ort {kapi['en_ort']}, "
                    f"en_tepe {kapi['en_tepe']})")
            if "isim_kapisi" in kayit:
                ik = kayit["isim_kapisi"]
                log(f"{ed} {oran} isim kapisi: {json.dumps(ik, ensure_ascii=False)}")
            kayit["poster_sn"] = round(sum(t_poster) / len(t_poster), 2)
            kayit["toplam_sn"] = round(s["kurulum_sn"] + sum(t_poster), 1)
            sonuc[ed][oran] = kayit
        k = kiyas(posterler, ed)
        if k is not None:
            k.save(YOL / ed / f"KIYAS_{ed}.jpg", quality=88)
    (YOL / "EDISYON_SONUC.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    rapor(sonuc)
    if not a.yerel:
        rc("copy", str(YOL), DEST_E, "--exclude", "*/ham/**", "--exclude",
           "*/zemin/**", capture=False, timeout=900)
        log(f"ciktilar {DEST_E} altina yazildi")


def rapor(sonuc):
    m = ["# EDISYONLAR: Black, Pure White, Modern, Vintage", "",
         f"Kosu: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "",
         "## DEGISEN OGELER", "",
         "- **Zemin**: her edisyonun oran-ici sayfa render'i (Canva kopyasindan "
         "zemin disi ogeler silinerek). Tuval olcusu referans sayfayla ayni "
         "oldugu icin hizalama BIRIM; edisyona ozel hiza sabiti yok.",
         "- **Doku**: yazi profili edisyonun kendi sayfa 28'indeki CANCER/LIBRA "
         "isimlerinden cikarilir.",
         "- **Isim kapisi**: sekil Blue'nun oran ici onayli satiriyla renkten "
         f"bagimsiz (kayma <= {SEKIL_KAYMA} px, IoU >= {SEKIL_IOU}); doku "
         f"edisyonun kendi sayfa 28'i ile (fark <= {DOKU_FARK}).",
         "- **Girdi kapisi**: her kosuda tuval olcusu, zemin olcusu, sayfa adi "
         f"ve olculen bosluk (kilitli degerden <= {BOSLUK_PAY} px) dogrulanir.",
         "", "### Degismeyen", "",
         "- Blue'nun ONAYLI.json ogeleri, onayli isim satirlari, ORAN_SABITLERI "
         "hizalamalari, D kurali, kenar payi %10, punto/buyuk harf kurallari ve "
         "TUM kapi esikleri.", "",
         "## 1) Blok bazli kalinti kapisi", "",
         "| edisyon | oran | blok | en_ort (<=2) | en_tepe (<=6) | kotu | sonuc |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            if k.get("durum") != "URETILDI":
                m.append(f"| {ed} | {oran} | - | - | - | - | **{k['durum']}** |")
                continue
            for c in k["ciftler"]:
                g = c["blok_kapisi"]
                m.append(f"| {ed} | {oran} | {g['blok']} | {g['en_ort']} | "
                         f"{g['en_tepe']} | {g['kotu_blok']} | "
                         f"**{'GECTI' if g['gecti'] else 'KALDI'}** |")
    taban = sonuc.get("_blue_taban") or {}
    m += ["", "## 2) Isim kapisi (SERDAR - LENA)", "",
          "Olculen taban: Blue'nun KENDI posteri ayni IoU olcusunde "
          + ", ".join(f"{o} {v['iou']}/{v['iou_hizali']}"
                      for o, v in taban.items() if v) + " (hizasiz/hizali). "
          "Taban 1.0 ise esik ulasilabilirdir ve edisyondaki dusus gercek bir "
          "sekil farkidir (olculen cap -> punto sapmasi ya da edisyonun kendi "
          "isim bandinin dikey kaymasi).", "",
          "| edisyon | oran | kayma (<=1) | IoU (>=0.95) | ort RGB | std | profil | sonuc |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            ik = k.get("isim_kapisi")
            if not ik:
                m.append(f"| {ed} | {oran} | - | - | - | - | - | "
                         f"**{k.get('durum', '-')}** |")
                continue
            if "sekil" not in ik:
                m.append(f"| {ed} | {oran} | - | - | - | - | - | "
                         f"**KALDI ({ik.get('sebep')})** |")
                continue
            s_, d_ = ik["sekil"], ik["doku"]
            m.append(f"| {ed} | {oran} | {s_['kayma_px']} | {s_['iou']} | "
                     f"{d_['ort_rgb_fark']} | {d_['parlaklik_std_fark']} | "
                     f"{d_['profil_fark']} | "
                     f"**{'GECTI' if ik['gecti'] else 'KALDI'}** |")
    m += ["", "## 3) Uretim suresi (hedef: oran basina <= 30 sn)", "",
          "| edisyon | oran | kurulum (sn) | poster basina (sn) | toplam (sn) |",
          "| --- | --- | --- | --- | --- |"]
    for ed, oranlar in sonuc.items():
        if ed.startswith("_"):
            continue
        for oran, k in oranlar.items():
            if k.get("durum") == "URETILDI":
                m.append(f"| {ed} | {oran} | {k['kurulum_sn']} | "
                         f"{k['poster_sn']} | {k['toplam_sn']} |")
    m += ["", "## 4) Onay durumu", "",
          "Bu edisyon ciktilari **ONAY BEKLIYOR**. Serdar bir edisyonu "
          "onaylayana kadar uretimde kullanilmaz; onaylandiginda o edisyonun "
          "isim satiri `onayli/<edisyon>/ISIM_SATIRI_<oran>.png` olarak "
          "kilitlenecek.", "",
          "## 5) Gorsel kanit", "",
          "KIYAS_<edisyon>.jpg: bes oranin isim satiri bandi yan yana.",
          "IZ_KONTROL_<edisyon>_<oran>.jpg: 3x buyutme, 2.5x parlaklik.",
          "ALTIN_<oran>.jpg: SERDAR - LENA posteri.", ""]
    (YOL / "EDISYON_RAPOR.md").write_text("\n".join(m), encoding="utf-8")
    log("EDISYON_RAPOR.md yazildi")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", action="store_true")
    ap.add_argument("--edisyon", nargs="*", default=None)
    kos(ap.parse_args())


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
