"""
Author: Adrien Protzel

Statement parsing, merchant naming, and categorization for the transaction
pipeline. Nothing here touches the user interface, so every step is importable
and testable on its own.
"""

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACCOUNTS_PATH = ROOT / "accounts.json"
MERCHANTS_PATH = ROOT / "merchants.csv"
CATEGORIES_PATH = ROOT / "categories.csv"
SAMPLES_DIR = ROOT / "sample_statements"
OUTPUT_PATH = ROOT / "transactions.csv"
SKIPPED_PATH = ROOT / "skipped_rows.csv"

# A column named "*" is one the bank exports and the pipeline throws away.
IGNORED_COLUMN = "*"

# The one place the category list lives. The dashboard builds its buttons from
# this, and a mapping is refused if its category is not in here.
CATEGORIES = [
    "groceries",
    "dining",
    "gas",
    "shopping",
    "travel",
    "utilities",
    "subscriptions",
    "cash",
    "transfer",
    "misc",
]

# Card payments and internal movements are bookkeeping, not spending, so they
# never reach the output file.
DROPPED_CATEGORIES = {"transfer"}

OUTPUT_COLUMNS = [
    "year",
    "month",
    "date",
    "description",
    "category",
    "amount",
    "type",
    "bank",
    "card",
]


@dataclass(frozen=True)
class Account:
    """One card or bank account, and how its exported file is laid out."""

    type: str
    bank: str
    card: str
    skip_rows: int
    columns: tuple
    date_format: str
    amount_sign: int

    @property
    def slug(self):
        """Filename-safe identifier, also used to match sample statements."""
        return f"{self.type}_{self.bank}_{self.card}"

    @property
    def label(self):
        """Readable name for the dashboard dropdown."""
        return f"{self.type} - {self.bank} - {self.card}"


def load_accounts(path=ACCOUNTS_PATH):
    """Read the account definitions."""
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    return [
        Account(
            type=entry["type"],
            bank=entry["bank"],
            card=entry["card"],
            skip_rows=entry.get("skip_rows", 0),
            columns=tuple(entry["columns"]),
            date_format=entry.get("date_format", "%m/%d/%Y"),
            amount_sign=entry.get("amount_sign", 1),
        )
        for entry in entries
    ]


def load_map(path):
    """Read a two-column mapping file into a lowercase dict."""
    mapping = {}
    if not Path(path).exists():
        return mapping
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) >= 2 and row[0].strip():
                mapping[row[0].strip().lower()] = row[1].strip().lower()
    return mapping


def append_map(path, key, value):
    """Add one entry to a mapping file, creating it with a header if needed."""
    path = Path(path)
    header = ["merchant", "category"] if path.name == CATEGORIES_PATH.name else ["keyword", "merchant"]
    exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(header)
        writer.writerow([key.strip().lower(), value.strip().lower()])


def parse_amount(text):
    """Turn a bank's amount field into a float. Parentheses mean negative."""
    cleaned = re.sub(r"[^0-9.()-]", "", str(text).strip())
    if not cleaned:
        raise ValueError("empty amount")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("()")
    value = float(cleaned)
    return -value if negative else value


def parse_statement(path, account):
    """
    Read one exported statement.

    Returns the transactions it could read and the rows it could not, rather
    than guessing at a row it does not understand.
    """
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    transactions = []
    skipped = []
    for row in rows[account.skip_rows:]:
        if not any(cell.strip() for cell in row):
            continue
        transaction, reason = _build_transaction(row, account)
        if transaction is None:
            skipped.append(
                {
                    "file": Path(path).name,
                    "account": account.label,
                    "reason": reason,
                    "row": ",".join(row),
                }
            )
        else:
            transactions.append(transaction)
    return transactions, skipped


