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
    "R2 maskeden once echo (ayni adim)": GIRDI + "  a:\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\")\n          echo \"rec $R\"\n          echo \"::add-mask::$R\"\n",
    "R2 ayni satirda baska degisken maskeli": GIRDI + "  a:\n    steps:\n      - run: |\n          C=$(jq -r .inputs.cift \"$E\"); R=$(jq -r .inputs.receipt \"$E\")\n          echo \"::add-mask::$C\"\n          echo \"$R\"\n",
    "R0 olay dosyasi cat": GIRDI + "  a:\n    steps:\n      - run: cat \"$GITHUB_EVENT_PATH\"\n      - run: |\n          R=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"); echo \"::add-mask::$R\"\n",
    "R0 toJSON(inputs)": GIRDI + "  a:\n    steps:\n      - env: {A: \"${{ toJSON(inputs) }}\"}\n        run: echo hi\n",
    "R0 inputs['receipt']": GIRDI + "  a:\n    steps:\n      - env: {A: \"${{ inputs['receipt'] }}\"}\n        run: echo $A\n",
    "R2 calismayan maske (&&)": GIRDI + "  a:\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt \"$E\"); [ -n \"\" ] && echo \"::add-mask::$R\"; echo $R\n",
    "R0 Python olay okuma maskesiz": GIRDI + "  a:\n    steps:\n      - run: python3 -c \"import json,os;print(json.load(open(os.environ['GITHUB_EVENT_PATH']))['inputs']['receipt'])\"\n",
    "R0 toJSON(github.event.inputs)": GIRDI + "  a:\n    steps:\n      - env: {A: \"${{ toJSON(github.event.inputs) }}\"}\n        run: echo $A\n",
    "R0 set -x": GIRDI + "  a:\n    steps:\n      - run: |\n          set -x\n          R=$(jq -r .inputs.receipt \"$E\"); echo \"::add-mask::$R\"\n",
    "R2 if icinde maske": GIRDI + "  a:\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt \"$E\"); if false; then echo \"::add-mask::$R\"; fi\n",
    "R3 sinifsiz siparis girdisi": "on:\n  workflow_dispatch:\n    inputs:\n      no: {description: \"Etsy receipt id\"}\njobs:\n  a:\n    steps:\n      - run: echo ok\n",
    "R2 ikinci is maskesiz": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"); echo \"::add-mask::$r\"\n"
                                     "  b:\n    steps:\n      - run: jq -r .inputs.receipt \"$GITHUB_EVENT_PATH\"\n",
}
# Bagimsiz inceleme 2. tur (e760ddc) 37 atlatma ornegi (29 printf ve 38 onekli maskeli deger sizinti degil, haric)
INCELEME2 = {'inceleme2 01 bare jq print before masked assign': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          jq -r .inputs.receipt "$GITHUB_EVENT_PATH"\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH"); echo "::add-mask::$R"\n', 'inceleme2 02 jq -r .inputs whole object': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: jq -r \'.inputs\' "$GITHUB_EVENT_PATH"\n', 'inceleme2 03 jq -c . event': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: jq -c . "$GITHUB_EVENT_PATH"\n', 'inceleme2 04 jq "." dq': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: jq "." "$GITHUB_EVENT_PATH"\n', 'inceleme2 05 redirect < event jq .': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: jq . < "$GITHUB_EVENT_PATH"\n', 'inceleme2 06 head/grep event': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: grep -o \'"receipt"[^,]*\' "$GITHUB_EVENT_PATH"\n', 'inceleme2 07 toJSON(github.event)': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - env: {E: "${{ toJSON(github.event) }}"}\n        run: echo ok\n', 'inceleme2 08 toJSON(github)': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo \'${{ toJSON(github) }}\'\n', 'inceleme2 09 jq .inputs["receipt"]': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo "$(jq -r \'.inputs["receipt"]\' "$GITHUB_EVENT_PATH")"\n', 'inceleme2 10 jq to_entries': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: jq -r \'.inputs|to_entries[]|.value\' "$GITHUB_EVENT_PATH"\n', 'inceleme2 11 multiline if mask': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          if [ -n "$Z" ]; then\n            echo "::add-mask::$R"\n          fi\n          echo "$R"\n', 'inceleme2 12 mask in multiline function never called': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          m() {\n            echo "::add-mask::$R"\n          }\n          echo "$R"\n', 'inceleme2 13 mask in heredoc text': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          cat <<X\n          echo "::add-mask::$R"\n          X\n', 'inceleme2 14 tee in substitution': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH" | tee /dev/stderr); echo "::add-mask::$R"\n', 'inceleme2 15 export + env before mask': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          export R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          env\n          echo "::add-mask::$R"\n', 'inceleme2 16 first reader step skipped by if': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - if: false\n        run: |\n            R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH"); echo "::add-mask::$R"\n      - run: jq -r .inputs.receipt "$GITHUB_EVENT_PATH"\n', 'inceleme2 17 python exemption via comment': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          python3 - <<\'X\'\n          import json, os\n          # \'::add-mask::\' \'receipt\' \'fisler\'\n          print(json.load(open(os.environ[\'GITHUB_EVENT_PATH\'])))\n          X\n', 'inceleme2 18 python script with path arg': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python3 -c \'import sys;print(open(sys.argv[1]).read())\' "$GITHUB_EVENT_PATH"\n', 'inceleme2 19 github-script payload': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/github-script@v7\n        with:\n          script: core.info(context.payload.inputs.receipt)\n', 'inceleme2 20 defaults shell bash -x': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\ndefaults:\n  run:\n    shell: bash -x {0}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH"); echo "::add-mask::$R"\n', 'inceleme2 21 step shell bash -ex': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - shell: bash -ex {0}\n        run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH"); echo "::add-mask::$R"\n', 'inceleme2 22 mask && on previous line (continuation)': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          false &&\n            echo "::add-mask::$R"\n          echo "$R"\n', 'inceleme2 23 ${{ github.event.inputs }} bare': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo \'${{ github.event.inputs }}\'\n', "inceleme2 24 R3 desc 'Siparis numarasi'": 'on:\n  workflow_dispatch:\n    inputs:\n      order: {description: \'Etsy siparis numarasi\'}\njobs:\n  a:\n    steps:\n      - run: echo "${{ inputs.order }}"\n', "inceleme2 25 R3 desc 'order id'": 'on:\n  workflow_dispatch:\n    inputs:\n      order: {description: \'Etsy order id\'}\njobs:\n  a:\n    steps:\n      - run: echo "${{ inputs.order }}"\n', 'inceleme2 26 workflow_call receipt': 'on:\n  workflow_call:\n    inputs:\n      receipt: {type: string}\njobs:\n  a:\n    steps:\n      - run: echo "${{ inputs.receipt }}"\n', 'inceleme2 27 SHELLOPTS env xtrace': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    env: {SHELLOPTS: xtrace}\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH"); echo "::add-mask::$R"\n', 'inceleme2 28 eval/case conditional': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\n      fisler: {default: ""}\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: |\n          R=$(jq -r .inputs.receipt "$GITHUB_EVENT_PATH")\n          case x in y)\n            echo "::add-mask::$R";;\n          esac\n          echo "$R"\n', "inceleme2 30 format('{0}', inputs.receipt)": 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    steps:\n      - run: echo "${{ format(\'{0}\', inputs.receipt) }}"\n', "inceleme2 31 format('{0}', toJSON(inputs))": "on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    steps:\n      - run: echo '${{ format('{0}', toJSON(inputs)) }}'\n", 'inceleme2 32 run-name': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\nrun-name: "x ${{ github.event.inputs.receipt }}"\njobs:\n  a:\n    steps:\n      - run: echo ok\n', 'inceleme2 33 concurrency': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\nconcurrency: {group: "g-${{ inputs.receipt }}"}\njobs:\n  a:\n    steps:\n      - run: echo ok\n', 'inceleme2 34 workflow env': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\nenv: {R: "${{ inputs.receipt }}"}\njobs:\n  a:\n    steps:\n      - run: echo ok\n', 'inceleme2 35 reusable with': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    uses: ./.github/workflows/x.yml\n    with: {r: "${{ inputs.receipt }}"}\n', 'inceleme2 36 if: with side-effect? (job name)': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    name: "job ${{ inputs.receipt }}"\n    steps:\n      - run: echo ok\n', 'inceleme2 37 multi-line $( ) then printf leak': 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    steps:\n      - run: |\n          R=$(\n            jq -r .inputs.receipt "$GITHUB_EVENT_PATH"\n          )\n          printf \'%s\\n\' "$R"\n', "inceleme2 39 jq -r '.inputs' | jq -r .receipt": 'on:\n  workflow_dispatch:\n    inputs:\n      receipt: {required: true}\njobs:\n  a:\n    steps:\n      - run: jq -r \'.inputs\' "$GITHUB_EVENT_PATH" | jq -r .receipt\n'}
PASS_ORNEK = {
    "if icinde ifade serbest": GIRDI + "  a:\n    if: ${{ inputs.receipt != '' }}\n    steps:\n      - run: echo ok\n",
    "okuma + maske": GIRDI + "  a:\n    steps:\n      - run: |\n          r=$(jq -r '.inputs.receipt // empty' \"$GITHUB_EVENT_PATH\"); [ -z \"$r\" ] || echo \"::add-mask::$r\"\n",
    "liste for maske": GIRDI + "  a:\n    steps:\n      - run: |\n          F=$(jq -r .inputs.fisler \"$GITHUB_EVENT_PATH\"); for f in ${F//,/ }; do echo \"::add-mask::$f\"; done\n",
    "kosullu koruma [ -z ] ||": GIRDI + "  a:\n    steps:\n      - run: |\n          R=$(jq -r '.inputs.receipt // empty' \"$E\"); [ -z \"$R\" ] || echo \"::add-mask::$R\"; echo \"$R\"\n",
    "liste while maske": GIRDI + "  a:\n    steps:\n      - run: |\n          F=$(jq -r '.inputs.fisler' \"$E\")\n          while IFS= read -r f; do [ -z \"$f\" ] || echo \"::add-mask::$f\"; done < <(tr ',' '\\n' <<< \"$F\")\n",
    "shell jq .inputs[$k] (ifade degil)": GIRDI + "  a:\n    steps:\n      - run: |\n          for k in a b; do jq -re --arg k \"$k\" '.inputs[$k]' \"$E\"; done\n",
    "Python okuma + her tasiyici maskeli": GIRDI + "  a:\n    steps:\n      - run: |\n          python3 - <<'X'\n          import json, os\n          i = json.load(open(os.environ['GITHUB_EVENT_PATH']))['inputs']\n          for k in ('receipt', 'fisler'):\n              print('::add-mask::' + str(i.get(k)))\n          X\n",
    "tasiyici girdi yok": "on:\n  workflow_dispatch:\n    inputs:\n      mod: {default: x}\njobs:\n  a:\n    steps:\n      - run: echo \"${{ inputs.mod }}\"\n",
}
FAIL_ORNEK.update(INCELEME2)
FAIL_ORNEK["v3 liste for dongusu (izin listesinde yok)"] = PASS_ORNEK.pop("liste for maske")
FAIL_ORNEK["v3 Python okuma (sha ile onayli degil)"] = PASS_ORNEK.pop("Python okuma + her tasiyici maskeli")
FAIL_ORNEK["C2 secim girdisi seceneginde 10 haneli sayi"] = ("on:\n  workflow_dispatch:\n    inputs:\n      mode: {type: choice, options: [a, '9000000123'],"
                                                         " description: 'receipt secimi'}\njobs:\n  a:\n    steps:\n      - run: echo ok\n")
