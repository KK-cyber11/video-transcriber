"""抖音：用匿名「游客身份」读取单条公开视频的详情（不登录、不用任何人的账号）。

做法与 Evil0ctal/Douyin_TikTok_Download_API v5 一致：
1. 用全新无痕浏览器打开 douyin.com 首页，拿到普通访客都会得到的游客 cookie（ttwid、s_v_web_id、UIFID_TEMP 等）；
2. 用移植的签名算法（a_bogus、x-secsdk-web-signature）对 /aweme/v1/web/aweme/detail/ 请求签名；
3. 返回该视频的元数据和音频地址。调用方必须校验返回的 aweme_id 与请求一致。
"""
import json, random, string, urllib.parse, urllib.request
from urllib.parse import quote, unquote
from dysign.abogus import ABogus, DEFAULT_BROWSER_INFO
from dysign import websign

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
DETAIL = "https://www.douyin.com/aweme/v1/web/aweme/detail/"
BASE = {"device_platform": "webapp", "aid": "6383", "channel": "channel_pc_web", "pc_client_type": "1",
        "version_code": "290100", "version_name": "29.1.0", "cookie_enabled": "true", "screen_width": "1920",
        "screen_height": "1080", "browser_language": "zh-CN", "browser_platform": "Win32", "browser_name": "Chrome",
        "browser_version": "130.0.0.0", "browser_online": "true", "engine_name": "Blink", "engine_version": "130.0.0.0",
        "os_name": "Windows", "os_version": "10", "cpu_core_num": "12", "device_memory": "8", "platform": "PC",
        "downlink": "10", "effective_type": "4g", "round_trip_time": "0", "update_version_code": "170400"}

def guest_cookies():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        c = b.new_context(user_agent=UA, viewport={"width": 1920, "height": 947}, locale="zh-CN")
        pg = c.new_page(); pg.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=45000)
        jar = {}
        for _ in range(20):
            pg.wait_for_timeout(1000)
            jar = {k["name"]: k["value"] for k in c.cookies() if "douyin.com" in k["domain"] and k["name"]}
            if jar.get("UIFID_TEMP") and jar.get("s_v_web_id") and jar.get("ttwid"): break
        b.close()
    return jar

def _sign(params, jar):
    params = dict(params)
    params["msToken"] = jar.get("msToken") or "".join(random.choices(string.ascii_letters + string.digits, k=126)) + "=="
    query = urllib.parse.urlencode(params)
    bogus = ABogus(UA, browser_info=DEFAULT_BROWSER_INFO).get_value(query, body="", content_type="")
    query = f"{query}&a_bogus={quote(bogus, safe='')}"
    uifid = websign.pick_uifid(jar)
    headers = {}
    if uifid:
        pairs = [(unquote(k), unquote(v)) for k, _, v in (x.partition("=") for x in query.split("&") if x)]
        vfp = jar.get(websign.VERIFY_FP_COOKIE)
        if vfp:
            pairs += [(n, vfp) for n in websign.VERIFY_FP_PARAMS]
        query, _sig, headers = websign.sign(pairs, uifid)
    return query, dict(headers)

def detail(aweme_id, jar=None):
    jar = jar or guest_cookies()
    q, h = _sign({**BASE, "aweme_id": str(aweme_id)}, jar)
    req = urllib.request.Request(DETAIL + "?" + q, headers={"User-Agent": UA, "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*", "Cookie": "; ".join(f"{k}={v}" for k, v in jar.items()), **h})
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    if not body.strip():
        raise RuntimeError("抖音接口返回空内容（签名或游客身份被拒，可稍后重试）")
    d = json.loads(body).get("aweme_detail")
    if not d:
        raise RuntimeError("抖音接口没有返回该视频（可能已删除、私密或需要登录）")
    return d

def media_urls(d):
    """优先纯音频（转写只需要声音、文件小），其次最小的带声音 mp4。"""
    v = d.get("video") or {}
    out = []
    for a in v.get("bit_rate_audio") or []:
        ul = (a.get("audio_meta") or {}).get("url_list") or {}
        out += [u for u in (ul.get("main_url"), ul.get("backup_url"), ul.get("fallback_url")) if u]
    for k in ("play_addr", "download_addr"):
        out += ((v.get(k) or {}).get("url_list") or [])
    return out
