#!/usr/bin/env python3
"""video_yukle_78 --surum v7 yerel testi (Merkez 26 Eki) - sahte Etsy, 4 ilan, 60 sn alti. Senaryolar:
normal (DEGISTIR: yukle -> geri oku -> eski sil -> geri oku), videosuz ilan (yalniz yukle), yukleme sonrasi hata (ikinci
yukleme YOK; ilanda tek yeni video -> kabul, yeni yok -> FAIL ve eski SILINMEZ), eski silme hatasi (FAIL, ilan videosuz
kalmaz, durur), galeri v10 degil (kuru BLOK: ILERLEME PASS degil / canli kapak farkli; apply kapak degisti -> ATLANDI),
kota kapisi (ilan basi ust + taban), BLOK satirli v7 plan, v5/v7 plan surumu karismaz. updateListing hic cagrilmaz.
Inceleme (26 Eki) ekleri: yeni video active olmadan eski SILINMEZ; DELETE 404 (ilk istek islenmis) YUKLENDI; galeri kumesi /
set eksik BLOK; kuru yalniz galeri BLOK'unda PASS, baska BLOK FAIL; yazilacak satiri olmayan apply FAIL; SONUC.json her ilanda.
Kuru kosu gercek 1440x1080 6 sn mp4 ile (ffmpeg) olcer; ffmpeg yoksa video_bilgi sahtelenir."""
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_yukle_78 as V  # noqa: E402

V.OKUMA_BEKLE = V.OKUMA_BEKLE_V7 = 0
os.environ["ETSY_SHOP_ID"] = "39729443"
TMP = Path(tempfile.mkdtemp())
IDS = [("111", "ARIES_LEO"), ("222", "CANCER_LIBRA"), ("333", "PISCES_VIRGO"), ("444", "LEO_LEO")]
KAPAK = {lid: int(lid) * 100 for lid, _ in IDS}   # galeri v10 kapak kimligi (ILERLEME son_ids[0])


class Fake:
    """hata: {lid: 'post_sonra' (yukler, sonra hata) | 'post_once' (yuklemez, hata) | 'post_bos' (yukler, kimliksiz yanit)
    | 'sil' | 'sil404' (ilk istek islenmis, yanit 404) | 'islenmez' (yeni video hep inactive)}"""

    def __init__(self, kota=5000, hata=None, vids=None):
        self.remaining, self.hata = str(kota), hata or {}
        self.nid, self.yaz, self.tekrar = 9000, [], []
        self.L = {lid: {"state": "active", "vids": list((vids or {}).get(lid, [int(lid) * 10])),
                        "imgs": [KAPAK[lid], KAPAK[lid] + 1]} for lid, _ in IDS}

    def _k(self):
        self.remaining = str(int(self.remaining) - 1)

    def get(self, path, params=None, ok404=False):
        self._k()
        if path.startswith("/shops/"):
            return {"shop_id": 1}
        lid = path.split("/listings/")[1].split("/")[0]
        if path.endswith("/videos"):
            pasif = self.hata.get(lid) == "islenmez"
            return {"results": [{"video_id": v, "video_state": "inactive" if pasif and v > 9000 else "active",
                                 "video_url": f"https://v/{v}.mp4"} for v in self.L[lid]["vids"]]}
        if path.endswith("/images"):
            return {"results": [{"listing_image_id": x, "rank": i + 1} for i, x in enumerate(self.L[lid]["imgs"])][::-1]}
        return {"listing_id": int(lid), "state": self.L[lid]["state"]}

    def post_file(self, path, files, data=None, tekrar=3):
        self._k()
        lid = path.split("/listings/")[1].split("/")[0]
        self.yaz.append(("POST", lid, data["name"]))
        self.tekrar.append(tekrar)
        h = self.hata.get(lid)
        if h == "post_once":
            raise SystemExit(f"HATA: POST(file) {path} -> 500: x")
        self.nid += 1
        self.L[lid]["vids"].append(self.nid)
        if h == "post_sonra":
            raise TimeoutError("read timeout")
        return {} if h == "post_bos" else {"video_id": self.nid}

    def delete(self, path, ok404=False):
        self._k()
        lid, vid = path.split("/listings/")[1].split("/videos/")
        self.yaz.append(("DELETE", lid, vid, ok404))
        if self.hata.get(lid) == "sil":
            raise SystemExit(f"HATA: DELETE {path} -> 500: x")
        self.L[lid]["vids"].remove(int(vid))
        if self.hata.get(lid) == "sil404":   # 5xx sonrasi yeniden deneme: ilk istek islenmis, ikinci 404
            if not ok404:
                raise SystemExit(f"HATA: DELETE {path} -> 404: x")
            return None

    def patch(self, *a, **k):
        raise AssertionError("updateListing cagrildi")
    put = patch