PASS_ORNEK["C2 secim girdisi (aciklamada receipt kelimesi) serbest"] = ("on:\n  workflow_dispatch:\n    inputs:\n      mode: {type: choice, options: [a, b],"
                                                                    " description: 'merchantReference siparis_oku'}\njobs:\n  a:\n    steps:\n      - run: echo ok\n")
for ad, metin in FAIL_ORNEK.items():
    kontrol("bilinen FAIL: " + ad, len(K.denetle_veri(wf(metin), "t.yml")) > 0)
for ad, metin in PASS_ORNEK.items():
    b = K.denetle_veri(wf(metin), "t.yml")
    kontrol("bilinen PASS: " + ad + (" " + str(b) if b else ""), not b)
_d = K.denetle_veri(wf("on:\n  workflow_dispatch:\n    inputs:\n      skus: {default: ''}\njobs:\n  a:\n    env: {S: \"${{ inputs.skus }}\"}\n"
                       "    steps:\n      - run: echo ok\n"), "prodigi-quote.yml")
kontrol("EK: prodigi-quote skus tasiyici (env FAIL)", len(_d) > 0)
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

IKINCI_OKUMA = {("siparis-kisisel-oku.yml", "- name: Token geri yaz + gizli klasore yaz"),
                ("by-siparis-ornek.yml", "- name: Uret + kontrol (PASS/FAIL)")}   # ilk maske onayli Python adiminda
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
def env_oku(genv):
    """GITHUB_ENV ayracli bicim (AD<<AYRAC / deger / AYRAC) -> dict."""
    d, s = {}, genv.split("\n")
    i = 0
    while i < len(s):
        if "<<" in s[i]:
            ad, ay = s[i].split("<<", 1)
            j = s.index(ay, i + 1)
            d[ad] = "\n".join(s[i + 1:j])
            i = j + 1
        else:
            i += 1
    return d


