"""
Author: Adrien Protzel

This script converts a CSV file to a JSON file and then removes the original CSV file.

Modules used:
- csv: For reading the CSV file.
- json: For writing the JSON file.
- os: For interacting with the operating system.

Functions:
- csv_to_json(csv_file_path, json_file_path): Converts a CSV file to a JSON file and removes the original CSV file.
"""

import csv
import json
import os

def csv_to_json(csv_file_path, json_file_path):
    """Convert a CSV file to a JSON file and remove the original CSV file."""
    # Read the CSV file
    with open(csv_file_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        data = [row for row in csv_reader]

    # Write the data to a JSON file
    with open(json_file_path, mode='w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4)

    # Remove the old CSV file
    os.remove(csv_file_path)

# Specify the file paths
csv_file_path = 'Data/clean.csv'
json_file_path = 'Data/clean.json'

# Convert the CSV to JSON and remove the old CSV file
csv_to_json(csv_file_path, json_file_path)
