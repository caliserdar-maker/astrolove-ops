"""Etsy sirlarini GitHub Actions log'unda maskeler.

Kullanim: `python scripts/etsy/mask_secrets.py` (Etsy cagrisi YOK, cikti yalniz
`::add-mask::` satiri). Bir adimda python ciktisi $GITHUB_OUTPUT'a yonlendiriliyorsa
TokenStore'un kendi maskesi log'a ulasmaz; bu betik yonlendirmeden ONCE calistirilir.
"""
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from etsy_common import mask  # noqa: E402

ORTAM = ("ETSY_API_KEY", "ETSY_SHARED_SECRET", "ETSY_REFRESH_TOKEN")
DOSYA = ("refresh_token", "access_token", "shared_secret", "keystring")


def main():
    for ad in ORTAM:
        mask(os.environ.get(ad))
    yol = os.environ.get("TOKEN_FILE") or (sys.argv[1] if len(sys.argv) > 1 else "")
    if yol and pathlib.Path(yol).exists():
        try:
            d = json.loads(pathlib.Path(yol).read_text(encoding="utf-8"))
        except Exception:
            return
        for k in DOSYA:
            mask(d.get(k))


if __name__ == "__main__":
    main()
