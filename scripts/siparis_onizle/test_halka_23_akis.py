#!/usr/bin/env python3
"""2:3 ailesi + siparis-giris akis testi (19 Kas aksam, GOREV_CEO_DENETIM_HALKA_KALICI_3 C1 + C2; Serdar KARARLAR_20261119_25 secenek a).
Ag kapali, sahte veri (sahte receipt 900000001, gercek goruntu YOK). Gercek kod kosar:
  1) halka_kapi.kapi 2:3 olculerde: 12x18 BASKI tam piksel (3600x5400) ve 24x36 ONIZLEME (1333x2000) sentetik kaynak; temiz kaynak PASS,
     kaynaginda halka olan (mutlak bant 0.10-0.13, kodlama bandi temiz) FAIL: tavan 0.13 ve ustune gevsetilirse (19 Kas TAVAN_23 0.16 gibi) test duser.
  2) siparis-giris.yml `yeni` isinin GERCEK adim metinleri (yaml'dan okunur) bash -e ile, sahte arac (rclone, python) PATH / yol yerine
     konarak: bayrak karari (MB 24x36 baski = acik, MB 24x36 dijital = kapali, baska renk = kapali), teslim zorunlu (yoksa `yeni` durur),
     Kapilar adimi (halka FAIL -> HALKA_RC=1 + ::error + adim ozeti), Drive'a yaz (HALKA_RC=1 / tanimsiz+bayrak -> AstroLoveArt YUKLENMEZ;
     0 -> yuklenir), Sonuc adimi (HALKA_RC=1 -> is kirmizi).
  3) siparis-yardimci.yml siparis_v2 Girdi adimi: 2:3 (24x36) artik reddedilmez; Digital Format yine reddedilir.
Adim metninde yalniz MUTLAK yollar test dizinine cevrilir (/tmp/is, /tmp/g, /tmp/vo/bin/python, /home/claude/blender/venv/bin/python);
mantik satirlari degistirilmez."""
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok
B = Path(__file__).resolve().parent
KOK = B.parents[1]
sys.path.insert(0, str(B)); sys.path.insert(0, str(B / "halka_yama"))
import halka_kapi as HK  # noqa: E402
import halka_kodla as KD  # noqa: E402
import zemin_duzelt as Z  # noqa: E402

HATA = []
AGSIZ = ("import socket\ndef _ag(*a, **k):\n    raise AssertionError('gercek ag acilmaya calisildi')\n"
         "socket.socket.connect = _ag; socket.create_connection = _ag\n")


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


# ---------- 1) halka_kapi, 2:3 olculer ----------
def kaynak(olcu, W, H, halka):
    """Sentetik koyu mavi radyal zemin + altin yay + kanal basina gren (test_halka_kapi ile ayni kurgu, olcuye olceklenmis)."""
    cx, cy, _ = Z.merkez(olcu); s = W / Z.OLCU[olcu][0]; cx, cy = cx * s, cy * s; k = W / 3300
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); r = np.hypot(xx - cx, yy - cy)
    a = np.empty((H, W, 3), np.float32)
    a[..., 0] = 4 + 6 * np.exp(-r / (900 * k)); a[..., 1] = 6 + 10 * np.exp(-r / (900 * k)); a[..., 2] = 20 + 40 * np.exp(-r / (900 * k))
    if halka:
        a[..., 2] += halka * np.sin(2 * np.pi * r / (180 * k)) * (r < 1500 * k)
    yay = (np.abs(r - 1100 * k) < 6 * k) & (yy < cy); a[yay] = (212, 160, 50)
    a += np.random.default_rng(3).standard_normal(a.shape).astype(np.float32) * 1.5
    return np.clip(a, 0, 255)


