#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 data/ 下所有期数是否合规，并打印时间线概况。

    python3 tools/check.py

检查项：
  · 文件名 = id，kind 合法
  · 必备字段齐不齐
  · 每个 section 有 name/num/items；每个 item 有 title
  · catalog.json 里登记的 id，是否有对应 JSON（没写的是「待生成」，不算错）
  · data/ 里有 JSON 但没登记的（会提示，因为界面上看不到）
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
KIND = {'daily', 'weekly', 'monthly'}
REQUIRED = ('kind', 'id', 'masthead', 'dateline', 'brief', 'briefLabel',
            'lead', 'sections', 'footer')
ID_RE = re.compile(r'^(?:\d{4}-\d{2}-\d{2}|\d{4}-W\d{2}|\d{4}-\d{2})$')

errs, warns = [], []


def check_doc(path):
    name = os.path.basename(path)
    try:
        d = json.load(open(path, encoding='utf-8'))
    except json.JSONDecodeError as e:
        return errs.append(f'{name}: JSON 解析失败 —— {e}')
    for k in REQUIRED:
        if k not in d:
            errs.append(f'{name}: 缺字段 {k}')
    if d.get('kind') not in KIND:
        errs.append(f'{name}: kind 必须是 {sorted(KIND)}')
    if os.path.splitext(name)[0] != d.get('id'):
        errs.append(f'{name}: 文件名与 id（{d.get("id")}）不一致')
    if not ID_RE.match(str(d.get('id', ''))):
        errs.append(f'{name}: id 格式应为 2026-10-07 / 2026-W39 / 2026-09')
    L = d.get('lead') or {}
    if not L.get('title'):
        errs.append(f'{name}: lead.title 为空')
    if not L.get('paragraphs'):
        warns.append(f'{name}: lead.paragraphs 为空，头条会显得很单薄')
    if not d.get('brief'):
        warns.append(f'{name}: brief 为空，导读栏不会显示')
    for i, s in enumerate(d.get('sections') or []):
        if not s.get('name') or not s.get('items'):
            errs.append(f'{name}: sections[{i}] 缺 name 或 items')
        for it in s.get('items') or []:
            if not it.get('title'):
                errs.append(f'{name}: sections[{i}] 有条目缺 title')
    d['_file'] = name
    return d


def main():
    docs = {}
    paths = sorted(p for p in glob.glob(os.path.join(DATA, '*.json'))
                   if os.path.basename(p) != 'catalog.json')
    for p in paths:
        d = check_doc(p)
        if isinstance(d, dict):
            docs[d['id']] = d

    cat_path = os.path.join(DATA, 'catalog.json')
    if not os.path.exists(cat_path):
        errs.append('缺 data/catalog.json')
        cat = {'timeline': []}
    else:
        cat = json.load(open(cat_path, encoding='utf-8'))
        for e in cat.get('timeline', []):
            if e.get('kind') not in KIND:
                errs.append(f'catalog: {e.get("id")} 的 kind 非法')
            if not ID_RE.match(str(e.get('id', ''))):
                errs.append(f'catalog: id 格式不合法 {e.get("id")}')
    registered = {e['id'] for e in cat.get('timeline', [])}
    for i in docs:
        if i not in registered:
            warns.append(f'{i}: 有 JSON 但没在 catalog.json 登记，界面上看不到')

    by_kind = {k: ([e for e in cat.get('timeline', []) if e['kind'] == k]) for k in ('daily', 'weekly', 'monthly')}
    order = {'daily': 0, 'weekly': 1, 'monthly': 2}
    print('时间线：')
    for k in sorted(by_kind, key=lambda x: order[x]):
        items = sorted(by_kind[k], key=lambda e: e['id'], reverse=True)
        n = sum(1 for e in items if e['id'] in docs)
        span = f'{items[-1]["id"]} … {items[0]["id"]}' if items else '（空）'
        print(f'  {k:8s} {n}/{len(items)} 已生成   登记范围 {span}')
    for w in warns:
        print('  ! ' + w)
    for e in errs:
        print('  ✗ ' + e)
    print(f'\n共 {len(docs)} 份 JSON，{len(errs)} 个错误，{len(warns)} 个提醒')
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
