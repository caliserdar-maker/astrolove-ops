# set_yerlestir.py  (7 Kas) - fal sahnesi (duz yakut disk) + onayli baski kodla birebir (ANA_1 2.1)
# AI diski baskisiz uretildi: isik katmani = AI diskinin kendi taban parlakligina gore gri carpan + beyaz parlama (OK 18).
# kullanim: python set_yerlestir.py kapak|agac|kart
import sys, json, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont

AD = sys.argv[1]
BASKI = os.environ["BASKI"]   # 8 Kas v9: baski zorunlu (cift x stil, Drive TOPLAMA78)
KX, KY, KR = 476.0, 477.0, 449.0
DX, DY = 476.0, 163.0
HR_ORAN = 28.3 / KR                       # kapak_yasam.py satir 420 (EK_OLCUM.json cap 56,6)
W, H = 3000, 2250
if len(sys.argv) > 3:                                   # yeni giris: python set_yerlestir.py AD giris.png giris.olc.json
    _o = json.load(open(sys.argv[3])); _k = W / _o["W"]
    _Hs = int(round(_o["H"] * _k)); PAD = (H - _Hs) // 2          # inceleme 3: tek olcek, eksik yukseklik yansitmali dolgu
    O = dict(cx=_o["cx"] * _k, cy=_o["cy"] * _k + PAD, A=_o["A"] * _k, B=_o["B"] * _k, aci=_o["aci"],
             delik=[_o["delik"][0] * _k, _o["delik"][1] * _k + PAD, _o["delik"][2] * _k])
    GIRIS = sys.argv[2]
else:
    O = json.load(open("set_olcum.json"))[AD]; GIRIS = f"ham_{AD}.png"; _Hs = None

G = cv2.imread(GIRIS)[:, :, ::-1].astype(np.float32)
if _Hs is None or _Hs == H:
    G = np.clip(cv2.resize(G, (W, H), interpolation=cv2.INTER_LANCZOS4), 0, 255)
else:
    G = np.clip(cv2.resize(G, (W, _Hs), interpolation=cv2.INTER_LANCZOS4), 0, 255)
    G = cv2.copyMakeBorder(G, PAD, H - _Hs - PAD, 0, 0, cv2.BORDER_REFLECT)
cx, cy, a, b, th = O["cx"], O["cy"], O["A"] / 2, O["B"] / 2, np.deg2rad(O["aci"])
R = (a + b) / 2
gx_, gy_, ghr = O["delik"]
# AI deligi: merkez + yaricap, ip olmayan acilarda (asagi yarim + yanlar) radyal en guclu kenara daire uydurma
_L = cv2.GaussianBlur(0.2126 * G[..., 0] + 0.7152 * G[..., 1] + 0.0722 * G[..., 2], (0, 0), 1.2)
_hr0 = HR_ORAN * R


def _delik_uydur(cx0, cy0):
    pts = []
    for _a in np.deg2rad(np.arange(-30, 211, 6)):
        _rs = np.arange(0.5 * _hr0, 2.2 * _hr0, 0.5)
        _v = np.array([_L[int(cy0 + _rr * np.sin(_a)), int(cx0 + _rr * np.cos(_a))] for _rr in _rs])
        _i = int(np.argmax(np.abs(np.diff(_v))))
        pts.append((cx0 + _rs[_i] * np.cos(_a), cy0 + _rs[_i] * np.sin(_a)))
    Pq = np.array(pts)
    A_ = np.c_[2 * Pq[:, 0], 2 * Pq[:, 1], np.ones(len(Pq))]
    for _ in range(3):                                   # aykiri noktalari at, yeniden uydur
        sol = np.linalg.lstsq(A_, (Pq ** 2).sum(1), rcond=None)[0]
        c0, c1 = sol[0], sol[1]; rr = np.sqrt(sol[2] + c0 ** 2 + c1 ** 2)
        res = np.abs(np.hypot(Pq[:, 0] - c0, Pq[:, 1] - c1) - rr)
        keep = res < max(2.0, np.percentile(res, 70))
        A_, Pq = A_[keep], Pq[keep]
    return c0, c1, rr


