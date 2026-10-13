#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow", "numpy", "opencv-python-headless"]
# ///
"""把一张公有领域的图处理成古典式拼贴用的纸片：抠图 → 统一成墨色 / 纸色 → 加剪刀白边。

  uv run prep_asset.py bust.jpg -o assets/bust.png --height 720                  # 抠图 + 版画线网 + 白边（默认）
  uv run prep_asset.py hand.jpg -o assets/hand.png --height 400 --tone halftone  # 报纸网点
  uv run prep_asset.py griffin.jpg -o assets/griffin.png --height 600 --tone ink # 版画、素描：纸变透明，只留墨线
  uv run prep_asset.py letter.jpg -o assets/letter.png --width 520 --cut none --tone duotone   # 整张当纸片
  uv run prep_asset.py hand.jpg -o assets/hand_px.png --height 400 --tone pixel   # 同一物件的「屏幕版」：马赛克色块
  uv run prep_asset.py paper.jpg -o assets/paper.jpg --tone texture               # 纸纹，整幅叠在古典层上

--height / --width 填它在 1600×900 画面里要占的尺寸（SVG 单位）。输出是 2 倍像素，
脚本最后一行打印 <image> 标签，照抄宽高即可。

抠图默认用 rembg（没装就退回 grabcut）。要用 rembg：
  uv run --with "rembg[cpu]" prep_asset.py ...
"""
import argparse, os, sys
import numpy as np, cv2
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
INK = np.array([0x14, 0x11, 0x0E], np.float32) / 255
PAPER = np.array([0xF3, 0xEE, 0xE2], np.float32) / 255   # 纸片比底纸 #E8E2D4 亮一档，贴上去才分得开
EDGE = np.array([0xF8, 0xF5, 0xEC], np.float32) / 255


def cut_rembg(rgb, model):
    from rembg import new_session, remove
    out = remove(Image.fromarray(rgb), session=new_session(model), post_process_mask=True)
    return np.asarray(out)[..., 3].astype(np.float32) / 255


def cut_grabcut(rgb):
    """馆藏器物照多是纯色底，grabcut 从四边取背景样本就够用。"""
    h, w = rgb.shape[:2]
    s = 900 / max(h, w)
    small = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else rgb
    sh, sw = small.shape[:2]
    m = int(min(sh, sw) * 0.03) + 2
    mask = np.zeros((sh, sw), np.uint8)
    cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, (m, m, sw - 2 * m, sh - 2 * m),
                np.zeros((1, 65)), np.zeros((1, 65)), 6, cv2.GC_INIT_WITH_RECT)
    a = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8) * 255
    n, lab, stats, _ = cv2.connectedComponentsWithStats(a)
    if n > 1:
        a = (lab == 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])).astype(np.uint8) * 255   # 只留最大的一块
    a = cv2.GaussianBlur(cv2.resize(a, (w, h), interpolation=cv2.INTER_LINEAR), (0, 0), 1.2)
    return a.astype(np.float32) / 255


def levels(L, alpha, lo_p=2, hi_p=98, gamma=1.0):
    """只按主体范围内的像素定黑白场。"""
    v = L[alpha > 0.5] if (alpha > 0.5).sum() > 100 else L.ravel()
    lo, hi = np.percentile(v, [lo_p, hi_p])
    return np.clip((L - lo) / max(hi - lo, 1e-3), 0, 1) ** gamma


def line_screen(cov, period, angle):
    """线网：线宽随 cov 变。和 SVG 里的 pattern 排线同周期、同角度，位图和矢量才接得上。"""
    h, w = cov.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(angle)
    u = (x * np.cos(a) + y * np.sin(a)) / period
    T = 0.5 - 0.5 * np.cos(2 * np.pi * u)
    return np.clip((cov - T) / (2.2 / period) + 0.5, 0, 1)


def dot_screen(cov, period, angle):
    h, w = cov.shape
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    a = np.deg2rad(angle)
    u = (x * np.cos(a) + y * np.sin(a)) / period
    v = (-x * np.sin(a) + y * np.cos(a)) / period
    T = (np.cos(2 * np.pi * u) + np.cos(2 * np.pi * v)) * 0.25 + 0.5
    return np.clip((cov - T) / (1.6 / period) + 0.5, 0, 1)


