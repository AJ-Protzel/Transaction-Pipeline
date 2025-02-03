"""
Author: Adrien Protzel

This script creates a GUI application using Tkinter to organize files based on user selections.
Users can drag and drop files into the application, which then copies the files to appropriate folders
based on the selected type, bank, and card.

Modules used:
- tkinter: For creating the GUI.
- tkinterdnd2: For drag-and-drop functionality in Tkinter.
- os: For interacting with the operating system.
- shutil: For file operations.
- json: For reading configuration files.

Functions:
- drop(event): Handles file drop events and copies files to appropriate folders.
- copy_file(file): Copies a file to the appropriate folder based on user selections.
- update_bank_options(*args): Updates bank options based on the selected type.
- update_card_options(*args): Updates card options based on the selected type and bank.
- cancel(): Closes the application.
- create_dropdown(label_text, variable, options, parent, default_value): Creates a dropdown menu with a label.
- center_window(window, width, height): Centers the window on the screen with specified width and height.
"""

import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import shutil
import json

# Load configuration from Configs/config.json
config_path = os.path.join(os.path.dirname(__file__), 'Configs', 'config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

# Extract unique options for type, bank, and card
types = sorted(set(item['type'] for item in config))
banks = {}
cards = {}

# Populate banks and cards dictionaries based on the config data
for item in config:
    if item['type'] not in banks:
        banks[item['type']] = set()
    banks[item['type']].add(item['bank'])
    
    if (item['type'], item['bank']) not in cards:
        cards[(item['type'], item['bank'])] = set()
    cards[(item['type'], item['bank'])].add(item['card'])

def drop(event):
    """
    Handle file drop event. Copy dropped files to the appropriate folder based on user selections.
    
    Args:
        event: The drop event containing the file paths.
    """
    files = root.tk.splitlist(event.data)
    for file in files:
        copy_file(file)
    
    # Clear the fields after input of files
    type_var.set("")
    bank_var.set("")
    card_var.set("")
    
    # Ask the user if they want to continue or not
    if not messagebox.askyesno("Continue", "Do you want to continue?"):
        root.destroy()

def copy_file(file):
    """
    Copy the file to the appropriate folder based on user selections.
    
    Args:
        file (str): The path of the file to be copied.
    """
    type_selection = type_var.get()
    bank_selection = bank_var.get()
    card_selection = card_var.get()
    
    # Construct the folder path relative to the current program location
    base_path = os.path.join(os.path.dirname(__file__), "Data")
    folder_path = os.path.join(base_path, f"{type_selection}_{bank_selection}_{card_selection}")
    
    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    # Copy the file to the folder
    shutil.copy(file, folder_path)

def update_bank_options(*args):
    """
    Update bank options based on the selected type.
    """
    type_selection = type_var.get()
    bank_options = sorted(banks.get(type_selection, []))
    
    bank_var.set("")
    bank_menu['menu'].delete(0, 'end')
    
    for option in bank_options:
        bank_menu['menu'].add_command(label=option, command=tk._setit(bank_var, option))
    
    update_card_options()

def update_card_options(*args):
    """
    Update card options based on the selected type and bank.
    """
    type_selection = type_var.get()
    bank_selection = bank_var.get()
    card_options = sorted(cards.get((type_selection, bank_selection), []))
    
    card_var.set("")
    card_menu['menu'].delete(0, 'end')
    
    for option in card_options:
        card_menu['menu'].add_command(label=option, command=tk._setit(card_var, option))

def cancel():
    """
    Handle cancel button click. Close the application.
    """
    root.destroy()

def create_dropdown(label_text, variable, options, parent, default_value=""):
    """
    Create a dropdown menu with a label.
    
    Args:
        label_text (str): The text for the label.
        variable (tk.StringVar): The variable associated with the dropdown.
        options (list): The list of options for the dropdown.
        parent (tk.Widget): The parent widget.
        default_value (str): The default value for the dropdown.
    
    Returns:
        tk.OptionMenu: The created dropdown menu.
    """
    frame = tk.Frame(parent)
    frame.pack(anchor='center', pady=5, fill='x')
    label = tk.Label(frame, text=label_text)
    label.pack(side='left', padx=5)
    variable.set(default_value if options else "")
    menu = tk.OptionMenu(frame, variable, *(options if options else [default_value]))
    menu.pack(side='left', padx=5)
    return menu

def center_window(window, width, height):
    """
    Center the window on the screen with specified width and height.
    
    Args:
        window (tk.Tk): The window to be centered.
        width (int): The width of the window.
        height (int): The height of the window.
    """
    window.update_idletasks()
    x = (window.winfo_screenwidth() // 2) - (width // 2)
    y = (window.winfo_screenheight() // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

# Initialize main window
root = TkinterDnD.Tk()
root.title("File Organizer")

# Center the window with new dimensions
center_window(root, width=250, height=400)

# Type dropdown
type_var = tk.StringVar()
type_menu = create_dropdown("Type:", type_var, types, root)

# Bank dropdown
bank_var = tk.StringVar()
bank_menu = create_dropdown("Bank:", bank_var, [], root)

# Card dropdown
card_var = tk.StringVar()
card_menu = create_dropdown("Card:", card_var, [], root)

# Bind update functions to type and bank dropdown changes
type_var.trace('w', update_bank_options)
bank_var.trace('w', update_card_options)

# Drag and drop area
drop_area = tk.Label(root, text="Drag and drop files here", width=60, height=15, bg="lightgray")
drop_area.pack(pady=20)
drop_area.drop_target_register(DND_FILES)
drop_area.dnd_bind('<<Drop>>', drop)

# Cancel button
cancel_button = tk.Button(root, text="Cancel", command=cancel)
cancel_button.pack(pady=10)

# Run the main loop
root.mainloop()
