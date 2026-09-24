"""Descobre qual e a pagina IMPRESSA de cada pagina do PDF.

Ordem de confianca:
1. rotulos embutidos no PDF (page labels) - o proprio arquivo diz "i, ii, ... 1, 2"
2. numeros detectados nas margens das paginas
3. deslocamento (offset) fixo informado pelo usuario
4. numero da pagina do PDF (ultimo recurso)
"""
from __future__ import annotations

from collections import Counter

from .extract import roman_to_int
from .model import Options, PageData

# tolerancia da altura do numero de pagina, em fracao da altura da folha
_Y_TOL = 0.02
# quantas paginas seguidas precisam concordar para valer uma renumeracao
_RUN = 3


class PageLabels:
    def __init__(self, labels: list[str], source: str, offset: int | None = None,
                 detail: str = ""):
        self.labels = labels
        self.source = source          # embedded | detected | offset | pdf
        self.offset = offset
        self.detail = detail

    def label(self, index: int) -> str:
        """Rotulo da pagina impressa, ou "" quando a folha nao tem numeracao."""
        if 0 <= index < len(self.labels):
            return self.labels[index]
        return ""

    @property
    def first_real(self) -> str:
        return next((l for l in self.labels if l), "")

    @property
    def human(self) -> str:
        if self.source == "embedded":
            return "rotulos embutidos no PDF"
        if self.source == "detected":
            if self.offset is not None:
                return f"numeros impressos detectados (deslocamento {self.offset:+d})"
            return "numeros impressos detectados"
        if self.source == "offset":
            desloc = f" ({self.offset:+d})" if self.offset is not None else ""
            return "deslocamento manual" + desloc
        if self.source == "pdf":
            return "numeracao do proprio PDF"
        return self.source


def _first_roman(page: PageData) -> str:
    for rom, _y, _line in page.printed_roman:
        if roman_to_int(rom):
            return rom
    return ""


def _offset_labels(pages: list[PageData], off: int) -> list[str]:
    """Aplica um deslocamento fixo sem inventar pagina 0 ou negativa.

    As folhas que caem antes do inicio da numeracao sao pre-textuais: usam o
    romano impresso, se houver, e senao ficam sem rotulo - melhor admitir que
    a folha nao tem numero do que escrever um numero errado numa citacao.
    """
    labels: list[str] = []
    for p in pages:
        valor = p.index + 1 + off
        if valor >= 1:
            labels.append(str(valor))
        else:
            labels.append(_first_roman(p))
    return labels


def _embedded(doc) -> list[str] | None:
    try:
        labels = [(doc[i].get_label() or "").strip() for i in range(doc.page_count)]
    except Exception:
        return None
    filled = [l for l in labels if l]
    if len(filled) < doc.page_count * 0.8:
        return None
    # rotulos identicos em todas as paginas nao servem para nada
    if len(set(filled)) < max(2, len(filled) * 0.5):
        return None
    return labels


def _modal_band(pages: list[PageData]) -> float | None:
    """Altura em que o numero de pagina costuma aparecer (rodape ou cabecalho)."""
    ys: Counter = Counter()
    for p in pages:
        for _num, y, _line in p.printed_numbers:
            ys[round(y / _Y_TOL)] += 1
    if not ys:
        return None
    bucket, count = ys.most_common(1)[0]
    if count < max(2, 0.15 * len(pages)):
        return None
    return bucket * _Y_TOL


def _candidates(pages: list[PageData], band: float | None) -> dict[int, list]:
    """Numeros plausiveis por pagina, ja filtrados pela altura tipica."""
    out: dict[int, list] = {}
    for p in pages:
        items = p.printed_numbers
        if band is not None:
            items = [it for it in items if abs(it[1] - band) <= _Y_TOL * 1.5]
        if items:
            out[p.index] = items
    return out


