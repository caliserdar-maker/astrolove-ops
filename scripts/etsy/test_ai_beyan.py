#!/usr/bin/env python3
"""AI beyan kapisi KALICI testleri (Merkez / Serdar 31 Eki, Gorev E). ETSY YOK, ag yok.
Etsy kurali: "Sellers must disclose within their listing description if an item is created with the use of AI." Kapi tek yerde:
etsy_common.Etsy._call -> ai_beyan_kapisi (aciklama yazan her istek). Bu test:
  A  kapi birimi: EN updateListing (PATCH / PUT), createDraftListing (POST data / json), ceviri PUT (RU), kismi yazim (aciklamasiz) gecer,
     celisen govde / tanimsiz dil / beyansiz metin FAIL; YD yolu yalniz EN yazar (RU kapisi YD'de yok; yd_kapak_yukle tek gecis PATCH'i).
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
    cagri = [n for n in ast.walk(agac) if isinstance(n, ast.Call) and isinstance(n.func, (ast.Attribute, ast.Name))
             and getattr(n.func, "attr", getattr(n.func, "id", "")) == "ru_yazim_kapisi"]
    dize = [n for n in ast.walk(agac) if isinstance(n, ast.Constant) and isinstance(n.value, str) and "/translations" in n.value]
    k("A11 YD yolunda RU ceviri yazimi yok (kodda /translations dizesi ve ru_yazim_kapisi cagrisi yok; yorumlar sayilmaz)", not cagri and not dize)


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
            if _aciklamasiz_literal(c) and c.func.attr != "request":
                continue
            ic = [fn for fn in fonks if fn.lineno <= c.lineno <= (fn.end_lineno or fn.lineno)]
            kapsam = min(ic, key=lambda fn: (fn.end_lineno or 0) - fn.lineno) if ic else agac
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
        "baska_fonk_kapi": 'import requests\nfrom etsy_common import ai_beyan_kapisi\nAPI="https://openapi.etsy.com/v3"\ndef g(d):\n    ai_beyan_kapisi("PATCH", "/shops/1/listings/2", data={"description": d})\ndef f(d):\n    requests.patch(API + "/shops/1/listings/2", data={"description": d})\n',
    }
    muaf = {
        "state_literal": 'import requests\nAPI="https://openapi.etsy.com/v3"\ndef f():\n    requests.patch(API + "/shops/1/listings/2", data={"state": "active"})\nK = "description"\n',
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


def main():
    canli = "--canli" in sys.argv
    birim()
    call_yolu()
    kacis()
    cikis()
    eski_kaynak()
    if not canli:                      # depo taramasi yalniz CI'da (inceleme madde 6: ilgisiz betik canli yazimi / geri almayi durdurmasin)
        yazanlar = statik()
        mutasyon()
        print(f"aciklama yazan betik sayisi (statik): {len(yazanlar)}")
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
