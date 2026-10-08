# AIGC Skills & Agents

马自立自己写的（或改过的）AIGC skill 和 agent：给 AI 短片、AI 生图 / 生视频做前期设计用。目前收了两个 skill，都是给 [Claude Code](https://claude.com/claude-code) 用的，角色设计另有一份 [ChatCut](https://chatcut.io) 版。

要解决的问题：用 AI 生成一部短片时，**同一个角色每个镜头都长得不一样、穿得不一样**，配角和道具也是随手生成、彼此对不上。这两个 skill 把「这个角色是谁、穿什么、拿什么、每场戏怎么变」先定下来，写成能直接拼进每条生图 / 生视频 prompt 的锁定段。

```
剧本 / 节拍表 / 分镜
      │
      ▼
juese-sheji 角色设计 ──── 人物原型 → 创意风暴 → 设计落地（服化道总表 + 锁定段）→ 检验
      │  主造型（Look A）
      ▼
character-sheet 角色设定板 ── 三视图 + 表情 + 细节的设定板 prompt，锁定角色 ID
      │
      ▼
生图 / 生视频（GPT Image、Nano Banana、Seedance、Kling…）：每个镜头 = 角色锁定 + 本场造型 + 妆发 + 道具 + 镜头描述
```

## skills/

| skill | 干嘛的 | 什么时候触发 |
|---|---|---|
| [juese-sheji](skills/juese-sheji)（角色设计，原名 fuhuadao「服化道」） | 从人物原型到服化道（服装 / 化妆发型 / 道具），四个模式：<br>**D 人物原型**：122 张影视经典人物原型卡（家庭、校园、职场、犯罪、底层、动作、奇幻科幻恐怖、爱情、东亚与短剧、喜剧配角，外加一份慎用清单），每张有服、妆发、道具、姿态、场与光、翻转和英文 prompt，按「原型 + 一处具体 + 一处反转」本土化成这个故事里的人<br>**B 创意风暴**：用反差、物件叙事、时间痕迹、色彩隐喻等方法发散 4–6 个真正不同的造型方向，再按「真、准、记得住」收敛推荐<br>**C 设计落地**：把剧本 / 分镜拆成造型卡（Look）、妆发状态卡、道具卡、场次 × 角色总表和连戏表，每套写成英文锁定段<br>**A 检验**：按时代与环境、身份与处境、性格与弧光、记忆点、可生成性五个维度打分，列问题和改法；时代考据不确定就联网查证 | 「角色设计」「人设」「给我一个 XX 那种人」「服化道」「这个角色穿什么」「有没有穿帮」「连戏」「道具清单」 |
| [character-sheet](skills/character-sheet)（角色设定板） | 把参考图或角色描述做成锁定角色 ID 的设定板 prompt：4:3 横版，三视图、剪影、8 表情、5 微表情、头部结构、姿态、特写、服装细节、手部动作；先写一段逐项写实的「角色锁定段」，中英两版模板 | 「角色卡」「角色设定板」「character sheet」「三视图」「锁定角色一致性」 |

两个 skill 配合用：`juese-sheji` 定下的主造型交给 `character-sheet` 出设定板；上游可以接分镜 skill（比如 [DirectorSKILL](https://github.com/wuwangzhang1216/DirectorSKILL)），下游接按模型写 prompt 的 skill（比如 [visual-skills](https://github.com/smixs/visual-skills)）。

## chatcut/

[juese-sheji](chatcut/juese-sheji) 的 ChatCut 版：去掉了本机目录约定，模板挪到 `references/templates/`，已上传到 ChatCut「我的技能」。内容和 Claude Code 版同步更新。

## 安装

把 `skills/` 下的目录复制到 Claude Code 的 skill 目录：

- 只在某个工作区用：`<工作区>/.claude/skills/`（我的用法：放在一个专门做 AIGC 的目录里）
- 全局用：`~/.claude/skills/`

两个 skill 默认按这样的工作区结构存产出（相对工作区根目录），没有这些目录也能用，只是不存文件：

```
shorts/<项目>/          短片项目：README、资料/、节拍表、分镜稿；角色设计的产出存在这里（人物原型-v1.md、服化道-v1.md …）
character-sheets/<角色>/  每个角色一个目录：prompt.md、参考图、生成结果
```

## agents/

还没放。之后会把整套 AIGC 工作区（工作区说明 + 各 skill 的分工）整理成 agent 放进来。

---

正本在本机 AIGC 工作区，这里是副本：改完跑 `./sync.sh "改了什么"` 同步、提交、推送。
