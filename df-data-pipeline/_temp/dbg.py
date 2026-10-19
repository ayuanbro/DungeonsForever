sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read()
i = data.find(b'"memMarks"')
print("found at", i, "total len", len(data))
print(repr(data[i:i+400]))
