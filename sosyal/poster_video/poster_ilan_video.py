#!/usr/bin/env python3
"""Poster ilan videosu ORNEK (19 Eki 2026). Kupa ilan videosu mantigi (kupa-orchard dali kupa_orchard/kod/video6b.py, Serdar
18.10): sahne SABIT, 6 sn, 30 fps, sessiz H.264; ilk kare ve son kare = onayli kapak (birebir); 2. kareden toz baslar, ilk
0,3 sn icinde kapaktaki birlesik sembol yumusakca kaybolur; toz iki kucuk burc glifinden akar, sembol ilk varislarla
sifirdan yumusakca olusur, BITIS (5,0 sn) aninda tam; sonra kapak sabit. Zamanlama, toz sayisi (5200), gecikme, yay ve
parlaklik kupa koduyla ayni. Fark: mesaj yazilmaz (baslik, duvar, glifler, isimler, mesaj sabit); toz rengi posterin altini.
Kapak 4:3 (3000x2250) -> video 1440x1080.

Poster kapakta lacivert dikdortgen olarak bulunur; sembol ve glif maskeleri dogrudan kapaktaki posterden (PosterR: altin alfa,
birlesik sembol parcalari, kucuk burclar) cikar (kapak uretim kodu depoda yok). Sembolsuz hal: kupadaki gibi
BOS = KAPAK + (sembolsuz poster - poster) farki; sembolsuz poster = lib.Poster.bg (klasik Telea inpaint, yapay zeka yok).
Poster pikselleri yalniz olceklenir/tasinir; ilk ve son karede kapak oldugu gibi.

QC (ayni betik, kodlanmis videodan): sure, olcu, ses akisi yok, dosya MB; ilk ve son kare ile kapak arasindaki ortalama
mutlak fark (kapagin kayipsiz 4:2:0 kodlamasindaki fark + 0.2'den kucuk); sembol kutusunda kapakla farkin kalici olarak son karenin (kapak) kodlama tabanina + 0.5 indigi ilk kare
(sembol tam; crf 12, 4:2:0 kaybi taban olarak olculur); sembol sondugu anda kutudaki altin
artigi (cevre laciverde +-15), kapakta sembol ve gliflerde altinlik >= 40, poster orani 1.20-1.35. KONTAK.jpg: 0/1/2/3/4/5 sn
+ son kare; MASKE.jpg: sembol (kirmizi) ve glif (yesil) maskeleri kapak uzerinde.
v2 (--v2, Serdar 19 Eki): toz 5 kat (5200 -> 26000); toz iki glif + isimlerin arasindaki sonsuzluk isaretinden cikar; sembol
tozla birlikte olusur: her sembol pikselinin varis zamani = oraya inen ilk parcacigin zamani (inmeyen piksel en yakin
varistan), piksel varistan sonra FADE (0.06 = ~0.3 sn) icinde kapak rengine gelir, varis olmadan gorunmez; parcacik indigi
pikselde FADE boyunca durur, sonra sembole karisir. Kontak 0-6 sn her 0,5 sn; cikti <ad>_ilan_video_v2.mp4, QC.json.
Poster oran kapisi 1.20-1.35 (kapaktaki poster ~4:5; 1. ornekte 1.273 olculdu).
v3 (--v3, Serdar 19 Eki; v2'nin tum kurallari + iki duzeltme): (1) sembol tozla ayni hizda ~2,5 sn'de duzgun olusur: her sembol
pikseline kaynaklara (iki glif + sonsuzluk) uzakligina gore (yumusak gurultulu) sira verilir, sira 2,2-4,7 sn araligina esit
dagitilir (gorunen oran dogrusal artar); her parcacik hedef pikselin zamaninda iner (kalkis da ayni araliga yayilir); piksel
varistan sonra 0,25 sn'de tam renk. (2) zarif toz: boy cesitli (%88 cok kucuk, %12 biraz buyuk), renk karisimi (sembolun altin
tonlari %50, acik sampanya %30, parlak vurgu %20), yari saydam, yumusak parilti ve titresim (2,5-6 Hz), yollar genis yayili.
Kullanim: python3 -I poster_ilan_video.py <kapak.jpg> <cikti_dizini> <ad> [--v2 | --v3]"""
import json, os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import pin_uret as PU

