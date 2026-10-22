# GOREV 1 - Workflow guvenlik yamasi: test raporu

Branch: `claude/wf-hardening` (main'e push EDILMEDI).
Yama: 114 workflow'a `permissions: contents: read` + 2 workflow'a `etsy-token` concurrency.
`git apply --check`: **PASS**. Toplam degisiklik: 114 dosya, 350 satir eklendi, 0 satir silindi.

## Test sonuclari

| test | sonuc | detay |
|---|---|---|
| YAML ayristirma (121 workflow) | **PASS** | hepsi gecerli |
| bash -n tum run bloklari | **PASS** | hepsi gecerli |
| permissions blogu kapsami | **PASS** | 121/121 |
| read-only varsayilan (yamanin hedefi) | **PASS** | 120 workflow contents: read |
| write-all kullanan yok | **PASS** |  |
| GITHUB_TOKEN ile yazma yapan workflow yok (yama guvenli) | **PASS** | yok |
| PAT (OPS_ADMIN_TOKEN) kullananlar yamadan etkilenmez | **PASS** | repo-public.yml, ig-media-sync.yml -> PAT GITHUB_TOKEN izninden bagimsiz |
| secret DOGRUDAN echo edilmiyor (satir bazli) | **PASS** | 0 satir; GITHUB_ENV'e yazma GitHub'in standart yontemi, log degil |
| secret maskeleme zinciri (betik dahil) | **FAIL** | ['.github/workflows/pod-hero-batch.yml', '.github/workflows/pod-hero-crop.yml'] |
| Etsy workflow'larinda concurrency (51) | **FAIL** | ['.github/workflows/pod-hero-batch.yml', '.github/workflows/wp-audit-close.yml'] |
| Etsy kosusu ortada iptal edilmiyor | **PASS** |  |
| Drive token geri yazma | **PASS** | 51/51 |
| kosu sonunda token temizligi | **PASS** | 51/51 |
| guvenli durma (set -euo pipefail) | **PASS** | 120/121 |
| canli yazan workflow'larda ikinci kapi | **FAIL** | 13/18 |

## Duzeltilen yanlis pozitifler

Ilk kosuda 4 FAIL vardi; ikisi testin kendi kusuruydu:
- **secret echo (26 workflow)**: kural `env:` blogundaki `${{ secrets.X }}` ile ilerideki
  `echo` satirini ayni dosyada gorup esliyordu. Gercek satir
  `echo "RCLONE_CONFIG_...=$GOOGLE_CLIENT_SECRET" >> "$GITHUB_ENV"` - bu loga degil
  `$GITHUB_ENV` dosyasina yazar ve GitHub'in standart yontemidir. Satir bazli kontrolde
  **0 eslesme**.
- **maskeleme izi**: workflow'un cagirdigi betik `etsy_common.mask()` kullaniyorsa yeterli;
  kural yalniz workflow metnine bakiyordu.

## Yamanin kapsami disinda kalan GERCEK bulgular

| bulgu | workflow | oneri |
|---|---|---|
| mask() zinciri yok | pod-hero-batch.yml, pod-hero-crop.yml | betikler `scripts/pod/*` cagiriyor; ETSY_API_KEY tasiyorlarsa `mask()` eklenmeli |
| canli yazmada ikinci kapi yok | 18 workflow'un 5'i | `confirm=CANLI` kapisi pod-seo-update.yml ornek alinarak eklenmeli |

## Yamanin guvenligi

- `secrets.GITHUB_TOKEN` ile yazma yapan (PR acan, push eden, release yukleyen)
  workflow **yok** -> `contents: read` hicbir isi kirmaz.
- `repo-public.yml` ve `ig-media-sync.yml` **OPS_ADMIN_TOKEN (PAT)** kullaniyor;
  PAT izinleri `permissions:` blogundan bagimsizdir, etkilenmezler.
- 121/121 workflow YAML ve `bash -n` temiz.

## Uygulama

```
git fetch origin claude/wf-hardening
git checkout main && git merge --ff-only origin/claude/wf-hardening   # onay sonrasi
```

