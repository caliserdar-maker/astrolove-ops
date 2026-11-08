#!/usr/bin/env python3
"""ornament_galeri9.py sahte Etsy testleri (ag yok). Sahte Etsy olcumle kurulu (6 Kas ESIT: ayni rank'a yukleme kaydirmaz; 30 Eyl: silme
rank sikistirmaz); kaydirmali mod da denenir. Bilinen PASS: tam akis (iki mod). Bilinen FAIL: yedek disi gorsel / video silme, bilinmeyen
gorsel, baslik farki, baslangicta active (PATCH yok, DUR), pilot once, video 4xx (isaret geri), yarim kosudan devam, yabanci video."""
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
        o = Path(t, "o7"); o.mkdir(); a7 = g.Kuru("39729443", Y2); a7.ilan(Y2["LEO_LEO"]); medya_kur(t + "/img", "LEO_LEO")
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
    print("test_ornament_galeri9: 9/9 PASS")


if __name__ == "__main__":
    main()
