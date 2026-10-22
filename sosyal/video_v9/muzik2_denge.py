"""ADAY_09 v5: v3 removed too much brightness (muffled). Balanced fix: limited high-shelf cut (only the excess,
capped) + a gentle broadband dip around the hit, slow ramps. Two strengths: A light, B medium."""
import numpy as np, soundfile as sf, librosa, subprocess, re, sys
from scipy.ndimage import gaussian_filter1d, minimum_filter1d
S = '/tmp/claude-0/-home-claude/b27d1999-de9e-588b-b6f9-3ab0fbf52d0b/scratchpad'
y, sr = sf.read(S + '/_m2_yeni_raw.wav'); y = y.T
nfft, hop = 2048, 256; dt = hop / sr
Z = [librosa.stft(y[c], n_fft=nfft, hop_length=hop) for c in range(y.shape[0])]
P = sum(np.abs(z) ** 2 for z in Z)
fr = librosa.fft_frequencies(sr=sr, n_fft=nfft); tt = librosa.frames_to_time(np.arange(P.shape[1]), sr=sr, hop_length=hop)
sel = fr >= 3000
lev = gaussian_filter1d(10 * np.log10(P[sel].sum(0) + 1e-12), 0.08 / dt)
ref = np.median(lev[(tt > 10) & (tt < 16)])
w = np.clip((fr - 1500) / 2500, 0, 1)                    # shelf: 0 below 1.5 kHz, full above 4 kHz
for tag, shelf_max, dip in [('A', 8.0, 3.0), ('B', 12.0, 4.5)]:
    g = np.clip(ref + 4.0 - lev, -shelf_max, 0)
    g = np.where((tt > 15.5) & (tt < 21.0), g, 0)
    g = gaussian_filter1d(minimum_filter1d(g, int(0.4 / dt)), 0.25 / dt)
    bb = -dip * np.exp(-0.5 * ((tt - 18.05) / 0.5) ** 2)
    G = w[:, None] * g[None, :] + bb[None, :]
    out = np.stack([librosa.istft(z * 10 ** (G / 20), hop_length=hop, length=y.shape[1]) for z in Z])
    raw = S + f'/_m2_v5{tag}_raw.wav'; sf.write(raw, out.T, sr, subtype='FLOAT')
    gdb = 0.0
    for it in range(5):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', f'volume={gdb:.2f}dB,alimiter=limit=0.8:attack=5:release=80:level=false,aresample=48000',
                        '-c:a', 'aac', '-b:a', '192k', '-t', '24', S + f'/_m2_v5{tag}.m4a'], check=True)
        e = subprocess.run(['ffmpeg', '-nostats', '-i', S + f'/_m2_v5{tag}.m4a', '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
        I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', e)[-1])
        if abs(I + 16) < 0.2: break
        gdb += -16 - I
    print(tag, f'shelf max {g.min():.1f} dB, dip {dip} dB, {I:.1f} LUFS')
