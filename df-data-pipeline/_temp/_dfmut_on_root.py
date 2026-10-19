# -*- coding: utf-8 -*-
"""把 df_mut_check 的 BETA（+ harness 的 DF_ADDON_ROOT）临时指向一棵「可mutate的副本」，
并从一棵「纯净副本」还原，再跑全量变异注入。

用途：同一份 df_mut_check 定义，分别在「改前树」与「改后树」上注入，对照
      「锚点是否唯一 / 变异是否被抓住 / 输出是否逐字一致」。

用法：
    python _temp/_dfmut_on_root.py <beta_root_可写副本> <titan_root_纯净>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
beta_root, titan_root = sys.argv[1], sys.argv[2]
os.environ['DF_ADDON_ROOT'] = beta_root

import df_mut_check as M  # noqa: E402
M.BETA = beta_root
M.TITAN = titan_root
sys.exit(M.main())
