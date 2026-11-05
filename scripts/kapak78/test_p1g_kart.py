#!/usr/bin/env python3
"""p1g_kart testleri (Merkez 5 Kas P1-G). Bilinen PASS + bilinen FAIL. Sentetik kart (wa_s4); musteri verisi yok, Etsy yok, ag yok
(CI_KOK verilmezse kapak-ci-ref-20261029 dalindan ref/kapak_ci git fetch). Pillow 11.0.0 + raqm + tesseract gerekir.
Kullanim: [CI_KOK=<ref/kapak_ci>] python3 scripts/kapak78/test_p1g_kart.py -> SONUC n/n PASS (cikis 1 = FAIL)."""
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

BURA = Path(__file__).resolve().parent
KOK = BURA.parents[1]
sys.path.insert(0, str(BURA))
import p1g_kart as P  # noqa: E402
import yd_kart_ornek as K  # noqa: E402

sonuc = []
CIFT, ILAN = "AQUARIUS_AQUARIUS", "4570110121"
ESKI_SHA = "1f7d41ebed760908a716bb5cc29e31b0346528120c6ee3e0eeabac55cfb138e1"   # Drive MANIFEST_W02_W06_p0 (wa-kart-v11 40879133310)


def k(ad, kosul, ayr=""):
    sonuc.append(bool(kosul)); print(("PASS " if kosul else "FAIL ") + ad + ("" if kosul else f"  [{ayr}]"), flush=True)


def ci_kok():
    if os.environ.get("CI_KOK"):
        return Path(os.environ["CI_KOK"])
    d = Path(tempfile.mkdtemp(prefix="kapak_ci_"))
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", "kapak-ci-ref-20261029"], cwd=KOK, check=True)
    b = subprocess.run(["git", "show", f"FETCH_HEAD:ref/kapak_ci/CI_{CIFT}.png"], cwd=KOK, capture_output=True, check=True).stdout
    (d / f"CI_{CIFT}.png").write_bytes(b)
    return d


CI = ci_kok()
ci = Image.open(CI / f"CI_{CIFT}.png").convert("RGB")

# ---------- 1 bilinen PASS: ESKI metinle cizim = canli kartin Drive kaynagi (sha256); yeni metin varsayilan
eski_b, eski_k, eski_s, poster, cagri = P.ciz(ci, P.ESKI)
k("bilinen PASS: wa_s4(ci, ESKI) sha256 = Drive MANIFEST (W05 canli kaynagi)", hashlib.sha256(eski_b).hexdigest() == ESKI_SHA,
  hashlib.sha256(eski_b).hexdigest())
import wa_kupa_kart_ornek as WA  # noqa: E402
k("wa_s4 varsayilan = yeni onayli metin; eski soz wa_kupa_kart_ornek'te yok",
  WA.ONAY_METNI == "We make your print or file once you approve the preview" and P.ESKI not in Path(WA.__file__).read_text())
yeni_b, yeni_k, yeni_s, poster_y, _ = P.ciz(ci, P.YENI)
k("b: yeni metin iki satir 'We make your print or file' / 'once you approve the preview'",
  yeni_s[yeni_s.index("Your Approval") + 1:yeni_s.index("03")] == P.YENI_SATIR, yeni_s)
kb = P.kutu_b(eski_k, yeni_k, poster + poster_y)
k(f"b kutusu K.KUTULAR'dan = sabit {P.KUTU_B}", tuple(kb) == P.KUTU_B, kb)
sab = {b: kk for b, t, kk in yeni_k if t == "etiket" and b in ("blok0", "blok3")}
esk = {b: kk for b, t, kk in eski_k if t == "etiket" and b in ("blok0", "blok3")}
k("b: 01 ve 04 bloklari ve poster yerinde (yalniz 02 / 03 kayar)", sab == esk and poster == poster_y, (sab, esk, poster, poster_y))
try:
    P.kutu_b(eski_k + [("blok0", "metin", [1600, 900, 1700, 950])], yeni_k, poster)
    h = None
