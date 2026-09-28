#!/usr/bin/env python3
"""video_yukle_78 apply yerel testi - sahte Etsy, 4 ilan, 60 sn alti. Senaryolar:
temiz apply (4 YUKLENDI, ilanda yalniz yeni video); kota ilan basinda yetmez -> o ve kalan ATLANDI, yarim ilan yok;
canli video plandan farkli / sha farkli / yedek yok -> ATLANDI yazma yok; yukleme geri okuma FAIL -> eski SILINMEZ,
DURUR; onay dizesi yanlis -> DUR; updateListing (PATCH/PUT) hic cagrilmaz."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_yukle_78 as V  # noqa: E402

V.OKUMA_BEKLE = 0
os.environ["ETSY_SHOP_ID"] = "39729443"
TMP = Path(tempfile.mkdtemp())
IDS = [("111", "ARIES_LEO"), ("222", "CANCER_LIBRA"), ("333", "PISCES_VIRGO"), ("444", "LEO_LEO")]


class Fake:
    def __init__(self, kota=5000, dus=1, hayalet=False):
        self.remaining, self.dus, self.hayalet = str(kota), dus, hayalet  # hayalet: yuklenen video listede gorunmez
        self.nid, self.yaz = 9000, []
        self.L = {lid: {"state": "active", "vids": [int(lid) * 10]} for lid, _ in IDS}

    def _k(self):
        self.remaining = str(int(self.remaining) - self.dus)

    def get(self, path, params=None, ok404=False):
        self._k()
        if path.startswith("/shops/"):
            return {"shop_id": 1}
        lid = path.split("/listings/")[1].split("/")[0]
        if path.endswith("/videos"):
            return {"results": [{"video_id": v, "video_state": "active", "video_url": "x"} for v in self.L[lid]["vids"]]}
        return {"listing_id": int(lid), "state": self.L[lid]["state"]}

    def post_file(self, path, files, data=None):
        self._k()
        lid = path.split("/listings/")[1].split("/")[0]
        self.nid += 1
        self.yaz.append(("POST", lid, data["name"]))
        if not self.hayalet:
            self.L[lid]["vids"].append(self.nid)
        return {"video_id": self.nid}

    def delete(self, path):
        self._k()
        lid, vid = path.split("/listings/")[1].split("/videos/")
        self.yaz.append(("DELETE", lid, vid))
        self.L[lid]["vids"].remove(int(vid))

    def patch(self, *a, **k):
        raise AssertionError("updateListing cagrildi")
    put = patch


def hazirla():
    vd = TMP / "video"
    vd.mkdir(exist_ok=True)
    rows = []
    for lid, c in IDS:
        p = vd / f"VIDEO_{c}.mp4"
        p.write_bytes(os.urandom(20000))
        rows.append({"listing_id": lid, "cift": c, "state": "active", "durum": "DEGISTIR", "neden": "",
                     "video": {"dosya": p.name, "sha256": V.sha(p)},
                     "eski_video": [{"video_id": int(lid) * 10, "yedek": f"{lid}_{int(lid) * 10}.mp4"}]})
    (TMP / "PLAN.json").write_text(json.dumps({"olusturma": "t", "kaynak": {"klasor": "K"}, "satirlar": rows}))
    (TMP / "yedek.txt").write_text("\n".join(f"{lid}_{int(lid) * 10}.mp4" for lid, _ in IDS))
    return vd


def kos(api, ad, **kw):
    out = TMP / ad
    out.mkdir()
    a = SimpleNamespace(video_dir=str(TMP / "video"), yedek_liste=str(TMP / "yedek.txt"), quota_min=60, haric=[],
                        plan=str(TMP / "PLAN.json"), kaynak={"plan": "KURU_T/PLAN.json"})
    a.__dict__.update(kw)
    son, ok = V.apply(a, api, out, json.loads((TMP / "PLAN.json").read_text()))
    return {x["cift"]: x for x in son}, ok, (out / "report.md").read_text()


def main():
    vd = hazirla()
    hata = []

    def bak(ad, kosul):
        print(("PASS " if kosul else "FAIL ") + ad)
        kosul or hata.append(ad)

    # 1 temiz
    f = Fake()
    s, ok, rep = kos(f, "temiz")
    bak("temiz: 4 YUKLENDI + ok", ok and all(x["sonuc"] == "YUKLENDI" for x in s.values()))
    bak("temiz: ilanda yalniz yeni video", all(f.L[l]["vids"] == [int(s[c]["yeni_video"])] for l, c in IDS))
    bak("temiz: rapor sayilari", "YUKLENDI 4 | ATLANDI 0 | FAIL 0" in rep)
    bak("temiz: yukleme adi VIDEO_<CIFT>.mp4", [y[2] for y in f.yaz if y[0] == "POST"] == [f"VIDEO_{c}.mp4" for _, c in IDS])
    # 2 kota: esik = ust + 60; 2 ilanlik kota birak
    esik = V.ILAN_CAGRI_UST + 60
    f = Fake(kota=esik + 17)  # sahte ilan ~6 cagri; birkac ilan sonra ilan basinda esik alti
    s, ok, rep = kos(f, "kota")
    durum = [s[c]["sonuc"] for _, c in IDS]
    bak(f"kota: yetmeyince ATLANDI, yarim yok ({durum})",
        not ok and durum[0] == "YUKLENDI" and "ATLANDI" in durum and "FAIL" not in durum
        and all(d == "ATLANDI" for d in durum[durum.index("ATLANDI"):]))
    yari = [l for l, c in IDS if s[c]["sonuc"] == "ATLANDI" and any(y[1] == l for y in f.yaz)]
    bak("kota: ATLANDI ilana hic yazilmadi", not yari)
    bak("kota: ATLANDI ilanlarda eski video duruyor",
        all(f.L[l]["vids"] == [int(l) * 10] for l, c in IDS if s[c]["sonuc"] == "ATLANDI"))
    # 3 plan-canli uyusmazligi / sha / yedek
    f = Fake()
    f.L["111"]["vids"] = [5]
    (vd / "VIDEO_CANCER_LIBRA.mp4").write_bytes(os.urandom(20000))
    (TMP / "yedek.txt").write_text("333_3330.mp4\n444_4440.mp4")
    s, ok, rep = kos(f, "uyusmaz")
    bak("uyusmaz: 111 canli farkli, 222 sha farkli -> ATLANDI; 333/444 yedekli -> YUKLENDI",
        [s[c]["sonuc"] for _, c in IDS] == ["ATLANDI", "ATLANDI", "YUKLENDI", "YUKLENDI"])
    bak("uyusmaz: 111/222'ye yazma yok", not any(y[1] in ("111", "222") for y in f.yaz))
    hazirla()
    # 4 geri okuma FAIL -> eski silinmez, durur
    f = Fake(hayalet=True)
    s, ok, rep = kos(f, "hayalet")
    bak("hayalet: 1. FAIL, kalan ATLANDI", [s[c]["sonuc"] for _, c in IDS] == ["FAIL", "ATLANDI", "ATLANDI", "ATLANDI"])
    bak("hayalet: DELETE yok", not any(y[0] == "DELETE" for y in f.yaz))
    # 5 onay dizesi
    r = subprocess.run([sys.executable, V.__file__, "--video-dir", str(vd), "--out", str(TMP / "o5"), "--plan",
                        str(TMP / "PLAN.json"), "--apply", "--confirm", "EVET"], capture_output=True, text=True,
                       env={**os.environ, "TOKEN_FILE": "/yok", "ETSY_API_KEY": "", "ETSY_SHARED_SECRET": ""})
    bak("onay dizesi yanlis -> DUR", r.returncode != 0 and "VIDEO78_YUKLE" in r.stderr)
    print("SELFTEST", "PASS" if not hata else f"FAIL {hata}")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
