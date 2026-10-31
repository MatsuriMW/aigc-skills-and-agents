#!/usr/bin/env python3
"""MiniMax 语音合成（默认 speech-2.8-hd）：单句、整篇稿子分段配音、查音色、复刻自己的声音。

只用标准库；拼接整条音轨要 ffmpeg。密钥从环境变量 MINIMAX_API_KEY 或钥匙串的 minimax-api-key 取。
用法见 --help 和同目录上一层的 SKILL.md。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

CONFIG = Path.home() / ".config/minimax-tts/config.json"
DEFAULTS = {
    "host": "https://api.minimax.cn",   # 国内站的密钥用这个；国际站（minimax.io）的密钥改成 https://api.minimax.io
    "model": "speech-2.8-hd",
    "voice": "",                        # 没设就得每次 --voice；用 `default --voice xxx` 记下来
    "speed": 1.0,
    "vol": 1.0,
    "pitch": 0,
    "emotion": "",                      # 留空 = 让模型按上下文自己定（2.8 的强项），一般不用设
    "format": "mp3",
    "sample_rate": 32000,
    "bitrate": 128000,
    "gap": 0.35,                        # 拼整条音轨时段与段之间垫的静音，秒
}
PRICE = {"hd": 3.5, "turbo": 2.0}       # 元 / 万字符，2026-10 官网按量价
KEYCHAIN = "minimax-api-key"
MAX_CHARS = 9000                        # 接口单次上限 10000，留点余量
RETRY_CODES = {1001, 1002, 1039}        # 超时、限流：等一等再试
EMOTIONS = ["happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm", "fluent"]


def die(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def load_config():
    cfg = dict(DEFAULTS)
    if CONFIG.exists():
        try:
            cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
        except ValueError:
            die(f"{CONFIG} 不是合法的 JSON")
    return cfg


def api_key():
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if key:
        return key
    r = subprocess.run(["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN, "-w"], capture_output=True, text=True)
    key = r.stdout.strip()
    if r.returncode != 0 or not key:
        die("没找到 MiniMax 的密钥。在终端里跑一次（会让你把密钥粘进去，不会留在命令历史里）：\n"
            f'    security add-generic-password -a "$USER" -s {KEYCHAIN} -w\n'
            "密钥在 platform.minimaxi.com → 账户管理 → 接口密钥。")
    return key


def post(cfg, path, payload=None, form=None, timeout=180):
    """POST 一次。payload = JSON；form = (字段, 文件) 走 multipart。限流和超时自动重试。"""
    url = cfg["host"].rstrip("/") + path
    headers = {"Authorization": f"Bearer {api_key()}"}
    if form is not None:
        fields, (name, filename, blob) = form
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + blob + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    wait = 3
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(wait); wait *= 2; continue
            die(f"接口返回 HTTP {e.code}：{detail}")
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 4:
                time.sleep(wait); wait *= 2; continue
            die(f"连不上 {url}：{e}")
        base = body.get("base_resp") or {}
        code = base.get("status_code", 0)
        if code in RETRY_CODES and attempt < 4:
            time.sleep(wait); wait *= 2; continue
        if code:
            hint = {1004: "密钥不对，或者密钥是国际站的（把 host 改成 https://api.minimax.io）", 2049: "密钥无效", 1008: "余额不足，去控制台充值",
                    2013: "参数不对，多半是 voice_id 写错了，用 voices 子命令查", 1042: "文本里看不见的字符太多", 2038: "账号没有复刻权限，先在控制台做实名认证"}.get(code, "")
            die(f"MiniMax 报错 {code}：{base.get('status_msg', '')}{'（' + hint + '）' if hint else ''}")
        return body
    die("重试了几次还是不行")


# ---------- 文本 ----------

def bill_chars(text):
    """计费字符数：一个汉字算 2 个，字母、标点、空格、换行各算 1 个。"""
    return sum(2 if "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿" else 1 for ch in text)


def cost_of(text, model):
    return bill_chars(text) / 10000 * PRICE["turbo" if "turbo" in model else "hd"]


def clean(text, keep_brackets=False):
    """把稿子里不该念出来的东西去掉：Markdown 记号、链接地址、双链的方括号、【画面】这类标注。停顿标记 <#0.5#> 和语气词 (laughs) 留着。"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)                 # 图片
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)             # [字](链接) → 字
    text = re.sub(r"\[\[[^\]|]*\|([^\]]+)\]\]", r"\1", text)         # [[页|显示名]] → 显示名
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    if not keep_brackets:
        text = re.sub(r"【[^】]*】", "", text)                       # 【画面：…】【B-roll】这类给剪辑看的标注
    text = re.sub(r"(\*\*|__|~~|==|`)", "", text)
    text = re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "", text)   # *斜体*
    text = re.sub(r"\s#[\w/一-鿿-]+", "", text)              # 行尾的 #标签
    return text


