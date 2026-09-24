"""Transforma os blocos extraidos em Markdown."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .model import Block, Line, Options, PageData

_LIST_RE = re.compile(r"^\s*([-\u2013\u2014\u2022\u25aa\u00b7*\u25cf]|\(?\d{1,2}[.)]|\(?[a-z][.)])\s+")
_ORDERED_RE = re.compile(r"^\s*\(?(\d{1,2})[.)]\s+")
_END_PUNCT = (".", "!", "?", ":", ";", "\u201d", "\u2019", '"', ")", "]")
_HEADING_HINT = re.compile(
    r"^\s*(cap[i\u00ed]tulo|parte|se[c\u00e7][a\u00e3]o|unidade|anexo|ap[e\u00ea]ndice|"
    r"introdu[c\u00e7][a\u00e3]o|conclus[a\u00e3]o|refer[e\u00ea]ncias|bibliografia|"
    r"resumo|abstract|sum[a\u00e1]rio)\b",
    re.I,
)


@dataclass
class Stats:
    body_size: float
    heading_sizes: list[float]     # do maior para o menor

    def heading_level(self, size: float, base: int = 2) -> int | None:
        for i, s in enumerate(self.heading_sizes):
            if abs(size - s) < 0.35:
                return min(5, base + i)
        return None


def doc_stats(pages: list[PageData]) -> Stats:
    """Tamanho de fonte do corpo = o mais frequente, contado por caractere."""
    by_size: Counter = Counter()
    for p in pages:
        for b in p.blocks:
            if b.kind != "text":
                continue
            for line in b.lines:
                if line.drop:
                    continue
                by_size[round(line.size * 2) / 2] += len(line.text)
    if not by_size:
        return Stats(10.0, [])
    body = by_size.most_common(1)[0][0]
    total = sum(by_size.values())
    bigger = sorted(
        (s for s, c in by_size.items() if s > body * 1.12 and c > total * 0.0005),
        reverse=True,
    )
    # agrupa tamanhos quase iguais e fica com no maximo 4 niveis
    levels: list[float] = []
    for s in bigger:
        if not levels or abs(levels[-1] - s) > 0.6:
            levels.append(s)
    return Stats(body, levels[:4])


def _in_margin(line: Line, page: PageData) -> bool:
    return line.bbox[3] < 0.11 * page.height or line.bbox[1] > 0.89 * page.height


def _margin_texts(page: PageData) -> list[str]:
    out = []
    for blk in page.blocks:
        if blk.kind != "text":
            continue
        for line in blk.lines:
            if line.drop or len(line.text) > 90:
                continue
            if _in_margin(line, page):
                out.append(line.text)
    return out


def mark_running_heads(pages: list[PageData]) -> set:
    """Cabecalhos/rodapes repetidos (titulo do livro, do capitulo) viram ruido."""

    def norm(t: str) -> str:
        t = re.sub(r"\d+", "#", t.strip().lower())
        return re.sub(r"\s+", " ", t)

    counts: Counter = Counter()
    for p in pages:
        for t in _margin_texts(p):
            counts[norm(t)] += 1
    threshold = max(3, int(len(pages) * 0.35))
    repeated = {k for k, c in counts.items() if c >= threshold and len(k) > 3}
    if not repeated:
        return set()
    for p in pages:
        for blk in p.blocks:
            if blk.kind != "text":
                continue
            for line in blk.lines:
                if line.drop:
                    continue
                if norm(line.text) in repeated and _in_margin(line, p):
                    line.drop = True
    return repeated


# --------------------------------------------------------------------------- #
# marcadores de pagina
# --------------------------------------------------------------------------- #
def page_marker(label: str, pdf_page: int, opts: Options) -> str:
    if opts.marker_style == "none":
        return ""
    if not label:
        # folha sem numeracao (capa, rosto, folha de credito): dizer isso e
        # mais honesto do que passar o numero da folha como se fosse a pagina
        comment = f"<!-- page: sem-numeracao | pdf: {pdf_page} -->"
        heading = f"###### folha {pdf_page} (sem numeracao)"
        inline = f"**[folha {pdf_page}, sem numeracao]**"
        style = opts.marker_style
        if style == "comment":
            return comment
        if style == "heading":
            return heading
        if style == "inline":
            return inline
        return comment + "\n" + heading

    show_pdf = opts.show_pdf_page and label != str(pdf_page)
    comment = f"<!-- page: {label}" + (f" | pdf: {pdf_page}" if show_pdf else "") + " -->"
    heading = f"###### p. {label}"
    inline = f"**[p. {label}]**"
    style = opts.marker_style
    if style == "comment":
        return comment
    if style == "heading":
        return heading
    if style == "inline":
        return inline
    return comment + "\n" + heading


# --------------------------------------------------------------------------- #
# linhas -> markdown
# --------------------------------------------------------------------------- #
def _line_md(line: Line, opts: Options, plain: bool = False) -> str:
    if plain or not opts.emphasis:
        return re.sub(r"[ \t]+", " ", line.text).strip()
    parts: list[str] = []
    for s in line.spans:
        t = s.text
        core = t.strip()
        if not core:
            parts.append(t)
            continue
        lead = " " if t[:1].isspace() else ""
        trail = " " if t[-1:].isspace() else ""
        mark = "***" if (s.bold and s.italic) else "**" if s.bold else "*" if s.italic else ""
        parts.append(lead + (f"{mark}{core}{mark}" if mark else core) + trail)
    txt = "".join(parts)
    # junta marcacoes coladas: o PDF costuma quebrar uma palavra em varios spans
    txt = re.sub(r"\*\*\*(\s*)\*\*\*", r"\1", txt)
    txt = re.sub(r"\*\*(\s*)\*\*", r"\1", txt)
    txt = re.sub(r"(?<!\*)\*(\s*)\*(?!\*)", r"\1", txt)
    return re.sub(r"[ \t]+", " ", txt).strip()


def _join(prev: str, nxt: str, opts: Options) -> str:
    if not prev:
        return nxt
    if opts.dehyphenate and re.search(r"[\w\u00c0-\u024f][-\u00ad\u2010]$", prev):
        nxt_l = nxt.lstrip()
        if nxt_l[:1].islower() or nxt_l[:1].isdigit():
            return prev[:-1] + nxt_l
    return prev.rstrip() + " " + nxt.lstrip()


def _escape(text: str) -> str:
    return re.sub(r"^(\s*)([#>])", r"\1\\\2", text)


def _table_md(rows: list) -> str:
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [
        [(c or "").replace("|", "\\|").replace("\n", " ").strip() for c in r]
        + [""] * (width - len(r))
        for r in rows
    ]
    head = norm[0]
    body = norm[1:]
    if not any(head):
        head = [f"col {i + 1}" for i in range(width)]
    out = [
        "| " + " | ".join(head) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def _is_heading(line: Line, stats: Stats, opts: Options) -> int | None:
    if not opts.detect_headings:
        return None
    text = line.text
    if not text or len(text) > 150:
        return None
    lvl = stats.heading_level(line.size)
    if lvl:
        return lvl
    ends_like_prose = text.endswith((".", ",", ";"))
    if line.bold and len(text) <= 90 and not ends_like_prose \
            and line.size >= stats.body_size * 0.98:
        return min(5, 2 + len(stats.heading_sizes))
    if _HEADING_HINT.match(text) and len(text) <= 90 and not ends_like_prose \
            and line.size >= stats.body_size:
        return min(5, 2 + len(stats.heading_sizes))
    return None


def render_block(block: Block, stats: Stats, opts: Options) -> list[str]:
    if block.kind == "table":
        table = _table_md(block.rows or [])
        return [table] if table else []
    if block.kind == "image":
        return [f"![](assets/{block.path})"] if block.path else []

    lines = [l for l in block.lines if not l.drop and l.text]
    if not lines:
        return []

    left_edge = min(l.bbox[0] for l in lines)
    right_edge = max(l.bbox[2] for l in lines)
    width = right_edge - left_edge

    out: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            out.append(_escape(buf.strip()))
        buf = ""

    for line in lines:
        text = line.text
        lvl = _is_heading(line, stats, opts)
        if lvl:
            flush()
            out.append("#" * lvl + " " + _line_md(line, opts, plain=True))
            continue

        md = _line_md(line, opts)
        if _LIST_RE.match(text):
            flush()
            m = _ORDERED_RE.match(text)
            body = _LIST_RE.sub("", md, count=1)
            out.append((f"{m.group(1)}. " if m else "- ") + body)
            continue

        buf = _join(buf, md, opts)

        # fim de paragrafo: linha que termina antes da margem e com pontuacao
        short = width > 0 and (right_edge - line.bbox[2]) > 0.12 * width
        if short and text.rstrip().endswith(_END_PUNCT):
            flush()

    flush()
    return [o for o in out if o]


def render_page(page: PageData, stats: Stats, opts: Options) -> str:
    chunks: list[str] = []
    for block in page.blocks:
        chunks.extend(render_block(block, stats, opts))
    return "\n\n".join(chunks).strip()
