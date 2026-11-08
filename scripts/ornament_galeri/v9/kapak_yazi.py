# kapak_yazi.py (7 Kas, v2) - kapak: %8 yakinlastirma (ust sabit; alttan ve yanlardan kirpma) + baslik.
# Serdar: ust satir burc adlari "&" ile, alt satir urun (2 kelime); yazi buyuk; alt satir baslik ile disk ustu arasinda dikeyde ortali;
# ipin onunde yazi okunmuyor -> satirlar ip kelime boslugundan bolunur (hicbir harf ipe binmez).
# Tipografi A (set kartlari): Cormorant Garamond 500 + Manrope 600 harf aralikli; krem yazi + dar yumusak golge.
# kullanim: python kapak_yazi.py giris.jpg giris.json cikis.jpg
import sys, json, os
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

GIR, JS, CIK = sys.argv[1], sys.argv[2], sys.argv[3]
YAKIN = 1.08
UST_S, ALT_S = (os.environ.get("BASLIK", "Cancer & Libra"), os.environ.get("ALT", "PERSONALIZED ORNAMENT"))
ALT_OLCU = "PERSONALIZED ORNAMENT"   # 8 Kas: stil gorsellerinde alt satir punto kapakla ayni (olcu kapak alt satirindan)
KREM, GOLGE = (252, 248, 240), (28, 14, 10)
F1 = os.environ.get("FONT_DIR", str(__import__("pathlib").Path(__file__).resolve().parents[2] / "kapak78" / "yd_kart" / "fonts")) + "/"
BANT = (800, 2200)                       # Etsy kirpim kesisimi (kapak_ornek.py BANT)


def font(yol, px, ag):
    f = ImageFont.truetype(yol, px); f.set_variation_by_axes([ag]); return f


def yakinlas(a, s=YAKIN):
    H, W = a.shape[:2]
    b = cv2.resize(a, (round(W * s), round(H * s)), interpolation=cv2.INTER_LANCZOS4)
    x0 = (b.shape[1] - W) // 2
    return b[:H, x0:x0 + W]


J = json.load(open(JS))
hx, hy, hr = J["delik_bizim"]; R = J["R"]
im0 = np.asarray(Image.open(GIR).convert("RGB"))
H, W = im0.shape[:2]
a = yakinlas(im0)
x0 = (round(W * YAKIN) - W) // 2
ipx = hx * YAKIN - x0
disk_ust = (hy + 0.699 * R - R) * YAKIN
# ip genisligi (baslik yuksekliginde, altin pikseller ipx +- 80 px)
r_, g_, b_ = [a[..., k].astype(np.float32) for k in range(3)]
alt = ((g_ - b_) > 30) & (r_ > 110)
bol = alt[40:int(disk_ust) - 20, int(ipx) - 80:int(ipx) + 80]
sut = np.where(bol.mean(0) > 0.3)[0]
ip0, ip1 = int(ipx) - 80 + sut.min(), int(ipx) - 80 + sut.max()
PAY = 34


