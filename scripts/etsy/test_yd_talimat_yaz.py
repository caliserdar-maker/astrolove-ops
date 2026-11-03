#!/usr/bin/env python3
"""yd_talimat_yaz testleri (sahte Etsy; ag yok). Serdar 4 Kas kapisi: a (alanlar + sira + baslik/state ayni), b (kimlik tablosu),
c (siparis eslesmesi metinle). Kullanim: python3 scripts/etsy/test_yd_talimat_yaz.py -> SONUC n/n PASS."""
import copy
import csv
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


CANLI = [soru("Name under Cancer", "Up to 11 letters. Printed in capitals.", 1463163629866, mx=11),
         soru("Name under Libra", "Up to 11 letters. Printed in capitals.", 1463152997903, mx=11),
         soru("Your special date", "Write the month in letters, for example 14 June 2025", 1463163629868),
         soru("Heading", Y.ESKI, 1463152997905), soru("Optional short line", "Leave empty for Year One", 1463163629870, req=False)]
PILOT = copy.deepcopy(CANLI); PILOT[3].update(instructions=Y.YENI, question_id=1463183473146)   # 3 Kas canli geri okuma


class Sahte:
    def __init__(self, bozuk=None, state="active"):
        self.calls, self.remaining, self.post, self.ilan = 0, 500, [], {}
        self.bozuk, self.state, self.title = bozuk, state, "Cancer and Libra 1st Anniversary"

    def get(self, path, params=None, ok404=False):
        self.calls += 1
        if path.endswith("/personalization"):
            return {"personalization_questions": copy.deepcopy(PILOT if "/listings/4595350971/" in path else self.q(path))}
        return {"state": self.state, "title": self.title}

    def q(self, path):
        lid = path.rstrip("/").split("/")[-2]
        return self.ilan.setdefault(lid, copy.deepcopy(CANLI))

    @property
    def p(self):
        return self.q("/listings/9/personalization")

    def post_json(self, path, body):
        self.calls += 1; self.post.append(body)
        yeni = []
        for q in body["personalization_questions"]:
            q = dict(q, max_allowed_files=None, add_on_price=None)
            if q["question_text"] == "Heading":
                q["question_id"] = q["question_id"] + 1   # Etsy duzenlenen soruya yeni kimlik verir (3 Kas pilot olcumu)
            yeni.append(q)
        if self.bozuk == "zorunlu":
            yeni[0]["required"] = False
        if self.bozuk == "sira":
            yeni = [yeni[1], yeni[0]] + yeni[2:]
        if self.bozuk == "baslik":
            self.title = "degisti"
        if self.bozuk == "diger_talimat":
            yeni[2]["instructions"] = "x"
        self.ilan[path.rstrip("/").split("/")[-2]] = yeni


g = Y.govde(CANLI)
k("govde: 5 soru, mevcut question_id'ler gider", [q["question_id"] for q in g] == [q["question_id"] for q in CANLI])
k("govde: yalniz Heading talimati YENI; None alanlar yok", g[3]["instructions"] == Y.YENI and g[0]["instructions"] == CANLI[0]["instructions"]
  and all("max_allowed_files" not in q for q in g))
ok, ay = Y.siparis_eslesme_testi(PILOT)
k("c: siparis eslesmesi metinle, kimlikten bagimsiz (pilot canli seti)", ok and ay["sorun"] == [], ay)
k("c: eslesme yontemi raporlanir", "formatted_name" in ay["eslesme_yontemi"])
ok2, ay2 = Y.siparis_eslesme_testi(PILOT[:4])
k("c: eksik soru seti FAIL", not ok2, ay2)
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d)
    a = Sahte(); r = Y.isle(a, "1", "9", out, True)
    k("a: kimlik degisse de alanlar ayni -> PASS, 5 istek", r["sonuc"] == "PASS" and a.calls == 5, (r, a.calls))
    kim = {x["soru"]: x for x in r["kimlik"]}
    k("b: kimlik tablosu 5 satir, Heading degisti, digerleri ayni", len(r["kimlik"]) == 5 and kim["Heading"]["degisti"]
      and not kim["Name under Cancer"]["degisti"] and kim["Heading"]["yeni_id"] == 1463152997906)
    for bozuk in ("zorunlu", "sira", "baslik", "diger_talimat"):
        r = Y.isle(Sahte(bozuk=bozuk), "1", "9", out, True)
        k(f"a: {bozuk} degisirse FAIL", r["sonuc"] == "FAIL" and r["sorun"], r.get("sorun"))
    a = Sahte(); a.p[3]["instructions"] = Y.YENI; r = Y.isle(a, "1", "9", out, True)
    k("zaten YENI: POST yok", r["sonuc"] == "ZATEN_YENI" and not a.post)
    try:
        Y.isle(Sahte(state="draft"), "1", "9", out, True); dur = False
    except SystemExit:
        dur = True
    k("state draft: yazim yok", dur)
    a = Sahte(); a.p[3]["instructions"] = "baska"
    try:
        Y.isle(a, "1", "9", out, True); dur = False
    except SystemExit:
        dur = not a.post
    k("beklenmeyen talimat: DUR, POST yok", dur)
    a = Sahte(); a.remaining = 13
    try:
        Y.isle(a, "1", "9", out, True); dur = False
    except SystemExit as e:
        dur = not a.post and "ilan baslamadi" in str(e)
    k("kota < 5 + 10: ilan baslamadan DUR (yarim ilan yok)", dur)
    # calis: c testi -> ilanlar; FAIL'de dur; tablolar yazilir
    o2 = out / "c1"; o2.mkdir()
    a = Sahte(); s = Y.calis(a, "1", ["11", "12", "4595350971"], {"4595350971"}, o2, True, "4595350971")
    rows = list(csv.DictReader(open(o2 / "GERI_OKUMA.csv"))); kr = list(csv.DictReader(open(o2 / "KIMLIK.csv")))
    k("calis: 2 ilan PASS, pilot atlandi, tablolar (2 + 10 kimlik satiri)", [r["sonuc"] for r in s] == ["PASS", "PASS"] and len(rows) == 2
      and len(kr) == 10 and (o2 / "C_TESTI.json").exists())
    o3 = out / "c2"; o3.mkdir()
    b = Sahte(bozuk="zorunlu")
    try:
        Y.calis(b, "1", ["11", "12"], set(), o3, True, "4595350971"); dur = False
    except SystemExit:
        dur = len(b.post) == 1 and len(list(csv.DictReader(open(o3 / "GERI_OKUMA.csv")))) == 1
    k("calis: ilk FAIL'de DUR, ikinci ilana yazim yok, tablo yazilir", dur)
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
