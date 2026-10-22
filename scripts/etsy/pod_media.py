#!/usr/bin/env python3
"""
POD ilan medyasi ortak yardimcilari (EK 3, Mo 6 Eyl 2026): teknik kartlar + video.

- Kaynak (Drive): WALL_ART/LISTING_MEDIA/TECHNICAL/02_SYMBOL_STORY/<ED>/WA_02_TECH_SYMBOL_STORY_<PAIR>_<ED>.png
                  WALL_ART/LISTING_MEDIA/TECHNICAL/05_CRAFTED_DETAIL/<ED>/WA_05_TECH_CRAFTED_DETAIL_<PAIR>_<ED>.jpg
                  WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/01_EXPORTS/<ED>/WA_VIDEO_V01_<PAIR>_<ED>.mp4
  Yerelde: <media>/<PAIR>/<dosya adi>.
- Galeri sirasi (12): 1 hero, 2-3 sahne, 4 Symbol Story, 5 Crafted Detail, 6 Paper, 7 Size Guide,
  8 Shipping & Care, 9-12 diger edisyon hero. Video 1 adet (ana edisyon, 1080x1350).
- ON KONTROL: kart metninde dijitale ozgu ifade (download, instant, print at home, JPG/PDF, file)
  varsa kart yuklenmez (tesseract OCR; olculebilir: eslesen kelime listesi bos = PASS).
"""
import re
import shutil
import struct
import subprocess
from pathlib import Path

CARD_FILES = {"SYMBOL": "WA_02_TECH_SYMBOL_STORY_{pair}_{ed}.png",
              "CRAFTED": "WA_05_TECH_CRAFTED_DETAIL_{pair}_{ed}.jpg"}
CARD_DRIVE = {"SYMBOL": "WALL_ART/LISTING_MEDIA/TECHNICAL/02_SYMBOL_STORY/{ed}",
              "CRAFTED": "WALL_ART/LISTING_MEDIA/TECHNICAL/05_CRAFTED_DETAIL/{ed}"}
VIDEO_FILE = "WA_VIDEO_V01_{pair}_{ed}.mp4"
VIDEO_DRIVE = "WALL_ART/LISTING_MEDIA/VIDEOS/V01_FIREFLY_STORY/01_EXPORTS/{ed}"
VIDEO_WH = (1080, 1350)
CARD_RANK = {"SYMBOL": 4, "CRAFTED": 5}
# dijitale ozgu ifadeler (Mo EK 3): download, instant, print at home, JPG/PDF, file
FORBIDDEN = re.compile(r"download|instant|print\s*at\s*home|\bjpe?g\b|\bpdf\b|\bfiles?\b", re.I)


def card_path(media_root, pair, ed, kind):
    p = Path(media_root) / pair / CARD_FILES[kind].format(pair=pair, ed=ed)
    return p if p.exists() else None


def video_path(media_root, pair, ed):
    p = Path(media_root) / pair / VIDEO_FILE.format(pair=pair, ed=ed)
    return p if p.exists() else None


def ocr_text(path):
    """tesseract ile metin; tesseract yoksa None (kontrol yapilamadi)."""
    if not shutil.which("tesseract"):
        return None
    r = subprocess.run(["tesseract", str(path), "-", "--psm", "3"], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise SystemExit(f"HATA: tesseract {path}: {r.stderr[:200]}")
    return r.stdout


def precheck_card(path):
    """(metin_kelime_sayisi, [yasakli eslesmeler]) - bos liste = PASS. OCR yoksa (None, None)."""
    txt = ocr_text(path)
    if txt is None:
        return None, None
    words = [w for w in re.split(r"\s+", txt) if w.strip()]
    hits = sorted({m.group(0).lower() for m in FORBIDDEN.finditer(txt)})
    return len(words), hits


def mp4_dims(path):
    """MP4 moov/trak/tkhd genislik-yukseklik (ffprobe gerekmez). Bulunamazsa None."""
    data = Path(path).read_bytes()

    def boxes(buf, start, end):
        i = start
        while i + 8 <= end:
            size, typ = struct.unpack(">I4s", buf[i:i + 8])
            hdr = 8
            if size == 1:
                size = struct.unpack(">Q", buf[i + 8:i + 16])[0]; hdr = 16
            elif size == 0:
                size = end - i
            if size < hdr:
                return
            yield typ, i + hdr, i + size
            i += size

    for typ, s, e in boxes(data, 0, len(data)):
        if typ != b"moov":
            continue
        for t2, s2, e2 in boxes(data, s, e):
            if t2 != b"trak":
                continue
            for t3, s3, e3 in boxes(data, s2, e2):
                if t3 != b"tkhd":
                    continue
                ver = data[s3]
                off = s3 + (4 + 32 if ver == 1 else 4 + 20) + 8 + 2 + 2 + 2 + 2 + 36
                w, h = struct.unpack(">II", data[off:off + 8])
                w, h = w >> 16, h >> 16
                if w and h:
                    return w, h
    return None


def img_sig(src, n=48):
    """Piksel imzasi: gri, n x n, float32 (0-255). src: yol ya da bytes."""
    import io
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(src) if isinstance(src, (bytes, bytearray)) else src)
    im = im.convert("L").resize((n, n), Image.LANCZOS)
    return np.asarray(im, dtype="float32")


def sig_diff(a, b):
    import numpy as np
    return float(np.abs(a - b).mean())
