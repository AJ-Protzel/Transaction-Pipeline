# Transaction Pipeline

A Python-based transaction import and cleanup pipeline for bank and card statement files.

## Overview

This repository provides an end-to-end pipeline for importing transaction files, normalizing headers, cleaning data, categorizing descriptions, and converting between CSV and JSON.

The main orchestration script is `main.py`, which runs the import, merge, clean, and file conversion steps in sequence.

## Repository Structure

- `main.py` - Runs the full processing pipeline in order.
- `file_importer.py` - GUI file organizer to drag-and-drop files into `Data/<Type>_<Bank>_<Card>` folders.
- `file_merger.py` - Processes imported files, removes unwanted rows, merges like files, and adds headers.
- `file_cleaner.py` - Cleans merged CSVs, normalizes columns, adds metadata, removes bad rows, and invokes downstream changers.
- `bad_lines_cleaner.py` - GUI tool to review and correct bad CSV rows manually.
- `desc_cleaner.py` - Maps transaction descriptions to normalized descriptions.
- `cat_cleaner.py` - Maps transactions to categories and produces `Data/clean.csv`.
- `CSV_to_JSON.py` - Converts `Data/clean.csv` to `Data/clean.json`.
- `JSON_to_CSV.py` - Converts `Data/clean.json` back to `Data/clean.csv`.
- `Configs/config.json` - Configuration rules for imported file folders, header mapping, and row removal.
- `Configs/Maps/Description_map.txt` - Description keyword mapping file.
- `Configs/Maps/Category_map.txt` - Category keyword mapping file.

## Requirements

- Python 3.x
- `pandas`
- `tkinter` (usually included with Python)
- `tkinterdnd2`

Install dependencies with pip:

```bash
pip install pandas tkinterdnd2
```

## Usage

1. Place transaction files into the application by running:
   ```bash
   python file_importer.py
   ```
2. Use the GUI to select `Type`, `Bank`, and `Card`, then drag and drop files into the app.
3. Run the pipeline from `main.py`:
   ```bash
   python main.py
   ```

This will execute the following steps:

1. `file_importer.py` - organizes imported files into `Data/<Type>_<Bank>_<Card>` folders.
2. `file_merger.py` - removes header rows, merges files by folder, and writes a cleaned CSV.
3. `file_cleaner.py` - normalizes CSVs, adds metadata columns, removes bad lines, and runs description and category cleaning.
4. `CSV_to_JSON.py` - converts `Data/clean.csv` into `Data/clean.json`.
5. `JSON_to_CSV.py` - converts `Data/clean.json` back into `Data/clean.csv`.

## Configuration

The `Configs/config.json` file defines processing rules for each file source. Each entry includes:

- `type` - e.g. `Credit` or `Debit`
- `bank` - bank name
- `card` - card or account name
- `remove_rows` - number of top rows to drop from imported files
- `add_header` - header row to insert after merging

Example entry:

```json
{
  "type": "Credit",
  "bank": "Chase",
  "card": "Freedom",
  "remove_rows": 1,
  "add_header": ["Date", "*", "Description", "*", "*", "Amount", "*"]
}
```

## Mapping Files

- `Configs/Maps/description_map.txt` is used by `desc_cleaner.py` to normalize raw transaction descriptions.
- `Configs/Maps/category_map.txt` is used by `cat_cleaner.py` to assign categories such as `grocery`, `dining`, `travel`, `transfer`, and `cash`.

If a description or category is not found, the pipeline opens a manual GUI prompt to add a mapping.

## Output

- `Data/dirty.csv` - intermediate merged and cleaned data
- `Data/clean.csv` - final cleaned transactions with categories
- `Data/clean.json` - JSON version of the final cleaned data

## Notes

- The pipeline currently uses manual GUI prompts for unmapped descriptions and categories.
- Future improvements may include:
  - refactoring into reusable functions
  - consolidating all GUI steps into a single persistent window
  - automating category mapping for more transaction types

## License

This repository does not include an explicit license. Add one as needed.
