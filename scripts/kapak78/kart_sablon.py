#!/usr/bin/env python3
"""Bilgi karti SABLONLARI (Merkez 28 Eki, Serdar onayi; olcu kaynagi dal kart-sablon-ref-20261028 ref/kart_sablon_20261028/mock).
Stil yd_kart_ornek.py SADE (zemin #F5F0E7, tek murekkep #2B2220, Cormorant 170 baslik, Manrope 68 etiket / 64 metin / 58 not, 3000x2250).
Ayni kart turu uc kategoride (wall art, kupa, YD) ayni fonksiyonla cizilir:
  sembol_kart  : wa_s1 duzeni; iki burc + ad, iki kubik Bezier baglac (baglac2.py: genislik 9*sin(pi t)^0.8, 4x ornekleme), ortak sembol.
  yan_kart     : solda gorsel (1140 x icerik alani; birden fazla gorsel ust uste 30 px), 150 px bosluk, sagda etiket + metin bloklari
                 (yd_kart_ornek.adimlar; dikeyde icerik alaninda ortali). Kisisellestirme: sutun 1290 (sar_d). Surec: numara sutunu 150,
                 sutun min(1500, W - 2 KENAR - gorsel - 150). Yazi sigmazsa gorsel kuculur (1.0 / 0.92 / 0.85 / 0.78 / 0.72), yazi kuculmez.
  tablo_kart   : etiket solda, metin sagda (140 px, sutun 1500), satirlar 120 px, ayni satirda iki bilgi 0.6 x 64 px; tablo ortali.
  izgara_kart  : satirlar ortali (3 + 2 / 4 + 4), ayni yukseklik / olcek, etiket gorselin altinda ortali.
Gruplar (gorsel + 150 + en genis satir) yatayda ortali. Alt not tek satir NOT_Y'de ortali.
YERLESIM KAPILARI (yerlesim hesabindan, yapistirma sonrasi yuvarlanmis tam sayi kutularla; piksel taramasi degil):
  ortalama   : grup kutusunun sol ve sag boslugu farki <= 2 px
  ayri blok  : farkli bloklar (iki bilgi blogu, yazi-gorsel, yazi-baslik, yazi-alt not, izgara hucreleri ve komsu etiketler) arasi >= 40 px;
               blok ici (etiket-metin, numara-etiket, ust uste iki kupa) haric
  baglac     : birlesme noktasinin 40 px yakininda iki egri disinda murekkep pikseli yok (ok basi yok)
Biri tutmazsa kart yazilmaz (SystemExit "DUR: ...").
CLI (is akisi): kart_sablon.py kontak <out>   | kart_sablon.py kapak <KAPAK43 dir> <eski KAPAK43 dir>"""
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yd_kart_ornek as K  # noqa: E402

W, H = K.W, K.H
ARA = 150                                   # gorsel ile yazi arasi
GW = 1140                                   # gorsel genislik siniri
GH = K.ALAN[1] - K.ALAN[0]                  # gorsel yukseklik siniri: icerik alaninin tamami
GEN_KISISEL = 1290                          # kisisellestirme yazi sutunu (sar_d)
NO_G = 150                                  # "01" numara sutunu
OLCEKLER = (1.0, 0.92, 0.85, 0.78, 0.72)
AYRI = 40                                   # ayri bloklar arasi en az
ORTA_TOL = 2                                # grup ortalama toleransi
TABLO_GEN, TABLO_ET, TABLO_SATIR = 1500, 140, 120
ZEMIN_FARK = 3                              # kupa kirpimi: zeminden RGB farki > 3 olan piksellerin kutusu + 4 px
KUPA_PAY = 4


# ---------------------------------------------------------------- kutu kaydi
class Kayit:
    """kartin bloklari: ad -> [kutu]; yazilar K.yaz ile (K.BLOK[0] adiyla) K.KUTULAR'a duser"""
    def __init__(self):
        self.n0 = len(K.KUTULAR); self.gorsel = []; self.gruplar = []; self.simetrik = []

    def blok(self, ad):
        K.BLOK[0] = ad

    def ekle(self, ad, kutu):
        self.gorsel.append((ad, [int(round(v)) for v in kutu]))

    def bloklar(self):
        b = {}
        for ad, _, k in K.KUTULAR[self.n0:]:
            b.setdefault(ad, []).append(k)
        for ad, k in self.gorsel:
            b.setdefault(ad, []).append(k)
        return b


