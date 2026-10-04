# EMILY tek kesit (Serdar 4 Eki, yontem degisti: dokuyu formulle taklit etme, ana sembolun gercek malzemesini aktar)

Kaynak: docs/MOTOR_ENVANTER.md #9 "Altin efekt: DOSYA (Canva efekti degil)"; ana sembol Canva'dan altin disa aktarilmis
PNG main_symbols/cancer_libra_gold.png (sha256 e5a0b5801a5c0c3ed5d4bcf97c499b7d53162968e96bdd990e8adeaff8920261).
Ayri dolgu gorseli / kabartma ayari YOK -> doku ana sembolun kendi piksellerinden.

Yontem (motor/doku_aktar.py, parametrik model yok): sayfadaki ana sembol pikselleri zeminden ayrilir, cizgi yaricapi
EMILY'ye esitlenecek sekilde olceklenir (24 -> 11 px, 0.459); rehberli PatchMatch (7x7 yama, rehber = goreli derinlik +
kenar yonu, renk tutarliligi) ile EMILY maskesine ana sembol yamalari kopyalanir, ortusen yamalar oylanir.
Deneme 1 (piksel bazli kopya) taneyi kirpik parilti gurultusune ceviriyordu; bu kesit deneme 2.
Prototip: yalniz EMILY (isim1) degisti; diger ogeler 862f815 ile ayni. Serdar "ayni" demeden diger ogelere gecilmez.
