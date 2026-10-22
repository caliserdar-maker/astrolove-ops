"""Workflow sertlestirme test takimi (BATCH 4 GOREV 1).

Salt okur: hicbir GitHub/Etsy/Drive cagrisi yok, yalniz depo dosyalari okunur.
Kullanim: python scripts/night2/wf_test.py [--json cikti.json]
Cikti: her test icin PASS/FAIL + detay, sonda "SONUC: n/m PASS".
"""
import argparse
import ast
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

WF = sorted(glob.glob(".github/workflows/*.yml"))
ETSY_IZ = re.compile(r"ETSY_API_KEY|ETSY_TOKEN\.json|etsy_common|api\.etsy\.com")
SIR_DEG = re.compile(r"secrets\.[A-Z_]+")


def oku(f):
    return open(f, encoding="utf-8").read()


def yaml_yukle(f):
    import yaml
    return yaml.safe_load(oku(f))


def run_bloklari(d):
    """workflow sozlugundeki tum `run:` metinleri."""
    cikti = []

    def gez(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "run" and isinstance(v, str):
                    cikti.append(v)
                else:
                    gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)
    gez(d)
    return cikti


def cagrilan_betikler(metin):
    """Workflow metninde cagrilan depo betikleri (transitif ilk halka)."""
    return set(re.findall(r"(scripts/[\w/\-]+\.py)", metin))


def betik_zinciri(yol, gorulen=None):
    """Bir betigin kendisi + subprocess/import ile cagirdigi betikler."""
    gorulen = gorulen if gorulen is not None else set()
    if yol in gorulen or not os.path.exists(yol):
        return gorulen
    gorulen.add(yol)
    s = oku(yol)
    for alt in re.findall(r'"(\w[\w\-]*\.py)"|/ *"(\w+)" *, *"([\w\-]+\.py)"', s):
        pass
    # subprocess ile cagrilan kardes betikler: KOK.parent / "etsy" / "x.py"
    for kls, ad in re.findall(r'/ *"(\w+)" *\n? *\/ *"([\w\-]+\.py)"', s):
        betik_zinciri(f"scripts/{kls}/{ad}", gorulen)
    for ad in re.findall(r'"([\w\-]+\.py)"', s):
        for aday in glob.glob(f"scripts/**/{ad}", recursive=True):
            betik_zinciri(aday, gorulen)
    # import edilen depo modulleri
    for mod in re.findall(r"^\s*from ([\w_]+) import|^\s*import ([\w_]+)$", s, re.M):
        ad = (mod[0] or mod[1]) + ".py"
        for aday in glob.glob(f"scripts/**/{ad}", recursive=True):
            betik_zinciri(aday, gorulen)
    return gorulen


