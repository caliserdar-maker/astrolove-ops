# EMILY turu 2 (4 Eki): ana sembol kenar tepkisi harflere, A / B / C

Olcum (CANCER_LIBRA ana sembolu, orijinal poster, kenar normal acisina gore):
- Isik yonu sag-ust (~ -45 derece). Sag-uste (ve sol-alta) bakan kenarin 6-10 px bandi yuzden +37..+41 luma parlak.
- Saga / sola bakan kenarda 1-3 px koyu bronz bant: yuzden -20..-31 luma, rgb ~ (167, 111, 13) / (216, 152, 41).
- Kalin cizginin (r 25 px) ic yuzu duz (+-4 luma): ictonal gecis ana sembolde zayif; orijinal ince isimlerde (r 5 px)
  pah yari cizgiyi kapliyor (isik yarisi parlak, karsi yari koyu) -> Canva pahi MUTLAK boyutlu.
Koordinator gozlemi: (1) parlak isik kenari DOGRU, (2) karsi tarafta koyu bronz kenar DOGRU (en belirgin saga / sola
bakan kenarlarda), (3) ic gecis: harf olceginde dogru (mutlak pah), kalin ana sembol cizgisinde zayif.

Yontem (motor/kenar_tepki.py): ana sembolden M(kenardan ic uzaklik px 0-15, disa normal 24 aci) = luma - yuz tablosu
(kapsama RENK doygunlugundan; parlaklik kapsamasi koyu bronzu olcumden dusuruyordu); harfe AYNI px olceginde
uygulanir: L = yuz + guc x M; renk = ana sembolun luma -> RGB tablosu; tane = d4ea867 aktariminin ince detayi.
A = 0.6, B = 1.0 (olculen), C = 1.8. Her satirda cizgiye dik kesit grafigi (isik -45; ana sembol vs harf, px).
Not: C'de M'nin capraz kolunda cizgi ortasinda kesikli sirt dikisi var (normal ortada yon degistiriyor).
