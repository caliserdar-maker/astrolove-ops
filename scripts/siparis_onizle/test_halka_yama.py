#!/usr/bin/env python3
"""halka_yama testi (18 Kas, siparis V2B). Ag kapali. Gercek fonksiyon (olcu.yaz) iki kez kosar: bayrak YOK -> d2b414ee olcu.yaz ile
BAYT AYNI cikti (varsayilan davranis degismez); HALKA_DUZELT=1 -> kroma q100 (kroma nicemleme tablosu 1'ler, dosya buyur). Ayrica yama
farki yalniz bayrak korumali satirlar mi (d2b414ee'ye gore). Bilinen FAIL: bayrak korumasi kaldirilmis olcu.py bayt ayni testinde FAIL."""
import io, json, os, re, socket, subprocess, sys, tempfile
from pathlib import Path
import numpy as np


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket.connect = _ag_yok
socket.create_connection = _ag_yok
KOK = Path(__file__).resolve().parents[2]; YAMA = KOK / "scripts/siparis_onizle/halka_yama"; REF = "d2b414ee270ec029bd5abcef4a6535414ae7d1e1"
HATA = []
AGSIZ = ("import socket\ndef _ag(*a, **k):\n    raise AssertionError('gercek ag acilmaya calisildi')\n"
         "socket.socket.connect = _ag; socket.create_connection = _ag\n")   # inceleme F ORTA 8: alt surecte de ag kapali


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


def git(*a, b=False):
    r = subprocess.run(["git", "-C", str(KOK), *a], capture_output=True); assert r.returncode == 0, r.stderr[-300:]
    return r.stdout if b else r.stdout.decode()


