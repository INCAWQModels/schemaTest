#!/usr/bin/env python3
"""
Soil Temperature Time Series Calculator

This module calculates soil temperature time series using landCoverType-specific parameters 
from the catchment structure. Generates time series for each bucket in each landcover type.

Uses air temperature, snow depth, and various parameters to simulate soil temperature
dynamics based on thermal conductivity, heat capacity, and snow insulation effects.

Formula: delta_T = (D / 86400) * S * (K_t / 1.0e+06*(C_s * (Z_s**2))) * (T - T_s0)
Where: T_s = T_s0 + delta_T
"""

import os
import sys
import json
import csv
import datetime
import math
import uuid
import tkinter as tk
from tkinter import messagebox, filedialog

# Try to import project modules
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    timeseries_dir = os.path.join(project_root, 'code', 'timeSeries')
    if timeseries_dir not in sys.path:
        sys.path.insert(0, timeseries_dir)
    from timeSeries import TimeSeries
except ImportError:
    print("Warning: Could not import TimeSeries module. Using built-in fallback.")
    TimeSeries = None


class SimplifiedTimeSeries:
    """Simplified TimeSeries class for fallback use."""
    
    def __init__(self, name=None):
        self.data = []
        self.uuid = str(uuid.uuid4())
        self.columns = [self.uuid, "location"]
        self.metadata = {}
        self.metadata["uuid"] = self.uuid
        self.name = name
    
    def add_column(self, column_name):
        if column_name not in self.columns:
            self.columns.append(column_name)
            for row in self.data:
                if len(row) < len(self.columns):
                    row.extend([None] * (len(self.columns) - len(row)))
    
    def add_data(self, timestamp, location, values):
        if isinstance(values, dict):
            for col_name in values.keys():
                if col_name not in self.columns:
                    self.add_column(col_name)
            
            new_row = [None] * len(self.columns)
            new_row[0] = timestamp
            new_row[1] = location
            
            for col_name, value in values.items():
                col_index = self.columns.index(col_name)
                new_row[col_index] = value
        else:
            new_row = [timestamp, location] + list(values)
        
        self.data.append(new_row)
    
    def add_metadata(self, key, value):
        self.metadata[key] = value
    
    def save_to_files(self, name=None, output_dir=None):
        base_name = name or self.name
        if not base_name:
            raise ValueError("No name provided for output files")
        
        if output_dir:
            csv_filename = os.path.join(output_dir, f"{base_name}.csv")
            json_filename = os.path.join(output_dir, f"{base_name}.json")
        else:
            csv_filename = f"{base_name}.csv"
            json_filename = f"{base_name}.json"
        
        # Save data to CSV
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.columns)
            for row in self.data:
                formatted_row = []
                for i, value in enumerate(row):
                    if i == 0 and isinstance(value, datetime.datetime):
                        formatted_row.append(value.isoformat())
                    else:
                        formatted_row.append(value)
                writer.writerow(formatted_row)
        
        # Save metadata to JSON
        with open(json_filename, 'w') as jsonfile:
            json.dump(self.metadata, jsonfile, indent=4)
        
        return csv_filename, json_filename


