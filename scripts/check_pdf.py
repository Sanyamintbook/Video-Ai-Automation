import fitz
doc = fitz.open("test_data/input/Ch 3 Mineral and Power Resour.pdf")
text = ""
for page in doc:
    text += page.get_text()
print("Length of text:", len(text))
print("First 1000 characters:")
print(text[:1000])
