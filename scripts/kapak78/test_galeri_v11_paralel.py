#!/usr/bin/env python3
"""Galeri v11b hiz (Serdar 29 Eki: --isci 4, ONAR) yerel testi. Ag / Drive / Etsy yok, sure < 60 sn hedefi.
1. etsy_common.Etsy: iki is parcacigi ayni anda 401 alir -> TEK token yenilemesi, ikisi de yeni tokenla 200; ortak tempo (pace) tum
   iscilerde istek baslangiclarini en az pace arayla dizer; ilk yanittan once paralel istek "kota basligi okunamadi" DUR'u vermez.
2. Yukleyici: 6 ilan (4 v11b + 2 ONAR), kuru PLAN 6 (tur ONAR 2), yazim --isci 4 PASS 6; ONAR ilanlarinda rank 1 yeni yuklenen B1 MB
   kapak (alt metni B1'deki), W01 silinmis, 2-10 kimlikleri ayni, baglar MB 7 DB 8 PW 9 WP 10 (CI bagsiz); v11b ilanlarinda rank 1
   dokunulmaz; her ilan yalniz kendi galerisine yazar; DEVAM / ILERLEME 6 ilan; ETA satiri 6 kez."""
import contextlib
import csv
import io
import json
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

_GERCEK_UYKU = time.sleep   # test_eski78 time.sleep'i etkisiz yapar (modul geneli); tempo testi gercek uyku ister

from PIL import Image

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "etsy")); sys.path.insert(0, str(KOK / "scripts" / "kapak78"))
import test_galeri_v10 as T10  # noqa: E402
T10.ILAN.update({"4570111222": ("ARIES_LEO", "Aries", "Leo"), "4570111333": ("CANCER_VIRGO", "Cancer", "Virgo"),
                 "4570111444": ("GEMINI_LIBRA", "Gemini", "Libra"), "4570111555": ("LEO_TAURUS", "Leo", "Taurus")})
import test_galeri_v11 as T11  # noqa: E402
import test_galeri_v11b as TB  # noqa: E402
import galeri_v10_liste as L  # noqa: E402
import galeri_v10_yukle as V  # noqa: E402
import galeri_v11_yukle as Y11  # noqa: E402
import etsy_common as E  # noqa: E402

V.profil_kur("v11b", Y11.ek_kapi)
SONUC = []
ONAR = ("4570111444", "4570111555")
V11_BAG = {"Champagne Ivory": 1, "Midnight Blue": 7, "Deep Black": 8, "Pure White": 9, "Warm Parchment": 10}


def kontrol(ad, ok):
    SONUC.append((ad, bool(ok))); print(("PASS " if ok else "FAIL ") + ad, flush=True)


# ---------------------------------------------------------------- 1) etsy_common is parcacigi guvenligi
class Yanit:
    def __init__(self, kod, rem=5000):
        self.status_code, self.headers, self.text = kod, {"x-remaining-today": str(rem)}, ""

    def json(self):
        return {}


class Depo:
    def __init__(self):
        self.tok, self.n_yenile, self.api_key_header = "A", 0, "k:s"

    @property
    def access_token(self):
        return self.tok

    def refresh(self):
        self.n_yenile += 1; time.sleep(0.05); self.tok = "T%d" % self.n_yenile


def etsy_testi():
    d = Depo(); api = E.Etsy(d); api.pace = 0.05
    zaman, kilit = [], threading.Lock()

    def istek(method, url, **k):
        with kilit:
            zaman.append(time.monotonic())
        time.sleep(0.02)
        return Yanit(401 if k["headers"]["Authorization"] == "Bearer A" else 200)
    eski, E.requests.request = E.requests.request, istek
    eski_uyku, time.sleep = time.sleep, _GERCEK_UYKU
    hata = []
    try:
        th = [threading.Thread(target=lambda: (lambda: api.get("/x"))() if True else None) for _ in range(2)]

        def kos():
            try:
                api.get("/x")
            except SystemExit as e:
                hata.append(str(e.code))
        th = [threading.Thread(target=kos) for _ in range(4)]
        for t in th:
            t.start()
        for t in th:
            t.join()
    finally:
        E.requests.request = eski; time.sleep = eski_uyku
    kontrol(f"etsy: 4 isci ayni anda 401 -> TEK token yenilemesi ({d.n_yenile}), hepsi 200, kota basligi DUR'u yok ({hata})",
            d.n_yenile == 1 and not hata)
    ara = [b - a for a, b in zip(zaman, zaman[1:])]
    kontrol(f"etsy: ortak tempo, istek baslangiclari arasi en az {min(ara):.3f} sn (pace 0.05)", ara and min(ara) >= 0.045)
    kontrol(f"etsy: calls {api.calls} = istek sayisi {len(zaman)}", api.calls == len(zaman))


