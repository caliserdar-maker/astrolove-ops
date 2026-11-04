#!/usr/bin/env python3
"""poster_metin_yaz (YALNIZ P1 kipi) testleri: sahte Etsy, ag yok. Her kapi bilinen PASS + bilinen FAIL (Merkez 4 Kas dersi).
Canli bicim: testdata_poster_cancer_libra.json (3 Kas oncesi metin) + poster_metin_kuru.DEG (3-4 Kas yazimi) = 4 Kas canli EN;
canli RU = kur(EN) (test_p1_poster_kuru ile ayni; gercek veri paritesi orada). Kuru plan p1_poster_kuru.plan_ilan ile ayni canli
veriden kurulur (Serdar onayli kuru kosu 41833440548 ile ayni yol); FAIL durumlari sahte canlinin bozulmasiyla uretilir.
Kullanim: python3 scripts/etsy/test_poster_metin_yaz.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import copy
import csv
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as R  # noqa: E402
import poster_metin_kuru as P  # noqa: E402
import p1_poster_kuru as K  # noqa: E402
import poster_metin_yaz as Y  # noqa: E402

Y.BEKLE_SN = 0
D = json.loads((KOK / "testdata_poster_cancer_libra.json").read_text())
LID, SHOP = "4570143815", "1"
BOY = ["5×7″ (13×18cm)"] + list(P.K.BOYLAR)
BOYKOD = [P.boy_kodu(b) for b in BOY]
sonuc = []


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"), flush=True)


def canli_en():
    en = P.norm(D["description"])
    for a, b in P.DEG:
        en = en.replace(a, b)
    return en


EN0 = canli_en()
RU0 = R.kur(EN0, {"boy": BOYKOD})[0]


class Sahte:
    """Durumlu sahte Etsy: ilan (EN), RU ceviri, envanter. Yazmalar saklanir; bayraklar hata uretir."""

    def __init__(self, kalan=500, en=None, ru=None):
        self.calls, self.remaining, self.yaz = 0, kalan, []
        self.L = dict(listing_id=int(LID), state="active", title=D["title"], description=EN0 if en is None else en, tags=list(D["tags"]),
                      materials=["matte art paper", "ink"], last_modified_timestamp=1)
        self.ru = dict(title=D["ru"]["title"], description=RU0 if ru is None else ru, tags=list(D["ru"]["tags"]))
        self.inv = {"products": [{"property_values": [{"property_id": 513, "values": [b]}]} for b in BOY]}
        self.ru_put_hata = self.patch_bozuk = self.ru_bozuk = self.put_islenip_hata = self.patch_timeout = False
        self.patch_islenip_hata = self.son_bozuk = False
        self.put_n = 0

    def kota_kapisi(self, ne=""):
        if self.remaining is not None and self.remaining < E.KOTA_SINIRI:
            raise SystemExit("DUR: kota esigi")

    def _say(self):
        self.calls += 1
        if self.remaining is not None:
            self.remaining -= 1

    def get(self, path, params=None, ok404=False):
        self._say()
        if path == f"/listings/{LID}":
            x = copy.deepcopy(self.L)
            if self.son_bozuk and self.put_n:   # yazimdan sonra baslik degismis gibi (son okuma FAIL)
                x["title"] += " x"
            return x
        if path == f"/listings/{LID}/inventory":
            return copy.deepcopy(self.inv)
        if path == f"/shops/{SHOP}/listings/{LID}/translations/ru":
            return copy.deepcopy(self.ru)
        raise AssertionError(path)

    def patch(self, path, data):
        self._say(); self.yaz.append(("PATCH", path, dict(data)))
        assert set(data) == {"description"}, data
        if self.patch_timeout:
            raise TimeoutError("read timeout")
        if self.patch_islenip_hata:
            self.L["description"] = data["description"]; self.L["last_modified_timestamp"] += 1
            raise SystemExit("HTTP 503 PATCH (islendi)")
        self.L["description"] = data["description"] + (" X" if self.patch_bozuk else "")
        self.L["last_modified_timestamp"] += 1

    def put(self, path, data):
        self._say(); self.yaz.append(("PUT", path, dict(data)))
        self.put_n += 1
        if self.ru_put_hata:
            raise SystemExit("HTTP 500 PUT translations")
        self.ru = dict(title=data["title"], description=data["description"] + (" X" if self.ru_bozuk and self.put_n == 1 else ""),
                       tags=data["tags"].split(","))
        if self.put_islenip_hata:
            raise SystemExit("HTTP 503 PUT translations (islendi)")


def kayit_of(a):
    """p1_poster_oku HAM kaydi (sahte canlidan)"""
    x = a.get(f"/listings/{LID}"); inv = a.get(f"/listings/{LID}/inventory"); ru = a.get(f"/shops/{SHOP}/listings/{LID}/translations/ru")
    return dict(listing_id=LID, listing={k_: x.get(k_) for k_ in ("listing_id", "state", "title", "description", "tags", "materials",
                                                                  "last_modified_timestamp")},
                inventory=inv, ru={k_: ru.get(k_) for k_ in ("title", "description", "tags")}, ru_durum="var")


def kuru_plan(a=None):
    s, d = K.plan_ilan(kayit_of(a or Sahte()), SHOP)
    return s, {LID: d}


S0, KURU = kuru_plan()
assert S0["durum"] == "PLAN", S0


def kos(api, kuru=None, uygula=True, geri=False, ids=None):
    with tempfile.TemporaryDirectory() as d:
        try:
            s = Y.calis(api, SHOP, ids or [LID], kuru or KURU, d, uygula, geri); dur = None
        except SystemExit as e:
            s, dur = None, str(e)
        rows = list(csv.DictReader(open(pathlib.Path(d) / "DEGISIKLIK.csv", encoding="utf-8")))
    return s, dur, rows


def sonuc_satiri(rows):
    return [r for r in rows if r["sonuc"] != "EN_BASLADI"]


# ---------- 1 bilinen PASS: onayli "sonra" yazimi, birebir geri okuma, son okuma PASS
a = Sahte(); s, dur, rows = kos(a)
k("PASS yazim: EN + RU = kuru 'sonra' (birebir geri okuma), sonuc PASS", dur is None and sonuc_satiri(rows)[0]["sonuc"] == "PASS"
  and Y.norm(a.L["description"]) == Y.norm(KURU[LID]["en_sonra"]) and Y.norm(a.ru["description"]) == Y.norm(KURU[LID]["ru_sonra"]),
  (dur, rows))
k("PASS yazim: yeni EN / RU paragrafi canli metinde, eski soz yok", K.YENI_EN in a.L["description"].split("\n\n")
  and K.YENI_RU in a.ru["description"].split("\n\n") and K.SIL_EN.strip() not in a.L["description"]
  and K.SIL_RU.strip() not in a.ru["description"])
k("PASS son okuma: DEGISIKLIK son_okuma 'EN hedef / RU hedef | PASS'", sonuc_satiri(rows)[0]["son_okuma"] == "EN hedef / RU hedef | PASS",
  rows)
k("PASS DEGISIKLIK: once EN_BASLADI satiri, sonra sonuc satiri (en_utc, ru_utc, last_modified, parti 1)",
  [r["sonuc"] for r in rows] == ["EN_BASLADI", "PASS"] and rows[0]["en_utc"] and rows[1]["ru_utc"]
  and rows[1]["last_modified_timestamp"] == "2" and rows[1]["parti"] == "1", rows)
k("PASS yalniz aciklama: PATCH govdesi yalniz description; PUT RU baslik + etiket canli AYNEN; EN baslik / etiket degismedi",
  a.yaz[0][2].keys() == {"description"} and a.yaz[1][2]["title"] == D["ru"]["title"] and a.yaz[1][2]["tags"] == ",".join(D["ru"]["tags"])
  and a.L["title"] == D["title"] and a.L["tags"] == D["tags"] and [w[0] for w in a.yaz] == ["PATCH", "PUT"])
k(f"PASS istek: tipik 9 (3 okuma + PATCH + 1 + PUT + 1 + son okuma 2) <= butce {Y.ISTEK_ILAN}", a.calls == 9, a.calls)

# EN_BASLADI PATCH'ten ONCE diske yazilmis mi (flush): PATCH aninda dosya okunur
with tempfile.TemporaryDirectory() as dd:
    b = Sahte(); gor = {}
    eski_patch = b.patch

    def patch_gozle(path, data, _d=dd):
        gor["satir"] = list(csv.DictReader(open(pathlib.Path(_d) / "DEGISIKLIK.csv", encoding="utf-8")))
        return eski_patch(path, data)
    b.patch = patch_gozle
    Y.calis(b, SHOP, [LID], KURU, dd, True, False)
    k("PASS EN_BASLADI satiri PATCH aninda diskte (append + flush)", [r["sonuc"] for r in gor.get("satir", [])] == ["EN_BASLADI"], gor)

# kuru (uygula yok): yazim yok
b = Sahte(); s, dur, rows = kos(b, uygula=False)
k("PASS kuru kip: KURU, yazim yok", dur is None and rows[0]["sonuc"] == "KURU" and not b.yaz, (dur, rows))
# ZATEN_YENI: ikinci kosuda yazim yok, son okuma PASS
c = Sahte(); kos(c); n0 = len(c.yaz); s, dur, rows = kos(c)
k("PASS ZATEN_YENI: ikinci kosuda yazim yok, son okuma PASS", dur is None and rows[0]["sonuc"] == "ZATEN_YENI" and len(c.yaz) == n0
  and rows[0]["son_okuma"].endswith("PASS"), (dur, rows))

# ---------- 2 --geri-al (P1): EN = en_once, RU = ru_geri
m = Sahte(); kos(m); s, dur, rows = kos(m, geri=True)
k("PASS geri-al P1: EN = en_once, RU = ru_geri, GERI_ALINDI, son okuma PASS", dur is None and sonuc_satiri(rows)[0]["sonuc"] == "GERI_ALINDI"
  and Y.norm(m.L["description"]) == Y.norm(KURU[LID]["en_once"]) and Y.norm(m.ru["description"]) == Y.norm(KURU[LID]["ru_geri"])
  and sonuc_satiri(rows)[0]["son_okuma"] == "EN hedef / RU hedef | PASS", (dur, rows))
k("PASS geri-al: ru_geri = canli eski RU", Y.norm(KURU[LID]["ru_geri"]) == Y.norm(RU0))
s, dur, rows = kos(m, geri=True)
k("PASS geri-al ikinci kez: ZATEN_ESKI, yazim yok", dur is None and rows[0]["sonuc"] == "ZATEN_ESKI", (dur, rows))


# ---------- 3 yukle(): sha256 (ONCE_SONRA ve FARK ayri), FARK onay_ozet / durum
def kuru_dizin(d, kuru=None, fark_boz=None):
    d = pathlib.Path(d)
    (d / "ONCE_SONRA.json").write_text(json.dumps(kuru or KURU, ensure_ascii=False), encoding="utf-8")
    sat = dict(S0, onay_ozet=KURU[LID]["onay_ozet"], neden="")
    if fark_boz:
        sat.update(fark_boz)
    with open(d / "FARK.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sat), lineterminator="\n"); w.writeheader(); w.writerow(sat)
    return {n: hashlib.sha256((d / n).read_bytes()).hexdigest() for n in ("ONCE_SONRA.json", "FARK.csv")}


def yukle_dene(d, bek):
    try:
        return Y.yukle(d, bek), None
    except SystemExit as e:
        return None, str(e)


with tempfile.TemporaryDirectory() as d:
    h = kuru_dizin(d); kk, hata = yukle_dene(d, h)
    k("PASS yukle: sha256 ikisi de esit -> plan + yedek", hata is None and kk[LID]["onay_ozet"] == KURU[LID]["onay_ozet"] and "yedek" in kk[LID],
      hata)
    _, hata = yukle_dene(d, dict(h, **{"ONCE_SONRA.json": "0" * 64}))
    k("FAIL ONCE_SONRA sha256 farkli -> DUR (SystemExit, Etsy istegi yok)", hata and "ONCE_SONRA.json sha256 farkli" in hata, hata)
    _, hata = yukle_dene(d, dict(h, **{"FARK.csv": "0" * 64}))
    k("FAIL FARK sha256 farkli -> DUR", hata and "FARK.csv sha256 farkli" in hata, hata)
with tempfile.TemporaryDirectory() as d:
    h = kuru_dizin(d, fark_boz={"onay_ozet": "1" * 64}); _, hata = yukle_dene(d, h)
    k("FAIL FARK onay_ozet != ONCE_SONRA onay_ozet -> DUR", hata and "tutarsiz" in hata, hata)
with tempfile.TemporaryDirectory() as d:
    h = kuru_dizin(d, fark_boz={"durum": "DUR"}); _, hata = yukle_dene(d, h)
    k("FAIL FARK durum PLAN degil -> DUR", hata and "tutarsiz" in hata, hata)
k("yukle varsayilan sabitler = PLAN §6 sha256", Y.KURU_SHA == {
    "ONCE_SONRA.json": "56d86efaf7b32e7eec2ce7d1e44782eaac5d12cd3a36badf07e894af03843f9b",
    "FARK.csv": "c622807dc40f84b2cdcc9788f43f36b4073fa73806f0cd7732d5fdef2af7f065"})
gercek = KOK.parent.parent / "docs" / "p1" / "P1_KURU_20261104_1255"
if (gercek / "ONCE_SONRA.json").is_file():   # yalniz dalda (docs/p1 main'e girmez)
    kk, hata = yukle_dene(gercek, None)
    k("PASS yukle gercek kuru plan (dal docs/p1): sabit sha256 esit, 78 ilan, pilot 4570165628 var",
      hata is None and len(kk) == 78 and "4570165628" in kk, hata)


# ---------- 4 onay sozcugu + ids (Python) ve yml bash kapisi
def onay_dene(onay, ids, uygula, geri):
    try:
        return Y.onay_kontrol(onay, ids, uygula, geri), None
    except SystemExit as e:
        return None, str(e)


x, hata = onay_dene("P1-METIN-YAZ-4570165628", "4570165628", True, False)
k("PASS onay P1-METIN-YAZ-<ids>", hata is None and x == ["4570165628"], hata)
x, hata = onay_dene("P1-METIN-GERI-1,2", "1,2", True, True)
k("PASS onay P1-METIN-GERI-<ids> (geri-al ayri sozcuk)", hata is None and x == ["1", "2"], hata)
for ad, args in (("YAZ yerine KURU sozcugu", ("P1-METIN-KURU-4570165628", "4570165628", True, False)),
                 ("eski sozcuk POSTER-METIN", ("POSTER-METIN-YAZ-4570165628", "4570165628", True, False)),
                 ("ids farkli", ("P1-METIN-YAZ-4570165628", "4570165629", True, False)),
                 ("geri-al YAZ sozcuguyle", ("P1-METIN-YAZ-1", "1", True, True))):
    _, hata = onay_dene(*args)
    k(f"FAIL yanlis onay ({ad}) -> DUR", hata and "onay" in hata, hata)
_, hata = onay_dene("P1-METIN-YAZ-", "", True, False)
k("FAIL bos ids -> DUR", hata and "ids" in hata, hata)

try:
    import yaml
    yml = yaml.safe_load((KOK.parent.parent / ".github" / "workflows" / "poster-metin-yaz.yml").read_text())
    blok = [s_ for s_ in yml["jobs"]["yaz"]["steps"] if s_.get("name") == "Onay kapisi"][0]["run"]
    girdi = (yml.get(True) or yml.get("on"))["workflow_dispatch"]["inputs"]
except ImportError:
    blok = girdi = None


def bash_kapi(ids, onay, uygula, geri):
    env = dict(os.environ, IDS=ids, ONAY=onay, UYGULA=uygula, GERI=geri)
    return subprocess.run(["bash", "-e", "-c", blok], env=env, capture_output=True, text=True).returncode


if blok is not None:
    k("PASS yml bash onay kapisi: P1-METIN-YAZ-4570165628", bash_kapi("4570165628", "P1-METIN-YAZ-4570165628", "1", "0") == 0)
    k("FAIL yml bash: yanlis sozcuk", bash_kapi("4570165628", "POSTER-METIN-YAZ-4570165628", "1", "0") != 0)
    k("FAIL yml bash: KURU sozcuguyle yazim", bash_kapi("4570165628", "P1-METIN-KURU-4570165628", "1", "0") != 0)
    k("FAIL yml bash: bos ids", bash_kapi("", "P1-METIN-YAZ-", "1", "0") != 0)
    k("PASS yml bash: geri-al GERI sozcugu", bash_kapi("1", "P1-METIN-GERI-1", "1", "1") == 0)
    k("FAIL yml bash: geri-al YAZ sozcuguyle", bash_kapi("1", "P1-METIN-YAZ-1", "1", "1") != 0)
    yd = json.dumps(yml)
    k("yml: ids varsayilani bos, Python'a --onay geciyor, girdi TEMP/P1_KURU_20261104_1255, 3 Kas yolu yok",
      str(girdi["ids"].get("default", "")) == "" and '--onay \\"$ONAY\\"' in yd and "POSTER_KURU_20261103" not in yd
      and "YEDEK.json\"" not in yd and "for f in ONCE_SONRA.json FARK.csv" in yd and "TEMP/P1_KURU_20261104_1255" in yd, girdi)
else:
    k("yml testi icin PyYAML gerekli", False)

# ---------- 5 kota: ilan basi kalan >= 20 + 10
j = Sahte(kalan=Y.ISTEK_ILAN + E.KOTA_SINIRI - 1); s, dur, rows = kos(j)
k("FAIL kota kalan 29: ilan baslamaz (istek 0), DUR", dur and "kota" in dur and j.calls == 0, (dur, j.calls))
j2 = Sahte(kalan=Y.ISTEK_ILAN + E.KOTA_SINIRI); s, dur, rows = kos(j2)
k("PASS kota kalan 30: ilan yazilir", dur is None and sonuc_satiri(rows)[0]["sonuc"] == "PASS", dur)
j3 = Sahte(kalan=None); s, dur, _ = kos(j3)
k("FAIL kalan kota okunamiyor (None): ilk okumadan sonra DUR, yazim yok", dur and "x-remaining-today" in dur and not j3.yaz, dur)

# ---------- 6 canli ne once ne sonra / YARIM / yedek farki / state / RU bos
d1 = Sahte(en=EN0.replace("Every fusion symbol", "Each fusion symbol")); s, dur, rows = kos(d1)
k("FAIL canli EN ne once ne sonra: DUR (bayat, EN farkli / RU kaynak), yazim yok", dur and "bayat" in dur and "EN farkli" in dur
  and "RU kaynak" in dur and not d1.yaz, dur)
d2 = Sahte(ru=RU0 + "!"); s, dur, _ = kos(d2)
k("FAIL canli RU ne once ne sonra: DUR, yazim yok", dur and "bayat" in dur and "RU farkli" in dur and not d2.yaz, dur)
yr = Sahte(); kos(yr); yr.ru["description"] = RU0; n0 = len(yr.yaz); s, dur, _ = kos(yr)
k("FAIL YARIM (EN yeni, RU eski): DUR, yazim yok", dur and "YARIM" in dur and "EN hedef" in dur and "RU kaynak" in dur
  and len(yr.yaz) == n0, dur)
for ad, boz in (("EN baslik", lambda z: z.L.update(title=z.L["title"] + " x")), ("EN etiket", lambda z: z.L["tags"].append("yeni")),
                ("EN malzeme", lambda z: z.L.update(materials=["paper"])), ("RU baslik", lambda z: z.ru.update(title=z.ru["title"] + " x")),
                ("RU etiket", lambda z: z.ru["tags"].append("новый"))):
    g = Sahte(); boz(g); s, dur, _ = kos(g)
    k(f"FAIL {ad} yedekten farkli: DUR, yazim yok", dur and ad in dur and not g.yaz, dur)
f = Sahte(); f.L["state"] = "draft"; s, dur, _ = kos(f)
k("FAIL state draft: DUR, yazim yok", dur and "state" in dur and not f.yaz, dur)
bt = Sahte(); bt.ru["tags"] = []; kb = copy.deepcopy(KURU); kb[LID]["yedek"]["ru"]["tags"] = []; s, dur, _ = kos(bt, kuru=kb)
k("FAIL RU etiket bos: DUR (PUT etiketleri silebilir), yazim yok", dur and "bos" in dur and not bt.yaz, dur)

# ---------- 7 uyarlayici (p1_poster_kuru.plan_ilan) DUR / detay None / onay ozeti
u = Sahte(); u.inv["products"] = u.inv["products"][1:]   # 5x7 boyu yok: kur(EN once) != canli RU -> plan_ilan DUR
s, dur, _ = kos(u)
k("FAIL uyarlayici plan_ilan DUR (envanter boylari degismis): DUR, yazim yok", dur and "uyarlayici" in dur and "DUR" in dur
  and not u.yaz, dur)
_pi = K.plan_ilan
K.plan_ilan = lambda kayit, shop=K.SHOP: (dict(durum="PLAN", neden=[]), None)
try:
    u2 = Sahte(); s, dur, _ = kos(u2)
    k("FAIL uyarlayici detay None: DUR, yazim yok", dur and "uyarlayici" in dur and not u2.yaz, dur)
finally:
    K.plan_ilan = _pi
kb = copy.deepcopy(KURU); kb[LID]["onay_ozet"] = "0" * 64
e = Sahte(); s, dur, _ = kos(e, kuru=kb)
k("FAIL onay ozeti farkli: DUR, yazim yok", dur and "onay ozeti" in dur and not e.yaz, dur)
k("uyarlayici: canli kayit -> PLAN; RU bos (ru_gercek {}) -> ru_durum yok",
  Y.uyarlayici(LID, Sahte().L, Sahte().ru, Sahte().inv, SHOP)[0]["durum"] == "PLAN"
  and Y.uyarlayici(LID, Sahte().L, {}, Sahte().inv, SHOP)[0]["ru_durum"] == "yok")
# metin kapisi: canli metinde yasak ifade -> plan_ilan "metin kapisi uyari" -> DUR (kuru ayni canliyla kurulur)
en_y = EN0.replace("Keep away from direct sunlight", "Printed by Prodigi. Keep away from direct sunlight")
_, ky = kuru_plan(Sahte(en=en_y, ru=R.kur(en_y, {"boy": BOYKOD})[0]))
mk = Sahte(en=en_y, ru=ky[LID]["ru_once"]); s, dur, _ = kos(mk, kuru=ky)
k("FAIL metin kapisi eslesmesi (Prodigi): DUR, yazim yok", dur and "metin kapisi" in dur and not mk.yaz, dur)
en_b = EN0.replace(E.AI_BEYAN["en"], "We create the artwork")
_, kb2 = kuru_plan(Sahte(en=en_b, ru=R.kur(en_b, {"boy": BOYKOD})[0]))
ab = Sahte(en=en_b, ru=kb2[LID]["ru_once"]); s, dur, _ = kos(ab, kuru=kb2)
k("FAIL AI beyan kapisi (EN beyan yok): DUR, yazim yok", dur and "AI beyani eksik" in dur and not ab.yaz, dur)

# ---------- 8 geri okuma / RU hatasi / son okuma
i = Sahte(); i.patch_bozuk = True; s, dur, rows = kos(i)
k("FAIL EN geri okuma farki: DUR, RU yazilmadi, son okuma EN farkli / RU kaynak", dur and "EN geri okuma" in dur
  and [w[0] for w in i.yaz] == ["PATCH"] and sonuc_satiri(rows)[0]["son_okuma"].startswith("EN farkli / RU kaynak"), (dur, rows))
h2 = Sahte(); h2.ru_bozuk = True; s, dur, rows = kos(h2)
k("FAIL RU geri okuma farki: EN geri yazildi, RU'ya ek yazim yok, ELLE BAKILMALI, son okuma EN kaynak / RU farkli",
  dur and Y.norm(h2.L["description"]) == Y.norm(EN0) and [w[0] for w in h2.yaz] == ["PATCH", "PUT", "PATCH"]
  and sonuc_satiri(rows)[0]["sonuc"] == "FAIL" and "ELLE BAKILMALI" in sonuc_satiri(rows)[0]["neden"]
  and sonuc_satiri(rows)[0]["son_okuma"].startswith("EN kaynak / RU farkli"), (dur, rows))
h = Sahte(); h.ru_put_hata = True; s, dur, rows = kos(h)
r_ = sonuc_satiri(rows)[0] if sonuc_satiri(rows) else {}
k("FAIL RU PUT hatasi: EN yazimdan onceki metne geri yazildi, RU eski, DUR, FAIL satiri + geri_utc",
  dur and Y.norm(h.L["description"]) == Y.norm(EN0) and Y.norm(h.ru["description"]) == Y.norm(RU0)
  and [w[0] for w in h.yaz] == ["PATCH", "PUT", "PATCH"] and r_.get("sonuc") == "FAIL"
  and "EN yazimdan onceki metne geri yazildi" in r_.get("neden", "") and r_.get("geri_utc")
  and r_.get("son_okuma", "").startswith("EN kaynak / RU kaynak"), (dur, rows))
h3 = Sahte(); h3.put_islenip_hata = True; s, dur, rows = kos(h3)
k("FAIL PUT islendi + 5xx: canli RU yeni -> EN'ye dokunulmaz, TAMAM_HATALI, DUR",
  dur and Y.norm(h3.L["description"]) == Y.norm(KURU[LID]["en_sonra"]) and [w[0] for w in h3.yaz] == ["PATCH", "PUT"]
  and sonuc_satiri(rows)[0]["sonuc"] == "TAMAM_HATALI", (dur, rows))
t = Sahte(); t.patch_timeout = True; s, dur, rows = kos(t)
k("FAIL ag hatasi (Timeout) PATCH sirasinda: DUR, EN_BASLADI + FAIL satiri (ELLE BAKILMALI), PUT yok",
  dur and [r["sonuc"] for r in rows] == ["EN_BASLADI", "FAIL"] and "ELLE BAKILMALI" in rows[1]["neden"]
  and not [w for w in t.yaz if w[0] == "PUT"], (dur, rows))
t2 = Sahte(); t2.patch_islenip_hata = True; s, dur, rows = kos(t2)
k("FAIL PATCH islendi + 5xx: DUR, RU yazilmadi, 'EN yazilmis olabilir', son okuma EN hedef / RU kaynak",
  dur and "EN yazilmis olabilir" in sonuc_satiri(rows)[0]["neden"] and not [w for w in t2.yaz if w[0] == "PUT"]
  and sonuc_satiri(rows)[0]["son_okuma"].startswith("EN hedef / RU kaynak"), (dur, rows))
so = Sahte(); so.son_bozuk = True; s, dur, rows = kos(so)
k("FAIL son okuma (baslik yazimdan sonra farkli): DUR, sonuc FAIL, rapor 'EN baslik yedekten farkli'",
  dur and sonuc_satiri(rows)[0]["sonuc"] == "FAIL" and "EN baslik yedekten farkli" in sonuc_satiri(rows)[0]["son_okuma"], (dur, rows))
ok_, rap = Y.son_okuma(dict(Sahte().L, description=KURU[LID]["en_sonra"]), dict(Sahte().ru, description=KURU[LID]["ru_sonra"]),
                       KURU[LID], False)
k("PASS son_okuma fonksiyonu (hedef metin + yedek + active)", ok_ and rap == "EN hedef / RU hedef | PASS", rap)
ok_, rap = Y.son_okuma(dict(Sahte().L, description=KURU[LID]["en_sonra"], state="draft"),
                       dict(Sahte().ru, description=KURU[LID]["ru_sonra"]), KURU[LID], False)
k("FAIL son_okuma: state draft", not ok_ and "state draft" in rap, rap)

# ---------- 9 parti: 20 / 20 / 20 / 17 tanimi; DUR sonraki ilani yazmaz
k("parti boyu 20 (77 -> 20/20/20/17)", Y.PARTI_BOYU == 20 and [min(20, 77 - i_) for i_ in range(0, 77, 20)] == [20, 20, 20, 17])
pz = Sahte(); s, dur, rows = kos(pz, ids=[LID, "999"])
k("FAIL kuru planda olmayan ikinci ilan: ilk PASS, ikinci DUR (kuru plan yok)", dur and "kuru plan yok" in dur
  and [r["sonuc"] for r in rows] == ["EN_BASLADI", "PASS", "DUR"], (dur, rows))

# ---------- 10 RU kapisi gercek: izinsiz poster RU metni DUR
E.RU_POSTER_IZIN.clear()
try:
    E.ru_yazim_kapisi("PUT", f"/shops/1/listings/{LID}/translations/ru", data={"title": "x", "description": "baska metin", "tags": ""}); kapi = False
except SystemExit:
    kapi = True
k("RU kapisi: izinsiz poster RU metni DUR (gercek kapi)", kapi)

# ---------- 11 GERCEK Etsy._call yolu (sahte requests): html_coz, ru_yazim_kapisi, AI beyan, metin kapisi, KOTA_SINIRI tabani
import requests  # noqa: E402


class Yanit:
    def __init__(self, kod, govde, kalan):
        self.status_code, self._g, self.headers, self.text = kod, govde, {"x-remaining-today": str(kalan)}, json.dumps(govde)

    def json(self):
        return self._g


def gercek_api(sahte):
    def istek(method, url, params=None, data=None, json=None, headers=None, timeout=None):
        path = url.split("/v3/application", 1)[1]
        try:
            if method == "GET":
                g = sahte.get(path)
            elif method == "PATCH":
                sahte.patch(path, data); g = {}
            elif method == "PUT":
                sahte.put(path, data); g = {}
            else:
                raise AssertionError(method)
        except SystemExit:
            return Yanit(503, {}, sahte.remaining)
        return Yanit(200, g, sahte.remaining)
    requests.request = istek
    api = E.Etsy.__new__(E.Etsy)
    E.Etsy.__init__(api, type("S", (), {"access_token": "x", "api_key_header": "k", "needs_refresh": lambda self: False})())
    api._headers = lambda tok=None: {}
    api.pace = 0
    api._erken_yenile = lambda: None
    return api


gercek_req = requests.request
try:
    g1 = Sahte(); api = gercek_api(g1); E.METIN_UYARI.clear(); E.RU_POSTER_IZIN.clear()
    s, dur, rows = kos(api)
    k("gercek _call: normal akis PASS (gercek kapilar), metin kapisi uyari 0, son okuma PASS", dur is None
      and sonuc_satiri(rows)[0]["sonuc"] == "PASS" and Y.norm(g1.ru["description"]) == Y.norm(KURU[LID]["ru_sonra"])
      and not E.METIN_UYARI and sonuc_satiri(rows)[0]["son_okuma"].endswith("PASS"), (dur, rows, E.METIN_UYARI[:2]))
    k("gercek _call: gonderilen EN HTML varliksiz (&#39; yok)", "&#39;" not in g1.yaz[0][2]["description"] and "'" in g1.yaz[0][2]["description"])
    g2 = Sahte(); api = gercek_api(g2); E.RU_POSTER_IZIN.clear()
    kb3 = copy.deepcopy(KURU); kb3[LID]["ru_sonra"] = kb3[LID]["ru_sonra"] + "\nEK SATIR"
    s, dur, _ = kos(api, kuru=kb3)
    k("gercek _call FAIL: kuru RU degistirilmis -> yazim yok", dur and not g2.yaz, dur)
finally:
    requests.request = gercek_req
print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
