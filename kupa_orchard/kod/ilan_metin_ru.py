#!/usr/bin/env python3
"""Orchard kupa 78 ilan RU katmani (Etsy listing translation, language=ru). Kaynak: ChatGPT cevirisi 19 Eki 2026,
Claude kontrolu: burc adlari POD_LISTING_TEMPLATE B59 haritasiyla ayni; madde isaretleri EN metindeki gibi "- ".
Etiketlerde "ё" yerine "е" (aramada yaygin yazim). Cikti: kupa_orchard/ilan/KUPA78_ORCHARD_METIN_RU.csv
Sutunlar: kod, baslik, baslik_kr, etiketler, aciklama.
Kontroller (biri bile FAIL ise CSV yazilmaz): baslik <= 140, 13 tekrarsiz etiket <= 20, uzun/orta tire yok,
"Lena" ve "Serdar" yok, yer tutucu kalmamis, 78 cift.
Kullanim: python3 -I ilan_metin_ru.py"""
import csv, itertools, os, re, sys

KOK = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
CIKTI = os.path.join(KOK, 'ilan', 'KUPA78_ORCHARD_METIN_RU.csv')
Z = ['ARIES', 'TAURUS', 'GEMINI', 'CANCER', 'LEO', 'VIRGO', 'LIBRA', 'SCORPIO', 'SAGITTARIUS', 'CAPRICORN', 'AQUARIUS', 'PISCES']
CIFTLER = sorted('_'.join(sorted(p)) for p in itertools.combinations_with_replacement(Z, 2))
RU = {'ARIES': 'Овен', 'TAURUS': 'Телец', 'GEMINI': 'Близнецы', 'CANCER': 'Рак', 'LEO': 'Лев', 'VIRGO': 'Дева',
      'LIBRA': 'Весы', 'SCORPIO': 'Скорпион', 'SAGITTARIUS': 'Стрелец', 'CAPRICORN': 'Козерог', 'AQUARIUS': 'Водолей',
      'PISCES': 'Рыбы'}

BASLIK = '{B1} и {B2}: кружка с именами и символами зодиака, подарок для пары'
ETIKET = ['именная кружка', 'кружка для пары', 'кружка на заказ', 'кружка с именами', 'подарок для пары',
          'подарок молодоженам', 'зодиакальная кружка', 'символы зодиака', 'зодиакальный подарок', 'астрология',
          'кружка с назаром', 'подарок на помолвку']
YEDEK_ILK = 'знаки зодиака'
ISIM_SATIRI = {
    'farkli': '1. Имя человека со знаком «{B1}» (до 10 букв)\n2. Имя человека со знаком «{B2}» (до 10 букв)',
    'ayni': '1. Имя слева (до 10 букв)\n2. Имя справа (до 10 букв)',
}
ACIKLAMA = """Именная кружка для пары со знаками зодиака «{B1}» и «{B2}»: мы объединяем ваши два знака в один оригинальный символ и добавляем ваши имена и личную надпись. Кофейная кружка на заказ и персональный подарок, созданный для вас двоих.

[ ПОДАРОК ДЛЯ ПАРЫ ]
Подарок на свадьбу или помолвку для пары, которая любит астрологию, сюрприз на годовщину или подарок молодожёнам. Зодиакальный подарок для ваших утренних ритуалов.

[ ЧТО ВЫ ПОЛУЧИТЕ ]
Одну кружку с печатью с двух сторон. На первом фото показаны её лицевая и обратная стороны.
Лицевая сторона: объединённый символ, два небольших знака зодиака, ваши имена заглавными буквами, соединённые знаком ∞, и названия ваших знаков зодиака.
Обратная сторона: ваша надпись курсивом, ваши имена и небольшое изображение назара (турецкого глаза).

[ 8 СТИЛЕЙ: THE ORCHARD WE KEEP ]
Orange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, Lemon Grove, Blue Grape или Golden Loquat. Во всех стилях мы используем один и тот же символ для пары «{B1} и {B2}» и изображение назара на обратной стороне. Смотрите фото 4.

[ ДВА РАЗМЕРА ]
- 11 oz (325 мл)
- 15 oz (444 мл)
Одинаковый дизайн в обоих размерах. Смотрите фото 5.

[ КАК ПЕРСОНАЛИЗИРОВАТЬ ]
Укажите данные в поле персонализации на трёх отдельных строках:
{ISIM_SATIRI}
3. Надпись (одна строка, до 30 символов, включая пробелы и знаки препинания)
Если вы оставите поле для надписи пустым, мы напечатаем:
My favorite place is with you
Пожалуйста, проверьте правильность написания перед оформлением заказа. Смотрите фото 3 и 6.

[ ХАРАКТЕРИСТИКИ ]
- Глянцевая белая керамика, белая внутренняя поверхность
- Можно мыть в посудомоечной машине и использовать в микроволновой печи
- Изготавливаем на заказ специально для вас
- Оригинальные объединённые символы зодиака от AstroLoveArt

[ ВОЗВРАТ И ОБМЕН ]
Каждую кружку мы персонализируем, поэтому не принимаем возврат или обмен, если вы передумали. Если кружка пришла повреждённой, пришлите нам фото в течение 7 дней с момента получения, и мы бесплатно отправим замену.

Есть вопросы? Напишите нам, будем рады помочь."""

