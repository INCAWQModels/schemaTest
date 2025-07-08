#!/usr/bin/env python3
"""
Enhanced Potential Evapotranspiration Calculator

This module calculates PET using landCoverType-specific parameters from the catchment structure.
Uses the Jensen-Haise method with parameters from the evaporation section of each landCoverType:
- solarRadiationScalingFactor (replaces ct coefficient)
- growingDegreeOffset (replaces jh_offset)

Formula: PET = Rs * (1/solarRadiationScalingFactor) * (T + growingDegreeOffset)
"""

import os
import sys
import json
import csv
import datetime
import math
import uuid

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


def calculate_pet_with_landcover_params(solar_ts, temp_ts, landcover_params, 
                                       solar_column="solar_radiation", 
                                       temp_column="temperature_c"):
    """
    Calculate PET using Jensen-Haise method with landCoverType-specific parameters.
    
    Parameters:
    solar_ts: TimeSeries object with solar radiation data (W/m²)
    temp_ts: TimeSeries object with temperature data (°C)
    landcover_params: Dict with 'solarRadiationScalingFactor' and 'growingDegreeOffset'
    solar_column: Name of solar radiation column
    temp_column: Name of temperature column
    
    Returns:
    TimeSeries object with PET values (mm/day)
    """
    
    # Extract landcover parameters
    solar_scaling = landcover_params.get('solarRadiationScalingFactor', 60.0)
    degree_offset = landcover_params.get('growingDegreeOffset', 0.0)
    
    # Use TimeSeries class if available, otherwise use simplified version
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create output TimeSeries
    output_ts = TSClass()
    
    # Copy metadata from solar time series
    for key, value in solar_ts.metadata.items():
        output_ts.add_metadata(key, value)
    
    # Add PET-specific metadata
    output_ts.add_metadata("calculation_method", "Jensen-Haise with landcover parameters")
    output_ts.add_metadata("solar_radiation_scaling_factor", str(solar_scaling))
    output_ts.add_metadata("growing_degree_offset", str(degree_offset))
    output_ts.add_metadata("generation_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    output_ts.add_metadata("formula", "PET = Rs * (1/solarRadiationScalingFactor) * max(0, T + growingDegreeOffset)")
    output_ts.add_metadata("temperature_constraint", "PET = 0 when (T + growingDegreeOffset) <= 0")
    
    # Add PET column
    output_ts.add_column("pet_mm_day")
    
    # Find column indices
    try:
        if hasattr(solar_ts, 'columns'):
            solar_idx = solar_ts.columns.index(solar_column)
            timestamp_idx_solar = 0  # First column is always timestamp
            location_idx_solar = 1   # Second column is always location
        else:
            solar_idx = 2  # Assume third column for simplified case
            timestamp_idx_solar = 0
            location_idx_solar = 1
    except (ValueError, AttributeError):
        raise ValueError(f"Solar radiation column '{solar_column}' not found")
    
    try:
        if hasattr(temp_ts, 'columns'):
            temp_idx = temp_ts.columns.index(temp_column)
            timestamp_idx_temp = 0
            location_idx_temp = 1
        else:
            temp_idx = 2  # Assume third column for simplified case  
            timestamp_idx_temp = 0
            location_idx_temp = 1
    except (ValueError, AttributeError):
        raise ValueError(f"Temperature column '{temp_column}' not found")
    
    # Create temperature lookup for efficient matching
    temp_lookup = {}
    for row in temp_ts.data:
        timestamp = row[timestamp_idx_temp]
        location = row[location_idx_temp]
        temperature = row[temp_idx] if len(row) > temp_idx else None
        
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
                pet = 0.0
            else:
                pet = rs * (1.0 / solar_scaling) * adjusted_temp
            
            # Ensure PET is non-negative (additional safety check)
            pet = max(0.0, pet)
            
        else:
            pet = None
        
        # Add to output time series
        output_ts.add_data(timestamp, location, {"pet_mm_day": pet})
    
    return output_ts


def test_pet_calculation():
    """Test function to demonstrate PET calculation."""
    
    print("Testing PET calculation with landcover parameters...")
    
    # Create sample solar radiation data
    start_date = datetime.datetime(2024, 6, 21, 12, 0, 0)  # Summer solstice, noon
    
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Solar radiation time series
    solar_ts = TSClass("Test_Solar")
    solar_ts.add_column("solar_radiation")
    solar_ts.add_metadata("latitude", "45.0")
    solar_ts.add_metadata("longitude", "15.0")
    
    # Temperature time series  
    temp_ts = TSClass("Test_Temperature")
    temp_ts.add_column("temperature_c")
    
    # Add sample data for 5 days with varying temperatures (including cold)
    for i in range(5):
        current_date = start_date + datetime.timedelta(days=i)
        solar_rad = 300.0 + i * 10  # Varying solar radiation
        temperature = -2.0 + i * 4   # Temperature from -2°C to 14°C
        
        solar_ts.add_data(current_date, "TestLocation", {"solar_radiation": solar_rad})
        temp_ts.add_data(current_date, "TestLocation", {"temperature_c": temperature})
    
    # Test with different landcover parameters
    test_params = [
        {"name": "Forest", "solarRadiationScalingFactor": 60.0, "growingDegreeOffset": 0.0},
        {"name": "Agriculture", "solarRadiationScalingFactor": 80.0, "growingDegreeOffset": 2.0},
        {"name": "Cold_Climate", "solarRadiationScalingFactor": 40.0, "growingDegreeOffset": -3.0}  # Will create some zero PET values
    ]
    
    print(f"\n{'Date':>12} {'Solar(W/m²)':>12} {'Temp(°C)':>10} {'LandCover':>12} {'Adj.Temp':>10} {'PET(mm/d)':>12}")
    print("-" * 80)
    
    for params in test_params:
        pet_ts = calculate_pet_with_landcover_params(solar_ts, temp_ts, params)
        
        for i, row in enumerate(pet_ts.data):
            timestamp = row[0]
            pet_value = row[2]  # PET is in third column
            solar_value = solar_ts.data[i][2]
            temp_value = temp_ts.data[i][2]
            adjusted_temp = temp_value + params.get('growingDegreeOffset', 0.0)
            
            print(f"{timestamp.strftime('%Y-%m-%d'):>12} {solar_value:>12.1f} {temp_value:>10.1f} "
                  f"{params['name']:>12} {adjusted_temp:>10.1f} {pet_value:>12.3f}")
        
        print()  # Blank line between landcover types
    
    # Save one example
    if test_params:
        example_params = test_params[0]
        pet_ts = calculate_pet_with_landcover_params(solar_ts, temp_ts, example_params)
        csv_file, json_file = pet_ts.save_to_files("test_pet_calculation")
        print(f"Saved example PET calculation to: {csv_file}")
    
    return pet_ts


if __name__ == "__main__":
    # Run test
    test_pet_calculation()
    
    print("\nKey differences from original calculate_potential_evapotranspiration.py:")
    print("1. Uses solarRadiationScalingFactor instead of fixed ct (0.025)")
    print("2. Uses growingDegreeOffset instead of fixed jh_offset (3.0)")
    print("3. Reads parameters from landCoverType evaporation section")
    print("4. Formula: PET = Rs * (1/solarRadiationScalingFactor) * max(0, T + growingDegreeOffset)")
    print("5. Temperature constraint: PET = 0 when (T + growingDegreeOffset) <= 0")
    print("6. Integrates with catchment structure for landcover-specific calculations")
    print("\nBiological rationale: Evapotranspiration ceases when growing-degree-adjusted")
    print("temperature is at or below freezing (0°C).")
    
    # Demonstrate the temperature constraint
    print(f"\nTemperature constraint examples:")
    print(f"- Temperature: 5°C, growingDegreeOffset: -2°C → Adjusted: 3°C → PET calculated normally")
    print(f"- Temperature: 2°C, growingDegreeOffset: -3°C → Adjusted: -1°C → PET = 0.0 mm/day")
    print(f"- Temperature: 0°C, growingDegreeOffset: 0°C → Adjusted: 0°C → PET = 0.0 mm/day")
