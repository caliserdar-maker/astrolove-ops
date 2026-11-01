#!/usr/bin/env python3
"""AI beyan kapisi KALICI testleri (Merkez / Serdar 31 Eki, Gorev E). ETSY YOK, ag yok.
Etsy kurali: "Sellers must disclose within their listing description if an item is created with the use of AI." Kapi tek yerde:
etsy_common.Etsy._call -> ai_beyan_kapisi (aciklama yazan her istek). Bu test:
  A  kapi birimi: EN updateListing (PATCH / PUT), createDraftListing (POST data / json), ceviri PUT (RU), kismi yazim (aciklamasiz) gecer,
     celisen govde / tanimsiz dil / beyansiz metin FAIL; YD tek gecis EN PATCH + RU PUT (6c, 1 Kas).
  B  _call gercek yol: Etsy._call beyansiz aciklamada istek GONDERMEZ (requests cagrilmaz), beyanliysa gonderir; BEYAN_HATA dolar.
  C  dogrudan requests korumasi (statik): scripts/ altinda Etsy'ye dogrudan requests.post/put/patch yapan ve govdesinde description olan
     her cagrinin 8 satir oncesinde ai_beyan_kapisi( olmali (createDraftListing: by78_taslak, by_taslak_ac, kupa_taslak). Yeni bir
     dogrudan yazim kapisiz eklenirse FAIL.
  D  kapsam (statik): aciklama yazan her betik (patch / put / post cagrisi yaninda "description" ya da translations) etsy_common'u kullanir
     ya da C kapsamindadir; baska HTTP istemcisiyle Etsy'ye aciklama yazan betik FAIL.
  E  eski kaynak metinleri FAIL: beyansiz eski kupa EN (kupa_en_ornek beyan=False), YD canli HAM aciklamasi (test_veri), RU eski metin.
  F  kacis yollari (inceleme 31 Eki madde 7): yol sorgu dizesi, post_file createDraftListing, rus / zh-hant, tekrarli description, JSON dizesi,
     None degeri, generator govde; surec cikisi (os._exit 1) alt surecte olculur.
Bilinen sinirlar (statik C): kapi cagrisinin her dalda calistigi (dominans) kanitlanmaz; yalniz ayni fonksiyonda cagri ONCE gelir.
Calistir: python3 scripts/etsy/test_ai_beyan.py           (tam: A-F + depo taramasi; CI ai-beyan-test.yml)
          python3 scripts/etsy/test_ai_beyan.py --canli   (canli yukleyici adimi: yalniz kapi davranisi A/B/E/F; ilgisiz betik koşuyu durdurmaz)"""
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KOK = HERE.parents[1]
sys.path.insert(0, str(HERE))
import etsy_common as E  # noqa: E402
from beyan_marka_yaz import BEYAN, RU_BEYAN  # noqa: E402

sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def gecer(method, path, **kw):
    try:
        E.ai_beyan_kapisi(method, path, **kw); return True
    except E.BeyanYok:
        return False
    finally:
        E.BEYAN_HATA.clear()          # test kayitlari surec cikisinda ::error:: olarak basilmasin


