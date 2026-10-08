# AGENTS.md — AI newspaper

给在这个目录里干活的 agent 的说明。**动手前先读完这一份。**

## 这是什么

把 AIHOT（aihot.news）的 AI 日报 / 周报 / 月报，做成报纸风格的中文版面，收在一个页面里。
`index.html` 是唯一页面：左侧时间线（日报 / 周报 / 月报 三个切页），右侧阅读区。

## 怎么打开（重要）

数据是散装 JSON，页面用 `fetch()` 读。**浏览器不允许 `file://` 页面读同目录的 JSON**，
所以直接双击 `index.html` 会看到「需要用一个本地服务打开」的提示。正确打开方式：

```bash
cd ai-newspaper
python3 -m http.server 8137       # 然后打开 http://localhost:8137/
```

macOS 上双击 `serve.command` 等价。**不要**为了绕开这一点去把 JSON 合并成 `.js`/bundle，
也不要写回 `local()` 或 CDN 字体：目录必须保持「散装 JSON + 自托管字体」的形态。

## 分享单期

右栏的「分享」按钮复制的是 `index.html?doc=<id>`（如 `?doc=2026-W39`）。
带这个参数打开时：**不显示顶部栏与左栏，只渲染这一期**，也不去拉目录和全量数据——
所以分享链接很快，且只依赖那一期的那一个 JSON 文件。别忘了在页脚/说明里保留这个能力，
不要把它改成 hash（`#` 是索引页内部切期用的，不产生分享视图）。

复制成功后的反馈：**按钮文案始终是「分享」，旁边冒一个「已复制」的小描边提示，1.4 秒后消失**。
不要把按钮文字改成 `copied` 之类（用户明确要求过）。

## 目录

```
index.html            唯一页面（左时间线 / 右阅读区，全部由 data/ 下的 JSON 渲染）
serve.command         双击起本地服务
assets/newspaper.css  公用主题样式；页面里不要再写一份自己的排版 CSS
assets/fonts/         Maple Mono NF CN（自托管，Regular 400 + Bold 700，unicode-range 分片）
data/catalog.json     期数登记表（只登记已完结的期；界面只列有 JSON 的那些）
data/daily/2026/10/2026-10-07.json    日报，按 年/月 分目录
data/weekly/2026-W39.json             周报
data/monthly/2026-09.json             月报
tools/aihot2json.py   AIHOT markdown → data/ 下的某期 JSON
tools/fill_bodies.py  用条目页摘要补齐条目正文（快讯描述）
tools/check.py        数据校验 + 时间线概况
```

## 加一期的完整流程

```bash
# 1) 取源数据（AIHOT 匿名只读，只发 GET；不要要 key、不要改 User-Agent 之外的东西）
code=$(curl -sSL --compressed -A "aihot-skill/2.0.0" -o /tmp/rep.md -w '%{http_code}' \
  "https://aihot.news/api/v1/agent/daily/2026-10-07")
#    weekly/2026-W39 · monthly/2026-09 · daily/2026-10-07
#    条目/事件的取料方式见「补充细节时到哪里取料」
#    404 或没有【栏目】→ 安静日/没这期，到此为止，别生成任何东西（见下一节）

# 2) 机械转换（栏目、条目、标题、链接、来源、日期、正文全部照搬 AIHOT）
python3 tools/aihot2json.py /tmp/rep.md data/daily/2026/10/2026-10-07.json

# 3) 用 AIHOT 条目页的摘要把短条目补全（快讯必做；--all 连正文条目一起）
python3 tools/fill_bodies.py 2026-10-07

# 4) 补编辑部分：见下面「要人工写什么」

# 5) 登记到时间线（没登记就不会出现在界面）
#    编辑 data/catalog.json，加一条 {kind,id,label,window}

# 6) 校验 + 打开看
python3 tools/check.py
python3 -m http.server 8137
```

## 要人工写什么（转换器给不了的部分）

`tools/aihot2json.py` 只搬运，下列字段要按原文事实补齐：

