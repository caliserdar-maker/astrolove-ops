import csv
Z=['ARIES','TAURUS','GEMINI','CANCER','LEO','VIRGO','LIBRA','SCORPIO','SAGITTARIUS','CAPRICORN','AQUARIUS','PISCES']
BASLIK='{B} Gifts, Personalized {B} Mug with Name or Date, Custom Coffee Cup'
ETIKET=['{b} gifts','{b} mug','{b} birthday','personalized mug','custom mug','custom coffee mug','personalized cup',
        'evil eye mug','customizable mug','custom name mug','birthday mug','zodiac gift','{b} zodiac']
ILK="{B} Gifts made personal: a personalized {B} mug with the zodiac symbol and a name or date on the front, and your own message on the back. A custom coffee cup for {A} {B} birthday."
STIL=[('07','Orange Blossom','orange'),('08','Purple Fig','fig'),('09','Olive Breeze','olive'),('10','Pomegranate Bloom','pomegranate'),
      ('11','Almond Blossom','almond blossom'),('12','Lemon Grove','lemon'),('13','Blue Grape','grape'),('14','Golden Loquat','loquat')]
def alt(B):
    a=[('01 kapak',f"{B.upper()} Personalized Gift Mug: a hand holds a white ceramic mug with the {B} zodiac symbol and the example name EMILY, framed by orange blossom branches"),
       ('02 K02_SEMBOL',f"Your Zodiac Sign: the {B} symbol shown large, as printed on the front of this personalized mug"),
       ('03 K03_KISISEL',f"Front and back of the {B} mug: {B} symbol with a name or date on the front, evil eye bead and your message on the back"),
       ('04 K05_BOYUT',f"Size comparison of the 11 oz and 15 oz {B} mugs with height, diameter and volume"),
       ('05 K07_SUREC',f"Made for You, Step by Step: a preview of your {B} mug via Etsy Messages, your approval, printing on both sides, and easy care (dishwasher and microwave safe)"),
       ('06 K04_STIL',f"All 8 styles of the personalized {B} mug: Orange Blossom, Purple Fig, Olive Breeze, Pomegranate Bloom, Almond Blossom, Lemon Grove, Blue Grape and Golden Loquat")]
    for n,s,f in STIL: a.append((f"{n} STIL",f"{B.upper()} {s}: a hand holds the personalized {B} mug in the {s} style, with {f} branches and the {B} symbol above the example name EMILY"))
    return a
src={r['kod']:r for r in csv.DictReader(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..','ilan','SADE12_METIN.csv')))}
hata=[];out=[]
for k in Z:
    B=k.title(); b=k.lower()
    t=BASLIK.format(B=B); e=[x.format(b=b) for x in ETIKET]
    eski=src[k]['aciklama']; ilk_eski=eski.split('\n')[0]
    acik=eski.replace(ilk_eski,ILK.format(B=B,A='an' if B[0] in 'AEIOU' else 'a'),1)
    if len(t)>140: hata.append((k,'baslik',len(t)))
    if len(set(e))!=13 or any(len(x)>20 for x in e): hata.append((k,'etiket',[x for x in e if len(x)>20]))
    for s in (t,acik,*[x[1] for x in alt(B)]):
        if any(c in s for c in '—–'): hata.append((k,'tire'))
    for n,x in alt(B):
        if len(x)>250: hata.append((k,n,len(x)))
    out.append(dict(kod=k,baslik=t,baslik_kr=len(t),kelime=len(t.replace(',','').split()),etiketler=', '.join(e),aciklama=acik,
                    alt='\n'.join(f"{n}: {x}" for n,x in alt(B))))
def kanser(o):
    if o['kod']!='CANCER': return o
    for k in ('baslik','aciklama','alt'):
        o[k]=o[k].replace('Cancer mug with the zodiac symbol','Cancer mug with the Cancer symbol').replace('Cancer Mug','Cancer Zodiac Mug').replace('Cancer mug','Cancer zodiac mug')
    o['etiketler']=o['etiketler'].replace('cancer mug,','cancer zodiac mug,').replace('cancer birthday,','cancer zodiac gift,')
    o['baslik_kr']=len(o['baslik']); o['kelime']=len(o['baslik'].replace(',','').split())
    return o
out=[kanser(o) for o in out]
for o in out:
    e=[x.strip() for x in o['etiketler'].split(',')]
    assert len(e)==13 and len(set(e))==13 and all(len(x)<=20 for x in e), o['kod']
w=csv.DictWriter(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'..','ilan','SADE12_SEO_ONERI.csv'),'w',newline=''),fieldnames=list(out[0]));w.writeheader();w.writerows(out)
print('HATA',hata)
for o in out: print(o['kod'],o['baslik_kr'],o['kelime'])
print(out[0]['baslik']);print(out[0]['etiketler']);print(out[0]['aciklama'][:400]);print(out[0]['alt'])
