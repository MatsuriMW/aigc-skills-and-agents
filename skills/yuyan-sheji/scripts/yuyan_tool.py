#!/usr/bin/env python3
"""语言设计的辅助脚本（只用标准库）。

  stats    统计一段文字或某个角色台词的句长、填充词、缩写、用词长度等，给「从样本建档」和检查用
  variety  按目标变体（uk / us / au）扫出穿帮的叫法和拼写，比如英国角色说了 apartment、color
  era      古代台词里的现代词（--lang zh / en / ja）
  ja       日语台词检查：简体字混入、人称、现实风格里的役割语、已知敬语错误、句末分布、易错读音、估算拍数

台词文件可以是纯文字，也可以是剧本格式「角色名: 台词」或「角色名：台词」，用 --speaker 只看一个人。

  python3 yuyan_tool.py stats 样本.txt
  python3 yuyan_tool.py stats 剧本.md --speaker JULIAN
  python3 yuyan_tool.py variety 剧本.md --target uk --speaker JULIAN
  python3 yuyan_tool.py ja 剧本.md --speaker 田中 --style real --self 俺,僕 --sec 5
"""
import argparse
import collections
import csv
import re
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "references" / "data" / "variety.tsv"
ERA_DATA = Path(__file__).resolve().parent.parent / "references" / "era" / "data" / "era-words.tsv"
JA_DATA = Path(__file__).resolve().parent.parent / "references" / "ja" / "data" / "ja-lint.tsv"
LINE_RE = re.compile(r"^\s*[*_]*([^:：\n]{1,30}?)[*_]*\s*[:：]\s*(.+)$")

EN_FILLERS = ["um", "uh", "like", "you know", "i mean", "sort of", "kind of", "basically",
              "literally", "actually", "right", "well", "so", "anyway", "look", "listen",
              "honestly", "lowkey", "to be fair", "i guess", "innit"]
ZH_FILLERS = ["就是", "然后", "那个", "对吧", "反正", "其实", "怎么说呢", "你知道吧", "我跟你说",
              "说实话", "讲真", "说白了", "这个", "呃", "嗯", "啊", "吧", "呢", "嘛", "哈", "呗", "咋", "整", "贼"]
JA_FILLERS = ["えっと", "ええと", "あの", "その", "なんか", "まあ", "やっぱ", "ていうか", "てか", "なんていうか",
              "そうですね", "ちょっと", "まじで", "ほんとに", "うん"]
EN_STOP = set("""a an the and or but so to of in on at for with by from is are was were be been am i you he
she it we they me him her us them my your his its our their this that these those not no do does did
have has had will would can could should just what who how why when where if then than there here as
up out about into over all""".split())
LATINATE = re.compile(r"(tion|sion|ment|ity|ence|ance|ive|ous|ize|ise|ate)s?$")


def read_lines(path, speaker, keep_ruby=False):
    text = Path(path).read_text(encoding="utf-8")
    out = []
    for raw in text.splitlines():
        m = LINE_RE.match(raw)
        if speaker:
            if m and m.group(1).strip().lower() == speaker.lower():
                out.append(m.group(2))
        else:
            out.append(m.group(2) if m and len(m.group(1)) <= 20 else raw)
    body = "\n".join(l for l in out if l.strip())
    # 去掉舞台说明（括号里的）；日语的读音标注「私（わたくし）」要留着
    if keep_ruby:
        return re.sub(r"[（(](?![ぁ-んァ-ヶー]+[）)])[^）)]*[）)]", "", body)
    return re.sub(r"[（(][^）)]*[）)]", "", body)


def is_zh(text):
    han = len(re.findall(r"[一-鿿]", text))
    return han > len(re.findall(r"[A-Za-z]+", text))


def split_sentences(text, zh):
    pat = r"[。！？!?…]+|\n" if zh else r"(?<=[.!?])\s+|\n|—\s"
    return [s.strip() for s in re.split(pat, text) if s and s.strip()]


