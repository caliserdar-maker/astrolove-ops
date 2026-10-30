#!/usr/bin/env python3
"""video_yukle_78 --surum v7d yerel testi (Serdar onayi 30 Eki) - sahte Etsy, sentetik veri, gercek token YOK, Etsy'ye istek YOK.
Senaryolar: --manifest-uret (PASS; QC FAIL / ses akisi / 1280x720 / eksik dosya / fazla dosya / QC.csv eksik cift -> DUR, MANIFEST
yazilmaz), galeri v11 kapisi (PASS / kayit yok / hedef 9 / son_ids eksik / canli kapak farkli / kume farkli), kuru v7d (galeri bekliyor
SONUC'u bozmaz, MANIFEST alan farki FAIL, eski video indirilmez), apply v7d (yukle -> active -> eski sil, galeri ATLANDI, kota kapisi),
main kilitleri (MANIFEST ilan listesiyle birebir degil, plan v7 / v7d karismaz, plan MANIFEST sha256 farkli -> DUR; hepsi token
okunmadan). ffmpeg / ffprobe gerekli (yoksa testler SKIP degil FAIL)."""
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
import video_yukle_78_v7_test as T  # noqa: E402  (Fake API ve ilanlar)

V.OKUMA_BEKLE = V.OKUMA_BEKLE_V7 = 0
os.environ["ETSY_SHOP_ID"] = "39729443"
TMP = Path(tempfile.mkdtemp())
IDS = T.IDS
GALERI_ID = {lid: [int(lid) * 100 + i for i in range(10)] for lid, _ in IDS}   # v11: 10 gorsel, son_ids[0] = canli kapak


def mp4(p, w=1440, h=1080, d=6, ses=False):
    k = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x202030:s={w}x{h}:r=30:d={d}"]
    if ses:
        k += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono:d={d}", "-shortest", "-c:a", "aac"]
    subprocess.run(k + ["-c:v", "libx264", "-pix_fmt", "yuv420p"] + ([] if ses else ["-an"]) + [str(p)], check=True)


def ids_csv(p, rows):
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["listing_id", "cift", "a", "b"])
        w.writerows([[lid, c, "x", "y"] for lid, c in rows])


def qc_csv(p, rows):
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["cift", "sonuc", "deneme"])
        w.writerows([[c, s, 1] for c, s in rows])


def g11(**ek):
    g = {lid: {"cift": c, "set": 10, "hedef": 10, "durum": "PASS", "son_ids": list(GALERI_ID[lid])} for lid, c in IDS}
    for lid, d in ek.items():
        g[lid].update(d)
    return g


def fake(**kw):
    f = T.Fake(**kw)
    for lid, _ in IDS:
        f.L[lid]["imgs"] = list(GALERI_ID[lid])
    return f


