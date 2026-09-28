#!/usr/bin/env python3
"""kilit_bekle yerel testi (sahte GitHub API, sahte saat; ag yok, 60 sn alti).
 1 iki kosu sirayla: B (yeni) A (eski) bitene kadar bekler; A hic beklemez
 2 router atla: kumede aktif kosu varsa atla=true, yoksa false
 3 kume disi ve daha yeni kosular beklenmez; kendi kosusu sayilmaz; eski concurrency'li kosu kumede
 4 zaman asimi -> FAIL (1)
 5 API hatasi 6 kez -> FAIL (1), kilitsiz devam yok"""
import os
import sys
import tempfile
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kilit_bekle as K  # noqa: E402

KOK = tempfile.mkdtemp()
W = Path(KOK, ".github/workflows"); W.mkdir(parents=True)
(W / "yeni.yml").write_text("steps:\n  - run: python3 scripts/etsy/kilit_bekle.py\n")
(W / "eski.yml").write_text("concurrency:\n  group: etsy-token\n")
(W / "router.yml").write_text("run: python3 scripts/etsy/kilit_bekle.py --mod atla\n")
(W / "ilgisiz.yml").write_text("jobs: {}\n")


def kos(i, wf, st, t):
    return {"id": i, "path": f".github/workflows/{wf}.yml", "status": st, "created_at": t}


class Saat:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
    def uyku(self, s): self.t += s


def main():
    kotu = []
    out = Path(KOK, "out.txt")
    os.environ["GITHUB_OUTPUT"] = str(out)
    # 1 sira: A (eski, in_progress) ve B (yeni, bu kosu). A 3 tur sonra biter.
    s = Saat(); tur = {"n": 0}

    def getir_b():
        tur["n"] += 1
        a_st = "in_progress" if tur["n"] <= 3 else "completed"
        return [kos(200, "yeni", "in_progress", "2026-09-28T12:05:00Z"), kos(100, "eski", a_st, "2026-09-28T12:00:00Z")]
    os.environ["GITHUB_RUN_ID"] = "200"
    r = K.calis("bekle", KOK, getir_b, s.uyku, s, aralik=20)
    if r != 0 or tur["n"] != 4 or s.t != 60:
        kotu.append(f"sira B: donus {r} tur {tur['n']} sure {s.t}")
    os.environ["GITHUB_RUN_ID"] = "100"
    s2 = Saat()
    r = K.calis("bekle", KOK, lambda: [kos(100, "eski", "in_progress", "2026-09-28T12:00:00Z"),
                                       kos(200, "yeni", "queued", "2026-09-28T12:05:00Z")], s2.uyku, s2)
    if r != 0 or s2.t != 0:
        kotu.append(f"sira A beklememeli: {r} {s2.t}")
    # 2 router atla
    os.environ["GITHUB_RUN_ID"] = "300"
    out.write_text("")
    r = K.calis("atla", KOK, lambda: [kos(300, "router", "in_progress", "2026-09-28T12:10:00Z"),
                                      kos(200, "yeni", "in_progress", "2026-09-28T12:05:00Z")])
    if r != 0 or "atla=true" not in out.read_text():
        kotu.append(f"router atlamali: {r} {out.read_text()}")
    out.write_text("")
    r = K.calis("atla", KOK, lambda: [kos(300, "router", "in_progress", "2026-09-28T12:10:00Z"),
                                      kos(200, "yeni", "completed", "2026-09-28T12:05:00Z"),
                                      kos(150, "ilgisiz", "in_progress", "2026-09-28T12:01:00Z")])
    if r != 0 or "atla=false" not in out.read_text():
        kotu.append(f"router normal calismali: {r} {out.read_text()}")
    # 3 kume disi / daha yeni / kendisi beklenmez
    os.environ["GITHUB_RUN_ID"] = "200"
    s3 = Saat()
    r = K.calis("bekle", KOK, lambda: [kos(200, "yeni", "in_progress", "2026-09-28T12:05:00Z"),
                                       kos(150, "ilgisiz", "in_progress", "2026-09-28T12:01:00Z"),
                                       kos(250, "eski", "queued", "2026-09-28T12:06:00Z")], s3.uyku, s3)
    if r != 0 or s3.t != 0:
        kotu.append(f"kume disi/yeni beklenmemeli: {r} {s3.t}")
    if len(K.kilit_kumesi(KOK)) != 3:
        kotu.append(f"kume {K.kilit_kumesi(KOK)}")
    # 4 zaman asimi
    s4 = Saat()
    r = K.calis("bekle", KOK, lambda: [kos(200, "yeni", "in_progress", "2026-09-28T12:05:00Z"),
                                       kos(100, "eski", "in_progress", "2026-09-28T12:00:00Z")], s4.uyku, s4,
                zaman_asimi_dk=2)
    if r != 1 or s4.t < 120:
        kotu.append(f"zaman asimi: {r} {s4.t}")
    # 5 API hatasi
    s5 = Saat()

    def bozuk():
        raise urllib.error.URLError("sahte")
    r = K.calis("bekle", KOK, bozuk, s5.uyku, s5)
    if r != 1:
        kotu.append(f"API hatasi: {r}")
    print("SELFTEST:", "PASS" if not kotu else "FAIL " + "; ".join(kotu))
    raise SystemExit(0 if not kotu else 2)


if __name__ == "__main__":
    main()