KAPAK, OUT, AD = sys.argv[1:4]
V3 = '--v3' in sys.argv[4:]
V2 = '--v2' in sys.argv[4:] or V3                                     # v3, v2'nin kurallarini (toz 5 kat, sonsuzluk, genis inpaint) tasir
VW, VH, FPS, SURE, SILME, BITIS = 1440, 1080, 30, 6.0, 0.3, 5.0
N = 26000 if V2 else 5200                                             # v2: 5 kat (Serdar)
FADE = 0.06                                                           # v2: piksel varistan sonra tam renge (tt birimi)
V3_T0, V3_T1, V3_FADE_SN = 2.2, 4.7, 0.25                             # v3: sembol olusum araligi (sn) ve piksel gecisi
ESIK_IK = 0.2                     # ilk/son kare: kayipsiz 4:2:0 tabaninin en fazla 0.2 ustu
rng = np.random.default_rng(11)
t0 = time.time()
os.makedirs(OUT, exist_ok=True)
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))
R = {}

# ---------- kapak ve poster
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
R['kapak_olcu'] = f'{kap_src.shape[1]}x{kap_src.shape[0]}'
KAP8 = cv2.resize(kap_src, (VW, VH), interpolation=cv2.INTER_AREA)
KAP = KAP8.astype(np.float32)

# ---------- poster kapakta: koyu dikdortgen (duvar acik bej). 1. kosuda (39291450782)
# kaynak poster -> kapak SIFT eslesmesi yanlis oturdu (61 ic nokta, sembol maskesinde altinlik -1.1): parca ayrimi artik
# dogrudan kapaktaki poster uzerinde (PosterR), eslesme yok.
kf = kap_src.astype(np.float32); lum_ = kf @ np.float32([0.299, 0.587, 0.114])
lac = (lum_ < 90).astype(np.uint8)      # koyu bolge (posterin alt kenari neredeyse siyah, B > R sarti orada tutmaz)
lac = cv2.morphologyEx(lac, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(lac, 8)
bi = 1 + int(np.argmax(st_[1:, 4]))
x0, y0, cw, ch = (int(v) for v in st_[bi, :4]); x1, y1 = x0 + cw, y0 + ch
R['poster_kutu_kapak'] = [x0, y0, cw, ch]; R['poster_oran'] = round(ch / cw, 3)
s_ = 2000 / cw
tmp = os.path.join(OUT, '_poster_kapaktan.png')
Image.fromarray(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC)).save(tmp)
P = PU.PosterR(tmp); os.remove(tmp)


def vid(m):
    """poster (2000 px genislik) uzayindaki katman -> kapak -> video (1440x1080)."""
    c = np.zeros(kap_src.shape[:2] + m.shape[2:], np.float32)
    c[y0:y1, x0:x1] = cv2.resize(m.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA)
    return cv2.resize(c, (VW, VH), interpolation=cv2.INTER_AREA)


