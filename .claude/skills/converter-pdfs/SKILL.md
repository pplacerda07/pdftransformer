---
name: converter-pdfs
description: Converte PDFs em notas Markdown com a página da publicação preservada e atualiza o índice do vault. Use quando o usuário pedir para converter PDF, transformar PDF em markdown, adicionar textos ao vault, alimentar o Obsidian com bibliografia, ou quando perguntar por que a página de uma citação saiu errada.
---

# Converter PDFs para o vault

Fluxo completo, do PDF à nota citável. Execute os passos — não os descreva.

## 1. Descubra o que converter e para onde

- **De onde:** o usuário pode dar uma pasta, arquivos soltos, ou dizer "os PDFs que
  eu baixei". Se ficar ambíguo, pergunte uma vez e siga.
- **Para onde:** não pergunte. O programa acha sozinho o vault na Área de Trabalho e
  guarda a escolha; a primeira linha da saída diz qual pasta ele usou. Só informe um
  destino com `-o` se o usuário pedir outro.

Se a pasta de origem tiver subpastas, o programa varre todas. A estrutura de pastas
**não** é espelhada automaticamente: para espelhar, converta pasta por pasta usando
`-o` correspondente.

## 2. Converta

```bash
.venv\Scripts\python.exe -m pdf2md "<origem>"
```

Sem `-o`, ele grava no vault do usuário e atualiza o índice automaticamente. Para
outro destino: `-o "<pasta>" --indices`. Para trocar o vault padrão:
`--definir-vault "<pasta>"`.

Se o ambiente não existir, rode `instalar.bat` primeiro.

Para acervos grandes (mais de 50 arquivos), rode em segundo plano e avise que pode
levar alguns minutos — cerca de 1 a 3 segundos por arquivo, mais tempo em livros
longos.

## 3. Confira a numeração antes de dizer que terminou

Esta é a parte que não pode ser pulada. Leia a saída e separe as obras em dois grupos
pelo que aparece ao lado de cada `OK`:

- **`rotulos embutidos no PDF`** ou **`numeros impressos detectados`** → o usuário pode
  citar direto.
- **`numeracao do proprio PDF`** → o programa não descobriu a página impressa e está
  contando folhas. **Liste essas obras nominalmente** e explique, em uma frase, que
  citar por elas pode errar a página.

Para resolver uma obra desse segundo grupo:

1. peça ao usuário o número impresso numa folha qualquer do PDF e em que folha do
   arquivo ela está (por exemplo: "na folha 17 do PDF está impresso 1");
2. calcule `deslocamento = numero_impresso - numero_da_folha`;
3. reconverta só aquela obra:

```bash
.venv\Scripts\python.exe -m pdf2md "<arquivo>" --modo-pagina offset --offset <valor>
```

## 4. Relate

Diga, em poucas linhas: quantas obras entraram, quantas páginas no total, quantas com
numeração confiável, quais precisam ser conferidas e quais são escaneadas (sem texto).
Aponte o arquivo `000 - Acervo.md` do vault, que traz tudo isso organizado.

## Casos que aparecem

**PDF escaneado (páginas sem texto).** O OCR precisa do Tesseract instalado
(`winget install -e --id UB-Mannheim.TesseractOCR`) mais `pip install pytesseract pillow`.
**Peça autorização antes de instalar.** Avise que o texto sai como parágrafo corrido e
que o OCR não ajuda na numeração — nesses livros use deslocamento manual.

**Obra que já está no vault.** A nota é sobrescrita. Se o usuário costuma anotar dentro
das notas de fonte, avise antes — e sugira manter os comentários dele numa nota
separada que aponte para as páginas.

**Dois PDFs com o mesmo nome.** O programa detecta e grava o segundo como `(2)`,
avisando no registro. Não é erro.

**O título da nota saiu estranho.** Ele vem dos metadados do PDF; se não houver, da
maior linha das duas primeiras páginas; em último caso, do nome do arquivo. Corrija a
linha `title:` da nota e o `# Título` logo abaixo do cabeçalho.

## Nunca

- Fazer commit do vault ou dos PDFs: é material de terceiros num repositório público.
- Dar a conversão por concluída sem informar a origem da numeração.
- Instalar programas sem autorização explícita.
