#!/usr/bin/env python3
"""Log susgeci (Serdar, 27 Eyl 2026): Drive'a yazilacak her log bundan gecer.

stdin -> stdout: '::add-mask::' iceren satirlar atilir; token/anahtar desenleri '***' olur.
--say: yalniz eslesme sayisini yazar (0 = temiz); cikis kodu 1 = sir benzeri icerik var.
"""
import re
import sys

MASK = "::add-mask::"
DESEN = re.compile(
    r"""(?ix)
    (   (?:access_token|refresh_token|id_token|client_secret|shared_secret|api[_-]?key|x-api-key|
         keystring|password|authorization)["']?\s*[:=]\s*["']?(?:bearer\s+)?
      | bearer\s+
    )
    (?!bearer\b)([^\s"',}*]{6,})
    """)


def suz(satir):
    if MASK in satir:
        return None
    return DESEN.sub(lambda m: m.group(1) + "***", satir)


def say(metin):
    return sum(1 for s in metin.splitlines() if MASK in s) + sum(
        1 for s in metin.splitlines() if MASK not in s for m in DESEN.finditer(s) if m.group(2) != "***")


if __name__ == "__main__":
    veri = sys.stdin.read()
    if "--say" in sys.argv:
        n = say(veri)
        print(n)
        sys.exit(1 if n else 0)
    for s in veri.splitlines(keepends=True):
        t = suz(s)
        if t is not None:
            sys.stdout.write(t)
