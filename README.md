# AIGC Skills & Agents

马自立（[@MatsuriMW](https://github.com/MatsuriMW)）做 AI 短片和给稿子配图时用的 [Claude](https://claude.com/claude-code) skill 和工作区配置。这个仓库只放 AI 生图、生视频相关的；写作、笔记这些通用的在 [skills-agents-and-prompts](https://github.com/MatsuriMW/skills-agents-and-prompts)。

- **角色设定板（character-sheet）**：把一个角色的长相锁死，之后每个镜头都照着它生成，解决「同一个角色每个镜头长得不一样」。
- **古典式配图（gudianshi-skill）**：给文章和口播稿画解释图，版画的质感上插一个屏幕时代的元素。两种做法：全部用 SVG 画，或者把博物馆公开的雕像、油画、版画剪成纸片，和 SVG 拼在一起。
- **导演 skill（cinematic-director，改版）**：把剧本或一段文字变成分镜、调度和镜头清单。改自第三方 skill，加了杜琪峰的导演风格和一份中文视觉词汇表。
- **Eagle 拼贴素材（eagle-assets）**：从 Eagle 里一个放公有领域素材的文件夹（胸像、石膏手、版画、旧纸、颗粒纹理）里找图、拷进工程，顺手把出处和许可写进 `CREDITS.md`。
- **Eagle 音效（eagle-sfx）**：做片子时从 [Eagle](https://eagle.cool) 素材库的音效包里挑转场声、重击和拟音，量出每个音效最响的一下在第几秒，对在剪辑点上。
- **MiniMax 配音（minimax-tts）**：用 MiniMax 的 speech-2.8-hd 把口播稿配成音频，整篇按段合成、接成一条音轨、出字幕和每段的时长表，改稿后只重新合成改过的段。
- **欧美梗图（virgin-vs-chad）**：做 Virgin vs Chad 对比图、Yes Chad 回怼图这类简陋低幼风的配图，角色用经典梗图的原图，字和线用 SVG。
- **语言设计（yuyan-sheji）**：给角色建一份「语言档案」，按档案写台词、查台词，让律师、修理工、英国老钱、东北老板娘一开口就各是各的人，不再说同一种 AI 客服腔。
- **aigc-workspace**：把上面这些串起来的工作区规则文件。

角色设计（juese-sheji）原来也在这里，内容越做越多，已经拆到独立仓库 [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)，这里不再留副本。

## Skills

| skill | 作用 | 推荐度 | 需要什么 |
|---|---|---|---|
| [character-sheet](skills/character-sheet)（角色设定板） | 把参考图、一段角色描述或角色设计的产出，做成锁定角色长相的设定板 prompt：4:3 横版，三视图、剪影、8 种表情、5 种微表情、头部结构、姿态、特写、服装细节、手部动作；可以拆出单独的表情板（3×3 面部研究）和状态板（同一个人的几种精神状态）。表情一律写成低强度的肌肉动作和不动的部位，专门防生图模型把表情做夸张、做出 AI 味。先写一段逐项写实的「角色锁定段」，以后每个镜头都把它拼进 prompt。中英两版模板 | ★★★ 装上就能用 | 无；能生图的话可以直接出图 |
| [gudianshi-skill](skills/gudianshi-skill)（古典式配图） | 读完稿子，挑出最值得画的 3～6 个论点，每个画一张 1600×900 的 SVG：底下是版画排线和旧纸，上面只放一个只属于屏幕的东西（光标、加载圈、选中框、红点角标……），而且让它占住古典物件原本的位置。六种构图模板（对切、真假两条线、对照栏、被压扁、递减条、人物 + 对象 + 刺），数据图按同一个比例尺算坐标。只用一个强调色，不写标题和观点句。两个方向：纯 SVG（[`examples/`](skills/gudianshi-skill/examples) 里有 7 张成品），和 SVG + 拼贴素材（公有领域的雕像、浮雕、版画、器物照刻成版画线网的纸片，老油画沿轮廓剪下人和物、处理成美柔汀颗粒，[5 张成品](skills/gudianshi-skill/references/collage-examples)） | ★★★ 纯 SVG 装上就能用；★★ 拼贴要本机能跑脚本 | 纯 SVG：无。拼贴：Python（推荐用 [uv](https://docs.astral.sh/uv/)）和 Chrome；都不需要生图模型 |
| [cinematic-director](skills/cinematic-director)（导演 skill，改版） | 导演和预演：把剧本、一段文字或已有的图和视频素材，拆成潜台词、节拍表、导演阐述、调度走位、带覆盖镜头的镜头清单、关键帧和分镜 prompt、图生视频的运动 prompt、声音和对白方案、剪辑时间线、连戏手册和返修意见；可以套一位导演的风格。改自 [wuwangzhang1216/DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)（MIT）：加了杜琪峰风格（`references/director_styles/21_johnnie_to.md`）和中文视觉词汇表（`references/visual-vocabulary-zh.md`） | ★★ 内容多，先看它的 README | 无；出图和出视频要有对应的平台 |
| [eagle-assets](skills/eagle-assets)（Eagle 拼贴素材） | 做拼贴、撕纸风格的视频和海报时，从 Eagle 的「拼贴素材」文件夹里找图：按子文件夹或关键词列（查名字、注释、标签），`export` 把原图拷进项目目录，并在 `CREDITS.md` 里追加作者、年代、馆藏、许可和原页面。只收公有领域（CC0）素材，公开视频能直接用；也负责往这个文件夹里补新素材 | ★ 要先在 Eagle 里攒一个自己的素材文件夹，适合参考着改 | Eagle（开着）、Python 3（只用标准库）。仓库里不带任何素材图 |
| [eagle-sfx](skills/eagle-sfx)（Eagle 音效） | 从 Eagle 里的一整包音效（我的是一万四千多个、三百多个文件夹）里给视频挑音效：看文件夹树，按文件夹、关键词、时长筛，名字和文件夹名一起搜，支持「键盘 OR 打字」和「脚步 -雪」这样的写法。用 ffmpeg 量出每个音效最响的一下在第几秒、听得见的那一段有多长，分成打击、掠过、上升三种形状；导出时把文件拷进工程，并写一份记着这些数的 `sfx.json`，照着它就能把峰值钉在目标帧上。量过的数会记下来，文件在 iCloud 上没下载的会标出来、用到时才下载。对 Eagle 只读 | ★ 和我的音效库绑得深，适合参考着改 | Eagle（开着）、Python 3、ffmpeg；Eagle 里要有一个放音效的文件夹。仓库里不带任何音效文件 |
| [minimax-tts](skills/minimax-tts)（MiniMax 配音） | 给视频配音：念一句，或者把整篇稿子按空行分段合成，标题、引用、表格、`【画面：…】` 这类标注自动跳过，`--only` 只念某一章。产出每段一个音频、一份记着每段时长和起点的 `manifest.json`（剪辑和 Remotion 对时间用），可选接成整条音轨、出对齐的 SRT 字幕。改稿后重跑，没变的段沿用上次的文件、不重复花钱。另有查音色、复刻自己的声音、合成前估价。SKILL.md 里写了停顿、语气词、多音字怎么标，让它念得像人 | ★★ 有密钥就能用；字幕结构和复刻是照官方文档写的，还没用真密钥跑过 | Python 3（只用标准库）、MiniMax 开放平台的接口密钥（读环境变量或 macOS 钥匙串）；接整条音轨要 ffmpeg |
| [virgin-vs-chad](skills/virgin-vs-chad)（欧美梗图） | 四种格式：Virgin vs Chad 对比（左右两个角色各一圈标注、底下一句结论）、Yes Chad 回怼（一方说一大段，Chad 只回「Yes.」）、单角色标注、Impact 上下字。写一份 JSON 描述，脚本把标题、标注、指引线写进 SVG（中文不乱码、每条标注能单独改），用 Chrome 渲染成 PNG。SKILL.md 里写了哪个角色适合表达什么、标注怎么写才好笑 | ★ 角色图要自己准备，适合参考着改 | Python 3、Chrome、ImageMagick；Eagle 里一个放梗图角色原图的文件夹。仓库里不带角色图 |
| [yuyan-sheji](skills/yuyan-sheji)（语言设计） | 从说话习惯塑造角色：用出身阶级和现在的阶级、国别地区、年龄、教育、职业推出这个人怎么说话，拆成十个能逐项检查的维度：口音和英式 / 美式 / 澳洲用词、黑人英语（AAVE）的语法规则、律师腔、京味儿和东北话、随对象切换语体、用词水平和 U / non-U、夹法语和拉丁语（吃饭前的 *Bon appétit*、举杯的 *Santé*，也分阶层）、句子复杂度、口头禅（每个都有频率上限）、用典、语用、情绪失控时往哪个方向崩。英国角色要过词表、语法、语用、阶层四关，附《吸血鬼日记》Klaus 和《路西法》Lucifer 的拆解。四个模式：从样本建档、从人设建档（接[角色设计](https://github.com/MatsuriMW/ai-character-design-skill)）、按档案写或改台词、逐句检查并回写档案。带五个反差大的示例角色和七个验收用例；跑过三轮盲测（每轮四个人各 3 句、打乱去名，另一个模型只看档案认人：自己写台词 12/12，换一个会话写 10/12，按认错的句子补档案后 12/12），题、答案和每轮记录都在 `evals/`。脚本能统计台词特征，按英式 / 美式 / 澳洲词表抓用词和拼写穿帮 | ★★★ 装上就能用 | 无；脚本要 Python 3（只用标准库） |

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

画面的主角换成真的老东西：大理石胸像、全身雕像、浮雕、石膏手、五百年前的铜版画，以及从老油画里剪下来的人和物。这些图来自博物馆的开放馆藏，公有领域，可以放心用在公开发布的内容里。素材先刻成和 SVG 排线同样角度、同样疏密的版画线网（油画改用美柔汀颗粒，大片柔和的明暗不会被线网刻碎），再放进 SVG 画的壁龛、拱窗、画框里；那个「刺」仍然是 SVG 画的，纯色、硬边。

<p>
  <img src="skills/gudianshi-skill/references/collage-examples/01_%E6%B2%A1%E8%AF%B4%E5%87%BA%E5%8F%A3%E7%9A%84%E9%83%A8%E5%88%86.jpg" width="49%" alt="希罗多德胸像被刻成版画线网，嘴里伸出一个输入框，红色光标后面是替他补全的灰条">
  <img src="skills/gudianshi-skill/references/collage-examples/02_%E5%90%8C%E4%B8%80%E5%8F%AA%E6%89%8B%E4%B8%A4%E7%A7%8D%E7%94%BB%E6%B3%95.jpg" width="49%" alt="对切：罗丹的《握紧的左手》，左半边是版画，右半边是马赛克，光标点在一个红色像素上">
</p>
<p>
  <img src="skills/gudianshi-skill/references/collage-examples/03_%E7%8B%AE%E9%B9%AB%E8%A2%AB%E9%80%89%E4%B8%AD.jpg" width="49%" alt="施恩告尔的铜版画《狮鹫》装在 SVG 画的尖拱窗里，头上套着一个带八个控制点的选中框">
  <img src="skills/gudianshi-skill/references/collage-examples/04_%E6%89%8B%E6%90%AD%E5%9C%A8%E8%8D%B7%E9%A9%AC%E5%A4%B4%E4%B8%8A.jpg" width="49%" alt="伦勃朗油画里剪下的亚里士多德和荷马胸像，处理成美柔汀颗粒；他搭在胸像头上的手停着一个红色光标，旁边弹出「荷马 · hover 2,700 年」的提示框">
</p>
<p>
  <img src="skills/gudianshi-skill/references/collage-examples/05_%E6%96%AD%E8%87%82%E9%95%BF%E5%87%BA%E5%85%89%E6%A0%87.jpg" width="49%" alt="罗马大理石老妇人像立在 SVG 画的壁龛里，断臂的缺口伸出一条虚线补出的前臂，末端是红色光标和 ⌘ Z 键">
</p>

五张图的接法：

| 图 | 素材 | 素材怎么处理 | 和 SVG 怎么接 | 刺 |
|---|---|---|---|---|
| 没说出口的部分 | 希罗多德胸像（大都会艺术博物馆） | 照片刻成版画线网，带剪刀白边 | 壁龛和台面的排线跟素材同角度、同疏密；纸片的投影只位移不模糊 | 从嘴里伸出来的输入框 |
| 同一只手两种画法 | 罗丹《握紧的左手》（大都会艺术博物馆） | 同一张图处理两遍：版画线网、马赛克 | 两张叠在同一个位置，沿分割线各露一半 | 光标，点在一个红色像素上 |
| 狮鹫被选中 | 施恩告尔《狮鹫》（克利夫兰艺术博物馆） | 版画只留墨线，纸变透明 | 用 SVG 画的尖拱把它裁出来，拱外是交叉排线 | 八个控制点的选中框 |
| 手搭在荷马头上 | 伦勃朗《亚里士多德与荷马胸像》（大都会艺术博物馆） | 沿轮廓剪出人和胸像，美柔汀颗粒 | 人物从 SVG 画框里出框，环境用颗粒不用排线 | 手搭在胸像头上就是一次悬停：光标 + 提示框 |
| 断臂长出光标 | 罗马大理石老妇人像（大都会艺术博物馆） | 展厅照抠图，压暗后刻成版画线网 | SVG 壁龛和台座，排线同频 | 长在断臂缺口上的虚线前臂和光标 |

**怎么用**

1. 说「用古典式，做拼贴的」或者「用素材配图」，把稿子给它。没点名的时候它自己判断：主角是一个具体的人或器物、又找得到合适的素材，就走拼贴；稿子讲的是一个场景、一个动作（有人在指、在看、在读信），它会去油画里找那一幕剪下来；数据图走纯 SVG。
2. 素材先从你自己的素材库里挑（配合 Eagle 用时），不够再去大都会、芝加哥、克利夫兰这几家博物馆的开放馆藏里找，只取公有领域或 CC0 的（油画要作者去世七十年以上、且照片是馆藏标了公有领域的那张），并把作品名、作者、年代、馆藏、许可记进 `CREDITS.md`。你也可以把自己的图丢给它，但要是你有权使用的。
3. 它用 `scripts/prep_asset.py` 把素材抠图、刻成纸片（油画满幅都是东西，它会先出一张带网格的预览图，照着网格写剪刀路径，只把要的那个人或物剪下来），写好 SVG，再用 `scripts/pack_svg.py` 打包。你拿到的是 `imgs/` 下的一个单文件 SVG（位图已经嵌在里面）和一张 3200×1800 的 PNG。

**需要什么**

- Python。装了 [uv](https://docs.astral.sh/uv/) 的话依赖会自动装好；没有就 `pip install pillow numpy opencv-python-headless "rembg[cpu]"`。
- Chrome、Chromium 或 Edge，用来把 SVG 渲染成 PNG。
- 第一次抠图会下载一个 176 MB 的模型，要等一会儿。
- 在 claude.ai 里用时没有这些条件，它会退回纯 SVG。

素材有七种处理方式（版画线网、美柔汀颗粒、报纸网点、只留墨线、连续调、马赛克、纸纹），油画和雕像各自怎么剪、怎么调明暗，和 SVG 的六种接法、图层顺序、容易踩的坑，都写在 [`references/collage.md`](skills/gudianshi-skill/references/collage.md)。

### 两个方向都守的规矩

- **图不替代说话的人**。画面里只留图离不开的字：年份、数字、单位、坐标刻度、两三个字的标签，最多再加一两行陈述事实的说明。标题、观点句、你嘴里会说出来的话，一律不写进图里。
- **数字要核实过才上图**。数据图先写出坐标的换算公式再画；不按比例的示意图会在交付时说明。
- **只有一个强调色**。素材进画面之前一律处理成墨色，不保留原色；红色只给刺或关键数据。
- **不抄有版权的东西**。纯 SVG 的古典层都是原创的剪影和排线；拼贴只用公有领域或 CC0 的素材，并记出处。别人的海报、摄影、插画不剪进来。
- **不给生图模型写 prompt**。两个方向都不生图。

**你可以这样说**：「给这篇稿子配图」「用古典式」「做几张解释图」「把这组数据画成图」「用拼贴素材做」。给它稿子就行，它自己挑论点、选构图。

这个 skill 在 claude.ai 上也能用（上传 `skills/gudianshi-skill` 目录的 zip，那里只能走纯 SVG），SkillHub 上的 slug 是 `gudianshi`。

## Eagle 音效

用代码做片子（Remotion、ffmpeg），声音这一步最费时间的是两件事：在几千上万个文件里找到合适的那一个，再把它对准画面。这个 skill 把两件事都交给脚本。

**找**。脚本每次从 Eagle 的本机接口取一遍音效包的目录，一两秒，不读音频文件。然后有三种找法：

| 找法 | 命令 | 适合什么 |
|---|---|---|
| 看文件夹 | `folders`、`list --folder 转场 --max 1.5` | 知道要哪一类，想按时长筛 |
| 搜关键词 | `search "键盘 OR 打字 -机械"` | 名字和文件夹名一起搜。音效包里常有几千个只有编号的文件，只能靠文件夹名找到 |
| 按意思搜 | `search --ai "快速的嗖声"` | 不知道这包里管它叫什么。要 Eagle 的 MCP Server 和 AI Search 两个插件；比的是名字的含义，不是声音本身 |

**对**。转场声和重击要对的是最响的那一下，不是文件开头：一个嗖声往往要铺垫零点几秒才到顶。脚本用 ffmpeg 量出峰值在第几秒，导出时写进 `sfx.json`，音效就从 `目标帧 − 峰值秒 × 帧率` 开始放。

```tsx
// 让 space-woosh.wav（峰值在 0.73 秒）最响的一下落在第 90 帧
<Sequence from={Math.round(90 - 0.73 * fps)}>
  <Audio src={staticFile("sfx/space-woosh.wav")} volume={0.6} />
</Sequence>
```

SKILL.md 里还有一张表，写的是画面上的哪种动作配哪种声音、峰值对在哪一帧：硬切配短嗖声，标题落定配重击，揭晓之前用一个铺垫一秒以上才到顶的上升声。

**你可以这样说**：「给这三个转场配上嗖声」「标题砸下来那一帧加个重击」「找几个两秒以内的脚步声让我挑」「片子开头铺一层下雨的环境声」。

**想用在自己的音效库上**

它是照着我自己的库写的，换一个库要改三处：

1. 脚本默认找 Eagle 里叫「董北 音效」的顶层文件夹。换成你的，设环境变量 `EAGLE_SFX_ROOT`，或者改 `scripts/eagle_sfx.py` 开头的 `ROOT`。
2. `--kind` 的类别（嗖声、重击、玻璃……）是按英文文件名里的词分的，规则在脚本的 `KINDS` 表里，按你的库里的命名改。
3. SKILL.md 里的分类表和数量是我这包的，换成你的，Claude 才知道库里有什么。

仓库里没有音效文件，也没有我量出来的索引。音效的版权要自己把关：我这包是课程附赠的合集，出处不明，所以 skill 里写着公开发布的片子用之前先问本人；你的库如果都是买断或 CC0 的，把那一段删掉就行。

## 欧美梗图

**你可以这样说**：「做一张 Virgin vs Chad，左边是天天抽卡的，右边是先写剧本再生图的」「Yes Chad 回怼图」「给这段话配个 Impact 字」。

仓库里只有脚本和说明，没有角色图：这批梗图出处和许可各不相同，GigaChad 还是真人照片。自己用要先准备角色库：

1. 在 Eagle 里建一个叫「梗图角色」的文件夹（想用别的名字，改 `scripts/prep_chars.py` 开头的 `FOLDER`），把 Wojak、Yes Chad 这些原图放进去，条目名和 `CHARS` 表里写的一致。
2. 跑 `python3 scripts/prep_chars.py`，它按 `CHARS` 里记的框把多人合图裁开，存进角色库并写好 `chars.json`。框是我那几张原图上的像素坐标，你的图不一样就要改。
3. `python3 scripts/meme.py example versus > 图.json` 拿一份样子改，再 `render` 出图。

公开发布的图别用真人照片那几个角色；Soyjak 那张是 CC BY-SA 2.0，要署名。

## 安装

把 `skills/` 下要用的目录复制到 Claude Code 的 skill 目录，重开会话：

- 全局用：`~/.claude/skills/`
- 只在某个项目里用：`<项目>/.claude/skills/`

## 许可

我自己写的 skill（character-sheet、古典式配图、eagle-assets、eagle-sfx、minimax-tts、virgin-vs-chad、语言设计）和 aigc-workspace 的规则文件按 [CC BY-NC-SA 4.0](LICENSE)（署名-非商业性使用-相同方式共享）发布，每个 skill 目录里的 `LICENSE.md` 有中文说明：

- 可以免费用、转载、改编，要写明原作者「马自立（MatsuriMW）」和出处链接，改编后的版本用同一个协议发布。
- 不能拿 skill 本身去卖：付费下载、打包进付费课程或资料包、在付费 skill 市场转售都不行。
- 用它们做出来的图、视频、配音、文案归你自己，不受这个协议限制。
- 想商用，或者拿不准算不算商用，联系作者。

例外：cinematic-director 改自 [wuwangzhang1216/DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)，原作的文件仍按 MIT，只有我加的杜琪峰风格和中文视觉词汇表两份按 CC BY-NC-SA 4.0，见它目录里的 `NOTICE.md`。拼贴样图里的公有领域素材仍是公有领域，出处见各自的 `CREDITS.md`。改协议之前已经推送的提交仍按原来的条件。

## 相关仓库

- [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)：角色设计 skill，把「一个轻佻的男性」这种模糊感觉拆成八个维度的名词和动作，有一键安装脚本和 claude.ai 用的 zip
- [skills-agents-and-prompts](https://github.com/MatsuriMW/skills-agents-and-prompts)：我其他的 skill、agent 和提示词（写作、笔记问答、投资研究等）
