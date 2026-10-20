# -*- coding: utf-8 -*-
"""专业页数据 · 一键流水线：抓取 → 解析 → 字段审计 → 文案对账 → 生成 → CSV 合并 → 专精。

为什么要有这么一层：这四步各自可单独跑，但**顺序有硬依赖** ——
  · 解析产出的键名改了，生成器的字段序就得跟着改（fc_fields.py 抓这个）；
  · 数据源加了新文案，对照表就少一条（fc_i18n.py --audit 抓这个）。
手工按顺序敲四条命令，漏掉中间那条就是「全绿但数据静默变旧」，所以串成一条。

两种模式控制生成的 Lua 与合并 CSV 是否落盘：

    python fc_update.py --check    # 只抓+解析+审计，不碰 Core/Data（看有没有变化）
    python fc_update.py --apply    # 落盘生成 Data_Prof*.lua、物品与训练师专精 CSV
    python fc_update.py --apply --offline   # 不联网，用缓存重放（回归/离线环境）

默认走网络；`--offline` 用 _fc/cache/ 和已有 CSV 重放。
Wowhead 专精页面单独遵守缓存与限流策略，不随 fc_fetch 的 --force 强制刷新。
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
    ('合并物品 CSV 与更新商人数据', ['fc_prof_items.py'], {'--dry-run': 'no-apply'}),
    ('合并配方学习专精', ['fc_prof_specializations.py'],
     {'--dry-run': 'no-apply', '--offline': True}),
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


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    FAILED.clear()
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true',
                      help='把生成结果落盘到 Core/Data 与 _fc/data（默认只 dry-run）')
    mode.add_argument('--check', action='store_true',
                      help='只检查生成结果，不写入 Lua 或合并 CSV（默认模式）')
    ap.add_argument('--offline', action='store_true',
                    help='不联网，用 _fc/cache 里的旧页面重放')
    ap.add_argument('--vendors-csv', type=os.path.abspath,
                    help='商人报价 CSV（相对调用目录），转发给 fc_prof_items.py')
    ap.add_argument('--npcs-csv', type=os.path.abspath,
                    help='NPC 定位 CSV（相对调用目录），转发给 fc_prof_items.py')
    ap.add_argument('--prices-csv', type=os.path.abspath,
                    help='物品基础购买价 CSV（相对调用目录），转发给 fc_prof_items.py')
    ap.add_argument('--verified-at', help='兼容日期校验，转发给 fc_prof_items.py；不输出该字段')
    ap.add_argument('--recipe-items-csv', type=os.path.abspath,
                    help='客户端图纸专精 CSV，转发给 fc_prof_specializations.py')
    ap.add_argument('--trainer-csv', type=os.path.abspath,
                    help='训练师专精 CSV 输入/输出路径，转发给 fc_prof_specializations.py')
    ap.add_argument('--specialization-cache-dir', type=os.path.abspath,
                    help='Wowhead 专精页面缓存目录，转发为 --cache-dir')
    ap.add_argument('--specialization-output-lua', type=os.path.abspath,
                    help='独立专精 Lua 输出路径，转发为 --output-lua')
    ap.add_argument('--specialization-build',
                    help='目标客户端完整 Build；独立更新时必须匹配实际导出版本，转发为 --build')
    ap.add_argument('--refresh-trainers', action='store_true',
                    help='显式刷新训练师页面缓存；仍遵守请求间隔、robots 和冷却限制')
    ap.add_argument('--specializations-only', action='store_true',
                    help='独立更新价格/图纸快照、学习专精和审计；整批校验成功后发布，适合重复运行')
    ap.add_argument('--specialization-cache-root', type=os.path.abspath,
                    help='独立更新入口的缓存根目录（含 DB2 快照和运行状态）')
    ap.add_argument('--specialization-data-dir', type=os.path.abspath,
                    help='独立更新入口的 prof_*.json 目录')
    ap.add_argument('--item-csv', type=os.path.abspath,
                    help='独立更新入口的原始 Item CSV 路径')
    ap.add_argument('--tool-directory', type=os.path.abspath,
                    help='独立更新入口的 wow.tools.local 安装目录')
    ap.add_argument('--base-url', help='独立更新入口的 wow.tools.local 回环 HTTP 地址')
    ap.add_argument('--db2-dir', type=os.path.abspath,
                    help='独立更新离线重放时显式指定既有 DB2 快照')
    ap.add_argument('--refresh-catalog', action='store_true',
                    help='独立更新时刷新 wuxianwow 配方目录缓存')
    ap.add_argument('--skip-recipe-catalog', action='store_true',
                    help='独立更新时省略可选 wuxianwow 目录交叉核对')
    args = ap.parse_args(argv)

    if args.specializations_only:
        extra = ['--apply' if args.apply else '--check']
        for flag in ('offline', 'refresh_trainers', 'refresh_catalog'):
            if getattr(args, flag):
                extra.append('--' + flag.replace('_', '-'))
        if args.skip_recipe_catalog:
            extra.append('--skip-catalog')
        for key, option in (
            ('prices_csv', '--prices-csv'), ('item_csv', '--item-csv'),
            ('recipe_items_csv', '--recipe-items-csv'), ('trainer_csv', '--trainer-csv'),
            ('specialization_cache_dir', '--wowhead-cache-dir'),
            ('specialization_cache_root', '--cache-root'),
            ('specialization_data_dir', '--data-dir'),
            ('specialization_output_lua', '--output-lua'), ('specialization_build', '--build'),
            ('tool_directory', '--tool-directory'), ('base_url', '--base-url'), ('db2_dir', '--db2-dir'),
        ):
            if getattr(args, key) is not None:
                extra.extend([option, getattr(args, key)])
        return 1 if run('更新配方专精与审计', ['fc_refresh_specializations.py'], extra) else 0

    only_options = ('specialization_cache_root', 'specialization_data_dir', 'item_csv',
                    'tool_directory', 'base_url', 'db2_dir', 'refresh_catalog', 'skip_recipe_catalog')
    if any(getattr(args, key) for key in only_options):
        ap.error('这些更新选项需要 --specializations-only')

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
        if argv[0] == 'fc_prof_items.py':
            for key in ('vendors_csv', 'npcs_csv', 'prices_csv', 'verified_at'):
                value = getattr(args, key)
                if value is not None:
                    extra.extend(['--' + key.replace('_', '-'), value])
        if argv[0] == 'fc_prof_specializations.py':
            for key, option in (
                ('recipe_items_csv', '--recipe-items-csv'),
                ('trainer_csv', '--trainer-csv'),
                ('specialization_cache_dir', '--cache-dir'),
                ('specialization_output_lua', '--output-lua'),
                ('specialization_build', '--build'),
            ):
                value = getattr(args, key)
                if value is not None:
                    extra.extend([option, value])
            if args.refresh_trainers:
                extra.append('--refresh-trainers')
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