with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    for olcu, tur, (W, H) in (("12x18", "baski", Z.OLCU["12x18"]), ("24x36", "onizleme", (1333, 2000))):
        for ad, h, bek in (("temiz kaynak", 0.0, True), ("TAVAN KENARI: kaynaginda halka, mutlak bant 0.10-0.13 (tavan gevsetilirse test duser)", 0.19, False)):
            src = kaynak(olcu, W, H, h); y = td / f"{olcu}_{tur}_{h}.jpg"
            KD.kaynak_yaz(src, y); KD.ycc_kaydet(src, y, np.random.default_rng(7)); del src
            r = HK.kapi(y, olcu, td / "o", tur, kaynak=KD.kaynak_yolu(y))
            hb, kb = r.get("halka_bant"), r.get("kodlama_bant")
            if bek:
                ok = r["PASS"] is True and hb is not None and hb <= HK.TAVAN[tur] and kb is not None and kb <= HK.kodlama_esigi(tur, W, H)
            else:                                                    # kodlama temiz, FAIL'i yalniz TAVAN verir (karar 3 siniri)
                ok = r["PASS"] is False and hb is not None and HK.TAVAN[tur] < hb < 0.13 and kb is not None and kb <= HK.kodlama_esigi(tur, W, H)
            print(f"  olcum 2:3 {olcu} {tur}: halka_bant {hb} kodlama_bant {kb}")
            kontrol(f"2:3 {olcu} {tur} {W}x{H}: {ad} -> {'PASS' if bek else 'FAIL'}", ok, f"PASS {r['PASS']} halka_bant {hb} kodlama {kb} hata {r.get('hata')}")
kontrol("esikler degismedi: baski 0.020 (5 MP alti 0.030), onizleme 0.040, tavan 0.10 her tur",
        HK.KODLAMA_ESIK == {"baski": 0.020, "onizleme": 0.040} and HK.KODLAMA_ESIK_KUCUK_BASKI == 0.030 and HK.TAVAN == {"baski": 0.10, "onizleme": 0.10})

# 1b) sozlesme (inceleme D 2. tur DUSUK 1): halka_kapi.py CLI (gercek __main__, alt surec, ag kapali) ciktisi -> halka_neden.neden
import halka_neden as HN  # noqa: E402
with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    for ad, h, bek in (("temiz", 0.0, "onizleme: PASS"), ("tavan ustu", 0.35, "onizleme: TAVAN (mutlak halka 0.")):
        src = kaynak("24x36", 1333, 2000, h); y = td / f"cli_{h}.jpg"; KD.kaynak_yaz(src, y); KD.ycc_kaydet(src, y, np.random.default_rng(8))
        kod = AGSIZ + "import runpy, sys\nsys.argv = %r\nsys.path.insert(0, %r)\nrunpy.run_path(%r, run_name='__main__')\n" % (
            [str(B / "halka_kapi.py"), str(y), "24x36", str(td / "o"), "--tur", "onizleme", "--kaynak", str(KD.kaynak_yolu(y))], str(B), str(B / "halka_kapi.py"))
        r = subprocess.run([sys.executable, "-I", "-c", kod], capture_output=True, text=True, timeout=300)
        (td / "h_onizleme.log").write_text(r.stdout + r.stderr)
        n = HN.neden(td / "h_onizleme.log")
        kontrol(f"sozlesme halka_kapi CLI -> halka_neden: {ad} -> '{bek}...' (cikis {'0' if h == 0 else '1'})", n.startswith(bek) and r.returncode == (0 if h == 0 else 1), f"rc {r.returncode} {n} {r.stderr[-200:]}")

# ---------- 2) siparis-giris `yeni` isi adimlari ----------
GIRIS = yaml.safe_load((KOK / ".github/workflows/siparis-giris.yml").read_text())["jobs"]["yeni"]["steps"]


def adim(bas):
    return next(s for s in GIRIS if s.get("name", "").startswith(bas))["run"]


SAHTE_RCLONE = r'''#!/bin/bash
# sahte rclone: her cagri $SAHTE_LOG'a tek satir; copy kaynak dizindeki --include kalibina uyan dosyalari hedef dizine (yerel) kopyalar
echo "$*" >> "$SAHTE_LOG"
cmd="$1"; shift
case "$cmd" in
  copy) src="$1"; case "$2" in /*) dst="$2";; *) dst="$SAHTE_KOK/$(printf %s "$2" | tr -c 'A-Za-z0-9_.\n' '_')";; esac; mkdir -p "$dst"; shift 2; inc=()
        while [ $# -gt 0 ]; do case "$1" in --include) inc+=("$2"); shift 2;; --exclude|--max-depth) shift 2;; *) shift;; esac; done
        [ -d "$src" ] || exit 0
        for p in "${inc[@]}"; do for f in "$src"/$p; do [ -f "$f" ] && cp "$f" "$dst"/; done; done; exit 0 ;;
  lsl) exit 0 ;;
  lsf) [ -n "${SAHTE_LSF:-}" ] && printf '%s\n' $SAHTE_LSF; exit 0 ;;
  *) echo "sahte rclone: bilinmeyen $cmd" >&2; exit 2 ;;
esac
'''


