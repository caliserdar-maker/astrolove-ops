import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

# The production workflow installs requests. Unit tests use FakeApi and only
# need the module import to succeed in the minimal local Python environment.
if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.post = lambda *args, **kwargs: None
    requests_stub.request = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_stub

from scripts.etsy.seo_attribute_audit import run


class FakeApi:
    calls = 0

    def get(self, path):
        self.calls += 1
        if path == "/seller-taxonomy/nodes":
            return {"results": [
                {"id": 2078, "name": "Digital Prints", "children": []},
                {"id": 121, "name": "Giclée Prints", "children": []},
            ]}
        if path.endswith("/2078/properties"):
            return {"results": [{"display_name": "Primary color"}]}
        if path.endswith("/121/properties"):
            return {"results": [
                {"display_name": "Framing"}, {"display_name": "Material multi"},
                {"display_name": "Number of pieces included"}, {"display_name": "Orientation"},
            ]}
        raise AssertionError(path)


class AuditTest(unittest.TestCase):
    def test_supported_and_unsupported_are_distinguished(self):
        rows = [
            {"listing_id": "1", "product_family": "Digital wall art", "zodiac_pair": "ARIES_LEO",
             "edition": "Deep Black", "taxonomy_id": 2078,
             "properties_json": json.dumps({"Primary color": ["Black"]}), "url": "u1"},
            {"listing_id": "2", "product_family": "POD baski", "zodiac_pair": "ARIES_LEO",
             "edition": "5 renk (varyasyon)", "taxonomy_id": 121,
             "properties_json": json.dumps({"Framing": ["Unframed"], "Material multi": ["Paper"],
                                               "Number of pieces included": ["1"], "Orientation": ["Vertical"]}),
             "url": "u2"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snap = root / "snapshot.json"
            snap.write_text(json.dumps(rows), encoding="utf-8")
            out = run(FakeApi(), snap, root / "out", expected_count=2)
            self.assertEqual(out[0]["overall_status"], "PASS")
            self.assertEqual(out[0]["room"], "NOT_SUPPORTED")
            self.assertEqual(out[1]["overall_status"], "PASS")
            self.assertEqual(out[1]["framing"], "SET: Unframed")


if __name__ == "__main__":
    unittest.main()