_bas = (gx_, gy_, ghr)
for _ in range(2):                          # inceleme t2-2: uydurma bekleneni bozarsa (acik renk disk) baslangic korunur
    _n = _delik_uydur(gx_, gy_)
    if np.hypot(_n[0] - gx_, _n[1] - gy_) < 0.6 * _hr0 and 0.045 * ((O["A"] + O["B"]) / 4) < _n[2] < 0.10 * ((O["A"] + O["B"]) / 4):
        gx_, gy_, ghr = _n
    else:
        print("UYARI delik uydurma reddedildi", [round(float(v), 1) for v in _n], "baslangic", [round(float(v), 1) for v in _bas])
        break
Rm = lambda t: np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
E2 = Rm(th) @ np.diag([a / KR, b / KR]) @ Rm(th).T
hedef = np.array([gx_ - cx, gy_ - cy])
best = None
for phi in np.deg2rad(np.arange(-15, 15.001, 0.02)):
    v = E2 @ Rm(phi) @ np.array([DX - KX, DY - KY])
    d = abs(np.arctan2(v[0], -v[1]) - np.arctan2(hedef[0], -hedef[1]))
    if best is None or d < best[0]:
        best = (d, phi)
phi = best[1]
A2 = E2 @ Rm(phi)
M = np.hstack([A2, (np.array([cx, cy]) - A2 @ np.array([KX, KY]))[:, None]])
nhx, nhy = M @ np.array([DX, DY, 1.0])
hr = min(ghr, 0.080 * R)     # AI deligi cok buyukse (studyo 0,091R) gorunen delik 0,080R ile sinirli; gorunen delik AI deliginin boyutu (ANA_1 1.8 r~34/449 = 0,076R; kod 28,3 = 0,063R; aralik icinde)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dkx, dky = nhx - gx_, nhy - gy_
s_loc = 1.0
r_out = np.hypot(xx - nhx, yy - nhy)
r1, r2 = 1.6 * hr, 1.6 * hr + 0.12 * R
fac = np.where(r_out < r1, s_loc, np.where(r_out < r2, s_loc + (1 - s_loc) * (r_out - r1) / (r2 - r1), 1.0)).astype(np.float32)
qx = nhx + (xx - nhx) * fac; qy = nhy + (yy - nhy) * fac
rim_y = cy - np.sqrt(np.clip(b ** 2 - (xx - cx) ** 2, 0, None))
y_a = nhy - 1.6 * hr
wy = np.where(yy <= rim_y, 0.0, np.where(yy < y_a, (yy - rim_y) / np.maximum(y_a - rim_y, 1), np.where(yy < nhy + 1.6 * hr, 1.0,
              np.clip(1 - (yy - (nhy + 1.6 * hr)) / (0.2 * R), 0, 1))))
wx = np.clip(1 - (np.abs(xx - nhx) - 1.6 * hr) / (0.15 * R), 0, 1)
wt = (wy * wx).astype(np.float32)
srcx = (qx - wt * dkx).astype(np.float32); srcy = (qy - wt * dky).astype(np.float32)
G = cv2.remap(G, srcx, srcy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
delik_ai = [round(float(gx_), 1), round(float(gy_), 1), round(float(ghr), 1)]   # inceleme 5: rapor icin sakla
gx_, gy_ = nhx, nhy                    # AI deligi artik bizim delikte (ghr = AI yaricapi kalir)
dx, dy = xx - cx, yy - cy
xr = dx * np.cos(th) + dy * np.sin(th); yr = -dx * np.sin(th) + dy * np.cos(th)
el = np.sqrt((xr / a) ** 2 + (yr / b) ** 2)
r_, g_, b_ = G[..., 0], G[..., 1], G[..., 2]
KENAR = 0.007 * R                      # inceleme 2: yuz maskesi silüete kadar, yalniz yakut renkli piksellerde (disariya tasma yok)
_dout = (el - 1) * R
_yak = (r_ > 1.6 * g_ + 10) & (r_ > 30)
# inceleme t2-11: genisletme aciya gore (piksel piksel degil): her 1 derecelik dilimde bant cogunlukla yakutsa genislet, aci boyunca yumusat
_aci = (np.rad2deg(np.arctan2(yy - cy, xx - cx)) + 360) % 360
_bant = (_dout > 0) & (_dout <= KENAR)
_bin = _aci.astype(np.int32) % 360
_top = np.bincount(_bin[_bant], minlength=360).astype(np.float32)
_yk = np.bincount(_bin[_bant & _yak], minlength=360).astype(np.float32)
_ef = np.where(_top > 0, _yk / np.maximum(_top, 1), 0)
_ef = np.convolve(np.r_[_ef[-10:], _ef, _ef[:10]], np.exp(-0.5 * (np.arange(-10, 11) / 3.0) ** 2) / np.exp(-0.5 * (np.arange(-10, 11) / 3.0) ** 2).sum(), "same")[10:-10]
_e = np.clip((_ef - 0.5) / 0.3, 0, 1) * KENAR
_ea = _e[_bin]
yuz = np.clip(_ea - _dout + 0.5, 0, 1).astype(np.float32)
LG = 0.2126 * r_ + 0.7152 * g_ + 0.0722 * b_


def gen(m, px):
    px = max(int(round(px)), 0)
    return cv2.dilate(m.astype(np.uint8), np.ones((2 * px + 1, 2 * px + 1), np.uint8)).astype(bool)


def _kucuk_doldur(m):
    # inceleme t3-3: yalniz kucuk kapali bosluklar doldurulur (ip kollari arasi gibi buyuk alanlar baskidan gelir)
    m = m.astype(np.uint8)
    _ff = m.copy(); _fm = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8); cv2.floodFill(_ff, _fm, (0, 0), 1)
    bos = ((_ff == 0) & (m == 0)).astype(np.uint8)
    n_, lb_, st_, _ = cv2.connectedComponentsWithStats(bos)
    kucuk = np.isin(lb_, 1 + np.where(st_[1:, 4] < 0.0005 * R * R)[0])
    return (m > 0) | kucuk


