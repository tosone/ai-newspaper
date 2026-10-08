#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 AIHOT 条目页的摘要，给 data/ 下某一期里缺正文的条目补上 body。

    python3 tools/fill_bodies.py 2026-10-01            # 只补「快讯」（日报/周报/月报的短条目）
    python3 tools/fill_bodies.py 2026-10-01 --all      # 连正文条目也一起补
    python3 tools/fill_bodies.py 2026-10-01 --force    # 已有 body 也覆盖

条目页 `<meta name="description">` 是 AIHOT 自己的整条摘要，比日报里的更完整。
超过 200 字的只按句截断，不改写内容。可以重复执行（幂等）。
"""
import json, re, html, sys, os, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'aihot-skill/2.0.0 (+https://aihot.news/aihot-skill/)'
LIMIT = 200


def fetch_desc(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            s = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
            m = re.search(r'<meta name="description" content="([^"]*)"', s)
            if m:
                return html.unescape(m.group(1))
        except Exception as e:
            if i == tries - 1:
                print(f'    ! 取不到 {url}: {e}')
        time.sleep(0.4 * (i + 1))
    return ''


def clip(t):
    if len(t) <= LIMIT:
        return t
    out = ''
    for part in re.split(r'(?<=[。；])', t):
        if len(out) + len(part) > LIMIT:
            break
        out += part
    return out or t[:LIMIT]


def resolve(arg):
    """参数给 id（2026-10-07 / 2026-W39 / 2026-09），在 data/ 下递归找同名文件"""
    stem = arg[len('daily-'):] if arg.startswith('daily-') else \
           arg[len('weekly-'):] if arg.startswith('weekly-') else \
           arg[len('monthly-'):] if arg.startswith('monthly-') else arg
    hits = sorted(glob.glob(os.path.join(ROOT, 'data', '**', stem + '.json'), recursive=True))
    if len(hits) != 1:
        raise SystemExit(f'✗ data/ 下找不到唯一对应的 {stem}（命中 {len(hits)} 个）')
    return hits[0]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        raise SystemExit(__doc__)
    only_quick = '--all' not in sys.argv
    force = '--force' in sys.argv

    path = resolve(args[0])
    doc = json.load(open(path, encoding='utf-8'))
    n = 0
    for sec in doc['sections']:
        if only_quick and sec['name'] != '快讯':
            continue
        for it in sec['items']:
            if it.get('body') and not force:
                continue
            if not it.get('url'):
                continue
            desc = clip(fetch_desc(it['url']))
            if not desc:
                continue
            it['body'] = desc
            n += 1
            print(f'  {len(desc):>3}字 | {it["title"][:44]}')
            time.sleep(0.15)
    json.dump(doc, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'✓ {os.path.basename(path)}：补了 {n} 条')


if __name__ == '__main__':
    main()