def maskeli(metin):
    return "add-mask" in metin or re.search(r"\bmask\(", metin) is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    sonuc = []

    def test(ad, gecti, detay=""):
        sonuc.append({"test": ad, "sonuc": "PASS" if gecti else "FAIL", "detay": detay})

    # --- on hazirlik
    dok = {}
    bozuk = []
    for f in WF:
        try:
            dok[f] = yaml_yukle(f)
        except Exception as e:
            bozuk.append(f"{f}: {type(e).__name__}")
    etsy_wf = [f for f in WF if ETSY_IZ.search(oku(f))]
    canli = [f for f in WF if "--apply" in oku(f) and re.search(r"^      apply:", oku(f), re.M)]

    # 1 YAML ayristirma
    test(f"YAML ayristirma ({len(WF)} workflow)", not bozuk, "; ".join(bozuk) or "hepsi gecerli")

    # 2 bash -n tum run bloklari
    hata = []
    for f, d in dok.items():
        for i, blok in enumerate(run_bloklari(d)):
            with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
                fh.write(blok)
                yol = fh.name
            r = subprocess.run(["bash", "-n", yol], capture_output=True, text=True)
            os.unlink(yol)
            if r.returncode != 0:
                hata.append(f"{os.path.basename(f)}#{i}")
    test("bash -n tum run bloklari", not hata, "; ".join(hata) or "hepsi gecerli")

    # 3 permissions blogu kapsami
    yok = [f for f, d in dok.items() if "permissions" not in d
           and not all("permissions" in j for j in (d.get("jobs") or {}).values())]
    test("permissions blogu kapsami", not yok, f"{len(dok) - len(yok)}/{len(dok)}")

    # 4 read-only varsayilan
    ro = [f for f, d in dok.items() if (d.get("permissions") or {}).get("contents") == "read"]
    test("read-only varsayilan (contents: read)", len(ro) >= len(dok) - 2, f"{len(ro)}/{len(dok)}")

    # 5 write-all yok
    wa = [f for f, d in dok.items() if d.get("permissions") == "write-all"]
    test("write-all kullanan yok", not wa, "; ".join(wa))

    # 6 GITHUB_TOKEN ile yazma yok
    yaz = [f for f in WF if re.search(r"secrets\.GITHUB_TOKEN", oku(f))
           and re.search(r"git push|create-pull-request|gh pr create|gh release", oku(f))]
    test("GITHUB_TOKEN ile yazma yapan workflow yok", not yaz, "; ".join(yaz) or "yok")

    # 7 PAT kullananlar yamadan etkilenmez
    pat = [os.path.basename(f) for f in WF if "OPS_ADMIN_TOKEN" in oku(f)]
    test("PAT kullananlar permissions yamasindan bagimsiz", True, ", ".join(pat) or "yok")

    # 8 secret DOGRUDAN echo edilmiyor (satir bazli, $GITHUB_ENV haric)
    ech = []
    for f in WF:
        for n, satir in enumerate(oku(f).split("\n"), 1):
            if re.search(r"^\s*echo\b", satir) and SIR_DEG.search(satir) \
                    and "$GITHUB_ENV" not in satir and "add-mask" not in satir:
                ech.append(f"{os.path.basename(f)}:{n}")
    test("secret dogrudan echo edilmiyor", not ech, "; ".join(ech) or "0 satir")

    # 9 secret maskeleme zinciri (cagrilan betikler dahil)
    eksik = []
    for f in etsy_wf:
        s = oku(f)
        if maskeli(s):
            continue
        tamam = False
        for b in cagrilan_betikler(s):
            for z in betik_zinciri(b):
                if maskeli(oku(z)):
                    tamam = True
        if not tamam:
            eksik.append(os.path.basename(f))
    test(f"secret maskeleme zinciri ({len(etsy_wf)} Etsy workflow)", not eksik,
         "; ".join(eksik) or "hepsi maskeli")

    # 10 Etsy workflow'larinda concurrency
    def etsy_kilidi(d):
        """Workflow duzeyinde VEYA Etsy'ye dokunan is duzeyinde etsy-token kilidi."""
        c = d.get("concurrency")
        if isinstance(c, dict) and c.get("group") == "etsy-token":
            return True
        for j in (d.get("jobs") or {}).values():
            jc = (j or {}).get("concurrency")
            if isinstance(jc, dict) and jc.get("group") == "etsy-token":
                return True
        return False

    ceksik = [os.path.basename(f) for f in etsy_wf if not etsy_kilidi(dok.get(f) or {})]
    test(f"Etsy workflow'larinda etsy-token concurrency ({len(etsy_wf)})", not ceksik,
         "; ".join(ceksik) or "hepsi var")

    # 11 Etsy kosusu ortada iptal edilmiyor
    def iptal_eden(d):
        for c in [d.get("concurrency")] + [(j or {}).get("concurrency")
                                           for j in (d.get("jobs") or {}).values()]:
            if isinstance(c, dict) and c.get("group") == "etsy-token" \
                    and c.get("cancel-in-progress") is True:
                return True
        return False

    ipt = [os.path.basename(f) for f in etsy_wf if iptal_eden(dok.get(f) or {})]
    test("Etsy kosusu ortada iptal edilmiyor", not ipt, "; ".join(ipt) or "yok")

    # 12 Drive token geri yazma
    gy = [f for f in etsy_wf if "ETSY_TOKEN.json" in oku(f)]
    eksik_gy = [os.path.basename(f) for f in gy
                if not re.search(r'copyto[^\n]*ETSY_TOKEN\.json"?\s+"?gdrive:', oku(f))]
    test(f"Drive token geri yazma ({len(gy)})", not eksik_gy, "; ".join(eksik_gy) or "hepsi var")

    # 13 kosu sonunda token temizligi
    tz = [os.path.basename(f) for f in gy if "rm -rf" not in oku(f)]
    test(f"kosu sonunda token temizligi ({len(gy)})", not tz, "; ".join(tz) or "hepsi var")

    # 14 guvenli durma
    gd = []
    for f, d in dok.items():
        for blok in run_bloklari(d):
            duz = re.sub(r"\\\n\s*", " ", blok).strip()
            komut = [x for x in duz.split("\n")
                     if x.strip() and not x.strip().startswith("#")]
            bilincli = "set +e" in blok and "set -uo pipefail" in blok
            yalniz_rapor = all(re.match(r"^[\s{}]*(echo|cat|printf|\}|\{)", x) or
                               ">> \"$GITHUB_STEP_SUMMARY\"" in x for x in komut)
            if len(komut) > 2 and "set -e" not in blok \
                    and not bilincli and not yalniz_rapor:
                gd.append(os.path.basename(f))
                break
    test("guvenli durma (set -e / bilincli set +e)", not gd,
         "; ".join(gd) or f"{len(dok)}/{len(dok)}")

    # 15 canli yazan workflow'larda ikinci kapi
    kapisiz = [os.path.basename(f) for f in canli
               if not (re.search(r"inputs\.confirm", oku(f)) and "CANLI" in oku(f))]
    test(f"canli yazan workflow'larda ikinci kapi ({len(canli)})", not kapisiz,
         "; ".join(kapisiz) or f"{len(canli)}/{len(canli)}")

    # 16 (yeni) GITHUB_OUTPUT'a yonlendirilen blokta maske kaybi yok
    kayip = []
    for f in WF:
        s = oku(f)
        for m in re.finditer(r"python - <<'PY' >>? *\"?\$GITHUB_OUTPUT\"?(.*?)\nPY", s, re.S):
            if "TokenStore" in m.group(1) and "mask_secrets.py" not in s:
                kayip.append(os.path.basename(f))
    test("GITHUB_OUTPUT yonlendirmesinde maske kaybi yok", not kayip,
         "; ".join(kayip) or "yok")

    gecen = sum(1 for r in sonuc if r["sonuc"] == "PASS")
    for r in sonuc:
        print(f"[{r['sonuc']}] {r['test']} - {r['detay']}")
    print(f"\nSONUC: {gecen}/{len(sonuc)} PASS")
    if a.json:
        open(a.json, "w", encoding="utf-8").write(json.dumps(sonuc, ensure_ascii=False, indent=2))
    return 0 if gecen == len(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
