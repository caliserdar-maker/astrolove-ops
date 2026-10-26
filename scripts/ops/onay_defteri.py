#!/usr/bin/env python3
"""Siparis onay defteri (ONAYLAR.json) okuma/yazma kapilari (26 Eki 2026, Serdar onayi).

Sorun: siparis-onay-yaz okuma hatasinda bos defterle devam edip onu Drive'a geri yaziyordu (tum onaylar silinir).
  oku: rclone lsjson ile dosya aranir. Listeleme hatasi -> FAIL. Dosya varsa copyto ZORUNLU basarili, boyut
       listeyle ayni ve icerik JSON nesnesi olmali; degilse FAIL. Dosya yoksa (ilk kayit) bos defter, logda "ilk kayit";
       ama klasorde ONAYLAR_YEDEK_* varsa ya da dosya dogrudan okunabiliyorsa (liste/filtre hatasi) FAIL.
       Okunan hal <durum>/ONCE.json (+ ILK_KAYIT isareti) olarak saklanir.
  yaz: (1) azalmama: yeni defter = onceki + bu kimlik (ekleme ya da ayni kimligin guncellenmesi); diger kayitlar
       birebir ayni. (2) uzaktaki defter okundugundan beri degismemis olmali (sha256). (3) yedek: onceki defter
       ONAYLAR_YEDEK_<UTC damga>.json olarak ayni klasore yazilir ve geri okunur; yazilamazsa asil yazma yok.
       (4) yazim + geri okuma: uzak sha256 = yerel sha256.
Her FAIL cikis 1 ve Drive'a hicbir sey yazilmaz (yedekten sonraki adimlarda yalniz yedek kalir).
rclone komutu RCLONE ortam degiskeniyle degistirilebilir (yerel test: sahte rclone)."""
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AD = "ONAYLAR.json"


class DefterHatasi(Exception):
    pass


