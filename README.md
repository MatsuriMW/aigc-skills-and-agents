# AIGC Skills & Agents

马自立（[@MatsuriMW](https://github.com/MatsuriMW)）做 AI 短片和给稿子配图时用的 [Claude](https://claude.com/claude-code) skill 和工作区配置。这个仓库只放 AI 生图、生视频相关的；写作、笔记这些通用的在 [skills-agents-and-prompts](https://github.com/MatsuriMW/skills-agents-and-prompts)。

- **角色设定板（character-sheet）**：把一个角色的长相锁死，之后每个镜头都照着它生成，解决「同一个角色每个镜头长得不一样」。
- **古典式配图（gudianshi-skill）**：给文章和口播稿画解释图，版画的质感上插一个屏幕时代的元素。两种做法：全部用 SVG 画，或者把博物馆公开的雕像、版画处理成纸片，和 SVG 拼在一起。
- **导演 skill（cinematic-director，改版）**：把剧本或一段文字变成分镜、调度和镜头清单。改自第三方 skill，加了杜琪峰的导演风格和一份中文视觉词汇表。
- **aigc-workspace**：把上面这些串起来的工作区规则文件。

角色设计（juese-sheji）原来也在这里，内容越做越多，已经拆到独立仓库 [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)，这里不再留副本。

## Skills

| skill | 作用 | 推荐度 | 需要什么 |
|---|---|---|---|
| [character-sheet](skills/character-sheet)（角色设定板） | 把参考图、一段角色描述或角色设计的产出，做成锁定角色长相的设定板 prompt：4:3 横版，三视图、剪影、8 种表情、5 种微表情、头部结构、姿态、特写、服装细节、手部动作；可以拆出单独的表情板（3×3 面部研究）和状态板（同一个人的几种精神状态）。表情一律写成低强度的肌肉动作和不动的部位，专门防生图模型把表情做夸张、做出 AI 味。先写一段逐项写实的「角色锁定段」，以后每个镜头都把它拼进 prompt。中英两版模板 | ★★★ 装上就能用 | 无；能生图的话可以直接出图 |
| [gudianshi-skill](skills/gudianshi-skill)（古典式配图） | 读完稿子，挑出最值得画的 3～6 个论点，每个画一张 1600×900 的 SVG：底下是版画排线和旧纸，上面只放一个只属于屏幕的东西（光标、加载圈、选中框、红点角标……），而且让它占住古典物件原本的位置。六种构图模板（对切、真假两条线、对照栏、被压扁、递减条、人物 + 对象 + 刺），数据图按同一个比例尺算坐标。只用一个强调色，不写标题和观点句。两个方向：纯 SVG（[`examples/`](skills/gudianshi-skill/examples) 里有 7 张成品），和 SVG + 拼贴素材（公有领域的雕像、版画、器物照刻成版画线网的纸片，[3 张成品](skills/gudianshi-skill/references/collage-examples)） | ★★★ 纯 SVG 装上就能用；★★ 拼贴要本机能跑脚本 | 纯 SVG：无。拼贴：Python（推荐用 [uv](https://docs.astral.sh/uv/)）和 Chrome；都不需要生图模型 |

| [cinematic-director](skills/cinematic-director)（导演 skill，改版） | 导演和预演：把剧本、一段文字或已有的图和视频素材，拆成潜台词、节拍表、导演阐述、调度走位、带覆盖镜头的镜头清单、关键帧和分镜 prompt、图生视频的运动 prompt、声音和对白方案、剪辑时间线、连戏手册和返修意见；可以套一位导演的风格。改自 [wuwangzhang1216/DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)（MIT）：加了杜琪峰风格（`references/director_styles/21_johnnie_to.md`）和中文视觉词汇表（`references/visual-vocabulary-zh.md`） | ★★ 内容多，先看它的 README | 无；出图和出视频要有对应的平台 |

## Agents

| agent | 作用 | 推荐度 | 需要什么 |
|---|---|---|---|
| [aigc-workspace](agents/aigc-workspace) | AI 短片前期工作区的规则文件（`CLAUDE.md`）：目录怎么分（角色设定板、短片项目、参考资料）、从剧本到分镜、角色设计、角色设定板再到按模型写 prompt 的几个 skill 怎么分工、产出存在哪、版本怎么编号 | ★ 和我的目录约定绑得深，适合参考 | 上面的 skill；[角色设计](https://github.com/MatsuriMW/ai-character-design-skill) |

工作区里还用到两个原样下载的第三方 skill，这里不收录，需要的话去原仓库装：按具体模型写生图 / 生视频 prompt 的 `image` 和 `video`，来自 [smixs/visual-skills](https://github.com/smixs/visual-skills)（CC-BY-4.0）。

## 角色设定板

用 AI 做一部短片，最常见的问题是**同一个角色每个镜头长得不一样、穿得不一样**。设定板是这条链路上的第二步：

```
剧本 / 节拍表 / 分镜
      │
      ▼
juese-sheji 角色设计 ── 模糊感觉 → 名词和动作 → 服化道总表 + 锁定段，定下主造型
      │                  （独立仓库：ai-character-design-skill）
      ▼
character-sheet 角色设定板 ── 三视图 + 不夸张的表情板 + 细节的设定板 prompt，锁定角色长相
      │                  （本仓库）
      ▼
生图 / 生视频（GPT Image、Nano Banana、Seedance、Kling…）：每个镜头 = 角色锁定段 + 本场造型 + 镜头描述
```

**你可以这样说**：「做一张角色设定板」「锁定这个角色的长相」「三视图」「character sheet」。手上已经有角色设计的产出时，设定板会直接沿用它的锁定段，不会重写。

有项目目录时，产出默认存进 `character-sheets/<角色>/`（prompt、参考图、生成结果）；没有就直接在对话里给。

可以配合的其他 skill：上游分镜 / 导演用本仓库的 [cinematic-director](skills/cinematic-director)，下游按具体模型写 prompt 用 [visual-skills](https://github.com/smixs/visual-skills)。

## 古典式配图

给口播和文章配图，AI 生图的毛病是每张都像素材库：好看，但和你正在讲的那句话没关系。古典式走另一条路：不生图，直接写 SVG，需要的时候再拼上真的老物件。**古典层负责质感，现代层负责刺**，一张图只放一个刺，放在画面里那个「被指着、被捧着、被供奉着」的位置上。

<p>
  <img src="skills/gudianshi-skill/examples/04_%E5%90%8C%E4%B8%80%E6%9E%9A%E7%A1%AC%E5%B8%81%E4%B8%A4%E5%A5%97%E5%88%A4%E5%86%B3.svg" width="49%" alt="对切：左边 1179 年的尖拱墓碑，右边 2026 年的卡片 UI，同一枚硬币骑在分割线上">
  <img src="skills/gudianshi-skill/examples/01_%E5%88%BB%E5%BA%A6%E5%9C%A8%E5%8A%A8.svg" width="49%" alt="台阶上的金币，旁边的刻度尺套着一个带八个控制点的选中框">
</p>
<p>
  <img src="skills/gudianshi-skill/examples/02_%E5%80%9F%E7%9F%AD%E8%BF%98%E9%95%BF%E7%A9%BA%E8%BD%AC.svg" width="49%" alt="古典轮盘：印钞、长债、回购、短债循环，轮心是一个加载圈">
  <img src="skills/gudianshi-skill/examples/06_%E4%B8%89%E5%B1%82%E8%A2%AB%E5%8E%8B%E6%88%90%E4%B8%80%E5%B1%82.svg" width="49%" alt="被压扁：三级带排线的台阶被一根纯黑横杠压成一层">
</p>

它有两个方向，规矩是同一套，差别只在古典层怎么来。

### 方向一：纯 SVG

上面四张都是。古典层全部用矢量画：剪影、排线、暗角。交付一个 SVG，拿到手可以直接改字、改数、改颜色。数据图和结构图走这个方向，它们靠比例尺和排线密度说话。

### 方向二：SVG + 拼贴素材

画面的主角换成真的老东西：大理石胸像、石膏手、五百年前的铜版画。这些图来自博物馆的开放馆藏，公有领域，可以放心用在公开发布的内容里。素材先刻成和 SVG 排线同样角度、同样疏密的版画线网，再放进 SVG 画的壁龛、拱窗里；那个「刺」仍然是 SVG 画的，纯色、硬边。

<p>
  <img src="skills/gudianshi-skill/references/collage-examples/01_%E6%B2%A1%E8%AF%B4%E5%87%BA%E5%8F%A3%E7%9A%84%E9%83%A8%E5%88%86.jpg" width="49%" alt="希罗多德胸像被刻成版画线网，嘴里伸出一个输入框，红色光标后面是替他补全的灰条">
  <img src="skills/gudianshi-skill/references/collage-examples/02_%E5%90%8C%E4%B8%80%E5%8F%AA%E6%89%8B%E4%B8%A4%E7%A7%8D%E7%94%BB%E6%B3%95.jpg" width="49%" alt="对切：罗丹的《握紧的左手》，左半边是版画，右半边是马赛克，光标点在一个红色像素上">
</p>
<p>
  <img src="skills/gudianshi-skill/references/collage-examples/03_%E7%8B%AE%E9%B9%AB%E8%A2%AB%E9%80%89%E4%B8%AD.jpg" width="49%" alt="施恩告尔的铜版画《狮鹫》装在 SVG 画的尖拱窗里，头上套着一个带八个控制点的选中框">
</p>

三张图用了三种接法：

| 图 | 素材 | 素材怎么处理 | 和 SVG 怎么接 | 刺 |
|---|---|---|---|---|
| 没说出口的部分 | 希罗多德胸像（大都会艺术博物馆） | 照片刻成版画线网，带剪刀白边 | 壁龛和台面的排线跟素材同角度、同疏密；纸片的投影只位移不模糊 | 从嘴里伸出来的输入框 |
| 同一只手两种画法 | 罗丹《握紧的左手》（大都会艺术博物馆） | 同一张图处理两遍：版画线网、马赛克 | 两张叠在同一个位置，沿分割线各露一半 | 光标，点在一个红色像素上 |
| 狮鹫被选中 | 施恩告尔《狮鹫》（克利夫兰艺术博物馆） | 版画只留墨线，纸变透明 | 用 SVG 画的尖拱把它裁出来，拱外是交叉排线 | 八个控制点的选中框 |

**怎么用**

1. 说「用古典式，做拼贴的」或者「用素材配图」，把稿子给它。没点名的时候它自己判断：主角是一个具体的人或器物、又找得到合适的素材，就走拼贴；数据图走纯 SVG。
2. 素材它会去大都会、芝加哥、克利夫兰这几家博物馆的开放馆藏里找，只取公有领域或 CC0 的，并把作品名、作者、年代、馆藏、许可记进 `CREDITS.md`。你也可以把自己的图丢给它，但要是你有权使用的。
3. 它用 `scripts/prep_asset.py` 把素材抠图、刻成纸片，写好 SVG，再用 `scripts/pack_svg.py` 打包。你拿到的是 `imgs/` 下的一个单文件 SVG（位图已经嵌在里面）和一张 3200×1800 的 PNG。

**需要什么**

- Python。装了 [uv](https://docs.astral.sh/uv/) 的话依赖会自动装好；没有就 `pip install pillow numpy opencv-python-headless "rembg[cpu]"`。
- Chrome、Chromium 或 Edge，用来把 SVG 渲染成 PNG。
- 第一次抠图会下载一个 176 MB 的模型，要等一会儿。
- 在 claude.ai 里用时没有这些条件，它会退回纯 SVG。

素材有六种处理方式（版画线网、报纸网点、只留墨线、连续调、马赛克、纸纹），和 SVG 的六种接法、图层顺序、容易踩的坑，都写在 [`references/collage.md`](skills/gudianshi-skill/references/collage.md)。

### 两个方向都守的规矩

- **图不替代说话的人**。画面里只留图离不开的字：年份、数字、单位、坐标刻度、两三个字的标签，最多再加一两行陈述事实的说明。标题、观点句、你嘴里会说出来的话，一律不写进图里。
- **数字要核实过才上图**。数据图先写出坐标的换算公式再画；不按比例的示意图会在交付时说明。
- **只有一个强调色**。素材进画面之前一律处理成墨色，不保留原色；红色只给刺或关键数据。
- **不抄有版权的东西**。纯 SVG 的古典层都是原创的剪影和排线；拼贴只用公有领域或 CC0 的素材，并记出处。别人的海报、摄影、插画不剪进来。
- **不给生图模型写 prompt**。两个方向都不生图。

**你可以这样说**：「给这篇稿子配图」「用古典式」「做几张解释图」「把这组数据画成图」「用拼贴素材做」。给它稿子就行，它自己挑论点、选构图。

这个 skill 在 claude.ai 上也能用（上传 `skills/gudianshi-skill` 目录的 zip，那里只能走纯 SVG），SkillHub 上的 slug 是 `gudianshi`。

## 安装

把 `skills/` 下要用的目录复制到 Claude Code 的 skill 目录，重开会话：

- 全局用：`~/.claude/skills/`
- 只在某个项目里用：`<项目>/.claude/skills/`

## 相关仓库

- [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)：角色设计 skill，把「一个轻佻的男性」这种模糊感觉拆成八个维度的名词和动作，有一键安装脚本和 claude.ai 用的 zip
- [skills-agents-and-prompts](https://github.com/MatsuriMW/skills-agents-and-prompts)：我其他的 skill、agent 和提示词（写作、笔记问答、投资研究等）
