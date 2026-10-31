"""Generate narration per chunk with gates and retries, then join it with measured pauses.

Each segment of a script (one file, for one shot) is generated per chunk (at most ~100 characters, split only at
sentence ends), each chunk gated and regenerated on failure; long one-shot generation drifts and buzzes. Segments
are joined into one master that must pass the whole-track gate before it is written.
"""
# 搬自 sweety-handdraw-video 2.0.2 的 scripts/narration_master.py（MIT，Copyright (c) 2026 threerocks）：
# 分段、句尾清理、逐段门禁和换种子重试照搬；原版按手绘视频的 job.json 组织，这里的 chunks_of / render_segment / build
# 改成按稿子的段落组织：一段一个文件，再拼成整条。
from pathlib import Path
import hashlib
import json
import math
import re
import wave
import numpy as np

SAMPLE_RATE = 48000
MAX_CHUNK_CHARS = 100
MIN_CHUNK_CHARS = 8
SENTENCE_END = '。！？!?…'
CLAUSE_END = '，,、；;：:'
# Spoken characters per second of speech span. Accepted VoxCPM2 films ran 6.3 (snake) and 6.7 (wolf)
# chars/s overall and 5.9-7.5 per sentence group, so 6 would reject both accepted voices; skipped or
# babbled text is caught by ASR coverage, the rate only flags gross stretching or truncation.
SPEECH_RATE_RANGE = (3., 8.)
GENERATION_ATTEMPTS = 3
EDGE_SECONDS = (.06, .1)
# Silence between chunks (speech end to speech start). Measured at punctuation with align.activity:
# accepted VoxCPM2 films (snake, wolf) sentence median .15/.23 s, clause .15/.21 s; 89 sentence ends of
# clean human long-form narration median .60 s. Sentence/beat stay near the model's own cadence, a page
# turn takes the human sentence pause; jobs may override per kind (join_pause_seconds).
# 用在稿子上：beat = 同一个标题下的相邻两段，page = 换了标题。
JOIN_PAUSE_SECONDS = {'clause': .2, 'sentence': .3, 'beat': .4, 'page': .6}
END_TAIL_SECONDS = .3
# Where a chunk really ends. The activity threshold alone cut 0.1 s after "speech", often through a breath or the
# model's own after-sound, with no fade: listeners heard a tick or a clipped extra syllable at sentence ends.
TAIL_QUIET_DB = -40.      # the last syllable has ended once the level stays this far under the chunk peak...
TAIL_QUIET_SECONDS = .03  # ...for this long
TAIL_BURST_DB = -30.      # a sound this loud after that quiet is not speech we asked for (an artifact after the sentence)
TAIL_LOUD_DB = -25.       # a chunk that still ends this loud, with no quiet after its last word, was cut off
TAIL_KEEP_SECONDS = .12   # natural decay and breath kept after the last syllable
FADE_OUT_SECONDS = .05    # shortest raised-cosine fade at a cut, so no edge lands on a sound
FADE_IN_SECONDS = .01


def pieces(text, breaks):
    return re.findall('[^' + breaks + ']+[' + breaks + ']*|[' + breaks + ']+', text)


def pack(parts, limit):
    packed = []
    for part in parts:
        if packed and len(packed[-1]) + len(part) <= limit:
            packed[-1] += part
        else:
            packed.append(part)
    return packed


def split_long(text, limit=MAX_CHUNK_CHARS):
    """A beat over the limit splits at sentence ends; only a single over-long sentence splits at clauses."""
    if len(text) <= limit:
        return [text]
    parts = []
    for sentence in pieces(text, SENTENCE_END):
        parts += [sentence] if len(sentence) <= limit else pack(pieces(sentence, CLAUSE_END), limit)
    return pack(parts, limit)


def to_rate(samples, rate):
    from scipy.signal import resample_poly
    samples = np.asarray(samples, dtype=np.float64).reshape(-1)
    if rate == SAMPLE_RATE:
        return samples
    factor = math.gcd(int(rate), SAMPLE_RATE)
    return resample_poly(samples, SAMPLE_RATE // factor, int(rate) // factor)


def write_pcm(path, samples):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.stem + '.writing.wav')
    with wave.open(str(temporary), 'wb') as stream:
        stream.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
        stream.writeframes(np.clip(np.rint(np.asarray(samples) * 32767), -32768, 32767).astype('<i2').tobytes())
    temporary.replace(path)


