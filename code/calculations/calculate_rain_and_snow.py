#!/usr/bin/env python3
"""
Rain and Snow Time Series Calculator

This module calculates rain and snow dynamics using landCoverType-specific parameters 
from the catchment structure. Generates time series with:
- Air temperature (from input)
- Depth of snowfall (calculated)
- Depth of rain (calculated)
- Depth of snowpack at end of time period (calculated)
- Depth of snowmelt during time period (calculated)

Uses temperature thresholds and scaling factors from subcatchment precipitationAdjustments
and landCoverType-specific parameters.
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


def calculate_rain_and_snow_with_params(temp_ts, precip_ts, subcatchment_params, landcover_params,
                                       temp_column="temperature_c", precip_column="precipitation", 
                                       timestep_seconds=86400):
    """
    Calculate rain and snow dynamics using subcatchment and landcover-specific parameters.
    
    Parameters:
    temp_ts: Temperature time series
    precip_ts: Precipitation time series
    subcatchment_params: Dict with precipitationAdjustments
    landcover_params: Dict with landcover-specific parameters
    temp_column: Name of temperature column
    precip_column: Name of precipitation column
    timestep_seconds: Timestep in seconds for scaling snowmelt (default: 86400 for daily)
    
    Returns:
    TimeSeries with columns: air_temperature, snowfall_depth, rain_depth, 
                           snowpack_depth, snowmelt_depth
    """
    
    # Use TimeSeries class if available, otherwise use simplified version
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Create output time series
    output_ts = TSClass("Rain_Snow_Dynamics")
    output_ts.add_column("air_temperature")
    output_ts.add_column("snowfall_depth")
    output_ts.add_column("rain_depth")
    output_ts.add_column("snowpack_depth")
    output_ts.add_column("snowmelt_depth")
    
    # Extract parameters
    # Subcatchment parameters
    snow_offset = subcatchment_params.get("precipitationAdjustments", {}).get("snowOffset", 0.0)
    subcatch_rain_mult = subcatchment_params.get("precipitationAdjustments", {}).get("rainfallMultiplier", 1.0)
    subcatch_snow_mult = subcatchment_params.get("precipitationAdjustments", {}).get("snowfallMultiplier", 1.0)
    
    # Landcover parameters
    landcover_rain_mult = landcover_params.get("rainfallMultiplier", 1.0)
    landcover_snow_mult = landcover_params.get("snowfallMultiplier", 1.0)
    melt_temperature = landcover_params.get("snowpack", {}).get("meltTemperature", 0.0)
    degree_day_melt_rate = landcover_params.get("snowpack", {}).get("degreeDayMeltRate", 3.0)
    initial_snowpack = landcover_params.get("snowpack", {}).get("depth", 0.0)
    
    # Calculate timestep scaling factor for snowmelt
    timestep_scale_factor = timestep_seconds / 86400.0  # Scale from daily to actual timestep
    
    # Find column indices
    temp_idx = temp_ts.columns.index(temp_column) if temp_column in temp_ts.columns else None
    timestamp_idx_temp = 0
    location_idx_temp = 1
    
    precip_idx = precip_ts.columns.index(precip_column) if precip_column in precip_ts.columns else None
    timestamp_idx_precip = 0
    location_idx_precip = 1
    
    if temp_idx is None or precip_idx is None:
        print(f"Error: Required columns not found. Temperature: {temp_column}, Precipitation: {precip_column}")
        return output_ts
    
    # Create lookup dictionary for precipitation data
    precip_lookup = {}
    for row in precip_ts.data:
        timestamp = row[timestamp_idx_precip]
        location = row[location_idx_precip]
        precipitation = row[precip_idx] if len(row) > precip_idx else None
        key = (timestamp, location)
        precip_lookup[key] = precipitation
    
    # Track snowpack depth for each location
    snowpack_tracker = {}
    
    # Process each temperature data point
    for row in temp_ts.data:
        timestamp = row[timestamp_idx_temp]
        location = row[location_idx_temp]
        temperature = row[temp_idx] if len(row) > temp_idx else None
        
        # Look up corresponding precipitation
        key = (timestamp, location)
        precipitation = precip_lookup.get(key)
        
        # Initialize snowpack for this location if not seen before
        if location not in snowpack_tracker:
            snowpack_tracker[location] = initial_snowpack
        
        # Calculate rain and snow if both values are available
        if temperature is not None and precipitation is not None:
            # Determine if precipitation falls as rain or snow
            critical_temp = snow_offset  # Temperature threshold for snow vs rain
            
            if temperature >= critical_temp:
                # Rain
                rain_depth = landcover_rain_mult * subcatch_rain_mult * precipitation
                snowfall_depth = 0.0
            else:
                # Snow
                rain_depth = 0.0
                snowfall_depth = landcover_snow_mult * subcatch_snow_mult * precipitation
            
            # Calculate snowmelt using degree day model with timestep scaling
            if temperature > melt_temperature:
                # Potential melt scaled by timestep
                potential_melt = degree_day_melt_rate * (temperature - melt_temperature) * timestep_scale_factor
                
                # Actual melt is limited by available snow (previous snowpack + new snowfall)
                available_snow = snowpack_tracker[location] + snowfall_depth
                actual_melt = min(potential_melt, available_snow)
            else:
                actual_melt = 0.0
            
            # Update snowpack depth
            new_snowpack_depth = snowpack_tracker[location] + snowfall_depth - actual_melt
            new_snowpack_depth = max(0.0, new_snowpack_depth)  # Cannot be negative
            
            # Store updated snowpack depth
            snowpack_tracker[location] = new_snowpack_depth
            
        else:
            rain_depth = None
            snowfall_depth = None
            actual_melt = None
            new_snowpack_depth = snowpack_tracker.get(location, 0.0)
        
        # Add to output time series
        output_ts.add_data(timestamp, location, {
            "air_temperature": temperature,
            "snowfall_depth": snowfall_depth,
            "rain_depth": rain_depth,
            "snowpack_depth": new_snowpack_depth,
            "snowmelt_depth": actual_melt
        })
    
    return output_ts


def load_timestep_from_metadata(json_path):
    """Load timestep information from JSON metadata file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata.get('timestep_seconds', 86400)  # Default to daily if not found
    except Exception as e:
        print(f"Warning: Could not load timestep from {json_path}: {e}")
        return 86400  # Default to daily timestep