except SystemExit as e:
    h = str(e)
k("bilinen FAIL: b kutusu 01 blogunun kutusuna degerse DUR", h and "degiyor" in h, h)

# ---------- 2 kapilar: b ve a bilinen PASS
ta = P.dizi(eski_b)
kirp_b = P.birlesik([kk for b, t, kk in yeni_k if b == "blok1" and t == "metin"])
kirp_b = (kirp_b[0] - 6, kirp_b[1] - 6, kirp_b[2] + 6, kirp_b[3] + 6)
g = P.kart_kapilari(yeni_b, ta, kb, kirp_b, yeni_s)
k("b: tum kapilar PASS (bant / OCR / metin / jpeg)", g["PASS"], g)
a_b, kutu_a, ink, a_s, a_k = P.yontem_a(eski_b, eski_k, cagri)
ga = P.kart_kapilari(a_b, ta, kutu_a, kutu_a, a_s)
k(f"a: tum kapilar PASS, kutu = murekkep {ink} + 6", ga["PASS"] and list(kutu_a) == [ink[0] - 6, ink[1] - 6, ink[2] + 6, ink[3] + 6], ga)
k("a: yeni satirlar eski satirin x / y'sinde (ilk satir ust kenari = eski)", a_k[0][:2] == [k_ for b, t, k_ in eski_k if b == "blok1" and t == "metin"][0][:2],
  (a_k, eski_k))

# ---------- 3 bilinen FAIL
go = P.kart_kapilari(eski_b, ta, kb, kirp_b, yeni_s)
k("bilinen FAIL: eski metinli W05 -> OCR kapisi FAIL (eski desen >= 1)", not go["ocr"]["PASS"] and len(go["ocr"]["eski_desen"]) >= 1, go["ocr"])
im = Image.open(io.BytesIO(yeni_b)).convert("RGB"); d = ImageDraw.Draw(im)
K.BLOK[0] = "test"; K.yaz(d, K.METIN, ["Extra line"], 1663, 1700)           # 04 blogu hizasinda, kutu disinda
gt = P.kart_kapilari(P.jpeg_bayt(im), ta, kb, kirp_b, yeni_s)
k("bilinen FAIL: kutu disina bir satir -> bant kapisi FAIL", not gt["bant"]["PASS"], gt["bant"])
for t in ("We make your print or file once you approve the preview.", "We make your print — once you approve", "Print + file", "a = b"):
    m = P.metin_kapisi([t])
    k(f"bilinen FAIL: metin kapisi {t!r}", not m["PASS"], m)
m = P.metin_kapisi(["We make your print or file printed on museum paper"])
k("bilinen FAIL: etsy_common METIN_KESIN (museum) -> metin FAIL", not m["PASS"] and m["etsy_metin"], m)
k("metin kapisi: yeni metin PASS", P.metin_kapisi([P.YENI])["PASS"])
b90 = io.BytesIO(); Image.open(io.BytesIO(yeni_b)).save(b90, "JPEG", quality=90, subsampling=0)
b420 = io.BytesIO(); Image.open(io.BytesIO(yeni_b)).save(b420, "JPEG", quality=95)
k("bilinen FAIL: JPEG q90 -> jpeg kapisi FAIL (nicemleme tablosu)", not P.jpeg_kapisi(b90.getvalue())["PASS"])
k("bilinen FAIL: JPEG q95 subsampling 4:2:0 -> jpeg kapisi FAIL", not P.jpeg_kapisi(b420.getvalue())["PASS"])

