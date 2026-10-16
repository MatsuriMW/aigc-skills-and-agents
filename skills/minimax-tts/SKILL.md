---
name: minimax-tts
description: 用 MiniMax 语音合成（默认 speech-2.8-hd）给视频配音：把口播稿、旁白、解说词、角色台词念成音频。能念一句，也能把整篇稿子按段配好、接成一条完整音轨、出对得上的 SRT 字幕和每段的时长表（给剪辑和 Remotion 对时间用）；改稿后只重新合成改过的段。还能查音色、复刻用户自己的声音、算一篇稿子要花多少钱。用户说「配音」「旁白」「念出来」「TTS」「语音合成」「给这条视频配个音」「用我的声音念」「MiniMax 配音」「speech-2.8」「出一条人声轨」「配音加字幕」时使用。只是要背景音乐或音效的不用这个（音效用 eagle-sfx）。
license: CC-BY-NC-SA-4.0
---

# MiniMax 配音

脚本是本 skill 的 `scripts/minimax_tts.py`，只用 Python 标准库；接整条音轨时要 ffmpeg。默认模型 `speech-2.8-hd`，接口是 MiniMax 开放平台的同步语音合成（`POST https://api.minimax.cn/v1/t2a_v2`）。

## 第一次用

1. **密钥**：在 platform.minimaxi.com → 账户管理 → 接口密钥 里建一个，然后用户自己在终端里跑（会提示粘贴，不进命令历史）：

   ```bash
   security add-generic-password -a "$USER" -s minimax-api-key -w
   ```

   密钥由用户自己录，Agent 不经手。脚本先看环境变量 `MINIMAX_API_KEY`，没有再读钥匙串。国际站（minimax.io）的密钥要把地址改掉：`minimax_tts.py default --host https://api.minimax.io`。

2. **选一个音色，记成默认**：

   ```bash
   python3 scripts/minimax_tts.py voices 男 青年        # 关键词都要命中，在 voice_id、名字、描述里找
   python3 scripts/minimax_tts.py say "大家好，今天聊一件事。" --voice <voice_id> -o 试听.mp3
   python3 scripts/minimax_tts.py default --voice <voice_id>
   ```

   没设默认音色又没写 `--voice` 时脚本会停下来提醒。挑音色时拿稿子里最有情绪的那两句试，别拿「大家好」试。

## 给一篇稿子配音

```bash
python3 scripts/minimax_tts.py cost 稿子.md --only 口播文案          # 先看怎么分段、要花多少钱，不合成
python3 scripts/minimax_tts.py script 稿子.md --only 口播文案 --join --srt -o 配音/
```

- **怎么分段**：空行分段；`#` 标题不念，当它后面那几段的名字；`>` 引用、表格、代码块、分隔线、笔记属性跳过；列表符号、加粗、链接地址、双链方括号、`#标签` 自动去掉；`【画面：…】` 这类方括号标注默认不念（要念加 `--keep-brackets`）。
- **`--only 词`**：只念标题里带这个词的章节。口播稿里常带备选标题、封面说明、创作备注，不筛就会被一起念出来，先 `cost` 看一眼分段再合成。
- **产出**：`01-段名.mp3`、`02-…`，每段一个文件；`manifest.json` 里有每段的字、时长、在整条音轨上的起点（`start`）；加 `--join` 多一条 `全片.mp3`，段间垫 0.35 秒静音（`--gap` 改）；加 `--srt` 每段一份字幕，和 `--join` 一起用时再出一份对齐整条音轨的 `全片.srt`。
- **改稿后重跑同一条命令**：字和参数都没变的段沿用上次的文件，不重新合成，只花改动那几段的钱。稿子里删掉的段，旧文件会被清掉。要全部重来加 `--force`。
- 剪辑、Remotion、ChatCut 对时间用 `manifest.json` 的 `start` 和 `duration`，不要自己估语速。

## 让它念得像人

speech-2.8 会按上下文自己定情绪和语调，所以**先别设 `--emotion`**，把力气花在稿子上：

- **停顿**：`<#0.6#>` 是停 0.6 秒（0.01–99.99）。放在两段能念的字中间，不能连着写两个。转折前、抛问题后、数字前各停一下，比调语速管用。
- **语气词**（只有 2.8 系列支持）：`(laughs)` `(chuckle)` `(sighs)` `(breath)` `(inhale)` `(exhale)` `(gasps)` `(emm)` `(coughs)` `(clear-throat)` `(sniffs)` `(pant)` `(groans)` `(humming)` `(lip-smacking)` `(snorts)` `(hissing)` `(sneezes)` `(burps)`。口播里常用的就前八个，一条片子用两三处，多了假。
- **多音字和专有名词**：在字后面用英文括号写拼音加声调，比如 `重(chong2)新`、`行(hang2)情`；英文缩写想按字母念就写开（`A I`）。
- **数字**：`12%`、`4600 美元`、日期一般念得对；一串编号、版本号这种，直接写成想听到的汉字。
- **语速**：口播 `--speed 1.05` 到 `1.15`；旁白、情绪片 `0.9` 到 `1.0`。先用默认的 1.0 听一遍再调。
- 真要压情绪时才用 `--emotion`：`happy` `sad` `angry` `fearful` `disgusted` `surprised` `calm` `fluent`。整篇只设一种会很平，按段分别合成更好（把那几段单独存一个文件跑，或用 `say`）。

## 用自己的声音

```bash
python3 scripts/minimax_tts.py clone 我的录音.m4a --voice-id MyVoice01 --preview "这是复刻出来的声音，听听像不像。"
python3 scripts/minimax_tts.py default --voice MyVoice01
```

- 录音要 10 秒到 5 分钟、20 MB 以内、mp3 / m4a / wav。安静的房间、离麦一拳、用平时讲口播的状态连着说一两分钟，比念稿子的腔调好；环境吵加 `--denoise`。
- 账号要先做实名认证才有复刻权限。
- 复刻本身不立刻收费，**第一次用这个音色正式合成时收 9.9 元**；复刻完 7 天内不正式用一次，平台会把它删掉。
- 只复刻用户本人或者明确授权了的声音。

## 钱

按量计费（2026-10 官网价）：`speech-2.8-hd` 3.5 元 / 万字符，`speech-2.8-turbo` 2 元 / 万字符；**一个汉字算 2 个字符**，字母、标点、空格各算 1 个。一千字的中文稿大约 0.7 元。脚本每次都会报这次计了多少字符。草稿阶段反复试可以先 `--model speech-2.8-turbo`，定稿再用 hd 跑一遍。

## 出了问题

| 报错 | 原因 |
|---|---|
| 没找到密钥 | 还没往钥匙串里录，见「第一次用」 |
| 1004 / 2049 | 密钥不对；或者是国际站的密钥，要改 `--host` |
| 1008 | 余额不足，去控制台充值 |
| 2013 | 参数不对，多半是 `voice_id` 写错了，用 `voices` 查 |
| 2038 | 没有复刻权限，先实名认证 |
| 1002 / 1039 | 限流，脚本会自己等一等再试 |

## 还没实测过的地方

脚本写完时本机还没有 MiniMax 密钥，下面几处是照官方接口文档写的，第一次用的时候留意：字幕文件（`subtitle_file`）的内部结构是按「带 `time_begin` / `time_end` / `text` 的条目」认的；复刻走的是「上传文件 → `voice_clone`」两步。分段、计费估算、音轨拼接、字幕时间换算是在本机测过的。实测通过后把这一节删掉。