AGSIZ_PY3 = AGSIZ + r'''import runpy, sys
a = sys.argv[1:]
if a[:1] == ["-c"]:
    sys.argv = ["-c"] + a[2:]; exec(compile(a[1], "<-c>", "exec"), {"__name__": "__main__"})
else:
    sys.argv = a; runpy.run_path(a[0], run_name="__main__")
'''


def calis(metin, env_ek, d, bash_e=True):
    (d / "bin").mkdir(exist_ok=True)
    (d / "bin" / "rclone").write_text(SAHTE_RCLONE); (d / "bin" / "rclone").chmod(0o755)
    (d / "agsiz_py3.py").write_text(AGSIZ_PY3)                 # alt surec python3 da ag kapali (TEST AGI)
    (d / "bin" / "python3").write_text(f'#!/bin/bash\nexec {sys.executable} -I {d / "agsiz_py3.py"} "$@"\n'); (d / "bin" / "python3").chmod(0o755)
    (d / "adim.sh").write_text(metin)
    for f in ("env", "ozet", "rclone.log"):
        (d / f).touch()
    env = {"PATH": f"{d / 'bin'}:{os.environ.get('PATH', '')}", "GITHUB_ENV": str(d / "env"), "GITHUB_STEP_SUMMARY": str(d / "ozet"),
           "SAHTE_LOG": str(d / "rclone.log"), "SAHTE_KOK": str(d / "drive"), "GITHUB_RUN_ID": "1", "HOME": str(d)}
    env.update(env_ek)
    arg = ["bash", "--noprofile", "--norc"] + (["-e"] if bash_e else []) + [str(d / "adim.sh")]
    r = subprocess.run(arg, cwd=d, capture_output=True, text=True, env=env, timeout=60)
    genv = dict(s.split("=", 1) for s in (d / "env").read_text().splitlines() if "=" in s)
    return r.returncode, r.stdout + r.stderr, genv, (d / "ozet").read_text(), (d / "rclone.log").read_text()


# 2a) bayrak karari + teslim zorunlu: "Kaynak indir" adiminin TT= satirindan sonuna kadar (oncesi indirme / kurulum: ag, sudo)
kaynak_adim = adim("Kaynak indir")
BAYRAK = "set -euo pipefail\n" + kaynak_adim[kaynak_adim.index("TT=$(jq"):]
kontrol("bayrak bolumu ALTI23 ya da 2:3 dislamasi icermiyor", "ALTI23" not in kaynak_adim and "12x18 16x24 20x30 24x36" not in BAYRAK.split("then")[0])


def bayrak(renk, olcu, teslim):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); hy = d / "ops/scripts/siparis_onizle/halka_yama"; hy.mkdir(parents=True)
        (hy / "bindir.sh").write_text(f'#!/bin/bash\ntouch "{d}/bindirildi"\n')
        ev = {"inputs": {} if teslim is None else {"teslim": teslim}}; (d / "olay.json").write_text(json.dumps(ev))
        rc, out, genv, _, _ = calis(BAYRAK, {"GITHUB_EVENT_PATH": str(d / "olay.json"), "RENK": renk, "OLCU": olcu, "GITHUB_WORKSPACE": str(d)}, d)
        return rc, out, genv, (d / "bindirildi").exists()