# ---------- maskeler (poster uzayi) -> video
ids = [c[0] for c in P.merged_parts]
msym = np.isin(P.lab, ids).astype(np.uint8)
if V2:   # v2: sembol + golgesi (31 px), yumusak kenar; v1'de 9 px bolgede golge izi kaliyordu (v2 yerel deneme, 0,5 sn)
    msym_g = cv2.GaussianBlur(cv2.dilate(msym, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 5.0)
else:
    msym_g = cv2.dilate(msym, np.ones((9, 9), np.uint8)).astype(np.float32)
    msym_g = cv2.GaussianBlur(msym_g, (0, 0), 2.0)                    # sembol bolgesi (yumusak kenar)
MS_p = np.clip(P.alpha * cv2.dilate(msym, np.ones((7, 7), np.uint8)), 0, 1)   # sembolun altin alfasi
MG_p = np.zeros_like(P.alpha)
for s2 in (P.sign_a, P.sign_b):
    _, x, y, w, h, _ = s2
    MG_p[y:y + h, x:x + w] = P.alpha[y:y + h, x:x + w]
if V2:                                                                # isimler satirindaki sonsuzluk isareti (ortadaki parca)
    _, nx, ny, nw, nh, _ = P.names_row
    sonsuz = [c for c in P.comps if nx <= c[1] + c[3] / 2 <= nx + nw and ny <= c[2] + c[4] / 2 <= ny + nh
              and abs(c[1] + c[3] / 2 - P.w / 2) < 0.08 * P.w]
    for c in sonsuz:
        m_ = cv2.dilate((P.lab == c[0]).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        MG_p[m_] = np.maximum(MG_p[m_], P.alpha[m_])
    R['sonsuz_parca'] = len(sonsuz)
if V2:   # sembolsuz poster: genis bolge kapaktaki posterin kendi pikselleriyle klasik Telea inpaint (yarim olcek), yapay zeka yok
    hm = cv2.resize((msym_g > 0.02).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_NEAREST)
    hi = cv2.resize(np.clip(P.img, 0, 255).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_AREA)
    bos = cv2.resize(cv2.inpaint(hi, cv2.dilate(hm, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32),
                     (P.w, P.h), interpolation=cv2.INTER_CUBIC)
    D_p = (bos - P.img) * msym_g[..., None]
else:
    D_p = (P.bg - P.img) * msym_g[..., None]                          # sembolsuz - tam (yalniz sembol bolgesinde)
MS, MG, DIFF, MREG = vid(MS_p), vid(MG_p), vid(D_p), vid(msym_g)
PK = vid(np.ones_like(P.alpha)) > 0.99                                # poster alani (video)
FULL = KAP
BASE = np.clip(KAP + DIFF, 0, 255)
ys, xs = np.where(MREG > 0.05)
SK = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))   # sembol kutusu (video px)
R['sembol_kutu'] = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)]
rb = lambda im, m=None: float((im[..., 0] - im[..., 2])[(MS > 0.5) if m is None else m].mean())   # altinlik (R - B)
cevre = (MREG < 0.01) & PK & (cv2.dilate((MREG > 0.05).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0)
R['sembol_altinlik'] = {'kapak': round(rb(KAP), 1), 'sembolsuz': round(rb(BASE), 1), 'cevre_lacivert': round(rb(KAP, cevre), 1),
                        'glif_kapak': round(rb(KAP, MG > 0.5), 1)}
dbg = KAP.copy(); dbg[MS > 0.5] = dbg[MS > 0.5] * 0.3 + np.float32([255, 0, 0]) * 0.7
dbg[MG > 0.5] = dbg[MG > 0.5] * 0.3 + np.float32([0, 255, 0]) * 0.7
Image.fromarray(np.clip(dbg, 0, 255).astype(np.uint8)).resize((720, 540), Image.LANCZOS).save(os.path.join(OUT, 'MASKE.jpg'), quality=88)

# ---------- toz (kupa video6b ile ayni davranis)


def noktalar(m, n):
    ys_, xs_ = np.where(m > 0.35)
    i = rng.choice(len(xs_), n, replace=True)
    return np.stack([xs_[i], ys_[i]], 1).astype(np.float32) + rng.random((n, 2)).astype(np.float32) - 0.5


src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
yay = -(8 + 16 * rng.random(N).astype(np.float32))
gold = P.ramp.astype(np.float32)                                      # posterin altin rampasi (karanliktan parlaga)
renk = np.where((rng.random(N) < 0.22)[:, None], gold[235], gold[rng.integers(120, 220, N)])
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)
nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
R['toz_parcacik'] = {'v1': 5200, 'bu_ornek': N}
TARR = gec + 0.38                                                     # parcacigin sembole indigi an (uu = 1), tt birimi
DUR = 0.38
SNT = (nB - 1) / FPS                                                  # tt = 1 anindaki saniye (4,967)
if V3:   # piksel zaman haritasi: kaynaklara uzaklik + yumusak gurultu -> sira -> 2,2-4,7 sn esit dagilim
    from scipy.ndimage import distance_transform_edt
    FADE = V3_FADE_SN / SNT
    n_, lab_g, _, cen = cv2.connectedComponentsWithStats((MG > 0.35).astype(np.uint8), 8)
    kay = [cen[k] for k in range(1, n_) if (lab_g == k).sum() > 20]  # glif ve sonsuzluk parcalarinin merkezleri
    yy_, xx_ = np.mgrid[0:VH, 0:VW].astype(np.float32)
    uz = np.min([np.hypot(xx_ - cx, yy_ - cy) for cx, cy in kay], axis=0)
    gz = cv2.GaussianBlur(np.random.default_rng(7).random((VH, VW)).astype(np.float32), (0, 0), 10)
    gz = (gz - gz.mean()) / (gz.std() + 1e-6)
    sm = MS > 0.5
    anah = uz + gz * 0.08 * (uz[sm].max() - uz[sm].min())
    sira = np.empty(int(sm.sum()), np.float32); sira[np.argsort(anah[sm])] = np.arange(int(sm.sum()), dtype=np.float32)
    VAR = np.full((VH, VW), np.inf, np.float32)
    VAR[sm] = (V3_T0 + (V3_T1 - V3_T0) * sira / max(1, sm.sum() - 1)) / SNT
    ii = distance_transform_edt(~sm, return_indices=True)[1]
    VAR = VAR[ii[0], ii[1]]                                           # sembol disi bolge (kenar, golge): en yakin sembol pikseli
    R['v3'] = {'kaynak_sayisi': len(kay), 'olusum_sn': [V3_T0, V3_T1], 'piksel_gecis_sn': V3_FADE_SN}
    dx = np.clip(np.round(dst[:, 0]).astype(int), 0, VW - 1); dy = np.clip(np.round(dst[:, 1]).astype(int), 0, VH - 1)
    TARR = VAR[dy, dx]                                                # parcacik hedef pikselin zamaninda iner
    DUR = (0.38 * (0.75 + 0.5 * rng.random(N))).astype(np.float32)   # ucus 1,4-2,4 sn: ayni bolgeye farkli anlarda kalkis
    gec = TARR - DUR                                                  # kalkis: ayni araliga yayilir
    big = rng.random(N) < 0.12                                        # boy: %88 cok kucuk, %12 biraz buyuk
    tip = rng.random(N)
    sampanya = np.float32([246, 228, 190]) + rng.normal(0, 6, (N, 3)).astype(np.float32)
    vurgu = np.float32([255, 248, 226]) + rng.normal(0, 4, (N, 3)).astype(np.float32)
    renk = np.where((tip < 0.5)[:, None], gold[rng.integers(100, 226, N)], np.where((tip < 0.8)[:, None], sampanya, vurgu))
    renk = np.clip(renk, 0, 255).astype(np.float32)
    par = np.where(big, 0.28 + 0.22 * rng.random(N), 0.15 + 0.25 * rng.random(N)).astype(np.float32)   # yari saydam
    ftr, fph = (2.5 + 3.5 * rng.random(N)).astype(np.float32), (2 * np.pi * rng.random(N)).astype(np.float32)
    yay = -(10 + 30 * rng.random(N).astype(np.float32))               # yollar daha genis yayili (topak yok)
    yan = ((rng.random(N) - 0.5) * 14).astype(np.float32)
