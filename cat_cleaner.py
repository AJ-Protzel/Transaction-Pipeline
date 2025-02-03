"""
Author: Adrien Protzel

This script processes a CSV file to categorize transaction descriptions.
It uses a predefined category map to automatically categorize descriptions.
If a description does not match any category, a manual input window is displayed
to allow the user to categorize the transaction.

Modules used:
- pandas: For data manipulation and analysis.
- tkinter: For creating the GUI.
- os: For interacting with the operating system.

Functions:
- load_category_map(): Loads the category map from a file.
- check_description(row): Checks the description against the category map and
  displays a manual input window if no match is found.
"""

import pandas as pd
import tkinter as tk
import os

# Load the CSV file
csv_file_path = 'Data/dirty.csv'
df = pd.read_csv(csv_file_path)

# Ensure the 'Description' column is of type string and convert to lowercase
df['Description'] = df['Description'].astype(str).str.lower()

def load_category_map():
    """Load the category map file."""
    category_map_file_path = 'Configs/Maps/category_map.txt'
    category_map = {}
    with open(category_map_file_path, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                category_map[parts[0]] = parts[1]
    return category_map

def check_description(row):
    """Check descriptions based on the mapping."""
    category_map = load_category_map()
    description = row['Description']
    for keyword, mapped_category in category_map.items():
        if keyword in description:
            return mapped_category
    
    # If no mapping is found, show a popup window with the current description
    def cancel():
        root.destroy()
        raise SystemExit

    def skip():
        root.destroy()

    def add_mapping(category):
        with open('Configs/Maps/category_map.txt', 'a') as f:
            f.write(f"{description},{category.lower()}\n")
        root.destroy()

    root = tk.Tk()
    root.title("Manual Category Mapping")

    def center_window(window, width, height):
        """Center the window on the screen."""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    # Make the window smaller
    center_window(root, width=400, height=300)

    info_label = tk.Label(root, text=f"{row['Date']}: {row['Card']}: {row['Amount']}")
    info_label.pack(pady=5)

    description_label = tk.Label(root, text=f"Description: {description}", wraplength=380)
    description_label.pack(pady=10)

    category_buttons_frame1 = tk.Frame(root)
    category_buttons_frame1.pack(pady=5)

    category_buttons_frame2 = tk.Frame(root)
    category_buttons_frame2.pack(pady=5)

    categories1 = ["Grocery", "Dining", "Shopping", "Misc"]
    categories2 = ["Subscription", "Utility", "Travel", "Gas", "Transfer"]
    
    for category in categories1:
        button = tk.Button(category_buttons_frame1, text=category, command=lambda c=category: add_mapping(c))
        button.pack(side=tk.LEFT, padx=5)

    for category in categories2:
        button = tk.Button(category_buttons_frame2, text=category, command=lambda c=category: add_mapping(c))
        button.pack(side=tk.LEFT, padx=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    cancel_button = tk.Button(button_frame, text="Cancel", command=cancel)
    cancel_button.grid(row=0, column=0, padx=(0, 20))  # Add space between Cancel and Skip button

    skip_button = tk.Button(button_frame, text="Skip", command=skip)
    skip_button.grid(row=0, column=1)  # Add space between Skip and Enter button

    root.mainloop()

    return description

df['Category'] = df.apply(check_description, axis=1)

# Save the modified DataFrame back to a new CSV file
new_csv_file_path = 'Data/clean.csv'
df.to_csv(new_csv_file_path, index=False)

# Remove the original file after saving the new one
os.remove(csv_file_path)
