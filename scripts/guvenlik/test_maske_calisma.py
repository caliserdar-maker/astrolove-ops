#!/usr/bin/env python3
"""IP adim 0 c3 (18 Kas 2026): takip_kuru.py, siparis_kiyas.py, prodigi_siparis_oku.py GERCEK main() kosusu.

Her betik ayri alt surecte `runpy` ile __main__ olarak kosar; Prodigi / Etsy / requests sahte (ag kapali, CLAUDE.md TEST AGI).
Sahte veride siparis no 9000000123, merchantReference etsy-9000000123-8x10, Prodigi kimligi ord_1234567890,
takip no 1Z12345E0291980793 var. Kontrol: stdout, stderr ve GITHUB_STEP_SUMMARY dosyasinda bu degerler ACIK yok;
ord_ ve takip no yalniz son 4 hane, siparis no opak kod (S-xxxxxxxx).
Bilinen FAIL (her betik): ayni kosu maske kapatilarak (maskeli_cikti_kur no-op, maskeli_metin_tam kimlik) yapilir;
denetim sizintiyi BULMALI (bulamazsa test FAIL). Hata yolu: siparis_kiyas'ta GET 404 -> sys.exit metni stderr'de maskeli.
siparis_kiyas alici METNI (sehir, baslik) Serdar karariyla kapsam disi (yalniz numara denetlenir).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import socket
import urllib.request


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")


socket.socket = _ag_yok
socket.create_connection = _ag_yok
urllib.request.urlopen = _ag_yok

KOK = Path(__file__).resolve().parents[2]
RID, REF, ORD, TAKIP = "9000000123", "etsy-9000000123-8x10", "ord_1234567890", "1Z12345E0291980793"
HATA = []

# Alt surecte calisan surucu: ag kapali, sahte requests, sahte Prodigi / Etsy, sonra betik __main__ olarak.
SURUCU = r'''
import json, os, runpy, socket, sys, types, urllib.request
def _ag_yok(*a, **k):
    raise AssertionError("gercek ag acilmaya calisildi")
socket.socket = _ag_yok; socket.create_connection = _ag_yok; urllib.request.urlopen = _ag_yok
KOK, BETIK, MASKE = sys.argv[1], sys.argv[2], sys.argv[3]
RID, REF, ORD, TAKIP = "9000000123", "etsy-9000000123-8x10", "ord_1234567890", "1Z12345E0291980793"
class _Yanit:
    def __init__(self, kod, veri): self.status_code, self._v = kod, veri
    def json(self): return self._v
class _ReqHata(Exception): pass
rq = types.ModuleType("requests")
rq.RequestException = _ReqHata
rq.exceptions = types.SimpleNamespace(RequestException=_ReqHata, HTTPError=_ReqHata, ConnectionError=_ReqHata, Timeout=_ReqHata)
def _yok(*a, **k): raise _ReqHata("sahte requests: ag yok")
rq.get = rq.post = rq.request = _yok
class _Oturum:
    headers = {}
    def request(self, *a, **k): raise _ReqHata("sahte requests: ag yok")
    get = post = request
rq.Session = _Oturum
sys.modules["requests"] = rq
for p in ("scripts/prodigi", "scripts/etsy", "scripts/guvenlik"):
    sys.path.insert(0, os.path.join(KOK, p))
import order_router as R
SIPARIS = {"id": ORD, "merchantReference": REF, "created": "2026-11-10T10:00:00Z", "lastUpdated": "2026-11-11T10:00:00Z",
           "shippingMethod": "Standard", "status": {"stage": "Complete", "details": {"printReadyAssetsPrepared": "Complete"},
           "issues": [{"errorCode": "X", "description": "ref " + REF}]},
           "recipient": {"address": {"countryCode": "US", "townOrCity": "Town", "stateOrCounty": "ST"}},
           "items": [{"sku": "GLOBAL-HPR-8x10", "copies": 1, "merchantReference": REF, "status": "Ok",
                      "assets": [{"printArea": "default", "url": "https://x/y.png", "md5Hash": "abc"}]}],
           "charges": [{"totalCost": {"amount": "10", "currency": "USD"}, "items": []}],
           "shipments": [{"carrier": {"name": "UPS", "service": "Ground"}, "tracking": {"number": TAKIP, "url": "https://t/" + TAKIP},
                          "dispatchDate": "2026-11-11", "status": "Shipped"}]}
IKINCI = dict(SIPARIS, id="ord_2222222222", created="2026-11-12T10:00:00Z")
KANAL = dict(SIPARIS, id="ord_3333333333", merchantReference=RID, created="2026-11-13T10:00:00Z",   # Etsy kanal siparisi (ref = ciplak no)
             status={"stage": "InProgress", "details": {"printReadyAssetsPrepared": "NotStarted"}, "issues": []})
HATA404 = os.environ.get("T_HATA404") == "1"
def _cagri(self, method, path, body=None):
    if HATA404:
        return 404, {"outcome": "NotFound", "merchantReference": REF, "id": ORD}
    if path.startswith("/orders/"):
        return 200, {"order": SIPARIS if path.endswith(ORD) else KANAL if path.endswith("3333333333") else IKINCI}
    return 200, {"orders": [SIPARIS, IKINCI, KANAL], "hasMore": False}
R.load_prodigi_key = lambda env: "sahte"
R.Prodigi.call = _cagri
R.Prodigi.get_order = lambda self, oid: _cagri(self, "GET", "/orders/" + oid)
class _Depo:
    def __init__(self, *a, **k): pass
    def needs_refresh(self): return False
class _Etsy:
    def __init__(self, *a, **k): pass
    def get(self, path, ok404=False):
        return {"receipt_id": int(RID), "create_timestamp": 1794900000, "is_shipped": True, "country_iso": "US", "city": "Town",
                "shipments": [{"carrier_name": "ups", "tracking_code": TAKIP}],
                "transactions": [{"sku": "S", "quantity": 1, "title": "T", "variations": []}]}
R.TokenStore, R.Etsy = _Depo, _Etsy
import prodigi_pilot_quote as PQ
class _Api:
    def __init__(self, *a, **k): pass
    def _call(self, method, path, body=None):
        kod, veri = _cagri(None, method, path)
        if "merchantReference=" in path:
            veri = {"orders": [SIPARIS]}
        return _Yanit(kod, veri)
PQ.Api, PQ.load_key = _Api, (lambda *a, **k: "sahte")
if MASKE == "kapali":                       # bilinen FAIL: maske yok
    R.maskeli_cikti_kur = lambda: None
    R.maskeli_metin_tam = lambda t: t
sys.argv = [BETIK] + sys.argv[4:]
runpy.run_path(BETIK, run_name="__main__")
'''


def kos(betik, argv, maske="acik", hata404=False, anahtar=True):
    with tempfile.TemporaryDirectory() as d:
        ozet = Path(d) / "ozet.md"
        ozet.write_text("")
        env = {"PATH": os.environ.get("PATH", ""), "GITHUB_STEP_SUMMARY": str(ozet),
               "TOKEN_FILE": str(Path(d) / "yok.json"), "ETSY_SHOP_ID": "39729443", "T_HATA404": "1" if hata404 else "0"}
        if anahtar:                       # pod-arac-v4 ana adimi ETSY_SHARED_SECRET verir (yml:212); prodigi-quote vermez
            env["ETSY_SHARED_SECRET"] = "k"
        argv = [x.replace("{OUT}", d) for x in argv]
        r = subprocess.run([sys.executable, "-I", "-c", SURUCU, str(KOK), str(KOK / betik), maske] + argv,
                           capture_output=True, text=True, timeout=120, env=env, cwd=d)
        return r.returncode, r.stdout, r.stderr, ozet.read_text()


def denetim(cikti):
    """Acik deger listesi (bos = temiz)."""
    return [x for x in (RID, ORD, TAKIP, "1234567890", "0291980793", "3333333333") if x in cikti]


def kontrol(ad, kosul, ek=""):
    print(("PASS " if kosul else "FAIL ") + ad + (f" [{ek}]" if ek and not kosul else ""))
    if not kosul:
        HATA.append(ad)


BETIKLER = [   # (betik, argv, ozet yazar mi, gercek is akisinda anahtar var mi)
    ("scripts/prodigi/takip_kuru.py", ["--env", "live", "--out", "{OUT}/takip", "--top", "5", "--url-kontrol", "kapali"], True, True,
     r"\| S-[0-9a-f]{8} \("),                                   # receipt sutunu
    ("scripts/prodigi/siparis_kiyas.py", ["--env", "live", "--siparis", ORD, "--kiyas", "ord_2222222222", "--top", "5"], True, True,
     r'"merchantReference": "etsy-S-[0-9a-f]{8}-8x10"'),
    ("scripts/prodigi/prodigi_siparis_oku.py", [ORD, REF, "5"], False, False, r'"merchantReference": "etsy-S-gizli-8x10"'),
]
import re  # noqa: E402
for betik, argv, ozet_var, anahtar, kod in BETIKLER:
    rc, so, se, oz = kos(betik, argv, anahtar=anahtar)
    hepsi = so + se + oz
    kontrol(f"{betik}: gercek main() rc 0", rc == 0, f"rc={rc} stderr={se[-300:]}")
    kontrol(f"{betik}: veri ciktiya ulasti (stdout satiri > 3)", len(so.splitlines()) > 3, so[-200:])
    kontrol(f"{betik}: stdout + stderr + ozet'te acik siparis no / ord / takip yok", not denetim(hepsi), str(denetim(hepsi)))
    # UPS 1Z: Merkez S1 (4 Kas) sirasi: once fis deseni -> 10 hanelik kuyruk S- kodu, 1Z + gonderici kodu (8 karakter) kalir
    # (test_receipt_desen "UPS 1Z" ile ayni; bilinen sinir, raporda). Rakam kuyrugu acik degil (denetim listesinde).
    kontrol(f"{betik}: ord_ son 4 hane gorunur", "ord_***7890" in so, so[:300])
    kontrol(f"{betik}: merchantReference opak kod ({'S-<8 hex>' if anahtar else 'anahtarsiz S-gizli'}, is akisi ortami)",
            re.search(kod, so) is not None, so[:300])
    if ozet_var:
        kontrol(f"{betik}: adim ozeti yazildi ve denetlendi ({len(oz.splitlines())} satir)", len(oz.splitlines()) > 3 and not denetim(oz),
                str(denetim(oz)))
    rc2, so2, se2, oz2 = kos(betik, argv, maske="kapali", anahtar=anahtar)
    kontrol(f"{betik}: bilinen FAIL: maske kapaliyken denetim sizintiyi bulur", rc2 == 0 and bool(denetim(so2 + se2 + oz2)),
            f"rc={rc2}")
    if ozet_var:
        kontrol(f"{betik}: bilinen FAIL: maskesiz adim ozeti sizintiyi tasir", bool(denetim(oz2)))

# kanal_oku.py (modul duzeyi betik, main yok): ozet satirinda kanal_ilerlemeyen_acik ord kimlikleri; pod-arac-v4.yml kanal_oku
rc, so, se, oz = kos("scripts/prodigi/kanal_oku.py", ["{OUT}/kanal"])
kontrol("kanal_oku: rc 0, ilerlemeyen kanal siparisi ozette son 4 (ord_***3333), acik ord / no yok",
        rc == 0 and "kanal_ilerlemeyen_acik: ['ord_***3333']" in so and not denetim(so + se), f"rc={rc} {denetim(so + se)} {se[-300:]}")
rc, so, se, oz = kos("scripts/prodigi/kanal_oku.py", ["{OUT}/kanal"], maske="kapali")
kontrol("bilinen FAIL: kanal_oku maskesiz tam ord kimligini basar", rc == 0 and "ord_3333333333" in so)

# hata yolu: GET 404 -> sys.exit(...) metni (yanitta merchantReference / ord) stderr'de maskeli
rc, so, se, oz = kos("scripts/prodigi/siparis_kiyas.py", ["--siparis", ORD], hata404=True)
kontrol("siparis_kiyas hata yolu: cikis 1, stderr'de HATA satiri, acik no yok", rc == 1 and "HATA" in se and not denetim(so + se),
        f"rc={rc} {denetim(so + se)}")
rc, so, se, oz = kos("scripts/prodigi/siparis_kiyas.py", ["--siparis", ORD], maske="kapali", hata404=True)
kontrol("bilinen FAIL: hata yolu maskesiz stderr'e no basar", rc == 1 and bool(denetim(se)))

# --- is akisi: pod-arac-v4 LISTING (iptal_dok / siparis_kiyas ord id) ve prodigi-quote ekstra_tesis (IP c3)
import yaml  # noqa: E402


def adimlar(yol, metin=None):
    d = yaml.safe_load(metin if metin is not None else (KOK / yol).read_text())
    return d, [s for j in d["jobs"].values() for s in j.get("steps", [])]


def _degerler(x):
    """Ayristirilmis YAML'daki tum metin degerleri (anahtarlar dahil; YAML kacislari cozulmus)."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k)
            yield from _degerler(v)
    elif isinstance(x, list):
        for v in x:
            yield from _degerler(v)
    elif x is not None:
        yield str(x)


