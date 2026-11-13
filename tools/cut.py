#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从整集源片切片段,并自动登记进素材索引 index/clips.csv。

用法示例:
  python tools/cut.py --ep 3 --start 00:12:30 --end 00:14:05 \
      --name "刘姥姥一进门前问门房" \
      --persons "刘姥姥" --scene "一进荣国府" \
      --quote "太爷们纳福" --tags "卑微,喜剧"
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))

CLIPS_HEADER = [
    "id", "ep", "start", "end", "duration_sec", "persons", "scene",
    "quote", "tags", "file", "created",
]


def parse_ts(ts: str) -> float:
    """接受 hh:mm:ss / hh:mm:ss.ms / 纯秒数,返回秒。"""
    ts = ts.strip()
    if re.fullmatch(r"\d+(\.\d+)?", ts):
        return float(ts)
    parts = ts.split(":")
    if not 2 <= len(parts) <= 3:
        sys.exit(f"时间格式不对: {ts} (应为 hh:mm:ss 或纯秒数)")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def sanitize(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name.strip())[:60]


def next_id(csv_path: Path) -> str:
    if not csv_path.exists():
        return "CL-0001"
    last = 0
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            m = re.match(r"CL-(\d+)", row.get("id", ""))
            if m:
                last = max(last, int(m.group(1)))
    return f"CL-{last + 1:04d}"


def append_row(csv_path: Path, row: dict) -> None:
    new_file = not csv_path.exists()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CLIPS_HEADER)
        if new_file:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    try:  # Windows 控制台中文输出
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="切集片段并登记素材索引")
    ap.add_argument("--ep", type=int, required=True, help="集数,如 3 表示 03.mkv")
    ap.add_argument("--start", required=True, help="开始时间 hh:mm:ss")
    ap.add_argument("--end", required=True, help="结束时间 hh:mm:ss")
    ap.add_argument("--name", required=True, help="片段名(进文件名)")
    ap.add_argument("--persons", default="", help="出场人物,逗号分隔")
    ap.add_argument("--scene", default="", help="场景说明(缺省用 name)")
    ap.add_argument("--quote", default="", help="关键台词关键词")
    ap.add_argument("--tags", default="", help="标签,逗号分隔")
    ap.add_argument("--height", type=int, default=1080,
                    help="输出高度像素,0=保持原分辨率(默认 1080)")
    ap.add_argument("--crf", type=int, default=18,
                    help="质量,越小越清晰体积越大(默认 18)")
    ap.add_argument("--copy", action="store_true",
                    help="不转码直接切(秒出,但切点对不齐关键帧)")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令不执行")
    args = ap.parse_args()

    start = parse_ts(args.start)
    end = parse_ts(args.end)
    dur = end - start
    if dur <= 0:
        sys.exit("结束时间必须晚于开始时间")

    src = Path(CONFIG["raw_dir"]) / f"{args.ep:02d}.mkv"
    if not src.exists():
        sys.exit(f"找不到源集: {src}")

    cid = next_id(ROOT / CONFIG["index_csv"])
    clips_dir = Path(CONFIG["clips_dir"])
    out_name = f"{cid}_E{args.ep:02d}_{fmt_ts(start)}-{fmt_ts(end)}_{sanitize(args.name)}.mp4"
    out = clips_dir / out_name
    clips_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-hide_banner",
           "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{dur:.3f}"]
    if args.copy:
        cmd += ["-c", "copy"]
    else:
        cmd += ["-c:v", "libx264", "-crf", str(args.crf), "-preset", "medium",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
        if args.height:
            cmd += ["-vf", f"scale=-2:{args.height}"]
    cmd.append(str(out))

    print(" ".join(cmd))
    if args.dry_run:
        print("(dry-run,未执行)")
        return

    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"ffmpeg 失败(片段未登记索引): {out}")

    append_row(ROOT / CONFIG["index_csv"], {
        "id": cid,
        "ep": f"{args.ep:02d}",
        "start": fmt_ts(start),
        "end": fmt_ts(end),
        "duration_sec": int(dur),
        "persons": args.persons,
        "scene": args.scene or args.name,
        "quote": args.quote,
        "tags": args.tags,
        "file": out_name,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    print(f"完成: {out}\n已登记索引: {cid}")


if __name__ == "__main__":
    main()
