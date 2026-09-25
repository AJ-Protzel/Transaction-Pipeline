"""
Author: Adrien Protzel

Tests for the pipeline, run against the bundled sample statements.

    python -m unittest
"""

import csv
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import pipeline


class ParseAmountTests(unittest.TestCase):
    """Banks write amounts in more than one way."""

    def test_plain_number(self):
        self.assertEqual(pipeline.parse_amount("42.18"), 42.18)

    def test_currency_and_thousands(self):
        self.assertEqual(pipeline.parse_amount("$1,204.50"), 1204.50)

    def test_leading_minus(self):
        self.assertEqual(pipeline.parse_amount("-71.22"), -71.22)

    def test_parentheses_mean_negative(self):
        self.assertEqual(pipeline.parse_amount("(18.30)"), -18.30)

    def test_empty_is_an_error(self):
        with self.assertRaises(ValueError):
            pipeline.parse_amount("   ")


class AccountTests(unittest.TestCase):
    """Every account should be usable and every sample should have one."""

    def setUp(self):
        self.accounts = pipeline.load_accounts()

    def test_accounts_load(self):
        self.assertTrue(self.accounts)

    def test_slug_splits_into_three_parts(self):
        for account in self.accounts:
            self.assertEqual(len(account.slug.split("_")), 3, account.slug)

    def test_date_format_is_usable(self):
        for account in self.accounts:
            datetime.strptime(
                datetime(2025, 1, 2).strftime(account.date_format),
                account.date_format,
            )

    def test_every_account_has_a_sample(self):
        pairs = pipeline.sample_files(self.accounts)
        self.assertEqual(len(pairs), len(self.accounts))


class ParseStatementTests(unittest.TestCase):
    """Reading the sample statements, each in its own export format."""

    def setUp(self):
        self.accounts = {a.card: a for a in pipeline.load_accounts()}

    def parse(self, card):
        account = self.accounts[card]
        path = pipeline.SAMPLES_DIR / (account.slug + ".csv")
        return pipeline.parse_statement(path, account)

    def test_headerless_file_with_positive_amounts(self):
        transactions, skipped = self.parse("Rewards")
        self.assertEqual(len(transactions), 6)
        self.assertEqual(skipped, [])
        # The file records spending as positive, so amount_sign flips it.
        costco = transactions[0]
        self.assertEqual(costco["amount"], -42.18)
        self.assertEqual(costco["date"], "2025-01-04")

    def test_header_row_is_skipped(self):
        transactions, skipped = self.parse("Cashback")
        self.assertEqual(len(transactions), 5)
        self.assertEqual(skipped, [])
        self.assertTrue(all(t["amount"] < 0 for t in transactions))

    def test_iso_dates_are_normalized(self):
        transactions, _ = self.parse("Everyday")
        self.assertEqual(transactions[0]["date"], "2025-01-02")
        self.assertEqual(transactions[0]["month"], "January")
        self.assertEqual(transactions[0]["year"], 2025)

    def test_short_row_is_reported_not_guessed(self):
        transactions, skipped = self.parse("Everyday")
        self.assertEqual(len(transactions), 4)
        self.assertEqual(len(skipped), 1)
        self.assertIn("found 6", skipped[0]["reason"])

    def test_preamble_rows_are_skipped(self):
        transactions, skipped = self.parse("Checking")
        self.assertEqual(len(transactions), 5)
        self.assertEqual(skipped, [])
        self.assertEqual(transactions[0]["amount"], 400.00)

    def test_descriptions_are_lowercased_and_squeezed(self):
        transactions, _ = self.parse("Rewards")
        self.assertEqual(transactions[1]["raw"], "starbucks store 44119")


