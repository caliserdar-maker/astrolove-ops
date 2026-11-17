#!/usr/bin/env python3
"""receipt_log_kapi testi (IP adim 0 c, 17 Kas 2026). Ag kapali (CLAUDE.md TEST AGI); alt surecler yalniz bash + jq.

1) Kapi: bilinen FAIL ornekleri (R1 env/run/with, R2 maskesiz okuma, liste girdisi tek maske) ve bilinen PASS ornekleri.
2) Depo: .github/workflows altindaki tum workflow'lar kapidan gecer (0 bulgu).
3) Mutasyon: degisen her workflow'da maske satiri silinince kapi FAIL verir.
4) Gercek adim: degisen maske adimlari bash -e ile sahte olay dosyasiyla kosulur; siparis no stdout'ta yalniz
   '::add-mask::' satirinda gecer, bos girdide maske satiri basilmaz, adim cikis kodu 0.
Sahte siparis no: 9000000123 (CLAUDE.md test serisi). Gercek siparis no YOK.
"""
import glob
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import urllib.request


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(KOK, "scripts", "guvenlik"))
import yaml  # noqa: E402
import receipt_log_kapi as K  # noqa: E402

SAHTE = "9000000123"
HATA = []


def kontrol(ad, kosul):
    print(("PASS " if kosul else "FAIL ") + ad)
    if not kosul:
        HATA.append(ad)


def wf(metin):
    return yaml.safe_load(metin)


GIRDI = """on:
  workflow_dispatch:
    inputs:
      receipt: {required: true}
      fisler: {default: ""}
jobs:
"""

# --- 1) bilinen FAIL / PASS
FAIL_ORNEK = {
    "R1 step env": GIRDI + "  a:\n    steps:\n      - env: {R: \"${{ inputs.receipt }}\"}\n        run: echo ok\n",
    "R1 run metni": GIRDI + "  a:\n    steps:\n      - run: echo \"${{ github.event.inputs.receipt }}\"\n",
    "R1 job env": GIRDI + "  a:\n    env: {R: \"${{ inputs.receipt || '' }}\"}\n    steps:\n      - run: echo ok\n",
    "R1 with": GIRDI + "  a:\n    steps:\n      - uses: x/y@v1\n        with: {r: \"${{ inputs.receipt }}\"}\n",
    "R2 maskesiz okuma": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\")\n          echo \"$r\"\n",
    "R2 maske sonraki adimda": GIRDI + "  a:\n    steps:\n      - run: jq -re '.inputs.receipt' \"$GITHUB_EVENT_PATH\"\n"
                                       "      - run: |\n          r=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"); echo \"::add-mask::$r\"\n",
    "R2 baska degisken maskeli": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"); x=1; echo \"::add-mask::$x\"\n",
    "R2 liste tek parca maske": GIRDI + "  a:\n    steps:\n      - run: |\n          F=$(jq -r .inputs.fisler \"$GITHUB_EVENT_PATH\"); echo \"::add-mask::$F\"\n",
    "R2 ikinci is maskesiz": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"); echo \"::add-mask::$r\"\n"
                                     "  b:\n    steps:\n      - run: jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"\n",
}
PASS_ORNEK = {
    "if icinde ifade serbest": GIRDI + "  a:\n    if: ${{ inputs.receipt != '' }}\n    steps:\n      - run: echo ok\n",
    "okuma + maske": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r '.inputs.receipt // empty' \"$GITHUB_EVENT_PATH\"); [ -z \"$r\" ] || echo \"::add-mask::$r\"\n",
    "liste for maske": GIRDI + "  a:\n    steps:\n      - run: |\n          F=$(jq -r .inputs.fisler \"$GITHUB_EVENT_PATH\"); for f in ${F//,/ }; do echo \"::add-mask::$f\"; done\n",
    "tasiyici girdi yok": "on:\n  workflow_dispatch:\n    inputs:\n      mod: {default: x}\njobs:\n  a:\n    steps:\n      - run: echo \"${{ inputs.mod }}\"\n",
}
for ad, metin in FAIL_ORNEK.items():
    kontrol("bilinen FAIL: " + ad, len(K.denetle_veri(wf(metin), "t.yml")) > 0)
