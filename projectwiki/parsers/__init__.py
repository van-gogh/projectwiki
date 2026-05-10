from __future__ import annotations

from pathlib import Path

from ..models import ParsedBlock
from .code import parse_code
from .csv_parser import parse_csv
from .docx import parse_docx
from .markdown import parse_markdown
from .pdf import parse_pdf
from .plaintext import parse_plaintext
from .xlsx import parse_xlsx

CODE_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rs", ".cpp", ".c", ".h", ".sh", ".sql"}


def parse_file(path: str | Path) -> list[ParsedBlock]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".rst"}:
        return parse_markdown(path)
    if suffix == ".csv":
        return parse_csv(path)
    if suffix == ".xlsx":
        return parse_xlsx(path)
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in CODE_EXTENSIONS or suffix in {".yaml", ".yml", ".json", ".toml", ".ini"}:
        return parse_code(path)
    return parse_plaintext(path)
