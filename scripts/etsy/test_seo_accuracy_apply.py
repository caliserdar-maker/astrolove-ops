#!/usr/bin/env python3
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.modules.setdefault("requests", types.SimpleNamespace())
import seo_accuracy_apply as target


def sha(text):
    return target.digest(text)


def fixture(count=546, pending_first=True):
    listings, plan = [], []
    for i in range(1, count + 1):
        old = f"Description {i} {target.OLD_HEADER}" if i == 1 else f"Description {i}"
        new = old.replace(target.OLD_HEADER, target.NEW_HEADER)
        tags_old = [f"tag{i % 9}{j}" for j in range(13)]
        tags_new = list(tags_old)
        if i == 1:
            tags_old[0], tags_new[0] = "bad phrase", "good phrase"
        listing = {"listing_id": i, "title": f"Title {i}", "description": old if pending_first or i != 1 else new,
                   "tags": tags_old if pending_first or i != 1 else tags_new, "state": "active",
                   "price": {"amount": 100}, "listing_type": "download", "quantity": 1}
        listings.append(listing)
        plan.append({"listing_id": str(i), "title_sha256": sha(listing["title"]),
                     "description_before_sha256": sha(old), "description_after_sha256": sha(new),
                     "description_replace": target.OLD_HEADER if i == 1 else "",
                     "tags_before": tags_old, "tags_after": tags_new})
    return listings, plan


class FakeApi:
    def __init__(self, listings):
        self.items = {str(x["listing_id"]): dict(x) for x in listings}
        self.remaining = "5000"
        self.calls = 0
        self.patches = []

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        self.remaining = str(int(self.remaining) - 1)
        if path.endswith("/listings"):
            offset = int((params or {}).get("offset", 0)); limit = int((params or {}).get("limit", 100))
            vals = [self.items[k] for k in sorted(self.items, key=int)]
            return {"results": vals[offset:offset + limit]}
        return dict(self.items[path.rsplit("/", 1)[-1]])

    def patch(self, path, data):
        self.calls += 1
        self.remaining = str(int(self.remaining) - 1)
        lid = path.rsplit("/", 1)[-1]
        if "description" in data:
            self.items[lid]["description"] = data["description"]
        if "tags" in data:
            self.items[lid]["tags"] = data["tags"].split(",")
        self.patches.append((lid, set(data)))
        return dict(self.items[lid])


class SeoAccuracyApplyTest(unittest.TestCase):
    def test_dry_run_never_writes(self):
        listings, plan = fixture()
        api = FakeApi(listings)
        with tempfile.TemporaryDirectory() as temp:
            summary = target.run(api, "shop", plan, Path(temp), apply=False, sleep_seconds=0)
            self.assertEqual(api.patches, [])
            self.assertEqual(summary["preflight_pass"], 546)

    def test_apply_writes_only_pending_fields_and_preserves_title(self):
        listings, plan = fixture()
        api = FakeApi(listings)
        with tempfile.TemporaryDirectory() as temp:
            summary = target.run(api, "shop", plan, Path(temp), apply=True, quota_buffer=10, sleep_seconds=0)
            self.assertEqual(api.patches, [("1", {"description", "tags"})])
            self.assertEqual(summary["final_pass"], 546)
            self.assertEqual(api.items["1"]["title"], "Title 1")

    def test_scope_mismatch_stops_before_write(self):
        listings, plan = fixture()
        api = FakeApi(listings[:-1])
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit):
                target.run(api, "shop", plan, Path(temp), apply=True, sleep_seconds=0)
            self.assertEqual(api.patches, [])


if __name__ == "__main__":
    unittest.main()
