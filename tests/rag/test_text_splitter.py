from app.infrastructure.rag.text_splitter import RecursiveCharacterTextSplitter

def test_recursive_splitter_simple():
    splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=10)
    text = "Hello world. This is a simple test of our recursive character text splitter."
    chunks = splitter.split_text(text)
    
    assert len(chunks) > 0
    # Every chunk should be less than or equal to size 50 + headroom
    for chunk in chunks:
        assert len(chunk) <= 50
        
def test_recursive_splitter_empty():
    splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=2)
    assert splitter.split_text("") == []
    assert splitter.split_text(None) == []

def test_recursive_splitter_paragraphs():
    splitter = RecursiveCharacterTextSplitter(chunk_size=15, chunk_overlap=2)
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    chunks = splitter.split_text(text)
    
    assert len(chunks) >= 3
    assert "Paragraph 1." in chunks[0]
    assert "Paragraph 2." in chunks[1]
    assert "Paragraph 3." in chunks[2]