def birim():
    d1, d0 = "Line one.\n\n" + BEYAN + "\n\nMore.", "Line one.\n\nNo disclosure here."
    k("A1 EN updateListing PATCH beyanli gecer / beyansiz FAIL",
      gecer("PATCH", "/shops/1/listings/123", data={"description": d1}) and not gecer("PATCH", "/shops/1/listings/123", data={"description": d0}))
    k("A2 updateListing PUT (json) beyansiz FAIL", not gecer("PUT", "/shops/1/listings/123", json_body={"description": d0}))
    k("A3 createDraftListing POST (data) beyanli gecer / beyansiz FAIL",
      gecer("POST", "/shops/1/listings", data={"description": d1, "title": "t"}) and not gecer("POST", "/shops/1/listings", data={"description": d0}))
    k("A4 ceviri PUT RU: RU beyani gecer, EN beyani RU'da yetmez",
      gecer("PUT", "/shops/1/listings/123/translations/ru", data={"description": "Текст.\n\n" + RU_BEYAN})
      and not gecer("PUT", "/shops/1/listings/123/translations/ru", data={"description": d1}))
    k("A5 kismi yazim (yalniz baslik / etiket / state) aciklamayi degistirmez, gecer",
      gecer("PATCH", "/shops/1/listings/123", data={"title": "x", "tags": "a,b"}) and gecer("PATCH", "/shops/1/listings/123", data={"state": "active"}))
    k("A6 celisen govdeler (data beyanli, json beyansiz) FAIL",
      not gecer("PATCH", "/shops/1/listings/123", data={"description": d1}, json_body={"description": d0}))
    k("A7 tanimsiz dil (de) FAIL (beyan cumlesi yok)", not gecer("PUT", "/shops/1/listings/123/translations/de", data={"description": d1}))
    k("A8 GET hic etkilenmez", gecer("GET", "/shops/1/listings/123", params={"description": d0}))
    k("A9 satir sonlu beyan da bulunur", gecer("PATCH", "/shops/1/listings/9", data={"description": "a\n\n" + BEYAN.replace(" ", "\n", 2)}))
    k("A9b HTML varlikli beyan (&#32; / &nbsp;) bulunur, HTML ile bolunmus beyan (<b>) FAIL (guvenli taraf)",
      gecer("PATCH", "/shops/1/listings/9", data={"description": "a " + BEYAN.replace(" ", "&#32;", 3)})
      and not gecer("PATCH", "/shops/1/listings/9", data={"description": "a " + BEYAN.replace("AI tools", "<b>AI</b> tools")}))
    # YD: tek gecis PATCH yalniz EN (title + description); RU kapisi YD yolunda yok
    k("A10 YD tek gecis PATCH (title + description, EN) beyanli gecer / beyansiz FAIL",
      gecer("PATCH", "/shops/1/listings/4595350971", data={"title": "T", "description": d1})
      and not gecer("PATCH", "/shops/1/listings/4595350971", data={"title": "T", "description": d0}))
    yd = (KOK / "scripts/kapak78/yd_kapak_yukle.py").read_text(encoding="utf-8")
    agac = ast.parse(yd)
    # 6c (Serdar 1 Kas): YD tek geciste RU da yazilir; YALNIZ api.put ile (Etsy._call: ru_yazim_kapisi + ai_beyan_kapisi), dogrudan HTTP yok;
    # kuruda tg_metin_kapisi EN + RU beyanini birlikte (beyan_on_kontrol) ve RU_YASAK'i denetler
    ru_yaz = [n for n in ast.walk(agac) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and any(isinstance(x, ast.JoinedStr) and "/translations/ru" in ast.unparse(x) for x in n.args[:1])
              and n.func.attr not in ("get",)]
    fn = {n.name: ast.unparse(n) for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)}
    kap_src = fn.get("tg_metin_kapisi", "") + fn.get("tg_ru_kapisi", "")   # yasak ifade kuruda; beyan canli RU ile planda (karar 3 + 4)
    if "tg_ru_kapisi" not in fn:   # Serdar 1 Kas: main'e yalniz AI beyan v2; YD tek gecis RU yolu yd-kapak dalinda (A11 orada kosar)
        print("ATLANDI A11 YD RU yazimi: yd_kapak_yukle tek gecis RU yolu bu dalda yok (YD degisiklikleri main'e alinmadi)")
        return
    k(f"A11 YD RU yazimi yalniz api.put ({[n.func.attr for n in ru_yaz]}), dogrudan requests yok; kuru kapisi beyan_on_kontrol + RU_YASAK",
      ru_yaz and all(n.func.attr == "put" and ast.unparse(n.func.value) == "api" for n in ru_yaz) and "requests" not in yd
      and "beyan_on_kontrol" in fn.get("tg_ru_kapisi", "") and "RU_YASAK" in fn.get("tg_metin_kapisi", "") and "RU metni yok" in kap_src)


def call_yolu():
    import requests
    gonderilen = []

    class R:
        status_code, headers, text = 200, {"x-remaining-today": "5000"}, "{}"

        def json(self):
            return {}
    gercek = requests.request
    requests.request = lambda *a, **kw: (gonderilen.append((a, kw)), R())[1]
    try:
        api = E.Etsy.__new__(E.Etsy)
        api.__dict__.update(calls=0, remaining=5000, store=type("S", (), {"access_token": "x"})(), api_key="k", shared_secret="s")
        E.BEYAN_HATA.clear()
        try:
            api._call("PATCH", "/shops/1/listings/555", data={"description": "no disclosure"})
            dur = False
        except E.BeyanYok:
            dur = True
        k("B1 Etsy._call beyansiz aciklamada istek GONDERMEZ, BEYAN_HATA'ya ilan id", dur and not gonderilen and E.BEYAN_HATA
          and E.BEYAN_HATA[-1][0] == "555", f"gonderilen {len(gonderilen)} hata {E.BEYAN_HATA}")
        class Gecti(Exception):
            pass

        def isaret():
            raise Gecti()
        api._istek_oncesi = isaret          # kapidan sonraki ilk adim: buraya ulasildiysa kapi gecildi
        try:
            api._call("PATCH", "/shops/1/listings/556", data={"description": "x\n\n" + BEYAN}); gecti = False
        except Gecti:
            gecti = True
        k("B2 Etsy._call beyanli aciklamada kapidan gecer (gonderim adimina ulasir)", gecti)
        api._istek_oncesi = lambda: (_ for _ in ()).throw(Gecti())
        try:
            api.post_file("/shops/1/listings", {}, data={"description": "no disclosure"}); pf = "gecti"
        except E.BeyanYok:
            pf = "kapi"
        except Gecti:
            pf = "gecti"
        try:
            api.post_file("/shops/1/listings/557/images", {}, data={"rank": 1}); pg = "kapi"
        except Gecti:
            pg = "gecti"
        k("B3 post_file: beyansiz multipart createDraftListing kapida durur, gorsel yukleme etkilenmez", pf == "kapi" and pg == "gecti", f"{pf} {pg}")
    finally:
        requests.request = gercek
        E.BEYAN_HATA.clear()


