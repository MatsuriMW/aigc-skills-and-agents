#!/usr/bin/env python3
"""把引用了 assets/ 里位图的工作稿 SVG 打包成单文件（位图转成 base64 内嵌），并渲染一张 PNG。只用标准库。

  python3 pack_svg.py imgs/src/01_没说出口的话.svg            # → imgs/01_没说出口的话.svg + .png
  python3 pack_svg.py imgs/src/*.svg --out imgs --no-png

PNG 用本机的 Chrome / Chromium / Edge 无头渲染（3200×1800）。找不到浏览器就只出 SVG。
纯 SVG 的图不需要打包，但也可以用它来出 PNG 预览。
"""
import argparse, base64, mimetypes, os, re, shutil, subprocess, sys, tempfile

BROWSERS = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Chromium.app/Contents/MacOS/Chromium',
            '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge', 'google-chrome', 'chromium', 'chromium-browser', 'msedge']


def inline(svg, base):
    n = 0
    def rep(m):
        nonlocal n
        head, attr, q, href = m.groups()
        if href.startswith(('data:', 'http:', 'https:', '#')):
            return m.group(0)
        p = os.path.join(base, href)
        if not os.path.isfile(p):
            sys.exit(f'找不到位图：{p}')
        mime = mimetypes.guess_type(p)[0] or 'image/png'
        n += 1
        return f'{head}{attr}={q}data:{mime};base64,{base64.b64encode(open(p, "rb").read()).decode()}{q}'
    out = re.sub(r'(<image\b[^>]*?\s)((?:xlink:)?href)=(["\'])(.*?)\3', rep, svg, flags=re.S)
    return out, n


def size_of(svg):
    m = re.search(r'viewBox=["\']\s*[\d.\-]+[\s,]+[\d.\-]+[\s,]+([\d.]+)[\s,]+([\d.]+)', svg)
    return (float(m.group(1)), float(m.group(2))) if m else (1600.0, 900.0)


def render(svg_path, png_path, w, h, scale):
    exe = next((b for b in BROWSERS if os.path.isfile(b) or shutil.which(b)), None)
    if not exe:
        print('没找到 Chrome / Chromium / Edge，跳过 PNG', file=sys.stderr)
        return False
    with tempfile.TemporaryDirectory() as tmp:
        html = os.path.join(tmp, 'p.html')
        open(html, 'w', encoding='utf-8').write(
            f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:#E8E2D4;overflow:hidden}}'
            f'img{{display:block;width:{w}px;height:{h}px}}</style><img src="file://{os.path.abspath(svg_path)}">')
        r = subprocess.run([exe, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                            f'--user-data-dir={os.path.join(tmp, "prof")}', f'--force-device-scale-factor={scale}',
                            f'--window-size={int(w)},{int(h)}', '--virtual-time-budget=4000',
                            f'--screenshot={os.path.abspath(png_path)}', f'file://{html}'],
                           capture_output=True, text=True, timeout=120)
    if not os.path.isfile(png_path):
        print(f'渲染失败：{r.stderr[-400:]}', file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('svgs', nargs='+')
    ap.add_argument('--out', help='输出目录，默认是工作稿所在目录的上一级')
    ap.add_argument('--no-png', action='store_true')
    ap.add_argument('--scale', type=float, default=2, help='PNG 的倍率，默认 2（3200×1800）')
    a = ap.parse_args()
    for src in a.svgs:
        base = os.path.dirname(os.path.abspath(src))
        out_dir = os.path.abspath(a.out) if a.out else os.path.dirname(base)
        os.makedirs(out_dir, exist_ok=True)
        svg, n = inline(open(src, encoding='utf-8').read(), base)
        dst = os.path.join(out_dir, os.path.basename(src))
        if os.path.abspath(src) == dst:
            sys.exit(f'输出会覆盖工作稿：{dst}，用 --out 指到别的目录')
        open(dst, 'w', encoding='utf-8').write(svg)
        print(f'{dst}  内嵌 {n} 张位图  {os.path.getsize(dst) // 1024} KB')
        if not a.no_png:
            png = os.path.splitext(dst)[0] + '.png'
            w, h = size_of(svg)
            if render(dst, png, w, h, a.scale):
                print(f'{png}  {os.path.getsize(png) // 1024} KB')


if __name__ == '__main__':
    main()
