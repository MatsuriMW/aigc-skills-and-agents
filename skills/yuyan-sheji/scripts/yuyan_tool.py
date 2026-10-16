#!/usr/bin/env python3
"""语言设计的辅助脚本（只用标准库）。

  stats    统计一段文字或某个角色台词的句长、填充词、缩写、用词长度等，给「从样本建档」和检查用
  variety  按目标变体（uk / us / au）扫出穿帮的叫法和拼写，比如英国角色说了 apartment、color

台词文件可以是纯文字，也可以是剧本格式「角色名: 台词」或「角色名：台词」，用 --speaker 只看一个人。

  python3 yuyan_tool.py stats 样本.txt
  python3 yuyan_tool.py stats 剧本.md --speaker JULIAN
  python3 yuyan_tool.py variety 剧本.md --target uk --speaker JULIAN
"""
import argparse
import collections
import csv
import re
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "references" / "data" / "variety.tsv"
LINE_RE = re.compile(r"^\s*[*_]*([^:：\n]{1,30}?)[*_]*\s*[:：]\s*(.+)$")

EN_FILLERS = ["um", "uh", "like", "you know", "i mean", "sort of", "kind of", "basically",
              "literally", "actually", "right", "well", "so", "anyway", "look", "listen"]
ZH_FILLERS = ["就是", "然后", "那个", "对吧", "反正", "其实", "怎么说呢", "你知道吧", "我跟你说",
              "说实话", "嗯", "啊", "吧", "呢", "嘛", "哈", "呗", "咋", "整", "贼"]
EN_STOP = set("""a an the and or but so to of in on at for with by from is are was were be been am i you he
she it we they me him her us them my your his its our their this that these those not no do does did
have has had will would can could should just what who how why when where if then than there here as
up out about into over all""".split())
LATINATE = re.compile(r"(tion|sion|ment|ity|ence|ance|ive|ous|ize|ise|ate)s?$")


def read_lines(path, speaker):
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
    # 去掉舞台说明（括号里的）
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
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
