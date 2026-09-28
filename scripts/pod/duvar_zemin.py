#!/usr/bin/env python3
"""Galeri kartlari icin kapak duvari zemini + yazi kontrasti (Serdar 28 Eyl karari).
Onayli gorseller (01 kapak, 06/09/10/11 sahne) haric 14 gorselin zemini = kapagin duvari:
data/pod/kapak_sahne_v9.png kapakla ayni isleme: 1213x910'a LANCZOS -> 3000x2250 LANCZOS (kapak_v9_toplu + kapak_v8_kur).
Yazi kontrasti WCAG: >= 4.5:1, arkadaki duvarin en koyu %5'ine (koyu yazi icin en kotu durum) karsi olculur.
Saglanmazsa yazi rengi ayni tonda koyulastirilir (lacivert/kahve); duvar degismez.
"""
import numpy as np
from PIL import Image

KREM = (237, 232, 226)


LEKE = {'yok': 0.0, 'hafif': 0.35, 'orta': 0.60, 'guclu': 0.85}


VARSAYILAN = 'guclu'   # Serdar 28 Eyl: GUCLU (%56 leke azalmasi) onaylandi
VARSAYILAN_AYDINLIK = 'acik3'   # Serdar 28 Eyl: GUCLU + ACIK-3 (L* +15) nihai zemin
# Serdar 28 Eyl: GUCLU sonrasi daha acik/aydinlik secenekler: L* sabit artar (huzme-duvar farki ve doku aynen),
# ton acisi sabit, kroma hafif artar (soluk/gri olmaz). Deger: (L* artisi, kroma carpani)
AYDINLIK = {'acik1': (5.0, 1.00), 'acik2': (10.0, 1.04), 'acik3': (15.0, 1.08)}


def aydinlat(D, dL, kroma=1.0):
    """Duvari acar: Lab'de L* + dL (L* 85 ustunde 100'e yumusak tavan), a/b ayni oranla (ton acisi sabit).
    Artis sabit oldugu icin huzme-duvar farki, ince doku ve azaltilmis leke seviyesi degismez."""
    import cv2
    x = np.asarray(D).astype(np.float32) / 255
    L = cv2.cvtColor(x, cv2.COLOR_RGB2Lab)
    l = L[..., 0] + dL
    tavan = 85.0
    L[..., 0] = np.where(l > tavan, tavan + (100 - tavan) * np.tanh((l - tavan) / (100 - tavan)), l)
    L[..., 1:] *= kroma
    y = cv2.cvtColor(L, cv2.COLOR_Lab2RGB)
    return Image.fromarray(np.clip(np.rint(y * 255), 0, 255).astype(np.uint8))


def duvar(yol, seviye=VARSAYILAN, aydinlik=VARSAYILAN_AYDINLIK):
    """Kapak duvari 3000x2250; varsayilan nihai zemin GUCLU + ACIK-3. Kapaktaki ham duvar: duvar(yol, 'yok', None).
    yol zaten 3000x2250 ise (hazir duvar) aynen kullanilir."""
    im = Image.open(yol).convert('RGB')
    if im.size == (3000, 2250):
        return im
    D = leke_azalt(im.resize((1213, 910), Image.LANCZOS).resize((3000, 2250), Image.LANCZOS), LEKE[seviye])
    return aydinlat(D, *AYDINLIK[aydinlik]) if aydinlik else D


def _g(a, s):
    """Buyuk sigma Gauss: 1/4 olcekte bulanik, geri buyut (hizli; dusuk frekans icin kayipsiz sayilir)."""
    import cv2
    if s < 20:
        return cv2.GaussianBlur(a, (0, 0), s)
    h, w = a.shape[:2]
    k = cv2.resize(a, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.GaussianBlur(k, (0, 0), s / 4), (w, h), interpolation=cv2.INTER_LINEAR)


def leke_azalt(D, k):
    """Serdar 28 Eyl: duvar dokusundaki lekeler azalir; ton, parlaklik ve iki yandaki isik ayni kalir.
    Bantlar: aydinlatma (sigma 160 ustu) + leke (5-160 px) + ince doku (5 px alti). Yalniz leke bandi k oraninda
    zayiflar; isik huzmesi maskesinde (g80 - g400 > ~4..16) ve kenar vinyetinde (250 px) zayiflatma yok. k=0 ise aynen."""
    a = np.asarray(D).astype(np.float32)
    if k <= 0:
        return D
    leke = _g(a, 5) - _g(a, 160)
    hz = np.clip(((_g(a, 80) - _g(a, 400)).mean(2) - 4) / 12, 0, 1)
    hz = _g(hz, 60)
    # kenar vinyeti de aydinlatmadir: kenardan 250 px icinde zayiflatma yumusakca sifira iner (kose tonu korunur)
    h, w = hz.shape
    yy, xx = np.mgrid[0:h, 0:w]
    kenar = np.clip(np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)) / 250.0, 0, 1)
    kenar = kenar * kenar * (3 - 2 * kenar)
    koru = np.maximum(hz, 1 - kenar)
    b = a - k * (1 - koru)[..., None] * leke
    return Image.fromarray(np.clip(np.rint(b), 0, 255).astype(np.uint8))


if __name__ == '__main__':
    # Kullanim: duvar_zemin.py KAPAK_SAHNE_V9.png SEVIYE CIKIS.png [AYDINLIK]  (yok|hafif|orta|guclu; acik1|acik2|acik3)
    import sys
    duvar(sys.argv[1], sys.argv[2], (None if sys.argv[4] == 'yok' else sys.argv[4]) if len(sys.argv) > 4 else VARSAYILAN_AYDINLIK).save(sys.argv[3])


def _lin(c):
    c = np.asarray(c, np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lum(rgb):
    """WCAG goreli parlaklik; rgb (...,3)."""
    l = _lin(rgb)
    return l[..., 0] * 0.2126 + l[..., 1] * 0.7152 + l[..., 2] * 0.0722


def kontrast(l1, l2):
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def duvar_lum(D, kutu, yuzde=5):
    """Yazi kutusu (x0,y0,x1,y1) arkasindaki duvarin yuzdelik parlakligi (koyu yazi icin %5 = en kotu)."""
    x0, y0, x1, y1 = (int(v) for v in kutu)
    a = np.asarray(D)[max(y0, 0):y1, max(x0, 0):x1].reshape(-1, 3)
    return float(np.percentile(lum(a), yuzde))


def yazi_rengi(renk, lw, esik=4.5):
    """Koyu yazi rengini, duvar parlakligi lw'ye karsi kontrast >= esik olana dek ayni tonda koyulastirir."""
    k = 1.0
    r = tuple(int(v) for v in renk)
    while kontrast(float(lum(np.array(r))), lw) < esik and k > 0.05:
        k -= 0.02
        r = tuple(int(round(v * k)) for v in renk)
    return r