def stats(args):
    text = read_lines(args.file, args.speaker)
    if not text.strip():
        sys.exit("没有读到台词（检查 --speaker 的名字）")
    if len(re.findall(r"[ぁ-んァ-ヶ]", text)) > len(text) * 0.15:
        print("提醒：这段像日语，stats 按中文算，结果不准；日语用 ja 子命令。\n")
    zh = is_zh(text) if args.lang == "auto" else args.lang == "zh"
    sents = split_sentences(text, zh)
    if zh:
        lens = [len(re.findall(r"[一-鿿]", s)) for s in sents]
        unit, total = "字", sum(lens)
        fillers = {f: text.count(f) for f in ZH_FILLERS}
    else:
        words_by_sent = [re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)*", s) for s in sents]
        lens = [len(w) for w in words_by_sent]
        words = [w.lower() for ws in words_by_sent for w in ws]
        unit, total = "词", len(words)
        low = " " + " ".join(words) + " "
        fillers = {f: low.count(" " + f + " ") for f in EN_FILLERS}
    lens = [n for n in lens if n > 0]
    print(f"句子 {len(lens)} 句，共 {total} {unit}")
    if lens:
        print(f"句长（{unit}）：平均 {statistics.mean(lens):.1f}，中位 {statistics.median(lens)}，"
              f"最短 {min(lens)}，最长 {max(lens)}")
        short = sum(1 for n in lens if n <= (6 if zh else 4))
        print(f"碎片短句（≤{6 if zh else 4}{unit}）占 {short / len(lens):.0%}")
    q = len(re.findall(r"[?？]", text))
    ex = len(re.findall(r"[!！]", text))
    print(f"问句 {q}，感叹 {ex}")
    per = 100 / max(total, 1)
    hits = sorted(((n, f) for f, n in fillers.items() if n), reverse=True)
    if hits:
        print(f"填充词 / 语气词（每百{unit}）：" + "，".join(f"{f} {n * per:.1f}" for n, f in hits))
    if not zh:
        contr = sum(1 for w in words if "'" in w)
        uniq = len(set(words))
        long_ = sum(1 for w in words if len(w) >= 9)
        lat = sum(1 for w in words if len(w) >= 7 and LATINATE.search(w))
        print(f"缩写（don't、I'm…）占词 {contr * per:.1f}%；不同词 / 总词 {uniq / max(total, 1):.2f}")
        print(f"长词（≥9 字母）占 {long_ * per:.1f}%；拉丁后缀词占 {lat * per:.1f}%")
        top = collections.Counter(w for w in words if w not in EN_STOP and len(w) > 2).most_common(15)
        print("高频词：" + "，".join(f"{w} {n}" for w, n in top))
    else:
        print(f"儿化「儿」出现 {text.count('儿')} 次")
        print("（中文没有分词，成语密度、词的档位请人工看）")
    if total < (600 if zh else 300):
        print(f"\n提醒：样本只有 {total} {unit}，偏少，归纳出来的规则都标〔推测〕。")


