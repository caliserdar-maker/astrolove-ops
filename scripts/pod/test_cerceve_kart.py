#!/usr/bin/env python3
"""cerceve_kart kalite kapilarinin agsiz birim testleri."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import cerceve_kart as ck


def synthetic() -> Image.Image:
    im = Image.new("RGB", (400, 500), "#f2e8d5")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 199, 249), fill="#cf3f4f")
    d.rectangle((200, 0, 399, 249), fill="#315b9a")
    d.rectangle((0, 250, 199, 499), fill="#e3b341")
    d.rectangle((200, 250, 399, 499), fill="#36755a")
    for n in range(10, 400, 20):
        d.line((n, 0, n, 499), fill="white", width=1)
    return im


class CerceveKartTest(unittest.TestCase):
    def test_single_and_options_pass(self):
        design = synthetic()
        for image, boxes in (ck.single_card(design, "BK", False), ck.options_card(design, True)):
            passed, detail = ck.quality_gate(design, image, boxes)
            self.assertTrue(passed, detail)
            self.assertEqual(image.size, (2000, 2500))

    def test_corrupted_design_area_fails(self):
        design = synthetic()
        image, boxes = ck.single_card(design, "NA", False)
        damaged = np.asarray(image).copy()
        x0, y0, x1, y1 = boxes[0]
        damaged[y0:y1, x0:x1] = 0
        passed, _ = ck.quality_gate(design, Image.fromarray(damaged), boxes)
        self.assertFalse(passed)

    def test_input_ratio_and_jpeg_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jpg"
            Image.new("RGB", (4, 4)).save(path)
            with self.assertRaises(ValueError):
                ck.open_design(path)
            out = Path(tmp) / "out.jpg"
            ck.save_checked(Image.new("RGB", (2000, 2500)), out)
            with Image.open(out) as saved:
                self.assertEqual(saved.size, (2000, 2500))
                self.assertTrue(saved.info.get("icc_profile"))


if __name__ == "__main__":
    unittest.main()
