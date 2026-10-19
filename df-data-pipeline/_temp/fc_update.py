# -*- coding: utf-8 -*-
"""专业页数据 · 一键流水线：抓取 → 解析 → 字段审计 → 文案对账 → 生成。

为什么要有这么一层：这四步各自可单独跑，但**顺序有硬依赖** ——
  · 解析产出的键名改了，生成器的字段序就得跟着改（fc_fields.py 抓这个）；
  · 数据源加了新文案，对照表就少一条（fc_i18n.py --audit 抓这个）。
手工按顺序敲四条命令，漏掉中间那条就是「全绿但数据静默变旧」，所以串成一条。

两种模式的区别只在**最后一步落不落盘**：

    python fc_update.py --check    # 只抓+解析+审计，不碰 Core/Data（看有没有变化）
    python fc_update.py --apply    # 落盘生成 4 个 Data_Prof*.lua
    python fc_update.py --apply --offline   # 不联网，用缓存重放（回归/离线环境）

默认走网络；`--offline` 用 _fc/cache/ 里的旧页面重放（结果完全可重复）。
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

STEPS = [
    ('抓取 14 个页面', ['fc_fetch.py'], {'--offline': True}),
    ('RSC → 归一化 JSON', ['fc_parse.py'], {}),
    # 区域名 → AreaTable ID（产物里不落区域名；客户端拿中文名）。排在生成之前，
    # 且离线重放时用缓存表 —— 否则「离线跑一遍」会因为没网而拿不到对照表。
    ('区域名 → AreaTable ID', ['fc_zones.py'], {'--offline': True}),
    ('字段覆盖审计', ['fc_fields.py', '--strict'], {}),
    ('文案对照表对账', ['fc_i18n.py', '--audit'], {}),
    ('生成 Core/Data/Data_Prof*.lua', ['fc_gen.py'], {'--dry-run': 'no-apply'}),
    ('生成后复检', ['fc_fields.py', '--strict'], {}),
]

FAILED = []


def run(label, argv, extra=()):
    cmd = [PY, os.path.join(HERE, argv[0])] + list(argv[1:]) + list(extra)
    # 子进程直写同一个 stdout，父进程不 flush 的话自己的行会跑到子进程输出后面
    print()
    print('── %s  %s' % (label, os.path.basename(argv[0])), flush=True)
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        FAILED.append('%s（exit=%d）' % (label, r.returncode))
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='把生成结果落盘到 Core/Data（默认只 dry-run）')
    ap.add_argument('--offline', action='store_true',
                    help='不联网，用 _fc/cache 里的旧页面重放')
    args = ap.parse_args()

    print('=== 专业页数据流水线（%s / %s）==='
          % ('落盘' if args.apply else '仅检查', '离线重放' if args.offline else '联网抓取'),
          flush=True)

    for label, argv, opt in STEPS:
        extra = []
        if opt.get('--offline') and args.offline:
            extra.append('--offline')
        # ★ 联网模式的抓取步骤必须 --force：fc_fetch 对已缓存页默认跳过，
        #   不强制重抓的话「与站点对比」就是对着旧缓存自说自话 —— 2026-10-09
        #   踩实过：站点 build 69913→70245 全专业路线重排，旧流程却报「无变化」。
        if label.startswith('抓取') and not args.offline:
            extra.append('--force')
        if opt.get('--dry-run') and not args.apply:
            extra.append('--dry-run')
        if run(label, argv, extra) != 0 and FAILED:
            break        # 前一步失败就别往下跑：后面几步的结果没有意义

    # ★ 收尾：生成物不留任何注释（2026-10-17 用户定：插件不带任何注释）。
    #   --apply 才有新文件落盘；dry-run 模式跳过。
    if args.apply and not FAILED:
        run('注释零容忍（生成物不留任何注释）', ['strip_lua_comments.py', '--apply'])

    print()
    if FAILED:
        print('[FAIL] ' + '；'.join(FAILED))
        return 1
    if not args.apply:
        print('[OK] 全链路通过（未落盘）。确认无误后跑 --apply 写入 Core/Data')
    else:
        print('[OK] 全链路通过且已落盘。接着跑回归：')
        print('     python mk_df_check.py && python mk_df_mut.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