def galeri(durum="PASS", farkli=()):
    return {lid: {"cift": c, "set": 9, "hedef": 9, "durum": durum, "son_ids": [KAPAK[lid] + (7 if lid in farkli else 0), KAPAK[lid] + 1]}
            for lid, c in IDS}


def hazirla(vids=None):
    vd = TMP / "video"
    vd.mkdir(exist_ok=True)
    rows = []
    for lid, c in IDS:
        p = vd / f"{c}.mp4"
        p.write_bytes(os.urandom(20000))
        ev = list((vids or {}).get(lid, [int(lid) * 10]))
        rows.append({"listing_id": lid, "cift": c, "state": "active", "durum": "DEGISTIR" if ev else "YUKLE", "neden": "",
                     "video": {"dosya": p.name, "sha256": V.sha(p)}, "kapak_id": KAPAK[lid],
                     "eski_video": [{"video_id": v, "url": f"https://v/{v}.mp4", "yedek": f"{lid}_{v}.mp4"} for v in ev]})
    (TMP / "PLAN.json").write_text(json.dumps({"olusturma": "t", "surum": "v7", "kaynak": {"klasor": "K"}, "satirlar": rows}))
    (TMP / "yedek.txt").write_text("\n".join(f"{lid}_{v}.mp4" for lid, _ in IDS for v in (vids or {}).get(lid, [int(lid) * 10])))
    return vd


def kos(api, ad, **kw):
    out = TMP / ad
    out.mkdir()
    a = SimpleNamespace(video_dir=str(TMP / "video"), yedek_liste=str(TMP / "yedek.txt"), quota_min=10, haric=[],
                        plan=str(TMP / "PLAN.json"), kaynak={"plan": "KURU_T/PLAN.json"}, surum="v7", galeri=galeri())
    a.__dict__.update(kw)
    son, ok = V.apply(a, api, out, json.loads((TMP / "PLAN.json").read_text()))
    return {x["cift"]: x for x in son}, ok, (out / "report.md").read_text()


def mp4(p):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x202030:s=1440x1080:r=30:d=6",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(p)], check=True)


