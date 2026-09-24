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


def _button(parent, text, command, kind="ghost", width=None):
    """Botao chapado com estado de hover (o ttk nao deixa colorir a vontade)."""
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
    return btn


def _card(parent, step: str, title: str, hint: str = ""):
    """Cartao branco com borda fina; devolve (cartao, corpo)."""
    outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                     highlightcolor=BORDER, highlightthickness=1, bd=0)
    head = tk.Frame(outer, bg=CARD)
    head.pack(fill="x", padx=16, pady=(13, 0))
    tk.Label(head, text=f" {step} ", font=("Segoe UI Semibold", 9), bg=ACCENT_SOFT,
             fg=ACCENT, padx=4, pady=2).pack(side="left")
    tk.Label(head, text=title, font=F_CARD, bg=CARD, fg=TEXT).pack(side="left", padx=(8, 0))
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
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # o rodape e criado antes do corpo para nunca ser empurrado para fora
        self._build_footer()

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        self._build_files(body)
        self._build_pages(body)
        self._build_output(body)

    # ---------------------------------------------------------------- cartoes --
    def _build_files(self, parent) -> None:
        card, body = _card(parent, "1", "PDFs a converter",
                           "arraste arquivos para a lista" if HAS_DND else "")
        card.pack(fill="both", expand=True, pady=(0, 12))

        wrap = tk.Frame(body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(fill="both", expand=True)
        cols = ("arquivo", "pasta", "status")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=6,
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
        _button(bar, "Adicionar PDFs", self.add_files, "soft").pack(side="left")
        _button(bar, "Adicionar pasta", self.add_folder).pack(side="left", padx=6)
        _button(bar, "Remover", self.remove_selected).pack(side="left")
        _button(bar, "Limpar", self.clear_files).pack(side="left", padx=6)
        self.count_lbl = tk.Label(bar, text="nenhum arquivo", font=F_SMALL,
                                  bg=CARD, fg=MUTED)
        self.count_lbl.pack(side="right")

    def _build_pages(self, parent) -> None:
        card, body = _card(parent, "2", "Numeracao das paginas",
                           "e isto que garante a citacao correta")
        card.pack(fill="x", pady=(0, 12))
        body.columnconfigure(1, weight=1)

        tk.Label(body, text="Como descobrir a pagina impressa", font=F_SMALL,
                 bg=CARD, fg=MUTED).grid(row=0, column=0, sticky="w")
        self.page_combo = ttk.Combobox(body, state="readonly", font=F_BASE,
                                       values=[c[0] for c in PAGE_MODE_CHOICES])
        self.page_combo.current(0)
        self.page_combo.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(3, 10))
        self.page_combo.bind("<<ComboboxSelected>>", self._on_mode)

        tk.Label(body, text="Marcador que aparece no texto", font=F_SMALL,
                 bg=CARD, fg=MUTED).grid(row=2, column=0, sticky="w")
        self.marker_combo = ttk.Combobox(body, state="readonly", font=F_BASE,
                                         values=[c[0] for c in MARKER_CHOICES])
        self.marker_combo.current(0)
        self.marker_combo.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(3, 10))

        off = tk.Frame(body, bg=CARD)
        off.grid(row=4, column=0, columnspan=2, sticky="ew")
        tk.Label(off, text="Deslocamento", font=F_SMALL, bg=CARD, fg=MUTED).pack(side="left")
        self.offset = tk.IntVar(value=0)
        self.offset_spin = ttk.Spinbox(off, from_=-999, to=999, width=6, font=F_BASE,
                                       textvariable=self.offset, state="disabled")
        self.offset_spin.pack(side="left", padx=8)
        tk.Label(off, text="pagina impressa = folha do PDF + deslocamento.   "
                           "Ex.: a pagina 1 do livro esta na folha 17  ->  -16",
                 font=F_SMALL, bg=CARD, fg=MUTED).pack(side="left")
        _button(off, "Conferir numeracao", self.check_numbering, "soft").pack(side="right")

    def _build_output(self, parent) -> None:
        card, body = _card(parent, "3", "Saida e limpeza do texto")
        card.pack(fill="x", pady=(0, 12))
        body.columnconfigure(1, weight=1)

        self.same_folder = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Salvar numa subpasta 'markdown' ao lado de cada PDF",
                        variable=self.same_folder, command=self._toggle_out).grid(
            row=0, column=0, columnspan=3, sticky="w")

        self.out_var = tk.StringVar()
        self.out_entry = ttk.Entry(body, textvariable=self.out_var, font=F_BASE,
                                   state="disabled")
        self.out_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 12))
        self.out_btn = _button(body, "Escolher pasta", self.pick_out)
        self.out_btn.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(7, 12))
        self.out_btn.configure(state="disabled")

        grid = tk.Frame(body, bg=CARD)
        grid.grid(row=2, column=0, columnspan=3, sticky="ew")
        for c in range(3):
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
            ("Cabecalho YAML com a fonte", self.v_frontmatter),
            ("Nota de contexto para a IA", self.v_legend),
            ("Detectar titulos", self.v_headings),
            ("Remover cabecalho/rodape repetido", self.v_running),
            ("Juntar palavras com hifen", self.v_dehyph),
            ("Preservar negrito e italico", self.v_emphasis),
            ("Converter tabelas", self.v_tables),
            ("Detectar duas colunas", self.v_columns),
            ("Extrair imagens", self.v_images),
            ("Tambem uma nota por pagina", self.v_perpage),
            ("OCR em paginas sem texto", self.v_ocr),
        ]
        for i, (label, var) in enumerate(checks):
            ttk.Checkbutton(grid, text=label, variable=var).grid(
                row=i // 3, column=i % 3, sticky="w", pady=2)

    def _build_footer(self) -> None:
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", side="bottom")
        foot = tk.Frame(self.root, bg=CARD)
        foot.pack(fill="x", side="bottom")

        log_wrap = tk.Frame(foot, bg=CARD)
        log_wrap.pack(fill="x", padx=20, pady=(12, 0))
        self.log = tk.Text(log_wrap, height=5, wrap="word", font=F_MONO, bd=0,
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

        self.progress = ttk.Progressbar(foot, style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=20, pady=(10, 0))

        bar = tk.Frame(foot, bg=CARD)
        bar.pack(fill="x", padx=20, pady=12)
        self.status = tk.Label(bar, text="Pronto para converter.", font=F_BASE,
                               bg=CARD, fg=MUTED, anchor="w")
        self.status.pack(side="left")
        self.run_btn = _button(bar, "Converter", self.start, "primary")
        self.run_btn.pack(side="right")
        self.cancel_btn = _button(bar, "Cancelar", self.cancel)
        self.cancel_btn.pack(side="right", padx=8)
        self.cancel_btn.configure(state="disabled")
        self.open_btn = _button(bar, "Abrir pasta de saida", self.open_out)
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
            rows = [(i + 1, labels.label(i)) for i in range(min(limit, 40))]
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
        tk.Label(top, text=f"Origem: {labels.human}", font=F_SMALL, bg=CARD,
                 fg=ACCENT, wraplength=390, justify="left").pack(anchor="w", padx=18)
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