HTTP_YAZ = {"post", "put", "patch", "request", "urlopen", "Request"}


def _kaynak(n, t):
    try:
        return ast.get_source_segment(t, n) or ""
    except Exception:   # noqa: BLE001
        return ""


def _literal_anahtarlar(c):
    out = set()
    for kw in c.keywords:
        if kw.arg in ("data", "json") and isinstance(kw.value, ast.Dict):
            out |= {k_.value for k_ in kw.value.keys if isinstance(k_, ast.Constant)}
    return out


def _aciklamasiz_literal(c):
    """Govde anahtarlari (data / json / files / params) hepsi literal dict ve description / ** yok mu (or. state PATCH)."""
    gv = [kw for kw in c.keywords if kw.arg in ("data", "json", "files", "params")]
    if any(kw.arg is None for kw in c.keywords) or len(c.args) > 2:
        return False
    for kw in gv:
        v = kw.value
        if not isinstance(v, ast.Dict) or any(k_ is None or not isinstance(k_, ast.Constant) or k_.value == "description" for k_ in v.keys):
            return False
    return True


def statik():
    """AST taramasi (inceleme 31 Eki madde 1): cok satirli cagri, degiskenle kurulan URL, Session / urllib, yorum metni sayilmaz."""
    ihlal, baska_istemci, yazanlar = [], [], []
    for f in sorted((KOK / "scripts").rglob("*.py")):
        rel = str(f.relative_to(KOK))
        if "/test_" in rel or "__pycache__" in rel or rel.endswith("etsy_common.py") or rel.endswith("_selftest.py"):
            continue
        t = f.read_text(encoding="utf-8", errors="replace")
        etsy = bool(re.search(r"openapi\.etsy\.com|ETSY_API|from etsy_common import|import etsy_common", t))
        if not etsy:
            continue
        try:
            agac = ast.parse(t)
        except SyntaxError as e:
            ihlal.append(f"{rel}: ayristirilamadi ({e})"); continue
        aciklama = bool(re.search(r"[\"']description[\"']|translations", t))
        if aciklama:
            yazanlar.append(rel)
        fonks = [n for n in ast.walk(agac) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for c in ast.walk(agac):
            if not (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in HTTP_YAZ):
                continue
            taban = _kaynak(c.func.value, t)
            if c.func.attr in ("urlopen", "Request") or re.search(r"urllib|httpx|http\.client|aiohttp", taban):
                yaz = c.func.attr in ("post", "put", "patch") or len(c.args) >= 2 or any(
                    kw.arg == "data" or (kw.arg == "method" and not (isinstance(kw.value, ast.Constant) and str(kw.value.value).upper() in ("GET", "HEAD")))
                    for kw in c.keywords)
                if aciklama and yaz:          # yalniz govdeli / yontemli istek (GET gorsel indirme sayilmaz)
                    baska_istemci.append(f"{rel}:{c.lineno}")
                continue
            if not re.search(r"requests|[Ss]ession|\bses\b|\bsess\b", taban):
                continue
            if c.func.attr == "request" and not c.args and not c.keywords:
                continue
            # yalniz GET (requests.get) bu kumede yok; requests.request(method, ...) yontemi bilinmedigi icin muaf DEGIL
            ic = [fn for fn in fonks if fn.lineno <= c.lineno <= (fn.end_lineno or fn.lineno)]
            kapsam = min(ic, key=lambda fn: (fn.end_lineno or 0) - fn.lineno) if ic else agac
            if _aciklamasiz_literal(c) and c.func.attr != "request":
                # karar 1 (1 Kas): state yazan dogrudan istek (yayina alma) ayni fonksiyonda once yayin_beyan_kontrol cagirmali
                if "state" in _literal_anahtarlar(c) and not [n for n in ast.walk(kapsam) if isinstance(n, ast.Call) and n.lineno <= c.lineno
                                                           and getattr(n.func, "attr", getattr(n.func, "id", "")) == "yayin_beyan_kontrol"]:
                    ihlal.append(f"{rel}:{c.lineno} (state yazimi, yayin_beyan_kontrol yok)")
                continue
            kapi = [n for n in ast.walk(kapsam) if isinstance(n, ast.Call) and n.lineno < c.lineno
                    and getattr(n.func, "attr", getattr(n.func, "id", "")) == "ai_beyan_kapisi"]
            if not kapi:
                ihlal.append(f"{rel}:{c.lineno}")
        if aciklama and re.search(r"subprocess.*curl|os\.system\(.*curl", t):
            baska_istemci.append(f"{rel}: curl")
    kabuk = []
    for f in list((KOK / "scripts").rglob("*.sh")) + list((KOK / ".github/workflows").glob("*.yml")):
        t = f.read_text(encoding="utf-8", errors="replace")
        for i, ln in enumerate(t.splitlines()):
            if re.search(r"curl[^\n]*(openapi\.etsy\.com|\$\{?ETSY)", ln) and re.search(r"-X\s*(PATCH|PUT|POST)|--data|-d\s|-F\s", ln) \
                    and re.search(r"description|translations", ln):
                kabuk.append(f"{f.relative_to(KOK)}:{i + 1}")
    k(f"C Etsy'ye dogrudan requests / Session yazimlarinin hepsi ayni fonksiyonda once ai_beyan_kapisi cagiriyor (AST, {len(ihlal)} ihlal)",
      not ihlal, str(ihlal[:6]))
    k(f"D aciklama yazan {len(yazanlar)} betikte baska HTTP istemcisi (urllib / httpx / curl) ile Etsy yazimi yok", not baska_istemci, str(baska_istemci[:5]))
    k(f"D2 .sh ve workflow dosyalarinda curl ile Etsy'ye aciklama yazimi yok", not kabuk, str(kabuk[:5]))
    return yazanlar


def mutasyon():
    """C/D'nin gercekten yakaladigini kanitlar: gecici dosyalarla 9 kacis bicimi (inceleme madde 1) + 2 muaf bicim."""
    import shutil
    import tempfile
    global KOK
    eski = KOK
    ornekler = {
        "cok_satir": 'import requests\nAPI="https://openapi.etsy.com/v3/application"\ndef f(d):\n    requests.post(\n        API + "/shops/1/listings",\n        data={"description": d})\n',
        "degisken_url": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(d):\n    url = API + "/shops/1/listings/2"\n    requests.patch(url, data={"description": d})\n',
        "session": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(d):\n    requests.Session().patch(API + "/x", data={"description": d})\n',
        "yorum": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(d):\n    # ai_beyan_kapisi(\n    requests.patch(API + "/shops/1/listings/2", data={"description": d})\n',
        "karisik_govde": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(t, d):\n    requests.patch(API + "/shops/1/listings/2", data={"title": t}, json={"description": d})\n',
        "ortam_url": 'import os, requests\nAPI=os.environ["ETSY_API"]\ndef f(d):\n    requests.put(API + "/listings/2", json={"description": d})\n',
        "urllib": 'import urllib.request\nAPI="https://openapi.etsy.com/v3"\ndef f(b):\n    urllib.request.urlopen(urllib.request.Request(API + "/x", data=b, method="PATCH"))\nK = "description"\n',
        "request_method": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(m, g):\n    requests.request(m, API + "/shops/1/listings/2", data=g)\nK = "description"\n',
        "state_kontrolsuz": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f():\n    requests.patch(API + "/shops/1/listings/2", data={"state": "active"})\nK = "description"\n',
        "baska_fonk_kapi": 'import requests\nfrom etsy_common import ai_beyan_kapisi\nAPI="https://openapi.etsy.com/v3"\ndef g(d):\n    ai_beyan_kapisi("PATCH", "/shops/1/listings/2", data={"description": d})\ndef f(d):\n    requests.patch(API + "/shops/1/listings/2", data={"description": d})\n',
    }
    muaf = {
        "state_literal": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f(api):\n    api.yayin_beyan_kontrol("PATCH", "/shops/1/listings/2", data={"state": "active"})\n    requests.patch(API + "/shops/1/listings/2", data={"state": "active"})\nK = "description"\n',
        "baslik_literal": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f():\n    requests.patch(API + "/shops/1/listings/2", data={"title": "t"})\nK = "description"\n',
        "kapili": 'import requests\nfrom etsy_common import ai_beyan_kapisi\nAPI="https://openapi.etsy.com/v3"\ndef f(d):\n    ai_beyan_kapisi("POST", "/shops/1/listings", data=d)\n    requests.post(\n        API + "/shops/1/listings", data=d)\nK = "description"\n',
    }
    yakalanan, kacan = [], []
    for grup, beklenen in ((ornekler, True), (muaf, False)):
        for ad, kod in grup.items():
            d = Path(tempfile.mkdtemp(prefix="aib_mut_"))
            try:
                (d / "scripts").mkdir(); (d / ".github/workflows").mkdir(parents=True)
                (d / "scripts" / f"m_{ad}.py").write_text(kod)
                KOK = d
                n = len(sonuc)
                with open("/dev/null", "w") as dn:
                    o = sys.stdout; sys.stdout = dn
                    try:
                        statik()
                    finally:
                        sys.stdout = o
                fail = not all(sonuc[n:])
                del sonuc[n:]
                (yakalanan if fail == beklenen else kacan).append(ad)
            finally:
                KOK = eski
                shutil.rmtree(d, ignore_errors=True)
    k(f"C/D mutasyon: {len(ornekler)} kacis bicimi yakalaniyor, {len(muaf)} gecerli bicim muaf (yanlis sonuc: {kacan})", not kacan)


def cikis():
    """Surec cikisi olculur (inceleme madde 5): betik BeyanYok'u yakalayip sys.exit(0) ile bitse de cikis kodu 1, ::error:: satiri basilir."""
    kod = ("import sys; sys.path.insert(0, %r); import etsy_common as E\n"
           "try:\n    E.ai_beyan_kapisi('PATCH', '/shops/1/listings/77', data={'description': 'x'})\nexcept E.BeyanYok:\n    pass\n"
           "print('bitti'); sys.exit(0)\n") % str(HERE)
    p = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, timeout=60)
    k("F8 BeyanYok yakalanip sys.exit(0) ile bitse de surec cikisi 1, hata satirinda ilan id, stdout tamponu yazildi",
      p.returncode == 1 and "::error::" in p.stderr and "77" in p.stderr and "bitti" in p.stdout, f"rc {p.returncode}")