# ---------------------------------------------------------------- 2) yukleyici 6 ilan, 2 ONAR, --isci 4
def onar_kur(d, g, canli):
    """ONAR ilanlari: canli 10 gorsel v11 durumu (W01..W10), B1 yedeginde gercek JPEG r1."""
    sab = {int(x["sira"]): x for x in csv.DictReader(open(KOK / "data/pod/galeri_v11_alt.csv", encoding="utf-8-sig"))}
    for lid in ONAR:
        cift, a, b = T10.ILAN[lid]; base = int(lid[-3:]) * 100
        alt = L.alt_metin(sab, a, b)
        y = Path(g["yd"]) / f"{lid}_{cift}"
        Image.new("RGB", (300, 225), (20, 30, 70)).save(y / f"r1_{base + 1}.jpg", "JPEG")
        j = json.loads((y / "GALERI.json").read_text()); j["gorseller"][0]["alt_text"] = f"eski MB kapak {cift}"
        (y / "GALERI.json").write_text(json.dumps(j))
        gor = [dict(rank=r, listing_image_id=base + 50 + r, alt_text=alt[r]) for r in range(1, 11)]
        bag = [dict(property_id=200, value_id=T10.VID[k], value=k, image_id=base + 50 + r) for k, r in V11_BAG.items()]
        c = Path(canli) / f"{lid}_{cift}"
        (c / "GALERI.json").write_text(json.dumps(dict(listing_id=lid, cift=cift, ilan=dict(state="active"), gorseller=gor, baglar=bag,
                                                       videolar=[])))
    return {lid: [(r, int(lid[-3:]) * 100 + 50 + r) for r in range(1, 11)] for lid in ONAR}


def sahte_kur(onar_canli, alt_v11):
    sh = {}
    for lid in T10.ILAN:
        if lid in onar_canli:
            base = int(lid[-3:]) * 100
            f = T11.S11(lid, onar_canli[lid], {k: base + 50 + r for k, r in V11_BAG.items()})
            for x in f.img:
                x["alt_text"] = alt_v11[lid][x["rank"]]
            f.max_n = 0
        else:
            f = T11.sahte(lid)
        sh[lid] = f
    return sh


