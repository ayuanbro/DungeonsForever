# -*- coding: utf-8 -*-
"""调试 fc_pins.py 的 RSC 正则。"""
import re

d = open('_ref/dg_shadowfang-keep.html', encoding='utf-8', errors='replace').read()

PIN_A = re.compile(
    r'\{\\"x\\":([\d.]+),\\"y\\":([\d.]+),\\"boss\\":\\"([\w-]+)\\",\\"face\\":(\d+),'
    r'\\"faceKind\\":\\"(\w+)\\",\\"label\\":\\"((?:[^"\\\\]|\\\\.)*)\\"')
print('多行版:', len(PIN_A.findall(d)))

PIN_B = re.compile(
    r'\{\\"x\\":([\d.]+),\\"y\\":([\d.]+),\\"boss\\":\\"([\w-]+)\\",\\"face\\":(\d+),\\"faceKind\\":\\"(\w+)\\",\\"label\\":\\"((?:[^"\\\\]|\\\\.)*)\\"')
print('单行版:', len(PIN_B.findall(d)))
