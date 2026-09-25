#!/usr/bin/env python3
"""Duvar kagidi metin bantlarinin OLCUMU (tahmin yok).

Her dosyada: kucuk burc glifleri, isim satiri (SOL AD + sonsuzluk + SAG AD) ve
slogan ayni dikey sirada. Bant sinirlari yuzdeyle DEGIL, dosyanin kendi
murekkep profilinden olculur; yuzdeler yalniz arama penceresidir.
"""
import cv2
import numpy as np

# arama pencereleri (Serdar 25 Eyl 2026 notu; yalniz PENCERE, sinir olculur)
PENCERE = {
    "phone":   {"isim": (0.58, 0.71), "tag": (0.68, 0.80)},
    "tablet":  {"isim": (0.68, 0.81), "tag": (0.80, 0.93)},
    "desktop": {"isim": (0.68, 0.83), "tag": (0.80, 0.94)},
}
GOVDE_ORAN = 0.25      # govde satiri: murekkep >= medyan satirin %25'i (a1_poster kurali)
KUME_BOSLUK = 0.012    # sutun kumelerini ayiran en kucuk bosluk (tuval genisligine gore)


def luma(a):
    return a.astype(np.float32) @ np.float32([0.299, 0.587, 0.114])


def murekkep_maskesi(im):
    """Yuksek gecirgen fark + gurultu tabanindan turetilen esik.

    Altin yazi MB/DB'de zeminden ACIK, CI/WP'de KOYU; mutlak fark iki polariteyi
    de yakalar. Esik, gorselin kendi gurultusunden (MAD) turetilir.
    """
    g = luma(np.asarray(im.convert("RGB")))
    bg = cv2.GaussianBlur(g, (0, 0), 15)
    hp = g - bg
    mad = np.median(np.abs(hp - np.median(hp))) * 1.4826
    esik = max(6.0 * mad, 6.0)
    m = (np.abs(hp) > esik).astype(np.uint8)
    # Doku gurultusu (parsomen / fildisi kagit) kucuk bilesenler uretir; harf ve
    # glif cizgileri buyuk bilesenlerdir. Esik gorselin KENDI olcusunden turetilir.
    en_az = max(20, int((0.004 * g.shape[1]) ** 2))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    tut = np.zeros(n, bool)
    tut[1:] = st[1:, cv2.CC_STAT_AREA] >= en_az
    return tut[lab], hp, float(mad), float(esik)


def bantlar(mask, en_az=3, en_ince=8):
    """Satir profilinden kesintisiz murekkep bantlari."""
    sat = mask.sum(1)
    out, i, n = [], 0, len(sat)
    while i < n:
        if sat[i] >= en_az:
            j = i
            while j < n and sat[j] >= en_az:
                j += 1
            if j - i >= en_ince:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def kumeler(mask, bosluk):
    """Sutun profilinden, en az `bosluk` px ara ile ayrilan kumeler."""
    sut = mask.sum(0) > 0
    out, i, n = [], 0, len(sut)
    while i < n:
        if sut[i]:
            j = i
            son = i
            while j < n:
                if sut[j]:
                    son = j
                    j += 1
                elif j - son <= bosluk:
                    j += 1
                else:
                    break
            out.append((i, son + 1))
            i = j
        else:
            i += 1
    return out


def govde_bandi(mask, b0, b1, kutular):
    """Inen kuyruklar (J, Q, y) haric en uzun kesintisiz govde kosusu."""
    sat = np.zeros(b1 - b0)
    for (x0, x1) in kutular:
        sat += mask[b0:b1, x0:x1].sum(1)
    pos = sat[sat > 0]
    if len(pos) == 0:
        return b0, b1
    ok = sat >= GOVDE_ORAN * np.median(pos)
    en, kos, i = 0, (0, len(ok)), 0
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
    return b0 + kos[0], b0 + kos[1]


