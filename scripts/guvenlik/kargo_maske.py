#!/usr/bin/env python3
"""Kargo maskesi (Serdar, 28 Eyl 2026): loga giden metinde kargo takip numarasi ve Prodigi siparis kimligi
yalniz son 4 hanesiyle kalir. Drive'a yazilan dosyalar (STATE, TAKIP_DENETIM.json, REPORT.md) tam kalir.

Desenler:
- Prodigi siparis: ord_<rakam>                                   -> ord_***1234
- UPS: 1Z + 16 alfanumerik                                         -> ***1234
- UPU S10 (LX104881201NL gibi): 2 harf + 9 rakam + 2 harf          -> ***01NL
- En az 12 haneli rakam dizisi (USPS IMpb, FedEx, 420+ZIP onekli)  -> ***1234
- Buyuk harf + rakam karisik, 12+ karakter, en az 8 rakam (PRO0560NL26629002201 gibi) -> ***2201
Takip linklerindeki numara da ayni desenle maskelenir. Etsy receipt (10 hane) bu modulun isi degildir.
"""
import re
import sys

_ORD = re.compile(r"\bord_(\d+)")
_TAKIP = re.compile(
    r"""(?x)
    (?<![A-Za-z0-9])
    (   1Z[0-9A-Z]{16}
      | [A-Z]{2}\d{9}[A-Z]{2}
      | \d{12,}
      | (?=[A-Z0-9]{12,}(?![A-Za-z0-9]))(?=(?:[A-Z]*\d){8})(?=\d*[A-Z])[A-Z0-9]{12,}
    )
    (?![A-Za-z0-9])
    """)


def son4(s):
    return "***" + s[-4:]


def _satir(s):
    if s.lstrip().startswith("::add-mask::"):          # GitHub maskesinin degeri degismemeli
        return s
    s = _ORD.sub(lambda m: "ord_" + son4(m.group(1)), s)
    return _TAKIP.sub(lambda m: son4(m.group(1)), s)


def maskele(metin):
    return "".join(_satir(s) for s in metin.splitlines(keepends=True))


class MaskeliAkis:
    """sys.stdout / sys.stderr sarmalayicisi: yazilan her metin maskele()'den gecer."""
    def __init__(self, akis, ek=None):
        self._a = akis
        self._ek = ek

    def write(self, t):
        t = maskele(t)
        return self._a.write(self._ek(t) if self._ek else t)

    def flush(self):
        return self._a.flush()

    def __getattr__(self, ad):
        return getattr(self._a, ad)


if __name__ == "__main__":
    for s in sys.stdin:
        sys.stdout.write(maskele(s))
