#!/usr/bin/env python3
"""Siparis yardimcisi is akisi kabuk testi (18-19 Kas): eski klasor-girdili modlarin yoklugu ve kosu_sil (tur / dal / baslatan / sinir /
siparis izi) adimi, sahte gh / curl ile (ag yok). Bilinen PASS + bilinen FAIL."""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok

KOK = Path(__file__).resolve().parents[2]
HATA = []
SAHTE_RCLONE = r'''#!/bin/bash
# sahte rclone: "gdrive,root_folder_id=<ID>:" -> $SAHTE_KOK/<ID>; ag yok
yol() { case "$1" in gdrive,root_folder_id=*) local i="${1#gdrive,root_folder_id=}"; echo "$SAHTE_KOK/${i%%:*}";; *) echo "$1";; esac; }
cmd="$1"; shift
case "$cmd" in
  copy) src=$(yol "$1"); dst=$(yol "$2"); mkdir -p "$dst"; cp -r "$src"/. "$dst"/ ;;
  check) [ "${SAHTE_CHECK_FAIL:-0}" = "1" ] && { echo "sahte: 1 differences found" >&2; exit 1; }; exit 0 ;;
  lsl) for f in "$(yol "$1")"/*; do echo "   123 2026-11-18 00:00:00.000 $(basename "$f")"; done ;;
  *) echo "sahte rclone: bilinmeyen $cmd" >&2; exit 2 ;;
esac
'''


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


yeni = (KOK / ".github/workflows/siparis-yardimci.yml").read_text()
kontrol("yardimcida gizli klasor kimligi alan eski modlar YOK (kesit_tasi, halka_tani, motor_tani; Serdar karar 2)",
        not any(m in yaml.safe_load(yeni)["jobs"] for m in ("kesit_tasi", "halka_tani", "motor_tani")) and "inputs.kis" not in yeni and "inputs.gpt" not in yeni)


# kosu_sil (V2B ORTA bulgu): sahte gh / curl (ag yok). Kosu bilgisi $SAHTE_KOK/run_<id>.txt; DELETE -> silindi_<id>; curl silinmise 404.
SAHTE_GH = r'''#!/bin/bash
if [ "$2" = "-X" ] && [ "$3" = "DELETE" ]; then id="${4##*/}"; touch "$SAHTE_KOK/silindi_$id"; exit 0; fi
case "$2" in
  */jobs) id="${2%/jobs}"; id="${id##*/}"; [ -f "$SAHTE_KOK/run_$id.txt" ] || exit 1; echo "5$id";;      # tek is, kimlik 5<kosu>
  */annotations) j="${2%/annotations}"; j="${j##*/}"; [ -f "$SAHTE_KOK/izi_${j#5}.txt" ] && cat "$SAHTE_KOK/izi_${j#5}.txt"; exit 0;;
  *) id="${2##*/}"; [ -f "$SAHTE_KOK/run_$id.txt" ] || exit 1; cat "$SAHTE_KOK/run_$id.txt";;
esac
'''
SAHTE_CURL = r'''#!/bin/bash
u="${@: -1}"; id="${u##*/}"; [ -f "$SAHTE_KOK/silindi_$id" ] && printf 404 || printf 200
'''


IZ = {"11": "0123456789abcdef", "12": "0123456789abcdef", "13": "0123456789abcdef", "21": "0123456789abcdef", "22": "0123456789abcdef",
      "23": "0123456789abcdef", "24": "0123456789abcdef", "31": "fedcba9876543210"}


def sil_dene(kosular, sinir, kayit, aktor="serdar", capa="11", iz=None):
    run = next(s for s in yaml.safe_load(yeni)["jobs"]["kosu_sil"]["steps"] if s.get("name", "").startswith("Kosu kayitlarini sil"))["run"]
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); (d / "drive").mkdir(); (d / "bin").mkdir()
        for ad, ic in (("gh", SAHTE_GH), ("curl", SAHTE_CURL)):
            (d / "bin" / ad).write_text(ic); (d / "bin" / ad).chmod(0o755)
        for i, satir in kayit.items():
            (d / "drive" / f"run_{i}.txt").write_text(satir + "\n")
        for i, z in (IZ if iz is None else iz).items():
            (d / "drive" / f"izi_{i}.txt").write_text(z + "\n")
        (d / "adim.sh").write_text(run)
        env = {"PATH": f"{d / 'bin'}:{os.environ.get('PATH', '')}", "SAHTE_KOK": str(d / "drive"), "KOSULAR": kosular, "SINIR": sinir,
               "GITHUB_ACTOR": aktor, "GITHUB_RUN_ID": "1", "GITHUB_REPOSITORY": "o/r", "GH_TOKEN": "x", "CAPA": capa}
        r = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(d / "adim.sh")], cwd=d, capture_output=True, text=True,
                           timeout=60, env=env)
        return r.returncode, r.stdout, sorted(p.name[8:] for p in (d / "drive").glob("silindi_*"))