def scissor_border(alpha, r, seed=0):
    """沿轮廓外扩 r 像素，再把边折成直线段——剪刀剪出来的边是一段一段直的，不是圆滑的。"""
    rng = np.random.default_rng(seed)
    h, w = alpha.shape
    a = (alpha > 0.45).astype(np.uint8) * 255
    k = lambda n: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * n + 1, 2 * n + 1))
    d = cv2.morphologyEx(cv2.dilate(a, k(r)), cv2.MORPH_CLOSE, k(r * 3))
    cnts, _ = cv2.findContours(d, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    ss = 2
    out = np.zeros((h * ss, w * ss), np.uint8)
    for c in cnts:
        if cv2.contourArea(c) < 200:
            continue
        ap = cv2.approxPolyDP(c, max(2.0, r * 0.6), True)[:, 0, :].astype(np.float32)
        ap += rng.uniform(-0.8, 0.8, ap.shape)
        cv2.fillPoly(out, [np.round(ap * ss).astype(np.int32)], 255, lineType=cv2.LINE_AA)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--height', type=float, help='在画面里的高度（SVG 单位）')
    ap.add_argument('--width', type=float, help='在画面里的宽度（SVG 单位），和 --height 二选一')
    ap.add_argument('--cut', choices=['auto', 'rembg', 'grabcut', 'none'], default='auto',
                    help='auto：有 rembg 用 rembg，没有用 grabcut；none：不抠，整张当纸片')
    ap.add_argument('--model', default='u2net', help='rembg 的模型，下载慢可换 silueta / u2netp')
    ap.add_argument('--tone', choices=['engrave', 'halftone', 'duotone', 'ink', 'pixel', 'texture'], default='engrave',
                    help='engrave 版画线网；halftone 报纸网点；duotone 连续调墨色；ink 纸变透明只留墨线（给版画、素描）；'
                         'pixel 马赛克色块（同一物件的「屏幕版」）；texture 整张纸纹，输出 JPG，叠在最上面用 multiply')
    ap.add_argument('--block', type=float, default=14, help='pixel 的色块边长（SVG 单位）')
    ap.add_argument('--period', type=float, default=4, help='线网 / 网点的周期（SVG 单位），默认 4；SVG 里配套的排线用同周期同角度')
    ap.add_argument('--angle', type=float, default=45)
    ap.add_argument('--gamma', type=float, default=1.0, help='>1 整体压暗，<1 提亮')
    ap.add_argument('--edge', type=float, default=5, help='剪刀白边的宽度（SVG 单位），0 不加')
    ap.add_argument('--crop', help='先裁原图：x0,y0,x1,y1，0–1 的比例')
    ap.add_argument('--flip', action='store_true', help='左右镜像')
    ap.add_argument('--scale', type=float, default=2, help='输出像素是 SVG 单位的几倍')
    a = ap.parse_args()
    if not (a.height or a.width) and a.tone != 'texture':
        ap.error('需要 --height 或 --width')

    im = Image.open(a.src)
    im.seek(0)
    rgb = np.asarray(im.convert('RGB'))
    if a.crop:
        x0, y0, x1, y1 = (float(v) for v in a.crop.split(','))
        H, W = rgb.shape[:2]
        rgb = rgb[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)]
    if a.flip:
        rgb = rgb[:, ::-1]
    rgb = np.ascontiguousarray(rgb)
    if max(rgb.shape[:2]) > 2400:                       # 馆藏原图常有三四千像素，抠图前先缩
        s = 2400 / max(rgb.shape[:2])
        rgb = cv2.resize(rgb, (int(rgb.shape[1] * s), int(rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)

    if a.tone == 'texture':
        # 纸纹、颗粒：去色，把平均亮度推到接近白，multiply 叠上去只压暗纹理，不改底色
        g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        w = int(a.width or 1600)
        h = int(a.height or round(w * g.shape[0] / g.shape[1]))
        g = cv2.resize(g, (w, h), interpolation=cv2.INTER_AREA)
        g = np.clip((g - g.mean()) * 1.6 + 236, 0, 255).astype(np.uint8)
        out_path = os.path.splitext(a.out)[0] + '.jpg'
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        Image.fromarray(g, 'L').save(out_path, quality=82)
        print(f'{out_path}  {w}×{h}px  {os.path.getsize(out_path) // 1024} KB', file=sys.stderr)
        print(f'<image href="assets/{os.path.basename(out_path)}" x="0" y="0" width="{w}" height="{h}" '
              f'preserveAspectRatio="xMidYMid slice" opacity="0.55" style="mix-blend-mode:multiply"/>')
        return

    cut = a.cut
    if a.tone == 'ink' and cut == 'auto':
        cut = 'none'
    if cut == 'auto':
        try:
            import rembg  # noqa: F401
            cut = 'rembg'
        except ImportError:
            cut = 'grabcut'
            print('没装 rembg，改用 grabcut（纯色底的器物照够用；人像、杂乱背景请加 --with "rembg[cpu]"）', file=sys.stderr)
    alpha = {'rembg': lambda: cut_rembg(rgb, a.model), 'grabcut': lambda: cut_grabcut(rgb),
             'none': lambda: np.ones(rgb.shape[:2], np.float32)}[cut]()

    if cut != 'none':
        # 清掉抠图留下的碎片（台座残边、背景上的小岛），只留够大的块
        ko = int(max(alpha.shape) * 0.007) | 1
        m = cv2.morphologyEx((alpha > 0.5).astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ko, ko)))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(m)
        if n > 1:
            keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] >= 0.04 * stats[1:, cv2.CC_STAT_AREA].max()]
            m = np.isin(lab, keep).astype(np.uint8)
        alpha = alpha * cv2.dilate(m, np.ones((5, 5), np.uint8))
        # 裁到主体外接框
        ys, xs = np.where(alpha > 0.1)
        if len(ys) == 0:
            sys.exit('抠图结果是空的，换 --cut 或 --crop 再试')
        rgb, alpha = rgb[ys.min():ys.max() + 1, xs.min():xs.max() + 1], alpha[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    h0, w0 = rgb.shape[:2]
    unit = (a.height / h0) if a.height else (a.width / w0)      # 原图像素 → SVG 单位
    W, H = max(1, round(w0 * unit * a.scale)), max(1, round(h0 * unit * a.scale))
    interp = cv2.INTER_AREA if W < w0 else cv2.INTER_CUBIC
    rgb = cv2.resize(rgb, (W, H), interpolation=interp).astype(np.float32) / 255
    alpha = np.clip(cv2.resize(alpha, (W, H), interpolation=interp), 0, 1)

    L = levels(rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11, alpha, gamma=a.gamma)
    period = a.period * a.scale

    if a.tone == 'ink':
        # 版画、素描：亮的地方是纸，直接透明；剩下的墨线叠在 SVG 的旧纸上
        # 版画大半是纸，按中位数以上的亮度定「纸白」，纸上的污渍和版痕才清得掉
        paper = np.percentile(L, 60)
        ink = np.clip((0.72 - L / max(paper, 1e-3)) / 0.45, 0, 1) ** 0.8
        out = np.dstack([np.broadcast_to(INK, (H, W, 3)), ink * alpha])
    else:
        if a.tone == 'engrave':
            # 照片的反差通常不够刻成线：先拉局部反差，再分三层——亮部留白、中间调单向排线、暗部交叉排线，最后勾轮廓
            Lc = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6)).apply((L * 255).astype(np.uint8)).astype(np.float32) / 255
            Lc = 0.45 * L + 0.55 * Lc
            cov = np.clip((0.86 - Lc) / 0.86, 0, 1)
            ink = line_screen(cov * 0.9, period, a.angle)
            ink = np.maximum(ink, line_screen(np.clip((cov - 0.5) / 0.5, 0, 1) * 0.75, period, a.angle - 90))
            s = 0.9 * a.scale
            dog = cv2.GaussianBlur(Lc, (0, 0), s * 2.2) - cv2.GaussianBlur(Lc, (0, 0), s)
            ink = np.maximum(ink, np.clip((dog - 0.045) / 0.03, 0, 1))                    # 轮廓线：五官、发卷、衣褶
            base = PAPER
        elif a.tone == 'pixel':
            # 缩成色块再放大，量化成四档墨色：硬边、纯色，属于现代层的画法
            b = max(2, round(a.block * a.scale))
            small = cv2.resize(L, (max(1, W // b), max(1, H // b)), interpolation=cv2.INTER_AREA)
            sa = cv2.resize(alpha, (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
            q = np.round(np.clip(small, 0, 1) * 3) / 3
            ink = 1 - cv2.resize(q, (W, H), interpolation=cv2.INTER_NEAREST)
            alpha = cv2.resize((sa > 0.5).astype(np.float32), (W, H), interpolation=cv2.INTER_NEAREST)
            base = PAPER
        elif a.tone == 'halftone':
            ink = dot_screen(np.clip(1.02 - L, 0, 1), period, a.angle)
            base = PAPER * (0.72 + 0.28 * L[..., None])      # 网点底下留一点连续调，像报纸翻印
        else:
            ink = (1 - L) ** 1.1
            base = PAPER
        ink = ink[..., None]
        col = base * (1 - ink) + INK * ink
        pad = int(a.edge * a.scale * 3) + 4 if a.edge > 0 and a.tone != 'pixel' else 0
        if pad:
            col = np.pad(col, ((pad, pad), (pad, pad), (0, 0)))
            alpha = np.pad(alpha, pad)
            border = scissor_border(alpha, max(1, round(a.edge * a.scale)), seed=W + H)
            col = col * alpha[..., None] + EDGE * (1 - alpha[..., None])
            alpha = np.maximum(border, alpha * (border > 0))
            ys, xs = np.where(alpha > 0.02)
            col, alpha = col[ys.min():ys.max() + 1, xs.min():xs.max() + 1], alpha[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        out = np.dstack([col, alpha])

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8), 'RGBA').save(a.out, optimize=True)
    w_svg, h_svg = out.shape[1] / a.scale, out.shape[0] / a.scale
    print(f'{a.out}  {out.shape[1]}×{out.shape[0]}px  {os.path.getsize(a.out) // 1024} KB', file=sys.stderr)
    print(f'<image href="assets/{os.path.basename(a.out)}" x="0" y="0" width="{w_svg:.0f}" height="{h_svg:.0f}"/>')


if __name__ == '__main__':
    main()
