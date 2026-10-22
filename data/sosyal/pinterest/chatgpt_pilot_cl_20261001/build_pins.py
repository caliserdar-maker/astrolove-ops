"""Deterministic Pinterest compositions. Existing artwork is only resized uniformly.

Run: python build_pins.py --config pair.json
All coordinates use top-left origin. Rectangle convention: [x, y, width, height].
Typography uses pixels; pt = px * 72 / 96, at an explicit 96 dpi.
"""
from pathlib import Path
import argparse, csv, hashlib, json, io, os, uuid
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent
NAVY, CREAM, GOLD, MUTED = '#111D31', '#F2EEE7', '#947748', '#665E53'
FONTS = {'serif': ROOT/'fonts/P052-Roman.otf', 'sans': ROOT/'fonts/NimbusSans-Regular.otf'}
ROWS, COMPS, CHECKS = [], {}, []
PREFIX = ''

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def font(role, px): return ImageFont.truetype(str(FONTS[role]), px)
def path(p): return ROOT / p
def save_image(im, dest, format='PNG', **kwargs):
    # Commit complete image bytes atomically, so preview/indexing readers never
    # encounter an image halfway through a write.
    data=io.BytesIO(); im.save(data,format=format,**kwargs)
    dest=Path(dest); dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.tmp')
    with temp.open('wb') as stream:
        stream.write(data.getvalue()); stream.flush(); os.fsync(stream.fileno())
    os.replace(temp,dest)

class Composition:
    def __init__(self, name, size, backdrop):
        self.name, self.size, self.layers = PREFIX + name, size, []
        self.canvas = Image.open(path(backdrop)).convert('RGBA')
        assert self.canvas.size == size
        self.add('00_background', self.canvas.copy(), {'type':'background', 'asset':backdrop, 'bbox_xywh':[0,0,*size]})

    def add(self, lid, image, meta):
        image = image.convert('RGBA')
        assert image.size == self.size
        dest = path(f'layers/{self.name}/{lid}.png')
        dest.parent.mkdir(parents=True, exist_ok=True)
        save_image(image,dest,dpi=(96,96))
        layer = {'id':lid, 'full_canvas_asset':str(dest.relative_to(ROOT)), 'opacity':1, 'blend':'normal', **meta}
        self.layers.append(layer)
        self.canvas.alpha_composite(image)

    def text(self, lid, text, x, y, role, px, color=NAVY, max_width=None, align='left', spacing=1.1):
        if max_width:
            while max(font(role,px).getlength(line) for line in text.split('\n')) > max_width:
                px -= 1
                if px < 16: raise ValueError('Copy too long')
        lay = Image.new('RGBA',self.size)
        d=ImageDraw.Draw(lay)
        h=round(px*spacing)
        for i,line in enumerate(text.split('\n')):
            d.text((x,y+i*h),line,font=font(role,px),fill=color,anchor='mt' if align=='center' else 'lt')
        bbox=lay.getbbox()
        assert bbox and bbox[0] >= 0 and bbox[1] >= 0 and bbox[2] <= self.size[0] and bbox[3] <= self.size[1]
        self.add(lid,lay,{'type':'text','text':text,'x':x,'y':y,'anchor':'mt' if align=='center' else 'lt','font_family':'P052' if role=='serif' else 'Nimbus Sans','font_asset':str(FONTS[role].relative_to(ROOT)),'font_px':px,'font_pt_at_96dpi':px*.75,'color':color,'line_step_px':h,'bbox_xywh':[bbox[0],bbox[1],bbox[2]-bbox[0],bbox[3]-bbox[1]]})

    def artwork(self, lid, asset, slot, shadow=False):
        im=Image.open(path(asset)).convert('RGBA')
        x,y,w,h=slot
        scale=min(w/im.width,h/im.height)
        aw,ah=round(im.width*scale),round(im.height*scale)
        ax,ay=x+(w-aw)//2,y+(h-ah)//2
        resized=im.resize((aw,ah),Image.Resampling.LANCZOS)
        if shadow:
            mask=Image.new('RGBA',self.size)
            ImageDraw.Draw(mask).rectangle((ax+7,ay+10,ax+aw+7,ay+ah+10),fill=(32,25,18,52))
            self.add(lid+'_shadow',mask.filter(ImageFilter.GaussianBlur(13)),{'type':'shadow','bbox_xywh':[ax+7,ay+10,aw,ah],'blur_px':13,'color':'#201912','alpha':52/255})
        lay=Image.new('RGBA',self.size)
        lay.alpha_composite(resized,(ax,ay))
        self.add(lid,lay,{'type':'artwork','asset':asset,'source_sha256':sha(path(asset)),'slot_xywh':slot,'bbox_xywh':[ax,ay,aw,ah],'uniform_scale':scale,'rotation':0,'crop':None,'color_adjustment':None,'overlay_on_artwork':False})
        CHECKS.append({'composition':self.name,'layer':lid,'aspect_error':abs(aw/ah-im.width/im.height),'source_sha256':sha(path(asset)),'pixel_preservation_after_uniform_resize':lay.crop((ax,ay,ax+aw,ay+ah)).tobytes()==resized.tobytes()})

    def rule(self,lid,xy,color=GOLD,width=1):
        lay=Image.new('RGBA',self.size); ImageDraw.Draw(lay).line(xy,fill=color,width=width)
        self.add(lid,lay,{'type':'rule','points':xy,'width_px':width,'color':color})

    def finish(self,folder):
        save_image(self.canvas.convert('RGB'),path(f'{folder}/{self.name}.jpg'),format='JPEG',quality=96,subsampling=0,dpi=(96,96))
        save_image(self.canvas.convert('RGB'),path(f'{folder}/{self.name}.png'),dpi=(96,96))
        COMPS[self.name]={'canvas':{'width':self.size[0],'height':self.size[1],'dpi':96},'layer_order':'bottom to top','layers':self.layers}