LISTING_IFADE = re.compile(r"""(?i)inputs\s*(\.\s*listing\b|\[\s*['"]listing['"])|\[\s*['"]inputs['"]\s*\]|"""
                           r"""tojson\s*\(\s*(inputs|github(\.event(\.inputs)?)?)\s*\)""")


def pod_kontrol(metin):
    d, st = adimlar(".github/workflows/pod-arac-v4.yml", metin)
    env = {k for j in d["jobs"].values() for k in (j.get("env") or {})}
    ilk = st[0].get("run", "")
    kanal = [s["run"] for s in st if "kanal_oku.py" in s.get("run", "")]
    kanal_satir = [x for r in kanal for x in r.splitlines() if "kanal_oku.py" in x]
    # inceleme 2 (ORTA 1): her YAML degerindeki her ${{ }} ifadesi; buyuk/kucuk harf, ['inputs'] erisimi, toJSON(inputs|github)
    ifade = [x for v in _degerler(d) for x in re.findall(r"\$\{\{(.*?)\}\}", v, re.S)]
    return (not any(LISTING_IFADE.search(x) for x in ifade)
            and "LISTING" not in env and "inputs.listing" in ilk and "::add-mask::$o" in ilk and "LISTING<<" in ilk
            and kanal_satir and all("| python3 scripts/guvenlik/kargo_maske.py" in x for x in kanal_satir))