import datetime as _dt  # noqa: E402
_s = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
_y = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
_e = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
K = {"11": f"completed .github/workflows/siparis-kisisel-oku.yml {_y} main workflow_dispatch serdar",
     "12": f"completed .github/workflows/siparis-giris.yml {_y} main workflow_dispatch serdar",
     "13": f"completed .github/workflows/siparis-yardimci.yml@refs/heads/main {_y} main workflow_dispatch serdar",
     "21": f"completed .github/workflows/siparis-kisisel-oku.yml {_e} main workflow_dispatch serdar",
     "22": f"completed .github/workflows/siparis-kisisel-oku.yml {_y} main workflow_dispatch baskasi",
     "23": f"completed .github/workflows/siparis-giris.yml {_y} baska-dal workflow_dispatch serdar",
     "24": f"in_progress .github/workflows/siparis-giris.yml {_y} main workflow_dispatch serdar"}
rc, so, sil = sil_dene("11:oku,12:giris,13:tara", _s, K)
kontrol("kosu_sil bilinen PASS: tur / dal / baslatan / sinir uyan 3 kosu silinir, 404, cikis 0", rc == 0 and sil == ["11", "12", "13"], f"rc={rc} {so}")
for ad, ks in (("tur yanlis bildirilmis (giris dedi, oku kosusu)", "11:giris"), ("sinir_utc'den eski", "21:oku"), ("baslatan farkli", "22:oku"),
               ("dal farkli", "23:giris"), ("bitmemis kosu", "24:giris"), ("kayit yok", "99:oku")):
    rc, so, sil = sil_dene(ks, _s, K)
    kontrol(f"kosu_sil bilinen FAIL: {ad} -> silinmez, cikis 1", rc == 1 and sil == [], f"rc={rc} {sil} {so}")
for ad, ks, sn in (("tursuz id", "11", _s), ("bos sinir", "11:oku", ""), ("bicimsiz sinir", "11:oku", "dun")):
    rc, so, sil = sil_dene(ks, sn, K)
    kontrol(f"kosu_sil bilinen FAIL: {ad} -> hic silinmez", rc == 1 and sil == [], f"rc={rc} {sil}")
rc, so, sil = sil_dene("11:oku,22:oku", _s, K)
kontrol("kosu_sil karisik liste: uyan silinir, uymayan kalir, cikis 1", rc == 1 and sil == ["11"], f"rc={rc} {sil}")
K["31"] = f"completed .github/workflows/siparis-giris.yml {_y} main workflow_dispatch serdar"
rc, so, sil = sil_dene("11:oku,31:giris", _s, K)
kontrol("kosu_sil bilinen FAIL (D7): baska siparisin izi -> o kosu silinmez, ayni izli silinir", rc == 1 and sil == ["11"], f"rc={rc} {sil} {so}")
rc, so, sil = sil_dene("12:giris", _s, K, iz={k: v for k, v in IZ.items() if k != "12"})
kontrol("kosu_sil bilinen FAIL: izi olmayan siparis kosusu silinmez", rc == 1 and sil == [], f"rc={rc} {sil}")
rc, so, sil = sil_dene("11:oku,12:giris", _s, K, capa="")
kontrol("kosu_sil bilinen FAIL: capa yok -> hicbir sey silinmez", rc == 1 and sil == [])
rc, so, sil = sil_dene("11:oku", _s, K, capa="99")
kontrol("kosu_sil bilinen FAIL: capanin izi okunamaz -> hicbir sey silinmez", rc == 1 and sil == [])
rc, so, sil = sil_dene("12:giris", _s, K, iz=dict(IZ, **{"11": "0123456789abcdef\nfedcba9876543210"}))
kontrol("kosu_sil bilinen FAIL: capada iki farkli iz -> hicbir sey silinmez", rc == 1 and sil == [])
K["41"] = f"completed .github/workflows/ai-beyan-test.yml {_y} claude/upbeat-hopper-fjsaii push serdar"
rc, so, sil = sil_dene("41:ci", _s, K)
kontrol("kosu_sil: ci kosusu (siparis verisi yok) izsiz silinir", rc == 0 and sil == ["41"], f"rc={rc} {sil} {so}")

print("premium-tara kabuk testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
