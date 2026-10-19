# -*- coding: utf-8 -*-
"""注释红线检查：只扫注释（行注释 + 长块注释），命中其他插件 / 外部项目名即 FAIL。

依据 AGENTS.md「注释纪律」：注释里永远不写任何其他插件 / 外部项目名
（集成功能在注释里只能写泛称；代码标识符与 L[] 界面文案不受此限）。

范围 = 打包集（toc + Core/**.lua + Locales/*.lua）。Libs/ 不扫：
第三方库版权头与注册名必须原样保留（AGENTS.md 明文豁免）。

用法：
  python check_comment_redline.py          # 全量扫，命中 exit=1
  python check_comment_redline.py <file>   # 只扫单个文件
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ★ 红线词表（注释中禁止）：其他插件 / 外部项目名 + 站点措辞。
#   注意：Auctionator / BiaoGe 等作为**代码标识符**出现不在本检查范围（本脚本只看注释）。
FORBIDDEN = [
    "BiaoGe", "Lootified", "Ranker", "YUI", "EllesmereUI", "Auctionator",
    "TalentsForever", "foreverchanges", "AtlasQuest", "nfu",
    "Icy-Veins", "icy-veins", "warcrafttavern", "indiekings", "MageBookTracker",
    "wuxianwow", "无限图鉴",
    "站点",
]
# 放行短语（良性否定句，如「零站点回退」——说明运行期不从数据站取数）。
ALLOW = ("零站点回退",)

LINE_RE = re.compile(
    "|".join(re.escape(w) for w in FORBIDDEN))


def scan_text(text, label, hits):
    """逐字符小状态机：只把『注释』内容按行送检，字符串/长字符串一律跳过（防误报）。"""
    i, n, line = 0, len(text), 1
    state = "code"  # code | lcomment | block | dq | sq | lstr
    level = 0        # 长括号级别 [--[==[ / [==[
    mark = 0
    while i < n:
        c = text[i]
        if c == "\n":
            if state == "lcomment":
                hits.append((label, line, text[mark:i]))
                state = "code"
            line += 1
            i += 1
            continue
        if state == "code":
            if text.startswith("--", i):
                m = re.match(r"--\[(=*)\[", text[i:])
                if m:
                    state, level, mark = "block", len(m.group(1)), i + m.end()
                    i += m.end()
                else:
                    state, mark = "lcomment", i + 2
                    i += 2
            elif c == '"':
                state, i = "dq", i + 1
            elif c == "'":
                state, i = "sq", i + 1
            else:
                m = re.match(r"\[(=*)\[", text[i:]) if c == "[" else None
                if m:
                    state, level, i = "lstr", len(m.group(1)), i + m.end()
                else:
                    i += 1
        elif state == "lcomment":
            i += 1
        elif state == "block":
            m = re.match(r"\]%s\]" % ("=" * level), text[i:])
            if m:
                state, i = "code", i + m.end()
            else:
                i += 1
        elif state in ("dq", "sq"):
            if c == "\\":
                i += 2
            elif (state == "dq" and c == '"') or (state == "sq" and c == "'"):
                state, i = "code", i + 1
            else:
                i += 1
        elif state == "lstr":
            m = re.match(r"\]%s\]" % ("=" * level), text[i:])
            if m:
                state, i = "code", i + m.end()
            else:
                i += 1
    if state == "lcomment":  # 文件尾行注释无换行
        hits.append((label, line, text[mark:]))


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [os.path.join(ROOT, TOC := "DungeonsForever.toc")]
        for sub in ("Core", "Locales"):
            files += glob.glob(os.path.join(ROOT, sub, "**", "*.lua"), recursive=True)
        files = sorted(set(files))
    hits = []
    for p in files:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                scan_text(f.read(), os.path.relpath(p, ROOT), hits)
        except OSError as e:
            print("!! 读不了 %s: %s" % (p, e))
            return 2
    bad = []
    for label, ln, seg in hits:
        m = LINE_RE.search(seg)
        if m and not any(a in seg for a in ALLOW):
            bad.append((label, ln, m.group(0), seg.strip()[:110]))
    if bad:
        print("[FAIL] 注释红线命中 %d 处：" % len(bad))
        for label, ln, word, seg in bad:
            print("  %s:%d  [%s]  %s" % (label, ln, word, seg))
        return 1
    n = len(hits)
    print("[OK] 注释红线 0 命中（扫注释行 %d 处 / %d 文件）" % (n, len(files)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
