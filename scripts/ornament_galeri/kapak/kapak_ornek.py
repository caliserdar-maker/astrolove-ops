#!/usr/bin/env python3
"""Ornament kapak YON ornegi (Merkez, 6 Kas 2026; GALERI_PLAN v2 adim 3; Etsy yok, toplu uretim yok).
Canva AI sahnesindeki bos beyaz diske ONAYLI baski dosyasini (954 PNG, sha SHA256SUMS ile esit) geometrik donusumle yerlestirir.
- Kesim dairesi: kaynak merkez (476,477) r 449 (gercek_boy_kontrol.py sabitleri) sahnedeki disk elipsine eslenir; r 449 disi atilir.
- Donusum: M = R S R^T (icerik donmez) + oteleme; S = elips yari eksenleri / 449.
- Golgelendirme: sahne parlakligi disk icinde, yumusatilmis, orana cevrilir ve sinirlanir (ALT, UST); yalniz disk maskesi icinde.
- Delik: sahnedeki delik tasarimin deligine (476,163 -> merkezden 0,699 R yukari) tasinir; ip ustten yeni delige uzatilir.
- Baslik: Cinzel (kupa kapagi kalibi): 1. satir "<A> & <B>" 650, 2. satir alt yazi; 4:5 orta bant (680-2320) icinde.
Kullanim: kapak_ornek.py SAHNE.png BASKI_954.png CIKTI.jpg --baslik "CANCER & LIBRA" --alt "PERSONALIZED ORNAMENT" --renk koyu|krem
Cikti yaninda <CIKTI>.json: olcumler, ileri kiyas kapisi (kaplama oncesi geometri 0 fark), kirpim kutulari."""
import argparse
import json
import math, os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 3000, 2250
KX, KY, KR = 476.0, 477.0, 449.0
DX, DY = 476.0, 163.0
ALT, UST = 0.86, 1.07
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "font", "Cinzel.ttf")
BANT = (800, 2200)          # Etsy kirpimlari: 1:1, 5:4, 4:5, 3:4, 2:3 orta kirpimlarinin kesisimi x 750-2250 (+50 pay)
ALT_GEN = 1600


