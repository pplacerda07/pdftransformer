"""Uso pela linha de comando: python -m pdf2md arquivo.pdf [...] [opcoes]"""
from __future__ import annotations

import argparse
import os
import sys

from .converter import convert_file
from .model import Options


def _collect(paths: list[str]) -> list[str]:
    out: list[str] = []
    for p in paths:
        if os.path.isdir(p):
            for base, _d, names in os.walk(p):
                out += [os.path.join(base, n) for n in sorted(names)
                        if n.lower().endswith(".pdf")]
        elif p.lower().endswith(".pdf"):
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pdf2md",
        description="Converte PDFs em Markdown preservando a pagina da publicacao.")
    ap.add_argument("entrada", nargs="+", help="arquivos .pdf ou pastas")
    ap.add_argument("-o", "--saida", help="pasta de saida (padrao: ./markdown ao lado do PDF)")
    ap.add_argument("--modo-pagina", default="auto",
                    choices=["auto", "embedded", "detect", "offset", "pdf"])
    ap.add_argument("--offset", type=int, default=0,
                    help="pagina impressa = pagina do pdf + offset")
    ap.add_argument("--marcador", default="both",
                    choices=["both", "comment", "heading", "inline", "none"])
    ap.add_argument("--sem-frontmatter", action="store_true")
    ap.add_argument("--por-pagina", action="store_true", help="gera tambem um .md por pagina")
    ap.add_argument("--imagens", action="store_true")
    ap.add_argument("--ocr", action="store_true")
    args = ap.parse_args(argv)

    files = _collect(args.entrada)
    if not files:
        print("Nenhum PDF encontrado.", file=sys.stderr)
        return 1

    opts = Options(
        page_mode=args.modo_pagina,
        manual_offset=args.offset,
        marker_style=args.marcador,
        frontmatter=not args.sem_frontmatter,
        per_page_files=args.por_pagina,
        extract_images=args.imagens,
        ocr=args.ocr,
        output_dir=args.saida,
    )

    falhas = 0
    for path in files:
        try:
            res = convert_file(path, opts, log=print)
            for w in res.warnings:
                print(f"    aviso: {w}")
        except Exception as exc:
            falhas += 1
            print(f"ERRO  {path}: {exc}", file=sys.stderr)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
