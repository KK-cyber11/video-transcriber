#!/usr/bin/env python3
"""v2md: 抖音/小红书公开视频链接 或 本地音视频文件 -> 简体中文 Markdown 逐字稿

只访问公开页面；不登录、不读取浏览器 cookie、不绕过任何访问限制。
思路参考 MrCarlsama/mrcarlsama-social-transcriber-skill（MIT），代码为独立编写。
"""
import argparse, datetime, json, os, re, subprocess, sys, tempfile, pathlib
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt_dlp, opencc
KEEP_VIDEO = False
OUT = pathlib.Path(os.environ.get("V2MD_OUT", "./transcripts")); CC = opencc.OpenCC("t2s")
U = "未知"

def visitor_cookies(url, path):
    # 匿名、全新浏览器访问公开页面，仅取访客 cookie；不读取任何用户登录态
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True); c = b.new_context()
        pg = c.new_page(); pg.goto(url, wait_until="domcontentloaded", timeout=30000); pg.wait_for_timeout(4000)
        with open(path, "w") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for k in c.cookies():
                f.write("\t".join([k["domain"], "TRUE" if k["domain"].startswith(".") else "FALSE", k["path"],
                    "TRUE" if k["secure"] else "FALSE", str(int(k.get("expires") or 0) if (k.get("expires") or 0) > 0 else 0), k["name"], k["value"]]) + "\n")
        b.close()