elif V2:                                                              # piksel basina varis haritasi
    from scipy.ndimage import distance_transform_edt
    VAR = np.full((VH, VW), np.inf, np.float32)
    dx = np.clip(np.round(dst[:, 0]).astype(int), 0, VW - 1); dy = np.clip(np.round(dst[:, 1]).astype(int), 0, VH - 1)
    np.minimum.at(VAR, (dy, dx), TARR)
    yok_ = ~np.isfinite(VAR)
    R['varis_dogrudan_piksel_orani'] = round(float((~yok_ & (MS > 0.5)).sum() / max(1, (MS > 0.5).sum())), 3)
    ii = distance_transform_edt(yok_, return_indices=True)[1]
    VAR = cv2.GaussianBlur(VAR[ii[0], ii[1]], (0, 0), 1.0)
    VAR = np.minimum(VAR, 1 - FADE)                                   # BITIS'te her piksel tam


def a_harita(tt):
    if V2:
        return np.clip((tt - VAR) / FADE, 0, 1) ** 1.0 * np.clip(MREG, 0, 1)
    return ease((tt - 0.36) / 0.64) * np.clip(MREG, 0, 1)


TOZ_IST = {}


def toz_v3(f, p, gor, ag):
    """v3 zarif toz: kucuk ve buyuk parcaciklar ayri bulaniklikla, yari saydam, yumusak parilti eklenir."""
    xi, yi = p[:, 0].astype(int), p[:, 1].astype(int)
    ok = gor & (xi >= 0) & (xi < VW) & (yi >= 0) & (yi < VH) & (ag > 0)
    al_t = np.zeros((VH, VW), np.float32); kat_t = np.zeros((VH, VW, 3), np.float32)
    for m_, sg, kz in ((ok & ~big, 0.55, 1.0), (ok & big, 1.3, 2.4)):
        al = np.zeros((VH, VW), np.float32); kat = np.zeros((VH, VW, 3), np.float32)
        np.add.at(al, (yi[m_], xi[m_]), ag[m_])
        for c in range(3):
            np.add.at(kat[..., c], (yi[m_], xi[m_]), renk[m_, c] * ag[m_])
        al_t += cv2.GaussianBlur(al, (0, 0), sg) * kz; kat_t += cv2.GaussianBlur(kat, (0, 0), sg) * kz
    rk = kat_t / np.maximum(al_t[..., None], 1e-4)
    a3 = np.clip(al_t, 0, 0.75)[..., None]
    g = f * (1 - a3) + rk * a3
    pa = cv2.GaussianBlur(kat_t, (0, 0), 3.5) * 0.35                  # yumusak parilti (eklenir)
    TOZ_IST.setdefault('ucan', []).append(int(ok.sum())); TOZ_IST.setdefault('doygun', []).append(
        float((al_t > 0.75).sum() / max(1, (al_t > 0.05).sum())))
    return np.clip(g + pa, 0, 255).astype(np.uint8)


