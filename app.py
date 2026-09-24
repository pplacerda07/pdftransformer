"""PDF -> Markdown: interface do programa.

Converte PDFs em .md preservando o numero da pagina da publicacao,
para citar com seguranca e usar como contexto de IA / vault do Obsidian.
"""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pdf2md.model import Options
from tooltip import tip

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:                                   # pragma: no cover
    DND_FILES, TkinterDnD = None, None
    HAS_DND = False

APP_TITLE = "PDF para Markdown"
APP_SUB = "paginas fieis para citacao"

# ----------------------------------------------------------------- aparencia --
BG = "#F2F3F7"
CARD = "#FFFFFF"
BORDER = "#E3E5EB"
TEXT = "#14161D"
MUTED = "#6B7180"
ACCENT = "#4B45C6"
ACCENT_HOVER = "#3B35A8"
ACCENT_SOFT = "#EEEDFB"
OK_C = "#0A7C57"
WARN_C = "#A1620B"
ERR_C = "#C42B2B"

F_BASE = ("Segoe UI", 10)
F_SMALL = ("Segoe UI", 9)
F_TITLE = ("Segoe UI Semibold", 19)
F_CARD = ("Segoe UI Semibold", 11)
F_BTN = ("Segoe UI Semibold", 10)
F_MONO = ("Consolas", 9)

MARKER_CHOICES = [
    ("Comentario + titulo de pagina  (recomendado)", "both"),
    ("Somente comentario   <!-- page: 23 -->", "comment"),
    ("Somente titulo   ###### p. 23", "heading"),
    ("Marcador no meio do texto   **[p. 23]**", "inline"),
    ("Sem marcador de pagina", "none"),
]

PAGE_MODE_CHOICES = [
    ("Automatico  (rotulos do PDF, depois numeros impressos)", "auto"),
    ("Somente rotulos embutidos no PDF", "embedded"),
    ("Somente numeros impressos nas margens", "detect"),
    ("Deslocamento manual", "offset"),
    ("Usar a folha do proprio PDF", "pdf"),
]


