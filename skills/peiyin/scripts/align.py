"""Compare narration with what local ASR heard, find speech and pauses, and time caption cues.

Caption cues come from Whisper word timestamps when available, otherwise from a deterministic pause split:
N pieces use the N-1 most prominent pauses.
"""
# 搬自 sweety-handdraw-video 2.0.2 的 scripts/align.py（MIT，Copyright (c) 2026 threerocks）。
# 只留配音要用的部分；Whisper 改为在本环境里直接调用（原版起子进程），字幕切分只留按分句打包的默认方式。
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import re
import unicodedata
import numpy as np

SAMPLE_RATE = 48000
PUNCTUATION = set('，。！？；：、“”‘’（）《》〈〉【】—…·,.!?;:"\'()[]<>-~ \n\t')
SENTENCE_END = '。！？!?…'
CAPTION_BREAKS = '。！？!?…；;，,、：:'
MAX_CAPTION_CHARS = 24
MIN_PAUSE_SECONDS = .08
SYNC_TOLERANCE_SECONDS = .3
# Clause breaks in fluent narration can be 30-50 ms; shifting cues by 0.4 s still fails nearly every cue.
SYNC_PAUSE_SECONDS = .03
ASR_MODEL = 'mlx-community/whisper-large-v3-turbo'

CHINESE_DIGITS = dict(zip('零〇一二两三四五六七八九', (0, 0, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9)))
CHINESE_UNITS = {'十': 10, '百': 100, '千': 1000, '万': 10 ** 4, '亿': 10 ** 8}
NUMBER_DIGITS = '0-9零〇一二两三四五六七八九'
NUMBER_PATTERN = '[' + NUMBER_DIGITS + '十百千万亿]+(?:[.点][' + NUMBER_DIGITS + '十百千万亿]+)*'


def spoken(text):
    # A decimal point carries a value; sentence punctuation does not.
    return ''.join(character for index, character in enumerate(text)
                   if character not in PUNCTUATION or (character == '.' and 0 < index < len(text) - 1
                       and text[index - 1].isdigit() and text[index + 1].isdigit()))


def chinese_number(text):
    """Parse exact Chinese/Arabic magnitude notation without float rounding or range guessing."""
    normalized = ''.join(str(CHINESE_DIGITS.get(character, character)) for character in text).replace('点', '.')
    # Adjacent spoken nonzero digits can be an approximation (两三万, 四五十), not 23/45.
    if re.search('[一二两三四五六七八九]{2}', text) and len(text) < 4:
        return text

    def value(token):
        for unit in ('亿', '万'):
            if unit in token:
                if token.count(unit) != 1:
                    raise ValueError('Repeated magnitude')
                left, right = token.split(unit)
                return value(left or '1') * CHINESE_UNITS[unit] + (value(right) if right else 0)
        total, previous, cursor = Decimal(0), 10000, 0
        for match in re.finditer(r'([0-9]+(?:\.[0-9]+)?)?([十百千])', token):
            if match.start() != cursor or CHINESE_UNITS[match[2]] >= previous:
                raise ValueError('Invalid small-unit order')
            previous = CHINESE_UNITS[match[2]]
            total += Decimal(match[1] or '1') * previous
            cursor = match.end()
        return total + (Decimal(token[cursor:]) if token[cursor:] else 0)

    try:
        result = format(value(normalized), 'f')
        return result.rstrip('0').rstrip('.') if '.' in result else result
    except (InvalidOperation, ValueError):
        return text


def numbers(text):
    """Normalize comparison text only; retain different magnitudes, fractions and signs."""
    text = unicodedata.normalize('NFKC', text)
    text = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', text)
    text = re.sub('百分之(' + NUMBER_PATTERN + ')', lambda match: chinese_number(match[1]) + '%', text)
    text = re.sub(NUMBER_PATTERN, lambda match: chinese_number(match[0]), text)
    return re.sub(r'-(?=\d)', '负', text)


def edit_rate(expected, actual):
    """Levenshtein distance over any two sequences, divided by the expected length."""
    row = np.arange(len(actual) + 1)
    for index, item in enumerate(expected, 1):
        previous, row = row, np.empty_like(row)
        row[0] = index
        for column, other in enumerate(actual, 1):
            row[column] = min(previous[column] + 1, row[column - 1] + 1, previous[column - 1] + (item != other))
    return float(row[-1] / max(1, len(expected)))


def cer(expected, actual):
    return edit_rate(spoken(numbers(expected)), spoken(numbers(actual)))


def syllables(text):
    """Toneless pinyin per Han character in context; digits, Latin letters and signs stay one token each."""
    from pypinyin import lazy_pinyin
    return lazy_pinyin(text, errors=lambda other: list(other))


def anchored(expected, actual, error, max_cer):
    blocks = [block for block in SequenceMatcher(None, expected, actual, autojunk=False).get_matching_blocks() if block.size]
    return bool(blocks) and error <= max_cer and blocks[0].a <= 2 and blocks[-1].a + blocks[-1].size >= len(expected) - 2


