# -*- coding: utf-8 -*-
"""最小化 dry-run 桩：只提供 fc_fields.py 复检所需的 STUB。

完整版（BGLite 的 tools/tf_dryrun.py）带整条「加载→建界面→点命令」链路，
这里不需要，只把 WoW API 桩单独抽出来放在 wow_stub.lua。
"""
import io
import os

with io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          'wow_stub.lua'), encoding='utf-8') as fh:
    STUB = fh.read()