def yaz_kos(olcu_kaynak, td, bayrak, ad):
    """olcu.yaz'i verilen kaynak metinle ayri surecte kosar (ayni girdi, ayni tohum); cikti baytlarini doner."""
    k = td / f"m_{ad}"; k.mkdir(); (k / "olcu.py").write_text(olcu_kaynak)
    (k / "teslim_jpg.py").write_bytes(git("show", f"{REF}:motor_gpt/teslim_jpg.py", b=True) if "eski" in ad else (YAMA / "teslim_jpg.py").read_bytes())
    (k / "halka_kodla.py").write_bytes((YAMA / "halka_kodla.py").read_bytes())
    kod = f"""
import sys, numpy as np, os
sys.path.insert(0, {str(k)!r}); os.environ['MOTOR_KOK'] = {str(k)!r}
import olcu
H, W = 840, 660; yy, xx = np.mgrid[0:H, 0:W]
P2 = np.stack([10 + 30 * np.exp(-np.hypot(xx - 330, yy - 340) / 300)] * 3, -1).astype(np.float32); P2[..., 2] *= 1.8
M2 = np.zeros((H, W), np.uint8); M2[400:420, 300:360] = 1
b = dict(olcu='11x14', hedef_px=[660, 840], _kutu=[(20, 20, 200, 200), (460, 20, 640, 200), (20, 600, 200, 800), (460, 600, 640, 800)])
olcu.yaz(P2, M2, b, {str(td / ('o_' + ad + '.jpg'))!r}, {str(td / 'cjpeg')!r})
"""
    env = dict(os.environ); env.pop("HALKA_DUZELT", None)
    if bayrak:
        env["HALKA_DUZELT"] = "1"
    r = subprocess.run([sys.executable, "-I", "-c", AGSIZ + kod], capture_output=True, text=True, env=env, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    return (td / f"o_{ad}.jpg").read_bytes()


def _ornek(bayt):
    from PIL import Image, JpegImagePlugin
    im = Image.open(io.BytesIO(bayt)); return JpegImagePlugin.get_sampling(im), tuple(round(float(x)) for x in im.info.get("dpi", (0, 0)))


def _oni(yol, kaynak):
    from PIL import Image
    if not Path(yol).exists():
        return False
    im = Image.open(yol); w, h = im.size
    return max(w, h) == 2000 and abs(w / h - kaynak[0] / kaynak[1]) < 0.002 and all(set(v) == {1} for v in im.quantization.values())


def dqt(bayt):
    from PIL import Image
    return Image.open(io.BytesIO(bayt)).quantization


with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    (td / "cjpeg").write_bytes(git("show", f"{REF}:motor_gpt/bin/cjpeg-mozjpeg-4.1.1", b=True)); (td / "cjpeg").chmod(0o755)
    eski = git("show", f"{REF}:motor_gpt/olcu.py"); yeni = (YAMA / "olcu.py").read_text()
    a = yaz_kos(eski, td, False, "eski"); b = yaz_kos(yeni, td, False, "yeni0"); c = yaz_kos(yeni, td, True, "yeni1")
    kontrol("bayrak YOK: yamali olcu.yaz cikti d2b414ee ile BAYT AYNI", a == b, f"{len(a)} != {len(b)}")
    qa, qc = dqt(a), dqt(c)
    kontrol("bayrak YOK: kroma tablosu 1'ler DEGIL (q97)", any(v > 1 for v in qa.get(1, [])), str(qa.get(1, [])[:8]))
    kontrol("HALKA_DUZELT=1: luma ve kroma tablolari tum 1 (q100), 4:4:4, 300 dpi", all(set(v) == {1} for v in qc.values()) and len(qc) == 2 and _ornek(c) == (0, (300, 300)), str({k_: v[:4] for k_, v in qc.items()}))
    kontrol("HALKA_DUZELT=1: onizleme yazildi (uzun kenar 2000, ayni oran, tablolar 1)", _oni(td / "o_yeni1_Preview.jpg", (660, 840)))
    kontrol("bayrak YOK: onizleme YAZILMAZ", not (td / "o_yeni0_Preview.jpg").exists())
    bozuk = yeni.replace("    if os.environ.get('HALKA_DUZELT') == '1':                          # 19 Kas", "    if True:                          # 19 Kas")
    kontrol("bilinen FAIL (mutasyon): olcu.yaz bayrak korumasi kaldirilinca bayt ayni testi FAIL", bozuk != yeni and yaz_kos(bozuk, td, False, "bozuk") != a)

def tj_kos(kaynak, td, bayrak, ad):
    k = td / f"tj_{ad}"; k.mkdir(); (k / "teslim_jpg.py").write_text(kaynak); (k / "halka_kodla.py").write_bytes((YAMA / "halka_kodla.py").read_bytes())
    kod = f"""
import sys, numpy as np
sys.path.insert(0, {str(k)!r}); import teslim_jpg
H, W = 10800, 7200; yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)   # teslim_jpg kutulari 7200x10800 olceginde sabit
P = np.empty((H, W, 3), np.float32); r = np.hypot(xx - 3600, yy - 4392); del xx, yy
P[..., 0] = P[..., 1] = 8 + 20 * np.exp(-r / 3000); P[..., 2] = 2.2 * P[..., 0]; del r
z = dict(_konum=np.array([[3000, 4000]]), _ad=np.array(['ana']), ana=np.full((400, 1200), 255, np.uint8))
print(teslim_jpg.yaz(P, z, {str(td / ('tj_' + ad + '.jpg'))!r}, {str(td / 'cjpeg')!r}).get('q'))
"""
    env = dict(os.environ); env.pop("HALKA_DUZELT", None)
    if bayrak:
        env["HALKA_DUZELT"] = "1"
    r = subprocess.run([sys.executable, "-I", "-c", AGSIZ + kod], capture_output=True, text=True, env=env, timeout=400)
    assert r.returncode == 0, r.stderr[-800:]
    return (td / f"tj_{ad}.jpg").read_bytes()


with tempfile.TemporaryDirectory() as t:
    td = Path(t)
    (td / "cjpeg").write_bytes(git("show", f"{REF}:motor_gpt/bin/cjpeg-mozjpeg-4.1.1", b=True)); (td / "cjpeg").chmod(0o755)
    eski = git("show", f"{REF}:motor_gpt/teslim_jpg.py"); yeni = (YAMA / "teslim_jpg.py").read_text()
    a = tj_kos(eski, td, False, "eski"); b = tj_kos(yeni, td, False, "yeni0"); c = tj_kos(yeni, td, True, "yeni1")
    kontrol("teslim_jpg (24x36) bayrak YOK: cikti d2b414ee ile BAYT AYNI", a == b)
    kontrol("teslim_jpg HALKA_DUZELT=1: tablolar tum 1, 4:4:4, onizleme var", all(set(v) == {1} for v in dqt(c).values()) and _ornek(c)[0] == 0
            and _oni(td / "tj_yeni1_Preview.jpg", (7200, 10800)))
    bozuk = yeni.replace("    if os.environ.get('HALKA_DUZELT') == '1':                           # 19 Kas", "    if True:                           # 19 Kas")
    kontrol("bilinen FAIL (mutasyon): teslim_jpg bayrak korumasi kaldirilinca bayt ayni testi FAIL", bozuk != yeni and tj_kos(bozuk, td, False, "bozuk") != a)

# yama farki: d2b414ee'ye gore eklenen her satir bayrak korumasinda ya da korunan blogun icinde; silinen tek satir olcu.py cjpeg cagrisi
import re  # noqa: E402

KOSUL_ACIK = re.compile(r"^(\s*)if os\.environ\.get\('HALKA_DUZELT'\) == '1':(\s*#.*)?$")
KOSUL_KAPALI = re.compile(r"^(\s*)if os\.environ\.get\('HALKA_DUZELT'\) != '1':(\s*#.*)?$")


def _g(s):
    return len(s) - len(s.lstrip())


def _blok(sat, i, ind):
    """sat[i] blok basi (girinti ind); govde satirlarinin bitis indeksi (ilk bos olmayan, girintisi <= ind satir)."""
    j = i + 1
    while j < len(sat) and (not sat[j].strip() or _g(sat[j]) > ind):
        j += 1
    while j > i + 1 and not sat[j - 1].strip():                 # sondaki bos satirlar bloga ait degil
        j -= 1
    return j


def bayrak_kapali(sat):
    """Yamali dosyanin HALKA_DUZELT kapaliyken calisan metni: '== 1' bloklari atilir (else kolu girintisi 4 azaltilip kalir), '!= 1' govdesi
    girintisi 4 azaltilip kalir, `def _yaz_halka` atilir. Kosul YALNIZ tam bicimle taninir (yorumdaki ya da baska bicimdeki ad korumaz)."""
    out, i = [], 0
    while i < len(sat):
        s = sat[i]; m1 = KOSUL_ACIK.match(s); m2 = KOSUL_KAPALI.match(s)
        if m1:
            ind = len(m1.group(1)); j = _blok(sat, i, ind)
            if j < len(sat) and sat[j].strip() == "else:" and _g(sat[j]) == ind:
                k = _blok(sat, j, ind); out += bayrak_kapali([x[4:] if x.strip() else x for x in sat[j + 1:k]]); i = k
            else:
                i = j
            continue
        if m2:
            ind = len(m2.group(1)); j = _blok(sat, i, ind); out += bayrak_kapali([x[4:] if x.strip() else x for x in sat[i + 1:j]]); i = j
            continue
        if s.startswith("def _yaz_halka("):
            j = _blok(sat, i, 0)
            i = j; out_bos = 0
            while out and not out[-1].strip() and out_bos < 2:   # fonksiyonun oncesindeki iki bos satir eklenmisti
                out.pop(); out_bos += 1
            continue
        out.append(s); i += 1
    return out


for f in ("siparis_uret.py", "renk_uyum.py", "olcu.py", "teslim_jpg.py", "siparis_kapi.py"):
    eski = git("show", f"{REF}:motor_gpt/{f}").splitlines(); yeni = (YAMA / f).read_text().splitlines()
    kapali = bayrak_kapali(yeni)
    fark = [k for k in range(max(len(eski), len(kapali))) if (eski[k] if k < len(eski) else None) != (kapali[k] if k < len(kapali) else None)]
    kontrol(f"bayrak KAPALI metni d2b414ee ile satir satir AYNI: {f}", not fark and any(KOSUL_ACIK.match(x) for x in yeni),
            f"ilk fark satir {fark[0] + 1 if fark else '-'}: {(kapali[fark[0]] if fark and fark[0] < len(kapali) else '')[:80]}")
    subprocess.run([sys.executable, "-m", "py_compile", str(YAMA / f)], check=True)
# bilinen FAIL (inceleme G ORTA 7 mutasyonlari): else koluna, '!= 1' blokuna ve yorumunda bayrak adi gecen korumasiz satira ekleme
_r = (YAMA / "renk_uyum.py").read_text().splitlines(); _e = git("show", f"{REF}:motor_gpt/renk_uyum.py").splitlines()
for ad, fn in (("else koluna eklenen satir", lambda y: y.insert(next(i for i, x in enumerate(y) if x.strip() == "else:") + 1, "    print('ek')")),
               ("'!= 1' blokuna eklenen satir", lambda y: y.insert(next(i for i, x in enumerate(y) if KOSUL_KAPALI.match(x)) + 1, "    print('ek')")),
               ("yorumunda HALKA_DUZELT gecen korumasiz satir", lambda y: y.insert(len(y) - 1, "print('ek')   # HALKA_DUZELT"))):
    y = list(_r); fn(y)
    kontrol(f"bilinen FAIL (mutasyon): {ad} bayrak kapali metni bozar", bayrak_kapali(y) != _e)
# B2 (Serdar karar 1): boyut kapisi baski 100 MB, dijital 20 MB; bayrak KAPALI iken 20 MB (eski). Gercek kod: olcu.kapi_g (boyut yamali),
# siparis_kapi.py'nin g blogu (kaynaktan ayiklanip calistirilir).
def kapi_g_kos(bayrak, tur, bayt):
    with tempfile.TemporaryDirectory() as t:
        k = Path(t); (k / "olcu.py").write_text((YAMA / "olcu.py").read_text()); (k / "teslim_jpg.py").write_text((YAMA / "teslim_jpg.py").read_text())
        kod = f"""
import sys, os, numpy as np
from PIL import Image
sys.path.insert(0, {str(k)!r}); os.environ['MOTOR_KOK'] = {str(k)!r}
import olcu
Image.new('RGB', (60, 80)).save({str(k / 'a.jpg')!r}, quality=95, subsampling=0, dpi=(300, 300))
olcu.halka_olc = lambda *a: (0.01, {{}}); olcu.os.path.getsize = lambda p: {bayt}
g = olcu.kapi_g({str(k / 'a.jpg')!r}, np.zeros((80, 60, 3), np.float32), np.ones((80, 60), bool), dict(hedef_px=[60, 80], _kutu=[]))
print(g['PASS'], g.get('sinir_bayt'))
"""
        env = {x: v for x, v in os.environ.items() if x not in ("HALKA_DUZELT", "TESLIM_TUR")}
        if bayrak:
            env["HALKA_DUZELT"] = "1"
        if tur:
            env["TESLIM_TUR"] = tur
        r = subprocess.run([sys.executable, "-I", "-c", AGSIZ + kod], capture_output=True, text=True, env=env, timeout=60)
        assert r.returncode == 0, r.stderr[-600:]
        return r.stdout.split()[0] == "True"


def sk_kos(bayrak, tur, bayt):
    src = (YAMA / "siparis_kapi.py").read_text().splitlines()
    b = next(i for i, x in enumerate(src) if x.startswith("    g['PASS'] = bool(g['bayt'] < 20_000_000")); e = next(i for i in range(b, len(src)) if src[i].startswith("else:"))
    kod = "\n".join(x[4:] for x in src[b:e])
    g = dict(bayt=bayt, boyut=[10, 10], ornekleme_444=True, dpi_teslim=[300, 300], dpi_ana=[300, 300], halka=0.01)
    ortam = {"HALKA_DUZELT": "1"} if bayrak else {}
    if tur:
        ortam["TESLIM_TUR"] = tur

    class _O:
        ESIK_HALKA = 0.10

    class _OS:
        environ = ortam
    exec(kod, {"g": g, "hw_": [10, 10], "_olcu": _O, "os": _OS})
    return g["PASS"]


for ad, bay, tur, bayt, bek in (("baski 25 MB", 1, "baski", 25_000_000, True), ("baski 99 MB", 1, "baski", 99_000_000, True),
                                ("baski 100.1 MB", 1, "baski", 100_100_000, False), ("dijital 25 MB", 1, "dijital", 25_000_000, False),
                                ("dijital 19 MB", 1, "dijital", 19_000_000, True), ("tur yok 25 MB (siki)", 1, None, 25_000_000, False),
                                ("bayrak KAPALI baski 25 MB (eski 20 MB)", 0, "baski", 25_000_000, False), ("bayrak KAPALI 19 MB", 0, None, 19_000_000, True)):
    a1 = kapi_g_kos(bay, tur, bayt); a2 = sk_kos(bay, tur, bayt)
    kontrol(f"boyut kapisi ({'PASS' if bek else 'FAIL'} beklenir) {ad}: olcu.kapi_g ve siparis_kapi g", a1 is bek and a2 is bek, f"kapi_g {a1} siparis_kapi {a2}")
print("halka_yama testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
