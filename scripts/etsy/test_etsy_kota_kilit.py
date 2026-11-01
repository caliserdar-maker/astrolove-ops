#!/usr/bin/env python3
"""etsy-kota olcum kilidi testi (Serdar 1 Kas madde 7). ETSY YOK, ag yok.
Etsy kilit kumesinde in_progress kosu varken etsy-kota olcum yapmaz / CSV'ye satir yazmaz; is akisi kilit kumesine girmez.
K1 kume: kupa-galeri78-yukle + yd-kapak-yukle icinde, etsy-kota DISINDA (yazicilari bekletmez)
K2 kontrol adiminin python'u (YAML'dan cikarilir) sahte GitHub kosulariyla: yazici in_progress -> atla; queued / completed / kume disi / kendi
   kosusu -> olc; API hatasi -> atla
K3 adim kosullari: olcum k1'e, Drive'a yazim k1 VE k2'ye bagli; Drive'a CSV yazan tek adim o; kota_olc yalniz olcum adiminda
K4 uctan uca sahte kosu: once bos, olcum sirasinda yazici basladi -> Drive'a yazim yok
Calistir: python3 scripts/etsy/test_etsy_kota_kilit.py [--yml .github/workflows/etsy-kota.yml] [--kok .]"""
import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sonuc = []


def k(ad, kosul, d=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + (f" | {d}" if d else ""))


def adimlar(yml):
    return yaml.safe_load(Path(yml).read_text(encoding="utf-8"))["jobs"]["olc"]["steps"]


def kontrol_kodu(adim):
    m = re.search(r"<<'PY'\n(.*?)\nPY", adim["run"], re.S)
    return m.group(1)


def kos(kod, kok, kosular, benim=500):
    sys.path.insert(0, str(Path(kok) / "scripts/etsy"))
    import kilit_bekle as K
    eski = K.api_kosular
    if isinstance(kosular, Exception):
        def getir():
            raise kosular
    else:
        def getir():
            return kosular
    K.api_kosular = getir
    out = Path(tempfile.mkstemp(prefix="kota_out_")[1])
    os.environ.update(GITHUB_RUN_ID=str(benim), GITHUB_OUTPUT=str(out))
    cwd = os.getcwd()
    try:
        os.chdir(kok)
        exec(compile(kod, "etsy-kota-kontrol", "exec"), {"__name__": "__main__"})
    finally:
        os.chdir(cwd); K.api_kosular = eski
    t = out.read_text(); out.unlink()
    return "atla=true" in t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yml", default=str(HERE.parents[1] / ".github/workflows/etsy-kota.yml"))
    ap.add_argument("--kok", default=str(HERE.parents[1]))
    a = ap.parse_args()
    sys.path.insert(0, str(Path(a.kok) / "scripts/etsy"))
    import kilit_bekle as K
    kume = K.kilit_kumesi(a.kok, "etsy")
    k(f"K1 kilit kumesi ({len(kume)}): kupa + yd yazicilari icinde, etsy-kota DISINDA",
      ".github/workflows/kupa-galeri78-yukle.yml" in kume and ".github/workflows/yd-kapak-yukle.yml" in kume
      and ".github/workflows/etsy-kota.yml" not in kume)
    st = adimlar(a.yml)
    ad = {s.get("name"): s for s in st}
    k1, k2 = ad.get("Etsy kosusu kontrolu (once)"), ad.get("Etsy kosusu kontrolu (sonra)")
    olc, yaz = ad.get("Olc (Drive'a henuz yazilmaz)"), ad.get("Drive'a ekle (olcum boyunca Etsy kosusu yoksa)")
    k("K3a adimlar var (kontrol once / olcum / kontrol sonra / Drive'a ekle) ve sirali",
      all([k1, k2, olc, yaz]) and st.index(k1) < st.index(olc) < st.index(k2) < st.index(yaz))
    if not all([k1, k2, olc, yaz]):
        return 1
    k("K3b olcum k1'e, sonra-kontrol k1'e, Drive'a yazim k1 VE k2'ye bagli",
      "steps.k1.outputs.atla == 'false'" in olc["if"] and "steps.k1.outputs.atla == 'false'" in k2["if"]
      and "steps.k1.outputs.atla == 'false'" in yaz["if"] and "steps.k2.outputs.atla == 'false'" in yaz["if"]
      and k1.get("id") == "k1" and k2.get("id") == "k2")
    drive_yaz = [s.get("name") for s in st if re.search(r'rclone\s+copyto\s+ETSY_KOTA\.csv\s+"gdrive:', s.get("run") or "")]
    olcen = [s.get("name") for s in st if "kota_olc.py" in (s.get("run") or "")]
    k(f"K3c Drive'a CSV yazan tek adim 'Drive'a ekle' ({drive_yaz}), kota_olc yalniz olcum adiminda ({olcen})",
      drive_yaz == [yaz["name"]] and olcen == [olc["name"]])
    izin = yaml.safe_load(Path(a.yml).read_text())["permissions"]
    k("K3d permissions actions: read, GH_TOKEN github.token (sir degil)", izin.get("actions") == "read"
      and k1["env"]["GH_TOKEN"] == "${{ github.token }}" and k2["env"]["GH_TOKEN"] == "${{ github.token }}")
    kod = kontrol_kodu(k1)
    k("K3e iki kontrol adiminin python'u ayni (yalniz etiket farki)", kod.replace("once", "X") == kontrol_kodu(k2).replace("sonra", "X"))
    kupa, yd = ".github/workflows/kupa-galeri78-yukle.yml", ".github/workflows/yd-kapak-yukle.yml"
    kosu = lambda i, p, s: dict(id=i, path=p, status=s, created_at="2026-11-01T10:00:00Z")  # noqa: E731
    vakalar = [
        ("kupa yazimi in_progress -> atla", [kosu(1, kupa, "in_progress")], True),
        ("yd in_progress -> atla", [kosu(2, yd, "in_progress")], True),
        ("yalniz queued kupa (kota tuketmiyor) -> olc", [kosu(3, kupa, "queued")], False),
        ("completed -> olc", [kosu(4, kupa, "completed")], False),
        ("kume disi in_progress (etsy-kota baska kosusu / CI) -> olc", [kosu(5, ".github/workflows/etsy-kota.yml", "in_progress"),
                                                                       kosu(6, ".github/workflows/ai-beyan-test.yml", "in_progress")], False),
        ("kendi kosusu ignore", [kosu(500, kupa, "in_progress")], False),
        ("bos -> olc", [], False),
    ]
    for ad_, kl, bek in vakalar:
        k(f"K2 {ad_}", kos(kod, a.kok, kl) == bek)
    k("K2 GitHub API hatasi -> atla (yanlis satir yerine eksik satir)", kos(kod, a.kok, OSError("ag yok")) is True)
    # K4 uctan uca: once bos, olcum sirasinda yazici basladi
    a1 = kos(kod, a.kok, [])
    a2 = kos(kontrol_kodu(k2), a.kok, [kosu(7, kupa, "in_progress")])
    yazilir = (not a1) and (not a2)
    k("K4 olcum sirasinda kupa basladi -> Drive'a yazim adimi kosmaz (k1 false, k2 true)", a1 is False and a2 is True and not yazilir)
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
