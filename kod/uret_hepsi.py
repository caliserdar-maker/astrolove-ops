"""All 78 pairs: 5 posters + 5 cards (example names EMMA / JAMES) + 13 gallery images.
Usage: BY_ROOT=<package> python3 uret_hepsi.py [PAIR ...]   (no PAIR = all 78)
Output: <ROOT>/cikti/<PAIR>/{poster,kart,galeri}/  + <ROOT>/cikti/KONTAK_<n>.jpg contact sheets for eye QC.
"""
import os, sys, time, subprocess, csv
from PIL import Image
ROOT = os.environ.get("BY_ROOT", "/home/claude/by78")
HERE = os.path.dirname(os.path.abspath(__file__))
PAIRS = sys.argv[1:] or [r["cift"] for r in csv.DictReader(open(f"{ROOT}/BIZIM_YILIMIZ_78_ILAN_METIN.csv"))]
env0 = dict(os.environ, BY_ROOT=ROOT, NAME1="EMMA", NAME2="JAMES", DATE="14 JUNE 2025", LINE="YEAR ONE")
t0 = time.time()
for i, p in enumerate(PAIRS, 1):
    env = dict(env0, PAIR=p)
    for script in ("by_poster.py", "by_kart.py", "by_galeri.py"):
        r = subprocess.run([sys.executable, f"{HERE}/{script}"], env=env, capture_output=True, text=True)
        if r.returncode:
            print(f"\nHATA {p} {script}\n{r.stderr[-2000:]}")
            sys.exit(1)
    el = time.time() - t0
    print(f"{i}/{len(PAIRS)} {100 * i / len(PAIRS):.0f}% {p} gecen {el / 60:.1f} dk kalan {el / i * (len(PAIRS) - i) / 60:.1f} dk", flush=True)
# contact sheets: 6 pairs per sheet, row = 5 posters + 5 cards + cover
for k in range(0, len(PAIRS), 6):
    rows = []
    for p in PAIRS[k:k + 6]:
        b = f"{ROOT}/cikti/{p}"
        ims = [Image.open(f"{b}/poster/{n}_8x10.jpg").resize((240, 300)) for n in ("1_Starlit", "2_Timeless", "3_FirstPage", "4_Layers", "5_Botanical")]
        ims += [Image.open(f"{b}/kart/{n}_5x7.jpg").resize((214, 300)) for n in ("1_Starlit", "2_Timeless", "3_FirstPage", "4_Layers", "5_Botanical")]
        ims += [Image.open(f"{b}/galeri/01_Cover.jpg").resize((240, 300))]   # kapak = Layers posteri (4:5)
        rows.append(ims)
    wd = sum(m.width + 6 for m in rows[0])
    sheet = Image.new("RGB", (wd, len(rows) * 306), "white")
    for j, ims in enumerate(rows):
        x = 0
        for m in ims:
            sheet.paste(m, (x, j * 306)); x += m.width + 6
    sheet.save(f"{ROOT}/cikti/KONTAK_{k // 6 + 1:02d}.jpg", quality=85)
print("tamam")
