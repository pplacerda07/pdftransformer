"""Extracao de texto com informacao de layout, usando PyMuPDF."""
from __future__ import annotations

import re

from ._pdf import fitz

from .model import BOLD, ITALIC, SUPERSCRIPT, Block, Line, Options, PageData, Span

# numero de pagina solto na margem: "23", "- 23 -", "[23]", "xiv", "p. 23"
_NUM_ONLY = re.compile(r"^[\[\(\-–—\s\.]*(?:p{1,2}\.?\s*)?(\d{1,4})[\]\)\-–—\s\.]*$", re.I)
_ROMAN_ONLY = re.compile(r"^[\[\(\-–—\s\.]*([ivxlcdm]{1,7})[\]\)\-–—\s\.]*$", re.I)

_TEXT_FLAGS = fitz.TEXT_PRESERVE_WHITESPACE | fitz.TEXT_MEDIABOX_CLIP


def _span_from_dict(s: dict) -> Span:
    flags = s.get("flags", 0)
    font = (s.get("font") or "").lower()
    return Span(
        text=s.get("text", ""),
        size=float(s.get("size", 0.0)),
        bold=bool(flags & BOLD) or "bold" in font or "black" in font or "heavy" in font,
        italic=bool(flags & ITALIC) or "italic" in font or "oblique" in font,
        superscript=bool(flags & SUPERSCRIPT),
    )


