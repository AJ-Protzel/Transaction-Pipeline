"""
Author: Adrien Protzel

This program processes files in specified directories created by file_importer.py and formats based on configurations provided in a config.json file. 

It removes or adds headers as needed, records bad lines, and merges like files.
"""

import json
import csv
from pathlib import Path

def load_config(config_path):
    """
    Load the configuration file.

    Args:
        config_path (Path): Path to the configuration file.

    Returns:
        dict: Configuration data.
    """
    with open(config_path, 'r') as config_file:
        return json.load(config_file)

def get_directories(folder_path):
    """
    Get a list of directories in the specified folder path.

    Args:
        folder_path (Path): Path to the folder containing directories.

    Returns:
        list: List of directory paths.
    """
    return [d for d in folder_path.iterdir() if d.is_dir()]

def process_file(file, remove_rows, bad_lines_path):
    """
    Process a single file by removing specified rows, checking for bad lines, and returning cleaned lines.

    Args:
        file (Path): Path to the file to be processed.
        remove_rows (int): Number of rows to remove from the top of the file.
        bad_lines_path (Path): Path to the bad lines log file.

    Returns:
        list: List of cleaned lines.
    """
    try:
        # Read the file, skipping the specified number of rows
        with file.open('r') as f:
            lines = f.readlines()

        # Remove the specified number of rows
        lines = lines[remove_rows:]

        # Write the modified lines back to the file
        with file.open('w') as f:
            f.writelines(lines)

        # Check for bad lines and write them to bad_lines.txt
        with file.open('r') as f:
            reader = csv.reader(f)
            lines = list(reader)

        cleaned_lines = []
        with open(bad_lines_path, 'a') as bad_lines_log:
            for row in lines:
                if len(row) != len(lines[0]):  # Check if the row length matches the header length
                    bad_lines_log.write(f"{file}: {row}\n")  # Log bad lines
                else:
                    cleaned_lines.append(row)  # Add valid rows to the cleaned_lines list

        # Remove the old file
        file.unlink()
        return cleaned_lines

    except Exception as e:
        print(f"Error processing file {file}: {e}")
        return []

def merge_files(directory, config, all_lines):
    """
    Merge all cleaned lines into a new file and add a header if specified.

    Args:
        directory (Path): Path to the directory containing the files.
        config (dict): Configuration data for the directory.
        all_lines (list): List of all cleaned lines to be merged.
    """
    merged_file_path = directory / f"{config['type']}_{config['bank']}_{config['card']}.csv"
    with merged_file_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(all_lines)

    # Add header if specified
    if 'add_header' in config:
        with merged_file_path.open('r') as f:
            lines = f.readlines()
        lines.insert(0, ','.join(config['add_header']) + '\n')
        with merged_file_path.open('w') as f:
            f.writelines(lines)

def main():
    """
    Main function to process files in specified directories based on configurations.
    """
    # Define the folder path
    folder_path = Path('Data')

    # Load the configuration file
    config_path = Path('Configs/config.json')
    config_data = load_config(config_path)

    # Create a dictionary to map folder names to their configurations
    folder_config = {f"{entry['type']}_{entry['bank']}_{entry['card']}": entry for entry in config_data}

    # List all directories in the specified folder path
    directories = get_directories(folder_path)

    # Iterate through each directory and apply the remove_rows value to the files
    for directory in directories:
        directory_formatted = directory.name.replace(' ', '_')
        if directory_formatted in folder_config:
            config = folder_config[directory_formatted]
            remove_rows = config['remove_rows']
            bad_lines_path = folder_path / 'bad_lines.txt'
            all_lines = []

            for file in directory.iterdir():
                if file.is_file():
                    cleaned_lines = process_file(file, remove_rows, bad_lines_path)
                    all_lines.extend(cleaned_lines)

            merge_files(directory, config, all_lines)

if __name__ == "__main__":
    main()
    