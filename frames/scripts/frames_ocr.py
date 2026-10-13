#!/usr/bin/env python3
"""从视频的一段时间里抽几帧，识别画面上的文字（烧录字幕等），用来核对【存疑】处。

用法：frames_ocr.py <视频文件> <开始> <结束> [--n 6] [--bottom 0.45]
  时间可写秒数（12.5）或 时:分:秒（00:01:08）。
输出：每帧的时间和识别到的文字（字幕区优先），以及汇总去重后的文字行。
只在本机运行（RapidOCR + ONNX Runtime，CPU 即可）。
"""
import argparse, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2md import ffmpeg_bin, CC

def sec(t):
    if ":" in t:
        p = [float(x) for x in t.split(":")]
        while len(p) < 3: p.insert(0, 0)
        return p[0] * 3600 + p[1] * 60 + p[2]
    return float(t)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("start"); ap.add_argument("end")
    ap.add_argument("--n", type=int, default=6, help="抽帧数量（默认 6）")
    ap.add_argument("--bottom", type=float, default=0.45, help="字幕区：画面下方多大比例（默认 0.45；0 表示整幅画面都算字幕区）")
    a = ap.parse_args()
    s, e = sec(a.start), sec(a.end)
    if e <= s: e = s + 2
    from rapidocr_onnxruntime import RapidOCR
    ocr = RapidOCR()
    d = tempfile.mkdtemp(prefix="ocr-")
    seen, lines = set(), []
    for i in range(a.n):
        t = s + (e - s) * (i + 0.5) / a.n
        img = f"{d}/f{i}.jpg"
        subprocess.run([ffmpeg_bin(), "-v", "error", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1", "-q:v", "2", "-y", img], check=True)
        res, _ = ocr(img)
        if not res: print(f"[{t:7.2f}s] （无文字）"); continue
        import struct
        with open(img, "rb") as fh: data = fh.read()
        # 读图片高度（JPEG SOF 段），用于判断文字是否在字幕区
        h = None
        for m in re.finditer(rb"\xff[\xc0\xc2]", data):
            h = struct.unpack(">H", data[m.end() + 3:m.end() + 5])[0]; break
        sub, other = [], []
        for box, text, conf in res:
            if conf < 0.6: continue
            y = sum(p[1] for p in box) / 4
            text = CC.convert(text.strip())
            (sub if (not h or a.bottom == 0 or y > h * (1 - a.bottom)) else other).append(text)
        print(f"[{t:7.2f}s] 字幕区：{' / '.join(sub) or '（无）'}" + (f"    其他文字：{' / '.join(other)}" if other else ""))
        for x in sub:
            if x not in seen: seen.add(x); lines.append(x)
    print("\n汇总（字幕区，去重）：")
    for x in lines: print(" ", x)
    if not lines: print("  （没有识别到字幕；保持【存疑】）")

if __name__ == "__main__":
    main()
