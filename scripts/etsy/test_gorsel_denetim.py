import io
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gorsel_denetim as target


def jpeg(kind="noise", size=(2100, 2100), quality=92):
    rng = np.random.default_rng(42)
    if kind == "flat": arr = np.full((size[1], size[0], 3), 127, np.uint8)
    elif kind == "blur":
        arr = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
        import cv2
        arr = cv2.GaussianBlur(arr, (101, 101), 30)
    else: arr = rng.integers(0, 256, (size[1], size[0], 3), dtype=np.uint8)
    out = io.BytesIO(); Image.fromarray(arr).save(out, "JPEG", quality=quality); return out.getvalue()


class AuditTests(unittest.TestCase):
    def run_audit(self, specs, ocr=("Aries", "Leo")):
        blobs, listings = {}, []
        for lid, title, images in specs:
            rows = []
            for rank, blob in enumerate(images, 1):
                url = f"mem://{lid}/{rank}"; blobs[url] = blob
                rows.append({"rank": rank, "url_fullxfull": url})
            listings.append({"listing_id": lid, "title": title, "images": rows})
        with patch.object(target, "ocr_signs", return_value=set(ocr)):
            return target.audit(listings, blobs.__getitem__)[0]

    def test_pass(self):
        rows = self.run_audit([("1", "Aries Leo", [jpeg()])])
        self.assertEqual(rows[0]["durum"], "PASS")

    def test_low_resolution(self):
        self.assertIn("cozunurluk", self.run_audit([("1", "Aries Leo", [jpeg(size=(900, 900))])])[0]["neden"])

    def test_flat_and_small_file(self):
        reason = self.run_audit([("1", "Aries Leo", [jpeg("flat")])])[0]["neden"]
        self.assertIn("bos_tek_renk", reason); self.assertIn("dosya_boyutu", reason)

    def test_ratio_mismatch(self):
        rows = self.run_audit([("1", "Aries Leo", [jpeg(), jpeg(size=(2100, 2500))])])
        self.assertTrue(any("oran_tutarsiz" in row["neden"] for row in rows))

    def test_data_driven_blur(self):
        rows = self.run_audit([("1", "Aries Leo", [jpeg(), jpeg(), jpeg("blur")])])
        self.assertIn("bulanik", rows[2]["neden"])

    def test_inside_duplicate(self):
        blob = jpeg(); rows = self.run_audit([("1", "Aries Leo", [blob, blob])])
        self.assertIn("ilan_ici_tekrar", rows[1]["neden"])

    def test_cross_listing_cover_duplicate(self):
        blob = jpeg(); rows = self.run_audit([("1", "Aries Leo", [blob]), ("2", "Aries Leo", [blob])])
        self.assertTrue(all("ilanlar_arasi_ayni_kapak" in row["neden"] for row in rows))

    def test_wrong_ocr_and_unknown_ocr(self):
        wrong = self.run_audit([("1", "Aries Leo", [jpeg()])], ("Cancer", "Libra"))[0]
        unknown = self.run_audit([("1", "Aries Leo", [jpeg()])], ())[0]
        self.assertIn("ocr_yanlis_cift", wrong["neden"]); self.assertEqual(unknown["durum"], "BELIRSIZ")


if __name__ == "__main__":
    unittest.main()
