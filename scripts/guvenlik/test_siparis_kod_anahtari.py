#!/usr/bin/env python3
"""SIPARIS_KOD_ANAHTARI testi (Serdar 12 Kas 2026, K2). Opak siparis kodu ("S-" + HMAC) ureten iki islev:
scripts/prodigi/order_router.py receipt_kod ve scripts/kupa_siparis/kupa_siparis.py kod_. Python kodu DEGISMEDI; yalniz 5 adim
env'ine SIPARIS_KOD_ANAHTARI eklendi. Islevler modul ICE AKTARILMADAN (agir bagimliliklar, ag yok) kaynaktan ayiklanip kosulur.
Bilinen PASS: anahtar BOS (GitHub'da tanimsiz secret bos dize gelir) -> kod onceki ile AYNI (ETSY_SHARED_SECRET ile).
Bilinen FAIL: anahtar DOLU -> kod FARKLI ve Etsy shared secret degisse de AYNI kalir.
Tum degerler sentetik. Kullanim: python3 scripts/guvenlik/test_siparis_kod_anahtari.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import ast
import hashlib
import hmac
import os
import re
import sys
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parents[2]
KAYNAK = (("order_router.receipt_kod", "scripts/prodigi/order_router.py", "receipt_kod"),
          ("kupa_siparis.kod_", "scripts/kupa_siparis/kupa_siparis.py", "kod_"))
ESKI, YENI, ANAHTAR, NO = "sentetik-eski-secret-01", "sentetik-yeni-secret-02", "sentetik-kod-anahtari-03", "9000000001"
SATIR = "SIPARIS_KOD_ANAHTARI: ${{ secrets.SIPARIS_KOD_ANAHTARI }}"
sonuc = []


def k(ad, kosul):
    sonuc.append(bool(kosul))
    print(("PASS " if kosul else "FAIL ") + ad, flush=True)


def islev(dosya, ad):
    """Islevi kaynaktan ayiklar; modulun geri kalani calistirilmaz. Ayiklamanin gercek modulden ayrismamasi icin: ayni adli tek ust
    duzey tanim olmali, baska yerde yeniden atanmamali ve islevin kullandigi os / hmac / hashlib modulde (ya da islevde) ice aktarilmis
    olmali (ad alanini bu test verdigi icin eksik import'u kendisi gostermezdi)."""
    agac = ast.parse((KOK / dosya).read_text(encoding="utf-8"))
    tanimlar = [d for d in ast.walk(agac) if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)) and d.name == ad]
    atamalar = [d for d in ast.walk(agac) if isinstance(d, ast.Name) and d.id == ad and isinstance(d.ctx, ast.Store)]
    assert len(tanimlar) == 1 and tanimlar[0] in agac.body and not atamalar, f"{dosya}: {ad} tek ust duzey tanim olmali"
    dugum = tanimlar[0]

    def ithal(govde):
        return {(a.asname or a.name).split(".")[0] for d in govde if isinstance(d, (ast.Import, ast.ImportFrom)) for a in d.names}
    kullanilan = {d.id for d in ast.walk(dugum) if isinstance(d, ast.Name)} & {"os", "hmac", "hashlib"}
    eksik = kullanilan - ithal(agac.body) - ithal(list(ast.walk(dugum)))
    assert not eksik, f"{dosya}: {ad} icin modulde ice aktarilmamis: {sorted(eksik)}"
    ns = {"os": os, "hmac": hmac, "hashlib": hashlib}
    exec(compile(ast.Module(body=[dugum], type_ignores=[]), dosya, "exec"), ns)  # noqa: S102  depodaki kendi kaynagimiz
    return ns[ad]


def kod(f, **ortam):
    with mock.patch.dict(os.environ, ortam, clear=True):
        return f(NO)


def beklenen(anahtar):
    return "S-" + hmac.new(anahtar.encode(), NO.encode(), hashlib.sha256).hexdigest()[:8]


