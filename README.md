# PDF → Markdown, com a página da publicação preservada

Converte qualquer PDF com texto em um arquivo `.md` limpo, marcando **onde começa
cada página da publicação original**. O objetivo não é parecer com a página: é que
você (e a IA que vai ler a nota) saibam com segurança de que página veio cada trecho
na hora de citar.

Feito para montar um vault no Obsidian e dar contexto ao Claude.

**Manual completo, item por item: [MANUAL.md](MANUAL.md).**
Dentro do programa, pare o mouse sobre qualquer botão ou caixa para ver o que ele faz.

---

## Como usar

1. Dê dois cliques em **`abrir.bat`**.
2. **Arraste os PDFs para a lista** (ou use **Adicionar PDFs** / **Adicionar pasta**, que varre subpastas inteiras).
3. Confira a numeração no botão **Conferir numeração do PDF selecionado...**.
4. **Converter**.

Por padrão os `.md` são salvos numa subpasta `markdown` ao lado dos PDFs. Desmarque a
opção para escolher direto a pasta do seu vault do Obsidian.

Se o programa ainda não estiver instalado nesta máquina, rode antes o **`instalar.bat`**.

---

## Como a numeração é descoberta

Esta é a parte que garante a citação. O programa tenta, nesta ordem:

| Origem | O que é | Confiança |
| --- | --- | --- |
| `embedded` | O próprio PDF traz os rótulos de página (`i, ii, … 1, 2, 3`). Comum em livros e teses. | Máxima |
| `detected` | O número impresso no rodapé/cabeçalho é lido e casado com as folhas do PDF. | Alta |
| `offset` | Você informa o deslocamento manualmente. | Você decide |
| `pdf` | Nada foi encontrado: usa a folha do PDF. | Último recurso |

A detecção é conservadora de propósito: só aceita números que aparecem **sempre na
mesma altura da folha** (é assim que um rodapé se comporta), e só aceita uma mudança de
numeração quando várias páginas seguidas concordam. Assim o "1" de uma legenda ou de um
diagrama não bagunça o documento inteiro.

**Quando o automático erra**, use *Deslocamento manual*:
se a página 1 do livro está na folha 17 do PDF, o deslocamento é **-16**.
O botão *Conferir numeração* mostra a tabela `folha do PDF → página da publicação`
antes de converter.

A origem usada fica registrada no cabeçalho do `.md` (`page_numbering`), então você
sempre sabe o quanto confiar naquela numeração.

---

## Como fica o arquivo gerado

```markdown
---
title: "Avaliação na Escola Básica"
author: "Maria Souza"
source_file: "avaliacao.pdf"
pdf_pages: 240
page_numbering: "detected"
page_numbering_note: "numeros impressos detectados (deslocamento -4)"
converted: 2026-09-24
tags:
  - pdf
  - fonte
---

> [!info] Numeração de páginas
> Cada marcador de página indica o início da página N da publicação original.

# Avaliação na Escola Básica

<!-- page: 23 | pdf: 27 -->
###### p. 23

A avaliação formativa difere da somativa porque acompanha o processo...
```

Os dois marcadores servem a públicos diferentes:

- `<!-- page: 23 | pdf: 27 -->` — invisível na leitura do Obsidian, fácil de achar por
  busca ou por script, e diz também em que folha do PDF aquilo está (útil para voltar
  ao original).
- `###### p. 23` — vira um item no painel de navegação do Obsidian e permite **link
  direto para a página**: `[[avaliacao#p. 23]]`.

---

## Usando com o Claude

Como cada página está demarcada, dá para exigir citação exata. Exemplo de instrução:

> Responda apenas com base nas notas fornecidas. Sempre que afirmar algo, cite a fonte
> no formato (Autor, p. N), usando o número do marcador `p. N` imediatamente anterior
> ao trecho que você usou.

---

## Opções da tela

| Opção | Para que serve |
| --- | --- |
| Cabeçalho YAML | Metadados da fonte no topo da nota (título, autor, arquivo de origem). |
| Nota explicando os marcadores | Um parágrafo dizendo à IA o que os marcadores significam. |
| Detectar títulos e subtítulos | Vira `##`, `###`… conforme o tamanho da fonte. O nível `######` fica reservado para as páginas. |
| Remover cabeçalho/rodapé repetidos | Tira o título do livro que se repete em toda página. |
| Juntar palavras separadas por hífen | `pro-` + `cesso` → `processo`. |
| Preservar negrito e itálico | Mantém `**negrito**` e `*itálico*`. |
| Converter tabelas | Tabelas viram tabelas Markdown. |
| Detectar duas colunas | Ordem de leitura correta em artigos e periódicos. |
| Extrair imagens | Salva as imagens em `assets/` e referencia na nota. |
| Gerar também uma nota por página | Cria uma pasta com um `.md` por página, com links de navegação. |
| OCR | Só para PDFs escaneados — exige o Tesseract instalado. |

---

## Linha de comando (para lotes grandes)

```bash
.venv\Scripts\python.exe -m pdf2md "C:\caminho\dos\pdfs" -o "C:\meu-vault\Fontes"
```

Principais opções: `--modo-pagina auto|embedded|detect|offset|pdf`, `--offset -16`,
`--marcador both|comment|heading|inline|none`, `--por-pagina`, `--imagens`, `--ocr`.

Você também pode arrastar um PDF ou uma pasta para cima do `converter.bat`.

---

## PDFs escaneados

Se o PDF for imagem pura (livro escaneado sem OCR), não há texto para extrair. O
programa avisa quais páginas ficaram vazias em vez de gerar uma nota silenciosamente
incompleta. Para converter esses casos, instale o OCR:

```bash
winget install -e --id UB-Mannheim.TesseractOCR
```

```bash
.venv\Scripts\python.exe -m pip install pytesseract pillow
```

Depois marque a opção **OCR** na tela.

---

## Organização do projeto

```
abrir.bat          abre o programa
instalar.bat       instala o ambiente e as bibliotecas
converter.bat      conversão arrastando arquivos
app.py             a interface
pdf2md/
  extract.py       lê o PDF com posição, fonte e tamanho de cada linha
  pagelabels.py    descobre a página impressa de cada folha
  mdwriter.py      monta o Markdown (títulos, parágrafos, listas, tabelas)
  converter.py     junta tudo e grava o arquivo
  cli.py           linha de comando
```