def browser_grab(url, d):
    # 匿名无痕浏览器像普通访客一样播放公开视频，记录它请求的视频地址并用同一会话下载
    from playwright.sync_api import sync_playwright
    vids = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        c = b.new_context(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")
        pg = c.new_page()
        def on(r):
            ct = r.headers.get("content-type", "")
            if "douyinstatic.com/obj/douyin-pc-web" in r.url: return
            if ct.startswith(("video/", "audio/")) or re.search(r"\.mp4|douyinvod|xhscdn\.com/.*(stream|spectrum)|mime_type=video", r.url):
                if r.url not in vids: vids.append(r.url)
        pg.on("response", on)
        pg.goto(url, wait_until="domcontentloaded", timeout=45000)
        for _ in range(15):
            if vids: break
            pg.wait_for_timeout(1000)
        try: pg.evaluate("document.querySelector('video') && document.querySelector('video').play()")
        except Exception: pass
        pg.wait_for_timeout(3000)
        src = pg.evaluate("(()=>{const v=document.querySelector('video');return v?(v.currentSrc||v.src||''):''})()")
        if src and src.startswith("http") and src not in vids: vids.insert(0, src)
        def meta(n):
            try: return pg.evaluate(f"(document.querySelector('meta[property=\"{n}\"],meta[name=\"{n}\"]')||{{}}).content||''")
            except Exception: return ""
        title = meta("og:title") or pg.title() or U
        title = re.sub(r"\s*[-|]\s*(抖音|小红书.*)$", "", title).strip() or U
        author = U
        for sel in ['[data-e2e="user-info"] a span', '.author-wrapper .username', '.author .name', '.username']:
            try:
                t = pg.locator(sel).first.inner_text(timeout=1500).strip()
                if t: author = t; break
            except Exception: pass
        # 校验：页面必须仍停留在所请求的视频上（抖音会把匿名访客跳转到「精选」推荐流，那时播放的是别的视频）
        want = re.search(r"/video/(\d+)", url) or re.search(r"modal_id=(\d+)", url)
        here = pg.url
        got = re.search(r"/video/(\d+)", here) or re.search(r"modal_id=(\d+)", here)
        if (want and (not got or got.group(1) != want.group(1))) or (not want and not got):
            b.close(); sys.exit(f"页面被跳转到了别处（{here[:80]}），播放的不是你要的视频，已停止，避免转写错视频。可稍后重试，或在 App 里保存视频后转写本地文件。")
        if not vids: b.close(); sys.exit("浏览器打开页面后没有发现可播放的视频流（可能需要登录或不是视频）。")
        f = f"{d}/video.mp4"; ok = False
        vids.sort(key=lambda v: 0 if "audio" in v else 1)  # 分离式音轨优先（转写只需要声音）
        for v in vids:
            try:
                r = c.request.get(re.sub(r"[&?]range=[^&]*", "", v), headers={"Referer": url}, timeout=300000)
                if r.ok and len(r.body()) > 50000:
                    open(f, "wb").write(r.body()); ok = True; break
            except Exception: pass
        b.close()
    if not ok: sys.exit("抓到了视频地址但下载失败。")
    return f, {"title": title, "author": author, "url": url, "date": U}

MUA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

def xhs(url, d):
    # 以手机浏览器身份打开公开分享页，读取页面自带的笔记数据（不登录、不用 cookie）
    import urllib.request
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": MUA}), timeout=30)
    html = r.read().decode("utf-8", "ignore"); final = r.geturl()
    m = re.search(r"window.__INITIAL_STATE__=(.*?)</script>", html, re.S)
    if not m: return None
    st = json.loads(re.sub(r"\bundefined\b", "null", m.group(1)))
    nid = re.search(r"/(?:item|explore)/([0-9a-f]{24})", final)
    def find(o):
        if isinstance(o, dict):
            if "noteId" in o and ("title" in o or "desc" in o) and "user" in o and (not nid or o.get("noteId") == nid.group(1)): return o
            for v in o.values():
                x = find(v)
                if x: return x
        elif isinstance(o, list):
            for v in o:
                x = find(v)
                if x: return x
    n = find(st)
    if not n: return None
    t = n.get("time"); date = datetime.datetime.fromtimestamp(t/1000).strftime("%Y-%m-%d") if t else U
    meta = {"title": n.get("title") or U, "author": (n.get("user") or {}).get("nickname") or (n.get("user") or {}).get("nickName") or U,
            "url": url, "date": date, "desc": n.get("desc") or "", "type": n.get("type")}
    if n.get("type") != "video": return None, meta
    vurl = None
    for codec in ("h264", "h265", "av1"):
        for sm in (((n.get("video") or {}).get("media") or {}).get("stream") or {}).get(codec) or []:
            if sm.get("masterUrl"): vurl = sm["masterUrl"]; break
        if vurl: break
    if not vurl: return None, meta
    f = f"{d}/video.mp4"
    vurl = re.sub(r"^http://", "https://", vurl)
    req = urllib.request.Request(vurl, headers={"User-Agent": MUA, "Referer": "https://www.xiaohongshu.com/"})
    open(f, "wb").write(urllib.request.urlopen(req, timeout=300).read())
    return f, meta

def douyin_id(url):
    m = re.search(r"(?:/video/|/note/|modal_id=)(\d{15,})", url)
    if m: return m.group(1)
    # 短链（v.douyin.com）：只跟随跳转，读出视频 ID
    r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": MUA}), timeout=30)
    m = re.search(r"/(?:video|note)/(\d{15,})", r.geturl())
    return m.group(1) if m else None

def douyin(url, d):
    import douyin_api
    vid = douyin_id(url)
    if not vid: raise RuntimeError("无法从链接里读出抖音视频 ID")
    info = douyin_api.detail(vid)
    if str(info.get("aweme_id")) != vid:  # 关键校验：绝不转写别的视频
        raise RuntimeError(f"接口返回的视频 ID {info.get('aweme_id')} 与请求的 {vid} 不一致，已停止")
    f = f"{d}/douyin_media"
    for u in douyin_api.media_urls(info):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": douyin_api.UA, "Referer": "https://www.douyin.com/"})
            with urllib.request.urlopen(req, timeout=600) as r, open(f, "wb") as out:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    out.write(chunk)
            ok = subprocess.run([ffmpeg_bin(), "-v", "error", "-i", f, "-map", "0:a:0", "-t", "1", "-f", "null", "-"], capture_output=True).returncode == 0
            if ok: break
        except Exception as e:
            print(f"[v2md] 抖音媒体地址下载失败：{e}", file=sys.stderr)
    else:
        raise RuntimeError("拿到了视频信息，但所有媒体地址都下载失败或没有声音")
    if KEEP_VIDEO:
        # 画面用：选体积最小的视频流（可以没有声音）
        brs = sorted((b for b in (info.get("video") or {}).get("bit_rate") or [] if (b.get("play_addr") or {}).get("url_list")),
                     key=lambda b: (b.get("play_addr") or {}).get("data_size") or 9e12)
        for vu in [u for b in brs[:3] for u in b["play_addr"]["url_list"]]:
            try:
                req = urllib.request.Request(vu, headers={"User-Agent": douyin_api.UA, "Referer": "https://www.douyin.com/"})
                with urllib.request.urlopen(req, timeout=600) as r, open(f"{d}/frames.mp4", "wb") as out:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk: break
                        out.write(chunk)
                if os.path.getsize(f"{d}/frames.mp4") > 100000: break
            except Exception as e:
                print(f"[v2md] 一个画面地址下载失败（继续尝试下一个）：{str(e)[:80]}", file=sys.stderr)
    t = info.get("create_time")
    a = info.get("author") or {}
    desc = info.get("desc") or ""
    first = desc.split("#")[0].strip().splitlines()[0].strip() if desc.split("#")[0].strip() else ""
    head = first.split()[0] if first.split() and len(first.split()[0]) >= 8 else first  # 抖音描述常为「标题 + 空格 + 正文」
    return f, {"title": head[:60] or U, "author": a.get("nickname") or U, "url": url,
               "date": datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d") if t else U,
               "desc": info.get("desc") or "", "id": vid}

def sph(url, d):
    """视频号：调用外部下载器（见 docs_sph.md，需要元宝登录态）。未配置时提示保存本地文件。"""
    dl = os.environ.get("SPH_DOWNLOADER")
    if not dl or not os.path.isfile(dl):
        sys.exit("视频号需要额外配置下载器（见仓库 docs_sph.md）；或先在微信里保存视频，再把文件路径传给 v2md。")
    out = os.path.expanduser(os.environ.get("SPH_OUT", "~/videos/sph"))
    env = {**os.environ, "DISPLAY": os.environ.get("SPH_DISPLAY", os.environ.get("DISPLAY", ":0"))}
    r = subprocess.run([sys.executable, dl, "batch", url, "--browser", "chromium", "--output-dir", out],
                       capture_output=True, text=True, env=env)
    try: res = json.loads(r.stdout)
    except Exception: sys.exit(f"视频号下载失败：{r.stdout[-800:]}\n{r.stderr[-800:]}")
    items = res.get("results") or res.get("items") or []
    f = None; title = U; au = U
    for it in items if isinstance(items, list) else []:
        f = it.get("file_path") or f; au = it.get("author") or au
        title = it.get("title") or it.get("description") or title
    if not f or not os.path.isfile(f): sys.exit(f"视频号下载失败：{json.dumps(res, ensure_ascii=False)[:1500]}")
    return f, {"title": title, "author": au, "url": url, "date": U}


def download(url, d):
    if re.search(r"douyin\.com|iesdouyin\.com", url):
        try:
            return douyin(url, d)
        except Exception as e:
            print(f"[v2md] 抖音游客接口失败：{e}；改用其他方式…", file=sys.stderr)
    if re.search(r"xhslink\.(com|cn)|xiaohongshu\.com", url):
        try:
            res = xhs(url, d)
            if res: return res
        except Exception as e:
            print(f"[v2md] 小红书页面解析失败：{e}", file=sys.stderr)
    if "weixin.qq.com" in url or "channels.weixin" in url:
        return sph(url, d)
    opts = {"outtmpl": f"{d}/%(id)s.%(ext)s", "quiet": True, "no_warnings": True, "format": "best[ext=mp4]/best"}
    try:
        info = yt_dlp.YoutubeDL(opts).extract_info(url, download=True)
    except Exception as e:
        print(f"[v2md] 直接下载失败：{str(e)[:200]}；尝试匿名访客 cookie 重试…", file=sys.stderr)
        ck = f"{d}/cookies.txt"; visitor_cookies(url, ck)
        try:
            info = yt_dlp.YoutubeDL({**opts, "cookiefile": ck}).extract_info(url, download=True)
        except Exception as e2:
            print(f"[v2md] 访客 cookie 仍失败：{str(e2)[:150]}；改用匿名浏览器打开公开页面抓取播放流…", file=sys.stderr)
            return browser_grab(url, d)
    f = yt_dlp.YoutubeDL(opts).prepare_filename(info)
    return f, {"title": info.get("title") or U, "author": info.get("uploader") or info.get("creator") or info.get("channel") or U,
               "url": url, "date": (lambda s: f"{s[:4]}-{s[4:6]}-{s[6:]}" if s else U)(info.get("upload_date"))}

def ffmpeg_bin():
    import shutil
    if shutil.which("ffmpeg"): return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def zhpunct(t):
    # 中文句子里的半角标点统一为全角
    for a, b in ((",", "，"), ("?", "？"), ("!", "！"), (";", "；"), (":", "：")):
        t = re.sub(rf"(?<=[\u4e00-\u9fff]){re.escape(a)}|{re.escape(a)}(?=[\u4e00-\u9fff])", b, t)
    return re.sub(r"(?<=[\u4e00-\u9fff])\.(?!\d)", "。", t)

def ts(s): s=int(s); return f"{s//3600:02d}:{s%3600//60:02d}:{s%60:02d}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("--model", default="small")
    ap.add_argument("--title"); ap.add_argument("--author"); ap.add_argument("--url")
    ap.add_argument("--video", action="store_true", help="同时保存一份视频文件到输出目录（供 frames_ocr.py 看画面字幕核对【存疑】）")
    ap.add_argument("--glossary", help="术语表文件（每行一个词，# 开头为注释），作为提示词帮助识别专有名词")
    ap.add_argument("--out", help="输出目录（默认 ./transcripts，或环境变量 V2MD_OUT）"); a = ap.parse_args()
    global OUT, KEEP_VIDEO
    KEEP_VIDEO = a.video
    if a.out: OUT = pathlib.Path(a.out)
    d = tempfile.mkdtemp(prefix="v2md-")
    if os.path.exists(a.src):
        f = a.src; meta = {"title": pathlib.Path(f).stem, "author": U, "url": U, "date": U}
    else:
        f, meta = download(a.src, d)
        if f is None:  # 图文笔记：保存正文
            title = CC.convert(meta["title"]); safe = re.sub(r'[\\/:*?"<>|\s#]+', "_", title)[:40].strip("_") or "untitled"
            out = OUT / f"{datetime.date.today()}-{safe}.md"; OUT.mkdir(parents=True, exist_ok=True)
            out.write_text(f"# {title}\n\n- 类型：图文笔记（无视频）\n- 作者：{meta['author']}\n- 来源：{meta['url']}\n- 发布日期：{meta['date']}\n\n## 正文\n\n{meta.get('desc') or '未知'}\n")
            print(out); return
    for k in ("title", "author", "url"):
        if getattr(a, k): meta[k] = getattr(a, k)
    wav = f"{d}/a.wav"
    subprocess.run([ffmpeg_bin(), "-y", "-loglevel", "error", "-i", f, "-ac", "1", "-ar", "16000", wav], check=True)
    from faster_whisper import WhisperModel
    prompt = "以下是普通话的句子，使用简体中文。"
    if a.glossary:
        words = [w.strip() for w in open(a.glossary, encoding="utf-8") if w.strip() and not w.strip().startswith("#")]
        if words: prompt += "可能出现的词：" + "、".join(words)[:150] + "。"
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
    import wave, numpy as np
    with wave.open(wav) as w: audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    segs, info = m.transcribe(audio, language="zh", vad_filter=True, initial_prompt=prompt)
    segs = [(s.start, s.end, zhpunct(CC.convert(s.text.strip()))) for s in segs if s.text.strip()]
    title = CC.convert(meta["title"]); safe = re.sub(r'[\\/:*?"<>|\s#]+', "_", title)[:40].strip("_") or "untitled"
    out = OUT / f"{datetime.date.today()}-{safe}.md"; OUT.mkdir(parents=True, exist_ok=True)
    desc1 = " ".join(CC.convert(meta.get("desc") or "").split())
    md = [f"# {title}", "", f"- 作者：{CC.convert(meta['author'])}", f"- 来源：{meta['url']}", f"- 发布日期：{meta['date']}"]
    if meta.get("id"): md.append(f"- 视频 ID：{meta['id']}（已核对）")
    md.append(f"- 时长：{ts(info.duration)}")
    if desc1: md.append(f"- 正文/描述：{desc1}")
    md += [f"- 转写：{datetime.datetime.now():%Y-%m-%d %H:%M}，faster-whisper {a.model}，机器转写，可能有错字",
           "- 校对：未校对", "",
           "## 校对版", "", "（待 AI 助手按 SKILL.md 校对后填写）", "",
           "## 修改记录", "", "| 时间 | 原文 | 改为 | 理由 |", "|---|---|---|---|", "",
           "## 带时间戳原文", "", "> 机器转写原文，保持不动，供核对。", ""] + [f"[{ts(s)}] {t}" for s, e, t in segs] + [""]
    vf = os.path.join(os.path.dirname(f), "frames.mp4")
    if KEEP_VIDEO:
        import shutil
        dst = out.with_suffix(".mp4")
        if os.path.exists(vf): shutil.copy(vf, dst)
        elif not f.endswith(".wav") and os.path.exists(f) and os.path.abspath(f) != os.path.abspath(str(dst)): shutil.copy(f, dst)
        if dst.exists(): md.insert(md.index("- 校对：未校对") + 1, f"- 画面文件：{dst.name}（用于 frames_ocr.py 核对字幕）")
    out.write_text("\n".join(md)); print(out)
if __name__ == "__main__":
    main()
