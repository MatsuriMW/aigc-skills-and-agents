---
name: peiyin
description: 给视频配音：把口播稿、旁白、解说词、台词念成音频。默认用本机的 VoxCPM2（mlx-audio，Apple Silicon，不花钱，稿子不出电脑）：每段生成后过声音门禁（嗡声、底噪、削波、语速、Whisper 对稿），不过就换种子重来，整条拼好再过一次门禁；出每段音频、整条音轨、对得上的 SRT 字幕和每段时长表（给剪辑和 Remotion 对时间用），改稿后只重做改过的段。还能用一句话描述造一个声音，或者用自己的录音克隆声音（先降噪清洗，再试念过门禁才入库）。MiniMax 云端合成作为可选后端保留。用户说「配音」「旁白」「念出来」「TTS」「语音合成」「给这条视频配个音」「用我的声音念」「出一条人声轨」「配音加字幕」「造个声音」「声音克隆」「VoxCPM」「MiniMax 配音」时使用。已经有配音、要给配音配画面动效的用 video-talkcraft；只要背景音乐或音效的用 eagle-sfx。
license: CC-BY-NC-SA-4.0
---

# 配音

两个后端，默认用本机：

| | 本机 VoxCPM2（默认） | MiniMax（可选） |
|---|---|---|
| 脚本 | `scripts/voxcpm_tts.py`，在 `~/.venvs/voxcpm2` 里跑 | `scripts/minimax_tts.py`，系统自带的 python3 就行 |
| 钱 | 不花钱，只花电和时间 | 按量计费；国际站 API 要 25 美元起充 |
| 声音门禁 | 每块、整条、新声音入库都过 | 没有 |
| 声音 | 自己的声音库：声音设计造的，或自己录的 | 平台音色，或在平台复刻 |
| 弱项 | 中文里夹的英文词、数字读法不稳 | 要联网、要钱 |

下面的 `vox` 是 `~/.venvs/voxcpm2/bin/python scripts/voxcpm_tts.py` 的简写，在 skill 目录里跑。

## 本机 VoxCPM2

### 第一次用：环境

```bash
uv venv ~/.venvs/voxcpm2 --python 3.12
uv pip install --python ~/.venvs/voxcpm2/bin/python "mlx-audio==0.5.8" soundfile mlx-whisper pypinyin socksio sentencepiece
```

- mlx-audio 锁 0.5.8：VoxCPM2 在这一版上验证过，新版参数名可能变。`socksio` 是因为 shell 里有 `ALL_PROXY=socks5://…`，下载库走 SOCKS 要它；`sentencepiece` 是加载降噪模型时 mlx-audio 顺带要的。
- 模型第一次用时自动下：VoxCPM2-8bit 3.2 GB、Whisper large-v3-turbo 1.6 GB、降噪的 DeepFilterNet3 9 MB。脚本关掉了 Hugging Face 的 Xet 下载协议（走代理时它只有 0.4 MB/秒，关掉后 2–3 MB/秒），下好之后自动离线跑。
- 只能在 Apple Silicon 上跑。M3 Max 上大约 1 秒出 1 秒音频，短句慢一些；内存峰值约 8 GB。别开两个进程并行，反而更慢。

### 声音库：先有一个声音

声音库在 `~/.local/share/voxcpm-tts/voices/`，是个人数据，不进 skill。一个声音 = 一段参考录音 + 一字不差的逐字稿，之后每次都用「参考 + 逐字稿」高保真克隆，音色稳定。

`voice add` 入库前有两道检查，过不了就不收：

1. **查参考本身**：短片段门禁，长 5–30 秒，语速 2.5–8 字/秒（逐字稿要盖住整段），Whisper 逐字对上（同音字也不放过）。
2. **用它试念一段约 12 秒的话，按整条音轨的口径过门禁。** 实测过：一条参考自己能过门禁，克隆出来拼成整条却有 50 Hz 的嗡声。参考里听不出的底噪会在生成时放大，只查参考不够。

三个来源：

- **声音设计**（不涉及真人，最省事）：

  ```bash
  vox design "青年男声，音色清亮温和，吐字清晰，语速适中，适合科技产品讲解"
  ```

  出 4 个候选，每个都自动裁到句末、补尾部静音、峰值统一到 -3 dBFS、过门禁和对稿，再用它试念一段过门禁；只有打 ✓ 的能用，目录里有 `reference.wav` 和 `试念.wav` 可以听。听完挑一个：`vox voice add 讲解男声 --audio <候选目录>/reference.wav --consent designed`。描述写「身份 + 质感 + 场景」，只写声音特征，不写「像某某」。每次设计都像换了一个人，所以一定是挑一条锁成参考，之后都用克隆。