def kacis():
    d1 = "x\n\n" + BEYAN
    k("F1 yol sorgu dizesindeki beyansiz description FAIL (data bos ya da beyanli olsa da)",
      not gecer("PATCH", "/shops/1/listings/2?description=beyansiz", data={})
      and not gecer("PATCH", "/shops/1/listings/2?description=beyansiz", data={"description": d1}))
    k("F2 rus / zh-hant ceviri yollari kapsamda (tanimsiz dil FAIL)",
      not gecer("PUT", "/shops/1/listings/2/translations/rus", data={"description": d1})
      and not gecer("PUT", "/shops/1/listings/2/translations/zh-hant", data={"description": d1}))
    k("F3 tekrarli description (tuple listesi / liste deger) beyansiz biri varsa FAIL",
      not gecer("PATCH", "/shops/1/listings/2", data=[("description", "beyansiz"), ("description", d1)])
      and not gecer("PATCH", "/shops/1/listings/2", data={"description": ["beyansiz", d1]}))
    k("F4 JSON dizesi govde okunur (beyansiz FAIL, beyanli gecer)",
      not gecer("PATCH", "/shops/1/listings/2", data=json.dumps({"description": "beyansiz"}))
      and gecer("PATCH", "/shops/1/listings/2", data=json.dumps({"description": d1})))
    k("F5 description None (requests gondermez) kismi yazim gibi gecer", gecer("PATCH", "/shops/1/listings/2", data={"description": None, "title": "t"}))
    k("F6 generator govde okunamaz -> FAIL (guvenli taraf)", not gecer("PATCH", "/shops/1/listings/2", data=(x for x in [("description", d1)])))
    k("F7 form dizesi (bytes) beyansiz FAIL", not gecer("PATCH", "/shops/1/listings/2", data=b"title=t&description=beyansiz"))