pm = (KOK / ".github/workflows/pod-arac-v4.yml").read_text()
kontrol("pod-arac-v4: job env'de LISTING yok, listing maske adiminda okunur + ord maskesi, kanal_oku kargo_maske'den gecer", pod_kontrol(pm))
eski = pm.replace("    env:\n      MOD:", "    env:\n      LISTING: ${{ inputs.listing || '4570110641' }}\n      MOD:", 1)
kontrol("bilinen FAIL: eski job env LISTING satiri denetimden gecmez", eski != pm and not pod_kontrol(eski))
eski = pm.replace("    env:\n      MOD:", "    env:\n      OID: ${{ inputs.listing }}\n      MOD:", 1)
kontrol("bilinen FAIL (inceleme m1): baska adla job env tasiyicisi denetimden gecmez", eski != pm and not pod_kontrol(eski))
eski = pm.replace("      - name: Girdi maskesi (IP adim 0 c, 17 Kas; siparis ref / onay / alici loga *** olur)\n",
                  "      - name: Girdi maskesi (IP adim 0 c, 17 Kas; siparis ref / onay / alici loga *** olur)\n"
                  "        env: { L2: \"${{ github.event.inputs.listing }}\" }\n", 1)
kontrol("bilinen FAIL (inceleme m3): maske adiminda adim env tasiyicisi denetimden gecmez", eski != pm and not pod_kontrol(eski))
for ad, satir in (("inputs.LISTING", "OID: ${{ inputs.LISTING }}"), ("github.event['inputs']['listing']", "OID: ${{ github.event['inputs']['listing'] }}"),
                  ("toJSON(inputs)", "EV: ${{ toJSON(inputs) }}"), ("toJSON(github.event)", "EV: ${{ toJSON(github.event) }}"),
                  ("YAML kacisi", 'OID: "${{ inputs.\\u006cisting }}"')):
    eski = pm.replace("    env:\n      MOD:", "    env:\n      " + satir + "\n      MOD:", 1)
    kontrol(f"bilinen FAIL (inceleme 2 ORTA 1): job env {ad} denetimden gecmez", eski != pm and not pod_kontrol(eski))
