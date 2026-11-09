#!/usr/bin/env python3
"""kolye_pazar sahte testi (Etsy'ye istek YOK: etsy_common.requests.request ve CDN indirme taklit; sahte Etsy emsal
ornament_pazar_selftest.Sahte). Bilinen PASS: 6 ifade, tekillestirme, butce, rapor alanlari, log ozeti. Bilinen FAIL: butce asimi,
kota ALT alti, GET disi istek (SaltOkur SystemExit), SaltOkur olmayan istemci."""
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import etsy_common as E  # noqa: E402
import kolye_pazar as KP  # noqa: E402
import ornament_pazar as OP  # noqa: E402
import ornament_pazar_selftest as ST  # noqa: E402


def _ag_yok(*a, **k):
    raise AssertionError("gercek ag cagrisi (requests.post / get)")


def kur(s):
    E.requests.request = s
    E.requests.post = E.requests.get = _ag_yok       # Etsy.post_file vb. gercek aga gidemez
    E.time.sleep = lambda *_: None
    api = KP.SaltOkur(E.APIKeyStore("anahtar", "sir"))
    api.pace = 0
    return api


def dur(f, *a, **k):
    try:
        f(*a, **k)
    except SystemExit as e:
        return str(e.code if e.code is not None else e)
    return None


def kos(s, d):
    log = io.StringIO()
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        kod = KP.calis(Path(d), kur(s), indir=ST.resim)
    return kod, log.getvalue()


ORN_IFADELER, ORN_RAPOR = list(OP.IFADELER), OP.rapor_taslak


KOK = Path(__file__).resolve().parents[2]
WF = KOK / ".github/workflows/kolye-arastirma.yml"


def adim(ad):
    """Is akisindan adimin run: | govdesi (girinti kaldirilmis)."""
    sat = WF.read_text(encoding="utf-8").splitlines()
    i = next(k for k, x in enumerate(sat) if x.strip() == f"- name: {ad}")
    j = next(k for k in range(i + 1, len(sat)) if sat[k].strip() == "run: |")
    g = len(sat[j]) - len(sat[j].lstrip())
    govde = []
    for x in sat[j + 1:]:
        if x.strip() and len(x) - len(x.lstrip()) <= g:
            break
        govde.append(x[g + 2:])
    return "\n".join(govde).replace("${{ github.run_id }}", "123") + "\n"


def is_akisi_kos(sahte_cikti, ek_dosya=None):
    """Oku + Drive'a yaz adimlarini sahte python (kolye_pazar yerine) ve sahte rclone ile kosar (bash -e, GitHub gibi)."""
    d = Path(tempfile.mkdtemp(prefix="kolye_wf_"))
    (d / "scripts").symlink_to(KOK / "scripts")
    b = d / "_bin"
    b.mkdir()
    (b / "python").write_text("#!/bin/bash\ncat \"$SAHTE\"\nmkdir -p out && echo '{}' > out/OZET.json\nexit 0\n")
    (b / "rclone").write_text("#!/bin/bash\nmkdir -p \"$DRIVE\" && cp -r \"$2\" \"$DRIVE/kopya\"\n")
    for f in b.iterdir():
        f.chmod(f.stat().st_mode | stat.S_IEXEC)
    (d / "sahte.txt").write_text(sahte_cikti)
    env = dict(os.environ, PATH=f"{b}:{os.environ['PATH']}", SAHTE=str(d / "sahte.txt"), DRIVE=str(d / "_drive"),
               GITHUB_ENV=str(d / "_env"))
    env.pop("RUNNER_TEMP", None)
    r1 = subprocess.run(["bash", "-e", "-c", adim("Oku (salt okur)")], cwd=d, env=env, capture_output=True, text=True)
    if ek_dosya:
        (d / "out" / ek_dosya[0]).write_text(ek_dosya[1])
    kod = dict(x.split("=", 1) for x in (d / "_env").read_text().split() if "=" in x).get("KOD") if (d / "_env").exists() else None
    r2 = subprocess.run(["bash", "-e", "-c", adim("Drive'a yaz")], cwd=d, env=dict(env, KOD=str(kod)), capture_output=True, text=True)
    yerel = (d / "out" / "KOSU_LOG.txt").read_text() if (d / "out" / "KOSU_LOG.txt").exists() else None
    drive = "".join(p.read_text(errors="ignore") for p in (d / "_drive").rglob("*") if p.is_file()) if (d / "_drive").exists() else None
    shutil.rmtree(d, ignore_errors=True)
    return r1, r2, kod, yerel, drive


