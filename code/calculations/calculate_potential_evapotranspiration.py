#!/usr/bin/env python3
"""
Enhanced Potential Evapotranspiration Calculator

This module calculates PET using landCoverType-specific parameters from the catchment structure.
Uses the Jensen-Haise method with parameters from the evaporation section of each landCoverType:
- solarRadiationScalingFactor (replaces ct coefficient)
- growingDegreeOffset (replaces jh_offset)

Formula: PET = Rs * (1/solarRadiationScalingFactor) * (T + growingDegreeOffset) * (timestep_seconds/86400)

The timestep scaling factor is obtained from the JSON metadata associated with the temperature
and precipitation time series to ensure proper units for different timesteps.
"""

import os
import sys
import json
import csv
import datetime
import math
import uuid
import tkinter as tk

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
    # Use TimeSeries class if available, otherwise use simplified version
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Load metadata
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"Warning: Could not load metadata from {json_path}: {e}")
        metadata = {}
    
    # Create TimeSeries object
    ts = TSClass()
    
    # Add metadata
    for key, value in metadata.items():
        ts.add_metadata(key, value)
    
    # Load CSV data
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Add columns (skip first two which are timestamp and location)
            for col_name in header[2:]:
                ts.add_column(col_name)
            
            # Load data
            for row in reader:
                if len(row) >= 3:
                    # Parse timestamp
                    timestamp_str = row[0]
                    try:
                        # Handle both ISO format and UUID columns
                        if len(timestamp_str) > 20:  # Likely a timestamp
                            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('T', ' '))
                        else:
                            continue  # Skip UUID rows
                    except ValueError:
                        continue  # Skip invalid timestamps
                    
                    location = row[1]
                    
                    # Parse data values
                    values = {}
                    for i, col_name in enumerate(header[2:], 2):
                        if i < len(row):
                            try:
                                values[col_name] = float(row[i]) if row[i] else None
                            except ValueError:
                                values[col_name] = None
                    
                    ts.add_data(timestamp, location, values)
    
    except Exception as e:
        print(f"Error loading CSV data from {csv_path}: {e}")
        return None
    
    return ts


def get_timestep_seconds_from_timeseries(temp_ts, solar_ts):
    """
    Extract timestep_seconds from time series metadata to calculate the timestep scaling factor.
    
    Parameters:
    temp_ts: Temperature time series object
    solar_ts: Solar radiation time series object
    
    Returns:
    float: Timestep scaling factor (timestep_seconds / 86400)
    """
    timestep_seconds = None
    
    # Try to get timestep_seconds from temperature time series metadata
    if hasattr(temp_ts, 'metadata') and 'timestep_seconds' in temp_ts.metadata:
        timestep_seconds = temp_ts.metadata['timestep_seconds']
    # Try solar radiation time series metadata
    elif hasattr(solar_ts, 'metadata') and 'timestep_seconds' in solar_ts.metadata:
        timestep_seconds = solar_ts.metadata['timestep_seconds']
    
    # If found, calculate scaling factor
    if timestep_seconds is not None:
        try:
            timestep_seconds = float(timestep_seconds)
            scaling_factor = timestep_seconds / 86400.0  # 86400 seconds in a day
            print(f"Found timestep_seconds: {timestep_seconds}, scaling factor: {scaling_factor:.6f}")
            return scaling_factor
        except (ValueError, ZeroDivisionError):
            print(f"Warning: Invalid timestep_seconds value: {timestep_seconds}")
    
    # Default to 1.0 (daily timestep) if not found
    print("Warning: timestep_seconds not found in metadata, assuming daily timestep (scaling factor = 1.0)")
    return 1.0