def birlesim(kutular):
    return [min(k[0] for k in kutular), min(k[1] for k in kutular), max(k[2] for k in kutular), max(k[3] for k in kutular)]


def ayrim(a, b):
    """iki kutu arasi bosluk (Chebyshev): ust uste binerse negatif"""
    dx = max(a[0] - b[2], b[0] - a[2]); dy = max(a[1] - b[3], b[1] - a[3])
    return max(dx, dy)


def yerlesim_kapisi(kay, ad):
    """-> olcu dict; tutmazsa SystemExit"""
    b = kay.bloklar(); adlar = sorted(b); en_az = None; hata = []
    for i, x in enumerate(adlar):
        for y in adlar[i + 1:]:
            m = min(ayrim(p, q) for p in b[x] for q in b[y])
            if en_az is None or m < en_az[0]:
                en_az = (m, x, y)
            if m < AYRI:
                hata.append(f"{x} - {y} {m} px")
    orta = []
    for g in kay.gruplar:
        k = birlesim([q for n in g for q in b[n]])
        sol, sag = k[0], W - k[2]
        orta.append(dict(grup=g if len(g) < 6 else f"{len(g)} blok", kutu=k, sol=sol, sag=sag))
        if abs(sol - sag) > ORTA_TOL:
            hata.append(f"ortalama {g}: sol {sol} sag {sag}")
    for x, y in kay.simetrik:                       # iki burc (sembol karti): merkezlerin ortasi sayfa ortasinda
        kx, ky = birlesim(b[x]), birlesim(b[y]); m = ((kx[0] + kx[2]) / 2 + (ky[0] + ky[2]) / 2) / 2
        orta.append(dict(simetrik=[x, y], merkez_ort=m))
        if abs(m - W / 2) > ORTA_TOL / 2:
            hata.append(f"simetri {x} / {y}: merkez ortalamasi {m}")
    if hata:
        raise SystemExit(f"DUR: {ad} yerlesim kapisi: {'; '.join(hata)}")
    return dict(en_kucuk_ayrim=dict(px=en_az[0], bloklar=en_az[1:]) if en_az else None, ortalama=orta, blok_sayisi=len(adlar))


# ---------------------------------------------------------------- gorsel yardimcilari
def maske(yol, h):
    """kupa_uretim sembol maskesi (RGBA, alfa = altin) -> murekkep renginde RGBA, yukseklik h (keskin kenar yd_kart_ornek.sembol_al ile ayni)"""
    a = Image.open(yol).convert("RGBA").getchannel("A")
    a = a.crop(a.getbbox()); a = a.resize((round(a.width * h / a.height), h), Image.LANCZOS)
    al = np.clip((np.asarray(a).astype(np.float32) / 255 - 0.2) / 0.6, 0, 1)
    rgba = np.zeros(al.shape + (4,), np.uint8); rgba[..., :3] = K.rgb(K.MUREKKEP); rgba[..., 3] = (al * 255).astype(np.uint8)
    return Image.fromarray(rgba)


def kupa_kirp(z):
    """kupa sahnesi (zemin #F5F0E7'ye esitlenmis) -> zeminden RGB farki > 3 piksellerin en kucuk kutusu + 4 px (kupa + golge)"""
    a = np.asarray(z.convert("RGB")).astype(np.int16)
    ys, xs = np.nonzero(np.abs(a - np.int16(K.rgb(K.ZEMIN))).max(axis=2) > ZEMIN_FARK)
    k = [max(0, int(xs.min()) - KUPA_PAY), max(0, int(ys.min()) - KUPA_PAY), min(a.shape[1], int(xs.max()) + KUPA_PAY + 1),
         min(a.shape[0], int(ys.max()) + KUPA_PAY + 1)]
    return z.convert("RGB").crop(k), k


def kucult(p, w, h):
    """yalniz kucultme (buyutme yok)"""
    if w > p.width or h > p.height:
        raise SystemExit(f"DUR: gorsel buyutulmeden sigmali ({p.size} -> {w}x{h})")
    return p.resize((w, h), Image.LANCZOS)


# ---------------------------------------------------------------- baglac (baglac2.py)
def _bez(P, t):
    u = 1 - t
    return np.stack([u ** 3 * P[0][0] + 3 * u * u * t * P[1][0] + 3 * u * t * t * P[2][0] + t ** 3 * P[3][0],
                     u ** 3 * P[0][1] + 3 * u * u * t * P[1][1] + 3 * u * t * t * P[2][1] + t ** 3 * P[3][1]], 1)


