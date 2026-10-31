#!/usr/bin/env python3
"""Workflow YAML'larini ve IS_0025 salt-okur/log sozlesmesini denetle."""

import os
from pathlib import Path
import subprocess

try:
    import yaml
except ModuleNotFoundError:  # Yerel/yalin konteynerlerde Ruby stdlib YAML kullanilir.
    yaml = None


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
# 26 Eyl: getListingVariationImages canli olcumde x-api-key ile 401 verdi -> varyasyon-canli OAuth + etsy-token kilidinde kalir.
PUBLIC_AUDITS = ("gorsel-denetim.yml",)


def main() -> int:
    files = sorted(WORKFLOWS.glob("*.yml"))
    assert files, "workflow bulunamadi"
    for path in files:
        if yaml is not None:
            with path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream)
            assert isinstance(data, dict), f"{path.name}: kok mapping degil"
            assert data.get("jobs"), f"{path.name}: jobs yok"
        else:
            subprocess.run(
                ["ruby", "-e", "require 'yaml'; d=YAML.load_file(ARGV[0]); abort 'jobs yok' unless d['jobs']", str(path)],
                check=True,
            )

    for name in PUBLIC_AUDITS:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "group: etsy-token" not in text, f"{name}: salt-okur is token kilidinde"
        assert "ETSY_TOKEN.json" not in text, f"{name}: salt-okur is OAuth token okuyor"
        assert "2>&1 | tee _log" in text and "pipefail" in text, f"{name}: ana log eksik"
        assert "tail -n 150" in text and "TEMP/LOGS" in text, f"{name}: hata logu eksik"
        assert "_OZET.md" in text, f"{name}: ozet logu eksik"
    visual = (WORKFLOWS / "gorsel-denetim.yml").read_text(encoding="utf-8")
    assert "CSV: $([ -f" in visual and "FAIL gorseli: $([ -f" in visual, "gorsel-denetim: eksik dosya ozeti yok"
    assert "2>> \"$log\"" in visual and "YUKLEME HATASI" in visual, "gorsel-denetim: yukleme hata logu yok"
    router = (WORKFLOWS / "pod-order-router.yml").read_text(encoding="utf-8")
    assert "TEMP/SIPARIS_ONAY/${R_SUBMIT}" in router and "ONAYLAR.json" in router, "submit onay indirmiyor"
    assert "siparis_onay.py hazirla" in router and "rclone copyto \"$uzak\"" in router, "paket onaya hazirlanmiyor"
    onay = (WORKFLOWS / "siparis-onay-yaz.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in onay and "siparis_onay.py onayla" in onay, "onay workflow sozlesmesi eksik"
    assert "kilit_bekle.py --grup onay-defteri" in onay and "actions: read" in onay, "defter yarisi korunmuyor"
    assert "concurrency:" not in onay, "onay-yaz concurrency grubu ortadaki kosuyu iptal eder"
    assert "printf '{}" not in onay and "onay_defteri.py oku" in onay and "onay_defteri.py yaz" in onay, "onay defteri kapisi yok"
    assert onay.index("onay_defteri.py oku") < onay.index("siparis_onay.py onayla") < onay.index("onay_defteri.py yaz") \
        < onay.index("if: ${{ always() }}"), "onay defteri adim sirasi bozuk"
    import sys
    sys.path.insert(0, str(ROOT / "scripts" / "etsy"))
    import kilit_bekle
    onay_wf = ".github/workflows/siparis-onay-yaz.yml"
    assert kilit_bekle.kilit_kumesi(str(ROOT), "onay-defteri") == {onay_wf}, "onay-defteri kumesi yalniz onay-yaz olmali"
    assert onay_wf not in kilit_bekle.kilit_kumesi(str(ROOT)), "onay-yaz Etsy kilit kumesine girmemeli"
    # 26 Eki (Serdar onayi): durum dosyasi kapilari; bos varsayilanla devam yok, okuma -> is -> yazma sirasi
    for wf, oku_, yaz_, eski in (
            ("pod-order-router.yml", "durum_dosyasi.py oku --uzak \"gdrive:ASTROLOVE/TEMP/POD_ORDERS_STATE.csv\"",
             "durum_dosyasi.py yaz --uzak \"gdrive:ASTROLOVE/TEMP/POD_ORDERS_STATE.csv\"", "STATE yok; yeni baslar"),
            ("kupa-siparis.yml", "durum_dosyasi.py oku --uzak \"gdrive:ASTROLOVE/$HEDEF/STATE.csv\"",
             "durum_dosyasi.py yaz --uzak \"gdrive:ASTROLOVE/$HEDEF/STATE.csv\"", "STATE yok; yeni baslar"),
            ("drive-satir-ekle.yml", "durum_dosyasi.py oku --uzak \"gdrive:ASTROLOVE/$DOSYA\"",
             "durum_dosyasi.py yaz --uzak \"gdrive:ASTROLOVE/$DOSYA\"", ": > _d.md"),
            ("galeri-77-yukle.yml", "durum_dosyasi.py oku --uzak \"$T/GALERI_YAYIN/ILERLEME.json\"",
             "durum_dosyasi.py yaz --uzak \"gdrive:ASTROLOVE/TEMP/GALERI_YAYIN/ILERLEME.json\"", "echo '{\"ilanlar\": {}}'")):
        t = (WORKFLOWS / wf).read_text(encoding="utf-8")
        assert eski not in t, f"{wf}: bos varsayilan geri geldi"
        assert oku_ in t and yaz_ in t and t.index(oku_) < t.index(yaz_), f"{wf}: durum kapisi / sira eksik"
    dse = (WORKFLOWS / "drive-satir-ekle.yml").read_text(encoding="utf-8")
    assert "concurrency:" not in dse and "kilit_bekle.py --grup drive-satir-ekle" in dse, "drive-satir-ekle sira kilidi yok"
    assert kilit_bekle.kilit_kumesi(str(ROOT), "drive-satir-ekle") == {".github/workflows/drive-satir-ekle.yml"}
    assert ".github/workflows/drive-satir-ekle.yml" not in kilit_bekle.kilit_kumesi(str(ROOT)), "drive-satir-ekle Etsy kumesinde"
    # 26 Eki (Serdar onayi): galeri v10 yukleyicisi; Drive girdileri ve durum okumasi Etsy kilidinden ONCE, yazma onay + plan ile
    gv = (WORKFLOWS / "galeri-v10-yukle.yml").read_text(encoding="utf-8")
    assert ".github/workflows/galeri-v10-yukle.yml" in kilit_bekle.kilit_kumesi(str(ROOT)), "galeri-v10-yukle Etsy kilidinde degil"
    assert "concurrency:" not in gv and "actions: read" in gv, "galeri-v10-yukle kilit sozlesmesi"
    kilit = gv.index("python3 scripts/etsy/kilit_bekle.py")
    for x in ("durum_dosyasi.py oku --uzak \"$O/DEVAM.json\"", "durum_dosyasi.py oku --uzak \"$O/ILERLEME.json\"",
              "durum_dosyasi.py oku --uzak \"$O/SONUC.csv\""):   # durum okumasi kilitten SONRA (inceleme 26 Eki: eski durumla yazim yok)
        assert x in gv and kilit < gv.index(x) < gv.index("python3 scripts/kapak78/galeri_v10_yukle.py"), f"galeri-v10-yukle: {x}"
    for x in ("rclone lsjson -R \"$Y\"", "rclone copy \"$T/POSTER_GALERI_V10/$GD\"",
              "rclone copy \"$T/POSTER_KAPAK_V10/20261026_153710\"", "--files-from _work/yedek_kart.txt", "python3 scripts/kapak78/galeri_v10_liste.py"):
        assert x in gv and gv.index(x) < kilit, f"galeri-v10-yukle: kilitten once degil: {x}"
    assert kilit < gv.index("rclone copyto \"$T/ETSY_TOKEN.json\" _work") < gv.index("python3 scripts/kapak78/galeri_v10_yukle.py") \
        < gv.index("python3 scripts/ops/durum_dosyasi.py yaz"), "galeri-v10-yukle adim sirasi"
    assert "default: \"true\"" in gv and "[ \"$ONAY\" = GALERI_V10 ]" in gv and "plan_damga" in gv, "galeri-v10-yukle yazim kapisi"
    # 26 Eki (Merkez): video v7 yukleyicisi; Drive girdileri + eski video yedegi kilitten ONCE, token + ILERLEME kilitten SONRA
    vv = (WORKFLOWS / "video-v7-yukle.yml").read_text(encoding="utf-8")
    assert ".github/workflows/video-v7-yukle.yml" in kilit_bekle.kilit_kumesi(str(ROOT)), "video-v7-yukle Etsy kilidinde degil"
    assert "concurrency:" not in vv and "actions: read" in vv and "schedule" not in vv, "video-v7-yukle kilit sozlesmesi"
    kilit = vv.index("python3 scripts/etsy/kilit_bekle.py")
    kos = vv.index("python3 scripts/etsy/video_yukle_78.py")
    for x in ("rclone copyto \"$Y/KURU_${PD}/PLAN.json\"", "rclone copy \"$V/BIRLESIK_${BD}\"", "g = requests.get(v[\"url\"]",
              "VIDEO_V7_YEDEK_${PD}\" --immutable"):
        assert x in vv and vv.index(x) < kilit, f"video-v7-yukle: kilitten once degil: {x}"
    for x in ("rclone copyto \"gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json\" _work", "durum_dosyasi.py oku --uzak \"$G/ILERLEME.json\""):
        assert x in vv and kilit < vv.index(x) < kos, f"video-v7-yukle: kilitten sonra / kosudan once degil: {x}"
    assert "--ilk-kayit-izni" not in vv and "--surum v7" in vv and "updateListing YOK" in vv, "video-v7-yukle galeri / surum"
    assert "kuru: {description: \"true = yazma yok (plan); false = yazim\", required: true, default: \"true\"}" in vv \
        and "[ \"$ONAY\" = VIDEO_V7_YUKLE ]" in vv, "video-v7-yukle yazim kapisi"
    # 27 Eki (Merkez, plan v3 adim 2-8): YD kapak is akislari (yd-kapak dalindan 30 Eki main'e). Tasima ayri kilit grubu yd-kapak;
    # yedek / QC Etsy'siz ve kilitsiz; yukleyici Etsy kilidinde, Drive girdileri + yedek kapisi kilitten ONCE, cdn yedegi kilit altinda yok
    tasi = (WORKFLOWS / "yd-kapak-tasi.yml").read_text(encoding="utf-8")
    assert kilit_bekle.kilit_kumesi(str(ROOT), "yd-kapak") == {".github/workflows/yd-kapak-tasi.yml"}, "yd-kapak kumesi yalniz tasima"
    assert ".github/workflows/yd-kapak-tasi.yml" not in kilit_bekle.kilit_kumesi(str(ROOT)), "yd-kapak-tasi Etsy kumesinde"
    assert "--grup yd-kapak --zaman-asimi-dk 15" in tasi and "--urun yd" in tasi and "--immutable" in tasi and "concurrency:" not in tasi
    for wf in ("yd-kapak-yedek.yml", "yd-kapak-qc.yml"):
        t = (WORKFLOWS / wf).read_text(encoding="utf-8")
        assert "ETSY_TOKEN" not in t and "ETSY_API_KEY" not in t and "kilit_bekle" not in t, f"{wf}: Etsy'ye dokunmamali"
    yy = (WORKFLOWS / "yd-kapak-yukle.yml").read_text(encoding="utf-8")
    assert ".github/workflows/yd-kapak-yukle.yml" in kilit_bekle.kilit_kumesi(str(ROOT)), "yd-kapak-yukle Etsy kilidinde degil"
    assert "concurrency:" not in yy and "actions: read" in yy and "schedule" not in yy, "yd-kapak-yukle kilit sozlesmesi"
    kilit = yy.index("python3 scripts/etsy/kilit_bekle.py")
    # Serdar 31 Eki karar 6b (CLAUDE.md KILIT SURESI istisnasi): kilit is akisinin en basinda (checkout'tan hemen sonra), girdi indirme kilit
    # altinda en fazla 15 dk; zaman butcesi kilit anindan (KILIT_T0) sayilir, azami_dk <= 100 (bekleyen Etsy kosulari en fazla 120 dk bekler)
    assert yy.index("uses: actions/checkout@v4") < kilit < yy.index("name: rclone.conf") < yy.index("rclone copy \"$K\" _in/kapak"), \
        "yd-kapak-yukle: kilit en basta degil"
    for x in ("rclone copy \"$K\" _in/kapak", "rclone copyto \"$K/QC_$QD/QC_RAPOR.json\"", "rclone copy \"$T/$EN/HAM\"",
              "rclone lsjson -R \"$Y\"", "python3 scripts/kapak78/yd_liste_uret.py liste"):
        assert x in yy and kilit < yy.index(x), f"yd-kapak-yukle: kilitten once: {x}"
    assert "KILIT_T0=$(date +%s)" in yy and "AZE=$(( AZ - GEC ))" in yy and "--azami-dk \"$AZE\"" in yy and "-le 100" in yy \
        and "timeout-minutes: 15" in yy, "yd-kapak-yukle: kilit suresi butcesi"
    assert kilit_bekle.ZAMAN_ASIMI_DK >= 100 + 15, "kilit bekleme siniri butceden kisa"
    import subprocess, time as _t
    sn = [x for x in yy.splitlines() if "GEC=$((" in x or x.strip().startswith('[ "$AZE" -ge 1 ]')]
    betik = "\n".join(x.strip() for x in sn).replace('echo "KOD=1" >> "$GITHUB_ENV"; ', "") + '\necho "AZE=$AZE"'
    for gecen, bek_rc, bek in ((5, 0, "AZE=85"), (95, 1, "")):   # azami_dk 90: 5 dk sonra 85 dk butce; 95 dk sonra ilan baslamaz
        r = subprocess.run(["bash", "-c", betik], capture_output=True, text=True,
                           env={"KILIT_T0": str(int(_t.time()) - gecen * 60), "AZ": "90", "PATH": os.environ.get("PATH", "")})
        assert r.returncode == bek_rc and bek in r.stdout, f"yd-kapak-yukle kilit butcesi ({gecen} dk): {r.returncode} {r.stdout} {r.stderr}"
    for x in ("durum_dosyasi.py oku --uzak \"$O/DEVAM.json\"", "durum_dosyasi.py oku --uzak \"$O/ILERLEME.json\""):
        assert x in yy and kilit < yy.index(x) < yy.index("python3 scripts/kapak78/yd_kapak_yukle.py"), f"yd-kapak-yukle: {x}"
    assert "default: \"true\"" in yy and "[ \"$ONAY\" = YD_KAPAK ]" in yy and "plan_damga" in yy, "yd-kapak-yukle yazim kapisi"
    # 30 Eki inceleme (8d8c66a8, KILIT SURESI): kupa galeri 78 hazirlik (kaynak + CDN yedegi) ayri, kilitsiz ve Etsy'siz is akisi;
    # yukleyici Etsy kilidinde, yalniz partinin dosyalari kilitten once, durum + token kilitten sonra
    kh = (WORKFLOWS / "kupa-galeri78-hazir.yml").read_text(encoding="utf-8")
    assert "ETSY_" not in kh and "kilit_bekle" not in kh and "--immutable" in kh and "lsjson -R --hash" in kh, "kupa-galeri78-hazir"
    assert ".github/workflows/kupa-galeri78-hazir.yml" not in kilit_bekle.kilit_kumesi(str(ROOT)), "kupa-galeri78-hazir Etsy kumesinde"
    ky = (WORKFLOWS / "kupa-galeri78-yukle.yml").read_text(encoding="utf-8")
    assert ".github/workflows/kupa-galeri78-yukle.yml" in kilit_bekle.kilit_kumesi(str(ROOT)), "kupa-galeri78-yukle Etsy kilidinde degil"
    assert "concurrency:" not in ky and "actions: read" in ky and "schedule" not in ky and "needs:" not in ky, "kupa-galeri78-yukle kilit"
    assert "--immutable" not in ky and "kupa_galeri78.py yedek" not in ky, "kupa-galeri78-yukle: yedek kilitli kosuda"
    kilit = ky.index("python3 scripts/etsy/kilit_bekle.py")
    assert ky.index("--out _work/parti_on") < kilit < ky.index("durum_dosyasi.py oku --uzak \"$O/DEVAM.json\"") \
        < ky.index("rclone copyto \"$T/ETSY_TOKEN.json\" _work") < ky.index("python3 scripts/etsy/kupa_galeri78.py yaz"), "kupa-galeri78-yukle sira"
    assert ky.count("--devam-hedef-kok \"$O/DEVAM_ILAN/$PD\"") == 2 and "[ -z \"$PARTI\" ]" in ky, "kupa-galeri78-yukle DEVAM / parti"
    # #61 (30 Eki): galeri-v11-dogrula yalniz kendi rapor klasorune yazar; okuma yedegi POSTER_GALERI_V11_YEDEK degismez
    import shlex
    dg = (WORKFLOWS / "galeri-v11-dogrula.yml").read_text(encoding="utf-8")
    hedef = []
    for s in dg.splitlines():
        if "rclone " in s and not s.strip().startswith("#"):
            a = shlex.split(s.split("rclone ", 1)[1], comments=True)
            if a and a[0] in ("copy", "copyto", "sync", "move", "moveto") and len(a) > 2:
                hedef.append(a[2])
            elif a and a[0] in ("delete", "deletefile", "purge", "rmdir", "touch") and len(a) > 1:
                hedef.append(a[1])
    uzak = [h for h in hedef if h.startswith(("$T/", "gdrive:"))]
    assert uzak == ["$T/POSTER_GALERI_V11_YUKLE/DOGRULA/${GITHUB_RUN_ID}"], f"galeri-v11-dogrula: rapor klasoru disina yazim {uzak}"
    print(f"PASS: {len(files)} workflow YAML, {len(PUBLIC_AUDITS)} public denetim sozlesmesi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