def kare(i):
    if i == 0 or i >= nB:
        return KAP8
    tt = i / (nB - 1)
    uu = np.clip((tt - gec) / DUR, 0, 1)
    # v1: ilk varislarla sifirdan, tum alan birlikte; v2: piksel varis haritasiyla. BITIS'te tam (kenar artigi yok)
    A = a_harita(tt)[..., None]
    f = BASE * (1 - A) + FULL * A
    if i <= nS:                                                        # ilk 0,3 sn: kapaktaki sembol yumusakca kaybolur
        e = ease(i / nS)
        f = KAP * (1 - e) + f * e
    ue = uu * uu * (3 - 2 * uu)
    if V3:   # yari dogrusal: hedefe yaklasirken yavaslayip yigilma (topak) olmaz
        ue = 0.55 * uu + 0.45 * ue
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
    if V3:
        p[:, 0] += yan * np.sin(np.pi * ue)
        gor = (uu > 0) & (tt < TARR + FADE)
        ag = par * np.minimum(1, uu / 0.15) * np.where(tt > TARR, 0.6 * (1 - np.clip((tt - TARR) / FADE, 0, 1)), 1.0) \
            * (0.7 + 0.3 * np.sin(2 * np.pi * ftr * (i / FPS) + fph))  # titresim
        return toz_v3(f, p, gor, ag)
    if V2:   # ucusta belirir, indigi pikselde FADE boyunca durur, piksel tam renge gelirken soner
        gor = (uu > 0) & (tt < TARR + FADE)
        ag = par * np.minimum(1, uu / 0.15) * (1 - np.clip((tt - TARR) / FADE, 0, 1))
    else:
        gor = (uu > 0) & (uu < 1)
        ag = par * np.sin(np.pi * uu)
    xi, yi = p[gor, 0].astype(int), p[gor, 1].astype(int)
    ok = (xi >= 0) & (xi < VW) & (yi >= 0) & (yi < VH)
    a_ = ag[gor][ok]
    al = np.zeros((VH, VW), np.float32); kat = np.zeros((VH, VW, 3), np.float32)
    np.add.at(al, (yi[ok], xi[ok]), a_)
    for c in range(3):
        np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
    al = cv2.GaussianBlur(al, (0, 0), 0.9) * 2.0
    kat = cv2.GaussianBlur(kat, (0, 0), 0.9) * 2.0
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None]
    return np.clip(f * (1 - a3) + rk * a3, 0, 255).astype(np.uint8)