def calculate_pet_with_landcover_params(solar_ts, temp_ts, landcover_params,
                                      solar_column="solar_radiation", temp_column="temperature_c"):
    """
    Calculate potential evapotranspiration using landcover-specific parameters
    and timestep scaling from JSON metadata.
    
    This function implements the enhanced Jensen-Haise equation:
    PET = Rs * (1/solarRadiationScalingFactor) * max(0, T + growingDegreeOffset) * (timestep_seconds/86400)
    
    Where the timestep scaling factor is extracted from the time series metadata.
    
    Parameters:
    solar_ts: TimeSeries object containing solar radiation data
    temp_ts: TimeSeries object containing temperature data  
    landcover_params: Dictionary containing landcover-specific parameters
    solar_column: Name of solar radiation column in solar_ts
    temp_column: Name of temperature column in temp_ts
    
    Returns:
    TimeSeries object with PET values scaled for the appropriate timestep
    """
    # Extract parameters with defaults
    solar_scaling = landcover_params.get('solarRadiationScalingFactor', 60.0)  # Default from Jensen-Haise
    degree_offset = landcover_params.get('growingDegreeOffset', 0.0)          # Default offset
    
    # Get timestep scaling factor from metadata
    timestep_scaling = get_timestep_seconds_from_timeseries(temp_ts, solar_ts)
    
    print(f"PET calculation parameters:")
    print(f"  - Solar radiation scaling factor: {solar_scaling}")
    print(f"  - Growing degree offset: {degree_offset}")
    print(f"  - Timestep scaling factor: {timestep_scaling:.6f}")
    
    # Create output time series
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    output_ts = TSClass(f"PET_{landcover_params.get('name', 'Unknown')}")
    output_ts.add_column("pet_mm_timestep")  # Updated column name to reflect units
    
    # Copy relevant metadata from source time series
    if hasattr(solar_ts, 'metadata'):
        for key, value in solar_ts.metadata.items():
            output_ts.add_metadata(key, value)
    
    # Add PET-specific metadata
    output_ts.add_metadata("calculation_method", "Enhanced Jensen-Haise with timestep scaling")
    output_ts.add_metadata("solar_scaling_factor", solar_scaling)
    output_ts.add_metadata("growing_degree_offset", degree_offset)
    output_ts.add_metadata("timestep_scaling_factor", timestep_scaling)
    output_ts.add_metadata("pet_units", "mm per timestep")
    output_ts.add_metadata("pet_formula", "Rs * (1/solar_scaling) * max(0, T + offset) * (timestep_s/86400)")
    
    # Find column indices
    solar_idx = None
    timestamp_idx_solar = 0
    location_idx_solar = 1
    
    if hasattr(solar_ts, 'columns'):
        try:
            solar_idx = solar_ts.columns.index(solar_column)
        except ValueError:
            print(f"Warning: Solar column '{solar_column}' not found. Available columns: {solar_ts.columns}")
            return output_ts
    else:
        solar_idx = 2  # Assume third column
    
    # Build temperature lookup table
    temp_lookup = {}
    temp_idx = None
    if hasattr(temp_ts, 'columns'):
        try:
            temp_idx = temp_ts.columns.index(temp_column)
        except ValueError:
            print(f"Warning: Temperature column '{temp_column}' not found. Available columns: {temp_ts.columns}")
            return output_ts
    else:
        temp_idx = 2  # Assume third column
    
    for row in temp_ts.data:
        if len(row) > temp_idx:
            timestamp = row[0]
            location = row[1]
            temperature = row[temp_idx]
            key = (timestamp, location)
            temp_lookup[key] = temperature
    
    # Process each solar radiation data point
    for row in solar_ts.data:
        timestamp = row[timestamp_idx_solar]
        location = row[location_idx_solar]
        solar_radiation = row[solar_idx] if len(row) > solar_idx else None
        
        # Look up corresponding temperature
        key = (timestamp, location)
        temperature = temp_lookup.get(key)
        
        # Calculate PET if both values are available
        if solar_radiation is not None and temperature is not None:
            # Convert solar radiation from W/m² to MJ/m²/day
            rs = solar_radiation * 0.0864
            
            # Calculate adjusted temperature
            adjusted_temp = temperature + degree_offset
            
            # Calculate PET using modified Jensen-Haise equation
            # PET = Rs * (1/solarRadiationScalingFactor) * (T + growingDegreeOffset)
            # BUT: Use 0 when (T + growingDegreeOffset) <= 0
            if adjusted_temp <= 0.0:
                pet_daily = 0.0
            else:
                pet_daily = rs * (1.0 / solar_scaling) * adjusted_temp
            
            # Apply timestep scaling to convert from mm/day to mm/timestep
            pet = pet_daily * timestep_scaling
            
            # Ensure PET is non-negative (additional safety check)
            pet = max(0.0, pet)
            
        else:
            pet = None
        
        # Add to output time series
        output_ts.add_data(timestamp, location, {"pet_mm_timestep": pet})
    
    return output_ts


