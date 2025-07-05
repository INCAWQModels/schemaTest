#!/usr/bin/env python3
"""
Time Series Data Viewer

A tkinter application for displaying time series data from CSV files.
Uses matplotlib for plotting and standard library for most functionality.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import csv
from datetime import datetime
from collections import defaultdict
import sys

# Try to import matplotlib for plotting
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class TimeSeriesViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Time Series Data Viewer")
        self.root.geometry("1000x700")
        
        # Try to set the window icon
        self.set_window_icon()
        
        # Data storage
        self.csv_files = []
        self.all_series_data = {}  # {series_name: [(datetime, value), ...]}
        self.unique_series = set()
        
        self.create_widgets()
        
        if not HAS_MATPLOTLIB:
            messagebox.showwarning("Warning", 
                "Matplotlib not available. Plotting functionality will be limited.\n"
                "Please install matplotlib for full functionality: pip install matplotlib")
    
    def set_window_icon(self):
        """Set the window icon to INCAMan.png if available."""
        try:
            # Try to find INCAMan.png in common locations
            icon_paths = [
                "INCAMan.png",
                os.path.join(os.path.dirname(__file__), "INCAMan.png"),
                os.path.join(os.path.dirname(__file__), "..", "INCAMan.png"),
                os.path.join(os.getcwd(), "INCAMan.png")
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    icon = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(False, icon)
                    break
        except Exception as e:
            # If anything fails with the icon, just continue
            print(f"Could not load icon: {e}")
    
    def create_widgets(self):
        """Create the main interface widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Folder selection
        ttk.Label(main_frame, text="1. Select Folder:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_var = tk.StringVar()
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state="readonly")
        self.folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.select_folder).grid(row=0, column=1)
        
        # CSV file selection
        ttk.Label(main_frame, text="2. Select CSV Files:").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        csv_frame = ttk.Frame(main_frame)
        csv_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 5))
        csv_frame.columnconfigure(0, weight=1)
        
        # CSV listbox with scrollbar
        csv_list_frame = ttk.Frame(csv_frame)
        csv_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        csv_list_frame.columnconfigure(0, weight=1)
        
        self.csv_listbox = tk.Listbox(csv_list_frame, selectmode=tk.MULTIPLE, height=4)
        self.csv_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        csv_scrollbar = ttk.Scrollbar(csv_list_frame, orient=tk.VERTICAL, command=self.csv_listbox.yview)
        csv_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.csv_listbox.configure(yscrollcommand=csv_scrollbar.set)
        
        ttk.Button(csv_frame, text="Load Selected Files", command=self.load_csv_files).grid(row=1, column=0, pady=(5, 0))
        
        # Series selection
        ttk.Label(main_frame, text="3. Select Time Series:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        series_frame = ttk.Frame(main_frame)
        series_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 5))
        series_frame.columnconfigure(0, weight=1)
        
        # Series listbox with scrollbar
        series_list_frame = ttk.Frame(series_frame)
        series_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        series_list_frame.columnconfigure(0, weight=1)
        
        self.series_listbox = tk.Listbox(series_list_frame, selectmode=tk.MULTIPLE, height=4)
        self.series_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        series_scrollbar = ttk.Scrollbar(series_list_frame, orient=tk.VERTICAL, command=self.series_listbox.yview)
        series_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.series_listbox.configure(yscrollcommand=series_scrollbar.set)
        
        # Buttons frame
        button_frame = ttk.Frame(series_frame)
        button_frame.grid(row=1, column=0, pady=(5, 0))
        
        ttk.Button(button_frame, text="Plot Selected Series", command=self.plot_series).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(button_frame, text="Show Data Summary", command=self.show_data_summary).grid(row=0, column=1)
        
        # Plot area
        self.plot_frame = ttk.Frame(main_frame)
        self.plot_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.plot_frame.columnconfigure(0, weight=1)
        self.plot_frame.rowconfigure(0, weight=1)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready - Select a folder to begin")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def select_folder(self):
        """Open folder selection dialog."""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_var.set(folder_path)
            self.find_csv_files(folder_path)
    
    def find_csv_files(self, folder_path):
        """Find all CSV files in the selected folder."""
        try:
            csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
            
            # Clear and populate the CSV listbox
            self.csv_listbox.delete(0, tk.END)
            for csv_file in csv_files:
                self.csv_listbox.insert(tk.END, csv_file)
            
            self.status_var.set(f"Found {len(csv_files)} CSV files in folder")
            
            # Clear previous data
            self.clear_data()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error reading folder: {str(e)}")
            self.status_var.set("Error reading folder")
    
    def clear_data(self):
        """Clear all loaded data."""
        self.csv_files = []
        self.all_series_data = {}
        self.unique_series = set()
        self.series_listbox.delete(0, tk.END)
        
        # Clear plot area
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
    
    def load_csv_files(self):
        """Load selected CSV files and extract time series data."""
        selected_indices = self.csv_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select one or more CSV files to load.")
            return
        
        folder_path = self.folder_var.get()
        if not folder_path:
            messagebox.showwarning("Warning", "Please select a folder first.")
            return
        
        self.clear_data()
        
        # Get selected files
        selected_files = [self.csv_listbox.get(i) for i in selected_indices]
        
        try:
            for csv_file in selected_files:
                file_path = os.path.join(folder_path, csv_file)
                self.load_single_csv(file_path)
            
            # Update series listbox
            self.update_series_listbox()
            
            self.status_var.set(f"Loaded {len(selected_files)} files with {len(self.unique_series)} unique time series")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading CSV files: {str(e)}")
            self.status_var.set("Error loading files")
    
    def load_single_csv(self, file_path):
        """Load a single CSV file and extract time series data."""
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Try to detect the dialect
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # Use csv.Sniffer to detect delimiter
            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.reader(csvfile, dialect)
            except:
                # Fallback to comma-separated
                reader = csv.reader(csvfile)
            
            # Read all rows
            rows = list(reader)
            
            if len(rows) < 2:
                return  # Skip files with insufficient data
            
            # Determine if first row is header
            first_row = rows[0]
            has_header = self.detect_header(first_row)
            
            # Process data rows
            data_start = 1 if has_header else 0
            
            for row in rows[data_start:]:
                if len(row) < 3:  # Need at least timestamp, location, and one value
                    continue
                
                try:
                    # Parse timestamp (first column)
                    timestamp_str = row[0].strip()
                    timestamp = self.parse_timestamp(timestamp_str)
                    
                    # Get location (second column)
                    location = row[1].strip()
                    
                    # Process numeric columns (third column onwards)
                    for col_idx in range(2, len(row)):
                        try:
                            value = float(row[col_idx])
                            
                            # Create series name
                            if has_header and len(first_row) > col_idx:
                                series_name = f"{location}_{first_row[col_idx].strip()}"
                            else:
                                series_name = f"{location}_column_{col_idx}"
                            
                            # Store the data
                            if series_name not in self.all_series_data:
                                self.all_series_data[series_name] = []
                            
                            self.all_series_data[series_name].append((timestamp, value))
                            self.unique_series.add(series_name)
                            
                        except ValueError:
                            # Skip non-numeric values
                            continue
                            
                except Exception as e:
                    # Skip problematic rows
                    print(f"Skipping row: {row}, Error: {e}")
                    continue
        
        # Sort data by timestamp for each series
        for series_name in self.all_series_data:
            self.all_series_data[series_name].sort(key=lambda x: x[0])
    
    def detect_header(self, first_row):
        """Simple heuristic to detect if first row is a header."""
        # If first column looks like a timestamp, probably not a header
        try:
            self.parse_timestamp(first_row[0])
            return False
        except:
            # If we can't parse it as a timestamp, might be a header
            return True
    
    def parse_timestamp(self, timestamp_str):
        """Parse timestamp string into datetime object."""
        # Common timestamp formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d",
            "%H:%M:%S"  # Time only
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # If no format matches, raise an error
        raise ValueError(f"Unable to parse timestamp: {timestamp_str}")
    
    def update_series_listbox(self):
        """Update the series selection listbox."""
        self.series_listbox.delete(0, tk.END)
        
        # Sort series names for better presentation
        sorted_series = sorted(self.unique_series)
        
        for series_name in sorted_series:
            self.series_listbox.insert(tk.END, series_name)
    
    def plot_series(self):
        """Plot the selected time series."""
        if not HAS_MATPLOTLIB:
            messagebox.showerror("Error", "Matplotlib is required for plotting. Please install it: pip install matplotlib")
            return
        
        selected_indices = self.series_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select one or more time series to plot.")
            return
        
        # Get selected series names
        selected_series = [self.series_listbox.get(i) for i in selected_indices]
        
        # Clear previous plot
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        
        # Create matplotlib figure
        fig = Figure(figsize=(10, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Plot each selected series
        for series_name in selected_series:
            if series_name in self.all_series_data:
                data = self.all_series_data[series_name]
                timestamps = [point[0] for point in data]
                values = [point[1] for point in data]
                
                ax.plot(timestamps, values, label=series_name, marker='o', markersize=2)
        
        # Configure plot
        ax.set_xlabel('Time')
        ax.set_ylabel('Value')
        ax.set_title('Time Series Data')
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        # Format x-axis dates with intelligent spacing
        if len(selected_series) > 0 and self.all_series_data[selected_series[0]]:
            # Get the time range to determine appropriate formatting
            all_timestamps = []
            for series_name in selected_series:
                if series_name in self.all_series_data:
                    timestamps = [point[0] for point in self.all_series_data[series_name]]
                    all_timestamps.extend(timestamps)
            
            if all_timestamps:
                time_range = max(all_timestamps) - min(all_timestamps)
                
                # Choose appropriate date formatting and locator based on time range
                if time_range.days <= 7:  # Week or less
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
                    ax.xaxis.set_major_locator(mdates.DayLocator())
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
                elif time_range.days <= 31:  # Month or less
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, time_range.days // 10)))
                elif time_range.days <= 365:  # Year or less
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    ax.xaxis.set_major_locator(mdates.MonthLocator())
                    ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
                else:  # More than a year
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, time_range.days // 365)))
                    ax.xaxis.set_minor_locator(mdates.MonthLocator())
                
                # Auto-format dates and rotate labels for better readability
                fig.autofmt_xdate(rotation=45)
                
                # Set maximum number of ticks to prevent overcrowding
                ax.xaxis.set_major_locator(plt.MaxNLocator(nbins=10))
                
                # Ensure labels don't overlap by adjusting spacing
                for label in ax.get_xticklabels():
                    label.set_horizontalalignment('right')
        
        # Adjust layout to prevent legend cutoff
        fig.tight_layout()
        
        # Add plot to tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Add navigation toolbar
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar = NavigationToolbar2Tk(canvas, self.plot_frame)
            toolbar.update()
        except ImportError:
            pass
        
        self.status_var.set(f"Plotted {len(selected_series)} time series")
    
    def show_data_summary(self):
        """Show a summary of the loaded data."""
        if not self.all_series_data:
            messagebox.showinfo("No Data", "No time series data loaded.")
            return
        
        # Create summary window
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Data Summary")
        summary_window.geometry("600x400")
        
        # Try to set icon for summary window too
        try:
            summary_window.iconphoto(False, self.root.iconphoto())
        except:
            pass
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(summary_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Generate summary text
        summary = f"Data Summary\n{'='*50}\n\n"
        summary += f"Total time series: {len(self.unique_series)}\n\n"
        
        for series_name in sorted(self.unique_series):
            data = self.all_series_data[series_name]
            if data:
                values = [point[1] for point in data]
                start_time = min(point[0] for point in data)
                end_time = max(point[0] for point in data)
                
                summary += f"Series: {series_name}\n"
                summary += f"  Data points: {len(data)}\n"
                summary += f"  Time range: {start_time} to {end_time}\n"
                summary += f"  Value range: {min(values):.3f} to {max(values):.3f}\n"
                summary += f"  Mean value: {sum(values)/len(values):.3f}\n\n"
        
        text_widget.insert(tk.END, summary)
        text_widget.configure(state=tk.DISABLED)

def main():
    """Main function to run the application."""
    root = tk.Tk()
    app = TimeSeriesViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()