import tempfile
import unittest
from pathlib import Path

import dijital_donusum_uygula as app


class FakeAPI:
    def __init__(self, listings): self.listings, self.calls, self.writes = listings, 0, []
    def get(self, path): self.calls += 1; return self.listings[path.rsplit("/", 1)[-1]]
    def patch(self, path, data): self.calls += 1; self.writes.append(("patch", path, data)); return {}
    def put_json(self, path, data): self.calls += 1; self.writes.append(("put", path, data)); return {}


def row(lid="1", action="TUT_VE_DONUSTUR", pair="ARIES_LEO"):
    return {"ilan_id": lid, "eylem": action, "cift": pair}


class Tests(unittest.TestCase):
    def test_sources_match_exactly(self): app.validate_sources([row(str(i)) for i in range(78)], {str(i) for i in range(78)})
    def test_sources_conflict_stops(self):
        with self.assertRaises(app.Dur): app.validate_sources([row(str(i)) for i in range(78)], {str(i) for i in range(77)})
    def test_draft_is_preserved_without_write(self):
        api = FakeAPI({"1": {"state": "draft"}}); result = app.run(api, "s", [row()], set(), 5, True)
        self.assertEqual(result[0]["sonuc"], "TASLAK_KORUNDU"); self.assertFalse(api.writes)
    def test_dry_run_never_writes(self):
        api = FakeAPI({"1": {"state": "active"}}); app.run(api, "s", [row()], set(), 9, False)
        self.assertFalse(api.writes)
    def test_idempotent_listing_has_no_patch(self):
        wanted = app.target("ARIES_LEO"); api = FakeAPI({"1": {"state": "active", **wanted}})
        app.run(api, "s", [row()], set(), 9, True); self.assertFalse(api.writes)
    def test_budget_stops_before_next_call(self):
        api = FakeAPI({"1": {"state": "active"}})
        with self.assertRaises(app.Dur): app.run(api, "s", [row()], set(), 1, True)
    def test_inactive_is_idempotent(self):
        api = FakeAPI({"1": {"state": "inactive"}}); result = app.run(api, "s", [row(action="TASLAGA_AL")], set(), 2, True)
        self.assertEqual(result[0]["sonuc"], "DEGISIM_YOK"); self.assertFalse(api.writes)
    def test_active_duplicate_becomes_inactive(self):
        api = FakeAPI({"1": {"state": "active"}}); app.run(api, "s", [row(action="TASLAGA_AL")], set(), 2, True)
        self.assertEqual(api.writes[0][2], {"state": "inactive"})
    def test_cancer_special_tag_and_limits(self):
        tags = app.target("CANCER_SAGITTARIUS")["tags"]
        self.assertIn("cancer zodiac gift", tags); self.assertTrue(all(len(x) <= 20 for x in tags))
    def test_made_to_order_api_field_is_applied_when_present(self):
        api = FakeAPI({"1": {"state": "active", "is_made_to_order": False}})
        app.run(api, "s", [row()], set(), 9, True)
        self.assertTrue(api.writes[0][2]["is_made_to_order"])
    def test_duplicate_plan_id_stops(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "p.csv"; p.write_text("ilan_id,cift,eylem\n1,ARIES_LEO,TUT_VE_DONUSTUR\n1,ARIES_LEO,TUT_VE_DONUSTUR\n")
            with self.assertRaises(app.Dur): app.read_plan(p)


if __name__ == "__main__": unittest.main()