class MappingTests(unittest.TestCase):
    """Naming merchants and giving them categories."""

    def account(self):
        return pipeline.load_accounts()[0]

    def transaction(self, description, amount=-1.00):
        return pipeline.make_transaction(
            datetime(2025, 1, 1), description, amount, self.account()
        )

    def test_longest_keyword_wins(self):
        merchants = {"amazon": "amazon", "amazon prime": "amazon prime"}
        transactions = [self.transaction("AMAZON PRIME*4K2M1")]
        pipeline.name_merchants(transactions, merchants)
        self.assertEqual(transactions[0]["description"], "amazon prime")

    def test_keywords_do_not_match_inside_a_longer_word(self):
        merchants = {"fee": "fee", "ross": "ross", "ups": "ups",
                     "apple": "apple store"}
        descriptions = ["sunrise coffee house", "crossroads market 22",
                        "backups inc", "pineapple express cafe"]
        transactions = [self.transaction(d) for d in descriptions]
        unknown = pipeline.name_merchants(transactions, merchants)
        self.assertEqual(sorted(unknown), sorted(descriptions))

    def test_keywords_still_match_a_trailing_store_number(self):
        merchants = {"rei #": "rei", "ups": "ups", "amzn mktp": "amazon"}
        transactions = [self.transaction(d) for d in
                        ["rei #161 outdoors", "ups store 4412",
                         "amzn mktp us*2m40k"]]
        pipeline.name_merchants(transactions, merchants)
        self.assertEqual([t["description"] for t in transactions],
                         ["rei", "ups", "amazon"])

    def test_keyword_matches_agrees_with_naming(self):
        self.assertTrue(pipeline.keyword_matches("Costco", "costco whse #0812"))
        self.assertFalse(pipeline.keyword_matches("fee", "the coffee bean"))

    def test_unknown_descriptions_are_grouped(self):
        transactions = [
            self.transaction("SUNRISE BAGEL CO 883"),
            self.transaction("SUNRISE BAGEL CO 883"),
        ]
        unknown = pipeline.name_merchants(transactions, {})
        self.assertEqual(list(unknown), ["sunrise bagel co 883"])
        self.assertEqual(len(unknown["sunrise bagel co 883"]), 2)

    def test_categories_come_from_the_merchant_name(self):
        transactions = [self.transaction("COSTCO WHSE #0812")]
        pipeline.name_merchants(transactions, {"costco": "costco"})
        unknown = pipeline.categorize(transactions, {"costco": "groceries"})
        self.assertEqual(transactions[0]["category"], "groceries")
        self.assertEqual(unknown, {})

    def test_transfers_are_dropped(self):
        transactions = [self.transaction("A"), self.transaction("B")]
        transactions[0]["category"] = "transfer"
        transactions[1]["category"] = "dining"
        kept, dropped = pipeline.drop_transfers(transactions)
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(dropped), 1)

    def test_every_shipped_category_is_a_known_one(self):
        categories = pipeline.load_map(pipeline.CATEGORIES_PATH)
        unknown = set(categories.values()) - set(pipeline.CATEGORIES)
        self.assertEqual(unknown, set())

    def test_every_merchant_has_a_category(self):
        merchants = pipeline.load_map(pipeline.MERCHANTS_PATH)
        categories = pipeline.load_map(pipeline.CATEGORIES_PATH)
        self.assertEqual(set(merchants.values()) - set(categories), set())

    def test_append_map_writes_a_header_once(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "merchants.csv"
            pipeline.append_map(path, "Sunrise Bagel", "Sunrise Bagel")
            pipeline.append_map(path, "Meridian Books", "Meridian Books")
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["keyword", "merchant"])
        self.assertEqual(rows[1], ["sunrise bagel", "sunrise bagel"])
        self.assertEqual(len(rows), 3)


class EndToEndTests(unittest.TestCase):
    """Every sample statement through the whole pipeline."""

    def setUp(self):
        accounts = pipeline.load_accounts()
        self.merchants = pipeline.load_map(pipeline.MERCHANTS_PATH)
        self.categories = pipeline.load_map(pipeline.CATEGORIES_PATH)
        self.transactions, self.skipped = [], []
        for path, account in pipeline.sample_files(accounts):
            read, skipped = pipeline.parse_statement(path, account)
            self.transactions += read
            self.skipped += skipped

    def test_the_sample_run_reads_every_readable_row(self):
        self.assertEqual(len(self.transactions), 24)
        self.assertEqual(len(self.skipped), 1)

    def test_only_the_invented_merchants_need_review(self):
        unknown = pipeline.name_merchants(self.transactions, self.merchants)
        self.assertEqual(
            sorted(unknown),
            ["meridian books", "netflix monthly", "sunrise bagel co 883"],
        )

    def test_output_has_one_row_per_kept_transaction(self):
        pipeline.name_merchants(self.transactions, self.merchants)
        pipeline.categorize(self.transactions, self.categories)
        for transaction in self.transactions:
            if not transaction["category"]:
                transaction["category"] = "misc"
        kept, dropped = pipeline.drop_transfers(self.transactions)
        self.assertEqual(len(dropped), 2)

        with tempfile.TemporaryDirectory() as folder:
            path = pipeline.write_transactions(kept, Path(folder) / "out.csv")
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), len(kept))
        self.assertEqual(list(rows[0]), pipeline.OUTPUT_COLUMNS)
        self.assertEqual(rows, sorted(rows, key=lambda r: r["date"]))
        self.assertTrue(all(r["category"] in pipeline.CATEGORIES for r in rows))

    def test_totals_add_up(self):
        pipeline.name_merchants(self.transactions, self.merchants)
        pipeline.categorize(self.transactions, self.categories)
        kept, _ = pipeline.drop_transfers(self.transactions)
        totals = pipeline.summarize(kept)
        self.assertAlmostEqual(sum(totals.values()),
                               sum(t["amount"] for t in kept), places=2)


if __name__ == "__main__":
    unittest.main()
