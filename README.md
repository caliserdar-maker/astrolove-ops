# astrolove-ops

AstroLove otomasyon scriptleri.

Bu depo, AstroLove icin Etsy, Instagram ve Pinterest tarafindaki tekrarli
islerin otomasyonunu barindirir. Scriptler GitHub Actions workflow'lari
uzerinden veya lokalde elle calistirilabilir.

## Klasor yapisi

| Yol | Icerik |
| --- | --- |
| `scripts/etsy/` | Etsy API scriptleri (listeleme, siparis, envanter) |
| `scripts/instagram/` | Instagram paylasim ve icerik scriptleri |
| `scripts/pinterest/` | Pinterest pin ve board scriptleri |
| `scripts/common/` | Ortak yardimci moduller (auth, http, log) |
| `.github/workflows/` | Zamanlanmis ve manuel GitHub Actions workflow'lari |
| `docs/` | Dokumantasyon |

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Sirlar

Calistirmak icin gereken ortam degiskenleri ve GitHub Secrets listesi
[`docs/SECRETS.md`](docs/SECRETS.md) dosyasindadir. Gercek deger hicbir
zaman depoya yazilmaz.