satirlar, hatalar = [], []
for i, kod in enumerate(CIFTLER, 1):
    k1, k2 = kod.split('_')
    b1, b2 = RU[k1], RU[k2]
    tur = 'ayni' if k1 == k2 else 'farkli'
    baslik = BASLIK.format(B1=b1, B2=b2)
    ilk = f'{b1.lower()} и {b2.lower()}'
    if len(ilk) > 20:
        ilk = YEDEK_ILK
    etiket = [ilk] + ETIKET
    aciklama = ACIKLAMA.replace('{ISIM_SATIRI}', ISIM_SATIRI[tur]).format(B1=b1, B2=b2)
    tum = baslik + ' ' + ' '.join(etiket) + ' ' + aciklama
    if len(baslik) > 140:
        hatalar.append(f'{kod}: baslik {len(baslik)} > 140')
    if len(etiket) != 13 or len(set(etiket)) != 13 or any(len(e) > 20 for e in etiket):
        hatalar.append(f'{kod}: etiket {etiket}')
    if re.search('[–—]', tum):
        hatalar.append(f'{kod}: uzun/orta tire')
    if re.search(r'lena|serdar', tum, re.I):
        hatalar.append(f'{kod}: isim (Lena/Serdar) var')
    if re.search(r'[{}]', tum):
        hatalar.append(f'{kod}: yer tutucu kalmis')
    satirlar.append({'kod': kod, 'baslik': baslik, 'baslik_kr': len(baslik), 'etiketler': ', '.join(etiket),
                     'aciklama': aciklama})
    if i % 13 == 0 or i == len(CIFTLER):
        print(f'[{i}/{len(CIFTLER)} %{100 * i // len(CIFTLER)}] {kod}', flush=True)

if len(satirlar) != 78:
    hatalar.append(f'cift sayisi {len(satirlar)} != 78')
if hatalar:
    print('FAIL', len(hatalar)); print('\n'.join(hatalar))
    sys.exit(1)
os.makedirs(os.path.dirname(CIKTI), exist_ok=True)
with open(CIKTI, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(satirlar[0]))
    w.writeheader()
    w.writerows(satirlar)
yedek = sum(r['etiketler'].startswith(YEDEK_ILK) for r in satirlar)
print('PASS', len(satirlar), 'ilan | en uzun baslik', max(r['baslik_kr'] for r in satirlar), '| en uzun ilk etiket',
      max(len(r['etiketler'].split(', ')[0]) for r in satirlar), '| yedek ilk etiket', yedek,
      '| en uzun aciklama', max(len(r['aciklama']) for r in satirlar), '->', CIKTI)
