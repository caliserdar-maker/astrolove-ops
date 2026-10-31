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
Calistir: python3 scripts/etsy/test_ai_beyan.py"""
import json
import re
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
    k("A9 HTML kacisli / satir sonlu beyan da bulunur", gecer("PATCH", "/shops/1/listings/9", data={"description": "a\n\n" + BEYAN.replace(" ", "\n", 2)}))
    # YD: tek gecis PATCH yalniz EN (title + description); RU kapisi YD yolunda yok
    k("A10 YD tek gecis PATCH (title + description, EN) beyanli gecer / beyansiz FAIL",
      gecer("PATCH", "/shops/1/listings/4595350971", data={"title": "T", "description": d1})
      and not gecer("PATCH", "/shops/1/listings/4595350971", data={"title": "T", "description": d0}))
    yd = (KOK / "scripts/kapak78/yd_kapak_yukle.py").read_text(encoding="utf-8")
    k("A11 YD yolunda RU ceviri yazimi yok (translations / ru_yazim_kapisi cagrisi yok)",
      "translations" not in yd and "ru_yazim_kapisi" not in yd)


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
    finally:
        requests.request = gercek
        E.BEYAN_HATA.clear()


DOGRUDAN = re.compile(r"requests\.(post|put|patch|request)\(")


def statik():
    ihlal, kapsam_disi, yazanlar = [], [], []
    for f in sorted((KOK / "scripts").rglob("*.py")):
        rel = str(f.relative_to(KOK))
        if "/test_" in rel or "__pycache__" in rel or rel.endswith("etsy_common.py") or rel.endswith("_selftest.py"):
            continue
        t = f.read_text(encoding="utf-8", errors="replace"); S = t.splitlines()
        etsy = bool(re.search(r"openapi\.etsy\.com|from etsy_common import|import etsy_common", t))
        for i, ln in enumerate(S):
            if DOGRUDAN.search(ln) and etsy and re.search(r"/listings", ln) and not re.search(r"requests\.request\(\s*method", ln):
                # govde satirda literal dict ve description icermiyorsa (or. by78_yayinla state PATCH) aciklama yazmaz: muaf
                lit = re.search(r"data=\{([^}]*)\}", ln)
                if lit and "description" not in lit.group(1):
                    continue
                if "ai_beyan_kapisi(" not in "\n".join(S[max(0, i - 8):i]) and "ai_beyan_kapisi(" not in "\n".join(S[max(0, i - 20):i]):
                    ihlal.append(f"{rel}:{i + 1}")
        yazar = any(re.search(r"\.(patch|put|put_json|post|post_json|_call)\(", ln)
                    and re.search(r"[\"']description[\"']|translations", "\n".join(S[max(0, i - 6):i + 6])) for i, ln in enumerate(S))
        if yazar and etsy:
            yazanlar.append(rel)
            if not re.search(r"from etsy_common import|import etsy_common", t):
                kapsam_disi.append(rel)
    k(f"C dogrudan requests ile Etsy'ye aciklama yazan cagrilarin hepsi ai_beyan_kapisi'ndan geciyor ({len(ihlal)} ihlal)", not ihlal, str(ihlal[:5]))
    k(f"D aciklama yazan {len(yazanlar)} betigin hepsi etsy_common kullaniyor (kapi _call'da)", yazanlar and not kapsam_disi, str(kapsam_disi[:5]))
    return yazanlar


def eski_kaynak():
    sys.path.insert(0, str(HERE))
    from kupa_en_ornek import en as kupa_en
    k("E1 eski kupa EN metni (beyan=False) kapida FAIL", not gecer("PATCH", "/shops/1/listings/1", data={"description": kupa_en("Cancer", "Libra", beyan=False)}))
    k("E2 guncel kupa EN metni (beyanli) kapidan gecer", gecer("PATCH", "/shops/1/listings/1", data={"description": kupa_en("Cancer", "Libra")}))
    ham = json.loads((KOK / "scripts/kapak78/test_veri/HAM_4595350971.json").read_text(encoding="utf-8"))
    yd_eski = (ham.get("listing") or {}).get("description") or ""
    k(f"E3 YD canli HAM aciklamasi (pilot, {len(yd_eski)} kr.): beyan {'VAR' if E.beyan_var(yd_eski, 'en') else 'YOK'} -> kapi kararla tutarli",
      gecer("PATCH", "/shops/1/listings/4595350971", data={"description": yd_eski}) == E.beyan_var(yd_eski, "en"))
    k("E4 RU eski metin (beyansiz) kapida FAIL", not gecer("PUT", "/shops/1/listings/1/translations/ru", data={"description": "Старый текст без пометки."}))


def main():
    birim()
    call_yolu()
    yazanlar = statik()
    eski_kaynak()
    print(f"aciklama yazan betik sayisi (statik): {len(yazanlar)}")
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