for renk, olcu, tes, acik in (("MIDNIGHT_BLUE", "24x36", "baski", True), ("MIDNIGHT_BLUE", "12x18", "baski", True), ("MIDNIGHT_BLUE", "16x24", "baski", True),
                              ("MIDNIGHT_BLUE", "20x30", "baski", True), ("MIDNIGHT_BLUE", "11x14", "baski", True), ("MIDNIGHT_BLUE", "24x36", "dijital", False),
                              ("MIDNIGHT_BLUE", "12x16", "dijital", False), ("MIDNIGHT_BLUE", "11x14", "dijital", True), ("MIDNIGHT_BLUE", "5x7", "dijital", True),
                              ("DEEP_BLACK", "24x36", "baski", False), ("PURE_WHITE", "11x14", "baski", False), ("MIDNIGHT_BLUE", "", "baski", False)):
    rc, out, genv, bnd = bayrak(renk, olcu, tes)
    ok = rc == 0 and genv.get("TESLIM_TUR") == tes and (genv.get("HALKA_DUZELT") == "1") is acik and bnd is acik
    if renk == "MIDNIGHT_BLUE" and olcu and not acik:
        ok = ok and "::warning title=HALKA::" in out and "dijitalde q100 > 20 MB" in out
    if acik:
        ok = ok and "::notice title=HALKA::" in out
    kontrol(f"bayrak {renk} {olcu or '(bos)'} {tes}: {'ACIK' if acik else 'KAPALI'}", ok, f"rc {rc} env {genv} bindir {bnd} {out[-200:]}")
for ad, tes in (("teslim yok", None), ("teslim gecersiz", "posta")):
    rc, out, genv, bnd = bayrak("MIDNIGHT_BLUE", "24x36", tes)
    kontrol(f"teslim zorunlu: {ad} -> `yeni` durur (cikis != 0, ::error, bayrak yok)", rc != 0 and "::error::teslim girdisi zorunlu" in out
            and "HALKA_DUZELT" not in genv and not bnd, f"rc {rc} {out[-200:]}")

# 2b) Kapilar adimi (halka kapisi kismi): sahte python (siparis_kapi / halka_kapi cikis kodu ortamdan)
SAHTE_PY = r'''#!/bin/bash
case "$*" in
  *siparis_kapi.py*) echo '{}' > "$IS/KAPI.json"; exit "${KAPI_SAHTE_RC:-0}" ;;
  *halka_kapi.py*) echo "$*" >> "$IS/halka_cagri.log"
    case "${HALKA_SAHTE_MOD:-tavan}" in
      cok) echo "Traceback: sahte cokme" ;;
      kodlama) echo 'HALKA_KAPI {"PASS": false, "halka_bant": 0.05, "tavan": 0.1, "kodlama_bant": 0.031, "kodlama_esik": 0.02}' ;;
      *) [ "${HALKA_SAHTE_RC:-0}" = "0" ] && echo 'HALKA_KAPI {"PASS": true, "halka_bant": 0.05, "tavan": 0.1, "kodlama_bant": 0.01, "kodlama_esik": 0.02}' \
           || echo 'HALKA_KAPI {"PASS": false, "halka_bant": 0.1316, "tavan": 0.1, "kodlama_bant": 0.0144, "kodlama_esik": 0.02}' ;;
    esac
    exit "${HALKA_SAHTE_RC:-0}" ;;
  *) echo "sahte python: beklenmeyen $*" >&2; exit 3 ;;
esac
'''


def kapilar(halka_rc, duzelt, atla="", mod="tavan"):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); IS = d / "is"; (IS / "son").mkdir(parents=True); py = d / "py"; py.write_text(SAHTE_PY); py.chmod(0o755)
        (d / "ops").symlink_to(KOK)                                  # adim ops/scripts/siparis_onizle/halka_neden.py cagirir (gercek betik)
        metin = adim("Kapilar").replace("/home/claude/blender/venv/bin/python", str(py)).replace("/tmp/is", str(IS))
        assert "/tmp/is" not in metin and "/home/claude/blender/venv/bin/python" not in metin
        env = {"IS": str(IS), "RENK": "MIDNIGHT_BLUE", "CIFT": "CANCER_LEO", "OLCU": "24x36", "TESLIM_TUR": "baski", "HALKA_SAHTE_RC": str(halka_rc),
               "HALKA_KAPI_ATLA": atla, "HALKA_SAHTE_MOD": mod}
        if duzelt:
            env["HALKA_DUZELT"] = "1"
        rc, out, genv, ozet, _ = calis(metin, env, d)
        cagri = (IS / "halka_cagri.log").read_text() if (IS / "halka_cagri.log").exists() else ""
        return rc, out, genv, ozet, cagri


