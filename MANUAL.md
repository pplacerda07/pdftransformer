# Manual do PDF para Markdown

Este manual explica **o que faz cada coisa** do programa: cada botão, cada caixa,
cada campo do arquivo gerado e cada mensagem que pode aparecer.

> **Atalho:** dentro do programa, pare o mouse sobre qualquer item e espere um
> instante — aparece um balão com a explicação resumida daquele item. Este manual é
> a versão longa desses balões.

**Índice**

1. [O que o programa faz](#1-o-que-o-programa-faz)
2. [O uso normal, em quatro passos](#2-o-uso-normal-em-quatro-passos)
3. [Cartão 1 — Os arquivos](#3-cartão-1--os-arquivos)
4. [Cartão 2 — A numeração das páginas](#4-cartão-2--a-numeração-das-páginas)
5. [Cartão 3 — Saída e limpeza do texto](#5-cartão-3--saída-e-limpeza-do-texto)
6. [O rodapé: progresso, registro e botões](#6-o-rodapé-progresso-registro-e-botões)
7. [O arquivo gerado, linha por linha](#7-o-arquivo-gerado-linha-por-linha)
8. [Usando no Obsidian e no Claude](#8-usando-no-obsidian-e-no-claude)
9. [Mensagens e avisos: o que fazer](#9-mensagens-e-avisos-o-que-fazer)
10. [Receitas para casos comuns](#10-receitas-para-casos-comuns)
10b. [Perguntas frequentes](#10b-perguntas-frequentes)
11. [Linha de comando](#11-linha-de-comando)
12. [Instalação e arquivos do programa](#12-instalação-e-arquivos-do-programa)

---

## 1. O que o programa faz

Ele lê PDFs que **já têm texto** e grava, para cada um, um arquivo `.md` (Markdown)
com o texto limpo e com marcadores dizendo onde começa cada página da publicação
original.

O objetivo não é deixar o `.md` parecido com a página impressa. É que você, ou uma
IA lendo a nota, consiga dizer com segurança **"isto está na página 143"** na hora de
citar.

**O que ele não faz:** não lê PDF escaneado sem ajuda (veja
[OCR](#ocr-em-páginas-sem-texto)), não abre PDF protegido por senha e não altera o
PDF original em momento nenhum — ele só lê.

Para abrir: dê dois cliques em **`abrir.bat`**.

---

## 2. O uso normal, em quatro passos

1. **Arraste os PDFs** para a lista (ou clique em *Adicionar PDFs*).
2. Clique em **Conferir numeração** e veja se a página bate com a do livro.
3. Confira a pasta de destino no cartão 3.
4. Clique em **Converter**.

As opções já vêm marcadas de um jeito que serve para quase tudo. Os cartões 2 e 3
só precisam da sua atenção quando alguma coisa sair errada.

---

## 3. Cartão 1 — Os arquivos

### A lista

A tabela mostra tudo o que será convertido. Três colunas:

| Coluna | O que mostra |
| --- | --- |
| **ARQUIVO** | O nome do PDF. |
| **PASTA** | Onde ele está no seu computador — útil quando há dois arquivos com o mesmo nome. |
| **SITUAÇÃO** | O andamento daquele arquivo. |

A coluna SITUAÇÃO pode mostrar:

- **na fila** (cinza) — ainda não começou.
- **convertendo...** (lilás) — está sendo lido agora.
- **24 páginas** (verde) — pronto, e diz quantas páginas tinha.
- **erro** (vermelho) — o arquivo não pôde ser lido (não é um PDF válido, está
  corrompido ou em uso por outro programa).
- **não convertido** (vermelho) — o arquivo abriu, mas nenhum `.md` foi gravado. Na
  prática, é o caso do **PDF protegido por senha**.

Clicar numa linha **seleciona** aquele arquivo. Isso importa para dois botões:
*Remover* e *Conferir numeração*.

### Arrastar e soltar

Você pode arrastar arquivos do Explorador do Windows direto para a lista. Só entram
arquivos `.pdf`: se você arrastar uma pasta ou um `.docx` junto, eles são ignorados
em silêncio — nada quebra, apenas não aparecem na lista.

### Os botões

| Botão | O que faz |
| --- | --- |
| **Adicionar PDFs** | Abre a janela do Windows para escolher arquivos. Segure `Ctrl` para marcar vários. |
| **Adicionar pasta** | Você aponta uma pasta e ele varre **também todas as subpastas**, colocando na lista todo PDF que encontrar. É o caminho para um acervo inteiro. |
| **Remover** | Tira da lista só o que estiver selecionado. Não apaga nada do computador. |
| **Limpar** | Esvazia a lista inteira. Também não apaga nada do computador. |

Um arquivo que já está na lista não entra duas vezes. À direita, o contador mostra
quantos arquivos estão na fila.

---

## 4. Cartão 2 — A numeração das páginas

**Este é o cartão que decide se a sua citação vai sair certa.** Vale ler com calma
uma vez; depois disso ele quase não precisa ser tocado.

### Folha do PDF ≠ página da publicação

Um livro digitalizado tem capa, folha de rosto, ficha catalográfica e sumário antes
da página 1. Então a **folha 17 do PDF** costuma ser a **página 1 do livro**. Se a
nota usar o número da folha, toda citação sua sairá deslocada.

O programa tenta descobrir o número impresso de verdade e é isso que vai para o
marcador.

### "Como descobrir a página impressa" — as cinco opções

| Opção | O que faz | Quando usar |
| --- | --- | --- |
| **Automático** (padrão) | Tenta nesta ordem: 1) os rótulos embutidos no PDF; 2) os números impressos nas margens; 3) o deslocamento que estiver na caixinha, se for diferente de 0; 4) a folha do PDF — e neste caso **avisa** no registro. | Deixe assim. É o certo em quase todos os casos. |
| **Somente rótulos embutidos no PDF** | Só aceita a numeração que o próprio arquivo declara — e só se pelo menos 80% das folhas tiverem rótulo e eles forem suficientemente variados (um PDF que repete o mesmo rótulo em tudo é recusado). | Quando você confia no arquivo e quer que ele ignore números impressos que estejam confundindo a leitura. |
| **Somente números impressos nas margens** | Pula os rótulos embutidos e lê o rodapé/cabeçalho. | Quando o PDF tem rótulos embutidos **errados** (acontece em arquivos remontados). |
| **Deslocamento manual** | Ignora as duas descobertas e aplica a conta que você informar. | Quando você já sabe a diferença e quer garantia. |
| **Usar a folha do próprio PDF** | Numera 1, 2, 3… conforme as folhas. | Material sem numeração nenhuma, ou quando a página do original não importa. |

Nas duas opções "Somente…", se a descoberta falhar o programa avisa no registro
dizendo exatamente por quê.

### O campo Deslocamento

A conta é:

```
página impressa = folha do PDF + deslocamento
```

| Situação | Deslocamento |
| --- | --- |
| A página 1 do livro está na folha 17 do PDF | **-16** |
| O PDF é um capítulo solto que começa na página 145 do original | **+144** |
| A folha 1 já é a página 1 | **0** |

O campo só pode ser **digitado** quando você escolhe *Deslocamento manual*. Mas
atenção a um detalhe: **o valor que ficar guardado ali continua valendo como último
recurso no modo Automático** — se o programa não achar rótulos nem números
impressos, ele aplica esse deslocamento em vez de cair na folha do PDF. Se você não
quer isso, deixe o campo em 0.

Se o campo ficar vazio ou com texto que não seja número, o programa usa 0 em vez de
dar erro.

**Páginas de rosto:** quando a conta cai antes do início da numeração (folha 2 com
deslocamento -16, por exemplo), o programa **não inventa** "página -14". Ele usa o
número romano impresso, se houver (`i`, `ii`, `iii`), e senão marca a folha como
`folha 2 (sem numeracao)`.

### "Marcador que aparece no texto" — as cinco opções

Define como a virada de página aparece dentro da nota. Em todas elas o marcador fica
num parágrafo só dele, no início da página:

| Opção | O que escreve no arquivo |
| --- | --- |
| **Comentário + título de página** (padrão) | `<!-- page: 23 \| pdf: 27 -->` e, na linha seguinte, `###### p. 23` |
| **Somente comentário** | `<!-- page: 23 \| pdf: 27 -->` |
| **Somente título** | `###### p. 23` |
| **Marcador no meio do texto** | `**[p. 23]**` |
| **Sem marcador de página** | Nada. A nota vira texto corrido, sem referência de página. |

O trecho `| pdf: 27` só aparece quando a página impressa é diferente da folha do PDF.

### O botão Conferir numeração

Analisa o PDF **selecionado na lista** (ou o primeiro, se nenhum estiver selecionado)
e abre uma janela com:

- a **origem** da numeração — é a informação mais importante da janela;
- a tabela `folha do PDF → página da publicação`, onde as folhas sem número
  impresso aparecem como `(sem numeracao)`.

Ele lê **até 60 folhas** e mostra **até 40 linhas** na tabela. A janela não trava o
programa: você pode deixá-la aberta e mexer nas opções.

**Como usar de verdade:** abra o PDF no seu leitor, vá até uma folha qualquer do
miolo e compare o número impresso na página com o que a tabela diz. Se não bater,
feche a janela, escolha *Deslocamento manual*, informe a diferença e confira de novo.

---

## 5. Cartão 3 — Saída e limpeza do texto

### Onde salvar

**"Salvar numa subpasta 'markdown' ao lado de cada PDF"** (marcado por padrão): cada
nota vai para uma pasta `markdown` criada ao lado do próprio PDF. As notas ficam
junto das fontes.

Desmarcando, você escolhe **uma pasta só** para tudo — por exemplo, a pasta do seu
vault do Obsidian. O campo e o botão *Escolher pasta* só ficam ativos nesse caso.

> **Cuidado:** se você digitar um caminho que não existe, o programa **cria** a pasta
> e grava ali. Um erro de digitação não dá mensagem de erro: ele produz uma pasta
> nova num lugar inesperado. Prefira o botão *Escolher pasta*.

**O programa lembra da sua pasta.** Da primeira vez ele procura sozinho um vault na
Área de Trabalho (a pasta que tiver um `000 - Acervo.md` dentro, ou cujo nome fale em
vault) e guarda a escolha. Da segunda em diante, a pasta já vem preenchida, e arrastar
um PDF em cima do `converter.bat` grava direto nela com o índice atualizado. Para
trocar, basta escolher outra pasta na janela e converter uma vez.

**Quando já existe uma nota com aquele nome:** se ela veio do **mesmo PDF**, é
substituída — é o que você espera ao reconverter para corrigir a numeração. Se veio
de **outro PDF** (dois `cap1.pdf` em pastas diferentes, por exemplo), a nova é gravada
como `cap1 (2).md` e o registro avisa. Nenhuma nota é apagada em silêncio.

### As onze caixas

Todas vêm marcadas, menos as três últimas.

#### Cabeçalho YAML com a fonte — *marcada*
Escreve no topo da nota o bloco entre `---` com título, autor, arquivo de origem,
caminho completo, total de folhas, de onde veio a numeração e a data da conversão.
É o que o Obsidian lê como **propriedades** da nota. Detalhe de cada campo na
[seção 7](#7-o-arquivo-gerado-linha-por-linha).

#### Nota de contexto para a IA — *marcada*
Acrescenta um quadro `> [!info]` explicando o que os marcadores significam e pedindo
que a citação use o número do marcador anterior ao trecho. É o que faz o Claude
citar a página certa. O texto é fixo, muda apenas a frase que diz a origem da
numeração.

#### Detectar títulos — *marcada*
Transforma em títulos (`##`, `###`…) as linhas que se destacam do corpo do texto.
Uma linha vira título quando:

- está numa fonte **mais de 12% maior** que a do corpo; **ou**
- tem **mais de 70% dos caracteres em negrito**, no máximo 90 caracteres, não termina
  em `.`, `,` ou `;`, e tem pelo menos o tamanho do corpo; **ou**
- começa com uma destas palavras: *Capítulo*, *Parte*, *Seção*, *Unidade*, *Anexo*,
  *Apêndice*, *Introdução*, *Conclusão*, *Referências*, *Bibliografia*, *Resumo*,
  *Abstract* ou *Sumário* — com as mesmas restrições de tamanho.

Os títulos gerados vão de `##` a `#####`. O nível `######` fica **reservado para os
marcadores de página**.

Desmarque se o seu material tiver muitos destaques soltos virando título à toa.

#### Remover cabeçalho/rodapé repetido — *marcada*
Tira o título do livro ou do capítulo impresso em toda página. Uma linha só é
removida se estiver na margem (topo ou base da folha), tiver mais de 3 caracteres e
se repetir em **pelo menos 35% das páginas** (no mínimo 3).

Desmarque se notar que algum texto útil está sumindo.

#### Juntar palavras com hifen — *marcada*
Une palavras cortadas na quebra de linha: `pro-` no fim de uma linha e `cesso` no
início da seguinte viram `processo`. Sem isso a IA lê palavras partidas e a busca por
termos falha. Hífens legítimos no meio da linha (`guarda-chuva`) não são tocados.

#### Preservar negrito e italico — *marcada*
Mantém os destaques do original como `**negrito**` e `*itálico*`.

#### Converter tabelas — *marcada*
Reconhece tabelas e escreve em formato de tabela do Markdown. Ele descarta as linhas
totalmente vazias e só aceita o que sobrar se houver pelo menos 2 linhas e a primeira
tiver 2 células. O texto que estiver com mais de 60% da sua área dentro da tabela sai
do corpo (para não aparecer duas vezes).

Desmarque se as tabelas do seu material saírem embaralhadas — sem a opção, o conteúdo
sai como texto corrido, o que às vezes é mais legível para a IA.

#### Detectar duas colunas — *marcada*
Lê a coluna da esquerda inteira antes da direita, como em artigos de periódico. Sem
isso, as frases das duas colunas saem intercaladas e o texto perde o sentido.

#### Extrair imagens — *desmarcada*
Salva as figuras numa pasta `assets` e referencia na nota.

Dois detalhes importantes: as imagens de uma página saem **todas juntas no fim do
texto daquela página**, não no ponto exato onde estavam; e figuras com menos de 60
pixels de largura ou altura são ignoradas, assim como gráficos desenhados com traços
vetoriais (só imagens de verdade são extraídas).

#### Também uma nota por página — *desmarcada*
Além da nota única, cria uma pasta `NomeDoPDF - paginas` com um arquivo por página.
Cada um traz um YAML próprio e links `<- anterior` / `proxima ->` — o primeiro tem só
"próxima" e o último só "anterior".

Nesses arquivos a nota de contexto para a IA não é escrita e o menu de marcador não
vale: o título é sempre `# p. N`.

> Um livro de 300 páginas vira 300 arquivos no seu vault. Use com parcimônia.

#### OCR em páginas sem texto — *desmarcada*
Para PDFs escaneados. Veja [OCR](#ocr-em-páginas-sem-texto) na seção de mensagens.

---

## 6. O rodapé: progresso, registro e botões

**A barra de progresso** anda **dentro do arquivo que está sendo convertido**, página
por página. Para acompanhar o lote inteiro, olhe a coluna SITUAÇÃO da lista. Ela
chega a 100% e o programa ainda leva um instante montando e gravando o arquivo — não
é travamento.

**O registro** mostra uma linha por arquivo. As cores:

- **verde** — convertido, com o número de páginas e a origem da numeração;
- **laranja** — atenção: páginas sem texto, numeração duvidosa, PDF com senha;
- **vermelho** — o arquivo não pôde ser lido;
- **cinza** — mensagens do próprio programa ("3 arquivo(s) adicionado(s)").

As linhas da lista também mudam de cor, com o mesmo significado.

> **Importante num acervo grande:** o registro **não é salvo em lugar nenhum** — ele
> some ao fechar o programa. Antes de fechar depois de converter centenas de
> arquivos, olhe as linhas laranja e vermelhas e anote quais precisam de atenção.

**Os botões:**

| Botão | O que faz |
| --- | --- |
| **Converter** | Converte tudo o que está na lista. Roda em segundo plano: a janela continua respondendo e você pode usar o computador. |
| **Cancelar** | Interrompe. Os arquivos já concluídos continuam salvos; o que estava no meio é descartado. Só fica ativo durante a conversão. |
| **Abrir pasta de saída** | Abre a pasta das notas no Explorador do Windows. Só fica ativo depois que o primeiro arquivo termina. |

---

## 7. O arquivo gerado, linha por linha

```markdown
---
title: "Avaliação na Escola Básica"
author: "Maria Souza"
source_file: "avaliacao.pdf"
source_path: "C:\\Users\\pedro\\Documentos\\avaliacao.pdf"
pdf_pages: 240
page_numbering: "detected"
page_numbering_note: "numeros impressos detectados (deslocamento -4)"
first_page_label: "i"
converted: 2026-09-24
tool: pdftransformer
tags:
  - pdf
  - fonte
---

> [!info] Numeracao de paginas
> Cada marcador de pagina (o titulo `p. N` e o comentario HTML logo acima dele)
> indica o **inicio da pagina N da publicacao original**. Origem da numeracao:
> numeros impressos detectados (deslocamento -4).
> Ao citar este documento, use o numero do marcador imediatamente anterior ao trecho.

# Avaliação na Escola Básica

<!-- page: 23 | pdf: 27 -->
###### p. 23

A avaliação formativa difere da somativa porque acompanha o processo...
```

### Os campos do cabeçalho

| Campo | O que é |
| --- | --- |
| `title` | O título. **Não é digitado por ninguém** — veja o aviso abaixo. |
| `author` | O autor gravado dentro do PDF. Só aparece se existir. |
| `source_file` | O nome do PDF de origem. |
| `source_path` | O caminho completo **do arquivo**, com o nome do PDF no fim. As barras aparecem duplicadas, o que é normal em YAML. |
| `pdf_pages` | Quantas **folhas** o PDF tem (não é a última página impressa). |
| `page_numbering` | De onde veio a numeração: `embedded`, `detected`, `offset` ou `pdf`. |
| `page_numbering_note` | A mesma informação em português. Quando é `detected`, traz sempre o deslocamento entre parênteses, com sinal — inclusive `(deslocamento +0)`. |
| `first_page_label` | O rótulo da primeira folha, ou `sem numeracao`. |
| `converted` | A data da conversão. |
| `tool` | Sempre `pdftransformer`. |
| `tags` | `pdf` e `fonte`, para você filtrar no Obsidian. |

> **Sobre o `title`:** o programa usa, nesta ordem, o título gravado dentro do PDF;
> se não houver, a maior linha de texto das duas primeiras páginas; e, em último
> caso, o nome do arquivo. Por isso às vezes sai uma frase de capa no lugar do
> título. **Vale conferir e corrigir essa linha** nas obras que você for citar — é
> uma edição de dois segundos na nota.

### Os marcadores de página

- `<!-- page: 23 | pdf: 27 -->` — comentário. **Não aparece** na leitura do Obsidian,
  mas está no arquivo: a IA lê, a busca acha e você sabe em que folha do PDF procurar.
- `###### p. 23` — título de nível 6. **Aparece** na leitura e no painel de navegação,
  e é o que permite o link direto para a página.
- `###### folha 3 (sem numeracao)` — quando aquela folha não tem número impresso.

### Valores de `page_numbering` e o quanto confiar

| Valor | Significa | Confiança |
| --- | --- | --- |
| `embedded` | O próprio PDF declara os rótulos. | Máxima |
| `detected` | Números impressos lidos das margens e conferidos entre si. | Alta |
| `offset` | O deslocamento que você informou. | A sua |
| `pdf` | Nada foi descoberto: está contando folhas. | **Confira antes de citar** |

---

## 8. Usando no Obsidian e no Claude

**Link direto para uma página:**

```markdown
[[avaliacao#p. 23]]
```

**Buscar por página** na busca do Obsidian:

```
page: "23"
```

(as aspas importam — é assim que o campo é escrito nas notas por página).

**Instrução para o Claude** — cole junto com as notas:

> Responda apenas com base nas notas fornecidas. Sempre que afirmar algo, cite a
> fonte no formato (Autor, p. N), usando o número do marcador `p. N` imediatamente
> anterior ao trecho que você usou. Se o trecho estiver numa folha marcada como "sem
> numeracao", diga isso em vez de inventar um número.

---

## 9. Mensagens e avisos: o que fazer

### "N pagina(s) sem texto extraivel (ex.: 1, 2) - PDF escaneado?"
Aquelas páginas são imagem pura. No lugar do texto, a nota recebe
*"(pagina sem texto extraivel)"*. Se forem só a capa e a contracapa, ignore. Se for o
livro inteiro, você precisa de [OCR](#ocr-em-páginas-sem-texto).

### "Numeracao: ... Os marcadores estao usando a FOLHA do PDF"
O programa não conseguiu descobrir a página impressa. **Confira uma folha no leitor
de PDF** e, se não bater, use *Deslocamento manual*.

### "PDF protegido por senha - nao foi possivel abrir"
O arquivo é criptografado. Abra no seu leitor, salve uma cópia sem senha (imprimir
para PDF resolve) e converta a cópia.

### "Failed to open file ... as type pdf"
Não é um PDF válido, está corrompido, ou está aberto/bloqueado por outro programa.
Feche o arquivo e tente de novo.

### "Tesseract nao encontrado - o OCR sera ignorado"
Aparece ao clicar em Converter com a caixa de OCR marcada, e traz os comandos de
instalação. A conversão segue normalmente, só sem OCR.

### OCR em páginas sem texto

Para funcionar, precisa de **três** coisas instaladas:

```bash
winget install -e --id UB-Mannheim.TesseractOCR
```

```bash
.venv\Scripts\python.exe -m pip install pytesseract pillow
```

Depois marque a caixa. Quatro avisos honestos:

- o OCR só é acionado **nas páginas com menos de 25 caracteres de texto**, uma a uma.
  Num livro meio escaneado, só as páginas-imagem passam por ele;
- o texto reconhecido sai como **um parágrafo corrido** por página, sem títulos, sem
  negrito e sem quebras de parágrafo — o OCR não devolve a posição das linhas;
- o idioma é fixo em **português + inglês**. Livros em francês ou espanhol serão
  reconhecidos com erros;
- o OCR **não ajuda na numeração**: ele roda depois da leitura das margens, então um
  livro escaneado sempre cairá na folha do PDF. Use *Deslocamento manual* nesses
  casos.

---

## 10. Receitas para casos comuns

**Converter um acervo inteiro de uma vez**
*Adicionar pasta* → aponte a pasta raiz (ele varre as subpastas) → deixe a saída na
subpasta `markdown` → Converter. Depois, olhe o registro só para as linhas laranja e
vermelhas.

**A citação saiu com a página errada**
Conferir numeração → compare com o PDF aberto → *Deslocamento manual* → informe a
diferença → Conferir de novo → Converter.

**Um capítulo solto, numerado a partir da página 145**
*Deslocamento manual* com **+144** (se a folha 1 do PDF for a página 145).

**Quero as notas direto no vault do Obsidian**
Desmarque *"Salvar numa subpasta 'markdown'…"* → *Escolher pasta* → aponte a pasta de
fontes do seu vault.

**A nota ficou com título errado**
Abra o `.md` e corrija a linha `title:` e o `# Título`. Veja o aviso na
[seção 7](#7-o-arquivo-gerado-linha-por-linha).

---

## 10b. Perguntas frequentes

**Meus PDFs saem do computador? Vai alguma coisa para a internet?**
Não. Tudo acontece na sua máquina. O programa não tem login, não envia nada e não usa
inteligência artificial nenhuma para converter — a IA entra só depois, quando *você*
usa as notas. Internet só é necessária na instalação.

**Posso deixar 400 PDFs rodando à noite e usar o computador?**
Pode. Ele converte um por vez, em segundo plano. Só não feche a janela: fechar
durante a conversão interrompe tudo (os já concluídos ficam salvos). Não existe pausa,
só *Cancelar*. E lembre que o registro some ao fechar — veja o aviso na
[seção 6](#6-o-rodapé-progresso-registro-e-botões).

**Converte Word, EPUB ou foto de página?**
Não, só PDF. Fotos de páginas precisam virar PDF antes, e ainda assim exigem OCR.

**Dá para converter só as páginas 120 a 160?**
Não. Ele sempre converte o PDF inteiro. Para um recorte, extraia essas páginas no seu
leitor de PDF e converta o arquivo menor — nesse caso use *Deslocamento manual* para
que a numeração continue a do livro (folha 1 = página 120 → deslocamento **+119**).

**Se eu reconverter um PDF, perco as anotações que fiz na nota do Obsidian?**
Sim. A nota é reescrita do zero. Se você anota dentro das notas de fonte, crie uma
nota separada para os seus comentários e use links para as páginas — assim reconverter
nunca destrói o seu trabalho.

**O programa guarda as minhas escolhas?**
Não. Cada vez que você abre, tudo volta ao padrão: modo de numeração, deslocamento,
marcador, pasta de saída e as caixas. Para uma configuração fixa, use a
[linha de comando](#11-linha-de-comando).

**As imagens não aparecem na nota do Obsidian.**
Elas ficam em `markdown/assets/<nome do livro>/`. Se você mover o `.md` para outro
lugar, mova a pasta `assets` junto — o link é relativo à pasta da nota.

**Como sei se um PDF é escaneado antes de perder tempo?**
Tente selecionar o texto no seu leitor de PDF. Se não der, é imagem. O programa também
avisa: a nota sai com *"(pagina sem texto extraivel)"* e o registro mostra a linha
laranja dizendo quantas páginas ficaram assim.

**A conferência bateu no começo mas errou no meio do livro.**
A conferência lê só as 60 primeiras folhas. Num livro que reinicia a numeração por
parte, ou com anexos numerados à parte, o programa acompanha mudanças de numeração,
mas só quando há números impressos suficientes. Confira também uma folha do meio e
uma do fim abrindo o `.md` gerado.

**Os `###### p. 23` poluem minha leitura.**
Troque o marcador para *Somente comentário*: o comentário não aparece na leitura do
Obsidian, e a IA continua enxergando a página. Você perde o link direto
`[[nota#p. 23]]`.

**Um livro de 600 páginas virou um `.md` gigante. Tudo bem?**
Para o Obsidian, sim. Para dar de contexto ao Claude, prefira mandar o trecho que
interessa, ou marque *Também uma nota por página* nas obras que você consulta por
página.

**Como ficam as notas de rodapé?**
Os numerinhos de chamada entram grudados na palavra (`formativa12`) e o texto da nota
de rodapé aparece como um parágrafo comum no fim da página. O programa não separa
notas de rodapé.

**Posso apagar a pasta `markdown` e converter tudo de novo?**
Pode, sem medo. Ela é só resultado; o PDF original nunca é tocado.

**O Windows avisa ao abrir um `.bat`. É seguro?**
Esses três arquivos são texto simples, você pode abrir no Bloco de Notas e ler o que
eles fazem. O aviso aparece porque o arquivo veio de fora do computador.

---

## 11. Linha de comando

Para lotes grandes ou para repetir sempre a mesma configuração:

```bash
.venv\Scripts\python.exe -m pdf2md "C:\caminho\dos\pdfs" -o "C:\meu-vault\Fontes"
```

| Opção | Para que serve |
| --- | --- |
| `-o`, `--saida` | Pasta de destino. Sem ela, usa a subpasta `markdown` ao lado de cada PDF. |
| `--modo-pagina` | `auto`, `embedded`, `detect`, `offset` ou `pdf`. |
| `--offset -16` | O deslocamento. |
| `--marcador` | `both`, `comment`, `heading`, `inline` ou `none`. |
| `--sem-frontmatter` | Não escreve o cabeçalho YAML. |
| `--por-pagina` | Gera também uma nota por página. |
| `--imagens` | Extrai as imagens. |
| `--ocr` | Liga o OCR. |

As opcoes de limpeza do texto (detectar titulos, remover cabecalho/rodape, juntar
hifen, negrito, tabelas, duas colunas e a nota de contexto) **nao existem como
parametros** — na linha de comando elas ficam sempre ligadas.

Aceita arquivos e pastas misturados na mesma chamada. Você também pode arrastar um
PDF ou uma pasta para cima do **`converter.bat`**.

---

## 12. Instalação e arquivos do programa

| Arquivo | Para que serve |
| --- | --- |
| **`abrir.bat`** | Abre o programa. É o único que você usa no dia a dia. |
| **`instalar.bat`** | Prepara o ambiente. Só precisa ser rodado uma vez por computador — ou se você levar a pasta para outra máquina. |
| **`converter.bat`** | Conversão arrastando um PDF ou pasta para cima dele. |
| `app.py` | A janela do programa. |
| `tooltip.py` | Os balõezinhos de ajuda. |
| `pdf2md/` | O motor da conversão. |
| `requirements.txt` | A lista de bibliotecas necessárias. |
| `.venv/` | O ambiente Python instalado. Não precisa abrir, e não vai para o GitHub. |

O **`converter.bat`** abre uma janela preta que fica em silêncio enquanto trabalha:
cada arquivo só imprime a sua linha quando termina. Num livro grande, alguns segundos
sem nada na tela são normais.

**Se o programa não abrir:** se faltar só a biblioteca PyMuPDF, aparece uma caixa de
erro dizendo isso. Qualquer outra falha (Python quebrado, arquivo danificado) é
silenciosa, porque o `abrir.bat` roda sem janela de texto. Para ver o erro, abra a
pasta no Explorador, escreva `cmd` na barra de endereço, dê Enter e digite:

```bash
.venv\Scripts\python.exe app.py
```

Na dúvida, rode o `instalar.bat` e leia a última linha. Se ele disser que não
encontrou o Python, instale com:

```bash
winget install -e --id Python.Python.3.12
```

e rode o `instalar.bat` de novo.

**Levando para outro computador:** copie a pasta inteira (sem a `.venv`, que é
pesada), rode o `instalar.bat` lá e pronto.