eski = pm.replace("\njobs:\n", "\nrun-name: ${{ inputs.Listing }}\njobs:\n", 1)
kontrol("bilinen FAIL (inceleme 2 ORTA 1): run-name inputs.Listing denetimden gecmez", eski != pm and not pod_kontrol(eski))
eski = pm.replace("    env:\n      MOD:", "    env:\n      LISTING_ADI: listing\n      MOD:", 1)
kontrol("bilinen PASS: ifade disinda 'listing' kelimesi (ifade yok) yanlis FAIL vermez", eski != pm and pod_kontrol(eski))


def adim_kos(run, olay):
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "olay.json").write_text(json.dumps(olay))
        (Path(d) / "env").write_text("")
        (Path(d) / "adim.sh").write_text(run)
        r = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", str(Path(d) / "adim.sh")], capture_output=True,
                           text=True, timeout=60, cwd=d, env={"PATH": os.environ.get("PATH", ""), "GITHUB_EVENT_PATH": str(Path(d) / "olay.json"),
                                                               "GITHUB_ENV": str(Path(d) / "env")})
        return r.returncode, r.stdout, (Path(d) / "env").read_text()


ilk = adimlar(".github/workflows/pod-arac-v4.yml")[1][0]["run"]
rc, so, ge = adim_kos(ilk, {"inputs": {"mod": "siparis_kiyas", "listing": "ord_1234567890, ord_2222222222"}})
kontrol("pod-arac-v4 maske adimi (bash -eo pipefail): iki ord kimligi + rakamlari maskelenir, LISTING GITHUB_ENV'de",
        rc == 0 and all(f"::add-mask::{x}" in so.splitlines() for x in ("ord_1234567890", "1234567890", "ord_2222222222", "2222222222"))
        and "LISTING<<" in ge and "ord_1234567890, ord_2222222222" in ge, f"rc={rc} {so[-300:]}")
