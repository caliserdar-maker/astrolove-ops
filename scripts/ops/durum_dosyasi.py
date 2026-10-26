#!/usr/bin/env python3
"""Drive durum dosyasi okuma/yazma kapilari (26 Eki 2026, Serdar onayi). onay_defteri.py'nin genellestirilmis hali.

Sorun: okuma hatasinda bos varsayilanla devam edilip sonra Drive'a geri yaziliyordu (eski kayitlar silinir).
Turler:
  onay          JSON nesnesi; yalniz --kimlik kaydi eklenir/guncellenir, digerleri birebir ayni (ONAYLAR.json).
  json-ilanlar  JSON nesnesi, "ilanlar" nesnesi; anahtarlar azalmaz, degerler guncellenebilir (galeri ILERLEME.json).
  csv           baslikta --anahtar sutunu; anahtar kumesi azalmaz, satir degerleri guncellenebilir (STATE.csv).
  md            bos olmayan metin; eski satirlar yeni metinde ayni sirayla durur (yalniz satir ekleme).
oku: lsjson hatasi FAIL. Dosya listede varsa copyto ZORUNLU, boyut listeyle ayni, icerik ture uygun (bos / bozuk FAIL).
     Ilk kayit yalniz: --ilk-kayit-izni + dosya listede yok (ya da klasor yok, ust klasorden dogrulanir) + yedek yok +
     dogrudan okuma da basarisiz. csv: anahtar bos/tekrar FAIL; md: CRLF normalize.
yaz: icerik degismediyse yazma yok (onay turunde once kimlik kaydi kontrol edilir). Azalmama (csv --korunan sutunlarda dolu
     deger bosalmaz; json-ilanlar'da cift/set/durum bosalmaz, PASS ve set>=hedef (kayittaki beklenen gorsel sayisi, yoksa 17) kayit geri donmez), okumadan beri uzak degismedi (sha256), yedek <klasor>/YEDEK/<ad>_<damga>_<run>
     (--immutable + geri okuma; yazilamazsa asil yazma yok), yazim + sha256 geri okuma, sonra YEDEK/ icinde yalniz bu
     dosyanin yedeklerinden en yeni 30'u kalir (silme yalniz yeni yedek geri okunduktan ve asil yazim dogrulandiktan sonra).
Her FAIL cikis 1; ::error:: satirinda yalniz neden ve sayilar (kimlik/receipt yazilmaz). RCLONE ortam degiskeni: sahte rclone."""
import argparse
import csv
import fnmatch
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

YEDEK_DIR, YEDEK_SAKLA = "YEDEK", 30
BOS = {"onay": b"{}\n", "json-ilanlar": b'{"ilanlar": {}}\n', "csv": b"", "md": b""}


class DurumHatasi(Exception):
    pass


def rclone(*args):
    komut = shlex.split(os.environ.get("RCLONE", "rclone")) + list(args)
    r = subprocess.run(komut, capture_output=True, timeout=120)
    return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")[-300:]


def sha(b):
    return hashlib.sha256(b).hexdigest()