def read_pcm(path):
    with wave.open(str(path)) as stream:
        return np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype(np.float64) / 32767


def frame_levels(samples, rate=SAMPLE_RATE):
    """Level of 20 ms frames every 10 ms, in dB under the chunk peak."""
    hop, width = round(.01 * rate), round(.02 * rate)
    if len(samples) < width:
        return np.full(1, -120.)
    peak = max(float(np.abs(samples).max()), 1e-9)
    starts = np.arange(0, len(samples) - width + 1, hop)
    energy = np.concatenate([[0.], np.cumsum(np.asarray(samples, float) ** 2)])
    rms = np.sqrt(np.maximum(energy[starts + width] - energy[starts], 0.) / width)
    return 20 * np.log10(np.maximum(rms, 1e-9) / peak)


def speech_tail(samples, words=None, rate=SAMPLE_RATE):
    """(cut seconds or None, report). The last syllable ends at the first quiet run after the last word starts; a burst
    after that quiet is dropped; None when the chunk still ends loud with no quiet after its last word (cut off)."""
    from align import speech_span
    levels = frame_levels(samples, rate)
    count = len(levels)
    duration = len(samples) / rate
    if words:
        anchor = float(words[-1]['start'])
    else:
        anchor = max(0., speech_span(samples, rate)[1] - .4)
    quiet = max(1, round(TAIL_QUIET_SECONDS / .01))
    first = min(count - 1, max(0, int(anchor / .01)))
    end_frame = None
    for frame in range(first, count - quiet + 1):
        if (levels[frame:frame + quiet] < TAIL_QUIET_DB).all():
            end_frame = frame
            break
    if end_frame is None:
        if levels[-3:].max() > TAIL_LOUD_DB:
            return None, {'status': 'cut_off', 'final_level_db': round(float(levels[-3:].max()), 1)}
        end_frame = first + int(np.argmin(levels[first:]))
    speech_end = end_frame * .01 + .01
    burst = next((frame for frame in range(end_frame + quiet, count) if levels[frame] > TAIL_BURST_DB), None)
    cut = speech_end + TAIL_KEEP_SECONDS
    if burst is not None:
        cut = min(cut, burst * .01 - .01)
    cut = min(max(cut, speech_end + .02), duration)
    report = {'status': 'artifact_dropped' if burst is not None and burst * .01 < duration else 'clean', 'speech_end': round(speech_end, 3),
              'cut': round(cut, 3), 'dropped_seconds': round(duration - cut, 3)}
    return cut, report


def finish_edges(samples, cut, speech_end, rate=SAMPLE_RATE):
    """Cut at `cut` with a raised-cosine fade from the end of speech (at least FADE_OUT_SECONDS) and a short fade-in."""
    samples = np.array(samples[:max(1, round(cut * rate))], float)
    fade = max(round(FADE_OUT_SECONDS * rate), len(samples) - round(speech_end * rate))
    fade = min(fade, len(samples))
    if fade > 1:
        samples[-fade:] *= .5 + .5 * np.cos(np.linspace(0, np.pi, fade))
    lead = min(round(FADE_IN_SECONDS * rate), len(samples))
    if lead > 1:
        samples[:lead] *= .5 - .5 * np.cos(np.linspace(0, np.pi, lead))
    return samples


def clean_edges(samples, words=None, rate=SAMPLE_RATE):
    """(samples ending cleanly after the last syllable, report); samples None when the chunk was cut off mid-sound."""
    cut, report = speech_tail(samples, words, rate)
    if cut is None:
        return None, report
    return finish_edges(samples, cut, report['speech_end'], rate), report


def check_chunk(samples, text, path, asr):
    """Noise gate, speech rate and ASR coverage (asr: True = local ASR when installed, or a callable)."""
    from audio_gate import measure
    from align import speech_span, spoken_syllables, covers, transcribe
    start, end = speech_span(samples)
    rate = spoken_syllables(text) / max(.01, end - start)
    result = {'gate': measure(samples, path.name, short_clip=True), 'chars_per_second': round(rate, 2), 'rate_unit': 'syllables'}
    failures = list(result['gate']['failures'])
    if not SPEECH_RATE_RANGE[0] <= rate <= SPEECH_RATE_RANGE[1]:
        failures.append(f'speech rate {rate:.2f} syllables/s outside {SPEECH_RATE_RANGE}')
    words = (asr if callable(asr) else transcribe)(path) if asr else None
    if words:
        result['asr'] = covers(text, words['text'])
        result['words'] = words['words']
        if result['asr']['status'] != 'pass':
            failures.append(f"ASR does not cover the text (CER {result['asr']['cer']})")
    else:
        result['asr'] = {'status': 'not_available' if asr else 'disabled'}
    return {**result, 'failures': failures, 'status': 'FAIL' if failures else 'PASS'}


