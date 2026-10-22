#!/usr/bin/env python3
"""Recompose gallery previews from gallery_layout.json and its clean B images.
Requires Python 3.10+ and Pillow with FreeType. Run: python render_previews.py
Does not modify the B images or the original assets.
"""
import argparse, json, io, os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageCms

def render(root, destination, selected=None):
    data=json.loads((root/'gallery_layout.json').read_text(encoding='utf-8'))
    W,H=data['canvas']['width_px'],data['canvas']['height_px']
    destination.mkdir(parents=True,exist_ok=True)
    profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    def box(e):
        cx,cy,w,h=(e[k] for k in ['center_x_pct','center_y_pct','width_pct','height_pct'])
        return [round((cx-w/2)*W/100),round((cy-h/2)*H/100),round((cx+w/2)*W/100),round((cy+h/2)*H/100)]
    for s in data['slides']:
        if selected and s['number'] not in selected:continue
        a=Image.open(root/s['clean_background_file']).convert('RGBA')
        for e in s['elements']:
            layer=Image.new('RGBA',(W,H));draw=ImageDraw.Draw(layer)
            typ=e['type']
            if typ in ('poster','symbol'):
                b=box(e);im=Image.open(root/e['content']['source_file']).convert('RGBA')
                scale=min((b[2]-b[0])/im.width,(b[3]-b[1])/im.height)
                nw,nh=round(im.width*scale),round(im.height*scale)
                im=im.resize((nw,nh),Image.Resampling.LANCZOS)
                layer.alpha_composite(im,(round((b[0]+b[2]-nw)/2),round((b[1]+b[3]-nh)/2)))
            elif typ=='text':
                b=box(e);fd=e['font'];size=fd['size_px']
                f=ImageFont.truetype(str(root/fd['file']),round(size))
                f.set_variation_by_axes([fd['weight']])
                tracking=e['letter_spacing_px'];lines=e['content'].split('\n')
                advance=size*e['line_height_em'];lh=size+(len(lines)-1)*advance
                top=b[1]+((b[3]-b[1])-lh)/2
                for j,line in enumerate(lines):
                    tw=f.getlength(line) if tracking==0 else sum(f.getlength(c) for c in line)+tracking*max(0,len(line)-1)
                    if tw>b[2]-b[0]+1:raise ValueError(f"Slide {s['number']} text does not fit: {e['id']}")
                    x=b[0] if e['alignment']=='left' else (b[2]-tw if e['alignment']=='right' else (b[0]+b[2]-tw)/2)
                    ink=f.getbbox(line);y=top+j*advance+(size-(ink[3]-ink[1]))/2-ink[1]
                    if '&' in line and fd.get('italic'):
                        # AstroLoveArt rule: '&' is always a plain upright ampersand (italic & looks like 'Et')
                        fu=ImageFont.truetype(str(root/'fonts/CormorantGaramond.ttf'),round(size));fu.set_variation_by_axes([fd['weight']])
                        parts=line.split('&');tw=sum(f.getlength(p) for p in parts)+fu.getlength('&')*(len(parts)-1)
                        x=b[0] if e['alignment']=='left' else (b[2]-tw if e['alignment']=='right' else (b[0]+b[2]-tw)/2)
                        for k,p in enumerate(parts):
                            draw.text((x,y),p,font=f,fill=e['color_hex']);x+=f.getlength(p)
                            if k<len(parts)-1:draw.text((x,y),'&',font=fu,fill=e['color_hex']);x+=fu.getlength('&')
                    elif tracking:
                        for c in line:
                            draw.text((x,y),c,font=f,fill=e['color_hex']);x+=f.getlength(c)+tracking
                    else:draw.text((x,y),line,font=f,fill=e['color_hex'])
            elif typ=='line':
                points=[(round(x*W/100),round(y*H/100)) for x,y in e['points_pct']]
                draw.line(points,fill=e['stroke_hex'],width=e['stroke_width_px'])
                if e.get('arrow_at_end'):
                    x,y=points[-1];draw.line([(x-27,y-18),(x,y),(x-27,y+18)],fill=e['stroke_hex'],width=e['stroke_width_px'])
            else:raise ValueError(typ)
            if e.get('rotation_deg',0):
                layer=layer.rotate(-e['rotation_deg'],resample=Image.Resampling.BICUBIC,center=(e['center_x_pct']*W/100,e['center_y_pct']*H/100))
            a.alpha_composite(layer)
        path=destination/Path(s['preview_file']).name
        buffer=io.BytesIO()
        a.convert('RGB').save(buffer,format='JPEG',quality=97,subsampling=0,optimize=True,icc_profile=profile)
        temp=path.with_suffix('.writing')
        temp.write_bytes(buffer.getvalue())
        os.replace(temp,path)
        print(path.name)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='Recomposed_A');ap.add_argument('--slides',type=int,nargs='*')
    ap.add_argument('--root',default=None)
    args=ap.parse_args();root=Path(args.root) if args.root else Path(__file__).resolve().parent
    render(root,root/args.output,args.slides)
