#!/usr/bin/env python3
"""Cut a clean 8-15 s cloning reference that ends at a sentence boundary; originals are never changed.

DeepFilterNet3 (mlx-audio, weights mlx-community/DeepFilterNet-mlx v3) removes the noise floor before the cut. The
result must pass audio_gate and cover the exact transcript in local ASR.
"""
# 搬自 sweety-handdraw-video 2.0.2 的 scripts/clean_reference.py（MIT，Copyright (c) 2026 threerocks）。
# 去掉了 HTDemucs 人声分离（要 PyTorch；自己在安静处录的用不上）；DeepFilterNet3 改为在本环境里直接调用；
# 不给起止时间时取整段的语音范围。
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from audio_gate import decode, measure, SAMPLE_RATE
from align import activity, covers, speech_span, transcribe

LEAD_SECONDS = .15
TAIL_SECONDS = (.5, .8)
DURATION_RANGE = (8., 15.)
PEAK_DBFS = -3.


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_wav(path, samples, rate=SAMPLE_RATE):
    wavfile.write(path, rate, np.clip(np.rint(samples * 32767), -32768, 32767).astype('<i2'))


def boundaries(samples, start, end):
    """Snap a requested window to the real speech onset after start and the sentence end near end."""
    active = activity(samples)
    first, last = round(start * 100), min(len(active) - 1, round(end * 100))
    onset = next((index for index in range(max(0, first - 40), min(len(active), first + 60)) if active[index] and not active[max(0, index - 15):index].any()), None)
    candidates = [index for index in range(max((onset or 0) + 1, last - 60), min(len(active) - 1, last + 60)) if active[index] and not active[index + 1:index + 26].any()]
    if onset is None or not candidates:
        raise ValueError('No pause-bounded sentence near --start/--end (within 0.6 s); choose times at real sentence boundaries')
    offset = min(candidates, key=lambda index: abs(index - last))
    following = next((index for index in range(offset + 1, len(active)) if active[index]), len(active))
    return onset * .01, offset * .01 + .02, (following - offset) * .01 - .02


def denoise(samples):
    """DeepFilterNet3 on 48 kHz mono; same length, so the timeline stays."""
    from mlx_audio.sts.models.deepfilternet import DeepFilterNetModel
    enhanced = np.asarray(DeepFilterNetModel.from_pretrained().enhance_array(np.asarray(samples, dtype=np.float32)), dtype=np.float64)
    if len(enhanced) != len(samples) or not np.isfinite(enhanced).all():
        raise ValueError('DeepFilterNet3 changed the length or produced non-finite audio')
    return enhanced


def clean(source, transcript, output, start=None, end=None, context=3., denoise_noise=True, asr=True):
    source, output = Path(source).resolve(), Path(output).resolve()
    if (output/'reference.wav').exists():
        raise ValueError('Output already has a reference; choose a new directory so earlier files stay intact')
    output.mkdir(parents=True, exist_ok=True)
    if start is None or end is None:
        first, last = speech_span(decode(source))
        start, end = first if start is None else start, last if end is None else end
    window_start = max(0., start - context)
    raw = decode(source, window_start, end + context - window_start)
    cleaned = denoise(raw) if denoise_noise else raw
    steps = [{'model': 'DeepFilterNet3 MLX', 'weights': 'mlx-community/DeepFilterNet-mlx v3', 'timeline_preserved': True}] if denoise_noise else []
    onset, offset, gap = boundaries(cleaned, start - window_start, end - window_start)
    first = max(0, round((onset - LEAD_SECONDS) * SAMPLE_RATE))
    natural = min(max(0., gap - .05), TAIL_SECONDS[1])
    stop = round((offset + natural) * SAMPLE_RATE)
    padding = max(0., TAIL_SECONDS[0] - natural)
    fade = np.linspace(1, 0, round(.01 * SAMPLE_RATE))
    reference = cleaned[first:stop].copy()
    reference[-len(fade):] *= fade
    reference = np.concatenate([reference, np.zeros(round(padding * SAMPLE_RATE))])
    duration = len(reference) / SAMPLE_RATE
    if not DURATION_RANGE[0] <= duration <= DURATION_RANGE[1]:
        raise ValueError(f'Reference must be {DURATION_RANGE[0]:.0f}-{DURATION_RANGE[1]:.0f} s after snapping to sentence boundaries; got {duration:.2f} s')
    gain = 10 ** (PEAK_DBFS / 20) / np.abs(reference).max()
    reference *= gain
    target = output/'reference.wav'
    write_wav(target, reference)
    (output/'transcript.txt').write_text(transcript.strip() + '\n')
    record = {'source': str(source), 'source_sha256': sha256(source), 'requested_seconds': [start, end],
              'used_seconds': [round(window_start + first / SAMPLE_RATE, 3), round(window_start + offset, 3)],
              'tail': {'natural_seconds': round(natural, 3), 'padded_seconds': round(padding, 3)}, 'gain_db': round(20 * np.log10(gain), 2),
              'steps': steps or [{'note': 'denoise skipped; trimmed only'}],
              'gate_before': measure(raw[first:stop], 'source window', True), 'gate_after': measure(reference, str(target), True),
              'reference_sha256': sha256(target), 'transcript_sha256': hashlib.sha256(transcript.strip().encode()).hexdigest(),
              'duration_seconds': round(duration, 3), 'listening': 'pending'}
    record['asr'] = covers(transcript, transcribe(target)['text'], homophones=False) if asr else {'status': 'disabled'}
    (output/'clean-record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2))
    if record['gate_after']['status'] != 'PASS' or record['asr']['status'] == 'fail':
        raise ValueError('Cleaned reference failed: ' + json.dumps({'gate': record['gate_after']['failures'], 'asr': record['asr']}, ensure_ascii=False))
    return record


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path)
    parser.add_argument('--start', type=float, help='Approximate start of the first sentence (s); default: where speech starts')
    parser.add_argument('--end', type=float, help='Approximate end of the last sentence (s); default: where speech ends')
    parser.add_argument('--transcript', type=Path, required=True, help='Exact transcript of exactly that span')
    parser.add_argument('--output', type=Path, required=True, help='New directory; never overwritten')
    parser.add_argument('--no-denoise', action='store_true')
    parser.add_argument('--no-asr', action='store_true')
    arguments = parser.parse_args()
    result = clean(arguments.source, arguments.transcript.read_text(), arguments.output, arguments.start, arguments.end,
                   denoise_noise=not arguments.no_denoise, asr=not arguments.no_asr)
    print(json.dumps({key: result[key] for key in ('used_seconds', 'duration_seconds', 'gate_after', 'asr')}, ensure_ascii=False, indent=2))
