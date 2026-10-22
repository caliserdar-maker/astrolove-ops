"""Kart 02 (Choose your format) Digital File aciklamasi: TEK KAYNAK (Serdar 9 Eki: teslim kurali 1 JPG).
Eski (30 Eyl): 'All 5 colors as print-ready PDFs. 300 dpi. Sent' / 'within 24 hours via Etsy Messages.' (2 satir, merkez x 489.5).
Yeni metin: 'One print-ready JPG in your chosen color and size. 300 dpi. Delivered to your Etsy order within 24 hours.'
Eski genislikte (en fazla 759 px, Lato 38) 3 satir; ayni merkez (dijital yigin ekseni), ayni satir araligi (45 px), ayni renk."""
FONT, PUNTO, MERKEZ_X, RENK = 'Lato-Regular.ttf', 38, 489.5, (37, 44, 57)
ESKI = [('All 5 colors as print-ready PDFs. 300 dpi. Sent', 1558, 108, (37, 44, 57)), ('within 24 hours via Etsy Messages.', 1603, 200, (37, 45, 56))]  # 30 Eyl, birebir
YENI = [('One print-ready JPG in your chosen color', 1558, None, RENK), ('and size. 300 dpi. Delivered to your', 1603, None, RENK),
        ('Etsy order within 24 hours.', 1648, None, RENK)]
TAM_METIN = 'One print-ready JPG in your chosen color and size. 300 dpi. Delivered to your Etsy order within 24 hours.'
assert ' '.join(t[0] for t in YENI) == TAM_METIN
assert not any(ch in TAM_METIN for ch in '—–')        # uzun/orta tire yok


def ciz(d, D, fd, satirlar, duvar_lum, yazi_rengi, ImageFont, os):
    """satirlari D (duvar) uzerine ortali basar; [(metin, kutu, renk)] dondurur (kart02_duvar_kur ile ayni renk kurali)."""
    f = ImageFont.truetype(os.path.join(fd, FONT), PUNTO); out = []
    for t, y, x, renk in satirlar:
        b = f.getbbox(t, anchor='ls')
        if x is None: x = round(MERKEZ_X - (b[0] + b[2]) / 2)
        kutu = (x + b[0], y + b[1], x + b[2], y + b[3]); r = yazi_rengi(renk, duvar_lum(D, kutu))
        d.text((x, y), t, font=f, fill=r, anchor='ls'); out.append((t, kutu, r))
    return out