def segments_of(raw, keep_brackets=False):
    """稿子 → [(段名, 要念的字)]。空行分段；# 标题不念，只当它后面那几段的名字；> 引用块、--- 分隔线、表格、代码块跳过。"""
    raw = re.sub(r"\A---\n.*?\n---\n", "", raw, flags=re.S)          # 笔记属性
    raw = re.sub(r"```.*?```", "", raw, flags=re.S)
    segs, buf, label = [], [], ""

    def flush():
        text = clean("\n".join(buf), keep_brackets).strip()
        buf.clear()
        if text and re.search(r"[\w一-鿿]", text):
            segs.append((label, text))

    for line in raw.splitlines():
        s = line.strip()
        if not s:
            flush(); continue
        m = re.match(r"^#{1,6}\s+(.*)$", s)
        if m:
            flush(); label = re.sub(r"[\\/:*?\"<>|\s]+", " ", clean(m.group(1))).strip()[:24]; continue
        if s.startswith(">") or s.startswith("|") or re.fullmatch(r"[-*_]{3,}", s):
            flush(); continue
        buf.append(re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s))          # 列表符号不念
    flush()
    out = []
    for name, text in segs:                                          # 太长的段按句子再切
        if bill_chars(text) <= MAX_CHARS:
            out.append((name, text)); continue
        cur = ""
        for sent in re.findall(r"[^。！？!?\n]+[。！？!?\n]*", text):
            if cur and bill_chars(cur + sent) > MAX_CHARS:
                out.append((name, cur.strip())); cur = ""
            cur += sent
        if cur.strip():
            out.append((name, cur.strip()))
    return out


# ---------- 合成 ----------

def voice_args(args, cfg):
    v = {k: (getattr(args, k, None) if getattr(args, k, None) not in (None, "") else cfg[k]) for k in ("model", "voice", "speed", "vol", "pitch", "emotion", "format")}
    if not v["voice"]:
        die("还没选音色。先 `minimax_tts.py voices 关键词` 找一个，再 `minimax_tts.py default --voice <voice_id>` 记下来，或者这次加 --voice")
    if v["emotion"] and v["emotion"] not in EMOTIONS:
        die(f"emotion 只能是 {' / '.join(EMOTIONS)}，或者不设")
    return v


def synth(cfg, text, v, subtitle=False):
    """合成一段，返回 (音频字节, 接口给的 extra_info, 字幕条目或 None)。"""
    payload = {
        "model": v["model"], "text": text, "stream": False, "output_format": "hex",
        "voice_setting": {"voice_id": v["voice"], "speed": float(v["speed"]), "vol": float(v["vol"]), "pitch": int(v["pitch"])},
        "audio_setting": {"sample_rate": int(cfg["sample_rate"]), "bitrate": int(cfg["bitrate"]), "format": v["format"], "channel": 1},
        "language_boost": "auto",
    }
    if v["emotion"]:
        payload["voice_setting"]["emotion"] = v["emotion"]
    if subtitle:
        payload["subtitle_enable"] = True
    body = post(cfg, "/v1/t2a_v2", payload)
    data = body.get("data") or {}
    audio = data.get("audio") or ""
    if not audio:
        die(f"接口没返回音频（trace_id {body.get('trace_id', '?')}）")
    cues = None
    if subtitle and data.get("subtitle_file"):
        try:
            with urllib.request.urlopen(data["subtitle_file"], timeout=60) as r:
                cues = cues_of(json.loads(r.read().decode("utf-8")))
        except Exception as e:                                      # 字幕拿不到不该让整段白合成
            print(f"  ! 字幕没取到：{e}", file=sys.stderr)
    return bytes.fromhex(audio), body.get("extra_info") or {}, cues


def cues_of(obj):
    """接口的字幕 JSON → [(开始秒, 结束秒, 字)]。结构按「一组带 time_begin / time_end / text 的条目」认，套在哪一层都行。"""
    found = []

    def walk(o):
        if isinstance(o, dict):
            if "time_begin" in o and "time_end" in o and isinstance(o.get("text"), str):
                found.append((float(o["time_begin"]) / 1000, float(o["time_end"]) / 1000, o["text"].strip()))
            else:
                for x in o.values():
                    walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(obj)
    return [c for c in found if c[2]]


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path, cues):
    Path(path).write_text("".join(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1)), encoding="utf-8")