rc, out, genv, ozet, cagri = kapilar(1, True)
satir = {("baski" if "--tur baski" in s else "onizleme"): s for s in cagri.splitlines()}
kontrol("Kapilar: halka FAIL (tavan) -> HALKA_RC=1, ::error + ozet nedeni TAVAN, baski + onizleme kapisi cagrildi",
        rc == 0 and genv.get("HALKA_RC") == "1" and "::error title=HALKA KAPISI FAIL::" in out and "Neden: baski: TAVAN (mutlak halka 0.1316 > 0.1" in out
        and "Halka kapisi FAIL" in ozet and "Neden: baski: TAVAN" in ozet and len(satir) == 2, f"rc {rc} env {genv} {out[-400:]}")
kontrol("Kapilar: kaynak (_REF) dosya adi sozlesmesi: baski -> son/<CIFT>_teslim_REF.png, onizleme -> son/<CIFT>_teslim_Preview_REF.png (inceleme D DUSUK 2)",
        satir.get("baski", "").rstrip().endswith("/son/CANCER_LEO_teslim_REF.png") and satir.get("onizleme", "").rstrip().endswith("/son/CANCER_LEO_teslim_Preview_REF.png")
        and "/AstroLoveArt_Cancer_Leo_24x36.jpg " in satir.get("baski", "") and "/AstroLoveArt_Cancer_Leo_24x36_Preview.jpg " in satir.get("onizleme", ""), str(satir))
rc, out, genv, ozet, cagri = kapilar(1, True, mod="kodlama")
kontrol("Kapilar: kodlama bandi FAIL -> neden KODLAMA (cift duzeltme degil)", genv.get("HALKA_RC") == "1" and "Neden: baski: KODLAMA (kodlama bandi 0.031 > 0.02" in out
        and "TAVAN" not in out.split("Neden:")[-1], out[-300:])
rc, out, genv, ozet, cagri = kapilar(1, True, mod="cok")
kontrol("Kapilar: kapi coktu (HALKA_KAPI satiri yok) -> neden COKTU", genv.get("HALKA_RC") == "1" and "Neden: baski: COKTU" in out and "onizleme: COKTU" in out, out[-300:])
rc, out, genv, ozet, cagri = kapilar(0, True)
kontrol("Kapilar: halka PASS -> HALKA_RC=0, ::error yok, ozette FAIL yok", rc == 0 and genv.get("HALKA_RC") == "0" and "::error" not in out
        and "Halka kapisi FAIL" not in ozet and cagri.count("halka_kapi.py") == 2, f"rc {rc} env {genv}")
rc, out, genv, ozet, cagri = kapilar(1, True, atla="1")
kontrol("Kapilar: HALKA_KAPI_ATLA=1 (Serdar istisnasi) -> HALKA_RC=0 + ::warning", rc == 0 and genv.get("HALKA_RC") == "0" and "Serdar istisnasi" in out
        and "::error" not in out, f"{genv}")
rc, out, genv, ozet, cagri = kapilar(1, False)
kontrol("Kapilar: bayrak kapali -> halka kapisi cagrilmaz, HALKA_RC=0", rc == 0 and genv.get("HALKA_RC") == "0" and cagri == "", f"{genv} {cagri}")

# 2c) Drive'a yaz (C2: yukleme karari) + Sonuc adimi, bash -e
DRIVE = adim("Drive'a yaz")
SONUC = adim("Sonuc")


def yukle(halka_rc, duzelt, renk="MIDNIGHT_BLUE"):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); IS = d / "is"; (IS / "halka").mkdir(parents=True)
        for f in ("AstroLoveArt_Cancer_Leo_24x36.jpg", "AstroLoveArt_Cancer_Leo_24x36_Preview.jpg", "AstroLoveArt_Cancer_Leo.jpg", "KAPI.json", "siparis.json"):
            (IS / f).write_text("x")
        (IS / "halka" / "HALKA_KAPI_x.json").write_text("{}"); (IS / "halka" / "KONTROL_x.jpg").write_text("x")
        metin = DRIVE.replace("/tmp/is", str(IS)); assert "/tmp/is" not in metin
        env = {"RENK": renk, "CIFT": "CANCER_LEO", "RECEIPT": "900000001", "T_BAS": "1", "GPT_REF": "d2b414ee"}
        if halka_rc is not None:
            env["HALKA_RC"] = str(halka_rc)
        if duzelt:
            env["HALKA_DUZELT"] = "1"
        rc, out, _, _, log = calis(metin, env, d)
        hedef = d / "drive"
        musteri = sorted(p.name for p in hedef.rglob("AstroLoveArt_*.jpg")) if hedef.exists() else []
        return rc, out, log, musteri