def main():
    hata = []

    def bak(ad, kosul):
        print(("PASS " if kosul else "FAIL ") + ad)
        kosul or hata.append(ad)

    def sonuc(s):
        return [s[c]["sonuc"] for _, c in IDS]

    # 1 normal DEGISTIR
    hazirla()
    f = Fake()
    s, ok, rep = kos(f, "normal")
    bak("normal: 4 YUKLENDI + ok", ok and sonuc(s) == ["YUKLENDI"] * 4)
    bak("normal: ilanda yalniz yeni video", all(f.L[l]["vids"] == [int(s[c]["yeni_video"])] for l, c in IDS))
    bak("normal: sira POST -> DELETE (ilan basi), ad <CIFT>.mp4",
        [(y[0], y[1]) for y in f.yaz] == [(o, l) for l, _ in IDS for o in ("POST", "DELETE")]
        and [y[2] for y in f.yaz if y[0] == "POST"] == [f"{c}.mp4" for _, c in IDS])
    bak("normal: tek gonderim (tekrar=1)", f.tekrar == [1] * 4)
    bak("normal: rapor ust v7", f"ust {V.ILAN_CAGRI_UST_V7} + taban 10" in rep)
    # 2 videosuz ilan: yalniz yukle
    bos = {lid: [] for lid, _ in IDS}
    hazirla(bos)
    f = Fake(vids=bos)
    s, ok, rep = kos(f, "videosuz")
    bak("videosuz: 4 YUKLENDI, DELETE yok", ok and sonuc(s) == ["YUKLENDI"] * 4 and not any(y[0] == "DELETE" for y in f.yaz))
    # 3a yukleme sonrasi hata, video ilanda -> kabul, ikinci yukleme yok
    hazirla()
    f = Fake(hata={"111": "post_sonra", "222": "post_bos"})
    s, ok, rep = kos(f, "post_sonra")
    bak("post_sonra/bos: hataya ragmen tek yeni video -> YUKLENDI", ok and sonuc(s) == ["YUKLENDI"] * 4)
    bak("post_sonra/bos: ilan basi tek POST", [y[1] for y in f.yaz if y[0] == "POST"] == [l for l, _ in IDS])
    bak("post_sonra/bos: ilanda yalniz yeni video", all(len(f.L[l]["vids"]) == 1 and f.L[l]["vids"][0] > 9000 for l, _ in IDS))
    # 3b yukleme hatasi, ilanda yeni yok -> FAIL, eski SILINMEZ, ikinci yukleme yok, durur
    hazirla()
    f = Fake(hata={"222": "post_once"})
    s, ok, rep = kos(f, "post_once")
    bak("post_once: 222 FAIL, sonrakiler ATLANDI", sonuc(s) == ["YUKLENDI", "FAIL", "ATLANDI", "ATLANDI"])
    bak("post_once: 222 tek POST, DELETE yok, eski video duruyor",
        [y[0] for y in f.yaz if y[1] == "222"] == ["POST"] and f.L["222"]["vids"] == [2220])
    bak("post_once: ATLANDI ilanlara yazma yok", not any(y[1] in ("333", "444") for y in f.yaz))
    # 4 eski silme hatasi -> FAIL, ilan videosuz degil (yeni + eski), durur
    hazirla()
    f = Fake(hata={"111": "sil"})
    s, ok, rep = kos(f, "sil")
    bak("sil: FAIL + kalan ATLANDI", sonuc(s) == ["FAIL", "ATLANDI", "ATLANDI", "ATLANDI"])
    bak("sil: ilanda yeni ve eski video (videosuz degil, 2. yukleme yok)",
        len(f.L["111"]["vids"]) == 2 and 1110 in f.L["111"]["vids"] and [y[0] for y in f.yaz].count("POST") == 1)
    # 5 galeri: apply aninda kapak plandakinden farkli / ILERLEME PASS degil -> ATLANDI, yazma yok
    hazirla()
    f = Fake()
    f.L["111"]["imgs"] = [55, KAPAK["111"]]
    g = galeri()
    g["222"]["durum"] = "DUR"
    s, ok, rep = kos(f, "galeri", galeri=g)
    bak("galeri apply: 111 kapak degisti, 222 ILERLEME DUR -> ATLANDI; 333/444 YUKLENDI",
        sonuc(s) == ["ATLANDI", "ATLANDI", "YUKLENDI", "YUKLENDI"] and not any(y[1] in ("111", "222") for y in f.yaz))
    # 6 kota kapisi: ilan basinda ust + taban yoksa ilana baslanmaz
    hazirla()
    esik = V.ILAN_CAGRI_UST_V7 + 10
    f = Fake(kota=esik + 12)
    s, ok, rep = kos(f, "kota")
    d = sonuc(s)
    bak(f"kota: yetmeyince ATLANDI, yarim yok ({d})", not ok and d[0] == "YUKLENDI" and "FAIL" not in d
        and all(x == "ATLANDI" for x in d[d.index("ATLANDI"):]))
    bak("kota: ATLANDI ilanlarda eski video duruyor, yazma yok",
        all(f.L[l]["vids"] == [int(l) * 10] and not any(y[1] == l for y in f.yaz) for l, c in IDS if s[c]["sonuc"] == "ATLANDI"))
    # 6b yeni video active olmadi -> eski SILINMEZ, FAIL, durur
    hazirla()
    f = Fake(hata={"111": "islenmez"})
    s, ok, rep = kos(f, "islenmez")
    bak("islenmez: FAIL + kalan ATLANDI, DELETE yok, ilanda eski + yeni",
        sonuc(s) == ["FAIL", "ATLANDI", "ATLANDI", "ATLANDI"] and not any(y[0] == "DELETE" for y in f.yaz)
        and 1110 in f.L["111"]["vids"] and "active olmadi" in s["ARIES_LEO"]["neden"])
    # 6c DELETE 404 (ilk istek islenmis) -> ok404, son okuma [yeni] -> YUKLENDI
    hazirla()
    f = Fake(hata={"111": "sil404"})
    s, ok, rep = kos(f, "sil404")
    bak("sil404: YUKLENDI, DELETE ok404=True", ok and sonuc(s) == ["YUKLENDI"] * 4 and all(y[3] for y in f.yaz if y[0] == "DELETE"))
    bak("SONUC.json yazildi (4 kayit)", len(json.loads((TMP / "sil404" / "SONUC.json").read_text())["sonuc"]) == 4)
    # 6d galeri kumesi farkli / set eksik -> ATLANDI
    hazirla()
    f = Fake()
    f.L["333"]["imgs"] = [KAPAK["333"], 77]
    g = galeri()
    g["444"]["set"] = 8
    s, ok, rep = kos(f, "galeri_kume", galeri=g)
    bak("galeri kume: 333 galeri farkli, 444 set 8/9 -> ATLANDI", sonuc(s) == ["YUKLENDI", "YUKLENDI", "ATLANDI", "ATLANDI"]
        and "farkli" in s["PISCES_VIRGO"]["neden"] and "set 8/9" in s["LEO_LEO"]["neden"])
    # 6e yazilacak satiri olmayan v7 apply FAIL; BLOK satirlar DOKUNULMADI listesinde
    hazirla()
    pl = json.loads((TMP / "PLAN.json").read_text())
    for x in pl["satirlar"]:
        x["durum"], x["neden"] = "BLOK", "galeri v10 kaydi PASS degil (kayit yok)"
    (TMP / "PLAN.json").write_text(json.dumps(pl))
    f = Fake()
    s, ok, rep = kos(f, "sifir")
    bak("sifir satir: FAIL, yazma yok, DOKUNULMADI 4", not ok and not f.yaz and "DOKUNULMADI (plan BLOK, 4)" in rep)
    # 7 kuru: galeri kapisi BLOK, eski video INDIRILMEZ, PLAN surum v7, BLOK'lu plan ok
    vd = TMP / "kuru_video"
    vd.mkdir()
    if shutil.which("ffmpeg"):
        mp4(vd / "ARIES_LEO.mp4")
        for _, c in IDS[1:]:
            shutil.copyfile(vd / "ARIES_LEO.mp4", vd / f"{c}.mp4")
    else:
        for _, c in IDS:
            (vd / f"{c}.mp4").write_bytes(b"x" * 20000)
        V.video_bilgi = lambda p: {"w": 1440, "h": 1080, "kare": 180, "fps": 30.0, "sure": 6.0}
    man = {c: {"cift": c, "qc_sonuc": "PASS", "sha256": V.sha(vd / f"{c}.mp4"), "ses_akisi": "False"} for _, c in IDS}
    man["LEO_LEO"]["qc_sonuc"] = "FAIL"
    g = galeri(farkli=("222",))
    g["333"]["durum"] = "DUR"
    f = Fake(vids={"111": [1110], "222": [2220], "333": [], "444": [4440]})
    indir = []
    V.requests.get = lambda *a, **k: indir.append(a) or (_ for _ in ()).throw(AssertionError("indirme"))
    out = TMP / "kuru"
    out.mkdir()
    a = SimpleNamespace(video_dir=str(vd), quota_min=10, haric=[], kaynak={}, surum="v7", galeri=g, manifest_rows=man)
    V.BEKLENEN = len(IDS)   # kuru: ilan sayisi kapisi (gercekte 78)
    kok = V.kuru(a, f, out, [{"listing_id": l, "cift": c} for l, c in IDS])
    p = json.loads((out / "PLAN.json").read_text())
    r = {x["cift"]: x for x in p["satirlar"]}
    bak("kuru: 111 DEGISTIR (galeri PASS + kapak ayni, video 1440x1080 6 sn)",
        r["ARIES_LEO"]["durum"] == "DEGISTIR" and r["ARIES_LEO"]["kapak_id"] == KAPAK["111"]
        and r["ARIES_LEO"]["eski_video"][0]["yedek"] == "111_1110.mp4" and r["ARIES_LEO"]["video"]["sure"] == 6.0)
    bak("kuru: 222 BLOK canli kapak galeri v10 degil", r["CANCER_LIBRA"]["durum"] == "BLOK" and "galeri v10 kapagi" in r["CANCER_LIBRA"]["neden"])
    bak("kuru: 333 BLOK ILERLEME PASS degil", r["PISCES_VIRGO"]["durum"] == "BLOK" and "PASS degil" in r["PISCES_VIRGO"]["neden"])
    bak("kuru: 444 BLOK MANIFEST QC FAIL", r["LEO_LEO"]["durum"] == "BLOK" and "MANIFEST" in r["LEO_LEO"]["neden"])
    bak("kuru: eski video indirilmedi, yazma yok, surum v7", not indir and not f.yaz and p["surum"] == "v7")
    bak("kuru: MANIFEST BLOK (galeri disi) -> SONUC FAIL", not kok and "galeri v10 bekliyor 2, diger 1" in (out / "report.md").read_text())
    man["LEO_LEO"]["qc_sonuc"] = "PASS"
    out2 = TMP / "kuru2"
    out2.mkdir()
    kok2 = V.kuru(a, Fake(vids={"111": [1110], "222": [2220], "333": [], "444": [4440]}), out2,
                  [{"listing_id": l, "cift": c} for l, c in IDS])
    bak("kuru: yalniz galeri BLOK -> SONUC PASS", kok2 and "galeri v10 bekliyor 2, diger 0" in (out2 / "report.md").read_text())
    with open(out / "PLAN.csv", encoding="utf-8") as fh:
        bak("kuru: PLAN.csv 4 satir", len(list(csv.DictReader(fh))) == 4)
    # 8 main: v5 plani v7 ile, onay dizesi
    env = {**os.environ, "TOKEN_FILE": "/yok", "ETSY_API_KEY": "", "ETSY_SHARED_SECRET": ""}
    r1 = subprocess.run([sys.executable, V.__file__, "--surum", "v7", "--video-dir", str(vd), "--out", str(TMP / "o8"), "--plan",
                         str(TMP / "PLAN.json"), "--yedek-liste", str(TMP / "yedek.txt"), "--apply", "--confirm", "VIDEO78_YUKLE",
                         "--manifest", "m", "--galeri-ilerleme", "g"], capture_output=True, text=True, env=env)
    bak("main: v7'de v5 onay dizesi -> DUR", r1.returncode != 0 and "VIDEO_V7_YUKLE" in r1.stderr)
    r2 = subprocess.run([sys.executable, V.__file__, "--surum", "v7", "--video-dir", str(vd), "--out", str(TMP / "o9")],
                        capture_output=True, text=True, env=env)
    bak("main: v7 manifest / galeri-ilerleme yok -> DUR", r2.returncode != 0 and "--galeri-ilerleme" in r2.stderr)
    print("V7 TEST", "PASS" if not hata else f"FAIL {hata}")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
