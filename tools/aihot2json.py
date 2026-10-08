#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIHOT markdown → data/<kind>-<id>.json

    # 先取源数据（AIHOT 只允许 GET，匿名只读，无需 key）
    curl -sSL --compressed -A "aihot-skill/2.0.0" \
      "https://aihot.news/api/v1/agent/daily/2026-10-07" -o /tmp/rep.md
    # 再转换
    python3 tools/aihot2json.py /tmp/rep.md data/daily-2026-10-07.json

转换器只做机械搬运：栏目、条目、标题、链接、来源、日期、正文都按 AIHOT 原文照搬，
顺序不重排；头条 / 导读 / 总述 / 快讯按对应结构落位。
真正需要判断力的部分（lead.deck、lead.aside、brief 的措辞）转换器会给一个
稳妥的默认值，之后按需人工微调——不要凭空补事实。
"""
import json, re, sys, os, datetime

MONTH_EN = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
            7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
WD = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
KIND = {
    'daily':   {'cn': 'AI 快报', 'en': 'The Artificial Intelligence Daily',  'cadence': '{wd}', 'span': '本期'},
    'weekly':  {'cn': 'AI 周报', 'en': 'The Artificial Intelligence Weekly',  'cadence': '每周一 10:00（北京时间）发布', 'span': '本周'},
    'monthly': {'cn': 'AI 月报', 'en': 'The Artificial Intelligence Monthly', 'cadence': '每月 1 日 10:30（北京时间）发布', 'span': '本月'},
}


# ── 小工具 ───────────────────────────────────────────────────────────────
def mdlink(s):
    """正文里的 [文字](链接) → 文字；裸链接保留"""
    return re.sub(r'\[([^\]]+)\]\((?:https?://[^)]+)\)', r'\1', s)


def clean(s):
    s = mdlink(s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def split_source(line):
    """'蚂蚁百灵（05-01）' → ('蚂蚁百灵', '05-01')"""
    m = re.search(r'[（(](\d{2}-\d{2})[）)]\s*$', line)
    if m:
        return line[:m.start()].strip(' ·'), m.group(1)
    return line.strip(' ·'), ''


# ── 解析 ─────────────────────────────────────────────────────────────────
def parse(md):
    lines = md.split('\n')
    try:
        a = next(i for i, l in enumerate(lines) if '不可信外部资料开始' in l)
        b = next(i for i, l in enumerate(lines) if '不可信外部资料结束' in l)
    except StopIteration:
        a, b = 0, len(lines)
    head, body = lines[:a], lines[a + 1:b]

    meta = {'headline': '', 'summary': '', 'window': '', 'lines': []}
    for l in head:
        l = l.strip()
        if l.startswith('头条：'):
            meta['headline'] = l[3:].strip()
        elif l.startswith('总述：'):
            meta['summary'] = l[3:].strip()
        elif l.startswith('收录北京时间'):
            meta['window'] = l.replace('收录北京时间', '').split('的动态')[0].strip()
        elif l.startswith('从 ') and '的日报里选出' in l:
            meta['window'] = l.split('的日报里选出')[0].replace('从 ', '').strip()

    sections, cur = [], None
    mode = None            # 'item' | 'quick'
    for raw in body:
        line = raw.rstrip()
        if not line.strip():
            continue
        s = line.strip()

        m = re.match(r'^【(.+?)】$', s)
        if m:
            cur = {'name': m.group(1), 'note': '', 'items': []}
            sections.append(cur)
            mode = None
            continue
        if cur is None:
            # 头条 / 总述 / 导语 在安全分隔标记之后、第一个栏目之前
            if s.startswith('头条：'):
                meta['headline'] = s[3:].strip()
            elif s.startswith('总述：'):
                meta['summary'] = s[3:].strip()
            elif s.startswith('导语：'):
                meta['headline'] = s[3:].strip()
            elif not s.startswith(('［', '】')):
                meta['lines'].append(s)   # 导语后面那一段正文（安静日只有这一句）
            continue
        if s.startswith('导读：'):
            cur['note'] = clean(s[3:])
            continue

        # 快讯：- 10-07 20:45 · [标题](url) · 来源
        m = re.match(r'^-\s*(?:(\d{2}-\d{2} \d{2}:\d{2})\s*·\s*)?\[(.+?)\]\((https?://[^)]+)\)(?:\s*·\s*(.*))?$', s)
        if m and (cur['name'] == '快讯' or m.group(1)):
            d, t, u, src = m.group(1) or '', m.group(2), m.group(3), (m.group(4) or '')
            cur['items'].append({'title': clean(t), 'url': u, 'source': clean(src), 'date': d})
            mode = None
            continue

        # 条目：1. [标题](url) · 来源（05-01）
        m = re.match(r'^\d+\.\s*\[(.+?)\]\((https?://[^)]+)\)(?:\s*·\s*(.*))?$', s)
        if m:
            src, date = split_source(m.group(3) or '')
            cur['items'].append({'title': clean(m.group(1)), 'url': m.group(2), 'source': src, 'date': date})
            mode = 'item'
            continue

        # 其余行：条目正文 / 相关 / 跟进（markdown 里常写成 "- 相关：…"）
        if mode == 'item' and cur['items']:
            if re.match(r'^-?\s*(相关|跟进)[：:]', s):
                s = re.sub(r'^-\s*', '', s)
                cur['items'][-1]['extra'] = (cur['items'][-1].get('extra', '') + ' ' + clean(s)).strip()
            else:
                it = cur['items'][-1]
                it['body'] = (it.get('body', '') + clean(s)) if it.get('body') else clean(s)

    sections = [s for s in sections if s['items']]
    return meta, sections


def build(path, out):
    md = open(path, encoding='utf-8').read()
    m = re.match(r'^# AIHOT (日报|周报|月报) · (\S+)', md)
    if not m:
        raise SystemExit('✗ 不是 AIHOT 日报/周报/月报 markdown')
    kind = {'日报': 'daily', '周报': 'weekly', '月报': 'monthly'}[m.group(1)]
    did = re.match(r'\d{4}(?:-W\d{2}|-\d{2}-\d{2}|-\d{2})', m.group(2)).group(0)
    meta, sections = parse(md)

    # 篇眉
    if kind == 'daily':
        d = datetime.date.fromisoformat(did)
        stamp = f'**{d.year} 年 {d.month} 月 {d.day} 日**\u3000{WD[d.weekday()]}'
        edition = f'第 {d.strftime("%Y%m%d")} 期'
        dateline = [stamp, '北京时间（UTC+8）', f'本版收录 {meta["window"]} 的 AI 动态']
    elif kind == 'weekly':
        y, w = int(did[:4]), int(did.split('-W')[1])
        mon = datetime.date.fromisocalendar(y, w, 1)
        sun = mon + datetime.timedelta(days=6)
        stamp = (f'**{y} 年第 {w} 周**\u3000'
                 f'{mon.month:02d}.{mon.day:02d} — {sun.month:02d}.{sun.day:02d}')
        edition = f'第 {did} 期'
        dateline = [stamp, '每周一 10:00（北京时间）发布', f'选自 {meta["window"]} 的日报重点']
    else:
        y, mo = int(did[:4]), int(did[5:])
        edition = f'第 {did} 期'
        dateline = [f'**{y} 年 {mo} 月**', '每月 1 日 10:30（北京时间）发布',
                    f'选自 {meta["window"]} 的日报重点']

    # 导读：总述拆句；没有总述就用各栏目导读的第一句兜底
    brief = []
    if meta['summary']:
        s = re.sub(r'^[^：]{0,12}大事，最受关注的是：', '', meta['summary'])
        parts = [p.strip() for p in re.split(r'[；;]', s.rstrip('。')) if p.strip()]
        brief = [p + '。' for p in parts][:3]
    if not brief:
        brief = [s['note'].split('。')[0] + '。' for s in sections if s['note']][:3]
    if not brief and meta['headline']:            # 安静日的日报：只有一句导语
        brief = [meta['headline'] + ('。' if not meta['headline'].endswith('。') else '')]

    # 头条：若栏目里有同名条目，直接用它的正文；否则用总述 / 首个栏目导读 / 导语正文
    lead_title = (meta['headline'] or (brief[0] if brief else '')
                  or (sections[0]['name'] if sections else '本期无大事'))
    lead = {'title': lead_title, 'paragraphs': []}
    hit = None
    for s in sections:
        for it in s['items']:
            if it['title'] == meta['headline'] or (meta['headline'] and
                                                   it['title'].startswith(meta['headline'][:12])):
                hit = it
                break
        if hit:
            break
    if hit and hit.get('body'):
        lead['paragraphs'] = [hit['body']]
        lead['source'] = f'来源：{hit["source"]}' + (f'（{hit["date"]}）' if hit['date'] else '')
    elif meta['summary']:
        lead['paragraphs'] = [meta['summary']]
        lead['source'] = '来源：AIHOT 本期总述'
    elif sections and sections[0]['note']:
        lead['paragraphs'] = [sections[0]['note']]
        lead['source'] = f'来源：AIHOT 本期「{sections[0]["name"]}」导读'
    elif meta['lines']:
        lead['paragraphs'] = [' '.join(meta['lines'])]
        lead['source'] = '来源：AIHOT 本期导语'

    # 栏目编号 02 起（01 是头条）
    out_sections = []
    for i, s in enumerate(sections):
        sec = {'num': f'{i + 2:02d}', 'name': s['name'], 'cols': 3, 'items': []}
        if s['note']:
            sec['note'] = s['note']
        for it in s['items']:
            item = {'title': it['title'], 'url': it['url']}
            if it['source']:
                item['source'] = it['source']
            if it['date']:
                item['date'] = it['date']
            if it.get('body'):
                item['body'] = it['body']
            if it.get('extra'):
                item['extra'] = it['extra']
            sec['items'].append(item)
        out_sections.append(sec)

    doc = {
        'kind': kind,
        'id': did,
        'masthead': {'cn': KIND[kind]['cn'], 'en': KIND[kind]['en']},
        'edition': edition,
        'dateline': dateline,
        'briefLabel': {'daily': '今日导读', 'weekly': '本周总述', 'monthly': '本月总述'}[kind],
        'brief': brief,
        'lead': lead,
        'sections': out_sections,
        'footer': {
            'stamp': KIND[kind]['cn'],
            'lines': [
                f'本版内容整理自 AIHOT {m.group(1)}（{did}），数据来源：AIHOT（aihot.news）。'
                f'标题、摘要来自第三方信源，仅供资料参考，数字与原话请回原文核对。',
                f'{m.group(1)}收录范围：北京时间 {meta["window"]}。所有时间均为北京时间。',
            ],
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'✓ {out}  {kind} {did} | 栏目 {len(out_sections)} | 条目 '
          f'{sum(len(s["items"]) for s in out_sections)} | 头条 {lead["title"][:28]}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2])
