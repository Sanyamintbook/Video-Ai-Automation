import os
from pptx import Presentation

def inspect_pptx(path):
    print(f"\nInspecting PPTX: {path}")
    try:
        prs = Presentation(path)
        for i, slide in enumerate(prs.slides):
            print(f"--- Slide {i+1} ---")
            if slide.shapes.title:
                print(f"Title: {slide.shapes.title.text}")
            for shape in slide.shapes:
                if shape.has_text_frame and shape != slide.shapes.title:
                    print(f"Body: {shape.text_frame.text}")
    except Exception as e:
        print(f"Error reading {path}: {e}")

def main():
    for root, dirs, files in os.walk("."):
        if ".venv" in root or ".git" in root or ".gemini" in root:
            continue
        for file in files:
            if file.endswith(".pptx") and "output" in file:
                inspect_pptx(os.path.join(root, file))

if __name__ == "__main__":
    main()