def main():
    kodlar = {}
    for etiket, dosya, ad in KAYNAK:
        f = islev(dosya, ad)
        onceki = kod(f, ETSY_SHARED_SECRET=ESKI)                                   # degisiklikten onceki ortam: anahtar hic yok
        bos = kod(f, ETSY_SHARED_SECRET=ESKI, SIPARIS_KOD_ANAHTARI="")             # yeni ortam, secret tanimsiz (bos dize)
        dolu = kod(f, ETSY_SHARED_SECRET=ESKI, SIPARIS_KOD_ANAHTARI=ANAHTAR)
        dolu_yeni = kod(f, ETSY_SHARED_SECRET=YENI, SIPARIS_KOD_ANAHTARI=ANAHTAR)  # Etsy secret'i yenilendi
        bos_yeni = kod(f, ETSY_SHARED_SECRET=YENI, SIPARIS_KOD_ANAHTARI="")
        kodlar[etiket] = (bos, dolu)
        k(f"{etiket}: ikisi de BOS (sahte receipt adiminin ortami) -> sabit yedek anahtar; onceki davranisla ayni",
          kod(f) == kod(f, ETSY_SHARED_SECRET="", SIPARIS_KOD_ANAHTARI="") == beklenen("astrolove"))
        k(f"{etiket}: bilinen PASS: anahtar BOS -> kod onceki ile AYNI", bos == onceki == beklenen(ESKI))
        k(f"{etiket}: bilinen FAIL: anahtar DOLU -> kod FARKLI", dolu != onceki and dolu == beklenen(ANAHTAR))
        k(f"{etiket}: anahtar DOLU iken Etsy secret'i degisse de kod AYNI", dolu_yeni == dolu)
        k(f"{etiket}: kontrol: anahtar BOS iken Etsy secret'i degisince kod DEGISIR (anahtarin gerekcesi)", bos_yeni != bos and bos_yeni == beklenen(YENI))
        k(f"{etiket}: kod bicimi S- + 8 onaltilik hane; siparis no kodda gecmez", re.fullmatch(r"S-[0-9a-f]{8}", dolu) is not None and NO not in dolu)
    k("iki islev ayni ortamda ayni kodu uretir (router ve kupa kodlari eslesir)", len(set(kodlar.values())) == 1)
    # is akislari: 5 env blogu, her biri ETSY_SHARED_SECRET satirinin hemen altinda (kodu ureten adimin anahtari aldigi: test_workflows.py)
    BEKLENEN = {"pod-order-router.yml": 2, "kupa-siparis.yml": 1, "router-kota-deneme.yml": 1, "pod-arac-v4.yml": 1}
    metinler = {p.name: p.read_text(encoding="utf-8") for p in sorted((KOK / ".github/workflows").glob("*.yml"))}

    def say(m):
        sayim = {}
        for ad, metin in m.items():
            sat = metin.split("\n")
            for i, x in enumerate(sat):
                if x.strip() == SATIR:
                    sayim[ad] = sayim.get(ad, 0) + 1
                    ust = sat[i - 1]
                    if not ust.strip().startswith("ETSY_SHARED_SECRET: ${{ secrets.ETSY_SHARED_SECRET }}") or \
                            len(ust) - len(ust.lstrip()) != len(x) - len(x.lstrip()):
                        sayim[ad + " (yanlis yer)"] = 1
        return sayim
    k("is akislari: SIPARIS_KOD_ANAHTARI tam 5 env blogunda (pod-order-router 2, kupa-siparis 1, router-kota-deneme 1, pod-arac-v4 1)",
      say(metinler) == BEKLENEN)
    r = metinler["pod-order-router.yml"]
    for ad, bozuk in (("bir blokta satir eksik", r.replace("          " + SATIR + "\n", "", 1)),
                      ("satir ETSY_SHARED_SECRET'in altinda degil", r.replace("          " + SATIR + "\n", "", 1).replace(
                          "          ETSY_API_KEY:", "          " + SATIR + "\n          ETSY_API_KEY:", 1)),
                      ("girinti farkli", r.replace("          " + SATIR, "            " + SATIR, 1))):
        k(f"bilinen FAIL: sayim kontrolu: {ad} -> yakalanir", bozuk != r and say(dict(metinler, **{"pod-order-router.yml": bozuk})) != BEKLENEN)
    # anahtar adi gecen her dosya (tirnak bicimine bakmadan; .py, .sh, is akislari): yeni bir kullanim eklenirse env blogu da eklenmeli
    gecen = sorted(str(p.relative_to(KOK)) for kok, desen in (("scripts", "*.py"), ("scripts", "*.sh"), (".github/workflows", "*.yml"))
                   for p in (KOK / kok).rglob(desen) if "SIPARIS_KOD_ANAHTARI" in p.read_text(encoding="utf-8", errors="replace"))
    uretim = [x for x in gecen if "/test_" not in x and x not in ("scripts/etsy/secret_gecis.py", ".github/workflows/etsy-secret-gecis.yml")]
    k("anahtar adi gecen uretim dosyalari: yalniz order_router.py, kupa_siparis.py ve 4 is akisi",
      uretim == sorted([".github/workflows/" + a for a in BEKLENEN] + ["scripts/kupa_siparis/kupa_siparis.py", "scripts/prodigi/order_router.py"]))
    print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
    return 0 if all(sonuc) else 1


if __name__ == "__main__":
    sys.exit(main())
