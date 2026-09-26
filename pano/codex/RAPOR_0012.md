# RAPOR 0012
Olcek kapisi hi-res renderi 2400'e BOX ile indirip 2400 referansla olcuyordu; yeniden ornekleme harf kenarini degistiriyordu.
Olcek kapisi artik iki renderi dogal piksel olceginde olcuyor ve hi-res koordinatlarini 2400 birimine normalize ediyor.
Leke kapisi baskiyi plate ile karsilastiriyordu; plate ortak zemin oldugu icin kaynaktaki burc resmi leke sayiliyordu.
Leke kapisi artik bant disini hibrit baskinin gercek kaynak tuvaliyle, ayni hedef piksel boyunda karsilastiriyor.
Sentetik test dogru olcek/lekeyi PASS, uc piksel kaymayi ve 256 px yapay lekeyi FAIL dogruluyor.
