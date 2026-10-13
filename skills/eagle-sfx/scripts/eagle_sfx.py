#!/usr/bin/env python3
"""从 Eagle 库「董北 音效」（整包一万四千多个）里挑音效，并把选中的拷进项目。只用标准库 + ffmpeg，对 Eagle 只读，Eagle 要开着。

  eagle_sfx.py folders [脚步] [--depth 3]                 # 文件夹树和各自多少个；给一个词就只看带这个词的
  eagle_sfx.py list --folder 转场 [--kind 嗖声] [-k riser] [--min 0.5] [--max 2] [--shape 上升] [--limit 60] [--measure] [--json]
  eagle_sfx.py search "键盘 OR 打字 -机械" [--max 3] [--limit 40] [--measure] [--json]   # 名字和文件夹名都搜
  eagle_sfx.py search --ai "快速的嗖声" [--limit 20]       # 按意思搜（要 Eagle 的 MCP Server 和 AI Search 两个插件）
  eagle_sfx.py export <id> [<id> ...] --to public/sfx     # 拷音效，并在目标目录写 sfx.json（峰值秒等）和 CREDITS.md
  eagle_sfx.py index --folder 脚步 [--force]              # 把一个文件夹预先量一遍（会从 iCloud 下载这些文件）

峰值、起止这些数是用到时才量的：转场、撞击两组已经量好；别的在 export 时自动量，list / search 加 --measure 也会量。
"""
import argparse, array, json, math, os, re, shutil, subprocess, sys, urllib.parse, urllib.request

API = os.environ.get('EAGLE_API', 'http://localhost:41595')
MCP = os.environ.get('EAGLE_MCP', 'http://127.0.0.1:41596')   # Eagle 里的「MCP Server」插件，只有 search --ai 用它
AUDIO = {'wav', 'mp3', 'aif', 'aiff', 'flac', 'ogg', 'm4a'}
ROOT = os.environ.get('EAGLE_SFX_ROOT', '董北 音效')   # Eagle 里放音效的那个顶层文件夹；换成别的音效库就改这里
PACK = '附赠音效库'   # 这一层名字太长又没信息，路径里略掉
INDEX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'index.json')
RATE = 4000          # 分析用的采样率：只量包络，够用
WIN = 40             # 10 毫秒一格
SEP = ' / '

# 文件名（英文）里的词 → 类别。一个音效可以有好几类。中文类别就是它所在的文件夹
KINDS = [
    ('嗖声', r'wh?oosh|swoosh|swish|zwoosh|wipe|whip'),
    ('飞过', r'fly ?by|flame pass|speeder|torpedo|train|space ship|low fly'),
    ('蓄势', r'riser|reverse|power ?up|progressive|powerup'),
    ('尖啸', r'zing|zip'),
    ('重击', r'\bhit\b|impact|bang|stomp|smash|crash|big drum|metal drum|dull drum|bell drum|bass drum'),
    ('断电', r'power down'),
    ('玻璃', r'glass|window|chipped'),
    ('激光', r'laser|electric dart'),
    ('爆炸', r'explos'),
    ('钟鼓', r'bell|drum|cymbal|percussion'),
    ('吉他', r'guitar'),
    ('裂响', r'crack|wrenched'),
    ('掉落', r'dropp?ed|drop\b|door|storage bin|frying pan|trash can|appliance|record hit|camera pop|boing|double take'),
    ('火', r'fire|flame|hot|heat|gas|boiling|scolding'),
    ('冰', r'freeze|icy'),
    ('水', r'water|wet|splat|sewer'),
    ('电子', r'computer|electr|electic|static|sci-?fi|future|space|teleport|trance|modulator|distortion|phazed|stereo'),
    ('暗黑', r'dark|evil|scary|ghost|abduction|monster'),
    ('金属', r'metal|aluminum|sword'),
    ('空灵', r'hollow|airy|gleam|golden|tingly|sweet|windy'),
    ('拖尾', r'echo|reverb|delay|stutter|large room'),
]


