# 选题库

一切内容从选题开始:先在候选池排队,立项通过才进制作。**人物是素材,选题(期)才是产品**——所以选题层独立于人物层,系列B主题式选题没有单一主角,也能住在这里。

## 文件

```
outline.md          选题大纲总表 = 全量候选池(8 系列,129 期)— 唯一源
outline.html        outline.md 的浏览页(左侧目录→点选题,右侧看点+正文),由脚本生成
_template.md        立项书模板 → 复制为 topics/<slug>/topic.md
<slug>/             已立项选题,一期一文件夹
```

outline.md 改完后重跑 `python tools/outline_to_html.py` 刷新浏览页;别手改 outline.html。

slug 约定:人物式选题用人物同名 slug(与 persons/ 一致,如 `liu-laolao`);主题式选题用主题拼音(如 `zhichang`、`gao-mi-zhe`)。

## 漏斗与状态

```
候选 → 立项 → 制作 → 发布
```

| 状态 | 含义 | 载体 |
|---|---|---|
| 候选 | 在 outline.md 里排队,未开工 | outline.md |
| 立项 | 一句话观点立得住,建了 `<slug>/topic.md` | topics/`<slug>`/ |
| 制作 | 档案 → 观点文章 → 切片 → 脚本(见根 README 工作流) | persons/ + index/ |
| 发布 | 上线,published/ 回填台账与复盘 | published/(待建) |

状态写在每期 topic.md 头部;**活跃选题(立项及之后)必须列入下方排期表**,候选不用——全量看 outline.md。

## 当前排期

| 期 | 选题 | 状态 | 选题书 |
|---|---|---|---|
| 01 | 刘姥姥 | 制作(档案+文章骨架已建,论点待定稿) | [liu-laolao/topic.md](liu-laolao/topic.md) |
| 02 | 放贷(凤姐的灰色收入) | 制作(观点文章已成稿,87版切片待核实) | [fangdai/topic.md](fangdai/topic.md) |

## 与 persons/、index/ 的分工

- **persons/`<slug>`/** 是人物的家:档案、观点文章、脚本——人物式选题的全部产出住这,一个人物可被多期引用
- **topics/`<slug>`/** 是一期的家:立项书;主题式选题(系列B)的文章和脚本也住这
- **index/** 是素材的家:persons.csv 人物台账、clips.csv 片段台账,人物式和主题式共用