_dmed = np.median(G[el < 0.6], 0)                  # K06: fildisi / beyaz disk yuzu altin sanilmasin
altin = ((g_ - b_) > 22) & (g_ > 0.33 * r_) & (np.linalg.norm(G - _dmed, axis=2) > 45) \
    & (r_ > 0.8 * g_) & ((r_ - b_) > 0.4 * r_)       # K06: altin sicak ve doygun; zumrut / fildisi kenar parlamasi degil
gdel = np.hypot(xx - gx_, yy - gy_) < ghr * 1.08
_ipdis = (np.hypot(xx - gx_, yy - gy_) < hr) if hr < ghr * 0.99 else gdel   # sinirli delikte halka icindeki ip kesilmesin
ip = altin & (yuz > 0) & ~_ipdis                   # duz diskte yuzdeki her altin ip'tir
ip = cv2.morphologyEx(ip.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))   # inceleme 4: ipteki parlak benekler
ip = _kucuk_doldur(ip) & (yuz > 0) & ~_ipdis
# inceleme t2 (5,6,7,8,11): ip = (a) delikten yukari koridorda, altin cekirdege yakin ve disk tabanindan sapan her piksel
#   (soluk / parlak / golgeli ip pikselleri dahil), (b) koridor disinda yalniz buyuk altin bilesenler (kenar beneklerini at)
_kor = (np.abs(xx - gx_) < 3.2 * ghr) & (yy < gy_ + 1.3 * ghr)
_x0, _x1 = int(max(gx_ - 4.5 * ghr, 0)), int(min(gx_ + 4.5 * ghr, W)); _y1 = int(min(gy_ + 2.5 * ghr, H))
_y0 = int(max(min(cy - b - 10, gy_ - 6 * ghr), 0))
_Gk = np.clip(G[_y0:_y1, _x0:_x1], 0, 255).astype(np.uint8)
_cek = (altin & _kor)[_y0:_y1, _x0:_x1].astype(np.uint8)
_yak = cv2.dilate(_cek, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.4 * ghr) | 1, int(0.4 * ghr) | 1)))   # t3-3: ip golgesi alinmasin
_taban = cv2.inpaint(_Gk, cv2.dilate(_yak, np.ones((9, 9), np.uint8)) | gdel[_y0:_y1, _x0:_x1].astype(np.uint8), 7, cv2.INPAINT_TELEA)
_sap = np.abs(_Gk.astype(np.float32) - _taban.astype(np.float32)).max(2) > 28
_ipk = np.zeros((H, W), bool); _ipk[_y0:_y1, _x0:_x1] = (_sap & (_yak > 0)) | (_cek > 0)
_dr_ = np.hypot(xx - gx_, yy - gy_)
_ipk &= ~((_dr_ < 1.8 * ghr) & ~altin)          # t3-1: delik halkasinda yalniz gercek altin (AI delik dudagi ip degil)
_bnt = el >= 0.97
_ic = _ipk & ~_bnt                               # t4-Y1: bant disindaki ip; banttan gecen ip kolonu dikey uzatilir (+-2 px)
_kol = cv2.dilate(_ic.astype(np.uint8), np.ones((int(0.08 * R) | 1, 5), np.uint8)) > 0
_ipk &= ~_bnt | altin | _kol                     # t3-2: bantta sapma yalniz ip kolonunda (kenar parlamasi ip degil)
_ipk &= _kor & (yuz > 0) & ~_ipdis
_n, _lb, _st, _ = cv2.connectedComponentsWithStats((ip & ~_kor).astype(np.uint8))
_kenar_or = np.bincount(_lb.ravel(), weights=(el > 0.92).ravel().astype(np.float64), minlength=_n) / np.maximum(_st[:, 4], 1)
_buyuk = np.isin(_lb, 1 + np.where((_st[1:, 4] > 0.004 * R * R) & (_kenar_or[1:] < 0.5))[0])   # kenar parlamasi ip degil
ip = _ipk | (ip & ~_kor & _buyuk)
ip = cv2.morphologyEx(ip.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))   # t4-Y3: kollar arasi kopru kurulmasin
_ipdis2 = np.hypot(xx - gx_, yy - gy_) < max(hr - 3, 1)                                  # t4-Y5: ip delige 3 px uzanir (arada baski seridi kalmasin)
ip = _kucuk_doldur(ip) & (yuz > 0) & ~(_ipdis2 | (_ipdis & ~altin))
_nn, _ll, _ss, _ = cv2.connectedComponentsWithStats(ip.astype(np.uint8))                  # t4-Y4: delik cevresinde kopuk adaciklar ip degil
_yakin = np.hypot(_ss[:, 0] + _ss[:, 2] / 2 - gx_, _ss[:, 1] + _ss[:, 3] / 2 - gy_) < 3 * ghr
_kucuk = np.where((_ss[1:, 4] < 60 * (R / 577.0) ** 2) & _yakin[1:])[0] + 1
ip &= ~np.isin(_ll, _kucuk)
hale = np.hypot(xx - gx_, yy - gy_) < 1.8 * ghr    # inceleme 1: AI delik cevresi kabarik halka isiga girmesin
# isik katmani (AI diskinin kendi tabanina gore)
mask = (gen(ip, 4) | gen(gdel, 2) | hale | (yuz < 1)).astype(np.uint8)
LGi = cv2.inpaint(LG.astype(np.float32), mask, 5, cv2.INPAINT_TELEA)
w = ((yuz > 0.99) & ~hale).astype(np.float32)