def eski_kaynak():
    sys.path.insert(0, str(HERE))
    from kupa_en_ornek import en as kupa_en
    k("E1 eski kupa EN metni (beyan=False) kapida FAIL", not gecer("PATCH", "/shops/1/listings/1", data={"description": kupa_en("Cancer", "Libra", beyan=False)}))
    k("E2 guncel kupa EN metni (beyanli) kapidan gecer", gecer("PATCH", "/shops/1/listings/1", data={"description": kupa_en("Cancer", "Libra")}))
    ham = json.loads((KOK / "scripts/kapak78/test_veri/HAM_4595350971.json").read_text(encoding="utf-8"))
    yd_eski = (ham.get("listing") or {}).get("description") or ""
    beyansiz = yd_eski.replace(BEYAN, "Every design is reviewed and finished by us.")
    k(f"E3 YD canli HAM aciklamasi (pilot 4595350971, {len(yd_eski)} kr., beyanli) kapidan gecer; beyan cumlesi cikarilmis hali FAIL",
      len(yd_eski) > 500 and BEYAN in yd_eski and gecer("PATCH", "/shops/1/listings/4595350971", data={"description": yd_eski})
      and not gecer("PATCH", "/shops/1/listings/4595350971", data={"description": beyansiz}))
    k("E4 RU eski metin (beyansiz) kapida FAIL", not gecer("PUT", "/shops/1/listings/1/translations/ru", data={"description": "Старый текст без пометки."}))