def generate_chunk(synthesize, chunk, path, seed, asr):
    """synthesize(text, seed) -> (samples, rate) or (samples, rate, words) when the engine returns timestamps."""
    from align import speech_span
    attempts = []
    for attempt in range(GENERATION_ATTEMPTS):
        audio, rate, *timestamps = synthesize(chunk['text'], seed + attempt)
        audio = to_rate(audio, rate)
        if not len(audio) or not np.isfinite(audio).all():
            attempts.append({'seed': seed + attempt, 'status': 'FAIL', 'failures': ['empty or non-finite audio']})
            continue
        start, end = speech_span(audio)
        first = max(0, round((start - EDGE_SECONDS[0]) * SAMPLE_RATE))
        # Keep a generous tail for now: where speech really ends is decided with the recognized words below.
        audio = audio[first:round((end + .6) * SAMPLE_RATE)]
        write_pcm(path, audio)
        check = check_chunk(read_pcm(path), chunk['text'], path, asr)
        if timestamps and timestamps[0]:
            shift = first / SAMPLE_RATE
            check['words'] = [{**word, 'start': word['start'] - shift, 'end': word['end'] - shift} for word in timestamps[0]]
            check['timestamps'] = 'engine'
        cleaned, tail = clean_edges(read_pcm(path), check.get('words'))
        check['tail'] = tail
        if cleaned is None:
            check['failures'] = check['failures'] + [f"the chunk ends mid-sound ({tail['final_level_db']} dB): the last word is cut off"]
            check['status'] = 'FAIL'
        else:
            write_pcm(path, cleaned)
        attempts.append({'seed': seed + attempt, **check})
        if check['status'] == 'PASS':
            return attempts
    path.unlink(missing_ok=True)
    raise ValueError(f"Chunk failed {GENERATION_ATTEMPTS} attempts: {chunk['text'][:24]}... " + json.dumps([item['failures'] for item in attempts], ensure_ascii=False))


def chunks_of(text, limit=MAX_CHUNK_CHARS):
    """Synthesis chunks of one segment with the kind of pause before each; a piece under MIN_CHUNK_CHARS joins its neighbour."""
    from align import spoken
    chunks = []
    for part in split_long(text, limit):
        if chunks and len(spoken(chunks[-1]['text'])) < MIN_CHUNK_CHARS:
            chunks[-1]['text'] += part
        else:
            chunks.append({'text': part, 'join': None if not chunks else 'sentence' if chunks[-1]['text'][-1] in SENTENCE_END else 'clause'})
    if len(chunks) > 1 and len(spoken(chunks[-1]['text'])) < MIN_CHUNK_CHARS:
        chunks[-2]['text'] += chunks.pop()['text']
    return chunks


def tidy(cues):
    """A cue ends no later than the next one starts."""
    return [(start, min(end, cues[index + 1][0]) if index + 1 < len(cues) else end, text) for index, (start, end, text) in enumerate(cues)]


