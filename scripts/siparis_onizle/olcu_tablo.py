"""Olcu tablosu, TEK KAYNAK = halka_yama/olcu.py (motor_gpt/olcu.py d2b414ee ile ayni sozluk; 21 Kas, GOREV SIPARIS_HATTI_DIJITAL 4).
olcu.py motor bagimliliklari (cv2, motor yolu) olmadan okunur: OLCU ve AILE sozlukleri ast ile dosyadan alinir (kopya tablo YOK).
PX[olcu] = (genislik, yukseklik) 300 dpi piksel; AILE[olcu] = oran ailesi. Belge: docs/OLCU_TABLOSU.md (olcu_tablo.py --yaz ile uretilir,
test_olcu_tablo.py belge == kaynak kontrol eder).
Kullanim: olcu_tablo.py [--yaz BELGE_YOLU]"""
import ast
import sys
from pathlib import Path

KAYNAK = Path(__file__).resolve().parent / "halka_yama" / "olcu.py"


def _sozluk(ad):
    for d in ast.parse(KAYNAK.read_text(encoding="utf-8")).body:
        if isinstance(d, ast.Assign) and any(isinstance(t, ast.Name) and t.id == ad for t in d.targets):
            return ast.literal_eval(d.value)
    raise SystemExit(f"olcu_tablo: {ad} {KAYNAK} icinde yok")


PX = {k: tuple(v) for k, v in _sozluk("OLCU").items()}
AILE = dict(_sozluk("AILE"))
SIRA = ["5x7", "8x10", "11x14", "A4", "12x16", "16x20", "A3", "12x18", "18x24", "16x24", "A2", "20x30", "24x30", "24x36"]


def belge():
    eksik = sorted(set(PX) - set(SIRA)) + sorted(set(SIRA) - set(PX))
    if eksik:
        raise SystemExit(f"olcu_tablo: SIRA ile kaynak farkli: {eksik}")
    s = ["# Olcu tablosu (300 dpi piksel)", "",
         "Tek kaynak: `scripts/siparis_onizle/halka_yama/olcu.py` (`OLCU`, `AILE`; motor_gpt/olcu.py d2b414ee ile ayni). Bu belge",
         "`python3 scripts/siparis_onizle/olcu_tablo.py --yaz docs/OLCU_TABLOSU.md` ile uretilir; elle duzeltilmez",
         "(`test_olcu_tablo.py` belge ve kaynak farkliysa FAIL verir). Baski ve dijital ayni piksel olcusunu kullanir;",
         "fark yalniz dosya siniri (baski 100 MB, dijital 20 MB) ve dijitalde olcu basina kodlama (`halka_kodla.DIJITAL_KODLAMA`).", "",
         "| Olcu | Piksel (G x Y) | Oran ailesi | Megapiksel |", "|---|---|---|---|"]
    for o in SIRA:
        w, h = PX[o]
        s.append(f"| {o} | {w} x {h} | {AILE[o]} | {w * h / 1e6:.1f} |")
    return "\n".join(s) + "\n"


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--yaz" in a:
        Path(a[a.index("--yaz") + 1]).write_text(belge(), encoding="utf-8")
    else:
        sys.stdout.write(belge())
