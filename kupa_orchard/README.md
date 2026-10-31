# Kupa: Orchard koleksiyonu (The Orchard We Keep)

Kararların tamamı proje belgesinde: `claude/AstroLove_KUPA_ORCHARD_KARARLAR_20261018.md`.
Bu klasör, onaylı Cancer + Libra seti ve zor örneklerle (Capricorn + Sagittarius, Sagittarius + Sagittarius,
Aquarius + Aquarius) birebir aynı çıktıyı veren kod ve varlıklardır (19 Eki 2026 doğrulandı: baskı, galeri, video farkı 0).

## Kullanım

```
bash kod/sembol_al.sh CANCER_LIBRA /tmp/sem_CL
python3 -I kod/cift.py Cancer Libra Emily James "My favorite place is with you" /tmp/sem_CL /tmp/cikti_CL
python3 -I kod/kontrol_burc.py /tmp/cikti_CL Cancer Libra /tmp/sem_CL
```

`cift.py` çıktısı: `baski/` (8 stil 11 oz baskı), `kapak/`, `galeri/` (01-14, GALERI_1_14, MOBIL_400px), `video/` (6 sn),
`olcum.txt`. `kontrol_burc.py` dala 2B mesafeyi gerçek baskı dosyasında ölçer (`kontrol/burc_mesafe.txt`).
Not: `kontrol_burc.py` şu an Maximilian & Josephine ve uzun mesajla ölçer; toplu üretimde ilanın isim ve mesajı verilmelidir.

## Klasörler

- `kod/`: üretim kodu. `kod/kaynak/`: varlıkların nasıl üretildiğini gösteren kaynak betikler (yeniden koşmak gerekmez).
- `varlik/kes/`: onaylı görsellerden kesilmiş süsleme katmanları (8 stil, ön/arka) ve yerleşim.
- `varlik/sahne/`: 8 kapak sahnesi. `varlik/gorunum/`: tek ön/arka, yakın plan, 15 oz sahneleri ve geometrileri.
- `varlik/onayli/`: Serdar'ın onayladığı 8 nihai görsel (kesimin kaynağı). `varlik/font/`: Cinzel, EB Garamond.

## Kurallar

- Sembol kaynağı `kupa-printful-sonuc` dalı yalnız OKUNUR. `printful-kupa-mockup.yml` ve `printful-kupa-tasarim.yml` ÇALIŞTIRILMAZ.
- Burç satırı: hedef 1,95 mm, sığmazsa harf aralığı 0, sonra en az 1,70 mm; dala hedef 1,2 mm (2B).
