"""
Author: Adrien Protzel

This program sequentially calls other scripts to import, manage, and clean data.
"""

import subprocess
import sys


def run_step(script, label):
    """Run a pipeline step and stop the pipeline if it fails."""
    result = subprocess.run([sys.executable, script])
    if result.returncode != 0:
        print(f"{label}......Failed")
        raise SystemExit(result.returncode)
    print(f"{label}......Done")


if __name__ == "__main__":
    # Ask user to import files and to which folder <Type>_<Bank>_<Card>
    run_step("file_importer.py", "File Importing")

    # Cleans headers and merges multiple files in single bank account file
    run_step("file_merger.py", "File Merging")

    # Removes, renames, adds, splits columns, merges into single clean file in clean folder
    run_step("file_cleaner.py", "File Cleaning")

    # Convert CSV to JSON
    run_step("csv_to_json.py", "CSV to JSON")

    # Convert JSON to CSV
    run_step("json_to_csv.py", "JSON to CSV")
