#!/usr/bin/env python3
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.modules.setdefault("requests", types.SimpleNamespace())
import seo_live_snapshot as target


class FakeApi:
    def __init__(self, listings, props, remaining="1000"):
        self.listings = listings
        self.props = props
        self.remaining = remaining
        self.calls = 0
        self.methods = []

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        self.methods.append("GET")
        if path.endswith("/listings"):
            return {"results": self.listings}
        listing_id = path.split("/")[-2]
        return {"results": self.props.get(listing_id, [])}


class SeoLiveSnapshotTest(unittest.TestCase):
    def fixtures(self):
        listings = [
            {
                "listing_id": 1,
                "title": "Cancer and Libra Zodiac Wall Art, Champagne Ivory Edition, Digital Download",
                "description": "Instant digital download",
                "tags": [f"tag {i}" for i in range(13)],
                "taxonomy_id": 10,
                "listing_type": "download",
                "state": "active",
            },
            {
                "listing_id": 2,
                "title": "Aries Leo Matching Couple Wallpaper, 4 Colors, Phone Tablet Desktop Watch",
                "description": "Digital wallpaper",
                "tags": [f"wall {i}" for i in range(13)],
                "taxonomy_id": 11,
                "listing_type": "download",
                "state": "active",
            },
            {
                "listing_id": 3,
                "title": "Aries and Leo Zodiac Couple Print, Minimalist Gold Line Art, Unframed",
                "description": "Physical print",
                "tags": [f"print {i}" for i in range(13)],
                "taxonomy_id": 12,
                "listing_type": "physical",
                "state": "active",
            },
        ]
        props = {
            "1": [{"property_name": "Primary color", "values": ["Beige"]}],
            "2": [{"property_name": "Room", "values": ["Bedroom"]}],
            "3": [{"property_name": "Orientation", "values": ["Vertical"]}],
        }
        return listings, props

    def test_build_row(self):
        listings, props = self.fixtures()
        row = target.build_row(listings[0], props["1"])
        self.assertEqual(row["product_family"], "Digital wall art")
        self.assertEqual(row["zodiac_pair"], "CANCER_LIBRA")
        self.assertEqual(row["primary_color"], "Beige")
        self.assertEqual(row["tag_count"], 13)

    def test_run_is_get_only_and_writes_manifest(self):
        listings, props = self.fixtures()
        api = FakeApi(listings, props)
        with tempfile.TemporaryDirectory() as temp:
            status = target.run(api, "shop", Path(temp), expected_count=3, quota_buffer=10)
            manifest = json.loads((Path(temp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(status, "PASS")
            self.assertEqual(api.methods, ["GET", "GET", "GET", "GET"])
            self.assertEqual(manifest["active_listings"], 3)
            self.assertEqual(manifest["families"]["POD baski"], 1)


if __name__ == "__main__":
    unittest.main()
