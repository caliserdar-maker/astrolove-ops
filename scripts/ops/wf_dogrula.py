#!/usr/bin/env python3
"""Workflow YAML dogrulamasi: YINELENEN ANAHTARI hata sayar.

Neden: PyYAML'in varsayilan SafeLoader'i yinelenen anahtari sessizce son degerle
ezer. 26 Eyl'de bu yuzden gecersiz bir workflow push edildi (ayni adimda iki
`if:`); GitHub dosyayi ayristiramadi ve kosu aninda dustu (kosu 36230580678).
"""
import sys
import yaml


class Kati(yaml.SafeLoader):
    pass


def esle(loader, node, deep=False):
    m = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in m:
            raise yaml.YAMLError(f"YINELENEN ANAHTAR {key!r} (satir {k.start_mark.line + 1})")
        m[key] = loader.construct_object(v, deep=deep)
    return m


Kati.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, esle)


def main(yollar):
    hata = 0
    for y in yollar:
        try:
            with open(y, encoding="utf-8") as f:
                yaml.load(f, Loader=Kati)
            print(f"OK   {y}")
        except yaml.YAMLError as e:
            print(f"HATA {y}: {e}")
            hata += 1
    return 1 if hata else 0


if __name__ == "__main__":
    import glob
    sys.exit(main(sys.argv[1:] or sorted(glob.glob(".github/workflows/*.yml"))))
