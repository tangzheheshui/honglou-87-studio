#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""topics/outline.md → topics/outline.html

选题大纲浏览页:左侧目录(系列 → 选题标题),点标题右侧出详情。
详情上半部分(看点/串联)固定,下半部分为正文区(可滚动)。
大纲内容以 outline.md 为唯一源;改完大纲后重跑本脚本即可更新视图:

    python tools/outline_to_html.py

有真实文章母本的选题,正文区直接嵌入全文(见下方 ARTICLES 登记表);
未写的选题展示占位说明 + 参考讲稿骨架。
"""
from __future__ import annotations

import datetime
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "topics" / "outline.md"
DST = ROOT / "topics" / "outline.html"

# 选题名 → 已有的文章母本(命中后,该选题正文区嵌入全文)
# 人物式选题用人物名做 key,主题式选题用主题名(「——」前)做 key
ARTICLES = {
    "刘姥姥": ROOT / "persons" / "liu-laolao" / "article.md",
    "放贷": ROOT / "topics" / "fangdai" / "article.md",
}


# ---------------------------------------------------------------- 解析

def parse_md(text: str) -> list[dict]:
    """md → 块列表 {'level', 'title', 'blocks': [(kind, payload)]}"""
    blocks: list[dict] = []
    cur: dict = {"level": 0, "title": "", "blocks": []}
    blocks.append(cur)
    pending: dict | None = None

    def flush_table():
        nonlocal pending
        if pending is not None:
            cur["blocks"].append(("table", pending))
            pending = None

    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if pending is None:
                pending = {"header": None, "rows": []}
            if pending["header"] is None:
                pending["header"] = cells
            elif set("".join(cells)) <= set(":-— "):
                pass
            else:
                pending["rows"].append(cells)
            continue
        m = re.match(r"^(#{1,4})\s+(.+)$", s)
        if m:
            flush_table()
            cur = {"level": len(m.group(1)), "title": m.group(2).strip(), "blocks": []}
            blocks.append(cur)
            continue
        m = re.match(r"^(\d+)[.、]\s+(.*)$", s)
        if m:
            flush_table()
            cur["blocks"].append(("oli", m.group(2)))
            continue
        if s.startswith("- "):
            flush_table()
            cur["blocks"].append(("uli", s[2:]))
            continue
        if s.startswith("> "):
            flush_table()
            cur["blocks"].append(("quote", s[2:]))
            continue
        if not s:
            flush_table()
            continue
        flush_table()
        cur["blocks"].append(("p", s))
    flush_table()
    return blocks


def organize(blocks: list[dict]) -> tuple[dict, list[dict]]:
    header = next(b for b in blocks if b["level"] == 1)
    series: list[dict] = []
    cur: dict | None = None
    for b in blocks:
        if b["level"] == 2:
            cur = {"sec": b, "units": []}
            series.append(cur)
        elif b["level"] == 3 and cur is not None:
            cur["units"].append(b)
    return header, series


# ---------------------------------------------------------------- 工具

def esc(t: str) -> str:
    return html.escape(t, quote=True)


def strip_bold(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t)


def fmt(t: str) -> str:
    t = html.escape(t, quote=True)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def strip_count(title: str) -> str:
    return re.sub(r"[（(]\d+期[)）]", "", title).strip()


def short_label(title: str) -> str:
    return re.split(r"—", strip_count(title))[0].strip().strip("—、 ")


def group_name(title: str) -> str:
    """系列标题 → 目录分组名(去掉“系列A:”这类编号字眼)"""
    return re.sub(r"^系列[A-Za-z][:：]\s*", "", short_label(title))


def unit_name(title: str) -> str:
    """单元标题 → 子分组名(去掉“A1”这类编号)"""
    return re.sub(r"^[A-Za-z]\d+\s*", "", short_label(title))


def clean_title(cell: str) -> tuple[str, str | None]:
    """选题单元格 → (干净标题, 已立项期数或 None)"""
    done = None
    m = re.search(r"★已立项(\d+)期", cell)
    if m:
        done = f"已立项{m.group(1)}期"
    t = re.sub(r"★已立项\d+期", "", cell)
    t = strip_bold(t).replace("★", "").strip(" :：—- ")
    return t, done


def clean_points(cell: str) -> list[str]:
    cell = re.sub(r"★已立项\d+期", "", cell)
    segs = [s.replace("★", "").strip(" ;；。") for s in re.split(r"[;；]", cell)]
    return [s for s in segs if s]


def article_for(title: str):
    """按选题名找文章母本:人物式取「:」前,主题式取「——」前"""
    return ARTICLES.get(title.split(":")[0].strip()) or ARTICLES.get(title.split("——")[0].strip())

# ---------------------------------------------------------------- 渲染(md → html)

def render_table(tbl: dict) -> str:
    h = ["<table>"]
    if tbl["header"]:
        h.append("<thead><tr>" + "".join(f"<th>{fmt(c)}</th>" for c in tbl["header"]) + "</tr></thead>")
    h.append("<tbody>")
    for row in tbl["rows"]:
        h.append("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in row) + "</tr>")
    h.append("</tbody></table>")
    return "".join(h)


def render_blocks(items: list[tuple]) -> str:
    out: list[str] = []
    i = 0
    while i < len(items):
        kind, payload = items[i]
        if kind in ("oli", "uli", "quote"):
            tag = {"oli": "ol", "uli": "ul", "quote": "blockquote"}[kind]
            lis: list[str] = []
            while i < len(items) and items[i][0] == kind:
                lis.append(f"<li>{fmt(items[i][1])}</li>" if kind != "quote" else f"<p>{fmt(items[i][1])}</p>")
                i += 1
            out.append(f"<{tag}>" + "".join(lis) + f"</{tag}>")
            continue
        if kind == "p":
            out.append(f"<p>{fmt(payload)}</p>")
        elif kind == "table":
            out.append(render_table(payload))
        i += 1
    return "".join(out)


def render_md(text: str) -> str:
    """文章母本渲染:一级标题降为 h2(页面已有自己的 h1)"""
    out: list[str] = []
    for b in parse_md(text):
        if b["level"] == 1:
            out.append(f"<h2>{fmt(strip_bold(b['title']))}</h2>")
        elif b["level"] >= 2:
            out.append(f'<h{min(b["level"] + 1, 6)}>{fmt(strip_bold(b["title"]))}</h{min(b["level"] + 1, 6)}>')
        out.append(render_blocks(b["blocks"]))
    return "".join(out)


# ---------------------------------------------------------------- 选题详情

SKELETON_A = [
    ("钩子", "破除刻板印象:大家以为 TA 是 XX,其实……(冷开场争议钩子)"),
    ("底牌", "出身、身份、手里有什么筹码(人物弧线)"),
    ("关键事件", "用 87 版对应片段讲 TA 的选择(切片登记,引用 CL 编号)"),
    ("矛盾点", "善与恶、清醒与局限、挣扎与妥协(关键场景拆解)"),
    ("落点", "轮换:制度 / 人心 / 代价 / 幸存,别每期都落“规则困住了 TA”"),
    ("收尾", "87 版演员的演绎与改编处理(主题升华+系列特色)"),
]

SKELETON_GENERIC = [
    ("冷开场", "争议钩子,一句话把人拉进来"),
    ("主体", "人物弧线 / 串联素材逐个展开"),
    ("关键场景", "2-3 个场景逐段拆解(87 版切片引用 CL 编号)"),
    ("关系网", "把单点事件展开成人物关系全景"),
    ("主题升华", "落点轮换:制度 / 人心 / 代价 / 幸存"),
]


def placeholder_body(is_a: bool) -> str:
    sk = SKELETON_A if is_a else SKELETON_GENERIC
    lis = "".join(f"<li><b>{esc(k)}</b>——{esc(v)}</li>" for k, v in sk)
    return (
        '<p class="ph">正文母本未写。立项后写到 '
        "<code>persons/&lt;slug&gt;/article.md</code>(主题式选题在 "
        "<code>topics/&lt;slug&gt;/</code>),在 tools/outline_to_html.py 的 "
        "ARTICLES 表里登记,重跑脚本,这里就会显示全文。</p>"
        "<h2>参考讲稿骨架</h2><ol>" + lis + "</ol>"
    )


def article_body(path: Path) -> str:
    return (
        '<p class="src">文章母本:<code>'
        + esc(str(path.relative_to(ROOT)))
        + "</code>(以下为当前内容,成稿后以文件为准)</p>"
        + render_md(path.read_text(encoding="utf-8"))
    )


# ---------------------------------------------------------------- 主流程

def build() -> None:
    header, entries = organize(parse_md(SRC.read_text(encoding="utf-8")))
    series = [e for e in entries if e["sec"]["title"].startswith("系列")]
    extras = [e for e in entries if not e["sec"]["title"].startswith("系列")]

    data: dict[str, dict] = {}
    counter = 0

    def new_id() -> str:
        nonlocal counter
        counter += 1
        return f"t{counter}"

    def add(label, crumb, done, points, link, body):
        tid = new_id()
        chips = ""
        if done:
            chips += f'<span class="chip done">{esc(done)}</span>'
        pts = "".join(f"<li>{esc(p)}</li>" for p in points)
        lnk = f'<div class="link"><b>串联素材</b>:{esc(link)}</div>' if link else ""
        head = (
            f'<div class="crumb">{esc(crumb)}</div>'
            f"<h1>{esc(label)}</h1>"
            + (f'<div class="chips">{chips}</div>' if chips else "")
            + (f'<ul class="points">{pts}</ul>' if pts else "")
            + lnk
        )
        data[tid] = {"head": head, "body": body}
        return tid

    # 大纲说明(总述)作为目录第一项
    intro_body = (
        '<p class="src">来源:<code>topics/outline.md</code> 开头总述。'
        "选题立项流程见根目录 <code>README.md</code> 工作流第 0 步。</p>"
        + render_blocks(header["blocks"])
    )
    intro_id = add("大纲说明", "总述 · 题式骨架", None, [], "", intro_body)

    def topic_rows(u):
        """一个块(系列或单元)的表格行 → [(标题, 已立项, 看点列表, 串联)]"""
        rows = []
        for k, p in u["blocks"]:
            if k != "table":
                continue
            for row in p["rows"]:
                title, done = clean_title(row[0])
                if done is None:
                    m = re.search(r"★已立项(\d+)期", " ".join(row[1:]))
                    if m:
                        done = f"已立项{m.group(1)}期"
                points = clean_points(row[-1])
                link = strip_bold(row[1]).strip() if len(row) >= 3 else ""
                rows.append((title, done, points, link))
        return rows

    def leaf_html(tid: str, title: str) -> str:
        return f'<a class="leaf" data-id="{tid}" href="javascript:;">{esc(title)}</a>'

    # 各系列 → (单元 →)选题
    default_id = None
    groups: list[dict] = []
    for si, entry in enumerate(series):
        sec = entry["sec"]
        gname = group_name(sec["title"])
        gopen = " open" if si == 0 else ""
        if entry["units"]:
            subs: list[dict] = []
            default_sub = -1
            for ui, u in enumerate(entry["units"]):
                uname = unit_name(u["title"])
                leaves = []
                for (title, done, points, link) in topic_rows(u):
                    src = article_for(title)
                    body = article_body(src) if src else placeholder_body(True)
                    tid = add(title, " · ".join([gname, uname]), done, points, link, body)
                    if done and default_id is None:
                        default_id = tid
                        default_sub = ui
                    leaves.append(leaf_html(tid, title))
                subs.append({"name": esc(uname), "open": "", "leaves": leaves, "count": len(leaves)})
            if si == 0 and default_sub >= 0:
                subs[default_sub]["open"] = " open"
            groups.append({
                "name": esc(gname), "open": gopen, "subs": subs,
                "leaves": [], "count": sum(s["count"] for s in subs),
            })
        else:
            leaves = []
            for (title, done, points, link) in topic_rows(sec):
                src = article_for(title)
                body = article_body(src) if src else placeholder_body(False)
                tid = add(title, gname, done, points, link, body)
                if done and default_id is None:
                    default_id = tid
                leaves.append(leaf_html(tid, title))
            groups.append({
                "name": esc(gname), "open": gopen, "subs": None,
                "leaves": leaves, "count": len(leaves),
            })

    # 附:开更顺序 / 讲稿结构
    extra_leaves: list[str] = []
    for e in extras:
        label = short_label(e["sec"]["title"])
        tid = add(label, "附", None, [], "", render_blocks(e["sec"]["blocks"]))
        extra_leaves.append(leaf_html(tid, label))

    def grp_html(g: dict) -> str:
        if g["subs"]:
            inner = "".join(
                f'<div class="sub"><div class="sub-head"><span class="chev{s["open"]}"></span>'
                f'<span class="sub-name">{s["name"]}</span><span class="cnt">{s["count"]}</span></div>'
                f'<div class="sub-body{s["open"]}">{"".join(s["leaves"])}</div></div>'
                for s in g["subs"]
            )
        else:
            inner = "".join(g["leaves"])
        return (
            f'<div class="grp"><div class="grp-head"><span class="chev{g["open"]}"></span>'
            f'<span class="grp-name">{g["name"]}</span><span class="cnt">{g["count"]}</span></div>'
            f'<div class="grp-body{g["open"]}">{inner}</div></div>'
        )

    # ---- 目录 HTML ----
    tree = [f'<a class="leaf intro" data-id="{intro_id}" href="javascript:;">大纲说明</a>']
    tree += [grp_html(g) for g in groups]
    tree.append(
        '<div class="grp"><div class="grp-head"><span class="chev"></span>'
        '<span class="grp-name">附</span><span class="cnt">' + str(len(extra_leaves)) + '</span></div>'
        '<div class="grp-body">' + "".join(extra_leaves) + "</div></div>"
    )

    n_topics = sum(g["count"] for g in groups)
    n_done = sum(1 for v in data.values() if "已立项" in v["head"])

    page = (
        TEMPLATE
        .replace("__STATS__", f"{len(groups)} 个系列 · {n_topics} 期 · {n_done} 已立项")
        .replace("__TREE__", "".join(tree))
        .replace("__DATA__", json.dumps(data, ensure_ascii=False))
        .replace("__DEFAULT__", default_id or "")
        .replace("__GEN__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    DST.write_text(page, encoding="utf-8")
    print(f"{len(groups)} 个系列,共 {n_topics} 期,已立项 {n_done} 期,附 {len(extras)} 节,说明 1 节")
    print(f"已生成 {DST.relative_to(ROOT)}")


# ---------------------------------------------------------------- 页面模板

TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>选题大纲 · 红楼梦 87 版</title>
<style>
:root{
  --bg:#faf9f7; --panel:#ffffff; --ink:#2b2622; --muted:#8a8378;
  --line:#e7e2da; --accent:#9a5b32; --accent-soft:#f3e7db;
  --star:#d99a1b; --badge-bg:#e5f2e3; --badge-ink:#2f6b33;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#191715; --panel:#211e1b; --ink:#e8e2da; --muted:#948d83;
    --line:#332e29; --accent:#d59a6a; --accent-soft:#33291f;
    --star:#e5b13f; --badge-bg:#25341f; --badge-ink:#8fce8a;
  }
}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.7 -apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
code{background:var(--accent-soft);border-radius:5px;padding:1px 6px;font-size:.9em}

/* ---- 骨架 ---- */
.app{display:flex;height:100vh}
body.side-off #sidebar{display:none}
#side-show{display:none;position:fixed;top:14px;left:14px;z-index:20;
  padding:7px 13px;border:1px solid var(--line);border-radius:8px;background:var(--panel);
  color:var(--ink);cursor:pointer;font-size:13px;box-shadow:0 2px 10px rgba(0,0,0,.12)}
body.side-off #side-show{display:block}
#side-show:hover{color:var(--accent);border-color:var(--accent)}

/* ---- 左:目录 ---- */
#sidebar{width:300px;flex:none;display:flex;flex-direction:column;
  background:var(--panel);border-right:1px solid var(--line);padding:18px 14px 10px}
.side-head{display:flex;align-items:flex-start;gap:6px}
.brand{flex:1}
.brand .ttl{font-size:17px;font-weight:700}
.brand .sub{color:var(--muted);font-size:12px;margin-top:2px}
.stats{margin:10px 2px 12px;color:var(--muted);font-size:12.5px}
#side-hide{flex:none;border:none;background:none;color:var(--muted);cursor:pointer;
  font-size:15px;line-height:1;padding:5px 7px;border-radius:6px}
#side-hide:hover{color:var(--accent);background:var(--accent-soft)}
#tree{flex:1;overflow:auto;border-top:1px solid var(--line);padding-top:10px}
#tree>.leaf.intro{font-weight:600;margin-bottom:10px}
.grp{margin-bottom:2px}
.grp-head{display:flex;align-items:center;gap:4px;padding:3px 0}
.grp-name{font-weight:600;font-size:13.5px}
.chev{flex:none;width:15px;height:20px;display:flex;align-items:center;justify-content:center;
  color:var(--muted);cursor:pointer;user-select:none;font-size:11px;border-radius:4px}
.chev:hover{color:var(--accent);background:var(--accent-soft)}
.chev::before{content:"▸";display:inline-block;transition:transform .15s}
.chev.open::before{transform:rotate(90deg)}
.cnt{color:var(--muted);font-weight:400;font-size:11.5px;margin-left:auto;padding-right:6px}
.grp-body{display:none;padding-left:14px;margin-bottom:6px}
.grp-body.open{display:block}
.sub{margin-bottom:7px}
.sub-head{display:flex;align-items:center;gap:3px;padding:2px 0}
.sub-name{font-size:12.5px;font-weight:600;color:var(--muted)}
.sub-body{display:none;padding-left:16px;margin-top:2px}
.sub-body.open{display:block}
a.leaf{display:block;padding:5px 8px;border-radius:6px;color:var(--ink);
  font-size:13px;line-height:1.45;cursor:pointer}
a.leaf:hover{background:var(--accent-soft);color:var(--accent)}
a.leaf.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.foot{border-top:1px solid var(--line);margin-top:8px;padding-top:8px;
  color:var(--muted);font-size:11.5px;line-height:1.5}

/* ---- 右:详情 ---- */
#detail{flex:1;min-width:0;overflow:auto}
#d-top{position:sticky;top:0;z-index:5;background:var(--panel);
  border-bottom:1px solid var(--line);padding:20px 34px 16px;max-height:52vh;overflow:auto}
#d-top h1{font-size:22px;margin:2px 0 0;line-height:1.4}
.crumb{color:var(--muted);font-size:12.5px}
.chips{margin-top:8px}
.chip{display:inline-block;border-radius:99px;padding:1px 10px;font-size:12px;
  font-weight:600;margin:0 6px 4px 0}
.chip.done{background:var(--badge-bg);color:var(--badge-ink)}
ul.points{margin:12px 0 0;padding-left:1.4em;font-size:14px}
ul.points li{margin:3px 0}
.link{margin-top:10px;color:var(--muted);font-size:13px}
.link b{color:var(--ink);font-weight:600}
#d-body{padding:24px 34px 80px;max-width:820px}
#d-body h2{font-size:19px;margin:26px 0 10px}
#d-body h3{font-size:16px;margin:20px 0 8px}
#d-body blockquote{margin:14px 0;padding:8px 16px;border-left:3px solid var(--accent);
  background:var(--panel);border-radius:0 8px 8px 0;color:var(--muted)}
#d-body blockquote p{margin:4px 0}
.ph,.src{color:var(--muted);font-size:13.5px;background:var(--panel);
  border:1px dashed var(--line);border-radius:8px;padding:10px 14px}
.src{margin-bottom:16px}
@media (max-width:880px){
  .app{flex-direction:column}
  #sidebar{width:auto;max-height:45vh;border-right:none;border-bottom:1px solid var(--line)}
  #d-top,#d-body{padding-left:18px;padding-right:18px}
}
</style>
</head>
<body>
<button id="side-show" type="button">☰ 目录</button>
<div class="app">
<nav id="sidebar">
  <div class="side-head">
    <div class="brand"><div class="ttl">选题大纲</div><div class="sub">红楼梦 87 版 · 候选池</div></div>
    <button id="side-hide" type="button" title="收起目录">«</button>
  </div>
  <div class="stats">__STATS__</div>
  <div id="tree">__TREE__</div>
  <div class="foot">由 tools/outline_to_html.py 从 topics/outline.md 生成(__GEN__),改大纲后重跑脚本即可。</div>
</nav>
<main id="detail">
  <header id="d-top"></header>
  <div id="d-body"></div>
</main>
</div>
<script>
const DATA = __DATA__;
const DEFAULT_ID = "__DEFAULT__";
const dTop = document.getElementById('d-top');
const dBody = document.getElementById('d-body');
const detail = document.getElementById('detail');
let current = null;

function select(a){
  if (!a) return;
  if (current) current.classList.remove('active');
  current = a;
  a.classList.add('active');
  const e = DATA[a.dataset.id];
  if (!e) return;
  dTop.innerHTML = e.head;
  dBody.innerHTML = e.body;
  detail.scrollTop = 0;
  dTop.scrollTop = 0;
}

document.getElementById('tree').addEventListener('click', ev => {
  const leaf = ev.target.closest('.leaf');
  if (leaf){ select(leaf); return; }
  const chev = ev.target.closest('.chev');
  if (chev){
    const body = chev.parentElement.nextElementSibling;
    if (body){
      const open = body.classList.toggle('open');
      chev.classList.toggle('open', open);
    }
  }
});

document.getElementById('side-hide').onclick = () =>
  document.body.classList.add('side-off');
document.getElementById('side-show').onclick = () =>
  document.body.classList.remove('side-off');

select(document.querySelector('.leaf[data-id="' + DEFAULT_ID + '"]'));
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build()