def olc(im, cihaz):
    """Dosyanin kendi olcumu: glif bandi, isim bandi (sol/sonsuz/sag), slogan bandi."""
    W, H = im.size
    m, hp, mad, esik = murekkep_maskesi(im)
    p = PENCERE[cihaz]
    bl = bantlar(m)
    if not bl:
        raise RuntimeError("murekkep bandi bulunamadi")

    def pencerede(ad):
        y0, y1 = int(p[ad][0] * H), int(p[ad][1] * H)
        ic = [b for b in bl if b[0] >= y0 - 1 and b[1] <= y1 + 1]
        if not ic:
            raise RuntimeError(f"{ad} bandi pencerede yok ({y0}-{y1})")
        return max(ic, key=lambda b: m[b[0]:b[1]].sum())

    ib = pencerede("isim")
    tb = pencerede("tag")
    if tb[0] <= ib[0]:
        raise RuntimeError("slogan bandi isim bandinin ustunde")
    # glif bandi: isim bandinin hemen ustundeki bant; ayni sembolun PARCALI
    # bantlari (orn. Kova'nin iki dalgasi) x araligi ortusuyorsa birlestirilir.
    ust = sorted([b for b in bl if b[1] <= ib[0]], key=lambda b: -b[1])
    gb = list(ust[0]) if ust else None
    if gb:
        bosluk_px = int(KUME_BOSLUK * W)
        birles = max(20, int(0.013 * H))
        k0 = [k for k in kumeler(m[gb[0]:gb[1]], bosluk_px) if k[1] - k[0] > 0.01 * W]
        for b in ust[1:]:
            if gb[0] - b[1] > birles:
                break
            k = [c for c in kumeler(m[b[0]:b[1]], bosluk_px) if c[1] - c[0] > 0.01 * W]
            if len(k) == len(k0) and all(
                    min(k[i][1], k0[i][1]) - max(k[i][0], k0[i][0]) > 0.4 * (k0[i][1] - k0[i][0])
                    for i in range(len(k0))):
                gb[0] = b[0]
                k0 = [(min(k[i][0], k0[i][0]), max(k[i][1], k0[i][1])) for i in range(len(k0))]
        gb = tuple(gb)

    bosluk = int(KUME_BOSLUK * W)
    isim_k = [k for k in kumeler(m[ib[0]:ib[1]], bosluk) if k[1] - k[0] > 0.01 * W]
    if len(isim_k) > 3:
        # Tuval kenarindaki doku lekeleri ayri kume uretebilir (WP/DB masaustu
        # olcumu): murekkep kutlesi en buyuk 3 kume satirin kendisidir.
        isim_k = sorted(sorted(isim_k, key=lambda k: -m[ib[0]:ib[1], k[0]:k[1]].sum())[:3])
    if len(isim_k) != 3:
        raise RuntimeError(f"isim satirinda 3 kume bekleniyordu, {len(isim_k)} bulundu: {isim_k}")
    sol, inf, sag = isim_k
    g0, g1 = govde_bandi(m, ib[0], ib[1], [sol, sag])

    def murekkep_merkezi(x0, x1):
        sut = m[ib[0]:ib[1], x0:x1].sum(0).astype(np.float32)
        return x0 + float((sut * np.arange(x1 - x0)).sum() / max(sut.sum(), 1))

    tag_k = [k for k in kumeler(m[tb[0]:tb[1]], bosluk) if k[1] - k[0] > 2]
    tag_kutu = (min(k[0] for k in tag_k), min(tb), max(k[1] for k in tag_k), max(tb))
    tg0, tg1 = govde_bandi(m, tb[0], tb[1], [(tag_kutu[0], tag_kutu[2])])

    glif = None
    if gb:
        gk = [k for k in kumeler(m[gb[0]:gb[1]], bosluk) if k[1] - k[0] > 0.01 * W]
        glif = {"bant": [int(gb[0]), int(gb[1])], "kutular": [[int(a), int(b)] for a, b in gk]}

    return {
        "tuval": [W, H], "mad": round(mad, 2), "esik": round(esik, 2),
        "isim_bant": [int(ib[0]), int(ib[1])],
        "isim_govde": [int(g0), int(g1)],
        "sol": [int(sol[0]), int(sol[1])], "sag": [int(sag[0]), int(sag[1])],
        "sonsuz": [int(inf[0]), int(inf[1])],
        "merkez": {"sol": round(murekkep_merkezi(*sol), 1), "sag": round(murekkep_merkezi(*sag), 1)},
        "cap": int(g1 - g0),
        "tag_bant": [int(tb[0]), int(tb[1])],
        "tag_kutu": [int(v) for v in tag_kutu],
        "tag_cap": int(tg1 - tg0), "tag_govde": [int(tg0), int(tg1)],
        "satir_kutu": [int(sol[0]), int(ib[0]), int(sag[1]), int(ib[1])],
        "glif": glif,
        "sanat_kenar": int(min(int(np.nonzero(m[:gb[0]].any(0))[0].min()),
                               W - int(np.nonzero(m[:gb[0]].any(0))[0].max()) - 1)) if gb else None,
    }, m, hp


def yazi_maskesi(hp, kutu, oran=0.35):
    """Verilen kutuda KATI yazi maskesi: yuksek gecirgen farkin baskin
    polaritesinde, bolgenin kendi tepe degerinin `oran` katini asan pikseller.
    (Kenar maskesi degil; altin dokusu bu maskeden olculur.)"""
    x0, y0, x1, y1 = kutu
    b = hp[y0:y1, x0:x1]
    art = float(b[b > 0].sum()) if (b > 0).any() else 0.0
    eks = float(-b[b < 0].sum()) if (b < 0).any() else 0.0
    yon = 1.0 if art >= eks else -1.0
    s = yon * b
    tepe = float(np.percentile(s, 99.5))
    m = np.zeros(hp.shape, bool)
    m[y0:y1, x0:x1] = s > max(oran * tepe, 3.0)
    return m, yon
