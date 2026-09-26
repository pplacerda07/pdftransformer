"""Guarda as preferencias entre uma sessao e outra.

A ideia e simples: quem usa isso todo dia nao deveria ter que dizer de novo
onde fica o vault. O arquivo fica fora do projeto, na pasta do usuario, para
nao ir parar no repositorio.
"""
from __future__ import annotations

import json
import os

PASTA = os.path.join(
    os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "pdftransformer")
ARQUIVO = os.path.join(PASTA, "config.json")


def ler() -> dict:
    try:
        with open(ARQUIVO, encoding="utf-8") as fh:
            dados = json.load(fh)
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def gravar(dados: dict) -> bool:
    try:
        os.makedirs(PASTA, exist_ok=True)
        atual = ler()
        atual.update(dados)
        with open(ARQUIVO, "w", encoding="utf-8") as fh:
            json.dump(atual, fh, ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


MARCA = "000 - Acervo.md"          # arquivo que so existe num vault deste programa


def _areas_de_trabalho() -> list[str]:
    casa = os.path.expanduser("~")
    nomes = ["Desktop", "Área de Trabalho", "Area de Trabalho"]
    pastas = [os.path.join(casa, n) for n in nomes]
    pastas += [os.path.join(casa, "OneDrive", n) for n in nomes]
    return [p for p in pastas if os.path.isdir(p)]


def descobrir_vault() -> str | None:
    """Procura um vault na Area de Trabalho, sem precisar perguntar nada.

    Vale como vault a pasta que ja tem o indice deste programa dentro; se nao
    houver nenhuma, aceita uma pasta cujo nome fale em vault.
    """
    candidatos = []
    for mesa in _areas_de_trabalho():
        try:
            for nome in sorted(os.listdir(mesa)):
                caminho = os.path.join(mesa, nome)
                if not os.path.isdir(caminho):
                    continue
                if os.path.exists(os.path.join(caminho, MARCA)):
                    return caminho
                if "vault" in nome.lower():
                    candidatos.append(caminho)
        except OSError:
            continue
    return candidatos[0] if candidatos else None


def vault(procurar: bool = True) -> str | None:
    """Pasta do vault: a escolhida antes ou, se nao houver, uma encontrada."""
    caminho = ler().get("vault")
    if caminho and os.path.isdir(caminho):
        return caminho
    if procurar:
        achado = descobrir_vault()
        if achado:
            definir_vault(achado)
            return achado
    return None


def definir_vault(caminho: str) -> bool:
    return gravar({"vault": os.path.abspath(caminho)})