mp4 = os.path.join(OUT, f'{AD}_ilan_video{"_v3" if V3 else "_v2" if V2 else ""}.mp4')
enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                        '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '12',
                        '-preset', 'slow', '-movflags', '+faststart', mp4], stdin=subprocess.PIPE)
for i in range(nT):
    enc.stdin.write(kare(i).tobytes())
    if i % 30 == 0 or i == nT - 1:
        g = time.time() - t0
        print(f'kare {i + 1}/{nT} %{100 * (i + 1) // nT} gecen {g:.0f} sn kalan ~{g / (i + 1) * (nT - i - 1):.0f} sn', flush=True)
enc.stdin.close(); enc.wait()

# ---------- QC (kodlanmis videodan)
j = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', mp4],
                              capture_output=True, text=True, check=True).stdout)
vs = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
R['video'] = {'olcu': f"{vs['width']}x{vs['height']}", 'oran': round(vs['width'] / vs['height'], 4), 'kare': int(vs['nb_read_frames']),
              'sure_sn': round(float(j['format']['duration']), 3), 'fps': vs['r_frame_rate'], 'codec': vs['codec_name'],
              'ses_akisi': any(s['codec_type'] == 'audio' for s in j['streams']),
              'boyut_mb': round(os.path.getsize(mp4) / 1e6, 2)}
dec = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
FR = np.frombuffer(dec, np.uint8).reshape(-1, VH, VW, 3)
fark = lambda a_, b_: round(float(np.abs(a_.astype(np.float32) - b_.astype(np.float32)).mean()), 3)
R['ilk_kare_fark'] = fark(FR[0], KAP8); R['son_kare_fark'] = fark(FR[-1], KAP8)
tb = os.path.join(OUT, '_taban.mp4')                                   # 4:2:0 donusum tabani: kapak, kayipsiz (crf 0) kodlama
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}', '-r', str(FPS), '-i', '-',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '0', tb], input=KAP8.tobytes(), check=True)
tf = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', tb, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                                  capture_output=True, check=True).stdout, np.uint8).reshape(VH, VW, 3)
R['taban_420_kayipsiz'] = fark(tf, KAP8); os.remove(tb)
sk = [fark(f[SK], KAP8[SK]) for f in FR]
taban = sk[-1]                                                        # son kare = kapak: kutudaki kodlama kaybi tabani
tam = next((i for i in range(1, len(FR)) if all(x <= taban + 0.5 for x in sk[i:])), None)
R['sembol_kutu_taban'] = taban
R['sembol_tam_kare'] = tam; R['sembol_tam_sn'] = round(tam / FPS, 3) if tam is not None else None
R['sembol_kutu_fark_en_buyuk'] = {'kare': int(np.argmax(sk)), 'fark': max(sk)}
R['sembol_altinlik']['sondugu_an_video'] = round(rb(FR[nS].astype(np.float32)), 1)
mb = MREG > 0.5
R['sondugu_an_sembolsuz_fark'] = round(float(np.abs(FR[nS].astype(np.float32) - BASE)[mb].mean()), 3)   # 0,3 sn: iz yok
R['kapak_sembolsuz_fark'] = round(float(np.abs(KAP - BASE)[mb].mean()), 3)                             # olcek icin


