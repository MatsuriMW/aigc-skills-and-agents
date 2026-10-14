#!/usr/bin/env python3
"""Virgin vs Chad 这一路的欧美梗图：角色用真图（角色库），标题、标注、指引线、Impact 字用 SVG 写，最后渲染成 PNG。

  python3 meme.py chars                          # 角色库里有哪些角色
  python3 meme.py render 图.json [-o 输出前缀]     # 按描述文件出图：同名的 .svg（自带图片，单文件）和 .png
  python3 meme.py example versus                 # 打印一份描述文件的样子（versus / reply / labels / impact）

角色库默认在 ~/claude/aigc/assets/meme-chars/（prep_chars.py 从 Eagle 生成），环境变量 MEME_CHARS 可以改。
PNG 用本机 Chrome 无头渲染；找不到浏览器就只出 SVG。
"""
import argparse, base64, html, json, math, os, re, shutil, subprocess, sys, tempfile

CHARS = os.path.expanduser(os.environ.get('MEME_CHARS', '~/claude/aigc/assets/meme-chars'))
BROWSERS = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
SANS = "Arial, 'Helvetica Neue', 'PingFang SC', 'Heiti SC', sans-serif"
IMPACT = "Impact, 'Haettenschweiler', 'Arial Black', 'Hiragino Sans GB', 'PingFang SC', 'Heiti SC', sans-serif"
W, H = 1600, 900
CLOSERS = set('」』）)】》〉，。、！？；：…—!?,.;:%')

EXAMPLES = {
    'versus': {'template': 'versus',
               'left': {'char': 'wojak', 'title': 'THE VIRGIN 形容词', 'notes': ['「要高级感、电影感」', '同一句 prompt 抽了 40 张', '出来全是同一张平均脸', '结尾必加 masterpiece, best quality', '觉得是模型不行']},
               'right': {'char': 'yes-chad', 'title': 'THE CHAD 名词', 'notes': ['「35mm，侧逆光，左肩磨白的皮夹克」', '没说的维度一个不留给默认值', '一张过，去吃饭了', '改一个词，只变一处']},
               'footer': '形容词是请模型猜，名词是给模型下单'},
    'reply': {'template': 'reply', 'left': {'char': 'soyjak', 'text': '你这提示词也太长了吧？？现在的模型那么聪明，写一句「电影感」不就够了？？'},
              'right': {'char': 'yes-chad', 'text': '对。'}},
    'labels': {'template': 'labels', 'char': 'doomer', 'title': '凌晨三点还在改提示词的他',
               'notes': ['第 37 版 prompt', '收藏了 200 个提示词模板，一个没用过', '知道问题出在形容词', '但还是写了「高级感」', '明天一定早睡']},
    'impact': {'template': 'impact', 'char': 'wojak', 'top': '写了一千字提示词', 'bottom': '模型只看了第一句'},
}


def die(msg):
    sys.exit(f'✗ {msg}')


def library():
    p = os.path.join(CHARS, 'chars.json')
    if not os.path.isfile(p):
        die(f'角色库还没生成：先跑 prep_chars.py（Eagle 要开着），会建好 {CHARS}')
    return json.load(open(p, encoding='utf-8'))


def image(ref, lib):
    """角色 id 或者图片路径 → (data URI, 宽, 高, 朝向, 是不是真人照片)。"""
    if ref in lib:
        c = lib[ref]
        path, w, h, facing, photo = os.path.join(CHARS, c['file']), c['width'], c['height'], c.get('facing', 'front'), c.get('photo', False)
    else:
        path = os.path.expanduser(ref)
        if not os.path.isfile(path):
            die(f'没有这个角色，也不是一个文件：{ref}（`meme.py chars` 看有哪些）')
        r = subprocess.run(['magick', 'identify', '-format', '%w %h', path + '[0]'], capture_output=True, text=True)
        w, h = (int(x) for x in r.stdout.split()[:2]) if r.returncode == 0 else (800, 800)
        facing, photo = 'front', False
    ext = os.path.splitext(path)[1].lower().lstrip('.') or 'png'
    mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp', 'svg': 'svg+xml'}.get(ext, 'png')
    return f'data:image/{mime};base64,{base64.b64encode(open(path, "rb").read()).decode()}', w, h, facing, photo


