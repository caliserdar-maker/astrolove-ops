#!/usr/bin/env python3
"""S1 testleri (Serdar 4 Kas "A."): fis deseni (router + tarayici), add-mask muafiyeti, router stdout, cok satirli mesaj maskesi,
iki grep kapisi. Her kontrol bilinen PASS + bilinen FAIL. Gercek fis no KULLANILMAZ; tum degerler sentetik.
Kullanim: python3 scripts/guvenlik/test_receipt_desen.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import base64
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "scripts" / "guvenlik"))
sys.path.insert(0, str(KOK / "scripts" / "prodigi"))
import receipt_desen as D  # noqa: E402
import musteri_tara as M  # noqa: E402

os.environ.setdefault("SIPARIS_KOD_ANAHTARI", "test-anahtar")
import order_router as R  # noqa: E402

sonuc = []
ESKI_STR = re.compile(r"(?<!\d)4[01]\d{8}(?!\d)")       # S1 oncesi order_router.py:698
ESKI_B = re.compile(rb"(?<!\d)4[01]\d{8}(?!\d)")        # S1 oncesi gizlilik_temizlik.py:31


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"), flush=True)


# ---------- 1 router deseni: sentetik degerler stdout'ta S- kodu
DEGER = {"42 alt": "4200000001", "42 ust": "4299999999", "40/41": "4011111111", "11 hane": "40000000001", "12 hane": "400000000001",
         "pod78 ilan id": "4570165628", "test serisi": "9000000001"}


def router_cikti(fn):
    buf = io.StringIO(); eski = sys.stdout
    sys.stdout = R._MaskeliCikti(buf)
    try:
        fn()
    finally:
        sys.stdout = eski
    return buf.getvalue()


for ad, v in DEGER.items():
    o = router_cikti(lambda: print(f"receipt {v} durum"))
    k(f"PASS router stdout {ad}: deger yok, S- kodu var (receipt_kod)", v not in o and R.receipt_kod(v) in o, o)
for ad in ("42 alt", "42 ust", "11 hane"):
    v = DEGER[ad]
    k(f"bilinen FAIL eski desen {ad}: eski desen kacirir", ESKI_STR.sub("X", f"receipt {v}") == f"receipt {v}")
k("PASS router: 9 ve 13 haneli sayi dokunulmaz (10-12 disi)", D.ROUTER.sub("X", "123456789 1234567890123") == "123456789 1234567890123")
k("PASS router: tarih / saat parcasi dokunulmaz", D.ROUTER.sub("X", "2026-11-04T20:01:57Z") == "2026-11-04T20:01:57Z")

# ---------- 2 add-mask muafiyeti
SATIR = "::add-mask::1234567890.abc"
o = router_cikti(lambda: print(SATIR))
k("PASS add-mask satiri router'dan aynen gecer", o == SATIR + "\n", o)
k("bilinen FAIL muafiyetsiz genis desen add-mask satirini bozar", D.ROUTER.sub(lambda m: R.receipt_kod(m.group(0)), SATIR) != SATIR)
o = router_cikti(lambda: print(f"::add-mask::abc\nreceipt {DEGER['42 alt']}"))
k("PASS cok satirli yazimda yalniz add-mask satiri muaf, sonraki satir maskeli", o.startswith("::add-mask::abc\n")
  and DEGER["42 alt"] not in o, o)

# inceleme S1 madde 4: parcali yazim (satir tamponu)
o = router_cikti(lambda: print("::add-mask::", "1234567890.abc"))
k("PASS cok argumanli print: add-mask satiri aynen (muafiyet tam satira)", o == "::add-mask:: 1234567890.abc\n", o)
o = router_cikti(lambda: (sys.stdout.write("::add-mask::tok"), sys.stdout.write("1234567890\n")))
k("PASS parcali write: add-mask satiri aynen", o == "::add-mask::tok1234567890\n", o)
o = router_cikti(lambda: (sys.stdout.write("receipt 42000"), sys.stdout.write("00001 x\n")))
k("PASS parcali write: bolunmus fis no da maskeli", "4200000001" not in o and R.receipt_kod("4200000001") in o, o)
o = router_cikti(lambda: (sys.stdout.write("receipt 4200000001"), sys.stdout.flush()))
k("PASS satir sonu olmadan flush: maskeli yazilir", o == "receipt " + R.receipt_kod("4200000001"), o)
class EskiSarma:   # S1 oncesi _MaskeliCikti: parca parca (tamponsuz) maskeleme
    def __init__(self, a):
        self.a = a

    def write(self, t):
        return self.a.write(R.kargo_maske.maskele(R.maskele_metin(t)))

    def flush(self):
        return self.a.flush()


_b = io.StringIO(); _e = sys.stdout; sys.stdout = EskiSarma(_b)
try:
    print("::add-mask::", "1234567890.abc")
finally:
    sys.stdout = _e
k("bilinen FAIL tamponsuz (eski) sarmalayici: cok argumanli print'te add-mask satiri bozulur", _b.getvalue() != "::add-mask:: 1234567890.abc\n",
  _b.getvalue())
# inceleme S1 madde 3: sira once fis deseni (Merkez: 12 hane = S- kodu), ord_ kargo_maske'de son 4 hane
for ad, g, bek in (("12 haneli takip -> S- kodu", "takip 123456789012", "takip " + R.receipt_kod("123456789012")),
                   ("ord_ 10 hane -> son 4", "ord_1234567890", "ord_***7890"), ("ord_ 12 hane -> son 4", "ord_123456789012", "ord_***9012")):
    o = router_cikti(lambda: print(g))
    k(f"PASS {ad}", o == bek + "\n", o)
o = router_cikti(lambda: print("1Z999AA10123456784"))
k("PASS UPS 1Z: rakam dizisi acikta degil (S- kodu; son 4 hane gorunumu yok, raporda)", "10123456784" not in o and "6784" not in o, o)
k("bilinen FAIL ord_ dislamasi olmadan ord_ kimligi S- olur", re.sub(r"(?<!\d)\d{10,12}(?!\d)", "S", "ord_1234567890") == "ord_S")
# inceleme S1 madde 6: yalniz \n'de bolunur
k("PASS satir_satir: \u2028 sonrasi add-mask parcasi muaf sayilmaz", "4200000001" not in
  D.satir_satir("x\u2028::add-mask::4200000001\n", lambda t: D.ROUTER.sub("X", t)))

# ---------- 3 router cikti satirlari (L302 ::error ACIL, L889 ilerleme, L1188 rapor) gercek R.log / print yoluyla
rid = DEGER["42 alt"]
o = router_cikti(lambda: (print(f"::error title=ACIL {rid}::kanal bekcisi", flush=True),
                          R.log(f"[1/1] receipt {rid} | gecen 0s kalan~0s %100"),
                          R.log("\n".join([f"- {rid}: ATLA (STATE shipped)", "", "STATE: {}", "", "hata yok"]))))
k("PASS router L302 / L889 / L1188 bicimi: 42'li deger hic yok, 3 kez S- kodu", rid not in o and o.count(R.receipt_kod(rid)) == 3, o)
k("bilinen FAIL eski desenle ayni satirlar 42'li degeri birakir", rid in ESKI_STR.sub("X", f"::error title=ACIL {rid}::x"))

# ---------- 4 tarayici deseni (bytes)
for ad, v in (("42", b"4200000001"), ("40", b"4000000001"), ("41", b"4111111111")):
    k(f"PASS tarayici {ad}'li 10 hane isaretlenir", bool(D.TARAMA_B.search(b"log " + v + b" x")))
k("PASS tarayici 11 haneli kosu id'si isaretlenmez", not D.TARAMA_B.search(b"run 41902637886 ok"))
k("BILINEN FAZLA ISARETLEME: 10 haneli ilan id ve epoch da isaretlenir (canli sayi OLCULMEDI)",
  bool(D.TARAMA_B.search(b"ilan 4570165628")) and bool(D.TARAMA_B.search(b"ts 1793809359")))
k("bilinen FAIL eski tarayici 42'liyi kacirir", not ESKI_B.search(b"log 4200000001 x"))
k("str ve bytes tarayici ayni sonucu verir", bool(D.TARAMA.search("x 4200000001")) and not D.TARAMA.search("41902637886"))
sys.path.insert(0, str(KOK / "scripts" / "ops"))
os.environ.setdefault("GITHUB_REPOSITORY", "x/y"); os.environ.setdefault("GH_TOKEN", "x")
import gizlilik_temizlik as G  # noqa: E402
k("gizlilik_temizlik RECEIPT_DESEN = receipt_desen.TARAMA_B (tek kaynak)", G.RECEIPT_DESEN is D.TARAMA_B)
k("order_router RECEIPT_DESEN = receipt_desen.ROUTER (tek kaynak)", R.RECEIPT_DESEN is D.ROUTER)

# ---------- 5 musteri_tara (kod degismedi; ZAYIF TEST: FAIL veremez)
c = M.tara("receipt_id: 4200000001\nreceipt_id: 9000000001\n")
k("musteri_tara: 42'li -> receipt_no, 900000000N -> test_receipt (ZAYIF TEST)", c.get("receipt_no") == 1 and c.get("test_receipt") == 1, c)

# ---------- 6 cok satirli mesaj maskesi: is akisi satirlari aynen kosturulur
MESAJ = "Seni seviyorum\r\nÇok özledim ğüşı\r\n\r\nSonsuza dek"   # 3 bos olmayan satir, aksanli, \r\n
B64 = base64.b64encode(MESAJ.encode()).decode()
WF = KOK / ".github" / "workflows"
satirlar = []
for f in sorted(WF.glob("*.yml")):
    for i, s in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if "mesaj_b64" in s and "base64 -d" in s:
            satirlar.append((f.name, i, s.strip()))


def kos(satir):
    with tempfile.TemporaryDirectory() as d:
        ev = pathlib.Path(d) / "ev.json"; ev.write_text(json.dumps({"inputs": {"mesaj_b64": B64}}))
        ist = pathlib.Path(d) / "istek.json"; ist.write_text(json.dumps({"mesaj_b64": B64}))
        betik = "set -euo pipefail\n" + satir.replace("/tmp/istek.json", str(ist))
        r = subprocess.run(["bash", "-c", betik], env=dict(os.environ, GITHUB_EVENT_PATH=str(ev), E=str(ev)),
                           capture_output=True, text=True)
        return r.returncode, [x for x in r.stdout.splitlines() if x.startswith("::add-mask::")]


k("cok satirli: is akislarinda 12 mesaj_b64 + base64 -d satiri", len(satirlar) == 12, [(a, b) for a, b, _ in satirlar])
for ad, i, s in satirlar:
    rc, am = kos(s)
    k(f"PASS {ad}:{i} cikis 0, 3 add-mask satiri, \\r yok, aksanli satir dahil", rc == 0 and len(am) == 3
      and not any("\r" in x for x in am) and "::add-mask::Çok özledim ğüşı" in am, (rc, len(am)))
yard = satirlar[0][2][satirlar[0][2].index("while IFS="):] if satirlar else "false"
for ad, m, bek in (("tek \\r ayirici", "line1\rline2", ["::add-mask::line1", "::add-mask::line2"]),
                   ("kisa satir (< 4 bayt) maskelenmez (olcum 41987043341)", "1\nx\nA2\nx20\nLove", ["::add-mask::Love"]),
                   ("cok baytli kisa satir (3 harf, 4+ bayt) maskelenir (locale'den bagimsiz)", "Çok\nab", ["::add-mask::Çok"]),
                   ("bas/son bosluk kirpilir", "  Forever yours  ", ["::add-mask::Forever yours"])):
    r = subprocess.run(["bash", "-c", "set -euo pipefail\nm=$'" + m.replace("\r", "\\r") + "'; " + yard], capture_output=True, text=True)
    k(f"PASS yardimci {ad}", r.returncode == 0 and r.stdout.splitlines() == bek, (r.returncode, r.stdout.splitlines()))
ESKI_SATIR = 'm=$(jq -r \'.inputs.mesaj_b64\' "$GITHUB_EVENT_PATH" | base64 -d); echo "::add-mask::$m"'
rc, am = kos(ESKI_SATIR)
k("bilinen FAIL eski kalip yalniz 1 add-mask satiri uretir", rc == 0 and len(am) == 1, (rc, len(am)))
yard = satirlar[0][2][satirlar[0][2].index("while IFS="):] if satirlar else "false"
for ad, m in (("bos", ""), ("son satiri bos", "a\n\n"), ("yalniz bosluk", "  \r\n")):
    r = subprocess.run(["bash", "-c", "set -euo pipefail\nm=$'" + m.replace("\n", "\\n").replace("\r", "\\r") + "'; " + yard],
                       capture_output=True, text=True)
    k(f"PASS mesaj {ad}: cikis 0 (set -e altinda dongu durmaz), bos add-mask yok", r.returncode == 0
      and "::add-mask::\n" not in r.stdout + "\n" and all(x.strip() != "::add-mask::" for x in r.stdout.splitlines()), r.returncode)

# ---------- 7 kapilar
eski_say = sum(f.read_text(encoding="utf-8").count('echo "::add-mask::$m"') for f in WF.glob("*.yml"))
k("kapi: eski kalip grep sayimi 0", eski_say == 0, eski_say)
olumlu = all("while IFS= read -r s" in s and s.index("base64 -d") < s.index("while IFS= read -r s") < s.index("::add-mask::$s")
             for _, _, s in satirlar)
k("kapi (olumlu): her mesaj_b64 + base64 -d satirinda yardimci ayni satirda, add-mask'tan once", olumlu and satirlar)
import yaml  # noqa: E402

# ---------- 8 sessiz atlama kapilari (S1 karar 1 a): yml'deki adim aynen kosturulur
def adim(dosya, is_adi, adim_adi):
    y = yaml.safe_load((WF / dosya).read_text(encoding="utf-8"))
    return [x for x in y["jobs"][is_adi]["steps"] if x.get("name") == adim_adi][0]["run"]


def kos_env(betik, env):
    return subprocess.run(["bash", "-e", "-c", betik], env=dict(os.environ, **env), capture_output=True, text=True).returncode


DOLU = dict(O_RENK='["CHAMPAGNE_IVORY"]', O_SAYFA='{"include":[]}', O_SAYFA_VAR="0", O_WP="[]")
pk = adim("siparis-dijital.yml", "paket", "Sessiz atlama kapisi (S1, Serdar 5 Kas karar 1 a)")
k("PASS siparis-dijital paket kapisi: 6 output dolu -> 0", kos_env(pk, DOLU) == 0)
for o in DOLU:
    k(f"bilinen FAIL siparis-dijital paket kapisi: {o} bos -> FAIL", kos_env(pk, dict(DOLU, **{o: ""})) != 0)
yk = adim("siparis-giris.yml", "yol_kapisi", "Sessiz atlama kapisi")
for v in ("eski", "yeni", "kuru-eski", "kuru-yeni"):
    k(f"PASS siparis-giris yol kapisi: yol={v} -> 0", kos_env(yk, {"YOL": v}) == 0)
k("bilinen FAIL siparis-giris yol kapisi: yol bos -> FAIL", kos_env(yk, {"YOL": ""}) != 0)
k("bilinen FAIL siparis-giris yol kapisi: beklenmeyen yol -> FAIL", kos_env(yk, {"YOL": "***"}) != 0)
pkenv = [x for x in yg_ham["jobs"]["paket"]["steps"] if x.get("name", "").startswith("Sessiz atlama")][0]["env"] if (yg_ham := yaml.safe_load(
    (WF / "siparis-dijital.yml").read_text(encoding="utf-8"))) else {}
k("paket kapisi env eslemesi: O_X = needs.plan.outputs.x (4 kullanilan output, cift/normalize YOK)",
  pkenv == {f"O_{o.upper()}": f"${{{{ needs.plan.outputs.{o} }}}}" for o in ("renk", "sayfa", "sayfa_var", "wp")}, pkenv)
k("paket isi if: always() && plan success (kapi her durumda kosar)",
  yg_ham["jobs"]["paket"]["if"].replace(" ", "") == "${{always()&&needs.plan.result=='success'}}", yg_ham["jobs"]["paket"]["if"])
k("kullanilan output'lar: paket kapisi denetimleri = islerde okunan plan output'lari",
  set(__import__("re").findall(r"needs\.plan\.outputs\.(\w+)", (WF / "siparis-dijital.yml").read_text(encoding="utf-8").split("  paket:")[0]))
  == {"renk", "sayfa", "sayfa_var", "wp"})
ykenv = [x for x in ygi_ham["jobs"]["yol_kapisi"]["steps"]][0]["env"] if (ygi_ham := yaml.safe_load(
    (WF / "siparis-giris.yml").read_text(encoding="utf-8"))) else {}
k("yol kapisi env eslemesi: YOL = needs.yonlendir.outputs.yol", ykenv == {"YOL": "${{ needs.yonlendir.outputs.yol }}"}, ykenv)
# isim cakismasi (inceleme bulgu 1): isim 'Leo' -> 'LEO' cift output'unda gecer; kapi cift'e bakmadigi icin yanlis FAIL yok
k("isim/cift cakismasi: cift bosalsa da (denetlenmez) kapi PASS", kos_env(pk, DOLU) == 0)
yg = yaml.safe_load((WF / "siparis-dijital.yml").read_text(encoding="utf-8"))
k("paket isi kapisi ilk adim ve paket plan'a bagli", yg["jobs"]["paket"]["steps"][0]["name"].startswith("Sessiz atlama")
  and "plan" in yg["jobs"]["paket"]["needs"])
ygi = yaml.safe_load((WF / "siparis-giris.yml").read_text(encoding="utf-8"))
k("siparis-giris yol_kapisi yonlendir'e bagli, always", ygi["jobs"]["yol_kapisi"]["needs"] == "yonlendir"
  and "always()" in ygi["jobs"]["yol_kapisi"]["if"])

# ---------- 9 gizlilik-temizlik (S1 karar 2 a): yalniz tara; fazla isaretleme sayilir
import io as _io, zipfile as _zf  # noqa: E401,E402


def zipb(metin):
    b = _io.BytesIO()
    with _zf.ZipFile(b, "w") as z:
        z.writestr("1_adim.txt", metin)
    return b.getvalue()


G.SON["yalniz_yeni"] = False
v = G.zip_tara(zipb("ilan 4570165628 yuklendi"), [], [])
k("tara: ilan id (10 hane) yeni desenle isaretlenir ve 'yalniz yeni desen' sayilir", v is True and G.SON["yalniz_yeni"] is True)
v = G.zip_tara(zipb("receipt 4011111111"), [], [])
k("tara: eski desenin de yakaladigi deger 'yalniz yeni' sayilmaz", v is True and G.SON["yalniz_yeni"] is False)
v = G.zip_tara(zipb("run 41987043341 ok"), [], [])
k("tara: 11 haneli kosu id temiz", v is False)
_argv = sys.argv
sys.argv = ["gizlilik_temizlik.py", "sil"]
try:
    G.main(); h = None
except SystemExit as e:
    h = str(e)
finally:
    sys.argv = _argv
k("bilinen FAIL: gizlilik_temizlik sil -> DUR (Serdar 5 Kas karar 2 a, ayri onay)", h and "KAPALI" in h, h)
gb = yaml.safe_load((WF / "gizlilik-temizlik.yml").read_text(encoding="utf-8"))
gr = [x for x in gb["jobs"][list(gb["jobs"])[0]]["steps"] if x.get("name") == "Tara / sil"][0]["run"]
case_satir = [x for x in gr.splitlines() if 'case "$MOD"' in x][0]
k("gizlilik-temizlik.yml: MOD=sil -> exit 1 (adimin kendi case satiri)", kos_env(case_satir, {"MOD": "sil"}) != 0)
k("gizlilik-temizlik.yml: MOD=tara -> 0", kos_env(case_satir, {"MOD": "tara"}) == 0)
deg = ["siparis-giris.yml", "siparis-dijital.yml", "olcek-tani-siparis.yml", "wp-kayma-tani.yml"]
try:
    [yaml.safe_load((WF / f).read_text(encoding="utf-8")) for f in deg]; ok = True
except Exception as e:   # noqa: BLE001
    ok = str(e)
k("kapi: degisen 4 is akisi YAML olarak ayristirilir", ok is True, ok)

print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
