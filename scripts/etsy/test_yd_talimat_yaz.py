#!/usr/bin/env python3
"""yd_talimat_yaz testleri (sahte Etsy; ag yok). Kullanim: python3 scripts/etsy/test_yd_talimat_yaz.py -> SONUC n/n PASS."""
import copy
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import yd_talimat_yaz as Y  # noqa: E402

sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"))


def soru(t, ins, qid, req=True, mx=20):
    return {"question_text": t, "instructions": ins, "question_id": qid, "question_type": "text_input", "required": req,
            "max_allowed_characters": mx, "max_allowed_files": None, "add_on_price": None}


CANLI = [soru("Name under Cancer", "Up to 11 letters. Printed in capitals.", 1, mx=11),
         soru("Name under Libra", "Up to 11 letters. Printed in capitals.", 2, mx=11),
         soru("Your special date", "Write the month in letters, for example 14 June 2025", 3),
         soru("Heading", Y.ESKI, 4), soru("Optional short line", "Leave empty for Year One", 5, req=False)]


class Sahte:
    def __init__(self, kimlik_degis=False, state="active"):
        self.p, self.calls, self.remaining, self.post = copy.deepcopy(CANLI), 0, 500, []
        self.kd, self.state = kimlik_degis, state

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(self.p)}
        return {"state": self.state}

    def post_json(self, path, body):
        self.calls += 1; self.post.append(body)
        yeni = []
        for i, q in enumerate(body["personalization_questions"]):
            q = dict(q, max_allowed_files=None, add_on_price=None)
            if self.kd:
                q["question_id"] = 100 + i
            yeni.append(q)
        self.p = yeni


g = Y.govde(CANLI)
k("govde: 5 soru, question_id korunur", [q["question_id"] for q in g] == [1, 2, 3, 4, 5])
k("govde: yalniz Heading talimati YENI", [q["instructions"] for q in g][3] == Y.YENI and g[0]["instructions"] == CANLI[0]["instructions"])
k("govde: None alanlar gonderilmez", all("max_allowed_files" not in q and "add_on_price" not in q for q in g))
k("govde: Heading zorunlu ve 20 kalir", g[3]["required"] is True and g[3]["max_allowed_characters"] == 20)
k("YENI 36 karakter, ESKI 88", len(Y.YENI) == 36 and len(Y.ESKI) == 88)
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d)
    a = Sahte(); r = Y.isle(a, "1", "9", out, False)
    k("kuru: POST yok", r["sonuc"] == "KURU" and not a.post)
    a = Sahte(); r = Y.isle(a, "1", "9", out, True)
    k("uygula: PASS, tek POST, 5 istek", r["sonuc"] == "PASS" and len(a.post) == 1 and a.calls == 5, (r, a.calls))
    k("uygula: kimlik korundu", r["kimlik_korundu"] is True)
    a = Sahte(); a.p[3]["instructions"] = Y.YENI; r = Y.isle(a, "1", "9", out, True)
    k("zaten YENI: POST yok", r["sonuc"] == "ZATEN_YENI" and not a.post)
    try:
        Y.isle(Sahte(kimlik_degis=True), "1", "9", out, True); dur = False
    except SystemExit as e:
        dur = "question_id" in str(e)
    k("kimlik degisirse DUR", dur)
    try:
        Y.isle(Sahte(state="draft"), "1", "9", out, True); dur = False
    except SystemExit:
        dur = True
    k("state draft ise yazim yok", dur)
    a = Sahte(); a.p[3]["instructions"] = "baska"
    try:
        Y.isle(a, "1", "9", out, True); dur = False
    except SystemExit:
        dur = not a.post
    k("beklenmeyen talimat: DUR, POST yok", dur)
    a = Sahte(); a.remaining = 12
    try:
        Y.isle(a, "1", "9", out, True); dur = False
    except SystemExit:
        dur = not a.post
    k("kota < 4 + 10: DUR, POST yok", dur)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