g = env_oku(genv)
kontrol("pod-arac-v4: GITHUB_ENV SIPARIS_REF/CONFIRM/SIPARIS_ALICI (ayracli)", g.get("SIPARIS_REF") == "etsy-%s-8x10" % SAHTE
        and g.get("CONFIRM") == "etsy-%s-8x10" % SAHTE and g.get("SIPARIS_ALICI", "").startswith("Ada Test|"))
kontrol("pod-arac-v4: 4 harften kisa alici parcasi maskelenmez (TR)", "::add-mask::TR\n" not in out + "\n")
rc, out, genv = kos(s, {"confirm": "PILOT_15"}, {"MOD": "pilot15_yaz"})
g = env_oku(genv)
kontrol("pod-arac-v4 bos ref: varsayilan; onay kelimesi aynen GITHUB_ENV'de", rc == 0 and g.get("SIPARIS_REF") == "etsy-1000000001-8x10"
        and g.get("CONFIRM") == "PILOT_15" and g.get("SIPARIS_ALICI") == "")
rc, out, genv = kos(s, {"siparis_alici": "Ada\nSAHTE=1|x"}, {"MOD": "kuru"})
g = env_oku(genv)
kontrol("pod-arac-v4: girdideki yeni satir ek degisken yazamaz", rc == 0 and "SAHTE" not in g and g.get("SIPARIS_ALICI", "").startswith("Ada\nSAHTE=1"))

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
rc, out, genv = kos(s, {}, {"P": "20261117_120000", "N": ""})
kontrol("wa-hazirlik-oku Girdi: fisler yoksa girdi varsayilani (inputs.fisler ile ayni)", rc == 0
        and "F=9000000531,9000000522,9000000523,9000000524,9000000525" in genv)