def main():
    hata = []

    def bak(ad, kosul):
        print(("PASS " if kosul else "FAIL ") + ad)
        kosul or hata.append(ad)

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("FAIL ffmpeg / ffprobe yok")
        sys.exit(1)
    V.BEKLENEN = len(IDS)
    # ---------------- 1 --manifest-uret
    src = TMP / "tam78"
    src.mkdir()
    mp4(src / "ARIES_LEO.mp4")
    for _, c in IDS[1:]:
        shutil.copyfile(src / "ARIES_LEO.mp4", src / f"{c}.mp4")
    with open(src / "LEO_LEO.mp4", "ab") as fh:   # sha256 tekil olsun (gercekte her cift farkli)
        fh.write(b"\0")
    for i, (_, c) in enumerate(IDS[1:3], 1):
        with open(src / f"{c}.mp4", "ab") as fh:
            fh.write(b"\0" * (i + 1))
    ids_csv(TMP / "ids.csv", IDS)
    qc_csv(TMP / "qc.csv", [(c, "PASS") for _, c in IDS])

    def uret(ad, vdir=src, qc=TMP / "qc.csv", ids=TMP / "ids.csv"):
        out = TMP / ad
        kod = V.manifest_uret(SimpleNamespace(video_dir=str(vdir), qc_csv=str(qc), ids=str(ids), out=str(out)))
        return kod, out, json.loads((out / "OLCUM.json").read_text())

    kod, out, oz = uret("m_ok")
    rows = list(csv.DictReader(open(out / "MANIFEST.csv", encoding="utf-8"))) if (out / "MANIFEST.csv").exists() else []
    bak("manifest PASS: 4 satir, kod 0", kod == 0 and len(rows) == 4)
    bak("manifest sutunlari", rows and list(rows[0]) == V.MANIFEST_ALAN)
    bak("manifest: listing_id / dosya / olcum (1440x1080, 6 sn, 30 fps, ses False, QC PASS)",
        all(r["listing_id"] == lid and r["dosya"] == f"{c}.mp4" and r["genislik"] == "1440" and r["yukseklik"] == "1080"
            and float(r["sure_sn"]) == 6.0 and float(r["fps"]) == 30.0 and r["ses_akisi"] == "False" and r["qc_sonuc"] == "PASS"
            and r["sha256"] == V.sha(src / f"{c}.mp4") for r, (lid, c) in zip(rows, IDS)))
    bak("manifest OLCUM dagilimi", oz["cozunurluk"] == {"1440x1080": 4} and oz["sonuc"] == "PASS" and (out / "OLCUM.md").read_text().startswith("PASS video 4 / 4"))

    def dur(ad, kosul_md, **kw):
        kod, out, oz = uret(ad, **kw)
        bak(f"manifest DUR {ad}: kod 1, MANIFEST yok, neden '{kosul_md}'",
            kod == 1 and not (out / "MANIFEST.csv").exists() and kosul_md in (out / "OLCUM.md").read_text())

    qc_csv(TMP / "qc_fail.csv", [(c, "FAIL" if c == "LEO_LEO" else "PASS") for _, c in IDS])
    dur("qc_fail", "LEO_LEO: QC FAIL", qc=TMP / "qc_fail.csv")
    qc_csv(TMP / "qc_eksik.csv", [(c, "PASS") for _, c in IDS[:3]])
    dur("qc_eksik", "QC.csv", qc=TMP / "qc_eksik.csv")
    s2 = TMP / "tam78_ses"
    shutil.copytree(src, s2)
    mp4(s2 / "CANCER_LIBRA.mp4", ses=True)
    dur("ses", "CANCER_LIBRA: ses True", vdir=s2)
    s3 = TMP / "tam78_boyut"
    shutil.copytree(src, s3)
    mp4(s3 / "PISCES_VIRGO.mp4", w=1280, h=720)
    dur("boyut", "PISCES_VIRGO: cozunurluk 1280x720", vdir=s3)
    s4 = TMP / "tam78_eksik"
    shutil.copytree(src, s4)
    (s4 / "LEO_LEO.mp4").unlink()
    dur("eksik_dosya", "mp4", vdir=s4)
    s5 = TMP / "tam78_fazla"
    shutil.copytree(src, s5)
    shutil.copyfile(src / "LEO_LEO.mp4", s5 / "VIRGO_VIRGO.mp4")
    dur("fazla_dosya", "fazla ['VIRGO_VIRGO']", vdir=s5)
    s6 = TMP / "tam78_kisa"
    shutil.copytree(src, s6)
    mp4(s6 / "ARIES_LEO.mp4", d=3)
    dur("sure", "ARIES_LEO: sure 3.0", vdir=s6)
    man = {r["cift"]: r for r in rows}

    # ---------------- 2 galeri v11 kapisi (dogrudan)
    f = fake()

    def kapi(kayit, lid="111"):
        n = []
        kp = V.galeri_kapisi_v11(f, lid, kayit, n)
        return kp, n

    g = g11()
    bak("galeri v11 PASS: neden yok, kapak = son_ids[0]", kapi(g["111"]) == (GALERI_ID["111"][0], []))
    bak("galeri v11 kayit yok -> neden", "kayit yok" in " ".join(kapi(None)[1]))
    bak("galeri v11 hedef 9 (v10 kaydi) -> neden", "PASS degil" in " ".join(kapi(dict(g["111"], hedef=9, set=9))[1]))
    bak("galeri v11 son_ids eksik -> neden", "son_ids 9" in " ".join(kapi(dict(g["111"], son_ids=GALERI_ID["111"][:9]))[1]))
    bak("galeri v11 durum DUR -> neden", "PASS degil (DUR" in " ".join(kapi(dict(g["111"], durum="DUR"))[1]))
    f.L["111"]["imgs"] = [GALERI_ID["111"][1], GALERI_ID["111"][0]] + GALERI_ID["111"][2:]
    bak("galeri v11 canli kapak farkli -> neden", "galeri v11 kapagi" in " ".join(kapi(g["111"])[1]))
    f.L["111"]["imgs"] = GALERI_ID["111"][:9] + [5]
    bak("galeri v11 kume farkli -> neden", "kaydindan farkli" in " ".join(kapi(g["111"])[1]))
    bak("galeri v7 (v10) kapisi degismedi: hedef 9 kayit PASS sayilir",
        V.galeri_kapisi(fake(), "111", {"durum": "PASS", "set": 10, "hedef": 9, "son_ids": GALERI_ID["111"]}, []) == GALERI_ID["111"][0])

    # ---------------- 3 kuru v7d
    indir = []
    V.requests.get = lambda *a, **k: indir.append(a) or (_ for _ in ()).throw(AssertionError("indirme"))
    g = g11(**{"333": {"durum": "DUR"}, "444": {"hedef": 9}})
    a = SimpleNamespace(video_dir=str(src), quota_min=10, haric=[], kaynak={"klasor": "TEMP/VIDEO_V7_DUZELTME/X/TAM78/",
                        "manifest_sha256": "abc"}, surum="v7d", galeri=g, manifest_rows=man)
    f = fake(vids={"111": [1110], "222": [], "333": [3330], "444": [4440]})
    out = TMP / "kuru"
    out.mkdir()
    kok = V.kuru(a, f, out, [{"listing_id": l, "cift": c} for l, c in IDS])
    p = json.loads((out / "PLAN.json").read_text())
    r = {x["cift"]: x for x in p["satirlar"]}
    rep = (out / "report.md").read_text()
    bak("kuru v7d: 111 DEGISTIR, 222 YUKLE, kapak id", r["ARIES_LEO"]["durum"] == "DEGISTIR" and r["CANCER_LIBRA"]["durum"] == "YUKLE"
        and r["ARIES_LEO"]["kapak_id"] == GALERI_ID["111"][0])
    bak("kuru v7d: 333 / 444 BLOK galeri bekliyor (v11)", r["PISCES_VIRGO"]["galeri_bekliyor"] and r["LEO_LEO"]["galeri_bekliyor"]
        and "galeri v11 kaydi" in r["LEO_LEO"]["neden"])
    bak("kuru v7d: yalniz galeri BLOK -> SONUC PASS, rapor 'galeri v11 bekliyor 2, diger 0'",
        kok and "galeri v11 bekliyor 2, diger 0" in rep)
    bak("kuru v7d: PLAN surum v7d + kaynak manifest_sha256, yazma / indirme yok",
        p["surum"] == "v7d" and p["kaynak"]["manifest_sha256"] == "abc" and not f.yaz and not indir)
    man2 = {c: dict(x) for c, x in man.items()}
    man2["CANCER_LIBRA"]["listing_id"] = "999"
    a.manifest_rows, a.galeri = man2, g11()
    out2 = TMP / "kuru2"
    out2.mkdir()
    kok2 = V.kuru(a, fake(), out2, [{"listing_id": l, "cift": c} for l, c in IDS])
    r2 = {x["cift"]: x for x in json.loads((out2 / "PLAN.json").read_text())["satirlar"]}
    bak("kuru v7d: MANIFEST listing_id farkli -> BLOK (galeri disi) -> SONUC FAIL",
        not kok2 and r2["CANCER_LIBRA"]["durum"] == "BLOK" and "listing_id" in r2["CANCER_LIBRA"]["neden"]
        and not r2["CANCER_LIBRA"]["galeri_bekliyor"])
    man3 = {c: dict(x) for c, x in man.items()}
    man3["ARIES_LEO"]["ses_akisi"] = "True"
    a.manifest_rows = man3
    out3 = TMP / "kuru3"
    out3.mkdir()
    kok3 = V.kuru(a, fake(), out3, [{"listing_id": l, "cift": c} for l, c in IDS])
    bak("kuru v7d: MANIFEST ses True -> BLOK, SONUC FAIL", not kok3 and "ses True" in (out3 / "report.md").read_text())

    # ---------------- 4 apply v7d
    plan_rows = []
    for lid, c in IDS:
        plan_rows.append({"listing_id": lid, "cift": c, "state": "active", "durum": "DEGISTIR", "neden": "",
                          "video": {"dosya": f"{c}.mp4", "sha256": V.sha(src / f"{c}.mp4")}, "kapak_id": GALERI_ID[lid][0],
                          "eski_video": [{"video_id": int(lid) * 10, "url": "u", "yedek": f"{lid}_{int(lid) * 10}.mp4"}]})
    plan = {"olusturma": "t", "surum": "v7d", "kaynak": {"klasor": "K"}, "satirlar": plan_rows}
    (TMP / "yedek.txt").write_text("\n".join(f"{lid}_{int(lid) * 10}.mp4" for lid, _ in IDS))

    def ap(f, ad, **kw):
        out = TMP / ad
        out.mkdir()
        a = SimpleNamespace(video_dir=str(src), yedek_liste=str(TMP / "yedek.txt"), quota_min=10, haric=[], plan="P",
                            kaynak={"plan": "KURU_T/PLAN.json"}, surum="v7d", galeri=g11())
        a.__dict__.update(kw)
        s, ok = V.apply(a, f, out, plan)
        return {x["cift"]: x for x in s}, ok

    f = fake()
    s, ok = ap(f, "ap_ok")
    bak("apply v7d: 4 YUKLENDI, tek gonderim, ilanda yalniz yeni video",
        ok and [s[c]["sonuc"] for _, c in IDS] == ["YUKLENDI"] * 4 and f.tekrar == [1] * 4
        and all(f.L[l]["vids"] == [int(s[c]["yeni_video"])] for l, c in IDS))
    f = fake()
    g = g11(**{"222": {"hedef": 9}})
    s, ok = ap(f, "ap_galeri", galeri=g)
    bak("apply v7d: galeri v11 hedef 9 -> GALERI_BEKLIYOR (hata degil), yazma yok, diger 3 YUKLENDI -> PASS",
        s["CANCER_LIBRA"]["sonuc"] == "GALERI_BEKLIYOR" and "galeri v11" in s["CANCER_LIBRA"]["neden"]
        and not any(y[1] == "222" for y in f.yaz) and ok and sum(x["sonuc"] == "YUKLENDI" for x in s.values()) == 3)
    f = fake()
    f.L["333"]["vids"] = [3330, 3331]
    s, ok = ap(f, "ap_galeri2", galeri=g11(**{"333": {"hedef": 9}}))
    bak("apply v7d: galeri + baska neden -> ATLANDI (galeri bekliyor sayilmaz), EKSIK",
        s["PISCES_VIRGO"]["sonuc"] == "ATLANDI" and not ok)
    f = fake(kota=V.ILAN_CAGRI_UST_V7 + 10 + 12)
    s, ok = ap(f, "ap_kota")
    d = [s[c]["sonuc"] for _, c in IDS]
    bak(f"apply v7d: kota kapisi (ust {V.ILAN_CAGRI_UST_V7} + taban 10) -> ATLANDI, yarim yok ({d})",
        not ok and d[0] == "YUKLENDI" and "FAIL" not in d and "ATLANDI" in d)
    f = fake(hata={"111": "islenmez"})
    s, ok = ap(f, "ap_islenmez")
    bak("apply v7d: yeni video active olmadi -> FAIL, eski SILINMEDI, durur",
        s["ARIES_LEO"]["sonuc"] == "FAIL" and not any(y[0] == "DELETE" for y in f.yaz) and 1110 in f.L["111"]["vids"])
    f = fake()
    f.L["333"]["vids"] = [3330, 3331]
    s, ok = ap(f, "ap_canli")
    bak("apply v7d: canli video plandan farkli -> ATLANDI", s["PISCES_VIRGO"]["sonuc"] == "ATLANDI" and "canli video" in s["PISCES_VIRGO"]["neden"])
    (TMP / "yedek_eksik.txt").write_text("111_1110.mp4")
    s, ok = ap(fake(), "ap_yedek", yedek_liste=str(TMP / "yedek_eksik.txt"))
    bak("apply v7d: yedegi olmayan ilan ATLANDI", s["CANCER_LIBRA"]["sonuc"] == "ATLANDI" and "yedegi" in s["CANCER_LIBRA"]["neden"])

    # ---------------- 5 main kilitleri (token okunmadan DUR; TOKEN_FILE yok)
    env = {k: v for k, v in os.environ.items() if k not in ("TOKEN_FILE", "ETSY_API_KEY", "ETSY_SHARED_SECRET")}
    rows78 = [(str(4570000000 + i), f"C{i:02d}_X") for i in range(78)]
    ids_csv(TMP / "ids78.csv", rows78)
    with open(TMP / "man78.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=V.MANIFEST_ALAN)
        w.writeheader()
        w.writerows({"cift": c, "listing_id": lid} for lid, c in rows78[:77])
    (TMP / "g.json").write_text(json.dumps({"ilanlar": {}}))
    (TMP / "kb.json").write_text(json.dumps({"klasor": "TEMP/VIDEO_V7_DUZELTME/X/TAM78/"}))
    temel = [sys.executable, V.__file__, "--surum", "v7d", "--ids", str(TMP / "ids78.csv"), "--video-dir", str(src),
             "--galeri-ilerleme", str(TMP / "g.json"), "--kaynak-bilgi", str(TMP / "kb.json"), "--out", str(TMP / "o_main")]
    r1 = subprocess.run(temel + ["--manifest", str(TMP / "man78.csv")], capture_output=True, text=True, env=env)
    bak("main v7d: MANIFEST 77/78 -> DUR (token okunmadan)", r1.returncode != 0 and "birebir degil" in r1.stderr and "TOKEN" not in r1.stderr)
    with open(TMP / "man78.csv", "a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=V.MANIFEST_ALAN).writerow({"cift": rows78[77][1], "listing_id": rows78[77][0]})
    pl = {"surum": "v7", "kaynak": {"klasor": "TEMP/VIDEO_V7_DUZELTME/X/TAM78/"}, "satirlar": [
        {"listing_id": rows78[0][0], "cift": rows78[0][1], "durum": "YUKLE"}]}
    (TMP / "pl_v7.json").write_text(json.dumps(pl))
    app = ["--apply", "--confirm", "VIDEO_V7_YUKLE", "--yedek-liste", str(TMP / "yedek.txt"), "--manifest", str(TMP / "man78.csv")]
    r2 = subprocess.run(temel + app + ["--plan", str(TMP / "pl_v7.json")], capture_output=True, text=True, env=env)
    bak("main v7d: v7 plani -> DUR (surum karismaz)", r2.returncode != 0 and "plan surumu v7 != --surum v7d" in r2.stderr)
    pl.update(surum="v7d")
    pl["kaynak"]["manifest_sha256"] = "farkli"
    (TMP / "pl_v7d.json").write_text(json.dumps(pl))
    r3 = subprocess.run(temel + app + ["--plan", str(TMP / "pl_v7d.json")], capture_output=True, text=True, env=env)
    bak("main v7d: plan MANIFEST sha256 farkli -> DUR", r3.returncode != 0 and "v7d plan kaynagi" in r3.stderr)
    pl["kaynak"]["manifest_sha256"] = V.sha(TMP / "man78.csv")
    pl["kaynak"]["klasor"] = "TEMP/VIDEO_V7_DUZELTME/Y/TAM78/"
    (TMP / "pl_v7d2.json").write_text(json.dumps(pl))
    r4 = subprocess.run(temel + app + ["--plan", str(TMP / "pl_v7d2.json")], capture_output=True, text=True, env=env)
    bak("main v7d: plan TAM78 klasoru farkli -> DUR", r4.returncode != 0 and "v7d plan kaynagi" in r4.stderr)
    pl["kaynak"]["klasor"] = "TEMP/VIDEO_V7_DUZELTME/X/TAM78/"
    pl["satirlar"].append({"listing_id": rows78[1][0], "cift": rows78[1][1], "durum": "BLOK", "galeri_bekliyor": False, "neden": "state draft"})
    (TMP / "pl_blok.json").write_text(json.dumps(pl))
    r6 = subprocess.run(temel + app + ["--plan", str(TMP / "pl_blok.json")], capture_output=True, text=True, env=env)
    bak("main v7d: planda galeri disi BLOK (kuru FAIL) -> DUR", r6.returncode != 0 and "plan kullanilamaz" in r6.stderr)
    pl["satirlar"][-1].update(galeri_bekliyor=True, neden="galeri v11 kaydi PASS degil")
    (TMP / "pl_gal.json").write_text(json.dumps(pl))
    r7 = subprocess.run(temel + app + ["--plan", str(TMP / "pl_gal.json")], capture_output=True, text=True, env=env)
    bak("main v7d: yalniz galeri BLOK'lu plan kilitleri gecer (token adimina kadar; TOKEN_FILE yok)",
        r7.returncode != 0 and "plan kullanilamaz" not in r7.stderr and "TOKEN_FILE" in r7.stderr)
    r5 = subprocess.run([sys.executable, V.__file__, "--manifest-uret", "--video-dir", str(src), "--out", str(TMP / "o_mu")],
                        capture_output=True, text=True, env=env)
    bak("main --manifest-uret: --qc-csv yok -> DUR", r5.returncode != 0 and "--qc-csv" in r5.stderr)
    r6 = subprocess.run([sys.executable, V.__file__, "--manifest-uret", "--video-dir", str(src), "--qc-csv", str(TMP / "qc.csv"),
                         "--ids", str(TMP / "ids.csv"), "--out", str(TMP / "o_mu2")], capture_output=True, text=True, env=env)
    bak("main --manifest-uret: token okunmaz (TOKEN_FILE yok), 4 != 78 -> DUR, MANIFEST yok",
        r6.returncode == 1 and not (TMP / "o_mu2" / "MANIFEST.csv").exists() and "KeyError" not in r6.stderr)
    print("V7D TEST", "PASS" if not hata else f"FAIL {hata}")
    sys.exit(1 if hata else 0)


if __name__ == "__main__":
    main()
