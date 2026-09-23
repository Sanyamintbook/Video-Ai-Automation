import os

def main():
    target = "instructional design"
    print(f"Searching for '{target}'...")
    for root, dirs, files in os.walk("."):
        if ".venv" in root or ".git" in root or ".gemini" in root:
            continue
        for file in files:
            if file.endswith((".py", ".md", ".txt", ".json", ".env")):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if target in content.lower():
                        print(f"Found in: {path}")
                except Exception as e:
                    pass

if __name__ == "__main__":
    main()
