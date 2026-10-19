import io
import re

P = '.workbuddy/UI_RULES.md'
s = io.open(P, encoding='utf-8', newline='').read()

good = (
    '**十四次（2026-10-18）任务总览连线圆角**：连线改 `path()` 点序列 + 拐点两侧让位 R=`DG.Q_OV_RAD`(6) '
    '+ `Media/DFLineArc.tga`（64×64 · 4× 密度 · 白 RGB / alpha 超采样覆盖率）画四分之一圆环；'
    '`vline`/`hline` 降级为 `rawSeg` 薄封装，`elbow`/`laneElbow` 改走 `path`；'
    '脊线上首末列 `path` 圆弧接入、中段列 T 形分叉保持直角，底部汇线同理（定式见 §4）'
)

pat = re.compile(r'\*\*十四次（2026-10-18）任务总览连线圆角\*\*.*?（定式见 §4）', re.S)
n = len(pat.findall(s))
assert n == 1, n
s = pat.sub(lambda m: good, s, count=1)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('rewritten ok')
