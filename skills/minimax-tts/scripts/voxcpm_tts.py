#!/usr/bin/env python3
"""本机 VoxCPM2 配音（mlx-audio，Apple Silicon，不花钱）：整篇稿子分段配音、念一句、设计声音、管声音库、清洗参考录音。

门禁照搬 sweety-handdraw-video：每个生成块都过门禁（嗡声、停顿不安静、削波、语速、Whisper 按拼音对稿），不过就换种子，
最多 3 次；整条拼好再过一次，不过不出「全片」。新声音入库前先查参考录音，再用它试念一段过门禁。
在 ~/.venvs/voxcpm2 里跑；用法见 --help 和上一层的 SKILL.md。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

from align import ASR_MODEL, spoken

HOME = Path.home() / ".local/share/voxcpm-tts"
VOICES = HOME / "voices"
CONFIG = HOME / "config.json"
MODEL = "mlx-community/VoxCPM2-8bit"
DENOISER = "mlx-community/DeepFilterNet-mlx"
CONSENT = {"self": "本人录音", "authorized": "获得授权的他人录音", "designed": "声音设计造的，不对应真人"}
# 声音设计念这段当参考（约 10 秒、句末收住），之后克隆时它就是逐字稿
DESIGN_TEXT = "大家好，今天聊一件小事。很多人以为做计划最难的是开始，其实最难的是估时间：一件事到底要多久，我们总是想得太乐观。所以这期，我想换个办法。"
# 新声音入库前用它试念（约 12 秒，一个生成块），按整条音轨的口径过门禁：参考里听不出的底噪，克隆出来常常变成嗡声
TRIAL_TEXT = "我们先看一组数字：上个月一共记了一百二十件事，真正按计划完成的，不到一半。问题不在执行力，而在估时间这一步。下面我用三个例子，一个一个讲清楚，你可以对照一下自己的情况。"
REFERENCE_SECONDS = (5., 30.)   # 官方说 5–30 秒都行；clean 裁出来的是 8–15 秒


def die(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def hub(repo):
    return Path(os.environ.get("HF_HUB_CACHE", Path.home() / ".cache/huggingface/hub")) / ("models--" + repo.replace("/", "--"))


def prepare(*repos):
    """在 import mlx-audio 之前定联网方式：模型都下好了就离线（省掉每次联网检查）；要下载时关掉 Xet（走代理时它很慢）。"""
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    if all((hub(repo) / "snapshots").is_dir() for repo in repos):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")


# ---------- 模型 ----------

_model = None


def model():
    global _model
    if _model is None:
        from mlx_audio.tts.utils import load
        _model = load(MODEL)
    return _model


def synthesizer(reference=None, transcript=None, design=None, steps=10):
    """synthesize(text, seed) → (samples, rate)。有参考 = 高保真克隆（参考 + 逐字稿），没有 = 声音设计。"""
    import mlx.core as mx
    import numpy as np

    def synthesize(text, seed):
        mx.random.seed(seed)
        kwargs = {"text": text, "inference_timesteps": steps, "cfg_value": 2.0, "max_tokens": len(text) * 6 + 10}
        if reference:
            kwargs.update(ref_audio=str(reference), prompt_audio=str(reference), prompt_text=transcript)
        else:
            kwargs["instruct"] = design
        result = list(model().generate(**kwargs))
        return np.concatenate([np.asarray(c.audio) for c in result]).astype(np.float32), result[0].sample_rate
    return synthesize


# ---------- 声音库 ----------

def config():
    return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}


def save_config(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def voice(name=None):
    """(名字, 参考 wav, 逐字稿, voice.json)。参考被改过就停下：克隆用的必须是入库时验过的那份。"""
    name = name or config().get("default")
    if not name:
        die("声音库里还没有声音。先 design 或 clean 出一段参考，再 voice add（见 SKILL.md「第一次用」）")
    folder = VOICES / name
    if not (folder / "voice.json").is_file():
        die(f"声音库里没有「{name}」。voice list 看有哪些")
    meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
    if sha256(folder / "reference.wav") != meta["reference_sha256"]:
        die(f"「{name}」的参考录音入库后被改过，重新 voice add")
    return name, folder / "reference.wav", meta["transcript"], meta


def identity(name, meta, steps):
    """会影响声音的一切；变了就不沿用之前生成的块。"""
    return {"engine": "voxcpm2-mlx", "model": MODEL, "voice": name, "mode": "combined", "reference_sha256": meta["reference_sha256"],
            "reference_text": meta["transcript"], "cfg_value": 2.0, "timesteps": steps}


def check_reference(audio, transcript):
    """参考录音要干净（短片段门禁）、长 5–30 秒，逐字稿要盖住整段：语速 2.5–8 字/秒，Whisper 逐字对上（不放过同音字）。"""
    from audio_gate import decode, measure, SAMPLE_RATE
    from align import covers, speech_span, transcribe
    samples = decode(audio)
    gate = measure(samples, Path(audio).name, short_clip=True)
    start, end = speech_span(samples)
    rate = len(spoken(transcript)) / max(.01, end - start)
    heard = covers(transcript, transcribe(audio)["text"], homophones=False)
    seconds = len(samples) / SAMPLE_RATE
    problems = list(gate["failures"])
    if not REFERENCE_SECONDS[0] <= seconds <= REFERENCE_SECONDS[1]:
        problems.append(f"长 {seconds:.1f} 秒，要 5–30 秒（最好 8–15 秒）")
    if not 2.5 <= rate <= 8:
        problems.append(f"逐字稿和录音对不上：每秒 {rate:.1f} 个字（正常 2.5–8）")
    if heard["status"] != "pass":
        problems.append(f"Whisper 听到的和逐字稿不一致（字错率 {heard['cer']}）：{heard['asr_text']}")
    return samples, {"seconds": round(seconds, 2), "pause_depth_db": gate.get("pause_depth_db"), "chars_per_second": round(rate, 2),
                     "asr_cer": heard["cer"], "problems": problems}


def trial(folder, name, transcript, steps, seed):
    """用这个声音试念 TRIAL_TEXT，按整条音轨的口径过门禁。返回 (报告, 问题列表)。"""
    from audio_gate import measure
    from narration import render_segment, write_pcm
    reference = folder / "reference.wav"
    meta = {"reference_sha256": sha256(reference), "transcript": transcript}
    try:
        samples, _, records = render_segment(TRIAL_TEXT, folder / ".trial", synthesizer(reference, transcript, steps=steps), identity(name, meta, steps), seed)
    except ValueError as error:
        return {}, [f"试念的生成块 3 个种子都没过：{error}"]
    finally:
        shutil.rmtree(folder / ".trial", ignore_errors=True)
    write_pcm(folder / "试念.wav", samples)
    gate = measure(samples, "试念.wav")
    return {"pause_depth_db": gate.get("pause_depth_db"), "tonal_lines_hz": gate.get("tonal_lines_hz_persistence"),
            "seeds_tried": [r["attempts"] for r in records]}, gate["failures"]


def cmd_voice_add(args):
    from narration import write_pcm
    name = args.name.strip()
    if not name or "/" in name or name.startswith("."):
        die("声音名不能带 /，也不能以 . 开头")
    folder = VOICES / name
    if folder.exists():
        die(f"声音库里已经有「{name}」了：换个名字，或者先把 {folder} 挪走")
    audio = Path(args.audio).expanduser()
    if not audio.is_file():
        die(f"没有这个文件：{audio}")
    beside = audio.parent / "transcript.txt"
    transcript = (args.text or (beside.read_text(encoding="utf-8") if beside.is_file() else "")).strip()
    if not transcript:
        die("要给参考录音的逐字稿：--text，或者参考旁边放 transcript.txt（clean 和 design 会自动写）")
    print(f"检查参考 {audio} …")
    samples, check = check_reference(audio, transcript)
    if check["problems"]:
        die("参考没过检查，没有加进声音库：\n  " + "\n  ".join(check["problems"]) + "\n先用 clean 降噪、裁到句末，再来加")
    folder.mkdir(parents=True)
    write_pcm(folder / "reference.wav", samples)          # 统一成 48 kHz、单声道、16 位
    (folder / "transcript.txt").write_text(transcript + "\n", encoding="utf-8")
    print(f"参考没问题（停顿深度 {check['pause_depth_db']} dB）。用它试念一段过门禁 …")
    report, problems = trial(folder, name, transcript, args.steps, args.seed)
    if problems:
        shutil.rmtree(folder)
        die("试念没过门禁，没有加进声音库：\n  " + "\n  ".join(problems) +
            "\n参考里多半带着听不出来的底噪：用 clean 降噪后再加，或者换一条参考")
    design = audio.parent.parent / "design.json"
    meta = {"name": name, "consent": args.consent, "consent_note": CONSENT[args.consent], "transcript": transcript,
            "reference_sha256": sha256(folder / "reference.wav"), "source": str(audio),
            "design": json.loads(design.read_text(encoding="utf-8")).get("description") if design.is_file() else None,
            "steps": args.steps, "reference_check": check, "trial": report, "listening": "pending", "added": time.strftime("%Y-%m-%d %H:%M")}
    (folder / "voice.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    cfg = config()
    if not cfg.get("default"):
        cfg["default"] = name
        save_config(cfg)
    print(f"✓ 「{name}」进了声音库{'，设成了默认声音' if cfg['default'] == name else ''}。试念停顿深度 {report['pause_depth_db']} dB。\n"
          f"  门禁只能抓明显的毛病，先听一遍：{folder / '试念.wav'}")


def cmd_voice_list(args):
    default = config().get("default")
    folders = sorted(p for p in VOICES.glob("*") if (p / "voice.json").is_file()) if VOICES.exists() else []
    if not folders:
        print("声音库是空的。先 design 或 clean 出一段参考，再 voice add")
    for folder in folders:
        meta = json.loads((folder / "voice.json").read_text(encoding="utf-8"))
        print(f"{'*' if folder.name == default else ' '} {folder.name:<12} {meta['consent_note']:<16} 试念停顿 {meta['trial']['pause_depth_db']} dB  "
              f"步数 {meta['steps']}  {meta['added']}{'  ' + meta['design'] if meta.get('design') else ''}")


def cmd_voice_default(args):
    if not (VOICES / args.name / "voice.json").is_file():
        die(f"声音库里没有「{args.name}」")
    save_config({**config(), "default": args.name})
    print(f"✓ 默认声音改成「{args.name}」")


# ---------- 生成 ----------

def speakable(text):
    """MiniMax 才认的停顿 <#0.5#> 和语气词 (laughs) 去掉；段内换行接起来（中文不加空格）。"""
    text = re.sub(r"<#[\d.]+#>", "", text)
    text = re.sub(r"\([a-z ]+\)", "", text)
    return re.sub(r"\s*\n\s*", "", text).strip()


