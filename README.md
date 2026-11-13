# honglou-87-studio

红楼梦 87 版人物解读内容工作室。主产品:剧集片段 + 解说的长视频;衍生:图文、短视频切片。

## 目录

```
topics/     选题库(outline.md 候选池 / _template.md 立项模板 / 各期立项书)— git 管理
persons/    人物档案,一人一文件夹(profile.md / article.md / 脚本)— git 管理
index/      素材索引(clips.csv 片段台账 / persons.csv 人物台账)— git 管理
published/  已发布台账与复盘(待建)
tools/      cut.py 切片脚本 — git 管理
assets/     封面等本地素材 — 不进 git
```

**媒体资产在库外**:36 集源片在 `D:\hlm`(01.mkv–36.mkv,2160p,189G),切片输出在 `D:\hlm\clips`。git 只管文本。

## 环境依赖

- Python 3.10(已有)
- ffmpeg(必需,切片靠它):`winget install Gyan.FFmpeg`,装完重开终端

## 工作流(每期一条流水线,文章先行)

核心原则:**先有文章、先立观点**。文章是一切形式的母本——长视频解说词是它的口语化改写,图文直接用它,短视频从长视频里切。

0. **选题立项** `topics/<slug>/topic.md`:从 `topics/outline.md` 候选池里选中,一句话观点立得住才立项(模板 `topics/_template.md`;状态流转见 `topics/README.md`)
1. **建人物档案** `persons/<slug>/profile.md`:出场索引、关系网、金句、看点
2. **写观点文章** `persons/<slug>/article.md`:论点、结构、写作要点——这一步定生死,观点立不住后面全白做
3. **对照视频核实集数/时间码**,逐段切片:
   ```bash
   python tools/cut.py --ep 3 --start 00:12:30 --end 00:14:05 \
       --name "刘姥姥一进门前问门房" --persons "刘姥姥" \
       --quote "太爷们纳福" --tags "卑微,喜剧"
   ```
   片段落盘 `D:\hlm\clips\` 并自动登记 `index/clips.csv`(CL-#### 编号)。
   快速验证用 `--dry-run`;不转码秒切用 `--copy`。
4. **写视频脚本** `persons/<slug>/script-v1.md`(解说词=文章口语化,引用片段 id):
   冷开场(争议钩子)→ 人物弧线 → 2-3 个关键场景逐段拆解 → 关系网展开 → 主题升华
5. **剪辑 → 发布**,台账记入 `published/`,复盘数据反哺下期选题

## 发布注意

片段必须服务于解说观点:控制片段总占比、避免大段原声直出,防止被判搬运;保留一版"解说音轨+静帧"的备份以便被下架后快速重传。