def _button(parent, text, command, kind="ghost", width=None, ajuda=None):
    """Botao chapado com estado de hover (o ttk nao deixa colorir a vontade).

    `ajuda` e um par (titulo, explicacao) que vira balao ao parar o mouse.
    """
    if kind == "primary":
        bg, fg, hover = ACCENT, "#FFFFFF", ACCENT_HOVER
    elif kind == "soft":
        bg, fg, hover = ACCENT_SOFT, ACCENT, "#E2E0F8"
    else:
        bg, fg, hover = "#F4F5F8", TEXT, "#E9EBF0"
    btn = tk.Button(
        parent, text=text, command=command, font=F_BTN, bg=bg, fg=fg,
        activebackground=hover, activeforeground=fg, relief="flat", bd=0,
        padx=14, pady=7, cursor="hand2", highlightthickness=0,
        disabledforeground="#AFB3BE",
    )
    if width:
        btn.configure(width=width)

    def on_enter(_e):
        if btn["state"] != "disabled":
            btn.configure(bg=hover)

    def on_leave(_e):
        if btn["state"] != "disabled":
            btn.configure(bg=bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    btn._base_bg = bg
    if ajuda:
        tip(btn, *ajuda)
    return btn


def _card(parent, step: str, title: str, hint: str = "", ajuda=None):
    """Cartao branco com borda fina; devolve (cartao, corpo)."""
    outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                     highlightcolor=BORDER, highlightthickness=1, bd=0)
    head = tk.Frame(outer, bg=CARD)
    head.pack(fill="x", padx=16, pady=(13, 0))
    badge = tk.Label(head, text=f" {step} ", font=("Segoe UI Semibold", 9),
                     bg=ACCENT_SOFT, fg=ACCENT, padx=4, pady=2)
    badge.pack(side="left")
    rotulo = tk.Label(head, text=title, font=F_CARD, bg=CARD, fg=TEXT)
    rotulo.pack(side="left", padx=(8, 0))
    if ajuda:
        tip(badge, *ajuda)
        tip(rotulo, *ajuda)
    if hint:
        tk.Label(head, text=hint, font=F_SMALL, bg=CARD, fg=MUTED).pack(side="left", padx=(10, 0))
    body = tk.Frame(outer, bg=CARD)
    body.pack(fill="both", expand=True, padx=16, pady=(10, 14))
    return outer, body


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(f"{APP_TITLE} - {APP_SUB}")
        root.configure(bg=BG)

        # a janela acompanha a escala do Windows, mas nunca passa da tela
        scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        w = min(int(1000 * scale), root.winfo_screenwidth() - 80)
        h = min(int(790 * scale), root.winfo_screenheight() - 110)
        x = max(0, (root.winfo_screenwidth() - w) // 2)
        y = max(0, (root.winfo_screenheight() - h) // 2 - 20)
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(min(880, w), min(620, h))

        self.files: list[str] = []
        self.rows: dict[str, str] = {}          # caminho -> id na tabela
        self.queue: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None
        self._cancel = threading.Event()
        self.last_out_dir: str | None = None

        self._style()
        self._build()
        self.root.after(120, self._drain)

    # ------------------------------------------------------------------ tema --
    def _style(self) -> None:
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TCheckbutton", background=CARD, foreground=TEXT, font=F_BASE,
                     focuscolor=CARD)
        st.map("TCheckbutton",
               background=[("active", CARD)],
               foreground=[("disabled", MUTED)])
        st.configure("TCombobox", fieldbackground="#FFFFFF", background="#FFFFFF",
                     bordercolor=BORDER, arrowcolor=MUTED, foreground=TEXT,
                     lightcolor=BORDER, darkcolor=BORDER, padding=5)
        st.map("TCombobox", fieldbackground=[("readonly", "#FFFFFF")],
               selectbackground=[("readonly", "#FFFFFF")],
               selectforeground=[("readonly", TEXT)])
        st.configure("TSpinbox", fieldbackground="#FFFFFF", bordercolor=BORDER,
                     arrowcolor=MUTED, padding=4)
        st.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=BORDER, padding=5)
        st.configure("Accent.Horizontal.TProgressbar", troughcolor="#E7E9F0",
                     background=ACCENT, bordercolor="#E7E9F0",
                     lightcolor=ACCENT, darkcolor=ACCENT, thickness=6)
        st.configure("Files.Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                     foreground=TEXT, rowheight=26, borderwidth=0, font=F_BASE)
        st.configure("Files.Treeview.Heading", background="#F7F8FA", foreground=MUTED,
                     font=F_SMALL, relief="flat", padding=5)
        st.map("Files.Treeview", background=[("selected", ACCENT_SOFT)],
               foreground=[("selected", TEXT)])
        st.map("Files.Treeview.Heading", background=[("active", "#F0F1F5")])
        st.layout("Files.Treeview", [("Files.Treeview.treearea", {"sticky": "nswe"})])

    # -------------------------------------------------------------- estrutura --
    def _build(self) -> None:
        header = tk.Frame(self.root, bg=CARD, height=68)
        header.pack(fill="x")
        header.pack_propagate(False)
        inner = tk.Frame(header, bg=CARD)
        inner.pack(fill="both", expand=True, padx=24)
        tk.Label(inner, text=APP_TITLE, font=F_TITLE, bg=CARD, fg=TEXT).pack(
            side="left", pady=(14, 0), anchor="w")
        tk.Label(inner, text=APP_SUB, font=F_BASE, bg=CARD, fg=MUTED).pack(
            side="left", padx=(12, 0), pady=(20, 0), anchor="w")
        dica = tk.Label(inner, text="?  pare o mouse sobre qualquer item para ver o que faz",
                        font=F_SMALL, bg=ACCENT_SOFT, fg=ACCENT, padx=10, pady=4)
        dica.pack(side="right", pady=(18, 0))
        tip(dica, "Ajuda em qualquer lugar",
            "Todo botao, caixa e coluna desta tela tem uma explicacao curta como esta. "
            "Basta parar o mouse em cima e esperar um instante.")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # o rodape e criado antes do corpo para nunca ser empurrado para fora
        self._build_footer()

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        self._build_files(body)

        # cartoes 2 e 3 lado a lado: em pe um embaixo do outro nao cabem na tela
        colunas = tk.Frame(body, bg=BG)
        colunas.pack(fill="both")
        esquerda = tk.Frame(colunas, bg=BG)
        esquerda.pack(side="left", fill="both", expand=True)
        direita = tk.Frame(colunas, bg=BG)
        direita.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self._build_pages(esquerda)
        self._build_output(direita)

        # a janela nunca pode ficar menor do que o conteudo precisa
        self.root.update_idletasks()
        alt = self.root.winfo_reqheight()
        larg = min(max(880, self.root.winfo_reqwidth()), self.root.winfo_screenwidth() - 80)
        tela_h = self.root.winfo_screenheight() - 90
        if alt > self.root.winfo_height():
            nova = min(alt, tela_h)
            self.root.geometry(f"{self.root.winfo_width()}x{nova}")
        self.root.minsize(larg, min(alt, tela_h))

    # ---------------------------------------------------------------- cartoes --
    def _build_files(self, parent) -> None:
        card, body = _card(
            parent, "1", "PDFs a converter",
            "arraste arquivos para a lista" if HAS_DND else "",
            ajuda=("Passo 1: escolher os arquivos",
                   "Monte aqui a fila de PDFs. Pode ser um arquivo so ou uma pasta "
                   "inteira com centenas deles - a conversao roda um apos o outro "
                   "sem voce precisar acompanhar."))
        card.pack(fill="both", expand=True, pady=(0, 12))

        wrap = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True)
        cols = ("arquivo", "pasta", "status")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=5,
                                 style="Files.Treeview", selectmode="extended")
        self.tree.heading("arquivo", text="ARQUIVO", anchor="w")
        self.tree.heading("pasta", text="PASTA", anchor="w")
        self.tree.heading("status", text="SITUACAO", anchor="w")
        self.tree.column("arquivo", width=330, anchor="w")
        self.tree.column("pasta", width=300, anchor="w")
        self.tree.column("status", width=150, anchor="w")
        self.tree.tag_configure("ok", foreground=OK_C)
        self.tree.tag_configure("erro", foreground=ERR_C)
        self.tree.tag_configure("indo", foreground=ACCENT)
        self.tree.tag_configure("espera", foreground=MUTED)
        self.tree.pack(side="left", fill="both", expand=True)
        tip(self.tree, "Lista de PDFs a converter",
            "Todos os arquivos daqui serao convertidos quando voce clicar em Converter.\n"
            "A coluna SITUACAO acompanha cada um: 'na fila', 'convertendo...', "
            "'N paginas' quando termina, ou 'erro'.\n"
            "Clique num arquivo para seleciona-lo (e o que o botao Conferir numeracao usa).")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        self.empty_hint = tk.Label(
            self.tree,
            text=("Arraste seus PDFs para ca\n\nou use os botoes abaixo"
                  if HAS_DND else "Use os botoes abaixo para adicionar seus PDFs"),
            font=F_BASE, bg="#FFFFFF", fg=MUTED, justify="center")
        self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")

        if HAS_DND:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind("<<Drop>>", self._on_drop)

        bar = tk.Frame(body, bg=CARD)
        bar.pack(fill="x", pady=(10, 0))
        _button(bar, "Adicionar PDFs", self.add_files, "soft", ajuda=(
            "Escolher arquivos PDF",
            "Abre a janela do Windows para voce escolher os PDFs. "
            "Segure Ctrl para marcar varios de uma vez.")).pack(side="left")
        _button(bar, "Adicionar pasta", self.add_folder, ajuda=(
            "Adicionar uma pasta inteira",
            "Varre a pasta escolhida E todas as subpastas dela, e poe na lista "
            "todos os PDFs encontrados. E o caminho mais rapido para um acervo "
            "grande.")).pack(side="left", padx=6)
        _button(bar, "Remover", self.remove_selected, ajuda=(
            "Tirar da lista",
            "Remove da lista os arquivos selecionados. "
            "Nao apaga nada do seu computador.")).pack(side="left")
        _button(bar, "Limpar", self.clear_files, ajuda=(
            "Esvaziar a lista",
            "Tira todos os arquivos da lista para voce comecar outro lote. "
            "Nenhum arquivo do computador e apagado.")).pack(side="left", padx=6)
        self.count_lbl = tk.Label(bar, text="nenhum arquivo", font=F_SMALL,
                                  bg=CARD, fg=MUTED)
        self.count_lbl.pack(side="right")
        tip(self.count_lbl, "Quantos arquivos estao na fila",
            "Conta os PDFs da lista neste momento.")

    def _build_pages(self, parent) -> None:
        card, body = _card(
            parent, "2", "Numeracao das paginas",
            "e isto que garante a citacao correta",
            ajuda=("Passo 2: a parte que garante a citacao",
                   "Aqui voce decide de onde sai o numero de pagina que vai para a "
                   "nota, e como ele aparece no texto. Se algum dia uma citacao sua "
                   "sair com a pagina errada, o problema esta neste cartao."))
        card.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        tk.Label(body, text="Como descobrir a pagina impressa", font=F_SMALL,
                 bg=CARD, fg=MUTED).grid(row=0, column=0, sticky="w")
        self.page_combo = ttk.Combobox(body, state="readonly", font=F_BASE, width=34,
                                       values=[c[0] for c in PAGE_MODE_CHOICES])
        self.page_combo.current(0)
        self.page_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 10))
        self.page_combo.bind("<<ComboboxSelected>>", self._on_mode)
        tip(self.page_combo, "De onde vem o numero da pagina",
            "A folha 27 do PDF quase nunca e a pagina 27 do livro. Esta opcao decide "
            "como descobrir o numero certo.\n\n"
            "Automatico: tenta primeiro os rotulos que o proprio PDF traz; se nao "
            "houver, le os numeros impressos no rodape. Deixe assim na maioria dos "
            "casos.\n"
            "Deslocamento manual: voce mesmo informa a diferenca, no campo abaixo.\n"
            "Usar a folha do PDF: ignora a publicacao e numera 1, 2, 3...")

        tk.Label(body, text="Marcador que aparece no texto", font=F_SMALL,
                 bg=CARD, fg=MUTED).grid(row=2, column=0, sticky="w")
        self.marker_combo = ttk.Combobox(body, state="readonly", font=F_BASE, width=34,
                                         values=[c[0] for c in MARKER_CHOICES])
        self.marker_combo.current(0)
        self.marker_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 10))
        tip(self.marker_combo, "Como a virada de pagina aparece na nota",
            "Recomendado: escreve as duas formas - um comentario que fica invisivel "
            "na leitura do Obsidian e um titulo 'p. 23', que aparece no painel de "
            "navegacao e permite link direto para a pagina.\n\n"
            "Escolha 'somente comentario' se quiser a nota totalmente limpa, ou "
            "'sem marcador' se nao precisar citar pagina nesse material.")

        off = tk.Frame(body, bg=CARD)
        off.grid(row=4, column=0, columnspan=2, sticky="ew")
        tk.Label(off, text="Deslocamento", font=F_SMALL, bg=CARD, fg=MUTED).pack(side="left")
        self.offset = tk.IntVar(value=0)
        self.offset_spin = ttk.Spinbox(off, from_=-999, to=999, width=6, font=F_BASE,
                                       textvariable=self.offset, state="disabled")
        self.offset_spin.pack(side="left", padx=8)
        ajuda_offset = (
            "Corrigir a numeracao na mao",
            "So fica ativo quando voce escolhe 'Deslocamento manual' acima.\n\n"
            "A conta e: pagina impressa = folha do PDF + deslocamento.\n"
            "A pagina 1 do livro esta na folha 17 do PDF? Use -16.\n"
            "O PDF e um capitulo solto que comeca na pagina 145 do original? Use +144.")
        tip(self.offset_spin, *ajuda_offset)
        legenda = tk.Label(off, text="pagina impressa = folha + deslocamento",
                           font=F_SMALL, bg=CARD, fg=MUTED, wraplength=200,
                           justify="left")
        legenda.pack(side="left")
        tip(legenda, *ajuda_offset)
        _button(off, "Conferir numeracao", self.check_numbering, "soft", ajuda=(
            "Ver a numeracao antes de converter",
            "Analisa o PDF selecionado na lista e mostra a tabela "
            "'folha do PDF -> pagina da publicacao', junto com a origem dessa "
            "numeracao.\n\n"
            "Vale o habito: confira aqui sempre que for converter um livro novo "
            "que voce pretende citar.")).pack(side="right")

    def _build_output(self, parent) -> None:
        card, body = _card(
            parent, "3", "Saida e limpeza do texto", "",
            ajuda=("Passo 3: onde salvar e como limpar o texto",
                   "A primeira parte diz para qual pasta vao as notas. As caixas "
                   "abaixo controlam o que o programa arruma no texto extraido. "
                   "Os valores que ja vem marcados servem bem para quase tudo."))
        card.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        self.same_folder = tk.BooleanVar(value=True)
        chk_pasta = ttk.Checkbutton(
            body, text="Salvar numa subpasta 'markdown' ao lado de cada PDF",
            variable=self.same_folder, command=self._toggle_out)
        chk_pasta.grid(row=0, column=0, columnspan=3, sticky="w")
        tip(chk_pasta, "Onde as notas serao gravadas",
            "Marcado: cada .md vai para uma subpasta 'markdown' criada ao lado do "
            "proprio PDF. As notas ficam junto das fontes.\n\n"
            "Desmarcado: voce escolhe uma pasta unica para tudo - por exemplo, a "
            "pasta do seu vault do Obsidian.")

        self.out_var = tk.StringVar()
        self.out_entry = ttk.Entry(body, textvariable=self.out_var, font=F_BASE,
                                   state="disabled")
        self.out_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 12))
        tip(self.out_entry, "Pasta de destino",
            "Caminho da pasta onde todos os .md serao gravados. "
            "So fica disponivel com a caixa acima desmarcada.")
        self.out_btn = _button(body, "Escolher pasta", self.pick_out, ajuda=(
            "Procurar a pasta",
            "Abre a janela do Windows para voce apontar a pasta de destino - "
            "por exemplo, a pasta do seu vault do Obsidian."))
        self.out_btn.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(7, 12))
        self.out_btn.configure(state="disabled")

        grid = tk.Frame(body, bg=CARD)
        grid.grid(row=2, column=0, columnspan=3, sticky="ew")
        for c in range(2):
            grid.columnconfigure(c, weight=1, uniform="opt")

        self.v_frontmatter = tk.BooleanVar(value=True)
        self.v_legend = tk.BooleanVar(value=True)
        self.v_headings = tk.BooleanVar(value=True)
        self.v_running = tk.BooleanVar(value=True)
        self.v_dehyph = tk.BooleanVar(value=True)
        self.v_emphasis = tk.BooleanVar(value=True)
        self.v_tables = tk.BooleanVar(value=True)
        self.v_columns = tk.BooleanVar(value=True)
        self.v_images = tk.BooleanVar(value=False)
        self.v_perpage = tk.BooleanVar(value=False)
        self.v_ocr = tk.BooleanVar(value=False)

        checks = [
            ("Cabecalho YAML com a fonte", self.v_frontmatter,
             "Ficha da fonte no topo da nota",
             "Escreve um bloco com titulo, autor, arquivo de origem, total de paginas "
             "e de onde veio a numeracao. O Obsidian le esse bloco como propriedades "
             "da nota, e e por ele que voce sabe o quanto confiar na numeracao."),
            ("Nota de contexto para a IA", self.v_legend,
             "Explicacao para a inteligencia artificial",
             "Acrescenta um paragrafo dizendo o que os marcadores de pagina "
             "significam e pedindo que a citacao use o numero do marcador anterior "
             "ao trecho. E o que faz o Claude citar a pagina certa."),
            ("Detectar titulos", self.v_headings,
             "Transformar em titulos",
             "Linhas escritas em fonte maior que o corpo do texto viram titulos "
             "(##, ###). Isso da estrutura a nota e alimenta o painel de navegacao "
             "do Obsidian.\n\nDesmarque se o seu PDF tiver muitos destaques soltos "
             "virando titulo sem necessidade."),
            ("Remover cabecalho/rodape repetido", self.v_running,
             "Tirar o texto que se repete em toda pagina",
             "O titulo do livro ou do capitulo impresso no alto de cada pagina vira "
             "lixo quando repetido centenas de vezes.\n\nDesmarque se perceber que "
             "algum texto util esta sumindo."),
            ("Juntar palavras com hifen", self.v_dehyph,
             "Consertar palavras cortadas na quebra de linha",
             "'pro-' no fim de uma linha e 'cesso' no inicio da seguinte viram "
             "'processo'. Sem isso a IA le palavras partidas e a busca por termos "
             "falha."),
            ("Preservar negrito e italico", self.v_emphasis,
             "Manter os destaques do original",
             "O que estava em negrito vira **negrito** e o italico vira *italico* - "
             "util quando o autor destaca termos-chave ou titulos de obras."),
            ("Converter tabelas", self.v_tables,
             "Tabelas viram tabelas de Markdown",
             "Reconhece tabelas no PDF e escreve em formato de tabela, em vez de "
             "despejar as celulas soltas.\n\nDesmarque se as tabelas do seu material "
             "sairem embaralhadas."),
            ("Detectar duas colunas", self.v_columns,
             "Ordem de leitura em textos de duas colunas",
             "Le a coluna da esquerda inteira antes da direita, como em artigos de "
             "periodico. Sem isso, as frases das duas colunas saem intercaladas e o "
             "texto fica sem sentido."),
            ("Extrair imagens", self.v_images,
             "Salvar tambem as figuras",
             "Grava as imagens do PDF numa pasta 'assets' e referencia na nota. "
             "Deixe desmarcado se voce so quer o texto - fica mais leve e mais "
             "rapido."),
            ("Tambem uma nota por pagina", self.v_perpage,
             "Gerar um arquivo separado por pagina",
             "Alem da nota unica, cria uma pasta com um .md por pagina, cada um com "
             "links de anterior e proxima.\n\nAtencao: um livro de 300 paginas vira "
             "300 arquivos no seu vault."),
            ("OCR em paginas sem texto", self.v_ocr,
             "Ler paginas escaneadas (imagem)",
             "Quando a pagina e so imagem, tenta reconhecer as letras.\n\n"
             "Exige o programa Tesseract instalado a parte. Sem ele, o programa "
             "avisa e segue sem OCR."),
        ]
        for i, (label, var, t_titulo, t_corpo) in enumerate(checks):
            chk = ttk.Checkbutton(grid, text=label, variable=var)
            chk.grid(row=i // 2, column=i % 2, sticky="w", pady=2)
            tip(chk, t_titulo, t_corpo)

    def _build_footer(self) -> None:
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=CARD)
        foot.pack(fill="x", side="bottom")

        log_wrap = tk.Frame(foot, bg=CARD)
        log_wrap.pack(fill="x", padx=20, pady=(12, 0))
        self.log = tk.Text(log_wrap, height=4, wrap="word", font=F_MONO, bd=0,
                           bg="#FAFAFC", fg=TEXT, padx=10, pady=8,
                           highlightbackground=BORDER, highlightthickness=1,
                           state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        lsb = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        lsb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=lsb.set)
        self.log.tag_configure("ok", foreground=OK_C)
        self.log.tag_configure("erro", foreground=ERR_C)
        self.log.tag_configure("aviso", foreground=WARN_C)
        self.log.tag_configure("info", foreground=MUTED)
        tip(self.log, "Registro do que aconteceu",
            "Uma linha por arquivo convertido, com o numero de paginas e a origem da "
            "numeracao usada.\n\n"
            "Verde: convertido. Laranja: aviso - por exemplo, paginas sem texto "
            "porque o PDF e escaneado. Vermelho: o arquivo nao pode ser lido.")

        self.progress = ttk.Progressbar(foot, style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=20, pady=(10, 0))
        tip(self.progress, "Progresso do arquivo atual",
            "Avanca pagina a pagina dentro do PDF que esta sendo convertido. "
            "Para acompanhar o lote inteiro, olhe a coluna SITUACAO da lista.")

        bar = tk.Frame(foot, bg=CARD)
        bar.pack(fill="x", padx=20, pady=12)
        self.status = tk.Label(bar, text="Pronto para converter.", font=F_BASE,
                               bg=CARD, fg=MUTED, anchor="w")
        self.status.pack(side="left")
        tip(self.status, "Situacao atual",
            "Mostra qual arquivo esta sendo convertido e, ao final, quantos "
            "deram certo.")
        self.run_btn = _button(bar, "Converter", self.start, "primary", ajuda=(
            "Converter tudo o que esta na lista",
            "Gera um arquivo .md para cada PDF, com as opcoes escolhidas acima.\n\n"
            "A conversao roda em segundo plano: voce pode continuar usando o "
            "computador, e a janela continua respondendo."))
        self.run_btn.pack(side="right")
        self.cancel_btn = _button(bar, "Cancelar", self.cancel, ajuda=(
            "Interromper a conversao",
            "Para o processo no ponto em que estiver. Os arquivos ja concluidos "
            "continuam salvos; o que estava no meio e descartado."))
        self.cancel_btn.pack(side="right", padx=8)
        self.cancel_btn.configure(state="disabled")
        self.open_btn = _button(bar, "Abrir pasta de saida", self.open_out, ajuda=(
            "Ver os arquivos gerados",
            "Abre no Explorador do Windows a pasta onde as notas foram gravadas. "
            "Fica disponivel assim que o primeiro arquivo termina."))
        self.open_btn.pack(side="right")
        self.open_btn.configure(state="disabled")

    # ---------------------------------------------------------------- arquivos --
    def _on_drop(self, event) -> None:
        self._add(self.root.tk.splitlist(event.data))

    def add_files(self) -> None:
        self._add(filedialog.askopenfilenames(
            title="Escolha os PDFs",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]))

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Escolha a pasta com os PDFs")
        if not folder:
            return
        found = []
        for base, _dirs, names in os.walk(folder):
            for n in names:
                if n.lower().endswith(".pdf"):
                    found.append(os.path.join(base, n))
        self._add(sorted(found))

    def _add(self, paths) -> None:
        added = 0
        for p in paths:
            if os.path.isdir(p):
                continue
            p = os.path.abspath(p)
            if p in self.files or not p.lower().endswith(".pdf"):
                continue
            if not os.path.exists(p):
                continue
            self.files.append(p)
            item = self.tree.insert("", "end", tags=("espera",), values=(
                os.path.basename(p), os.path.dirname(p), "na fila"))
            self.rows[p] = item
            added += 1
        self._refresh_count()
        if added:
            self._log(f"{added} arquivo(s) adicionado(s).", "info")

    def remove_selected(self) -> None:
        for item in self.tree.selection():
            for path, iid in list(self.rows.items()):
                if iid == item:
                    self.files.remove(path)
                    del self.rows[path]
            self.tree.delete(item)
        self._refresh_count()

    def clear_files(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.files.clear()
        self.rows.clear()
        self._refresh_count()

    def _refresh_count(self) -> None:
        n = len(self.files)
        self.count_lbl.configure(
            text="nenhum arquivo" if not n else f"{n} arquivo{'s' if n > 1 else ''}")
        if n:
            self.empty_hint.place_forget()
        else:
            self.empty_hint.place(relx=0.5, rely=0.5, anchor="center")

    def pick_out(self) -> None:
        folder = filedialog.askdirectory(title="Pasta de saida")
        if folder:
            self.out_var.set(folder)

    def open_out(self) -> None:
        target = self.last_out_dir
        if target and os.path.isdir(target):
            if sys.platform.startswith("win"):
                os.startfile(target)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", target], check=False)
            else:
                subprocess.run(["xdg-open", target], check=False)

    def _toggle_out(self) -> None:
        state = "disabled" if self.same_folder.get() else "normal"
        self.out_entry.configure(state=state)
        self.out_btn.configure(state=state)

    def _on_mode(self, _evt=None) -> None:
        mode = PAGE_MODE_CHOICES[self.page_combo.current()][1]
        self.offset_spin.configure(state="normal" if mode == "offset" else "disabled")

    # ----------------------------------------------------------------- opcoes --
    def options(self) -> Options:
        out_dir = None if self.same_folder.get() else (self.out_var.get().strip() or None)
        return Options(
            page_mode=PAGE_MODE_CHOICES[self.page_combo.current()][1],
            manual_offset=int(self.offset.get() or 0),
            marker_style=MARKER_CHOICES[self.marker_combo.current()][1],
            frontmatter=self.v_frontmatter.get(),
            marker_legend=self.v_legend.get(),
            detect_headings=self.v_headings.get(),
            strip_running_heads=self.v_running.get(),
            dehyphenate=self.v_dehyph.get(),
            emphasis=self.v_emphasis.get(),
            tables=self.v_tables.get(),
            two_columns=self.v_columns.get(),
            extract_images=self.v_images.get(),
            per_page_files=self.v_perpage.get(),
            ocr=self.v_ocr.get(),
            output_dir=out_dir,
        )

    # ------------------------------------------------------------ conferencia --
    def check_numbering(self) -> None:
        sel = self.tree.selection()
        path = None
        if sel:
            path = next((p for p, i in self.rows.items() if i == sel[0]), None)
        path = path or (self.files[0] if self.files else None)
        if not path:
            messagebox.showinfo(APP_TITLE, "Adicione um PDF primeiro.")
            return

        self.status.configure(text="Analisando a numeracao...")
        self.root.update_idletasks()
        try:
            from pdf2md._pdf import fitz
            from pdf2md.extract import extract_page
            from pdf2md.pagelabels import resolve as resolve_labels

            opts = self.options()
            doc = fitz.open(path)
            limit = min(doc.page_count, 60)
            pages = [extract_page(doc[i], opts) for i in range(limit)]
            labels = resolve_labels(doc, pages, opts)
            rows = [(i + 1, labels.label(i) or "(sem numeracao)")
                    for i in range(min(limit, 40))]
            total = doc.page_count
            doc.close()
        except Exception as exc:
            self.status.configure(text="Pronto para converter.")
            messagebox.showerror(APP_TITLE, f"Nao foi possivel analisar:\n{exc}")
            return
        self.status.configure(text="Pronto para converter.")

        top = tk.Toplevel(self.root)
        top.title("Conferencia da numeracao")
        top.configure(bg=CARD)
        top.geometry("430x560")
        top.transient(self.root)

        tk.Label(top, text=os.path.basename(path), font=F_CARD, bg=CARD, fg=TEXT,
                 wraplength=390, justify="left").pack(anchor="w", padx=18, pady=(16, 2))
        origem = tk.Label(top, text=f"Origem: {labels.human}", font=F_SMALL, bg=CARD,
                          fg=ACCENT, wraplength=390, justify="left")
        origem.pack(anchor="w", padx=18)
        tip(origem, "De onde saiu esta numeracao",
            "Rotulos embutidos no PDF: o proprio arquivo informa - e o mais "
            "confiavel.\n"
            "Numeros impressos detectados: lidos do rodape das paginas.\n"
            "Deslocamento manual: o valor que voce informou.\n"
            "Numeracao do proprio PDF: nada foi encontrado, esta contando folhas. "
            "Se o livro tiver capa e prefacio, conserte com o deslocamento.")
        tk.Label(top, text=f"Analisadas {limit} de {total} folhas.", font=F_SMALL,
                 bg=CARD, fg=MUTED).pack(anchor="w", padx=18, pady=(2, 10))

        table = tk.Frame(top, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        table.pack(fill="both", expand=True, padx=18, pady=(0, 12))
        txt = tk.Text(table, font=F_MONO, bd=0, bg="#FFFFFF", fg=TEXT, padx=12, pady=10,
                      highlightthickness=0)
        txt.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table, orient="vertical", command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.configure(yscrollcommand=sb.set)
        txt.insert("end", "folha do PDF      pagina da publicacao\n")
        txt.insert("end", "-" * 40 + "\n")
        for pdf_page, label in rows:
            txt.insert("end", f"{pdf_page:>9}   ->   {label}\n")
        txt.configure(state="disabled")
        tip(txt, "Como conferir",
            "Abra o PDF no leitor, va ate uma folha qualquer e compare o numero "
            "impresso na pagina com o que esta nesta tabela.\n\n"
            "Se nao bater, feche esta janela, escolha 'Deslocamento manual' e "
            "informe a diferenca.")

        _button(top, "Fechar", top.destroy, "soft").pack(pady=(0, 14))

    # ------------------------------------------------------------- conversao --
    def start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self.files:
            messagebox.showinfo(APP_TITLE, "Adicione pelo menos um PDF.")
            return
        opts = self.options()
        if not self.same_folder.get() and not opts.output_dir:
            messagebox.showinfo(APP_TITLE, "Escolha a pasta de saida.")
            return
        if opts.ocr:
            from pdf2md import ocr as _ocr

            if not _ocr.available():
                messagebox.showwarning(
                    APP_TITLE,
                    "Tesseract nao encontrado - o OCR sera ignorado.\n\n"
                    "Para ativar:\n"
                    "  winget install -e --id UB-Mannheim.TesseractOCR\n"
                    "  .venv\\Scripts\\python.exe -m pip install pytesseract pillow")

        self._cancel.clear()
        self.run_btn.configure(state="disabled", bg="#A9A6DF")
        self.cancel_btn.configure(state="normal")
        self.progress.configure(value=0, maximum=100)
        for path, item in self.rows.items():
            self.tree.item(item, tags=("espera",), values=(
                os.path.basename(path), os.path.dirname(path), "na fila"))
        self.worker = threading.Thread(target=self._work, args=(list(self.files), opts),
                                       daemon=True)
        self.worker.start()

    def cancel(self) -> None:
        self._cancel.set()
        self.status.configure(text="Cancelando...")

    def _work(self, files: list[str], opts: Options) -> None:
        from pdf2md.converter import convert_file

        ok = 0
        for idx, path in enumerate(files, 1):
            if self._cancel.is_set():
                break
            self.queue.put(("status", f"Convertendo {idx} de {len(files)}: "
                                      f"{os.path.basename(path)}"))
            self.queue.put(("file", (path, "convertendo...", "indo")))
            try:
                res = convert_file(
                    path, opts,
                    progress=lambda cur, tot: self.queue.put(("progress", (cur, tot))),
                    cancel=self._cancel.is_set,
                )
                if res.out_path:
                    ok += 1
                    self.queue.put(("outdir", os.path.dirname(res.out_path)))
                    self.queue.put(("file", (path, f"{res.pages} paginas", "ok")))
                    self.queue.put(("log", (
                        f"OK   {os.path.basename(path)}  ->  "
                        f"{os.path.basename(res.out_path)}   "
                        f"({res.pages} pag., {res.page_source})", "ok")))
                else:
                    self.queue.put(("file", (path, "nao convertido", "erro")))
                for w in res.warnings:
                    self.queue.put(("log", (f"     aviso: {w}", "aviso")))
            except Exception as exc:
                self.queue.put(("file", (path, "erro", "erro")))
                self.queue.put(("log", (f"ERRO {os.path.basename(path)}: {exc}", "erro")))
        self.queue.put(("done", (ok, len(files))))

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    msg, tag = payload if isinstance(payload, tuple) else (payload, "info")
                    self._log(msg, tag)
                elif kind == "status":
                    self.status.configure(text=payload, fg=TEXT)
                elif kind == "progress":
                    cur, tot = payload
                    self.progress.configure(maximum=max(1, tot), value=cur)
                elif kind == "file":
                    path, texto, tag = payload
                    item = self.rows.get(path)
                    if item:
                        self.tree.item(item, tags=(tag,), values=(
                            os.path.basename(path), os.path.dirname(path), texto))
                        self.tree.see(item)
                elif kind == "outdir":
                    self.last_out_dir = payload
                    self.open_btn.configure(state="normal")
                elif kind == "done":
                    ok, total = payload
                    self.run_btn.configure(state="normal", bg=ACCENT)
                    self.cancel_btn.configure(state="disabled")
                    if self._cancel.is_set():
                        msg, cor = "Cancelado.", WARN_C
                    else:
                        msg = f"Concluido: {ok} de {total} arquivo(s) convertido(s)."
                        cor = OK_C if ok == total else WARN_C
                    self.status.configure(text=msg, fg=cor)
                    self._log(msg, "ok" if ok == total and not self._cancel.is_set()
                              else "aviso")
        except queue.Empty:
            pass
        self.root.after(120, self._drain)

    def _log(self, msg: str, tag: str = "info") -> None:
        self.log.configure(state="normal")
        self.log.insert("end", msg.rstrip() + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    try:
        from pdf2md._pdf import fitz  # noqa: F401
    except ImportError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            APP_TITLE,
            "A biblioteca PyMuPDF nao esta instalada.\n\n"
            "Rode o arquivo instalar.bat (ou: pip install -r requirements.txt).")
        return

    # precisa vir antes de criar a janela, senao o Windows so amplia a imagem
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    try:
        root.tk.call("tk", "scaling", root.winfo_fpixels("1i") / 72.0)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
