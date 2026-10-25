# 微信视频号下载（可选，需要登录元宝）

> 本方法**不是**本项目自带的功能，依赖第三方技能「视频号内容下载神器（本地下载）【波哥BOBBY-出品】」（作者：廖文波），
> 技能页：https://www.skillhub.cn/skills/user_2112d5ea/bobby-wechat-channels-downloader 。
> 该技能**未声明许可证**，所以本仓库**不包含它的任何源码**，只记录用法和我们在 Linux 上做的改动说明。请自行从技能页获取原技能。

## 原理
1. 用 Playwright 打开一个**专用的持久化浏览器配置**（与日常浏览器隔离），登录腾讯元宝 `yuanbao.tencent.com`（首次用微信或 QQ 扫码一次，之后复用登录状态）。
2. 把视频号分享链接交给元宝的解析接口，拿到视频的 feed 信息。
3. 再调用 `channels.weixin.qq.com` 的 finder-preview `get_feed_info` 取视频地址，下载 **mp4 + 封面 + json 元数据**。
4. 不装证书、不改系统代理、不动微信客户端。

只支持 `https://weixin.qq.com/sph/...` 形式的分享链接（微信里「分享 → 复制链接」得到的）。

## Linux 上的改动（原技能只在 Windows 上找浏览器）
在本地副本的 `scripts/wx_channels.py` 里做了以下修改（只描述，不附源码）：
- `--browser` 增加 `chromium` 选项；Linux 上默认用 `chromium`。
- 浏览器路径按顺序查找 `/usr/bin/google-chrome` → `/usr/bin/chromium` → `/usr/bin/chromium-browser`（`chrome` 选项查 `/usr/bin/google-chrome`、`/opt/google/chrome/chrome`）。
- 专用配置目录：`~/.sphdownload/wx_channels/profiles/chromium`。
- `batch` 支持 `--output-dir` 指定输出目录。
- 需要图形界面：必须设置 `DISPLAY`（有桌面或 Xvfb/VNC）。`--headless` 未测试。

## 用法
```bash
# 一次性登录：会弹出元宝页面，用微信或 QQ 扫码
DISPLAY=:0 python3 <原技能目录>/scripts/wx_channels.py login --browser chromium

# 下载（可一次传多个链接，整批只登录一次）
DISPLAY=:0 python3 <原技能目录>/scripts/wx_channels.py batch "https://weixin.qq.com/sph/XXXX" \
  --browser chromium --output-dir ~/videos/sph
```
输出为 JSON，`results[].file_path` 是下载好的 mp4。

## 和 v2md 配合
设置环境变量 `SPH_DOWNLOADER` 指向（已改好的）`wx_channels.py`，v2md 遇到视频号链接时会自动调用它下载，再照常转写：
```bash
export SPH_DOWNLOADER=<原技能目录>/scripts/wx_channels.py
export SPH_DISPLAY=:0             # 可选，默认用当前 DISPLAY
export SPH_OUT=~/videos/sph       # 可选，下载目录
scripts/v2md "https://weixin.qq.com/sph/XXXX"
```
没设置 `SPH_DOWNLOADER` 时，v2md 仍和以前一样提示「请先在微信里保存视频」。

## 风险与限制
- 用的是元宝**未公开的内部接口**，属于灰色用法；腾讯一改接口就会失效。
- 账号是否会被风控**未知**（没有查到相关说明），建议用不重要的账号。
- 部分发布者关闭了微信外解析，这类视频下不了。
- 元数据里的作者字段可能为空：校对时可根据视频里的自称、画面信息推断，但必须在 md 头部**注明是推断**。
- 仅供个人学习做笔记，请遵守微信/元宝用户协议和版权。
