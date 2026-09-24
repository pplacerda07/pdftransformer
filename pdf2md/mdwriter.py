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
    """Blocos que nao sao texto corrido: tabela e imagem."""
    if block.kind == "table":
        table = _table_md(block.rows or [])
        return [table] if table else []
    if block.kind == "image":
        if not block.path:
            return []
        alvo = f"assets/{block.path}"
        # caminho com espaco precisa dos sinais de menor/maior para o link valer
        return [f"![](<{alvo}>)" if " " in alvo else f"![]({alvo})"]
    return _paragrafos([l for l in block.lines if not l.drop and l.text], stats, opts)


def _passo_das_linhas(lines: list[Line]) -> float:
    """Distancia tipica entre duas linhas seguidas do mesmo paragrafo."""
    gaps = []
    for a, b in zip(lines, lines[1:]):
        g = b.bbox[1] - a.bbox[1]
        if 1.0 < g < 80.0:
            gaps.append(g)
    if not gaps:
        return 12.0
    gaps.sort()
    return gaps[len(gaps) // 2]          # mediana: nao se abala com saltos


def _margens(lines: list[Line]) -> tuple[float, float]:
    """Margens do CORPO do texto, nao da pagina.

    Usar o menor x da pagina daria errado sempre que houver um cabecalho ou um
    numero de pagina comecando antes da mancha de texto: todas as linhas do
    corpo pareceriam recuadas. Por isso a margem esquerda e a posicao mais
    repetida, e a direita e um percentil alto - robusto tambem em texto que
    nao e justificado.
    """
    x0s: Counter = Counter()
    for l in lines:
        x0s[round(l.bbox[0] / 2) * 2] += 1
    esquerda = float(x0s.most_common(1)[0][0])
    xs = sorted(l.bbox[2] for l in lines)
    direita = xs[min(len(xs) - 1, int(len(xs) * 0.85))]
    return esquerda, max(direita, esquerda + 1.0)


def _paragrafos(lines: list[Line], stats: Stats, opts: Options) -> list[str]:
    """Junta linhas em paragrafos usando a geometria da pagina.

    Muitos PDFs entregam cada linha como um bloco separado; se confiarmos nos
    blocos, o texto sai com uma linha por paragrafo e as palavras cortadas por
    hifen nunca se reencontram. Por isso a decisao e tomada aqui, olhando o
    espacamento, o recuo e onde a linha termina.
    """
    if not lines:
        return []

    passo = _passo_das_linhas(lines)
    esquerda, direita = _margens(lines)
    largura = max(1.0, direita - esquerda)
    limite_recuo = max(6.0, 0.022 * largura)

    out: list[str] = []
    buf = ""
    anterior: Line | None = None

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
            anterior = None
            continue

        md = _line_md(line, opts)
        if _LIST_RE.match(text):
            flush()
            m = _ORDERED_RE.match(text)
            corpo = _LIST_RE.sub("", md, count=1)
            out.append((f"{m.group(1)}. " if m else "- ") + corpo)
            anterior = None
            continue

        if buf and anterior is not None:
            salto = line.bbox[1] - anterior.bbox[1]
            recuo = line.bbox[0] - esquerda
            curta = (direita - anterior.bbox[2]) > 0.10 * largura

            quebra = (
                salto > passo * 1.6                      # espaco de paragrafo
                or salto < 0                             # voltou para cima: outra coluna
                or recuo > limite_recuo                  # linha com recuo: comeco novo
                or abs(line.size - anterior.size) > 1.0  # mudou o tamanho da fonte
                or (curta and anterior.text.rstrip().endswith(_END_PUNCT))
            )
            if quebra:
                flush()

        buf = _join(buf, md, opts)
        anterior = line

    flush()
    return [o for o in out if o]


def _mesma_faixa(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Dois blocos dividem a mesma coluna de texto?"""
    inicio = max(a[0], b[0])
    fim = min(a[1], b[1])
    sobra = fim - inicio
    menor = max(1.0, min(a[1] - a[0], b[1] - b[0]))
    return sobra / menor > 0.3


def render_page(page: PageData, stats: Stats, opts: Options) -> str:
    """Monta a pagina deixando os paragrafos atravessarem blocos vizinhos.

    Blocos que estao na mesma faixa horizontal pertencem ao mesmo fluxo de
    leitura e podem continuar o mesmo paragrafo. Quando a faixa muda - caso de
    um texto em duas colunas - o paragrafo e fechado, para as frases de uma
    coluna nao se misturarem com as da outra.
    """
    chunks: list[str] = []
    acumulado: list[Line] = []
    faixa: tuple[float, float] | None = None

    def despejar() -> None:
        nonlocal faixa
        if acumulado:
            chunks.extend(_paragrafos(acumulado, stats, opts))
            acumulado.clear()
        faixa = None

    for block in page.blocks:
        if block.kind != "text":
            despejar()
            chunks.extend(render_block(block, stats, opts))
            continue

        lines = [l for l in block.lines if not l.drop and l.text]
        if not lines:
            continue
        atual = (min(l.bbox[0] for l in lines), max(l.bbox[2] for l in lines))
        if faixa is not None and not _mesma_faixa(faixa, atual):
            despejar()
        acumulado.extend(lines)
        faixa = atual

    despejar()
    return "\n\n".join(chunks).strip()
