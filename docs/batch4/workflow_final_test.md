# BATCH 4 GOREV 1 - Workflow sertlestirme: son test raporu

Branch: `claude/wf-hardening` - **main'e merge EDILDI: 163e5ad** (16 Eyl 2026).
Test takimi: `scripts/night2/wf_test.py` (salt okur; GitHub/Etsy/Drive cagrisi yok).
Kosu: `python scripts/night2/wf_test.py`

## Sonuc: 16/16 PASS

| test | sonuc | detay |
|---|---|---|
| YAML ayristirma (122 workflow) | **PASS** | hepsi gecerli |
| bash -n tum run bloklari | **PASS** | hepsi gecerli |
| permissions blogu kapsami | **PASS** | 122/122 |
| read-only varsayilan (contents: read) | **PASS** | 122/122 |
| write-all kullanan yok | **PASS** |  |
| GITHUB_TOKEN ile yazma yapan workflow yok | **PASS** | yok |
| PAT kullananlar permissions yamasindan bagimsiz | **PASS** | ig-media-sync.yml, repo-public.yml |
| secret dogrudan echo edilmiyor | **PASS** | 0 satir |
| secret maskeleme zinciri (52 Etsy workflow) | **PASS** | hepsi maskeli |
| Etsy workflow'larinda etsy-token concurrency (52) | **PASS** | hepsi var |
| Etsy kosusu ortada iptal edilmiyor | **PASS** | yok |
| Drive token geri yazma (52) | **PASS** | hepsi var |
| kosu sonunda token temizligi (52) | **PASS** | hepsi var |
| guvenli durma (set -e / bilincli set +e) | **PASS** | 122/122 |
| canli yazan workflow'larda ikinci kapi (18) | **PASS** | 18/18 |
| GITHUB_OUTPUT yonlendirmesinde maske kaybi yok | **PASS** | yok |

## Batch 3'te acik kalan 3 bulgunun cozumu

**1) mask() zinciri yok - pod-hero-batch.yml, pod-hero-crop.yml**
Kok neden iki ayri kusurdu, ikisi de gercek:
- `pod_crop_batch.py` Etsy islerini alt surecte (`pod_hero_swap.py`) kosuyor ve
  ciktinin **yalniz son 2500 karakterini** log'a basiyor. Alt surecin `::add-mask::`
  satirlari cikti basinda uretildigi icin kirpmada kayboluyordu; maskeyi almayan log'a
  sonraki satirlar maskesiz dusuyordu. Cozum: `sirlari_maskele()` - maske **ust
  surecte**, alt surec baslamadan once kaydediliyor.
- `pod-hero-crop.yml` icindeki python blogunun stdout'u `$GITHUB_OUTPUT`'a
  yonlendirilmis; `TokenStore`'un kendi maskesi log'a degil cikti dosyasina gidiyordu
  (ustelik gecersiz satir olarak). Cozum: yonlendirmeden **once**
  `python scripts/etsy/mask_secrets.py` calisiyor.
- Ek sertlestirme: `TokenStore.__init__` artik yalniz token dosyasindaki degerleri
  degil, **ortamdan gelen** `keystring`/`shared_secret` degerlerini de maskeliyor.
  Bu, TokenStore kuran her betigi tek noktadan kapsiyor.
- Yeni regresyon testi (16): `$GITHUB_OUTPUT`'a yonlendirilen blokta `TokenStore`
  varsa ve `mask_secrets.py` cagrilmiyorsa FAIL.

**2) Etsy workflow'larinda concurrency**
Batch 3'te FAIL goruen `wp-full-chain.yml` gercekte **is (job) duzeyinde**
`concurrency: etsy-token` tasiyor (Etsy'ye yazan tek is: `upload_verify`).
Testin kendi kusuruydu: yalniz workflow duzeyine bakiyordu. Kural duzeltildi;
52/52 Etsy workflow'u kilitli.

**3) Canli yazan workflow'larda ikinci kapi**
Batch 3'teki "13/18" rakami yanlisti: kural `echo "::warning::APPLY..."` satirini
kapi sayiyordu. Uyari kapi degildir - kosuyu durdurmaz. Gercek durum **1/18**'di
(yalniz `pod-seo-update.yml`). 17 workflow'a `confirm` girdisi + ilk adim olarak
`Onay kapisi` eklendi; `apply=true` ve `confirm != CANLI` ise kosu **exit 1** ile durur.
Kapi davranisi bash ile dogrulandi:

| apply | confirm | sonuc |
|---|---|---|
| true | (bos) | DURUR |
| true | `canli` (kucuk harf) | DURUR |
| true | `CANLI` | gecer |
| false | (bos) | gecer (kuru deneme) |

**Cron muafiyeti:** `digital-desc-batch.yml` zamanlanmis kosuda (`0 */4 * * *`)
APPLY=true calisir ve bu kosu Mo tarafindan onaylidir. Kapi
`github.event_name == 'schedule'` ise muaf tutulur; elle tetiklenen `apply=true`
yine `CANLI` ister. Dogrulandi: schedule -> gecer, workflow_dispatch+apply -> durur.

## Kalan bulgular

Kod tarafinda kalan FAIL **yok**. Merge tamamlandi ve yerel/uzak `main`
`163e5ad` commit'inde dogrulandi.

- Merge sonrasi davranis degisikligi: **17 workflow'da `apply=true` artik tek
  basina yetmez**, `confirm=CANLI` de girilmelidir. Zamanlanmis digital-desc kosusu
  etkilenmez.