- **自己录**：在安静的地方（衣柜边就行），手机离嘴 20 厘米，用平时讲解的语气说 15 秒左右，句末收住后停一秒。然后清洗再入库：

  ```bash
  vox clean 录音.m4a --text "录音里说的每一个字，标点照录"     # 可加 --start 31.6 --end 46.0 只取一段
  vox voice add 我自己 --audio <clean 输出目录>/reference.wav --consent self
  ```

  `clean` 用 DeepFilterNet3 降噪，找真实的句子边界裁成 8–15 秒，尾部留 0.5 秒以上静音，再过门禁和逐字对稿；原文件不动。
- **别人的声音**：要有本人授权（`--consent authorized`）。不克隆明星、主播、平台音色，也不拿别家 TTS 的输出当参考。

`vox voice list` 看声音库（`*` 是默认的），`vox voice default 名字` 换默认。参考听着有杂音、或者入库被拒，先 `vox clean <参考> --text "逐字稿"` 降噪再加。

### 给一篇稿子配音

```bash
vox script 稿子.md --only 口播文案 --dry-run     # 先看分段和生成块，不生成
vox script 稿子.md --only 口播文案               # 可加 -o 配音/、--voice 名字
```

- **怎么分段**：和 MiniMax 一样。空行分段；`#` 标题不念，当它后面那几段的名字；引用、表格、代码块、分隔线、笔记属性跳过；`【画面：…】` 这类标注默认不念（`--keep-brackets` 才念）。MiniMax 专用的 `<#0.5#>` 和 `(laughs)` 会被去掉。`--only 词` 只念标题里带这个词的章节。
- **每段再切成生成块**：每块不超过约 100 字，只在句末切；单句太长才在逗号处切；不到 8 个字的并进相邻块。
- **每块的流程**：生成；裁掉开头的静音；找到真正的句尾，删掉说完后多出来的气声和杂音；句尾被截断的判失败。然后过门禁：
  - 嗡声或单频线
  - 停顿不够安静（要比说话低 25 dB 以上）
  - 削波、直流偏移
  - 语速 3–8 字/秒
  - Whisper 对稿：字错率不超过 15%，开头和结尾都要对上；汉字对不上时再按不带声调的拼音比一次，同音字放行

  不过就换下一个种子重来；3 个种子都不过就停下，报告是哪一句、什么原因。
- **拼接停顿**（实测值）：块之间逗号处 0.2 秒、句号处 0.3 秒；同一个标题下段与段之间 0.4 秒；换标题 0.6 秒。
- **整条拼好再过一次门禁**，不过就不出「全片」，各段文件和每段的门禁结果留在 `manifest.json` 里。每块只有几秒，凑不够判嗡声要的两个 2 秒窗，嗡声往往只在整条上才看得出来。
- **产出**：
  - 每段一个 `01-段名.wav` 和 `.srt`
  - `全片.wav` 和 `全片.srt`
  - `manifest.json`：每段的 `start`（在全片上的起点）、`duration`、字幕时间，每块用的种子、对稿结果和停顿深度，以及整条的门禁数值

  剪辑和 Remotion 用 `start` 和 `duration`，不要自己估语速。video-talkcraft 要的「一条配音 + 逐字稿」就是 `全片.wav` 加稿子。字幕时间来自 Whisper 的字级时间戳，对不上的地方按停顿切。
- **改稿后重跑同一条命令**：字、声音、种子都没变的块直接沿用，只生成改过的；稿子里删掉的段，旧文件一起清掉。`--force` 全部重来。
- 念一句：`vox say "这句话" -o 试听.wav`。挑声音时拿稿子里最有情绪的两句试，别拿「大家好」试。
- 单独测某个文件：`vox gate a.wav b.wav`（参考录音或单个短片段加 `--short-clip`）。

### 让它念得对：写稿时就处理

本机模型没有 MiniMax 的停顿标记和数字规范化：

