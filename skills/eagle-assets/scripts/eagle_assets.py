#!/usr/bin/env python3
"""查 Eagle 库里「拼贴素材」文件夹的图，并把选中的原图拷进项目。只用标准库，Eagle 要开着。

  eagle_assets.py folders                         # 有哪些子文件夹、各多少张
  eagle_assets.py list [--folder 手与指示] [-k 剪刀] [--json]
  eagle_assets.py export <id> [<id> ...] --to assets/collage   # 拷原图，并在目标目录的 CREDITS.md 里记出处
"""
import argparse, json, os, re, shutil, sys, urllib.parse, urllib.request

API = os.environ.get('EAGLE_API', 'http://localhost:41595')
ROOT = '拼贴素材'


def call(path):
    try:
        with urllib.request.urlopen(API + path, timeout=30) as r:
            return json.load(r)['data']
    except OSError as e:
        sys.exit(f'连不上 Eagle（{API}）：{e}\n先打开 Eagle，再重试。')


def tree():
    info = call('/api/library/info')
    def find(fs):
        for f in fs:
            if f['name'] == ROOT:
                return f
            hit = find(f.get('children', []))
            if hit:
                return hit
    root = find(call('/api/folder/list'))   # library/info 里的文件夹列表不及时，新建的文件夹要从这里取
    if not root:
        sys.exit(f'Eagle 库「{info["library"]["name"]}」里没有「{ROOT}」文件夹。')
    return info['library']['path'], root


def items():
    lib, root = tree()
    names = {f['id']: f['name'] for f in root.get('children', [])}
    names[root['id']] = ROOT
    out = []
    for it in call('/api/item/list?limit=2000&tags=' + urllib.parse.quote(ROOT)):
        folder = next((names[f] for f in it.get('folders', []) if f in names), None)
        if folder is None:
            continue
        note = it.get('annotation') or ''
        meta = dict(re.findall(r'^(作者|年代|材质|馆藏|许可|页面|来源)：(.*)$', note, re.M))
        out.append({'id': it['id'], 'name': it['name'], 'folder': folder, 'ext': it['ext'], 'width': it.get('width'), 'height': it.get('height'),
                    'tags': it.get('tags', []), 'page': it.get('url') or meta.get('页面', ''), 'license': meta.get('许可', ''),
                    'author': meta.get('作者', ''), 'date': meta.get('年代', ''), 'museum': meta.get('馆藏', '') or meta.get('来源', ''),
                    'note': note, 'path': f"{lib}/images/{it['id']}.info/{it['name']}.{it['ext']}"})
    return sorted(out, key=lambda x: (x['folder'], x['name']))


def real_path(it):
    if os.path.isfile(it['path']):
        return it['path']
    d = os.path.dirname(it['path'])
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith('.' + it['ext']) and not f.endswith('_thumbnail.png'):
                return os.path.join(d, f)
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('folders')
    ls = sub.add_parser('list')
    ls.add_argument('--folder'); ls.add_argument('-k', '--keyword'); ls.add_argument('--json', action='store_true')
    ex = sub.add_parser('export')
    ex.add_argument('ids', nargs='+'); ex.add_argument('--to', required=True)
    a = ap.parse_args()
    all_items = items()
    if a.cmd == 'folders':
        counts = {}
        for it in all_items:
            counts[it['folder']] = counts.get(it['folder'], 0) + 1
        for k, v in counts.items():
            print(f'{v:3d}  {k}')
        return
    if a.cmd == 'list':
        sel = [it for it in all_items if (not a.folder or it['folder'] == a.folder)
               and (not a.keyword or a.keyword.lower() in ' '.join([it['name'], it['note'], *it['tags']]).lower())]
        if a.json:
            print(json.dumps(sel, ensure_ascii=False, indent=1)); return
        for it in sel:
            print(f"{it['id']}  [{it['folder']}]  {it['name']}  {it['width']}×{it['height']}  {it['author'][:40]}  {it['date']}")
        print(f'共 {len(sel)} 张', file=sys.stderr)
        return
    by_id = {it['id']: it for it in all_items}
    os.makedirs(a.to, exist_ok=True)
    credits = os.path.join(a.to, 'CREDITS.md')
    known = open(credits, encoding='utf-8').read() if os.path.exists(credits) else '# 素材出处\n\n| 文件 | 作品 | 作者 | 年代 | 馆藏 / 来源 | 许可 | 页面 |\n|---|---|---|---|---|---|---|\n'
    for i in a.ids:
        it = by_id.get(i)
        if not it:
            print(f'跳过 {i}：不在「{ROOT}」里', file=sys.stderr); continue
        src = real_path(it)
        if not src:
            print(f'跳过 {i}：原图不在本机（库在 iCloud，先在 Eagle 里点开这张图让它下载）', file=sys.stderr); continue
        fname = re.sub(r'[^\w\-]+', '_', it['name']).strip('_')[:60] + f"_{it['id'][-5:]}.{it['ext']}"
        shutil.copy2(src, os.path.join(a.to, fname))
        if fname not in known:
            known += f"| `{fname}` | {it['name']} | {it['author']} | {it['date']} | {it['museum']} | {it['license']} | {it['page']} |\n"
        print(os.path.join(a.to, fname))
    open(credits, 'w', encoding='utf-8').write(known)


if __name__ == '__main__':
    main()