for ad, metin in PASS_ORNEK.items():
    b = K.denetle_veri(wf(metin), "t.yml")
    kontrol("bilinen PASS: " + ad + (" " + str(b) if b else ""), not b)
kontrol("EK: pod-arac-v4 confirm env FAIL",
        len(K.denetle_veri(wf("on:\n  workflow_dispatch:\n    inputs:\n      confirm: {default: ''}\njobs:\n  a:\n"
                              "    env: {C: \"${{ inputs.confirm }}\"}\n    steps:\n      - run: echo ok\n"), "pod-arac-v4.yml")) > 0)
kontrol("EK yalniz pod-arac-v4: baska workflow'da confirm serbest",
        not K.denetle_veri(wf("on:\n  workflow_dispatch:\n    inputs:\n      confirm: {default: ''}\njobs:\n  a:\n"
                              "    env: {C: \"${{ inputs.confirm }}\"}\n    steps:\n      - run: echo ok\n"), "baska.yml"))

# --- 2) depo
tum = []
for p in sorted(glob.glob(os.path.join(KOK, ".github", "workflows", "*.yml"))):
    tum += K.denetle(p)
kontrol("depo: tum workflow'lar kapidan gecer (%d bulgu)" % len(tum), not tum)
for b in tum[:20]:
    print("   ", b)

IKINCI_OKUMA = {("siparis-kisisel-oku.yml", "- name: Token geri yaz + gizli klasore yaz")}
# --- 3) mutasyon: her maske satirinda yalniz '::add-mask::' bozulunca (okuma kalir) FAIL
mut = 0
for p in sorted(glob.glob(os.path.join(KOK, ".github", "workflows", "*.yml"))):
    satirlar = open(p, encoding="utf-8").read().split("\n")
    for i, s in enumerate(satirlar):
        if "IP adim 0 c" in s and "::add-mask::" in s:
            bozuk = "\n".join(satirlar[:i] + [s.replace("::add-mask::", "::maske-yok::")] + satirlar[i + 1:])
            try:
                b = K.denetle_veri(yaml.safe_load(bozuk), os.path.basename(p))
            except yaml.YAMLError:
                b = ["yaml bozuk"]
            mut += 1
            adim = next((x.strip() for x in reversed(satirlar[:i]) if x.strip().startswith("- name:")), "")
            if (os.path.basename(p), adim) in IKINCI_OKUMA:
                # ayni isin ILK okuyan adimi maskeyi zaten kaydetti: bu satir fazladan maske; bulgu olmamasi dogru
                kontrol("mutasyon %s:%d ikinci okuma (maske onceki adimda): bulgu yok" % (os.path.basename(p), i + 1), not b)
                continue
            kontrol("mutasyon %s:%d maske bozulunca FAIL" % (os.path.basename(p), i + 1), len(b) > 0)
kontrol("mutasyon sayisi >= 12 (%d)" % mut, mut >= 12)


# --- 4) gercek adimlar bash -e ile
def adim_run(yol, is_, ad_bas):
    d = yaml.safe_load(open(os.path.join(KOK, ".github", "workflows", yol), encoding="utf-8"))
    for st in d["jobs"][is_]["steps"]:
        if str(st.get("name", "")).startswith(ad_bas):
            return st["run"]
    raise KeyError(yol + " " + ad_bas)


