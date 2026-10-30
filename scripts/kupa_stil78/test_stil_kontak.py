#!/usr/bin/env python3
"""stil_kontak.py testi: 624 tam set PASS (8 pafta), bir eksik ve bir tanimsiz dosya FAIL. Ag yok."""
import sys
import tempfile
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stil_kontak  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as t:
        d, o = Path(t) / "in", Path(t) / "out"
        d.mkdir()
        im = Image.new("RGB", (40, 30), (120, 80, 40))
        for c in stil_kontak.ciftler():
            for no, s in stil_kontak.STILLER:
                im.save(d / f"KUPA_STIL_{c}_{no}_{s}.jpg")
        assert stil_kontak.main(["--dir", str(d), "--out", str(o)]) == 0
        paftalar = sorted(p.name for p in o.glob("KONTAK_*.jpg"))
        assert len(paftalar) == 8 and paftalar[0] == "KONTAK_07_ORANGE.jpg", paftalar
        assert (o / "OZET.md").read_text().splitlines()[2].startswith("PASS | dosya 624/624")
        (d / "KUPA_STIL_LEO_LEO_10_POMEGRANATE.jpg").unlink()
        assert stil_kontak.main(["--dir", str(d), "--out", str(o)]) == 1
        assert "LEO_LEO 10 POMEGRANATE" in (o / "OZET.md").read_text()
        im.save(d / "KUPA_STIL_LEO_LEO_10_POMEGRANATE.jpg")
        im.save(d / "KUPA_STIL_LEO_LEO_15_KIWI.jpg")
        assert stil_kontak.main(["--dir", str(d), "--out", str(o)]) == 1
    print("test_stil_kontak PASS")


if __name__ == "__main__":
    main()
