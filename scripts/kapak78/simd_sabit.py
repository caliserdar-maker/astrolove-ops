#!/usr/bin/env python3
"""Kart / gorunum uretiminde SIMD yolunu sabitler (Serdar 31 Eki karar 8a). Kok neden (olcum, kart-determinizm kosulari 41186253130 /
41187364930 + yerel): NumPy AVX512 (X86_V4) olan islemcide arcsin / cos / us (**) icin farkli kod yolu secer, sonuc bit duzeyinde degisir;
fark gorunum -> GrabCut maskesi zincirinde buyur (kart farki en cok 237 / 255). AMD EPYC 7763 (AVX512 yok, ubuntu-24.04) gorunumleri
AVX512'li Intel 8573C / AMD 9V74 / 9V45 / yerel ile farkli; AVX512 kapatilinca yerel sonuc AVX2 yoluyla birebir (ayni olcum dizisi sha
e8794ab836, numpy 2.1.3 ve 2.5.3).
ayarla(env): NumPy (surume gore ozellik adlari) ve OpenCV AVX512 yolunu kapatan ortam degiskenlerini env'e yazar (numpy import edilmeden
once). prob(python, env): o python + env ile olcum dizisinin sha'si; REF ile esit degilse uretim DUR (kapi)."""
import os
import subprocess
import sys

# numpy surumu -> dagitilan AVX512 hedefleri (numpy hata verir: baska surumun adi kabul edilmez; olculdu 31 Eki)
NPY = {"2.1": "AVX512F AVX512CD AVX512_KNL AVX512_KNM AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL",
       "2.5": "X86_V4 AVX512_ICL AVX512_SPR"}
OPENCV = "AVX512-SKX"      # cv2.getCPUFeaturesLine adi (4.10 ve 5.0); kapaninca satirda 'AVX512-SKX?' gorunur
REF = "e8794ab836"         # olcum dizisinin AVX512 kapali (ve AVX2 / taban) sha'si; yerel olcum 31 Eki
PROB = ("import numpy as np, hashlib\n"
        "x = np.linspace(-0.999, 0.999, 2_000_003)\n"
        "print(hashlib.sha256(np.arcsin(x).tobytes()).hexdigest()[:10])")


def numpy_surum(python):
    e = {k: v for k, v in os.environ.items() if k != "NPY_DISABLE_CPU_FEATURES"}
    r = subprocess.run([python, "-c", "import importlib.metadata as m; print(m.version('numpy'))"], capture_output=True, text=True,
                       env=e)
    if r.returncode:
        raise SystemExit(f"DUR: {python} numpy surumu okunamadi: {r.stderr[-200:]}")
    return ".".join(r.stdout.strip().split(".")[:2])


def ayarla(env, python=sys.executable):
    s = numpy_surum(python)
    if s not in NPY:
        raise SystemExit(f"DUR: numpy {s} icin AVX512 ozellik listesi tanimsiz (simd_sabit.NPY); olcmeden eklenmez")
    env["NPY_DISABLE_CPU_FEATURES"] = NPY[s]
    env["OPENCV_CPU_DISABLE"] = OPENCV
    return env


def prob(python, env):
    r = subprocess.run([python, "-c", PROB], capture_output=True, text=True, env=env)
    return r.stdout.strip() if r.returncode == 0 else f"HATA {r.stderr.strip()[-200:]}"


def kapi(python, env, ad):
    p = prob(python, env)
    if p != REF:
        raise SystemExit(f"DUR: SIMD kapisi {ad}: olcum {p} != {REF} (AVX512 yolu kapali degil ya da ortam farkli)")
    return p


if __name__ == "__main__":
    for py in sys.argv[1:] or [sys.executable]:
        e = ayarla(dict(os.environ), py)
        print(py, numpy_surum(py), "acik:", prob(py, {k: v for k, v in os.environ.items() if k != "NPY_DISABLE_CPU_FEATURES"}),
              "kapali:", prob(py, e), "REF", REF)