def load_variety():
    with open(DATA, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def variety(args):
    text = read_lines(args.file, args.speaker)
    rows = load_variety()
    allowed = {"uk": {"uk"}, "us": {"us"}, "au": {"au", "uk"}}[args.target]
    found = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for r in rows:
            if r["variety"] in allowed:
                continue
            if re.search(r"(?<![\w'-])" + re.escape(r["term"]) + r"(?![\w-])", low):
                found.append((i, r, line.strip()))
    if not found:
        print(f"没有发现和 {args.target} 冲突的叫法或拼写（词表见 references/data/variety.tsv，只覆盖常见的）")
        return
    for i, r, line in found:
        mark = "穿帮" if r["severity"] == "hard" else "留意"
        note = f"（{r['note']}）" if r["note"] else ""
        print(f"[{mark}] 第 {i} 句：{r['term']}（{r['variety']}）→ {r['counterpart']}{note}\n    {line}")
    hard = sum(1 for _, r, _ in found if r["severity"] == "hard")
    print(f"\n共 {len(found)} 处，其中穿帮 {hard} 处。「留意」的词两边都有人用，看语境。")


def era(args):
    text = read_lines(args.file, args.speaker)
    with open(ERA_DATA, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE) if r["lang"] == args.lang]
    found = 0
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        for r in rows:
            term = r["term"].lower()
            hit = re.search(r"(?<![\w'-])" + re.escape(term) + r"(?![\w-])", low) if args.lang == "en" else term in low
            if hit:
                found += 1
                instead = f"，可改：{r['instead']}" if r["instead"] else ""
                print(f"[现代词] 第 {i} 句：{r['term']}（{r['kind']}{instead}）\n    {line.strip()}")
    print(f"\n共 {found} 处。词表只有常见的，查不了称谓对不对朝代，也查不了「现代想法换了古代腔」，这些要人工看（references/era/）。")


def mora_count(text):
    """估算拍数：读音标注按假名算，假名一字一拍（小写的不算），没标读音的汉字按 2 拍估。"""
    text = re.sub(r"[一-鿿々]+[（(]([ぁ-んァ-ヶー]+)[）)]", r"\1", text)
    kana = len(re.findall(r"[ぁ-んァ-ヶー]", text)) - len(re.findall(r"[ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ]", text))
    return kana + 2 * len(re.findall(r"[一-鿿々]", text))


def ja_ending(sent):
    s = sent.rstrip("」』）)…。、！？!? 　")
    if re.search(r"(です|ます|ました|でした|ません|ください|ございます|でしょう|ませんか)(ね|よ|か|よね)?$|っす(ね|よ)?$", s):
        return "敬体"
    if re.search(r"(よ|ね|な|か|の|ぞ|ぜ|さ|わ|かな|じゃん|けど|から|って|もん|し|でしょ|だろ|よね|のに)$", s):
        return "带句末词或留白"
    if re.search(r"(だ|である|た|ない|[うくぐすつぬぶむる])$", s):
        return "言い切り"
    return "其他（名词结束、感叹等）"


