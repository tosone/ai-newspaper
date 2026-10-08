# AI newspaper

AI 日报 / 周报 / 月报的报纸风格归档。**一个页面**：左侧列出已生成的期（日报 / 周报 / 月报 切页），
右侧渲染该期版面。

## 打开方式

浏览器不允许 `file://` 页面读取同目录的 JSON，所以需要一个本地服务：

```bash
cd ai-newspaper
python3 -m http.server 8137     # 打开 http://localhost:8137/
```

macOS 也可以直接双击 `serve.command`。

## 分享单期

右栏「分享」按钮复制的链接形如 `index.html?doc=2026-W39`。带上这个参数打开时，
页面只渲染这一期：没有顶栏、没有左侧列表，也不加载目录，只有一个 JSON 的依赖。

## 目录

```
index.html              唯一页面（左列表 / 右阅读区，全部由 data/*.json 渲染）
serve.command           双击起本地服务
AGENTS.md               给 agent 的工作说明（加一期、取材、版式与内容纪律）
assets/newspaper.css    公用主题样式（含 @import fonts/fonts.css）
assets/fonts/           Maple Mono NF CN 自托管（Regular 400 / Bold 700，unicode-range 分片）
data/catalog.json       期数登记表（左栏只列已生成的，即存在对应 JSON 的期）
data/<id>.json          每期内容（散装 JSON，唯一数据源）
tools/aihot2json.py     AIHOT markdown → data/<id>.json
tools/fill_bodies.py    用 AIHOT 条目页摘要补齐条目正文（快讯描述用这个）
tools/check.py          校验数据 + 打印时间线概况
```

## 加一期

```bash
curl -sSL --compressed -A "aihot-skill/2.0.0" \
  "https://aihot.news/api/v1/agent/daily/2026-10-07" -o /tmp/rep.md
python3 tools/aihot2json.py /tmp/rep.md data/2026-10-07.json
python3 tools/fill_bodies.py 2026-10-07        # 补齐短条目正文（可重复执行）
# 再补 lead.deck / lead.paragraphs / lead.aside / brief（细节见 AGENTS.md）
# 在 data/catalog.json 登记该期
python3 tools/check.py
```

## 数据格式（data/*.json）

```jsonc
{
  "kind": "daily",              // daily | weekly | monthly
  "id": "2026-10-07",
  "masthead":  { "cn": "AI 快报", "en": "The Artificial Intelligence Daily" },
  "edition":   "第 20261007 期",
  "dateline":  ["**2026 年 10 月 7 日**　星期三", "北京时间（UTC+8）", "本版收录 … 的 AI 动态"],
  "briefLabel":"今日导读",
  "brief":     ["导读一句", "导读一句"],
  "stats":     [{ "n": "56", "l": "说明文字" }],            // 可选，周报/月报的数字条
  "lead": {
    "kicker": "OpenAI · 全量开放",
    "title":  "头条标题",
    "deck":   "一句话副题",
    "paragraphs": ["正文段（取自同期条目正文）", "正文段"],
    "source": "来源：…",
    "aside":  { "title": "侧栏标题", "items": [{"title":"小标题","text":"说明"}], "more": "脚注" }
  },
  "sections": [
    { "num":"02", "name":"模型发布与更新", "cols":3, "note":"可选栏目引言",
      "items":[{ "title":"…", "url":"…", "source":"…", "date":"10-08", "body":"…", "extra":"…" }] }
  ],
  "footer": { "stamp": "AI 快报", "lines": ["页脚说明"] }
}
```

正文里 `**文字**` = 暗红加粗（渲染成 `<em>`）。`date` 缺失时不渲染日期。`cols: 2` 走两栏。
