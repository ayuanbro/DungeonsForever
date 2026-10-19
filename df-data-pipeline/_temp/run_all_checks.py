# -*- coding: utf-8 -*-
"""掉落过滤 / 副本页 · 统一离线回归入口。

一条命令依次跑下列离线校验，任一失败 → 整体非零退出：
    1. qa_lf_verify.py        掉落过滤独立验证（LootFilter / LootFilterUI / LootFilterData）
    2. df_dungeon_check.py    副本页 harness 全量断言
    3. _qa_probe_spec.py      职业指南页 · 专精指南定向探针（动态行为 + 源码静态闸）
    4. strip_comments.py      生成物/手写件判定入口守卫自检（--selftest）
    5. df_mut_check.py        副本页 harness 变异验证（证明断言非恒真）
    6. _prof_residual_probe.py 专业页 · 切页残留探针（购物清单→路线，走真分帧窗口）
    7. _prof_rowsig_probe.py   专业页 · 行内可视签名探针（跨页签回来是否留残影/卡片）
    8. _prof_rowhole_probe.py  专业页 · 行池丢行清场探针（「末行建帧失败 ⇒ #PD.rows 提前截断」）
    9. _prof_wipe_probe.py     专业页 · 切页/同页收窄「内容除净」探针（越界行不许挂着上一批内容）

用法（任选其一，工作目录随之固定为脚本所在 _temp/）：
    python run_all_checks.py
    <python> D:\\workspace\\DungeonsForever\\_temp\\run_all_checks.py

退出码：0 = 全过；1 = 至少一项失败。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python"

# (脚本名（不含 .py）, 用途说明, 额外命令行参数)
CHECKS = [
    ("qa_lf_verify", "掉落过滤独立验证（LootFilter / LootFilterUI / LootFilterData）", ()),
    ("df_dungeon_check", "副本页 harness 全量断言", ()),
    ("qa_prof_split", "专业配方数据分片化守卫（惰性 + 分片预热）", ()),
    ("_qa_probe_spec", "职业指南页 · 专精指南定向探针（动态行为 + 源码静态闸）", ()),
    ("strip_comments", "生成物/手写件判定入口守卫自检", ("--selftest",)),
    ("check_zero_comments", "注释零容忍：打包集不许有任何 lua 注释", ()),
    ("df_mut_check", "副本页 harness 变异验证（证明断言非恒真）", ()),
    ("_prof_residual_probe", "专业页 · 切页残留探针（购物清单→路线，走真分帧窗口）", ()),
    ("_prof_rowsig_probe", "专业页 · 行内可视签名探针（跨页签回来是否留残影/卡片）", ()),
    ("_prof_rowhole_probe", "专业页 · 行池丢行清场探针（末行建帧失败 ⇒ #PD.rows 提前截断）", ()),
    ("_prof_wipe_probe", "专业页 · 切页/同页收窄「内容除净」探针（越界行不许挂着上一批内容）", ()),
    ("_prof_trainer_recipe_probe", "专业页 · 训练师板/配方「全部」页签动态渲染探针（含 and-nil-or 红线扫描）", ()),
    ("_dbg_trainer_vis", "专业页 · 训练师板真机视口模式探针（强制 vis=true + root 尺寸断言）", ()),
]


def run_one(name, desc, args, env):
    path = os.path.join(HERE, name + ".py")
    print("=" * 72)
    print("▶ %s —— %s" % (name, desc))
    print("=" * 72)
    if not os.path.isfile(path):
        print("!! 缺少脚本：%s" % path)
        return 127
    proc = subprocess.run([PY, path] + list(args), cwd=HERE, env=env)
    code = proc.returncode
    print("— %s 退出码 = %d（%s）" % (name, code, "通过" if code == 0 else "失败"))
    return code


def main():
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")

    results = []
    for name, desc, args in CHECKS:
        results.append((name, run_one(name, desc, args, env)))

    print("=" * 72)
    print("汇总")
    print("=" * 72)
    failed = 0
    for name, code in results:
        tag = "OK" if code == 0 else "FAIL(%d)" % code
        print("  %-20s %s" % (name, tag))
        if code != 0:
            failed += 1
    print("总计 %d 项，失败 %d 项" % (len(results), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
