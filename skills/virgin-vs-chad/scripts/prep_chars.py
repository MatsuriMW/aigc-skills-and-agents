#!/usr/bin/env python3
"""从 Eagle 的「梗图角色」文件夹取原图，裁成单个角色，存进角色库（默认 ~/claude/aigc/assets/meme-chars/）。

  python3 prep_chars.py            # 重新生成全部角色和 chars.json
  python3 prep_chars.py --list     # 只看 Eagle 里有哪些图

Eagle 要开着；裁图用 ImageMagick（magick）。几张原图是多人合在一起的（Virgin 和 Chad、Becky 和 Stacy、一群 NPC），
按 CHARS 里记好的框裁开；人物旁边压着英文标注的，按 WHITE 里的框涂白。框都是原图上的像素坐标。
角色图本身不进 skill 目录：出处和许可各不相同（见 chars.json 和 Eagle 里每张的注释），skill 公开时不带图。
"""
import argparse, json, os, shutil, subprocess, sys, urllib.parse, urllib.request

API = os.environ.get('EAGLE_API', 'http://localhost:41595')
FOLDER = '梗图角色'
OUT = os.path.expanduser(os.environ.get('MEME_CHARS', '~/claude/aigc/assets/meme-chars'))

# id: (Eagle 里的条目名, 裁切框 w,h,x,y 或 None = 只去白边, 涂白的框列表（裁切后的坐标）, 角色朝向, 说明)
CHARS = {
    'wojak':       ('Wojak（感觉哥）', None, [], 'front', '秃头、八字眉、嘴角下垂：失落、无奈、「我懂那种感觉」'),
    'soyjak':      ('Soyjak（张嘴哥）', None, [], 'front', '眼镜、络腮胡、张大嘴：无脑兴奋、盲目追捧'),
    'virgin':      ('Virgin Walk vs Chad Stride', (380, 680, 200, 160), [], 'left', '缩着肩、低头走路：畏缩、讨好、想太多'),
    'chad':        ('Virgin Walk vs Chad Stride', (600, 720, 800, 120), [], 'left', '夸张的肌肉、昂首阔步：自信到离谱'),
    'yes-chad':    ('Yes Chad（Nordic Gamer）', None, [], 'left', '金发大胡子侧脸：坦然认下、不解释（配「Yes.」「对。」）'),
    'yes-stacy':   ('Yes Stacy（女版 Yes Chad）', None, [], 'left', '金发侧脸的女版 Yes Chad'),
    'becky':       ('Becky vs Stacy', (120, 374, 156, 26), [(96, 0, 24, 40), (108, 0, 12, 374)], 'right', '素颜、背包、抱着书：Virgin 的女版'),
    'stacy':       ('Becky vs Stacy', (166, 374, 612, 26), [(140, 0, 26, 200), (0, 196, 50, 34), (0, 0, 30, 160)], 'left', '金色长发、高跟鞋：Chad 的女版'),
    'doomer':      ('Doomer（丧哥）', (823, 686, 0, 0), [(81, 8, 250, 70), (14, 226, 222, 34), (728, 60, 95, 40), (744, 178, 79, 34), (710, 404, 113, 70)], 'front', '黑毛线帽、黑卫衣、叼烟：虚无、丧'),
    'doomer-girl': ('Doomer Girl', None, [], 'front', '黑短发、项圈的女版 Doomer'),
    'npc':         ('NPC', (214, 446, 352, 100), [], 'front', '灰色、面无表情：人云亦云、复读机'),
    'npc-crowd':   ('NPC', None, [], 'front', '一群 NPC：从众'),
    'brainlet':    ('Brainlet（小脑子）', None, [], 'front', '脑子露在外面：想不明白'),
    'wifejak':     ('Wifejak', None, [], 'front', '红色长发的女版 Wojak'),
    'gigachad':    ('GigaChad', None, [], 'left', '黑白真人肖像：顶级、无可挑剔。真人照片，公开发布前要换掉'),
    'gigachadette': ('女版 GigaChad（GigaChadette）', None, [], 'right', '黑白健身肖像。真人照片，公开发布前要换掉'),
}
PHOTOS = {'gigachad', 'gigachadette'}


def call(path):
    try:
        with urllib.request.urlopen(API + path, timeout=30) as r:
            return json.load(r)['data']
    except OSError as e:
        sys.exit(f'连不上 Eagle（{API}）：{e}\n先打开 Eagle，再重试。')


def eagle_items():
    def find(fs):
        for f in fs:
            if f['name'] == FOLDER:
                return f
            hit = find(f.get('children', []))
            if hit:
                return hit
    folder = find(call('/api/folder/list'))
    if not folder:
        sys.exit(f'Eagle 里没有「{FOLDER}」文件夹')
    lib = call('/api/library/info')['library']['path']
    out = {}
    for it in call(f'/api/item/list?limit=500&folders={folder["id"]}'):
        d = f"{lib}/images/{it['id']}.info"
        path = f"{d}/{it['name']}.{it['ext']}"
        if not os.path.isfile(path) and os.path.isdir(d):
            path = next((os.path.join(d, f) for f in os.listdir(d) if f.endswith('.' + it['ext']) and '_thumbnail' not in f), path)
        out[it['name']] = {'path': path, 'url': it.get('url', ''), 'note': it.get('annotation', ''), 'ext': it['ext']}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    items = eagle_items()
    if a.list:
        for k, v in items.items():
            print(f'{k:<36} {v["url"]}')
        return
    if not shutil.which('magick'):
        sys.exit('要先装 ImageMagick：brew install imagemagick')
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for cid, (name, box, white, facing, use) in CHARS.items():
        it = items.get(name)
        if not it or not os.path.isfile(it['path']):
            print(f'  ! 跳过 {cid}：Eagle 里没找到「{name}」')
            continue
        dst = os.path.join(OUT, f'{cid}.png')
        cmd = ['magick', it['path'] + ('[0]' if it['ext'] != 'svg' else ''), '-background', 'white', '-alpha', 'remove', '-alpha', 'off']
        if box:
            w, h, x, y = box
            cmd += ['-crop', f'{w}x{h}+{x}+{y}', '+repage']
        for (x, y, w, h) in white:
            cmd += ['-fill', 'white', '-stroke', 'none', '-draw', f'rectangle {x},{y} {x + w},{y + h}']
        cmd += ['-fuzz', '6%', '-trim', '+repage', '-bordercolor', 'white', '-border', '6', dst]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            print(f'  ! {cid} 处理失败：{r.stderr.strip()[:200]}')
            continue
        size = subprocess.run(['magick', 'identify', '-format', '%w %h', dst], capture_output=True, text=True).stdout.split()
        lic = next((l.split('：', 1)[1] for l in it['note'].splitlines() if l.startswith('许可：')), '不明')
        src = next((l.split('：', 1)[1] for l in it['note'].splitlines() if l.startswith('来源：')), '')
        meta[cid] = {'file': f'{cid}.png', 'width': int(size[0]), 'height': int(size[1]), 'facing': facing, 'use': use,
                     'photo': cid in PHOTOS, 'eagle': name, 'page': it['url'], 'source': src, 'license': lic}
        print(f'  ✓ {cid:<13} {size[0]}×{size[1]}  {use[:24]}')
    with open(os.path.join(OUT, 'chars.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f'→ {OUT}/  {len(meta)} 个角色，清单在 chars.json')


if __name__ == '__main__':
    main()
