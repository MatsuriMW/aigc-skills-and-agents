# AIGC Skills & Agents

马自立（[@MatsuriMW](https://github.com/MatsuriMW)）给 AI 短片、AI 生图 / 生视频做前期设计用的 [Claude Code](https://claude.com/claude-code) skill。

用 AI 做一部短片，最常见的问题是**同一个角色每个镜头长得不一样、穿得不一样**。这里的 skill 解决这条链路上的两步：先把角色设计具体，再把它锁定成一张设定板，之后每个镜头都照着它生成。

```
剧本 / 节拍表 / 分镜
      │
      ▼
juese-sheji 角色设计 ── 模糊感觉 → 名词和动作 → 服化道总表 + 锁定段，定下主造型
      │                  （独立仓库：ai-character-design-skill）
      ▼
character-sheet 角色设定板 ── 三视图 + 表情 + 细节的设定板 prompt，锁定角色长相
      │                  （本仓库）
      ▼
生图 / 生视频（GPT Image、Nano Banana、Seedance、Kling…）：每个镜头 = 角色锁定段 + 本场造型 + 镜头描述
```

## Skills

| skill | 作用 | 推荐度 | 需要什么 |
|---|---|---|---|
| [character-sheet](skills/character-sheet)（角色设定板） | 把参考图、一段角色描述或角色设计的产出，做成锁定角色长相的设定板 prompt：4:3 横版，三视图、剪影、8 种表情、5 种微表情、头部结构、姿态、特写、服装细节、手部动作。先写一段逐项写实的「角色锁定段」，以后每个镜头都把它拼进 prompt。中英两版模板 | ★★★ 装上就能用 | 无；能生图的话可以直接出图 |
| [juese-sheji](https://github.com/MatsuriMW/ai-character-design-skill)（角色设计） | 把「一个轻佻的男性」「一个老年人」这种模糊的人物感觉，拆成脸、发型、配饰、服装、体态、生活痕迹、微表情、说话方式八个维度，每个维度写成模型能直接执行的名词和动作；另有 122 张人物原型卡、风格库、服化道和连戏表、群像拉开、出图后的漂移检查 | ★★★ 装上就能用 | 无 |

角色设计 skill 内容比较多，单独放在 [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)，那里有一键安装脚本和 claude.ai 用的 zip。

**你可以这样说**：「做一张角色设定板」「锁定这个角色的长相」「三视图」「character sheet」。手上已经有角色设计的产出时，设定板会直接沿用它的锁定段，不会重写。

可以配合的其他 skill：上游分镜 / 导演用 [DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)，下游按具体模型写 prompt 用 [visual-skills](https://github.com/smixs/visual-skills)。

## 安装

把 `skills/` 下的目录复制到 Claude Code 的 skill 目录，重开会话：

- 全局用：`~/.claude/skills/`
- 只在某个项目里用：`<项目>/.claude/skills/`

有项目目录时，产出默认存进 `character-sheets/<角色>/`（prompt、参考图、生成结果）；没有就直接在对话里给。

## 相关仓库

- [ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)：角色设计 skill
- [skills-agents-and-prompts](https://github.com/MatsuriMW/skills-agents-and-prompts)：我其他的 skill、agent 和提示词（写作、笔记问答等），其中 `aigc-workspace` 是整套 AI 短片前期的工作区配置
