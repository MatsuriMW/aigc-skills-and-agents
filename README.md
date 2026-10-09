# AIGC Skills & Agents

马自立自己写的（或改过的）AIGC skill 和 agent：给 AI 短片、AI 生图 / 生视频做前期设计用，都是给 [Claude Code](https://claude.com/claude-code) 用的。

> **角色设计 skill（juese-sheji）已经搬到独立仓库 [MatsuriMW/ai-character-design-skill](https://github.com/MatsuriMW/ai-character-design-skill)**（带安装脚本、README 和 claude.ai 用的 zip），这里不再保留副本。

生成一部短片时，最常见的问题是**同一个角色每个镜头长得不一样、穿得不一样**。整条链路是这样的：

```
剧本 / 节拍表 / 分镜
      │
      ▼
juese-sheji 角色设计（独立仓库 ai-character-design-skill）
      │  模糊感觉 → 名词和动作 → 服化道总表 + 锁定段；定下主造型（Look A）
      ▼
character-sheet 角色设定板（本仓库）── 三视图 + 表情 + 细节的设定板 prompt，锁定角色 ID
      │
      ▼
生图 / 生视频（GPT Image、Nano Banana、Seedance、Kling…）：每个镜头 = 角色锁定 + 本场造型 + 妆发 + 道具 + 镜头描述
```

## skills/

| skill | 干嘛的 | 什么时候触发 |
|---|---|---|
| [character-sheet](skills/character-sheet)（角色设定板） | 把参考图、角色描述或 juese-sheji 的人物精细描述做成锁定角色 ID 的设定板 prompt：4:3 横版，三视图、剪影、8 表情、5 微表情、头部结构、姿态、特写、服装细节、手部动作；先写一段逐项写实的「角色锁定段」，中英两版模板 | 「角色卡」「角色设定板」「character sheet」「三视图」「锁定角色一致性」 |

上游可以接 [juese-sheji](https://github.com/MatsuriMW/ai-character-design-skill) 和分镜 skill（比如 [DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)），下游接按模型写 prompt 的 skill（比如 [visual-skills](https://github.com/smixs/visual-skills)）。

## 安装

把 `skills/` 下的目录复制到 Claude Code 的 skill 目录：

- 只在某个工作区用：`<工作区>/.claude/skills/`（我的用法：放在一个专门做 AIGC 的目录里）
- 全局用：`~/.claude/skills/`

默认把产出存进工作区根目录下的 `character-sheets/<角色>/`（prompt.md、参考图、生成结果）。没有这个目录也能用，只是不存文件。

## agents/

还没放。之后会把整套 AIGC 工作区（工作区说明 + 各 skill 的分工）整理成 agent 放进来。

---

正本在本机 AIGC 工作区，这里是副本：改完跑 `./sync.sh "改了什么"` 同步、提交、推送。
