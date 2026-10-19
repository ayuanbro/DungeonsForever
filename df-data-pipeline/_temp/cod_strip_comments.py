# -*- coding: utf-8 -*-
"""批量清理 Data_DungeonQuests.lua 的 q[12] 任务注释（2026-10-08 用户红线）：

- 不出现 npc=xxx / 任务 ID / 物品 ID（UI 任务详情已有）
- 不出现奖励选项 / 声望收获描述（UI 已有）
- 不出现来源溯源语句：fc 口径 / wowhead 实锤 / Forever 新任务（wowhead 永久库数据）等
只动 q[12]，q[11] 目标、q[5]/q[17] 名字、q[6] 地点、q[18] 收获一律不碰。

用法：--dry 只打印报告；--apply 写回数据文件并同步改写 enus_data*.py 翻译表的键/值。
"""
import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'Core', 'Data', 'Data_DungeonQuests.lua')

# ---------------------------------------------------------------- 字段解析
def split_fields(line):
    """按顶层逗号切分一行 `{ ... },` 的字段，返回 [(text, start, end)]。"""
    assert line.lstrip().startswith('{')
    fields, depth, i, n = [], 0, 0, len(line)
    start = line.index('{') + 1
    i = start
    in_str = False
    quote = ''
    while i < n:
        c = line[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                in_str = False
            i += 1
            continue
        if c in '"\'':
            in_str = True
            quote = c
        elif c in '{([':
            depth += 1
        elif c in '})]':
            depth -= 1
        elif c == ',' and depth == 0:
            fields.append((line[start:i], start, i))
            start = i + 1
        i += 1
    fields.append((line[start:i], start, i))
    return fields


def unquote(text):
    text = text.strip()
    if text.startswith('"') and text.endswith('"'):
        body = text[1:-1]
        return body.replace('\\"', '"').replace('\\\\', '\\')
    return None


def quote(body):
    return '"' + body.replace('\\', '\\\\').replace('"', '\\"') + '"'


# ---------------------------------------------------------------- 中文清理
def tidy_zh(s):
    s = re.sub(r'[ \t]{2,}', ' ', s)
    for _ in range(3):
        s = (s.replace('（）', '').replace('（，', '（').replace('，）', '）')
              .replace('（。', '（').replace('。）。', '）。').replace('（）', '')
              .replace('，，', '，').replace('；；', '；').replace('。。', '。')
              .replace('，。', '。').replace('；。', '。').replace('、。', '。')
              .replace('：。', '。').replace('◎：', '◎ ').replace('：）', '）')
              .replace(' ——。', '。').replace('，。', '。'))
    s = re.sub(r'^[，；、。 ]+', '', s)
    s = re.sub(r' 。', '。', s)
    s = re.sub(r'（ ）', '', s)
    s = s.replace('，◎', '。◎ ').replace('；◎', '。◎ ')
    s = s.replace('、疑为', '，疑为')
    return s.strip()


def strip_zh(s):
    # ── 溯源语句（用户红线）──
    s = s.replace('◎ Forever 新任务（wowhead 永久库数据）：', '')
    s = s.replace('◎ Forever 新任务（wowhead 永久库数据）', '')
    s = s.replace('Forever 新任务（wowhead 永久库数据）', '')
    s = s.replace('fc 口径：', '').replace('fc 口径:', '')
    s = s.replace('，fc 标注莫高雷', '')
    s = s.replace('fc 标注', '')
    s = re.sub(r'fc 在[^。]*。', '', s)
    s = s.replace('（fc 未公布具体首领名）', '')
    s = s.replace('wowhead 实锤', '')
    s = s.replace('与 Wowhead 表格口径矛盾', '与站点表格口径矛盾')
    s = s.replace('；wowhead 尚未收录其 NPC ID 与确切位置，待实机核实', '，确切位置待实机核实')
    s = s.replace('wowhead 未列奖励。', '')
    s = s.replace('（wowhead 实锤，Forever 定制 NPC、无官方中文名）', '')
    s = re.sub(r'（，?Forever 定制 NPC、无官方中文名）', '', s)
    s = s.replace('，wowhead 已核实', '')
    # ── 自译备注 ──
    s = s.replace('；任务名无官方中文，自译', '')
    s = s.replace('任务名自译，', '')
    s = s.replace('（Rexxie Copperclutch，名字自译）', '')
    s = s.replace('（名字自译）', '')
    s = s.replace('，名字自译', '')
    # ── ID 引用 ──
    s = re.sub(r'（npc=\d+）', '', s)
    s = re.sub(r'[ ]?npc=\d+', '', s)
    s = re.sub(r'（#\d+）', '', s)
    s = re.sub(r'#\d+', '', s)
    s = re.sub(r'（\d{3,7}）', '', s)
    s = re.sub(r'\((\d{3,7})\)', '', s)
    s = re.sub(r'（\d{3,7}，', '（', s)
    s = re.sub(r'，\d{3,7}）', '）', s)
    s = re.sub(r'，\d{3,7}，', '，', s)
    # ── 奖励 / 声望句（UI 已有）──
    s = re.sub(r'奖励[二三四]选一[：:][^。]*。', '', s)
    s = re.sub(r'[二三四]选一奖励。', '', s)
    s = re.sub(r'，[^。；]*二选一。', '。', s)
    s = re.sub(r'。[^。；]*二选一。', '。', s)
    s = re.sub(r'披风二选一。', '', s)
    s = re.sub(r'收获 ?\d+ ?点?[^。]*声望。', '', s)
    s = re.sub(r'每一步上交还给 ?\d+ ?点[^。]*声望。', '', s)
    s = re.sub(r'奖励含烹饪食谱。', '', s)
    s = s.replace('（Forever 定制 NPC、无官方中文名）', '')
    return tidy_zh(s)


# ---------------------------------------------------------------- 英文清理
def tidy_en(s):
    s = re.sub(r'[ \t]{2,}', ' ', s)
    s = re.sub(r'\(\s*,\s*', '(', s)
    s = re.sub(r',\s*\)', ')', s)
    s = re.sub(r'\(\s*\)', '', s)
    for _ in range(2):
        s = (s.replace(';;', ';').replace(' ,', ',').replace(' .', '.')
              .replace('..', '.').replace(';.', '.').replace(',.', '.'))
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'([.!?]) ([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), s)
    return s.strip()


def strip_en(s):
    s = re.sub(r'\s*\(\s*npc[= ]\d+\s*\)', '', s)
    s = re.sub(r'\s*\bnpc[= ]\d+', '', s)
    s = re.sub(r'\(#\d+\)', '', s)
    s = re.sub(r'#\d+', '', s)
    s = re.sub(r'\((\d{3,7})\)', '', s)
    s = re.sub(r'(?<=[（(])\d{3,7},\s*', '', s)      # (92432, ...) style leftovers
    s = re.sub(r'[^.!?]*[Cc]hoose one of (two|three)[^.!?]*\.', '', s)
    s = re.sub(r'[^.!?]*\b[Gg]rants? \d+ [^.!?]*reputation\.', '', s)
    s = s.replace('Forever-new quest (wowhead Forever DB data):', '')
    s = s.replace('Forever-new quest (wowhead Forever DB data).', '')
    s = s.replace('Forever-new quest (wowhead Forever DB data)', '')
    s = s.replace('wowhead confirmed start & end are the same NPC',
                  'start & end confirmed to be the same NPC')
    s = re.sub(r'\(wowhead confirmed, Forever custom NPC with no official CN name\)', '', s)
    s = s.replace('Per fc, the giver', 'The giver')
    s = s.replace('; wowhead has no NPC id or exact location yet — pending in-game check',
                  ' — exact location pending in-game check')
    s = s.replace(' (self-translated name)', '')
    s = s.replace(' (self-translated title)', '')
    s = s.replace(', self-translated title', '')
    s = s.replace(' per fc', '')
    s = re.sub(r'\(fc does not name it\)', '', s)
    s = re.sub(r'fc lists[^.]*\.', '', s)
    s = re.sub(r'No reward choices listed on [^.]*\.', '', s)
    return tidy_en(s)


# ---------------------------------------------------------------- 主流程
def iter_entries(src):
    """yield (entry_text, start_offset)，支持一条条目跨多行（按括号配平聚合）。"""
    lines = src.split('\n')
    pos = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^ +\{ \d+,', line):
            start = pos
            buf = [line]
            depth = _max_depth_balance(line)
            while depth > 0 or not buf[-1].rstrip().endswith('},'):
                i += 1
                pos += len(line) + 1
                line = lines[i]
                buf.append(line)
                depth += _max_depth_balance(line)
            text = '\n'.join(buf)
            yield text, start
            pos += len(line) + 1
        else:
            pos += len(line) + 1
        i += 1


def _max_depth_balance(line):
    """相对条目最外层 { 的括号净增量（忽略字符串字面量内部）。"""
    depth = 0
    in_str = False
    quote = ''
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if in_str:
            if c == '\\':
                i += 2
                continue
            if c == quote:
                in_str = False
        elif c in '"\'':
            in_str = True
            quote = c
        elif c in '{(':
            depth += 1
        elif c in '})':
            depth -= 1
        i += 1
    return depth


def main():
    apply_mode = '--apply' in sys.argv
    src = io.open(DATA, encoding='utf-8').read()
    changes = []          # (old, new)
    problems = []
    spans = []            # (start, end, replacement)
    for line, off in iter_entries(src):
        fields = split_fields(line)
        if len(fields) != 18:
            problems.append('字段数 %d: %s...' % (len(fields), line[:80]))
            continue
        raw = fields[11][0]
        body = unquote(raw)
        if body is None:
            if raw.strip() != 'nil':
                problems.append('q12 非字符串非 nil: %s...' % line[:80])
            continue
        new = strip_zh(body)
        if new == body:
            continue
        changes.append((body, new))
        new_line = line[:fields[11][1]] + quote(new) + line[fields[11][2]:]
        spans.append((off, off + len(line), new_line))

    spans.sort()
    out, prev = [], 0
    for a, b, rep in spans:
        out.append(src[prev:a])
        out.append(rep)
        prev = b
    out.append(src[prev:])
    out = ''.join(out)

    print('== 变更 %d 条 / 问题 %d ==' % (len(changes), len(problems)))
    for p in problems:
        print('!!', p)
    for old, new in changes:
        print('-' * 60)
        print('旧:', old)
        print('新:', new)

    # 残留体检（对新注释全集）
    leftovers = []
    for line, _ in iter_entries(out):
        fields = split_fields(line)
        if len(fields) != 18:
            continue
        body = unquote(fields[11][0])
        if body is None:
            continue
        for pat in ('npc=', 'fc', 'FC', 'wowhead', 'Wowhead', 'Forever 新任务',
                    '选一', '#'):
            if pat in body:
                leftovers.append((pat, body[:70]))
                break
    print('== 残留 %d ==' % len(leftovers))
    for pat, frag in leftovers:
        print('!! [%s] %s' % (pat, frag))

    if apply_mode and not problems:
        io.open(DATA, 'w', encoding='utf-8', newline='').write(out)
        import json
        json.dump(changes, io.open(os.path.join(os.path.dirname(DATA), '..', '_temp',
                                                'cod_comment_changes.json'), 'w',
                                   encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写回', DATA)
    elif apply_mode:
        print('存在问题，未写回')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
