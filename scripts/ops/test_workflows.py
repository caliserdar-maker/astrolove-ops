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
    assert "KILIT_T0=$(date +%s)" in yy and "AZE=$(( AZ - GEC ))" in yy and "--azami-dk \"$AZE\"" in yy, "yd-kapak-yukle: kilit suresi butcesi"
    adim = {x.split("\n", 1)[0].strip(): x for x in yy.split("\n      - name: ")[1:]}           # adim bazinda (ad -> blok)
    ind = next(v for k, v in adim.items() if k.startswith("Girdiler (Drive, kilit altinda"))
    yk = adim["YD kapak"]
    assert "timeout-minutes: 15" in ind and "rclone copy \"$K\" _in/kapak" in ind, "yd-kapak-yukle: indirme adimi 15 dk"
    assert "timeout-minutes: 95" in yk and "AZE=$(( AZ - GEC ))" in yk, "yd-kapak-yukle: YD kapak adimi 95 dk + butce"
    assert '[ "$AZ" -le 75 ]' in yy and 'default: "75"' in adim.get("Girdi kapisi", yy) + yy, "yd-kapak-yukle: azami_dk <= 75"
    assert 15 + 95 + 10 <= kilit_bekle.ZAMAN_ASIMI_DK, "kilit tutma ust siniri (indirme + YD kapak + kurulum/kapanis 10) bekleme sinirini asiyor"
    import subprocess, time as _t
    sn = [x for x in yy.splitlines() if "GEC=$((" in x or x.strip().startswith('[ "$AZE" -ge 1 ]')]
    betik = "\n".join(x.strip() for x in sn).replace('echo "KOD=1" >> "$GITHUB_ENV"; ', "") + '\necho "AZE=$AZE"'
    for gecen, bek_rc, bek in ((5, 0, "AZE=70"), (74, 0, "AZE=1"), (75, 1, ""), (95, 1, "")):   # azami_dk 75; sinir durumlari dahil
        r = subprocess.run(["bash", "-c", betik], capture_output=True, text=True,
                           env={"KILIT_T0": str(int(_t.time()) - gecen * 60 - 1), "AZ": "75", "PATH": os.environ.get("PATH", "")})
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
    import json as _j, tempfile as _tf
    # 6 Kas (Serdar, kalan 77 gruplar 5/20/25/26): p1g-w05-yukle GRUP 1 YALNIZ KURU. Iki kapi (Onay kapisi token oncesi + token adiminda
    # KAPI2) ayni kural: kip kuru + sadece = GRUP 1 dizesi birebir + onay W05-KURU-GRUP1; kip yaz HICBIR girdiyle kabul edilmez.
    pw = (WORKFLOWS / "p1g-w05-yukle.yml").read_text(encoding="utf-8")   # yaml modulu olmadan (yerel Ruby yolu) da calisir
    ps = pw.splitlines(); i0 = ps.index("      - name: Onay kapisi"); i1 = next(i for i in range(i0, len(ps)) if ps[i].strip() == "run: |")
    i2 = next(i for i in range(i1 + 1, len(ps)) if ps[i].startswith("      - "))
    k1 = "\n".join(x[10:] for x in ps[i1 + 1:i2])
    k2 = "\n".join(x.strip() for x in ps if x.rstrip().endswith("# KAPI2"))
    assert k2.count("# KAPI2") == 2, "p1g-w05-yukle: KAPI2 satirlari"
    G1 = "4570110121,4570110641,4570125580,4570126104,4570112095"
    D = "42223863686_0e95c567bc1b"
    durum = (("kuru", G1, "W05-KURU-GRUP1", "", 0),
             ("yaz", G1, "W05-KURU-GRUP1", "", 1), ("yaz", G1, "W05-YAZ-GRUP1", D, 1), ("yaz", G1, f"W05-YAZ-{G1}", D, 1),
             ("yaz", "4570155846", "W05-YAZ-4570155846", D, 1), ("yaz", "4570143815", "W05-YAZ-4570143815", D, 1),
             ("kuru", ",".join(G1.split(",")[:4]), "W05-KURU-GRUP1", "", 1), ("kuru", G1 + ",4570155846", "W05-KURU-GRUP1", "", 1),
             ("kuru", ",".join(reversed(G1.split(","))), "W05-KURU-GRUP1", "", 1), ("kuru", G1 + ",4570112095", "W05-KURU-GRUP1", "", 1),
             ("kuru", "4570110121,4570110121,4570125580,4570126104,4570112095", "W05-KURU-GRUP1", "", 1),
             ("kuru", "4570155846", "W05-KURU-GRUP1", "", 1), ("kuru", "4570143815", "W05-KURU-GRUP1", "", 1),
             ("kuru", "4570155846", "W05-KURU-4570155846", "", 1), ("kuru", G1, f"W05-KURU-{G1}", "", 1), ("kuru", G1, "W05-KURU-GRUP2", "", 1),
             ("kuru", G1, "", "", 1), ("kuru", "", "W05-KURU-GRUP1", "", 1), ("kuru", G1 + " ", "W05-KURU-GRUP1", "", 1),
             ("kuru", G1.replace(",", ", "), "W05-KURU-GRUP1", "", 1), ("sil", G1, "W05-KURU-GRUP1", "", 1), ("", G1, "W05-KURU-GRUP1", "", 1))
    for kip, sad, onay, dam, bek in durum:
        e = {"KIP": kip, "SADECE": sad, "ONAY": onay, "DAMGA": dam, "PATH": os.environ.get("PATH", "")}
        r1 = subprocess.run(["bash", "-c", k1], capture_output=True, text=True, env=e)
        assert (r1.returncode == 0) == (bek == 0), f"p1g-w05-yukle Onay kapisi {kip} {sad} {onay} {dam!r}: rc {r1.returncode} {r1.stdout}"
        bek2 = 0 if (kip == "kuru" and sad == G1) else 1   # KAPI2 onaya bakmaz: kip + liste
        r2 = subprocess.run(["bash", "-c", "set -euo pipefail\n" + k2], capture_output=True, text=True, env=e, cwd=str(ROOT))
        assert (r2.returncode == 0) == (bek2 == 0), f"p1g-w05-yukle KAPI2 {kip} {sad} {dam!r}: rc {r2.returncode} {r2.stdout} {r2.stderr}"
    # sira: Onay kapisi token oncesi; KAPI2 token adiminda ilan / cift eslesmesinden, kart ve GALERI.json indirmeden ONCE; token indirme
    # kapilar + girdilerden SONRA ve betikten once; betik adimi ayni inputs.sadece / kip / onay'i env ile alir
    tk = next(i for i, x in enumerate(ps) if x.strip() == "- name: Token + girdiler (kart, plan)")
    bt = next(i for i, x in enumerate(ps) if x.strip() == "- name: W05 degisim (betik)")
    k2s = [i for i, x in enumerate(ps) if x.rstrip().endswith("# KAPI2")]
    eslem = next(i for i, x in enumerate(ps) if "python3 - \"$SADECE\" > _work/ilan_cift.txt <<'PY'" in x)
    kart = next(i for i, x in enumerate(ps) if "rclone copyto \"gdrive:$P1G/${CIFT}_W05_SUREC.jpg\"" in x)
    gal = next(i for i, x in enumerate(ps) if "rclone copyto \"gdrive:$YEDEK/${ID}_${CIFT}/GALERI.json\"" in x)
    tok = [i for i, x in enumerate(ps) if "rclone copyto \"gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json\" _work/ETSY_TOKEN.json" in x]
    assert len(tok) == 1, "p1g-w05-yukle: token tek yerde indirilir"
    ck = next(i for i, x in enumerate(ps) if x.strip() == "- uses: actions/checkout@v4")
    assert i0 < ck < tk < min(k2s) and max(k2s) < eslem < kart < gal < tok[0] < bt, \
        "p1g-w05-yukle: kapi / girdi / token sirasi"
    benv = "\n".join(ps[bt:bt + 12])
    for x in ("KIP: ${{ inputs.kip }}", "SADECE: ${{ inputs.sadece }}", "ONAY: ${{ inputs.onay }}"):
        assert x in benv, f"p1g-w05-yukle betik adimi env: {x}"
    assert '--sadece "$SADECE"' in pw and '--onay "$ONAY"' in pw and "--plan-damga \"${PLAN_DAMGA:?}\"" in pw, "p1g-w05-yukle betik argumanlari"
    assert "${{ inputs." not in "\n".join(x for x in ps if not x.strip().startswith(("KIP:", "SADECE:", "ONAY:", "DAMGA:", "GH_TOKEN:"))), \
        "p1g-w05-yukle: inputs run icine gomulu (yalniz env ile)"
    def _yigin(bas):   # token adimindaki heredoc Python parcasi (10 bosluk girinti)
        a = next(i for i, x in enumerate(ps) if bas in x)
        b = next(i for i in range(a + 1, len(ps)) if ps[i].strip() == "PY")
        return "\n".join(x[10:] for x in ps[a + 1:b])
    # ilan / cift eslesmesi (pod78_ids.csv): liste sirasi korunur; bilinmeyen, tekrar, bos -> DUR
    es = _yigin("python3 - \"$SADECE\" > _work/ilan_cift.txt <<'PY'")
    r4 = subprocess.run(["python3", "-", G1], input=es, capture_output=True, text=True, cwd=str(ROOT))
    assert r4.returncode == 0 and [x.split()[0] for x in r4.stdout.splitlines()] == G1.split(",") and \
        [x.split()[1] for x in r4.stdout.splitlines()] == ["AQUARIUS_AQUARIUS", "AQUARIUS_ARIES", "AQUARIUS_CANCER", "AQUARIUS_CAPRICORN",
                                                           "AQUARIUS_GEMINI"], f"p1g-w05-yukle eslesme GRUP 1: {r4.stdout} {r4.stderr}"
    for kotu in ("4570110121,9999999999", "4570110121,4570110121", "", "4570110121,,4570110641"):
        r5 = subprocess.run(["python3", "-", kotu], input=es, capture_output=True, text=True, cwd=str(ROOT))
        assert r5.returncode != 0, f"p1g-w05-yukle eslesme bilinen FAIL {kotu!r}: {r5.stdout}"
    # inceleme 6 Kas: token adimi uctan uca, sahte rclone ile (ag yok). Tam liste: 5 kart + 5 GALERI.json + cift.csv liste sirasiyla, plan
    # sahte MANIFEST'le BLOK -> adim durur, ::error:: plan BLOK, token INMEZ. Eksik kart / GALERI.json: adim durur, sonraki ilanlar islenmez,
    # token INMEZ.
    a0 = next(i for i, x in enumerate(ps) if x.strip() == "- name: Token + girdiler (kart, plan)")
    a1 = next(i for i in range(a0, len(ps)) if ps[i].strip() == "run: |"); a2 = next(i for i in range(a1 + 1, len(ps)) if ps[i].startswith("      - "))
    adim = "\n".join(x[10:] for x in ps[a1 + 1:a2])
    ciftler = ["AQUARIUS_AQUARIUS", "AQUARIUS_ARIES", "AQUARIUS_CANCER", "AQUARIUS_CAPRICORN", "AQUARIUS_GEMINI"]

    def _uc(eksik=None):
        with _tf.TemporaryDirectory() as td:
            td = Path(td); (td / "bin").mkdir(); (td / "w").mkdir()
            (td / "bin" / "rclone").write_text('#!/bin/bash\n[ "$1" = copyto ] || exit 3\ns="${2#gdrive:}"; [ -f "$FAKE/$s" ] || exit 3\n'
                                               'mkdir -p "$(dirname "$3")"; cp "$FAKE/$s" "$3"\n'); (td / "bin" / "rclone").chmod(0o755)
            fk = td / "fake" / "ASTROLOVE" / "TEMP"; p1 = fk / "P1G_W05_20261106_090016"; yd = fk / "POSTER_GALERI_V11_YEDEK" / "20261106_090016"
            p1.mkdir(parents=True); (p1 / "MANIFEST_W05.csv").write_text("ilan,cift\n"); (fk / "ETSY_TOKEN.json").write_text("{}")
            for i, c in zip(G1.split(","), ciftler):
                if eksik != ("kart", c):
                    (p1 / f"{c}_W05_SUREC.jpg").write_text("k")
                if eksik != ("galeri", c):
                    (yd / f"{i}_{c}").mkdir(parents=True); (yd / f"{i}_{c}" / "GALERI.json").write_text("{}")
            for d in ("scripts", "data"):
                (td / "w" / d).symlink_to(ROOT / d)
            e = {"PATH": f"{td / 'bin'}:{os.environ.get('PATH', '')}", "FAKE": str(td / "fake"), "P1G": "ASTROLOVE/TEMP/P1G_W05_20261106_090016",
                 "YEDEK": "ASTROLOVE/TEMP/POSTER_GALERI_V11_YEDEK/20261106_090016", "KIP": "kuru", "SADECE": G1, "DAMGA": "",
                 "GITHUB_ENV": str(td / "genv")}
            r6 = subprocess.run(["bash", "-e", "-c", adim], capture_output=True, text=True, env=e, cwd=str(td / "w"), stdin=subprocess.DEVNULL)
            w = td / "w"
            cc = (w / "_work" / "cift.csv").read_text().splitlines() if (w / "_work" / "cift.csv").exists() else []
            return (r6.returncode, r6.stdout + r6.stderr, sorted(x.name for x in (w / "_kart").iterdir()) if (w / "_kart").exists() else [],
                    sorted(x.name for x in (w / "_canli").iterdir()) if (w / "_canli").exists() else [], [x.split(",")[0] for x in cc[1:]],
                    (w / "_work" / "ETSY_TOKEN.json").exists())
    rc6, ci6, kart6, can6, cc6, tok6 = _uc()
    assert rc6 != 0 and "plan BLOK" in ci6 and len(kart6) == 5 and len(can6) == 5 and cc6 == G1.split(",") and not tok6, \
        f"p1g-w05-yukle uctan uca tam liste: rc {rc6} kart {len(kart6)} canli {len(can6)} cift {cc6} token {tok6} {ci6[-300:]}"
    for ek in (("kart", "AQUARIUS_CANCER"), ("galeri", "AQUARIUS_CANCER")):
        rc7, ci7, kart7, can7, cc7, tok7 = _uc(ek)
        assert rc7 != 0 and "indirilemedi (4570125580 AQUARIUS_CANCER)" in ci7 and not tok7 and not cc7 \
            and not any("CAPRICORN" in x or "GEMINI" in x for x in kart7 + can7), f"p1g-w05-yukle uctan uca eksik {ek}: rc {rc7} {kart7} {can7} {ci7[-300:]}"
    # yaz yolunun kuru RAPOR Python kapisi listeye genel (bu commit'te kapi yuzunden calismaz): sahte KURU_RAPOR.json ile PASS / FAIL
    kod = _yigin("python3 - \"$DAMGA\" \"$SADECE\" <<'PY'")
    L1 = [{"ilan": i} for i in G1.split(",")]
    iyi = dict(mod="kuru", plan_damga=D, sayilar={"HAZIR": 5}, ilanlar=L1)
    for ad, rap, bek in (("iyi", iyi, 0), ("mod yazim", dict(iyi, mod="yazim"), 1), ("baska damga", dict(iyi, plan_damga=D[:-1] + "c"), 1),
                         ("HAZIR 4", dict(iyi, sayilar={"HAZIR": 4}), 1), ("HAZIR 4 + BLOK 1", dict(iyi, sayilar={"HAZIR": 4, "BLOK": 1}), 1),
                         ("HAZIR 1 (eski pilot)", dict(iyi, sayilar={"HAZIR": 1}), 1), ("HAZIR 5 + BLOK 1", dict(iyi, sayilar={"HAZIR": 5, "BLOK": 1}), 1), ("ilan eksik", dict(iyi, ilanlar=L1[:4]), 1),
                         ("ilan sirasi farkli", dict(iyi, ilanlar=L1[::-1]), 1), ("baska ilan", dict(iyi, ilanlar=L1[:4] + [{"ilan": "4570155846"}]), 1)):
        with _tf.TemporaryDirectory() as td:
            Path(td, "_plan").mkdir(); Path(td, "_out").mkdir()
            Path(td, "_plan", "KURU_RAPOR.json").write_text(_j.dumps(rap))
            r3 = subprocess.run(["python3", "-", D, G1], input=kod, capture_output=True, text=True, cwd=td)
            kk = _j.loads(Path(td, "_out", "KURU_KAPI.json").read_text())["kuru_kapisi"]
            assert (r3.returncode == 0) == (bek == 0) and kk == ("PASS" if bek == 0 else "FAIL"), f"p1g-w05-yukle kuru kapisi {ad}: {r3.returncode} {kk}"
    print(f"PASS: {len(files)} workflow YAML, {len(PUBLIC_AUDITS)} public denetim sozlesmesi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
