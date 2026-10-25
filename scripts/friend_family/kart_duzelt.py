"""Yesil kartlarda zemin kose suslerini sil + yazi satiri sil/tasi (Serdar 25 Eki). Orijinal yazi pikselleri korunur, yeni yazi cizilmez."""
import numpy as np, cv2

def zemin_doldur(A, mask, doku_kutu, sigma=40):
    """mask=1 bolgeleri zeminle doldurur: normalize bulanik (yalniz temiz zemin pikselleri) + temiz yamadan doku."""
    m = cv2.dilate(mask.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(np.float32)
    temiz = ((1 - m) * (A.mean(2) < 90) * (A.mean(2) > 15)).astype(np.float32)   # acik ogeler ve maske disi
    alcak = None
    for sg in (sigma, sigma * 2.5, sigma * 6):                    # coklu olcek: buyuk bosluklarda genis olcege dus
        pay = cv2.GaussianBlur(A * temiz[..., None], (0, 0), sg)
        payda = cv2.GaussianBlur(temiz, (0, 0), sg)[..., None]
        est = pay / np.maximum(payda, 1e-6); guv = np.clip(payda / 0.25, 0, 1)
        alcak = est if alcak is None else alcak * guv_once + est * (1 - guv_once)
        guv_once = guv if alcak is est else np.maximum(guv_once, guv)
    x0, y0, x1, y1 = doku_kutu
    p = A[y0:y1, x0:x1]; hf = p - cv2.GaussianBlur(p, (0, 0), 5)
    th, tw = hf.shape[:2]
    doku = np.tile(hf, (A.shape[0] // th + 2, A.shape[1] // tw + 2, 1))[:A.shape[0], :A.shape[1]]
    w = cv2.GaussianBlur(m, (0, 0), 2)[..., None]
    return A * (1 - w) + (alcak + doku) * w

def acik(A, esik=90):
    return A.mean(2) > esik
