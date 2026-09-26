"""Monta os indices de um vault: um por pasta e um geral na raiz.

Le o cabecalho das proprias notas, entao funciona em qualquer pasta que tenha
sido gerada por este programa, mesmo que as notas tenham vindo aos poucos.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict

PREFIXO = "000 - "
NOME_RAIZ = PREFIXO + "Acervo.md"

_CAMPO = re.compile(r"^(\w+):\s*(.*)$")
_NUMERACAO = {
    "embedded": ("confiavel", "o proprio PDF declara a numeracao"),
    "detected": ("confiavel", "numeros impressos lidos e conferidos"),
    "offset": ("media", "deslocamento informado na conversao"),
    "pdf": ("CONFERIR", "nao foi possivel descobrir a pagina impressa"),
}


def _confianca(origem: str) -> tuple[str, str]:
    return _NUMERACAO.get(origem, ("CONFERIR", origem or "desconhecida"))


def _ler_nota(caminho: str) -> dict | None:
    try:
        texto = open(caminho, encoding="utf-8").read()
    except OSError:
        return None
    dados: dict = {}
    if texto.startswith("---"):
        fim = texto.find("\n---", 3)
        for linha in texto[3:fim if fim > 0 else 600].splitlines():
            m = _CAMPO.match(linha.strip())
            if m:
                dados[m.group(1)] = m.group(2).strip().strip('"')
    dados["sem_texto"] = texto.count("(pagina sem texto extraivel")
    paginas = dados.get("pdf_pages", "")
    total = int(paginas) if str(paginas).isdigit() else 0
    dados["escaneada"] = dados["sem_texto"] > 3 or (
        total > 0 and dados["sem_texto"] >= total * 0.6)
    return dados


def _nome_indice(pasta: str) -> str:
    """Nome unico: duas pastas podem ter o mesmo nome em niveis diferentes."""
    partes = [p for p in pasta.replace("\\", "/").split("/") if p] or ["Acervo"]
    return PREFIXO + "Indice - " + " - ".join(partes)


def _titulo_link(nome: str) -> str:
    return nome.replace("[", "(").replace("]", ")")


def montar(vault: str) -> dict:
    """Cria (ou refaz) os indices. Devolve um resumo com os numeros."""
    vault = os.path.abspath(vault)
    notas = []
    for raiz, _dirs, arqs in os.walk(vault):
        for a in arqs:
            if not a.endswith(".md") or a.startswith(PREFIXO):
                continue
            d = _ler_nota(os.path.join(raiz, a))
            if d is None:
                continue
            d["nome"] = os.path.splitext(a)[0]
            pasta = os.path.relpath(raiz, vault).replace("\\", "/")
            d["pasta"] = "" if pasta == "." else pasta
            notas.append(d)

    if not notas:
        return {"notas": 0}

    por_pasta: dict[str, list] = defaultdict(list)
    for n in notas:
        por_pasta[n["pasta"]].append(n)

    # vault plano (tudo numa pasta so): o indice da raiz ja da conta
    plano = list(por_pasta) == [""]

    for pasta, obras in sorted(por_pasta.items()):
        if plano:
            break
        nome_pasta = os.path.basename(pasta) or "Acervo"
        linhas = [
            "---",
            f'title: "Indice - {pasta or nome_pasta}"',
            "tags:",
            "  - indice",
            "---",
            "",
            f"# {nome_pasta}",
            "",
            f"{len(obras)} obra(s) nesta pasta.",
            "",
            "| Obra | Paginas | Numeracao |",
            "| --- | --- | --- |",
        ]
        for o in sorted(obras, key=lambda x: x["nome"].lower()):
            nivel, _ = _confianca(o.get("page_numbering", ""))
            linhas.append(f"| [[{_titulo_link(o['nome'])}]] | "
                          f"{o.get('pdf_pages', '?')} | {nivel} |")
        caminho = os.path.join(vault, pasta, _nome_indice(pasta) + ".md")
        with open(caminho, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(linhas) + "\n")

    conferir = [n for n in notas if _confianca(n.get("page_numbering", ""))[0] == "CONFERIR"]
    escaneadas = [n for n in notas if n["escaneada"]]
    paginas = sum(int(n["pdf_pages"]) for n in notas
                  if str(n.get("pdf_pages", "")).isdigit())

    raiz = [
        "---",
        'title: "Acervo"',
        "tags:",
        "  - indice",
        "---",
        "",
        "# Acervo",
        "",
        f"**{len(notas)} obras** convertidas de PDF para Markdown, "
        f"**{format(paginas, ',d').replace(',', '.')} paginas** no total.",
        "",
        "> [!tip] Como citar a partir daqui",
        "> Cada nota traz um marcador `p. N` no inicio de cada pagina da publicacao.",
        "> Para citar, use o numero do marcador imediatamente anterior ao trecho.",
        "> Para linkar uma pagina: abra a nota e use o titulo `p. 143` como ancora.",
        "",
    ]
    if plano:
        raiz += ["## Obras", "", "| Obra | Paginas | Numeracao |", "| --- | --- | --- |"]
        for o in sorted(notas, key=lambda x: x["nome"].lower()):
            nivel, _ = _confianca(o.get("page_numbering", ""))
            raiz.append(f"| [[{_titulo_link(o['nome'])}]] | "
                        f"{o.get('pdf_pages', '?')} | {nivel} |")
    else:
        raiz += ["## Pastas", "", "| Pasta | Obras | Indice |", "| --- | --- | --- |"]
        for pasta in sorted(por_pasta):
            raiz.append(f"| {pasta or '(raiz)'} | {len(por_pasta[pasta])} | "
                        f"[[{_nome_indice(pasta)}]] |")

    raiz += [
        "",
        "## Confianca da numeracao",
        "",
        f"- **{len(notas) - len(conferir)} obras** com a pagina da publicacao "
        "descoberta. Pode citar direto.",
        f"- **{len(conferir)} obras** em que nao foi possivel descobrir: os "
        "marcadores estao usando a folha do PDF.",
        "",
    ]
    if conferir:
        raiz += ["### Conferir antes de citar", ""]
        for o in sorted(conferir, key=lambda x: x["nome"].lower()):
            raiz.append(f"- [[{_titulo_link(o['nome'])}]] — "
                        f"{o.get('pdf_pages', '?')} folhas · `{o['pasta'] or 'raiz'}`")
        raiz += ["",
                 "> Abra o PDF, veja o numero impresso numa folha qualquer e compare "
                 "com o marcador. Se nao bater, reconverta essa obra usando "
                 "*Deslocamento manual*.", ""]

    raiz += ["## Escaneadas (paginas sem texto extraivel)", ""]
    if escaneadas:
        for o in sorted(escaneadas, key=lambda x: -x["sem_texto"])[:60]:
            raiz.append(f"- [[{_titulo_link(o['nome'])}]] — {o['sem_texto']} de "
                        f"{o.get('pdf_pages', '?')} paginas sem texto")
        raiz += ["", "> Estas precisam de OCR para virarem texto pesquisavel.", ""]
    else:
        raiz += ["Nenhuma.", ""]

    with open(os.path.join(vault, NOME_RAIZ), "w", encoding="utf-8",
              newline="\n") as fh:
        fh.write("\n".join(raiz) + "\n")

    return {
        "notas": len(notas),
        "paginas": paginas,
        "pastas": len(por_pasta),
        "confiaveis": len(notas) - len(conferir),
        "conferir": len(conferir),
        "escaneadas": len(escaneadas),
    }


if __name__ == "__main__":
    import sys

    destino = sys.argv[1] if len(sys.argv) > 1 else "."
    resumo = montar(destino)
    if not resumo.get("notas"):
        print("Nenhuma nota encontrada em", os.path.abspath(destino))
    else:
        print(f"indices atualizados em {os.path.abspath(destino)}")
        print(f"  {resumo['notas']} obras em {resumo['pastas']} pasta(s), "
              f"{resumo['paginas']} paginas")
        print(f"  numeracao confiavel: {resumo['confiaveis']} | "
              f"a conferir: {resumo['conferir']} | escaneadas: {resumo['escaneadas']}")
