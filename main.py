import os  # Importing the os module for interacting with the operating system
import sys  # Importing the sys module for system-specific parameters and functions
import shutil  # Importing the shutil module for file operations
from cleaner import load_config, load_mappings, clean_csv, transform_csv  # Importing functions from cleaner.py

# Static paths
CLEAN_FOLDER_PATH = os.path.join('Data', 'Clean')  # Path to the folder where cleaned files will be stored
BAD_LINES_LOG_PATH = os.path.join(CLEAN_FOLDER_PATH, 'bad_lines.txt')  # Path to the log file for bad lines
MAPS_FOLDER_PATH = os.path.join('Configs', 'Maps')  # Path to the folder containing mapping files
DESCRIPTION_MAP_PATH = os.path.join(MAPS_FOLDER_PATH, 'Description_map.txt')  # Path to the description mapping file
CATEGORY_MAP_PATH = os.path.join(MAPS_FOLDER_PATH, 'Category_map.txt')  # Path to the category mapping file

def process_csv_files(config_path):
    """Process all CSV files in the specified folder."""
    # Load the configuration from the JSON file
    config = load_config(config_path)

    # Load the description and category mappings
    description_mappings = load_mappings(DESCRIPTION_MAP_PATH)
    category_mappings = load_mappings(CATEGORY_MAP_PATH)

    print(f"Processing: {config['FOLDER_PATH']}")

    # Iterate over all files in the specified folder
    for filename in os.listdir(config['FOLDER_PATH']):
        if filename.lower().endswith('.csv'):  # Check if the file is a CSV file
            file = os.path.join(config['FOLDER_PATH'], filename)

            # Clean and transform the CSV file
            clean_csv(file, config, BAD_LINES_LOG_PATH)
            transform_csv(file, config, description_mappings, category_mappings, DESCRIPTION_MAP_PATH, CATEGORY_MAP_PATH)

            # Generate a new filename and move the processed file to the clean folder
            new_filename = f"{config['ACCOUNT']}_{config['BANK']}_{config['CARD']}_{filename}"
            new_file_path = os.path.join(CLEAN_FOLDER_PATH, new_filename)
            shutil.move(file, new_file_path)


def run_cleaner(config_path):
    """Run the cleaner program with the specified configuration file."""
    process_csv_files(config_path)

if __name__ == "__main__":
    # Define the folder containing configuration files
    configs_folder = 'Configs'

    # Check if the configs folder exists
    if not os.path.exists(configs_folder):
        sys.exit(1)  # Exit the program if the folder does not exist

    # List all JSON configuration files in the configs folder
    configs = [os.path.join(configs_folder, config) for config in os.listdir(configs_folder) if config.endswith('.json')]

    # Exit if no configuration files are found
    if not configs:
        sys.exit(1)

    # Run the cleaner for each configuration file
    for config in configs:
        run_cleaner(config)
