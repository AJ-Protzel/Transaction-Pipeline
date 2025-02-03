"""
Author: Adrien Protzel

This script converts a JSON file to a CSV file and then removes the original JSON file.

Modules used:
- csv: For writing the CSV file.
- json: For reading the JSON file.
- os: For interacting with the operating system.

Functions:
- json_to_csv(json_file_path, csv_file_path): Converts a JSON file to a CSV file and removes the original JSON file.
"""

import csv
import json
import os

def json_to_csv(json_file_path, csv_file_path):
    """
    Convert a JSON file to a CSV file and remove the original JSON file.

    Args:
        json_file_path (str): Path to the JSON file.
        csv_file_path (str): Path to the CSV file.
    """
    # Read the JSON file
    with open(json_file_path, mode='r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # Get the keys for the CSV header from the first dictionary in the list
    header = data[0].keys()

    # Write the data to a CSV file
    with open(csv_file_path, mode='w', encoding='utf-8', newline='') as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=header)
        csv_writer.writeheader()
        csv_writer.writerows(data)

    # Remove the old JSON file
    os.remove(json_file_path)

# Specify the file paths
json_file_path = 'Data/clean.json'
csv_file_path = 'Data/clean.csv'

# Convert the JSON to CSV and remove the old JSON file
json_to_csv(json_file_path, csv_file_path)
