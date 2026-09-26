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
        assert "if: failure()" in text and "tail -n 150" in text, f"{name}: hata logu eksik"
        assert "_OZET.md" in text and "$GITHUB_STEP_SUMMARY" in text, f"{name}: ozet logu eksik"
    router = (WORKFLOWS / "pod-order-router.yml").read_text(encoding="utf-8")
    assert "TEMP/SIPARIS_ONAY/${R_SUBMIT}" in router and "ONAYLAR.json" in router, "submit onay indirmiyor"
    assert "siparis_onay.py hazirla" in router and "rclone copyto \"$uzak\"" in router, "paket onaya hazirlanmiyor"
    onay = (WORKFLOWS / "siparis-onay-yaz.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in onay and "siparis_onay.py onayla" in onay, "onay workflow sozlesmesi eksik"
    assert "group: siparis-onay-defteri" in onay and "cancel-in-progress: false" in onay, "defter yarisi korunmuyor"
    print(f"PASS: {len(files)} workflow YAML, {len(PUBLIC_AUDITS)} public denetim sozlesmesi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