def cmd_script(args):
    from minimax_tts import segments_of
    from narration import build, chunks_of
    src = Path(args.file).expanduser()
    if not src.is_file():
        die(f"没有这个文件：{src}")
    segs = segments_of(src.read_text(encoding="utf-8"), args.keep_brackets)
    if args.only:                                                    # 稿子里常带标题备选、封面说明这些不念的章节：只留标题里带这个词的
        segs = [(n, t) for n, t in segs if args.only in n]
    segs = [(name, name, speakable(text)) for name, text in segs]   # (段名, 所在章节, 要念的字)：段名就是它上面的标题
    segs = [s for s in segs if s[2]]
    if not segs:
        die("稿子里没有要念的字")
    chars = sum(len(spoken(t)) for *_, t in segs)
    print(f"{src.name}：{len(segs)} 段，{sum(len(chunks_of(t)) for *_, t in segs)} 个生成块，约 {chars} 字，念出来约 {chars / 6.5 / 60:.1f} 分钟")
    if args.dry_run:
        for i, (name, _, text) in enumerate(segs, 1):
            print(f"  {i:02d} {('[' + name + '] ') if name else ''}{len(chunks_of(text))} 块  {text[:36]}{'…' if len(text) > 36 else ''}")
        return
    name, reference, transcript, meta = voice(args.voice)
    steps = args.steps or meta.get("steps", 10)
    out = Path(args.output).expanduser() if args.output else src.with_suffix("")
    if args.force:
        shutil.rmtree(out / ".chunks", ignore_errors=True)
    print(f"声音「{name}」，输出到 {out}/")
    began = time.perf_counter()
    try:
        manifest = build(segs, out, synthesizer(reference, transcript, steps=steps), identity(name, meta, steps), seed=args.seed, source=str(src))
    except ValueError as error:
        die(f"有一块 3 个种子都没过门禁，停下了：{error}\n"
            "改写这一句（避开多音字、英文、阿拉伯数字），或者换个声音再跑；已经过关的块下次直接沿用")
    for row in manifest["segments"]:
        retried = sum(c["attempts"] - 1 for c in row["chunks"])
        warn = "  ⚠ " + "；".join(row["gate"]["failures"]) if row["gate"]["status"] != "PASS" else ""
        print(f"  {row['index']:02d} {row['duration']:5.1f} 秒  {row['file']}{f'  换了 {retried} 次种子' if retried else ''}{warn}")
    gate = manifest["gate"]
    if not manifest["joined"]:
        die(f"整条拼起来没过门禁，没出「全片」：{'；'.join(gate['failures'])}\n"
            f"  各段的文件和 manifest.json 都在 {out}/，每段的门禁结果记在 manifest 里。\n"
            "  嗡声、底噪多半出在参考声音上：用 clean 给参考降噪后重新 voice add，或者换个声音")
    print(f"✓ 全片 {manifest['total_duration']:.1f} 秒，整条门禁通过（停顿深度 {gate['pause_depth_db']} dB），用时 {time.perf_counter() - began:.0f} 秒\n"
          f"  {out / manifest['joined']}、全片.srt、每段的 wav 和 srt、manifest.json\n  门禁只能抓明显的毛病，交付前完整听一遍")


