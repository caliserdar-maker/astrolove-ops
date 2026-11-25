#!/usr/bin/env python3
"""terim-tarama.yml ve dijital-arastirma.yml kabuk adimlari testi (CLAUDE.md HIZ VE KALITE 2: is akisi kabuk adimlari push oncesi yerelde
sahte aracla ve is akisinin kabuguyla). AG KAPALI: socket / urllib engelli; rclone, curl, gh PATH'te sahte. Betik cagrisi (terim_tarama.py /
dijital_arastirma.py) adim metninde sahte betikle degistirilir (cikis kodu ve cikti test kontrolunde); sir_koru.py GERCEK calisir.
Sahte rclone: copy SRC DST [--max-depth 1] [--include "/AD"]... (rclone belgesi: '/' ile baslayan desen kokten eslesir; --include
verilince digerleri dislanir), mkdir, lsf. Bilinen PASS: gecerli girdi, Drive'dan yalniz TERIM_* + durum indirilir, cikis kodu
KOD'a yazilir (0/3/4), Drive'a yazim, Sonuc 3'te yesil. Bilinen FAIL: dk 0 / 46 / harf, yeniden 'evet', etiket bos / '../x',
logda sir (sir_koru tee) -> KOD 1, ciktida sir -> Drive'a yazilmaz, Sonuc 1'de kirmizi, schedule / zincir / push tetigi geri gelirse."""
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = Path(__file__).resolve().parents[2]
WF = KOK / ".github" / "workflows"
HATA = []

SAHTE_RCLONE = r'''#!/usr/bin/env python3
import os, shutil, sys
from pathlib import Path
a = sys.argv[1:]
with open(os.environ["RCLONE_IZ"], "a") as f:
    f.write(" ".join(a) + "\n")
kok = Path(os.environ["SAHTE_DRIVE"])
def yol(x):
    assert x.startswith("gdrive:"), x
    return kok / x[len("gdrive:"):]
k = a[0]
if k == "lsf":
    sys.exit(0 if yol(a[1]).exists() else 3)
if k == "mkdir":
    yol(a[1]).mkdir(parents=True, exist_ok=True); sys.exit(0)
if k == "copy":
    src, dst = a[1], a[2]
    inc = [a[i + 1] for i, x in enumerate(a) if x == "--include"]
    derin = "--max-depth" in a and a[a.index("--max-depth") + 1] == "1"
    s = yol(src) if src.startswith("gdrive:") else Path(src)
    d = yol(dst) if dst.startswith("gdrive:") else Path(dst)
    if not s.exists():
        sys.exit(3)
    for p in s.rglob("*"):
        if not p.is_file():
            continue
        r = p.relative_to(s)
        if derin and len(r.parts) > 1:
            continue
        if inc and ("/" + str(r)) not in inc:
            continue
        (d / r).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, d / r)
    sys.exit(0)
sys.exit(9)
'''


def tetikler(yml):
    """'on:' blogunun ust duzey anahtarlari (yorumlar haric)."""
    m = re.search(r"^on:\n((?:  .*\n|\n)+)", yml, re.M)
    return {x.strip().rstrip(":").split(":")[0] for x in (m.group(1) if m else "").splitlines()
            if re.match(r"^  [a-z_]+:", x)}


def yalniz_elle(yml):
    govde = "\n".join(x for x in yml.splitlines() if not x.lstrip().startswith("#"))
    return tetikler(yml) == {"workflow_dispatch"} and "gh workflow run" not in govde and "schedule:" not in govde


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def adimlar(yml):
    """'      - name: X' bloklarindan {ad: run metni} (yalniz 'run: |' bloklari; girinti 10 bosluk)."""
    out = {}
    for blok in yml.split("\n      - name: ")[1:]:
        ad = blok.split("\n", 1)[0].strip()
        m = re.search(r"\n        run: \|\n((?:          .*\n|\n)+)", blok + "\n")
        if m:
            out[ad] = "\n".join(x[10:] for x in m.group(1).splitlines())
    return out


def kur(tmp):
    b = tmp / "bin"
    b.mkdir()
    (b / "rclone").write_text(SAHTE_RCLONE)
    for ad in ("curl", "gh", "wget"):
        (b / ad).write_text("#!/bin/sh\necho \"sahte $0: ag yok\" >&2\nexit 97\n")
    for p in b.iterdir():
        p.chmod(0o755)
    (tmp / "drive" / "ASTROLOVE").mkdir(parents=True)
    (tmp / "iz.txt").write_text("")
    return b