def ince(im):   # ince ayrinti (gri - gauss sigma 6), mutlak
    g = im.astype(np.float32) @ np.float32([0.299, 0.587, 0.114]); return np.abs(g - cv2.GaussianBlur(g, (0, 0), 6))


bol = MREG > 0.3
hal = (cv2.dilate(bol.astype(np.uint8), np.ones((41, 41), np.uint8)) > 0) & ~(MREG > 0.02) & PK
ia = ince(FR[nS]); R['iz_orani_0_3sn'] = round(float(ia[bol].mean() / max(1e-6, ia[hal].mean())), 3)   # ~1: iz yok
ik = ince(KAP8); R['iz_orani_kapak'] = round(float(ik[bol].mean() / max(1e-6, ik[hal].mean())), 3)       # olcek: sembol var
cizim = {}
for sn in (2, 2.5, 3, 3.5, 4, 4.5):                                   # sembol piksellerinde gorunurluk (ic harita)
    a_ = a_harita(int(sn * FPS) / (nB - 1))[MS > 0.5]
    cizim[str(sn)] = {'tam': round(float((a_ > 0.95).mean()), 3), 'yok': round(float((a_ < 0.05).mean()), 3),
                      'kismi': round(float(((a_ >= 0.05) & (a_ <= 0.95)).mean()), 3)}
R['sembol_cizim_orani'] = cizim
kapi = {'olcu_4_3': R['video']['olcu'] == f'{VW}x{VH}', 'kare_180': R['video']['kare'] == nT,
        'sure_6': abs(R['video']['sure_sn'] - SURE) < 0.05, 'ses_yok': not R['video']['ses_akisi'],
        'ilk_kare_kapak': R['ilk_kare_fark'] <= R['taban_420_kayipsiz'] + ESIK_IK,
        'son_kare_kapak': R['son_kare_fark'] <= R['taban_420_kayipsiz'] + ESIK_IK,
        'sembol_tam_bitiste': tam is not None and tam <= nB,
        'poster_oran_1_20_1_35': 1.20 <= R['poster_oran'] <= 1.35, 'sembol_altin': R['sembol_altinlik']['kapak'] >= 40,
        'glif_altin': R['sembol_altinlik']['glif_kapak'] >= 40,
        'sembol_soner': abs(R['sembol_altinlik']['sondugu_an_video'] - R['sembol_altinlik']['cevre_lacivert']) <= 15}
if V2:
    kapi['sonsuz_bulundu'] = R.get('sonsuz_parca', 0) >= 1
    kapi['iz_yok_0_3sn'] = R['iz_orani_0_3sn'] <= 1.3                        # bolge ici ince ayrinti cevre halkadan en fazla %30 fazla
    kapi['parca_parca_3sn'] = cizim['3']['tam'] > 0.05 and cizim['3']['yok'] > 0.05   # 3. sn: kismen cizili (v1: tumu kismi)
