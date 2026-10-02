#!/usr/bin/env python3
"""SEMBOL KESITLERI: kapinin hizaladigi kaynak / uretim pencereleri yan yana 1:1 (buyutmesiz) ve x4 + fark olcusu.
Gozle gorunurluk: sembol murekkebinde CIE76 dE (Lab); dE < 2.3 ~ fark edilemez (JND). Girdi: ornek_is ciktilari."""
import glob, json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image, ImageDraw


def lab(a):
    return cv2.cvtColor(a.astype(np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32) * [100 / 255., 1, 1] - [0, 128, 128]


def main(giris, cikti):
    cikti = Path(cikti); cikti.mkdir(parents=True, exist_ok=True); sat = []
    for js in sorted(glob.glob(f'{giris}/*/SEMBOL_*.json')):
        d = Path(js).parent; k = json.load(open(js)); i = k['sira']
        for y in ('sol', 'sag'):
            a = np.asarray(Image.open(d / f'sembol_{i}_{y}_kaynak.png').convert('RGB')).astype(np.float32)
            b = np.asarray(Image.open(d / f'sembol_{i}_{y}_uretim.png').convert('RGB')).astype(np.float32)
            m = np.load(d / f'sembol_{i}_{y}_maske.npy')
            dE = np.sqrt(((lab(a) - lab(b)) ** 2).sum(2))
            f = np.abs(a - b).max(2)
            v = {'is': d.name, 'sira': i, 'yan': y, **k['yan'][y],
                 'dE_murekkep_ort': round(float(dE[m].mean()), 2), 'dE_murekkep_p95': round(float(np.percentile(dE[m], 95)), 2),
                 'dE_gt_2.3_payi': round(float((dE[m] > 2.3).mean()), 3), 'dE_zemin_ort': round(float(dE[~m].mean()), 2),
                 'kanal_fark_ort_RGB': [round(float(x), 2) for x in (b - a)[m].mean(0)]}
            sat.append(v)
            h = (np.clip(f * 8, 0, 255)).astype(np.uint8)
            yan = np.concatenate([a.astype(np.uint8), np.full((a.shape[0], 6, 3), 255, np.uint8), b.astype(np.uint8),
                                  np.full((a.shape[0], 6, 3), 255, np.uint8), np.stack([h] * 3, 2)], 1)
            im = Image.new('RGB', (yan.shape[1], yan.shape[0] + 30), (255, 255, 255)); im.paste(Image.fromarray(yan), (0, 30))
            ImageDraw.Draw(im).text((4, 8), f"{d.name} sira {i} {y}: KAYNAK | URETIM | |fark| x8   fark {v['fark']} "
                                            f"iou {v['iou']} dE ort {v['dE_murekkep_ort']} p95 {v['dE_murekkep_p95']}", fill=(0, 0, 0))
            ad = f"SEMBOL_{d.name}_s{i}_{y}"
            im.save(cikti / f'{ad}_1e1.png')
            im.resize((im.width * 4, im.height * 4), Image.NEAREST).save(cikti / f'{ad}_x4.png')
            print('SEMBOL', json.dumps(v), flush=True)
    (cikti / 'SEMBOL_OLCUM.json').write_text(json.dumps(sat, indent=1))
    t = ['# SEMBOL KAPISI KESITLERI', '', 'dE: CIE76, sembol murekkebi (kaynak maskesi); dE < 2.3 ~ gozle fark edilemez', '',
         '| is | sira | yan | fark | iou | kaydirma px | dE ort | dE p95 | dE>2.3 payi | zemin dE | RGB fark ort |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for v in sat:
        t.append(f"| {v['is']} | {v['sira']} | {v['yan']} | {v['fark']} | {v['iou']} | {v['kaydirma_px']} | {v['dE_murekkep_ort']} | "
                 f"{v['dE_murekkep_p95']} | {v['dE_gt_2.3_payi']} | {v['dE_zemin_ort']} | {v['kanal_fark_ort_RGB']} |")
    (cikti / 'SEMBOL_OLCUM.md').write_text('\n'.join(t) + '\n'); print('\n'.join(t))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
