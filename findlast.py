import os

# Read all folder names in ~/twasn into a list
folder_path = os.path.expanduser("~/twasn")
folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

# Read the whole file ./following.js as a string
with open("./following.js", "r") as f:
    following = f.read()

# Get the index of each folder's occurrence in following
idcs = []
for folder in folders:
    index = following.find(folder)
    if index == -1:
        print(f"{folder} not found in following")
    else:
        print(f"{folder} found in following at index {index}")
    idcs += [index]

print(max(idcs))
