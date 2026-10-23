#!/usr/bin/env python3
"""Merkezi RU yazim kapisi testleri (Serdar 23 Eki madde 4): eski poster RU hicbir betikten yazilamaz. Ag yok (requests sahte)."""
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
import etsy_common as E  # noqa: E402
import ru_poster as P  # noqa: E402


class Yanit:
    status_code, headers, text = 200, {"x-remaining-today": "4000"}, ""

    def json(self):
        return {"ok": 1}


giden = []
E.requests.request = lambda m, url, **k: giden.append((m, url)) or Yanit()
E.time.sleep = lambda s: None


class Depo:
    api_key_header, access_token = "x", "y"


def dene(f):
    n = len(giden)
    try:
        f()
        return "gitti" if len(giden) > n else "?"
    except SystemExit as e:
        return "durdu" if len(giden) == n else f"durdu ama istek gitti {e}"


def main():
    api = E.Etsy(Depo())
    POSTER, KUPA = "4570110121", "4598517993"
    ESKI = "Печатаем на хлопковой бумаге Hahnemühle Photo Rag 308 г/м²."
    YENI = "Именной постер для пары. Печать на премиальной матовой художественной бумаге."
    KUPA_RU = "Именная кружка для пары. Оригинальные символы от AstroLoveArt. 11 oz (325 мл)."
    s = []
    s.append(("poster: eski RU (yasak ifade) PUT gonderilmez", dene(lambda: api.put(f"/shops/1/listings/{POSTER}/translations/ru",
              {"title": "t", "description": ESKI, "tags": "a"})) == "durdu"))
    s.append(("poster: yasaksiz ama ru_poster izni yok -> gonderilmez", dene(lambda: api.put(
        f"/shops/1/listings/{POSTER}/translations/ru", {"title": "t", "description": YENI})) == "durdu"))
    s.append(("poster: pod_ru_tags gibi yalniz etiket (aciklama aynen) -> gonderilmez", dene(lambda: api.put(
        f"/shops/1/listings/{POSTER}/translations/ru", {"title": "t", "description": YENI, "tags": "x,y"})) == "durdu"))
    s.append(("poster: PASS olmayan kontrolle izin_ver -> DUR", dene(lambda: P.izin_ver(POSTER, YENI, {"pass_": False})) == "durdu"))
    P.izin_ver(POSTER, YENI, {"pass_": True, "sorunlar": ""})
    s.append(("poster: ru_poster izinli metin birebir -> gider", dene(lambda: api.put(
        f"/shops/1/listings/{POSTER}/translations/ru", {"title": "t", "description": YENI})) == "gitti"))
    s.append(("poster: izinli metinden tek harf farkli -> gonderilmez", dene(lambda: api.put(
        f"/shops/1/listings/{POSTER}/translations/ru", {"title": "t", "description": YENI + " "})) == "durdu"))
    s.append(("poster: json govde (put_json) de kapida", dene(lambda: api.put_json(
        f"/shops/1/listings/{POSTER}/translations/ru", {"description": ESKI})) == "durdu"))
    s.append(("kupa: temiz RU -> gider (davranis degismez)", dene(lambda: api.put(
        f"/shops/1/listings/{KUPA}/translations/ru", {"title": "t", "description": KUPA_RU})) == "gitti"))
    s.append(("kupa: Art'siz AstroLove -> gonderilmez", dene(lambda: api.put(
        f"/shops/1/listings/{KUPA}/translations/ru", {"description": "дизайн AstroLove"})) == "durdu"))
    s.append(("GET ve EN PATCH kapidan etkilenmez", dene(lambda: api.get(f"/shops/1/listings/{POSTER}/translations/ru")) == "gitti"
              and dene(lambda: api.patch(f"/shops/1/listings/{POSTER}", {"description": "x"})) == "gitti"))
    s.append(("poster listesi 78 ilan", len(E.poster_idler()) == 78 and POSTER in E.poster_idler()))
    s.append(("yasak desen: omur yili araligi var, 25 лет/11 букв yok", bool(E.RU_YASAK.search("100-200 years"))
              and bool(E.RU_YASAK.search("более 100 лет")) and not E.RU_YASAK.search("25 лет вместе, до 11 букв")))
    for b, arg in (("scripts/pod/metin_78.py", ["--out", "/tmp/x"]), ("scripts/pod/yayilim_78.py", ["yaz", "--csv", "x"]),
                   ("scripts/pod/yayilim_78.py", ["metin2", "--csv", "x"]),
                   ("scripts/etsy/pod_ru_tags.py", ["--state", "x", "--out", "/tmp/x", "--apply"])):
        r = subprocess.run([sys.executable, str(KOK.parents[1] / b)] + arg, capture_output=True, text=True, timeout=60)
        s.append((f"{b} {arg[0] if 'yayilim' in b else arg[-1]} KAPALI", r.returncode != 0 and "KAPALI" in (r.stdout + r.stderr)))
    for ad, ok in s:
        print("PASS" if ok else "FAIL", ad)
    n = sum(ok for _, ok in s)
    print(f"ru kapisi testleri: {n}/{len(s)} PASS")
    sys.exit(0 if n == len(s) else 1)


if __name__ == "__main__":
    main()
