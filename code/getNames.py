import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
from typing import Dict, List, Any

class JSONGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JSON Generator - names.json Schema")
        self.root.geometry("800x600")
        
        # Data storage
        self.data = {
            "catchment": {"name": "", "abbreviation": ""},
            "HRU": [],
            "landCoverType": [],
            "bucket": [],
            "grainSizeClass": []
        }
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Catchment tab
        self.create_catchment_tab(notebook)
        
        # HRU tab
        self.create_array_tab(notebook, "HRU", "HRU")
        
        # Land Cover Type tab
        self.create_array_tab(notebook, "Land Cover Type", "landCoverType")
        
        # Bucket tab
        self.create_array_tab(notebook, "Bucket", "bucket")
        
        # Grain Size Class tab
        self.create_grain_size_tab(notebook)
        
        # Control buttons
        self.create_control_buttons()
        
    def create_catchment_tab(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Catchment")
        
        # Title
        title_label = ttk.Label(frame, text="Catchment Information", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Input frame
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=20)
        
        # Name field
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.catchment_name = ttk.Entry(input_frame, width=40)
        self.catchment_name.grid(row=0, column=1, padx=5, pady=5)
        
        # Abbreviation field
        ttk.Label(input_frame, text="Abbreviation:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.catchment_abbrev = ttk.Entry(input_frame, width=40)
        self.catchment_abbrev.grid(row=1, column=1, padx=5, pady=5)
        
    def create_array_tab(self, notebook, tab_name, data_key):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=tab_name)
        
        # Title
        title_label = ttk.Label(frame, text=f"{tab_name} Management", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Input frame
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5)
        name_entry = ttk.Entry(input_frame, width=30)
        name_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="Abbreviation:").grid(row=0, column=2, sticky="w", padx=5)
        abbrev_entry = ttk.Entry(input_frame, width=15)
        abbrev_entry.grid(row=0, column=3, padx=5)
        
        def add_item():
            name = name_entry.get().strip()
            abbrev = abbrev_entry.get().strip()
            
            if not name or not abbrev:
                messagebox.showwarning("Input Error", "Please fill in both name and abbreviation.")
                return
                
            item = {"name": name, "abbreviation": abbrev}
            self.data[data_key].append(item)
            
            listbox.insert(tk.END, f"{name} ({abbrev})")
            name_entry.delete(0, tk.END)
            abbrev_entry.delete(0, tk.END)
        
        def remove_item():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to remove.")
                return
                
            index = selection[0]
            listbox.delete(index)
            del self.data[data_key][index]
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=4, padx=10)
        
        ttk.Button(button_frame, text="Add", command=add_item).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Remove", command=remove_item).pack(side=tk.LEFT, padx=2)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_grain_size_tab(self, notebook):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Grain Size Class")
        
        # Title
        title_label = ttk.Label(frame, text="Grain Size Class Management", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Input frame
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10)
        
        # Row 0: Name and Abbreviation
        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        name_entry = ttk.Entry(input_frame, width=25)
        name_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(input_frame, text="Abbreviation:").grid(row=0, column=2, sticky="w", padx=5, pady=2)
        abbrev_entry = ttk.Entry(input_frame, width=15)
        abbrev_entry.grid(row=0, column=3, padx=5, pady=2)
        
        # Row 1: Size dimensions
        ttk.Label(input_frame, text="Min Size (mm):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        min_size_entry = ttk.Entry(input_frame, width=15)
        min_size_entry.grid(row=1, column=1, padx=5, pady=2)
        min_size_entry.insert(0, "1.0")  # Default value
        
        ttk.Label(input_frame, text="Max Size (mm):").grid(row=1, column=2, sticky="w", padx=5, pady=2)
        max_size_entry = ttk.Entry(input_frame, width=15)
        max_size_entry.grid(row=1, column=3, padx=5, pady=2)
        max_size_entry.insert(0, "1.0")  # Default value
        
        def add_grain_size():
            name = name_entry.get().strip()
            abbrev = abbrev_entry.get().strip()
            
            if not name or not abbrev:
                messagebox.showwarning("Input Error", "Please fill in both name and abbreviation.")
                return
            
            try:
                min_size = float(min_size_entry.get())
                max_size = float(max_size_entry.get())
                
                if min_size < 0 or max_size < 0:
                    messagebox.showerror("Value Error", "Size values must be non-negative.")
                    return
                    
                if min_size > max_size:
                    messagebox.showerror("Value Error", "Minimum size cannot be greater than maximum size.")
                    return
                    
            except ValueError:
                messagebox.showerror("Value Error", "Please enter valid numeric values for sizes.")
                return
            
            item = {
                "name": name,
                "abbreviation": abbrev,
                "minimumSize": min_size,
                "maximumSize": max_size
            }
            
            self.data["grainSizeClass"].append(item)
            listbox.insert(tk.END, f"{name} ({abbrev}) - {min_size}-{max_size}mm")
            
            # Clear entries
            name_entry.delete(0, tk.END)
            abbrev_entry.delete(0, tk.END)
            min_size_entry.delete(0, tk.END)
            min_size_entry.insert(0, "1.0")
            max_size_entry.delete(0, tk.END)
            max_size_entry.insert(0, "1.0")
        
        def remove_grain_size():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Selection Error", "Please select an item to remove.")
                return
                
            index = selection[0]
            listbox.delete(index)
            del self.data["grainSizeClass"][index]
        
        # Buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="Add Grain Size Class", command=add_grain_size).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Remove Selected", command=remove_grain_size).pack(side=tk.LEFT, padx=5)
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_control_buttons(self):
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Generate JSON", command=self.generate_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load from File", command=self.load_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Preview JSON", command=self.preview_json).pack(side=tk.LEFT, padx=5)
    
    def update_data(self):
        """Update the data dictionary with current form values"""
        self.data["catchment"]["name"] = self.catchment_name.get().strip()
        self.data["catchment"]["abbreviation"] = self.catchment_abbrev.get().strip()
    
    def generate_json(self):
        """Generate and display JSON in a new window"""
        self.update_data()
        
        # Create the final JSON structure with definitions
        json_data = {
            "catchment": self.data["catchment"],
            "HRU": self.data["HRU"],
            "landCoverType": self.data["landCoverType"],
            "bucket": self.data["bucket"],
            "grainSizeClass": self.data["grainSizeClass"],
            "defs": {
                "header": {
                    "type": "object",
                    "properties": {
                        "name": "string",
                        "abbreviation": "string"
                    }
                }
            }
        }
        
        # Display in new window
        json_window = tk.Toplevel(self.root)
        json_window.title("Generated JSON")
        json_window.geometry("600x500")
        
        text_widget = tk.Text(json_window, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(json_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        json_str = json.dumps(json_data, indent=2)
        text_widget.insert(tk.END, json_str)
        text_widget.config(state=tk.DISABLED)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def preview_json(self):
        """Preview the current JSON structure"""
        self.generate_json()
    
    def save_to_file(self):
        """Save JSON to file"""
        self.update_data()
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save JSON File"
        )
        
        if filename:
            try:
                json_data = {
                    "catchment": self.data["catchment"],
                    "HRU": self.data["HRU"],
                    "landCoverType": self.data["landCoverType"],
                    "bucket": self.data["bucket"],
                    "grainSizeClass": self.data["grainSizeClass"],
                    "defs": {
                        "header": {
                            "type": "object",
                            "properties": {
                                "name": "string",
                                "abbreviation": "string"
                            }
                        }
                    }
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Success", f"JSON file saved successfully to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
    
    def load_from_file(self):
        """Load JSON from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load JSON File"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Update internal data
                if "catchment" in loaded_data:
                    self.data["catchment"] = loaded_data["catchment"]
                    self.catchment_name.delete(0, tk.END)
                    self.catchment_name.insert(0, loaded_data["catchment"].get("name", ""))
                    self.catchment_abbrev.delete(0, tk.END)
                    self.catchment_abbrev.insert(0, loaded_data["catchment"].get("abbreviation", ""))
                
                for key in ["HRU", "landCoverType", "bucket", "grainSizeClass"]:
                    if key in loaded_data:
                        self.data[key] = loaded_data[key]
                
                messagebox.showinfo("Success", "JSON file loaded successfully!")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def clear_all(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all data?"):
            self.data = {
                "catchment": {"name": "", "abbreviation": ""},
                "HRU": [],
                "landCoverType": [],
                "bucket": [],
                "grainSizeClass": []
            }
            
            self.catchment_name.delete(0, tk.END)
            self.catchment_abbrev.delete(0, tk.END)
            
            messagebox.showinfo("Cleared", "All data has been cleared.")

def main():
    root = tk.Tk()
    app = JSONGeneratorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()