def load_catchment_parameters(catchment_file_path):
    """Load catchment parameters from JSON file."""
    try:
        with open(catchment_file_path, 'r', encoding='utf-8') as f:
            catchment_data = json.load(f)
        return catchment_data
    except Exception as e:
        print(f"Error loading catchment file {catchment_file_path}: {e}")
        return None


def process_all_landcover_types(temp_ts, precip_ts, catchment_data, output_dir=None, timestep_json_path=None):
    """
    Process rain and snow calculations for all land cover types in all subcatchments.
    
    Parameters:
    temp_ts: Temperature time series
    precip_ts: Precipitation time series  
    catchment_data: Full catchment structure from JSON
    output_dir: Directory to save output files
    timestep_json_path: Path to JSON file containing timestep information
    
    Returns:
    List of created output files
    """
    output_files = []
    
    # Load timestep information if provided
    timestep_seconds = 86400  # Default to daily
    if timestep_json_path:
        timestep_seconds = load_timestep_from_metadata(timestep_json_path)
        print(f"Using timestep: {timestep_seconds} seconds ({timestep_seconds/86400:.3f} days)")
    
    # Process each HRU
    for hru_idx, hru in enumerate(catchment_data.get("HRUs", [])):
        hru_name = hru.get("name", f"HRU_{hru_idx}")
        subcatchment = hru.get("subcatchment", {})
        
        # Process each land cover type in this subcatchment
        for lc_idx, landcover in enumerate(subcatchment.get("landCoverTypes", [])):
            lc_name = landcover.get("name", f"LandCover_{lc_idx}")
            
            print(f"Processing {hru_name} - {lc_name}")
            
            # Calculate rain and snow for this combination with timestep scaling
            result_ts = calculate_rain_and_snow_with_params(
                temp_ts, precip_ts, subcatchment, landcover, timestep_seconds=timestep_seconds
            )
            
            # Add metadata
            result_ts.add_metadata("hru_name", hru_name)
            result_ts.add_metadata("landcover_name", lc_name)
            result_ts.add_metadata("calculation_type", "rain_and_snow_dynamics")
            result_ts.add_metadata("snow_offset", subcatchment.get("precipitationAdjustments", {}).get("snowOffset", 0.0))
            result_ts.add_metadata("melt_temperature", landcover.get("snowpack", {}).get("meltTemperature", 0.0))
            result_ts.add_metadata("timestep_seconds", timestep_seconds)
            result_ts.add_metadata("timestep_scale_factor", timestep_seconds / 86400.0)
            
            # Save to files
            base_name = f"{hru_name}_{lc_name}_rain_snow"
            try:
                csv_file, json_file = result_ts.save_to_files(base_name, output_dir)
                output_files.extend([csv_file, json_file])
                print(f"  Saved: {csv_file}")
            except Exception as e:
                print(f"  Error saving {base_name}: {e}")
    
    return output_files