def testler():  # noqa: C901
    t = []
    # S sir koruma (is akisi adimlari, sahte python + sahte rclone)
    r1, r2, kod, yerel, drive = is_akisi_kos("::add-mask::ORNEKDEGER123\nnormal satir\n")
    t.append(("PASS: add-mask satiri stdout'a aynen (runner maskeler)", "::add-mask::ORNEKDEGER123" in r1.stdout and r1.returncode == 0))
    t.append(("FAIL: ::add-mask::ORNEKDEGER123 KOSU_LOG.txt'ye ve Drive kopyasina girmez", yerel is not None and drive is not None
              and "normal satir" in yerel and "normal satir" in drive and "ORNEKDEGER123" not in yerel + drive
              and "::add-mask::" not in yerel + drive and kod == "0" and r2.returncode == 0))
    r1, r2, kod, yerel, drive = is_akisi_kos("::add-mask::ORNEKDEGER123\nsizinti ORNEKDEGER123 burada\n")
    t.append(("FAIL: sir degeri iceren satir engellenir, KOD 97 (is kirmizi), deger dosyada / Drive'da yok", kod == "97"
              and yerel is not None and "SIR ICEREN SATIR ENGELLENDI" in yerel and "ORNEKDEGER123" not in yerel + (drive or "")))
    r1, r2, kod, yerel, drive = is_akisi_kos("normal\n", ek_dosya=("OZET.json", "::add-mask::ORNEKDEGER123\n"))
    t.append(("FAIL: OZET.json'da sir izi -> sir_koru tara FAIL, Drive'a yazilmaz", r2.returncode != 0 and drive is None and "Drive'a yazilmadi" in r2.stdout))
    r1, r2, kod, yerel, drive = is_akisi_kos("normal\n", ek_dosya=("ILANLAR.csv", "listing_id,baslik\n9000000001,Ring Bearer Necklace Zodiac\n"))
    t.append(("PASS: 'Ring Bearer Necklace' basligi kosuyu durdurmaz (CSV taranmaz), Drive'a yazilir", r2.returncode == 0 and kod == "0"
              and drive is not None and "Ring Bearer Necklace Zodiac" in drive))
    wf = WF.read_text(encoding="utf-8").split("\n  printify:")[0]
    t.append(("PASS: pazar logu yalniz sir_koru tee ile, tara Drive kopyasindan once", "| tee " not in wf and "sir_koru.py tee out/KOSU_LOG.txt" in wf
              and wf.index("sir_koru.py tara out/KOSU_LOG.txt out/OZET.json") < wf.index('rclone copy out "$H"')))
    # K kimlik suzgeci
    for g, b in (("HATA: GET /listings/9000000001/reviews -> 403: x", "HATA: GET /listings/<id>/reviews -> 403: x"),
                 ("/shops/12345678 -> 500", "/shops/<id> -> 500"),
                 ("url ?listing_ids=9000000004%2C9000000005,9000000006&includes=Shop", "url ?listing_ids=<id>&includes=Shop"),
                 ("ilan 9000000002 atlandi", "ilan <id> atlandi"),
                 ("kota 4920 -> 4870 | istek 52 | fiyat 16.75", "kota 4920 -> 4870 | istek 52 | fiyat 16.75"),
                 ('{"error":"Listing 9000000002."}', '{"error":"Listing <id>."}'), ("listing 9000000002.", "listing <id>."),
                 ("shop_id 12345678 is invalid", "shop_id <id> is invalid"), ('"shop_id": 87654321,', '"shop_id": <id>,'),
                 ("listing_id=9000000002&x", "listing_id=<id>&x"), ("fiyat 9000000007.5", "fiyat 9000000007.5"),
                 ("::add-mask::9000000001 /listings/9000000001", "::add-mask::9000000001 /listings/9000000001")):
        t.append((f"PASS: kimlik suzgeci {g[:40]!r}", KP.kimlik_suz(g) == b))
    tam = io.StringIO()
    ak = KP.KimlikSuz(tam)
    ak.write("a /listings/12"); ak.write("34567890/x\nb 9000000003"); ak.flush()
    t.append(("PASS: KimlikSuz yarim satiri birlestirip suzer", tam.getvalue() == "a /listings/<id>/x\nb <id>"))
    kod_m = ("import sys; sys.path.insert(0, 'scripts/etsy'); import kolye_pazar as KP\n"
             "def c(out, api, indir=None):\n    print('HATA: GET /listings/9000000001/reviews -> 403')\n"
             "    raise RuntimeError('baglanti /shops/87654321 listing_ids=9000000004,9000000005')\n"
             "KP.calis = c; sys.argv = ['x', '--out', 'o']; KP.main()\n")
    kod_s = kod_m.replace("raise RuntimeError(", "raise SystemExit(")
    rs = subprocess.run([sys.executable, "-c", kod_s], cwd=KOK, capture_output=True, text=True,
                        env=dict(os.environ, ETSY_API_KEY="SAHTEANAHTAR99", ETSY_SHARED_SECRET="SAHTESIR99"))
    t.append(("FAIL: SystemExit mesajinda da kimlik yok", rs.returncode != 0 and "/shops/<id>" in rs.stderr
              and not re.search(r"87654321|9000000004", rs.stdout + rs.stderr)))
    r = subprocess.run([sys.executable, "-c", kod_m], cwd=KOK, capture_output=True, text=True,
                       env=dict(os.environ, ETSY_API_KEY="SAHTEANAHTAR99", ETSY_SHARED_SECRET="SAHTESIR99"))
    hep = r.stdout + r.stderr
    t.append(("FAIL: main() stdout + traceback'te rakip kimligi yok (KimlikSuz bagli)", r.returncode != 0 and "Traceback" in hep
              and "/listings/<id>/reviews" in hep and "/shops/<id>" in hep and "listing_ids=<id>" in hep
              and not re.search(r"9000000001|87654321|9000000004", hep) and "::add-mask::SAHTEANAHTAR99" in hep))
    # A normal
    s = ST.Sahte()
    with tempfile.TemporaryDirectory() as d:
        kod, log = kos(s, d)
        out = Path(d)
        oz = json.loads((out / "OZET.json").read_text())
        tum, ilk = ST.oku(out / "ILANLAR.csv"), ST.oku(out / "ILK20.csv")
        md = (out / "RAPOR_TASLAK.md").read_text()
        aramalar = [p["keywords"] for y, p in s.log if y == "/listings/active"]
        t.append(("PASS: kod 0", kod == 0))
        t.append(("PASS: 6 ifade, bu sirayla", aramalar == KP.IFADELER and len(KP.IFADELER) == 6
                  and KP.IFADELER[0] == "zodiac necklace" and KP.IFADELER[-1] == "constellation necklace"))
        t.append(("PASS: tekillestirme 350", len(tum) == 350 and len({r["listing_id"] for r in tum}) == 350 and oz["tekil_ilan"] == 350))
        t.append(("PASS: istek <= BUTCE 80 ve sayac = gercek", len(s.log) <= 80 and oz["etsy_istek"] == len(s.log) and OP.BUTCE == 80
                  and OP.ALT == 500))
        t.append(("PASS: dosyalar", all((out / f).exists() for f in ("ILANLAR.csv", "ILK20.csv", "OZET.json", "TEMAS.jpg", "RAPOR_TASLAK.md"))))
        t.append(("PASS: rapor basligi kolye, ornament basligi yok", md.startswith("# Kolye rakip orneklemi") and "Ornament pazar" not in md))
        t.append(("PASS: rapor uyarisi (talep degil, en cok satan yok, magaza toplami)", "TALEP olcumu degildir" in md
                  and "'En cok satan' iddiasi yoktur" in md and "magaza toplami" in md))
        t.append(("PASS: ifade tablosu 6 satir + eslesen sayisi", all(f"| {q} | {1234 + i} | 100 |" in md for i, q in enumerate(KP.IFADELER))))
        t.append(("PASS: fiyat dagilimi para birimine gore", re.search(r"- fiyat USD: n 350: en dusuk 15 \| c1 \S+ \| ortanca \S+ \| c3 \S+ \| "
                                                                        r"en yuksek 18\.49", md) is not None))
        t.append(("PASS: favori / yorum / magaza toplami dagilimi", "- favori (num_favorers): n 349" in md
                  and "ilan yorum sayisi (yalniz ilk 20 icin okundu): n 20" in md and "magaza toplami (magazanin TUM satisi" in md))
        t.append(("PASS: kisisellestirme orani", "kisisellestirme: 350/350" in md))
        t.append(("PASS: ilk 20 baslik + fiyat", sum(1 for x in md.splitlines() if re.match(r"\| \d+ \| Ornament \d+ \| \d", x)) == 20 and len(ilk) == 20))
        t.append(("PASS: log ozeti satirlari", "OZET pazar | ifade basi eslesen" in log and "OZET pazar | tekil ilan 350" in log
                  and "OZET pazar | fiyat ortancasi: USD" in log))
        oz_satir = [x for x in log.splitlines() if "OZET pazar" in x]
        t.append(("FAIL: log ozetinde ilan kimligi (1000000-1000349) / magaza kimligi (500-539) / baslik / magaza adi yok",
                  bool(oz_satir) and not any(re.search(r"\b1000[0-3]\d\d\b|\b5[0-3]\d\b|Ornament \d|Shop\d|Dukkan", x) for x in oz_satir)))
        t.append(("PASS: OP.IFADELER ve OP.rapor_taslak calis sonrasi geri alinir (ornament_pazar dosyasi degismez)",
                  OP.IFADELER == ORN_IFADELER and OP.rapor_taslak is ORN_RAPOR and aramalar == KP.IFADELER))
        tekil_m = {r["magaza_id"] for r in tum if r.get("magaza_id") and r.get("magaza_yorum") not in ("", None)}
        t.append(("PASS: magaza yorum dagilimi tekil magazaya gore", 0 < len(tekil_m) < 40
                  and f"magaza yorum sayisi (ilk 40 ilanin tekil magazalari): n {len(tekil_m)}:" in md))
    # dagilim birim
    g = KP.dagilim([5, 1, 3, 2, 4, "", None, "x"])
    t.append(("PASS: dagilim [1..5] (bos / metin sayilmaz)", g == {"n": 5, "en_dusuk": 1, "c1": 2, "ortanca": 3, "c3": 4, "en_yuksek": 5}))
    t.append(("PASS: dagilim bos", KP.dagilim([]) == {"n": 0}))
    # B kota ALT alti -> baslamaz, 1 istek, rapor yok
    for kalan, beklenen in ((580, 2), (581, 0)):
        s = ST.Sahte(kalan=kalan)
        with tempfile.TemporaryDirectory() as d:
            kod, log = kos(s, d)
            if beklenen == 2:
                t.append(("FAIL: kota 579 - 80 < 500 -> BASLAMADI, 1 istek, rapor yok", kod == 2 and len(s.log) == 1
                          and not (Path(d) / "RAPOR_TASLAK.md").exists() and "OZET pazar | tekil ilan None" in log))
            else:
                t.append(("PASS: kota 580 - 80 = 500 -> baslar", kod == 0 and len(s.log) > 1))
    # B2 429 (istisna) -> ozet yine loga
    s = ST.Sahte(yorum_kod=429)
    with tempfile.TemporaryDirectory() as d:
        log = io.StringIO()
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            h = dur(KP.calis, Path(d), kur(s), ST.resim)
        t.append(("FAIL: 429 -> DUR, ozet satirlari ve OZET.json (durum HATA) yine yazili", h is not None and "429" in h
                  and "OZET pazar | tekil ilan" in log.getvalue()
                  and json.loads((Path(d) / "OZET.json").read_text()).get("durum", "").startswith("HATA")))
        t.append(("PASS: istisnadan sonra da OP geri alinir", OP.IFADELER == ORN_IFADELER and OP.rapor_taslak is ORN_RAPOR))
    # C butce asimi
    s = ST.Sahte()
    ok = OP.Okuyucu(kur(s), butce=5)
    h = None
    try:
        for _ in range(10):
            ok.get("/openapi-ping")
    except OP.Butce as e:
        h = str(e)
    t.append(("FAIL: butce asimi -> Butce DUR", h is not None and "butce" in h and len(s.log) <= 5))
    # D GET disi istek -> SystemExit, istek gitmez
    s = ST.Sahte()
    api = kur(s)
    for ad, f in (("POST", lambda: api.post("/shops/1/listings", {"a": 1})), ("PUT", lambda: api.put("/listings/1", {"a": 1})),
                  ("PATCH", lambda: api.patch("/shops/1/listings/1", {"a": 1})), ("DELETE", lambda: api.delete("/listings/1")),
                  ("PUT json", lambda: api.put_json("/listings/1/inventory", {})),
                  ("post_file", lambda: api.post_file("/shops/1/listings/1/images", {"image": ("x", io.BytesIO(b"x"), "i")}))):
        t.append((f"FAIL: {ad} -> YASAK, istek yok", "YASAK" in (dur(f) or "") and s.log == []))
    t.append(("FAIL: SaltOkur olmayan istemci -> DUR", "SaltOkur degil" in (dur(KP.calis, Path(tempfile.mkdtemp()),
                                                                              E.Etsy(E.APIKeyStore("a", "b"))) or "")))
    # E tarama: betikte dogrudan ag cagrisi / yazma cagrisi yok
    kaynak = (Path(__file__).resolve().parent / "kolye_pazar.py").read_text()
    t.append(("PASS: tarama: requests / urllib / yazma cagrisi yok", not re.search(r"\brequests\.|\burllib\b|\.(post|put|patch|delete|put_json|post_file)\(",
                                                                                 kaynak.split("class SaltOkur")[0] + kaynak.split("def _sayi")[1])))
    return t


def main():
    t = testler()
    for ad, ok in t:
        print(("PASS " if ok else "FAIL ") + ad)
    n = sum(bool(ok) for _, ok in t)
    print(f"kolye_pazar testleri TOPLAM: {n}/{len(t)} PASS")
    sys.exit(0 if n == len(t) else 1)


if __name__ == "__main__":
    main()
