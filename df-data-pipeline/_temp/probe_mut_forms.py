import sys, importlib.util
spec = importlib.util.spec_from_file_location("dfm", "df_mut_check.py")
dfm = importlib.util.module_from_spec(spec)
import builtins
# stub __main__ guard by exec with __name__ != "__main__"
spec.loader.exec_module(dfm)

forms = {}
for name, sp in dfm.MUTATIONS:
    if isinstance(sp, tuple) and len(sp) == 2 and isinstance(sp[0], str):
        forms.setdefault('A: (fname, (old,new))', 0)
        forms['A: (fname, (old,new))'] += 1
    elif isinstance(sp, tuple) and len(sp) == 2 and isinstance(sp[0], bytes):
        forms.setdefault('B: (old,new) bare', 0)
        forms['B: (old,new) bare'] += 1
    elif isinstance(sp, tuple) and len(sp) == 3:
        forms.setdefault('C: 3-tuple', 0)
        forms['C: 3-tuple'] += 1
        print("C sample:", name, repr(sp)[:120])
    else:
        forms.setdefault('D: other', 0)
        forms['D: other'] += 1
        print("D sample:", name, type(sp), repr(sp)[:120])
print(forms)
print("total:", len(dfm.MUTATIONS))