def kos(script, girdiler, env=None):
    with tempfile.TemporaryDirectory() as t:
        olay = os.path.join(t, "olay.json")
        json.dump({"inputs": girdiler}, open(olay, "w"))
        genv = os.path.join(t, "env")
        open(genv, "w").close()
        e = {"PATH": os.environ["PATH"], "GITHUB_EVENT_PATH": olay, "GITHUB_ENV": genv, "HOME": t}
        e.update(env or {})
        r = subprocess.run(["bash", "-e", "-c", script], env=e, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout + r.stderr, open(genv).read()


def yalniz_maskede(cikti, deger):
    return all(("::add-mask::" in s) for s in cikti.splitlines() if deger in s)


# pod-arac-v4 Girdi maskesi
s = adim_run("pod-arac-v4.yml", "fiyat", "Girdi maskesi")
rc, out, genv = kos(s, {"siparis_ref": "etsy-%s-8x10" % SAHTE, "confirm": "etsy-%s-8x10" % SAHTE,
                        "siparis_alici": "Ada Test|1 Ornek Sk|Izmir||35000|TR"}, {"MOD": "siparis_gonder"})
kontrol("pod-arac-v4 maske adimi rc 0", rc == 0)
kontrol("pod-arac-v4: siparis no yalniz maske satirinda", yalniz_maskede(out, SAHTE) and "::add-mask::%s" % SAHTE in out)
kontrol("pod-arac-v4: ref + alici parcalari maskeli", "::add-mask::etsy-%s-8x10" % SAHTE in out and "::add-mask::Ada Test" in out
        and "::add-mask::1 Ornek Sk" in out)
kontrol("pod-arac-v4: GITHUB_ENV SIPARIS_REF/CONFIRM/SIPARIS_ALICI", "SIPARIS_REF=etsy-%s-8x10" % SAHTE in genv
        and "CONFIRM=etsy-%s-8x10" % SAHTE in genv and "SIPARIS_ALICI=Ada Test|" in genv)
rc, out, genv = kos(s, {"confirm": "PILOT_15"}, {"MOD": "pilot15_yaz"})
kontrol("pod-arac-v4 bos ref: varsayilan + PILOT_15 maskelenmez", rc == 0 and "SIPARIS_REF=etsy-1000000001-8x10" in genv
        and "::add-mask::PILOT_15" not in out and "CONFIRM=PILOT_15" in genv)

# kupa-siparis: RID satiri (adimin ilk satiri) tek basina
s = adim_run("kupa-siparis.yml", "uret", "Uret").split("\n")[0]
rc, out, _ = kos(s + "\necho \"RID_SON=${RID}\"", {"receipt_id": SAHTE})
kontrol("kupa-siparis RID olay dosyasindan + maske", rc == 0 and "::add-mask::%s" % SAHTE in out and "RID_SON=%s" % SAHTE in out)
rc, out, _ = kos(s + "\necho \"RID_SON=${RID}\"", {"receipt_id": ""})
kontrol("kupa-siparis bos RID: maske yok, rc 0", rc == 0 and "::add-mask::" not in out and "RID_SON=\n" in out + "\n")

# wa-hazirlik-oku Girdi
s = adim_run("wa-hazirlik-oku.yml", "onizle", "Girdi")
rc, out, genv = kos(s, {"fisler": "%s,9000000124" % SAHTE}, {"P": "20261117_120000", "N": ""})
kontrol("wa-hazirlik-oku Girdi rc 0 + her fis maskeli + F GITHUB_ENV", rc == 0 and "::add-mask::%s" % SAHTE in out
        and "::add-mask::9000000124" in out and "F=%s,9000000124" % SAHTE in genv)
rc, out, genv = kos(s, {"fisler": "12a"}, {"P": "20261117_120000", "N": ""})
kontrol("wa-hazirlik-oku Girdi bozuk fis FAIL", rc != 0)

# siparis-kesit-son Girdi
s = adim_run("siparis-kesit-son.yml", "kesit", "Girdi")
rc, out, _ = kos(s, {"receipt": SAHTE})
kontrol("siparis-kesit-son Girdi rc 0 + maske", rc == 0 and yalniz_maskede(out, SAHTE) and "::add-mask::%s" % SAHTE in out)
rc, out, _ = kos(s, {"receipt": "12x"})
kontrol("siparis-kesit-son Girdi rakam disi FAIL", rc != 0)

# _m satiri (siparis-dijital / giris / pdf-sayfa / kesit-birlesik / wp-kayma-tani ile ayni metin)
ms = [s for p in glob.glob(os.path.join(KOK, ".github", "workflows", "*.yml"))
      for s in open(p, encoding="utf-8").read().split("\n") if "_m=$(jq -r '.inputs.receipt // empty'" in s]
kontrol("_m satiri >= 12 yerde (%d)" % len(ms), len(ms) >= 12)
rc, out, _ = kos(ms[0].strip(), {"receipt": SAHTE})
kontrol("_m satiri maske basar", rc == 0 and out.strip() == "::add-mask::%s" % SAHTE)
rc, out, _ = kos(ms[0].strip(), {})
kontrol("_m satiri girdi yokken sessiz, rc 0", rc == 0 and out.strip() == "")
kontrol("_m satirlari ozdes (yorum haric)", len(set(x.split("#")[0].strip() for x in ms)) == 1)

print("receipt_log_kapi testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