def ja(args):
    text = read_lines(args.file, args.speaker, keep_ruby=True)
    if not text.strip():
        sys.exit("没有读到台词（检查 --speaker 的名字）")
    with open(JA_DATA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE))
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # 简体字：日文编码里没有的汉字
    bad = collections.Counter()
    for ch in re.findall(r"[一-鿿]", text):
        try:
            ch.encode("cp932")
        except UnicodeEncodeError:
            bad[ch] += 1
    problems = 0
    if bad:
        problems += sum(bad.values())
        print("[穿帮] 日文字库里没有的汉字（多半是简体字）：" + "，".join(f"{c}×{n}" for c, n in bad.most_common()))

    def hits(kind):
        out = collections.defaultdict(list)
        for r in rows:
            if r["kind"] != kind:
                continue
            for i, l in enumerate(lines, 1):
                if re.search(r["pattern"], l, re.M):
                    out[(r["label"], r["note"])].append((i, l))
        return out

    allowed = set(args.self.split(",")) if args.self else None
    for kind, title in (("self", "自称"), ("you", "对称")):
        found = hits(kind)
        if found:
            print(f"{title}：" + "，".join(f"{k[0]}×{len(v)}" for k, v in found.items()))
        if kind == "self" and allowed:
            for k, v in found.items():
                if k[0] not in allowed:
                    problems += len(v)
                    print(f"[穿帮] 第 {v[0][0]} 句 自称「{k[0]}」不在档案里（{args.self}）：{v[0][1]}")

    if args.style == "real":
        allow = set(args.allow.split(",")) if args.allow else set()
        for k, v in hits("role").items():
            if k[0] in allow:
                continue
            problems += len(v)
            note = f"（{k[1]}）" if k[1] else ""
            print(f"[穿帮] 现实风格里出现役割语「{k[0]}」{note}，第 {v[0][0]} 句：{v[0][1]}")
        for k, v in hits("role_soft").items():
            note = f"（{k[1]}）" if k[1] else ""
            print(f"[留意] 现实风格「{k[0]}」{note}，第 {v[0][0]} 句：{v[0][1]}")

    for k, v in hits("error").items():
        problems += len(v)
        print(f"[敬语] {k[0]}（{k[1]}），第 {v[0][0]} 句：{v[0][1]}")
    for k, v in hits("warn").items():
        print(f"[留意] {k[0]}（{k[1]}），第 {v[0][0]} 句：{v[0][1]}")

    sents = [s for s in re.split(r"(?<=[。！？!?…」])|\n", text) if s and s.strip("「」『』。！？!?… 　")]
    dist = collections.Counter(ja_ending(s.strip()) for s in sents)
    total = sum(dist.values()) or 1
    print("句末分布：" + "，".join(f"{k} {v / total:.0%}" for k, v in dist.most_common()))
    # 阈值借自 cccskills 的 charatone：说死的句子超过三成五就是报告口气
    if dist["言い切り"] / total > 0.35 and total >= 6:
        print("[留意] 「〜だ。」这类说死的句子超过 35%，除非是刻意硬、冷、傲的角色，否则加句末词或留白。")

    fills = [(text.count(f), f) for f in JA_FILLERS if f in text]
    if fills:
        print("填充词：" + "，".join(f"{f}×{n}" for n, f in sorted(fills, reverse=True)))
    found = hits("reading")
    if found:
        print("读音要标（写成 私（わたくし），或在念白版写假名）：" + "，".join(f"{k[0]}（{k[1]}）" for k in found))

    moras = [mora_count(l) for l in lines]
    print(f"拍数（估算，没标读音的汉字按 2 拍）：共 {sum(moras)} 拍，约 {sum(moras) / 8:.1f}–{sum(moras) / 6:.1f} 秒（8–6 拍/秒）")
    if args.sec:
        for i, (m, l) in enumerate(zip(moras, lines), 1):
            if m > args.sec * 8:
                problems += 1
                print(f"[超长] 第 {i} 句约 {m} 拍，{args.sec:g} 秒放不下：{l}")
            elif m > args.sec * 6:
                print(f"[偏紧] 第 {i} 句约 {m} 拍，{args.sec:g} 秒要说得很快：{l}")
    print(f"\n共 {problems} 处要改。查不了敬语方向、内外和人物像不像，这些要按 references/ja/00 的七步人工过。")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats", help="句长、填充词、用词统计")
    s.add_argument("file")
    s.add_argument("--speaker")
    s.add_argument("--lang", choices=["auto", "en", "zh"], default="auto")
    s.set_defaults(fn=stats)
    v = sub.add_parser("variety", help="按目标变体扫穿帮的叫法和拼写")
    v.add_argument("file")
    v.add_argument("--target", choices=["uk", "us", "au"], required=True)
    v.add_argument("--speaker")
    v.set_defaults(fn=variety)
    e = sub.add_parser("era", help="古代台词里的现代词")
    e.add_argument("file")
    e.add_argument("--lang", choices=["zh", "en", "ja"], required=True)
    e.add_argument("--speaker")
    e.set_defaults(fn=era)
    j = sub.add_parser("ja", help="日语台词检查")
    j.add_argument("file")
    j.add_argument("--speaker")
    j.add_argument("--style", choices=["real", "anime"], default="anime", help="real 时报役割语")
    j.add_argument("--self", help="档案允许的自称，逗号隔开，如 俺,僕,私")
    j.add_argument("--allow", help="现实风格里允许的词（方言角色的 わし、〜じゃ、〜のう），逗号隔开")
    j.add_argument("--sec", type=float, help="每句的镜头秒数，超了就报")
    j.set_defaults(fn=ja)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