# ---------- 文字 ----------

def em(text):
    """估一行字有多宽（单位：字号）：中日韩字和全角标点算 1，其余算 0.55。"""
    return sum(1.0 if ord(ch) > 0x2E7F else (0.3 if ch in ' .,;:!|il\'"' else 0.56) for ch in text)


def wrap(text, size, width):
    """按宽度折行：英文不在单词中间断，中文随处可断。"""
    lines = []
    for para in str(text).split('\n'):
        cur = ''
        for tok in re.findall(r'[A-Za-z0-9][A-Za-z0-9\'’.,:;!?%&+/-]*\s*|\s+|.', para):
            # 行首不放收尾的标点（」，。？！这些）：挤进上一行，宁可稍微超一点
            if cur and em(cur + tok.rstrip()) * size > width and tok not in CLOSERS:
                lines.append(cur.rstrip())
                cur = tok.lstrip()
            else:
                cur += tok
        lines.append(cur.rstrip())
    return lines or ['']


def text_block(x, y, text, size, width, anchor='start', weight=400, fill='#000', family=SANS, gap=1.25, extra=''):
    lines = wrap(text, size, width)
    out = [f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" font-family="{family}" {extra}>']
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{x}" dy="{0 if i == 0 else round(size * gap)}">{html.escape(ln)}</tspan>')
    out.append('</text>')
    return ''.join(out), len(lines) * size * gap


def fit(img_w, img_h, box_w, box_h):
    s = min(box_w / img_w, box_h / img_h)
    return img_w * s, img_h * s


def svg_doc(body, bg='#fff'):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            '<defs><filter id="wob" filterUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="7"/>'
            '<feDisplacementMap in="SourceGraphic" scale="4"/></filter></defs>'
            f'<rect width="{W}" height="{H}" fill="{bg}"/>{body}</svg>')


def figure(ref, lib, box, flip=False, valign='bottom'):
    """把角色图放进 box=(x, y, w, h)，水平居中；valign = bottom（站在底边上）/ middle（上下居中，半身像用）。返回 svg 片段和角色实际占的框。"""
    uri, iw, ih, facing, photo = image(ref, lib)
    bx, by, bw, bh = box
    w, h = fit(iw, ih, bw, bh)
    x, y = bx + (bw - w) / 2, (by + (bh - h) / 2) if valign == 'middle' else (by + bh - h)
    tf = f' transform="translate({2 * x + w:.1f},0) scale(-1,1)"' if flip else ''
    return f'<image href="{uri}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="xMidYMid meet"{tf}/>', (x, y, w, h), photo


def leader(nx, ny, fig, side):
    """从标注指向角色：落在角色框靠这一侧、往里收一点的位置。"""
    x, y, w, h = fig
    tx = x + w * (0.22 if side == 'left' else 0.78)
    ty = min(max(ny, y + h * 0.12), y + h * 0.9)
    return f'<path d="M{nx:.0f},{ny:.0f} L{tx:.0f},{ty:.0f}" stroke="#000" stroke-width="2.6" fill="none" stroke-linecap="round" filter="url(#wob)"/>'