def rclone(*args, girdi=None):
    komut = shlex.split(os.environ.get("RCLONE", "rclone")) + list(args)
    r = subprocess.run(komut, capture_output=True, input=girdi, timeout=120)
    return r.returncode, r.stdout, r.stderr.decode("utf-8", "replace")[-300:]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def nesne(b, ne):
    try:
        v = json.loads(b.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise DefterHatasi(f"{ne} gecerli JSON degil ({type(e).__name__})") from e
    if not isinstance(v, dict):
        raise DefterHatasi(f"{ne} JSON nesnesi degil ({type(v).__name__})")
    return v


def listele(uzak):
    """Kokteki ONAYLAR*.json (defter + yedekler). Donus: (defter kaydi ya da None, yedek sayisi)."""
    rc, out, err = rclone("lsjson", uzak, "--files-only", "--max-depth", "1", "--include", "/ONAYLAR*.json")
    if rc != 0:
        raise DefterHatasi(f"listeleme hatasi (rclone lsjson rc {rc}): {err.strip()}")
    try:
        hepsi = json.loads(out.decode("utf-8") or "[]")
        kayitlar = [k for k in hepsi if k.get("Name") == AD]
        yedek = sum(1 for k in hepsi if str(k.get("Name", "")).startswith("ONAYLAR_YEDEK_"))
    except (ValueError, AttributeError) as e:
        raise DefterHatasi("listeleme ciktisi okunamadi") from e
    if len(kayitlar) > 1:
        raise DefterHatasi(f"Drive'da {len(kayitlar)} adet {AD} var (belirsiz)")
    return (kayitlar[0] if kayitlar else None), yedek


def ilk_kayit_kapisi(uzak, yedek):
    """Liste bos dondu: ilk kayit yalniz defter gercekten hic olmadiysa (yedek yok) ve dogrudan okuma da basarisizsa."""
    if yedek:
        raise DefterHatasi(f"{AD} listede yok ama {yedek} yedek var: defter daha once vardi, ilk kayit sayilmaz; yazma yok")
    rc, out, _ = rclone("cat", f"{uzak}/{AD}")
    if rc == 0:
        raise DefterHatasi(f"{AD} listede yok ama dogrudan okunabiliyor (liste/filtre hatasi); yazma yok")


def uzak_oku(uzak):
    rc, out, err = rclone("cat", f"{uzak}/{AD}")
    if rc != 0:
        raise DefterHatasi(f"uzak defter okunamadi (rclone cat rc {rc}): {err.strip()}")
    return out


def oku(uzak, dizin, durum):
    dizin.mkdir(parents=True, exist_ok=True); durum.mkdir(parents=True, exist_ok=True)
    k, yedek = listele(uzak)
    if k is None:
        ilk_kayit_kapisi(uzak, yedek)
        (dizin / AD).write_bytes(b"{}\n")
        (durum / "ONCE.json").write_bytes(b"{}\n")
        (durum / "ILK_KAYIT").write_text("1\n")
        print(f"ilk kayit: Drive'da {AD} yok, bos defterle baslaniyor", flush=True)
        return 0
    rc, _, err = rclone("copyto", f"{uzak}/{AD}", str(dizin / AD), "-q")
    if rc != 0:
        raise DefterHatasi(f"defter listede var ama indirilemedi (rclone copyto rc {rc}): {err.strip()}")
    b = (dizin / AD).read_bytes()
    if "Size" in k and int(k["Size"]) != len(b):
        raise DefterHatasi(f"indirilen defter boyutu {len(b)} != Drive {k['Size']}")
    v = nesne(b, "okunan defter")
    (durum / "ONCE.json").write_bytes(b)
    (durum / "ILK_KAYIT").unlink(missing_ok=True)
    print(f"defter okundu: {len(v)} kayit, sha256 {sha(b)[:12]}", flush=True)
    return 0


def azalmama(once, sonra, kimlik):
    if kimlik not in sonra:
        raise DefterHatasi("yeni defterde bu kimligin kaydi yok")
    beklenen = len(once) + (0 if kimlik in once else 1)
    if len(sonra) != beklenen:
        raise DefterHatasi(f"kayit sayisi {len(sonra)} != beklenen {beklenen} (once {len(once)})")
    eksik = [k for k in once if k not in sonra]
    degisen = [k for k in once if k != kimlik and k in sonra and sonra[k] != once[k]]
    fazla = [k for k in sonra if k not in once and k != kimlik]
    if eksik or degisen or fazla:
        raise DefterHatasi(f"onceki kayitlar korunmadi: silinen {len(eksik)} degisen {len(degisen)} fazla {len(fazla)} kayit")


def yaz(uzak, dizin, durum, kimlik, damga=None):
    once_b = (durum / "ONCE.json").read_bytes()
    ilk = (durum / "ILK_KAYIT").exists()
    once = nesne(once_b, "onceki defter")
    yeni_b = (dizin / AD).read_bytes()
    yeni = nesne(yeni_b, "yeni defter")
    azalmama(once, yeni, kimlik)
    k, yedek_sayi = listele(uzak)                             # okundugundan beri uzakta degisiklik var mi
    if ilk:
        if k is not None:
            raise DefterHatasi(f"okumada {AD} yoktu, simdi var (baska yazici?); yazma yok")
        ilk_kayit_kapisi(uzak, yedek_sayi)
    else:
        if k is None:
            raise DefterHatasi(f"okumada {AD} vardi, simdi yok; yazma yok")
        if sha(uzak_oku(uzak)) != sha(once_b):
            raise DefterHatasi("uzak defter okundugundan beri degismis; yazma yok")
        damga = damga or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + f"_{os.environ.get('GITHUB_RUN_ID', 'yerel')}")
        yedek = f"ONAYLAR_YEDEK_{damga}.json"
        yerel_yedek = durum / yedek
        yerel_yedek.write_bytes(once_b)
        rc, _, err = rclone("copyto", str(yerel_yedek), f"{uzak}/{yedek}", "--immutable", "-q")
        if rc != 0:
            raise DefterHatasi(f"yedek yazilamadi (rc {rc}): {err.strip()}; asil yazma yok")
        rc, out, err = rclone("cat", f"{uzak}/{yedek}")
        if rc != 0 or sha(out) != sha(once_b):
            raise DefterHatasi("yedek geri okumasi tutmadi; asil yazma yok")
        print(f"yedek yazildi: {yedek} ({len(once)} kayit)", flush=True)
    rc, _, err = rclone("copyto", str(dizin / AD), f"{uzak}/{AD}", "-q")
    if rc != 0:
        g_rc, g, _ = rclone("cat", f"{uzak}/{AD}")
        durum_ = "yeni defter" if g_rc == 0 and sha(g) == sha(yeni_b) else ("onceki defter" if g_rc == 0 and sha(g) == sha(once_b) else "bilinmiyor")
        raise DefterHatasi(f"defter yazimi rc {rc} ({err.strip()}); uzaktaki defter simdi: {durum_}")
    geri = uzak_oku(uzak)
    if sha(geri) != sha(yeni_b):
        raise DefterHatasi(f"geri okuma sha256 {sha(geri)[:12]} != yerel {sha(yeni_b)[:12]}")
    print(f"defter yazildi: {len(once)} -> {len(yeni)} kayit, geri okuma sha256 {sha(yeni_b)[:12]} ayni", flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komut", choices=["oku", "yaz"])
    ap.add_argument("--uzak", required=True, help="defter klasoru (or. gdrive:ASTROLOVE/TEMP/SIPARIS_ONAY)")
    ap.add_argument("--dizin", required=True, help="yerel defter klasoru (ONAYLAR.json burada)")
    ap.add_argument("--durum", required=True, help="okuma anindaki defter kopyasi (ONCE.json) klasoru")
    ap.add_argument("--kimlik", default="")
    a = ap.parse_args(argv)
    try:
        if a.komut == "oku":
            return oku(a.uzak, Path(a.dizin), Path(a.durum))
        if not a.kimlik:
            raise DefterHatasi("yaz icin --kimlik gerekli")
        return yaz(a.uzak, Path(a.dizin), Path(a.durum), a.kimlik)
    except DefterHatasi as e:
        print(f"::error::ONAY DEFTERI FAIL: {e}", flush=True)
        return 1
    except Exception as e:  # noqa: BLE001 (zaman asimi, rclone yok, dosya hatasi): nedeni annotation'da gorunsun
        print(f"::error::ONAY DEFTERI FAIL: beklenmeyen {type(e).__name__}; yazma tamamlanmadi", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
