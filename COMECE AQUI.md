# Comece aqui

Este programa transforma seus PDFs em arquivos de texto (`.md`) que o Obsidian lê e
que o Claude consegue citar **com a página certa da publicação**.

Você não precisa saber programar. São três passos, uma vez só.

---

## Passo 1 — Baixar o programa

Na página do projeto no GitHub, clique no botão verde **Code** e depois em
**Download ZIP**. Salve na sua Área de Trabalho e descompacte (botão direito →
*Extrair tudo*).

Você vai ficar com uma pasta chamada `pdftransformer`.

---

## Passo 2 — Instalar

Abra a pasta e dê dois cliques em **`instalar.bat`**.

Uma janela preta vai aparecer e escrever algumas coisas. Quando ela disser
**"Pronto!"**, pode fechar. Isso só precisa ser feito uma vez.

> **Se aparecer "Python não encontrado":** abra a mesma pasta, clique na barra de
> endereço lá em cima, escreva `cmd` e dê Enter. Na janela preta, cole isto e dê
> Enter:
>
> ```
> winget install -e --id Python.Python.3.12
> ```
>
> Espere terminar, feche a janela e rode o `instalar.bat` de novo.

---

## Passo 3 — Usar

Você tem dois caminhos. Pode usar os dois.

### Caminho A — a janela do programa

Dois cliques em **`abrir.bat`**.

1. Arraste seus PDFs para a lista.
2. Clique em **Conferir numeração** e veja se a página bate com a do livro.
3. Desmarque *"Salvar numa subpasta markdown"* e escolha a pasta do seu vault.
4. **Converter**.

Pare o mouse em cima de qualquer botão ou caixa para ver o que ele faz. Tudo na tela
tem explicação.

### Caminho B — pedindo ao Claude

Abra o **Claude Code** dentro da pasta `pdftransformer`. Ele já vem com instruções
prontas aqui dentro, então é só falar normalmente:

> converte os PDFs da minha pasta Downloads para o meu vault do Obsidian

> a página da citação desse livro saiu errada, arruma

> atualiza o índice do vault

Na primeira vez ele vai perguntar onde fica o seu vault. Depois disso, não pergunta
mais.

---

## O que você recebe

Para cada PDF, uma nota `.md` com:

- o texto limpo, com parágrafos inteiros (palavras cortadas por hífen são reunidas);
- **um marcador no início de cada página da publicação**, assim:

  ```
  <!-- page: 143 | pdf: 157 -->
  ###### p. 143
  ```

  O primeiro é invisível quando você lê no Obsidian; o segundo aparece no painel de
  navegação e permite link direto para a página;
- uma ficha no topo com título, autor, arquivo de origem e **de onde veio a
  numeração** — é isso que te diz o quanto confiar.

E, na raiz da pasta, um arquivo **`000 - Acervo.md`** com a lista de tudo, quantas
páginas cada obra tem e quais precisam ser conferidas antes de citar.

---

## Por que a numeração importa tanto

A folha 157 do arquivo PDF quase nunca é a página 157 do livro: existe capa, folha de
rosto, sumário. Se a nota usar o número da folha, **toda citação sua sai deslocada**.

O programa tenta descobrir o número impresso de verdade, e sempre te conta como
descobriu:

| O que aparece | Significa |
| --- | --- |
| `rótulos embutidos no PDF` | o próprio arquivo informa. Pode citar. |
| `números impressos detectados` | ele leu os números do rodapé e conferiu entre si. Pode citar. |
| `deslocamento manual` | você informou a diferença. |
| `numeração do próprio PDF` | não deu para descobrir — **confira antes de citar**. |

Quando cai no último caso, é fácil resolver: abra o PDF, veja o número impresso numa
folha qualquer, e informe a diferença. Ou peça ao Claude: *"na folha 17 desse PDF está
impresso o número 1, arruma"*.

---

## Usando com o Claude depois

Com o vault pronto, você pode conectar a pasta a um Projeto do Claude, ou abrir o
Claude Code na pasta do vault. Uma instrução que funciona bem:

> Responda apenas com base nas notas fornecidas. Sempre que afirmar algo, cite a fonte
> no formato (Autor, p. N), usando o número do marcador `p. N` imediatamente anterior
> ao trecho que você usou.

---

## Se algo der errado

- **A janela não abre:** rode o `instalar.bat` de novo e leia a última linha.
- **A nota saiu vazia:** o PDF é escaneado (é uma foto da página, não texto). Precisa
  de OCR — peça ajuda ao Claude, ele sabe o que instalar.
- **O título da nota está errado:** ele é adivinhado a partir do PDF. Abra a nota e
  corrija a linha `title:`. Leva dois segundos.
- **Qualquer outra dúvida:** o arquivo `MANUAL.md` explica cada botão, cada caixa e
  cada mensagem do programa.