def notes_around(notes, fig, half_x0, half_x1, top, bottom, size=27):
    """标注分到角色两边，上下均匀排开，每条拉一根线指向角色。"""
    x, y, w, h = fig
    left = [n for i, n in enumerate(notes) if i % 2 == 0]
    right = [n for i, n in enumerate(notes) if i % 2 == 1]
    out = []
    for group, side in ((left, 'left'), (right, 'right')):
        if not group:
            continue
        col_w = (x - half_x0 - 44) if side == 'left' else (half_x1 - (x + w) - 44)
        col_w = max(col_w, 140)
        step = (bottom - top) / len(group)
        for i, n in enumerate(group):
            cy = top + step * (i + 0.5)
            tx = half_x0 + 18 if side == 'left' else x + w + 26
            block, bh = text_block(tx, cy - size * 0.4, n, size, col_w)
            out.append(block)
            lines = wrap(n, size, col_w)
            lw = max(em(l) for l in lines) * size
            if side == 'left':
                out.append(leader(tx + lw + 10, cy - size * 0.4 + (bh - size * 1.25) / 2 - size * 0.3, fig, 'left'))
            else:
                out.append(leader(tx - 10, cy - size * 0.4 + (bh - size * 1.25) / 2 - size * 0.3, fig, 'right'))
    return ''.join(out)


# ---------- 模板 ----------

def t_versus(spec, lib):
    """Virgin vs Chad：左右两半，各一个角色、一行标题、一圈标注；底下一句结论。"""
    body, photos = [], []
    footer = spec.get('footer')
    bottom = H - (110 if footer else 40)
    for k, (x0, x1) in (('left', (0, W / 2)), ('right', (W / 2, W))):
        s = spec[k]
        fw = (x1 - x0) * float(s.get('width', 0.46))
        img, fig, photo = figure(s['char'], lib, (x0 + (x1 - x0 - fw) / 2, 150, fw, bottom - 150), flip=bool(s.get('flip')), valign=s.get('valign', 'middle'))
        photos += [s['char']] if photo else []
        body.append(f'<g>{img}</g>')
        t, _ = text_block((x0 + x1) / 2, 88, s.get('title', ''), int(s.get('title_size', 56)), x1 - x0 - 60, anchor='middle', weight=900)
        body.append(t)
        body.append(notes_around(s.get('notes', [])[:8], fig, x0, x1, 175, bottom - 10, int(s.get('note_size', 24))))
    if spec.get('divider', True):
        body.append(f'<line x1="{W / 2}" y1="140" x2="{W / 2}" y2="{bottom}" stroke="#000" stroke-width="2" stroke-dasharray="2 10" opacity=".35"/>')
    if footer:
        t, _ = text_block(W / 2, H - 46, footer, 34, W - 160, anchor='middle', weight=700)
        body.append(t)
    return svg_doc(''.join(body), spec.get('background', '#fff')), photos


def t_reply(spec, lib):
    """Yes Chad 回怼：左边一个激动的角色说一大段，右边 Chad 只回一个词。"""
    body, photos = [], []
    L, R = spec['left'], spec['right']
    img, fig, p1 = figure(L.get('char', 'soyjak'), lib, (60, 330, 680, 540))
    body.append(img)
    t, _ = text_block(70, 90, L.get('text', ''), int(L.get('size', 40)), 690, weight=700)
    body.append(t)
    img, fig, p2 = figure(R.get('char', 'yes-chad'), lib, (860, 260, 700, 610))
    body.append(img)
    t, _ = text_block(1210, 170, R.get('text', 'Yes.'), int(R.get('size', 110)), 660, anchor='middle', weight=900, family="Georgia, 'Songti SC', serif")
    body.append(t)
    body.append(f'<line x1="{W / 2}" y1="40" x2="{W / 2}" y2="{H - 40}" stroke="#000" stroke-width="3" filter="url(#wob)"/>')
    photos += ([L.get('char')] if p1 else []) + ([R.get('char')] if p2 else [])
    return svg_doc(''.join(body)), photos


def t_labels(spec, lib):
    """单个角色 + 一圈标注（「The 27 岁的 Doomer」那种）。"""
    img, fig, photo = figure(spec['char'], lib, (W * 0.3, 150, W * 0.4, H - 190), flip=bool(spec.get('flip')))
    t, _ = text_block(W / 2, 92, spec.get('title', ''), int(spec.get('title_size', 56)), W - 120, anchor='middle', weight=900)
    body = img + t + notes_around(spec.get('notes', [])[:10], fig, 0, W, 170, H - 50, int(spec.get('note_size', 36)))
    return svg_doc(body, spec.get('background', '#fff')), ([spec['char']] if photo else [])