def _build_transaction(row, account):
    """Turn one raw CSV row into a transaction, or explain why it cannot."""
    if len(row) != len(account.columns):
        return None, "expected {} columns, found {}".format(len(account.columns), len(row))

    fields = {
        column: value
        for column, value in zip(account.columns, row)
        if column != IGNORED_COLUMN
    }

    raw_date = fields.get("Date", "").strip()
    if raw_date.lower() == "date":
        return None, "header row"
    try:
        date = datetime.strptime(raw_date, account.date_format)
    except ValueError:
        return None, "unreadable date: " + raw_date

    raw_amount = fields.get("Amount", "").strip()
    try:
        amount = parse_amount(raw_amount) * account.amount_sign
    except ValueError:
        return None, "unreadable amount: " + raw_amount

    return make_transaction(
        date=date,
        description=fields.get("Description", ""),
        amount=amount,
        account=account,
    ), None


def make_transaction(date, description, amount, account):
    """Build a transaction in the shape the rest of the pipeline expects."""
    raw = " ".join(str(description).split()).lower()
    return {
        "year": date.year,
        "month": date.strftime("%B"),
        "date": date.strftime("%Y-%m-%d"),
        "raw": raw,
        "description": raw,
        "category": "",
        "amount": round(amount, 2),
        "type": account.type,
        "bank": account.bank,
        "card": account.card,
    }


def keyword_pattern(keyword):
    """
    Build the matcher for one keyword.

    A plain substring test is too eager: "fee" would claim every coffee shop
    and "ross" every crossroads. So a keyword has to start and end on a word
    boundary -- but only at the ends that are themselves word characters, or a
    keyword like "rei #" would stop matching the store number that follows it.
    """
    before = r"(?<!\w)" if re.match(r"\w", keyword[:1]) else ""
    after = r"(?!\w)" if re.match(r"\w", keyword[-1:]) else ""
    return re.compile(before + re.escape(keyword) + after)


def keyword_matches(keyword, description):
    """Whether a keyword would claim a description."""
    return bool(keyword_pattern(keyword.strip().lower()).search(description))


def name_merchants(transactions, merchants):
    """
    Replace raw descriptions with merchant names.

    Keywords are matched longest first, so "amazon prime" wins over "amazon"
    whatever order the mapping file happens to be in.
    """
    matchers = [
        (keyword_pattern(keyword), merchants[keyword])
        for keyword in sorted(merchants, key=len, reverse=True)
    ]
    unknown = {}
    for transaction in transactions:
        match = next(
            (name for pattern, name in matchers
             if pattern.search(transaction["raw"])),
            None,
        )
        if match:
            transaction["description"] = match
        else:
            transaction["description"] = transaction["raw"]
            unknown.setdefault(transaction["raw"], []).append(transaction)
    return unknown


def categorize(transactions, categories):
    """Apply the category map, returning the merchants it has nothing for."""
    unknown = {}
    for transaction in transactions:
        category = categories.get(transaction["description"], "")
        transaction["category"] = category
        if not category:
            unknown.setdefault(transaction["description"], []).append(transaction)
    return unknown


def drop_transfers(transactions):
    """Split off the rows that move money between accounts rather than spend it."""
    kept = [t for t in transactions if t["category"] not in DROPPED_CATEGORIES]
    dropped = [t for t in transactions if t["category"] in DROPPED_CATEGORIES]
    return kept, dropped


def summarize(transactions):
    """Total the transactions by category, largest spend first."""
    totals = {}
    for transaction in transactions:
        category = transaction["category"] or "misc"
        totals[category] = round(totals.get(category, 0.0) + transaction["amount"], 2)
    return dict(sorted(totals.items(), key=lambda item: item[1]))


def write_transactions(transactions, path=OUTPUT_PATH):
    """Write the finished transactions out."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for transaction in sorted(transactions, key=lambda t: t["date"]):
            row = dict(transaction)
            row["amount"] = "{:.2f}".format(transaction["amount"])
            writer.writerow(row)
    return Path(path)


def write_skipped(skipped, path=SKIPPED_PATH):
    """Write the rows that could not be read, so nothing disappears silently."""
    path = Path(path)
    if not skipped:
        path.unlink(missing_ok=True)
        return None
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "account", "reason", "row"])
        writer.writeheader()
        writer.writerows(skipped)
    return path


def sample_files(accounts, directory=SAMPLES_DIR):
    """Pair each sample statement with the account named in its filename."""
    pairs = []
    for account in accounts:
        path = Path(directory) / (account.slug + ".csv")
        if path.exists():
            pairs.append((path, account))
    return pairs
