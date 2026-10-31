#!/usr/bin/env python3
"""Galeri karti uretimi SIMD baslaticisi (Serdar 31 Eki karar 8a + 31 Eki onayi 3: kupa / sade kupa / 1st Anniversary kartlarinin TUM
uretim is akislari). Hedef betigi, numpy / OpenCV AVX512 yolu kapali ve OpenBLAS cekirdegi sabit ortamda YENI surecte calistirir:
simd_sabit.ayarla (ortam) -> simd_sabit.kapi (olcum dizisi REF + __cpu_features__ + OpenCV ozellik satiri; tutmazsa DUR) -> os.execve.
Musteri siparis dosyalari kapsam disi (Serdar 31 Eki).
Kullanim: python3 -I simd_calistir.py   (hedef -I'siz kosar)
         python3 -I simd_calistir.py <betik.py> [arguman ...]   (python3 = hedef betigin kosacagi yorumlayici)"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simd_sabit  # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit("kullanim: simd_calistir.py <betik.py> [arguman ...]")
    env = simd_sabit.ayarla(dict(os.environ), sys.executable)
    simd_sabit.kapi(sys.executable, env, Path(sys.argv[1]).name)
    print(f"SIMD sabit: {Path(sys.argv[1]).name} NPY_DISABLE_CPU_FEATURES={env['NPY_DISABLE_CPU_FEATURES']!r} REF {simd_sabit.REF}",
          flush=True)
    # -I YOK: betiklerin bir kismi kendi klasorunu sys.path'ten bekler (yd_kart_ornek `import yd_kart_ornek as _M`); is akislari bu
    # betikleri onceden de -I'siz kosuyordu. Ortam degiskenleri (SIMD) acikca env ile verilir.
    os.execve(sys.executable, [sys.executable, *sys.argv[1:]], env)


if __name__ == "__main__":
    main()
