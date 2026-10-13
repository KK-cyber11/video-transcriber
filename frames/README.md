# video-transcriber-frames：抖音 / 小红书 视频 → 中文逐字稿（画面字幕核对版）

把一条抖音或小红书公开视频（或本地音视频文件）转成简体中文逐字稿，在自己电脑上本地转写，不上传到第三方。

## 适用系统
macOS（Apple 芯片或 Intel，用 CPU 跑）和常见 Linux。需要 Python 3.10+ 或 [uv](https://github.com/astral-sh/uv)，至少 3.5GB 可用磁盘（比轻量版多约 100MB 的 OCR 依赖）、建议 8GB 内存。

## 安装（一次）
```bash
cd video-transcriber-frames
sh scripts/setup.sh
```
没有 Python 的 Mac 可以先装 uv：`curl -LsSf https://astral.sh/uv/install.sh | sh`。

## 使用
```bash
scripts/v2md "https://v.douyin.com/xxxx/" --video
scripts/v2md "https://xhslink.com/o/xxxx"
scripts/v2md ~/Downloads/某视频.mp4 --title "标题" --author "作者"
```
选项：`--video`（同时保存视频，供看画面字幕核对）、`--out 目录`（默认 `./transcripts`，也可设环境变量 `V2MD_OUT`）、`--model tiny|base|small|medium`（默认 small）。

## macOS 安装步骤（Apple 芯片 / Intel 都可）
1. 解压 zip（双击即可），打开「终端」，`cd` 进入解压出的 `video-transcriber-frames` 文件夹。
2. 如果系统提示文件“来自互联网”或脚本无法执行，先去掉隔离标记：
   `xattr -dr com.apple.quarantine .`
3. 安装 uv（推荐，会自动准备 Python 3.12；macOS 自带的 python3 通常是 3.9，版本不够）：
   `curl -LsSf https://astral.sh/uv/install.sh | sh`，然后关掉终端重新打开。
   （或用 Homebrew：`brew install python@3.12`。）
4. `sh scripts/setup.sh`（会自动下载 Playwright 浏览器；macOS 不需要 apt，也不需要单独装 ffmpeg，脚本自带）。
5. 使用：`sh scripts/v2md "链接"`。用 `sh` 开头就不用管执行权限；也可以 `chmod +x scripts/v2md scripts/setup.sh` 后直接 `scripts/v2md "链接"`。
bash 和 zsh 都可以用。

## 校对
机器转写会有不少同音错字。输出是**一个** md 文件：头部信息、`## 校对版`、`## 修改记录`、`## 带时间戳原文`（机器原文，不改动）。配合 AI 助手使用时，`SKILL.md` 要求助手在同一文件里填好校对版和修改记录：修正错字、补标点分段，不确定处标 `【存疑：原文X】`。

**用画面字幕核对存疑**：转写时加 `--video` 会多存一份视频；再用 `scripts/ocr 视频.mp4 00:01:08 00:01:12` 抽几帧识别画面上的字幕（本地 OCR：RapidOCR，CPU 即可，Mac 也能用），助手据此解决存疑，修改记录理由写「画面字幕」。画面没有字幕时保持存疑。
不用 AI 助手时，可把原始稿交给任意 AI 并附上这段要求。
可选：把常见专有名词写进 `scripts/glossary.txt`，运行时加 `--glossary scripts/glossary.txt`，能少一些错字。

## 配合 AI 助手
把整个文件夹放进你的助手的 skills 目录（例如 Claude Code 的 `~/.claude/skills/`），助手会按 `SKILL.md` 自动调用。也可以直接告诉助手：「用 video-transcriber-frames 处理这个链接」。

## 须知
- **抖音**：脚本像普通未登录访客一样打开 douyin.com 拿到游客 cookie，再用移植的网页签名算法读取这条视频的信息，核对视频 ID 一致后只下载音轨。不登录、不用任何人的账号。抖音更新签名算法后可能失效；失败时脚本会报错停止，不会转写别的视频，此时请在 App 里保存视频再转写本地文件。2026-10-13 实测可用。
- 抖音、小红书公开页面没有可直接读取的字幕，统一用本地语音识别。
- 机器转写会有同音错字，引用前请看校对版并核对【存疑】处。
- 不支持微信视频号；不支持私密/付费/需登录内容。
- 不登录、不读取你的浏览器 cookie。仅供个人使用，请遵守平台协议与版权。
- 依赖：yt-dlp、faster-whisper、OpenCC、Playwright、imageio-ffmpeg（均为开源）。抖音签名代码（`scripts/dysign/`）来自 Evil0ctal/Douyin_TikTok_Download_API，Apache-2.0 许可，保留了原 LICENSE 和 NOTICE。思路参考了 MrCarlsama/mrcarlsama-social-transcriber-skill（MIT 许可，见 THIRD_PARTY_NOTICE），本工具代码为独立编写，MIT 许可（见 LICENSE）。
