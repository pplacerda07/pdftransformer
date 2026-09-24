"""Importa o PyMuPDF pelo nome novo (pymupdf) com fallback para o antigo (fitz)."""
import os

os.environ.setdefault("PYMUPDF_SUGGEST_LAYOUT_ANALYZER", "0")

try:
    import pymupdf as fitz
except ImportError:  # PyMuPDF < 1.24.3
    import fitz

# PDFs mal formados fazem o MuPDF despejar avisos no terminal. Nao sao erros
# nossos e so poluiriam o registro da interface.
try:
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
except Exception:
    pass

try:
    fitz.no_recommend_layout()
except Exception:
    pass

__all__ = ["fitz"]