class SahteSunucu:
    """requests.request / requests.patch seviyesinde sahte Etsy (gercek Etsy._call yolu calisir). Taslak PATCH'te active olur (7 Eyl)."""
    def __init__(self):
        self.L, self.T, self.istek = {}, {}, []

    def __call__(self, method, url, params=None, data=None, json=None, headers=None, timeout=None):
        import urllib.parse as up
        yol = up.urlparse(url).path.split("/v3/application", 1)[-1]
        self.istek.append((method, yol, dict(data or {}) if isinstance(data, dict) else data))
        m = re.fullmatch(r"(?:/shops/\d+)?/listings/(\d+)", yol); mt = re.fullmatch(r"/shops/\d+/listings/(\d+)/translations/(\w+)", yol)

        class R:
            headers = {"x-remaining-today": "5000"}
            text = ""

            def __init__(s, kod, j):
                s.status_code, s._j = kod, j

            def json(s):
                return s._j
        if mt:
            k_ = (mt.group(1), mt.group(2))
            if method == "GET":
                return R(200, dict(self.T[k_], listing_id=int(k_[0]))) if k_ in self.T else R(404, {})
            self.T[k_] = dict(data); return R(200, dict(data, listing_id=int(k_[0])))
        if m and m.group(1) in self.L:
            L = self.L[m.group(1)]
            if method == "GET":
                return R(200, dict(L))
            L.update(data or {})
            if L["state"] == "draft":
                L["state"] = "active"
            return R(200, dict(L))
        return R(404, {})


def canli_api(sunucu):
    import requests
    api = E.Etsy(type("S", (), {"access_token": "x", "api_key_header": "k"})())
    api.pace = 0
    return api