def cmd_say(args):
    from narration import SAMPLE_RATE, render_segment, write_pcm
    text = speakable(args.text if args.text != "-" else sys.stdin.read())
    if not text:
        die("没有要念的字")
    name, reference, transcript, meta = voice(args.voice)
    steps = args.steps or meta.get("steps", 10)
    out = Path(args.output or f"配音-{time.strftime('%m%d-%H%M%S')}.wav").expanduser()
    with tempfile.TemporaryDirectory() as cache:
        try:
            samples, _, records = render_segment(text, cache, synthesizer(reference, transcript, steps=steps), identity(name, meta, steps), args.seed)
        except ValueError as error:
            die(f"3 个种子都没过门禁：{error}\n改写这一句，或者换个声音")
    write_pcm(out, samples)
    retried = sum(r["attempts"] - 1 for r in records)
    print(f"✓ {out}  {len(samples) / SAMPLE_RATE:.1f} 秒（声音「{name}」{f'，换了 {retried} 次种子' if retried else ''}）")


def cmd_design(args):
    from clean_reference import clean
    from narration import to_rate, write_pcm
    out = Path(args.output).expanduser() if args.output else HOME / "candidates" / time.strftime("%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "design.json").write_text(json.dumps({"description": args.description, "text": DESIGN_TEXT}, ensure_ascii=False, indent=1), encoding="utf-8")
    synthesize = synthesizer(design=args.description, steps=args.steps)
    print(f"按「{args.description}」出 {len(args.seeds)} 个候选，每个都裁到句末、{'降噪、' if args.denoise else ''}过参考门禁，再试念一段过门禁 …")
    for seed in args.seeds:
        audio, rate = synthesize(DESIGN_TEXT, seed)
        raw = out / f"{seed}-原始.wav"
        write_pcm(raw, to_rate(audio, rate))
        try:
            record = clean(raw, DESIGN_TEXT, out / str(seed), denoise_noise=args.denoise)
        except ValueError as error:
            print(f"  ✗ 种子 {seed}：不能当参考（{error}）")
            continue
        report, problems = trial(out / str(seed), f"候选{seed}", DESIGN_TEXT, args.steps, 2026)   # 参考干净不等于克隆干净，试念才算数
        if problems:
            print(f"  ✗ 种子 {seed}：参考停顿深度 {record['gate_after']['pause_depth_db']} dB，但试念没过门禁（{'；'.join(problems)[:120]}）")
        else:
            print(f"  ✓ 种子 {seed}：参考停顿深度 {record['gate_after']['pause_depth_db']} dB，试念 {report['pause_depth_db']} dB  {out / str(seed)}/")
    print(f"每个 ✓ 的目录里有参考 reference.wav 和试念.wav。挑一个听着顺耳的加进声音库：\n"
          f"  voxcpm_tts.py voice add <名字> --audio {out}/<种子>/reference.wav --consent designed")


def cmd_clean(args):
    from clean_reference import clean
    text = args.text or (Path(args.text_file).expanduser().read_text(encoding="utf-8") if args.text_file else "")
    if not text.strip():
        die("要给这段录音的逐字稿：--text 或 --text-file，一字不差、标点照录")
    out = Path(args.output).expanduser() if args.output else HOME / "cleaned" / time.strftime("%m%d-%H%M%S")
    try:
        record = clean(Path(args.source).expanduser(), text, out, args.start, args.end, denoise_noise=not args.no_denoise)
    except ValueError as error:
        die(f"没清出合格的参考：{error}")
    print(f"✓ {out / 'reference.wav'}  {record['duration_seconds']} 秒，停顿深度 {record['gate_before']['pause_depth_db']} → "
          f"{record['gate_after']['pause_depth_db']} dB，对稿字错率 {record['asr']['cer']}\n"
          f"  听着没问题就加进声音库：voxcpm_tts.py voice add <名字> --audio {out / 'reference.wav'} --consent self|authorized|designed")


def cmd_gate(args):
    from audio_gate import measure
    failed = 0
    for file in args.files:
        r = measure(Path(file).expanduser(), short_clip=args.short_clip)
        failed += r["status"] != "PASS"
        print(f"{'✓' if r['status'] == 'PASS' else '✗'} {file}  停顿深度 {r.get('pause_depth_db')} dB  单频线 {r.get('tonal_lines_hz_persistence') or '无'}  "
              f"峰值 {r.get('peak_dbfs')} dBFS{'  ' + '；'.join(r['failures']) if r['failures'] else ''}")
    sys.exit(1 if failed else 0)


def main():
    p = argparse.ArgumentParser(description="本机 VoxCPM2 配音：整篇稿子分段配音（带门禁）、念一句、设计声音、声音库、清洗参考录音")
    sub = p.add_subparsers(dest="cmd", required=True)

    def gen_opts(sp):
        sp.add_argument("--voice", help="声音库里的声音名（不写用默认的）")
        sp.add_argument("--seed", type=int, default=2026, help="起始种子；不过关依次 +1 重来，最多 3 次（默认 2026）")
        sp.add_argument("--steps", type=int, help="推理步数（默认用这个声音入库时的，一般是 10；官方推荐 4–30，越大越细越慢）")

    s = sub.add_parser("script", help="整篇稿子按段配音：空行分段，# 标题当段名不念")
    s.add_argument("file", help="稿子（.md / .txt）")
    s.add_argument("-o", "--output", help="输出目录（默认：稿子同名的文件夹）")
    s.add_argument("--only", help="只念标题里带这个词的章节，比如 --only 口播文案")
    s.add_argument("--keep-brackets", action="store_true", help="【】里的字也念（默认当成给剪辑看的标注，不念）")
    s.add_argument("--dry-run", action="store_true", help="只看怎么分段，不生成")
    s.add_argument("--force", action="store_true", help="不管有没有变，全部重新生成")
    gen_opts(s)
    s.set_defaults(fn=cmd_script, models=(MODEL, ASR_MODEL))

    s = sub.add_parser("say", help="念一句或一小段")
    s.add_argument("text", help="要念的字；写 - 从标准输入读")
    s.add_argument("-o", "--output", help="存到哪个 wav")
    gen_opts(s)
    s.set_defaults(fn=cmd_say, models=(MODEL, ASR_MODEL))

    s = sub.add_parser("design", help="用一句描述造声音：出几个候选参考，挑一个 voice add")
    s.add_argument("description", help="身份 + 质感 + 场景，比如「青年男声，音色清亮温和，吐字清晰，适合科技产品讲解」；不写像谁")
    s.add_argument("--seeds", type=lambda v: [int(x) for x in v.split(",")], default=[2026, 7, 1, 2], help="逗号分隔（默认 2026,7,1,2）")
    s.add_argument("--steps", type=int, default=10)
    s.add_argument("--denoise", action="store_true", help="候选也过一遍 DeepFilterNet3 降噪")
    s.add_argument("-o", "--output", help="候选放哪（默认 ~/.local/share/voxcpm-tts/candidates/<时间>/）")
    s.set_defaults(fn=cmd_design, models=(MODEL, ASR_MODEL))

    s = sub.add_parser("voice", help="声音库：add / list / default")
    vs = s.add_subparsers(dest="voice_cmd", required=True)
    a = vs.add_parser("add", help="把一段参考加进声音库：先查参考，再试念一段过门禁")
    a.add_argument("name", help="起个好记的名字，比如「讲解男声」「我自己」")
    a.add_argument("--audio", required=True, help="参考录音：8–15 秒最好，句末收住，没有配乐和底噪")
    a.add_argument("--text", help="参考的逐字稿，一字不差、标点照录（不写就读参考旁边的 transcript.txt）")
    a.add_argument("--consent", required=True, choices=list(CONSENT), help="self = 本人录音；authorized = 获得授权；designed = 声音设计造的")
    a.add_argument("--steps", type=int, default=10, help="以后用这个声音时的默认推理步数")
    a.add_argument("--seed", type=int, default=2026, help="试念的起始种子")
    a.set_defaults(fn=cmd_voice_add, models=(MODEL, ASR_MODEL))
    a = vs.add_parser("list", help="看声音库")
    a.set_defaults(fn=cmd_voice_list, models=())
    a = vs.add_parser("default", help="改默认声音")
    a.add_argument("name")
    a.set_defaults(fn=cmd_voice_default, models=())

    s = sub.add_parser("clean", help="把一段录音清成合格的参考：降噪、裁到句末、补尾部静音、峰值 -3 dBFS，再过门禁和对稿")
    s.add_argument("source", help="原始录音（m4a / mp3 / wav 都行，原文件不动）")
    s.add_argument("--text", help="这一段的逐字稿")
    s.add_argument("--text-file", help="逐字稿放在文件里")
    s.add_argument("--start", type=float, help="大概从第几秒开始（默认：语音开始处）")
    s.add_argument("--end", type=float, help="大概到第几秒结束（默认：语音结束处）")
    s.add_argument("--no-denoise", action="store_true", help="不降噪，只裁")
    s.add_argument("-o", "--output", help="放到哪个新目录（默认 ~/.local/share/voxcpm-tts/cleaned/<时间>/）")
    s.set_defaults(fn=cmd_clean, models=(DENOISER, ASR_MODEL))

    s = sub.add_parser("gate", help="只跑门禁：嗡声 / 单频线、停顿深度、直流、削波")
    s.add_argument("files", nargs="+")
    s.add_argument("--short-clip", action="store_true", help="参考录音或单个短片段（停顿按最安静的 2% 算）")
    s.set_defaults(fn=cmd_gate, models=())

    args = p.parse_args()
    sys.stdout.reconfigure(line_buffering=True)                     # 进度和报错按发生的顺序出现，输出走管道时也是
    if getattr(args, "denoise", False):
        args.models += (DENOISER,)
    prepare(*args.models)
    args.fn(args)


if __name__ == "__main__":
    main()
