"""
Author: Adrien Protzel

This script processes CSV files in a directory by performing various cleaning and transformation tasks.
It merges the cleaned data into a single CSV file and then runs additional cleaning scripts.

Modules used:
- os: For interacting with the operating system.
- pandas: For data manipulation and analysis.
- json: For reading configuration files.
- shutil: For file operations.
- subprocess: For running external scripts.
- datetime: For date and time operations.

Functions:
- list_files_in_directory(directory): Lists all files in a directory and its subdirectories.
- remove_star_columns_from_csv(file_path): Removes columns labeled "*" from a CSV file.
- update_csv_header(file_path, new_header): Updates the header of a CSV file and adds empty fields for new columns if necessary.
- fill_in_type_bank_card(file_path, config): Fills in Type, Bank, and Card columns based on a configuration.
- clean_amount_column(file_path): Cleans the Amount column by converting it to a float with two decimal places.
- fill_year_month_columns(file_path): Extracts Year and Month from the Date column.
- remove_empty_amount_rows(file_path): Removes rows where the Amount column is empty or NaN.
"""

import os
import pandas as pd
import json
import shutil
import subprocess
from datetime import datetime

def list_files_in_directory(directory):
    """List all files in a directory and its subdirectories."""
    file_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths

def remove_star_columns_from_csv(file_path):
    """Remove columns labeled "*" from a CSV file."""
    df = pd.read_csv(file_path)
    df = df.loc[:, ~df.columns.str.contains('\\*')]
    df.to_csv(file_path, index=False)

def update_csv_header(file_path, new_header):
    """Update the header of a CSV file and add empty fields for new columns if necessary."""
    df = pd.read_csv(file_path)
    for column in new_header:
        if column not in df.columns:
            df[column] = ""
    df = df[new_header]
    df.to_csv(file_path, index=False)

def fill_in_type_bank_card(file_path, config):
    """Fill in Type, Bank, and Card columns based on a configuration."""
    df = pd.read_csv(file_path)
    df['Type'] = config['type']
    df['Bank'] = config['bank']
    df['Card'] = config['card']
    df.to_csv(file_path, index=False)

def clean_amount_column(file_path):
    """Clean the Amount column by converting it to a float with two decimal places."""
    df = pd.read_csv(file_path)
    df['Amount'] = df['Amount'].replace(r'[\$,]', '', regex=True).astype(float)
    df['Amount'] = df['Amount'].map('{:.2f}'.format)
    df.to_csv(file_path, index=False)

def fill_year_month_columns(file_path):
    """Extract Year and Month from the Date column."""
    df = pd.read_csv(file_path)
    df['Year'] = pd.to_datetime(df['Date'], format='%m/%d/%Y').dt.year
    df['Month'] = pd.to_datetime(df['Date'], format='%m/%d/%Y').dt.strftime('%B')
    df.to_csv(file_path, index=False)

def remove_empty_amount_rows(file_path):
    """Remove rows where the Amount column is empty or NaN."""
    df = pd.read_csv(file_path)
    df = df[df['Amount'].notna() & (df['Amount'] != '')]
    df.to_csv(file_path, index=False)

# Directory to search
directory = 'Data'

# Load config.json from Configs folder
with open('Configs/config.json', 'r') as f:
    configs = json.load(f)

# New header to be applied to all CSV files
new_header = ["Year", "Month", "Date", "Description", "Category", "Amount", "Type", "Bank", "Card"]

# Get list of all files in the directory and its subdirectories
all_files = list_files_in_directory(directory)

# List to store all dataframes for merging later
dataframes = []

# Process each CSV file to remove columns labeled "*", update the header, fill in Type, Bank, Card, and clean Amount column
for file in all_files:
    if file.endswith('.csv'):
        remove_star_columns_from_csv(file)
        update_csv_header(file, new_header)
        
        # Determine the folder name and match it with config
        folder_name = os.path.basename(os.path.dirname(file))
        for config in configs:
            if folder_name == f"{config['type']}_{config['bank']}_{config['card']}":
                fill_in_type_bank_card(file, config)
                break
        
        clean_amount_column(file)
        
        # Read the cleaned CSV into a dataframe and add it to the list of dataframes
        dataframes.append(pd.read_csv(file))

# Merge all dataframes into a single dataframe
merged_df = pd.concat(dataframes)

# Save the merged dataframe to dirty.csv in the Data folder
merged_df.to_csv(os.path.join(directory, 'dirty.csv'), index=False)

# Remove old CSV files and their respective folders
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.csv') and file != 'dirty.csv':
            os.remove(os.path.join(root, file))
            
for root, dirs, files in os.walk(directory):
    for dir in dirs:
        shutil.rmtree(os.path.join(root, dir))

# Call bad_lines_cleaner.py as a subprocess
subprocess.run(['python', 'bad_lines_cleaner.py'])

# Fill in Year and Month columns after bad_lines_cleaner.py has run
fill_year_month_columns(os.path.join(directory, 'dirty.csv'))

# Remove rows with empty 'Amount' column in the merged dataframe
remove_empty_amount_rows(os.path.join(directory, 'dirty.csv'))

# Call desc_cleaner.py as a subprocess
subprocess.run(['python', 'desc_cleaner.py'])

# Call cat_cleaner.py as a subprocess
subprocess.run(['python', 'cat_cleaner.py'])
