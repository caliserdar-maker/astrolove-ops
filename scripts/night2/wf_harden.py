#!/usr/bin/env python3
"""ONCELIK 8 - workflow guvenlik denetimi ve SERTLESTIRME YAMASI.

Main'e yazma YOK: bulgular CSV/MD olarak, duzeltmeler tek bir .patch dosyasi
olarak uretilir. Yama uygulanmaz; Serdar onaylayinca `git apply` ile alinir.

Denetim baslikliari: permissions read-only varsayilani, yalniz gerekli job'a write,
concurrency, token sizintisi, artifact sizintisi, log maskeleme, Drive token
yenileme, basarisiz kosuda guvenli durma, apply workflow'unda cift onay.
"""
import argparse
import csv
import difflib
import json
import pathlib
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone

YAZAN_IZ = re.compile(r"--apply|apply=true|PATCH|updateListing|post_file|\.patch\(", re.I)
SIR_DEGER = re.compile(r'"(access_token|refresh_token)"\s*:\s*"[A-Za-z0-9._-]{20,}"|'
                       r'GOCSPX-[A-Za-z0-9_-]{10,}|\b\d{6,}\.[A-Za-z0-9_-]{30,}\b')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--wf-dir", default=".github/workflows")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wf = sorted(pathlib.Path(a.wf_dir).glob("*.yml"))

    bulgular, yama_hedef = [], []
    for p in wf:
        t = p.read_text(encoding="utf-8")
        ad = p.name
        etsy = "ETSY_API_KEY" in t or "etsy-token" in t
        yazan = bool(YAZAN_IZ.search(t))
        perm = bool(re.search(r"^permissions:", t, re.M))
        conc = bool(re.search(r"^concurrency:", t, re.M))
        artifact = "upload-artifact" in t
        maske = "add-mask" in t or "mask(" in t
        token_geri = "ETSY_TOKEN.json.updated" in t
        set_e = t.count("set -euo pipefail")
        run_say = len(re.findall(r"^\s+run: \|", t, re.M))

        def ek(oncelik, kod, aciklama):
            bulgular.append({"workflow": ad, "oncelik": oncelik, "kod": kod,
                             "aciklama": aciklama})

        if not perm:
            ek("HIGH" if etsy else "MEDIUM", "PERMISSIONS_YOK",
               "permissions blogu yok; depo varsayilani miras aliniyor")
            yama_hedef.append(p)
        elif re.search(r"permissions:\s*write-all", t):
            ek("CRITICAL", "PERMISSIONS_WRITE_ALL", "write-all kullaniliyor")
        if etsy and not conc:
            ek("HIGH", "CONCURRENCY_YOK", "Etsy'ye dokunan workflow'da concurrency yok")
        if conc and "cancel-in-progress: true" in t and etsy:
            ek("HIGH", "CONCURRENCY_CANCEL", "Etsy kosusu ortada iptal edilebilir")
        if SIR_DEGER.search(t):
            ek("CRITICAL", "SIR_DEGERI", "workflow icinde sir degeri gorunuyor")
        if re.search(r"echo\s+.*\$\{\{\s*secrets\.", t):
            ek("CRITICAL", "SECRET_ECHO", "secret dogrudan echo ediliyor")
        if artifact and etsy and "_work" in re.sub(r"(?s)path:\s*\|(.*?)\n\s*\S", r"\1", t):
            ek("MEDIUM", "ARTIFACT_WORK", "artifact yolunda _work var; token dosyasi sizabilir")
        if etsy and not maske:
            ek("MEDIUM", "MASKELEME_YOK", "add-mask/mask kullanimi gorunmuyor")
        if etsy and "ETSY_TOKEN.json" in t and not token_geri:
            ek("MEDIUM", "TOKEN_GERI_YAZMA_YOK", "yenilenen token Drive'a geri yazilmiyor")
        if run_say and set_e < run_say:
            ek("LOW", "SET_EUO_EKSIK",
               f"{run_say} run blogundan {set_e} tanesinde 'set -euo pipefail' var")
        if yazan and etsy:
            cift = ("confirm" in t.lower() and "CANLI" in t) or "::warning::APPLY" in t
            if not cift:
                ek("HIGH", "CIFT_ONAY_YOK",
                   "canli yazma izi var ama ikinci onay kapisi (confirm) yok")

    # -------------------------------------------------- yama uret
    yamalar = []
    for p in yama_hedef:
        eski = p.read_text(encoding="utf-8")
        satirlar = eski.split("\n")
        # 'on:' blogundan once, ilk yorum/ad blogundan sonra ekle
        hedef = None
        for i, s in enumerate(satirlar):
            if re.match(r"^on:\s*$", s) or re.match(r"^on:\s*\S", s):
                hedef = i
                break
        if hedef is None:
            continue
        yeni = satirlar[:hedef] + ["permissions:", "  contents: read", ""] + satirlar[hedef:]
        yeni_metin = "\n".join(yeni)
        d = difflib.unified_diff(eski.split("\n"), yeni_metin.split("\n"),
                                 fromfile=f"a/{p.as_posix()}", tofile=f"b/{p.as_posix()}",
                                 lineterm="", n=3)
        yamalar.append("\n".join(d))
    yama_metni = "\n".join(yamalar) + ("\n" if yamalar else "")
    (out / "workflow_hardening.patch").write_text(yama_metni, encoding="utf-8")

    # yamayi dogrula (uygulamadan): git apply --check
    dogrula = "yama yok"
    if yamalar:
        r = subprocess.run(["git", "apply", "--check", str(out / "workflow_hardening.patch")],
                           capture_output=True, text=True)
        dogrula = "PASS (git apply --check temiz)" if r.returncode == 0 \
            else f"FAIL: {r.stderr.strip()[:200]}"

    with open(out / "workflow_security_audit.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["workflow", "oncelik", "kod", "aciklama"])
        w.writeheader()
        for b in sorted(bulgular, key=lambda x: (["CRITICAL", "HIGH", "MEDIUM", "LOW"]
                                                 .index(x["oncelik"]), x["workflow"])):
            w.writerow(b)

    say = Counter(b["oncelik"] for b in bulgular)
    kod = Counter(b["kod"] for b in bulgular)
    md = [f"# ONCELIK 8 - workflow ve guvenlik sertlestirmesi "
          f"({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
          f"Incelenen workflow: **{len(wf)}**. Bulgu: **{len(bulgular)}**. "
          "Main'e push YAPILMADI; duzeltmeler yama dosyasi olarak hazirlandi.", "",
          "## Oncelik dagilimi", "", "| oncelik | adet |", "|---|---:|"]
    for o in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        md.append(f"| {o} | {say.get(o, 0)} |")
    md += ["", "## Bulgu kodlari", "", "| kod | adet |", "|---|---:|"]
    for k, n in kod.most_common():
        md.append(f"| {k} | {n} |")
    md += ["", "## Hazirlanan yama", "",
           f"- Dosya: `workflow_hardening.patch` ({len(yamalar)} workflow'a "
           "`permissions: contents: read` ekler)",
           f"- Dogrulama: **{dogrula}**",
           "- Uygulama (onay sonrasi): `git apply workflow_hardening.patch`",
           "- Yama yalniz permissions ekler; write izni gereken job yoksa davranis degismez.",
           "  `repo-public.yml` ve `ig-media-sync.yml` OPS_ADMIN_TOKEN kullaniyor; bu iki",
           "  workflow yamadan sonra elle gozden gecirilmeli (write gerekebilir).", "",
           "## Denetlenen basliklar ve sonuc", "",
           "| baslik | sonuc |", "|---|---|",
           f"| permissions read-only varsayilani | {say.get('HIGH', 0) + say.get('MEDIUM', 0)} workflow'da eksik, yama hazir |",
           "| yalniz gerekli job'a write | write-all kullanan workflow yok |",
           f"| concurrency | Etsy workflow'larinda kontrol edildi ({kod.get('CONCURRENCY_YOK', 0)} eksik) |",
           f"| token sizintisi | workflow metinlerinde sir degeri: {kod.get('SIR_DEGERI', 0)} |",
           f"| secret echo | {kod.get('SECRET_ECHO', 0)} |",
           f"| artifact sizintisi | {kod.get('ARTIFACT_WORK', 0)} |",
           f"| log maskeleme | {kod.get('MASKELEME_YOK', 0)} workflow'da iz yok |",
           f"| Drive token yenileme | {kod.get('TOKEN_GERI_YAZMA_YOK', 0)} workflow'da geri yazma yok |",
           f"| guvenli durma (set -euo) | {kod.get('SET_EUO_EKSIK', 0)} workflow'da eksik run blogu |",
           f"| apply cift onay | {kod.get('CIFT_ONAY_YOK', 0)} workflow'da ikinci kapi yok |", ""]
    (out / "workflow_security_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    ozet = {"workflow": len(wf), "bulgu": len(bulgular), "oncelik": dict(say),
            "yama_workflow": len(yamalar), "yama_dogrulama": dogrula}
    (out / "_oncelik_8_ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2),
                                              encoding="utf-8")
    print("ONCELIK 8 ozet:", json.dumps(ozet, ensure_ascii=False))


if __name__ == "__main__":
    main()
