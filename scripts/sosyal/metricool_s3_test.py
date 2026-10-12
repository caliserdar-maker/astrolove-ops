#!/usr/bin/env python3
"""Metricool dogrudan dosya yukleme testi (GONDERI OLUSTURMAZ). Swagger: data/sosyal/kaynak/metricool/METRICOOL_SWAGGER.json
  1) PUT  /v2/media/s3/upload-transactions  {resourceType: planner, contentType, fileExtension, parts:[{size,startByte,endByte,hash}]}
  2) her parca presigned URL'ye PUT (5 MB alti SIMPLE, ustu MULTIPART)
  3) PATCH /v2/media/s3/upload-transactions {multipart:{uploadId,key,parts:[{partNumber,etag}]}} ya da {simple:{fileUrl}}
  4) GET  /v2/media/s3/upload-transactions?key&bucket (dosya bilgisi) + fileUrl HEAD probu
Cikti: JSON (presigned URL'ler YAZILMAZ). Kullanim: metricool_s3_test.py TOKEN.json DOSYA.mp4 CIKTI.json"""
import base64, hashlib, importlib.util, json, os, subprocess, sys, urllib.request

sp = importlib.util.spec_from_file_location('mpb', os.path.join(os.path.dirname(__file__), 'metricool_pin_baslik.py'))
mpb = importlib.util.module_from_spec(sp); sp.loader.exec_module(mpb)
PARCA = 8 * 1024 * 1024


def b64sha(b):
    return base64.b64encode(hashlib.sha256(b).digest()).decode()


def put_parca(url, veri, h, sha_baslik):
    bas = {'Content-Length': str(len(veri))}
    if sha_baslik:
        bas['x-amz-checksum-sha256'] = h
    r = urllib.request.Request(url, data=veri, method='PUT', headers=bas)
    try:
        with urllib.request.urlopen(r, timeout=300) as y:
            return y.status, y.headers.get('ETag')
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode('utf-8', 'replace')


def main():
    mc = mpb.MC(json.load(open(sys.argv[1])))
    yol, cikti = sys.argv[2], sys.argv[3]
    veri = open(yol, 'rb').read()
    n = len(veri)
    parcalar = [] if n >= 5 * 1024 * 1024 else [(0, n)]
    if not parcalar:
        for s in range(0, n, PARCA):
            parcalar.append((s, min(n, s + PARCA)))
    istek = {'resourceType': 'planner', 'contentType': 'video/mp4', 'fileExtension': 'mp4',
             'parts': [{'size': e - s, 'startByte': s, 'endByte': e, 'hash': b64sha(veri[s:e])} for s, e in parcalar]}
    rapor = {'dosya': os.path.basename(yol), 'boyut': n, 'parca': len(parcalar), 'sha256': hashlib.sha256(veri).hexdigest()}
    y = mpb.veri(mc.istek('PUT', '/v2/media/s3/upload-transactions', govde=istek))
    rapor['olustur'] = {k: y.get(k) for k in ('key', 'bucket', 'expiresAt', 'fileUrl', 'uploadType', 'totalSize')}
    for u in ([y.get('presignedUrl')] if y.get('presignedUrl') else [p.get('presignedUrl') for p in y.get('parts') or []]):
        print(f'::add-mask::{u}')
    etaglar = []
    if y.get('uploadType') == 'SIMPLE' or y.get('presignedUrl'):
        h = istek['parts'][0]['hash']
        st, et = put_parca(y['presignedUrl'], veri, h, True)
        if st >= 400:
            st, et = put_parca(y['presignedUrl'], veri, h, False)
        rapor['yukle'] = [{'parca': 1, 'http': st}]
        tamam = {'simple': {'fileUrl': y.get('fileUrl')}}
    else:
        yuk = []
        for p in sorted(y.get('parts') or [], key=lambda p: p['partNumber']):
            s, e = p['startByte'], p['endByte']
            h = b64sha(veri[s:e])
            st, et = put_parca(p['presignedUrl'], veri[s:e], h, True)
            if st >= 400:
                st, et = put_parca(p['presignedUrl'], veri[s:e], h, False)
            yuk.append({'parca': p['partNumber'], 'http': st})
            etaglar.append({'partNumber': p['partNumber'], 'etag': et if st < 400 else ''})
        rapor['yukle'] = yuk
        tamam = {'multipart': {'uploadId': y.get('uploadId'), 'key': y.get('key'), 'parts': etaglar}}
    if any(x['http'] >= 400 for x in rapor['yukle']):
        rapor['sonuc'] = 'YUKLEME_HATA'
    else:
        try:
            c = mpb.veri(mc.istek('PATCH', '/v2/media/s3/upload-transactions', govde=tamam))
            rapor['tamamla'] = c
        except SystemExit as e:
            rapor['tamamla'] = {'HATA': str(e)[:300]}
        try:
            rapor['bilgi'] = mpb.veri(mc.istek('GET', '/v2/media/s3/upload-transactions', {'key': y.get('key'), 'bucket': y.get('bucket')}))
        except SystemExit as e:
            rapor['bilgi'] = {'HATA': str(e)[:300]}
        url = (rapor.get('tamamla') or {}).get('convertedFileUrl') or (rapor.get('tamamla') or {}).get('fileUrl') or y.get('fileUrl')
        if url:
            o = subprocess.run(['curl', '-s', '-o', '/dev/null', '-m', '120', '-w', '%{http_code}|%{content_type}|%{size_download}', url],
                               capture_output=True, text=True).stdout
            rapor['prob'] = {'url': url, 'sonuc': o}
        rapor['sonuc'] = 'OK' if url and (rapor.get('prob') or {}).get('sonuc', '').startswith('200') else 'DOGRULANAMADI'
    json.dump(rapor, open(cikti, 'w'), ensure_ascii=False, indent=1)
    print('S3TEST', json.dumps(rapor, ensure_ascii=False)[:1500])


if __name__ == '__main__':
    main()
