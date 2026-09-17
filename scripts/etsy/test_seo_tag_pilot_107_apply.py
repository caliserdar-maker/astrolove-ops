#!/usr/bin/env python3
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.modules.setdefault("requests", types.SimpleNamespace())
import seo_tag_pilot_107_apply as target


def fixture():
    listings, plan = [], []
    for i in range(1, 547):
        before = [f"tag{i % 9}{j}" for j in range(13)]
        after = list(before)
        apply = i <= 107
        if apply:
            after[0] = f"new{i}"
        item = {
            "listing_id": i, "title": f"Title {i}", "description": f"Description {i}",
            "tags": list(before), "state": "active", "price": {"amount": 100},
            "listing_type": "download", "quantity": 1,
        }
        listings.append(item)
        plan.append({
            "listing_id": str(i), "zodiac_pair": "ARIES_LEO",
            "application_flag": "YES" if apply else "NO",
            "title_sha256": target.digest(item["title"]),
            "description_sha256": target.digest(item["description"]),
            "tags_before": before, "tags_after": after,
        })
    return listings, plan


class FakeApi:
    def __init__(self, listings, alter_ru=False):
        self.items = {str(x["listing_id"]): dict(x) for x in listings}
        self.remaining = "5000"
        self.patches = []
        self.alter_ru = alter_ru
        self.ru_reads = {}

    def get(self, path, params=None, ok404=False):
        self.remaining = str(int(self.remaining) - 1)
        if path.endswith("/listings"):
            offset = int((params or {}).get("offset", 0))
            limit = int((params or {}).get("limit", 100))
            vals = [self.items[k] for k in sorted(self.items, key=int)]
            return {"results": vals[offset:offset + limit]}
        if "/translations/ru" in path:
            lid = path.split("/listings/")[1].split("/")[0]
            self.ru_reads[lid] = self.ru_reads.get(lid, 0) + 1
            suffix = " changed" if self.alter_ru and lid == "1" and self.ru_reads[lid] > 1 else ""
            return {"title": f"RU {lid}{suffix}", "description": "RU desc", "tags": ["ru tag"]}
        return dict(self.items[path.rsplit("/", 1)[-1]])

    def patch(self, path, data):
        self.remaining = str(int(self.remaining) - 1)
        lid = path.rsplit("/", 1)[-1]
        self.items[lid]["tags"] = data["tags"].split(",")
        self.patches.append((lid, set(data)))
        return dict(self.items[lid])


class TagPilotApplyTest(unittest.TestCase):
    def test_dry_run_never_writes(self):
        listings, plan = fixture()
        api = FakeApi(listings)
        with tempfile.TemporaryDirectory() as temp:
            summary = target.run(api, "shop", plan, Path(temp), apply=False, sleep_seconds=0)
        self.assertEqual(api.patches, [])
        self.assertEqual(summary["preflight_pass"], 546)

    def test_apply_writes_only_tags_to_exactly_107(self):
        listings, plan = fixture()
        api = FakeApi(listings)
        with tempfile.TemporaryDirectory() as temp:
            summary = target.run(api, "shop", plan, Path(temp), apply=True,
                                 quota_buffer=10, sleep_seconds=0)
        self.assertEqual(len(api.patches), 107)
        self.assertTrue(all(fields == {"tags"} for _, fields in api.patches))
        self.assertEqual(summary["final_target_pass"], 107)
        self.assertEqual(summary["non_target_pass"], 439)
        self.assertEqual(summary["ru_pass"], 107)

    def test_any_catalog_mismatch_stops_before_write(self):
        listings, plan = fixture()
        listings[-1]["title"] = "Unexpected"
        api = FakeApi(listings)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit):
                target.run(api, "shop", plan, Path(temp), apply=True, sleep_seconds=0)
        self.assertEqual(api.patches, [])

    def test_ru_change_fails_final_verification(self):
        listings, plan = fixture()
        api = FakeApi(listings, alter_ru=True)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SystemExit):
                target.run(api, "shop", plan, Path(temp), apply=True,
                           quota_buffer=10, sleep_seconds=0)
        self.assertEqual(len(api.patches), 107)


if __name__ == "__main__":
    unittest.main()