def kos_adim(metin, tmp, cwd, env_ek, bas="-eo pipefail"):
    ge = tmp / "github_env"
    ge.touch()
    env = {"PATH": f"{tmp / 'bin'}:{os.environ['PATH']}", "HOME": str(tmp / "home"), "GITHUB_ENV": str(ge),
           "RUNNER_TEMP": str(tmp / "rt"), "RCLONE_IZ": str(tmp / "iz.txt"), "SAHTE_DRIVE": str(tmp / "drive")}
    (tmp / "rt").mkdir(exist_ok=True)
    for x in ge.read_text().splitlines():
        if "=" in x:
            k, v = x.split("=", 1)
            env[k] = v
    env.update(env_ek)
    r = subprocess.run(["bash", *bas.split(), "-c", metin], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    return r


def sahte_betik(tmp, ad, kod, cikti):
    p = tmp / ad
    p.write_text(f"import sys, pathlib\nprint({cikti!r})\npathlib.Path('out').mkdir(exist_ok=True)\n"
                 f"pathlib.Path('out/{'terim_durum.json' if 'terim' in ad else 'durum.json'}').write_text("
                 f"'{{\"durum\": \"devam\", \"asama\": \"yorum\", \"kosu\": 1, \"istek_toplam\": 5, \"kalan_terim_n\": 2}}')\n"
                 f"sys.exit({kod})\n")
    return p


def calisma(tmp, ad):
    """Depodan yalniz gereken dosyalarla calisma kopyasi (scripts/guvenlik)."""
    c = tmp / ad
    (c / "scripts").mkdir(parents=True)
    shutil.copytree(KOK / "scripts" / "guvenlik", c / "scripts" / "guvenlik")
    return c


def test_terim(tmp0):
    yml = (WF / "terim-tarama.yml").read_text(encoding="utf-8")
    kontrol("terim-tarama: yalniz workflow_dispatch (schedule / push / zincir yok)", yalniz_elle(yml))
    kontrol("terim-tarama: actions read, concurrency yok", "actions: read" in yml and "actions: write" not in yml and "concurrency:" not in yml)
    kontrol("terim-tarama: kilit Drive durumundan once", yml.index("python3 scripts/etsy/kilit_bekle.py")
            < yml.index("rclone copy \"gdrive:ASTROLOVE/DIJITAL_ARASTIRMA_20261125\" out") < yml.index("python scripts/etsy/terim_tarama.py"))
    kontrol("terim-tarama: ${{ }} run metninde yok (girdi env ile)", all("${{" not in v for v in adimlar(yml).values()))
    A = adimlar(yml)
    # girdi kapisi
    for dk, yen, bek in (("30", "false", 0), ("45", "true", 0), ("0", "false", 1), ("46", "false", 1), ("3a", "false", 1),
                         ("30", "evet", 1), ("", "", 0)):
        tmp = Path(tempfile.mkdtemp(dir=tmp0))
        kur(tmp)
        r = kos_adim(A["Girdi kapisi"], tmp, tmp, {"DK_G": dk, "YENIDEN_G": yen}, "-e")
        kontrol(f"terim girdi dk={dk!r} yeniden={yen!r} -> {bek}", r.returncode == bek)
    # Drive'dan al: yalniz TERIM_* + terim_durum.json, alt klasor yok
    tmp = Path(tempfile.mkdtemp(dir=tmp0))
    kur(tmp)
    uz = tmp / "drive" / "ASTROLOVE" / "DIJITAL_ARASTIRMA_20261125"
    (uz / "DERIN_1").mkdir(parents=True)
    for ad in ("TERIM_TARAMA.csv", "TERIM_ILAN.csv", "TERIM_MAGAZA.csv", "terim_durum.json", "ILANLAR.csv", "durum.json",
               "YORUMLAR.csv", "DERIN_1/durum.json"):
        (uz / ad).write_text("x")
    c = calisma(tmp, "c")
    r = kos_adim(A["Durumu Drive'dan al (kilitten sonra)"], tmp, c, {}, "-e")
    inen = sorted(str(p.relative_to(c / "out")) for p in (c / "out").rglob("*") if p.is_file())
    kontrol("terim Drive indirme: yalniz TERIM_* + terim_durum.json", r.returncode == 0
            and inen == ["TERIM_ILAN.csv", "TERIM_MAGAZA.csv", "TERIM_TARAMA.csv", "terim_durum.json"])
    # Tara: cikis kodu KOD'a; sir_koru tee gercek
    sir = "SAHTE-ANAHTAR-0123456789"
    for kod, cikti, bek in ((0, "KOSU 1: durum bitti", "0"), (3, "DUR: kota", "3"), (4, "YOL", "4"), (1, "HATA", "1"),
                            (0, f"sizinti {sir}", "1")):
        tmp = Path(tempfile.mkdtemp(dir=tmp0))
        kur(tmp)
        c = calisma(tmp, "c")
        sb = sahte_betik(tmp, "terim_sahte.py", kod, cikti)
        m = A["Tara (salt okur)"].replace("python scripts/etsy/terim_tarama.py", f"python3 {sb}")
        kontrol("terim Tara: betik cagrisi degistirildi", m != A["Tara (salt okur)"])
        (tmp / "github_env").write_text("DK=30\nYENIDEN=true\n")
        r = kos_adim(m, tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789", "YALNIZ": "a; b"}, "-e")
        ge = (tmp / "github_env").read_text()
        log = (c / "out" / "TERIM_KOSU_LOG.txt").read_text() if (c / "out" / "TERIM_KOSU_LOG.txt").exists() else ""
        kontrol(f"terim Tara cikis {kod} ({cikti[:12]}) -> KOD={bek}, adim 0", r.returncode == 0 and f"KOD={bek}" in ge)
        kontrol(f"terim Tara log dosyasinda sir yok ({cikti[:12]})", sir not in log and (cikti in log or sir in cikti))
        kontrol("terim Tara: sir.json silindi", not (tmp / "rt" / "sir.json").exists())
        if kod == 0 and sir not in cikti:
            # Drive'a yaz: temiz -> copy; sonra ciktida sir -> yazilmaz
            r2 = kos_adim(A["Drive'a yaz (sir taramasi)"], tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789"}, "-e")
            iz = (tmp / "iz.txt").read_text()
            kontrol("terim Drive'a yaz: temiz -> rclone copy out", r2.returncode == 0 and "copy out gdrive:ASTROLOVE/DIJITAL_ARASTIRMA_20261125" in iz)
            (c / "out" / "TERIM_ILAN.csv").write_text(f"x,{sir}\n")
            (tmp / "iz.txt").write_text("")
            r3 = kos_adim(A["Drive'a yaz (sir taramasi)"], tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789"}, "-e")
            kontrol("bilinen FAIL: ciktida sir -> Drive'a yazilmaz", r3.returncode == 1 and "copy out" not in (tmp / "iz.txt").read_text())
            (c / "out" / "TERIM_ILAN.csv").write_text("x\n")
            (c / "out" / "TERIM_KOSU_LOG.txt").write_text("authorization: Bearer abcdefghijklmnop\n")
            r4 = kos_adim(A["Drive'a yaz (sir taramasi)"], tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789"}, "-e")
            kontrol("bilinen FAIL: logda sir deseni -> Drive'a yazilmaz", r4.returncode == 1 and "copy out" not in (tmp / "iz.txt").read_text())
    for kod, bek in (("0", 0), ("3", 0), ("4", 0), ("1", 1), ("", 1)):
        tmp = Path(tempfile.mkdtemp(dir=tmp0))
        kur(tmp)
        r = kos_adim(A["Sonuc (1 ise kirmizi)"], tmp, tmp, {"KOD": kod} if kod else {}, "-e")
        kontrol(f"terim Sonuc KOD={kod!r} -> {bek}", r.returncode == bek)


def test_derin(tmp0):
    yml = (WF / "dijital-arastirma.yml").read_text(encoding="utf-8")
    kontrol("dijital-arastirma: yalniz workflow_dispatch (schedule / push / zincir yok)", yalniz_elle(yml) and "zincir:" not in yml)
    kontrol("dijital-arastirma: actions read", "actions: read" in yml and "actions: write" not in yml and "concurrency:" not in yml)
    kontrol("dijital-arastirma: kilit Drive durumundan once", yml.index("python3 scripts/etsy/kilit_bekle.py")
            < yml.index("rclone copy \"$U\" out") < yml.index("python scripts/etsy/dijital_arastirma.py"))
    A = adimlar(yml)
    kontrol("dijital-arastirma: ${{ }} run metninde yok", all("${{" not in v for v in A.values()))
    for dk, et, bek in (("40", "1", 0), ("45", "secim_A-2", 0), ("0", "1", 1), ("40", "", 1), ("40", "../x", 1),
                        ("40", "a" * 21, 1), ("40", "a b", 1)):
        tmp = Path(tempfile.mkdtemp(dir=tmp0))
        kur(tmp)
        r = kos_adim(A["Girdi kapisi"], tmp, tmp, {"DK_G": dk, "ETIKET_G": et}, "-e")
        kontrol(f"derin girdi dk={dk!r} etiket={et[:8]!r} -> {bek}", r.returncode == bek)
    tmp = Path(tempfile.mkdtemp(dir=tmp0))
    kur(tmp)
    uz = tmp / "drive" / "ASTROLOVE" / "DIJITAL_ARASTIRMA_20261125"
    (uz / "DERIN_7").mkdir(parents=True)
    (uz / "ILANLAR.csv").write_text("eski")
    (uz / "DERIN_7" / "durum.json").write_text("{}")
    c = calisma(tmp, "c")
    (tmp / "github_env").write_text("ETIKET=7\n")
    r = kos_adim(A["Durumu Drive'dan al (kilitten sonra)"], tmp, c, {}, "-e")
    inen = sorted(str(p.relative_to(c / "out")) for p in (c / "out").rglob("*") if p.is_file())
    kontrol("derin Drive indirme: yalniz DERIN_7 (ust klasor 25 Kas verisi inmez)", r.returncode == 0 and inen == ["durum.json"])
    sir = "SAHTE-ANAHTAR-0123456789"
    for kod, cikti, bek in ((0, "KOSU 1", "0"), (3, "DUR", "3"), (1, "HATA", "1"), (0, f"x {sir}", "1")):
        tmp = Path(tempfile.mkdtemp(dir=tmp0))
        kur(tmp)
        c = calisma(tmp, "c")
        sb = sahte_betik(tmp, "derin_sahte.py", kod, cikti)
        m = A["Oku (salt okur)"].replace("python scripts/etsy/dijital_arastirma.py", f"python3 {sb}")
        kontrol("derin Oku: betik cagrisi degistirildi", m != A["Oku (salt okur)"])
        (tmp / "github_env").write_text("DK=40\nETIKET=1\n")
        r = kos_adim(m, tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789", "TERIMLER": "a;b"}, "-e")
        kontrol(f"derin Oku cikis {kod} -> KOD={bek}", r.returncode == 0 and f"KOD={bek}" in (tmp / "github_env").read_text())
        if kod == 0 and sir not in cikti:
            r2 = kos_adim(A["Drive'a yaz (sir taramasi)"], tmp, c, {"ETSY_API_KEY": sir, "ETSY_SHARED_SECRET": "SAHTE-SIR-0123456789"}, "-e")
            kontrol("derin Drive'a yaz: DERIN_<etiket> klasorune", r2.returncode == 0
                    and "copy out gdrive:ASTROLOVE/DIJITAL_ARASTIRMA_20261125/DERIN_1 " in (tmp / "iz.txt").read_text() + " ")


def main():
    tmp0 = Path(tempfile.mkdtemp(prefix="isakis_"))
    try:
        test_terim(tmp0)
        test_derin(tmp0)
        # mutasyon: schedule geri gelirse kontrol yakalar
        yml = (WF / "terim-tarama.yml").read_text(encoding="utf-8").replace("on:\n  workflow_dispatch:", "on:\n  schedule:\n    - cron: \"1 * * * *\"\n  workflow_dispatch:")
        kontrol("mutasyon: schedule eklenirse yakalanir", not yalniz_elle(yml))
        eski = (WF / "dijital-arastirma.yml").read_text(encoding="utf-8")
        kontrol("mutasyon: zincir (gh workflow run) eklenirse yakalanir", not yalniz_elle(eski + "\n      - run: gh workflow run x.yml\n"))
        kontrol("mutasyon: push tetigi eklenirse yakalanir", not yalniz_elle(eski.replace("on:\n", "on:\n  push:\n    branches: [main]\n", 1)))
        import subprocess as _sp
        main_yml = _sp.run(["git", "show", "origin/main:.github/workflows/dijital-arastirma.yml"], cwd=KOK, capture_output=True, text=True)
        if main_yml.returncode == 0 and "schedule" in main_yml.stdout:
            kontrol("bilinen FAIL: 25 Kas main surumu (schedule + zincir) yakalanir", not yalniz_elle(main_yml.stdout))
    finally:
        shutil.rmtree(tmp0, ignore_errors=True)
    print(f"SONUC: {'FAIL ' + str(len(HATA)) if HATA else 'PASS'}")
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
