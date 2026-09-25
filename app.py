"""
Author: Adrien Protzel

Single-window dashboard for the transaction pipeline. One window stays open
from start to finish: the middle of it swaps between staging files, watching
them clean, reviewing whatever the maps could not name, and the summary.

Run it with:
    python app.py
"""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import pipeline

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    BaseWindow = TkinterDnD.Tk
    DRAG_AND_DROP = True
except ImportError:  # the app still works, it just needs the Add files button
    BaseWindow = tk.Tk
    DRAG_AND_DROP = False

BG = "#1b1e24"
PANEL = "#242933"
EDGE = "#333a47"
TEXT = "#e6e8eb"
MUTED = "#98a0ad"
ACCENT = "#4c8bf5"
GOOD = "#57b894"
WARN = "#e0a458"

TITLE_FONT = ("Segoe UI Semibold", 15)
HEAD_FONT = ("Segoe UI Semibold", 11)
BODY_FONT = ("Segoe UI", 10)
SMALL_FONT = ("Segoe UI", 9)
MONO_FONT = ("Consolas", 10)


def guess_keyword(description):
    """Suggest the part of a description worth matching on."""
    words = [w for w in description.split() if not any(c.isdigit() for c in w)]
    return " ".join(words[:2]) if words else description


def open_folder(path):
    """Show a file in the system file browser."""
    path = Path(path)
    if sys.platform == "win32":
        os.startfile(path.parent)
    elif sys.platform == "darwin":
        subprocess.run(["open", "-R", str(path)])
    else:
        subprocess.run(["xdg-open", str(path.parent)])