- **停顿靠标点**：句号停得比逗号长；要更长就拆句，不要堆标点。
- **数字、年份、版本号写成想听到的汉字**：「2026 年」写「二零二六年」，「2.0.3」写「二点零点三」。对稿对数字不够严：「一百二十」念成「一百」字错率才 8%，会被放过。数字要靠人耳确认。
- **多音字**：能换说法就换；换不掉的，用读音唯一的同音字（「小将」写「小匠」），字幕里改回原文。
- **英文词**：能用中文说就用中文；必须保留的，生成后单独听。实测 Claude、WorkBuddy 这类词念不稳。
- **太短的句子**（「好的」）声音偏弱，和前后句写在一起。
- 门禁和对稿只抓明显的故障，交付前完整听一遍。

### 出了问题

| 现象 | 处理 |
|---|---|
| 下载很慢 | 脚本已关掉 Xet 协议；还慢就是网络本身，耐心等，或者从魔搭（modelscope.cn）的同名镜像下 |
| `Using SOCKS proxy, but the 'socksio' package is not installed` | 环境里补装 `socksio` |
| 某块 3 个种子都没过，原因是对稿 | 改写这句：避开多音字、英文、阿拉伯数字 |
| 某块或整条有嗡声、停顿不安静 | 声音的问题：`clean` 参考后重新 `voice add`，或者换个声音 |
| 参考入库被拒 | 看报的原因；底噪、杂音先 `clean`；逐字稿对不上就改逐字稿 |
| 「参考录音入库后被改过」 | 声音库里的文件被动过，重新 `voice add` |

## MiniMax（可选，云端）

`python3 scripts/minimax_tts.py …`，只用标准库，接整条音轨要 ffmpeg。默认模型 `speech-2.8-hd`，接口是 `POST https://api.minimax.cn/v1/t2a_v2`。

- **密钥**：在 platform.minimaxi.com → 账户管理 → 接口密钥 里建，用户自己在终端里录（不进命令历史，Agent 不经手）：`security add-generic-password -a "$USER" -s minimax-api-key -w`。脚本先看环境变量 `MINIMAX_API_KEY`，再读钥匙串。国际站（minimax.io）的密钥要 `minimax_tts.py default --host https://api.minimax.io`；国际站的 API 余额要单独充，25 美元起，充进订阅的钱 API 用不了。
- **音色**：`voices 男 青年` 查，`say "…" --voice <id> -o 试听.mp3` 试，`default --voice <id>` 记成默认。
- **整篇**：`cost 稿子.md --only 口播文案` 先看分段和价钱；`script 稿子.md --only 口播文案 --join --srt -o 配音/` 出每段 mp3、`manifest.json`、`全片.mp3`、`全片.srt`。分段规则和本机一样；改稿重跑只合成改过的段。
- **念得像人**：先别设 `--emotion`，让 2.8 按上下文定。停顿写 `<#0.6#>`（不能连写两个）；语气词 `(laughs)` `(chuckle)` `(sighs)` `(breath)` `(inhale)` `(exhale)` `(gasps)` `(emm)` 等，一条片子用两三处；多音字写 `重(chong2)新`；口播 `--speed 1.05`–`1.15`。
- **复刻自己的声音**：`clone 我的录音.m4a --voice-id MyVoice01 --preview "…"`。录音 10 秒到 5 分钟、20 MB 以内；要先实名认证；第一次正式合成收 9.9 元，7 天不用会被平台删掉。只复刻本人或授权的声音。
- **钱**：`speech-2.8-hd` 3.5 元 / 万字符，`turbo` 2 元 / 万字符（2026-10）；一个汉字算 2 个字符，一千字约 0.7 元。
- **报错**：1004 / 2049 密钥不对或是国际站的；1008 余额不足；2013 多半是 voice_id 写错；2038 没实名；1002 / 1039 限流会自动重试。
- **还没实测过**：本机还没用真密钥跑过。字幕文件的结构和复刻的两步是照官方文档写的；分段、计费估算、拼接、字幕时间换算在本机测过。

## 来源

本机后端的门禁、分段、句尾清理、对稿和参考清洗搬自 [sweety-handdraw-video](https://github.com/threerocks/sweety-handdraw-video) 2.0.2（MIT，threerocks），哪些文件、哪些函数见 `LICENSE.md`。参数和做法的依据是它的 `references/voxcpm2.md`、`continuous-narration.md`，以及作者的文章《妈妈都分不清的配音》。