def main():
    t_bas = time.time()
    etsy_testi()
    t0 = Path(tempfile.mkdtemp(prefix="gv11p_"))
    try:
        d = t0 / "a"; d.mkdir(); g = T11.girdi(d); canli = TB.canli_kur(d, g)
        oc = onar_kur(d, g, canli)
        sab = {int(x["sira"]): x for x in csv.DictReader(open(KOK / "data/pod/galeri_v11_alt.csv", encoding="utf-8-sig"))}
        alt_v11 = {lid: L.alt_metin(sab, *T10.ILAN[lid][1:]) for lid in ONAR}
        rc, oz = TB.liste(d, g, canli, yazim=True)
        tur = {k: v.get("tur") for k, v in (oz or {}).get("ilanlar", {}).items()}
        kontrol(f"liste: 6 HAZIR, tur ONAR 2 / V11B 4 ({sorted(tur.values())})",
                rc == 0 and all(x["durum"] == "HAZIR" for x in oz["ilanlar"].values())
                and sorted(tur.values()) == ["ONAR"] * 2 + ["V11B"] * 4)
        for lid in ONAR:
            rows = list(csv.DictReader(open(d / "hazir" / lid / f"LISTE_{lid}.csv")))
            base = int(lid[-3:]) * 100
            kontrol(f"liste ONAR {lid}: 1 DEGISTIR (B1 MB kapak, alt B1), 9 KORU, CIKAR yalniz W01",
                    [x["islem"] for x in rows if x["hedef_sira"]] == ["DEGISTIR"] + ["KORU"] * 9
                    and rows[0]["hedef_alt"] == f"eski MB kapak {T10.ILAN[lid][0]}"
                    and [x["simdi_id"] for x in rows if x["islem"] == "CIKAR"] == [str(base + 51)])
        sh = sahte_kur(oc, alt_v11)
        api = T10.Coklu(sh); o = t0 / "o"; o.mkdir()
        rc, R = TB.kos(api, d / "hazir", o)
        kontrol(f"kuru: PLAN 6 ({R.get('sayilar')})", rc == 0 and R["sayilar"].get("PLAN") == 6)
        ist = {x["ilan"]: (x["en_az"], x["en_kotu"]) for x in R["ilanlar"]}
        kontrol(f"kuru: istek tahmini ONAR {ist[ONAR[0]]} / v11b {ist['4570110121']}", all(v[0] for v in ist.values()))
        shutil.copyfile(o / "PLAN_V11B.json", t0 / "PLAN.json")
        args = ["--hazir", str(d / "hazir"), "--out", str(o), "--bes-x7", "zorunlu", "--kosu", "889", "--isci", "4",
                "--devam", str(o / "DEVAM.json"), "--ilerleme", str(o / "ILERLEME.json"),
                "--confirm", "GALERI_V11B", "--plan", str(t0 / "PLAN.json"), "--plan-damga", R["plan_damga"]]
        a = V.arg(args); Y11.on_kapi(a, "v11b")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = V.sonlandir(api, "1", a)
        out = buf.getvalue(); R = json.loads((o / "RAPOR.json").read_text())
        kontrol(f"yazim --isci 4: PASS 6 ({R['sayilar']})", rc == 0 and R["sayilar"].get("PASS") == 6)
        kontrol(f"yazim: ETA satiri 6 ({out.count('ETA: ')}), ISCI 4 satiri", out.count("ETA: ") == 6 and "ISCI 4" in out)
        for lid in ONAR:
            f = sh[lid]; base = int(lid[-3:]) * 100
            gal = sorted(f.img, key=lambda x: x["rank"]); rk = {x["listing_image_id"]: x["rank"] for x in gal}
            kontrol(f"ONAR {lid}: rank 1 yeni MB kapak (alt B1), W01 silindi, 2-10 ayni kimlik, baglar MB7 DB8 PW9 WP10 CI yok",
                    len(gal) == 10 and gal[0]["listing_image_id"] >= 7000 and gal[0]["alt_text"] == f"eski MB kapak {T10.ILAN[lid][0]}"
                    and f.silinenler == [base + 51] and [x["listing_image_id"] for x in gal[1:]] == [base + 50 + r for r in range(2, 11)]
                    and f.n_yukle == 1 and {k: rk.get(v) for k, v in f.bag.items()} == TB.BAG_B)
        for lid in [x for x in T10.ILAN if x not in ONAR]:
            f = sh[lid]; base = int(lid[-3:]) * 100
            gal = sorted(f.img, key=lambda x: x["rank"]); rk = {x["listing_image_id"]: x["rank"] for x in gal}
            kontrol(f"v11b {lid}: rank 1 dokunulmaz, 10 gorsel, 9 yukleme, 8 silme, baglar 4",
                    gal[0]["listing_image_id"] == base + 1 and len(gal) == 10 and f.n_yukle == 9 and len(f.silinenler) == 8
                    and {k: rk.get(v) for k, v in f.bag.items()} == TB.BAG_B)
        yabanci = [(lid, y) for lid, f in sh.items() for y in f.yaz if len(y) > 1 and isinstance(y[1], int) and y[0] in ("sil", "sira")
                   and y[1] not in {x["listing_image_id"] for x in f.img} | set(f.silinenler)]
        kontrol(f"yazim: her ilan yalniz kendi gorsellerine yazdi (yabanci {yabanci[:2]})", not yabanci)
        il = json.loads((o / "ILERLEME.json").read_text())["ilanlar"]; dv = json.loads((o / "DEVAM.json").read_text())["ilanlar"]
        kontrol(f"durum dosyalari: ILERLEME PASS {sum(v.get('durum') == 'PASS' for v in il.values())}, DEVAM {len(dv)}",
                sum(v.get("durum") == "PASS" for v in il.values()) == 6 and len(dv) == 6)
    finally:
        shutil.rmtree(t0, ignore_errors=True)
    sure = time.time() - t_bas
    kontrol(f"sure {sure:.1f} sn < 60", sure < 60)
    bad = [a for a, ok in SONUC if not ok]
    print(f"galeri_v11 paralel testleri: {len(SONUC) - len(bad)}/{len(SONUC)} PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