def call(path):
    try:
        with urllib.request.urlopen(API + path, timeout=60) as r:
            return json.load(r)['data']
    except OSError as e:
        sys.exit(f'连不上 Eagle（{API}）：{e}\n先打开 Eagle，再重试。')


def mcp(tool, params):
    """调 Eagle 的 MCP Server 插件；插件没开（或者开着但服务停用了）返回 None。"""
    req = urllib.request.Request(MCP + '/api/tools/call', data=json.dumps({'tool': tool, 'params': params}).encode(), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
    except (OSError, ValueError):
        return None
    return d.get('data') if d.get('success') else None


def kinds_of(name):
    low = name.lower()
    return [k for k, pat in KINDS if re.search(pat, low)]


def squash(s):
    return re.sub(r'\s+', '', s).lower()


def folder_tree():
    """「董北 音效」底下每个文件夹：[(号, 路径)]，路径像「音效 / 人 / 脚步」，根是空串。"""
    def find(fs):
        for f in fs:
            if f['name'] == ROOT:
                return f
            hit = find(f.get('children', []))
            if hit:
                return hit
    root = find(call('/api/folder/list'))
    if not root:
        sys.exit(f'Eagle 库里没有「{ROOT}」文件夹。')
    out = []
    def walk(f, trail):
        out.append((f['id'], SEP.join(trail)))
        for c in f.get('children', []):
            walk(c, trail if c['name'].startswith(PACK) else trail + [c['name']])
    walk(root, [])
    return out


def load_index():
    try:
        return json.load(open(INDEX, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_index(idx):
    json.dump(idx, open(INDEX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)


def catalog():
    """整包的目录：每个音效的名字、格式、时长、所在文件夹，量过的带上峰值这些数。一两秒，不读音频文件。"""
    lib = call('/api/library/info')['library']['path']
    idx = load_index()
    items = {}
    for fid, path in folder_tree():
        page = 0
        while True:
            got = call(f'/api/item/list?limit=1000&offset={page}&folders={fid}')
            for it in got:
                if it.get('ext') not in AUDIO:
                    continue
                x = items.get(it['id'])
                if not x:
                    x = items[it['id']] = {'id': it['id'], 'name': it['name'], 'ext': it['ext'], 'duration': round(it.get('duration') or 0, 2),
                                           'size': it.get('size', 0), 'folders': [], 'kinds': kinds_of(it['name']),
                                           'path': f"{lib}/images/{it['id']}.info/{it['name']}.{it['ext']}"}
                    m = idx.get(it['id'])
                    if m and m.get('key') == f"{it['id']}:{x['size']}":
                        x.update({k: m[k] for k in ('peak', 'start', 'end', 'db')}, shape=shape_of(m))
                if path not in x['folders']:
                    x['folders'].append(path)
            if len(got) < 1000:
                break
            page += 1
    for x in items.values():
        x['folder'] = max(x['folders'], key=len)   # 同时在几个文件夹里的，显示最细的那个
    return sorted(items.values(), key=lambda x: (x['folder'], x['name']))


def real_path(it):
    if os.path.isfile(it['path']):
        return it['path']
    d = os.path.dirname(it['path'])
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith('.' + it['ext']):
                return os.path.join(d, f)
    return None


def is_local(it):
    """文件在不在本机：库在 iCloud，没下载的文件占位不占块。"""
    try:
        st = os.stat(it['path'])
    except OSError:
        return False
    return st.st_size == 0 or st.st_blocks > 0


def measure(path):
    """量包络：peak = 最响那一刻（秒），start / end = 响度高过峰值 -40 dB 的第一刻和最后一刻，db = 峰值电平。
    文件还在 iCloud 上的，读它的时候系统会先下载。"""
    try:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(RATE), '-f', 's16le', '-'], capture_output=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0 or len(r.stdout) < WIN * 2:
        return None
    pcm = array.array('h'); pcm.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == 'big':
        pcm.byteswap()
    env = [math.sqrt(sum(v * v for v in pcm[i:i + WIN]) / WIN) for i in range(0, len(pcm) - WIN + 1, WIN)]
    top = max(env)
    if top <= 0:
        return None
    at = env.index(top)
    floor = top * 0.01
    loud = [i for i, v in enumerate(env) if v >= floor]
    sec = lambda i: round(i * WIN / RATE, 2)
    return {'peak': sec(at), 'start': sec(loud[0]), 'end': sec(loud[-1] + 1), 'db': round(20 * math.log10(top / 32768), 1)}


def shape_of(m):
    """形状：上升 = 铺垫一秒以上才到顶（往一个点上冲）；打击 = 一下就到顶；其余 = 掠过（起来、过去）。"""
    attack, span = m['peak'] - m['start'], max(0.01, m['end'] - m['start'])
    if attack >= 1.0 and attack / span >= 0.5:
        return '上升'
    return '打击' if attack <= 0.15 or attack / span <= 0.2 else '掠过'


def ensure_measured(sel, force=False, quiet=False):
    """把这几个里还没量的量一遍，记进索引。返回没量成的个数。"""
    todo = [it for it in sel if force or 'peak' not in it]
    if not todo:
        return 0
    idx = load_index()
    failed = 0
    for n, it in enumerate(todo, 1):
        p = real_path(it)
        m = measure(p) if p else None
        if not m:
            failed += 1
            continue
        idx[it['id']] = {'key': f"{it['id']}:{it['size']}", **m}
        it.update(m, shape=shape_of(m))
        if not quiet and (n % 20 == 0 or n == len(todo)):
            print(f'量了 {n} / {len(todo)}', file=sys.stderr)
            save_index(idx)
    save_index(idx)
    return failed


def in_folder(it, want):
    """路径里有没有这个词（index 用）。"""
    w = squash(want)
    return any(w in squash(p) for p in it['folders'])


def exact_folder(items, want):
    w = squash(want)
    return any(squash(p) == w for it in items for p in it['folders'])


def parse_query(q):
    """「键盘 OR 打字 -机械 "glass break"」→ (必须都满足的几组，每组里满足一个就行)，(排除的词)。"""
    toks = [a or b for a, b in re.findall(r'"([^"]+)"|(\S+)', q)]
    groups, minus, join = [], [], False
    for t in toks:
        if t == 'OR':
            join = True
            continue
        if t.startswith('-') and len(t) > 1:
            minus.append(squash(t[1:]))
        elif join and groups:
            groups[-1].append(squash(t))
        else:
            groups.append([squash(t)])
        join = False
    return groups, minus


def length(it):
    """听得见的那一段有多长；没量过的只能拿文件时长。"""
    return it['end'] - it['start'] if 'peak' in it else it['duration']


def filtered(items, a):
    sel = items
    if getattr(a, 'folder', None):
        exact = exact_folder(items, a.folder)
        w = squash(a.folder)
        hit = (lambda p: squash(p) == w or squash(p).startswith(w + '/')) if exact else (lambda p: w in squash(p))
        # 同时在几个文件夹里的，显示对上的那个
        sel = [it | {'folder': next(p for p in it['folders'] if hit(p))} for it in sel if any(hit(p) for p in it['folders'])]
    if getattr(a, 'kind', None):
        sel = [it for it in sel if a.kind in it['kinds']]
    if getattr(a, 'keyword', None):
        k = squash(a.keyword)
        sel = [it for it in sel if k in squash(it['name'] + ' ' + ' '.join(it['kinds']))]
    if a.min is not None:
        sel = [it for it in sel if length(it) >= a.min]
    if a.max is not None:
        sel = [it for it in sel if length(it) <= a.max]
    return sel


def show(sel, total, a, tail=''):
    if a.json:
        print(json.dumps([{k: v for k, v in it.items() if k != 'folders'} | {'local': is_local(it)} for it in sel], ensure_ascii=False, indent=1))
        return
    for it in sel:
        sc = f"{it['score']:5.1f}  " if 'score' in it else ''
        if 'peak' in it:
            m = f"响 {length(it):5.1f}s  峰值 {it['peak']:5.2f}s  {it['shape']}  {it['db']:6.1f}dB"
        else:
            m = f"长 {it['duration']:5.1f}s  （没量）"
        cloud = '' if is_local(it) else '  ☁'
        print(f"{it['id']}  {sc}[{it['folder']}]  {it['name']}.{it['ext']}  {m}  {'·'.join(it['kinds'])}{cloud}")
    more = f'，只列了前 {len(sel)} 个（--limit 改，或者加条件筛）' if total > len(sel) else ''
    print(f'共 {total} 个{more}{tail}', file=sys.stderr)
    if any(not is_local(it) for it in sel):
        print('☁ = 还在 iCloud 上没下载，量峰值或导出时会自动下载', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    fo = sub.add_parser('folders'); fo.add_argument('word', nargs='?'); fo.add_argument('--depth', type=int, default=3)
    ix = sub.add_parser('index'); ix.add_argument('--folder', required=True); ix.add_argument('--force', action='store_true')
    ls = sub.add_parser('list')
    ls.add_argument('--folder'); ls.add_argument('--kind'); ls.add_argument('-k', '--keyword')
    ls.add_argument('--shape', choices=['上升', '打击', '掠过'])
    se = sub.add_parser('search'); se.add_argument('query'); se.add_argument('--ai', action='store_true')
    for p in (ls, se):
        p.add_argument('--min', type=float); p.add_argument('--max', type=float)
        p.add_argument('--limit', type=int, default=60 if p is ls else 40)
        p.add_argument('--measure', action='store_true'); p.add_argument('--json', action='store_true')
    ex = sub.add_parser('export')
    ex.add_argument('ids', nargs='+'); ex.add_argument('--to', required=True)
    a = ap.parse_args()
    items = catalog()

    if a.cmd == 'folders':
        own, total = {}, {}
        for it in items:
            seen = set()
            for p in it['folders']:
                own[p] = own.get(p, 0) + 1
                parts = p.split(SEP) if p else []
                for i in range(len(parts) + 1):
                    seen.add(SEP.join(parts[:i]))
            for p in seen:
                total[p] = total.get(p, 0) + 1
        w = squash(a.word) if a.word else None
        for p in sorted(total):
            if not p:
                continue
            depth = p.count(SEP) + 1
            if w:
                if w not in squash(p):
                    continue
            elif depth > a.depth:
                continue
            name = p if w else '  ' * (depth - 1) + p.split(SEP)[-1]
            print(f"{name}  {total[p]}" + (f"（直接放在这层的 {own[p]}）" if own.get(p) and own[p] != total[p] else ''))
        print(f'整包 {len(items)} 个' + ('' if w else f'；只列到第 {a.depth} 层，--depth 调，或者给一个词只看带这个词的文件夹'), file=sys.stderr)
        return

    if a.cmd == 'index':
        sel = [it for it in items if in_folder(it, a.folder)]
        if not sel:
            sys.exit(f'没有路径里带「{a.folder}」的文件夹。')
        away = [it for it in sel if not is_local(it)]
        print(f'{len(sel)} 个，其中 {len(away)} 个要先从 iCloud 下载（{sum(it["size"] for it in away) / 1e6:.0f} MB）', file=sys.stderr)
        failed = ensure_measured(sel, force=a.force)
        print(f'量完了，{failed} 个没量成' if failed else '量完了')
        return

    if a.cmd == 'list':
        if not (a.folder or a.kind or a.keyword or a.shape):
            sys.exit('整包有一万多个，list 至少给一个条件：--folder / --kind / -k / --shape。先用 folders 看有哪些文件夹。')
        sel = filtered(items, a)
        if a.shape:   # 形状要量过才知道
            if a.measure:
                ensure_measured(sel[:400])
            sel = [it for it in sel if it.get('shape') == a.shape]
        total = len(sel)
        sel = sel[:a.limit]
        if a.measure:
            ensure_measured(sel, quiet=a.json)
            if a.min is not None or a.max is not None:   # 量完以后按听得见的长度再筛一遍
                sel = [it for it in sel if (a.min is None or length(it) >= a.min) and (a.max is None or length(it) <= a.max)]
        show(sel, total, a)
        return

    if a.cmd == 'search':
        tail = ''
        if a.ai:
            st = mcp('ai_search_status', {})
            if not st or not st.get('available'):
                sys.exit('按意思搜用不了：要在 Eagle 里开着「MCP Server」和「AI Search」两个插件。' + (f"（{st.get('message')}）" if st else '（MCP Server 没开，或者它的服务停用了）'))
            by_id = {it['id']: it for it in items}
            sel = []
            # 整个库（图片也在里面）一起比，音效只占一部分：多要一些再筛
            for hit in mcp('ai_search_by_text', {'query': a.query, 'limit': 100}) or []:
                it = by_id.get(hit.get('id'))
                if it:
                    sel.append(it | ({'score': round(hit['score'], 1)} if isinstance(hit.get('score'), (int, float)) else {}))
        else:
            groups, minus = parse_query(a.query)
            if not groups:
                sys.exit('搜什么？给至少一个词。')
            sel = []
            for it in items:
                name = squash(it['name'] + ' ' + ' '.join(it['kinds']))
                hay = name + ' ' + ' '.join(squash(p) for p in it['folders'])
                if any(m in hay for m in minus) or not all(any(t in hay for t in g) for g in groups):
                    continue
                by_name = all(any(t in name for t in g) for g in groups)
                if not by_name:   # 靠文件夹名对上的：显示对上的那个文件夹
                    terms = [t for g in groups for t in g]
                    it = it | {'folder': next((p for p in it['folders'] if any(t in squash(p) for t in terms)), it['folder'])}
                sel.append((0 if by_name else 1, it))   # 名字里就有的排前面，只是文件夹对上的排后面
            sel = [it for _, it in sorted(sel, key=lambda x: (x[0], x[1]['folder'], x[1]['name']))]
        sel = filtered(sel, a)
        total = len(sel)
        sel = sel[:a.limit]
        if a.measure:
            ensure_measured(sel, quiet=a.json)
        show(sel, total, a, tail)
        return

    # export
    by_id = {it['id']: it for it in items}
    os.makedirs(a.to, exist_ok=True)
    manifest_path = os.path.join(a.to, 'sfx.json')
    try:
        manifest = json.load(open(manifest_path, encoding='utf-8'))
    except (OSError, ValueError):
        manifest = {}
    credits = os.path.join(a.to, 'CREDITS.md')
    known = open(credits, encoding='utf-8').read() if os.path.exists(credits) else (
        '# 音效出处\n\n来自 Eagle 库「董北 音效」，是课程附赠的音效合集，原始出处和许可不明，不是 CC0。\n'
        '公开发布前由本人确认能不能用。\n\n| 文件 | 原名 | 文件夹 |\n|---|---|---|\n')
    for i in a.ids:
        it = by_id.get(i)
        if not it:
            print(f'跳过 {i}：不是「{ROOT}」里的音效', file=sys.stderr); continue
        ensure_measured([it], quiet=True)   # 没量过的现量；文件在 iCloud 上的这一步会把它下载下来
        src = real_path(it)
        if not src or not is_local(it):
            print(f'跳过 {i}：文件没能从 iCloud 下载下来，在 Eagle 里点开这个音效再试', file=sys.stderr); continue
        fname = re.sub(r'[^a-z0-9]+', '-', it['name'].lower()).strip('-')[:50]
        if not it['name'].isascii() or not fname or re.fullmatch(r'[\d-]+', fname):   # 中文名、纯编号转不成像样的文件名：带上条目号免得撞名
            fname = (fname + '-' if fname else 'sfx-') + it['id'][-6:].lower()
        fname += f".{it['ext']}"
        shutil.copyfile(src, os.path.join(a.to, fname))
        manifest[fname] = {k: it[k] for k in ('name', 'folder', 'kinds', 'duration', 'peak', 'start', 'end', 'db', 'shape') if k in it}
        if f'`{fname}`' not in known:
            known += f"| `{fname}` | {it['name']} | {it['folder']} |\n"
        print(os.path.join(a.to, fname))
    json.dump(manifest, open(manifest_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    open(credits, 'w', encoding='utf-8').write(known)


if __name__ == '__main__':
    main()
