---
name: eagle-assets
description: 从 Eagle 素材库的「拼贴素材」文件夹里找图、取图：大理石胸像、石膏手、眼睛微型画、剪影、植物图谱、鹦鹉螺、剪刀、怀表、钥匙、旧信封、大理石纹纸，以及纸纹、颗粒、灰尘划痕等叠加纹理，都是公有领域（CC0）可以直接用在公开视频里的。做拼贴 / 剪贴 / 撕纸风格的视频或海报、需要可抠图的老照片、版画、古典物件、纸张纹理，或者用户说「用我 Eagle 里的素材」「拼贴素材」「从素材库里找一张…」时使用。也负责往这个文件夹里补新素材。
license: CC-BY-NC-SA-4.0
---

# Eagle 拼贴素材

用户的 Eagle 库「思想的记录」里有一个「拼贴素材」文件夹，放做拼贴用的通用件。每张图的注释里记了作者、年代、馆藏、许可和原页面。

| 子文件夹 | 有什么 |
|---|---|
| 纸张与票据 | 大理石纹纸、旧信封、手写信、扑克牌、花边名片 |
| 手与指示 | 石膏手、青铜握拳、手的素描、手套 |
| 人物与雕像 | 大理石胸像、眼睛微型画、剪影肖像、名片照、解剖版画 |
| 动植物 | 玫瑰图谱、狮鹫、狮子、鹦鹉螺杯、圣甲虫、瓢虫 |
| 天体与地图 | 眼球气球、地球仪桌、金字塔石版画 |
| 器物与机械 | 剪刀、怀表、钥匙、烛台、曼陀林、电报车、撑伞的人 |
| 纸纹与叠加纹理 | 纸纹、和纸、牛皮纸页、胶片颗粒、灰尘划痕 |

## 找图和取图

脚本在本 skill 的 `scripts/eagle_assets.py`，只用标准库。Eagle 要开着（它的本机接口在 `http://localhost:41595`）。

```bash
python3 scripts/eagle_assets.py folders                        # 各子文件夹有多少张
python3 scripts/eagle_assets.py list --folder 手与指示          # 列一个子文件夹
python3 scripts/eagle_assets.py list -k scissors               # 按关键词找（查名字、注释、标签）
python3 scripts/eagle_assets.py list --json                    # 要完整信息：尺寸、作者、许可、原图路径
python3 scripts/eagle_assets.py export <id> <id> --to assets/collage
```

`export` 把原图拷进项目目录，并在那个目录的 `CREDITS.md` 里追加一行出处和许可。做片子时用 `export`，不要直接引用 Eagle 库里的路径：库在 iCloud，路径里有空格和中文，文件也可能还没下载到本机。

作品名多数是英文（馆藏原名），关键词用英文更容易命中，比如 `bust`、`hand`、`eye`、`rose`、`key`。拿不准有什么，先 `list` 看一遍。

挑图之前想清楚这张图在画面里当什么：主角（要轮廓清楚、好抠）、背景页（纸张、版画、风景），还是叠在最上面的纹理（颗粒、灰尘）。要看图本身时，用 `list --json` 里的 `path` 读原图。

## 用进拼贴

抠图、加白边、做半调网点的做法在 `mg-styles-15` 的 `06-collage`：它的 `work/prep.py` 把素材处理成带剪刀白边和网点的纸片。馆藏图多数是灰底或白底的器物照，用 rembg 抠图效果好；版画和素描通常整张当纸片用，不抠。

## 用进古典式配图

`gudianshi-skill` 的方向二（SVG + 拼贴素材）从这里取图：`export` 到 `imgs/src/assets/raw/`，再用它的 `scripts/prep_asset.py` 刻成版画线网的纸片，和 SVG 画的排线、UI 元素拼在一起。做法见那个 skill 的 `references/collage.md`。

## 补新素材

这个文件夹用户允许直接往里加，库里别的文件夹只读。规矩：

- 只收公有领域或 CC0 的。来源用开放馆藏：大都会艺术博物馆（`collectionapi.metmuseum.org/public/collection/v1.1/search`，看 `isPublicDomain`）、芝加哥艺术博物馆（`api.artic.edu`，`is_public_domain`）、克利夫兰艺术博物馆（`openaccess-api.clevelandart.org`，`cc0=1`）。
- 标签加 `拼贴素材`、`CC0`、馆名和子文件夹名；注释按现有格式分行写 `作者：`、`年代：`、`材质：`、`馆藏：`、`许可：`、`页面：`。脚本靠 `拼贴素材` 这个标签和这几行注释找图、记出处，缺了就查不到。
- 用 Eagle 的接口加：`POST /api/item/addFromURLs`（`items` 里每项 `url`、`name`、`website`、`tags`、`annotation`，外加 `folderId`）。芝加哥的图有时拒绝大尺寸，把地址里的 `1686,` 换成 `843,` 再试，或者先下载再用 `/api/item/addFromPaths`。
- 子文件夹的 id 从 `GET /api/folder/list` 取。`/api/library/info` 里的文件夹列表不及时。
- 加完用 `folders` 数一下，确认真的进去了。

用户自己库里别的图（比如几千张海报）是别人的作品，只能当参考，不能剪进公开视频。
