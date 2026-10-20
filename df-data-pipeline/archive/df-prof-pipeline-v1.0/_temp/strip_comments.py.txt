# -*- coding: utf-8 -*-
"""注释精简：每个 Lua 只保留**文件开头**的注释块，其余注释（整行 + 行尾）全部删除。

口径（2026-09-29 用户定）：
  「只需要保留每个 Lua 内开头的那点注释就够了」——中间的过程性/踩坑/决策注释
  全部删除（那些内容已经在项目记忆里，留在代码里没有意义）。

实现要点：
  · 真词法扫描（短串 / 长串 / 单行注释 / 长注释），不靠 `split('--')` ——
    否则字符串里的 `--` 会被误判。
  · 行尾风格原样保留（本仓库所有文件都是 CRLF）。
  · 头部块 = 从第 1 行起连续的空行 / 整行注释，直到第一个含代码的行；块内原样保留。
  · 删注释后产生的连续空行压成 1 个（视觉整洁）；文件末尾保留一个换行。

用法：
    python strip_comments.py --dry-run                 # 默认范围 = **仅生成物**（第七轮收口）
    python strip_comments.py --apply                   # 落盘（同上，只碰生成物）
    python strip_comments.py --dry-run Core Locales    # 目录会被过滤为其中的「生成物」
    python strip_comments.py --apply Core/Data/Data_Professions.lua   # 显式点名文件=有意为之，直接处理
    python strip_comments.py --selftest                # 入口守卫回归自检（只断言，不落盘）

★ 入口守卫（第七轮收口，2026-09-29）：本 CLI **默认不再扫「Core + Locales」全量**，
  而只处理「生成物」（文件头注释块含生成标记者，见 GEN_MARKERS）。手写件（界面/逻辑、
  手维护数据，以及并行会话的手改件与占位件）一律跳过 —— 杜绝「谁手动跑一次 --apply
  就把并行会话 WIP 的注释剥掉」的外溢。要处理非生成物，只能**显式点名该 .lua 文件**。
  ★ 含否定句的手写件先判否：手写 UI 件头部写「本文件不是生成物」，而 GEN_MARKERS 是子串
    匹配 ⇒ 会误命中；故 is_generated() **先判 GEN_NEG_MARKERS（不是生成物/非生成物），
    再判是**（Task #10 修，回归守卫见 --selftest）。
  ★ strip_text() 行为未改（其他调用方依赖）。

★★ 2026-10-17 口径升级（用户定：「我们插件不要带任何注释」）：
  插件内**一个注释都不留**（连文件头注释块一起删）。本模块相应提供
  strip_all_text() / strip_all_files() —— 生成器收尾钩子改用它们；
  全仓一次性清零与门禁用 strip_lua_comments.py / check_zero_comments.py。
  ⚠️ 头注释块被删 ⇒ 生成标记不复存在 ⇒ is_generated() 在仓库里恒为假，
     CLI 默认范围（仅生成物）随之扫不到文件；清理请直接用 strip_lua_comments.py。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def comment_spans(text):
    """返回 [(start, end), ...]：注释（含前导 --）在 text 里的字符区间。"""
    spans = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '-' and i + 1 < n and text[i + 1] == '-':
            j = i + 2
            end = None
            if j < n and text[j] == '[':
                k = j + 1
                eq = 0
                while k < n and text[k] == '=':
                    eq += 1
                    k += 1
                if k < n and text[k] == '[':
                    close = ']' + '=' * eq + ']'
                    e = text.find(close, k + 1)
                    end = n if e < 0 else e + len(close)
            if end is None:
                e = text.find('\n', i)
                end = n if e < 0 else e
            spans.append((i, end))
            i = end
            continue
        if c == '"' or c == "'":
            j = i + 1
            while j < n:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == c:
                    j += 1
                    break
                if text[j] == '\n':
                    break
                j += 1
            i = j
            continue
        if c == '[':
            k = i + 1
            eq = 0
            while k < n and text[k] == '=':
                eq += 1
                k += 1
            if k < n and text[k] == '[':
                close = ']' + '=' * eq + ']'
                e = text.find(close, k + 1)
                i = n if e < 0 else e + len(close)
                continue
        i += 1
    return spans


def strip_text(text):
    """返回 (新文本, 删除的注释行数, 删除的行尾注释数)。"""
    lf = text.replace('\r\n', '\n')
    spans = comment_spans(lf)
    starts = [s for s, _ in spans]

    def first_span_at(pos):
        """pos 是否落在某个注释区间内。"""
        lo, hi = 0, len(spans) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            s, e = spans[mid]
            if pos < s:
                hi = mid - 1
            elif pos >= e:
                lo = mid + 1
            else:
                return True
        return False

    # 每行的字符起点
    lines = lf.split('\n')
    line_start = []
    off = 0
    for ln in lines:
        line_start.append(off)
        off += len(ln) + 1

    kept = []          # 处理后的行
    comment_only = []  # 该行是否「整行注释」（用于头部块判定）
    tail_stripped = 0
    comment_lines = 0
    for idx, ln in enumerate(lines):
        base = line_start[idx]
        cut = None
        for col, ch in enumerate(ln):
            if first_span_at(base + col):
                cut = col
                break
        if cut is None:
            comment_only.append(False)
            kept.append(ln)
            continue
        prefix = ln[:cut].rstrip()
        if prefix == '':
            comment_only.append(True)
            kept.append(None)        # 整行注释：彻底删除
        else:
            comment_only.append(False)
            tail_stripped += 1
            kept.append(prefix)

    # ---- 头部块：从第 0 行起连续 空行/整行注释 ----
    head_end = 0
    for idx in range(len(lines)):
        s = lines[idx].strip()
        if s == '' or comment_only[idx]:
            head_end = idx + 1
        else:
            break
    # 头块末尾的空行不算进块（避免头块与正文间多一个空行）
    while head_end > 0 and lines[head_end - 1].strip() == '':
        head_end -= 1

    head = lines[:head_end]                      # 原样保留（不含尾部空行）

    # 正文：丢掉整行注释（None），原空行最多保留 1 个
    res = []
    pending_blank = 0
    for i in range(head_end, len(kept)):
        ln = kept[i]
        if ln is None:
            continue
        if ln.strip() == '':
            pending_blank += 1
            continue
        if pending_blank and res:
            res.append('')
        pending_blank = 0
        res.append(ln)

    out = list(head)
    if head and res:
        out.append('')

    text_out = '\n'.join(out + res).rstrip('\n') + '\n'
    if '\r\n' in text:
        text_out = text_out.replace('\n', '\r\n')

    for i in range(head_end, len(lines)):
        if comment_only[i]:
            comment_lines += 1
    return text_out, comment_lines, tail_stripped


def strip_all_text(text):
    """零注释口径：删掉**所有**注释（连文件头注释块一起），只留代码。

    与 strip_text 的唯一区别 = 不保留文件头注释块（2026-10-17：插件不带任何注释）。
    返回 (新文本, 删除的整行注释数, 删除的行尾注释数)。
    """
    lf = text.replace('\r\n', '\n')
    spans = comment_spans(lf)
    lines = lf.split('\n')
    line_start = []
    off = 0
    for ln in lines:
        line_start.append(off)
        off += len(ln) + 1

    def in_span(pos):
        lo, hi = 0, len(spans) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            s, e = spans[mid]
            if pos < s:
                hi = mid - 1
            elif pos >= e:
                lo = mid + 1
            else:
                return True
        return False

    out = []
    comment_lines = tail_stripped = 0
    for idx, ln in enumerate(lines):
        base = line_start[idx]
        cut = None
        for col, ch in enumerate(ln):
            if in_span(base + col):
                cut = col
                break
        if cut is None:
            out.append(ln)
            continue
        prefix = ln[:cut].rstrip()
        if prefix == '':
            comment_lines += 1
            continue
        tail_stripped += 1
        out.append(prefix)

    while out and out[0].strip() == '':
        out.pop(0)
    res = '\n'.join(out).rstrip('\n') + '\n'
    if '\r\n' in text:
        res = res.replace('\n', '\r\n')
    return res, comment_lines, tail_stripped


def strip_all_files(paths):
    """对给定 lua 文件/目录原地做「零注释」清理，返回改动文件数。"""
    n = 0
    for p in walk(paths):
        with open(p, 'rb') as f:
            raw = f.read()
        txt = raw.decode('utf-8')
        new, _c, _t = strip_all_text(txt)
        if new != txt:
            with open(p, 'wb') as f:
                f.write(new.encode('utf-8'))
            n += 1
    return n


def walk(paths):
    for p in paths:
        if os.path.isdir(p):
            for dp, _, fn in os.walk(p):
                for f in sorted(fn):
                    if f.endswith('.lua'):
                        yield os.path.join(dp, f)
        elif p.endswith('.lua'):
            yield p


# ---- 生成物判定 · CLI 入口守卫（第七轮收口）---------------------------------
# 本 CLI 只在「生成物」上工作：文件头注释块内含下列任一标记 ⇒ 该 Lua 由 _temp/ 生成器
# 写出；手写件（界面/逻辑、手维护数据，以及并行会话的手改件与占位件）不含标记 → 一律
# 跳过，杜绝「谁手动跑一次 --apply 就把并行会话 WIP 的注释剥掉」的外溢。
GEN_MARKERS = (
    '生成物', '请勿手改', '禁手改', '勿手改',
    'Generated by _temp', '由 _temp/', '產出',
)

# ★ 否定句守卫（2026-09-29，Task #10）：手写界面件的头部会明确写「本文件不是生成物」，
#   而 GEN_MARKERS 是**子串匹配** ⇒ '生成物' 会命中否定句；且「由 _temp/…生成，勿手改」
#   往往指向**数据文件**而非本文件（如 TierUI 指的是 Data_ClassTier/Data_ClassGuide）。
#   若不先判否，会把 5 个手写 UI 件（BisUI / ExploreUI / ProfessionUI / RaidUI / TierUI）
#   误判为生成物，默认 --apply 就会剥掉它们的注释 —— 正是本守卫要杜绝的外溢。
#   故「先判否，再判是」。
GEN_NEG_MARKERS = ('不是生成物', '非生成物')


def head_comment_block(path):
    """返回文件开头连续的注释/空行块文本（到第一行代码为止；纯读，不改文件）。"""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            head = []
            for line in f:
                s = line.strip()
                if s == '' or s.startswith('--'):
                    head.append(s)
                else:
                    break
            return '\n'.join(head)
    except OSError:
        return ''


def is_generated(path):
    """该 Lua 是否「生成物」（头部含生成标记、且未声明「不是生成物」）。"""
    head = head_comment_block(path)
    if any(n in head for n in GEN_NEG_MARKERS):
        return False
    return any(m in head for m in GEN_MARKERS)


# 入口守卫回归自检样本：(文件头注释, 期望是否生成物) —— 写临时文件判定，不依赖仓库现状。
# ★ 2026-10-17：插件改为「零注释」后，仓库里已不存在生成标记 ⇒ 原「拿真文件当样本」的
#   写法必然全判「手写件」而假红。改成自足样本，守卫本身仍在（判据逻辑没动）。
SELFTEST_CASES = (
    ('-- 无限副本手册 · 界面手写件', False),
    ('-- ★ 本文件由脚本生成，请勿手改 ★', True),
    ('-- 本文件不是生成物：手写数据', False),
    ('-- 本文件不是生成物，是手写件\n-- （另一份由 _temp/x.py 生成，勿手改）', False),
    ('-- Generated by _temp/foo.py', True),
    ('-- 繁體資料副本 · 生成物', True),
)


def selftest():
    """入口守卫回归自检：断言 is_generated() 对已知样本判对；失败非零退出。"""
    import tempfile
    bad = 0
    for head, want in SELFTEST_CASES:
        fd, p = tempfile.mkstemp(suffix='.lua')
        os.close(fd)
        try:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(head + '\n\nlocal _, ns = ...\n')
            got = is_generated(p)
        finally:
            os.remove(p)
        if got != want:
            bad += 1
        print('  [%s] %-46s 期望=%s 实得=%s' % (
            'OK ' if got == want else 'FAIL', head.replace('\n', ' / ')[:46],
            '生成物' if want else '手写件', '生成物' if got else '手写件'))
    print('-' * 78)
    print('selftest：%d 项，%s' % (len(SELFTEST_CASES), '全部通过' if not bad else '判错 %d 项' % bad))
    return 1 if bad else 0


def main():
    argv = sys.argv[1:]
    if '--selftest' in argv:          # ★ 入口守卫回归自检：只跑断言，不落盘、不扫目录
        return selftest()
    apply = '--apply' in argv
    args = [a for a in argv if not a.startswith('--')]

    explicit_files = []          # 显式点名的 .lua 文件：直接处理（用户有意为之）
    scan_roots = []              # 目录/默认范围：只收其中的「生成物」
    if args:
        for a in args:
            p = a if os.path.isabs(a) else os.path.join(ROOT, a)
            if os.path.isfile(p) and p.endswith('.lua'):
                explicit_files.append(p)
            else:
                scan_roots.append(p)
    else:
        # ★ 第七轮收口：默认目标不再 =「Core + Locales」全量（会外溢到并行会话手写件），
        #   改为「仅生成物」——目录展开后再用 is_generated 过滤。
        scan_roots = [os.path.join(ROOT, 'Core'), os.path.join(ROOT, 'Locales')]

    targets, skipped = list(explicit_files), []
    seen = set(explicit_files)
    for p in walk(scan_roots):
        if p in seen:
            continue
        seen.add(p)
        (targets if is_generated(p) else skipped).append(p)

    print('范围：生成物 %d 个；已跳过非生成物 %d 个（手写件/占位，不扫）'
          % (len(targets), len(skipped)))

    tot_lines = tot_cmt = tot_tail = 0
    for p in targets:
        with open(p, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8')
        new, cmt, tail = strip_text(text)
        if new == text:
            continue
        old_n = text.count('\n')
        new_n = new.count('\n')
        tot_lines += old_n - new_n
        tot_cmt += cmt
        tot_tail += tail
        rel = os.path.relpath(p, ROOT).replace('\\', '/')
        print('  %-40s -%3d 行（整行注释 %d / 行尾注释 %d）' % (rel, old_n - new_n, cmt, tail))
        if apply:
            with open(p, 'wb') as f:
                f.write(new.encode('utf-8'))
    print('-' * 78)
    print('%s：整行注释 %d 行 + 行尾注释 %d 处，共减少 %d 行' %
          ('已落盘' if apply else '（dry-run 未落盘）', tot_cmt, tot_tail, tot_lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
