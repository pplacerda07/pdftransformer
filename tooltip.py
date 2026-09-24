"""Balao de ajuda que aparece ao parar o mouse sobre um item da tela.

Uso:
    from tooltip import tip
    tip(botao, "Converter", "Le os PDFs da lista e grava os arquivos .md.")
"""
from __future__ import annotations

import tkinter as tk

BG = "#1E2230"
FG = "#F3F4F8"
FG_DIM = "#B9BECD"
BORDER = "#343A4D"
DELAY_MS = 420
FADE_MS = 22

F_TITLE = ("Segoe UI Semibold", 9)
F_BODY = ("Segoe UI", 9)


class Tooltip:
    """Um balao por widget. Some ao sair, clicar ou rolar."""

    _aberto: "Tooltip | None" = None

    def __init__(self, widget, title: str, body: str = "", delay: int = DELAY_MS):
        self.widget = widget
        self.title = title
        self.body = body
        self.delay = delay
        self._after_id = None
        self._win: tk.Toplevel | None = None
        self._alpha = 0.0

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")
        widget.bind("<MouseWheel>", self._on_leave, add="+")
        widget.bind("<Destroy>", self._on_leave, add="+")

    # ------------------------------------------------------------- eventos --
    def _on_enter(self, _evt=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _on_leave(self, _evt=None) -> None:
        self._cancel()
        self._hide()

    def _cancel(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    # ------------------------------------------------------------- desenho --
    def _show(self) -> None:
        self._after_id = None
        if self._win or not self.title:
            return
        try:
            if not self.widget.winfo_viewable():
                return
        except Exception:
            return

        if Tooltip._aberto is not None and Tooltip._aberto is not self:
            Tooltip._aberto._hide()
        Tooltip._aberto = self

        win = tk.Toplevel(self.widget)
        win.wm_overrideredirect(True)
        win.configure(bg=BORDER)
        try:
            win.attributes("-alpha", 0.0)
            win.attributes("-topmost", True)
        except Exception:
            pass

        inner = tk.Frame(win, bg=BG)
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=self.title, font=F_TITLE, bg=BG, fg=FG,
                 justify="left", anchor="w", wraplength=330).pack(
            anchor="w", padx=11, pady=(8, 0))
        if self.body:
            tk.Label(inner, text=self.body, font=F_BODY, bg=BG, fg=FG_DIM,
                     justify="left", anchor="w", wraplength=330).pack(
                anchor="w", padx=11, pady=(3, 9))
        else:
            inner.pack_configure(pady=(1, 1))
            win.update_idletasks()

        win.update_idletasks()
        self._place(win)
        self._win = win
        self._alpha = 0.0
        self._fade_in()

    def _place(self, win: tk.Toplevel) -> None:
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except Exception:
            return
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = max(8, min(x, screen_w - w - 8))
        if y + h > screen_h - 40:                      # nao cabe embaixo: sobe
            y = max(8, self.widget.winfo_rooty() - h - 8)
        win.wm_geometry(f"+{int(x)}+{int(y)}")

    def _fade_in(self) -> None:
        if not self._win:
            return
        self._alpha = min(1.0, self._alpha + 0.2)
        try:
            self._win.attributes("-alpha", self._alpha)
        except Exception:
            return
        if self._alpha < 1.0:
            self._win.after(FADE_MS, self._fade_in)

    def _hide(self) -> None:
        if self._win is not None:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None
        if Tooltip._aberto is self:
            Tooltip._aberto = None

    # -------------------------------------------------------------- publico --
    def set_text(self, title: str, body: str = "") -> None:
        self.title, self.body = title, body


def tip(widget, title: str, body: str = "", delay: int = DELAY_MS) -> Tooltip:
    """Prende um balao de ajuda ao widget e devolve o balao."""
    return Tooltip(widget, title, body, delay)