for ad, hrc, duz, bek_yukle in (("HALKA_RC=1 (bayrak acik)", 1, True, False), ("HALKA_RC=0 (bayrak acik)", 0, True, True),
                                ("bayrak acik, HALKA_RC TANIMSIZ (kapi kosmadi)", None, True, False), ("bayrak kapali, HALKA_RC tanimsiz (bugunku yol)", None, False, True)):
    rc, out, log, musteri = yukle(hrc, duz)
    ok = rc == 0 and (len(musteri) == 3) is bek_yukle and ("KAPI.json" in log or "--include KAPI.json" in log)
    if not bek_yukle:
        ok = ok and "::error::halka kapisi FAIL: AstroLoveArt dosyalari yuklenmedi" in out and "--include AstroLoveArt_*.jpg" not in log
    else:
        ok = ok and all("_Midnight_Blue" in m for m in musteri)
    kontrol(f"yukleme karari (bash -e, sahte rclone): {ad} -> musteri dosyasi {'YUKLENIR' if bek_yukle else 'YUKLENMEZ'}", ok, f"rc {rc} musteri {musteri} {out[-200:]}")
for ad, env, bek in (("HALKA_RC=1", {"KAPI_RC": "0", "HALKA_RC": "1"}, 1), ("KAPI_RC=1", {"KAPI_RC": "1", "HALKA_RC": "0"}, 1),
                     ("ikisi 0", {"KAPI_RC": "0", "HALKA_RC": "0"}, 0), ("HALKA_RC tanimsiz", {"KAPI_RC": "0"}, 1)):
    with tempfile.TemporaryDirectory() as t:
        rc, out, _, _, _ = calis(SONUC, env, Path(t))
    kontrol(f"Sonuc adimi: {ad} -> is {'KIRMIZI' if bek else 'YESIL'}", (rc != 0) == bool(bek), f"rc {rc}")

# 2d) halka_neden.py (gercek betik, dogrudan): her siniflama + bilinen PASS
with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    for ad, ic, bek in (("tavan", 'HALKA_KAPI {"PASS": false, "halka_bant": 0.1316, "tavan": 0.1, "kodlama_bant": 0.0144, "kodlama_esik": 0.02}', "baski: TAVAN (mutlak halka 0.1316 > 0.1;"),
                        ("kodlama", 'HALKA_KAPI {"PASS": false, "halka_bant": 0.05, "tavan": 0.1, "kodlama_bant": 0.025, "kodlama_esik": 0.02}', "baski: KODLAMA (kodlama bandi 0.025 > 0.02;"),
                        ("ikisi", 'HALKA_KAPI {"PASS": false, "halka_bant": 0.2, "tavan": 0.1, "kodlama_bant": 0.05, "kodlama_esik": 0.02}', "baski: TAVAN (mutlak halka 0.2 > 0.1; kaynak halkasi, Merkez cifti elle duzeltir) + KODLAMA"),
                        ("kaynak yok", 'HALKA_KAPI {"PASS": false, "halka_bant": 0.05, "tavan": 0.1, "kodlama_bant": null, "kodlama_esik": 0.02}', "baski: KODLAMA olculemedi"),
                        ("hata", 'HALKA_KAPI {"PASS": false, "hata": "boyut 10x10 tur baski ile tutmuyor"}', "baski: HATA (kapi: boyut 10x10"),
                        ("coktu MemoryError", "Traceback (most recent call last):\n  File \"/tmp/is/x.py\", line 1\nMemoryError", "baski: COKTU (kapi sonuc vermedi; istisna MemoryError)"),
                        ("coktu FileNotFoundError (yol basilmaz)", "Traceback (most recent call last):\nFileNotFoundError: [Errno 2] No such file: '/tmp/is/son/X_REF.png'", "baski: COKTU (kapi sonuc vermedi; istisna FileNotFoundError)"),
                        ("olduruldu (bos log)", "", "baski: COKTU (kapi sonuc vermedi; log yok ya da surec olduruldu"),
                        ("bozuk json", "HALKA_KAPI {bozuk", "baski: COKTU (kapi ciktisi okunamadi)"),
                        ("PASS", 'HALKA_KAPI {"PASS": true, "halka_bant": 0.05}', "baski: PASS")):
        (td / "h_baski.log").write_text("HALKA_KAPI_BELLEK tepe_rss_mb=1\n" + ic + "\n")
        n = HN.neden(td / "h_baski.log")
        kontrol(f"halka_neden: {ad}", n.startswith(bek) and "/tmp/" not in n, n)
    kontrol("halka_neden: log yok -> COKTU", HN.neden(td / "h_onizleme.log").startswith("onizleme: COKTU"))