rc, out, genv = kos(s, {"fisler": "12a"}, {"P": "20261117_120000", "N": ""})
kontrol("wa-hazirlik-oku Girdi bozuk fis FAIL", rc != 0)

# pod-order-router Girdiler: submit olay dosyasindan + maske; R_SUBMIT GITHUB_ENV'de
s = adim_run("pod-order-router.yml", "route", "Girdiler")
rc, out, genv = kos(s, {"submit": SAHTE}, {"EV": "workflow_dispatch", "IN_APPROVE": "", "IN_ENV": "", "IN_DAYS": "", "IN_TR": "",
                                           "IN_EW": "", "IN_ONLY": "", "IN_OTO": "", "IN_MAX": ""})
kontrol("pod-order-router submit maskeli + R_SUBMIT", rc == 0 and out.splitlines()[0] == "::add-mask::%s" % SAHTE
        and "R_SUBMIT=%s" % SAHTE in genv and "R_APPROVE=off" in genv)
rc, out, genv = kos(s, {}, {"EV": "schedule"})
kontrol("pod-order-router cron: submit yok, maske yok", rc == 0 and "::add-mask::" not in out and "R_SUBMIT=\n" in genv)
# a3-esit-kiyas: ilk 3 satir (maske) bash ile
s = "\n".join(adim_run("a3-esit-kiyas.yml", "kiyas", "Indir").split("\n")[:3])
rc, out, _ = kos(s, {"eski": SAHTE, "yeni": "9000000124", "taban": "9000000102,9000000103,9000000104"})
kontrol("a3-esit-kiyas eski/yeni/taban maskeli", rc == 0 and all("::add-mask::%s" % v in out for v in
        (SAHTE, "9000000124", "9000000102", "9000000103", "9000000104")) and yalniz_maskede(out, SAHTE))

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