def baglac(im, xs, y0, uy, wmax=9.0, S=4, n=600):
    """iki kubik Bezier: P0 (x0, y0), P1 (x0, y0 + 120), P2 (W/2 + 0.08 (x0 - W/2), y0 + 55), P3 (W/2, uy); genislik
    wmax * sin(pi t)^0.8 (iki ucta sifir: uc keskin uc); 4x ornekli cokgen, LANCZOS, murekkep rengiyle -> (alfa 0-1, uc noktalar)"""
    lay = Image.new("L", (W * S, H * S), 0); ld = ImageDraw.Draw(lay)
    cx = W / 2; t = np.linspace(0, 1, n + 1)
    for x0 in xs:
        P = [(x0, y0), (x0, y0 + 120), (cx + (x0 - cx) * 0.08, y0 + 55), (cx, uy)]
        pts = _bez(P, t)
        tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1)[:, None]
        nor = np.stack([-tan[:, 1], tan[:, 0]], 1)
        w = wmax * np.sin(np.pi * t) ** 0.8
        L = pts + nor * w[:, None] / 2; R = pts - nor * w[:, None] / 2
        ld.polygon([tuple(p * S) for p in L] + [tuple(p * S) for p in R[::-1]], fill=255)
    lay = lay.resize((W, H), Image.LANCZOS)
    im.paste(Image.new("RGB", (W, H), K.MUREKKEP), (0, 0), lay)
    return np.asarray(lay).astype(np.float32) / 255, [(x, y0) for x in xs] + [(cx, uy)]


def baglac_kapisi(im, alfa, uc, r=40):
    """birlesme noktasinin r px yakininda iki egrinin (alfa > 0, 2 px genisletilmis) disinda murekkep (zeminden t > 0.03) yok"""
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    z, m = np.float32(K.rgb(K.ZEMIN)), np.float32(K.rgb(K.MUREKKEP)); v = m - z
    t = np.clip(((a - z) @ v) / float(v @ v), 0, 1)
    egri = K._kutu_toplam(alfa > 0.002, 2) > 0
    yy, xx = np.mgrid[0:H, 0:W]
    yakin = (xx - uc[0]) ** 2 + (yy - uc[1]) ** 2 <= r * r
    dis = int(((t > 0.03) & yakin & ~egri).sum())
    if dis:
        raise SystemExit(f"DUR: baglac kapisi: birlesme noktasi {r} px yakininda egri disi murekkep {dis} px")
    return dict(birlesme=[round(uc[0]), round(uc[1])], yaricap=r, egri_disi_px=0)