def _rect_overlap(a, b) -> float:
    """Fracao da area de `a` coberta por `b`."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    iy = max(0.0, min(ay1, by1) - max(ay0, by0))
    area = max(1e-6, (ax1 - ax0) * (ay1 - ay0))
    return (ix * iy) / area


def _find_tables(page, opts: Options):
    if not opts.tables:
        return []
    out = []
    try:
        finder = page.find_tables()
    except Exception:
        return []
    for t in getattr(finder, "tables", []):
        try:
            rows = t.extract()
        except Exception:
            continue
        rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in rows]
        rows = [r for r in rows if any(c for c in r)]
        if len(rows) >= 2 and len(rows[0]) >= 2:
            out.append(Block(kind="table", bbox=tuple(t.bbox), rows=rows))
    return out


def order_blocks(blocks: list[Block], width: float, two_columns: bool) -> list[Block]:
    """Ordem de leitura. Detecta duas colunas (artigos, periodicos)."""
    blocks = sorted(blocks, key=lambda b: (round(b.bbox[1], 1), round(b.bbox[0], 1)))
    if not two_columns or len(blocks) < 4:
        return blocks

    x_mid = width / 2.0

    def is_full(b: Block) -> bool:
        return (b.bbox[2] - b.bbox[0]) > 0.62 * width

    def side(b: Block) -> int:
        return 0 if ((b.bbox[0] + b.bbox[2]) / 2.0) < x_mid else 1

    narrow = [b for b in blocks if not is_full(b)]
    crossing = [
        b for b in narrow
        if b.bbox[0] < x_mid - 0.02 * width and b.bbox[2] > x_mid + 0.02 * width
    ]
    left = [b for b in narrow if side(b) == 0]
    right = [b for b in narrow if side(b) == 1]
    if crossing or len(left) < 2 or len(right) < 2:
        return blocks

    def flush(buf: list[Block]) -> list[Block]:
        l = sorted([b for b in buf if side(b) == 0], key=lambda b: b.bbox[1])
        r = sorted([b for b in buf if side(b) == 1], key=lambda b: b.bbox[1])
        return l + r

    ordered: list[Block] = []
    buf: list[Block] = []
    for b in blocks:
        if is_full(b):
            ordered.extend(flush(buf))
            buf = []
            ordered.append(b)
        else:
            buf.append(b)
    ordered.extend(flush(buf))
    return ordered


def _margin_number(line: Line, height: float) -> tuple[int | None, str | None]:
    """Se a linha for so um numero de pagina na margem, devolve (arabico, romano)."""
    y0, y1 = line.bbox[1], line.bbox[3]
    in_top = y1 < 0.12 * height
    in_bottom = y0 > 0.88 * height
    if not (in_top or in_bottom):
        return None, None
    txt = line.text
    if not txt or len(txt) > 12:
        return None, None
    m = _NUM_ONLY.match(txt)
    if m:
        try:
            return int(m.group(1)), None
        except ValueError:
            return None, None
    m = _ROMAN_ONLY.match(txt)
    if m and roman_to_int(m.group(1)):
        return None, m.group(1).lower()
    return None, None


def roman_to_int(s: str) -> int:
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    s = s.lower()
    if not s or any(ch not in vals for ch in s):
        return 0
    total, prev = 0, 0
    for ch in reversed(s):
        v = vals[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


def extract_page(page, opts: Options, images_dir: str | None = None) -> PageData:
    rect = page.rect
    pd = PageData(index=page.number, width=rect.width, height=rect.height)

    tables = _find_tables(page, opts)
    table_boxes = [t.bbox for t in tables]

    raw = page.get_text("dict", flags=_TEXT_FLAGS)
    text_blocks: list[Block] = []
    for b in raw.get("blocks", []):
        if b.get("type") != 0:
            continue
        bbox = tuple(b.get("bbox", (0, 0, 0, 0)))
        if any(_rect_overlap(bbox, tb) > 0.6 for tb in table_boxes):
            continue
        lines: list[Line] = []
        for ln in b.get("lines", []):
            spans = [_span_from_dict(s) for s in ln.get("spans", []) if s.get("text")]
            spans = [s for s in spans if s.text.strip() or s.text == " "]
            if not spans:
                continue
            line = Line(spans=spans, bbox=tuple(ln.get("bbox", bbox)))
            if not line.text:
                continue
            lines.append(line)
        if lines:
            text_blocks.append(Block(kind="text", bbox=bbox, lines=lines))

    blocks = order_blocks(text_blocks + tables, rect.width, opts.two_columns)

    # numeros de pagina impressos nas margens -> servem para casar a numeracao.
    # guardamos tambem a altura relativa: o numero de pagina real aparece sempre
    # na mesma altura, o que separa ele de numeros soltos de figuras e tabelas.
    for blk in blocks:
        if blk.kind != "text":
            continue
        if len(blk.lines) > 3:          # numero de pagina fica isolado, nao num paragrafo
            continue
        for line in blk.lines:
            num, rom = _margin_number(line, rect.height)
            if num is None and rom is None:
                continue
            y_rel = ((line.bbox[1] + line.bbox[3]) / 2.0) / max(1.0, rect.height)
            if num is not None:
                pd.printed_numbers.append((num, y_rel, line))
            else:
                pd.printed_roman.append((rom, y_rel, line))

    if opts.extract_images and images_dir:
        blocks.extend(_extract_images(page, images_dir))

    pd.blocks = blocks
    pd.char_count = sum(
        len(l.text) for b in blocks if b.kind == "text" for l in b.lines if not l.drop
    )
    return pd


def _extract_images(page, images_dir: str) -> list[Block]:
    import os

    out: list[Block] = []
    doc = page.parent
    for i, info in enumerate(page.get_images(full=True)):
        xref = info[0]
        try:
            pix = fitz.Pixmap(doc, xref)
            if pix.n - pix.alpha >= 4:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            if pix.width < 60 or pix.height < 60:
                continue
            name = f"p{page.number + 1:04d}_img{i + 1}.png"
            path = os.path.join(images_dir, name)
            pix.save(path)
            rects = page.get_image_rects(xref)
            bbox = tuple(rects[0]) if rects else (0, page.rect.height, 0, page.rect.height)
            out.append(Block(kind="image", bbox=bbox, path=name))
        except Exception:
            continue
    return out
