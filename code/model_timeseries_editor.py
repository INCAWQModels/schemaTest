import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from pathlib import Path

class ModelTimeSeriesEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Model Time Series Editor")
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
        """Try to load the default ModelTimeSeries.json file"""
        try:
            possible_paths = [
                "testData/ModelTimeSeries.json",
                "ModelTimeSeries.json",
                "../testData/ModelTimeSeries.json",
                "testdata/ModelTimeSeries.json"
            ]
            
            for path in possible_paths:
                if Path(path).exists():
                    self.load_file(path)
                    return
            
            # Create sample structure if no file found
            self.data = {
                "catchment": {
                    "name": "Sample Catchment",
                    "abbreviation": "SC",
                    "timeSeries": {
                        "folder": "SampleCatchment",
                        "solarRadiation": {
                            "fileName": "SampleCatchment_solarRadiation",
                            "mandatory": True,
                            "generated": False
                        },
                        "temperatureAndPrecipitation": {
                            "fileName": "SampleCatchment_temperatureAndPrecipitation",
                            "mandatory": True,
                            "generated": False
                        }
                    },
                    "HRUs": []
                },
                "summary": {
                    "totalHRUs": 0,
                    "generatedFrom": {
                        "schemas": "schemas.json",
                        "timeSeries": "timeSeries.json",
                        "generatedNames": "generatedNames.json"
                    },
                    "totalLandCoverTypes": 0,
                    "totalBuckets": 0,
                    "totalParticleSizeClasses": 0
                }
            }
            self.create_timeseries_interface()
            
        except Exception as e:
            self.handle_error("load_default_file", e)
    
    def open_file(self):
        """Open file dialog and load JSON file"""
        try:
            file_path = filedialog.askopenfilename(
                title="Open ModelTimeSeries JSON File",
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
            self.create_timeseries_interface()
            self.update_status(f"Loaded: {file_path}")
            
        except Exception as e:
            self.handle_error("load_file", e)
    
    def create_timeseries_interface(self):
        """Create interface for ModelTimeSeries JSON structure"""
        try:
            # Clear existing tabs
            for tab in self.notebook.tabs():
                self.notebook.forget(tab)
            
            # Clear widgets dictionary
            self.widgets = {}
            self.widget_paths = {}
            
            # Create overview tab
            self.create_overview_tab()
            
            # Create catchment time series tab
            if "catchment" in self.data:
                self.create_catchment_timeseries_tab()
            
            # Create individual HRU tabs
            catchment_data = self.data.get("catchment", {})
            hrus = catchment_data.get("HRUs", [])
            
            for i, hru in enumerate(hrus):
                self.create_hru_timeseries_tab(hru, i)
                
        except Exception as e:
            self.handle_error("create_timeseries_interface", e)
    
    def create_overview_tab(self):
        """Create the overview tab with summary information"""
        try:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text="Overview")
            
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
            ttk.Label(scrollable_frame, text="Model Time Series Overview", 
                     font=("Arial", 14, "bold")).pack(pady=10)
            
            # Catchment info section
            catchment_frame = ttk.LabelFrame(scrollable_frame, text="Catchment Information")
            catchment_frame.pack(fill=tk.X, padx=20, pady=10)
            
            catchment_data = self.data.get("catchment", {})
            
            # Catchment name and abbreviation (editable)
            self.create_field_row(catchment_frame, "Name:", catchment_data.get("name", ""), 
                                ["catchment", "name"])
            self.create_field_row(catchment_frame, "Abbreviation:", catchment_data.get("abbreviation", ""), 
                                ["catchment", "abbreviation"])
            
            # Summary section
            summary_frame = ttk.LabelFrame(scrollable_frame, text="Summary Statistics")
            summary_frame.pack(fill=tk.X, padx=20, pady=10)
            
            summary_data = self.data.get("summary", {})
            
            # Read-only summary fields
            for key, value in summary_data.items():
                if isinstance(value, dict):
                    # Handle nested objects like "generatedFrom"
                    sub_frame = ttk.Frame(summary_frame)
                    sub_frame.pack(fill=tk.X, padx=10, pady=2)
                    
                    ttk.Label(sub_frame, text=f"{self.format_key_name(key)}:", 
                             width=25).pack(side=tk.LEFT, padx=5)
                    
                    # Show nested dict as comma-separated key:value pairs
                    nested_text = ", ".join([f"{k}: {v}" for k, v in value.items()])
                    ttk.Label(sub_frame, text=nested_text, foreground="gray").pack(side=tk.LEFT, padx=5)
                else:
                    self.create_readonly_field_row(summary_frame, self.format_key_name(key), str(value))
            
            # Time series counts
            hrus = catchment_data.get("HRUs", [])
            ttk.Label(summary_frame, text=f"HRUs with time series: {len(hrus)}", 
                     foreground="blue").pack(pady=5)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_overview_tab", e)
    
    def create_catchment_timeseries_tab(self):
        """Create tab for catchment-level time series"""
        try:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text="Catchment Time Series")
            
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
            catchment_data = self.data.get("catchment", {})
            catchment_name = catchment_data.get("name", "Unknown")
            ttk.Label(scrollable_frame, text=f"Catchment Time Series: {catchment_name}", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Time series section
            timeseries_data = catchment_data.get("timeSeries", {})
            
            if timeseries_data:
                ts_frame = ttk.LabelFrame(scrollable_frame, text="Time Series Configuration")
                ts_frame.pack(fill=tk.X, padx=20, pady=10)
                
                for ts_name, ts_config in timeseries_data.items():
                    if ts_name == "folder":
                        # Special handling for folder property
                        self.create_field_row(ts_frame, "Output Folder:", ts_config, 
                                            ["catchment", "timeSeries", "folder"])
                    elif isinstance(ts_config, dict):
                        # Regular time series configuration
                        self.create_timeseries_section(ts_frame, ts_name, ts_config, 
                                                     ["catchment", "timeSeries", ts_name])
            else:
                ttk.Label(scrollable_frame, text="No catchment time series configured.", 
                         foreground="gray").pack(pady=20)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_catchment_timeseries_tab", e)
    
    def create_hru_timeseries_tab(self, hru_data, hru_index):
        """Create a tab for a specific HRU's time series"""
        try:
            # Use name for tab name, fallback to abbreviation or index
            tab_name = hru_data.get("name", hru_data.get("abbreviation", f"HRU {hru_index}"))
            
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=tab_name)
            
            # Create sub-notebook for HRU sections
            hru_notebook = ttk.Notebook(frame)
            hru_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Get time series data
            timeseries_data = hru_data.get("timeSeries", {})
            
            # Create tabs for subcatchment and reach time series
            if "subcatchment" in timeseries_data:
                self.create_subcatchment_timeseries_tab(hru_notebook, timeseries_data["subcatchment"], 
                                                      ["catchment", "HRUs", hru_index, "timeSeries", "subcatchment"])
            
            if "reach" in timeseries_data:
                self.create_reach_timeseries_tab(hru_notebook, timeseries_data["reach"], 
                                                ["catchment", "HRUs", hru_index, "timeSeries", "reach"])
                        
        except Exception as e:
            self.handle_error(f"create_hru_timeseries_tab (index {hru_index})", e)
    
    def create_subcatchment_timeseries_tab(self, parent_notebook, subcatchment_data, base_path):
        """Create subcatchment time series tab with land cover types"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text="Subcatchment")
            
            # Create sub-notebook for subcatchment sections
            subcatchment_notebook = ttk.Notebook(frame)
            subcatchment_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create tab for subcatchment-level time series
            self.create_subcatchment_properties_tab(subcatchment_notebook, subcatchment_data, base_path)
            
            # Create tabs for land cover types
            land_cover_types = subcatchment_data.get("landCoverTypes", [])
            for i, land_cover in enumerate(land_cover_types):
                land_cover_name = land_cover.get("name", f"LandCover {i}")
                land_cover_path = base_path + ["landCoverTypes", i]
                self.create_landcover_timeseries_tab(subcatchment_notebook, land_cover_name, 
                                                   land_cover, land_cover_path)
                        
        except Exception as e:
            self.handle_error("create_subcatchment_timeseries_tab", e)
    
    def create_subcatchment_properties_tab(self, parent_notebook, subcatchment_data, base_path):
        """Create tab for subcatchment-level time series properties"""
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
            ttk.Label(scrollable_frame, text="Subcatchment Time Series", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Time series for subcatchment level (excluding landCoverTypes)
            for key, value in subcatchment_data.items():
                if key != "landCoverTypes" and isinstance(value, dict):
                    # This should be a time series configuration
                    self.create_timeseries_section(scrollable_frame, key, value, base_path + [key])
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_subcatchment_properties_tab", e)
    
    def create_landcover_timeseries_tab(self, parent_notebook, land_cover_name, land_cover_data, base_path):
        """Create tab for land cover type time series"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text=land_cover_name)
            
            # Create sub-notebook for land cover sections
            landcover_notebook = ttk.Notebook(frame)
            landcover_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Create properties tab for land cover time series
            self.create_landcover_properties_tab(landcover_notebook, land_cover_data, base_path)
            
            # Create tabs for buckets if they exist
            timeseries_data = land_cover_data.get("timeSeries", {})
            buckets = timeseries_data.get("buckets", [])
            
            for i, bucket in enumerate(buckets):
                bucket_name = bucket.get("name", f"Bucket {i}")
                bucket_path = base_path + ["timeSeries", "buckets", i]
                self.create_bucket_timeseries_tab(landcover_notebook, bucket_name, bucket, bucket_path)
                        
        except Exception as e:
            self.handle_error(f"create_landcover_timeseries_tab ({land_cover_name})", e)
    
    def create_landcover_properties_tab(self, parent_notebook, land_cover_data, base_path):
        """Create tab for land cover time series properties"""
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
            land_cover_name = land_cover_data.get("name", "Unknown")
            ttk.Label(scrollable_frame, text=f"Land Cover Time Series: {land_cover_name}", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Read-only name and abbreviation
            info_frame = ttk.LabelFrame(scrollable_frame, text="Land Cover Information")
            info_frame.pack(fill=tk.X, padx=20, pady=10)
            
            self.create_readonly_field_row(info_frame, "Name", land_cover_data.get("name", ""))
            self.create_readonly_field_row(info_frame, "Abbreviation", land_cover_data.get("abbreviation", ""))
            
            # Time series configuration
            timeseries_data = land_cover_data.get("timeSeries", {})
            
            for key, value in timeseries_data.items():
                if key != "buckets" and isinstance(value, dict):
                    # This should be a time series configuration
                    self.create_timeseries_section(scrollable_frame, key, value, 
                                                 base_path + ["timeSeries", key])
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_landcover_properties_tab", e)
    
    def create_bucket_timeseries_tab(self, parent_notebook, bucket_name, bucket_data, base_path):
        """Create tab for bucket time series"""
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
            ttk.Label(scrollable_frame, text=f"Bucket Time Series: {bucket_name}", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Read-only bucket information
            info_frame = ttk.LabelFrame(scrollable_frame, text="Bucket Information")
            info_frame.pack(fill=tk.X, padx=20, pady=10)
            
            self.create_readonly_field_row(info_frame, "Name", bucket_data.get("name", ""))
            self.create_readonly_field_row(info_frame, "Abbreviation", bucket_data.get("abbreviation", ""))
            
            # Time series configuration
            timeseries_data = bucket_data.get("timeSeries", {})
            
            for ts_name, ts_config in timeseries_data.items():
                self.create_timeseries_section(scrollable_frame, ts_name, ts_config, 
                                             base_path + ["timeSeries", ts_name])
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error(f"create_bucket_timeseries_tab ({bucket_name})", e)
    
    def create_reach_timeseries_tab(self, parent_notebook, reach_data, base_path):
        """Create tab for reach time series"""
        try:
            frame = ttk.Frame(parent_notebook)
            parent_notebook.add(frame, text="Reach")
            
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
            ttk.Label(scrollable_frame, text="Reach Time Series", 
                     font=("Arial", 12, "bold")).pack(pady=10)
            
            # Time series configuration
            for ts_name, ts_config in reach_data.items():
                if isinstance(ts_config, dict):
                    self.create_timeseries_section(scrollable_frame, ts_name, ts_config, 
                                                 base_path + [ts_name])
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
        except Exception as e:
            self.handle_error("create_reach_timeseries_tab", e)
    
    def create_timeseries_section(self, parent, ts_name, ts_config, base_path):
        """Create a section for editing a time series configuration"""
        try:
            # Create frame for this time series
            ts_frame = ttk.LabelFrame(parent, text=self.format_key_name(ts_name))
            ts_frame.pack(fill=tk.X, padx=20, pady=10)
            
            # Create fields for each time series property
            for key, value in ts_config.items():
                if key == "fileName":
                    self.create_field_row(ts_frame, "File Name:", value, base_path + [key])
                elif key == "mandatory":
                    self.create_boolean_field_row(ts_frame, "Mandatory:", value, base_path + [key])
                elif key == "generated":
                    self.create_boolean_field_row(ts_frame, "Generated:", value, base_path + [key])
                else:
                    # Handle any other fields that might exist
                    self.create_field_row(ts_frame, f"{self.format_key_name(key)}:", str(value), 
                                        base_path + [key])
            
        except Exception as e:
            self.handle_error(f"create_timeseries_section ({ts_name})", e)
    
    def create_field_row(self, parent, label_text, initial_value, path):
        """Create an editable field row"""
        try:
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Label
            ttk.Label(row_frame, text=label_text, width=15).pack(side=tk.LEFT, padx=5)
            
            # Entry widget
            var = tk.StringVar(value=str(initial_value))
            entry = ttk.Entry(row_frame, textvariable=var, width=50)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            
            # Store widget reference
            widget_id = f"field_{len(self.widgets)}"
            self.widgets[widget_id] = var
            self.widget_paths[widget_id] = path
            
        except Exception as e:
            self.handle_error(f"create_field_row ({label_text})", e)
    
    def create_boolean_field_row(self, parent, label_text, initial_value, path):
        """Create a boolean field row with checkbox"""
        try:
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Label
            ttk.Label(row_frame, text=label_text, width=15).pack(side=tk.LEFT, padx=5)
            
            # Checkbox
            var = tk.BooleanVar(value=bool(initial_value))
            checkbox = ttk.Checkbutton(row_frame, variable=var)
            checkbox.pack(side=tk.LEFT, padx=5)
            
            # Store widget reference
            widget_id = f"bool_{len(self.widgets)}"
            self.widgets[widget_id] = var
            self.widget_paths[widget_id] = path
            
        except Exception as e:
            self.handle_error(f"create_boolean_field_row ({label_text})", e)
    
    def create_readonly_field_row(self, parent, label_text, value):
        """Create a read-only field row"""
        try:
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=tk.X, padx=10, pady=2)
            
            # Label
            ttk.Label(row_frame, text=f"{label_text}:", width=15).pack(side=tk.LEFT, padx=5)
            
            # Value label
            ttk.Label(row_frame, text=str(value), foreground="gray").pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            self.handle_error(f"create_readonly_field_row ({label_text})", e)
    
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
                            # Convert back to original type if needed
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
                title="Save ModelTimeSeries JSON File",
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
            self.create_timeseries_interface()
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
Model Time Series Editor

A specialized tool for editing ModelTimeSeries.json files for hydrological models.

Features:
- Overview tab with catchment information and summary statistics
- Catchment-level time series configuration with folder property
- Individual HRU tabs with subcatchment and reach time series
- Land cover type and bucket time series configuration
- Boolean checkboxes for mandatory/generated flags
- Hierarchical organization using nested notebooks

Time Series Properties:
- fileName: Base name for the time series files
- mandatory: Whether the time series is required for model execution
- generated: Whether the time series is generated during model run
- folder: Output folder for catchment-level time series files

The application supports the complete ModelTimeSeries.json structure including:
- Catchment properties and time series (with folder configuration)
- HRU-level organization with subcatchment and reach components
- Land cover types with individual bucket configurations
- Summary metadata tracking generation sources and statistics

Created with Python tkinter using only standard library components.
            """
            messagebox.showinfo("About", about_text.strip())
            
        except Exception as e:
            self.handle_error("show_about", e)


def main():
    """Main function to run the application"""
    try:
        root = tk.Tk()
        app = ModelTimeSeriesEditor(root)
        root.mainloop()
        
    except Exception as e:
        try:
            root = tk.Tk()
            root.withdraw()  # Hide main window
            messagebox.showerror("Fatal Error", f"Application failed to start:\n{str(e)}")
        except:
            print(f"Fatal Error: {str(e)}")


if __name__ == "__main__":
    main()