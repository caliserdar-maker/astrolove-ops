#!/usr/bin/env python3
"""Acik depoda MUSTERI BILGISI taramasi (14 Eki 2026, Takip gorevi). SALT OKUR; hicbir sey silinmez/degismez.
DEGER YAZMAZ: yalniz tur + sayi + kaynak (kosu no / artifact no / dal + yol + commit). Yoldaki 7+ haneli sayilar <NUM> olarak maskelenir.
Kaynaklar:
  loglar     : tum Actions kosularinin loglari (GET /actions/runs/{id}/logs zip)
  artifactlar: tum artifact zipleri (metin uyeleri taranir; gorsel/pdf uyeleri yalniz sayilir)
  git        : tum dallar + gecmis, metin blob'lari (<= 3 MB); bulunan blob'un dal/yol/ilk commit'i
Turler: eposta, receipt_no, prodigi_siparis, adres, telefon, alici_alani (buyer_*), kisisellestirme, mesaj, ad_adres_baglaminda.
Test degerleri (900000000N, 9000000001, 999001) ayri sayilir (test_receipt), musteri sayilmaz.
Ortam: GH_TOKEN (yalniz GET), GITHUB_REPOSITORY. Cikti: <out>/{LOG,ARTIFACT,GIT}_TARAMA.csv + OZET.md"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

IZINLI_ALAN = ("github.com", "noreply.github.com", "users.noreply.github.com", "anthropic.com", "example.com", "example.org",
               "rclone.org", "python.org", "iam.gserviceaccount.com", "prodigi.com", "metricool.com", "etsy.com", "googlegroups.com",
               "pypi.org", "astroloveart.com", "localhost")
IZINLI_EPOSTA_SHA = {"b7f5f765c9f06afbf4fdd09c054db80da908639fdff0a8efb3a466cf48f9ae25"}   # magaza sahibi (SAHIP_EPOSTA); deger depoda tutulmaz
DOSYA_UZANTI = re.compile(r"\.(png|jpe?g|gif|svg|webp|js|css|py|json|txt|md|csv|ya?ml|zip|pdf|ttf|woff2?)$", re.I)
TEST_RECEIPT = re.compile(r"^(9000000\d{3}|999001|900000000\d)$")
KALIP = {
    "eposta": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "receipt_no": re.compile(r"receipt(?:_id|Id| id|\b)[^0-9\n]{0,25}?(\d{6,12})", re.I),
    "prodigi_siparis": re.compile(r"\bord_\d{5,}\b"),
    # yalniz veri bicimi ("anahtar": "deger"); kod satirlari (row["city"], .get("zip")) sayilmaz
    "adres": re.compile(r'"(first_line|second_line|formatted_address|line1|line2|postalOrZipCode|townOrCity|zip|city)"\s*:\s*"([^"]{2,})"'),
    "telefon": re.compile(r'"(phone|phoneNumber|phone_number|telephone)"\s*:\s*"([^"]{5,})"', re.I),
    "alici_alani": re.compile(r'"(buyer_email|buyer_name|buyer_user_id|name_on_order)"\s*:\s*"?([^",}]{2,})'),
    "kisisellestirme": re.compile(r'"formatted_name"\s*:\s*"Personali[sz]ation[^"]*"\s*,\s*"formatted_value"\s*:\s*"([^"]{1,})"'
                                 r'|"formatted_value"\s*:\s*"([^"]{1,})"\s*,\s*"formatted_name"\s*:\s*"Personali[sz]ation'
                                 r'|"personali[sz]ation"\s*:\s*"([^"]{2,})"'
                                 r'|^\s*Personali[sz]ation\s*:\s*(\S.{1,})$', re.I | re.M),
    "mesaj": re.compile(r'"(message_from_buyer|gift_message|buyer_note|message_from_seller)"\s*:\s*"([^"]{2,})"'),
}
KOD = re.compile(r"[()\[\]{}$%\\]|\.get\b|\bNone\b|\bos\.|\bf\'|^\s*(r|row|x|o|p)\.")
AD = re.compile(r'"(name|first_name|last_name|full_name)"\s*:\s*"([^"]{2,})"')


def maskeli(v):
    v = (v or "").strip()
    return "***" in v or v in ("", "null", "None", "-", "[]", "{}", "true", "false", "0") or bool(KOD.search(v))


def tara(metin):
    """Donus: Counter(tur -> sayi). Degerler SAKLANMAZ."""
    c = Counter()
    for m in KALIP["eposta"].finditer(metin):
        e = m.group(0).lower()
        alan = e.split("@", 1)[1]
        if hashlib.sha256(e.encode()).hexdigest() in IZINLI_EPOSTA_SHA or DOSYA_UZANTI.search(e) or any(alan == a or alan.endswith("." + a) for a in IZINLI_ALAN) or "[bot]" in e:
            continue
        c["eposta"] += 1
    for m in KALIP["receipt_no"].finditer(metin):
        c["test_receipt" if TEST_RECEIPT.match(m.group(1)) else "receipt_no"] += 1
    c["prodigi_siparis"] += len(KALIP["prodigi_siparis"].findall(metin))
    for k in ("adres", "telefon", "alici_alani", "kisisellestirme", "mesaj"):
        for m in KALIP[k].finditer(metin):
            deger = next((g for g in reversed(m.groups()) if g), "")
            if not maskeli(deger):
                c[k] += 1
    if c["adres"]:
        c["ad_adres_baglaminda"] += sum(1 for m in AD.finditer(metin) if not maskeli(m.group(2)))
    return Counter({k: v for k, v in c.items() if v})


MUSTERI = ("eposta", "receipt_no", "prodigi_siparis", "adres", "telefon", "alici_alani", "kisisellestirme", "mesaj", "ad_adres_baglaminda")


class GH:
    def __init__(self, repo, token):
        self.repo, self.token, self.n = repo, token, 0

    def istek(self, yol, ham=False):
        url = yol if yol.startswith("http") else f"https://api.github.com/repos/{self.repo}{yol}"
        for d in range(4):
            r = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                                                     "X-GitHub-Api-Version": "2022-11-28"})
            try:
                self.n += 1
                with urllib.request.urlopen(r, timeout=120) as y:
                    b = y.read()
                    return b if ham else json.loads(b)
            except urllib.error.HTTPError as e:
                if e.code in (404, 410):
                    return None
                if e.code in (403, 429, 502, 503) and d < 3:
                    time.sleep(30 * (d + 1)); continue
                raise SystemExit(f"HTTP {e.code} {yol.split('?')[0]}")
        return None

    def hepsi(self, yol, anahtar):
        out, p = [], 1
        while True:
            j = self.istek(f"{yol}{'&' if '?' in yol else '?'}per_page=100&page={p}") or {}
            out += j.get(anahtar) or []
            if len(j.get(anahtar) or []) < 100:
                return out
            p += 1


def zip_tara(b, gorsel_say=False):
    c, g = Counter(), 0
    try:
        z = zipfile.ZipFile(io.BytesIO(b))
    except zipfile.BadZipFile:
        return tara(b.decode("utf-8", "replace")), 0
    for i in z.infolist():
        if i.is_dir():
            continue
        if re.search(r"\.(png|jpe?g|pdf|webp|tiff?|mp4|gif)$", i.filename, re.I):
            g += 1; continue
        if i.file_size > 50_000_000:
            continue
        c += tara(z.read(i).decode("utf-8", "replace"))
    return c, g


def yaz(yol, satirlar, alanlar):
    with open(yol, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=alanlar, extrasaction="ignore", lineterminator="\n"); w.writeheader(); w.writerows(satirlar)


def loglar(gh, out):
    runs = gh.hepsi("/actions/runs?", "workflow_runs")
    print(f"LOG: {len(runs)} kosu", flush=True)

    def bir(r):
        b = gh.istek(f"/actions/runs/{r['id']}/logs", ham=True)
        c, _ = zip_tara(b) if b else (Counter(), 0)
        return dict(kosu=r["id"], workflow=(r.get("path") or "").split("/")[-1], tarih=r["created_at"][:10], log_var=bool(b), **c)
    sat, t0 = [], time.time()
    with ThreadPoolExecutor(6) as ex:
        for i, s in enumerate(ex.map(bir, runs), 1):
            sat.append(s)
            if i % 200 == 0 or i == len(runs):
                g = time.time() - t0
                print(f"[{i}/{len(runs)}] %{100 * i // len(runs)} gecen {g:.0f} sn kalan ~{g / i * (len(runs) - i):.0f} sn | istek {gh.n}", flush=True)
    yaz(f"{out}/LOG_TARAMA.csv", sat, ["kosu", "workflow", "tarih", "log_var", "test_receipt", *MUSTERI])
    return sat


def artifactlar(gh, out):
    arts = gh.hepsi("/actions/artifacts?", "artifacts")
    print(f"ARTIFACT: {len(arts)}", flush=True)

    def bir(a):
        b = None if a.get("expired") else gh.istek(f"/actions/artifacts/{a['id']}/zip", ham=True)
        c, g = zip_tara(b) if b else (Counter(), 0)
        wr = a.get("workflow_run") or {}
        return dict(artifact=a["id"], ad=re.sub(r"\d{7,}", "<NUM>", a.get("name", "")), kosu=wr.get("id"), tarih=(a.get("created_at") or "")[:10],
                    suresi_doldu=a.get("expired"), gorsel_pdf=g, **c)
    with ThreadPoolExecutor(6) as ex:
        sat = list(ex.map(bir, arts))
    yaz(f"{out}/ARTIFACT_TARAMA.csv", sat, ["artifact", "ad", "kosu", "tarih", "suresi_doldu", "gorsel_pdf", "test_receipt", *MUSTERI])
    return sat


def git(out):
    oz = subprocess.run(["git", "cat-file", "--batch-all-objects", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                        capture_output=True, text=True, check=True).stdout.split("\n")
    blobs = [l.split()[0] for l in oz if l.endswith(tuple("0123456789")) and " blob " in l and int(l.split()[2]) <= 3_000_000]
    print(f"GIT: {len(blobs)} blob (<= 3 MB)", flush=True)
    p = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    bulunan = {}
    for i, sha in enumerate(blobs, 1):
        p.stdin.write((sha + "\n").encode()); p.stdin.flush()
        bas = p.stdout.readline().split()
        n = int(bas[2]); veri = p.stdout.read(n); p.stdout.read(1)
        if b"\x00" in veri[:8000]:
            continue
        c = tara(veri.decode("utf-8", "replace"))
        if any(c.get(k) for k in MUSTERI):
            bulunan[sha] = c
        if i % 20000 == 0:
            print(f"  [{i}/{len(blobs)}] bulunan {len(bulunan)}", flush=True)
    p.stdin.close(); p.wait()
    sat = []
    for sha, c in bulunan.items():
        ilk = subprocess.run(["git", "log", "--all", "--format=%h %cs", "--reverse", f"--find-object={sha}", "--name-only"],
                             capture_output=True, text=True).stdout.strip().split("\n")
        commit, tarih = (ilk[0].split() + ["", ""])[:2] if ilk and ilk[0] else ("", "")
        yol = next((x for x in ilk[1:] if x.strip()), "")
        dallar = subprocess.run(["git", "branch", "-r", "--contains", commit], capture_output=True, text=True).stdout.split() if commit else []
        tur_ = "kod_dokuman" if re.search(r"\.(py|sh|ya?ml|js|md)$|(^|/)CLAUDE\.md$", yol) else "veri"
        sat.append(dict(blob=sha[:10], yol=re.sub(r"\d{7,}", "<NUM>", yol), dosya_turu=tur_, ilk_commit=commit, tarih=tarih, dal_sayisi=len(dallar),
                        dallar=" ".join(d.replace("origin/", "") for d in dallar[:6]), **c))
    yaz(f"{out}/GIT_TARAMA.csv", sat, ["blob", "yol", "dosya_turu", "ilk_commit", "tarih", "dal_sayisi", "dallar", "test_receipt", *MUSTERI])
    return sat


def ozet(ad, sat, anahtar):
    etk = [s for s in sat if any(s.get(k) for k in MUSTERI)]
    tur = Counter()
    for s in etk:
        for k in MUSTERI:
            if s.get(k):
                tur[k] += 1
    en_eski = min((s.get("tarih") or "9999" for s in etk), default="-")
    grup = Counter(s.get(anahtar) for s in etk)
    acik = [f"## {ad}", f"- taranan {len(sat)}, musteri bilgisi olabilecek {len(etk)}, en eski {en_eski}",
            f"- tur (kac kayitta): {dict(tur)}"]
    if anahtar == "workflow":                            # workflow adlari acik loga yazilabilir; yol/artifact adi YALNIZ Drive'a
        acik.append(f"- en cok: {grup.most_common(12)}")
    return acik + [""], acik + [f"- en cok (ayrinti): {grup.most_common(25)}", ""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--kaynak", default="loglar,artifactlar,git")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    gh = GH(os.environ["GITHUB_REPOSITORY"], os.environ["GH_TOKEN"])
    bas = ["# Acik depo musteri bilgisi taramasi (salt okur; deger YOK, yalniz tur ve sayi)", ""]
    acik, gizli = list(bas), list(bas)
    k = a.kaynak.split(",")

    def ekle(parca):
        acik.extend(parca[0]); gizli.extend(parca[1])
    if "loglar" in k:
        ekle(ozet("Kosu loglari", loglar(gh, a.out), "workflow"))
    if "artifactlar" in k:
        s = artifactlar(gh, a.out)
        ekle(ozet("Artifact'ler", s, "ad"))
        g = f"- gorsel/pdf iceren artifact: {sum(1 for x in s if x.get('gorsel_pdf'))} (icerik taranamaz)"
        acik.append(g); gizli.append(g)
    if "git" in k:
        gs = git(a.out)
        ekle(ozet("Depo dosyalari + git gecmisi: VERI dosyalari (json/csv/txt/log...)", [x for x in gs if x["dosya_turu"] == "veri"], "yol"))
        ekle(ozet("Depo dosyalari + git gecmisi: KOD/DOKUMAN icinde (ornek ya da gercek; elle bakilmali)", [x for x in gs if x["dosya_turu"] != "veri"], "yol"))
    gizli.append(f"- GitHub istek sayisi {gh.n}")
    open(f"{a.out}/OZET.md", "w", encoding="utf-8").write("\n".join(gizli) + "\n")
    print("\n".join(acik))                                # acik log: yalniz sayi + workflow adi


if __name__ == "__main__":
    main()
