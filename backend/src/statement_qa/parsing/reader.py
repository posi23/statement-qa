"""Read text and its position from each page of a PDF.

The only parsing module that uses the PDF library.
"""

import io
from collections.abc import Sequence

from pypdf import PageObject, PdfReader
from pypdf.errors import PyPdfError

from statement_qa.parsing.errors import StatementParseError
from statement_qa.parsing.layout import TextPiece


def read_pages(pdf: bytes) -> list[list[TextPiece]]:
    """Return the text pieces on each page, in page order.

    Raises:
        StatementParseError: if the bytes aren't a readable PDF.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf))
        return [_read_page(page) for page in reader.pages]
    except (PyPdfError, ValueError) as error:
        raise StatementParseError(f"not a readable PDF: {error}") from error


def _read_page(page: PageObject) -> list[TextPiece]:
    """Collect every non-blank string pypdf finds on one page."""
    height = float(page.mediabox.height)
    pieces: list[TextPiece] = []

    def visit(
        text: str,
        cm: Sequence[float],
        tm: Sequence[float],
        font_dict: object,
        font_size: float,
    ) -> None:
        if not text.strip():
            return
        # Position = page transform offset + text matrix offset. PDF y counts
        # up from the bottom, so flip it to read top to bottom.
        x = float(cm[4]) + float(tm[4])
        y = height - (float(cm[5]) + float(tm[5]))
        pieces.append(TextPiece(x=x, y=y, text=text))

    page.extract_text(visitor_text=visit)
    return pieces
