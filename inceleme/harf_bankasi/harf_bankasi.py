#!/usr/bin/env python3
"""HARF BANKASI PILOTU (Serdar onerisi, 1 Eki): isim glifleri bir kez uretilir, sipariste yan yana dizilir.

Onayli hat (siparis_dosyasi.plaka_ss): ciz_metin harf harf cizer (ilerleme = font.getlength(c) + tracking,
tracking = s4 * -0.0388; cift kerning UYGULANMAZ), SS=4 kutu ortalamasi, >40 kirpim, altin_isim (kelime boyu TEK
dikey profil). Banka: ayni fontla (Cinzel, ISIM_W) her harf AYRI cizilir ve saklanir (maske + koken ofseti);
dizim harfi Pillow'un yaptigi gibi tam sayi x'e (s4 izgarasi, yarim yukari) koyar ve ayni karisim formuluyle
(Pillow BLEND) birlestirir. Kalan adimlar (SS indirme, kirpim, altin) onayli kodun aynisi. Altin efekt kelime
boyu oldugu icin bankada YOK; dizimden sonra uygulanir.
"""
import sys, time
import numpy as np
from PIL import Image, ImageDraw

KISISEL = '/home/user/kv/scripts/kisisel'
sys.path.insert(0, KISISEL); sys.path.insert(0, '/home/user/v1-wt/scripts/medya_v1')
import pilot12, pilot6                                             # noqa: E402
from kisisel_pilot import font_yukle, bbox_of                     # noqa: E402
import siparis_dosyasi as sd                                      # noqa: E402

HARFLER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ -'
SS = sd.ISIM_SS
PAD = 200


class HarfBankasi:
    def __init__(self, s4, harfler=HARFLER):
        self.s4 = s4
        self.font = font_yukle(pilot12.FONT_DIR / pilot6.ISIM_FONT, s4, pilot6.ISIM_W)
        self.H = int(self.font.size * 2.6) + 2 * PAD
        self.g = {}
        for c in harfler:
            w = int(self.font.getlength(c)) + 2 * PAD
            im = Image.new('L', (max(w, 10), self.H), 0)
            ImageDraw.Draw(im).text((PAD, PAD), c, fill=255, font=self.font)
            a = np.asarray(im)
            bb = bbox_of(a > 0)
            if bb is None:                                        # bosluk: yalniz ilerleme
                self.g[c] = (None, 0, 0, self.font.getlength(c)); continue
            x0, y0, x1, y1 = bb
            self.g[c] = (a[y0:y1, x0:x1].astype(np.uint16), x0 - PAD, y0 - PAD, self.font.getlength(c))

    def diz(self, metin, tracking):
        """ciz_metin ile ayni sozlesme: kirpilmis L maske (np.uint8) ve bbox."""
        W = int(sum(self.g[c][3] for c in metin) + tracking * max(len(metin) - 1, 0) + 2 * PAD)
        tuval = np.zeros((self.H, max(W, 10)), np.uint16)
        x = float(PAD)
        for c in metin:
            m, ox, oy, ilerle = self.g[c]
            if m is not None:
                X, Y = int(np.floor(x + 0.5)) + ox, PAD + oy
                h, w = m.shape
                t = tuval[Y:Y + h, X:X + w]
                # Pillow BLEND (ink 255): tmp = (255 - in) * m + 128; out = in + (((tmp >> 8) + tmp) >> 8)
                tmp = (255 - t) * m + 128
                tuval[Y:Y + h, X:X + w] = t + (((tmp >> 8) + tmp) >> 8)
            x += ilerle + tracking
        a = tuval.astype(np.uint8)
        bb = bbox_of(a > 40)
        x0, y0, x1, y1 = bb
        return a[y0:y1, x0:x1], bb


def plaka_banka(banka, metin, prof):
    """plaka_ss'in banka surumu (tam / boy disaridan: banka zaten o s4'te)."""
    a = banka.diz(metin, banka.s4 * -0.0388)[0].astype(np.float32)
    h, w = a.shape
    H, Wd = -(-h // SS) * SS, -(-w // SS) * SS
    b = np.zeros((H, Wd), np.float32); b[:h, :w] = a
    m = b.reshape(H // SS, SS, Wd // SS, SS).mean(axis=(1, 3))
    ys, xs = np.nonzero(m > 40)
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return pilot12.altin_isim(Image.fromarray(np.clip(m, 0, 255).astype(np.uint8)), prof)
