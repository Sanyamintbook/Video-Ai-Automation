import os

def main():
    target = "NarrationSegment"
    docs_dir = r"C:\Users\Sanyami Jain\Downloads\files"
    print(f"Searching for '{target}' in '{docs_dir}'...")
    for file in os.listdir(docs_dir):
        if file.endswith(".md"):
            path = os.path.join(docs_dir, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if target in content:
                    print(f"Found in: {file}")
                    # Let's print the line and context
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if target in line:
                            print(f"  Line {i+1}: {line}")
            except Exception as e:
                pass

if __name__ == "__main__":
    main()
