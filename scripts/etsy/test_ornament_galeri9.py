#!/usr/bin/env python3
"""ornament_galeri9.py sahte Etsy testleri (ag yok). Sahte Etsy olcumle kurulu (6 Kas ESIT: ayni rank'a yukleme kaydirmaz; 30 Eyl: silme
rank sikistirmaz); kaydirmali mod da denenir. Bilinen PASS: tam akis (iki mod). Bilinen FAIL: yedek disi gorsel / video silme, bilinmeyen
gorsel, baslik farki, baslangicta active (PATCH yok, DUR), pilot once, video 4xx (isaret geri), yarim kosudan devam, yabanci video.
8 Kas: yeni sira (2. sembol karti); sira modu: yalniz 2-6, baglar / video ayni, devam, yazimdan ONCE tam on kontrol (yer degisimi, alt metin,
ters bag, rank cakismasi, bilinmeyen gorsel), yalniz CANCER_LIBRA, acil inactive, video / variation yasak, geri okuma FAIL, eski sirali yarim
cift DUR, pilot kapisi bilinen FAIL ve PASS."""
import copy, csv, html, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ornament_galeri9 as g  # noqa: E402

KOK = Path(__file__).resolve().parents[2]


def yedek(pair="CANCER_LIBRA"):
    r = [x for x in csv.DictReader(open(KOK / "data/pod/ORNAMENT78_METIN.csv", encoding="utf-8")) if x["kod"] == pair][0]
    return {pair: dict(listing_id=4611501158, state="draft", baslik=html.unescape(r["baslik"]),
                       gorsel=[dict(id=7000 + i, rank=i, alt="x", w=3000, h=2250, url="") for i in range(1, 12)],
                       video=[dict(id=555, state="active", url="")],
                       bag={str(9000 + k): 7000 + rk for k, rk in enumerate([7, 8, 9, 10, 11])},
                       stil={s: 9000 + k for k, s in enumerate(["Ruby", "Sapphire", "Emerald", "White", "Ivory"])})}


def medya_kur(d, pair="CANCER_LIBRA"):
    k = Path(d) / pair; k.mkdir(parents=True)
    for x in g.GALERI:
        (k / f"{pair}_{x}.jpg").write_bytes(b"jpg")
    (k / f"{pair}_VIDEO.mp4").write_bytes(b"mp4")
    (k / f"{pair}_OLCUM.json").write_text(json.dumps({"sonuc": "PASS"}))


def calis(Y, out, ayar=None, kaydir=False):
    api = g.Kuru("39729443", Y); api.ilan(Y["CANCER_LIBRA"]); api.kaydir = kaydir
    if ayar:
        ayar(api)
    return api, g.yaz(api, "39729443", Path(out), "CANCER_LIBRA", Y)


def bekle_dur(fn, metin):
    try:
        fn()
    except SystemExit as e:
        assert metin in str(e.code), (metin, e.code)
        return
    raise AssertionError(f"DUR bekleniyordu: {metin}")