def yb(x, s):
    return cv2.GaussianBlur(x * w, (0, 0), s) / np.maximum(cv2.GaussianBlur(w, (0, 0), s), 1e-4)


LGs = yb(LGi, 2.0)
Lb = yb(LGi, 0.25 * R)
Lmed = float(np.median(LGi[yuz > 0.99]))
Lm_ = yb(LGi, 0.10 * R)
Sm = np.clip(np.minimum(Lm_, Lb) / Lmed, 0.35, 1.0)   # koyulasma yalniz dusuk frekans (yansima lekesi tasarimi bolmesin)
Ad = np.clip(LGs - Lmed, 0, 255) * 0.9                    # 2. inceleme bulgu 4: genis parlaklik da eklenir (cam parlakligi)
Sm = np.maximum(Sm, 0.85 if AD.startswith("kart") else 0.35)  # bulgu 3: kartta yansima deseni golge olmasin
_dr0 = np.hypot(xx - gx_, yy - gy_)
Ad *= np.clip((_dr0 - 1.7 * ghr) / (0.4 * ghr), 0, 1)         # inceleme 1: delik cevresinde hale yok

_P = cv2.imread(BASKI, cv2.IMREAD_UNCHANGED)
if _P.ndim == 3 and _P.shape[2] == 4:     # 8 Kas inceleme: SADE_ALTIN (White) saydam PNG; beyaz seramige bindirilir (yari saydam kenar koyu kalmasin)
    _a = _P[:, :, 3:4].astype(np.float32) / 255
    _P = _P[:, :, :3].astype(np.float32) * _a + 255.0 * (1 - _a)
