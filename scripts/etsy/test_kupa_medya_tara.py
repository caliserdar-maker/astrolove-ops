"""kupa_medya_tara: mukerrer klasor, eksik/fazla galeri, haric. Ag erisimi yok."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kupa_medya_tara as m  # noqa: E402

G = ["01_Orange_Blossom_kapak", "02_Yakin_plan", "03_How_to_personalize", "04_Choose_your_style", "05_Two_sizes",
     "06_Names_and_message", "07_Care_and_making", "08_Purple_Fig", "09_Olive_Breeze", "10_Pomegranate_Bloom",
     "11_Almond_Blossom", "12_Lemon_Grove", "13_Blue_Grape", "14_Golden_Loquat"]


def dosya(c, n=14, video=1):
    return [dict(Path=f"{c}/galeri/{g}.jpg") for g in G[:n]] + [dict(Path=f"{c}/video/v{i}.mp4") for i in range(video)]


class Test(unittest.TestCase):
    def test_karar(self):
        kok = [dict(Name=c, IsDir=True) for c in ("ARIES_ARIES", "LEO_LEO", "LEO_LEO", "LEO_VIRGO", "ARIES_LEO", "LEO_LIBRA")]
        fs = dosya("ARIES_ARIES") + dosya("LEO_LEO") + dosya("LEO_LEO") + dosya("LEO_VIRGO", n=13) + dosya("ARIES_LEO", video=2) \
            + dosya("LEO_LIBRA") + [dict(Path="LEO_LIBRA/galeri/01_kopya.jpg")]
        yaz, atla, indir = m.tara(kok, fs, ["ARIES_ARIES", "LEO_LEO", "LEO_VIRGO", "ARIES_LEO", "LEO_LIBRA", "VIRGO_VIRGO",
                                            "SAGITTARIUS_SAGITTARIUS"], {"SAGITTARIUS_SAGITTARIUS": "uretim HATA"})
        self.assertEqual(yaz, ["ARIES_ARIES"])
        self.assertEqual(len(indir), 15)
        neden = dict(atla)
        self.assertIn("2 klasor", neden["LEO_LEO"])
        self.assertIn("0 klasor", neden["VIRGO_VIRGO"])
        self.assertIn("galeri 13", neden["LEO_VIRGO"])
        self.assertIn("video 2", neden["ARIES_LEO"])
        self.assertIn("galeri 15", neden["LEO_LIBRA"])
        self.assertEqual(neden["SAGITTARIUS_SAGITTARIUS"], "uretim HATA")


if __name__ == "__main__":
    unittest.main()
