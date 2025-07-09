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


def simulate_soil_temperature_for_bucket(
    input_timeseries,
    bucket_params,
    landcover_params,
    timestep_seconds=86400,
    temp_column="air_temperature",
    snow_column="snowpack_depth"
):
    """
    Simulate soil temperature time series for a single bucket.
    
    Parameters:
    input_timeseries: TimeSeries object with air temperature and snow depth data
    bucket_params: Dict with bucket-specific parameters
    landcover_params: Dict with landcover-specific soil temperature parameters  
    timestep_seconds: Timestep scaling factor
    temp_column: Name of temperature column
    snow_column: Name of snow depth column
    
    Returns:
    TimeSeries object with soil temperature values
    """
    
    # Extract landcover parameters
    K_t = landcover_params.get("thermalConductivity", 0.63)
    C_s = landcover_params.get("specificHeatFreezeThaw", 1.3)
    f_s = landcover_params.get("snowDepthFactor", -3.3)
    
    # Extract bucket parameters
    soil_temp_params = bucket_params.get("soilTemperature", {})
    T_0 = soil_temp_params.get("curentTemperature", 5.0)  # Note: JSON has typo "curent"
    Z_s = soil_temp_params.get("effectiveDepth", 0.5)
    receives_precipitation = bucket_params.get("receivesPrecipitation", True)
    bucket_name = bucket_params.get("name", "Unknown")
    
    # Use TimeSeries class if available, otherwise use simplified version
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create output TimeSeries
    output_ts = TSClass()
    
    # Copy metadata from input time series
    for key, value in input_timeseries.metadata.items():
        output_ts.add_metadata(key, value)
    
    # Add soil temperature specific metadata
    output_ts.add_metadata("calculation_method", "Thermal conductivity model with snow insulation")
    output_ts.add_metadata("bucket_name", bucket_name)
    output_ts.add_metadata("bucket_abbreviation", bucket_params.get("abbreviation", ""))
    output_ts.add_metadata("initial_temperature", str(T_0))
    output_ts.add_metadata("thermal_conductivity", str(K_t))
    output_ts.add_metadata("specific_heat_capacity", str(C_s))
    output_ts.add_metadata("snow_depth_factor", str(f_s))
    output_ts.add_metadata("effective_depth", str(Z_s))
    output_ts.add_metadata("receives_precipitation", str(receives_precipitation))
    output_ts.add_metadata("timestep_seconds", str(timestep_seconds))
    output_ts.add_metadata("generation_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    output_ts.add_metadata("formula", "delta_T = (D/86400) * S * (K_t/(1e6*C_s*Z_s^2)) * (T-T_s0)")
    
    # Add soil temperature column
    output_ts.add_column("soil_temperature_c")
    
    # Find column indices
    try:
        if hasattr(input_timeseries, 'columns'):
            temp_idx = input_timeseries.columns.index(temp_column)
            snow_idx = input_timeseries.columns.index(snow_column)
            timestamp_idx = 0  # First column is always timestamp
            location_idx = 1   # Second column is always location
        else:
            temp_idx = 2  # Assume third column for simplified case
            snow_idx = 3  # Assume fourth column for simplified case
            timestamp_idx = 0
            location_idx = 1
    except (ValueError, AttributeError) as e:
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


def calculate_soil_temperature_with_landcover_params(
    input_timeseries, 
    landcover_params,
    timestep_seconds=86400,
    temp_column="air_temperature",
    snow_column="snowpack_depth"
):
    """
    Calculate soil temperature time series for all buckets in a landcover type.
    
    This is the main function that should be called by other modules like
    hydro_model_timeseries_generator.py.
    
    Parameters:
    input_timeseries: TimeSeries with air temperature and snow data
    landcover_params: Dict with complete landcover parameters including:
                     - soilTemperature: {thermalConductivity, specificHeatFreezeThaw, snowDepthFactor}  
                     - buckets: [list of bucket dicts with soilTemperature params]
    timestep_seconds: Timestep scaling factor
    temp_column: Name of temperature column  
    snow_column: Name of snow depth column
    
    Returns:
    Dict of {bucket_name: TimeSeries} with soil temperature data for each bucket
    """
    
    # Extract landcover-level soil temperature parameters
    soil_temp_params = landcover_params.get("soilTemperature", {})
    bucket_params = landcover_params.get("buckets", [])
    
    if not bucket_params:
        raise ValueError("No buckets found in landcover parameters")
    
    results = {}
    
    # Process each bucket
    for bucket in bucket_params:
        bucket_name = bucket.get("name", "Unknown")
        
        # Calculate soil temperature for this bucket
        bucket_ts = simulate_soil_temperature_for_bucket(
            input_timeseries=input_timeseries,
            bucket_params=bucket,
            landcover_params=soil_temp_params,
            timestep_seconds=timestep_seconds,
            temp_column=temp_column,
            snow_column=snow_column
        )
        
        results[bucket_name] = bucket_ts
    
    return results


def load_timeseries_from_files(csv_path, json_path):
    """
    Load a time series from CSV and JSON files.
    
    This helper function is useful for testing and standalone usage.
    """
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
                if not row:  # Skip empty rows
                    continue
                
                # Convert timestamp to datetime object
                timestamp_str = row[0]
                try:
                    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    # Try alternative parsing
                    try:
                        timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        continue
                
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
    except Exception as e:
        raise Exception(f"Error reading CSV file: {e}")
    
    # Create TimeSeries object
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    ts = TSClass()
    ts.columns = columns
    ts.data = data
    ts.metadata = metadata
    
    return ts


def test_soil_temperature_calculation():
    """Test function to demonstrate soil temperature calculation."""
    print("Testing soil temperature calculation with landcover parameters...")
    
    # Create sample input data
    start_date = datetime.datetime(2024, 1, 1, 0, 0, 0)
    
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create input time series with temperature and snow data
    input_ts = TSClass("Test_Input")
    input_ts.add_column("air_temperature")
    input_ts.add_column("snowpack_depth")
    input_ts.add_metadata("timestep_seconds", 86400)
    input_ts.add_metadata("hru_name", "TestHRU")
    input_ts.add_metadata("land_cover_type", "TestLandcover")
    
    # Add sample data for 10 days with varying conditions
    test_data = [
        (5.0, 0.0),    # Day 1: Mild, no snow
        (3.0, 0.5),    # Day 2: Cool, light snow
        (-2.0, 1.0),   # Day 3: Cold, snow building
        (-5.0, 1.5),   # Day 4: Very cold, deep snow
        (-3.0, 2.0),   # Day 5: Cold, deepest snow
        (0.0, 1.8),    # Day 6: Freezing, snow melting
        (2.0, 1.2),    # Day 7: Warming, snow melting
        (8.0, 0.8),    # Day 8: Warm, snow melting
        (12.0, 0.3),   # Day 9: Very warm, little snow
        (15.0, 0.0)    # Day 10: Hot, no snow
    ]
    
    for i, (temp, snow) in enumerate(test_data):
        current_date = start_date + datetime.timedelta(days=i)
        input_ts.add_data(current_date, "TestLocation", {
            "air_temperature": temp,
            "snowpack_depth": snow
        })
    
    # Test with different landcover configurations
    test_landcovers = [
        {
            "name": "Forest_Insulated",
            "soilTemperature": {
                "thermalConductivity": 0.63,
                "specificHeatFreezeThaw": 1.3,
                "snowDepthFactor": -3.3  # Strong snow insulation
            },
            "buckets": [
                {
                    "name": "Surface_Soil",
                    "abbreviation": "SS",
                    "receivesPrecipitation": True,
                    "soilTemperature": {
                        "curentTemperature": 5.0,
                        "effectiveDepth": 0.2  # Shallow, responsive
                    }
                },
                {
                    "name": "Deep_Soil", 
                    "abbreviation": "DS",
                    "receivesPrecipitation": False,
                    "soilTemperature": {
                        "curentTemperature": 8.0,
                        "effectiveDepth": 1.0  # Deep, stable
                    }
                }
            ]
        },
        {
            "name": "Agriculture_Exposed",
            "soilTemperature": {
                "thermalConductivity": 0.7,
                "specificHeatFreezeThaw": 6.6,
                "snowDepthFactor": -0.25  # Weak snow insulation
            },
            "buckets": [
                {
                    "name": "Topsoil",
                    "abbreviation": "TS", 
                    "receivesPrecipitation": True,
                    "soilTemperature": {
                        "curentTemperature": 4.0,
                        "effectiveDepth": 0.15
                    }
                }
            ]
        }
    ]
    
    print(f"\n{'Date':>12} {'Air T':>8} {'Snow':>8} {'Landcover':>18} {'Bucket':>12} {'Soil T':>10}")
    print("-" * 80)
    
    for lc_params in test_landcovers:
        lc_name = lc_params["name"]
        
        # Calculate soil temperature for this landcover
        soil_results = calculate_soil_temperature_with_landcover_params(
            input_ts, lc_params, timestep_seconds=86400
        )
        
        # Display results for each bucket
        for bucket_name, soil_ts in soil_results.items():
            for i, row in enumerate(soil_ts.data):
                timestamp = row[0]
                soil_temp = row[2]  # Soil temperature is in third column
                air_temp, snow_depth = test_data[i]
                
                print(f"{timestamp.strftime('%Y-%m-%d'):>12} {air_temp:>8.1f} {snow_depth:>8.1f} "
                      f"{lc_name:>18} {bucket_name:>12} {soil_temp:>10.3f}")
            
            print()  # Blank line between buckets
    
    # Save one example
    if test_landcovers:
        example_results = calculate_soil_temperature_with_landcover_params(
            input_ts, test_landcovers[0], timestep_seconds=86400
        )
        
        for bucket_name, ts in example_results.items():
            csv_file, json_file = ts.save_to_files(f"test_soil_temperature_{bucket_name}")
            print(f"Saved example calculation for {bucket_name} to: {csv_file}")
    
    return soil_results


def show_calculation_info():
    """Display information about the soil temperature calculation method."""
    print("Soil Temperature Calculation Method:")
    print("=" * 50)
    print("1. Uses thermal conductivity model with snow insulation effects")
    print("2. Landcover parameters: thermalConductivity, specificHeatFreezeThaw, snowDepthFactor")
    print("3. Bucket parameters: currentTemperature, effectiveDepth, receivesPrecipitation")
    print("4. Snow insulation: S = exp(f_s * z) if receives precipitation, else S = 1.0")
    print("5. Temperature change: delta_T = (D/86400) * S * (K_t/(1e6*C_s*Z_s^2)) * (T-T_s0)")
    print("6. Updated temperature: T_s = T_s0 + delta_T")
    print("")
    print("Physical rationale: Soil temperature responds to air temperature based on")
    print("thermal properties, with snow acting as insulation when present.")
    print("Different buckets in the same landcover can have different thermal responses.")


if __name__ == "__main__":
    # Show calculation information
    show_calculation_info()
    
    # Run test
    test_results = test_soil_temperature_calculation()
    
    print("\nKey features of this soil temperature calculator:")
    print("1. Calculates separate soil temperature for each bucket in a landcover")
    print("2. Uses landcover-specific thermal properties")
    print("3. Accounts for snow insulation effects")
    print("4. Scales calculations based on timestep_seconds")
    print("5. Integrates with catchment structure for bucket-specific parameters")
    print("6. Can be imported and used by other modules (e.g., hydro_model_timeseries_generator.py)")