def test_rain_snow_calculation():
    """Test function to demonstrate rain and snow calculation with timestep scaling."""
    print("Testing Rain and Snow calculation with landcover parameters and timestep scaling...")
    
    # Create sample temperature and precipitation data
    start_date = datetime.datetime(2024, 12, 1, 0, 0, 0)  # Winter season
    
    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
    
    # Temperature time series
    temp_ts = TSClass("Test_Temperature")
    temp_ts.add_column("temperature_c")
    
    # Precipitation time series
    precip_ts = TSClass("Test_Precipitation")
    precip_ts.add_column("precipitation")
    
    # Add sample data for 10 days with varying conditions
    for i in range(10):
        current_date = start_date + datetime.timedelta(days=i)
        # Temperature varying from -5°C to +5°C
        temperature = -5.0 + i * 1.1
        # Precipitation varying from 0 to 10 mm
        precipitation = max(0, 2.0 + i * 0.5 - (i % 3))
        
        temp_ts.add_data(current_date, "TestLocation", {"temperature_c": temperature})
        precip_ts.add_data(current_date, "TestLocation", {"precipitation": precipitation})
    
    # Test with different parameter sets and timesteps
    test_scenarios = [
        {
            "name": "Cold Climate Forest (Daily)",
            "timestep_seconds": 86400,  # Daily
            "subcatchment": {
                "precipitationAdjustments": {
                    "snowOffset": -1.0,  # Snow below -1°C
                    "rainfallMultiplier": 1.2,
                    "snowfallMultiplier": 1.5
                }
            },
            "landcover": {
                "rainfallMultiplier": 0.8,
                "snowfallMultiplier": 1.3,
                "snowpack": {
                    "depth": 50.0,  # Start with existing snowpack
                    "meltTemperature": 1.0,  # Melt above 1°C
                    "degreeDayMeltRate": 2.5
                }
            }
        },
        {
            "name": "Cold Climate Forest (Hourly)",
            "timestep_seconds": 3600,  # Hourly
            "subcatchment": {
                "precipitationAdjustments": {
                    "snowOffset": -1.0,  # Snow below -1°C
                    "rainfallMultiplier": 1.2,
                    "snowfallMultiplier": 1.5
                }
            },
            "landcover": {
                "rainfallMultiplier": 0.8,
                "snowfallMultiplier": 1.3,
                "snowpack": {
                    "depth": 50.0,  # Start with existing snowpack
                    "meltTemperature": 1.0,  # Melt above 1°C
                    "degreeDayMeltRate": 2.5
                }
            }
        }
    ]
    
    print(f"\n{'Date':>12} {'Temp(°C)':>8} {'Precip':>8} {'Scenario':>25} {'Timestep':>8} {'Rain':>8} {'Snow':>8} {'Melt':>8} {'Pack':>8}")
    print("-" * 120)
    
    for scenario in test_scenarios:
        rain_snow_ts = calculate_rain_and_snow_with_params(
            temp_ts, precip_ts, 
            scenario["subcatchment"], 
            scenario["landcover"],
            timestep_seconds=scenario["timestep_seconds"]
        )
        
        timestep_label = f"{scenario['timestep_seconds']}s"
        
        for i, row in enumerate(rain_snow_ts.data):
            timestamp = row[0]
            temp_value = temp_ts.data[i][2]
            precip_value = precip_ts.data[i][2]
            
            # Extract values from rain_snow calculation
            air_temp = row[2]  # air_temperature
            snowfall = row[3]  # snowfall_depth
            rain = row[4]     # rain_depth
            snowpack = row[5]  # snowpack_depth
            melt = row[6]     # snowmelt_depth
            
            print(f"{timestamp.strftime('%Y-%m-%d'):>12} {temp_value:>8.1f} {precip_value:>8.1f} "
                  f"{scenario['name']:>25} {timestep_label:>8} {rain:>8.2f} {snowfall:>8.2f} {melt:>8.2f} {snowpack:>8.1f}")
        
        print()  # Blank line between scenarios
    
    # Save one example
    if test_scenarios:
        example_scenario = test_scenarios[0]
        rain_snow_ts = calculate_rain_and_snow_with_params(
            temp_ts, precip_ts,
            example_scenario["subcatchment"],
            example_scenario["landcover"],
            timestep_seconds=example_scenario["timestep_seconds"]
        )
        csv_file, json_file = rain_snow_ts.save_to_files("test_rain_snow_calculation")
        print(f"Saved example calculation to: {csv_file}")
        print(f"\nNote: Hourly timestep shows reduced snowmelt compared to daily timestep")
        print(f"This is because snowmelt is scaled by timestep_seconds/86400 = {3600/86400:.4f} for hourly data")
    
    return rain_snow_ts


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 4:
        print("Usage: python calculate_rain_and_snow.py <temp_csv> <temp_json> <precip_csv> <precip_json> <catchment_json> [output_dir]")
        print("\nExample:")
        print("python calculate_rain_and_snow.py temp_data.csv temp_data.json precip_data.csv precip_data.json generated_catchment.json output/")
        print("\nNote: The temp_json file will be used to extract timestep_seconds for snowmelt scaling")
        return
    
    # Setup GUI for icon
    try:
        root = tk.Tk()
        root.withdraw()
        set_window_icon(root)
        root.destroy()
    except:
        pass
    
    # Parse command line arguments
    temp_csv = sys.argv[1]
    temp_json = sys.argv[2]
    precip_csv = sys.argv[3]
    precip_json = sys.argv[4]
    catchment_json = sys.argv[5]
    output_dir = sys.argv[6] if len(sys.argv) > 6 else None
    
    # Load input data
    print("Loading temperature time series...")
    temp_ts = load_timeseries_from_files(temp_csv, temp_json)
    if not temp_ts:
        print("Error: Could not load temperature time series")
        return
    
    print("Loading precipitation time series...")
    precip_ts = load_timeseries_from_files(precip_csv, precip_json)
    if not precip_ts:
        print("Error: Could not load precipitation time series")
        return
    
    print("Loading catchment parameters...")
    catchment_data = load_catchment_parameters(catchment_json)
    if not catchment_data:
        print("Error: Could not load catchment parameters")
        return
    
    # Process all land cover types with timestep information
    print("Processing all land cover types...")
    output_files = process_all_landcover_types(temp_ts, precip_ts, catchment_data, output_dir, temp_json)
    
    print(f"\nCompleted! Generated {len(output_files)} files:")
    for file_path in output_files:
        print(f"  {file_path}")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Run test if no arguments provided
        test_rain_snow_calculation()
    else:
        # Run with command line arguments
        main()
