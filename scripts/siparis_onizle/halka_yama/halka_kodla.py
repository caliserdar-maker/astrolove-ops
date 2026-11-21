"""Midnight Blue son kodlama (19 Kas 2026, GOREV_CEO_DENETIM_HALKA_KALICI C). Yalniz HALKA_DUZELT=1 iken cagrilir (olcu.yaz, teslim_jpg.yaz,
renk_uyum). SON piksel adimi ve SON kodlama; sonrasinda JPEG yeniden kodlama YOK.
Kayan nokta RGB -> YCbCr (JFIF tam aralik BT.601, cozucuyle ayni) -> zeminde (agirlik) kanal basina TPDF (+-1) + kroma Gauss gurultusu
(sigma KROMA_SIGMA, Cb ve Cr) -> 8 bit -> Image(...,'YCbCr') q100 (nicemleme tablolari tum 1), 4:4:4, 300 dpi.
Neden kroma gurultusu (olcum, rapor C): motor greni uc kanala ortak oldugu icin Cb/Cr'de gurultu yok; yalniz TPDF ile q100 kodlama bile
halka birakiyor (temiz zemin, Merkez yumusatma + ortak gren + YCbCr TPDF: halka bandi 0.0665). Kroma sigma 0.5 / 1.0 / 1.5:
0.0453 / 0.0207 / 0.0089. Secim 1.0 (temiz 8 bit + YCbCr TPDF duzeyi 0.0215 ile ayni). Ogelerde (agirlik 0) kroma gurultusu yok.
Pillow libjpeg-turbo (trellis yok; ycc_tablolari ile denetlenir)."""
import numpy as np
from PIL import Image

YCC = np.array([[0.299, 0.587, 0.114], [-0.168736, -0.331264, 0.5], [0.5, -0.418688, -0.081312]], np.float32)
KROMA_SIGMA = 1.0


def tablolar(luma_q=100, kroma_adim=1):
    """Nicemleme tablolari (21 Kas, dijital 20 MB): luma = libjpeg standart tablosu `luma_q` kalitesinde (100 = tum 1), kroma = duz
    `kroma_adim` (halka kroma nicemlemesinden geliyordu: standart kroma tablosu YOK). Pillow'un kendi urettigi tablo geri okunur
    (sira donusumu Pillow'da; kesit_olcum.onizleme_yap ile ayni yontem)."""
    import io
    if luma_q >= 100:
        luma = [1] * 64
    else:
        b = io.BytesIO(); Image.new("RGB", (8, 8)).save(b, "JPEG", quality=int(luma_q)); luma = list(Image.open(b).quantization[0])
    return [luma, [int(kroma_adim)] * 64, [int(kroma_adim)] * 64]


def ycc_kaydet(rgb, yol, rng, agirlik=None, kroma_sigma=KROMA_SIGMA, icc=None, qtables=None):
    """rgb: HxWx3 kayan nokta sRGB 0-255; agirlik: HxW (1 = zemin, kroma gurultusu tam; 0 = oge) ya da None (her yer zemin).
    qtables: None = q100 (tum 1, bugunku yol, bayt bayt ayni); verilirse tablolar(...) ciktisi (dijital 20 MB kodlamasi)."""
    H = rgb.shape[0]; ycc8 = np.empty(rgb.shape, np.uint8)
    for y0 in range(0, H, 1200):
        s = rgb[y0:y0 + 1200].astype(np.float32) @ YCC.T; s[..., 1:] += 128
        ag = None if agirlik is None else np.asarray(agirlik[y0:y0 + 1200], np.float32)[..., None]
        tp = rng.random(s.shape, dtype=np.float32) - rng.random(s.shape, dtype=np.float32)
        s += tp if ag is None else tp * ag                           # inceleme G ORTA 14: titresim yalniz zeminde, ogeler yalniz yuvarlanir
        if kroma_sigma:
            g = rng.standard_normal(s[..., 1:].shape, dtype=np.float32) * kroma_sigma
            s[..., 1:] += g if ag is None else g * ag
        ycc8[y0:y0 + 1200] = np.clip(np.rint(s), 0, 255).astype(np.uint8)
    k = dict(quality=100, subsampling=0, dpi=(300, 300)) if qtables is None else dict(qtables=qtables, subsampling=0, dpi=(300, 300))
    if icc:
        k['icc_profile'] = icc
    Image.fromarray(ycc8, 'YCbCr').save(yol, 'JPEG', **k)


def kaynak_yolu(yol):
    return str(yol)[:-4] + '_REF.png'


def kaynak_yaz(rgb, yol):
    """Halka kapisinin kaynagi: kodlama ONCESI kayan nokta goruntunun 8 bit (rint) PNG'si, yol[:-4] + '_REF.png'. Teslim EDILMEZ (adi
    AstroLoveArt_*.jpg kalibina uymaz; uretim klasorunde kalir). halka_kapi --kaynak ile kodlamanin ekledigi halkayi olcer."""
    Image.fromarray(np.clip(np.rint(rgb), 0, 255).astype(np.uint8)).save(kaynak_yolu(yol), compress_level=1)


def onizleme(rgb, yol, rng, agirlik=None, uzun=2000, icc=None, kaynak=False):
    """Musteri onizlemesi: kayan noktada LANCZOS (kanal basina), uzun kenar `uzun`, ayni ycc_kaydet. kaynak=True: kodlama oncesi
    onizleme de _REF.png olarak yazilir (halka kapisi). Doner [w, h]."""
    H, W = rgb.shape[:2]; f = uzun / max(H, W); hw = (round(W * f), round(H * f))
    kan = [np.asarray(Image.fromarray(np.ascontiguousarray(rgb[..., c], dtype=np.float32), 'F').resize(hw, Image.LANCZOS)) for c in range(3)]
    ag = None if agirlik is None else np.asarray(Image.fromarray(np.asarray(agirlik, np.float32), 'F').resize(hw, Image.BOX))
    on = np.clip(np.stack(kan, -1), 0, 255)
    if kaynak:
        kaynak_yaz(on, yol)
    ycc_kaydet(on, yol, rng, agirlik=ag, icc=icc)
    return list(hw)


def ycc_tablolari(yol):
    """Denetim: kayitli dosyanin nicemleme tablolari tum 1 mi, ornekleme 4:4:4 mu."""
    from PIL import JpegImagePlugin
    with Image.open(yol) as im:
        q = im.quantization
        return dict(tum_1=all(set(v) == {1} for v in q.values()), tablo_sayisi=len(q), ornekleme_444=JpegImagePlugin.get_sampling(im) == 0)
