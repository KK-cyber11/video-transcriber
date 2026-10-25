# video-transcriber：抖音 / 小红书视频 → 中文逐字稿

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.10%2B-blue) ![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

把一条抖音或小红书的公开视频链接（或本地视频文件）转成简体中文逐字稿，并由你的 AI 助手（Claude Code、Cursor 等支持 `SKILL.md` 的 Agent）自动校对。语音识别在你自己的电脑上本地运行。

## 简介

本仓库包含两个可独立使用的 Skill：

- **`lite/`（video-transcriber-lite）**：轻量版。只下载音轨，本地转写，由 AI 助手根据上下文校对；没把握的地方标【存疑】。
- **`frames/`（video-transcriber-frames）**：画面核对版。在轻量版基础上，额外下载视频画面，在【存疑】处抽帧做 OCR，读取视频里烧录的字幕来核对，准确度更高。

两个版本都输出**一个** Markdown 文件。

## 功能

- 支持抖音、小红书公开视频链接（包括 App「分享 → 复制链接」得到的短链），以及本地视频/音频文件
- 本地语音识别（faster-whisper，CPU 即可），自动转为简体中文
- 自动读取标题、作者、发布日期、时长、正文/描述；取不到的写「未知」，不编造
- 抖音链接会**核对视频 ID**，不一致就停止，绝不转写别的视频
- AI 助手按 `SKILL.md` 校对：修正同音错字、补标点分段，列出修改记录，原文保持不动
- frames 版：对【存疑】处抽帧 OCR 画面字幕（RapidOCR，本地 CPU 运行）
- 可选术语表（`scripts/glossary.txt`），帮助识别专有名词

## 两个版本对比

| | lite（轻量版） | frames（画面核对版） |
|---|---|---|
| 下载内容 | 只下载音轨 | 音轨 + 一份低清视频画面 |
| 校对方式 | AI 根据上下文校对 | AI 校对 + 在【存疑】时间点抽帧 OCR 画面字幕 |
| 没把握的地方 | 保留【存疑】，需要你自己对照视频 | 画面有字幕时直接解决；没有字幕仍保留【存疑】 |
| 速度 | 更快 | 更慢（多一步画面核对） |
| 额外依赖 | 无 | RapidOCR + ONNX Runtime（约 100MB） |
| 适合 | 快速拿到大意、视频没有字幕 | 要求准确、视频带烧录字幕（多数口播、知识类视频都有） |

## 支持平台

| 平台 | 支持情况 |
|---|---|
| 抖音（`douyin.com`、`v.douyin.com` 短链） | ✅ 公开视频 |
| 小红书（`xiaohongshu.com`、`xhslink.com` / `xhslink.cn` 短链） | ✅ 公开视频笔记；图文笔记只保存正文 |
| 本地视频/音频文件 | ✅ mp4、mov、m4a、mp3 等 |
| **微信视频号** | ⚠️ 默认不支持；可选配置元宝登录态下载器（见 [docs_sph.md](docs_sph.md)），或用下文替代方案 |
| 其他平台、私密/付费/需登录内容 | ❌ 不支持 |

系统：macOS（已在 Apple 芯片 Mac 上测试；Intel Mac 未测试，CPU 运行）、常见 Linux 发行版。

## 安装

先选一个版本，进入对应文件夹（下面以 `lite` 为例，用 frames 版就把 `lite` 换成 `frames`）。

### macOS

1. 下载本仓库（`git clone` 或 GitHub 页面 `Code → Download ZIP` 后解压），打开「终端」，进入文件夹：
   ```bash
   cd video-transcriber/lite
   ```
2. 如果系统提示文件“来自互联网”或脚本无法执行，去掉隔离标记：
   ```bash
   xattr -dr com.apple.quarantine .
   ```
3. 安装 [uv](https://github.com/astral-sh/uv)（推荐，会自动准备 Python 3.12；macOS 自带的 `python3` 通常是 3.9，版本不够）：
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   装好后关掉终端重新打开。也可以用 Homebrew：`brew install python@3.12`。
4. 一次性安装依赖（含无头浏览器，不需要单独装 ffmpeg）：
   ```bash
   sh scripts/setup.sh
   ```

### Linux

```bash
cd video-transcriber/lite
sh scripts/setup.sh
```
需要 Python 3.10+ 或 uv。若无头浏览器缺系统库，按提示用 `sudo` 运行
`scripts/.venv/bin/python -m playwright install-deps chromium`。

### 放进 AI 助手

把 `lite/`（或 `frames/`）整个文件夹复制到助手的 skills 目录，例如 Claude Code：
```bash
mkdir -p ~/.claude/skills && cp -R lite ~/.claude/skills/video-transcriber-lite
```
之后对助手说「用 video-transcriber-lite 处理这个链接：<链接>」即可。助手会按 `SKILL.md` 自动转写并校对。

## 使用

命令行直接用（不经过 AI 助手时，只会得到转写原文，校对部分需要 AI 填写）：

```bash
# lite
sh scripts/v2md "https://v.douyin.com/xxxxxxx/"
sh scripts/v2md "https://xhslink.com/o/xxxxxxx"
sh scripts/v2md ~/Downloads/某视频.mp4 --title "标题" --author "作者"

# frames：转写时加 --video，保存一份画面
sh scripts/v2md "https://v.douyin.com/xxxxxxx/" --video
# 对某个【存疑】时间段抽帧识别画面字幕
sh scripts/ocr ./transcripts/<名字>.mp4 00:01:08 00:01:12
```

常用选项：
- `--out 目录`：输出目录（默认 `./transcripts`，也可设环境变量 `V2MD_OUT`）
- `--model tiny|base|small|medium`：识别模型（默认 `small`；`medium` 更准但需要约 5GB 以上空闲内存）
- `--glossary scripts/glossary.txt`：术语提示

### 参考耗时（约 2 分钟的视频，在 Apple 芯片 Mac、macOS 15 上实测，AI 校对为估计；视机器和网络而定）

| 步骤 | 大约耗时 |
|---|---|
| 首次安装（`setup.sh`） | 约 1 分钟；第一次转写还会下载约 500MB 的识别模型（首次转写约 1.5 分钟） |
| 转写 | 约 30 秒 |
| 画面核对（仅 frames） | 每个【存疑】处约 20 秒（含助手查看结果） |
| AI 校对 | 约 1–2 分钟（估计，取决于你用的 AI 助手） |
| **合计** | **lite 约 1–2 分钟；frames 约 2–4 分钟** |

## 输出格式

每条视频生成**一个** Markdown 文件：`<日期>-<标题>.md`

```markdown
# <标题>

- 作者：…
- 来源：<链接>
- 发布日期：…
- 视频 ID：…（已核对）        ← 抖音
- 时长：…
- 正文/描述：…
- 转写：<时间>，faster-whisper small，机器转写，可能有错字
- 校对：AI 校对，已修正 N 处，存疑 M 处

## 校对版
（修正错字、补标点、分段后的全文；没把握处写成【存疑：原文“X”】）

## 修改记录
| 时间 | 原文 | 改为 | 理由 |
|---|---|---|---|
| 00:00:12 | …… | …… | 同音 / 上下文 / 画面字幕 |

## 带时间戳原文
[00:00:00] 机器转写原文（不改动，供核对）
[00:00:03] ……
```

## 微信视频号：替代方案

本工具**不支持视频号**：视频号内容只能在微信里打开，网页端拿不到。可以用微信里的官方 AI「元宝」提取逐字稿：

1. 在微信顶部搜索「元宝」，添加官方账号（标有 AI 标识的那个）。
2. 打开要提取的视频号视频，点 **转发 → 转发给朋友 → 选择「元宝」**。
3. 在和元宝的对话里发送：**提取完整逐字稿**。
4. 复制元宝返回的文字。

> 说明：以上步骤来自公开文章的介绍，不是本项目的功能，微信/元宝的行为可能随时变化。公开文章提到大约 **30 分钟以内**的视频效果较好，更长的视频可能只给出摘要。拿到文字后，可以交给你的 AI 助手按本项目 `SKILL.md` 的规则校对。

另一个办法：在微信里把视频保存到手机（作者允许下载时），再用本工具转写本地文件。

**进阶（需要登录元宝）**：借助第三方技能，用元宝登录态直接下载视频号视频，再交给 v2md 转写。步骤、Linux 改动和风险见 [docs_sph.md](docs_sph.md)。

## 注意事项 / 免责声明

- **抖音的实现方式**：脚本像普通未登录访客一样打开 douyin.com，获得游客身份（访客 cookie），再用移植自 [Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)（Apache-2.0）的网页请求签名算法读取该视频信息。
  - 抖音更新网页端后**可能随时失效**；失败时脚本会报错停止，**不会转写别的视频**。此时可在 App 里保存视频，再转写本地文件。
- **不登录、不读取浏览器 cookie、不使用任何人的账号**，只用普通访客自动获得的游客身份；不绕过访问控制，只处理公开内容。
- **仅供个人学习、做笔记使用**。请遵守各平台用户协议和著作权法，不要用于搬运、二次分发或商用。
- **机器转写会有同音错字**（如人名、品牌、术语）。AI 校对能修正大部分，但请以原视频为准，引用前核对【存疑】处。
- 视频中的数据、观点不等于事实，使用前请自行核实。
- 本项目按「现状」提供，不对可用性或因使用产生的任何后果负责。

## 致谢与许可证

- 本仓库代码以 **MIT** 许可发布，见 [LICENSE](./LICENSE)。
- 抖音请求签名代码（`*/scripts/dysign/`）来自 [Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API)，**Apache-2.0** 许可，原 LICENSE 与 NOTICE 见 `third_party/` 及 `*/scripts/dysign/`。
- 思路参考 [MrCarlsama/mrcarlsama-social-transcriber-skill](https://github.com/MrCarlsama/mrcarlsama-social-transcriber-skill)（MIT，见 `third_party/MrCarlsama-MIT.txt`），代码为独立编写。
- 依赖的开源项目：[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[yt-dlp](https://github.com/yt-dlp/yt-dlp)、[OpenCC](https://github.com/yichen0831/opencc-python)、[Playwright](https://github.com/microsoft/playwright-python)、[imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg)、[RapidOCR](https://github.com/RapidAI/RapidOCR)（frames 版）。

## FAQ

**Q：需要 API key 或付费吗？**
A：不需要。转写在本机运行；校对由你正在用的 AI 助手完成。

**Q：没有 GPU 能用吗？Mac 呢？**
A：能。默认用 CPU 运行，已在 Apple 芯片 Mac 上测试通过（Intel Mac 未测试），长视频会慢一些。

**Q：抖音链接报错“页面被跳转到了别处”或“接口返回空内容”？**
A：多半是抖音更新了网页端或临时风控。稍后重试；仍不行就在 App 里保存视频，用 `v2md 文件路径` 转写。

**Q：小红书链接打不开？**
A：请用 App 里「分享 → 复制链接」得到的新链接；浏览器地址栏复制的链接常缺少访问参数，旧链接也会过期。

**Q：能支持视频号吗？**
A：默认不能。可以按 [docs_sph.md](docs_sph.md) 配置元宝登录态下载器（需扫码登录，有失效和风控风险），或用上文「微信视频号：替代方案」。

**Q：【存疑】太多怎么办？**
A：用 frames 版（视频带字幕时效果明显）；或把常见专有名词写进 `scripts/glossary.txt`；或换用 `--model medium`。

**Q：能批量下载、抓取作者主页或评论吗？**
A：不能，也不打算支持。本项目一次只处理一条链接。

**Q：lite 和 frames 能同时安装吗？**
A：可以，它们是两个独立的 Skill，各自有自己的依赖环境。