def make_backgrounds():
    save_image(Image.new('RGB',(1000,1500),CREAM),path('assets/bg_cream_1000x1500.png'))
    save_image(Image.new('RGB',(1600,900),CREAM),path('assets/bg_cream_1600x900.png'))
    save_image(Image.open(path('assets/scene_empty_master.png')).convert('RGB').resize((1000,1500),Image.Resampling.LANCZOS),path('assets/scene_empty_1000x1500.png'))
    gift=Image.new('RGB',(1000,1500),CREAM)
    scene=Image.open(path('assets/scene_empty_1000x1500.png')).resize((840,1260),Image.Resampling.LANCZOS).crop((0,105,840,1155))
    gift.paste(scene,(80,345))
    save_image(gift,path('assets/bg_gift_1000x1500.png'))

def main():
    global PREFIX
    parser=argparse.ArgumentParser(); parser.add_argument('--config',default='pair.json'); parser.add_argument('--prefix',default=''); args=parser.parse_args()
    if any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for ch in args.prefix):
        raise ValueError('Prefix must use English letters, digits, underscores or hyphens')
    PREFIX = args.prefix + '_' if args.prefix else ''
    for folder in ['assets','pins','profile','layers','templates']:
        path(folder).mkdir(parents=True,exist_ok=True)
    cfg=json.loads(path(args.config).read_text())
    pair=cfg['pair_display']; framed=cfg['framed_artwork']; colors=cfg['colors']
    make_backgrounds()
    c=Composition('01_Discovery_1000x1500',(1000,1500),'assets/scene_empty_1000x1500.png')
    c.text('01_brand','ASTROLOVEART',80,74,'sans',23,GOLD)
    c.text('02_pair',pair,80,132,'serif',68,max_width=840)
    c.text('03_hook','One symbol. Your love story.',80,221,'sans',29)
    c.artwork('04_framed_poster',framed,[172,314,656,835],shadow=True)
    c.text('05_personalization','Your two names. Your own message.',500,1222,'sans',30,align='center',max_width=840)
    c.text('06_formats','FINE ART PRINT  /  FRAMED PRINT  /  DIGITAL FILE',500,1290,'sans',19,align='center',max_width=840)
    c.finish('pins')

    c=Composition('02_Personalization_1000x1500',(1000,1500),'assets/bg_cream_1000x1500.png')
    c.text('01_brand','ASTROLOVEART  /  '+pair.upper(),80,66,'sans',22,GOLD,max_width=840)
    c.text('02_headline','Your names.\nYour words.',80,123,'serif',76)
    c.text('03_subtitle','A personal story, written by you.',80,305,'sans',28)
    c.artwork('04_complete_poster',framed,[174,384,652,831],shadow=True)
    c.text('05_instruction','Add two names and a short message.',500,1276,'sans',30,align='center',max_width=840)
    c.rule('06_rule',[(80,1352),(920,1352)])
    c.text('07_footer','PERSONALIZED ZODIAC COUPLE ART',500,1380,'sans',21,GOLD,align='center')
    c.finish('pins')

    c=Composition('03_Five_Colors_1000x1500',(1000,1500),'assets/bg_cream_1000x1500.png')
    c.text('01_brand','ASTROLOVEART  /  '+pair.upper(),80,66,'sans',22,GOLD,max_width=840)
    c.text('02_headline','Five colors.\nOne personal story.',80,123,'serif',65,max_width=840)
    c.text('03_subtitle','Find the palette that feels like you.',80,286,'sans',28,max_width=840)
    slots=[(80,405),(380,405),(680,405),(230,875),(530,875)]
    for i,(color,xy) in enumerate(zip(colors,slots)):
        x,y=xy
        c.artwork(f'04_color_{i+1}',color['asset'],[x,y,240,300])
        label=color['label'].replace(' ','\n',1)
        c.text(f'05_label_{i+1}',label,x+120,y+329,'sans',26,align='center',spacing=1.12)
    c.rule('06_rule',[(80,1325),(920,1325)])
    c.text('07_footer','The same original symbol in every edition.',500,1360,'sans',28,align='center',max_width=840)
    c.finish('pins')

    c=Composition('04_Anniversary_Gift_1000x1500',(1000,1500),'assets/bg_gift_1000x1500.png')
    c.text('01_brand','ASTROLOVEART',80,66,'sans',23,GOLD)
    c.text('02_headline','An anniversary gift\nwritten in the stars.',80,124,'serif',64,max_width=840)
    c.text('03_pair',pair+'  /  PERSONALIZED COUPLE ART',80,280,'sans',22,max_width=840)
    c.artwork('04_real_framed_poster',framed,[172,414,656,835],shadow=True)
    c.text('05_footer','Made personal with your names and message.',500,1430,'sans',23,align='center',max_width=840)
    c.finish('pins')

    c=Composition('Profile_Cover_1600x900',(1600,900),'assets/bg_cream_1600x900.png')
    c.text('01_brand','ASTROLOVEART',120,137,'sans',27,GOLD)
    c.text('02_headline','Two signs.\nOne love story.',120,235,'serif',94,max_width=780,spacing=1.1)
    c.text('03_subtitle','Personalized zodiac couple art',120,474,'sans',31)
    c.rule('04_rule',[(120,548),(785,548)])
    c.text('05_range','78 original zodiac pair designs',120,587,'sans',27)
    c.text('06_formats','Fine art prints, framed prints and digital files',120,638,'sans',24,max_width=770)
    c.text('07_signature','Your two names. Your own message.',120,704,'sans',26,MUTED)
    c.artwork('08_real_framed_poster',framed,[991,120,489,660],shadow=True)
    c.finish('profile')

    path(PREFIX+'layer_manifest.json').write_text(json.dumps(COMPS,ensure_ascii=False,indent=2))
    path(PREFIX+'qa_results.json').write_text(json.dumps(CHECKS,indent=2))
    with path(PREFIX+'layer_list.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['composition','layer','type','asset','bbox_xywh','text','font','font_px','font_pt_at_96dpi','color'])
        writer.writeheader()
        for name,comp in COMPS.items():
            for a in comp['layers']:
                writer.writerow({'composition':name,'layer':a['id'],'type':a['type'],'asset':a.get('asset',a['full_canvas_asset']),'bbox_xywh':json.dumps(a.get('bbox_xywh')),'text':a.get('text',''),'font':a.get('font_family',''),'font_px':a.get('font_px',''),'font_pt_at_96dpi':a.get('font_pt_at_96dpi',''),'color':a.get('color','')})
    # Full-size layers are linked, so SVGs remain portable when kept with the package.
    from xml.sax.saxutils import escape
    for name,comp in COMPS.items():
        w,h=comp['canvas']['width'],comp['canvas']['height']
        body=[]
        for a in comp['layers']:
            body.append(f'<g id="{a["id"]}"><image x="0" y="0" width="{w}" height="{h}" href="../{escape(a["full_canvas_asset"])}"/></g>')
        path(f'templates/{name}.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'+''.join(body)+'</svg>')
    print(json.dumps({'created':list(COMPS),'artwork_checks':len(CHECKS),'all_pixel_checks':all(a['pixel_preservation_after_uniform_resize'] for a in CHECKS)},indent=2))

if __name__=='__main__': main()
