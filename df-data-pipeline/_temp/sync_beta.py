# -*- coding: utf-8 -*-
"""把开发仓的「打包集」同步到 beta 验证副本（harness 断的是 beta，不是本目录）。

2026-10-06 起改为薄壳，委托 .workbuddy/tools/deploy_to_client.py：
  - 只部署打包集（规则唯一出处 = .workbuddy/tools/pkgfiles.py），
    不再把 AGENTS.md / .gitignore / _fc_* / _probe_out.txt 等非包文件带进客户端；
  - --apply 时默认**清理**客户端里的多余文件（客户端内容永远 = 用户拿到的包）。

用法（与旧契约兼容）：
  python sync_beta.py            # 只比对（dry-run，即 deploy --check）
  python sync_beta.py --apply    # 实际复制 + 清理多余
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEPLOY = os.path.join(os.path.dirname(HERE), ".workbuddy", "tools", "deploy_to_client.py")

argv = ["--check"] if "--apply" not in sys.argv[1:] else []
print("[sync_beta] 委托 deploy_to_client.py %s" % (argv or ["(apply)"]))
sys.exit(subprocess.call([sys.executable, DEPLOY] + argv))
