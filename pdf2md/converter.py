"""Orquestra a conversao de um PDF em Markdown."""
from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Callable

from ._pdf import fitz

from . import ocr as _ocr
from .extract import extract_page
from .mdwriter import doc_stats, mark_running_heads, page_marker, render_page
from .model import Block, DocResult, Line, Options, PageData, Span
from .pagelabels import resolve as resolve_labels

Progress = Callable[[int, int], None]
Log = Callable[[str], None]

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_name(name: str, limit: int = 120) -> str:
    name = _INVALID.sub("-", name).strip(" .")
    name = re.sub(r"\s+", " ", name)
    return (name[:limit].strip() or "documento")


def _yaml(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    text = re.sub(r"\s+", " ", text).strip()
    return f'"{text}"'


def _guess_title(doc, pages: list[PageData], fallback: str, body_size: float) -> str:
    meta = (doc.metadata or {}).get("title") or ""
    meta = meta.strip()
    if len(meta) >= 4 and not meta.lower().endswith(".pdf") and "untitled" not in meta.lower():
        return meta
    # maior texto das primeiras paginas, desde que destoe do corpo do texto
    for page in pages[:2]:
        best, best_size = "", body_size * 1.15
        for blk in page.blocks:
            if blk.kind != "text":
                continue
            for line in blk.lines:
                text = line.text
                if line.drop or not (4 <= len(text) <= 120):
                    continue
                if text.endswith(("-", "‐", "­", ",")):
                    continue
                if line.size > best_size:
                    best, best_size = text, line.size
        if best:
            return best
    return fallback


def _ocr_page_block(text: str, page) -> Block:
    lines = []
    y = 0.0
    for raw in text.splitlines():
        if not raw.strip():
            continue
        y += 12.0
        lines.append(
            Line(spans=[Span(text=raw.strip(), size=10.0)],
                 bbox=(0.0, y, page.rect.width, y + 11.0))
        )
    return Block(kind="text", bbox=(0.0, 0.0, page.rect.width, page.rect.height), lines=lines)


def convert_file(
    pdf_path: str,
    opts: Options,
    progress: Progress | None = None,
    log: Log | None = None,
    cancel: Callable[[], bool] | None = None,
) -> DocResult:
    say = log or (lambda _m: None)
    stem = os.path.splitext(os.path.basename(pdf_path))[0]
    out_dir = opts.output_dir or os.path.join(os.path.dirname(pdf_path), "markdown")
    os.makedirs(out_dir, exist_ok=True)

    images_dir = None
    if opts.extract_images:
        images_dir = os.path.join(out_dir, "assets", safe_name(stem))
        os.makedirs(images_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    result = DocResult(source=pdf_path, out_path=None, pages=doc.page_count)

    if doc.is_encrypted and not doc.authenticate(""):
        doc.close()
        result.warnings.append("PDF protegido por senha - nao foi possivel abrir.")
        return result

    pages: list[PageData] = []
    for i in range(doc.page_count):
        if cancel and cancel():
            doc.close()
            result.warnings.append("Cancelado pelo usuario.")
            return result
        page = doc[i]
        pd = extract_page(page, opts, images_dir)
        if pd.char_count < 25:
            if opts.ocr and _ocr.available():
                text = _ocr.page_text(page, opts.ocr_lang)
                if text.strip():
                    pd.blocks = [_ocr_page_block(text, page)]
                    pd.char_count = len(text)
                    pd.ocr_used = True
            if pd.char_count < 25:
                result.empty_pages.append(i + 1)
        pages.append(pd)
        if progress:
            progress(i + 1, doc.page_count)

    # a numeracao vem primeiro: ela decide quais numeros de margem sao numero
    # de pagina (e somem do texto) e quais sao conteudo de verdade.
    labels = resolve_labels(doc, pages, opts)
    result.page_source = labels.human

    if opts.strip_running_heads:
        mark_running_heads(pages)

    stats = doc_stats(pages)

    for pd in pages:
        pd.label = labels.label(pd.index)

    title = _guess_title(doc, pages, stem, stats.body_size)
    meta = doc.metadata or {}
    result.meta = {
        "title": title,
        "author": (meta.get("author") or "").strip(),
        "pages": doc.page_count,
        "first_label": labels.label(0),
        "last_label": labels.label(doc.page_count - 1),
    }

    body_parts: list[str] = []
    for pd in pages:
        marker = page_marker(pd.label, pd.index + 1, opts)
        text = render_page(pd, stats, opts)
        if not text and not marker:
            continue
        chunk = marker
        if text:
            chunk = (marker + "\n\n" + text) if marker else text
        elif pd.index + 1 in result.empty_pages:
            chunk = marker + "\n\n*(pagina sem texto extraivel - provavelmente imagem/escaneada)*"
        body_parts.append(chunk.strip())

    header = _build_header(pdf_path, result, labels, opts, title, meta)
    content = header + "\n\n".join(body_parts).strip() + "\n"
    content = re.sub(r"\n{4,}", "\n\n\n", content)

    out_path = os.path.join(out_dir, safe_name(stem) + ".md")
    if not opts.overwrite and os.path.exists(out_path):
        n = 2
        while os.path.exists(out_path):
            out_path = os.path.join(out_dir, f"{safe_name(stem)} ({n}).md")
            n += 1
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    result.out_path = out_path

    if opts.per_page_files:
        result.per_page_dir = _write_per_page(pages, stats, opts, out_dir, stem, title, pdf_path)

    if result.empty_pages:
        result.warnings.append(
            f"{len(result.empty_pages)} pagina(s) sem texto extraivel "
            f"(ex.: {', '.join(str(p) for p in result.empty_pages[:6])}"
            f"{'...' if len(result.empty_pages) > 6 else ''}) - PDF escaneado?"
        )
    if labels.source == "pdf" and labels.detail:
        result.warnings.append(
            f"Numeracao: {labels.detail}. Usando a pagina do PDF; "
            "se a publicacao comeca em outra pagina, informe o deslocamento."
        )

    doc.close()
    say(f"OK  {os.path.basename(pdf_path)} -> {os.path.basename(out_path)} "
        f"({result.pages} pag., {result.page_source})")
    return result


def _build_header(pdf_path, result: DocResult, labels, opts: Options, title, meta) -> str:
    if not opts.frontmatter and not opts.marker_legend:
        return ""
    parts: list[str] = []
    if opts.frontmatter:
        today = _dt.date.today().isoformat()
        fm = [
            "---",
            f"title: {_yaml(title)}",
        ]
        if (meta.get("author") or "").strip():
            fm.append(f"author: {_yaml(meta.get('author'))}")
        fm += [
            f"source_file: {_yaml(os.path.basename(pdf_path))}",
            f"source_path: {_yaml(pdf_path)}",
            f"pdf_pages: {result.pages}",
            f"page_numbering: {_yaml(labels.source)}",
            f"page_numbering_note: {_yaml(labels.human)}",
            f"first_page_label: {_yaml(labels.label(0) or labels.first_real or 'sem numeracao')}",
            f"converted: {today}",
            "tool: pdftransformer",
            "tags:",
            "  - pdf",
            "  - fonte",
            "---",
        ]
        parts.append("\n".join(fm))
    if opts.marker_legend and opts.marker_style != "none":
        parts.append(
            "> [!info] Numeracao de paginas\n"
            "> Cada marcador de pagina (o titulo `p. N` e o comentario HTML logo acima "
            "dele) indica o **inicio da pagina N da publicacao original**. "
            f"Origem da numeracao: {labels.human}.\n"
            "> Ao citar este documento, use o numero do marcador imediatamente anterior "
            "ao trecho."
        )
    parts.append(f"# {title}")
    return "\n\n".join(parts) + "\n\n"


def _write_per_page(pages, stats, opts, out_dir, stem, title, pdf_path) -> str:
    folder = os.path.join(out_dir, safe_name(stem) + " - paginas")
    os.makedirs(folder, exist_ok=True)
    total = len(pages)
    for pd in pages:
        text = render_page(pd, stats, opts)
        rotulo = f"p. {pd.label}" if pd.label else f"folha {pd.index + 1} (sem numeracao)"
        fm = [
            "---",
            f"title: {_yaml(title + ' - ' + rotulo)}",
            f"source_file: {_yaml(os.path.basename(pdf_path))}",
            f"page: {_yaml(pd.label or 'sem numeracao')}",
            f"pdf_page: {pd.index + 1}",
            "---",
            "",
        ]
        nav = []
        if pd.index > 0:
            nav.append(f"[[{safe_name(stem)} p{pd.index:04d}|<- anterior]]")
        if pd.index + 1 < total:
            nav.append(f"[[{safe_name(stem)} p{pd.index + 2:04d}|proxima ->]]")
        body = "\n".join(fm) + f"# {rotulo}\n\n" + (text or "*(sem texto)*")
        if nav:
            body += "\n\n---\n" + " · ".join(nav) + "\n"
        path = os.path.join(folder, f"{safe_name(stem)} p{pd.index + 1:04d}.md")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
    return folder


def convert_many(
    paths: list[str],
    opts: Options,
    on_file: Callable[[str, int, int], None] | None = None,
    progress: Progress | None = None,
    log: Log | None = None,
    cancel: Callable[[], bool] | None = None,
) -> list[DocResult]:
    results: list[DocResult] = []
    for i, path in enumerate(paths):
        if cancel and cancel():
            break
        if on_file:
            on_file(path, i + 1, len(paths))
        try:
            results.append(convert_file(path, opts, progress, log, cancel))
        except Exception as exc:  # pragma: no cover - protege o lote inteiro
            res = DocResult(source=path, out_path=None, pages=0)
            res.warnings.append(f"Erro: {exc}")
            results.append(res)
            if log:
                log(f"ERRO  {os.path.basename(path)}: {exc}")
    return results