# ---------------------------------------------------------------- 1) sembol karti (wa_s1 duzeni)
def sembol_kart(a, b, sem, alt):
    """sem: dizin (sol.png, sag.png, ana.png; kupa_uretim/sembol/<CIFT>). -> im, olcu, foto kutulari, renk muafiyeti (uc noktalar)"""
    kay = Kayit(); im = K.tuval(); d = ImageDraw.Draw(im)
    kay.blok("baslik"); K.baslik(d, "Two Signs, One Shared Symbol")
    kay.blok("alt_baslik"); K.yaz(d, K.METIN, [f"{a} and {b} joined in an original AstroLoveArt design"], W / 2,
                                  K.BASLIK_Y + K.BASLIK["boy"] + 50, "center", W - 2 * K.KENAR)
    gh, cxs, gy = 300, (W / 2 - 560, W / 2 + 560), 680
    for f, cx, ad, bl in ((sem / "sol.png", cxs[0], a, "burc_a"), (sem / "sag.png", cxs[1], b, "burc_b")):
        g = maske(f, gh); x = round(cx - g.width / 2); im.paste(g, (x, gy), g)
        kay.ekle(bl, [x, gy, x + g.width, gy + g.height])
        kay.blok(bl); K.yaz(d, K.ETIKET, [ad], cx, gy + gh + 50, "center", 0.3 * W)
    ty = gy + gh + 50 + K.ETIKET["boy"] + 60; uy = ty + 170          # eski duz cizgi baslangici ve ok ucu (P0 y = ty - 13 = 1145, uc 1328)
    s = maske(sem / "ana.png", round(K.NOT_Y - 80 - (uy + 50)))
    sx = round(W / 2 - s.width / 2); im.paste(s, (sx, round(uy + 50)), s)
    kay.ekle("ortak_sembol", [sx, round(uy + 50), sx + s.width, round(uy + 50) + s.height])
    alfa, uc = baglac(im, cxs, ty - 13, uy)
    ys, xs_ = np.nonzero(alfa > 0.002)
    kay.ekle("baglac", [int(xs_.min()), int(ys.min()), int(xs_.max()) + 1, int(ys.max()) + 1])
    d = ImageDraw.Draw(im)
    kay.blok("not"); K.yaz(d, K.METIN, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    kay.gruplar = [["baglac"], ["ortak_sembol"]]; kay.simetrik = [("burc_a", "burc_b")]   # burc glifleri farkli genislikte, merkezleri W/2 +- 560
    o = dict(glif_h=gh, sembol=[s.width, s.height], baglac=dict(P0_y=ty - 13, uc_y=uy, x0=list(cxs), genislik=9))
    o["baglac_kapisi"] = baglac_kapisi(im, alfa, uc[-1])
    o["yerlesim"] = yerlesim_kapisi(kay, "sembol")
    return im, o, [], uc


# ---------------------------------------------------------------- 2) yan kart (kisisellestirme / surec)
def _geri_al(n):
    del K.YAZILAR[n[0]:]; del K.SATIRLAR[n[1]:]; del K.KUTULAR[n[2]:]


def yan_kart(baslik, gorseller, bloklar, alt, surec=False, ara_p=30):
    """gorseller: [PIL] (ust uste ara_p px); bloklar: [(numara|None, [etiket satirlari], metin)]"""
    son = None
    for k in OLCEKLER:
        n = (len(K.YAZILAR), len(K.SATIRLAR), len(K.KUTULAR))
        try:
            return _yan_kart(baslik, gorseller, bloklar, alt, surec, ara_p, k)
        except SystemExit as e:
            if "sigmiyor" not in str(e) and "kenar" not in str(e):
                raise
            son = e; _geri_al(n)
    raise SystemExit(f"DUR: {baslik}: yazi en kucuk gorsel olceginde (0.72) de sigmadi ({son})")


def _yan_kart(baslik, gorseller, bloklar, alt, surec, ara_p, k):
    kay = Kayit(); no_g = NO_G if any(x for x, _, _ in bloklar) else 0
    hh = (GH - ara_p * (len(gorseller) - 1)) / len(gorseller)
    olc = [min(GW / p.width, hh / p.height) * k for p in gorseller]
    boy = [(round(p.width * s), round(p.height * s)) for p, s in zip(gorseller, olc)]
    gw = max(w for w, _ in boy)
    gen = min(1500, W - 2 * K.KENAR - gw - ARA) if surec else GEN_KISISEL
    hazir = [(x, e, K.sar_d(K.METIN, t, gen - no_g)) for x, e, t in bloklar]
    tw = no_g + max(max(K.genislik(K.ETIKET, x) for x in e) for _, e, _ in hazir)
    tw = max(tw, no_g + max(K.genislik(K.METIN, x) for _, _, t in hazir for x in t))
    x0 = round((W - (gw + ARA + tw)) / 2)
    if x0 < K.KENAR - 0.5:
        raise SystemExit(f"DUR: kenar: grup {gw + ARA + tw:.0f} px, sol bosluk {x0} < {K.KENAR:.0f}")
    im = K.tuval()
    top = sum(h for _, h in boy) + ara_p * (len(boy) - 1)
    y = round((K.ALAN[0] + K.ALAN[1]) / 2 - top / 2); kut = []
    for p, (w, h) in zip(gorseller, boy):
        x = x0 + round((gw - w) / 2)
        im.paste(kucult(p, w, h), (x, y)); kut.append([x, y, x + w, y + h]); kay.ekle("gorsel", kut[-1]); y += h + ara_p
    d = ImageDraw.Draw(im)
    kay.blok("baslik"); K.baslik(d, baslik)
    _adimlar(d, kay, x0 + gw + ARA, gen, bloklar, no_g)
    kay.blok("not"); K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    kay.gruplar = [["gorsel"] + [f"blok{i}" for i in range(len(bloklar))]]
    o = dict(olcek=k, gorsel=[list(b_) for b_ in boy], yazi_sutunu=gen, metin_sutunu=gen - no_g, numara_sutunu=no_g,
             grup_x0=x0, grup_w=round(gw + ARA + tw), satirlar={str(i): t for i, (_, _, t) in enumerate(hazir)})
    o["yerlesim"] = yerlesim_kapisi(kay, baslik)
    return im, o, kut


def _adimlar(d, kay, x0, gen, bloklar, no_g):
    """yd_kart_ornek.adimlar ile ayni hesap; her bilgi blogu ayri blok adiyla (blok0, blok1, ...)"""
    hazir = [(n, e, K.sar_d(K.METIN, t, gen - no_g)) for n, e, t in bloklar]
    ara_et = 0.28 * K.ETIKET["boy"]
    yuk = [K.blok_yuk(K.ETIKET, len(e)) + ara_et + K.blok_yuk(K.METIN, len(t)) for _, e, t in hazir]
    bos = min(140, (K.ALAN[1] - K.ALAN[0] - sum(yuk)) / max(1, len(yuk) - 1))
    if bos < 60:
        raise SystemExit(f"DUR: adimlar sigmiyor (aralik {bos:.0f} px)")
    y = (K.ALAN[0] + K.ALAN[1]) / 2 - (sum(yuk) + bos * (len(yuk) - 1)) / 2
    for i, ((n, e, t), h) in enumerate(zip(hazir, yuk)):
        kay.blok(f"blok{i}")
        if n:
            K.yaz(d, K.ETIKET, [n], x0, y, gen=no_g)
        yy = y + K.yaz(d, K.ETIKET, e, x0 + no_g, y, gen=gen - no_g) + ara_et
        K.yaz(d, K.METIN, t, x0 + no_g, yy, gen=gen - no_g)
        y += h + bos


# ---------------------------------------------------------------- 3) tablo karti (format)
def tablo_kart(baslik, satirlar, alt):
    """satirlar: [(etiket, [bilgi, ...])]"""
    kay = Kayit(); im = K.tuval(); d = ImageDraw.Draw(im)
    kay.blok("baslik"); K.baslik(d, baslik)
    ew = max(K.genislik(K.ETIKET, e) for e, _ in satirlar)
    hz = [(e, [K.sar_d(K.METIN, p, TABLO_GEN) for p in ps]) for e, ps in satirlar]
    tw = max(K.genislik(K.METIN, x) for _, ps in hz for p in ps for x in p)
    par = 0.6 * K.METIN["boy"]
    yk = [max(K.ETIKET["boy"], sum(K.blok_yuk(K.METIN, len(p)) for p in ps) + par * (len(ps) - 1)) for _, ps in hz]
    top = sum(yk) + TABLO_SATIR * (len(yk) - 1)
    x0 = round((W - (ew + TABLO_ET + tw)) / 2); y = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
    for i, ((e, ps), h) in enumerate(zip(hz, yk)):
        kay.blok(f"satir{i}")
        K.yaz(d, K.ETIKET, [e], x0, y + (K.METIN["boy"] - K.ETIKET["boy"]) / 2, gen=ew)   # etiket metnin ilk satiriyla hizali
        yy = y
        for p in ps:
            yy += K.yaz(d, K.METIN, p, x0 + ew + TABLO_ET, yy, gen=TABLO_GEN) + par
        y += h + TABLO_SATIR
    kay.blok("not"); K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    kay.gruplar = [[f"satir{i}" for i in range(len(hz))]]
    o = dict(etiket_w=round(ew), metin_w=round(tw), satirlar={e: ps for e, ps in hz})
    o["yerlesim"] = yerlesim_kapisi(kay, baslik)
    return im, o, []


# ---------------------------------------------------------------- 4) izgara karti (genel bakis)
def izgara_kart(baslik, ogeler, alt, sira, yerler, et_ara, sat_ara, olcek_fn):
    """ogeler: [(ad, PIL)]; sira: satir basina oge (3, 2); yerler(r, j, n) -> hucre merkezi x; olcek_fn(ogeler) -> [(w, h)] (ayni
    yukseklik ya da ayni olcek); satir yuksekligi = en yuksek gorsel; gorseller satirda ALT kenara hizali, etiket et_ara px altta ortali"""
    kay = Kayit(); boy = olcek_fn(ogeler)
    gh = max(h for _, h in boy)
    sat_h = gh + et_ara + K.ETIKET["boy"]; top = len(sira) * sat_h + (len(sira) - 1) * sat_ara
    y0 = (K.ALAN[0] + K.ALAN[1]) / 2 - top / 2
    im = K.tuval(); kut = []; i = 0; yer = []
    for r, n in enumerate(sira):
        sat = [(yerler(r, j, n), i + j) for j in range(n)]
        # satir grubu (gorsel + etiket kutulari) sayfada ortali: farkli genislikte gorsellerde merkez araligi korunur, satir kaydirilir
        yar = [max(boy[k][0], K.genislik(K.ETIKET, ogeler[k][0])) / 2 for _, k in sat]
        dx = (W - min(c - h for (c, _), h in zip(sat, yar)) - max(c + h for (c, _), h in zip(sat, yar))) / 2
        yer += [(c + dx, y0 + r * (sat_h + sat_ara), r) for c, _ in sat]; i += n
    for i, ((ad, g), (w, h), (cx, y, r)) in enumerate(zip(ogeler, boy, yer)):
        x = round(cx - w / 2); yy = round(y + gh - h)
        im.paste(kucult(g, w, h), (x, yy)); kut.append([x, yy, x + w, yy + h]); kay.ekle(f"hucre{i}", kut[-1])
    d = ImageDraw.Draw(im)
    kay.blok("baslik"); K.baslik(d, baslik)
    for i, ((ad, _), (cx, y, r)) in enumerate(zip(ogeler, yer)):
        kay.blok(f"hucre{i}"); K.yaz(d, K.ETIKET, [ad], cx, y + gh + et_ara, "center", W - 2 * K.KENAR)
    kay.blok("not"); K.yaz(d, K.NOT, [alt], W / 2, K.NOT_Y, "center", W - 2 * K.KENAR)
    s0 = 0; kay.gruplar = []
    for n in sira:
        kay.gruplar.append([f"hucre{i}" for i in range(s0, s0 + n)]); s0 += n
    o = dict(gorsel=[list(b_) for b_ in boy], satir_yuksekligi=gh)
    o["yerlesim"] = yerlesim_kapisi(kay, baslik)
    return im, o, kut


def secim_kart(baslik, ogeler, alt):
    """WA renk / YD stil secimi (mock_secim.py): 3 + 2, merkezler 760 px, etiket 45 px alt, satirlar 90 px; poster yuksekligi iki satira
    sigan en buyuk deger, hepsi ayni yukseklikte, yalniz kucultme"""
    sira = (3, 2); ET, SAT, ARALIK = 45, 90, 760
    ph = int((GH - len(sira) * (ET + K.ETIKET["boy"]) - (len(sira) - 1) * SAT) // len(sira))
    return izgara_kart(baslik, ogeler, alt, sira, lambda r, j, n: W / 2 + (j - (n - 1) / 2) * ARALIK, ET, SAT,
                       lambda og: [(round(g.width * ph / g.height), ph) for _, g in og])


def kontak_sayfa(satirlar, basliklar, kb_sinir=300):
    """satirlar: [[(ad, PIL)]] (galeri sirasi); -> (JPEG baytlari, kalite)"""
    tw, th, et = 420, 315, 30
    n = max(len(s) for s in satirlar)
    t = Image.new("RGB", (n * (tw + 8) + 160, len(satirlar) * (th + et + 8)), "white"); d = ImageDraw.Draw(t)
    for r, (sat, bas) in enumerate(zip(satirlar, basliklar)):
        y = r * (th + et + 8)
        d.text((6, y + th // 2), bas, fill=(0, 0, 0))
        for j, (ad, im) in enumerate(sat):
            x = 160 + j * (tw + 8)
            t.paste(im.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
            d.text((x + 2, y + th + 6), f"{j + 1}  {ad}"[:60], fill=(0, 0, 0))
    for q in (85, 80, 75, 70, 65):
        b = io.BytesIO(); t.save(b, "JPEG", quality=q)
        if b.tell() < kb_sinir * 1024:
            return b.getvalue(), q
    raise SystemExit(f"DUR: KONTAK {b.tell() / 1024:.0f} KB ({kb_sinir} KB alti beklenir)")


# ---------------------------------------------------------------- CLI: kontak (galeri sirasi) ve kupa kapak kontrolleri
def kontak_cli(out):
    out = Path(out); c = json.loads((out / "KART_OZET_WA_KUPA.json").read_text(encoding="utf-8"))["cift"]
    k43 = out / "KAPAK43"
    wa = [f"WA_{c}_S1_SEMBOL", f"WA_{c}_S2_KISISEL", "WA_ORTAK_S3_FORMAT", f"WA_{c}_S4_SUREC", f"WA_{c}_S5_GENEL"]
    ku = ["KAPAK43/KUPA_KAPAK43_01_orange", f"KUPA_{c}_K02_SEMBOL", f"KUPA_{c}_K03_KISISEL", f"KUPA_{c}_K05_BOYUT", f"KUPA_{c}_K07_SUREC",
          f"KUPA_{c}_K04_STIL", "KAPAK43/KUPA_KAPAK43_08_fig"]
    yd = [f"{c}_Y02", f"{c}_Y03", "ORTAK_Y04", f"{c}_Y05", f"YD_{c}_GENEL"]
    sat = [[(Path(n).name, Image.open(out / f"{n}.jpg")) for n in g] for g in (wa, ku, yd)]
    b, q = kontak_sayfa(sat, ["WALL ART", "KUPA", "YD"])
    (out / "KONTAK_KART_SABLON.jpg").write_bytes(b)
    print(f"KONTAK_KART_SABLON.jpg {len(b) / 1024:.0f} KB q{q} ({sum(len(s) for s in sat)} gorsel, galeri sirasi)")
    assert k43.exists()


def kenar_seridi(a, esik=6):
    """kenardan iceri tek renk (satir / sutun icinde kanal farki <= esik) ardisik satir / sutun sayisi: ust, alt, sol, sag"""
    def say(dizi):
        n = 0
        for s in dizi:
            if (np.ptp(s, axis=0) <= esik).all():
                n += 1
            else:
                break
        return n
    return dict(ust=say(a), alt=say(a[::-1]), sol=say(a.transpose(1, 0, 2)), sag=say(a.transpose(1, 0, 2)[::-1]))


def kapak_cli(d, eski):
    d, eski = Path(d), Path(eski); R = {}
    for p in sorted(d.glob("KUPA_KAPAK43_*.jpg")):
        im = Image.open(p).convert("RGB"); a = np.asarray(im).astype(np.int16)
        ks = kenar_seridi(a); beyaz = {k: int((a[s].min(axis=-1) > 250).all(axis=-1).sum()) for k, s in
                                       (("ust", np.s_[:4]), ("alt", np.s_[-4:]))}
        r = dict(boyut=list(im.size), kenar_tek_renk_seridi=ks, kenar_beyaz_satir=beyaz,
                 gecti=im.size == (3000, 2250) and not any(ks.values()) and not any(beyaz.values()))
        st = p.stem.split("_")[-1]
        im.crop((600, 0, 2400, 2250)).resize((720, 900), Image.LANCZOS).save(d / f"ONIZLEME_{st}_arama_4x5.jpg", quality=85)
        im.crop((375, 0, 2625, 2250)).resize((900, 900), Image.LANCZOS).save(d / f"ONIZLEME_{st}_magaza_1x1.jpg", quality=85)
        im.crop((750, 0, 2250, 1500)).save(d / f"KESIT_{st}_baslik_isim_1e1.jpg", quality=92)   # %100 kesit (yumusaklik)
        e = eski / p.name
        if e.exists():
            b_ = np.asarray(Image.open(e).convert("RGB")).astype(np.int16)
            if b_.shape == a.shape:
                f = np.abs(a - b_)
                r["eski_fark"] = dict(ort=round(float(f.mean()), 3), max=int(f.max()), p99=int(np.percentile(f.max(axis=2), 99)),
                                      kaynak="TEMP/WA_KUPA_KART_ORNEK/20261027_192528/20261028_065730/KAPAK43")
        else:
            r["eski_fark"] = "eski dosya yok"
        R[p.name] = r
        if not r["gecti"]:
            raise SystemExit(f"DUR: kapak kontrolu {p.name} {r}")
    (d / "KAPAK43_KONTROL.json").write_text(json.dumps(R, indent=1, ensure_ascii=False))
    print(json.dumps(R, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "kontak":
        kontak_cli(sys.argv[2])
    elif sys.argv[1] == "kapak":
        kapak_cli(sys.argv[2], sys.argv[3])
    else:
        raise SystemExit(__doc__)