# ---------- 3b kesin kimlik zinciri (Serdar 5 Kas A): r5 id = SONRA son_ids[W05], yukleme_kaydi[5] sha256 = MANIFEST
GERCEK = {"CANCER_LIBRA": (8764246038, "11ff57bd9570ad788ac0af7d9f651610a2b25796629a914747f6542b12cf40f4"),   # 5 Kas GALERI.json r5 +
          "SAGITTARIUS_SAGITTARIUS": (8769344230, "0e17ae6567299f4903032a1b01abac8d527188bff18b47075946c99d00179963"),  # Drive MANIFEST
          "AQUARIUS_AQUARIUS": (8810839017, ESKI_SHA)}
with tempfile.TemporaryDirectory() as td:
    kok = Path(td)
    for i, (c, (rid, sh)) in enumerate(GERCEK.items()):
        lid = str(9100000000 + i)
        son = [rid + 100 + x for x in range(10)]; son[4] = rid
        kay = [dict(hedef_sira=x + 1, sha256=f"{x:064x}" if x != 4 else sh, listing_image_id=son[x]) for x in range(10)]
        for kosu, j in (("40884979725", dict(son_ids=[0] * 10, yukleme_kaydi=kay)),          # eski kosu: tum kayit
                        ("40922119855", dict(son_ids=son, yukleme_kaydi=[dict(kay[0], sha256="f" * 64)]))):   # sonraki: yalniz rank 1 (ONAR)
            (kok / kosu / "ilanlar").mkdir(parents=True, exist_ok=True)
            (kok / kosu / "ilanlar" / f"SONRA_{lid}.json").write_text(json.dumps(j))
        so = P.sonra_kayit(kok, lid)
        kp = P.kimlik_kapisi(rid, so, sh)
        k(f"bilinen PASS: kimlik zinciri {c} (r5 id = son_ids[W05], yukleme sha = MANIFEST; iki kosu birlesik)", kp["PASS"], kp)
        k(f"bilinen FAIL: {c} baska rank'in id'si (son_ids[W04]) -> kimlik FAIL", not P.kimlik_kapisi(son[3], so, sh)["PASS"])
        baska = [v for x, (_, v) in GERCEK.items() if x != c][0]
        k(f"bilinen FAIL: {c} baska ciftin sha256'si -> kimlik FAIL", not P.kimlik_kapisi(rid, so, baska)["PASS"])
    k("bilinen FAIL: SONRA kaydi yok -> kimlik FAIL", not P.kimlik_kapisi(1, P.sonra_kayit(kok, "1"), ESKI_SHA)["PASS"])
    # kaynak secimi: sha = MANIFEST = yukleme sha (canli fark kapisi yok)
    (kok / "k" / "40879133310").mkdir(parents=True)
    (kok / "k" / "40879133310" / f"{CIFT}_W05_SUREC.jpg").write_bytes(eski_b)
    (kok / "k" / "40879133310" / "MANIFEST_W02_W06_p0.csv").write_text(f"cift,ad,dosya,sha256\n{CIFT},W05_SUREC,{CIFT}_W05_SUREC.jpg,{ESKI_SHA}\n")
    sec, _ = P.kaynak_sec(kok / "k", CIFT, ESKI_SHA)
    k("kaynak secimi: dosya sha = MANIFEST = yukleme sha -> secilir", sec and sec["kosu"] == "40879133310")
    k("bilinen FAIL: kaynak secimi yukleme sha farkli -> secilmez", P.kaynak_sec(kok / "k", CIFT, "0" * 64)[0] is None)
with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
    f.write(eski_b); f.flush(); co = P.canli_ocr(f.name)
k("canli OCR kapisi: eski metinli kart -> eski desen >= 1 ve capa (PASS)", co["PASS"], co)
with tempfile.NamedTemporaryFile(suffix=".jpg") as f:
    f.write(yeni_b); f.flush(); cy = P.canli_ocr(f.name)
k("bilinen FAIL: canli OCR kapisi yeni metinli kart (eski desen yok) -> FAIL", not cy["PASS"], cy)