P = np.asarray(_P, np.float32)[:, :, ::-1].copy()
Pw = np.clip(cv2.warpAffine(P, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE), 0, 255)
out = Pw * Sm[..., None] + Ad[..., None] * np.array([1.0, 0.97, 0.95], np.float32)
hpG = (LG - cv2.GaussianBlur(LG, (0, 0), 2.0))[(mask == 0)]
rng = np.random.default_rng(5)
out += rng.normal(0, float(np.std(hpG)) * 0.8, out.shape).astype(np.float32)

dr = np.hypot(xx - nhx, yy - nhy)
delik = np.clip(hr + 0.5 - dr, 0, 1)
ipa = np.clip(cv2.GaussianBlur(ip.astype(np.float32), (0, 0), 0.7) * 1.3, 0, 1)   # t4-Y3: kenar yumusatma ip disina AI tasimasin
Gh, Gi = G, G
res = G * (1 - yuz[..., None]) + out * yuz[..., None]
res = res * (1 - delik[..., None]) + Gh * delik[..., None]
ipa_y = ipa                      # yuz disinda zaten sahne; kenarda koyu cizgi olusmasin
res = res * (1 - ipa_y[..., None]) + Gi * ipa_y[..., None]
img = Image.fromarray(np.clip(res, 0, 255).astype(np.uint8))

# kart yazisi (G1: yazi kodla; metin mevcut galeri kart 4 / alt metin ornament_metin.py:114)
if AD == "kart":
    # SADE tipografi (yd_kart_ornek.py:140-142): baslik Cormorant 500 170, etiket Manrope 600 68, metin Manrope 400 64; murekkep #2B2220
    FD = os.environ.get("FONT_DIR", str(__import__("pathlib").Path(__file__).resolve().parents[2] / "kapak78" / "yd_kart" / "fonts")) + "/"

    def font(dosya, boy, agirlik):
        f = ImageFont.truetype(FD + dosya, boy)
        f.set_variation_by_axes([agirlik])
        return f
    baslik, etk, gov = font("CormorantGaramond.ttf", 170, 500), font("Manrope.ttf", 68, 600), font("Manrope.ttf", 64, 400)
    d = ImageDraw.Draw(img)
    RENK = (43, 34, 32)
    x0, gen_max = 1880, 1000

    def sar(metin, f):
        kel, sat, cur = metin.split(" "), [], ""   # \u00a0 bolunmez bosluk
        for k in kel:
            dene = (cur + " " + k).strip()
            if f.getlength(dene) <= gen_max:
                cur = dene
            else:
                sat.append(cur); cur = k
        sat.append(cur)
        return sat
    satirlar = [("Round Ceramic", "2.99\u00a0in\u00a0(7.6\u00a0cm)\u00a0across, 0.1\u00a0in\u00a0(2.5\u00a0mm)\u00a0thick"),
                ("Both Sides", "The same design on both sides, glossy finish"),
                ("String Included", "Gold-colored string")]
    blok = []
    for e_, g2 in satirlar:
        blok.append((e_, sar(g2, gov)))
    yuk = 170 * 1.15 + 90 + sum(68 * 1.2 + len(s_) * 64 * 1.32 + 70 for _, s_ in blok)
    y = (H - yuk) / 2
    d.text((x0, y), "Size & Details", font=baslik, fill=RENK); y += 170 * 1.15 + 90
    for e_, s_ in blok:
        d.text((x0, y), e_, font=etk, fill=RENK); y += 68 * 1.2 + 6
        for ss in s_:
            d.text((x0, y), ss, font=gov, fill=RENK); y += 64 * 1.32
        y += 70
    assert max(gov.getlength(ss) for _, s_ in blok for ss in s_) <= gen_max and x0 + gen_max < W - 80
img.save(f"SET_{AD}.jpg", quality=95, subsampling=0)
if os.environ.get("CIKIS_PNG"):
    img.save(os.environ["CIKIS_PNG"])
rap = dict(ad=AD, R=round(R, 1), donme_der=round(float(np.rad2deg(phi)), 2), delik_bizim=[round(float(nhx), 1), round(float(nhy), 1), round(hr, 1)],
           delik_ai=delik_ai, ip_kayma=round(float(np.hypot(dkx, dky)), 1), delik_olcek=round(float(s_loc), 3),
           Sm_min=round(float(Sm[yuz > 0.99].min()), 3), Ad_max=round(float(Ad[yuz > 0.99].max()), 1), ip_px=int(ip.sum()))
json.dump(rap, open(f"SET_{AD}.json", "w"), indent=1)
print(rap)
