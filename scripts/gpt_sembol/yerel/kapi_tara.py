import csv, glob, os, subprocess, json, re
B='/home/claude/blender'
out={}
for r in csv.DictReader(open(f'{B}/isim_tagline_78.csv')):
    c=r['cift']
    if c in ('GEMINI_VIRGO','ARIES_LEO','CANCER_LIBRA'):
        g=f'{B}/gpt_api1/{c}_gpt.png'; t=f'/home/claude/gs/gpt_sembol/girdi/{c}_temiz.png'; kd='gi_gv' if c=='GEMINI_VIRGO' else 'gi_3'
    else:
        g=sorted(glob.glob(f'{B}/gpt_api_all/{c}_gpt_k*.png'),key=os.path.getmtime)[-1]; t=f'{B}/gi_all_girdi/{c}_temiz.png'; kd='gi_all'
    p=subprocess.run([f'{B}/venv/bin/python',f'{B}/gpt_birlestir2.py',c,g,t,kd,'/tmp/kapi_bos','KILIT_GPTGIRDI.json'],capture_output=True,text=True,cwd=B,env=dict(os.environ,KAPI_SADECE='1'))
    m=re.search(r'SEKIL_KAPI (\{.*\})',p.stdout)
    out[c]=json.loads(m.group(1)) if m else {'hata':p.stderr[-200:]}
    if not out[c].get('PASS'): print(c,out[c])
json.dump(out,open(f'{B}/kapi_tara.json','w'),indent=1)
print('FAIL',sum(1 for v in out.values() if not v.get('PASS')))
