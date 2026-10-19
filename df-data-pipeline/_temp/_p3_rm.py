import os,sys
b=r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever"
for n in ["_diag.txt","_diag2.txt","_diag3.txt"]:
    p=os.path.join(b,n)
    try:
        os.remove(p); print("OK",n)
    except Exception as e:
        print("ERR",n,e)
print("remain",[n for n in ["_diag.txt","_diag2.txt","_diag3.txt"] if os.path.exists(os.path.join(b,n))])