def render_segment(text, folder, synthesize, identity, seed=2026, asr=True, joins=None):
    """One segment: chunks generated (or reused while text, voice and seed are unchanged) with gates and retries, cleaned at
    the edges and joined with measured pauses. Returns (samples, cues [(start, end, text)] in seconds, chunk records)."""
    from align import caption_texts, piece_ranges
    joins = {**JOIN_PAUSE_SECONDS, **(joins or {})}
    parts, cues, records, cursor = [], [], [], 0
    for chunk in chunks_of(text):
        signature = hashlib.sha256(json.dumps({'identity': identity, 'text': chunk['text'], 'seed': seed}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        path = Path(folder) / f'{signature[:16]}.wav'
        record_path = path.with_suffix('.json')
        record = json.loads(record_path.read_text(encoding='utf-8')) if record_path.is_file() else {}
        if not (path.is_file() and record.get('signature') == signature):
            record = {'signature': signature, 'text': chunk['text'], 'attempts': generate_chunk(synthesize, chunk, path, seed, asr)}
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding='utf-8')
        last = record['attempts'][-1]
        audio, tail = clean_edges(read_pcm(path), last.get('words'))
        if audio is None:
            raise ValueError(f"Chunk ends mid-sound ({tail['final_level_db']} dB): delete {path.name} and its .json to regenerate it")
        if chunk['join']:
            parts.append(np.zeros(round(max(0., joins[chunk['join']] - EDGE_SECONDS[0] - EDGE_SECONDS[1]) * SAMPLE_RATE)))
            cursor += len(parts[-1])
        texts = caption_texts(chunk['text'])
        ranges, _ = piece_ranges(audio, texts, last.get('words'))
        cues += [(cursor / SAMPLE_RATE + left, cursor / SAMPLE_RATE + right, piece) for piece, (left, right) in zip(texts, ranges)]
        parts.append(audio)
        cursor += len(audio)
        records.append({'chunk': path.name, 'text': chunk['text'], 'join': chunk['join'], 'seed': last['seed'], 'attempts': len(record['attempts']),
                        'asr': {key: value for key, value in last.get('asr', {}).items() if key in ('status', 'cer', 'pinyin_cer', 'matched_by', 'asr_text')},
                        'pause_depth_db': last['gate'].get('pause_depth_db'), 'tail': tail})
    return np.concatenate(parts), tidy(cues), records


def build(segments, out, synthesize, identity, seed=2026, asr=True, joins=None, source=None):
    """segments: [(name, section, text)]. Writes NN-名.wav and .srt per segment and manifest.json into out; the joined 全片.wav /
    全片.srt only when the master passes the whole-track gate: a reference with a faint noise floor can pass every short chunk
    and still hum across the joined track. Returns the manifest."""
    from audio_gate import measure
    from minimax_tts import write_srt
    out, joins = Path(out), {**JOIN_PAUSE_SECONDS, **(joins or {})}
    folder = out / '.chunks'
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'manifest.json'
    old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else {}
    rows, master, all_cues, cursor, section_before = [], [], [], 0, None
    for index, (name, section, text) in enumerate(segments, 1):
        if master:
            pause = joins['beat' if section == section_before else 'page']
            master.append(np.zeros(round(max(0., pause - EDGE_SECONDS[0] - EDGE_SECONDS[1]) * SAMPLE_RATE)))
            cursor += len(master[-1])
        section_before = section
        audio, cues, records = render_segment(text, folder, synthesize, identity, seed, asr, joins)
        file = out / f"{index:02d}{('-' + name) if name else ''}.wav"
        write_pcm(file, audio)
        write_srt(file.with_suffix('.srt'), cues)
        start = cursor / SAMPLE_RATE
        all_cues += [(left + start, right + start, piece) for left, right, piece in cues]
        rows.append({'index': index, 'name': name, 'file': file.name, 'text': text, 'start': round(start, 3), 'duration': round(len(audio) / SAMPLE_RATE, 3),
                     'cues': [(round(left, 3), round(right, 3), piece) for left, right, piece in cues],
                     'gate': measure(audio, file.name, short_clip=True), 'chunks': records})
        master.append(audio)
        cursor += len(audio)
    master.append(np.zeros(round(END_TAIL_SECONDS * SAMPLE_RATE)))
    samples = np.concatenate(master)
    gate = measure(samples, '全片')
    files = {row['file'] for row in rows}
    for row in old.get('segments', []):  # segments removed from the script take their files with them
        if row['file'] not in files:
            for stale in (out / row['file'], (out / row['file']).with_suffix('.srt')):
                stale.unlink(missing_ok=True)
    used = {Path(record['chunk']).stem for row in rows for record in row['chunks']}
    for stale in folder.iterdir():
        if stale.stem not in used:
            stale.unlink()
    joined = out / '全片.wav'
    for stale in (joined, joined.with_suffix('.srt')):
        stale.unlink(missing_ok=True)
    if gate['status'] == 'PASS':
        write_pcm(joined, samples)
        write_srt(joined.with_suffix('.srt'), tidy(all_cues))
    manifest = {'source': source, 'engine': identity, 'seed': seed, 'join_pause_seconds': joins, 'total_duration': round(len(samples) / SAMPLE_RATE, 3),
                'joined': joined.name if gate['status'] == 'PASS' else None, 'gate': gate, 'subjective_listening': 'not_performed', 'segments': rows}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    return manifest
