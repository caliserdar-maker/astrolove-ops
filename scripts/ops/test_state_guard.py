#!/usr/bin/env python3
import copy
import unittest

import state_guard


class OperationalStateGuardTest(unittest.TestCase):
    def setUp(self):
        self.state = state_guard.load_state(state_guard.DEFAULT_STATE)
        self.ledger = state_guard.load_ledger()

    def test_current_state_is_consistent(self):
        self.assertEqual([], state_guard.validate(self.state, self.ledger))

    def test_completed_gpsr_cannot_return_to_pending(self):
        changed = copy.deepcopy(self.state)
        gpsr = next(x for x in changed["tasks"] if x["id"] == "gpsr_pod_78")
        gpsr["status"] = "pending_approval"
        errors = state_guard.validate(changed, self.ledger)
        self.assertTrue(any("tamamlanan is yeniden acilmis: gpsr_pod_78" in x for x in errors))

    def test_completed_merge_cannot_return_to_pending(self):
        changed = copy.deepcopy(self.state)
        merge = next(x for x in changed["tasks"] if x["id"] == "workflow_hardening_merge")
        merge["status"] = "pending_approval"
        errors = state_guard.validate(changed, self.ledger)
        self.assertTrue(any("tamamlanan is yeniden acilmis: workflow_hardening_merge" in x for x in errors))

    def test_next_task_excludes_completed_work(self):
        pending = [x for x in self.state["tasks"] if x["status"] != "completed"]
        pending.sort(key=lambda x: (x.get("priority", 999), x["id"]))
        self.assertEqual("wallpaper_description_78", pending[0]["id"])

    def test_first_40_title_rule_cannot_generate_candidates(self):
        catalog = (state_guard.ROOT / "scripts/night2/catalog.py").read_text(encoding="utf-8")
        batch4 = (state_guard.ROOT / "scripts/night2/batch4.py").read_text(encoding="utf-8")
        self.assertNotIn('"ILK40_URUN"', catalog)
        self.assertNotIn("def baslik_onerisi", batch4)


if __name__ == "__main__":
    unittest.main()