# ---------- 4 tara: eski -> desen, yeni -> 0, capa silinmis -> okunamadi, alt metin, dosya yok
with tempfile.TemporaryDirectory() as td:
    y = Path(td) / "y"; o = Path(td) / "o"
    capasiz = Image.open(io.BytesIO(yeni_b)).convert("RGB")
    lab = [kk for b, t, kk in yeni_k if b == "blok1" and t == "etiket"]
    ImageDraw.Draw(capasiz).rectangle(P.birlesik(lab), fill=K.ZEMIN)
    ilan = {"9000000001_ARIES_ARIES": [(5, eski_b, ""), (1, yeni_b, "No reply in 24 hours? We print as shown")],
            "9000000002_LEO_LEO": [(5, yeni_b, "")], "9000000003_LIBRA_LIBRA": [(5, P.jpeg_bayt(capasiz), ""), (2, None, "")]}
    for ad, gl in ilan.items():
        (y / ad).mkdir(parents=True)
        js = []
        for r, b, alt in gl:
            iid = 100 + r
            if b is not None:
                (y / ad / f"r{r}_{iid}.jpg").write_bytes(b)
            js.append(dict(rank=r, listing_image_id=iid, alt_text=alt))
        (y / ad / "GALERI.json").write_text(json.dumps(dict(gorseller=js)))
    rc = P.tara(y, o, 2)
    rows = list(csv.DictReader(open(o / "TARAMA.csv", encoding="utf-8")))
    oz = (o / "OZET.md").read_text(encoding="utf-8")
    ocr1 = {r_["desen"] for r_ in rows if r_["listing_id"] == "9000000001" and r_["rank"] == "5" and r_["kaynak"] == "ocr"}
    k("tara: eski metinli r5 -> OCR desenleri (no reply, as shown, if there is no)", {"no reply", "as shown", "if there is no"} <= ocr1, ocr1)
    k("tara: yeni metinli r5 -> 0 desen ve okunamadi degil", not [r_ for r_ in rows if r_["listing_id"] == "9000000002"], rows)
    k("tara: capa silinmis r5 -> okunamadi capa_yok", any(r_["listing_id"] == "9000000003" and r_["rank"] == "5" and r_["desen"] == "capa_yok"
                                                           for r_ in rows), rows)
    k("tara: dosya yok -> okunamadi dosya_yok", any(r_["listing_id"] == "9000000003" and r_["rank"] == "2" and r_["desen"] == "dosya_yok"
                                                    for r_ in rows), rows)
    alt = {r_["desen"] for r_ in rows if r_["kaynak"] == "alt_text"}
    k("tara: alt metin 'No reply in 24 hours?' -> no reply + 24 hours? (kaynak alt_text)", {"no reply", "24 hours?"} <= alt, alt)
    k("tara: TARAMA.csv metin icermez (yalniz ilan, cift, rank, image_id, kaynak, desen)", list(rows[0]) == P.TARA_ALAN and
      "as shown if" not in (o / "TARAMA.csv").read_text(), list(rows[0]))
    k("tara: OZET rank 5 okunamadi -> SONUC EKSIK; cikis 0", rc == 0 and "EKSIK" in oz and "gorsel (GALERI.json) 5" in oz, (rc, oz))
    with open(y / "OKUMA.csv", "w", newline="") as f_:
        w_ = csv.DictWriter(f_, fieldnames=["listing_id", "gorsel"]); w_.writeheader()
        w_.writerows([dict(listing_id="9000000001", gorsel=2), dict(listing_id="9000000002", gorsel=1), dict(listing_id="9000000003", gorsel=2)])
    P.tara(y, o, 2); oz = (o / "OZET.md").read_text(encoding="utf-8")
    k("tara: OKUMA.csv sayimi OZET'te (toplam 5, GALERI.json ile ayni)", "'okuma_toplam': 5" in oz and "'GALERI_json_ayni': True" in oz, oz)

print(f"SONUC: {sum(sonuc)}/{len(sonuc)} PASS")
sys.exit(0 if all(sonuc) else 1)
