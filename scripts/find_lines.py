with open(r"C:\Users\Sanyami Jain\Downloads\files\01_ARCHITECTURE_v1.0.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "1b" in line.lower() or "routing" in line.lower() or "escalat" in line.lower():
        print(f"Line {i+1}: {line.strip()}")
