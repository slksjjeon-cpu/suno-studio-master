"""v3 strong hum: 가사 10% / 반주 30% 목표.
- 원음(dry) 완전 제거, f0 추적 허밍 재합성 + 뭉갠 반주베드만 사용.
- 의존성: librosa, soundfile, scipy, numpy (로컬, 오프라인)
"""
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
from scipy import signal

SR = 22050
HOP = 512

def smooth_env(rms, sr=SR, hop=HOP, tau=0.12):
    # 지수 스무딩으로 자음 트랜지언트 뭉개기 (release 길게)
    alpha = np.exp(-(hop / sr) / tau)
    out = np.zeros_like(rms)
    acc = 0.0
    for i, v in enumerate(rms):
        acc = alpha * acc + (1 - alpha) * v if v < acc else 0.35 * v + 0.65 * acc
        out[i] = acc
    return out

def grain_smear(x, sr=SR, grain_ms=130, win_ms=900, seed=7, prog_cb=None):
    # 130ms 그레인을 900ms 창 안에서 섞어 단어 단위 파괴, 멜로디 윤곽은 유지
    rng = np.random.default_rng(seed)
    g = int(sr * grain_ms / 1000)
    w = int(sr * win_ms / 1000)
    y = np.zeros_like(x)
    n = len(x)
    wins = list(range(0, n, w))
    for i, s in enumerate(wins):
        e = min(n, s + w)
        seg = x[s:e]
        ng = int(np.ceil(len(seg) / g))
        grains = [seg[i*g:(i+1)*g] for i in range(ng)]
        order = rng.permutation(ng)
        pos = s
        for idx in order:
            gr = grains[idx]
            L = len(gr)
            # 짧은 크로스페이드로 클릭 제거
            f = min(L, int(sr * 0.015))
            if f > 1:
                ramp = np.linspace(0, 1, f)
                gr = gr.copy()
                gr[:f] *= ramp
                gr[-f:] *= ramp[::-1]
            y[pos:pos+L] += gr[:max(0, min(L, n-pos))]
            pos += L
        if prog_cb:
            prog_cb((i + 1) / len(wins))
    # 원본 대비 에너지 보정
    if np.max(np.abs(y)) > 1e-6:
        y *= (np.max(np.abs(x)) + 1e-9) / (np.max(np.abs(y)) + 1e-9)
    return y