def _detect(pages: list[PageData]) -> tuple[list[str], int] | None:
    """Casa a numeracao impressa com as folhas do PDF.

    Usa o deslocamento dominante e so aceita uma mudanca de numeracao quando
    varias paginas seguidas concordam com ela - assim um numero solto de figura
    nao bagunca o documento inteiro.
    """
    band = _modal_band(pages)
    cands = _candidates(pages, band)
    if not cands:
        return None

    votes: Counter = Counter()
    for idx, items in cands.items():
        for num, _y, _line in items:
            if 0 < num < 10000:
                votes[num - (idx + 1)] += 1
    if not votes:
        return None
    dominant, count = votes.most_common(1)[0]
    if count < max(3, 0.2 * len(pages)):
        return None

    # deslocamento observado por pagina (so quando a pagina tem um numero)
    seen: dict[int, set] = {}
    for idx, items in cands.items():
        seen[idx] = {num - (idx + 1) for num, _y, _line in items if 0 < num < 10000}

    # uma renumeracao so vale se _RUN paginas numeradas seguidas concordarem
    numbered = sorted(seen)
    accepted: dict[int, int] = {}
    current = dominant
    i = 0
    while i < len(numbered):
        idx = numbered[i]
        if current in seen[idx]:
            accepted[idx] = current
            i += 1
            continue
        alt = None
        for cand in seen[idx]:
            run = 1
            for j in range(i + 1, min(i + _RUN, len(numbered))):
                if cand in seen[numbered[j]]:
                    run += 1
            if run >= min(_RUN, len(numbered) - i):
                alt = cand
                break
        if alt is not None:
            current = alt
            accepted[idx] = current
        i += 1

    if not accepted:
        return None

    # aplica: cada folha recebe o deslocamento em vigor naquele ponto
    labels: list[str] = []
    offset = dominant
    first_numbered = min(accepted)
    for p in pages:
        if p.index in accepted:
            offset = accepted[p.index]
        elif p.index < first_numbered:
            offset = accepted[first_numbered]
        value = p.index + 1 + offset
        if value >= 1 and (p.index >= first_numbered or value >= 1):
            labels.append(str(value))
        else:
            labels.append("")

    # folhas antes da numeracao arabica: usa o romano impresso, se houver
    for p in pages:
        if labels[p.index]:
            continue
        rom = ""
        for cand, y, _line in p.printed_roman:
            if band is None or abs(y - band) <= _Y_TOL * 1.5:
                rom = cand
                break
        labels[p.index] = rom if roman_to_int(rom) else ""

    # esconde do texto so os numeros que realmente sao numero de pagina
    for p in pages:
        for num, y, line in p.printed_numbers:
            if band is not None and abs(y - band) > _Y_TOL * 1.5:
                continue
            if str(num) == labels[p.index]:
                line.drop = True
        for rom, y, line in p.printed_roman:
            if band is not None and abs(y - band) > _Y_TOL * 1.5:
                continue
            if rom == labels[p.index]:
                line.drop = True

    return labels, dominant


def _drop_all_margin_numbers(pages: list[PageData]) -> None:
    """Sem deteccao confiavel, ainda assim tira o numero repetido do rodape."""
    band = _modal_band(pages)
    if band is None:
        return
    for p in pages:
        for _num, y, line in p.printed_numbers:
            if abs(y - band) <= _Y_TOL * 1.5:
                line.drop = True
        for _rom, y, line in p.printed_roman:
            if abs(y - band) <= _Y_TOL * 1.5:
                line.drop = True


def resolve(doc, pages: list[PageData], opts: Options) -> PageLabels:
    n = len(pages)
    mode = opts.page_mode

    if mode == "pdf":
        _drop_all_margin_numbers(pages)
        return PageLabels([str(i + 1) for i in range(n)], "pdf")

    if mode == "offset":
        _drop_all_margin_numbers(pages)
        off = opts.manual_offset
        return PageLabels(_offset_labels(pages, off), "offset", off)

    if mode in ("auto", "embedded"):
        emb = _embedded(doc)
        if emb:
            _drop_all_margin_numbers(pages)
            return PageLabels(emb, "embedded")
        if mode == "embedded":
            _drop_all_margin_numbers(pages)
            return PageLabels([str(i + 1) for i in range(n)], "pdf",
                              detail="o PDF nao tem rotulos de pagina embutidos")

    if mode in ("auto", "detect"):
        found = _detect(pages)
        if found:
            labels, dominant = found
            return PageLabels(labels, "detected", dominant)
        if mode == "detect":
            _drop_all_margin_numbers(pages)
            return PageLabels([str(i + 1) for i in range(n)], "pdf",
                              detail="nenhum numero impresso consistente foi encontrado")

    _drop_all_margin_numbers(pages)
    if opts.manual_offset:
        off = opts.manual_offset
        return PageLabels(_offset_labels(pages, off), "offset", off)

    return PageLabels([str(i + 1) for i in range(n)], "pdf")
