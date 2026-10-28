#!/usr/bin/env python3
"""Poster ilan videosu v6 (Serdar 19 Eki, v5'ten): toz miktari ve murekkep gecisi kupa V6 videosuna (video6b, N 10400,
sigma 0.45) gore ayarlanir; gerisi v5 ile ayni (altin toz, sigma 0.45, zamanlama, silinme, yollar, mesaj, 6 sn, 1440x1080).
 - parcacik sayisi: ortam V6_N (v6_kalibre.py, sembol alanina gore toz yogunlugu kupa ile ayni olacak sekilde hesaplar)
 - murekkep: piksel basina min(c(t), F) (F = yerel toz birikimi; murekkep tozun onune gecmez); c(t) kare basina egri,
   ortam V6_C (json liste, kare 0..nB-1; yoksa kupanin murekkep egrisi ease((tt - 0.36) / 0.64)); v6_kalibre.py c'yi gorunen
   oran kupa V6 ile ayni olacak sekilde duzeltir.
Kaynak aciklama (v5):
Poster ilan videosu v5 (Serdar 19 Eki, v4 ana dosyadan; df252d7): yalniz uc degisiklik, gerisi v4 ile ayni:
 (1) toz 5 kat: N 5200 -> 26000; (2) tane boyu yarim: parcacik bulanikligi GaussianBlur sigma 0.9 -> 0.45 (al ve kat; FWHM
 2,12 -> 1,06 px; *2.0 carpani ve 0.9 ust siniri ayni); (3) sembol murekkebi tozdan once belirmez: her pikselin cevresine
 (sigma 3 px) inen tozun birikim orani F(t) = inen / toplam; murekkep F 0,2'yi gecmeden acilmaz, sonra dogrusal (F - 0,2) / 0,8;
 tum toz tt = 1,0'da (5,0 sn) inmis olur -> sembol en gec 5,0 sn'de tam. Mesaj yazimi, zamanlama, yollar, renk (murekkep =
 altin) ayni. Kaynak aciklama (v4):
Poster ilan videosu v4 (Serdar 19 Eki): YAYINDAKI kupa ilan videosunun (4598525642, Orchard Cancer & Libra) BIREBIR aynisi;
tek fark sahne = poster kapagi (4:3, 1440x1080). Kupa uretici: kupa-orchard dali kupa_orchard/kod/video6b.py (canli dosyayla
kare kare karsilastirma: poster-video-v4 is akisi). Asagidaki akis, sayilar ve formuller video6b.py ile ayni (satir satir):
6 sn, 30 fps, sessiz H.264 crf 17; ilk ve son kare = kapak; ilk 0,3 sn sembol ve mesaj yumusakca kaybolur; toz (5200, rng 11,
gecikme 0.62, yay 8-24 px, %22 altin / %78 yesil, parlaklik 0.55-1.0, bulaniklik 0.9 x 2.0) iki kucuk burc isaretinden (ve
posterde isimler arasindaki sonsuzluktan) akar; sembol ilk varislarla sifirdan yumusakca olusur, mesaj soldan saga yazilir;
toz ve mesaj BITIS (5,0 sn) aninda biter; sonra kapak sabit.
Degisen (yalniz sahne): kupada katmanlar baskidan (full/basem/nosym/noglif/nomes) gelir; posterde ayni katmanlar kapaktaki
posterden olculur: sembol, glif + sonsuzluk ve mesaj maskeleri PosterR (altin alfa); bos hal = kapak + (sembolsuz ve
mesajsiz poster - poster), sembolsuz/mesajsiz poster = kapaktaki posterin kendi pikselleriyle klasik Telea inpaint (yapay zeka
yok). Karisim agirligi maskenin yumusak bolgesi (bos hal yalniz bu bolgede kapaktan farkli; BITIS'te tam kapak).
Toz rengi: kupada %78 YESIL (22,60,36) = kupanin sembol murekkebi (Orange Blossom 10,40,24), %22 ALTIN (196,150,64).
'murekkep' (varsayilan): ayni rol posterde -> %78 posterin sembol murekkebi (olculen medyan), %22 ayni ALTIN.
'yesil': kupa sabitleri aynen.
Kullanim: python3 -I poster_video_v4.py <kapak.jpg> <cikti_mp4> [murekkep|yesil]"""
import os, subprocess, sys, time
import numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pin_v6'))
import pin_uret as PU

KAPAK, OUT = sys.argv[1:3]
RENK_MOD = sys.argv[3] if len(sys.argv) > 3 else 'murekkep'   # murekkep: toz = posterin sembol murekkebi (kupada YESIL =
# kupanin murekkebi); yesil: kupanin sabitleri aynen (lacivert posterde toz zor gorunur, olusma egrisi kupadan ayrilir)
BITIS = 5.0
VW, VH = 1440, 1080                                       # kupada V x V = 1080 x 1080; posterde 4:3, ayni yukseklik
FPS, SURE, SILME = 30, 6.0, 0.3
rng = np.random.default_rng(11)
t0 = time.time()

