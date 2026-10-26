#!/usr/bin/env python3
"""YEREL TEST ICIN sahte rclone (gdrive:<yol> -> $FAKE_ROOT/<yol>). Gercek Drive'a dokunmaz.
Komutlar: lsjson [-R] [--max-depth N] [--files-only] [--include KALIP]..., cat, copyto [--immutable], deletefile.
Hata enjeksiyonu ($FAKE_HATA, virgullu): lsjson, lsjson_bos, lsjson_bos_ana (ana dosya listeden duser), lsjson_cift,
cat, cat_bozuk_sonra (ana dosyaya yazimdan sonraki cat farkli icerik), copyto_indir, copyto_yedek, copyto_ana,
deletefile. Ana dosya adi $FAKE_ANA (varsayilan ONAYLAR.json)."""
import fnmatch
import json
import os
import shutil
import sys
from pathlib import Path

kok = Path(os.environ["FAKE_ROOT"])
hata = set(filter(None, os.environ.get("FAKE_HATA", "").split(",")))
ana = os.environ.get("FAKE_ANA", "ONAYLAR.json")


def yol(p):
    return kok / p[len("gdrive:"):] if p.startswith("gdrive:") else Path(p)


def secenek(a, ad, vars_=None):
    return a[a.index(ad) + 1] if ad in a else vars_


a = sys.argv[1:]
k = a[0]
if k == "lsjson":
    if "lsjson" in hata:
        sys.stderr.write("sahte ag hatasi"); sys.exit(3)
    d = yol(a[1])
    if not d.is_dir():
        sys.stderr.write("directory not found"); sys.exit(3)
    if "--dirs-only" in a:
        print(json.dumps([{"Path": f.name, "Name": f.name, "IsDir": True} for f in sorted(d.iterdir()) if f.is_dir()]))
        sys.exit(0)
    rek, derin = "-R" in a, int(secenek(a, "--max-depth", "1"))
    kalip = [a[i + 1].lstrip("/") for i, x in enumerate(a) if x == "--include"]
    L = []
    for f in sorted(d.rglob("*") if rek else d.iterdir()):
        if not f.is_file():
            continue
        r = f.relative_to(d).as_posix()
        if r.count("/") + 1 > derin:
            continue
        if kalip and not any(fnmatch.fnmatchcase(r, p) for p in kalip):
            continue
        L.append({"Path": r, "Name": f.name, "Size": f.stat().st_size})
    if "lsjson_bos" in hata:
        L = []
    if "lsjson_bos_ana" in hata:
        L = [x for x in L if x["Path"] != ana]
    if "lsjson_cift" in hata:
        L += [x for x in L if x["Path"] == ana]
    print(json.dumps(L))
elif k == "cat":
    p = yol(a[1])
    if "cat" in hata or not p.is_file():
        sys.exit(3)
    b = p.read_bytes()
    if "cat_bozuk_sonra" in hata and p.name == ana and (kok / ".yazildi").exists():
        b += b" "
    sys.stdout.buffer.write(b)
elif k == "copyto":
    s, h = yol(a[1]), yol(a[2])
    if "copyto_indir" in hata and a[1].startswith("gdrive:"):
        sys.exit(1)
    if "copyto_yedek" in hata and "/YEDEK/" in a[2]:
        sys.exit(1)
    if "copyto_ana" in hata and a[2].startswith("gdrive:") and a[2].endswith("/" + ana):
        sys.exit(1)
    if "--immutable" in a and h.exists() and h.read_bytes() != s.read_bytes():
        sys.stderr.write("immutable: hedef var ve farkli"); sys.exit(1)
    h.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(s, h)
    if a[2].startswith("gdrive:") and a[2].endswith("/" + ana):
        (kok / ".yazildi").touch()
elif k == "deletefile":
    if "deletefile" in hata:
        sys.exit(1)
    p = yol(a[1])
    if not p.is_file():
        sys.exit(3)
    p.unlink()
else:
    sys.exit(9)