def yayin_ve_geri():
    """Karar 1 / 2 / 4: gercek Etsy._call + sahte sunucu (requests.request yamali). Etsy YOK."""
    import os
    import tempfile
    import requests
    sv = SahteSunucu(); gercek = requests.request
    requests.request = sv
    t = Path(tempfile.mkdtemp(prefix="aib_ru_")) / "RU_BEYANSIZ.csv"
    eski_env = {x: os.environ.get(x) for x in ("RU_BEYANSIZ_CSV", "RU_BEYANSIZ_DRIVE")}
    os.environ.update(RU_BEYANSIZ_CSV=str(t), RU_BEYANSIZ_DRIVE="0")   # satir aninda yazilir (inceleme madde 12)
    d1 = "Text.\n\n" + BEYAN
    try:
        def dene(fn):
            try:
                fn(); return "gecti"
            except E.BeyanYok:
                return "kapi"
            except SystemExit as e:
                return "DUR:" + str(e)[:60]
            finally:
                E.BEYAN_HATA.clear()

        def yaz_sayi(lid):
            return [x for x in sv.istek if x[0] in ("PATCH", "PUT") and x[1].endswith(lid)]
        sv.L.update({"101": dict(listing_id=101, state="draft", description="Old text without disclosure.", title="Aries and Leo mug"),
                     "102": dict(listing_id=102, state="draft", description=d1, title="t"),
                     "103": dict(listing_id=103, state="active", description="Old text without disclosure.", title="t"),
                     "104": dict(listing_id=104, state="draft", description="Old text without disclosure.", title="t"),
                     "105": dict(listing_id=105, state="inactive", description="Old text without disclosure.", title="t")})
        api = canli_api(sv)
        g = dene(lambda: api.patch("/shops/1/listings/101", {"state": "active"}))
        k("G1 karar 1: beyansiz TASLAK state=active -> kapi, PATCH gonderilmedi, 1 canli GET",
          g == "kapi" and not yaz_sayi("101") and api.yayin_okuma == 1 and sv.L["101"]["state"] == "draft", f"{g} okuma {api.yayin_okuma}")
        api = canli_api(sv)
        g = dene(lambda: api.patch("/shops/1/listings/102", {"state": "active"}))
        k("G2 beyanli taslak state=active -> yazildi (1 GET + 1 PATCH)", g == "gecti" and len(yaz_sayi("102")) == 1 and api.yayin_okuma == 1, g)
        api = canli_api(sv)
        g = dene(lambda: api.patch("/shops/1/listings/103", {"tags": "a,b"}))
        k("G3 active ilan, beyansiz, yalniz etiket -> yazildi (yayina alma yok)", g == "gecti" and len(yaz_sayi("103")) == 1, g)
        api = canli_api(sv); sv.istek.clear()
        g = dene(lambda: (api.get("/listings/104"), api.patch("/shops/1/listings/104", {"title": "x"})))
        k("G4 bu kosuda okunmus taslak da TAZE okunur (inceleme madde 6: bellek bayatlar), beyansiz -> kapi, PATCH yok",
          g == "kapi" and api.yayin_okuma == 1 and [x[0] for x in sv.istek] == ["GET", "GET"], f"{g} {sv.istek}")
        api = canli_api(sv); sv.istek.clear()
        g = dene(lambda: api.patch("/shops/1/listings/104", {"state": "inactive"}))
        k("G5 acikca state=inactive (yayina almaz) -> okuma yok, yazildi", g == "gecti" and api.yayin_okuma == 0, g)
        sv.L["104"]["state"] = "draft"
        api = canli_api(sv); sv.istek.clear()
        g = dene(lambda: api.patch("/shops/1/listings/104", {"description": d1}))
        k("G6 aciklamali yazim (beyanli) -> yayin okumasi yok, ana kapi gecer", g == "gecti" and api.yayin_okuma == 0, g)
        # karar 2
        eski = "Old text without disclosure."
        api = canli_api(sv); sv.istek.clear()
        g0 = dene(lambda: api.patch("/shops/1/listings/103", {"description": eski}))
        g1 = dene(lambda: E.geri_alma_izni(103, eski, E.ozet("baska metin")))
        g2 = dene(lambda: (E.geri_alma_izni(103, eski, E.ozet(eski)), api.patch("/shops/1/listings/103", {"description": eski})))
        g3 = dene(lambda: api.patch("/shops/1/listings/103", {"description": eski + " degisik"}))
        g4 = dene(lambda: api.patch("/shops/1/listings/999103", {"description": eski}))
        k(f"G7 karar 2: beyansiz eski metne donus izinsiz kapi ({g0}); yanlis sha DUR ({g1[:30]}); yedek sha ile birebir gecti ({g2}); "
          f"baska metin kapi ({g3}); baska ilan kapi ({g4})",
          g0 == "kapi" and "geri alma izni" in g1 and g2 == "gecti" and g3 == "kapi" and g4 == "kapi"
          and E.GERI_ISTISNA and E.GERI_ISTISNA[-1][0] == "103")
        api = canli_api(sv); sv.istek.clear()
        g = dene(lambda: api.patch("/shops/1/listings/105", {"tags": "a"}))
        k("G8 karar 1 kapsam: inactive ilanda state'siz kismi yazim yayina almaz -> 1 durum okumasi, beyansiz da gecer (yalniz taslak / state=active)",
          g == "gecti" and api.yayin_okuma == 1 and [x[0] for x in sv.istek] == ["GET", "PATCH"], f"{g} {sv.istek}")
        g = dene(lambda: api.patch("/shops/1/listings/105", {"state": "active"}))
        k("G8b inactive ilana state=active (yayina alma) beyansiz -> kapi", g == "kapi" and sv.L["105"]["state"] == "inactive", g)
        sv.L["106"] = dict(listing_id=106, state="draft", description=eski, title="t")
        E.geri_alma_izni(106, eski, E.ozet(eski))
        g = dene(lambda: api.patch("/shops/1/listings/106", {"state": "active"}))
        k("G8c karar 2 izni yayina almayi ACMAZ (inceleme madde 5): izinli beyansiz taslak + state=active -> kapi",
          g == "kapi" and sv.L["106"]["state"] == "draft", g)
        # karar 4 (yd78 ilani: poster listesinde degil, cift tablodan)
        lid = "4595373190"
        sv.L[lid] = dict(listing_id=int(lid), state="active", description=d1, title="t")
        sv.T[(lid, "ru")] = dict(title="Старое", description="Старый текст без пометки.", tags="a")
        E.RU_BEYANSIZ.clear()
        api = canli_api(sv); sv.istek.clear()
        g = dene(lambda: api.put(f"/shops/1/listings/{lid}/translations/ru", {"title": "Новое", "description": "Старый текст без пометки.", "tags": "a"}))
        k("G9 karar 4: RU aciklamasi degismeyen yazim (yalniz baslik), eski RU beyansiz -> yazildi, 1 GET, RU_BEYANSIZ satiri (cift tablodan)",
          g == "gecti" and sv.T[(lid, "ru")]["title"] == "Новое" and api.yayin_okuma == 1 and E.RU_BEYANSIZ
          and E.RU_BEYANSIZ[-1]["listing_id"] == lid and E.RU_BEYANSIZ[-1]["cift"] == "AQUARIUS_AQUARIUS", f"{g} {E.RU_BEYANSIZ[-1:]}")
        n0 = api.yayin_okuma
        g = dene(lambda: api.put(f"/shops/1/listings/{lid}/translations/ru", {"title": "Новое 2", "description": "Старый текст без пометки.", "tags": "a"}))
        k("G10 ayni kosuda ikinci yazim: canli RU yine taze okunur (+1 GET)", g == "gecti" and api.yayin_okuma == n0 + 1, f"{g} {api.yayin_okuma - n0}")
        g = dene(lambda: api.put(f"/shops/1/listings/{lid}/translations/ru", {"title": "x", "description": "Новый текст без пометки.", "tags": "a"}))
        k("G11 aciklamaya DOKUNAN beyansiz RU yazimi -> kapi (kural aynen)", g == "kapi" and sv.T[(lid, "ru")]["description"] == "Старый текст без пометки.", g)
        lid2 = "4595350971"
        sv.L[lid2] = dict(listing_id=int(lid2), state="active", description=d1, title="t")
        g = dene(lambda: api.put(f"/shops/1/listings/{lid2}/translations/ru", {"title": "x", "description": "Старый текст.", "tags": "a"}))
        k("G12 canli RU ceviri yok (404) -> kapi", g == "kapi", g)
        satir = t.read_text().splitlines()       # _ru_beyansiz_yaz cagrilmadan: olay aninda yazilmis olmali
        k(f"G13 RU_BEYANSIZ CSV olay aninda (cikis beklenmeden): listing_id, cift, tarih; ilan basina tek satir ({len(satir) - 1})", satir[0].startswith("listing_id,cift,dil,tarih")
          and len(satir) == 2 and lid in satir[1] and "AQUARIUS_AQUARIUS" in satir[1], satir[:2])
        k("G15 cift_bul: tablodan; baslikta iki burc -> alfabetik; tek gecen / 3 burc -> ? (uydurulmaz)",
          E.cift_bul("4595373190") == "AQUARIUS_AQUARIUS" and E.cift_bul("1", "Libra and Cancer mug") == "CANCER_LIBRA"
          and E.cift_bul("1", "Leo and Leo mug") == "LEO_LEO" and E.cift_bul("1", "Leo mug") == "?" and E.cift_bul("1", "Leo Aries Virgo") == "?")
        kod = ("import sys, os; sys.path.insert(0, %r); import etsy_common as E\n"
               "E.RU_BEYANSIZ.append(dict(listing_id='1', dil='ru', cift='?', tarih='2026-11-01', neden='x'))\n") % str(HERE)
        pr = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, timeout=60,
                            env=dict(os.environ, RU_BEYANSIZ_CSV=str(t.parent / "b.csv"), RU_BEYANSIZ_DRIVE="0"))
        k("G14 yalniz RU_BEYANSIZ (beyan hatasi yok) -> surec cikisi 0 (FAIL degil), uyari satiri", pr.returncode == 0 and "RU_BEYANSIZ" in pr.stderr,
          f"rc {pr.returncode}")
    finally:
        requests.request = gercek
        E.BEYAN_HATA.clear(); E.RU_BEYANSIZ.clear(); E.GERI_IZIN.clear(); E.GERI_ISTISNA.clear()
        for x, v in eski_env.items():
            os.environ.pop(x, None) if v is None else os.environ.update({x: v})


