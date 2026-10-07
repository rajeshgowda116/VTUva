import os, glob

print("=== Search Python Files in Backend ===")
for root, dirs, files in os.walk("backend"):
    for file in files:
        if file.endswith(".py") or file.endswith(".json") or file.endswith(".txt") or file.endswith(".md"):
            path = os.path.join(root, file)
            print(path)
