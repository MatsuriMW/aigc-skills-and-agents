# 许可 / License

Copyright © 2026 马自立（MatsuriMW）· https://github.com/MatsuriMW

这个 skill 里作者自己写的全部文件（SKILL.md、references、templates、examples、evals、scripts 等）按**知识共享 署名-非商业性使用-相同方式共享 4.0 国际**（CC BY-NC-SA 4.0）发布。

- **署名**：转载、改编、二次分发，都要写明原作者「马自立（MatsuriMW）」和出处链接，并说明改了哪里。
- **非商业性使用**：不能拿这个 skill 本身去卖，包括付费下载、打包进付费课程或资料包、在付费的 skill / 提示词市场转售、当成付费服务的交付物。
- **相同方式共享**：改编后的版本只能用同一个协议发布，不能换成更宽的协议或闭源。

用这个 skill 做出来的东西（图片、视频、台词、文案、设计稿）归使用者自己，不受本协议限制。
skill 里收录的第三方内容（公有领域或 CC0 素材、上游项目的代码和提示词）按各自原来的许可，不在本协议内。
想商用、拿不准算不算商用，联系作者。

协议说明：https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans
协议全文：https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.zh-hans

---

This skill is licensed under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). You may share and adapt it for non-commercial purposes, with attribution to 马自立 (MatsuriMW), under the same license. Works you create with it are yours. Third-party materials keep their own licenses. For commercial licensing, contact the author.

---

## 第三方代码 / Third-party code

本机配音（VoxCPM2）的声音门禁、分段、句尾清理、对稿和参考清洗搬自 [sweety-handdraw-video](https://github.com/threerocks/sweety-handdraw-video) 2.0.2（提交 11429806bb），按它原来的 MIT 许可，不在上面的 CC BY-NC-SA 协议内：

- `scripts/audio_gate.py`：搬自原版 `scripts/audio_gate.py`，只留旁白门禁
- `scripts/align.py`：搬自原版 `scripts/align.py`，只留对稿、语音检测、字幕切分；Whisper 改为直接调用
- `scripts/clean_reference.py`：搬自原版 `scripts/clean_reference.py`，去掉人声分离，降噪改为直接调用
- `scripts/narration.py`：常量和 `pieces` 到 `generate_chunk` 搬自原版 `scripts/narration_master.py`；`chunks_of`、`tidy`、`render_segment`、`build` 是本 skill 写的

`scripts/voxcpm_tts.py`、`scripts/minimax_tts.py` 和 SKILL.md 是本 skill 自己写的，按上面的 CC BY-NC-SA 4.0。

The voice gate, chunking, edge cleaning, ASR coverage and reference cleaning of the local VoxCPM2 backend are adapted from sweety-handdraw-video 2.0.2 and stay under its MIT license:

```
MIT License

Copyright (c) 2026 threerocks

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
