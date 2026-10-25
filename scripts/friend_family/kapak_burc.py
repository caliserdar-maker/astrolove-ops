"""Kapak: 'YOUR ZODIAC SIGNS' yerine '<BURC1> & <BURC2>' (Serdar 25 Eki). Yazi tipi olcumle secildi: Cormorant Garamond 700 (IoU en yuksek)."""
import sys, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from kart_duzelt import zemin_doldur
KAP = "/mnt/user-data/attachments/f7c170a6-59b5-5b85-ad08-da97d1f9d029/45f81fa5-image.png"
FONT = "font/cormorant-garamond-latinext-700-normal.ttf"
A = np.asarray(Image.open(KAP).convert("RGB")).astype(np.float32); H, W = A.shape[:2]
fg = A.mean(2) > 150
S1 = (26, 73, 420, 1030)     # YOUR ZODIAC SIGNS  (y0,y1,x0,x1)
S2 = (85, 131, 370, 1085)    # UNITED IN ONE SYMBOL
renk = np.median(A[86:131, 370:1085][fg[86:131, 370:1085]], 0)
CAP = 39
# orijinal satir 2: dogal genislik 647 -> 689 (olcum): harf araligi orani
def yaz(txt, cap=CAP, iz=None):
    f = ImageFont.truetype(FONT, 57)
    if iz is None:
        g = ImageFont.truetype(FONT, 57); w0 = g.getlength("UNITED IN ONE SYMBOL"); iz = (689 * 57 / 57 - w0) / (len("UNITED IN ONE SYMBOL") - 1)
    im = Image.new("L", (2600, 200), 0); d = ImageDraw.Draw(im); x = 20
    for ch in txt:
        d.text((x, 40), ch, font=f, fill=255); x += f.getlength(ch) + iz
    a = np.asarray(im).astype(np.float32) / 255
    ys, xs = np.where(a > 0.5); a = a[ys.min():ys.max() + 1, xs.min() - 2:xs.max() + 3]
    sc = cap / a.shape[0]
    return cv2.resize(a, (int(a.shape[1] * sc), cap), interpolation=cv2.INTER_AREA)
def bas(B, a, yc, cx=W // 2):
    h, w = a.shape; y0 = int(yc - h / 2); x0 = int(cx - w / 2)
    sh = cv2.GaussianBlur(a, (0, 0), 1.5) * 0.35
    B[y0 + 2:y0 + 2 + h, x0 + 1:x0 + 1 + w] *= (1 - sh[..., None])
    B[y0:y0 + h, x0:x0 + w] = B[y0:y0 + h, x0:x0 + w] * (1 - a[..., None]) + renk * a[..., None]
    return x0, x0 + w
def sil(A, kutular):
    m = np.zeros((H, W), bool)
    for y0, y1, x0, x1 in kutular: m[y0:y1, x0:x1] = True
    return zemin_doldur(A, m, (60, 330, 260, 430))
def uret(b1, b2, sira, out):
    txt = f"{b1} & {b2}"
    if sira == "ust":
        B = sil(A, [S1]); x = bas(B, yaz(txt), (S1[0] + S1[1]) / 2 + 1)
    else:
        B = sil(A, [S1, S2])
        l2 = A[S2[0]:S2[1], S2[2]:S2[3]]; m2 = cv2.GaussianBlur((fg[S2[0]:S2[1], S2[2]:S2[3]]).astype(np.float32), (0, 0), 0.6)
        m2 = np.clip(cv2.dilate(m2, np.ones((3, 3))) , 0, 1)[..., None]
        dy = -59; B[S2[0] + dy:S2[1] + dy, S2[2]:S2[3]] = B[S2[0] + dy:S2[1] + dy, S2[2]:S2[3]] * (1 - m2) + l2 * m2
        x = bas(B, yaz(txt), (S2[0] + S2[1]) / 2)
    Image.fromarray(np.clip(B, 0, 255).astype(np.uint8)).save(out); print(out, "burc satiri x", x)
if __name__ == "__main__":
    uret("CANCER", "TAURUS", "ust", "kapak_burc_ust.png")
    uret("CANCER", "TAURUS", "alt", "kapak_burc_alt.png")
    uret("SAGITTARIUS", "CAPRICORN", "ust", "kapak_uzun_test.png")
