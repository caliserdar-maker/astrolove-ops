#!/usr/bin/env python3
"""ornament_galeri9.py sahte Etsy testleri (ag yok). Sahte Etsy olcumle kurulu (6 Kas ESIT: ayni rank'a yukleme kaydirmaz; silme: 30 Eyl
olcumu rank kapatmaz, 8 Kas olcumu 42461185221 kapatti -> iki mod da denenir); kaydirmali mod da denenir. Bilinen PASS: tam akis (iki mod). Bilinen FAIL: yedek disi gorsel / video silme, bilinmeyen
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
        # gecici kapi (8 Kas): gercek yaz() YAZ_ACIK=1 olmadan DUR; asagidaki kuru-disi testler kapiyi acarak mantigi dener
        a0 = g.Kuru("39729443", Y := yedek()); a0.ilan(Y["CANCER_LIBRA"]); a0.kuru = False; o0 = Path(t, "o0"); o0.mkdir()
        bekle_dur(lambda: g.yaz(a0, "39729443", o0, "CANCER_LIBRA", Y), "duzeltilmeden kapali")
        os.environ["YAZ_ACIK"] = "1"
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
            a = g.Kuru("39729443", Y); a.sikistir = False          # sira modu (8 Kas kapandi) yalniz sikistirmasiz Etsy'de dogruydu; mantik testi
            a.ilan_sira(Y["CANCER_LIBRA"], D["ciftler"]["CANCER_LIBRA"], "CANCER_LIBRA"); return a
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
        # yeniden (8 Kas "Kodla yeniden yaz"): sira FAIL sonrasi karisik galeri -> yaz yolu; Etsy silmede sikistirsa da sikistirmasa da PASS
        def yeni_durum(o):
            D = eski_durum(o); D["ciftler"]["CANCER_LIBRA"]["sira2"] = {"basladi": True, "yeni": {str(n): 70000 + n for n in g.SIRA_DEG}}
            json.dump(D, open(Path(o) / "DURUM9.json", "w")); return D
        def yeni_api(D, sik):
            a = g.Kuru("39729443", Y); a.sikistir = sik; a.ilan_yeniden(Y["CANCER_LIBRA"], D["ciftler"]["CANCER_LIBRA"], "CANCER_LIBRA"); return a
        for sik in (True,):                       # 8 Kas olcumu (iki gercek kosu): silme kalanlari 1..N yeniden numaralar
            o = Path(t, f"y{sik}"); o.mkdir(); D = yeni_durum(o); ay = yeni_api(D, sik)
            R = g.yeniden(ay, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), (sik, R["kontrol"])
            assert not [k for k in ay.kayit if "/videos" in k["url"] and k["method"] != "GET"]
            D2 = json.load(open(o / "DURUM9.json")); assert "CANCER_LIBRA" in D2["sira_v2"] and "sira2" not in D2["ciftler"]["CANCER_LIBRA"]
            assert "atlandi" in g.yeniden(ay, "39729443", o, "CANCER_LIBRA", Y)
        # yeniden devam: 7. yuklemede kopma, devam PASS (sikistirmali)
        o = Path(t, "yk"); o.mkdir(); D = yeni_durum(o); ayk = yeni_api(D, True); asil_y = ayk.post_file; say_y = {"n": 0}
        def kopy(path, files, data=None):
            say_y["n"] += 1
            if say_y["n"] == 7:
                raise SystemExit("HATA: baglanti koptu")
            return asil_y(path, files, data)
        ayk.post_file = kopy
        bekle_dur(lambda: g.yeniden(ayk, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        ayk.post_file = asil_y
        R = g.yeniden(ayk, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        # yeniden on kontrol: beklenmeyen gorsel / ters bag -> yazmadan DUR; yalniz CANCER_LIBRA; video yazimi yasak
        for ad, boz in (("yb1", lambda a: a.ims.append(dict(listing_image_id=1, rank=15, alt_text="", full_width=1, full_height=1))),
                        ("yb2", lambda a: a.vis.__setitem__(0, dict(a.vis[0], image_id=a.vis[1]["image_id"])))):
            o = Path(t, ad); o.mkdir(); D = yeni_durum(o); ab = yeni_api(D, True); boz(ab)
            bekle_dur(lambda: g.yeniden(ab, "39729443", o, "CANCER_LIBRA", Y), "on kontrol")
            assert not [k for k in ab.kayit if k["yazma"]], ad
        bekle_dur(lambda: g.yeniden(ab, "39729443", Path(t, "yb1"), "LEO_LEO", Y2), "yalniz CANCER_LIBRA")
        ab.lid = 4611501158; ab.video_yasak = True
        bekle_dur(lambda: ab._izin("POST", "/shops/39729443/listings/4611501158/videos"), "yeniden modu")
        # inceleme: eski stil gorsellerinin silinmesinde (bagli 5'ten 2.) kopma -> devam PASS, iki silme davranisinda (yaz ve yeniden)
        for sik in (True,):
            def kop_sil(a):
                asil = a._call; say = {"n": 0}; bagli = {v["image_id"] for v in a.vis}
                def kc(method, path, *x, **k):
                    if method == "DELETE" and "/images/" in path and int(path.rsplit("/", 1)[1]) in bagli:
                        say["n"] += 1
                        if say["n"] == 2:
                            raise SystemExit("HATA: baglanti koptu")
                    return asil(method, path, *x, **k)
                a._call = kc; return asil
            o = Path(t, f"ka{sik}"); o.mkdir(); D = yeni_durum(o); aa = yeni_api(D, sik); asil_a = kop_sil(aa)
            bekle_dur(lambda: g.yeniden(aa, "39729443", o, "CANCER_LIBRA", Y), "koptu")
            aa._call = asil_a
            R = g.yeniden(aa, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), ("yeniden devam", sik, R["kontrol"])
            o = Path(t, f"kb{sik}"); o.mkdir(); ab2 = g.Kuru("39729443", Y); ab2.ilan(Y["CANCER_LIBRA"]); ab2.sikistir = sik; asil_b = kop_sil(ab2)
            bekle_dur(lambda: g.yaz(ab2, "39729443", o, "CANCER_LIBRA", Y), "koptu")
            ab2._call = asil_b
            R = g.yaz(ab2, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), ("yaz devam", sik, R["kontrol"])
        # inceleme C: devamda kayitli yeni gorsel galeriden silinmis -> yazmadan DUR
        o = Path(t, "kc"); o.mkdir(); D = yeni_durum(o); ac = yeni_api(D, True); asil_c2 = ac.post_file; say_c = {"n": 0}
        def kopc(path, files, data=None):
            say_c["n"] += 1
            if say_c["n"] == 5:
                raise SystemExit("HATA: baglanti koptu")
            return asil_c2(path, files, data)
        ac.post_file = kopc
        bekle_dur(lambda: g.yeniden(ac, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        ac.post_file = asil_c2
        y2 = int(json.load(open(o / "DURUM9.json"))["ciftler"]["CANCER_LIBRA"]["yeniden"]["yeni"]["2"])
        ac.ims = [x for x in ac.ims if x["listing_image_id"] != y2]; n0 = len(ac.kayit)
        bekle_dur(lambda: g.yeniden(ac, "39729443", o, "CANCER_LIBRA", Y), "on kontrol")
        assert not [k for k in ac.kayit[n0:] if k["yazma"]]
        # sira kapisi bilinen FAIL (inceleme): Etsy her yuklemeyi rank 1'e koyarsa (ters sira) yaz ve yeniden "sirali degil" DUR, Style POST yok
        def ters_yukle(a):
            asil = a.post_file
            def p1(path, files, data=None):
                return asil(path, files, dict(data, rank="1") if path.endswith("/images") else data)
            a.post_file = p1
        o = Path(t, "ts1"); o.mkdir(); at = g.Kuru("39729443", Y); at.ilan(Y["CANCER_LIBRA"]); ters_yukle(at)
        bekle_dur(lambda: g.yaz(at, "39729443", o, "CANCER_LIBRA", Y), "sirali degil")
        assert not [k for k in at.kayit if k["url"].endswith("variation-images") and k["method"] != "GET"]
        o = Path(t, "ts2"); o.mkdir(); D = yeni_durum(o); at2 = yeni_api(D, True); ters_yukle(at2)
        bekle_dur(lambda: g.yeniden(at2, "39729443", o, "CANCER_LIBRA", Y), "sirali degil")
        assert not [k for k in at2.kayit if k["url"].endswith("variation-images") and k["method"] != "GET"]
        # onceki yeniden denemesi bitmis ama 4-5 yer degismis (42462674399) -> yeni deneme taban = onun 14'u, PASS, gecmis kaydi
        o = Path(t, "yg"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [990001], "yeni": {str(n): 80000 + n for n in range(1, 15)}}
        json.dump(D, open(o / "DURUM9.json", "w")); ag = yeni_api(D, True)
        assert sorted(x["rank"] for x in ag.ims) == list(range(1, 15)) and ag.ims[3]["rank"] == 5
        R = g.yeniden(ag, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        D2 = json.load(open(o / "DURUM9.json")); assert len(D2["ciftler"]["CANCER_LIBRA"]["yeniden_gecmis"]) == 1 and "CANCER_LIBRA" in D2["sira_v2"]
        sil = {int(k["url"].rsplit("/", 1)[1]) for k in ag.kayit if k["method"] == "DELETE"}
        assert sil == {80000 + n for n in range(1, 15)}, sil
        # inceleme T1: onceki deneme bitmis ve SIRA DOGRU -> yeni deneme yok, yazma yok (devam yolu yalniz geri okur)
        o = Path(t, "yt1"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [990001], "yeni": {str(n): 80000 + n for n in range(1, 15)},
                                                   "taban": {"ids": sorted([60001] + [60000 + n for n in range(7, 15)] + [70000 + n for n in g.SIRA_DEG]),
                                                             "bagli": {s_: 60000 + r for s_, r in g.STIL_SIRA.items()}}}
        json.dump(D, open(o / "DURUM9.json", "w")); at1 = yeni_api(D, True)
        for x in at1.ims:
            x["rank"] = x["listing_image_id"] - 80000
        R = g.yeniden(at1, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        assert not [k for k in at1.kayit if k["yazma"]], "sira dogruyken yazim olmamali"
        # inceleme T2: (a) sonrasi video degismis -> yazmadan DUR
        o = Path(t, "yt2"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [555], "yeni": {str(n): 80000 + n for n in range(1, 15)}}
        json.dump(D, open(o / "DURUM9.json", "w")); at2 = yeni_api(D, True)
        at2.vids = [dict(video_id=990001, video_state="active")]          # kayitli taban videosu 555, galeride baska video
        bekle_dur(lambda: g.yeniden(at2, "39729443", o, "CANCER_LIBRA", Y), "video 1")
        assert not [k for k in at2.kayit if k["yazma"]]
        # inceleme T3: (a) sonrasi on kontrol FAIL, sonraki kosuda taban ezilmez (video geri gelince PASS)
        at2.vids = [dict(video_id=555, video_state="active")]
        R = g.yeniden(at2, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        # inceleme V1: onceki bitmis denemede video anahtari yok -> taban videosu su anki video, PASS
        o = Path(t, "yv1"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "yeni": {str(n): 80000 + n for n in range(1, 15)}}
        json.dump(D, open(o / "DURUM9.json", "w")); av1 = yeni_api(D, True)
        R = g.yeniden(av1, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        # 42463597152 durumu: yarim deneme (taban + 13 yeni) -> devam 1 yukleme, PASS; rank hep <= 20
        o = Path(t, "yy13"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [990001],
            "taban": {"ids": sorted([90000 + n for n in range(1, 15)]), "bagli": {s_: 90000 + r for s_, r in g.STIL_SIRA.items()}},
            "yeni": {str(n): 91000 + n for n in range(1, 14)}}
        json.dump(D, open(o / "DURUM9.json", "w")); a13y = yeni_api(D, True)
        R = g.yeniden(a13y, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        yk = [k for k in a13y.kayit if k.get("dosya")]
        assert len(yk) == 1 and int(yk[0]["form"]["rank"]) == 19, yk
        # olcum: gercek durum (eski 5 bagli rank 1-5, yeni 1-13 rank 8-20, yeni 14 rank 19) -> B, C, D (E yok)
        o = Path(t, "olc"); o.mkdir(); D = yeni_durum(o)
        D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [990001],
            "taban": {"ids": [], "bagli": {s_: 90000 + r for s_, r in g.STIL_SIRA.items()}}, "yeni": {str(n): 91000 + n for n in range(1, 15)}}
        json.dump(D, open(o / "DURUM9.json", "w"))
        ao = g.Kuru("39729443", Y); ao.ilan(Y["CANCER_LIBRA"]); ao.sikistir = False
        a_o = dict(zip(g.GALERI, g.alt_metinler("CANCER_LIBRA")[0]))
        ao.ims = [dict(listing_image_id=90000 + r, rank=k, alt_text="e", full_width=3000, full_height=2250) for k, r in enumerate(g.STIL_SIRA.values(), 1)]
        ao.ims += [dict(listing_image_id=91000 + n, rank=7 + n if n < 14 else 19, alt_text=a_o[g.GALERI[n - 1]], full_width=3000, full_height=2250) for n in range(1, 15)]
        ao.vids = [dict(video_id=990001, video_state="active")]
        ao.vis = [dict(property_id=g.P_STYLE, value_id=Y["CANCER_LIBRA"]["stil"][s_], image_id=90000 + r) for s_, r in g.STIL_SIRA.items()]
        asil_sim = ao._sim
        def sim_norm(m, p, js):                    # silme sonrasi Etsy'nin 1..N normallestirdigi varsayimi (olcumun amaci bunu gormek)
            r = asil_sim(m, p, js)
            if m == "DELETE" and "/images/" in p:
                for k, x in enumerate(sorted(ao.ims, key=lambda x: (x["rank"], x["listing_image_id"])), 1):
                    x["rank"] = k
            return r
        ao._sim = sim_norm
        R = g.olcum(ao, "39729443", o, "CANCER_LIBRA", Y)
        O = json.load(open(o / "O9_CANCER_LIBRA.json")); assert "A baslangic" in O["okuma"] and "D 15 sn sonra" in O["okuma"]
        assert not [k for k in ao.kayit if "/videos" in k["url"] and k["method"] != "GET"]
        yaz_ = [k for k in ao.kayit if k["yazma"]]
        assert len([k for k in yaz_ if k["method"] == "DELETE"]) == 5 and not [k for k in yaz_ if k.get("dosya")], "yalniz B ve C"
        assert {int(k["url"].rsplit("/", 1)[1]) for k in yaz_ if k["method"] == "DELETE"} == {90000 + r for r in g.STIL_SIRA.values()}
        assert {x["image_id"] for x in ao.vis} == {91000 + r for r in g.STIL_SIRA.values()}
        D3 = json.load(open(o / "DURUM9.json"))["ciftler"]["CANCER_LIBRA"]["yeniden"]
        assert D3["olcum"]["bc"] and sorted(D3["taban"]["ids"]) == [91000 + n for n in range(1, 15)]
        n0 = len(ao.kayit); g.olcum(ao, "39729443", o, "CANCER_LIBRA", Y); assert not [k for k in ao.kayit[n0:] if k["yazma"]]   # tekrar: atlar
        # olcum: B sonrasi active -> acil inactive + DUR
        o = Path(t, "olc2"); o.mkdir(); json.dump(D, open(o / "DURUM9.json", "w"))
        ao2 = g.Kuru("39729443", Y); ao2.ilan(Y["CANCER_LIBRA"]); ao2.ims = [dict(x) for x in ao.ims]; ao2.vids = list(ao.vids)
        ao2.ims = [dict(listing_image_id=90000 + r, rank=k, alt_text="e", full_width=3000, full_height=2250) for k, r in enumerate(g.STIL_SIRA.values(), 1)] + \
                  [dict(listing_image_id=91000 + n, rank=7 + n, alt_text="x", full_width=3000, full_height=2250) for n in range(1, 15)]
        ao2.vis = [dict(property_id=g.P_STYLE, value_id=Y["CANCER_LIBRA"]["stil"][s_], image_id=90000 + r) for s_, r in g.STIL_SIRA.items()]
        asil_pj = ao2.post_json
        def pj(path, js):
            r = asil_pj(path, js); ao2.L["state"] = "active"; return r
        ao2.post_json = pj
        try:
            g.olcum(ao2, "39729443", o, "CANCER_LIBRA", Y); raise AssertionError("DUR bekleniyordu")
        except SystemExit as e:
            assert e.code == 2, e.code
        assert ao2.L["state"] == "inactive" and not [k for k in ao2.kayit if k["method"] == "DELETE"]
        bekle_dur(lambda: g.olcum(ao, "39729443", o, "LEO_LEO", Y2), "yalniz CANCER_LIBRA")
        # tasi (Serdar 8 Kas "Evet, bu yontemle"): olcum sonrasi gercek sira [1..11, 14, 12, 13] -> plan [14]; gecikmeli ve aninda kapatmada PASS
        g.DUZGUN_BEKLE_SN = 0
        def tasi_durum(o, sira):
            D = yeni_durum(o); yz = {str(n): 92000 + n for n in range(1, 15)}
            D["ciftler"]["CANCER_LIBRA"]["yeniden"] = {"basladi": True, "video": [990001], "yeni": yz,
                "olcum": {"bc": True, "D": [[k, 92000 + n] for k, n in enumerate(sira, 1)]}}
            json.dump(D, open(Path(o) / "DURUM9.json", "w")); return D
        def tasi_api(D, gec):
            a = g.Kuru("39729443", Y); a.ilan(Y["CANCER_LIBRA"]); a.sikistir = not gec; a.gecikme = 2 if gec else 0
            al = dict(zip(g.GALERI, g.alt_metinler("CANCER_LIBRA")[0]))
            a.ims = [dict(listing_image_id=i, rank=r, alt_text=al[g.GALERI[i - 92001]], full_width=3000, full_height=2250)
                     for r, i in D["ciftler"]["CANCER_LIBRA"]["yeniden"]["olcum"]["D"]]
            a.vids = [dict(video_id=990001, video_state="active")]
            a.vis = [dict(property_id=g.P_STYLE, value_id=Y["CANCER_LIBRA"]["stil"][s_], image_id=92000 + r) for s_, r in g.STIL_SIRA.items()]
            return a
        gercek = list(range(1, 12)) + [14, 12, 13]
        for gec in (True, False):
            o = Path(t, f"ts{gec}"); o.mkdir(); D = tasi_durum(o, gercek); at_ = tasi_api(D, gec)
            R = g.tasi(at_, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), (gec, R["kontrol"])
            assert R["plan"] == [14], R["plan"]
            assert len([k for k in at_.kayit if k.get("dosya")]) == 1 and len([k for k in at_.kayit if k["method"] == "DELETE"]) == 1
            assert not [k for k in at_.kayit if "/videos" in k["url"] and k["method"] != "GET"]
            assert "CANCER_LIBRA" in json.load(open(o / "DURUM9.json"))["sira_v2"]
        # birden cok yanlis: [1..10, 13, 11, 12, 14] -> plan [11, 12, 13, 14] degil en kucuk: [11..14]? (yerinde kalan hedefin basi) PASS
        o = Path(t, "ts_cok"); o.mkdir(); D = tasi_durum(o, list(range(1, 11)) + [13, 11, 12, 14]); at2_ = tasi_api(D, True)
        R = g.tasi(at2_, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        assert R["plan"] == [13, 14], R["plan"]
        # devam: yuklemeden sonra kopma (id kayitli) -> devam bag + silme, PASS
        o = Path(t, "ts_dev"); o.mkdir(); D = tasi_durum(o, gercek); at3 = tasi_api(D, True); asil_t = at3.post_json
        at3.post_json = lambda path, js: (_ for _ in ()).throw(SystemExit("HATA: baglanti koptu"))
        bekle_dur(lambda: g.tasi(at3, "39729443", o, "CANCER_LIBRA", Y), "koptu")
        at3.post_json = asil_t; n0 = len([k for k in at3.kayit if k.get("dosya")])
        R = g.tasi(at3, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        assert len([k for k in at3.kayit if k.get("dosya")]) == n0 == 1, "ikinci yukleme olmamali"
        # on kontrol: bilinmeyen gorsel -> yazmadan DUR; rank'lar hic duzelmezse yuklemeden DUR; yalniz CANCER_LIBRA
        o = Path(t, "ts_bil"); o.mkdir(); D = tasi_durum(o, gercek); at4 = tasi_api(D, True)
        at4.ims.append(dict(listing_image_id=5, rank=15, alt_text="", full_width=1, full_height=1))
        bekle_dur(lambda: g.tasi(at4, "39729443", o, "CANCER_LIBRA", Y), "on kontrol"); assert not [k for k in at4.kayit if k["yazma"]]
        o = Path(t, "ts_bek"); o.mkdir(); D = tasi_durum(o, gercek); at5 = tasi_api(D, True)
        for x in at5.ims:
            x["rank"] += 3
        bekle_dur(lambda: g.tasi(at5, "39729443", o, "CANCER_LIBRA", Y), "1..14 olmadi"); assert not [k for k in at5.kayit if k["yazma"]]
        bekle_dur(lambda: g.tasi(at5, "39729443", o, "LEO_LEO", Y2), "yalniz CANCER_LIBRA")
        g.DUZGUN_BEKLE_SN = 5
        # bilinen FAIL: Etsy silmede yeniden numaralamazsa son rank'lar 1-14 olmaz -> geri okuma DUR (kapak 1. degil); yeniden de ayni
        o = Path(t, "ynos"); o.mkdir(); a_n = g.Kuru("39729443", Y); a_n.ilan(Y["CANCER_LIBRA"]); a_n.sikistir = False
        bekle_dur(lambda: g.yaz(a_n, "39729443", o, "CANCER_LIBRA", Y), "rank 1-14")
        o = Path(t, "ynos2"); o.mkdir(); D = yeni_durum(o); a_n2 = yeni_api(D, False)
        bekle_dur(lambda: g.yeniden(a_n2, "39729443", o, "CANCER_LIBRA", Y), "rank 1-14")
        # sona ekleme: yuklemeler esit rank'a gitmez (her POST rank'i o anki en buyuk rank + 1)
        o = Path(t, "yeks"); o.mkdir(); a_e = g.Kuru("39729443", Y); a_e.ilan(Y["CANCER_LIBRA"]); onc = {}
        asil_e = a_e.post_file
        def eks(path, files, data=None):
            if path.endswith("/images"):
                assert int(data["rank"]) == len(a_e.ims) + 1 <= 20, (data["rank"], len(a_e.ims))
            return asil_e(path, files, data)
        a_e.post_file = eks
        R = g.yaz(a_e, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), R["kontrol"]
        # 77 ilanin yaz() yolu Etsy silmede sikistirsa da PASS
        o = Path(t, "ysik"); o.mkdir(); a_s = g.Kuru("39729443", Y); a_s.ilan(Y["CANCER_LIBRA"]); a_s.sikistir = True
        R = g.yaz(a_s, "39729443", o, "CANCER_LIBRA", Y); assert all(R["kontrol"].values()), ("yaz sikistir", R["kontrol"])
        # pilot kapisi bilinen PASS: tamam + sira_v2 varken LEO_LEO yazilir
        o = Path(t, "o22"); o.mkdir(); D = eski_durum(o); D["sira_v2"] = ["CANCER_LIBRA"]; json.dump(D, open(o / "DURUM9.json", "w"))
        a22 = g.Kuru("39729443", Y2); a22.ilan(Y2["LEO_LEO"]); a22.kuru = False
        R = g.yaz(a22, "39729443", o, "LEO_LEO", Y2); assert all(R["kontrol"].values()), R["kontrol"]
    print("test_ornament_galeri9: 60/60 PASS")


if __name__ == "__main__":
    main()
