from pathlib import Path
import docx
import pypdf


class DocumentProcessor:
    def __init__(self):
        self.supported_extensions = {".docx", ".pdf"}

    def process(self, file_path: str, progress_callback=None, is_cancelled=None) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")

        ext = path.suffix.lower()
        if ext == ".docx":
            return self._extract_docx(path, progress_callback, is_cancelled)
        elif ext == ".pdf":
            return self._extract_pdf(path, progress_callback, is_cancelled)
        else:
            raise ValueError(f"Unsupported document extension: {ext}")

    def _extract_docx(self, path: Path, progress_callback, is_cancelled) -> str:
        doc = docx.Document(path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        total = len(paragraphs)
        extracted = []

        for i, text in enumerate(paragraphs):
            if is_cancelled and is_cancelled():
                return ""
            extracted.append(text)
            if progress_callback and total > 0:
                progress_callback((i + 1) / total)

        return "\n\n".join(extracted)

    def _extract_pdf(self, path: Path, progress_callback, is_cancelled) -> str:
        text_pages = []
        reader = pypdf.PdfReader(path)
        total_pages = len(reader.pages)

        for i, page in enumerate(reader.pages):
            if is_cancelled and is_cancelled():
                return ""
            extracted = page.extract_text()
            if extracted:
                text_pages.append(extracted.strip())
            if progress_callback and total_pages > 0:
                progress_callback((i + 1) / total_pages)

        return "\n\n".join(text_pages)