class Dashboard(BaseWindow):
    """The whole application: one window, four views."""

    def __init__(self):
        super().__init__()
        self.title("Transaction Pipeline")
        self.configure(bg=BG)
        self.geometry("920x640")
        self.minsize(820, 560)
        self._center()
        self._style()

        self.accounts = pipeline.load_accounts()
        self.merchants = pipeline.load_map(pipeline.MERCHANTS_PATH)
        self.categories = pipeline.load_map(pipeline.CATEGORIES_PATH)

        self.staged = []  # (Path, Account) waiting to be read
        self.transactions = []
        self.skipped = []
        self.queue = []  # what still needs a human
        self.ignored = set()  # descriptions the user chose to leave alone

        self._build_frame()
        self.show_import()

    # ---------------------------------------------------------------- chrome

    def _center(self):
        """Put the window in the middle of the screen."""
        self.update_idletasks()
        width, height = 920, 640
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _style(self):
        """Dark theme for the ttk widgets."""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=PANEL, background=PANEL,
                        foreground=TEXT, arrowcolor=TEXT, bordercolor=EDGE)
        style.configure("Bar.Horizontal.TProgressbar", troughcolor=PANEL,
                        background=ACCENT, bordercolor=PANEL, lightcolor=ACCENT,
                        darkcolor=ACCENT)
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    def _build_frame(self):
        """Header and status bar stay put; the body in between gets swapped."""
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(20, 0))
        tk.Label(header, text="Transaction Pipeline", bg=BG, fg=TEXT,
                 font=TITLE_FONT).pack(side="left")
        self.step_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=SMALL_FONT)
        self.step_label.pack(side="right")

        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=24, pady=16)

        self.status = tk.Label(self, text="", bg=BG, fg=MUTED, font=SMALL_FONT,
                               anchor="w")
        self.status.pack(fill="x", padx=24, pady=(0, 14))

    def _clear_body(self, step=""):
        """Empty the middle of the window before drawing the next view."""
        for child in self.body.winfo_children():
            child.destroy()
        self.step_label.config(text=step)

    def _panel(self, parent, **kwargs):
        """A card-looking frame."""
        return tk.Frame(parent, bg=PANEL, highlightbackground=EDGE,
                        highlightthickness=1, **kwargs)

    def _button(self, parent, text, command, primary=False, width=None):
        """A flat button, accented when it is the obvious next thing to press."""
        return tk.Button(
            parent, text=text, command=command,
            bg=ACCENT if primary else PANEL, fg="#ffffff" if primary else TEXT,
            activebackground=ACCENT if primary else EDGE, activeforeground="#ffffff",
            font=HEAD_FONT if primary else BODY_FONT, relief="flat",
            padx=16, pady=8, cursor="hand2",
            width=width, disabledforeground=MUTED,
        )

    # ------------------------------------------------------------ view: stage

    def show_import(self):
        """First view: pick an account, add statements, start the run."""
        self._clear_body(step="Step 1 of 3 - Import")
        self.status.config(text="")

        chooser = tk.Frame(self.body, bg=BG)
        chooser.pack(fill="x")
        tk.Label(chooser, text="Account", bg=BG, fg=MUTED,
                 font=SMALL_FONT).pack(side="left", padx=(0, 8))
        self.account_choice = ttk.Combobox(
            chooser, values=[a.label for a in self.accounts],
            state="readonly", width=34, font=BODY_FONT,
        )
        self.account_choice.current(0)
        self.account_choice.pack(side="left")
        self._button(chooser, "Add files", self.browse_files).pack(side="left", padx=8)
        self._button(chooser, "Load samples", self.load_samples).pack(side="left")

        hint = ("Drop statement files below" if DRAG_AND_DROP
                else "tkinterdnd2 is not installed, so use Add files")
        drop = tk.Label(self.body, text=hint + "\n\nEach file is tagged with the "
                        "account selected above.", bg=PANEL, fg=MUTED,
                        font=BODY_FONT, height=6, highlightbackground=EDGE,
                        highlightthickness=1)
        drop.pack(fill="x", pady=14)
        if DRAG_AND_DROP:
            drop.drop_target_register(DND_FILES)
            drop.dnd_bind("<<Drop>>", self.on_drop)

        self.staged_panel = self._panel(self.body)
        self.staged_panel.pack(fill="both", expand=True)

        footer = tk.Frame(self.body, bg=BG)
        footer.pack(fill="x", pady=(14, 0))
        self.run_button = self._button(footer, "Clean", self.run, primary=True)
        self.run_button.pack(side="right")
        self._button(footer, "Clear", self.clear_staged).pack(side="right", padx=8)

        self.draw_staged()

    def draw_staged(self):
        """Redraw the list of files waiting to be read."""
        for child in self.staged_panel.winfo_children():
            child.destroy()

        if not self.staged:
            tk.Label(self.staged_panel, text="No files staged yet.", bg=PANEL,
                     fg=MUTED, font=BODY_FONT).pack(pady=24)
            self.run_button.config(state="disabled", bg=PANEL, fg=MUTED)
            return

        self.run_button.config(state="normal", bg=ACCENT, fg="#ffffff",
                               text=f"Clean {len(self.staged)} file"
                                    f"{'s' if len(self.staged) > 1 else ''}")
        for index, (path, account) in enumerate(self.staged):
            row = tk.Frame(self.staged_panel, bg=PANEL)
            row.pack(fill="x", padx=14, pady=4)
            tk.Label(row, text=path.name, bg=PANEL, fg=TEXT, font=BODY_FONT,
                     anchor="w").pack(side="left")
            tk.Label(row, text=account.label, bg=PANEL, fg=MUTED,
                     font=SMALL_FONT).pack(side="left", padx=10)
            tk.Button(row, text="remove", command=lambda i=index: self.unstage(i),
                      bg=PANEL, fg=MUTED, relief="flat", font=SMALL_FONT,
                      activebackground=PANEL, cursor="hand2").pack(side="right")

    def selected_account(self):
        """The account currently chosen in the dropdown."""
        return self.accounts[self.account_choice.current()]

    def stage(self, paths):
        """Tag files with the selected account and queue them up."""
        account = self.selected_account()
        for path in paths:
            path = Path(path)
            if path.is_file():
                self.staged.append((path, account))
        self.draw_staged()
        self.status.config(text=f"{len(self.staged)} file(s) staged")

    def on_drop(self, event):
        """Handle files dropped onto the window."""
        self.stage(self.tk.splitlist(event.data))

    def browse_files(self):
        """Pick files through the normal file dialog."""
        self.stage(filedialog.askopenfilenames(
            title="Choose statement files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        ))

    def load_samples(self):
        """Stage the bundled sample statements, each with its own account."""
        pairs = pipeline.sample_files(self.accounts)
        if not pairs:
            self.status.config(text="No sample statements found.")
            return
        self.staged = list(pairs)
        self.draw_staged()
        self.status.config(text=f"Loaded {len(pairs)} sample statements.")

    def unstage(self, index):
        """Drop one file from the list."""
        self.staged.pop(index)
        self.draw_staged()

    def clear_staged(self):
        """Drop every staged file."""
        self.staged = []
        self.draw_staged()

    # --------------------------------------------------------- view: progress

    def run(self):
        """Read every staged file, then hand whatever is unresolved to review."""
        self._clear_body(step="Step 2 of 3 - Clean")
        self.transactions, self.skipped, self.ignored = [], [], set()

        panel = self._panel(self.body)
        panel.pack(fill="both", expand=True)
        tk.Label(panel, text="Reading statements", bg=PANEL, fg=TEXT,
                 font=HEAD_FONT).pack(pady=(28, 6))
        detail = tk.Label(panel, text="", bg=PANEL, fg=MUTED, font=BODY_FONT)
        detail.pack()
        bar = ttk.Progressbar(panel, style="Bar.Horizontal.TProgressbar",
                              length=460, maximum=len(self.staged))
        bar.pack(pady=18)

        for index, (path, account) in enumerate(self.staged, start=1):
            detail.config(text=f"{path.name}  ({account.label})")
            bar["value"] = index
            self.update_idletasks()
            try:
                read, skipped = pipeline.parse_statement(path, account)
            except OSError as error:
                self.skipped.append({"file": path.name, "account": account.label,
                                     "reason": str(error), "row": ""})
                continue
            self.transactions += read
            self.skipped += skipped

        self.status.config(
            text=f"Read {len(self.transactions)} transactions from "
                 f"{len(self.staged)} file(s), skipped {len(self.skipped)} row(s)."
        )
        self.refresh_queue()

    # ----------------------------------------------------------- view: review

    def refresh_queue(self):
        """
        Work out what still needs a person.

        Rebuilt from scratch after every answer, because one new keyword can
        resolve several pending descriptions at once.
        """
        self.queue = []
        unknown = pipeline.name_merchants(self.transactions, self.merchants)
        pending = [(raw, rows) for raw, rows in unknown.items()
                   if raw not in self.ignored]
        if pending:
            self.queue = [("merchant", raw, rows) for raw, rows in pending]
            self.show_review()
            return

        unknown = pipeline.categorize(self.transactions, self.categories)
        pending = [(name, rows) for name, rows in unknown.items()
                   if name not in self.ignored]
        if pending:
            self.queue = [("category", name, rows) for name, rows in pending]
            self.show_review()
            return

        self.finish()

    def show_review(self):
        """Ask about the first thing in the queue."""
        kind, subject, rows = self.queue[0]
        self._clear_body(step=f"Step 3 of 3 - Review ({len(self.queue)} left)")

        panel = self._panel(self.body)
        panel.pack(fill="both", expand=True)

        tk.Label(panel, text="Unknown merchant" if kind == "merchant"
                 else "Needs a category", bg=PANEL, fg=WARN,
                 font=SMALL_FONT).pack(anchor="w", padx=20, pady=(18, 2))
        tk.Label(panel, text=subject, bg=PANEL, fg=TEXT, font=MONO_FONT,
                 wraplength=820, justify="left").pack(anchor="w", padx=20)

        example = rows[0]
        detail = (f"{example['date']}    {example['amount']:.2f}    "
                  f"{example['bank']} {example['card']}")
        if len(rows) > 1:
            detail += f"    and {len(rows) - 1} more like it"
        tk.Label(panel, text=detail, bg=PANEL, fg=MUTED,
                 font=SMALL_FONT).pack(anchor="w", padx=20, pady=(4, 16))

        if kind == "merchant":
            form = tk.Frame(panel, bg=PANEL)
            form.pack(anchor="w", padx=20)
            tk.Label(form, text="Match on", bg=PANEL, fg=MUTED,
                     font=SMALL_FONT, width=10, anchor="e").grid(row=0, column=0, pady=3)
            self.keyword_entry = tk.Entry(form, bg=BG, fg=TEXT, font=BODY_FONT,
                                          insertbackground=TEXT, relief="flat", width=42)
            self.keyword_entry.grid(row=0, column=1, padx=8, ipady=4)
            self.keyword_entry.insert(0, guess_keyword(subject))

            tk.Label(form, text="Call it", bg=PANEL, fg=MUTED, font=SMALL_FONT,
                     width=10, anchor="e").grid(row=1, column=0, pady=3)
            self.name_entry = tk.Entry(form, bg=BG, fg=TEXT, font=BODY_FONT,
                                       insertbackground=TEXT, relief="flat", width=42)
            self.name_entry.grid(row=1, column=1, padx=8, ipady=4)
            self.name_entry.insert(0, guess_keyword(subject))

            tk.Label(panel, text="Matching is a substring test, so a short "
                     "keyword catches every store number.", bg=PANEL, fg=MUTED,
                     font=SMALL_FONT).pack(anchor="w", padx=20, pady=(10, 0))

        tk.Label(panel, text="Category", bg=PANEL, fg=MUTED,
                 font=SMALL_FONT).pack(anchor="w", padx=20, pady=(18, 6))
        buttons = tk.Frame(panel, bg=PANEL)
        buttons.pack(anchor="w", padx=16)
        for index, category in enumerate(pipeline.CATEGORIES):
            button = self._button(buttons, category.title(),
                                  lambda c=category: self.answer(c))
            button.grid(row=index // 5, column=index % 5, padx=4, pady=4, sticky="ew")

        footer = tk.Frame(panel, bg=PANEL)
        footer.pack(anchor="w", padx=20, pady=18)
        self._button(footer, "Skip", self.skip).pack(side="left")
        self._button(footer, "Stop and save", self.finish).pack(side="left", padx=8)

    def answer(self, category):
        """Save the answer to the mapping files and move on."""
        kind, subject, _ = self.queue[0]

        if kind == "merchant":
            keyword = self.keyword_entry.get().strip().lower()
            name = self.name_entry.get().strip().lower()
            if not keyword or not name:
                self.status.config(text="A keyword and a name are both needed.")
                return
            if keyword not in subject:
                self.status.config(
                    text=f"'{keyword}' does not appear in that description.")
                return
            pipeline.append_map(pipeline.MERCHANTS_PATH, keyword, name)
            self.merchants[keyword] = name
        else:
            name = subject

        if self.categories.get(name) != category:
            pipeline.append_map(pipeline.CATEGORIES_PATH, name, category)
            self.categories[name] = category

        self.status.config(text=f"Saved {name} as {category}.")
        self.refresh_queue()

    def skip(self):
        """Leave this one alone for now and go to the next."""
        _, subject, _ = self.queue[0]
        self.ignored.add(subject)
        self.refresh_queue()

    # ---------------------------------------------------------- view: summary

    def finish(self):
        """Categorize whatever is left, write the files, and show the totals."""
        pipeline.categorize(self.transactions, self.categories)
        for transaction in self.transactions:
            if not transaction["category"]:
                transaction["category"] = "misc"

        kept, dropped = pipeline.drop_transfers(self.transactions)
        output = pipeline.write_transactions(kept)
        skipped_file = pipeline.write_skipped(self.skipped)
        self.show_summary(kept, dropped, output, skipped_file)

    def show_summary(self, kept, dropped, output, skipped_file):
        """Last view: what came out, and where it went."""
        self._clear_body(step="Done")

        panel = self._panel(self.body)
        panel.pack(fill="both", expand=True)

        tk.Label(panel, text=f"{len(kept)} transactions written", bg=PANEL,
                 fg=GOOD, font=HEAD_FONT).pack(anchor="w", padx=20, pady=(18, 2))
        notes = [f"{len(dropped)} transfer(s) dropped"]
        if self.skipped:
            notes.append(f"{len(self.skipped)} row(s) unreadable")
        if self.ignored:
            notes.append(f"{len(self.ignored)} left unmapped")
        tk.Label(panel, text="   ".join(notes), bg=PANEL, fg=MUTED,
                 font=SMALL_FONT).pack(anchor="w", padx=20)

        totals = pipeline.summarize(kept)
        table = tk.Frame(panel, bg=PANEL)
        table.pack(anchor="w", padx=20, pady=16)
        for row, (category, total) in enumerate(totals.items()):
            tk.Label(table, text=category, bg=PANEL, fg=TEXT, font=BODY_FONT,
                     width=16, anchor="w").grid(row=row, column=0, pady=1)
            tk.Label(table, text=f"{total:,.2f}", bg=PANEL, fg=TEXT,
                     font=MONO_FONT, width=12, anchor="e").grid(row=row, column=1)

        tk.Label(panel, text=str(output), bg=PANEL, fg=MUTED, font=SMALL_FONT,
                 wraplength=820, justify="left").pack(anchor="w", padx=20)
        if skipped_file:
            tk.Label(panel, text=str(skipped_file), bg=PANEL, fg=WARN,
                     font=SMALL_FONT).pack(anchor="w", padx=20, pady=(2, 0))

        footer = tk.Frame(panel, bg=PANEL)
        footer.pack(anchor="w", padx=20, pady=18)
        self._button(footer, "Show file", lambda: open_folder(output),
                     primary=True).pack(side="left")
        self._button(footer, "Start over", self.restart).pack(side="left", padx=8)

    def restart(self):
        """Back to an empty import view, mappings kept."""
        self.staged, self.transactions, self.skipped = [], [], []
        self.queue, self.ignored = [], set()
        self.show_import()


if __name__ == "__main__":
    Dashboard().mainloop()
