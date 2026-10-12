# Instagram / Facebook / Threads karusel paketi v6 (Serdar onayli tasarim, 12 Eki 2026)

4 slayt, 1080x1350 (4:5), her cift icin: 1 kapak (soru), 2 cevap (birlesik sembol + isimler), 3 duvar sahnesi, 4 yakin plan + "Make it yours / ASTROLOVEART / On Etsy".
Onayli ornekler (Gemini & Leo): `onayli/`. `ig_uret.py` bunlari ortalama 1 seviye fark ile (JPEG) birebir uretir.
lib.py, layouts.py, fontlar ve PosterR `../pin_v6/` klasorunden gelir (iki paket ayni kodu kullanir).

## Calistirma
```
pip install numpy opencv-python-headless pillow scipy
python3 sosyal/ig_v6/ig_uret.py --poster <cift posteri 2000x3000 jpg> --a Gemini --b Leo --out cikti/
```
- `--a` = cift anahtarinda ILK burc (posterde SOL), `--b` = ikinci (SAG). Cift anahtari alfabetik.
- Poster: pin paketiyle ayni 78 poster (9 Eki surumu, Midnight Blue, ORNEK isimli, 2000x3000).
- Uzun burc adi (SAGITTARIUS) yorungede once disa kayar, sigmazsa iki etiket birlikte kuculur; ortadaki sembole ve kenara degmez.

## Kurallar
- Poster pikselleri yalniz kesilir, olceklenir, tasinir. Yapay zeka ile degistirilmez.
- Gorsel yazilarinda cumle sonu nokta yok, "and" yerine "&".

## Toplu uretim + QC (workflow ig-v6)
- `ig_toplu.py --posters <dir> --out <dir> [--pairs ...] [--kontak]`: her cift ayri klasorde 4 slayt, ilerleme sayaci,
  QC PASS/FAIL (PosterR parcalari bulundu, sol/sag burc boyu +-%25, 4 dosya 1080x1350), QC.csv/json, FAIL.txt, KONTAK_IG1.jpg.
- `dogrula.py <dir>`: Gemini & Leo 4 slayti `onayli/` ile ortalama fark (< 2 PASS).
- Workflow `ig-v6` (mod ornek | hepsi): posterler pin-v6'nin Drive TEMP/PIN_V6_20261012/_POSTER2000/ klasorunden (78 sart),
  cikti Drive TEMP/IG_V6_20261012/ORNEK/ ve KARUSEL/<CIFT>/. Yayin yok.
