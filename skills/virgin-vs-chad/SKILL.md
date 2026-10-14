---
name: virgin-vs-chad
description: 做欧美梗图风格的配图：Virgin vs Chad 对比图（两个角色、各一圈标注）、Yes Chad 回怼图（一方说一大段，Chad 只回「Yes.」「对。」）、单角色标注图（「The 27 岁的 Doomer」那种）、Impact 上下字。角色用真的梗图角色（Wojak、Soyjak、Yes Chad、Stacy、Becky、Doomer、NPC、Brainlet、GigaChad 等，来自用户 Eagle 的「梗图角色」文件夹），标题、标注、指引线、Impact 字用 SVG 写，出 SVG 和 PNG。用户说「Virgin vs Chad」「chad 那种图」「做个对比梗图」「wojak」「soyjak」「Yes Chad」「梗图配图」「meme 图」「Impact 字」「简陋低幼风」「欧美梗图」，或者要给文章、口播、视频做一张讽刺对比的配图时使用。要动图、视频梗素材时去 Eagle 的「梗图角色」文件夹找，不用这个 skill 出图。
---

# Virgin vs Chad 梗图

一句话：**角色用真图，字和线用 SVG**。角色是网上那批经典梗图角色的原图（裁成单个人），标题、标注、指引线、Impact 字是脚本按描述文件写进 SVG 的，所以中文不会乱码、每条标注都能单独改，最后用 Chrome 渲染成 PNG。

## 先准备角色库（第一次用，或者 Eagle 里加了新角色以后）

```bash
python3 scripts/prep_chars.py        # Eagle 要开着；从「梗图角色」文件夹取原图，裁成单个角色
python3 scripts/meme.py chars        # 看有哪些角色
```

角色库在 `~/claude/aigc/assets/meme-chars/`（`chars.json` 记着每个角色的出处、许可、朝向和适合表达什么）。合图里的多个人（Virgin 和 Chad、Becky 和 Stacy、一群 NPC）按 `prep_chars.py` 里 `CHARS` 记好的框裁开；Eagle 里新加了角色，要在 `CHARS` 里加一行再重跑。

## 出图

写一份描述文件（JSON），再渲染：

```bash
python3 scripts/meme.py example versus > 图.json   # 先拿一份样子改
python3 scripts/meme.py render 图.json -o 输出/名字   # 出 名字.svg（图片内嵌，单文件）和 名字.png（3200×1800）
```

四种格式：

| template | 是什么 | 要填的 |
|---|---|---|
| `versus` | Virgin vs Chad 对比：左右两半，各一个角色、一行标题、一圈标注，底下一句结论 | `left` / `right` 各写 `char`、`title`、`notes`（每边 3–6 条）；`footer` |
| `reply` | Yes Chad 回怼：左边激动地说一大段，右边 Chad 只回一个词 | `left.char`（默认 soyjak）、`left.text`；`right.char`（默认 yes-chad）、`right.text` |
| `labels` | 单个角色 + 一圈标注 | `char`、`title`、`notes`（4–8 条） |
| `impact` | Impact 上下字：白字黑描边分在上下两头 | `char`（角色 id 或任意图片路径）、`top`、`bottom` |

可选项：`flip: true` 左右翻转角色（让脸朝向画面中间）；`width`（versus 里角色占半边的比例，默认 0.46）；`note_size`、`title_size`；`valign`（versus 默认 `middle`，全身像可以改 `bottom`）。

## 怎么配角色

- **对比图默认用 Wojak 对 Yes Chad**：两个都是同一种线稿风格的半身像，放在一起画风统一。**不要用那个彩色的 Chad Stride（黄尖头、绿裤子）**，用户不喜欢，而且全身像放进半边以后太小。
- 女性对比用 Becky 对 Stacy，或者 Wifejak / Doomer Girl 对 Yes Stacy。
- 张嘴哥 Soyjak 当「无脑兴奋、盲目追捧」的一方；NPC 当「人云亦云」；Doomer 当「丧、虚无」；Brainlet 当「想不明白」。
- Yes Chad 和 Yes Stacy 是侧脸朝左：放在右半边正好看向左边。放到左边就加 `flip: true`。
- **GigaChad、女版 GigaChad 是真人照片**（摄影师 Krista Sudmalis 的作品，后者就是她本人）。可以自己看、私下用；要公开发布的图不要用，脚本用到时会提醒。
- 其余角色是网络匿名梗图，作者不明；Soyjak 那张是 CC BY-SA 2.0，公开用要署名「The Frees / Wikimedia Commons」。出处都在 `chars.json` 和 Eagle 每张图的注释里。

## 写字的规矩

- **标题**沿用原梗的句式：`THE VIRGIN XX` / `THE CHAD XX`，XX 用中文，两三个字最好。
- **标注**一条一个具体的行为或细节，不写评价词：「同一句 prompt 抽了 40 张」比「很低效」好笑。Virgin 那边写畏缩、纠结、自我感动的细节；Chad 那边写坦然、简单、结果好得离谱的细节，可以一本正经地夸张。
- 每边 3–6 条，一条十几个字以内；超过两行就删字。
- `footer` 放这张图要说的那句真话，可以是文章里的核心论点。
- 要中英混排就混排，英文单词不会被从中间折断，句末标点不会被挤到行首。
- 不碰原梗里那些冲着族群、性别、性取向、自杀去的变体，这类图不做。

## 其他素材

用户 Eagle 的「梗图角色」文件夹里还有：`GigaChad 动图`、`Wojak 家族动图`、`经典视频梗`（This is fine、Stonks、Coffin Dance、Surprised Pikachu 等）、`配色版本`、`剪辑用 MP4`。做视频要反应镜头、做口播要插梗时去那里挑，MP4 直接拖进剪映或 ChatCut。它们大多是 GIF 平台转载的影视画面，版权归原作者，商业视频里用之前要再确认。

## 交付

存到 `~/claude/aigc/exports/<项目>/`，SVG 和 PNG 一起给。回复里贴 PNG，说清用了哪两个角色、哪些标注可以再改。