def bol_ciz(metin, f, y, d, iz=0.0, ciz=True):
    """satiri ip kelime boslugundan boler: en iyi bosluk = satir merkezi 1500'e en yakin; doner (ok, kutu)"""
    kel = metin.split(" ")
    def gen(s):
        return sum(f.getlength(c) for c in s) + round(f.size * iz) * (len(s) - 1)
    en = None
    for i in range(1, len(kel)):
        sol, sag = " ".join(kel[:i]), " ".join(kel[i:])
        xs = ip0 - PAY - gen(sol); xe = ip1 + PAY + gen(sag)
        if xs < BANT[0] or xe > BANT[1]:
            continue
        m = abs((xs + xe) / 2 - 1500)
        if en is None or m < en[0]:
            en = (m, sol, sag, xs)
    if en is None:
        return False, None
    if ciz:
        _, sol, sag, xs = en
        for parca, x in ((sol, xs), (sag, ip1 + PAY)):
            for c in parca:
                d.text((x, y), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + round(f.size * iz)
    return True, en


BOL = os.environ.get("BOL", "0") == "1"       # 7 Kas Serdar: ip dugumun biraz ustunden kademeli biter -> yazi ortali, bolme yok


def orta_ciz(metin, f, y, d, iz=0.0, ciz=True):
    g = sum(f.getlength(c) for c in metin) + round(f.size * iz) * (len(metin) - 1)
    xs = (W - g) / 2
    if xs < BANT[0]:
        return False, None
    if ciz:
        x = xs
        for c in metin:
            d.text((x, y), c, font=f, fill=255, anchor="ls"); x += f.getlength(c) + round(f.size * iz)
    return True, (xs, xs + g)


if not BOL:
    bol_ciz = orta_ciz
# punto: bant icine sigan en buyuk (baslik 240'tan, alt satir 78'den asagi)
kat = Image.new("L", (W, H), 0); d = ImageDraw.Draw(kat)
b1 = 240
while not bol_ciz(UST_S, font(F1 + "CormorantGaramond.ttf", b1, 500), 0, d, ciz=False)[0]:
    b1 -= 2
b2 = 78
while not bol_ciz(ALT_OLCU, font(F1 + "Manrope.ttf", b2, 600), 0, d, iz=0.16, ciz=False)[0]:
    b2 -= 2
f1, f2 = font(F1 + "CormorantGaramond.ttf", b1, 500), font(F1 + "Manrope.ttf", b2, 600)
# dikey: baslik ustu 70 px; alt satir baslik alti ile disk ustu arasinda ortali
asc1 = f1.getbbox("CL")[1]; y1 = 70 - asc1 + f1.getbbox("CL")[3] - f1.getbbox("CL")[1] + asc1   # taban cizgisi
cap2 = f2.getbbox("PO")[3] - f2.getbbox("PO")[1]
alt1 = y1 + (f1.getbbox("g")[3] - f1.getbbox("C")[3]) * 0.0                                          # baslik taban cizgisi (inis harfi yok sayilir)
y2 = (alt1 + disk_ust) / 2 + cap2 / 2                                                                # alt satir: taban cizgisi, ortalama icin buyuk harf yuksekligi
bol_ciz(UST_S, f1, y1, d)
bol_ciz(ALT_S, f2, y2, d, iz=0.16)
# ip soldurma: dugum ust kenari (ip genisliginin 1,5 katina cikan ilk satir), yazi alt kenari +15 px'te ip 0, dugumun 15 px ustunde 1
bb0 = kat.getbbox(); yazi_alt = bb0[3]
if not BOL:
    gen_ = alt[:int(disk_ust), int(ipx) - 80:int(ipx) + 80].sum(1).astype(np.float32)
    med = np.median(gen_[int(yazi_alt):int(disk_ust) - 60])
    dug = int(yazi_alt) + int(np.argmax(gen_[int(yazi_alt):int(disk_ust)] > 1.5 * med))
    y0f, y1f = dug - 8, dug + 3                     # Serdar: ip tam dugum bitiminde sonlansin (kisa yumusak kenar)
    ipm = np.zeros((H, W), np.uint8)
    ipm[:int(disk_ust), ip0 - 16:ip1 + 17] = 1                     # ipin tum seridi (soluk ip pikselleri de; arka plan bulanik bokeh)
    arka = cv2.inpaint(a, ipm, 15, cv2.INPAINT_TELEA)
    arka = np.where(ipm[..., None] > 0, cv2.GaussianBlur(arka, (0, 0), 10), arka)
    yy_ = np.arange(H, dtype=np.float32)[:, None]
    gor = np.clip((yy_ - y0f) / (y1f - y0f), 0, 1); gor = gor * gor * (3 - 2 * gor)          # ipin gorunurlugu
    sil = cv2.GaussianBlur(ipm.astype(np.float32), (0, 0), 4) * (1 - gor)
    a = (a.astype(np.float32) * (1 - sil[..., None]) + arka.astype(np.float32) * sil[..., None]).astype(np.uint8)
    print(dict(dugum_ust=dug, ip_kaybolur=round(y0f), ip_tam=round(y1f)))
k = np.asarray(kat, np.float32) / 255
g1 = np.asarray(kat.filter(ImageFilter.GaussianBlur(10)), np.float32) / 255
g2 = np.asarray(kat.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255
g0 = np.asarray(kat.filter(ImageFilter.GaussianBlur(22)), np.float32) / 255                       # Serdar "biraz daha golge": genis yumusak katman eklendi
g = 1 - (1 - np.clip(np.roll(g1, (9, 4), (0, 1)) * 0.95, 0, 1)) * (1 - np.clip(np.roll(g2, (3, 1), (0, 1)) * 0.8, 0, 1)) \
    * (1 - np.clip(np.roll(g0, (12, 5), (0, 1)) * 0.55, 0, 1))
o = a.astype(np.float32)
o = o * (1 - g[..., None]) + np.array(GOLGE, np.float32) * g[..., None]
# Serdar: yazilar urunun icindeki altin dokusuyla. Palet onayli baskinin altin piksellerinden (CANCER_LIBRA_RUBY_954.png, parlaklik
# yuzdelikleri 2/10/25/50/75/90/98); kabartma: yukseklik haritasi + sol ust isik (baskidaki gibi koyu kenar, parlak ust bant)
PAL = np.array([[125, 74, 3], [143, 91, 5], [161, 105, 18], [191, 130, 25], [212, 152, 34], [228, 191, 67], [240, 223, 94]], np.float32)
PQ = np.array([0.02, 0.10, 0.25, 0.50, 0.75, 0.90, 0.98], np.float32)
def altin_boya(k):
    h = cv2.GaussianBlur(k, (0, 0), 3.0)
    gx = cv2.Sobel(h, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(h, cv2.CV_32F, 0, 1, ksize=3)
    isik = -(gx * -0.6 + gy * -0.8) * 6.0                           # sol ust isik
    ic = cv2.GaussianBlur(k, (0, 0), 1.2)
    t = np.clip(0.42 + 0.30 * (ic - 0.5) + isik, 0.0, 1.0)
    rgb = np.stack([np.interp(t, PQ, PAL[:, c]) for c in range(3)], -1)
    return rgb.astype(np.float32)
RENK_MOD = os.environ.get("RENK", "krem2")      # Serdar: altin olmadi, "cok acik krem"
RENK = altin_boya(k) if RENK_MOD == "altin" else np.broadcast_to(np.array((247, 236, 214), np.float32), k.shape + (3,)).copy()   # cok acik krem (onceki 252,248,240'tan sicak)
o = o * (1 - k[..., None]) + RENK * k[..., None]
Image.fromarray(np.clip(o, 0, 255).astype(np.uint8)).save(CIK, quality=95, subsampling=0)
if os.environ.get("KATMAN"):                    # video icin: ip soldurma ve yazi katmanlari (ayni geometri)
    np.savez_compressed(os.environ["KATMAN"], sil=sil.astype(np.float16), arka=arka, k=k.astype(np.float16), g=g.astype(np.float16), renk=RENK.astype(np.uint8),
                        yakin=YAKIN, krem=np.array(KREM), golge=np.array(GOLGE))
bb = kat.getbbox()
ipe = (k[:, ip0:ip1 + 1] > 0.05).sum()
print(dict(punto=(b1, b2), ip=(ip0, ip1), kutu=bb, disk_ust=round(disk_ust), baslik_taban=round(y1), alt_taban=round(y2),
           ipe_binen_yazi_px=int(ipe), disk_alt=round((hy + 0.699 * R + R) * YAKIN)))
