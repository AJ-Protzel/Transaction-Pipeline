"""
Author: Adrien Protzel

This program sequentially calls other scripts to import, manage, and clean data.
"""

import subprocess

if __name__ == "__main__":
    # Csk user to import files and to which folder <Type>_<Bank>_<Card>
    subprocess.run(["python", "file_importer.py"])
    print("File Importing......Done")

    # Cleans headers and merges multiple files in single bank account file
    subprocess.run(["python", "file_merger.py"])
    print("File Merging......Done")

    # Removes, renames, adds, splits columns, merges into single clean file in Clean folder
    subprocess.run(["python", "file_cleaner.py"])
    print("File Cleaning......Done")

    # Convert CSV to JSON
    subprocess.run(["python", "CSV_to_JSON.py"])
    print("CSV to JSON......Done")

    # Convert JSONto CSV
    subprocess.run(["python", "JSON_to_CSV.py"])
    print("JSON to CSV......Done")