def covers(expected, actual, max_cer=.15, homophones=True):
    """ASR must cover the whole text: low CER and matched characters near both ends (numbers compared by value).

    Whisper writes rare characters as common homophones (蓑笠 -> 梭利, 钓 -> 吊, 大雪 -> 大学), which fails short
    classical lines that were read correctly. With homophones=True a failing character comparison is checked again on
    toneless pinyin (when pypinyin is installed): homophones pass; skipped, babbled or misread numbers still fail.
    Verbatim transcripts (voice references) pass homophones=False."""
    raw_expected, raw_actual = expected, actual
    expected, actual = spoken(numbers(expected)), spoken(numbers(actual))
    error = edit_rate(expected, actual)
    result = {'cer': round(error, 3), 'status': 'pass' if anchored(expected, actual, error, max_cer) else 'fail',
              'asr_text': raw_actual, 'comparison_text': actual}
    if result['status'] == 'fail' and homophones:
        # Number normalization reads a homophone as a numeral (牵牛 heard as 千牛 -> 1000牛), so the pinyin check also
        # compares the unnormalized text; a misread number differs in both forms.
        try:
            pairs = [(syllables(e), syllables(a)) for e, a in ((expected, actual), (spoken(raw_expected), spoken(raw_actual)))]
        except ImportError:
            result['pinyin'] = 'unavailable'
        else:
            scored = [(edit_rate(e, a), e, a) for e, a in pairs]
            pinyin_error, expected_syllables, actual_syllables = min(scored, key=lambda item: item[0])
            result['pinyin_cer'] = round(pinyin_error, 3)
            if anchored(expected_syllables, actual_syllables, pinyin_error, max_cer):
                result.update(status='pass', matched_by='pinyin')
    return result


