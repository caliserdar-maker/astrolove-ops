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
    # 7 Kas (Serdar "GRUP 2 evet, Ga evet, Gb evet"; kalan 77 gruplar 5/20/25/26): p1g-w05-yukle GRUP 2 YALNIZ KURU. Iki kapi (Onay kapisi
    # checkout oncesi + token adiminda KAPI2) ayni kural: kip kuru + sadece = GRUP 2 dizesi birebir + onay W05-KURU-GRUP2 + plan_damga BOS +
    # GITHUB_RUN_ATTEMPT 1 + ref main; kip yaz KAPALI. Tek kullanimlik kilit (KILIT1) yalniz kip yaz'da; yaz yolu (KILIT1, ISARET, kuru RAPOR
    # kapisi) olu kod, KAPI2 satirlari cikarilmis adim metniyle testli kalir.
    pw = (WORKFLOWS / "p1g-w05-yukle.yml").read_text(encoding="utf-8")   # yaml modulu olmadan (yerel Ruby yolu) da calisir
    ps = pw.splitlines(); i0 = ps.index("      - name: Onay kapisi"); i1 = next(i for i in range(i0, len(ps)) if ps[i].strip() == "run: |")
    i2 = next(i for i in range(i1 + 1, len(ps)) if ps[i].startswith("      - "))
    k1 = "\n".join(x[10:] for x in ps[i1 + 1:i2])
    k2 = "\n".join(x.strip() for x in ps if x.rstrip().endswith("# KAPI2"))
    assert k2.count("# KAPI2") == 2, "p1g-w05-yukle: KAPI2 satirlari"
    G1 = "4570110121,4570110641,4570125580,4570126104,4570112095"
    D = "42256985849_491eaad0c110"
    Y = "W05-YAZ-GRUP1"
    G2 = ("4570127160,4570113157,4570113675,4570128546,4570114301,4570150148,4570136319,4570151370,4570151950,4570152410,4570152820,"
          "4570031205,4570153208,4570138967,4570154042,4570139913,4570140539,4570141945,4570157258,4570157716")
    Y2 = "W05-KURU-GRUP2"
    g2l = G2.split(",")
    durum = (("kuru", G2, Y2, "", "1", 0),
             ("yaz", G2, Y2, "", "1", 1), ("yaz", G2, "W05-YAZ-GRUP2", D, "1", 1), ("yaz", G2, "W05-YAZ-GRUP2", "", "1", 1),
             ("yaz", G2, f"W05-YAZ-{G2}", D, "1", 1), ("yaz", G1, Y, D, "1", 1), ("yaz", G1, Y, "", "1", 1),
             ("kuru", G2, Y2, D, "1", 1), ("kuru", G2, Y2, "42223863686_0e95c567bc1b", "1", 1), ("kuru", G2, Y2, " ", "1", 1),
             ("kuru", ",".join(g2l[:19]), Y2, "", "1", 1), ("kuru", G2 + ",4570155846", Y2, "", "1", 1),
             ("kuru", ",".join(reversed(g2l)), Y2, "", "1", 1), ("kuru", G2 + "," + g2l[-1], Y2, "", "1", 1),
             ("kuru", ",".join([g2l[0]] + g2l[:19]), Y2, "", "1", 1),
             ("kuru", G1, Y2, "", "1", 1), ("kuru", G1, "W05-KURU-GRUP1", "", "1", 1), ("kuru", "4570155846", Y2, "", "1", 1),
             ("kuru", "4570143815", Y2, "", "1", 1), ("kuru", "", Y2, "", "1", 1),
             ("kuru", G2 + " ", Y2, "", "1", 1), ("kuru", G2.replace(",", ", "), Y2, "", "1", 1),
             ("kuru", G2, "W05-KURU-GRUP1", "", "1", 1), ("kuru", G2, "W05-YAZ-GRUP2", "", "1", 1), ("kuru", G2, "", "", "1", 1),
             ("kuru", G2, f"W05-KURU-{G2}", "", "1", 1), ("kuru", G2, Y2 + " ", "", "1", 1),
             ("kuru", G2, Y2, "", "2", 1), ("kuru", G2, Y2, "", "", 1), ("sil", G2, Y2, "", "1", 1), ("", G2, Y2, "", "1", 1),
             ("kuru", G2, Y2, "", "1R", 1))   # 1R: deneme 1 ama ref main degil
    for kip, sad, onay, dam, den, bek in durum:
        e = {"KIP": kip, "SADECE": sad, "ONAY": onay, "DAMGA": dam, "GITHUB_RUN_ATTEMPT": den.rstrip("R"),
             "GITHUB_REF": "refs/heads/baska" if den.endswith("R") else "refs/heads/main", "PATH": os.environ.get("PATH", "")}
        r1 = subprocess.run(["bash", "-c", k1], capture_output=True, text=True, env=e)
        assert (r1.returncode == 0) == (bek == 0), f"p1g-w05-yukle Onay kapisi {kip} {sad} {onay} {dam!r} {den}: rc {r1.returncode} {r1.stdout}"
        r2 = subprocess.run(["bash", "-c", "set -euo pipefail\n" + k2], capture_output=True, text=True, env=e, cwd=str(ROOT))
        assert (r2.returncode == 0) == (bek == 0), f"p1g-w05-yukle KAPI2 {kip} {sad} {onay} {dam!r} {den}: rc {r2.returncode} {r2.stdout} {r2.stderr}"
    # sira: Onay kapisi checkout oncesi; KAPI2 ve KILIT1 token adiminda eslesme / kart / plan indirmeden ONCE; token kapilar + girdilerden SONRA
    tk = next(i for i, x in enumerate(ps) if x.strip() == "- name: Token + girdiler (kart, plan)")
    bt = next(i for i, x in enumerate(ps) if x.strip() == "- name: W05 degisim (betik)")
    k2s = [i for i, x in enumerate(ps) if x.rstrip().endswith("# KAPI2")]
    kls = [i for i, x in enumerate(ps) if x.rstrip().endswith("# KILIT1")]
    eslem = next(i for i, x in enumerate(ps) if "python3 - \"$SADECE\" > _work/ilan_cift.txt <<'PY'" in x)
    kart = next(i for i, x in enumerate(ps) if "rclone copyto \"gdrive:$P1G/${CIFT}_W05_SUREC.jpg\"" in x)
    plan = next(i for i, x in enumerate(ps) if "rclone copyto \"gdrive:$P1G/PILOT/kuru_${K}/PLAN_W05.json\"" in x)
    tok = [i for i, x in enumerate(ps) if "rclone copyto \"gdrive:ASTROLOVE/TEMP/ETSY_TOKEN.json\" _work/ETSY_TOKEN.json" in x]
    ck = next(i for i, x in enumerate(ps) if x.strip() == "- uses: actions/checkout@v4")
    isr = [i for i, x in enumerate(ps) if x.rstrip().endswith("# ISARET")]
    assert len(tok) == 1 and len(kls) >= 8 and len(isr) == 1, "p1g-w05-yukle: token tek yerde; KILIT1 satirlari; kilit isareti tek yerde"
    assert ps[kls[0]].strip() == 'if [ "$KIP" = yaz ]; then  # KILIT1' and ps[kls[-1]].strip() == "fi  # KILIT1", \
        "p1g-w05-yukle: KILIT1 bloku yalniz kip yaz'da (if / fi)"
    assert i0 < ck < tk < min(k2s) and max(k2s) < min(kls) and max(kls) < eslem < kart < plan < isr[0] < tok[0] < bt, \
        "p1g-w05-yukle: kapi / kilit / girdi / kilit isareti / token sirasi"
    assert 'echo "CIKTI=$P1G/PILOT/${KIP}_${GITHUB_RUN_ID}${E}"' in pw and '"gdrive:${CIKTI:?}/KURU_KAPI.json"' in ps[isr[0]] and \
        '"gdrive:$P1G/PILOT/"' in pw, "p1g-w05-yukle: kilit isareti yolu (CIKTI) = kilidin okudugu PILOT/yaz_*"
    benv = "\n".join(ps[bt:next(i for i in range(bt, len(ps)) if ps[i].strip() == "run: |")])
    for x in ("KIP: ${{ inputs.kip }}", "SADECE: ${{ inputs.sadece }}"):
        assert x in benv, f"p1g-w05-yukle betik adimi env: {x}"
    assert "ONAY:" not in benv and '--onay "$ONAY"' not in pw and '--onay "W05-YAZ-$SADECE"' in pw, "p1g-w05-yukle: betik onayi SADECE'den, ONAY env yok"
    assert '--sadece "$SADECE"' in pw and "--plan-damga \"${PLAN_DAMGA:?}\"" in pw, "p1g-w05-yukle betik argumanlari"
    # betik adimi davranisi (son savunma hatti): sahte python3 argv + W05_KILIT kaydeder. kuru (ve yaz disi her kip): yalniz --kuru,
    # --confirm / --onay / W05_KILIT YOK; yaz: --confirm W05_DEGISTIR --onay W05-YAZ-<SADECE> + W05_KILIT=1
    import tempfile as _tf0
    br = next(i for i in range(bt, len(ps)) if ps[i].strip() == "run: |")
    bs = next(i for i in range(br, len(ps)) if ps[i].strip().startswith("- name:"))
    badim = "\n".join(x[10:] for x in ps[br + 1:bs])
    with _tf0.TemporaryDirectory() as td0:
        td0 = Path(td0); (td0 / "python3").write_text('#!/bin/bash\ncase "$1" in *w05_degistir.py) printf "%s\\n" "$@" > "$BLOG"; '
                                                         'echo "KILIT=${W05_KILIT:-YOK}" >> "$BLOG" ;; *) cat > /dev/null ;; esac\n')
        (td0 / "python3").chmod(0o755)
        for kp in ("kuru", "yaz", "", "sil", "Kuru"):
            bl = td0 / "b.log"
            if bl.exists():
                bl.unlink()
            eb = {"PATH": f"{td0}:{os.environ.get('PATH', '')}", "KIP": kp, "SADECE": G2, "PLAN_DAMGA": "43000000003_abc", "BLOG": str(bl)}
            r8 = subprocess.run(["bash", "-e", "-c", badim], capture_output=True, text=True, env=eb)
            av = bl.read_text().splitlines() if bl.exists() else []
            assert r8.returncode == 0 and av[:2] == ["scripts/kapak78/w05_degistir.py", "etsy"], f"p1g-w05-yukle betik {kp!r}: {r8.stderr} {av}"
            if kp == "yaz":
                assert av[2:6] == ["--confirm", "W05_DEGISTIR", "--onay", f"W05-YAZ-{G2}"] and "--kuru" not in av and av[-1] == "KILIT=1", \
                    f"p1g-w05-yukle betik yaz argv: {av}"
            else:
                assert av[2] == "--kuru" and "--confirm" not in av and "--onay" not in av and av[-1] == "KILIT=YOK", \
                    f"p1g-w05-yukle betik {kp!r}: yalniz --kuru, onay / kilit yok: {av}"
    tenv = "\n".join(ps[tk:next(i for i in range(tk, len(ps)) if ps[i].strip() == "run: |")])
    assert "ONAY: ${{ inputs.onay }}" in tenv and "DAMGA: ${{ inputs.plan_damga }}" in tenv, "p1g-w05-yukle token adimi env (ONAY, DAMGA)"
    assert "${{ inputs." not in "\n".join(x for x in ps if not x.strip().startswith(("KIP:", "SADECE:", "ONAY:", "DAMGA:", "GH_TOKEN:"))), \
        "p1g-w05-yukle: inputs run icine gomulu (yalniz env ile)"

    def _yigin(bas):   # token adimindaki heredoc Python parcasi (10 bosluk girinti)
        a = next(i for i, x in enumerate(ps) if bas in x)
        b = next(i for i in range(a + 1, len(ps)) if ps[i].strip() == "PY")
        return "\n".join(x[10:] for x in ps[a + 1:b])
    es = _yigin("python3 - \"$SADECE\" > _work/ilan_cift.txt <<'PY'")
    r4 = subprocess.run(["python3", "-", G1], input=es, capture_output=True, text=True, cwd=str(ROOT))
    assert r4.returncode == 0 and [x.split()[0] for x in r4.stdout.splitlines()] == G1.split(","), f"p1g-w05-yukle eslesme GRUP 1: {r4.stdout}"
    r4 = subprocess.run(["python3", "-", G2], input=es, capture_output=True, text=True, cwd=str(ROOT))
    g2c = [x.split()[1] for x in r4.stdout.splitlines()]
    assert r4.returncode == 0 and [x.split()[0] for x in r4.stdout.splitlines()] == g2l and len(g2c) == 20, f"p1g-w05-yukle eslesme GRUP 2: {r4.stdout}"
    for kotu in ("4570110121,9999999999", "4570110121,4570110121", "", "4570110121,,4570110641"):
        r5 = subprocess.run(["python3", "-", kotu], input=es, capture_output=True, text=True, cwd=str(ROOT))
        assert r5.returncode != 0, f"p1g-w05-yukle eslesme bilinen FAIL {kotu!r}: {r5.stdout}"
    # yaz yolunun kuru RAPOR Python kapisi (GRUP 1 kurusu 42256985849: HAZIR 5, GRUP 1 sirasi): bilinen PASS / FAIL
    kod = _yigin("python3 - \"$DAMGA\" \"$SADECE\" <<'PY'")
    L1 = [{"ilan": i} for i in G1.split(",")]
    iyi = dict(mod="kuru", plan_damga=D, sayilar={"HAZIR": 5}, ilanlar=L1)
    for ad, rap, bek in (("iyi", iyi, 0), ("mod yazim", dict(iyi, mod="yazim"), 1), ("baska damga", dict(iyi, plan_damga=D[:-1] + "c"), 1),
                         ("HAZIR 4", dict(iyi, sayilar={"HAZIR": 4}), 1), ("HAZIR 4 + BLOK 1", dict(iyi, sayilar={"HAZIR": 4, "BLOK": 1}), 1),
                         ("HAZIR 5 + BLOK 1", dict(iyi, sayilar={"HAZIR": 5, "BLOK": 1}), 1), ("ilan eksik", dict(iyi, ilanlar=L1[:4]), 1),
                         ("ilan sirasi farkli", dict(iyi, ilanlar=L1[::-1]), 1), ("baska ilan", dict(iyi, ilanlar=L1[:4] + [{"ilan": "4570155846"}]), 1)):
        with _tf.TemporaryDirectory() as td:
            Path(td, "_plan").mkdir(); Path(td, "_out").mkdir()
            Path(td, "_plan", "KURU_RAPOR.json").write_text(_j.dumps(rap))
            r3 = subprocess.run(["python3", "-", D, G1], input=kod, capture_output=True, text=True, cwd=td)
            kk = _j.loads(Path(td, "_out", "KURU_KAPI.json").read_text())["kuru_kapisi"]
            assert (r3.returncode == 0) == (bek == 0) and kk == ("PASS" if bek == 0 else "FAIL"), f"p1g-w05-yukle kuru kapisi {ad}: {r3.returncode} {kk}"
    # token adimi uctan uca, sahte rclone ile (ag yok): copyto / lsf --dirs-only / cat
    a0 = tk; a1 = next(i for i in range(a0, len(ps)) if ps[i].strip() == "run: |"); a2 = next(i for i in range(a1 + 1, len(ps)) if ps[i].startswith("      - "))
    adim_tam = "\n".join(x[10:] for x in ps[a1 + 1:a2])
    adim = "\n".join(x[10:] for x in ps[a1 + 1:a2] if not x.rstrip().endswith("# KAPI2"))   # yaz yolu testleri: KAPI2 cikarilmis
    assert adim_tam.count("# KAPI2") == 2 and "# KAPI2" not in adim
    ciftler = ["AQUARIUS_AQUARIUS", "AQUARIUS_ARIES", "AQUARIUS_CANCER", "AQUARIUS_CAPRICORN", "AQUARIUS_GEMINI"]
    # sahte rclone: copyto (indir / yukle), lsf --dirs-only | --files-only, cat; RCLONE_BOZ: lsf (dizin listesi), lsfdosya, cat, yukle
    sahte = ('#!/bin/bash\n[ -n "$RCLONE_LOG" ] && echo "$*" >> "$RCLONE_LOG"\n'
             'case "$1" in\n'
             ' copyto) if [ "${2#gdrive:}" != "$2" ]; then s="${2#gdrive:}"; [ -f "$FAKE/$s" ] || exit 3; mkdir -p "$(dirname "$3")"; cp "$FAKE/$s" "$3";\n'
             '   else [ "$RCLONE_BOZ" = yukle ] && exit 5; s="${3#gdrive:}"; mkdir -p "$(dirname "$FAKE/$s")"; cp "$2" "$FAKE/$s"; fi ;;\n'
             ' lsf) s="${3#gdrive:}"; s="${s%/}"; [ -d "$FAKE/$s" ] || exit 3\n'
             '   if [ "$2" = --dirs-only ]; then [ "$RCLONE_BOZ" = lsf ] && exit 5; for d in "$FAKE/$s"/*/; do [ -d "$d" ] && echo "$(basename "$d")/"; done; true\n'
             '   else [ "$RCLONE_BOZ" = lsfdosya ] && exit 5; for f in "$FAKE/$s"/*; do [ -f "$f" ] && basename "$f"; done; fi; true ;;\n'
             ' cat) [ "$RCLONE_BOZ" = cat ] && exit 5; s="${2#gdrive:}"; [ -f "$FAKE/$s" ] || exit 3; cat "$FAKE/$s" ;;\n'
             ' *) exit 3 ;;\nesac\n')

    def _uc(kip="yaz", den="1", eksik=None, rapor=None, kilit=None, boz=None, ref="refs/heads/main", ikinci=False, yalniz_rapor=False):
        with _tf.TemporaryDirectory() as td:
            td = Path(td); (td / "bin").mkdir(); (td / "w").mkdir()
            (td / "bin" / "rclone").write_text(sahte); (td / "bin" / "rclone").chmod(0o755)
            fk = td / "fake" / "ASTROLOVE" / "TEMP"; p1 = fk / "P1G_W05_20261106_090016"; pk = p1 / "PILOT" / "kuru_42256985849"
            pk.mkdir(parents=True); (fk / "ETSY_TOKEN.json").write_text("{}")
            if eksik != "plan":
                (pk / "PLAN_W05.json").write_text(_j.dumps({"plan_damga": D}))
            (pk / "RAPOR.json").write_text(_j.dumps(rapor if rapor is not None else iyi))
            (p1 / "PILOT" / "yaz_42233642909").mkdir(); (p1 / "PILOT" / "yaz_42233642909" / "KURU_KAPI.json").write_text(
                _j.dumps(dict(kuru_kapisi="PASS", plan_damga="42223863686_0e95c567bc1b")))
            (p1 / "PILOT" / "yaz_42210656786").mkdir()   # eski pilot: gercek bicimli (indent=1) baska damgali RAPOR.json + KURU_KAPI.json
            (p1 / "PILOT" / "yaz_42210656786" / "RAPOR.json").write_text(_j.dumps(dict(mod="yazim", plan_damga="42210418010_3b9f9139dc9e",
                                                                                       sayilar={"DUR": 1}), indent=1))
            (p1 / "PILOT" / "yaz_42210656786" / "KURU_KAPI.json").write_text(_j.dumps(dict(kuru_kapisi="PASS", plan_damga="42210418010_3b9f9139dc9e")))
            (p1 / "PILOT" / "yaz_42210656786" / "ilanlar").mkdir()
            (p1 / "PILOT" / "yaz_42999999990").mkdir()   # dosyasiz klasor (kuru kapisindan once dusmus kosu): kilidi tetiklemez
            if kilit:
                (p1 / "PILOT" / kilit).mkdir()
                (p1 / "PILOT" / kilit / ("RAPOR.json" if yalniz_rapor else "KURU_KAPI.json")).write_text(
                    _j.dumps(dict(mod="yazim" if yalniz_rapor else None, kuru_kapisi="FAIL", plan_damga=D)))
            for c in ciftler:
                if eksik != ("kart", c):
                    (p1 / f"{c}_W05_SUREC.jpg").write_text("k")
            for d in ("scripts", "data"):
                (td / "w" / d).symlink_to(ROOT / d)
            e = {"PATH": f"{td / 'bin'}:{os.environ.get('PATH', '')}", "FAKE": str(td / "fake"), "P1G": "ASTROLOVE/TEMP/P1G_W05_20261106_090016",
                 "YEDEK": "ASTROLOVE/TEMP/POSTER_GALERI_V11_YEDEK/20261106_090016", "KIP": kip, "SADECE": G1, "ONAY": Y if kip == "yaz" else "W05-KURU-GRUP1",
                 "DAMGA": D if kip == "yaz" else "", "GITHUB_RUN_ATTEMPT": den, "GITHUB_REF": ref, "GITHUB_ENV": str(td / "genv"),
                 "RCLONE_BOZ": boz or "", "CIKTI": "ASTROLOVE/TEMP/P1G_W05_20261106_090016/PILOT/yaz_43000000001"}
            r6 = subprocess.run(["bash", "-e", "-c", adim], capture_output=True, text=True, env=e, cwd=str(td / "w"), stdin=subprocess.DEVNULL)
            isaret = p1 / "PILOT" / "yaz_43000000001" / "KURU_KAPI.json"
            isaret_var = isaret.exists() and D in isaret.read_text()
            if ikinci:   # ayni Drive ile ikinci dispatch (yeni calisma klasoru): kilit isareti onu durdurmali
                assert r6.returncode == 0 and isaret_var, f"ilk kosu: {r6.returncode} {isaret_var} {r6.stderr[-300:]}"
                import shutil as _sh
                _sh.rmtree(td / "w"); (td / "w").mkdir()
                for d in ("scripts", "data"):
                    (td / "w" / d).symlink_to(ROOT / d)
                e["CIKTI"] = "ASTROLOVE/TEMP/P1G_W05_20261106_090016/PILOT/yaz_43000000002"
                r6 = subprocess.run(["bash", "-e", "-c", adim], capture_output=True, text=True, env=e, cwd=str(td / "w"), stdin=subprocess.DEVNULL)
            w = td / "w"
            kk = _j.loads((w / "_out" / "KURU_KAPI.json").read_text()).get("kuru_kapisi") if (w / "_out" / "KURU_KAPI.json").exists() else None
            return dict(rc=r6.returncode, ci=r6.stdout + r6.stderr, kart=sorted(x.name for x in (w / "_kart").iterdir()) if (w / "_kart").exists() else [],
                        canli=(w / "_canli").exists(), tok=(w / "_work" / "ETSY_TOKEN.json").exists(), kk=kk,
                        plan=(w / "_out" / "PLAN_W05_KULLANILAN.json").exists(),
                        genv=(td / "genv").read_text() if (td / "genv").exists() else "", isaret=isaret_var)
    z = _uc()
    assert z["rc"] == 0 and len(z["kart"]) == 5 and not z["canli"] and z["tok"] and z["kk"] == "PASS" and z["plan"] and f"PLAN_DAMGA={D}" in z["genv"] \
        and z["isaret"], f"p1g-w05-yukle uctan uca yaz: {z}"
    for ad, kw in (("eksik kart", dict(eksik=("kart", "AQUARIUS_CANCER"))),
                   ("eksik PLAN", dict(eksik="plan")), ("bozuk RAPOR (HAZIR 4)", dict(rapor=dict(iyi, sayilar={"HAZIR": 4}))),
                   ("tek kullanimlik kilit", dict(kilit="yaz_42999999999")), ("PILOT listesi okunamadi", dict(boz="lsf")),
                   ("kilit: yalniz RAPOR.json ayni damga", dict(kilit="yaz_42999999998", yalniz_rapor=True)),
                   ("kilit: yaz_ klasoru listelenemedi", dict(boz="lsfdosya")), ("kilit: KURU_KAPI.json okunamadi", dict(boz="cat")),
                   ("kilit isareti yuklenemedi", dict(boz="yukle")), ("ikinci dispatch (isaret)", dict(ikinci=True))):
        z = _uc(**kw)
        assert z["rc"] != 0 and not z["tok"], f"p1g-w05-yukle uctan uca bilinen FAIL {ad}: {z['rc']} token {z['tok']} {z['ci'][-300:]}"
        if ad in ("tek kullanimlik kilit", "PILOT listesi okunamadi", "kilit: yalniz RAPOR.json ayni damga",
                  "kilit: yaz_ klasoru listelenemedi", "kilit: KURU_KAPI.json okunamadi", "ikinci dispatch (isaret)"):
            assert not z["kart"], f"p1g-w05-yukle {ad}: kapi / kilit kart indirmeden once durmali {z['kart']}"
        if ad == "eksik kart":
            assert "indirilemedi (4570125580 AQUARIUS_CANCER)" in z["ci"] and not any("CAPRICORN" in x or "GEMINI" in x for x in z["kart"]), z["ci"][-300:]
        if ad == "bozuk RAPOR (HAZIR 4)":
            assert z["kk"] == "FAIL", z
        if ad == "tek kullanimlik kilit":
            assert "tek kullanimlik kilit: yaz_42999999999" in z["ci"], z["ci"][-300:]
        if ad == "ikinci dispatch (isaret)":
            assert "tek kullanimlik kilit: yaz_43000000001" in z["ci"], z["ci"][-300:]
        if ad == "kilit isareti yuklenemedi":
            assert "kilit isareti Drive'a yazilamadi" in z["ci"] and len(z["kart"]) == 5, z["ci"][-300:]
    # kuru uctan uca (GRUP 2, gercek adim metni KAPI2 dahil): sahte YEDEK GALERI.json (rank 1..11, W05 bagsiz) + PASS alanli sha256'li
    # MANIFEST_W05.csv; plan gercek w05_degistir.py plan ile kurulur. KILIT1 kuru'da hic calismaz (sahte rclone'a PILOT listesi istegi gelmez)
    # ve PILOT/yaz_* altinda "" iceren RAPOR.json olsa da durmaz.
    import hashlib as _hl

    def _uck(kip="kuru", den="1", ref="refs/heads/main", eksik=None, blok=None):
        with _tf.TemporaryDirectory() as td:
            td = Path(td); (td / "bin").mkdir(); (td / "w").mkdir()
            (td / "bin" / "rclone").write_text(sahte); (td / "bin" / "rclone").chmod(0o755)
            fk = td / "fake" / "ASTROLOVE" / "TEMP"; p1 = fk / "P1G_W05_20261106_090016"; yd = fk / "POSTER_GALERI_V11_YEDEK" / "20261106_090016"
            (p1 / "PILOT" / "yaz_42999999991").mkdir(parents=True); (fk / "ETSY_TOKEN.json").write_text("{}")
            (p1 / "PILOT" / "yaz_42999999991" / "RAPOR.json").write_text('{"mod": "yazim", "plan_damga": "", "a": ""}')   # bos damga tuzagi
            satir = ["cift,ilan,dosya,sha256,kimlik,canli_ocr,bilinen_pass,durum"]
            for n, (i, c) in enumerate(zip(g2l, g2c)):
                kart = p1 / f"{c}_W05_SUREC.jpg"
                if eksik != ("kart", c):
                    kart.write_bytes(b"" if eksik == ("bos_kart", c) else f"kart {c}".encode())
                satir.append(f"{c},{i},{c}_W05_SUREC.jpg,{_hl.sha256(f'kart {c}'.encode()).hexdigest()},PASS,PASS,PASS,PASS")
                if eksik == ("galeri", c):
                    continue
                base = 9000000000 + n * 100
                gor = [dict(rank=k, listing_image_id=base + k, alt_text="How your order works" if k == 5 else f"alt {c} {k}") for k in range(1, 12)]
                bag = [dict(property_id=200, value_id=100 + k, image_id=base + k) for k in (7, 8, 9, 10, 11)]
                if blok == c:
                    bag.append(dict(property_id=200, value_id=99, image_id=base + 5))
                (yd / f"{i}_{c}").mkdir(parents=True)
                (yd / f"{i}_{c}" / "GALERI.json").write_text("" if eksik == ("bos_galeri", c) else _j.dumps(dict(listing_id=i, cift=c, gorseller=gor, baglar=bag)))
            if eksik != "manifest":
                (p1 / "MANIFEST_W05.csv").write_text("\n".join(satir) + "\n")
            for d in ("scripts", "data"):
                (td / "w" / d).symlink_to(ROOT / d)
            e = {"PATH": f"{td / 'bin'}:{os.environ.get('PATH', '')}", "FAKE": str(td / "fake"), "P1G": "ASTROLOVE/TEMP/P1G_W05_20261106_090016",
                 "YEDEK": "ASTROLOVE/TEMP/POSTER_GALERI_V11_YEDEK/20261106_090016", "KIP": kip, "SADECE": G2, "ONAY": Y2, "DAMGA": "",
                 "GITHUB_RUN_ATTEMPT": den, "GITHUB_REF": ref, "GITHUB_ENV": str(td / "genv"), "GITHUB_RUN_ID": "43000000003",
                 "RCLONE_LOG": str(td / "rclone.log"), "CIKTI": "ASTROLOVE/TEMP/P1G_W05_20261106_090016/PILOT/kuru_43000000003"}
            r7 = subprocess.run(["bash", "-e", "-c", adim_tam], capture_output=True, text=True, env=e, cwd=str(td / "w"), stdin=subprocess.DEVNULL)
            w = td / "w"; lg = (td / "rclone.log").read_text() if (td / "rclone.log").exists() else ""
            pj = _j.loads((w / "_out" / "PLAN_W05.json").read_text()) if (w / "_out" / "PLAN_W05.json").exists() else {}
            return dict(rc=r7.returncode, ci=r7.stdout + r7.stderr, kart=sorted(x.name for x in (w / "_kart").iterdir()) if (w / "_kart").exists() else [],
                        canli=sorted(x.name for x in (w / "_canli").iterdir()) if (w / "_canli").exists() else [],
                        tok=(w / "_work" / "ETSY_TOKEN.json").exists(), lsf="lsf" in lg, plan=pj,
                        genv=(td / "genv").read_text() if (td / "genv").exists() else "")
    z = _uck()
    assert z["rc"] == 0 and len(z["kart"]) == 20 and len(z["canli"]) == 20 and z["tok"] and not z["lsf"] \
        and list((z["plan"].get("girdiler") or {})) == g2l and "PLAN_DAMGA=43000000003_" in z["genv"], \
        f"p1g-w05-yukle kuru uctan uca GRUP 2: rc {z['rc']} kart {len(z['kart'])} canli {len(z['canli'])} token {z['tok']} lsf {z['lsf']} {z['ci'][-400:]}"
    for ad, kw, ilk in (("kip yaz (KAPI2)", dict(kip="yaz"), True), ("deneme 2 (KAPI2)", dict(den="2"), True),
                        ("ref main degil (KAPI2)", dict(ref="refs/heads/baska"), True),
                        ("eksik kart", dict(eksik=("kart", g2c[7])), False), ("eksik GALERI.json", dict(eksik=("galeri", g2c[3])), False),
                        ("bos kart", dict(eksik=("bos_kart", g2c[19])), False), ("bos GALERI.json", dict(eksik=("bos_galeri", g2c[0])), False),
                        ("MANIFEST yok", dict(eksik="manifest"), False), ("plan BLOK (W05 renge bagli)", dict(blok=g2c[11]), False)):
        z = _uck(**kw)
        assert z["rc"] != 0 and not z["tok"] and not z["lsf"], f"p1g-w05-yukle kuru bilinen FAIL {ad}: rc {z['rc']} token {z['tok']} {z['ci'][-300:]}"
        if ilk:
            assert not z["kart"] and "KAPI2" in z["ci"], f"p1g-w05-yukle {ad}: KAPI2 kart indirmeden once durmali {z['kart']} {z['ci'][-200:]}"
        if ad == "MANIFEST yok":
            assert "MANIFEST_W05.csv indirilemedi" in z["ci"], z["ci"][-300:]
        if ad == "plan BLOK (W05 renge bagli)":
            assert "plan BLOK" in z["ci"], z["ci"][-300:]
        if ad == "eksik kart":
            assert f"kart indirilemedi ({g2l[7]} {g2c[7]})" in z["ci"], z["ci"][-300:]
        if ad == "bos kart":
            assert f"kart bos ({g2l[19]} {g2c[19]})" in z["ci"], z["ci"][-300:]
        if ad == "bos GALERI.json":
            assert f"canli GALERI.json bos ({g2l[0]} {g2c[0]})" in z["ci"], z["ci"][-300:]
        if ad == "eksik GALERI.json":
            assert f"canli GALERI.json indirilemedi ({g2l[3]} {g2c[3]})" in z["ci"], z["ci"][-300:]
    print(f"PASS: {len(files)} workflow YAML, {len(PUBLIC_AUDITS)} public denetim sozlesmesi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