class Dosya:
    def __init__(self, uzak, tur, anahtar="", kimlik="", eski_yedek="", etiket="", korunan=(), ilk_izin=True):
        if "/" not in uzak:
            raise DurumHatasi("uzak yol klasor/dosya olmali")
        self.klasor, self.ad = uzak.rsplit("/", 1)
        self.uzak, self.tur, self.anahtar, self.kimlik, self.eski_yedek = uzak, tur, anahtar, kimlik, eski_yedek
        self.korunan, self.ilk_izin = tuple(korunan), ilk_izin
        self.kok, self.uz = os.path.splitext(self.ad)
        self.etiket = etiket or ("defter" if tur == "onay" else "dosya")
        self.yedek_rx = re.compile(rf"^{re.escape(self.kok)}_\d{{8}}T\d{{12}}Z_[A-Za-z0-9-]+{re.escape(self.uz)}$")

    # ---- icerik
    def coz(self, b, ne):
        if self.tur in ("onay", "json-ilanlar"):
            try:
                v = json.loads(b.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                raise DurumHatasi(f"{ne} gecerli JSON degil ({type(e).__name__})") from e
            if not isinstance(v, dict):
                raise DurumHatasi(f"{ne} JSON nesnesi degil ({type(v).__name__})")
            if self.tur == "json-ilanlar" and not isinstance(v.get("ilanlar"), dict):
                raise DurumHatasi(f"{ne} 'ilanlar' nesnesi yok")
            return v
        try:
            t = b.decode("utf-8-sig")
        except UnicodeDecodeError as e:
            raise DurumHatasi(f"{ne} UTF-8 degil") from e
        if not t.strip():
            raise DurumHatasi(f"{ne} bos")
        if self.tur == "csv":
            r = csv.DictReader(io.StringIO(t))
            if not r.fieldnames or self.anahtar not in r.fieldnames:
                raise DurumHatasi(f"{ne} CSV basliginda '{self.anahtar}' yok")
            satir = list(r)
            if any(None in s for s in satir):
                raise DurumHatasi(f"{ne} CSV satirlarinda baslikla uyusmayan sutun var")
            anahtarlar = [(s.get(self.anahtar) or "").strip() for s in satir]
            if any(not k for k in anahtarlar):
                raise DurumHatasi(f"{ne} CSV'de bos '{self.anahtar}' var ({sum(1 for k in anahtarlar if not k)} satir)")
            if len(set(anahtarlar)) != len(anahtarlar):
                raise DurumHatasi(f"{ne} CSV'de tekrar eden '{self.anahtar}' var ({len(anahtarlar) - len(set(anahtarlar))} satir)")
            return dict(baslik=list(r.fieldnames), kayit={s[self.anahtar]: s for s in satir})
        return t.replace("\r\n", "\n").replace("\r", "\n").split("\n")      # CRLF: ekleme kodu metin kipinde okur

    def bos_mu(self, b):
        return self.tur in ("csv", "md") and not b.strip()

    # ---- azalmama
    def azalmama(self, once, sonra):
        if self.tur == "onay":
            k = self.kimlik
            if k not in sonra:
                raise DurumHatasi("yeni defterde bu kimligin kaydi yok")
            beklenen = len(once) + (0 if k in once else 1)
            if len(sonra) != beklenen:
                raise DurumHatasi(f"kayit sayisi {len(sonra)} != beklenen {beklenen} (once {len(once)})")
            eksik = [x for x in once if x not in sonra]
            degisen = [x for x in once if x != k and x in sonra and sonra[x] != once[x]]
            fazla = [x for x in sonra if x not in once and x != k]
            if eksik or degisen or fazla:
                raise DurumHatasi(f"onceki kayitlar korunmadi: silinen {len(eksik)} degisen {len(degisen)} fazla {len(fazla)} kayit")
        elif self.tur == "json-ilanlar":
            eksik = [x for x in once["ilanlar"] if x not in sonra["ilanlar"]]
            ust = [x for x in once if x not in sonra]
            if eksik or ust:
                raise DurumHatasi(f"kayit sayisi azaldi / onceki kayitlar korunmadi: silinen ilan {len(eksik)}, ust anahtar {len(ust)}")
            bos, geri = 0, 0
            for x, o in once["ilanlar"].items():
                n = sonra["ilanlar"][x]
                if not isinstance(n, dict) or any(str((o or {}).get(f) or "") and not str(n.get(f) or "") for f in ("cift", "set", "durum")):
                    bos += 1; continue
                try:
                    hedef = int(o.get("hedef") or 17)   # beklenen gorsel sayisi (kayitta yoksa galeri77: 17; galeri v10: 9)
                    tamam = o.get("durum") == "PASS" and int(o.get("set") or 0) >= hedef   # tekrar yuklenmeyen kayit
                    if tamam and (n.get("durum") != "PASS" or int(n.get("set") or 0) < int(o.get("set") or 0)):
                        geri += 1
                except (TypeError, ValueError):
                    geri += 1
            if bos or geri:
                raise DurumHatasi(f"onceki kayitlar korunmadi: icerigi bosaltilan ilan {bos}, PASS'tan geri donen ilan {geri}")
        elif self.tur == "csv":
            eksik = [x for x in once["kayit"] if x not in sonra["kayit"]]
            sutun = [c for c in once["baslik"] if c not in sonra["baslik"]]
            bos = sum(1 for x, o in once["kayit"].items() if x in sonra["kayit"]
                      for c in self.korunan if (o.get(c) or "").strip() and not (sonra["kayit"][x].get(c) or "").strip())
            if bos:
                raise DurumHatasi(f"onceki kayitlar korunmadi: korunan sutunda ({','.join(self.korunan)}) bosaltilan deger {bos}")
            if eksik or sutun:
                raise DurumHatasi(f"kayit sayisi {len(sonra['kayit'])} (once {len(once['kayit'])}) / onceki kayitlar korunmadi: "
                                  f"silinen {len(eksik)} satir, {len(sutun)} sutun")
        else:
            a, b = [x for x in once], [x for x in sonra]
            while a and not a[-1].strip():
                a.pop()
            while b and not b[-1].strip():
                b.pop()
            i = 0
            for x in b:
                if i < len(a) and x == a[i]:
                    i += 1
            if i != len(a) or len(b) < len(a):
                raise DurumHatasi(f"satir sayisi {len(b)} (once {len(a)}) / onceki satirlar korunmadi (yalniz ekleme serbest)")

    # ---- uzak
    def listele(self):
        inc = ["--include", f"/{self.ad}", "--include", f"/{YEDEK_DIR}/{self.kok}_*{self.uz}"]
        if self.eski_yedek:
            inc += ["--include", f"/{self.eski_yedek}"]
        rc, out, err = rclone("lsjson", self.klasor, "-R", "--max-depth", "2", "--files-only", *inc)
        if rc != 0 and "directory not found" in err and self.klasor_yok():
            print(f"klasor Drive'da yok (ust klasor listelendi): {self.ad} hic olusturulmamis", flush=True)
            return None, 0
        if rc != 0:
            raise DurumHatasi(f"listeleme hatasi (rclone lsjson rc {rc}): {err.strip()}")
        try:
            hepsi = json.loads(out.decode("utf-8") or "[]")
            yol = lambda k: str(k.get("Path") or k.get("Name") or "")  # noqa: E731
            ana = [k for k in hepsi if yol(k) == self.ad]
            yedek = [k for k in hepsi if (yol(k).startswith(f"{YEDEK_DIR}/") and self.yedek_rx.match(yol(k).split("/", 1)[1]))
                     or (self.eski_yedek and "/" not in yol(k) and fnmatch.fnmatch(yol(k), self.eski_yedek))]
        except (ValueError, AttributeError, TypeError) as e:
            raise DurumHatasi("listeleme ciktisi okunamadi") from e
        if len(ana) > 1:
            raise DurumHatasi(f"Drive'da {len(ana)} adet {self.ad} var (belirsiz)")
        return (ana[0] if ana else None), len(yedek)

    def klasor_yok(self):
        """Klasorun gercekten olmadigi ust klasor listesiyle dogrulanir; ust klasor de okunamazsa False (FAIL kalir)."""
        if "/" not in self.klasor.split(":", 1)[-1]:
            return False
        ust, ad = self.klasor.rsplit("/", 1)
        rc, out, _ = rclone("lsjson", ust, "--dirs-only", "--max-depth", "1")
        if rc != 0:
            return False
        try:
            return all(k.get("Name") != ad for k in json.loads(out.decode("utf-8") or "[]"))
        except (ValueError, AttributeError):
            return False

    def ilk_kayit_kapisi(self, yedek):
        if not self.ilk_izin:
            raise DurumHatasi(f"{self.ad} Drive'da bulunamadi ve bu dosya icin ilk kayit izni yok (dosya var olmali); yazma yok")
        if yedek:
            raise DurumHatasi(f"{self.ad} listede yok ama {yedek} yedek var: {self.etiket} daha once vardi, ilk kayit sayilmaz; yazma yok")
        rc, _, _ = rclone("cat", self.uzak)
        if rc == 0:
            raise DurumHatasi(f"{self.ad} listede yok ama dogrudan okunabiliyor (liste/filtre hatasi); yazma yok")

    def uzak_oku(self):
        rc, out, err = rclone("cat", self.uzak)
        if rc != 0:
            raise DurumHatasi(f"uzak {self.etiket} okunamadi (rclone cat rc {rc}): {err.strip()}")
        return out

    def yedek_buda(self):
        rc, out, err = rclone("lsjson", f"{self.klasor}/{YEDEK_DIR}", "--files-only", "--max-depth", "1",
                              "--include", f"/{self.kok}_*{self.uz}")
        if rc != 0:
            print(f"::warning::yedek listesi okunamadi, budama yapilmadi (rc {rc})", flush=True)
            return 0
        try:
            adlar = sorted(n for n in (k.get("Name", "") for k in json.loads(out.decode("utf-8") or "[]")) if self.yedek_rx.match(n))
        except (ValueError, AttributeError, TypeError):
            print("::warning::yedek listesi cozulemedi, budama yapilmadi", flush=True)
            return 0
        sil = adlar[:-YEDEK_SAKLA] if len(adlar) > YEDEK_SAKLA else []
        for n in sil:
            rc, _, err = rclone("deletefile", f"{self.klasor}/{YEDEK_DIR}/{n}")
            if rc != 0:
                print(f"::warning::eski yedek silinemedi (rc {rc}); sonraki kosuda yeniden denenir", flush=True)
        return len(sil)


def oku(d, yerel, durum):
    yerel.parent.mkdir(parents=True, exist_ok=True); durum.mkdir(parents=True, exist_ok=True)
    k, yedek = d.listele()
    if k is None:
        d.ilk_kayit_kapisi(yedek)
        yerel.write_bytes(BOS[d.tur])
        (durum / "ONCE").write_bytes(BOS[d.tur]); (durum / "ILK_KAYIT").write_text("1\n")
        print(f"ilk kayit: Drive'da {d.ad} yok, bos {d.etiket}la baslaniyor", flush=True)
        return 0
    rc, _, err = rclone("copyto", d.uzak, str(yerel), "-q")
    if rc != 0:
        raise DurumHatasi(f"{d.etiket} listede var ama indirilemedi (rclone copyto rc {rc}): {err.strip()}")
    b = yerel.read_bytes()
    if "Size" in k and int(k["Size"]) != len(b):
        raise DurumHatasi(f"indirilen {d.etiket} boyutu {len(b)} != Drive {k['Size']}")
    v = d.coz(b, f"okunan {d.etiket}")
    (durum / "ONCE").write_bytes(b); (durum / "ILK_KAYIT").unlink(missing_ok=True)
    n = len(v["kayit"]) if d.tur == "csv" else (len(v["ilanlar"]) if d.tur == "json-ilanlar" else len(v))
    print(f"{d.etiket} okundu: {n} {'satir' if d.tur == 'md' else 'kayit'}, sha256 {sha(b)[:12]}", flush=True)
    return 0


def yaz(d, yerel, durum, damga=None):
    if not (durum / "ONCE").exists():
        raise DurumHatasi("okuma adimi tamamlanmamis (ONCE yok); yazma yok")
    once_b, ilk = (durum / "ONCE").read_bytes(), (durum / "ILK_KAYIT").exists()
    yeni_b = yerel.read_bytes() if yerel.exists() else b""
    if d.tur == "onay":                                       # onay: kimlik kaydi yoksa "degismedi" diye basari verilmez
        d.azalmama(d.coz(once_b, "onceki defter"), d.coz(yeni_b, "yeni defter"))
    if yeni_b == once_b or (ilk and d.bos_mu(yeni_b)):
        print(f"{d.etiket} degismedi: yazma yok", flush=True)
        return 0
    yeni = d.coz(yeni_b, f"yeni {d.etiket}")
    if not (ilk and d.bos_mu(once_b)):                        # ilk kayitta csv/md oncesi bos: azalacak kayit yok
        d.azalmama(d.coz(once_b, f"onceki {d.etiket}"), yeni)
    k, yedek_sayi = d.listele()                               # okundugundan beri uzakta degisiklik var mi
    if ilk:
        if k is not None:
            raise DurumHatasi(f"okumada {d.ad} yoktu, simdi var (baska yazici?); yazma yok")
        d.ilk_kayit_kapisi(yedek_sayi)
    else:
        if k is None:
            raise DurumHatasi(f"okumada {d.ad} vardi, simdi yok; yazma yok")
        if sha(d.uzak_oku()) != sha(once_b):
            raise DurumHatasi(f"uzak {d.etiket} okundugundan beri degismis; yazma yok")
        damga = damga or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"_{os.environ.get('GITHUB_RUN_ID', 'yerel')}")
        yedek = f"{d.kok}_{damga}{d.uz}"
        yerel_yedek = durum / yedek
        yerel_yedek.write_bytes(once_b)
        hedef = f"{d.klasor}/{YEDEK_DIR}/{yedek}"
        rc, _, err = rclone("copyto", str(yerel_yedek), hedef, "--immutable", "-q")
        if rc != 0:
            raise DurumHatasi(f"yedek yazilamadi (rc {rc}): {err.strip()}; asil yazma yok")
        rc, out, _ = rclone("cat", hedef)
        if rc != 0 or sha(out) != sha(once_b):
            raise DurumHatasi("yedek geri okumasi tutmadi; asil yazma yok")
        print(f"yedek yazildi: {YEDEK_DIR}/{yedek}", flush=True)
    rc, _, err = rclone("copyto", str(yerel), d.uzak, "-q")
    if rc != 0:
        g_rc, g, _ = rclone("cat", d.uzak)
        durum_ = (f"yeni {d.etiket}" if g_rc == 0 and sha(g) == sha(yeni_b)
                  else (f"onceki {d.etiket}" if g_rc == 0 and sha(g) == sha(once_b) else "bilinmiyor"))
        raise DurumHatasi(f"{d.etiket} yazimi rc {rc} ({err.strip()}); uzaktaki {d.etiket} simdi: {durum_}")
    geri = d.uzak_oku()
    if sha(geri) != sha(yeni_b):
        raise DurumHatasi(f"geri okuma sha256 {sha(geri)[:12]} != yerel {sha(yeni_b)[:12]}")
    budanan = 0 if ilk else d.yedek_buda()
    print(f"{d.etiket} yazildi: geri okuma sha256 {sha(yeni_b)[:12]} ayni" + (f"; {budanan} eski yedek silindi" if budanan else ""), flush=True)
    return 0