# ---------- poster kapakta (koyu dikdortgen) ve katmanlar (yalniz sahne farki)
kap_src = np.asarray(Image.open(KAPAK).convert('RGB'))
kf = kap_src.astype(np.float32); lum_ = kf @ np.float32([0.299, 0.587, 0.114])
lac = cv2.morphologyEx((lum_ < 90).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
n_, lab_, st_, _ = cv2.connectedComponentsWithStats(lac, 8)
bi = 1 + int(np.argmax(st_[1:, 4]))
x0, y0, cw, ch = (int(v) for v in st_[bi, :4]); x1, y1 = x0 + cw, y0 + ch
s_ = 2000 / cw
tmp = OUT + '._poster.png'
# v7 (26 Eki, yeni Canva kapagi): kapaktaki poster kucuk (~1039 px); 2000 px'e buyutulunce ince halka PosterR'de kopuyor
# ('halka bulunamadi'). POSTER_SRC verilirse maskeler kapaktaki posterle AYNI icerigin yuksek cozunurluklu kaynagindan
# (orn. canli eski kapagin poster bolgesi) cikarilir; kutu yine kapaktan olculur, oran farki <= %1 olmali.
_src = os.environ.get('POSTER_SRC')
if _src:
    ps = np.asarray(Image.open(_src).convert('RGB'))
    if abs(ps.shape[0] / ps.shape[1] - ch / cw) > 0.01 * ch / cw:
        raise SystemExit(f'POSTER_SRC oran {ps.shape[0] / ps.shape[1]:.4f} kapak kutusu {ch / cw:.4f}: uyusmuyor')
    Image.fromarray(cv2.resize(ps, (2000, round(ch * s_)), interpolation=cv2.INTER_AREA if ps.shape[1] > 2000 else cv2.INTER_CUBIC)).save(tmp)
else:
    Image.fromarray(cv2.resize(kap_src[y0:y1, x0:x1], (2000, round(ch * s_)), interpolation=cv2.INTER_CUBIC)).save(tmp)


class PosterV(PU.PosterR):
    """PosterR; yalniz o 'sol veya sag kucuk burc bulunamadi' derse (21 Eki, LIBRA_TAURUS: Terazi taban cizgisi halkanin alt
    acikliginda, halka kutusunun 9 px altinda): halkanin hemen altindaki (ust kenar <= ry1 + 40), ortalanmis, genis (> 0,2 W)
    parca sembole katilir ve satir bantlarindan cikarilir. Basarili ayristirmalar (77 cift) degismez."""

    def _find_parts(self):
        try:
            return super()._find_parts()
        except RuntimeError as e:
            if 'halka bulunamadi' in str(e) and os.environ.get('V7_HALKASIZ') == '1':
                return self._halkasiz()
            if 'kucuk burc' not in str(e):
                raise
        Wp = self.w
        comps = sorted(self.comps, key=lambda c: -c[5])
        rings = [c for c in comps[:6] if c[5] / float(c[3] * c[4]) < 0.03 and c[3] > 0.6 * Wp]
        self.ring = rings[0]
        rx0 = min(c[1] for c in rings); ry0 = min(c[2] for c in rings)
        rx1 = max(c[1] + c[3] for c in rings); ry1 = max(c[2] + c[4] for c in rings)
        ring_ids = {c[0] for c in rings}
        alt = [c for c in comps if c[0] not in ring_ids and ry1 < c[2] <= ry1 + 40 and c[3] > 0.2 * Wp
               and abs(c[1] + c[3] / 2 - Wp / 2) < 0.05 * Wp]
        alt_ids = {c[0] for c in alt}
        inside = [c for c in comps if c[0] not in ring_ids and c[5] > 50
                  and rx0 < c[1] + c[3] / 2 < rx1 and ry0 < c[2] + c[4] / 2 < ry1] + alt
        self.merged_parts = inside
        self.merged = self._union(inside)
        below = sorted([c for c in comps if c[2] > ry1 and c[5] > 300 and c[0] not in alt_ids], key=lambda c: c[2])
        bands = []
        for c in below:
            if bands and c[2] <= bands[-1]['y1'] + 40:
                bands[-1]['cs'].append(c); bands[-1]['y1'] = max(bands[-1]['y1'], c[2] + c[4])
            else:
                bands.append({'cs': [c], 'y1': c[2] + c[4]})
        if len(bands) < 3:
            raise RuntimeError(f'beklenen en az 3 satir (burclar, isimler, mesaj), bulunan {len(bands)}')
        left = [c for c in bands[0]['cs'] if c[1] + c[3] / 2 < Wp / 2]
        right = [c for c in bands[0]['cs'] if c[1] + c[3] / 2 >= Wp / 2]
        if not alt or not left or not right:
            raise RuntimeError('sol veya sag kucuk burc bulunamadi (halka alti parca ile de)')
        self.sign_a, self.sign_b = self._union(left), self._union(right)
        self.names_row = self._union(bands[1]['cs'])
        self.msg_row = self._union([c for b in bands[2:] for c in b['cs']])
        self.halka_alti = [[int(v) for v in c[1:6]] for c in alt]


    def _halkasiz(self):
        """v7 toplu (Serdar 26 Eki: maske V10 kapagin kendisinden; ortam V7_HALKASIZ=1): kapaktaki poster ~1039 px, ince halka JPEG
        renk sikistirmasinda R - B > 40 cekirdeginde gorunmuyor ('halka bulunamadi'). Halkasiz ayristirma: alan > 300 parcalar ust
        kenarina gore 40 px bosluk kuraliyla bantlara ayrilir (PosterR ile ayni); en buyuk parcanin bandi sembol bandidir ve bosluk
        < 0,06 x yukseklik olan komsu bantlar (sembolun ayrik parcalari) ona katilir. Sembol bandinin kutusu icinde merkezi olan alan > 50
        parcalar da sembole katilir. Sembol bandindan sonraki bantlar: kucuk burclar, isimler, mesaj (PosterR ile ayni)."""
        Wp, Hp = self.w, self.h
        comps = sorted(self.comps, key=lambda c: -c[5])
        if not comps:
            raise RuntimeError('halkasiz: parca yok')
        bands = []
        for c in sorted([c for c in comps if c[5] > 300], key=lambda c: c[2]):
            if bands and c[2] <= bands[-1]['y1'] + 40:
                bands[-1]['cs'].append(c); bands[-1]['y1'] = max(bands[-1]['y1'], c[2] + c[4])
            else:
                bands.append({'cs': [c], 'y1': c[2] + c[4]})
        for b in bands:
            b['y0'] = min(c[2] for c in b['cs'])
        en = comps[0]
        i = next(k for k, b in enumerate(bands) if en in b['cs'])
        j0, j1 = i, i
        while j0 > 0 and bands[j0]['y0'] - bands[j0 - 1]['y1'] < 0.06 * Hp:
            j0 -= 1
        while j1 + 1 < len(bands) - 3 and bands[j1 + 1]['y0'] - bands[j1]['y1'] < 0.06 * Hp:   # altta en az 3 bant kalir (2. iterasyon:
            j1 += 1                                                                    # ARIES_CAPRICORN burc bandi 153 px < 156 ile sembole katiliyordu)
        sym = [c for b in bands[j0:j1 + 1] for c in b['cs']]
        sx0 = min(c[1] for c in sym); sy0 = min(c[2] for c in sym)
        sx1 = max(c[1] + c[3] for c in sym); sy1 = max(c[2] + c[4] for c in sym)
        ids = {c[0] for c in sym}
        sym += [c for c in comps if c[0] not in ids and 50 < c[5] <= 300 and sx0 < c[1] + c[3] / 2 < sx1 and sy0 < c[2] + c[4] / 2 < sy1]
        self.ring = None
        self.merged_parts = sym
        self.merged = self._union(sym)
        alt = bands[j1 + 1:]
        if len(alt) < 3:
            raise RuntimeError(f'halkasiz: beklenen en az 3 satir (burclar, isimler, mesaj), bulunan {len(alt)}')
        left = [c for c in alt[0]['cs'] if c[1] + c[3] / 2 < Wp / 2]
        right = [c for c in alt[0]['cs'] if c[1] + c[3] / 2 >= Wp / 2]
        if not left or not right:
            raise RuntimeError('halkasiz: sol veya sag kucuk burc bulunamadi')
        self.sign_a, self.sign_b = self._union(left), self._union(right)
        self.names_row = self._union(alt[1]['cs'])
        self.msg_row = self._union([c for b in alt[2:] for c in b['cs']])
        print(f'halkasiz ayristirma: sembol {len(sym)} parca ({sx0},{sy0})-({sx1},{sy1}), alt bant {len(alt)}', flush=True)


try:
    P = PosterV(tmp)
finally:   # ayristirma dusse de gecici kirpim cikti klasorunde kalmasin (20 Eki: LIBRA_TAURUS ._poster.png Drive'a gitmisti)
    os.remove(tmp)


def vid(m):
    c = np.zeros(kap_src.shape[:2] + m.shape[2:], np.float32)
    c[y0:y1, x0:x1] = cv2.resize(m.astype(np.float32), (cw, ch), interpolation=cv2.INTER_AREA)
    return cv2.resize(c, (VW, VH), interpolation=cv2.INTER_AREA)


def parcalar(kutu, kosul=lambda c: True):
    _, bx, by, bw, bh, _ = kutu
    return [c for c in P.comps if bx <= c[1] + c[3] / 2 <= bx + bw and by <= c[2] + c[4] / 2 <= by + bh and kosul(c)]


def alfa(cs, d=7):
    m = cv2.dilate(np.isin(P.lab, [c[0] for c in cs]).astype(np.uint8), np.ones((d, d), np.uint8))
    return np.clip(P.alpha * m, 0, 1), m


msym = np.isin(P.lab, [c[0] for c in P.merged_parts]).astype(np.uint8)
# v7c (Merkez 28 Eki, pilot 4570110121 geri alindi): silme alani yalniz etiketli sembol parcalarindan (core R-B > 40) kuruluyordu;
# sembolun ince uclari ve araliktaki kucuk parcalar core'a girmiyor, alfa da ~0 (lib.Poster zemini bu pikselleri kapsiyor), bu yuzden
# 0,3-0,5 sn karelerinde altin iz kaliyordu (AQUARIUS_AQUARIUS: uclar sembolden 30-100 px, kapak R-B fazlasi 15-67; silme agirligi
# 0,00-0,09). Duzeltme: kapak posterinde R-B'nin yerel zemine (61 px medyan) gore fazlasi > YAKIN_T olan ve sembole ilk bos 10 px
# banda kadar (en fazla 140) uzaklikta olan pikseller sembol maskesine katilir; kucuk burc, isim, mesaj kutulari (10 px pay) haric.
# Esik olcumle: AQUARIUS_AQUARIUS zemin bandi (sembolden 100-140 px) fazla en buyuk 12; halka 140 px'ten sonra. Bos bant yoksa 30 px.
# V7_SILME=eski: eski davranis.
YAKIN_T, YAKIN_MAX = 15, 150
if os.environ.get('V7_SILME', 'tam') == 'tam':
    _uz = cv2.distanceTransform((1 - msym).astype(np.uint8), cv2.DIST_L2, 5)
    _rb = P.img[..., 0] - P.img[..., 2]
    _alt = (_rb - (cv2.medianBlur(np.clip(_rb + 128, 0, 255).astype(np.uint8), 61).astype(np.float32) - 128)) > YAKIN_T
    for _k in (P.sign_a, P.sign_b, P.names_row, P.msg_row):
        _, _x, _y, _w, _h, _ = _k
        _alt[max(0, _y - 10):_y + _h + 10, max(0, _x - 10):_x + _w + 10] = False
    SILME_D = next((d for d in range(30, YAKIN_MAX, 10) if not (_alt & (_uz >= d) & (_uz < d + 10)).any()), None)
    SILME_VARSAYILAN = SILME_D is None   # inceleme 28 Eki: bos bant bulunamazsa 30 px, logda ayrica yazilir
    SILME_D = SILME_D or 30
    _ek = (_alt & (_uz < SILME_D) & (msym == 0)).astype(np.uint8)
    print(f'silme: sembol maskesi {int(msym.sum())} px + yakin altin {int(_ek.sum())} px (R-B fazlasi > {YAKIN_T}, sembole < {SILME_D} px{" VARSAYILAN: bos bant yok" if SILME_VARSAYILAN else ""})',
          flush=True)
    msym = np.maximum(msym, _ek)
MS_p = np.clip(P.alpha * cv2.dilate(msym, np.ones((7, 7), np.uint8)), 0, 1)
sonsuz = parcalar(P.names_row, lambda c: abs(c[1] + c[3] / 2 - P.w / 2) < 0.08 * P.w)
MG_p = np.zeros_like(P.alpha)
for s2 in (P.sign_a, P.sign_b):
    _, x, y, w, h, _ = s2
    MG_p[y:y + h, x:x + w] = P.alpha[y:y + h, x:x + w]
MG_p = np.maximum(MG_p, alfa(sonsuz, 5)[0])
# v7d (Merkez 28 Eki, Serdar onayi): mesaj tam silinip soldan saga yeniden yazilir (YD 27 Eki karari ile ayni mantik). Eskiden mesaj
# yalniz core (R-B > 40) parcalarindan ve alani > 300 parcalarin kutusundan kuruluyordu: 8 ciftte yalniz "K", 6 ciftte yarisi, digerlerinde
# ince harfler silinmiyordu (TAM78 40669865397). Simdi (yd_video.py 95-117 gibi) mesaj isim satirinin altindaki bolgenin tamamindan:
# parlaklik - yerel zemin (61 px medyan) > MESAJ_CEKIRDEK olan satir kumelerinin en buyugu (komsu kumeler <= 40 px bosluk ile katilir)
# mesaj bandidir (y +-12, x +-20 px); bant icinde parlaklik fazlasi > MESAJ_KENAR olan TUM pikseller (ince harf, kenar yumusatma) mesaj
# maskesine girer. Isim satiri ve kucuk burclar silme alanina girmez (RM_p bu kutularda 0). V7_MESAJ=eski: eski davranis.
MESAJ_CEKIRDEK, MESAJ_KENAR = 20, 10
MESAJ = None
if os.environ.get('V7_MESAJ', 'tam') == 'tam':
    _lum = P.img @ np.float32([0.299, 0.587, 0.114])
    _ex = _lum - cv2.medianBlur(np.clip(_lum, 0, 255).astype(np.uint8), 61).astype(np.float32)
    _ny1 = int(P.names_row[2] + P.names_row[4]) + 15
    _xa, _xb = int(0.04 * P.w), int(0.96 * P.w)
    _sat = (_ex[_ny1:, _xa:_xb] > MESAJ_CEKIRDEK).sum(1)
    _kum = []
    for _r in np.where(_sat > 0)[0]:
        if _kum and _r - _kum[-1][1] <= 6:
            _kum[-1][1] = _r
        else:
            _kum.append([_r, _r])
    if not _kum:
        raise SystemExit('v7d: isim satirinin altinda mesaj murekkebi yok')
    _ki = max(range(len(_kum)), key=lambda k: _sat[_kum[k][0]:_kum[k][1] + 1].sum())
    _a, _b = _kum[_ki]
    for _k in range(_ki - 1, -1, -1):                                # 2 satirli mesaj: komsu kumeler
        if _a - _kum[_k][1] <= 40 and _sat[_kum[_k][0]:_kum[_k][1] + 1].sum() > 0.1 * _sat[_kum[_ki][0]:_kum[_ki][1] + 1].sum():
            _a = _kum[_k][0]
        else:
            break
    for _k in range(_ki + 1, len(_kum)):
        if _kum[_k][0] - _b <= 40 and _sat[_kum[_k][0]:_kum[_k][1] + 1].sum() > 0.1 * _sat[_kum[_ki][0]:_kum[_ki][1] + 1].sum():
            _b = _kum[_k][1]
        else:
            break
    _ya, _yb = max(_ny1 - 4, _ny1 + _a - 12), min(P.h, _ny1 + _b + 13)
    _cols = np.where((_ex[_ya:_yb, _xa:_xb] > MESAJ_CEKIRDEK).any(0))[0]
    _mxa, _mxb = max(0, _xa + int(_cols.min()) - 20), min(P.w, _xa + int(_cols.max()) + 21)
    _mm = np.zeros(P.lab.shape, bool)
    _mm[_ya:_yb, _mxa:_mxb] = _ex[_ya:_yb, _mxa:_mxb] > MESAJ_KENAR
    _n2, _lab2, _st2, _ = cv2.connectedComponentsWithStats(_mm.astype(np.uint8), 8)
    _taban = int(P.lab.max()) + 1
    _yeni = []
    for _k in range(1, _n2):
        P.lab[_lab2 == _k] = _taban + _k
        _yeni.append((_taban + _k, *(int(v) for v in _st2[_k])))
    P.comps = [c for c in P.comps if not (_mxa <= c[1] + c[3] / 2 <= _mxb and _ya <= c[2] + c[4] / 2 <= _yb)] + _yeni
    P.msg_row = (-1, _mxa, _ya, _mxb - _mxa, _yb - _ya, int(_mm.sum()))
    MESAJ = {'bant_poster': [int(_mxa), int(_ya), int(_mxb), int(_yb)], 'murekkep_px': int(_mm.sum()), 'parca': len(_yeni)}
    print(f'mesaj: bant {MESAJ["bant_poster"]} (poster), murekkep {MESAJ["murekkep_px"]} px, {len(_yeni)} parca '
          f'(parlaklik fazlasi > {MESAJ_KENAR}, cekirdek > {MESAJ_CEKIRDEK})', flush=True)
mes = parcalar(P.msg_row)
MM_p, mmes = alfa(mes, 5)
# bos hal bolgeleri: sembol + golgesi (31 px), mesaj (11 px); yumusak kenar
RS_p = cv2.GaussianBlur(cv2.dilate(msym, np.ones((31, 31), np.uint8)).astype(np.float32), (0, 0), 5.0)
RM_p = cv2.GaussianBlur(cv2.dilate(mmes, np.ones((11, 11), np.uint8)).astype(np.float32), (0, 0), 2.0)
ISIM_ALT = 0.4   # isim satiri koruma payi (alt uzantilar), isim yuksekligi orani (yd_video ile ayni)
if MESAJ is not None:   # v7d: isim satiri (alt uzantilar dahil) ve kucuk burclar silinmez
    for _k in (P.names_row, P.sign_a, P.sign_b):
        RM_p[_k[2]:_k[2] + _k[4] + (int(ISIM_ALT * _k[4]) if _k is P.names_row else 0), _k[1]:_k[1] + _k[3]] = 0
R_p = np.maximum(RS_p, RM_p)
hm = cv2.resize((R_p > 0.02).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_NEAREST)
# v7b (26 Eki): bos hal KAPAKTAKI posterin kendi piksellerinden (POSTER_SRC yalniz maske icin). Kaynak ile Canva kapagi
# arasindaki kucuk keskinlik/konum farki (ort 2,65) BASE = KAP + (bos - P.img) farkinda sembolu hayalet olarak birakiyordu.
P_KAP = cv2.resize(kap_src[y0:y1, x0:x1], (P.w, P.h), interpolation=cv2.INTER_CUBIC).astype(np.float32) if _src else P.img
hi = cv2.resize(np.clip(P_KAP, 0, 255).astype(np.uint8), (P.w // 2, P.h // 2), interpolation=cv2.INTER_AREA)
if os.environ.get('V7_DOLGU') == 'nk':
    # v7 toplu 2. iterasyon (Serdar 26 Eki): Telea yalniz bolge sinirindan doldurur; 18 FAIL ciftte dolgu sembolun icinden gorunen
    # gercek zeminden mavi / acik (TAURUS_VIRGO R-B -42,35 / -41,14). Normalize Gauss: bilinmeyen bolge disindaki (ve sembolun ic
    # bosluklarindaki) tum zemin pikselleri agirlikli ortalamayla; sigma kucukten buyuge, agirlik toplami >= 0,25 olan ilk olcek.
    hmk = cv2.dilate(hm, np.ones((3, 3), np.uint8)) > 0
    w = (~hmk).astype(np.float32)
    hf = hi.astype(np.float32); dol = hf.copy(); kalan = hmk.copy()
    for sg in (6, 12, 24, 48, 96):
        den = cv2.GaussianBlur(w, (0, 0), sg)
        nk = cv2.GaussianBlur(hf * w[..., None], (0, 0), sg) / np.maximum(den, 1e-6)[..., None]
        ok = kalan & (den >= 0.25)
        dol[ok] = nk[ok]; kalan &= ~ok
    if kalan.any():
        dol[kalan] = nk[kalan]
    bos = cv2.resize(dol, (P.w, P.h), interpolation=cv2.INTER_CUBIC)
else:
    bos = cv2.resize(cv2.inpaint(hi, cv2.dilate(hm, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA).astype(np.float32),
                     (P.w, P.h), interpolation=cv2.INTER_CUBIC)
KAP = np.clip(np.round(cv2.resize(kap_src, (VW, VH), interpolation=cv2.INTER_AREA).astype(np.float32)), 0, 255)
FULL = KAP
BASE = np.clip(KAP + vid((bos - P_KAP) * R_p[..., None]), 0, 255)
MS, MG, MM = vid(MS_p), vid(MG_p), vid(MM_p)
WS, WM = np.clip(vid(RS_p), 0, 1), np.clip(vid(RM_p), 0, 1)      # karisim agirliklari (kupada maske = katman farki)
MM = cv2.dilate(MM, np.ones((3, 3), np.uint8))
XX = np.arange(VW, dtype=np.float32)[None, :].repeat(VH, 0)
print(f'poster kapakta {x0},{y0} {cw}x{ch} oran {ch / cw:.3f}; sonsuz {len(sonsuz)} parca, mesaj {len(mes)} parca', flush=True)
GLIF = {'sign_a': [int(v) for v in P.sign_a[1:5]], 'sign_b': [int(v) for v in P.sign_b[1:5]], 'poster_w': int(P.w),
        'sonsuz': [[int(v) for v in c[1:5]] for c in sonsuz], 'halka_alti_sembol_parcasi': getattr(P, 'halka_alti', [])}   # QC (78 uretim): glif ve sonsuz yerleri (poster 2000 px olcegi)
_g = [cv2.resize(P.alpha[y:y + h, x:x + w].astype(np.float32), (64, 64), interpolation=cv2.INTER_AREA) for _, x, y, w, h, _ in (P.sign_a, P.sign_b)]
_g = [(g - g.mean()) / (g.std() + 1e-6) for g in _g]
GLIF['benzerlik'] = round(float((_g[0] * _g[1]).mean()), 3)   # iki glifin NCC'si (ayni burcta yuksek olmali)
Image.fromarray(((MS > 0.95) * 255).astype(np.uint8)).save(OUT + '.sembol_maske.png')   # QC: cekirdek sembol pikselleri
Image.fromarray(((vid(msym.astype(np.float32)) > 0.25) * 255).astype(np.uint8)).save(OUT + '.silme_maske.png')   # QC silme_artik (v7c)


def kapsam(m):
    ys, xs = np.where(m > 0.2)
    return xs.min(), xs.max()


mx0, mx1 = kapsam(MM)
if MESAJ is not None:   # v7d inceleme 28 Eki bulgu 3: yazim araligi mesaj maskesinin tamami (alfa < 0,2 uc noktalari / suslar dahil);
    mx0, mx1 = kapsam(vid(mmes.astype(np.float32)))   # eskiden sol nokta hic silinmiyor, sag nokta siliniyordu
ease = lambda x: (lambda y: y * y * (3 - 2 * y))(min(1.0, max(0.0, x)))


def yazim(x0_, x1_, p, yum=10):
    """soldan saga yazilma: p ilerlemesine gore x esiginin solu acik, yumusak kenar"""
    esik = x0_ - yum + (x1_ - x0_ + 2 * yum) * p
    return np.clip((esik - XX) / yum, 0, 1)


def noktalar(m, N):
    ys, xs = np.where(m > 0.35)
    i = rng.choice(len(xs), N, replace=True)
    return np.stack([xs[i], ys[i]], 1).astype(np.float32) + rng.random((N, 2)).astype(np.float32) - 0.5


N = int(os.environ.get('V6_N', '26000'))                 # v6: kalibre (v5: 26000)
BOLGE_PX = int((cv2.dilate((MS > 0.95).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0).sum())   # olcum bolgesi (v6_kalibre)
if os.environ.get('V6_BOLGE_REF'):   # 78 uretim (20 Eki): N = 58000 x bolge alani / CL bolge alani
    N = int(round(float(os.environ.get('V6_N_REF', '58000')) * BOLGE_PX / float(os.environ['V6_BOLGE_REF']) / 100.0) * 100)
src, dst = noktalar(MG, N), noktalar(MS, N)
os_, od = np.median(src[:, 0]), np.median(dst[:, 0])
sol = src[:, 0] < os_
dsol, dsag = dst[dst[:, 0] < od], dst[dst[:, 0] >= od]
nl = int(sol.sum())
src = np.concatenate([src[sol], src[~sol]])
dst = np.concatenate([dsol[rng.choice(len(dsol), nl)], dsag[rng.choice(len(dsag), N - nl)]])
gec = rng.random(N).astype(np.float32) * 0.62
yay = -(8 + 16 * rng.random(N).astype(np.float32))
YESIL, ALTIN = np.array([22, 60, 36], np.float32), np.array([196, 150, 64], np.float32)
if RENK_MOD == 'murekkep':   # kupada ana toz rengi YESIL = kupanin sembol murekkebi; posterde ayni rol: sembolun kendi rengi
    YESIL = np.median(P.img[np.isin(P.lab, [c[0] for c in P.merged_parts]) & (P.alpha > 0.98)], 0).astype(np.float32)
print(f'toz renkleri ({RENK_MOD}): ana {YESIL.round().tolist()} %78, ALTIN {ALTIN.tolist()} %22', flush=True)
renk = np.where((rng.random(N) < 0.22)[:, None], ALTIN, YESIL)
par = (0.55 + 0.45 * rng.random(N)).astype(np.float32)

nT, nB, nS = int(round(SURE * FPS)), int(round(BITIS * FPS)), int(round(SILME * FPS))
TANE = 0.45                                                 # v5: parcacik bulanikligi sigma (v4 0.9)
# v5 murekkep kurali: yerel toz birikimi
from scipy.ndimage import distance_transform_edt
TARR = gec + 0.38                                           # parcacigin indigi an (uu = 1), tt birimi
dxi = np.clip(np.round(dst[:, 0]).astype(int), 0, VW - 1); dyi = np.clip(np.round(dst[:, 1]).astype(int), 0, VH - 1)
H_TUM = np.zeros((VH, VW), np.float32); np.add.at(H_TUM, (dyi, dxi), 1.0)
CF = cv2.GaussianBlur(H_TUM, (0, 0), 3.0)
iyi = CF > 0.02 * CF[MS > 0.5].max()
II = distance_transform_edt(~iyi, return_indices=True)[1]  # tozun az indigi kenar pikselleri en yakin iyi pikselin oranini alir
F_A, F_B = 0.2, 1.0                                         # (v5 esikleri; v6'da kullanilmaz, kayit icin)
import json as _j
C_EGRI = _j.load(open(os.environ['V6_C'])) if os.environ.get('V6_C') else [ease((k / (nB - 1) - 0.36) / 0.64) for k in range(nB)]
CEK = MS > 0.95                                             # cekirdek sembol pikselleri (olcum)
SIRA = np.argsort(TARR); TS = TARR[SIRA]; H_T = np.zeros((VH, VW), np.float32); k_ = 0
IC = {'kare': [], 'murekkep': [], 'toz_ortusu': [], 'ihlal': []}


def murekkep(tt):
    global k_
    j = int(np.searchsorted(TS, tt, side='right'))
    if j > k_:
        np.add.at(H_T, (dyi[SIRA[k_:j]], dxi[SIRA[k_:j]]), 1.0); k_ = j
    F = (cv2.GaussianBlur(H_T, (0, 0), 3.0) / np.maximum(CF, 1e-6))[II[0], II[1]]
    F = np.clip(F, 0, 1)
    return np.minimum(C_EGRI[min(len(C_EGRI) - 1, int(round(tt * (nB - 1))))], F), F   # v6: min(c(t), F)
KAP8 = KAP.astype(np.uint8)
HAM_KUTU, HAM_FARK = None, 0   # v7d QC (c): TOZSUZ=1 iken isim satiri (sonsuz haric) ve kucuk burc kutularinda ham kare - kapak farki
if os.environ.get('TOZSUZ'):
    _hk = np.zeros(P.alpha.shape, np.float32)
    for _k in (P.names_row, P.sign_a, P.sign_b):
        _hk[_k[2]:_k[2] + _k[4] + (int(ISIM_ALT * _k[4]) if _k is P.names_row else 0), _k[1]:_k[1] + _k[3]] = 1
    for _c in sonsuz:
        _hk[max(0, _c[2] - 8):_c[2] + _c[4] + 8, max(0, _c[1] - 8):_c[1] + _c[3] + 8] = 0
    HAM_KUTU = vid(_hk) > 0.5
pr = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{VW}x{VH}',
                       '-r', str(FPS), '-i', '-', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17',
                       '-preset', 'slow', '-movflags', '+faststart', OUT], stdin=subprocess.PIPE)
for i in range(nT):
    if i == 0 or i >= nB:
        pr.stdin.write(KAP8.tobytes())
        continue
    tt = i / (nB - 1)
    am = yazim(mx0, mx1, ease(tt)) * WM
    uu = np.clip((tt - gec) / 0.38, 0, 1)
    mk, F = murekkep(tt)                                     # v5: murekkep yalniz toz birikince (v4: ease((tt-0.36)/0.64))
    asym = mk * WS
    IC['kare'].append(i); IC['murekkep'].append(float(mk[CEK].mean())); IC['toz_ortusu'].append(float(F[CEK].mean()))
    IC['ihlal'].append(float((mk[CEK] - F[CEK]).max()))     # > 0 ise bir pikselde murekkep tozun onunde
    A = np.clip(am + asym, 0, 1)[..., None]
    f = BASE * (1 - A) + FULL * A
    if i <= nS:                                              # ilk 0,3 sn: kapaktaki sembol ve mesaj yumusakca kaybolur
        e = ease(i / nS)
        f = KAP * (1 - e) + f * e
    ue = uu * uu * (3 - 2 * uu)
    p = src * (1 - ue)[:, None] + dst * ue[:, None]
    p[:, 1] += yay * np.sin(np.pi * ue)
    p[:, 0] += np.sin(tt * 8 + np.arange(N) * 0.41) * 0.8 * np.sin(np.pi * ue)
    gor = (uu > 0) & (uu < 1)
    xi, yi = p[gor, 0].astype(int), p[gor, 1].astype(int)
    ok = (xi >= 0) & (xi < VW) & (yi >= 0) & (yi < VH)
    a_ = (par[gor] * np.sin(np.pi * uu[gor]))[ok]
    al = np.zeros((VH, VW), np.float32)
    kat = np.zeros((VH, VW, 3), np.float32)
    np.add.at(al, (yi[ok], xi[ok]), a_)
    for c in range(3):
        np.add.at(kat[..., c], (yi[ok], xi[ok]), renk[gor][ok, c] * a_)
    al = cv2.GaussianBlur(al, (0, 0), TANE) * 2.0             # v5: tane boyu yarim (v4 sigma 0.9)
    kat = cv2.GaussianBlur(kat, (0, 0), TANE) * 2.0
    rk = kat / np.maximum(al[..., None], 1e-4)
    a3 = np.clip(al, 0, 0.9)[..., None] * (0 if os.environ.get('TOZSUZ') else 1)   # TOZSUZ=1: yalniz QC (murekkep olusumu)
    o = np.clip(f * (1 - a3) + rk * a3, 0, 255).astype(np.uint8)
    if HAM_KUTU is not None:
        HAM_FARK = max(HAM_FARK, int(np.abs(o[HAM_KUTU].astype(np.int16) - KAP8[HAM_KUTU].astype(np.int16)).max()))
    pr.stdin.write(o.tobytes())
    if i % 15 == 0:
        g = time.time() - t0
        print(f'  kare {i}/{nB} %{100 * i // nB} (gecen {g:.0f}s, kalan ~{g / i * (nB - i):.0f}s)', flush=True)
pr.stdin.close(); pr.wait()
print(f'{nT} kare ({nT / FPS:.2f} sn), toz/yazi bitis {BITIS} sn, uretim {time.time() - t0:.0f}s', flush=True)
import json
DONUSUM = {'x0': x0, 'y0': y0, 'cw': cw, 'ch': ch, 'pw': int(P.w), 'ph': int(P.h), 'kw': int(kap_src.shape[1]), 'kh': int(kap_src.shape[0]),
           'vw': VW, 'vh': VH}   # poster (2000 px) -> video: vx = (x0 + px * cw / pw) * vw / kw
YAZIM = {'mx0': int(mx0), 'mx1': int(mx1), 'yum': 10, 'nB': nB, 'nS': nS, 'mesaj': MESAJ, 'isim_alt': ISIM_ALT,
         'isim_poster': [int(v) for v in P.names_row[1:5]], 'msg_row_poster': [int(v) for v in P.msg_row[1:5]]}   # QC mesaj_isim
if HAM_KUTU is not None:
    YAZIM['ham_kutu_fark_max'] = HAM_FARK; YAZIM['ham_kutu_px'] = int(HAM_KUTU.sum())
json.dump({'N': N, 'bolge_px': BOLGE_PX, 'glif': GLIF, 'donusum': DONUSUM, 'yazim': YAZIM, 'tane_sigma': {'v4': 0.9, 'v5': TANE}, 'c_egri': [round(float(x), 4) for x in C_EGRI], **IC}, open(OUT + '.ic.json', 'w'))
print('tamam', OUT)
