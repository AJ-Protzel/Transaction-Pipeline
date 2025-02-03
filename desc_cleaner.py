"""
Author: Adrien Protzel

This script processes a CSV file to replace transaction descriptions based on a predefined mapping.
If a description does not match any keyphrase, a manual input window is displayed to allow the user
to enter the correct description.

Modules used:
- pandas: For data manipulation and analysis.
- tkinter: For creating the GUI.

Functions:
- load_description_map(): Loads the description map from a file.
- replace_description(row): Replaces descriptions based on the mapping and displays a manual input window if no match is found.
"""

import pandas as pd
import tkinter as tk

# Load the CSV file
csv_file_path = 'Data/dirty.csv'
df = pd.read_csv(csv_file_path)

# Ensure the 'Description' column is of type string and convert to lowercase
df['Description'] = df['Description'].astype(str).str.lower()

def load_description_map():
    """Load the description map file."""
    description_map_file_path = 'Configs/Maps/description_map.txt'
    description_map = {}
    with open(description_map_file_path, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                description_map[parts[0]] = parts[1]
    return description_map

def replace_description(row):
    """Replace descriptions based on the mapping."""
    description_map = load_description_map()
    description = row['Description']
    for keyphrase, mapped_description in description_map.items():
        if description == mapped_description:
            return description  # Skip if it matches the true description exactly
        if keyphrase in description:
            return mapped_description
    
    # If no mapping is found, show a popup window with the current description
    def cancel():
        root.destroy()
        raise SystemExit

    def skip():
        root.destroy()

    def enter(event=None):
        keyword = keyword_entry.get().lower()
        true_description = true_description_entry.get().lower()
        
        # Append the new mapping to the description_map.txt file
        with open('Configs/Maps/description_map.txt', 'a') as f:
            f.write(f"{keyword},{true_description}\n")
        
        root.destroy()

    root = tk.Tk()
    root.title("Manual Description Mapping")

    def center_window(window, width, height):
        """Center the window on the screen."""
        window.update_idletasks()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    # Make the window wider to show the whole description
    center_window(root, width=500, height=250)

    info_label = tk.Label(root, text=f"{row['Date']}: {row['Card']}: {row['Amount']}")
    info_label.pack(pady=5)

    description_label = tk.Label(root, text=description, wraplength=480)
    description_label.pack(pady=10)

    frame = tk.Frame(root)
    frame.pack(pady=10)

    instruction_label1 = tk.Label(frame, text="Enter Description Keyword:", anchor='e', justify='right')
    instruction_label1.grid(row=0, column=0, sticky='e')
    keyword_entry = tk.Entry(frame)
    keyword_entry.grid(row=0, column=1)
    keyword_entry.insert(0, description)  # Prefill with the current description

    instruction_label2 = tk.Label(frame, text="Enter True Description:", anchor='e', justify='right')
    instruction_label2.grid(row=1, column=0, sticky='e')
    true_description_entry = tk.Entry(frame)
    true_description_entry.grid(row=1, column=1)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)

    cancel_button = tk.Button(button_frame, text="Cancel", command=cancel)
    cancel_button.grid(row=0, column=0, padx=(0, 20))  # Add space between Cancel and Skip button

    skip_button = tk.Button(button_frame, text="Skip", command=skip)
    skip_button.grid(row=0, column=1, padx=(0, 20))  # Add space between Skip and Enter button

    enter_button = tk.Button(button_frame, text="Enter", command=enter)
    enter_button.grid(row=0, column=2)

    root.bind('<Return>', enter)  # Bind the Enter key to the enter function

    root.mainloop()

    return description

df['Description'] = df.apply(replace_description, axis=1)

# Save the modified DataFrame back to the CSV file
df.to_csv(csv_file_path, index=False)
