#!/usr/bin/env python3
"""
ModelTimeSeries JSON Editor

A tkinter application for editing ModelTimeSeries.json files.
Provides a notebook-based interface to edit individual fields within the JSON structure.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from pathlib import Path


class ModelTimeSeriesEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("ModelTimeSeries JSON Editor")
        self.root.geometry("1200x800")
        
        # Set window icon
        self.set_window_icon()
        
        # Data storage
        self.json_data = None
        self.json_file_path = None
        self.current_folder = None
        self.field_widgets = {}  # Store references to editable widgets
        
        # Create GUI
        self.create_widgets()
        
    
    def format_label_text(self, field_name):
        """Convert camelCase or snake_case field names to readable labels."""
        # Handle common abbreviations and special cases
        special_cases = {
            'fileName': 'File Name',
            'timeSeries': 'Time Series',
            'landCoverTypes': 'Land Cover Types',
            'potentialEvapotranspiration': 'Potential Evapotranspiration',
            'actualEvapotranspiration': 'Actual Evapotranspiration',
            'temperatureAndPrecipitation': 'Temperature and Precipitation',
            'rainAndSnow': 'Rain and Snow',
            'solarRadiation': 'Solar Radiation',
            'runoffToReach': 'Runoff to Reach',
            'waterInputs': 'Water Inputs',
            'waterOutputs': 'Water Outputs',
            'waterLevel': 'Water Level',
            'soilTemperature': 'Soil Temperature',
            'totalHRUs': 'Total HRUs',
            'totalLandCoverTypes': 'Total Land Cover Types',
            'totalBuckets': 'Total Buckets',
            'totalParticleSizeClasses': 'Total Particle Size Classes',
            'generatedFrom': 'Generated From'
        }
        
        # Check if it's a special case first
        if field_name in special_cases:
            return special_cases[field_name]
        
        # Convert camelCase to Title Case with spaces
        # Insert space before capital letters (except the first one)
        result = ""
        for i, char in enumerate(field_name):
            if i > 0 and char.isupper():
                result += " "
            result += char
        
        # Capitalize the first letter and return
        return result.capitalize()
    def set_window_icon(self):
        """Set the window icon to INCAMan.png if available."""
        try:
            # Try to find INCAMan.png in common locations
            icon_paths = [
                "INCAMan.png",
                os.path.join(os.path.dirname(__file__), "INCAMan.png"),
                os.path.join(os.path.dirname(__file__), "..", "INCAMan.png"),
                os.path.join(os.path.dirname(__file__), "..", "..", "INCAMan.png")
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    icon = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(False, icon)
                    break
        except Exception as e:
            # If icon loading fails, continue without icon
            pass
    
    def create_widgets(self):
        """Create the main GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(2, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # File and folder selection frame - side by side layout
        selection_frame = ttk.Frame(main_frame)
        selection_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        selection_frame.columnconfigure(0, weight=1)
        selection_frame.columnconfigure(1, weight=1)
        
        # File selection section (left side)
        file_frame = ttk.LabelFrame(selection_frame, text="Select JSON File", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly")
        file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(file_frame, text="Browse...", command=self.select_json_file).grid(
            row=0, column=1, padx=(5, 0)
        )
        
        # Folder selection section (right side)
        folder_frame = ttk.LabelFrame(selection_frame, text="Specify New Folder (Optional)", padding="10")
        folder_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_path_var = tk.StringVar()
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path_var, state="readonly")
        folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        ttk.Button(folder_frame, text="Browse...", command=self.select_folder).grid(
            row=0, column=1, padx=(5, 0)
        )
        
        # Editor notebook - initially hidden
        self.editor_frame = ttk.Frame(main_frame)
        self.editor_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.editor_frame.columnconfigure(0, weight=1)
        self.editor_frame.rowconfigure(0, weight=1)
        
        self.notebook = ttk.Notebook(self.editor_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status section
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select a JSON file to begin editing")
        ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN, padding="5").grid(
            row=0, column=0, sticky=(tk.W, tk.E)
        )
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        self.apply_changes_button = ttk.Button(buttons_frame, text="Apply Changes", command=self.apply_changes, state="disabled")
        self.apply_changes_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.save_button = ttk.Button(buttons_frame, text="Save JSON", command=self.save_json, state="disabled")
        self.save_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.save_as_button = ttk.Button(buttons_frame, text="Save As...", command=self.save_as_json, state="disabled")
        self.save_as_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.update_folder_button = ttk.Button(buttons_frame, text="Update Folder", command=self.update_folder, state="disabled")
        self.update_folder_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(buttons_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # Configure grid weights for resizing
        main_frame.rowconfigure(1, weight=1)
        
        # Initially hide the editor
        self.editor_frame.grid_remove()
    
    def select_json_file(self):
        """Open file dialog to select a JSON file."""
        file_path = filedialog.askopenfilename(
            title="Select ModelTimeSeries JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.json_data = json.load(f)
                
                self.json_file_path = file_path
                self.file_path_var.set(file_path)
                self.status_var.set(f"Loaded JSON file: {os.path.basename(file_path)}")
                
                # Enable buttons
                self.save_button.config(state="normal")
                self.save_as_button.config(state="normal")
                self.update_folder_button.config(state="normal")
                self.apply_changes_button.config(state="normal")
                
                # Show editor and create tabs
                self.editor_frame.grid()
                self.create_editor_tabs()
                
                # Try to extract current folder from JSON
                self.extract_current_folder()
                
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON file:\n{e}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file:\n{e}")
    
    def extract_current_folder(self):
        """Extract the current folder from the JSON data if it exists."""
        try:
            if self.json_data and 'catchment' in self.json_data:
                catchment = self.json_data['catchment']
                if 'timeSeries' in catchment and 'folder' in catchment['timeSeries']:
                    folder_from_json = catchment['timeSeries']['folder']
                    
                    # Update the current_folder and folder_path_var if folder exists
                    if folder_from_json and os.path.exists(folder_from_json):
                        self.current_folder = folder_from_json
                        self.folder_path_var.set(folder_from_json)
                        self.status_var.set(f"Loaded file. Using folder from JSON: {folder_from_json}")
                    else:
                        self.status_var.set(f"Loaded file. Folder in JSON '{folder_from_json}' does not exist.")
                else:
                    self.status_var.set("Loaded file. No folder specified in JSON.")
        except Exception as e:
            pass
    
    def select_folder(self):
        """Open dialog to select a folder for updating the JSON."""
        folder_path = filedialog.askdirectory(
            title="Select folder containing time series files"
        )
        
        if folder_path:
            self.folder_path_var.set(folder_path)
            self.current_folder = folder_path
            self.status_var.set(f"Selected folder: {os.path.basename(folder_path)}")
            
            # Automatically update the JSON folder if JSON data is loaded
            if self.json_data:
                self.update_folder_in_json(folder_path)
    
    def create_editor_tabs(self):
        """Create notebook tabs for editing the JSON structure."""
        # Clear existing tabs
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        
        self.field_widgets = {}
        
        if not self.json_data:
            return
        
        # Create catchment overview tab
        self.create_catchment_tab()
        
        # Create HRU tabs
        if 'catchment' in self.json_data and 'HRUs' in self.json_data['catchment']:
            for i, hru in enumerate(self.json_data['catchment']['HRUs']):
                self.create_hru_tab(i, hru)
    
    def create_catchment_tab(self):
        """Create the catchment overview tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Catchment")
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Catchment information
        if 'catchment' in self.json_data:
            catchment = self.json_data['catchment']
            
            # Basic catchment info
            ttk.Label(scrollable_frame, text="Catchment Information", font=("Arial", 14, "bold")).grid(
                row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
            )
            
            row = 1
            
            # Name
            ttk.Label(scrollable_frame, text=f"{self.format_label_text('name')}:").grid(row=row, column=0, sticky=tk.W, padx=(20, 5))
            name_var = tk.StringVar(value=catchment.get('name', ''))
            name_entry = ttk.Entry(scrollable_frame, textvariable=name_var, width=40)
            name_entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
            self.field_widgets[('catchment', 'name')] = name_var
            row += 1
            
            # Abbreviation
            ttk.Label(scrollable_frame, text=f"{self.format_label_text('abbreviation')}:").grid(row=row, column=0, sticky=tk.W, padx=(20, 5))
            abbrev_var = tk.StringVar(value=catchment.get('abbreviation', ''))
            abbrev_entry = ttk.Entry(scrollable_frame, textvariable=abbrev_var, width=10)
            abbrev_entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
            self.field_widgets[('catchment', 'abbreviation')] = abbrev_var
            row += 1
            
            # Folder (always create this field)
            ttk.Label(scrollable_frame, text=f"{self.format_label_text('folder')}:").grid(row=row, column=0, sticky=tk.W, padx=(20, 5))
            
            # Ensure timeSeries structure exists
            if 'timeSeries' not in catchment:
                catchment['timeSeries'] = {}
            
            # Get current folder value or empty string
            current_folder = ""
            if 'timeSeries' in catchment and 'folder' in catchment['timeSeries']:
                current_folder = catchment['timeSeries']['folder']
            
            folder_var = tk.StringVar(value=current_folder)
            folder_entry = ttk.Entry(scrollable_frame, textvariable=folder_var, width=40)
            folder_entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
            self.field_widgets[('catchment', 'timeSeries', 'folder')] = folder_var
            row += 1
            
            # Summary information
            if 'summary' in self.json_data:
                ttk.Label(scrollable_frame, text="Summary", font=("Arial", 14, "bold")).grid(
                    row=row, column=0, columnspan=2, sticky=tk.W, pady=(20, 10)
                )
                row += 1
                
                summary = self.json_data['summary']
                for key, value in summary.items():
                    if isinstance(value, (str, int, float)):
                        ttk.Label(scrollable_frame, text=f"{self.format_label_text(key)}:").grid(row=row, column=0, sticky=tk.W, padx=(20, 5))
                        if isinstance(value, (int, float)):
                            var = tk.IntVar(value=value) if isinstance(value, int) else tk.DoubleVar(value=value)
                        else:
                            var = tk.StringVar(value=str(value))
                        entry = ttk.Entry(scrollable_frame, textvariable=var, width=20)
                        entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
                        self.field_widgets[('summary', key)] = var
                        row += 1
    
    def create_hru_tab(self, hru_index, hru_data):
        """Create a tab for editing an HRU."""
        hru_name = hru_data.get('name', f'HRU {hru_index + 1}')
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=hru_name)
        
        # Create scrollable frame
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # HRU basic information
        ttk.Label(scrollable_frame, text=f"HRU: {hru_name}", font=("Arial", 14, "bold")).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10)
        )
        
        row = 1
        
        # Name
        ttk.Label(scrollable_frame, text=f"{self.format_label_text('name')}:").grid(row=row, column=0, sticky=tk.W, padx=(0, 5))
        name_var = tk.StringVar(value=hru_data.get('name', ''))
        name_entry = ttk.Entry(scrollable_frame, textvariable=name_var, width=30)
        name_entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
        self.field_widgets[('catchment', 'HRUs', hru_index, 'name')] = name_var
        row += 1
        
        # Abbreviation
        ttk.Label(scrollable_frame, text=f"{self.format_label_text('abbreviation')}:").grid(row=row, column=0, sticky=tk.W, padx=(0, 5))
        abbrev_var = tk.StringVar(value=hru_data.get('abbreviation', ''))
        abbrev_entry = ttk.Entry(scrollable_frame, textvariable=abbrev_var, width=10)
        abbrev_entry.grid(row=row, column=1, sticky=tk.W, padx=(0, 20))
        self.field_widgets[('catchment', 'HRUs', hru_index, 'abbreviation')] = abbrev_var
        row += 1
        
        # Time series data
        if 'timeSeries' in hru_data:
            self.create_time_series_section(scrollable_frame, row, hru_data['timeSeries'], 
                                          ('catchment', 'HRUs', hru_index, 'timeSeries'))
    
    def create_time_series_section(self, parent, start_row, time_series_data, base_path):
        """Create editable fields for time series data."""
        row = start_row
        
        ttk.Label(parent, text=f"{self.format_label_text('timeSeries')}", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=3, sticky=tk.W, pady=(20, 10)
        )
        row += 1
        
        # Headers
        ttk.Label(parent, text="Type", font=("Arial", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=(20, 5))
        ttk.Label(parent, text=f"{self.format_label_text('fileName')}", font=("Arial", 10, "bold")).grid(row=row, column=1, sticky=tk.W, padx=(5, 5))
        ttk.Label(parent, text="Pick", font=("Arial", 10, "bold")).grid(row=row, column=2, sticky=tk.W, padx=(5, 5))
        ttk.Label(parent, text=f"{self.format_label_text('mandatory')}", font=("Arial", 10, "bold")).grid(row=row, column=3, sticky=tk.W, padx=(5, 5))
        ttk.Label(parent, text=f"{self.format_label_text('generated')}", font=("Arial", 10, "bold")).grid(row=row, column=4, sticky=tk.W, padx=(5, 5))
        row += 1
        
        # Process time series entries
        row = self.process_time_series_recursive(parent, row, time_series_data, base_path, indent_level=1)
        
        return row
    
    def process_time_series_recursive(self, parent, row, data, base_path, indent_level=0):
        """Recursively process time series data and create editable fields."""
        if isinstance(data, dict):
            for key, value in data.items():
                if key in ['landCoverTypes', 'buckets'] and isinstance(value, list):
                    # Handle arrays of land cover types or buckets
                    for i, item in enumerate(value):
                        if isinstance(item, dict) and 'name' in item:
                            item_name = item.get('name', f'Item {i+1}')
                            # Create a separator for this item
                            ttk.Separator(parent, orient='horizontal').grid(
                                row=row, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 5)
                            )
                            row += 1
                            
                            ttk.Label(parent, text=f"{key[:-1]}: {item_name}", 
                                     font=("Arial", 11, "bold")).grid(
                                row=row, column=0, columnspan=4, sticky=tk.W, 
                                padx=(20 * indent_level, 5), pady=(0, 5)
                            )
                            row += 1
                            
                            if 'timeSeries' in item:
                                row = self.process_time_series_recursive(
                                    parent, row, item['timeSeries'], 
                                    base_path + (key, i, 'timeSeries'), indent_level + 1
                                )
                elif isinstance(value, dict) and 'fileName' in value:
                    # This is a time series entry
                    row = self.create_time_series_entry(parent, row, key, value, base_path + (key,), indent_level)
                elif isinstance(value, dict) and key not in ['landCoverTypes', 'buckets']:
                    # Recursive call for nested dictionaries
                    row = self.process_time_series_recursive(
                        parent, row, value, base_path + (key,), indent_level
                    )
        
        return row
    
    def create_time_series_entry(self, parent, row, ts_type, ts_data, full_path, indent_level):
        """Create editable fields for a single time series entry."""
        # Type name (indented based on level) - use formatted label
        formatted_type = self.format_label_text(ts_type)
        type_label = ttk.Label(parent, text=formatted_type)
        type_label.grid(row=row, column=0, sticky=tk.W, padx=(20 * indent_level, 5))
        
        # File name
        filename_var = tk.StringVar(value=ts_data.get('fileName', ''))
        filename_entry = ttk.Entry(parent, textvariable=filename_var, width=35)
        filename_entry.grid(row=row, column=1, sticky=tk.W, padx=(5, 5))
        self.field_widgets[full_path + ('fileName',)] = filename_var
        
        # Pick button
        pick_button = ttk.Button(parent, text="Pick", width=6, 
                               command=lambda: self.pick_csv_file(filename_var))
        pick_button.grid(row=row, column=2, padx=(0, 5))
        
        # Mandatory checkbox
        mandatory_var = tk.BooleanVar(value=ts_data.get('mandatory', False))
        mandatory_check = ttk.Checkbutton(parent, variable=mandatory_var)
        mandatory_check.grid(row=row, column=3, padx=(5, 5))
        self.field_widgets[full_path + ('mandatory',)] = mandatory_var
        
        # Generated checkbox
        generated_var = tk.BooleanVar(value=ts_data.get('generated', True))
        generated_check = ttk.Checkbutton(parent, variable=generated_var)
        generated_check.grid(row=row, column=4, padx=(5, 5))
        self.field_widgets[full_path + ('generated',)] = generated_var
        
        return row + 1
    
    def pick_csv_file(self, filename_var):
        """Open a dialog to pick a CSV file from the specified folder."""
        # Determine which folder to use
        folder_to_use = None
        
        if self.current_folder:
            # User has explicitly selected a folder
            folder_to_use = self.current_folder
        elif self.json_data and 'catchment' in self.json_data:
            # Try to use folder from JSON
            catchment = self.json_data['catchment']
            if 'timeSeries' in catchment and 'folder' in catchment['timeSeries']:
                json_folder = catchment['timeSeries']['folder']
                if json_folder and os.path.exists(json_folder):
                    folder_to_use = json_folder
                    # Update current_folder for future use
                    self.current_folder = json_folder
                    self.folder_path_var.set(json_folder)
        
        if not folder_to_use:
            messagebox.showwarning("No Folder Available", 
                                 "Please select a folder using 'Specify New Folder', or ensure the JSON file contains a valid folder path.")
            return
        
        try:
            # Get all CSV files in the folder
            folder_path = Path(folder_to_use)
            csv_files = [f.stem for f in folder_path.glob("*.csv")]  # Use .stem to get filename without extension
            
            if not csv_files:
                messagebox.showinfo("No CSV Files", 
                                  f"No CSV files found in folder:\n{folder_to_use}")
                return
            
            # Sort the files alphabetically
            csv_files.sort()
            
            # Create a selection dialog
            self.show_file_selection_dialog(csv_files, filename_var)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not read folder contents:\n{e}")
    
    def show_file_selection_dialog(self, csv_files, filename_var):
        """Show a dialog with a list of CSV files to choose from."""
        # Create a new dialog window
        dialog = tk.Toplevel(self.root)
        dialog.title("Select CSV File")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Set icon for dialog
        try:
            dialog.iconphoto(False, self.root.iconphoto_get())
        except:
            pass
        
        # Main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Label
        ttk.Label(main_frame, text="Select a CSV file:", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create listbox and scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Populate listbox
        for csv_file in csv_files:
            listbox.insert(tk.END, csv_file)
        
        # Variables to store result
        selected_file = [None]
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_file[0] = csv_files[selection[0]]
                dialog.destroy()
        
        def on_double_click(event):
            on_select()
        
        def on_cancel():
            dialog.destroy()
        
        # Bind double-click to select
        listbox.bind('<Double-Button-1>', on_double_click)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X)
        
        ttk.Button(buttons_frame, text="Select", command=on_select).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT)
        
        # Center the dialog on parent window
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Wait for dialog to close
        self.root.wait_window(dialog)
        
        # Update the filename if a file was selected
        if selected_file[0]:
            filename_var.set(selected_file[0])
            self.status_var.set(f"Selected file: {selected_file[0]}")
    
    def apply_changes(self):
        """Apply all changes from widgets to the JSON data without saving to file."""
        if not self.json_data:
            messagebox.showwarning("Warning", "No JSON data loaded.")
            return
        
        try:
            self.update_json_from_widgets()
            self.status_var.set("Changes applied to JSON data in memory")
            messagebox.showinfo("Success", "All changes have been applied to the JSON data.\nUse 'Save JSON' to write changes to file.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not apply changes:\n{e}")
    
    def update_folder_in_json(self, folder_path):
        """Update the folder in the JSON data structure and widget."""
        try:
            # Ensure the structure exists
            if 'catchment' not in self.json_data:
                self.json_data['catchment'] = {}
            
            if 'timeSeries' not in self.json_data['catchment']:
                self.json_data['catchment']['timeSeries'] = {}
            
            # Update the JSON data directly
            self.json_data['catchment']['timeSeries']['folder'] = folder_path
            
            # Update the widget if it exists
            folder_widget_key = ('catchment', 'timeSeries', 'folder')
            if folder_widget_key in self.field_widgets:
                self.field_widgets[folder_widget_key].set(folder_path)
            
            self.status_var.set(f"Folder automatically updated to: {folder_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not update folder in JSON:\n{e}")
    
    def update_folder(self):
        """Update the folder in the JSON data."""
        if not self.json_data:
            messagebox.showwarning("Warning", "Please load a JSON file first.")
            return
            
        if not self.current_folder:
            messagebox.showwarning("Warning", "Please select a folder first.")
            return
        
        # Update the folder in the JSON structure
        try:
            self.update_folder_in_json(self.current_folder)
            messagebox.showinfo("Success", f"Updated folder to: {self.current_folder}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not update folder:\n{e}")
    
    def save_json(self):
        """Save the current JSON data to the original file."""
        if not self.json_data or not self.json_file_path:
            messagebox.showwarning("Warning", "No JSON data to save.")
            return
        
        # Update JSON data from widgets
        self.update_json_from_widgets()
        
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.json_data, f, indent=2, ensure_ascii=False)
            
            self.status_var.set(f"Saved: {os.path.basename(self.json_file_path)}")
            messagebox.showinfo("Success", f"JSON file saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not save JSON file:\n{e}")
    
    def save_as_json(self):
        """Save the JSON data to a new file."""
        if not self.json_data:
            messagebox.showwarning("Warning", "No JSON data to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save JSON file as...",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            # Update JSON data from widgets
            self.update_json_from_widgets()
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.json_data, f, indent=2, ensure_ascii=False)
                
                self.json_file_path = file_path
                self.file_path_var.set(file_path)
                self.status_var.set(f"Saved as: {os.path.basename(file_path)}")
                messagebox.showinfo("Success", f"JSON file saved as:\n{file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not save JSON file:\n{e}")
    
    def update_json_from_widgets(self):
        """Update the JSON data structure from the widget values."""
        for path, widget_var in self.field_widgets.items():
            try:
                # Navigate to the correct location in the JSON structure
                current = self.json_data
                for i, key in enumerate(path[:-1]):
                    if isinstance(key, int):
                        # Handle array index
                        if isinstance(current, list) and key < len(current):
                            current = current[key]
                        else:
                            break
                    else:
                        # Handle dictionary key
                        if key not in current:
                            current[key] = {}
                        current = current[key]
                else:
                    # Set the value (only if we successfully navigated the full path)
                    final_key = path[-1]
                    value = widget_var.get()
                    
                    # Handle the case where current might be a list and we need to ensure structure exists
                    if isinstance(current, dict):
                        current[final_key] = value
                
            except Exception as e:
                # Silently continue on errors - could add logging here if needed
                pass


def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = ModelTimeSeriesEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