def main():
    with tempfile.TemporaryDirectory() as t:
        os.environ["IMG_ROOT"] = t + "/img"; os.environ["BOYUT_KAPI"] = "0"; medya_kur(t + "/img")
        Y = yedek()
        # 1 PASS
        o = Path(t, "o1"); o.mkdir(); api, R = calis(Y, o)
        assert all(R["kontrol"].values()), R["kontrol"]
        assert sorted(x["rank"] for x in api.ims) == list(range(1, 15)) and len(api.vids) == 1 and not [k for k in api.kayit if k["method"] == "PATCH"]
        o = Path(t, "o1b"); o.mkdir(); api, R = calis(Y, o, kaydir=True)
        assert all(R["kontrol"].values()), ("kaydirmali", R["kontrol"])
        # 2 yedek disi gorsel silme yasak
        api2 = g.Kuru("39729443", Y); api2.lid, api2.sil_izin = 4611501158, frozenset({7001})
        bekle_dur(lambda: api2._izin("DELETE", "/shops/39729443/listings/4611501158/images/7002"), "yedekte olmayan gorsel")
        bekle_dur(lambda: api2._izin("DELETE", "/shops/39729443/listings/4611501158/videos/999"), "yedekte olmayan video")
        bekle_dur(lambda: api2._izin("DELETE", "/shops/39729443/listings/123/images/7001"), "YASAK")
        bekle_dur(lambda: api2._izin("PUT", "/listings/4611501158/inventory"), "YASAK")
        # 3 bilinmeyen gorsel
        o = Path(t, "o3"); o.mkdir()
        def ek(a): a.ims.append(dict(listing_image_id=123456, rank=12, alt_text="", full_width=1, full_height=1))
        bekle_dur(lambda: calis(Y, o, ek), "bilinmeyen gorsel")
        # 4 baslik farki
        o = Path(t, "o4"); o.mkdir()
        bekle_dur(lambda: calis(Y, o, lambda a: a.L.update(title="baska")), "kimlik")
        # 5 baslangicta active -> PATCH YOK, DUR
        o = Path(t, "o5"); o.mkdir()
        sak = {}
        def akt(a): a.L.update(state="active"); sak["api"] = a
        bekle_dur(lambda: calis(Y, o, akt), "dokunulmadi")
        assert not [k for k in sak["api"].kayit if k["method"] == "PATCH"]
        # 7 pilot once: CANCER_LIBRA tamam degilken baska cift DUR
        Y2 = yedek("LEO_LEO"); Y2["LEO_LEO"]["listing_id"] = 4611500000
        o = Path(t, "o7"); o.mkdir(); a7 = g.Kuru("39729443", Y2); a7.ilan(Y2["LEO_LEO"]); a7.kuru = False; medya_kur(t + "/img", "LEO_LEO")
        bekle_dur(lambda: g.yaz(a7, "39729443", o, "LEO_LEO", Y2), "pilotu")
        # 8 video 4xx: isaret geri alinir, yeniden kosuda video yuklenir
        o = Path(t, "o8"); o.mkdir()
        a8 = g.Kuru("39729443", Y); a8.ilan(Y["CANCER_LIBRA"]); asil8 = a8.post_file
        def red(path, files, data=None):
            if path.endswith("/videos"):
                raise SystemExit(f"HATA: POST(file) {path} -> 400: bad video")
            return asil8(path, files, data)
        a8.post_file = red
        bekle_dur(lambda: g.yaz(a8, "39729443", o, "CANCER_LIBRA", Y), "-> 400")
        assert json.load(open(o / "DURUM9.json"))["ciftler"]["CANCER_LIBRA"]["video_gonderildi"] is False
        a8.post_file = asil8
        R = g.yaz(a8, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        # 9 yabanci video
        o = Path(t, "o9"); o.mkdir()
        bekle_dur(lambda: calis(Y, o, lambda a: a.vids.append(dict(video_id=777, video_state="active"))), "yedekte olmayan video")
        # 6 yarim kosu: 5 yuklemeden sonra kopma, yeniden kosuda devam, ikinci kopya yok
        o = Path(t, "o6"); o.mkdir()
        api = g.Kuru("39729443", Y); api.ilan(Y["CANCER_LIBRA"])
        asil = api.post_file; say = {"n": 0}
        def kopan(path, files, data=None):
            if path.endswith("/images"):
                say["n"] += 1
                if say["n"] == 6:
                    raise SystemExit("HATA: baglanti koptu")
            return asil(path, files, data)
        api.post_file = kopan
        bekle_dur(lambda: g.yaz(api, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        api.post_file = asil
        R = g.yaz(api, "39729443", o, "CANCER_LIBRA", Y)
        assert all(R["kontrol"].values()), R["kontrol"]
        assert len(api.ims) == 14, len(api.ims)
        # 10 yeni sira: 2. gorsel sembol karti (Serdar 8 Kas)
        assert g.GALERI[1] == "06_SEMBOL" and g.SIRA_DEG == [2, 3, 4, 5, 6]
        o = Path(t, "o10"); o.mkdir(); api, R = calis(Y, o)
        ims = sorted(api.ims, key=lambda x: x["rank"])
        assert "Two Signs, One Shared Symbol" in ims[1]["alt_text"] and "STYLE" in ims[9]["alt_text"].upper()
        assert [k["dosya"]["image"]["ad"] for k in api.kayit if k.get("dosya") and "image" in k["dosya"]][:2] == \
            ["CANCER_LIBRA_01_KAPAK.jpg", "CANCER_LIBRA_06_SEMBOL.jpg"]
        # 11 sira modu: eski sirayla tamam pilot -> yalniz 2-6 silinir ve yeniden yuklenir; baglar ve video ayni; yarim kosudan devam
        def eski_durum(o):
            D = {"ciftler": {"CANCER_LIBRA": {"yeni": {str(n): 60000 + n for n in range(1, 15)}, "tamam": True}}, "tamam": ["CANCER_LIBRA"]}
            json.dump(D, open(Path(o) / "DURUM9.json", "w"))
            return D
        def sira_api(D):
            a = g.Kuru("39729443", Y); a.ilan_sira(Y["CANCER_LIBRA"], D["ciftler"]["CANCER_LIBRA"], "CANCER_LIBRA"); return a
        o = Path(t, "o11"); o.mkdir(); D = eski_durum(o); a11 = sira_api(D)
        R = g.sira(a11, "39729443", o, "CANCER_LIBRA", Y)
        assert all(R["kontrol"].values()), R["kontrol"]
        sil = [k["url"].rsplit("/", 1)[1] for k in a11.kayit if k["method"] == "DELETE"]
        assert sorted(int(x) for x in sil) == [60002, 60003, 60004, 60005, 60006], sil
        assert not [k for k in a11.kayit if k["method"] in ("PATCH", "PUT") or k["url"].endswith("variation-images") and k["method"] != "GET"]
        assert not [k for k in a11.kayit if "/videos" in k["url"] and k["method"] != "GET"]
        D2 = json.load(open(o / "DURUM9.json")); assert "CANCER_LIBRA" in D2["sira_v2"]
        R2 = g.sira(a11, "39729443", o, "CANCER_LIBRA", Y); assert "kontrol" not in R2          # ikinci kez: dokunmaz
        o = Path(t, "o12"); o.mkdir(); D = eski_durum(o); a12 = sira_api(D); asil12 = a12.post_file; say12 = {"n": 0}
        def kopan12(path, files, data=None):
            say12["n"] += 1
            if say12["n"] == 3:
                raise SystemExit("HATA: baglanti koptu")
            return asil12(path, files, data)
        a12.post_file = kopan12
        bekle_dur(lambda: g.sira(a12, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        a12.post_file = asil12
        R = g.sira(a12, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        assert len(a12.ims) == 14
        o = Path(t, "o13"); o.mkdir(); D = eski_durum(o); a13 = sira_api(D)
        a13.ims.append(dict(listing_image_id=123, rank=15, alt_text="", full_width=1, full_height=1))
        bekle_dur(lambda: g.sira(a13, "39729443", o, "CANCER_LIBRA", Y), "on kontrol")
        assert not [k for k in a13.kayit if k["yazma"]]
        o = Path(t, "o14"); o.mkdir(); D = eski_durum(o); a14 = sira_api(D); a14.vis = a14.vis[:4]
        bekle_dur(lambda: g.sira(a14, "39729443", o, "CANCER_LIBRA", Y), "stil baglari")
        o = Path(t, "o15"); o.mkdir()
        Path(t, "o15x").mkdir(); a15 = sira_api(eski_durum(Path(t, "o15x")))       # DURUM9 o15'te yok
        bekle_dur(lambda: g.sira(a15, "39729443", o, "CANCER_LIBRA", Y), "tamam degil")
        o = Path(t, "o15b"); o.mkdir(); D15 = eski_durum(o); D15["ciftler"]["CANCER_LIBRA"]["tamam"] = False
        json.dump(D15, open(o / "DURUM9.json", "w"))
        bekle_dur(lambda: g.sira(a15, "39729443", o, "CANCER_LIBRA", Y), "tamam degil")
        # inceleme 1: on kontrol yazimdan ONCE (7-8 yer degistirmis, alt metin degismis, stil baglari ters, rank cakismasi) -> yazma yok
        def on_dur(ad, boz):
            o = Path(t, ad); o.mkdir(); D = eski_durum(o); a = sira_api(D); boz(a)
            bekle_dur(lambda: g.sira(a, "39729443", o, "CANCER_LIBRA", Y), "on kontrol")
            assert not [k for k in a.kayit if k["yazma"]], ad
            assert "once" in json.load(open(o / "S9_CANCER_LIBRA.json"))
        def yer(a):
            x7, x8 = [x for x in a.ims if x["rank"] in (7, 8)]; x7["rank"], x8["rank"] = 8, 7
        on_dur("c1", yer)
        on_dur("c2", lambda a: a.ims[6].update(alt_text="elle degisti"))
        def ters(a):
            a.vis[0]["image_id"], a.vis[1]["image_id"] = a.vis[1]["image_id"], a.vis[0]["image_id"]
        on_dur("c3", ters)
        on_dur("c4", lambda a: a.ims[7].update(rank=7))
        # inceleme 2: sira yalniz CANCER_LIBRA; yaz() yeni sirayla yazilani sira_v2'ye ekler
        bekle_dur(lambda: g.sira(a11, "39729443", Path(t, "o11"), "LEO_LEO", Y2), "yalniz CANCER_LIBRA")
        o = Path(t, "o17"); o.mkdir(); api, R = calis(Y, o)
        assert "CANCER_LIBRA" in json.load(open(o / "DURUM9.json"))["sira_v2"]
        # inceleme 4: yazimdan sonra active -> acil inactive + DUR; video / variation-images yazimi yasak
        o = Path(t, "o18"); o.mkdir(); D = eski_durum(o); a18 = sira_api(D); asil18 = a18.post_file
        def akt18(path, files, data=None):
            r = asil18(path, files, data); a18.L["state"] = "active"; return r
        a18.post_file = akt18
        try:
            g.sira(a18, "39729443", o, "CANCER_LIBRA", Y); raise AssertionError("DUR bekleniyordu")
        except SystemExit as e:
            assert e.code == 2, e.code
        assert [k for k in a18.kayit if k["method"] == "PATCH"] and a18.L["state"] == "inactive"
        a19 = sira_api(eski_durum(Path(t, "o18"))); a19.lid = 4611501158; a19.yalniz_gorsel = True
        bekle_dur(lambda: a19._izin("POST", "/shops/39729443/listings/4611501158/videos"), "sira modu")
        bekle_dur(lambda: a19._izin("POST", "/shops/39729443/listings/4611501158/variation-images"), "sira modu")
        # geri okuma yanlisi yakalar: Etsy silmeyi uygulamazsa (eski gorsel kalir) FAIL
        o = Path(t, "o20"); o.mkdir(); D = eski_durum(o); a20 = sira_api(D); asil20 = a20._sim
        a20._sim = lambda m, p, js: {} if (m == "DELETE" and "/images/" in p) else asil20(m, p, js)
        bekle_dur(lambda: g.sira(a20, "39729443", o, "CANCER_LIBRA", Y), "FAIL kontrol")
        # inceleme 8: eski sirayla yarim cift yaz()'da DUR
        o = Path(t, "o21"); o.mkdir()
        json.dump({"ciftler": {"CANCER_LIBRA": {"yeni": {"1": 1, "2": 2}}}}, open(o / "DURUM9.json", "w"))
        bekle_dur(lambda: calis(Y, o), "eski sirayla yarim")
        # pilot kapisi: CANCER_LIBRA eski sirayla tamam ama sira_v2 yok -> baska cift DUR
        o = Path(t, "o16"); o.mkdir(); eski_durum(o)
        a16 = g.Kuru("39729443", Y2); a16.ilan(Y2["LEO_LEO"]); a16.kuru = False
        bekle_dur(lambda: g.yaz(a16, "39729443", o, "LEO_LEO", Y2), "pilotu")
        # inceleme 2. tur: silme basladiktan sonra, ilk yuklemeden once kopma (J1 ilk yukleme, J2 ikinci silme) -> devam PASS
        for ad, nokta in (("j1", "post"), ("j2", "delete")):
            o = Path(t, ad); o.mkdir(); D = eski_durum(o); aj = sira_api(D); say_j = {"n": 0}
            asil_p, asil_c = aj.post_file, aj._call
            def kp(path, files, data=None, _a=asil_p):
                if nokta == "post":
                    raise SystemExit("HATA: baglanti koptu")
                return _a(path, files, data)
            def kc(method, path, *a, _a=asil_c, **k):
                if nokta == "delete" and method == "DELETE":
                    say_j["n"] += 1
                    if say_j["n"] == 2:
                        raise SystemExit("HATA: baglanti koptu")
                return _a(method, path, *a, **k)
            aj.post_file, aj._call = kp, kc
            bekle_dur(lambda: g.sira(aj, "39729443", o, "CANCER_LIBRA", Y), "koptu")
            aj.post_file, aj._call = asil_p, asil_c
            R = g.sira(aj, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), (ad, R["kontrol"])
        # K: devamda eski 9'un rank'i elle degismis -> yazmadan DUR
        o = Path(t, "k1"); o.mkdir(); D = eski_durum(o); ak = sira_api(D); asil_k = ak.post_file
        ak.post_file = lambda path, files, data=None: (_ for _ in ()).throw(SystemExit("HATA: baglanti koptu"))
        bekle_dur(lambda: g.sira(ak, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        ak.post_file = asil_k; next(x for x in ak.ims if x["listing_image_id"] == 60009)["rank"] = 13; n0 = len(ak.kayit)
        bekle_dur(lambda: g.sira(ak, "39729443", o, "CANCER_LIBRA", Y), "on kontrol")
        assert not [k for k in ak.kayit[n0:] if k["yazma"]]
        # pilot kapisi bilinen PASS: tamam + sira_v2 varken LEO_LEO yazilir
        o = Path(t, "o22"); o.mkdir(); D = eski_durum(o); D["sira_v2"] = ["CANCER_LIBRA"]; json.dump(D, open(o / "DURUM9.json", "w"))
        a22 = g.Kuru("39729443", Y2); a22.ilan(Y2["LEO_LEO"]); a22.kuru = False
        R = g.yaz(a22, "39729443", o, "LEO_LEO", Y2); assert all(R["kontrol"].values()), R["kontrol"]
    print("test_ornament_galeri9: 30/30 PASS")


if __name__ == "__main__":
    main()