def calistir(komut, d, yerel, durum):
    try:
        return oku(d, Path(yerel), Path(durum)) if komut == "oku" else yaz(d, Path(yerel), Path(durum))
    except DurumHatasi as e:
        print(f"::error::{d.ad} {'DEFTERI ' if d.tur == 'onay' else ''}FAIL: {e}", flush=True)
        return 1
    except Exception as e:  # noqa: BLE001 (zaman asimi, rclone yok, dosya hatasi): nedeni annotation'da gorunsun
        print(f"::error::{d.ad} FAIL: beklenmeyen {type(e).__name__}; yazma tamamlanmadi", flush=True)
        return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["oku", "yaz"])
    ap.add_argument("--uzak", required=True, help="uzak dosya (or. gdrive:ASTROLOVE/TEMP/POD_ORDERS_STATE.csv)")
    ap.add_argument("--yerel", required=True)
    ap.add_argument("--durum", required=True, help="okuma anindaki kopya (ONCE) klasoru; dosya basina ayri")
    ap.add_argument("--tur", required=True, choices=sorted(BOS))
    ap.add_argument("--anahtar", default="", help="csv: satir anahtari sutunu")
    ap.add_argument("--kimlik", default="", help="onay: eklenen/guncellenen kayit")
    ap.add_argument("--korunan", default="", help="csv: dolu degeri bosaltilamayan sutunlar (virgullu)")
    ap.add_argument("--ilk-kayit-izni", action="store_true", help="dosya Drive'da yoksa ilk kayda izin ver (yoksa FAIL)")
    a = ap.parse_args(argv)
    if a.tur == "csv" and not a.anahtar:
        ap.error("csv icin --anahtar gerekli")
    if a.tur == "onay" and a.komut == "yaz" and not a.kimlik:
        ap.error("onay yaz icin --kimlik gerekli")
    try:
        d = Dosya(a.uzak, a.tur, a.anahtar, a.kimlik, korunan=[c for c in a.korunan.split(",") if c],
                  ilk_izin=a.ilk_kayit_izni)
    except DurumHatasi as e:
        print(f"::error::FAIL: {e}", flush=True); return 1
    return calistir(a.komut, d, a.yerel, a.durum)


if __name__ == "__main__":
    sys.exit(main())