| 字段 | 要求 |
|---|---|
| `lead.deck` | 一句话副题。只能由该期已有事实压缩而成 |
| `lead.paragraphs` | 2–3 段。**必须取自同一期 JSON 里的条目正文**（按标题匹配取 `body`），不要自己重写事实 |
| `lead.source` | 列出这几段的来源与日期，格式 `来源：X（10-07）· Y` |
| `lead.aside` | 侧栏 3–5 条，每条 `title` + `text`，同样只能由该期事实构成 |
| `brief` | 3 条导读；有「总述」时转换器会拆句填好，日报一般要手写 |

写完之后 `python3 tools/check.py` 会提醒 `paragraphs` / `brief` 为空的期。

## 补充细节时到哪里取料（都只在 AIHOT 站内）

AIHOT 的日报/周报 markdown 是「摘要的摘要」，条目往往很短。要写详细一点时：

| 想要什么 | 取哪里 |
|---|---|
| 某一条的完整摘要（快讯补描述就用这个） | `https://aihot.news/items/<id>` 页面里的 `<meta name="description">`，一行就是整条摘要；直接跑 `python3 tools/fill_bodies.py <id>` |
| 某个事件的来龙去脉、时间线 | `https://aihot.news/api/v1/agent/stories/<uuid>`（uuid 从 `/agent/hot` 的「来龙去脉」链接拿） |
| 某话题近 7 天的条目 | `https://aihot.news/api/v1/agent/search?q=关键词` |

```bash
curl -sSL --compressed -A "aihot-skill/2.0.0" "https://aihot.news/items/zvw2i4tg1gnqq72t596vpqoyl" \
  | python3 -c "import sys,re,html;print(html.unescape(re.search(r'<meta name=\"description\" content=\"([^\"]*)\"',sys.stdin.read()).group(1)))"
```

事件页综述（3 段）信息最全，适合写「头条正文 + 附注」；条目页 meta 一行，适合补快讯。
两者都比日报里的条目长，且都是 AIHOT 自己的文案——用它们扩写不属于「凭空补」。

## 版面不要放的东西

- **不要**在报头上面再加一行「期号 + 数据来源 + 刊名」：右侧阅读栏已经显示期号，
  页脚也已经写了来源，加了就是重复（曾经有过 `.topline`，已删）。
- 不要在页面上加期数说明、侧栏导航等界面元素；报纸版面上只留报头、内容与页脚。

## 内容纪律（硬性）

- **只用 AIHOT 返回的内容**。查不到就说查不到，**不要用训练记忆或别的新闻源补**。
- **保持 AIHOT 的栏目顺序与条目顺序**，不要重排、不要自己评榜。
- 每条都要有出处与北京时间；数字、原话回原文核对前不要加工。
- AIHOT 标了不确定的（「据报道」「仅有转述」「未披露」），照实保留，不要写成确定句。
- 一条 = 一件事。同一件事的后续放在同一条的 `extra` 里，不要另起一条。
- `**文字**` 表示暗红加粗（渲染成 `<em>`），只用来点关键数字/结论。
- AIHOT 的服务条款：个人非商业、组织内部使用免费；对外商业用途需事先取得书面授权。

## 文件命名

按类型分目录，日报再按 `年/月` 分；文件名就是 id：

```
data/daily/2026/10/2026-10-07.json     日报
data/daily/2026/09/2026-09-30.json     （跨月自动落在上一个月目录）
data/weekly/2026-W39.json              周报
data/monthly/2026-09.json              月报
data/catalog.json                      登记表，不按类型分
```

`index.html` 从 id 的形状推出路径（`2026-10-07` → daily/年/月、`2026-W39` → weekly、
`2026-09` → monthly），所以分享链接 `?doc=<id>` 里不需要带 kind。
`tools/check.py` 会校验每一期是否放在**该放的位置**，放错目录会直接报错。

## 安静日与缺报的日子：什么也不做

AIHOT 有时一天没有真正的日报。这两种情况**什么都不做**：不生成 JSON、不新增登记、不提交：