def duration_of(path, fallback_ms=0):
    if shutil.which("ffprobe"):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    return fallback_ms / 1000


def cmd_say(args, cfg):
    text = clean(args.text if args.text != "-" else sys.stdin.read()).strip()
    if not text:
        die("没有要念的字")
    v = voice_args(args, cfg)
    out = Path(args.output or f"配音-{time.strftime('%m%d-%H%M%S')}.{v['format']}").expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    audio, info, cues = synth(cfg, text, v, subtitle=args.srt)
    out.write_bytes(audio)
    if cues:
        write_srt(out.with_suffix(".srt"), cues)
    used = info.get("usage_characters") or bill_chars(text)
    print(f"✓ {out}  {duration_of(out, info.get('audio_length', 0)):.1f} 秒  计费 {used} 字符（约 {used / 10000 * PRICE['turbo' if 'turbo' in v['model'] else 'hd']:.3f} 元）{'  字幕 ' + str(out.with_suffix('.srt')) if cues else ''}")


def cmd_script(args, cfg):
    src = Path(args.file).expanduser()
    if not src.is_file():
        die(f"没有这个文件：{src}")
    segs = segments_of(src.read_text(encoding="utf-8"), args.keep_brackets)
    if getattr(args, "only", None):                                  # 稿子里常带标题备选、封面说明这些不念的章节：只留标题里带这个词的
        segs = [(n, t) for n, t in segs if args.only in n]
    if not segs:
        die("稿子里没有要念的字")
    if args.dry_run and not (args.voice or cfg["voice"]):
        args.voice = "还没选"                                         # 只是算钱，不用先选音色
    v = voice_args(args, cfg)
    total = sum(bill_chars(t) for _, t in segs)
    price = PRICE["turbo" if "turbo" in v["model"] else "hd"]
    print(f"{src.name}：{len(segs)} 段，计费 {total} 字符，全部重新合成约 {total / 10000 * price:.2f} 元（{v['model']}，音色 {v['voice']}）")
    if args.dry_run:
        for i, (name, text) in enumerate(segs, 1):
            print(f"  {i:02d} {('[' + name + '] ') if name else ''}{bill_chars(text):>5} 字符  {text[:36].replace(chr(10), ' ')}{'…' if len(text) > 36 else ''}")
        return
    out = Path(args.output or src.with_suffix("")).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    old = {}
    if manifest_path.exists() and not args.force:
        try:
            old = {s["hash"]: s for s in json.loads(manifest_path.read_text(encoding="utf-8")).get("segments", [])}
        except (ValueError, KeyError):
            old = {}
    gap = float(args.gap if args.gap is not None else cfg["gap"])
    rows, spent, offset, all_cues = [], 0, 0.0, []
    for i, (name, text) in enumerate(segs, 1):
        # 这一段的字和所有会影响声音的参数都没变，上次的文件还在：不重新合成（改稿后只花改动那几段的钱）
        h = hashlib.sha1(json.dumps([text, v, cfg["sample_rate"], cfg["bitrate"], bool(args.srt)], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
        file = out / f"{i:02d}{('-' + name) if name else ''}.{v['format']}"
        prev = old.get(h)
        cues = None
        if prev and (out / prev["file"]).exists():
            if prev["file"] != file.name:
                (out / prev["file"]).rename(file)
                if (out / prev["file"]).with_suffix(".srt").exists():
                    (out / prev["file"]).with_suffix(".srt").rename(file.with_suffix(".srt"))
            cues = [tuple(c) for c in prev.get("cues") or []] or None
            used, tag = 0, "没变，沿用"
        else:
            audio, info, cues = synth(cfg, text, v, subtitle=args.srt)
            file.write_bytes(audio)
            used = info.get("usage_characters") or bill_chars(text)
            spent += used
            tag = f"{used} 字符"
        dur = duration_of(file)
        if cues:
            write_srt(file.with_suffix(".srt"), cues)
            all_cues += [(a + offset, b + offset, t) for a, b, t in cues]
        rows.append({"index": i, "name": name, "file": file.name, "hash": h, "text": text, "duration": round(dur, 3), "start": round(offset, 3), "cues": cues or []})
        print(f"  {i:02d} {dur:6.1f} 秒  {tag:<10} {file.name}")
        offset += dur + gap
    keep = {r["file"] for r in rows} | {Path(r["file"]).with_suffix(".srt").name for r in rows}
    for s in old.values():                                           # 稿子里删掉的段，旧文件一起清掉
        for stale in (out / s["file"], (out / s["file"]).with_suffix(".srt")):
            if stale.name not in keep and stale.exists():
                stale.unlink()
    joined = None
    if args.join:
        joined = join(out, rows, gap, v["format"], cfg)
        if all_cues:
            write_srt(out / "全片.srt", all_cues)
    manifest_path.write_text(json.dumps({"source": str(src), "model": v["model"], "voice": v["voice"], "gap": gap, "total_duration": round(max(offset - gap, 0), 3),
                                         "joined": joined, "segments": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"✓ {out}/  共 {max(offset - gap, 0):.1f} 秒，这次计费 {spent} 字符（约 {spent / 10000 * price:.2f} 元）{'，整条音轨 ' + joined if joined else ''}")


def join(out, rows, gap, fmt, cfg):
    """把各段按顺序接成一条音轨，段与段之间垫 gap 秒静音。manifest 里每段的 start 就是它在这条音轨上的位置。"""
    if not shutil.which("ffmpeg"):
        print("  ! 没装 ffmpeg，没有拼整条音轨（各段文件都在）", file=sys.stderr)
        return None
    target = out / f"全片.{fmt if fmt in ('mp3', 'wav', 'flac') else 'wav'}"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for r in rows:
        cmd += ["-i", str(out / r["file"])]
    chain = "".join(f"[{i}:a]apad=pad_dur={gap if i < len(rows) - 1 else 0}[a{i}];" for i in range(len(rows)))
    chain += "".join(f"[a{i}]" for i in range(len(rows))) + f"concat=n={len(rows)}:v=0:a=1[out]"
    cmd += ["-filter_complex", chain, "-map", "[out]", "-ar", str(cfg["sample_rate"])]
    if target.suffix == ".mp3":
        cmd += ["-b:a", "192k"]
    r = subprocess.run(cmd + [str(target)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ! 拼接失败：{r.stderr.strip()[:300]}", file=sys.stderr)
        return None
    return target.name


def cmd_cost(args, cfg):
    args.dry_run, args.output, args.force, args.join, args.srt, args.gap, args.keep_brackets = True, None, False, False, False, None, args.keep_brackets
    cmd_script(args, cfg)


def cmd_voices(args, cfg):
    body = post(cfg, "/v1/get_voice", {"voice_type": args.type})
    kw = [k.lower() for k in args.keyword]
    n = 0
    for kind, title in (("system_voice", "系统音色"), ("voice_cloning", "复刻的音色"), ("voice_generation", "文生音色")):
        hits = []
        for x in body.get(kind) or []:
            line = f"{x.get('voice_id', ''):<44} {x.get('voice_name', '')}  {' '.join(x.get('description') or [])}  {x.get('created_time', '')}".rstrip()
            if all(k in line.lower() for k in kw):
                hits.append(line)
        if hits:
            print(f"\n{title}（{len(hits)}）")
            print("\n".join(hits))
            n += len(hits)
    if not n:
        print("没有符合的音色。关键词少写一点试试（比如只写「女」「青年」「Chinese」）")


def cmd_default(args, cfg):
    saved = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    changed = {k: getattr(args, k) for k in ("voice", "model", "speed", "vol", "pitch", "emotion", "format", "gap", "host") if getattr(args, k, None) is not None}
    if changed:
        saved.update(changed)
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    now = dict(DEFAULTS, **saved)
    for k in ("voice", "model", "speed", "vol", "pitch", "emotion", "format", "gap", "host"):
        print(f"{k:<8} {now[k] if now[k] != '' else '（没设）'}")


def cmd_clone(args, cfg):
    sample = Path(args.sample).expanduser()
    if not sample.exists():
        die(f"没有这个文件：{sample}")
    if sample.suffix.lower() not in (".mp3", ".m4a", ".wav"):
        die("样本只收 mp3 / m4a / wav")
    if sample.stat().st_size > 20 * 1024 * 1024:
        die("样本不能超过 20 MB")
    dur = duration_of(sample)
    if dur and not 10 <= dur <= 300:
        die(f"样本要 10 秒到 5 分钟，这个是 {dur:.0f} 秒")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{6,254}[A-Za-z0-9]", args.voice_id):
        die("voice_id 要 8 个字符以上，字母开头，只用字母、数字、- 和 _，不能以 - 或 _ 结尾")
    up = post(cfg, "/v1/files/upload", form=({"purpose": "voice_clone"}, ("file", sample.name, sample.read_bytes())))
    file_id = (up.get("file") or {}).get("file_id")
    if not file_id:
        die("上传成功了但没拿到 file_id")
    payload = {"file_id": int(file_id) if str(file_id).isdigit() else file_id, "voice_id": args.voice_id,
               "need_noise_reduction": args.denoise, "need_volume_normalization": True}
    if args.preview:
        payload.update({"text": args.preview, "model": cfg["model"]})
    body = post(cfg, "/v1/voice_clone", payload)
    print(f"✓ 复刻好了：{args.voice_id}")
    if body.get("demo_audio"):
        print(f"  试听：{body['demo_audio']}")
    print("  这个音色 7 天内要正式合成一次，不然会被平台删掉；第一次正式合成时收 9.9 元。\n"
          f"  设成默认音色：minimax_tts.py default --voice {args.voice_id}")


def main():
    cfg = load_config()
    p = argparse.ArgumentParser(description="MiniMax 语音合成：单句、整篇稿子分段配音、查音色、复刻声音")
    sub = p.add_subparsers(dest="cmd", required=True)

    def voice_opts(sp):
        sp.add_argument("--voice", help="音色 voice_id（不写用默认的）")
        sp.add_argument("--model", help=f"默认 {cfg['model']}；要便宜一点用 speech-2.8-turbo")
        sp.add_argument("--speed", type=float, help="语速 0.5–2")
        sp.add_argument("--vol", type=float, help="音量 0–10")
        sp.add_argument("--pitch", type=int, help="音高 -12–12")
        sp.add_argument("--emotion", help=f"{' / '.join(EMOTIONS)}；一般不设，让模型按上下文定")
        sp.add_argument("--format", choices=["mp3", "wav", "flac"], help="音频格式")

    s = sub.add_parser("say", help="念一句或一小段")
    s.add_argument("text", help="要念的字；写 - 从标准输入读")
    s.add_argument("-o", "--output", help="存到哪个文件")
    s.add_argument("--srt", action="store_true", help="顺手出一份字幕")
    voice_opts(s); s.set_defaults(fn=cmd_say)

    s = sub.add_parser("script", help="整篇稿子按段配音：空行分段，# 标题当段名不念")
    s.add_argument("file", help="稿子（.md / .txt）")
    s.add_argument("-o", "--output", help="输出目录（默认：稿子同名的文件夹）")
    s.add_argument("--join", action="store_true", help="另外接成一条完整音轨「全片」")
    s.add_argument("--srt", action="store_true", help="每段出字幕；和 --join 一起用时再出一份对齐整条音轨的「全片.srt」")
    s.add_argument("--gap", type=float, help=f"接整条音轨时段间静音的秒数（默认 {cfg['gap']}）")
    s.add_argument("--dry-run", action="store_true", help="只看怎么分段、要花多少钱，不合成")
    s.add_argument("--force", action="store_true", help="不管有没有变，全部重新合成")
    s.add_argument("--keep-brackets", action="store_true", help="【】里的字也念（默认当成给剪辑看的标注，不念）")
    s.add_argument("--only", help="只念标题里带这个词的章节，比如 --only 口播文案")
    voice_opts(s); s.set_defaults(fn=cmd_script)

    s = sub.add_parser("cost", help="算一篇稿子配音要多少钱（不合成）")
    s.add_argument("file")
    s.add_argument("--keep-brackets", action="store_true")
    s.add_argument("--only", help="只算标题里带这个词的章节")
    voice_opts(s); s.set_defaults(fn=cmd_cost)

    s = sub.add_parser("voices", help="查能用的音色")
    s.add_argument("keyword", nargs="*", help="关键词，都要命中（在 voice_id、名字、描述里找）")
    s.add_argument("--type", default="all", choices=["system", "voice_cloning", "voice_generation", "all"])
    s.set_defaults(fn=cmd_voices)

    s = sub.add_parser("default", help="看 / 改默认的音色和参数")
    for k, t in (("voice", str), ("model", str), ("speed", float), ("vol", float), ("pitch", int), ("emotion", str), ("format", str), ("gap", float), ("host", str)):
        s.add_argument(f"--{k}", type=t)
    s.set_defaults(fn=cmd_default)

    s = sub.add_parser("clone", help="用一段自己的录音复刻音色")
    s.add_argument("sample", help="录音：mp3 / m4a / wav，10 秒到 5 分钟，20 MB 以内")
    s.add_argument("--voice-id", required=True, help="给这个音色起的 id，比如 MyVoice01")
    s.add_argument("--preview", help="复刻完顺手念一句试听（按字符计费）")
    s.add_argument("--denoise", action="store_true", help="录音环境吵的话打开降噪")
    s.set_defaults(fn=cmd_clone)

    args = p.parse_args()
    args.fn(args, cfg)


if __name__ == "__main__":
    main()
