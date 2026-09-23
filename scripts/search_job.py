import os

project_root = r"C:\Users\Sanyami Jain\Documents\Vidoe_Automation\olympiad-ai-video\app"
for root, dirs, files in os.walk(project_root):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "import Job" in content or "Job(" in content:
                    print(f"Used in: {path}")
