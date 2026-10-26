#!/usr/bin/env python3
"""Workflow YAML'larini ve IS_0025 salt-okur/log sozlesmesini denetle."""

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
    print(f"PASS: {len(files)} workflow YAML, {len(PUBLIC_AUDITS)} public denetim sozlesmesi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
