import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import traceback
from pathlib import Path

class CatchmentJSONEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Catchment JSON Editor")
        self.root.geometry("1400x900")
        
        # Data storage
        self.data = {}
        self.file_path = None
        self.widgets = {}  # Store widget references for data binding
        self.widget_paths = {}  # Store the JSON path for each widget
        
        # Setup error handling
        self.setup_error_handling()
        
        try:
            # Create main interface
            self.create_menu()
            self.create_main_interface()
            
            # Try to load default file
            self.load_default_file()
            
        except Exception as e:
            self.handle_error("Initialization", e)
    
    def setup_error_handling(self):
        """Setup comprehensive error handling"""
        # Route tkinter errors to our handler
        self.root.report_callback_exception = self.handle_tkinter_error
        
    def handle_error(self, context, error):
        """Handle errors by showing in GUI"""
        error_msg = f"Error in {context}: {str(error)}"
        messagebox.showerror("Error", error_msg)
        
    def handle_tkinter_error(self, exc_type, exc_value, exc_traceback):
        """Handle tkinter callback errors"""
        error_msg = f"Interface Error: {exc_value}"
        messagebox.showerror("Interface Error", error_msg)
    
    def create_menu(self):
        """Create the menu bar"""
        try:
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)
            file_menu.add_command(label="Open", command=self.open_file)
            file_menu.add_command(label="Save", command=self.save_file)
            file_menu.add_command(label="Save As", command=self.save_as_file)
            file_menu.add_separator()
            file_menu.add_command(label="Refresh View", command=self.refresh_view)
            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.root.quit)
            
            # Help menu
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about)
            
        except Exception as e:
            self.handle_error("create_menu", e)
    
    def create_main_interface(self):
        """Create the main interface"""
        try:
            # Main frame
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # File info frame
            info_frame = ttk.Frame(main_frame)
            info_frame.pack(fill=tk.X, pady=(0, 10))
            
            self.file_label = ttk.Label(info_frame, text="No file loaded", font=("Arial", 10, "bold"))
            self.file_label.pack(side=tk.LEFT)
            
            # Create notebook for tabs
            self.notebook = ttk.Notebook(main_frame)
            self.notebook.pack(fill=tk.BOTH, expand=True)
            
            # Status bar
            self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
            
        except Exception as e:
            self.handle_error("create_main_interface", e)
    
    def load_default_file(self):
        """Try to load the default generated_catchment.json file"""
        try:
            possible_paths = [
                "testData/generated_catchment.json",
                "generated_catchment.json",
                "../testData/generated_catchment.json",
                "testdata/generated_catchment.json"
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.load_file(path)
                    return
            
            # Create sample structure if no file found
            self.data = {
                "name": "Sample Catchment",
                "abbreviation": "SC",
                "HRUs": []
            }
            self.create_catchment_interface()
            
        except Exception as e:
            self.handle_error("load_default_file", e)
    
    def open_file(self):
        """Open file dialog and load JSON file"""
        try:
            file_path = filedialog.askopenfilename(
                title="Open JSON File",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                self.load_file(file_path)
                
        except Exception as e:
            self.handle_error("open_file", e)
    
    def load_file(self, file_path):
        """Load JSON file and create interface"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            self.file_path = file_path
            self.file_label.config(text=f"File: {os.path.basename(file_path)}")
            self.create_catchment_interface()
            self.update_status(f"Loaded: {file_path}")
            
        except Exception as e:
            self.handle_error("load_file", e)
    
    def create_catchment_interface(self):
        """Create interface specifically for catchment JSON structure"""
        try:
            # Clear existing tabs
            for tab in self.notebook.tabs():
                self.notebook.forget(tab)
            
            # Clear widgets dictionary
            self.widgets = {}
            self.widget_paths = {}
            
            # Create catchment overview tab
            self.create_catchment_overview_tab()
            
            # Create individual HRU tabs
            if "HRUs" in self.data and isinstance(self.data["HRUs"], list):
                for i, hru in enumerate(self.data["HRUs"]):
                    self.create_hru_tab(hru, i)
                
        except Exception as e:
            self.handle_error("create_catchment_interface", e)
    
    def create_catchment_overview_tab(self):
        """Create the main catchment properties tab"""
        try:
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
            
            # Title
            ttk.Label(scrollable_frame, text="Catchment Properties", font=("Arial", 14, "bold")).pack(pady=10)
            
            # Create form for catchment properties
            form_frame = ttk.Frame(scrollable_frame)
            form_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Display all catchment-level properties
            row = 0
            for key, value in self.data.items():
                if key != "HRUs":  # Skip HRUs as they get their own tabs
                    current_path = [key]
                    
                    # Check if this is editable (not name or abbreviation for display purposes)
                    is_editable = key not in ["name", "abbreviation"]
                    
                    # Label
                    display_key = self.format_key_name(key)
                    if not is_editable:
                        display_key += " (Read-only)"
                    ttk.Label(form_frame, text=f"{display_key}:", width=25).grid(
                        row=row, column=0, sticky="w", padx=5, pady=5
                    )
                    
                    # Create widget
                    if isinstance(value, (dict, list)):
                        # Complex structure - show summary and expand
                        self.create_complex_value_display(form_frame, value, current_path, row)
                    else:
                        # Simple value
                        widget, var = self.create_widget_for_value(form_frame, value, current_path, readonly=not is_editable)
                        widget.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
                        
                        if var is not None:
                            widget_id = f"catchment_{key}"
                            self.widgets[widget_id] = var
                            self.widget_paths[widget_id] = current_path
                    
                    # Type info
                    type_info = f"({type(value).__name__})"
                    ttk.Label(form_frame, text=type_info, foreground="gray").grid(
                        row=row, column=2, sticky="w", padx=5, pady=5
                    )
                    
                    row += 1
            
            # HRU summary section (read-only)
            ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=20)
            
            ttk.Label(scrollable_frame, text="HRU Summary", font=("Arial", 12, "bold")).pack(pady=10)
            
            hru_count = len(self.data.get("HRUs", []))
            ttk.Label(scrollable_frame, text=f"Total HRUs: {hru_count}").pack(pady=5)
            
            # Configure grid weights
            form_frame.columnconfigure(1, weight=1)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_catchment_overview_tab", e)
    
    def create_hru_tab(self, hru_data, hru_index):
        """Create a tab for a specific HRU"""
        try:
            # Use name for tab name, fallback to abbreviation or index
            tab_name = hru_data.get("name", hru_data.get("abbreviation", f"HRU {hru_index}"))
            
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            
            # Create sub-notebook for HRU sections
            hru_notebook = ttk.Notebook(frame)
            hru_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create tabs for different HRU sections (skip properties tab)
            # Look for major sub-sections and create tabs for them
            for key, value in hru_data.items():
                if isinstance(value, dict) and key not in ["name", "abbreviation"]:
                    # Correct path construction: ["HRUs", hru_index, key]
                    if key == "subcatchment":
                        self.create_subcatchment_tab(hru_notebook, value, ["HRUs", hru_index, key])
                    else:
                        self.create_hru_section_tab(hru_notebook, key, value, ["HRUs", hru_index, key])
                        
        except Exception as e:
            self.handle_error(f"create_hru_tab (index {hru_index})", e)
    
    def create_subcatchment_tab(self, parent_notebook, subcatchment_data, base_path):
        """Create a special subcatchment tab with land cover types as tabs"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text="Subcatchment")
            
            # Create sub-notebook for subcatchment sections
            subcatchment_notebook = ttk.Notebook(frame)
            subcatchment_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Handle each section of subcatchment
            for key, value in subcatchment_data.items():
                current_path = base_path + [key]
                
                if key == "landCoverTypes" and isinstance(value, list):
                    # Create individual tabs for each land cover type
                    for i, land_cover in enumerate(value):
                        land_cover_path = current_path + [i]
                        land_cover_name = self.get_item_display_name(land_cover, i)
                        self.create_land_cover_tab(subcatchment_notebook, land_cover_name, land_cover, land_cover_path)
                else:
                    # Handle other subcatchment sections normally
                    if isinstance(value, dict):
                        self.create_subcatchment_section_tab(subcatchment_notebook, key, value, current_path)
                    elif isinstance(value, list):
                        self.create_subcatchment_list_tab(subcatchment_notebook, key, value, current_path)
                        
        except Exception as e:
            self.handle_error("create_subcatchment_tab", e)
    
    def create_land_cover_tab(self, parent_notebook, land_cover_name, land_cover_data, base_path):
        """Create a tab for a specific land cover type"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text=land_cover_name)
            
            # Create sub-notebook for land cover sections
            land_cover_notebook = ttk.Notebook(frame)
            land_cover_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Reset the properties creation flag for each land cover
            land_cover_props_created = False
            
            # Handle each section of land cover
            for key, value in land_cover_data.items():
                current_path = base_path + [key]
                
                if key == "buckets" and isinstance(value, list):
                    # Create individual tabs for each bucket
                    for i, bucket in enumerate(value):
                        bucket_path = current_path + [i]
                        bucket_name = self.get_item_display_name(bucket, i)
                        self.create_bucket_tab(land_cover_notebook, bucket_name, bucket, bucket_path)
                else:
                    # Handle other land cover sections normally
                    if isinstance(value, dict):
                        self.create_land_cover_section_tab(land_cover_notebook, key, value, current_path)
                    elif isinstance(value, list):
                        self.create_land_cover_list_tab(land_cover_notebook, key, value, current_path)
                    else:
                        # Simple values - create a properties tab if we don't have one
                        if not land_cover_props_created:
                            self.create_land_cover_properties_tab(land_cover_notebook, land_cover_data, base_path)
                            land_cover_props_created = True
                            
        except Exception as e:
            self.handle_error(f"create_land_cover_tab ({land_cover_name})", e)
    
    def create_bucket_tab(self, parent_notebook, bucket_name, bucket_data, base_path):
        """Create a tab for a specific bucket"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text=bucket_name)
            
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
            
            # Title
            ttk.Label(scrollable_frame, text=f"{bucket_name} Properties", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Create expandable structure for bucket data
            self.create_expandable_dict_interface(scrollable_frame, bucket_data, base_path)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_bucket_tab ({bucket_name})", e)
    
    def create_expandable_dict_interface(self, parent, data_dict, base_path, level=0):
        """Create an expandable interface for dictionary data"""
        try:
            for key, value in data_dict.items():
                current_path = base_path + [key]
                
                if isinstance(value, dict):
                    # Create expandable frame for sub-dictionary
                    self.create_dict_section(parent, key, value, current_path, level)
                elif isinstance(value, list):
                    # Create list section
                    self.create_list_section(parent, key, value, current_path, level)
                else:
                    # Simple value
                    self.create_simple_value_row(parent, key, value, current_path, level)
                    
        except Exception as e:
            self.handle_error(f"create_expandable_dict_interface (level {level})", e)
    
    def create_dict_section(self, parent, section_name, data_dict, path, level):
        """Create a collapsible section for a dictionary"""
        try:
            # Create frame for this section
            display_name = self.format_key_name(section_name)
            section_frame = ttk.LabelFrame(parent, text=f"{display_name} ({len(data_dict)} properties)")
            section_frame.pack(fill=tk.X, padx=level*20, pady=5)
            
            # Create content frame
            content_frame = ttk.Frame(section_frame)
            content_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Recursively create interface for dictionary contents
            self.create_expandable_dict_interface(content_frame, data_dict, path, level + 1)
            
        except Exception as e:
            self.handle_error(f"create_dict_section ({section_name})", e)
    
    def create_list_section(self, parent, section_name, data_list, path, level):
        """Create a section for a list"""
        try:
            section_frame = ttk.LabelFrame(parent, text=f"{self.format_key_name(section_name)} ({len(data_list)} items)")
            section_frame.pack(fill=tk.X, padx=level*20, pady=5)
            
            content_frame = ttk.Frame(section_frame)
            content_frame.pack(fill=tk.X, padx=10, pady=5)
            
            for i, item in enumerate(data_list):
                item_path = path + [i]
                
                # Try to get a meaningful name for the item
                item_name = self.get_item_display_name(item, i)
                
                if isinstance(item, dict):
                    # Dictionary item
                    item_frame = ttk.LabelFrame(content_frame, text=item_name)
                    item_frame.pack(fill=tk.X, pady=2)
                    
                    item_content = ttk.Frame(item_frame)
                    item_content.pack(fill=tk.X, padx=5, pady=5)
                    
                    self.create_expandable_dict_interface(item_content, item, item_path, level + 1)
                elif isinstance(item, list):
                    # Nested list
                    ttk.Label(content_frame, text=f"{item_name}: Nested list with {len(item)} items").pack(anchor="w")
                else:
                    # Simple item
                    self.create_simple_value_row(content_frame, f"Item {i}", item, item_path, level + 1)
                    
        except Exception as e:
            self.handle_error(f"create_list_section ({section_name})", e)
    
    def create_simple_value_row(self, parent, key, value, path, level):
        """Create a row for a simple value"""
        try:
            # Skip read-only name and abbreviation fields in subcatchment properties
            if key in ["name", "abbreviation"]:
                return
                
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, padx=level*10, pady=2)
            
            # Convert key to human-readable format
            display_key = self.format_key_name(key)
            
            # Label
            ttk.Label(row_frame, text=f"{display_key}:", width=25).pack(side=tk.LEFT, padx=5)
            
            # Widget
            widget, var = self.create_widget_for_value(row_frame, value, path)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            if var is not None:
                widget_id = f"widget_{len(self.widgets)}"
                self.widgets[widget_id] = var
                self.widget_paths[widget_id] = path
            
            # Type info
            type_info = f"({type(value).__name__})"
            ttk.Label(row_frame, text=type_info, foreground="gray").pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            self.handle_error(f"create_simple_value_row ({key})", e)
    
    def create_complex_value_display(self, parent, value, path, row):
        """Create display for complex values in the overview"""
        try:
            if isinstance(value, dict):
                summary = f"Dictionary with {len(value)} keys"
            elif isinstance(value, list):
                summary = f"Array with {len(value)} items"
            else:
                summary = str(value)
            
            ttk.Label(parent, text=summary, foreground="blue").grid(
                row=row, column=1, sticky="w", padx=5, pady=5
            )
            
        except Exception as e:
            self.handle_error(f"create_complex_value_display", e)
    
    def format_key_name(self, key):
        """Convert camelCase or snake_case keys to human-readable format"""
        try:
            import re
            
            # Handle camelCase: insert space before capital letters
            formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
            
            # Handle snake_case: replace underscores with spaces
            formatted = formatted.replace('_', ' ')
            
            # Capitalize first letter and return
            return formatted.capitalize()
            
        except Exception as e:
            self.handle_error(f"format_key_name ({key})", e)
            return key  # Return original if formatting fails
    
    def get_item_display_name(self, item, index):
        """Get a meaningful display name for a list item"""
        try:
            if isinstance(item, dict):
                # Try to find a name field
                if "name" in item and item["name"]:
                    return item["name"]
                elif "abbreviation" in item and item["abbreviation"]:
                    return item["abbreviation"]
                elif "title" in item and item["title"]:
                    return item["title"]
                else:
                    return f"Item {index}"
            else:
                return f"Item {index}"
                
        except Exception as e:
            self.handle_error(f"get_item_display_name (index {index})", e)
            return f"Item {index}"
    
    def create_widget_for_value(self, parent, value, path, readonly=False):
        """Create appropriate widget for a value type"""
        try:
            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                widget = ttk.Checkbutton(parent, variable=var, state='disabled' if readonly else 'normal')
                return widget, var
            
            elif isinstance(value, (int, float)):
                var = tk.StringVar(value=str(value))
                widget = ttk.Entry(parent, textvariable=var, width=10, justify='right', 
                                 state='readonly' if readonly else 'normal')
                return widget, var
            
            elif isinstance(value, str):
                var = tk.StringVar(value=value)
                if len(value) > 100:  # Long text
                    widget = tk.Text(parent, height=3, width=50)
                    widget.insert('1.0', value)
                    if readonly:
                        widget.config(state='disabled')
                    return widget, None  # Text widget doesn't use StringVar
                else:
                    # Use shorter width for strings too, unless they're very long
                    width = 50 if len(value) > 30 else 25
                    widget = ttk.Entry(parent, textvariable=var, width=width, state='readonly' if readonly else 'normal')
                    return widget, var
            
            elif value is None:
                var = tk.StringVar(value="null")
                widget = ttk.Entry(parent, textvariable=var, width=15, state='readonly' if readonly else 'normal')
                return widget, var
            
            else:
                # Fallback for other types - use shorter width
                var = tk.StringVar(value=str(value))
                widget = ttk.Entry(parent, textvariable=var, width=20, state='readonly' if readonly else 'normal')
                return widget, var
                
        except Exception as e:
            self.handle_error(f"create_widget_for_value", e)
            # Return a basic label as fallback
            label = ttk.Label(parent, text=str(value))
            return label, None
    
    # Additional tab creation methods
    def create_land_cover_properties_tab(self, parent_notebook, land_cover_data, base_path):
        """Create a properties tab for simple land cover values"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text="Properties")
            
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
            
            # Title
            ttk.Label(scrollable_frame, text="Land Cover Properties", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Create form for simple values only
            form_frame = ttk.Frame(scrollable_frame)
            form_frame.pack(fill=tk.X, padx=20, pady=10)
            
            row = 0
            for key, value in land_cover_data.items():
                if not isinstance(value, (dict, list)):  # Only simple values
                    current_path = base_path + [key]
                    self.create_simple_value_row(form_frame, key, value, current_path, 0)
                    row += 1
            
            form_frame.columnconfigure(1, weight=1)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_land_cover_properties_tab", e)
    
    def create_land_cover_section_tab(self, parent_notebook, section_name, section_data, base_path):
        """Create a tab for a land cover section"""
        try:
            frame = ttk.Frame(parent_notebook)
            tab_name = self.format_key_name(section_name)
            parent_notebook.add(frame, text=tab_name)
            
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
            
            # Title
            ttk.Label(scrollable_frame, text=f"{tab_name} Properties", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Create expandable structure for this section
            self.create_expandable_dict_interface(scrollable_frame, section_data, base_path)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_land_cover_section_tab ({section_name})", e)
    
    def create_land_cover_list_tab(self, parent_notebook, section_name, section_data, base_path):
        """Create a tab for a land cover list section"""
        try:
            frame = ttk.Frame(parent_notebook)
            tab_name = self.format_key_name(section_name)
            parent_notebook.add(frame, text=tab_name)
            
            # Create scrollable frame and list interface
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            self.create_list_section(scrollable_frame, section_name, section_data, base_path, 0)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_land_cover_list_tab ({section_name})", e)
    
    def create_subcatchment_section_tab(self, parent_notebook, section_name, section_data, base_path):
        """Create a tab for a subcatchment section"""
        try:
            frame = ttk.Frame(parent_notebook)
            tab_name = self.format_key_name(section_name)
            parent_notebook.add(frame, text=tab_name)
            
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
            
            # Title
            ttk.Label(scrollable_frame, text=f"{tab_name} Properties", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Create expandable structure for this section
            self.create_expandable_dict_interface(scrollable_frame, section_data, base_path)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_subcatchment_section_tab ({section_name})", e)
    
    def create_subcatchment_list_tab(self, parent_notebook, section_name, section_data, base_path):
        """Create a tab for a subcatchment list section"""
        try:
            frame = ttk.Frame(parent_notebook)
            tab_name = self.format_key_name(section_name)
            parent_notebook.add(frame, text=tab_name)
            
            # Create scrollable frame and list interface
            canvas = tk.Canvas(frame)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            self.create_list_section(scrollable_frame, section_name, section_data, base_path, 0)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_subcatchment_list_tab ({section_name})", e)
    
    def create_hru_section_tab(self, parent_notebook, section_name, section_data, base_path):
        """Create a tab for an HRU section (like reach, etc.)"""
        try:
            frame = ttk.Frame(parent_notebook)
            tab_name = section_name.title()
            parent_notebook.add(frame, text=tab_name)
            
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
            
            # Title
            ttk.Label(scrollable_frame, text=f"{section_name.title()} Properties", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Create expandable structure for this section
            self.create_expandable_dict_interface(scrollable_frame, section_data, base_path)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_hru_section_tab ({section_name})", e)
    
    def collect_data_from_widgets(self):
        """Collect all data from widgets and rebuild JSON structure"""
        try:
            # Create a deep copy of original data to preserve structure
            import copy
            updated_data = copy.deepcopy(self.data)
            
            # Update values from widgets
            for widget_id, var in self.widgets.items():
                if widget_id in self.widget_paths:
                    path = self.widget_paths[widget_id]
                    
                    try:
                        if isinstance(var, tk.BooleanVar):
                            new_value = var.get()
                        elif isinstance(var, tk.StringVar):
                            string_value = var.get()
                            # Convert back to original type
                            original_value = self.get_value_at_path(self.data, path)
                            new_value = self.convert_string_to_type(string_value, type(original_value))
                        else:
                            new_value = var.get()
                        
                        # Set the value at the path
                        self.set_value_at_path(updated_data, path, new_value)
                        
                    except Exception as e:
                        # Skip individual widget errors but continue with others
                        pass
            
            self.data = updated_data
            
        except Exception as e:
            self.handle_error("collect_data_from_widgets", e)
    
    def get_value_at_path(self, data, path):
        """Get value at a specific path in the data structure"""
        try:
            current = data
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
                    current = current[key]
                else:
                    return None
            return current
            
        except Exception as e:
            self.handle_error(f"get_value_at_path ({path})", e)
            return None
    
    def set_value_at_path(self, data, path, value):
        """Set value at a specific path in the data structure"""
        try:
            current = data
            
            # Navigate to the parent of the target
            for key in path[:-1]:
                if isinstance(current, dict):
                    if key in current:
                        current = current[key]
                    else:
                        return  # Path doesn't exist
                elif isinstance(current, list):
                    if isinstance(key, int) and 0 <= key < len(current):
                        current = current[key]
                    else:
                        return  # Invalid index
                else:
                    return  # Cannot navigate
            
            # Set the final value
            final_key = path[-1]
            
            if isinstance(current, dict):
                if final_key in current:
                    current[final_key] = value
            elif isinstance(current, list):
                if isinstance(final_key, int) and 0 <= final_key < len(current):
                    current[final_key] = value
                
        except Exception as e:
            self.handle_error(f"set_value_at_path ({path})", e)
    
    def convert_string_to_type(self, string_value, target_type):
        """Convert string value back to original type"""
        try:
            if target_type == bool:
                return string_value.lower() in ('true', '1', 'yes', 'on')
            elif target_type == int:
                try:
                    return int(float(string_value))
                except ValueError:
                    return 0
            elif target_type == float:
                try:
                    return float(string_value)
                except ValueError:
                    return 0.0
            elif target_type == type(None):
                return None if string_value.lower() in ('null', 'none', '') else string_value
            else:
                return string_value
                
        except Exception as e:
            self.handle_error(f"convert_string_to_type ({string_value}, {target_type})", e)
            return string_value
    
    def save_file(self):
        """Save the current data to file"""
        try:
            if not self.file_path:
                self.save_as_file()
                return
            
            self.collect_data_from_widgets()
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.update_status(f"Saved: {self.file_path}")
            messagebox.showinfo("Success", "File saved successfully!")
            
        except Exception as e:
            self.handle_error("save_file", e)
    
    def save_as_file(self):
        """Save the current data to a new file"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="Save JSON File",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                self.file_path = file_path
                self.file_label.config(text=f"File: {os.path.basename(file_path)}")
                self.save_file()
                
        except Exception as e:
            self.handle_error("save_as_file", e)
    
    def refresh_view(self):
        """Refresh the view (reload from current data)"""
        try:
            self.create_catchment_interface()
            self.update_status("View refreshed")
            
        except Exception as e:
            self.handle_error("refresh_view", e)
    
    def update_status(self, message):
        """Update the status bar"""
        try:
            self.status_bar.config(text=message)
            self.root.after(5000, lambda: self.status_bar.config(text="Ready"))
            
        except Exception as e:
            self.handle_error("update_status", e)
    
    def show_about(self):
        """Show about dialog"""
        try:
            about_text = """
Catchment JSON Editor

A specialized tool for editing catchment JSON files.

Features:
- Catchment overview tab
- Individual HRU tabs (using names as tab names)
- Expandable interface for complex nested data
- Read-only names and abbreviations for reference
- Right-aligned numeric fields with appropriate sizing
- Land cover types and buckets as individual tabs

Created with Python tkinter.
            """
            messagebox.showinfo("About", about_text.strip())
            
        except Exception as e:
            self.handle_error("show_about", e)


if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = CatchmentJSONEditor(root)
        root.mainloop()
        
    except Exception as e:
        try:
            root = tk.Tk()
            root.withdraw()  # Hide main window
            messagebox.showerror("Fatal Error", f"Application failed to start:\n{str(e)}")
        except:
            pass