rc, so, ge = adim_kos(ilk, {"inputs": {"mod": "iptal_dok", "listing": "ORD_9876543210"}})
kontrol("pod-arac-v4 maske adimi: buyuk harf ORD_ de maskelenir (inceleme 6)", rc == 0 and "::add-mask::ORD_9876543210" in so.splitlines()
        and "::add-mask::9876543210" in so.splitlines(), f"rc={rc}")
rc, so, ge = adim_kos(ilk, {"inputs": {"mod": "kuru"}})
kontrol("pod-arac-v4 maske adimi: listing bos -> varsayilan 4570110641, ord maskesi yok (bilinen PASS)",
        rc == 0 and "\n4570110641\n" in ge and "::add-mask::ord_" not in so, f"rc={rc}")
rc, so, ge = adim_kos(ilk.replace('echo "::add-mask::$o"', 'true'), {"inputs": {"listing": "ord_1234567890"}})
kontrol("bilinen FAIL: maske satiri kaldirilinca ord kimligi maskelenmez", "::add-mask::ord_1234567890" not in so)

qm = (KOK / ".github/workflows/prodigi-quote.yml").read_text()


def quote_kontrol(metin):
    _, st = adimlar(".github/workflows/prodigi-quote.yml", metin)
    run = "\n".join(s.get("run", "") for s in st)
    blok = run.split('if [ "$MODE" = "ekstra_tesis" ]; then', 1)[1].split("exit 0", 1)[0]
    satir = [x.split("#", 1)[0].strip() for x in blok.splitlines() if x.strip() and not x.strip().startswith("#")]
    cikis = [x for x in satir if "STEP_SUMMARY" in x or x.startswith(("head", "cat", "echo", "tail", "printf"))]
    kos_ = [x for x in satir if "prodigi_ekstra_tesis.py" in x and "--self-test" not in x]   # rapor tum ord'lari stdout'a basar
    art = [s for s in st if "upload-artifact" in str(s.get("uses", ""))]
    yol = str(art[0]["with"]["path"]) if len(art) == 1 else ""
    return (cikis and all(x.endswith("| python3 scripts/guvenlik/tam_maske.py") or "python3 scripts/guvenlik/tam_maske.py <" in x
                          for x in cikis)
            and len(kos_) == 1 and (kos_[0].endswith("> /dev/null") or kos_[0].endswith("| python3 scripts/guvenlik/tam_maske.py"))
            and "!out/PRODIGI_EKSTRA_TESIS.*" in yol
            and "!out/EKSTRA_TESIS.json" in yol)