| 情况 | 表现 | 处理 |
|---|---|---|
| 那天没有日报 | `/api/v1/agent/daily/<日期>` 返回 **404** | 跳过，什么都不做 |
| 安静日 | 200，但正文只有「导语：今日安静，无大事发生」，一个 `【栏目】` 都没有 | 跳过，什么都不做 |

判断方法就是看正文里有没有 `^【` 开头的栏目行。夜间 workflow（`.github/workflows/daily.yml`）
已经在拉取阶段就把这两种情况拦掉了；手动补期时也要自己先把好这道关。
`tools/aihot2json.py` 能处理安静日（生成一份只有导语的合法 JSON），但那只是为了工具健壮，
不代表应该把它入库。

## 当期未完结的，不要放出来

时间线只登记**已经完结**的期（未完但也别放在 catalog 里，免得以后顺手把 JSON 加上就露出来了）。
当前这一条规则已经落实：

- `2026-10-08` 日报：JSON 留着但**不登记**（用户要求先不展示）
- `2026-W41` 周报、`2026-10` 月报：未完结，不登记、不生成

以后也照此办理：当天日报要等 08:00 发布后才算完结；当周周报等周日过完；当月月报等月末。

## 版式纪律

- **一个页面**：不要生成「每期一个 HTML」。所有呈现由 `index.html` + `data/*.json` 完成。
- **左栏只列已生成的期**（`data/` 下存在对应 JSON 才显示），不显示占位、不显示「待生成」角标，
  也不要有时间轴的竖线与圆点（故意的，别加回去）。没有 JSON 的期只是登记在 catalog 里备用。
- 样式全在 `assets/newspaper.css`。渲染出来的类名必须用现成的：
  `.masthead/.dateline/.brief/.stats/.section/.section-head/.cn-num/.topic-note/
   .lead/.lead-main/.lead--solo/.lead-side/.kicker/.deck/.cols/.cols.two/.story/.src/
   .board/.footer/.sheet/.sheet--flat/.doc-wrap`
- 字体只从 `assets/fonts/fonts.css` 来（`newspaper.css` 已 `@import`）。不要加 CDN、不要加 `local()`。
- 出处 / 信源这类**引用行**是版面里最轻的一层：`--ink-faint` 的灰、9.5px，
  用在 `.story .src`、`.lead-main p.src-line`、`.board .meta`。不要再加深或放大它们。
  （日期用 `.src .t` 提出来给暗红，是为了能一眼扫到时间。）
- **页面上不出现斜体**：不要用 `font-style:italic`（字体包也只有一个字重、没有真斜体）。
  需要区分层级时用字重、颜色、左侧暗红竖线，或 `letter-spacing`。`<em>` 已被重置为不倾斜，
  只承担暗红加粗的语义。
- 阅读区是 CSS 容器（`.doc-wrap`），多栏按**面板自身宽度**折栏，别改成按视口折栏。
- 窄屏（≤900px）左栏是抽屉：`.menu-btn` 开关、`.backdrop` 遮罩、`body.drawer` 控制显隐，
  选完一期自动关闭。阅读区要用 `grid-template-columns:minmax(0,1fr)`：写成 `1fr` 时它的
  auto 最小值会被内容的最小尺寸撑开（曾在 390px 视口里溢出到 468px），配 `min-width:0` 更稳。

## 改完怎么验证

```bash
python3 tools/check.py                       # 数据
python3 -m http.server 8137 &                # 起服务
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --disable-gpu --hide-scrollbars --user-data-dir=/tmp/cp \
  --window-size=1500,1000 --screenshot=/tmp/shot.png --virtual-time-budget=8000 \
  "http://localhost:8137/index.html"
```

看截图确认：报头、导读、数字条、头条+侧栏、多栏正文、热榜、页脚都正常，没有溢出和错行。
`--user-data-dir` 用临时目录，避免命中旧缓存。

## 不要做的事

- 不要把 JSON 合并成 `bundle.js` 之类的产物；不要加 build 步骤。
- 不要在页面里内联一整套样式，或复制一份 CSS。
- 不要引入 CDN / 远程字体 / 本地已安装字体依赖。
- 不要生成没有 AIHOT 依据的内容，也不要把未完结的期放上时间线。
