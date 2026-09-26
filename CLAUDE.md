# Instruções para o Claude neste projeto

Este repositório é uma ferramenta que converte PDFs em Markdown **preservando o
número da página da publicação original**, para montar um vault no Obsidian que
possa ser citado com segurança.

**Quem usa isto costuma ser pesquisador, não programador.** Fale em português, sem
jargão, e prefira executar as coisas a explicar como executá-las. Nunca responda
"rode este comando" quando você mesmo pode rodar.

## A regra que vale mais que todas

Uma nota bonita com a página errada é pior que uma nota crua com a página certa.
Antes de dar qualquer conversão por concluída, verifique de onde veio a numeração e
**diga isso ao usuário**. O campo `page_numbering` do cabeçalho de cada nota tem a
resposta:

| valor | significa | o que dizer |
| --- | --- | --- |
| `embedded` | o próprio PDF declara os rótulos de página | pode citar direto |
| `detected` | os números impressos foram lidos e conferidos entre si | pode citar direto |
| `offset` | o deslocamento foi informado na conversão | confie no que foi informado |
| `pdf` | não foi possível descobrir: está contando folhas | **avise que precisa conferir antes de citar** |

## Como rodar

O ambiente fica em `.venv` na raiz do projeto. Use sempre o Python de dentro dele:

```bash
.venv\Scripts\python.exe -m pdf2md "<pasta ou arquivo>"
```

**Nao pergunte onde fica o vault na primeira vez.** O programa procura sozinho uma
pasta de vault na Area de Trabalho (a que tiver um `000 - Acervo.md` dentro, ou cujo
nome fale em vault), guarda a escolha e passa a usar sempre. Sem `-o`, ele grava no
vault e ja atualiza o indice. Use `-o "<pasta>"` apenas quando o usuario pedir outro
destino, e `--definir-vault "<pasta>"` para trocar o padrao.

- aceita arquivos e pastas misturados; pastas são varridas com subpastas;
- `--indices` monta o índice do vault no fim (só funciona junto com `-o`);
- outras opções: `--modo-pagina auto|embedded|detect|offset|pdf`, `--offset -16`,
  `--marcador both|comment|heading|inline|none`, `--por-pagina`, `--imagens`, `--ocr`.

Para abrir a interface gráfica: `abrir.bat`. Para instalar do zero: `instalar.bat`.

Se o ambiente não existir, rode `instalar.bat` antes de qualquer coisa. Se o Python
não estiver instalado na máquina: `winget install -e --id Python.Python.3.12`.

## Tarefas comuns

**"Converte esses PDFs"** → rode o comando acima sem `-o`. A primeira linha da saída
diz em que vault ele gravou; confira se faz sentido e siga. Ao final relate: quantas obras, quantas páginas, quantas com numeração confiável e a lista das
que precisam ser conferidas.

**"A página está errada nessa obra"** → peça ao usuário o número impresso numa folha
qualquer do PDF e em que folha ela está. Calcule `deslocamento = impressa - folha` e
reconverta só aquela obra com `--modo-pagina offset --offset <valor>`.

**"Atualiza o índice"** → `.venv\Scripts\python.exe -m pdf2md.indices "<pasta do vault>"`.

**"Esse PDF não tem texto"** → é escaneado. O OCR exige instalar o Tesseract
(`winget install -e --id UB-Mannheim.TesseractOCR`) e os pacotes
`pip install pytesseract pillow`. **Peça autorização antes de instalar qualquer coisa.**
Avise também que o OCR não ajuda na numeração: em livro escaneado use deslocamento
manual.

## Limites que você deve respeitar

- **Nunca faça commit do vault nem dos PDFs convertidos.** São material de terceiros
  e o repositório é público. Só o código da ferramenta entra no git.
- Não altere notas já geradas para "melhorar" o texto: se algo saiu errado, corrija a
  conversão e reconverta.
- Ao reconverter uma obra que já existe no vault, o programa sobrescreve a nota dela;
  se o usuário anotou dentro da nota, avise antes que ele vai perder as anotações.

## Como o código está organizado

```
app.py               interface gráfica (Tkinter)
tooltip.py           balões de ajuda da interface
pdf2md/
  extract.py         lê o PDF com posição, fonte e tamanho de cada linha
  pagelabels.py      descobre a página impressa de cada folha  <- parte crítica
  mdwriter.py        monta o Markdown (parágrafos, títulos, listas, tabelas)
  converter.py       junta tudo, escreve o cabeçalho YAML e grava
  indices.py         monta os índices do vault
  cli.py             linha de comando
```

Ao mexer em `pagelabels.py`, lembre: qualquer heurística nova precisa ser
conservadora e, na dúvida, cair para um modo declarado no `page_numbering` — o usuário
precisa saber o quanto confiar. Teste sempre em PDFs reais de vários tipos (livro com
capa, artigo de periódico que começa numa página alta, texto em duas colunas) antes de
dar por resolvido.

O `MANUAL.md` explica cada opção em detalhe e é a referência para responder dúvidas
sobre comportamento.