def char_times(text, words):
    """Map every spoken character of text to (start, end) seconds through ASR/aligner/TTS word times."""
    recognized = []
    for word in words:
        characters = spoken(word['text'])
        step = (word['end'] - word['start']) / max(1, len(characters))
        recognized += [(character, word['start'] + index * step, word['start'] + (index + 1) * step) for index, character in enumerate(characters)]
    expected = spoken(text)
    times = [None] * len(expected)
    matcher = SequenceMatcher(None, expected, ''.join(item[0] for item in recognized), autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == 'equal' or (tag == 'replace' and a1 - a0 == b1 - b0):
            for offset in range(a1 - a0):
                times[a0 + offset] = recognized[b0 + offset][1:]
    known = [index for index, value in enumerate(times) if value]
    if not known:
        raise ValueError('Timestamps do not match the narration text')
    for index, value in enumerate(times):
        if value is None:  # interpolate unmatched characters between their matched neighbours
            left = max((k for k in known if k < index), default=None)
            right = min((k for k in known if k > index), default=None)
            start = times[left][1] if left is not None else times[right][0]
            end = times[right][0] if right is not None else times[left][1]
            times[index] = (start, max(start, end))
    return times, round(len(known) / len(expected), 3)


def activity(samples, rate=SAMPLE_RATE):
    hop, width = round(.01 * rate), round(.02 * rate)
    samples = np.asarray(samples, dtype=np.float64)
    if len(samples) < width:
        return np.zeros(0, dtype=bool)
    count = 1 + (len(samples) - width) // hop
    # Frame energy from a running sum: the same values as a frame matrix without its memory (an 11-minute master is GBs).
    energy = np.concatenate([[0.], np.cumsum(samples * samples)])
    starts = hop * np.arange(count)
    levels = 20 * np.log10(np.sqrt(np.maximum(energy[starts + width] - energy[starts], 0.) / width) + 1e-9)
    threshold = max(np.percentile(levels, 95) - 35, np.percentile(levels, 10) + 6)
    return levels > threshold


def speech_span(samples, rate=SAMPLE_RATE):
    active = np.flatnonzero(activity(samples, rate))
    if not len(active):
        raise ValueError('No speech found')
    return active[0] * .01, active[-1] * .01 + .02


def pauses(samples, rate=SAMPLE_RATE, minimum=MIN_PAUSE_SECONDS):
    """Interior quiet runs as (start, end) seconds, between the first and last speech frames."""
    active = activity(samples, rate)
    found, start = [], None
    first, last = np.flatnonzero(active)[[0, -1]]
    for index in range(first, last + 1):
        if not active[index] and start is None:
            start = index
        elif active[index] and start is not None:
            if (index - start) * .01 >= minimum:
                found.append((start * .01 + .02, index * .01))
            start = None
    return found


def onsets(samples, rate=SAMPLE_RATE, minimum=.05):
    first, _ = speech_span(samples, rate)
    return [first] + [end for _, end in pauses(samples, rate, minimum)]


def pause_split(samples, weights, rate=SAMPLE_RATE):
    """Ranges for consecutive text pieces: the N-1 longest pauses, unless that gives implausible rates."""
    start, end = speech_span(samples, rate)
    if len(weights) == 1:
        return [(start, end)], 'single'
    found = pauses(samples, rate)
    def ranges(chosen):
        edges = [start] + [value for pause in chosen for value in pause] + [end]
        return [(edges[2 * index], edges[2 * index + 1]) for index in range(len(weights))]
    def plausible(result):
        return all(weight < 3 or 1.5 <= weight / max(.01, right - left) <= 10 for weight, (left, right) in zip(weights, result))
    longest = sorted(sorted(found, key=lambda pause: pause[1] - pause[0])[-(len(weights) - 1):]) if len(found) >= len(weights) - 1 else []
    if longest and plausible(ranges(longest)):
        return ranges(longest), 'longest_pauses'
    chosen, total, cursor = [], sum(weights), start
    for share in np.cumsum(weights)[:-1] / total:
        expected = start + share * (end - start)
        window = max(.8, .25 * (end - start))
        nearby = [pause for pause in found if pause[0] > cursor and abs((pause[0] + pause[1]) / 2 - expected) <= window]
        pick = max(nearby, key=lambda pause: pause[1] - pause[0]) if nearby else (expected, expected)
        chosen.append(pick)
        cursor = pick[1]
    return ranges(chosen), 'pauses_near_text_proportion'


def caption_texts(text, limit=MAX_CAPTION_CHARS):
    """Cue texts joining back to text: clauses packed up to limit characters, a long clause stays whole."""
    clauses = re.findall('[^' + CAPTION_BREAKS + ']+[' + CAPTION_BREAKS + ']*|[' + CAPTION_BREAKS + ']+', text)
    pieces = []
    for clause in clauses:
        if pieces and (not spoken(clause) or len(pieces[-1]) + len(clause) <= limit):
            pieces[-1] += clause
        else:
            pieces.append(clause)
    return pieces


def ranges_from_times(texts, times):
    result, cursor = [], 0
    for text in texts:
        count = len(spoken(text))
        result.append((times[cursor][0], times[cursor + count - 1][1]) if count else (times[max(0, cursor - 1)][1],) * 2)
        cursor += count
    return result


def snap_to_onsets(found, ranges, tolerance=SYNC_TOLERANCE_SECONDS / 2):
    """ASR character times can sit a second away from the voice. A piece that starts away from every speech onset
    (by more than half the sync tolerance, leaving room for the encoded track) moves to the nearest onset inside it;
    with no pause there the speech is fluent, so the previous piece runs on to it without a gap.
    found: onset seconds on the same clock as ranges."""
    found = np.asarray(found, float)
    result = [list(span) for span in ranges]
    for index in range(1, len(result)):
        start, end = result[index]
        if len(found) and np.min(np.abs(found - start)) <= tolerance:
            continue
        inside = found[(found > result[index - 1][0] + .25) & (found < end - .25)] if len(found) else found
        if len(inside):
            start = float(inside[np.argmin(np.abs(inside - start))])
            result[index][0] = start
        result[index - 1][1] = start
    return [tuple(span) for span in result]


def piece_ranges(samples, texts, words=None, rate=SAMPLE_RATE):
    """Ranges (seconds within samples) for consecutive text pieces, from timestamps or pauses."""
    if words:
        times, matched = char_times(''.join(texts), words)
        found = onsets(samples, rate, SYNC_PAUSE_SECONDS)
        ranges = ranges_from_times(texts, times)
        # Speech before the first recognized word (a lone syllable the recognizer dropped, such as an onomatopoeia
        # "叮") belongs to the first piece; otherwise that piece would get no time at all.
        if len(found) and found[0] < ranges[0][0] - SYNC_TOLERANCE_SECONDS / 2:
            ranges[0] = (float(found[0]), ranges[0][1])
        return snap_to_onsets(found, ranges), f'timestamps (matched {matched:.0%})'
    return pause_split(samples, [max(1, len(spoken(text))) for text in texts], rate)


def transcribe(path, model=ASR_MODEL, language='zh'):
    """Text and word timestamps from local Whisper (mlx-whisper); traditional characters folded to simplified when OpenCC is installed."""
    import mlx_whisper
    result = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, language=language, word_timestamps=True)
    try:
        from opencc import OpenCC
        convert = OpenCC('t2s').convert if language == 'zh' else (lambda text: text)
    except ImportError:
        convert = lambda text: text
    words = [{'text': convert(word['word']).strip(), 'start': word['start'], 'end': word['end']}
             for segment in result['segments'] for word in segment.get('words', [])]
    return {'text': convert(result['text']), 'words': words}


def spoken_syllables(text):
    """Spoken syllables, the unit of the speech-rate gates: one per CJK character, vowel groups per Latin word
    (an all-caps acronym is spelled letter by letter), one per digit. Counting "All In AI" as seven characters made
    a normal line read as too fast."""
    count = 0
    for token in re.findall(r'[\u3400-\u9fff\uf900-\ufaff]|[A-Za-z]+|\d', text):
        if len(token) == 1 and '\u3400' <= token <= '\ufaff' or token.isdigit():
            count += 1
        elif token.isupper() and len(token) <= 5:
            count += len(token) + sum(letter == 'W' for letter in token)
        else:
            groups = re.findall(r'[aeiouy]+', token.lower())
            count += max(1, len(groups) - (token.lower().endswith('e') and len(groups) > 1))
    return count