ON_KONTROL = {"scripts/etsy/pod_inventory_update.py", "scripts/pod/pod_boy_15.py", "scripts/pod/pod_pilot_15.py", "scripts/etsy/beyan_marka_yaz.py"}
YAZ_ATTR = {"patch", "put", "put_json", "post", "post_json", "post_file", "delete", "_yaz_dogrula"}


def on_kontrol():
    """Karar 3: birim + EN ve RU yazan 4 betikte, kontrolu iceren fonksiyonda kontrolden ONCE hicbir yazim cagrisi yok (AST)."""
    d1, r1 = "x\n\n" + BEYAN, "Текст.\n\n" + RU_BEYAN
    k("H1 beyan_on_kontrol: iki metin beyanli -> bos; RU beyansiz -> neden; EN beyansiz -> neden; RU yazilmiyorsa (None) yalniz EN",
      E.beyan_on_kontrol(d1, r1) == [] and len(E.beyan_on_kontrol(d1, "Текст.")) == 1 and len(E.beyan_on_kontrol("x", r1)) == 1
      and E.beyan_on_kontrol(d1, None) == [] and len(E.beyan_on_kontrol("x", "y")) == 2)
    k("H2 karar 4 ile uyum: RU aciklamasi canli ile ayni (dokunulmuyor) ve beyansiz -> engel degil",
      E.beyan_on_kontrol(d1, "Старый текст.", "Старый  текст.") == [] and len(E.beyan_on_kontrol(d1, "Новый.", "Старый.")) == 1)
    sorun = []
    for rel in sorted(ON_KONTROL):
        t = (KOK / rel).read_text(encoding="utf-8"); agac = ast.parse(t)
        fonks = [n for n in ast.walk(agac) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        cagri = [n for n in ast.walk(agac) if isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) == "beyan_on_kontrol"]
        if not cagri:
            sorun.append(f"{rel}: beyan_on_kontrol yok"); continue
        for c in cagri:
            fn = min([f for f in fonks if f.lineno <= c.lineno <= (f.end_lineno or f.lineno)], key=lambda f: (f.end_lineno or 0) - f.lineno)
            once = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and n.lineno < c.lineno
                    and getattr(n.func, "attr", getattr(n.func, "id", "")) in YAZ_ATTR]
            sonra = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Call) and n.lineno > c.lineno
                     and getattr(n.func, "attr", getattr(n.func, "id", "")) in YAZ_ATTR]
            if once or not sonra:
                sorun.append(f"{rel}:{c.lineno} once {once[:3]} sonra {len(sonra)}")
    k(f"H3 EN + RU yazan {len(ON_KONTROL)} betikte on kontrol, ayni fonksiyonda tum yazimlardan ONCE", not sorun, str(sorun))


def main():
    canli = "--canli" in sys.argv
    birim()
    call_yolu()
    kacis()
    cikis()
    yayin_ve_geri()
    if not canli:
        on_kontrol()
    eski_kaynak()
    if not canli:                      # depo taramasi yalniz CI'da (inceleme madde 6: ilgisiz betik canli yazimi / geri almayi durdurmasin)
        yazanlar = statik()
        mutasyon()
        print(f"aciklama yazan betik sayisi (statik): {len(yazanlar)}")
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