def disk_bul(bgr):
    """Hough dairesi + kenar noktalarina elips (acik zeminde renk esigi yetmiyor)."""
    h, w = bgr.shape[:2]
    gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    k = 4
    kucuk = cv2.resize(gri, (w // k, h // k), interpolation=cv2.INTER_AREA)
    kucuk = cv2.GaussianBlur(kucuk, (0, 0), 2)
    c = None
    hepsi = os.environ.get("V_DISK_X") is not None                          # ipucu varsa tum esiklerin adaylari toplanir
    adaylar = []
    for p1, p2, cl in ((60, 30, False), (40, 22, True), (30, 18, True)):    # dusuk kontrastli acik zeminde yedek esikler (CLAHE)
        kk = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(kucuk) if cl else kucuk
        c = cv2.HoughCircles(kk, cv2.HOUGH_GRADIENT, dp=1, minDist=60 if hepsi else 200, param1=p1, param2=p2,
                             minRadius=int(0.08 * h / k), maxRadius=int(0.40 * h / k))
        if c is not None:
            adaylar.append(c[0][:8])
            if not hepsi:
                break
    if adaylar:
        c = np.concatenate(adaylar)[None]
    if c is None:
        raise SystemExit("DUR: disk bulunamadi (Hough)")
    # en parlak ic bolgeli daire
    en = None
    for (x, y, r) in (c[0] if os.environ.get('V_DISK_X') else c[0][:8]):
        yy, xx = np.ogrid[:kucuk.shape[0], :kucuk.shape[1]]
        ic = (xx - x) ** 2 + (yy - y) ** 2 < (0.6 * r) ** 2
        p = float(kucuk[ic].mean()) if ic.any() else 0
        ipucu = os.environ.get("V_DISK_X")                                  # elle ipucu: diskin yaklasik x'i (cikti olcegi)
        if ipucu:
            p -= abs(x * k - float(ipucu)) * 0.5
        if en is None or p > en[0]:
            en = (p, x * k, y * k, r * k)
    _, x, y, r = en
    for t1, t2 in ((30, 90), (15, 45), (8, 24)):                        # acik zeminde dusuk Canny esikleri yedek
        ken = cv2.Canny(cv2.GaussianBlur(gri, (0, 0), 1.5), t1, t2)
        yy, xx = np.nonzero(ken)
        d = np.hypot(xx - x, yy - y)
        sec = (np.abs(d - r) < 0.06 * r) & (yy > y - 0.75 * r)          # ust kisim (delik/ip) haric
        pts = np.stack([xx[sec], yy[sec]], 1).astype(np.float32)
        if len(pts) >= 200:
            break
    if len(pts) < 200:
        raise SystemExit("DUR: kenar noktasi az")
    (cx, cy), (ea, eb), aci = cv2.fitEllipse(pts)
    oran = min(ea, eb) / max(ea, eb)
    return (1.0, cx, cy, ea, eb, aci, len(pts) / (math.pi * (ea + eb) / 2), oran, "hough")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sahne"); ap.add_argument("baski"); ap.add_argument("cikti")
    ap.add_argument("--baslik", required=True); ap.add_argument("--alt", required=True)
    ap.add_argument("--renk", choices=("koyu", "krem"), default="koyu")
    ap.add_argument("--baslik_renk", default=None, help="R,G,B (verilirse --renk yerine)")
    ap.add_argument("--hale", choices=("yok", "acik", "koyu"), default="yok", help="baslik arkasi yumusak hale")
    ap.add_argument("--disk", default="", help="elle elips: cx,cy,eksen_a,eksen_b,aci (cikti olcegi, zoom 1; tespit atlanir)")
    ap.add_argument("--dondur", default="0", help="baski donusu derece ya da 'oto' (delik sahnedeki ipin tam altina gelir)")
    ap.add_argument("--golge", action="store_true", help="baslik altina yumusak gölge (zemin rengi degismez)")
    ap.add_argument("--zoom", type=float, default=1.0)
    ap.add_argument("--temas", action="store_true", help="disk bir yuzeye degiyorsa alt kenar temas golgesi")
    ap.add_argument("--bant", default=None, help="baslik bandi x0,x1 (varsayilan BANT)")
    ap.add_argument("--y", default="330,500", help="baslik ve alt yazi taban cizgisi y1,y2")
    ap.add_argument("--hedef", default="1500,1540", help="zoom sonrasi disk merkezi x,y")
    a = ap.parse_args()

    ham = Image.open(a.sahne).convert("RGB")
    sah = ham.resize((W, H), Image.LANCZOS)
    bgr = cv2.cvtColor(np.asarray(sah), cv2.COLOR_RGB2BGR)
    if a.disk:
        # elle verilen elips (ham sahne koordinati): onceden olculmus disk, sahne disk_kaydir.py ile tasindiysa tespit cift kenara takilir
        cx, cy, ea, eb, aci = (float(v) for v in a.disk.split(","))
        skor, dol, oran, esik = 1.0, 1.0, min(ea, eb) / max(ea, eb), "elle"
    else:
        skor, cx, cy, ea, eb, aci, dol, oran, esik = disk_bul(bgr)
    pencere = None
    if a.zoom > 1.0:
        # yaklastirma: ham sahneden pencere kirpilir (ikinci buyutme yok), disk merkezi hedef noktaya gelir
        hx, hy = map(float, a.hedef.split(","))
        pw, ph = W / a.zoom, H / a.zoom
        x0w, y0w = cx - hx / a.zoom, cy - hy / a.zoom
        if x0w < 0 or y0w < 0 or x0w + pw > W or y0w + ph > H:
            raise SystemExit(f"DUR: zoom penceresi sahne disina tasiyor {x0w:.0f},{y0w:.0f},{x0w+pw:.0f},{y0w+ph:.0f}")
        k_ = ham.width / W
        kutu = (x0w * k_, y0w * k_, (x0w + pw) * k_, (y0w + ph) * k_)
        sah = ham.resize((W, H), Image.LANCZOS, box=kutu)
        sah = sah.filter(ImageFilter.UnsharpMask(radius=2, percent=35, threshold=2))
        pencere = [round(v, 1) for v in kutu]
        bgr = cv2.cvtColor(np.asarray(sah), cv2.COLOR_RGB2BGR)
        # elips yeniden aranmaz: yakinlastirilmamis olcum pencereye tam donusturulur (oran, aci, doluluk ayni)
        cx, cy, ea, eb = (cx - x0w) * a.zoom, (cy - y0w) * a.zoom, ea * a.zoom, eb * a.zoom
    buyutme = round(W / (ham.width if pencere is None else (pencere[2] - pencere[0])), 3)
    R = (ea + eb) / 4
    yy, xx = np.mgrid[0:H, 0:W]
    t = math.radians(aci)
    ux, uy = (xx - cx) * math.cos(t) + (yy - cy) * math.sin(t), -(xx - cx) * math.sin(t) + (yy - cy) * math.cos(t)
    elips = (ux / (ea / 2)) ** 2 + (uy / (eb / 2)) ** 2
    gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ref = float(np.median(gri[elips < 0.36]))

    # eski delik: diskin ust bandinda koyu leke
    bant = (elips < 0.95) & (yy < cy - 0.45 * R) & (np.abs(xx - cx) < 0.3 * R)
    koyu = (bant & (gri < ref - 45)).astype(np.uint8)
    n2, et2, ist2, mer2 = cv2.connectedComponentsWithStats(koyu)
    if n2 < 2:
        raise SystemExit("DUR: delik bulunamadi")
    j = 1 + int(np.argmax(ist2[1:, cv2.CC_STAT_AREA]))
    ox, oy = mer2[j]
    delik_m = cv2.dilate((et2 == j).astype(np.uint8), np.ones((5, 5), np.uint8))
    rh = math.sqrt(ist2[j, cv2.CC_STAT_AREA] / math.pi)

    # hale: tespit elipsinin hemen disinda sahnenin acik disk kenari kaliyorsa (tam cevre medyani) eksenler buyutulur, en cok 10 px
    def halka_med(g0, g1):
        e0 = (ux / (ea / 2 + g0)) ** 2 + (uy / (eb / 2 + g0)) ** 2
        e1 = (ux / (ea / 2 + g1)) ** 2 + (uy / (eb / 2 + g1)) ** 2
        m = (e0 >= 1) & (e1 < 1)
        return float(np.median(gri[m]))
    uzak = halka_med(16, 24)
    buyut = 0
    for g in range(0, 11):
        if abs(halka_med(g, g + 3) - uzak) < 12:
            buyut = g; break
    else:
        buyut = 10
    ea, eb = ea + 2 * buyut, eb + 2 * buyut
    R = (ea + eb) / 4
    uyari = []
    if oran < 0.97:
        uyari.append(f"elips orani {oran:.3f} < 0,97 (disk tam onden degil ya da uydurma hatali)")
    if dol < 0.30:
        uyari.append(f"kenar dolulugu {dol:.2f} < 0,30 (elips zayif kanitla uyduruldu)")
    # donusum
    Rm = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    S = np.diag([ea / 2 / KR, eb / 2 / KR])
    # asili disk: delik askı noktasinin tam altindadir. 'oto': sahnedeki ipin disk ustundeki x'i olculur, baski merkez etrafinda
    # dondurulur ki delik ipin altina gelsin (Serdar 6 Kas: "delikle olan baglanti yeri kaymis gibi")
    dondur_der = 0.0
    if a.dondur == "oto":
        hs_ = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        ipm_ = (hs_[..., 1] > 100) & (hs_[..., 0] >= 12) & (hs_[..., 0] <= 32) & (hs_[..., 2] > 70)
        yb0_, yb1_ = int(cy - (eb / 2) * 1.25), int(cy - (eb / 2) * 1.03)
        xb0_, xb1_ = int(cx - 0.3 * R), int(cx + 0.3 * R)
        bant_ = ipm_[max(0, yb0_):max(1, yb1_), max(0, xb0_):xb1_]
        if bant_.sum() > 20:
            xs_ip = xb0_ + float(np.median(np.nonzero(bant_)[1]))
            d_del = (KY - DY) / KR * R
            dondur_der = math.degrees(math.asin(float(np.clip((xs_ip - cx) / d_del, -0.3, 0.3))))
    elif a.dondur not in ("0", ""):
        dondur_der = float(a.dondur)
    tc = math.radians(dondur_der)
    Rc = np.array([[math.cos(tc), -math.sin(tc)], [math.sin(tc), math.cos(tc)]])
    A2 = Rm @ S @ Rm.T @ Rc
    b = np.array([cx, cy]) - A2 @ np.array([KX, KY])
    M = np.hstack([A2, b[:, None]]).astype(np.float64)
    nx, ny = A2 @ np.array([DX, DY]) + b

    elips = (ux / (ea / 2)) ** 2 + (uy / (eb / 2)) ** 2
    src = Image.open(a.baski).convert("RGBA")
    s = np.asarray(src).astype(np.float32)
    sy, sx = np.mgrid[0:src.height, 0:src.width]
    kesim = np.clip(KR + 0.5 - np.hypot(sx - KX, sy - KY), 0, 1)
    s[..., 3] = s[..., 3] * kesim
    pre = s.copy(); pre[..., :3] *= pre[..., 3:4] / 255.0
    w_ = cv2.warpAffine(pre, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # ileri kiyas kapisi (a): ikinci yol bagimsiz kurulur: ters matris numpy ile ayri hesaplanir, piksel haritasi
    # elle uretilir, cv2.remap ile ornekleme yapilir; warpAffine ciktisiyla karsilastirilir
    A_inv = np.linalg.inv(np.vstack([M, [0, 0, 1]]))[:2]
    gx_, gy_ = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
    mx = (A_inv[0, 0] * gx_ + A_inv[0, 1] * gy_ + A_inv[0, 2]).astype(np.float32)
    my = (A_inv[1, 0] * gx_ + A_inv[1, 1] * gy_ + A_inv[1, 2]).astype(np.float32)
    w2 = cv2.remap(pre, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    kapi_a = float(np.abs(w_ - w2).max())
    kapi_a_ort = float(np.abs(w_ - w2).mean())
    kapi_a_u8 = int(np.abs(np.round(w_).astype(np.int32) - np.round(w2).astype(np.int32)).max())   # 8 bit cikti duzeyinde fark
    al = np.clip(w_[..., 3:4] / 255.0, 0, 1)
    renk = np.where(al > 1e-6, w_[..., :3] / np.maximum(al, 1e-6), 0)
    # kenarda cok kucuk alfaya bolme parlak benek uretir: alfa < 0,5 olan kenar piksellerinin rengi icteki gecerli renkten (maskeli bulaniklik) alinir
    gec = (al[..., 0] >= 0.5).astype(np.float32)
    rb = cv2.GaussianBlur(renk.astype(np.float32) * gec[..., None], (0, 0), 3) / np.maximum(cv2.GaussianBlur(gec, (0, 0), 3), 1e-3)[..., None]
    renk = np.where(gec[..., None] > 0, renk, rb)

    # golge / parlaklik (yalniz disk icinde)
    hsv0 = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    ip0 = (hsv0[..., 1] > 100) & (hsv0[..., 0] >= 12) & (hsv0[..., 0] <= 32) & (hsv0[..., 2] > 70)
    sil = (cv2.dilate(delik_m, np.ones((9, 9), np.uint8)) > 0) | (ip0 & (elips < 1.0))
    sil = cv2.dilate(sil.astype(np.uint8), np.ones((5, 5), np.uint8))
    sahne_orj = np.asarray(sah).astype(np.float32).copy()
    bgr = cv2.inpaint(bgr, sil, 7, cv2.INPAINT_TELEA)
    sah = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    gri = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    sahne_f = np.asarray(sah).astype(np.float32)
    # isik yonu: bos diske duzlem uydurma (L = a + b*vx + c*vy); parlak taraf (b, c) yonunde
    mk = elips < 0.8
    Am = np.stack([np.ones(mk.sum()), ((xx - cx) / R)[mk], ((yy - cy) / R)[mk]], 1)
    kat_ = np.linalg.lstsq(Am, gri[mk], rcond=None)[0]
    lx, ly = float(kat_[1]), float(kat_[2]); ln = math.hypot(lx, ly) or 1.0
    lx, ly = lx / ln, ly / ln
    # isik aktarimi: bos beyaz diskin parlaklik haritasi (yalniz disk pikselleriyle normalize bulaniklik; kenara zemin sizmaz)
    dm_ = (elips < 0.985).astype(np.float32)
    sg = max(2.0, 0.02 * R)
    Lr = cv2.GaussianBlur(gri * dm_, (0, 0), sg) / np.maximum(cv2.GaussianBlur(dm_, (0, 0), sg), 1e-3)
    f = np.clip(Lr / ref, 0.72, 1.15)[..., None]
    # renk sicakligi: bos diskin rengi (beyaz yuzeye dusen ortam isigi)
    dr = np.median(sahne_f[elips < 0.36], axis=0)
    ton = np.clip(dr / dr.mean(), 0.92, 1.08)
    ton = 1 + (ton - 1) * float(os.environ.get("V_TON", "1"))             # 0 = baski rengi 1:1 (sicak sahnede krem seftaliye kaymasin)
    renk = renk * ton[None, None, :]
    # keskinlik eslesmesi: baski sahnenin buyutulmus yumusakligina yaklasir
    hsv_k = cv2.cvtColor(np.clip(renk, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    altin_k = (np.clip((hsv_k[..., 1] - 60) / 50, 0, 1) * np.clip((hsv_k[..., 2] - 70) / 50, 0, 1) * ((hsv_k[..., 0] >= 12) & (hsv_k[..., 0] <= 34))).astype(np.float32)
    altin_k = cv2.GaussianBlur(cv2.dilate(altin_k, np.ones((3, 3), np.uint8)), (0, 0), 0.8)[..., None]
    renk = cv2.GaussianBlur(renk.astype(np.float32), (0, 0), 0.5 * buyutme) * (1 - altin_k) + renk * altin_k   # v8 incelemesi: ince altin bulaniklikla V -%9..-17; altin keskin kalir
    # kenar: geometrik yumusak kenar (sahne kenar gecisi kadar), tasarim kenara dek
    ksig = 1.3 * buyutme * float(os.environ.get('V_KENAR', '1'))                                  # sahne kenari %10-90 ~ 2,56 sigma (olcum: 8-10 px)
    al = np.minimum(al, np.clip((1 - np.sqrt(elips)) * R / (2.56 * ksig) + 0.5, 0, 1)[..., None])
    seffaf = float((np.asarray(src)[..., 3] == 0).mean()) > 0.2      # White stil: seffaf PNG, sahnenin beyaz diski kalir
    if seffaf:
        # seffaf baski (White): alttaki bos disk yalniz dusuk frekans isigiyla kalir (eski delik/ip izi kalmaz)
        sgb = 0.05 * R
        taban = cv2.GaussianBlur(sahne_f * dm_[..., None], (0, 0), sgb) / np.maximum(cv2.GaussianBlur(dm_, (0, 0), sgb), 1e-3)[..., None]
        icm = np.clip((1 - np.sqrt(elips)) * R / 3 + 0.5, 0, 1)[..., None]
        bh = float(os.environ.get("V_BEYAZ", "0"))                       # >0: bos beyaz disk notr bu degere (sicak odada bej-gri gorunmesin)
        if bh > 0:
            d0 = np.median(taban[elips < 0.36], axis=0)
            taban = np.clip(taban * np.clip(bh / np.maximum(d0, 1), 0.8, 1.3)[None, None, :], 0, 255)
        sahne_f = sahne_f * (1 - icm) + taban * icm
        ust_k = renk * f
    else:
        ust_k = renk * f
    ust_k = np.clip(ust_k, 0, 255)
    kaldir = 0.0                                                          # v6 incelemesi: siyah kaldirma / doygunluk azaltma rengi ve altini bozdu, kaldirildi
    # altin maskesi (baskidan): altin pikseller yansima/parlama almaz (KARAR: altinin rengi degismez)
    hsv_b = cv2.cvtColor(np.clip(renk, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    altin = np.clip((hsv_b[..., 1] - 70) / 60, 0, 1) * np.clip((hsv_b[..., 2] - 110) / 50, 0, 1) * ((hsv_b[..., 0] >= 14) & (hsv_b[..., 0] <= 32))
    altin = cv2.GaussianBlur(altin.astype(np.float32), (0, 0), 1.5)
    # parlak seramik: sol ustten yumusak isik bandi (screen, dusuk) + yuvarlatilmis kenar: sol ust ince parlama, sag alt ince golge
    rr = np.sqrt(elips)
    vx_, vy_ = (xx - cx) / R, (yy - cy) / R
    yon = (vx_ * lx + vy_ * ly)                                            # sahnenin isik tarafi = +1
    dik_ = (-vx_ * ly + vy_ * lx)                                          # isik yonune dik eksen
    pen_ = np.exp(-((yon - 0.55) / 0.07) ** 4) * np.exp(-((dik_ + 0.15) / 0.38) ** 4)   # dar, yumusak kenarli pencere yansimasi
    pen_ = cv2.GaussianBlur(pen_.astype(np.float32), (0, 0), 0.02 * R)
    parla = (float(os.environ.get('V_PARLA', '0.04')) * pen_ * (rr < 0.97) * (1 - altin))[..., None]
    ust_k = 255 - (255 - ust_k) * (1 - parla)
    # seramik parlakligi (Serdar 6 Kas: "seramik algisi yok, hafif isiklandirma"): (1) isik tarafinda kenari izleyen ince hilal parlama,
    # (2) sag ustte kucuk yumusak softbox yansimasi, (3) cok hafif genel parlaklik gecisi. Altin piksellere uygulanmaz (renk kurali).
    v_hil = float(os.environ.get("V_HILAL", "0")); v_nok = float(os.environ.get("V_NOKTA", "0")); v_grd = float(os.environ.get("V_GRAD", "0"))
    if v_hil or v_nok or v_grd:
        acı_isik = math.atan2(ly, lx)
        acı_px = np.arctan2(vy_, vx_)
        fark = np.angle(np.exp(1j * (acı_px - acı_isik)))                      # isik yonune acisal uzaklik (-pi..pi)
        hilal = np.exp(-((rr - 0.93) / 0.025) ** 2) * np.exp(-((fark + 0.35) / 0.85) ** 2) * (rr < 0.985)   # isik tarafindan uste dogru
        hilal = cv2.GaussianBlur(hilal.astype(np.float32), (0, 0), 0.006 * R + 0.5)
        nx_s, ny_s = 0.42, -0.55                                               # sag ust: softbox yansimasi kenar egrisine paralel uzun yumusak leke
        tn_ = math.atan2(ny_s, nx_s) + math.pi / 2
        u_ = (vx_ - nx_s) * math.cos(tn_) + (vy_ - ny_s) * math.sin(tn_); w_ = -(vx_ - nx_s) * math.sin(tn_) + (vy_ - ny_s) * math.cos(tn_)
        nokta = np.exp(-((u_ / 0.16) ** 2 + (w_ / 0.045) ** 2))
        nokta = cv2.GaussianBlur(nokta.astype(np.float32), (0, 0), 0.01 * R + 0.5)
        grd = np.clip(0.5 + 0.5 * (vx_ * lx + vy_ * ly - 0.3 * vy_), 0, 1) ** 2
        sr = (v_hil * hilal + v_nok * nokta + v_grd * grd) * (rr < 1) * (1 - altin)
        ust_k = 255 - (255 - ust_k) * (1 - np.clip(sr, 0, 0.6)[..., None])
    # kenar aktarimi: sentetik pah yerine sahnedeki gercek diskin kendi kenar isigi (parlak yan duvar / pah parlamasi,
    # golgede kalan ince koyu kontur, kenara dogru koyulasma) ayni acida baskiya tasinir. Taban: ayni 5 derecelik dilimde
    # diskin ic halkasi (rd -0,25R..-0,12R) medyani. Parlak kisim screen (koyu parlak yuzeyde yansima eklenir), koyu kisim carpim.
    aci0 = np.degrees(np.arctan2(yy - cy, xx - cx)) % 360
    rd0 = (rr - 1) * R
    KB = 0.07 * R
    tab = np.full((H, W), np.nan, np.float32)
    for a0 in range(0, 360, 5):
        sek = (aci0 >= a0) & (aci0 < a0 + 5)
        im_ = sek & (rd0 > -0.25 * R) & (rd0 < -0.12 * R) & ~sil.astype(bool)
        if im_.sum() < 30:
            continue
        tab[sek & (rd0 >= -KB) & (rd0 <= 0)] = float(np.median(gri[im_]))
    NA, NB = 72, int(KB) + 1
    prof = np.ones((NA, NB), np.float32)
    rdb = np.clip(np.round(-rd0), 0, NB - 1).astype(np.int32)
    aib = (aci0 // 5).astype(np.int32) % NA
    for a_i in range(NA):
        sek = (aib == a_i)
        t_ = tab[sek & (rd0 >= -KB) & (rd0 <= 0)]
        if t_.size == 0 or np.isnan(t_).all():
            continue
        tb = float(np.nanmedian(t_))
        for b_i in range(2, NB):
            m_ = sek & (rdb == b_i) & (rd0 <= 0) & ~sil.astype(bool)
            if m_.sum() >= 3:
                prof[a_i, b_i] = float(np.median(gri[m_])) / max(tb, 1.0)
    prof[:, :7] = prof[:, 7:8]                                             # en dis 6-7 px sahnenin kenar yumusatma gecisi (zemine karisir): golge sayilmaz, komsu degerle
    # acida dairesel yumusatma (sigma 1,5 dilim) -> kopuk olmayan hilal
    pr3 = np.concatenate([prof, prof, prof], 0)
    pr3 = cv2.GaussianBlur(pr3, (1, 0), sigmaX=0.001, sigmaY=1.5)
    prof = pr3[NA:2 * NA]
    af = (aci0 / 5.0) % NA
    a0i = np.floor(af).astype(np.int32) % NA; a1i = (a0i + 1) % NA; wa = (af - np.floor(af)).astype(np.float32)
    bf = np.clip(-rd0, 0, NB - 1); b0i = np.floor(bf).astype(np.int32); b1i = np.minimum(b0i + 1, NB - 1); wb = (bf - b0i).astype(np.float32)
    koran = ((prof[a0i, b0i] * (1 - wb) + prof[a0i, b1i] * wb) * (1 - wa) + (prof[a1i, b0i] * (1 - wb) + prof[a1i, b1i] * wb) * wa)
    sond = np.clip((rd0 + KB) / (0.35 * KB), 0, 1) * (rd0 <= 0.5)
    dis_son = np.clip(0.6 + 0.4 * (-rd0 / 3.0), 0.6, 1)                   # en dis 3 px hafif azalir (tam sifir koyu dis cizgi yapiyordu, v7 K1)
    acik_ = np.clip(koran - 1, 0, 0.6) / 0.6 * sond * dis_son * np.clip((rd0 + 18) / 6, 0, 1)   # parlak kenar sahnedeki kadar dar (~14 px)
    koyu_ = np.clip(1 - koran, 0, 0.6) * sond * np.clip(1 - 2 * np.clip(yon, 0, 1), 0, 1)[...]   # isik alan tarafta koyu kontur yok (sahnede orada parlak kenar var)
    ust_k = 255 - (255 - ust_k) * (1 - (0.50 * acik_)[..., None])
    ust_k = ust_k * (1 - (1.0 * koyu_)[..., None])
    # yan duvar (v9 incelemesi K1): beyaz seramigin golgedeki kenari sahnede 8-10 px gri bant; baskili yuz bunu kapatmamali.
    # Ton sahnenin kendi bandindan (orijinal sahne, golge tarafi 150-210 derece, rd -14..+10, L 85-145 medyani); genislik golge tarafinda 9 px'e dek.
    lo_ = cv2.cvtColor(np.clip(sahne_orj, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    ys_m = (aci0 >= 150) & (aci0 <= 210) & (rd0 > -14) & (rd0 < 10) & (lo_ > 85) & (lo_ < 145)
    duvar_ton = np.median(sahne_orj[ys_m], axis=0) if ys_m.sum() > 50 else np.array([120.0, 112, 104])
    # dilim basina sahne kenar profili (orijinal sahne): koyu cekirdek tonu ve bant derinligi (zeminden >= 20 koyu kalan rd sayisi)
    NAD = 72
    cek_L = np.full(NAD, np.nan, np.float32); der_ = np.zeros(NAD, np.float32)
    ai_ = (aci0 // 5).astype(np.int32) % NAD
    rdi = np.round(rd0).astype(np.int32)
    for a_i in range(NAD):
        sek = ai_ == a_i
        zl_ = lo_[sek & (rd0 > 16) & (rd0 < 26)]
        if zl_.size < 20:
            continue
        zm_ = float(np.median(zl_))
        prf = []
        for rv in range(-20, 13):
            v_ = lo_[sek & (rdi == rv)]
            prf.append(float(np.median(v_)) if v_.size >= 3 else np.nan)
        prf = np.array(prf)
        koyu_b = np.nan_to_num(prf, nan=zm_) < zm_ - 20
        # yalniz kenar cevresindeki koyu bant (yuz parlak disk; koyu bant zemin ile yuz arasinda)
        der_[a_i] = float(koyu_b.sum())
        if koyu_b.any():
            cek_L[a_i] = float(np.nanmin(prf[koyu_b]))
    der_ = np.where(der_ >= 3, der_, 0)                                   # sahnede bant yoksa bant yok
    pad = lambda v: np.concatenate([v[-3:], v, v[:3]])
    der_s = np.convolve(pad(der_), np.ones(5) / 5, mode="same")[3:-3]
    cek_f = np.where(np.isnan(cek_L), np.nanmedian(cek_L) if np.isfinite(cek_L).any() else 110.0, cek_L)
    cek_s = np.convolve(pad(cek_f), np.ones(5) / 5, mode="same")[3:-3]
    afd = (aci0 / 5.0) % NAD; a0d = np.floor(afd).astype(np.int32) % NAD; a1d = (a0d + 1) % NAD; wad = (afd - np.floor(afd)).astype(np.float32)
    w_d = np.clip(der_s[a0d] * (1 - wad) + der_s[a1d] * wad, 0, 11) * (yon < 0.3)
    cekL_px = cek_s[a0d] * (1 - wad) + cek_s[a1d] * wad
    t_ = np.clip((-rd0) / np.maximum(w_d, 1), 0, 1) * 2 - 1                # bant icinde -1 (dis) .. +1 (ic)
    v_prof = 1.0 + 0.22 * np.abs(t_) ** 1.5                               # ortasi koyu, kenarlari acik (sahnedeki V profili)
    ton_olcek = (cekL_px / max(float(np.mean(duvar_ton)), 1.0))[..., None] * v_prof[..., None]
    yd_ton = np.clip(duvar_ton[None, None, :] / max(float(np.mean(duvar_ton)), 1.0) * float(np.mean(duvar_ton)) * ton_olcek, 0, 255)
    yd_m = np.clip((rd0 + w_d) / 4.5 + 0.5, 0, 1) * (w_d > 0.5) * (rd0 <= 1)   # ic kenar ~4-5 px yumusak (sahne konturu kadar)
    yd_m = yd_m * float(os.environ.get('V_DUVAR', '1'))
    ust_k = ust_k * (1 - yd_m[..., None]) + yd_ton * yd_m[..., None]
    yan_duvar = {"ton": [round(float(v), 1) for v in duvar_ton], "ornek_px": int(ys_m.sum()), "derinlik_dilim": [round(float(v), 1) for v in der_s], "cekirdek_L": [round(float(v), 1) for v in cek_s]}
    kenar_aktarim = {"bant_px": round(KB, 1), "acik_maks": round(float(acik_.max()), 3), "koyu_maks": round(float(koyu_.max()), 3)}
    # gren: sahnenin duz bolgesindeki gurultu kadar
    hp = gri - cv2.GaussianBlur(gri, (0, 0), 2)
    duz = np.abs(cv2.GaussianBlur(hp, (0, 0), 8)) < 1.0
    gstd = float(np.std(hp[duz & (elips > 2.5)])) if (duz & (elips > 2.5)).sum() > 1000 else 1.5
    rng0 = np.random.default_rng(11)
    ust_k = np.clip(ust_k + rng0.normal(0, 0.6 * gstd, (H, W))[..., None], 0, 255)
    # hale (acili, yerlestirmeden once sahnede): yumusak kenarin altinda ve diskin hemen disinda sahnenin parlak bos disk kenari kaldiysa, ayni acidaki zemin rengine cekilir
    aci_ = np.degrees(np.arctan2(yy - cy, xx - cx)) % 360
    rd = (rr - 1) * R                                                      # disk kenarindan disari px
    hale_px = 0
    ip_bolge = (np.abs(xx - nx) < 0.15 * R) & (yy < cy - 0.5 * R)            # yalniz ip/dugum bolgesi (yaprak gibi sari-zeytin lekeler korunmaz)
    ip_siki = (hsv0[..., 1] > 125) & (hsv0[..., 0] >= 12) & (hsv0[..., 0] <= 32) & (hsv0[..., 2] > 70)   # yari karisik bej kenar pikselleri korunmaz, inpaint edilir
    ipz = cv2.dilate((ip_siki & ip_bolge).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)   # ip / dugum cevresi korunur (duz kesik olmasin)
    if not seffaf:
        # disk ici (rd < -12) once dilim zemin medyaniyla doldurulur: inpaint beyaz diski kenara tasimasin
        for a0 in range(0, 360, 5):
            sek = (aci_ >= a0) & (aci_ < a0 + 5)
            zm = sek & (rd > 22) & (rd < 34) & ~ipz
            if zm.sum() >= 20:
                sahne_f[sek & (rd < -12) & ~ipz] = np.median(sahne_f[zm], axis=0)
        # kenar bandi (rd -12..+22; sahnedeki disk kenari elipsten -12..+7 px sapiyor): sahnedeki eski beyaz disk kenari ve acik halka, disaridaki zeminden inpaint ile doldurulur
        # (dilim medyani yerine yerel doku: yaprak ucu gibi ayrintilar dilim boyunca yamaya donusmez)
        bm_ = ((rd >= -12) & (rd < 22)).astype(np.uint8)                 # dugum de bant icinde doldurulur (altin rengi inpaint ile yanlara sizmasin); dugum sonra sahneden geri konur
        sf8 = np.clip(sahne_f, 0, 255).astype(np.uint8)
        sahne_f = cv2.inpaint(sf8, bm_, 6, cv2.INPAINT_TELEA).astype(np.float32)
        hale_px = int(bm_.sum())
    else:
        for a0 in range(0, 360, 5):
            sek = (aci_ >= a0) & (aci_ < a0 + 5)
            zm = sek & (rd > 14) & (rd < 24) & ~ipz
            if zm.sum() < 20:
                continue
            zr = np.median(sahne_f[zm], axis=0); zl = float(np.median(gri[zm]))
            bm = sek & (rd >= 0) & (rd < 14) & ~ipz & (gri > zl + 6)
            if bm.any():
                w_h = np.clip((gri[bm] - zl - 6) / 12, 0, 1)[:, None]
                sahne_f[bm] = sahne_f[bm] * (1 - w_h) + zr[None, :] * w_h
                hale_px += int(bm.sum())
    out = sahne_f * (1 - al) + ust_k * al
    # temas / ortam golgesi: diskin alt yarisinda, disari dogru yumusak koyulasma (kumasla bulustugu yer)
    alt_ = np.clip((yy - cy) / R, 0, 1) ** 1.5
    ao = np.clip(1 - rd / (0.016 * R), 0, 1) * (rd >= -1) * alt_ * (0.38 if a.temas else 0.0)   # asili diskte temas golgesi yok
    out = out * (1 - ao[..., None])

    # delik: sahnenin eski deligi tasinmaz; yeni delik koddan cizilir. Cap 56,6 px baski olcegi (Printful sablon olcumu,
    # docs/ornament/ornek/ORNAMENT_ORNEK_20261102_1043/EK_OLCUM.json sablon.delik.cap_printfile)
    hr = 28.3 / KR * R
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    ipm = ((hsv[..., 1] > 100) & (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 2] > 70))
    arka_b = (elips > 1.08) & (elips < 1.40) & (yy < cy - 0.5 * R) & (np.abs(xx - cx) < 0.35 * R) & ~cv2.dilate(ipm.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    arka = np.median(sahne_f[arka_b], axis=0) if arka_b.sum() > 50 else np.array([40.0, 35, 32])
    dd = np.hypot(xx - nx, yy - ny)
    gol_h = np.clip(1 - np.abs(dd - hr - 0.10 * hr) / (0.22 * hr), 0, 1)[..., None] * 0.12   # delik cevresi ince golge (acik stilde kontur olmasin)
    out = out * (1 - gol_h)
    ic = np.clip((hr - dd) / 3.0 + 0.5, 0, 1)[..., None]                  # delik kenari dis kenar gibi ~3 px
    # ic: arka zemin (koyulastirilmis, ustten golge), altta seramik ic duvar (acik hilal)
    vy_ = (yy - ny) / hr
    derin = (0.93 + 0.05 * np.clip(vy_, -1, 1))
    ust_hilal = np.clip((np.hypot(xx - nx, (yy - ny) - 0.40 * hr) - 0.95 * hr) / (0.25 * hr), 0, 1) * (vy_ < 0.2)   # ust ic duvar golgesi
    derin = (derin * (1 - 0.55 * cv2.GaussianBlur(ust_hilal.astype(np.float32), (0, 0), 0.08 * hr + 0.5)))[..., None]
    ic_renk = arka[None, None, :] * derin

    duvar = (np.clip((np.hypot(xx - nx, yy - (ny - 0.16 * hr)) - hr) * 4 / hr, 0, 1) * (vy_ > 0))[..., None]   # alt ic duvar hilali (yukari kaydirilmis dairenin disi)
    seramik = np.array([228.0, 222, 214])
    ic_renk = ic_renk * (1 - duvar * 0.9) + seramik * f * (duvar * 0.9)
    out = out * (1 - ic) + ic_renk * ic

    # ip: disk disindaki gercek ip sahneden kalir; disk yuzundeki parca (giris -> yeni delik) koddan bukumlu ip olarak cizilir
    halka_bolge = ipm & (elips > 1.02) & (elips < 1.35) & (yy < cy) & (np.abs(xx - nx) < 0.45 * R)
    ip_eklendi = 0
    artik_px = 0
    kal = 0.0
    if halka_bolge.sum() > 10:
        n3, et3, ist3, mer3 = cv2.connectedComponentsWithStats(halka_bolge.astype(np.uint8))
        aday = []
        for i in range(1, n3):
            if ist3[i, cv2.CC_STAT_AREA] <= 8:
                continue
            ex, ey = mer3[i]
            y0_, x0_ = max(0, int(ey - 0.6 * R)), max(0, int(ex - 0.12 * R))
            ust = int(ipm[y0_:int(ey), x0_:int(ex + 0.12 * R)].sum())
            aday.append((-ust / (1.0 + abs(ex - nx) / (0.06 * R)), i))
        aday.sort()
        ipm_g = ipm & (hsv[..., 1] > 140)
        ipp = sahne_f[ipm_g & (elips > 1.02) & (elips < 2.2) & (np.abs(xx - nx) < 0.5 * R) & (yy < cy)]
        ip_renk = np.median(ipp[ipp.sum(1) >= np.median(ipp.sum(1))], axis=0) / 1.05   # parlak yari / silindir ortalamasi
        blk = ipm[max(0, int(cy - R * 1.45)):int(cy - R * 1.08), max(0, int(nx - 0.15 * R)):int(nx + 0.15 * R)]
        kos = []
        for row in blk:
            d_ = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
            bas_, son_ = np.nonzero(d_ == 1)[0], np.nonzero(d_ == -1)[0]
            kos += [int(q) for q in (son_ - bas_) if q >= 3]
        kal = float(np.clip(np.median(kos) if kos else 6.0, 4.0, 0.035 * R))     # tek ip genisligi (cift ipte toplam degil)
        if aday:
            i = aday[0][1]
            ys_c, xs_c = np.nonzero(et3 == i)
            ey = float(ys_c.max()); ex = float(xs_c[ys_c >= ey - 2].mean())     # bilesenin diske en yakin ucu (V seklinde agirlik merkezi ipin disinda kalabilir)
            y0_, x0_ = max(0, int(ey - 0.6 * R)), max(0, int(ex - 0.12 * R))
            ys_, xs_ = np.nonzero(ipm[y0_:int(ey), x0_:int(ex + 0.12 * R)])
            if len(ys_) > 30:
                vx, vy = float(np.mean(xs_ + x0_) - ex), float(np.mean(ys_ + y0_) - ey)
                n_ = math.hypot(vx, vy); vx, vy = vx / n_, vy / n_
            else:
                vx, vy = 0.0, -1.0
            P0 = np.array([ex + vx * 0.012 * R, ey + vy * 0.012 * R])   # gercek ipin diske en yakin ucu (kisa bindirme)
            P1 = np.array([ex - vx * 0.08 * R, ey - vy * 0.08 * R])     # teget surekli
            P2 = np.array([nx, ny - 0.55 * hr])                         # ip deligin ust kenarindan arkaya gecer
            tt_ = np.linspace(0, 1, 400)[:, None]
            C = (1 - tt_) ** 2 * P0 + 2 * (1 - tt_) * tt_ * P1 + tt_ ** 2 * P2
            sl = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(C, axis=0).T))])
            x0, x1 = int(C[:, 0].min() - 4 * kal), int(C[:, 0].max() + 4 * kal)
            y0, y1 = int(C[:, 1].min() - 4 * kal), int(C[:, 1].max() + 4 * kal)
            gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            P = np.stack([gx.ravel(), gy.ravel()], 1)
            best_d = np.full(len(P), 1e9, np.float32); best_k = np.zeros(len(P), np.int32)
            for k0 in range(0, 400, 50):
                d_ = np.hypot(P[:, None, 0] - C[None, k0:k0 + 50, 0], P[:, None, 1] - C[None, k0:k0 + 50, 1])
                kk = d_.argmin(1); dm_ = d_[np.arange(len(P)), kk]
                yeni_ = dm_ < best_d; best_d[yeni_] = dm_[yeni_]; best_k[yeni_] = kk[yeni_] + k0
            k = best_k.reshape(gx.shape); dmin = best_d.reshape(gx.shape)
            tgx = np.gradient(C[:, 0]); tgy = np.gradient(C[:, 1]); tn = np.hypot(tgx, tgy)
            nxv, nyv = -tgy / tn, tgx / tn
            sd = (gx - C[k, 0]) * nxv[k] + (gy - C[k, 1]) * nyv[k]            # isaretli dik uzaklik
            c = np.clip(sd / (kal / 2), -1, 1)
            alfa = np.clip(kal / 2 + 0.5 - dmin, 0, 1)
            alfa *= np.clip(sl[k] / (0.012 * R), 0, 1)                            # bas: gercek ipe yumusak gecis
            # bukum: capraz seritler + silindir golgesi + parlama
            pitch = 1.15 * kal
            rng = np.random.default_rng(7)
            serit = 0.84 + 0.24 * np.cos(2 * math.pi * (sl[k] / pitch + 0.45 * c)) + 0.06 * rng.standard_normal(c.shape)   # v9: buküm kontrasti sahne ipine yakin
            silindir = 0.58 + 0.52 * np.sqrt(np.clip(1 - c ** 2, 0, 1)) - 0.10 * c
            parla = 0.25 * np.exp(-((c + 0.3) / 0.22) ** 2) * (serit > 0.98)
            ipc = np.clip(1.1 * ip_renk[None, None, :] * (silindir * serit)[..., None] + 255 * parla[..., None] * 0.5, 0, 255)   # v8: sahne ipinden %23 solukti
            # delik ici: ip deligin ust kenarindan iceri girer, arkaya gecer: derinlikle koyulasir ve incelir
            dd_ = np.hypot(gx - nx, gy - ny)
            ic_ = dd_ < hr
            derinlik = np.clip((gy - (ny - hr * 0.95)) / (0.45 * hr), 0, 1) * ic_
            ipc = ipc * (1 - 0.65 * derinlik)[..., None]
            alfa = alfa * np.where(ic_, np.clip(1.15 - 1.0 * derinlik, 0, 1), 1)
            # keskinlik: sahne 2x buyutuldugu icin ip sahne ipiyle ayni yumusaklikta
            alfa = cv2.GaussianBlur(alfa.astype(np.float32), (0, 0), 0.9)
            ipc = cv2.GaussianBlur(ipc.astype(np.float32), (0, 0), 0.9)
            parca = out[y0:y1, x0:x1].copy()
            # golge (yalniz disk yuzunde): alfa kaydirilmis, bulanik
            ofs = (int(round(0.018 * R)), -int(round(0.010 * R)))              # isik sagdan: golge sola-asagi
            gl = cv2.GaussianBlur(np.roll(alfa, ofs, (0, 1)), (0, 0), 0.25 * kal + 1) * 0.35
            gl *= np.clip(1.0 - elips[y0:y1, x0:x1], 0, 1) > 0
            parca = parca * (1 - gl[..., None])
            out[y0:y1, x0:x1] = parca * (1 - alfa[..., None]) + ipc * alfa[..., None]
            ip_eklendi = 1
    # sahnedeki dugum disk ust kenarina biniyorsa (ip onde) geri konur: duz kesik kalmasin
    dug = (ip0 & (elips >= 0.93) & (elips < 1.0) & (np.abs(xx - nx) < 0.06 * R) & (yy < cy - 0.8 * R)).astype(np.uint8)
    dugum_px = int(dug.sum())
    if dugum_px:
        hso = cv2.cvtColor(np.clip(sahne_orj, 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
        ipw_ = np.clip((hso[..., 1] - 120) / 40, 0, 1) * ((hso[..., 0] >= 12) & (hso[..., 0] <= 32)) * np.clip((hso[..., 2] - 60) / 40, 0, 1)
        rd_d = (np.sqrt(elips) - 1) * R
        kutu = ((np.abs(xx - nx) < 0.08 * R) & (rd_d > -0.04 * R) & (rd_d < 0.07 * R) & (yy < cy - 0.8 * R)).astype(np.float32)
        sonum = np.clip((rd_d + 10.0) / 4.0, 0, 1)                                 # disk icinde cizilen ip esas; sahne ipi yalniz kenarin 5 px icine dek (tirtik kalmasin)
        dm2 = cv2.GaussianBlur((ipw_ * kutu * sonum).astype(np.float32), (0, 0), 0.6)
        # dugumun disk yuzune yumusak golgesi (isik sagdan: sola-asagi)
        gd = cv2.GaussianBlur(np.roll(dm2, (int(round(0.009 * R)), -int(round(0.006 * R))), (0, 1)), (0, 0), 3.0) * 0.30 * (elips < 1.0)
        gd = gd * (1 - dm2)
        out = out * (1 - gd[..., None])
        # dugumun alt kenari disk kenarinda duz bitiyor (sahnede dugum beyaz diskin ustunde): her sutunda alt satir rengi asagi
        # yuvarlak bir uzatmayla diskin ~8 px icine tasinir (dugum onde durur), alt yuzu hafif koyu
        dug_al = dm2.copy(); dug_rk = sahne_orj.copy()
        kx = np.nonzero((dm2 > 0.5).any(0) & (np.abs(np.arange(W) - nx) < 0.08 * R))[0]
        if kx.size >= 6:
            xa, xb = int(kx.min()), int(kx.max()); xc_ = 0.5 * (xa + xb); hw_ = max(0.5 * (xb - xa), 1.0)
            for x_ in range(xa, xb + 1):
                ys_ = np.nonzero(dm2[:, x_] > 0.5)[0]
                ys_ = ys_[ys_ < int(cy - 0.8 * R)]
                if ys_.size == 0:
                    continue
                yb_ = int(ys_.max())
                uz = int(round(8.0 * math.sqrt(max(0.0, 1 - ((x_ - xc_) / hw_) ** 2))))
                for k_ in range(1, uz + 1):
                    yy_ = yb_ + k_
                    if yy_ >= H:
                        break
                    kar = 1 - 0.25 * k_ / max(uz, 1)
                    kaynak_s = [yv for yv in range(yb_ - 8, yb_ - 1) if dm2[yv, x_] > 0.8]   # alt satir beyaz diske karisik: ustteki saf dugum pikselleri
                    if not kaynak_s:
                        break
                    dug_rk[yy_, x_] = np.median(sahne_orj[kaynak_s, x_], axis=0) * kar
                    dug_al[yy_, x_] = max(dug_al[yy_, x_], 1.0 if k_ < uz else 0.6)
                if uz and any(dm2[yv, x_] > 0.8 for yv in range(yb_ - 8, yb_ - 1)):
                    for yv in range(yb_ - 2, yb_ + 1):                              # alt 3 satir da saf renge cekilir (soluk cizgi kalmasin)
                        ks = [q for q in range(yb_ - 8, yb_ - 1) if dm2[q, x_] > 0.8 and q < yv]
                        if ks:
                            dug_rk[yv, x_] = np.median(sahne_orj[ks, x_], axis=0); dug_al[yv, x_] = max(dug_al[yv, x_], 1.0)
        dm2 = cv2.GaussianBlur(dug_al.astype(np.float32), (0, 0), 0.6)[..., None]
        out = out * (1 - dm2) + dug_rk * dm2
    # ipin yanindaki ince acik cizgi (sahne kusuru): disk ustunde, ipin iki yanindaki 8 px icinde zeminden parlak pikseller satir zemin medyanina cekilir
    acik_cizgi_px = 0
    ip_s = cv2.dilate(ipm.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    for y_ in range(int(cy - 1.6 * R), int(cy - R)):                      # parmak bolgesine girmez
        xs_ = np.nonzero(ip_s[y_, int(nx - 0.15 * R):int(nx + 0.15 * R)])[0]
        if xs_.size == 0:
            continue
        xl = int(nx - 0.15 * R) + int(xs_.min()); xr = int(nx - 0.15 * R) + int(xs_.max())
        zem = np.median(out[y_, max(0, xl - 70):max(1, xl - 25)], axis=0)
        zl_ = float(zem.mean())
        for x_ in list(range(max(0, xl - 8), xl)) + list(range(xr + 1, min(W, xr + 9))):
            if out[y_, x_].mean() > zl_ + 5 and not ip_s[y_, x_]:
                out[y_, x_] = zem; acik_cizgi_px += 1
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

    # baslik (kupa kalibi; 4:5 bant icinde, ust bosluk)
    F1, F2 = os.environ.get("V_FONT1", ""), os.environ.get("V_FONT2", "")   # sabit yazi tipi dosyalari (bos: Cinzel degisken)
    def font(px, ag):
        yol = (F1 if ag == 650 else F2) or ""
        if yol:
            return ImageFont.truetype(yol, px)
        fo = ImageFont.truetype(FONT, px); fo.set_variation_by_axes([ag]); return fo
    bant_ = tuple(int(v) for v in a.bant.split(",")) if a.bant else BANT
    boy = 185
    while font(boy, 650).getbbox(a.baslik)[2] - font(boy, 650).getbbox(a.baslik)[0] > bant_[1] - bant_[0]:
        boy -= 1
    fa = 110
    while True:
        fs = font(fa, 700); iz = round(fa * float(os.environ.get('V_IZ2', '0.05')))
        if sum(fs.getlength(ch) for ch in a.alt) + iz * (len(a.alt) - 1) <= min(ALT_GEN, bant_[1] - bant_[0]): break
        fa -= 1
    fb = font(boy, 650)
    pass
    s_gen = sum(fs.getlength(ch) for ch in a.alt) + iz * (len(a.alt) - 1)
    y1, y2 = (int(v) for v in a.y.split(","))
    kat = Image.new("L", im.size, 0); d = ImageDraw.Draw(kat)
    # ip basligi ortadan bolmesin: satir, kelime boslugu ipin hizasina gelecek kadar kaydirilir (bant icinde kalirsa)
    ipx = None
    yb0, yb1 = max(0, y1 - boy), min(H, y2 + 20)
    bx = ipm[yb0:yb1, 1200:1800]
    if bx.sum() > 50:
        ipx = 1200 + float(np.median(np.nonzero(bx)[1]))
    # ip kelime boslugundan gecer: satir ipin iki yanina bolunur, bosluk ip genisligi + pay kadar acilir (bant icinde kalmazsa punto kuculur)
    ipw = 0.0
    if ipx is not None:
        sat = bx[bx.shape[0] // 2]
        ipw = float(max(8, sat.sum()))
    def satir_ciz(metin, f_, iz_, y_, anchor_dikey):
        """-> (yerlestirildi_mi, kutu_genisligi). Harfler tek tek, iz_ harf araligi."""
        amp_yol = os.environ.get("V_AMP", "")
        amp_f = ImageFont.truetype(amp_yol, max(8, int(round(f_.size * float(os.environ.get("V_AMP_OLCEK", "0.7")))))) if (amp_yol and f_ is fb) else None
        fch = lambda ch: amp_f if (amp_f is not None and ch == "&") else f_
        gen = [fch(ch).getlength(ch) for ch in metin]
        top = sum(gen) + iz_ * (len(metin) - 1)
        bos = [i for i, ch in enumerate(metin) if ch == " "]
        x0_ = 1500 - top / 2
        bol = None
        if ipx is not None and bos:
            pos_ = [x0_ + sum(gen[:i]) + iz_ * i for i in range(len(metin))]
            i_s = min(bos, key=lambda i: abs(ipx - (pos_[i] + gen[i] / 2)))
            sol = sum(gen[:i_s]) + iz_ * i_s                     # bosluga kadar
            sag = top - sol - gen[i_s] - iz_                     # bosluktan sonra
            g_ = max(gen[i_s] + 2 * iz_, ipw + 2 * max(14, 0.12 * f_.size))
            D_ = (3000 - 2 * ipx + sol - sag)                       # gR - gL farki: merkez 1500 icin
            D_ = 0.0                                                # v7 incelemesi: ip boslugun tam ortasinda (asimetrik bosluk dengesiz okundu)
            gL = g_ / 2 - min(D_, 0) ; gR = g_ / 2 + max(D_, 0)
            xs = ipx - gL - sol; xe = ipx + gR + sag
            if xs >= bant_[0] and xe <= bant_[1] and abs((xs + xe) / 2 - 1500) <= float(os.environ.get("V_MERKEZ", "260")):  # baslik merkezi 1500 +- V_MERKEZ px
                bol = (i_s, xs, ipx + gR)
        if ipx is not None and bos and bol is None:
            return False, top
        x_ = x0_ if bol is None else bol[1]
        for i, ch in enumerate(metin):
            if bol is not None and i == bol[0]:
                x_ = bol[2]; continue
            if bol is not None and i > bol[0] and False:
                pass
            d.text((x_, y_), ch, font=fch(ch), fill=255, anchor="l" + anchor_dikey)
            x_ += gen[i] + iz_
        return True, top
    boy0 = boy
    while True:
        ok_b, _ = satir_ciz(a.baslik, fb, 0, y1, "s") if boy <= float(os.environ.get("V_MIN_OLCEK", "0.85")) * boy0 else (None, None)
        if ok_b is None:
            kat_t = Image.new("L", im.size, 0); dd_ = ImageDraw.Draw(kat_t)
            d_bak = d; d = dd_
            ok_b, _ = satir_ciz(a.baslik, fb, 0, y1, "s")
            d = d_bak
            if ok_b:
                satir_ciz(a.baslik, fb, 0, y1, "s"); break
            boy -= 2; fb = font(boy, 650); continue
        if not ok_b:
            # ip kelime boslugundan gecemiyor: harf kesilir. 6 Kas inceleme KRITIK: sessiz basma yok, DUR
            uyari.append("IP_HARF_KESIYOR: baslikta ipin gececegi bosluk bulunamadi")
            if os.environ.get("V_KESIM_SERBEST", "0") != "1":
                raise SystemExit(f"DUR: ip baslikta harf kesiyor ({a.baslik!r}, punto {boy}); V_MIN_OLCEK / V_MERKEZ ile cozum secilmeli")
            ipx_y = ipx; ipx = None; satir_ciz(a.baslik, fb, 0, y1, "s"); ipx = ipx_y
        break
    fa0 = fa
    while True:
        kat_t = Image.new("L", im.size, 0); d_bak = d; d = ImageDraw.Draw(kat_t)
        ok_a, _ = satir_ciz(a.alt, fs, iz, y2, "s")
        d = d_bak
        if ok_a:
            satir_ciz(a.alt, fs, iz, y2, "s"); break
        if fa <= 0.8 * fa0:
            ipx_y = ipx; ipx = None; satir_ciz(a.alt, fs, iz, y2, "s"); ipx = ipx_y; break
        fa -= 2; fs = font(fa, 700); iz = round(fa * float(os.environ.get('V_IZ2', '0.05')))
    kb_, ka_ = boy, fa
    if a.hale != "yok":
        hr_ = np.asarray(kat.filter(ImageFilter.GaussianBlur(24)), np.float32) / 255
        hr_ = np.clip(hr_ * 2.2, 0, 1) * 0.78
        hc = (250, 244, 236) if a.hale == "acik" else (30, 20, 16)
        im = Image.composite(Image.new("RGB", im.size, hc), im, Image.fromarray((hr_ * 255).astype(np.uint8)))
    if a.baslik_renk:
        RENK = tuple(int(v) for v in a.baslik_renk.split(","))
    elif a.renk == "krem":
        RENK = (252, 248, 240)
        g = np.zeros((H, W), np.float32)
        for blur, o, ddx, ddy in ((22, 0.35, 0, 2), (7, 0.55, 5, 6)):
            gg = np.asarray(kat.filter(ImageFilter.GaussianBlur(blur)), np.float32) / 255 * o * 1.6
            g = 1 - (1 - g) * (1 - np.clip(np.roll(gg, (ddy, ddx), (0, 1)), 0, 1))
        im = Image.composite(Image.new("RGB", im.size, (35, 22, 10)), im, Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8)))
    else:
        RENK = (43, 34, 32)
    hale = float(os.environ.get("V_HALE", "0"))                             # koyu yazi icin acik hale (0 = yok)
    if hale > 0:
        hh = np.asarray(kat.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(float(os.environ.get("V_HALE_BLUR", "9")))), np.float32) / 255
        im = Image.composite(Image.new("RGB", im.size, (255, 253, 248)), im, Image.fromarray((np.clip(hh * hale, 0, 1) * 255).astype(np.uint8)))
    if a.golge:
        # golge: yalniz harflerin sag altinda, dar ve yumusak; harf disinda zemin rengi korunur (genis hale yok)
        gk = float(os.environ.get("V_GOLGE", "1"))                          # golge gucu carpani (1 = onayli Ruby)
        gg = np.asarray(kat.filter(ImageFilter.GaussianBlur(float(os.environ.get("V_GOLGE_BLUR", 5 * (1 + 0.5 * (gk - 1)))))), np.float32) / 255
        gg = np.roll(gg, (int(round(8 * (1 + 0.4 * (gk - 1)))), -int(round(5 * (1 + 0.4 * (gk - 1))))), (0, 1)) * min(0.95, 0.60 * gk)
        gg2 = np.asarray(kat.filter(ImageFilter.GaussianBlur(2)), np.float32) / 255
        gg2 = np.roll(gg2, (3, -2), (0, 1)) * min(0.9, 0.40 * gk)
        g_ = 1 - (1 - np.clip(gg, 0, 1)) * (1 - np.clip(gg2, 0, 1))
        im = Image.composite(Image.new("RGB", im.size, (28, 16, 12)), im, Image.fromarray((np.clip(g_, 0, 1) * 255).astype(np.uint8)))
    im = Image.composite(Image.new("RGB", im.size, RENK), im, kat)
    im.save(a.cikti, quality=95, subsampling=0)                            # 4:4:4 (ince altin renk alt orneklemesiyle sonmesin)
    kb = kat.getbbox()
    rap = {"sahne": a.sahne, "baski": a.baski, "disk": {"cx": round(cx, 1), "cy": round(cy, 1), "eksen_a": round(ea, 1), "eksen_b": round(eb, 1),
           "aci": round(aci, 1), "R": round(R, 1), "eksen_orani": round(oran, 4), "doluluk": round(dol, 4), "esik": esik,
           "disk_4x5_icinde": bool(cx - R >= 600 and cx + R <= 2400), "disk_1x1_icinde": bool(cx - R >= 375 and cx + R <= 2625)},
           "eski_delik": {"x": round(float(ox), 1), "y": round(float(oy), 1), "yukari_R": round(float((cy - oy) / R), 3), "r": round(rh, 1)},
           "yeni_delik": {"x": round(float(nx), 1), "y": round(float(ny), 1), "yukari_R": round(float((cy - ny) / R), 3)},
           "ip_cizildi": ip_eklendi, "ip_kalinlik_px": round(kal, 1), "delik_r_px": round(hr, 1),
           "kapi_a_bagimsiz_yol_ort_fark": round(kapi_a_ort, 4), "hale_buyutme_px": buyut, "hale_acili_duzeltilen_px": hale_px, "isik_yonu": [round(lx, 3), round(ly, 3)], "uyari": uyari, "kapi_a_8bit_max_fark": kapi_a_u8, "kapi_a_bagimsiz_yol_max_fark": kapi_a, "seffaf_baski": seffaf, "baslik_boy": boy, "baslik_kutu": kb,
           "baslik_4x5_icinde": bool(kb[0] >= 600 and kb[2] <= 2400), "baslik_2x3_icinde": bool(kb[0] >= 750 and kb[2] <= 2250),
           "disk_2x3_icinde": bool(cx - R >= 750 and cx + R <= 2250), "baslik_renk": a.baslik_renk or a.renk, "hale": a.hale,
           "zoom": a.zoom, "sahne_penceresi_ham_px": pencere, "sahne_buyutme_kat": buyutme, "gren_std": round(gstd, 2), "siyah_kaldirma": round(kaldir, 1), "kenar_aktarim": kenar_aktarim, "yan_duvar": yan_duvar, "golge": a.golge, "dondur_der": round(dondur_der, 2), "ip_x_baslik": ipx, "dugum_geri_px": dugum_px, "acik_cizgi_px": acik_cizgi_px, "baslik_kaydirma": [round(kb_, 1), round(ka_, 1)]}
    json.dump(rap, open(a.cikti + ".json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rap, ensure_ascii=False))


if __name__ == "__main__":
    main()
