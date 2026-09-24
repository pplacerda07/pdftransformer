"""Estruturas de dados e opcoes de conversao."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# flags de span do PyMuPDF
SUPERSCRIPT = 1 << 0
ITALIC = 1 << 1
SERIF = 1 << 2
MONO = 1 << 3
BOLD = 1 << 4


@dataclass
class Options:
    """Tudo o que a interface deixa o usuario ajustar."""

    # --- numeracao de paginas (o ponto critico para citar) ---
    page_mode: str = "auto"          # auto | embedded | detect | offset | pdf
    manual_offset: int = 0            # pagina impressa = pagina do pdf + offset
    marker_style: str = "both"        # both | comment | heading | inline | none
    show_pdf_page: bool = True        # mostra "(pdf 61)" quando difere

    # --- limpeza e estrutura do texto ---
    detect_headings: bool = True
    strip_running_heads: bool = True
    dehyphenate: bool = True
    emphasis: bool = True
    tables: bool = True
    two_columns: bool = True

    # --- saida ---
    frontmatter: bool = True
    marker_legend: bool = True        # nota explicando os marcadores para a IA
    per_page_files: bool = False
    extract_images: bool = False
    output_dir: str | None = None
    overwrite: bool = True

    # --- ocr (opcional, exige tesseract instalado) ---
    ocr: bool = False
    ocr_lang: str = "por+eng"


@dataclass
class Span:
    text: str
    size: float
    bold: bool = False
    italic: bool = False
    superscript: bool = False


@dataclass
class Line:
    spans: list[Span]
    bbox: tuple[float, float, float, float]
    drop: bool = False

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.spans).strip()

    @property
    def size(self) -> float:
        if not self.spans:
            return 0.0
        # tamanho dominante = o que cobre mais caracteres
        by_size: dict[float, int] = {}
        for s in self.spans:
            by_size[round(s.size, 1)] = by_size.get(round(s.size, 1), 0) + len(s.text)
        return max(by_size.items(), key=lambda kv: kv[1])[0]

    @property
    def bold(self) -> bool:
        chars = sum(len(s.text.strip()) for s in self.spans)
        if not chars:
            return False
        bold_chars = sum(len(s.text.strip()) for s in self.spans if s.bold)
        return bold_chars / chars > 0.7


@dataclass
class Block:
    kind: str                                   # text | table | image
    bbox: tuple[float, float, float, float]
    lines: list[Line] = field(default_factory=list)
    rows: list[list[str]] | None = None         # tabelas
    path: str | None = None                     # imagens extraidas


@dataclass
class PageData:
    index: int                                  # 0-based
    width: float
    height: float
    blocks: list[Block] = field(default_factory=list)
    char_count: int = 0
    printed_numbers: list = field(default_factory=list)   # [(numero, y relativo 0-1)] nas margens
    printed_roman: list = field(default_factory=list)      # [(romano, y relativo 0-1)]
    ocr_used: bool = False
    label: str = ""                             # preenchido depois


@dataclass
class DocResult:
    source: str
    out_path: str | None
    pages: int
    empty_pages: list[int] = field(default_factory=list)
    page_source: str = ""                       # de onde veio a numeracao
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    per_page_dir: str | None = None
