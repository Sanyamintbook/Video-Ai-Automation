import os

def main():
    target1 = "test_data"
    target2 = "output"
    print(f"Searching for references...")
    for root, dirs, files in os.walk("."):
        if ".venv" in root or ".git" in root or ".gemini" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if target1 in content or "output/" in content or "output\\" in content:
                        print(f"Found reference in: {path}")
                except Exception as e:
                    pass

if __name__ == "__main__":
    main()