def set_window_icon(root):
    """Set the tkinter window icon to INCAMan.png if available."""
    try:
        icon_paths = [
            "INCAMan.png",
            os.path.join(os.path.dirname(__file__), "INCAMan.png"),
            os.path.join(os.path.dirname(__file__), "..", "INCAMan.png"),
            os.path.join(os.path.dirname(__file__), "..", "..", "INCAMan.png")
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                icon = tk.PhotoImage(file=icon_path)
                root.iconphoto(False, icon)
                break
    except Exception:
        # If icon loading fails, continue without icon
        pass


def load_timeseries_from_files(csv_path, json_path):
    """Load a time series from CSV and JSON files."""
    # Load metadata from JSON
    try:
        with open(json_path, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print(f"Warning: JSON file {json_path} not found. Using defaults.")
        metadata = {}
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in {json_path}. Using defaults.")
        metadata = {}
    
    # Load data from CSV
    data = []
    columns = []
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            columns = next(reader)  # First row is header
            
            for row in reader:
                # Convert timestamp to datetime object
                timestamp_str = row[0]
                try:
                    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    # Try alternative parsing
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                
                # Convert numeric values
                processed_row = [timestamp]
                for i, value in enumerate(row[1:], 1):
                    if i == 1:  # Location column
                        processed_row.append(value)
                    else:
                        try:
                            processed_row.append(float(value) if value else None)
                        except ValueError:
                            processed_row.append(value)
                
                data.append(processed_row)
    
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file {csv_path} not found")
    
    # Create TimeSeries object
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    ts = TSClass()
    ts.columns = columns
    ts.data = data
    ts.metadata = metadata
    
    return ts


def simulate_soil_temperature(
    input_timeseries,
    T_0=5.0,        # Initial soil temperature (°C)
    C_s=1.3,        # Soil heat capacity (J/m³/K)
    K_t=0.63,       # Thermal conductivity (W/m/K)
    f_s=-3.3,       # Snow damping factor
    Z_s=0.5,        # Soil depth (m)
    receives_precipitation=True,  # Whether bucket receives precipitation
    timestep_seconds=86400,       # Timestep in seconds
    temp_column="air_temperature",
    snow_column="snowpack_depth"
):
    """
    Simulate soil temperature time series for a single bucket.
    
    Parameters:
    input_timeseries: TimeSeries object with air temperature and snow depth data
    T_0: Initial soil temperature (°C)
    C_s: Soil heat capacity (J/m³/K) 
    K_t: Thermal conductivity (W/m/K)
    f_s: Snow damping factor
    Z_s: Soil depth (m)
    receives_precipitation: Boolean flag for precipitation reception
    timestep_seconds: Timestep scaling factor
    temp_column: Name of temperature column
    snow_column: Name of snow depth column
    
    Returns:
    TimeSeries object with soil temperature values
    """
    
    # Use TimeSeries class if available, otherwise use simplified version
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create output TimeSeries
    output_ts = TSClass("Soil_Temperature")
    output_ts.add_column("soil_temperature_c")
    
    # Copy metadata from input time series
    for key, value in input_timeseries.metadata.items():
        output_ts.add_metadata(key, value)
    
    # Add soil temperature specific metadata
    output_ts.add_metadata("calculation_method", "Thermal conductivity model")
    output_ts.add_metadata("initial_temperature", str(T_0))
    output_ts.add_metadata("thermal_conductivity", str(K_t))
    output_ts.add_metadata("specific_heat_capacity", str(C_s))
    output_ts.add_metadata("snow_depth_factor", str(f_s))
    output_ts.add_metadata("effective_depth", str(Z_s))
    output_ts.add_metadata("receives_precipitation", str(receives_precipitation))
    output_ts.add_metadata("timestep_seconds", str(timestep_seconds))
    output_ts.add_metadata("generation_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Find column indices
    try:
        temp_idx = input_timeseries.columns.index(temp_column)
        snow_idx = input_timeseries.columns.index(snow_column)
        timestamp_idx = 0  # First column is always timestamp
        location_idx = 1   # Second column is always location
    except ValueError as e:
        raise ValueError(f"Required column not found: {e}")
    
    # Initialize soil temperature
    T_s0 = T_0
    
    # Scaling factor
    D = timestep_seconds
    
    # Process each data point
    for row in input_timeseries.data:
        timestamp = row[timestamp_idx]
        location = row[location_idx]
        
        # Get air temperature and snow depth
        T = row[temp_idx] if len(row) > temp_idx and row[temp_idx] is not None else 0.0
        z = row[snow_idx] if len(row) > snow_idx and row[snow_idx] is not None else 0.0
        
        # Calculate snow insulation factor
        if receives_precipitation:
            S = math.exp(f_s * z)
        else:
            S = 1.0
        
        # Calculate change in soil temperature
        # delta_T = (D / 86400) * S * (K_t / 1.0e+06*(C_s * (Z_s**2))) * (T - T_s0)
        delta_T = (D / 86400.0) * S * (K_t / (1.0e+06 * C_s * (Z_s**2))) * (T - T_s0)
        
        # Update soil temperature
        T_s = T_s0 + delta_T
        
        # Add to output time series
        output_ts.add_data(timestamp, location, {"soil_temperature_c": T_s})
        
        # Update previous temperature for next iteration
        T_s0 = T_s
    
    return output_ts


def calculate_soil_temperature_for_landcover(input_timeseries, landcover_params, bucket_params, timestep_seconds):
    """
    Calculate soil temperature time series for all buckets in a landcover type.
    
    Parameters:
    input_timeseries: TimeSeries with air temperature and snow data
    landcover_params: Dict with landcover-level soil temperature parameters
    bucket_params: List of dicts with bucket-level parameters
    timestep_seconds: Timestep scaling factor
    
    Returns:
    Dict of {bucket_name: TimeSeries} with soil temperature data
    """
    
    # Extract landcover parameters
    K_t = landcover_params.get("thermalConductivity", 0.63)
    C_s = landcover_params.get("specificHeatFreezeThaw", 1.3)
    f_s = landcover_params.get("snowDepthFactor", -3.3)
    
    results = {}
    
    # Process each bucket
    for bucket in bucket_params:
        bucket_name = bucket.get("name", "Unknown")
        
        # Extract bucket parameters
        soil_temp_params = bucket.get("soilTemperature", {})
        T_0 = soil_temp_params.get("curentTemperature", 5.0)  # Note: JSON has typo "curent"
        Z_s = soil_temp_params.get("effectiveDepth", 0.5)
        receives_precipitation = bucket.get("receivesPrecipitation", True)
        
        # Calculate soil temperature for this bucket
        bucket_ts = simulate_soil_temperature(
            input_timeseries=input_timeseries,
            T_0=T_0,
            C_s=C_s,
            K_t=K_t,
            f_s=f_s,
            Z_s=Z_s,
            receives_precipitation=receives_precipitation,
            timestep_seconds=timestep_seconds
        )
        
        # Update metadata with bucket-specific info
        bucket_ts.add_metadata("bucket_name", bucket_name)
        bucket_ts.add_metadata("bucket_abbreviation", bucket.get("abbreviation", ""))
        
        results[bucket_name] = bucket_ts
    
    return results


def main_gui():
    """Main GUI application for soil temperature calculation."""
    root = tk.Tk()
    root.title("Soil Temperature Time Series Calculator")
    root.geometry("600x500")
    
    # Set window icon
    set_window_icon(root)
    
    # Variables
    rain_snow_file = tk.StringVar()
    catchment_file = tk.StringVar()
    output_dir = tk.StringVar(value=".")
    
    def browse_rain_snow():
        filename = filedialog.askopenfilename(
            title="Select Rain and Snow CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            rain_snow_file.set(filename)
    
    def browse_catchment():
        filename = filedialog.askopenfilename(
            title="Select Catchment JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            catchment_file.set(filename)
    
    def browse_output():
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            output_dir.set(dirname)
    
    def calculate():
        try:
            # Validate inputs
            if not rain_snow_file.get():
                messagebox.showerror("Error", "Please select a rain and snow CSV file")
                return
            
            if not catchment_file.get():
                messagebox.showerror("Error", "Please select a catchment JSON file")
                return
            
            # Load the rain and snow time series
            csv_path = rain_snow_file.get()
            json_path = csv_path.replace('.csv', '.json')
            
            if not os.path.exists(json_path):
                messagebox.showerror("Error", f"JSON file not found: {json_path}")
                return
            
            input_ts = load_timeseries_from_files(csv_path, json_path)
            
            # Load catchment data
            with open(catchment_file.get(), 'r') as f:
                catchment_data = json.load(f)
            
            # Get timestep from metadata
            timestep_seconds = input_ts.metadata.get("timestep_seconds", 86400)
            
            # Extract location and landcover from the filename or data
            location = input_ts.metadata.get("hru_name", "Unknown")
            landcover_name = input_ts.metadata.get("land_cover_type", "Unknown")
            
            # Find the corresponding HRU and landcover in catchment data
            hru_data = None
            for hru in catchment_data.get("HRUs", []):
                if hru.get("name") == location:
                    hru_data = hru
                    break
            
            if not hru_data:
                messagebox.showerror("Error", f"HRU '{location}' not found in catchment data")
                return
            
            # Find the landcover type
            landcover_data = None
            landcover_types = hru_data.get("subcatchment", {}).get("landCoverTypes", [])
            for lc in landcover_types:
                if lc.get("name") == landcover_name:
                    landcover_data = lc
                    break
            
            if not landcover_data:
                messagebox.showerror("Error", f"Landcover '{landcover_name}' not found for HRU '{location}'")
                return
            
            # Extract parameters
            soil_temp_params = landcover_data.get("soilTemperature", {})
            bucket_params = landcover_data.get("buckets", [])
            
            if not bucket_params:
                messagebox.showerror("Error", f"No buckets found for landcover '{landcover_name}'")
                return
            
            # Calculate soil temperature for all buckets
            results = calculate_soil_temperature_for_landcover(
                input_ts, soil_temp_params, bucket_params, timestep_seconds
            )
            
            # Save results
            saved_files = []
            for bucket_name, ts in results.items():
                # Create filename
                safe_location = location.replace(" ", "_")
                safe_landcover = landcover_name.replace(" ", "_")
                safe_bucket = bucket_name.replace(" ", "_")
                base_name = f"{safe_location}_{safe_landcover}_{safe_bucket}_soilTemperature"
                
                # Save files
                csv_file, json_file = ts.save_to_files(base_name, output_dir.get())
                saved_files.extend([csv_file, json_file])
            
            # Show success message
            messagebox.showinfo("Success", 
                f"Soil temperature calculated successfully!\n\n"
                f"Generated {len(results)} bucket time series.\n"
                f"Files saved to: {output_dir.get()}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed: {str(e)}")
    
    # Create GUI
    tk.Label(root, text="Soil Temperature Time Series Calculator", 
             font=("Arial", 14, "bold")).pack(pady=10)
    
    # Rain and snow file selection
    frame1 = tk.Frame(root)
    frame1.pack(fill="x", padx=20, pady=5)
    tk.Label(frame1, text="Rain and Snow CSV File:").pack(anchor="w")
    entry_frame1 = tk.Frame(frame1)
    entry_frame1.pack(fill="x", pady=2)
    tk.Entry(entry_frame1, textvariable=rain_snow_file).pack(side="left", fill="x", expand=True)
    tk.Button(entry_frame1, text="Browse", command=browse_rain_snow).pack(side="right", padx=(5,0))
    
    # Catchment file selection
    frame2 = tk.Frame(root)
    frame2.pack(fill="x", padx=20, pady=5)
    tk.Label(frame2, text="Catchment JSON File:").pack(anchor="w")
    entry_frame2 = tk.Frame(frame2)
    entry_frame2.pack(fill="x", pady=2)
    tk.Entry(entry_frame2, textvariable=catchment_file).pack(side="left", fill="x", expand=True)
    tk.Button(entry_frame2, text="Browse", command=browse_catchment).pack(side="right", padx=(5,0))
    
    # Output directory selection
    frame3 = tk.Frame(root)
    frame3.pack(fill="x", padx=20, pady=5)
    tk.Label(frame3, text="Output Directory:").pack(anchor="w")
    entry_frame3 = tk.Frame(frame3)
    entry_frame3.pack(fill="x", pady=2)
    tk.Entry(entry_frame3, textvariable=output_dir).pack(side="left", fill="x", expand=True)
    tk.Button(entry_frame3, text="Browse", command=browse_output).pack(side="right", padx=(5,0))
    
    # Calculate button
    tk.Button(root, text="Calculate Soil Temperature", command=calculate,
              bg="lightblue", font=("Arial", 12)).pack(pady=20)
    
    # Information text
    info_text = tk.Text(root, height=8, width=70, wrap="word")
    info_text.pack(fill="both", expand=True, padx=20, pady=10)
    
    info_content = """Soil Temperature Calculator Information:

1. Select a rain and snow CSV file (contains air temperature and snow depth data)
2. Select the corresponding catchment JSON file (contains soil temperature parameters)
3. Choose output directory for generated files
4. Click 'Calculate Soil Temperature' to generate time series

The calculator will generate soil temperature time series for each bucket in the landcover type,
using thermal conductivity models with snow insulation effects.

Parameters used:
- thermalConductivity, specificHeatFreezeThaw, snowDepthFactor (from landcover)
- currentTemperature, effectiveDepth, receivesPrecipitation (from buckets)"""
    
    info_text.insert("1.0", info_content)
    info_text.config(state="disabled")
    
    root.mainloop()


def test_soil_temperature_calculation():
    """Test function to demonstrate soil temperature calculation."""
    print("Testing soil temperature calculation...")
    
    # Create sample data
    start_date = datetime.datetime(2024, 1, 1, 0, 0, 0)
    
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create input time series with temperature and snow data
    input_ts = TSClass("Test_Input")
    input_ts.add_column("air_temperature")
    input_ts.add_column("snowpack_depth")
    input_ts.add_metadata("timestep_seconds", "86400")
    
    # Add sample data for 10 days
    temperatures = [5.0, 3.0, -2.0, -5.0, -3.0, 0.0, 2.0, 8.0, 12.0, 15.0]
    snow_depths = [0.0, 0.5, 1.0, 1.5, 2.0, 1.8, 1.2, 0.8, 0.3, 0.0]
    
    for i in range(10):
        current_date = start_date + datetime.timedelta(days=i)
        input_ts.add_data(current_date, "TestLocation", {
            "air_temperature": temperatures[i],
            "snowpack_depth": snow_depths[i]
        })
    
    # Test with sample parameters
    soil_ts = simulate_soil_temperature(
        input_timeseries=input_ts,
        T_0=5.0,           # Initial temperature
        C_s=1.3,           # Heat capacity
        K_t=0.63,          # Thermal conductivity
        f_s=-3.3,          # Snow factor
        Z_s=0.5,           # Soil depth
        receives_precipitation=True,
        timestep_seconds=86400
    )
    
    print(f"\n{'Date':>12} {'Air T(°C)':>10} {'Snow(mm)':>10} {'Soil T(°C)':>12}")
    print("-" * 50)
    
    for i, row in enumerate(soil_ts.data):
        timestamp = row[0]
        soil_temp = row[2]  # Soil temperature is in third column
        air_temp = temperatures[i]
        snow_depth = snow_depths[i]
        
        print(f"{timestamp.strftime('%Y-%m-%d'):>12} {air_temp:>10.1f} {snow_depth:>10.1f} {soil_temp:>12.3f}")
    
    # Save example
    csv_file, json_file = soil_ts.save_to_files("test_soil_temperature")
    print(f"\nSaved test calculation to: {csv_file}")
    
    return soil_ts


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test
        test_soil_temperature_calculation()
    else:
        # Run GUI
        main_gui()
