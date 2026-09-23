import io
from app.domain.models.source_document import SourceDocument

class ParserError(Exception):
    pass

class PdfParser:
    def parse(self, file_bytes: bytes, filename: str = "document.pdf") -> SourceDocument:
        text = ""
        # Try PyMuPDF (fitz) first
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception:
            # Fallback to pure Python pypdf
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            except Exception as e:
                raise ParserError(f"Failed to parse PDF: {str(e)}")
                
        if not text.strip():
            raise ParserError("No extractable text found in PDF.")
            
        return SourceDocument(
            document_id="doc_" + filename,
            filename=filename,
            content_type="pdf",
            raw_text=text,
            storage_path=""
        )
