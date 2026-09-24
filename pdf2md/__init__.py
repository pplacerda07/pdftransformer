"""pdftransformer - converte PDFs em Markdown preservando a pagina da publicacao."""
from .model import Options, DocResult
from .converter import convert_file, convert_many

__all__ = ["Options", "DocResult", "convert_file", "convert_many"]
__version__ = "1.0.0"
