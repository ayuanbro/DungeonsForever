from PIL import Image
import glob, os
f = max(glob.glob(r"C:/Users/Administrator/AppData/Local/WuxianWorkshop/snaps/snap-*.png"), key=os.path.getmtime)
im = Image.open(f)
c = im.crop((620, 130, 1680, 1010)).resize((1272, 1056), Image.LANCZOS)
c.save(r"D:/workspace/DungeonsForever/_temp/_ov_shot.png")
print("ok")