def t_impact(spec, lib):
    """Impact 上下字：图铺满（或居中），白字黑描边分在上下两头。"""
    uri, iw, ih, _, photo = image(spec['char'], lib)
    mode = spec.get('fit', 'contain')
    if mode == 'cover':
        s = max(W / iw, H / ih)
    else:
        s = min(W / iw, H / ih)
    w, h = iw * s, ih * s
    body = [f'<image href="{uri}" x="{(W - w) / 2:.1f}" y="{(H - h) / 2:.1f}" width="{w:.1f}" height="{h:.1f}"/>']
    size = int(spec.get('size', 92))
    # 中文没有 Impact：退到最粗的黑体，描边再加厚一点，才有那种「白字黑边」的分量
    style = f'stroke="#000" stroke-width="{max(6, size // 7)}" paint-order="stroke" stroke-linejoin="round" letter-spacing="2"'
    for key, y0 in (('top', size * 1.05), ('bottom', None)):
        txt = spec.get(key)
        if not txt:
            continue
        lines = wrap(txt, size, W - 80)
        y = y0 if y0 else H - 36 - (len(lines) - 1) * size * 1.08
        t, _ = text_block(W / 2, y, txt, size, W - 80, anchor='middle', weight=900, fill='#fff', family=IMPACT, gap=1.08, extra=style)
        body.append(t)
    return svg_doc(''.join(body), spec.get('background', '#fff')), ([spec['char']] if photo else [])


TEMPLATES = {'versus': t_versus, 'reply': t_reply, 'labels': t_labels, 'impact': t_impact}


def render_png(svg_path, png_path, scale=2):
    exe = next((b for b in BROWSERS if os.path.isfile(b)), None) or shutil.which('google-chrome') or shutil.which('chromium')
    if not exe:
        print('  ! 没找到 Chrome，只出了 SVG', file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, 'p.html')
        open(page, 'w', encoding='utf-8').write(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;overflow:hidden}}img{{display:block;width:{W}px;height:{H}px}}</style>'
                                                f'<img src="file://{os.path.abspath(svg_path)}">')
        subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files', f'--user-data-dir={tmp}/prof',
                        f'--force-device-scale-factor={scale}', f'--window-size={W},{H}', '--virtual-time-budget=4000', f'--screenshot={os.path.abspath(png_path)}',
                        f'file://{page}'], capture_output=True, text=True, timeout=120)
    return os.path.isfile(png_path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('chars')
    r = sub.add_parser('render'); r.add_argument('spec'); r.add_argument('-o', '--out'); r.add_argument('--scale', type=float, default=2)
    e = sub.add_parser('example'); e.add_argument('template', choices=list(EXAMPLES))
    a = ap.parse_args()
    if a.cmd == 'example':
        print(json.dumps(EXAMPLES[a.template], ensure_ascii=False, indent=1))
        return
    lib = library()
    if a.cmd == 'chars':
        for k, c in lib.items():
            print(f'{k:<13} {c["width"]:>5}×{c["height"]:<5} 朝{ {"left": "左", "right": "右"}.get(c["facing"], "前") }  {"〔真人照片〕" if c.get("photo") else ""}{c["use"]}')
        return
    spec = json.load(open(a.spec, encoding='utf-8'))
    tpl = TEMPLATES.get(spec.get('template'))
    if not tpl:
        die(f'template 只能是 {" / ".join(TEMPLATES)}')
    svg, photos = tpl(spec, lib)
    out = a.out or os.path.splitext(a.spec)[0]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out + '.svg', 'w', encoding='utf-8').write(svg)
    ok = render_png(out + '.svg', out + '.png', a.scale)
    print(f'✓ {out}.svg' + (f'  {out}.png' if ok else ''))
    if photos:
        print(f'  ! 用了真人照片：{", ".join(photos)}。只能自己看或者私下用，公开发布前换成简笔画角色')


if __name__ == '__main__':
    main()