if V3:   # 0,5 sn tablosu: ic harita (sembol pikselleri, A > 0.5) ve videodan (altinlik kapak/sembolsuz arasinin yarisini gecti)
    rbk, rbb = KAP[..., 0] - KAP[..., 2], BASE[..., 0] - BASE[..., 2]
    vm = (MS > 0.5) & (rbk - rbb > 40)
    tab = {}
    for k in range(13):
        i_ = min(len(FR) - 1, k * 15)
        ic_ = float((a_harita(i_ / (nB - 1)) [MS > 0.5] > 0.5).mean()) if 0 < i_ < nB else (1.0 if i_ == 0 or i_ >= nB else 0.0)
        if 0 < i_ <= nS:
            ic_ = None
        fr_ = FR[i_].astype(np.float32); vid_ = float(((fr_[..., 0] - fr_[..., 2] - rbb)[vm] > 0.5 * (rbk - rbb)[vm]).mean())
        tab[f'{k * 0.5:g}'] = {'ic_harita': None if ic_ is None else round(ic_, 3), 'video': round(vid_, 3)}
    R['gorunen_sembol_orani'] = tab
    sr = [tab[f'{k * 0.5:g}']['ic_harita'] for k in range(1, 11)]     # 0,5 - 5,0 sn (0,5 sn: sondu)
    sr = [0.0 if x is None else x for x in sr]
    R['en_buyuk_0_5sn_artis'] = round(max(b - a for a, b in zip(sr, sr[1:])), 3)
    u = np.array(TOZ_IST['ucan'][int(1.0 * FPS):int(4.5 * FPS)])
    R['toz_akis'] = {'ucan_parcacik_1_4_5sn_min': int(u.min()), 'max': int(u.max()), 'ort': int(u.mean()),
                     'doygun_piksel_orani_en_buyuk': round(max(TOZ_IST['doygun']), 3), 'doygun_ort': round(float(np.mean(TOZ_IST['doygun'])), 3)}
    kapi['artis_0_5sn_en_fazla_30'] = R['en_buyuk_0_5sn_artis'] <= 0.30
    x0_, x1_ = max(0, SK[1].start - 20), min(VW, SK[1].stop + 20); y0_, y1_ = max(0, SK[0].start - 20), min(VH, SK[0].stop + 20)
    Image.fromarray(FR[90][y0_:y1_, x0_:x1_]).resize(((x1_ - x0_) * 2, (y1_ - y0_) * 2), Image.LANCZOS).save(
        os.path.join(OUT, 'YAKIN_3sn_200.jpg'), quality=94)
R['kapi'] = kapi; R['sonuc'] = 'PASS' if all(kapi.values()) else 'FAIL'
json.dump(R, open(os.path.join(OUT, 'QC.json' if V2 else f'{AD}_QC.json'), 'w'), indent=1, default=str)

# ---------- KONTAK: 0 / 1 / 2 / 3 / 4 / 5 sn + son kare, 4:3
if V2:   # 0-6 sn her 0,5 sn (6,0 sn = son kare)
    tw, th, ust, sut = 384, 288, 36, 5
    sec = [(f'{k * 0.5:g} sn', min(len(FR) - 1, k * 15)) for k in range(13)]
else:
    tw, th, ust, sut = 480, 360, 40, 4
    sec = [('0 sn', 0), ('1 sn', 30), ('2 sn', 60), ('3 sn', 90), ('4 sn', 120), ('5 sn', 150), (f'son ({len(FR) - 1})', len(FR) - 1)]
sat = (len(sec) + sut - 1) // sut
K = Image.new('RGB', (sut * tw + (sut - 1) * 8, sat * (th + ust) + (sat - 1) * 8), (245, 245, 245)); dr = ImageDraw.Draw(K)
try:
    fo = ImageFont.truetype('DejaVuSans-Bold.ttf', 24)
except OSError:
    fo = ImageFont.load_default()
for n_, (et, i) in enumerate(sec):
    x, y = (n_ % sut) * (tw + 8), (n_ // sut) * (th + ust + 8)
    dr.text((x + 6, y + 6), et, fill=(0, 0, 0), font=fo)
    K.paste(Image.fromarray(FR[i]).resize((tw, th), Image.LANCZOS), (x, y + ust))
K.save(os.path.join(OUT, 'KONTAK.jpg'), quality=92)
print(json.dumps(R, ensure_ascii=False, default=str))
print('SONUC', R['sonuc'], f'{time.time() - t0:.0f} sn')
sys.exit(0 if R['sonuc'] == 'PASS' else 1)
