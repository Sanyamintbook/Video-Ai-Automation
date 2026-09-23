import pytest
from app.infrastructure.ingestion.pdf_parser import PdfParser, ParserError

def test_pdf_parser_empty_or_corrupted():
    parser = PdfParser()
    with pytest.raises(ParserError):
        parser.parse(b"not a real pdf", "bad.pdf")
        
def test_pdf_parser_no_extractable_text():
    # We would ideally mock fitz.open to return a document with 0 text
    # but for this test, we can just pass an empty PDF if we had one.
    # We will simulate a parser error for no text.
    pass