kontrol("prodigi-quote ekstra_tesis: rapor stdout'u /dev/null, ozet ve head tam_maske'den gecer, ekstra dosyalari artifact'e girmez",
        quote_kontrol(qm))
eski = qm.replace('python3 scripts/guvenlik/tam_maske.py < out/PRODIGI_EKSTRA_TESIS.md >> "$GITHUB_STEP_SUMMARY"',
                  'cat out/PRODIGI_EKSTRA_TESIS.md >> "$GITHUB_STEP_SUMMARY"')
kontrol("bilinen FAIL: maskesiz cat ozeti denetimden gecmez", eski != qm and not quote_kontrol(eski))
eski = qm.replace("            !out/EKSTRA_TESIS.json\n", "")
kontrol("bilinen FAIL: artifact disarida birakmasi silinince denetimden gecmez", eski != qm and not quote_kontrol(eski))
eski = qm.replace("--out-dir out > /dev/null   # skus", "--out-dir out   # skus")
kontrol("bilinen FAIL (inceleme m2): rapor stdout'u loga acilinca denetimden gecmez", eski != qm and not quote_kontrol(eski))
eski = qm.replace("head -40 out/PRODIGI_EKSTRA_TESIS.md | python3 scripts/guvenlik/tam_maske.py",
                  "head -40 out/PRODIGI_EKSTRA_TESIS.md | python3 scripts/guvenlik/kargo_maske.py")
kontrol("bilinen FAIL (inceleme 4): yalniz kargo_maske (fis maskesi yok) denetimden gecmez", eski != qm and not quote_kontrol(eski))
# ekstra_tesis ozetinin gercek maskesi: rapor() ciktisi tam_maske'den gecince ord yalniz son 4, fatura aciklamasindaki fis no opak
sys.path.insert(0, str(KOK / "scripts/prodigi"))
sys.path.insert(0, str(KOK / "scripts/guvenlik"))
os.environ["REF_SIPARIS"] = ORD
import kargo_maske  # noqa: E402
import prodigi_ekstra_tesis as PE  # noqa: E402
PE.REF_SIPARIS = ORD
with tempfile.TemporaryDirectory() as d:
    o = {"id": ORD, "created": "2026-11-10", "status": {"stage": "Complete"},
         "charges": [{"totalCost": {"amount": "5", "currency": "USD"},
                      "items": [{"description": "Postcard " + REF, "itemSku": "X", "cost": {"amount": "5", "currency": "USD"}}]}]}
    md = PE.rapor([PE.siparis_ozet(o)], 1.3, "t", d)
    AGSIZ = ("import socket, sys, runpy\ndef _y(*a, **k): raise AssertionError('ag')\nsocket.socket.connect = _y; socket.socket.connect_ex = _y; socket.create_connection = _y\n"
             "sys.argv = [sys.argv[1]]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n")
    sonuc_ = {}
    for arac in ("tam_maske.py", "kargo_maske.py"):
        sonuc_[arac] = subprocess.run([sys.executable, "-I", "-c", AGSIZ, str(KOK / "scripts/guvenlik" / arac)], input=md,
                                      capture_output=True, text=True, timeout=60, env={"PATH": os.environ.get("PATH", "")})
r_ = sonuc_["tam_maske.py"]
kontrol("ekstra_tesis raporu: ham metinde tam ord + fis no var; tam_maske sonrasi ord_***7890, fis no opak (S-gizli)",
        ORD in md and RID in md and r_.returncode == 0 and not denetim(r_.stdout) and "ord_***7890" in r_.stdout
        and "etsy-S-gizli-8x10" in r_.stdout, r_.stderr[-300:])
kontrol("bilinen FAIL: yalniz kargo_maske fatura aciklamasindaki fis noyu birakir", RID in sonuc_["kargo_maske.py"].stdout)

print("maske calisma testi: %d FAIL" % len(HATA))
sys.exit(1 if HATA else 0)
