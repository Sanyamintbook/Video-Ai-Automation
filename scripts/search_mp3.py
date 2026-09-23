import os

project_root = r"C:\Users\Sanyami Jain\Documents\Vidoe_Automation\olympiad-ai-video"
for root, dirs, files in os.walk(project_root):
    for file in files:
        if file.endswith(".mp3"):
            print(f"Found MP3: {os.path.join(root, file)}")