def test_pet_calculation():
    """Test function to demonstrate PET calculation with timestep scaling."""
    print("Testing PET calculation with landcover parameters and timestep scaling...")
    
    # Create sample solar radiation data
    start_date = datetime.datetime(2024, 6, 21, 12, 0, 0)  # Summer solstice, noon
    
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Solar radiation time series
    solar_ts = TSClass("Test_Solar")
    solar_ts.add_column("solar_radiation")
    solar_ts.add_metadata("latitude", "45.0")
    solar_ts.add_metadata("longitude", "15.0")
    solar_ts.add_metadata("timestep_seconds", 86400)  # Daily timestep
    
    # Temperature time series  
    temp_ts = TSClass("Test_Temperature")
    temp_ts.add_column("temperature_c")
    temp_ts.add_metadata("timestep_seconds", 86400)  # Daily timestep
    
    # Add sample data for 5 days with varying temperatures (including cold)
    for i in range(5):
        current_date = start_date + datetime.timedelta(days=i)
        solar_rad = 300.0 + i * 10  # Varying solar radiation
        temperature = -2.0 + i * 4   # Temperature from -2°C to 14°C
        
        solar_ts.add_data(current_date, "TestLocation", {"solar_radiation": solar_rad})
        temp_ts.add_data(current_date, "TestLocation", {"temperature_c": temperature})
    
    # Test with different landcover parameters and timesteps
    test_params = [
        {"name": "Forest", "solarRadiationScalingFactor": 60.0, "growingDegreeOffset": 0.0},
        {"name": "Agriculture", "solarRadiationScalingFactor": 80.0, "growingDegreeOffset": 2.0},
        {"name": "Cold_Climate", "solarRadiationScalingFactor": 40.0, "growingDegreeOffset": -3.0}
    ]
    
    # Test different timesteps
    test_timesteps = [86400, 3600, 43200]  # Daily, hourly, 12-hourly
    timestep_names = ["Daily (86400s)", "Hourly (3600s)", "12-Hourly (43200s)"]
    
    print(f"\n{'Date':>12} {'Solar(W/m²)':>12} {'Temp(°C)':>10} {'LandCover':>12} {'Timestep':>15} {'Scaling':>10} {'PET':>12}")
    print("-" * 110)
    
    for timestep, timestep_name in zip(test_timesteps, timestep_names):
        # Update timestep in metadata
        solar_ts.add_metadata("timestep_seconds", timestep)
        temp_ts.add_metadata("timestep_seconds", timestep)
        
        for params in test_params:
            pet_ts = calculate_pet_with_landcover_params(solar_ts, temp_ts, params)
            
            for i, row in enumerate(pet_ts.data):
                if i >= 3:  # Only show first 3 rows for brevity
                    break
                    
                timestamp = row[0]
                pet_value = row[2]  # PET is in third column
                solar_value = solar_ts.data[i][2]
                temp_value = temp_ts.data[i][2]
                scaling_factor = timestep / 86400.0
                
                print(f"{timestamp.strftime('%Y-%m-%d'):>12} {solar_value:>12.1f} {temp_value:>10.1f} "
                      f"{params['name']:>12} {timestep_name:>15} {scaling_factor:>10.6f} {pet_value:>12.6f}")
            
            print()  # Blank line between landcover types
        
        print("-" * 110)  # Separator between timesteps
    
    # Save one example
    if test_params:
        example_params = test_params[0]
        pet_ts = calculate_pet_with_landcover_params(solar_ts, temp_ts, example_params)
        csv_file, json_file = pet_ts.save_to_files("test_pet_calculation_with_timestep")
        print(f"Saved example PET calculation to: {csv_file}")
    
    return pet_ts


if __name__ == "__main__":
    # Set up window icon for any GUI components
    root = tk.Tk()
    root.withdraw()
    set_window_icon(root)
    
    # Run test
    test_pet_calculation()
    
    print("\nKey features of the enhanced PET calculation:")
    print("1. Uses solarRadiationScalingFactor instead of fixed ct (0.025)")
    print("2. Uses growingDegreeOffset instead of fixed jh_offset (3.0)")
    print("3. Reads parameters from landCoverType evaporation section")
    print("4. Formula: PET = Rs * (1/solarRadiationScalingFactor) * max(0, T + growingDegreeOffset) * (timestep_seconds/86400)")
    print("5. Temperature constraint: PET = 0 when (T + growingDegreeOffset) <= 0")
    print("6. Timestep scaling: Automatically scales output based on timestep_seconds from JSON metadata")
    print("7. Integrates with catchment structure for landcover-specific calculations")
    print("\nBiological rationale: Evapotranspiration ceases when growing-degree-adjusted")
    print("temperature is at or below freezing (0°C). The timestep scaling ensures proper")
    print("units regardless of whether the input data is daily, hourly, or other intervals.")
    
    # Demonstrate the temperature constraint and timestep scaling
    print(f"\nTimestep scaling examples:")
    print(f"- Daily data (86400s): scaling factor = 1.0 → PET in mm/day")
    print(f"- Hourly data (3600s): scaling factor = 0.04167 → PET in mm/hour")
    print(f"- 12-hour data (43200s): scaling factor = 0.5 → PET in mm/12hours")
    
    root.destroy()