# ---------- 3) siparis_v2 Girdi adimi: 2:3 artik reddedilmez ----------
YARD = yaml.safe_load((KOK / ".github/workflows/siparis-yardimci.yml").read_text())["jobs"]["siparis_v2"]["steps"]
GIRDI = next(s for s in YARD if s.get("name", "").startswith("Girdi (KISISEL.json)"))["run"]


def v2(co, fmt, boy):
    with tempfile.TemporaryDirectory() as t:
        d = Path(t); g = d / "g"
        sahte_py = d / "vo_py"
        sahte_py.write_text(f'#!/bin/bash\nexec {sys.executable} -I -c "$(cat {d}/agsiz.py)" "$@"\n'); sahte_py.chmod(0o755)
        (d / "agsiz.py").write_text(AGSIZ + "import runpy, sys\nsys.argv = sys.argv[1:]\nsys.path.insert(0, %r)\nrunpy.run_path(sys.argv[0], run_name='__main__')\n" % str(B))
        metin = GIRDI.replace("/tmp/vo/bin/python", str(sahte_py)).replace("/tmp/g", str(g)); assert "/tmp/g/" not in metin and "/tmp/vo/" not in metin
        (d / "scripts").symlink_to(KOK / "scripts")
        var = [dict(ad="Name under Cancer", deger="Milo"), dict(ad="Name under Leo", deger="Harper"), dict(ad="Your message", deger="Always Yours"),
               dict(ad="Color", deger="Midnight Blue"), dict(ad="Size", deger=boy), dict(ad="Format", deger="Print")]
        kis = {"receipt_id": 900000001, "kalemler": [{"varyasyon": var}]}
        src = d / "drive_src" / "OKUMA_1"; src.mkdir(parents=True); (src / "KISISEL.json").write_text(json.dumps(kis))
        (d / "olay.json").write_text(json.dumps({"inputs": {"receipt": "900000001"}}))
        # sahte rclone copy kaynagi: "gdrive:ASTROLOVE/SIPARIS/<r>/OKUMA_1" -> yerel kopya icin sembolik bag
        bag = d / "gdrive:ASTROLOVE" / "SIPARIS" / "900000001"; bag.mkdir(parents=True); (bag / "OKUMA_1").symlink_to(src)
        rc, out, genv, _, _ = calis(metin, {"GITHUB_EVENT_PATH": str(d / "olay.json"), "GH": "", "CO": co, "FMT": fmt, "SIPARIS_IZ_ANAHTARI": "",
                                            "SAHTE_LSF": "OKUMA_1/"}, d)
        ist = json.loads((g / "istek.json").read_text()) if (g / "istek.json").exists() else None
        return rc, out, genv, ist


rc, out, genv, ist = v2("CANCER_LEO:24x36", "Print", "24x36 in")
kontrol("siparis_v2: 2:3 (24x36) Print artik REDDEDILMEZ (istek yazilir, OLCU=24x36)", rc == 0 and ist is not None and ist.get("olcu") == "24x36"
        and genv.get("OLCU") == "24x36" and "2:3" not in out and "Milo" not in out.replace("::add-mask::Milo", ""), f"rc {rc} {out[-300:]}")
rc, out, genv, ist = v2("CANCER_LEO:24x36", "Digital", "24x36 in")
kontrol("siparis_v2: Format Digital yine reddedilir (bilinen FAIL)", rc != 0 and ist is None and "yalniz baski" in out, f"rc {rc}")
rc, out, genv, ist = v2("CANCER_LEO:24x36", "Print", "11x14 in")
kontrol("siparis_v2: Etsy olcusu farkli (bilinen FAIL)", rc != 0 and ist is None, f"rc {rc}")
print("halka 2:3 + akis testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
