"""
Author: Adrien Protzel

This script creates a GUI application using Tkinter to manually clean up bad lines from a file.
It reads bad lines from a specified file, displays them in a pop-up window, and allows the user
to manually enter the correct information. The corrected data is then written to a CSV file.

Modules used:
- tkinter: For creating the GUI.
- tkinterdnd2: For drag-and-drop functionality in Tkinter.
- pathlib: For handling file paths.
- csv: For reading and writing CSV files.
- os: For interacting with the operating system.
"""

import tkinter as tk
from tkinterdnd2 import TkinterDnD
from pathlib import Path
import csv
import os

# Define the desired column order
HEADER = ["Year", "Month", "Date", "Description", "Category", "Amount", "Type", "Bank", "Card"]

def read_bad_lines(file_path):
    """Read bad lines from the specified file."""
    with open(file_path, 'r') as file:
        return file.readlines()

def center_window(window, width, height):
    """Center the window on the screen."""
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

def parse_filepath(filepath):
    """Parse the filepath to extract Type, Bank, and Card."""
    folder_name = Path(filepath).parent.name
    type_, bank, card = folder_name.split('_')
    return type_, bank, card

def create_popup(root, line, next_line_callback, cancel_callback):
    """Create a pop-up window to display the bad line."""
    popup = tk.Toplevel(root)
    popup.title("Manual Entry for Bad Lines")
    center_window(popup, width=800, height=600)  # Center the window on the screen

    # Parse the line into two lines with the second line starting with '['
    if ': [' in line:
        part1, part2 = line.split(': [', 1)
        part2 = '[' + part2  # Add the '[' back to the second part
        line_label1 = tk.Label(popup, text=f"Bad Line: {part1.strip()}")
        line_label2 = tk.Label(popup, text=part2.strip())
        line_label1.pack()
        line_label2.pack()
    else:
        line_label = tk.Label(popup, text=f"Bad Line: {line.strip()}")
        line_label.pack()

    # Prefill the Type, Bank, and Card fields based on the filepath
    filepath = part1.split(':')[0]
    type_, bank, card = parse_filepath(filepath)

    # List the desired columns vertically with a colon after each, aligned right, and add input fields
    columns_frame = tk.Frame(popup)
    columns_frame.pack(pady=10)
    entries = {}
    for col in HEADER:
        if col in ["Year", "Month", "Category"]:
            continue  # Skip these columns
        row_frame = tk.Frame(columns_frame)
        row_frame.pack(fill='x', pady=2)
        col_label = tk.Label(row_frame, text=f"{col if col != 'Description' else 'Description Keyword'}:", anchor='e', width=20)
        col_label.pack(side='left')
        if col == "Date":
            date_frame = tk.Frame(row_frame)
            date_frame.pack(side='left', fill='x', expand=True)
            month_entry = tk.Entry(date_frame, width=2)
            month_entry.pack(side='left')
            tk.Label(date_frame, text="/").pack(side='left')
            day_entry = tk.Entry(date_frame, width=2)
            day_entry.pack(side='left')
            tk.Label(date_frame, text="/").pack(side='left')
            year_var = tk.StringVar(date_frame)
            year_var.set("2025")  # Set default value
            year_options = [str(year) for year in range(2025, 1999, -1)]
            year_menu = tk.OptionMenu(date_frame, year_var, *year_options)
            year_menu.pack(side='left')
            entries["Date"] = (month_entry, day_entry, year_var)
        elif col == "Amount":
            amount_frame = tk.Frame(row_frame)
            amount_frame.pack(side='left', fill='x', expand=True)
            amount_entry = tk.Entry(amount_frame, width=10)
            amount_entry.pack(side='left')
            tk.Label(amount_frame, text=".").pack(side='left')
            cents_entry = tk.Entry(amount_frame, width=2)
            cents_entry.pack(side='left')
            entries["Amount"] = (amount_entry, cents_entry)
        else:
            entry = tk.Entry(row_frame, width=50)  # Make the input fields longer
            entry.pack(side='left', fill='x', expand=True)
            if col == "Type":
                entry.insert(0, type_)
            elif col == "Bank":
                entry.insert(0, bank)
            elif col == "Card":
                entry.insert(0, card)
            entries[col] = entry

    def clean_date_input(entry, length):
        """Clean and format date input fields."""
        value = entry.get().zfill(length)
        entry.delete(0, tk.END)
        entry.insert(0, value)
        return value

    def on_enter():
        """Collect input data and write it to a CSV file."""
        # Clean and merge date inputs
        month, day, year_var = entries["Date"]
        month = clean_date_input(month, 2)
        day = clean_date_input(day, 2)
        year = year_var.get()
        date = f"{month}/{day}/{year}"

        # Collect the inputted fields
        input_data = []
        for col in HEADER:
            if col == "Date":
                input_data.append(date)
            elif col == "Amount":
                amount, cents = entries["Amount"]
                amount = amount.get()
                cents = cents.get().zfill(2)
                input_data.append(f"{amount}.{cents}")
            elif col in entries:
                input_data.append(entries[col].get())
            else:
                input_data.append("")

        # Write the input data to dirty.csv as a comma-separated list
        with open('Data/dirty.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(input_data)

        popup.destroy()
        next_line_callback()

    def on_cancel():
        """Cancel the current operation and close the pop-up window."""
        popup.destroy()
        cancel_callback()

    button_frame = tk.Frame(popup)
    button_frame.pack(pady=20)

    enter_button = tk.Button(button_frame, text="Enter", command=on_enter)
    enter_button.pack(side='left', padx=10)

    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel)
    cancel_button.pack(side='left', padx=10)

# Initialize main window
root = TkinterDnD.Tk()
root.withdraw()  # Hide the root window
root.title("Bad Lines Cleaner")
center_window(root, width=400, height=300)  # Center the window on the screen

# Read bad lines and create pop-up windows
bad_lines_path = Path('Data/bad_lines.txt')
bad_lines = read_bad_lines(bad_lines_path)

def show_next_line(index=0):
    """Display the next bad line in a pop-up window."""
    if index < len(bad_lines):
        create_popup(root, bad_lines[index], lambda: show_next_line(index + 1), lambda: root.destroy())
    else:
        remove_bad_lines_file()
        root.destroy()

def remove_bad_lines_file():
    """Remove the bad lines file after processing."""
    if bad_lines_path.exists():
        os.remove(bad_lines_path)

show_next_line()
root.mainloop()
