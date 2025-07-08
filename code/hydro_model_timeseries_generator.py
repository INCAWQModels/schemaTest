#!/usr/bin/env python3
"""
Hydrological Model Time Series Generator

This script generates time series data for hydrological modeling by:
1. Reading catchment structure and time series location files
2. Validating temperature/precipitation data for all HRUs
3. Generating solar radiation time series for each HRU
4. Writing results to specified output locations

Uses only Python standard library components plus existing project code.
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

# Add the project code directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
calculations_dir = os.path.join(project_root, 'code', 'calculations')
timeseries_dir = os.path.join(project_root, 'code', 'timeSeries')

# Add to sys.path if directories exist
for path in [calculations_dir, timeseries_dir]:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

try:
    # Import project modules
    from calculate_solar_radiation import compute_radiation_timeseries
    from timeSeries import TimeSeries
except ImportError as e:
    print(f"Warning: Could not import project modules: {e}")
    print("Some functionality may be limited.")


class TimeSeriesValidator:
    """Class to validate time series data consistency."""
    
    def __init__(self):
        self.validation_results = {}
    
    def load_timeseries_metadata(self, csv_file_path, json_file_path):
        """Load and parse time series metadata from JSON file."""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract key information
            start_datetime = metadata.get('start_datetime')
            timestep_seconds = metadata.get('timestep_seconds')
            num_records = metadata.get('num_records')
            
            if start_datetime:
                start_dt = datetime.datetime.fromisoformat(start_datetime.replace('T', ' '))
            else:
                start_dt = None
            
            return {
                'start_datetime': start_dt,
                'timestep_seconds': timestep_seconds,
                'num_records': num_records,
                'metadata': metadata
            }
        except Exception as e:
            print(f"Error loading metadata from {json_file_path}: {e}")
            return None
    
    def validate_csv_structure(self, csv_file_path):
        """Validate CSV file structure and count records."""
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                
                # Count data rows
                record_count = sum(1 for row in reader)
                
                # Check for required columns
                required_cols = ['location', 'precipitation_mm', 'temperature_c']
                missing_cols = [col for col in required_cols if col not in header]
                
                return {
                    'valid': len(missing_cols) == 0,
                    'record_count': record_count,
                    'header': header,
                    'missing_columns': missing_cols
                }
        except Exception as e:
            print(f"Error validating CSV {csv_file_path}: {e}")
            return {'valid': False, 'error': str(e)}
    
    def check_timeseries_consistency(self, timeseries_info_list):
        """Check that all time series have consistent start date, timestep, and length."""
        if not timeseries_info_list:
            return False, "No time series to validate"
        
        reference = timeseries_info_list[0]
        ref_start = reference.get('start_datetime')
        ref_timestep = reference.get('timestep_seconds')
        ref_records = reference.get('num_records')
        
        inconsistencies = []
        
        for i, ts_info in enumerate(timeseries_info_list[1:], 1):
            hru_name = ts_info.get('hru_name', f'HRU_{i}')
            
            if ts_info.get('start_datetime') != ref_start:
                inconsistencies.append(f"{hru_name}: Different start date")
            
            if ts_info.get('timestep_seconds') != ref_timestep:
                inconsistencies.append(f"{hru_name}: Different timestep")
            
            if ts_info.get('num_records') != ref_records:
                inconsistencies.append(f"{hru_name}: Different number of records")
        
        if inconsistencies:
            return False, "; ".join(inconsistencies)
        
        return True, "All time series are consistent"


class HydrologicalTimeSeriesGenerator:
    """Main class for generating hydrological model time series."""
    
    def __init__(self, catchment_file="../testData/generated_catchment.json", 
                 timeseries_file="../testData/modelTimeSeries.json", replace_all=True):
        self.catchment_file = catchment_file
        self.timeseries_file = timeseries_file
        self.replace_all = replace_all
        self.catchment_data = None
        self.timeseries_data = None
        self.validator = TimeSeriesValidator()
        self.base_folder = None
        
        # Try to set window icon if running with GUI
        self.root = None
        self.setup_gui()
    
    def setup_gui(self):
        """Setup basic GUI for file selection if needed."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # Hide the main window initially
            
            # Try to set the window icon
            icon_path = "INCAMan.png"
            if os.path.exists(icon_path):
                self.root.iconphoto(True, tk.PhotoImage(file=icon_path))
            elif os.path.exists(os.path.join("..", "INCAMan.png")):
                self.root.iconphoto(True, tk.PhotoImage(file=os.path.join("..", "INCAMan.png")))
                
        except Exception as e:
            print(f"GUI setup warning: {e}")
    
    def load_json_file(self, file_path):
        """Load and parse a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File {file_path} not found.")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return None
    
    def load_input_files(self):
        """Load the catchment structure and time series configuration files."""
        print("Loading input files...")
        
        # Load catchment structure
        self.catchment_data = self.load_json_file(self.catchment_file)
        if not self.catchment_data:
            print(f"Failed to load catchment file: {self.catchment_file}")
            return False
        
        # Load time series configuration
        self.timeseries_data = self.load_json_file(self.timeseries_file)
        if not self.timeseries_data:
            print(f"Failed to load time series file: {self.timeseries_file}")
            return False
        
        # Extract base folder for time series files
        try:
            self.base_folder = self.timeseries_data['catchment']['timeSeries']['folder']
            print(f"Time series base folder: {self.base_folder}")
        except KeyError:
            print("Warning: No base folder specified in time series configuration")
            self.base_folder = os.path.dirname(self.timeseries_file)
        
        return True
    
    def validate_temperature_precipitation_files(self):
        """Validate that all HRUs have valid temperature/precipitation files."""
        print("\nValidating temperature and precipitation files...")
        
        if 'HRUs' not in self.catchment_data:
            print("Error: No HRUs found in catchment data")
            return False
        
        hru_timeseries_info = []
        
        for i, hru in enumerate(self.catchment_data['HRUs']):
            hru_name = hru.get('name', f'HRU_{i}')
            print(f"\nChecking HRU: {hru_name}")
            
            # Find corresponding HRU in time series data
            ts_hru = None
            for ts_hru_candidate in self.timeseries_data['catchment']['HRUs']:
                if ts_hru_candidate['name'] == hru_name:
                    ts_hru = ts_hru_candidate
                    break
            
            if not ts_hru:
                print(f"Error: No time series configuration found for HRU {hru_name}")
                return False
            
            # Get temperature/precipitation file info
            try:
                temp_precip_info = ts_hru['timeSeries']['subcatchment']['temperatureAndPrecipitation']
                filename = temp_precip_info['fileName']
                
                # Construct full file paths
                csv_path = os.path.join(self.base_folder, f"{filename}.csv")
                json_path = os.path.join(self.base_folder, f"{filename}.json")
                
                print(f"  CSV file: {csv_path}")
                print(f"  JSON file: {json_path}")
                
                # Check if files exist
                if not os.path.exists(csv_path):
                    print(f"Error: CSV file not found: {csv_path}")
                    return False
                
                if not os.path.exists(json_path):
                    print(f"Error: JSON metadata file not found: {json_path}")
                    return False
                
                # Load and validate metadata
                metadata_info = self.validator.load_timeseries_metadata(csv_path, json_path)
                if not metadata_info:
                    print(f"Error: Could not load metadata for {hru_name}")
                    return False
                
                # Validate CSV structure
                csv_validation = self.validator.validate_csv_structure(csv_path)
                if not csv_validation['valid']:
                    print(f"Error: Invalid CSV structure for {hru_name}: {csv_validation.get('error', 'Unknown error')}")
                    if 'missing_columns' in csv_validation:
                        print(f"Missing columns: {csv_validation['missing_columns']}")
                    return False
                
                # Store information for consistency check
                metadata_info['hru_name'] = hru_name
                metadata_info['csv_path'] = csv_path
                metadata_info['json_path'] = json_path
                metadata_info['coordinates'] = hru.get('coordinates', {})
                hru_timeseries_info.append(metadata_info)
                
                print(f"  ✓ Valid - {metadata_info['num_records']} records, timestep: {metadata_info['timestep_seconds']}s")
                
            except KeyError as e:
                print(f"Error: Missing temperature/precipitation configuration for {hru_name}: {e}")
                return False
        
        # Check consistency across all HRUs
        print(f"\nChecking consistency across {len(hru_timeseries_info)} HRUs...")
        consistent, message = self.validator.check_timeseries_consistency(hru_timeseries_info)
        
        if not consistent:
            print(f"Error: Time series inconsistency detected: {message}")
            return False
        
        print("✓ All temperature/precipitation files are valid and consistent")
        
        # Store for later use
        self.hru_timeseries_info = hru_timeseries_info
        return True
    
    def generate_solar_radiation_timeseries(self):
        """Generate solar radiation time series for all HRUs."""
        print("\nGenerating solar radiation time series...")
        
        if not hasattr(self, 'hru_timeseries_info'):
            print("Error: Must validate temperature/precipitation files first")
            return False
        
        try:
            from calculate_solar_radiation import compute_radiation_timeseries
        except ImportError:
            print("Error: Could not import solar radiation calculation module")
            print("Falling back to built-in solar radiation calculation...")
            return self.generate_solar_radiation_builtin()
        
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            print(f"\nGenerating solar radiation for {hru_name}...")
            
            # Get coordinates
            coordinates = hru_info['coordinates']
            latitude = coordinates.get('decimalLatitude', 45.0)
            longitude = coordinates.get('decimalLongitude', -15.0)
            
            # Handle longitude convention: schema says "west positive" but standard is "east positive"
            # If longitude is negative in "west positive" system, convert to standard system
            if longitude < 0:
                longitude = -longitude  # Convert from "west positive" to standard "east positive"
            
            print(f"  Coordinates: {latitude}°N, {longitude}°E (converted from west-positive)")
            
            # Get time series parameters
            start_dt = hru_info['start_datetime']
            timestep_seconds = hru_info['timestep_seconds']
            num_records = hru_info['num_records']
            
            # Calculate solar radiation at the midpoint between adjacent time periods
            # This ensures consistency across all timestep sizes
            midpoint_offset = timestep_seconds // 2  # Half the timestep
            adjusted_start = start_dt + datetime.timedelta(seconds=midpoint_offset)
            
            print(f"  Calculating at midpoint: {adjusted_start.time()} (+ {midpoint_offset//3600}h {(midpoint_offset%3600)//60}m from period start)")
            
            # Calculate end time based on adjusted start
            end_dt = adjusted_start + datetime.timedelta(seconds=(num_records - 1) * timestep_seconds)
            
            # Estimate timezone offset based on longitude (rough approximation)
            # Each 15 degrees of longitude = 1 hour of time difference
            timezone_offset = longitude / 15.0
            
            print(f"  Time range: {adjusted_start} to {end_dt}")
            print(f"  Timestep: {timestep_seconds} seconds")
            print(f"  Estimated timezone offset: {timezone_offset:.1f} hours")
            
            # Generate solar radiation time series
            try:
                solar_ts = compute_radiation_timeseries(
                    start_time=adjusted_start,
                    end_time=end_dt,
                    step_seconds=timestep_seconds,
                    latitude=latitude,
                    longitude=longitude,
                    timezone_offset=timezone_offset,
                    location_id=hru_name
                )
                
                # Find output file name from time series configuration
                output_filename = None
                for ts_hru in self.timeseries_data['catchment']['HRUs']:
                    if ts_hru['name'] == hru_name:
                        try:
                            solar_info = ts_hru['timeSeries']['subcatchment']['solarRadiation']
                            output_filename = solar_info['fileName']
                            break
                        except KeyError:
                            print(f"Warning: No solar radiation output configuration for {hru_name}")
                
                if not output_filename:
                    output_filename = f"{hru_name}_subcatchment_solarRadiation"
                
                # Check if files already exist
                csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                
                if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                    print(f"  ✓ Skipping (files exist): {output_filename}")
                    continue
                
                # Write output files
                solar_ts.save_to_files(output_filename, self.base_folder)
                
                status_msg = "Regenerated" if (os.path.exists(csv_output_path)) else "Generated"
                print(f"  ✓ {status_msg}: {csv_output_path}")
                print(f"  ✓ Metadata: {json_output_path}")
                
            except Exception as e:
                print(f"Error generating solar radiation for {hru_name}: {e}")
                return False
        
        print("\n✓ Solar radiation generation completed successfully")
        return True
    
    def generate_potential_evapotranspiration_timeseries(self):
        """Generate potential evapotranspiration time series for all HRU/landCoverType combinations."""
        print("\nGenerating potential evapotranspiration time series...")
        
        if not hasattr(self, 'hru_timeseries_info'):
            print("Error: Must validate temperature/precipitation files first")
            return False
        
        try:
            # Try to import the enhanced PET calculator
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from enhanced_pet_calculator import calculate_pet_with_landcover_params, load_timeseries_from_files
            print("Using enhanced PET calculator with landcover parameters")
        except ImportError:
            print("Warning: Could not import enhanced PET calculator")
            return self.generate_pet_builtin()
        
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            print(f"\nProcessing PET for HRU: {hru_name}")
            
            # Load solar radiation time series for this HRU
            solar_filename = None
            for ts_hru in self.timeseries_data['catchment']['HRUs']:
                if ts_hru['name'] == hru_name:
                    try:
                        solar_info = ts_hru['timeSeries']['subcatchment']['solarRadiation']
                        solar_filename = solar_info['fileName']
                        break
                    except KeyError:
                        print(f"Warning: No solar radiation configuration for {hru_name}")
            
            if not solar_filename:
                print(f"Error: No solar radiation file found for {hru_name}")
                continue
            
            # Load solar radiation data
            solar_csv_path = os.path.join(self.base_folder, f"{solar_filename}.csv")
            solar_json_path = os.path.join(self.base_folder, f"{solar_filename}.json")
            
            if not os.path.exists(solar_csv_path):
                print(f"Error: Solar radiation file not found: {solar_csv_path}")
                continue
            
            solar_ts = load_timeseries_from_files(solar_csv_path, solar_json_path)
            if not solar_ts:
                print(f"Error: Could not load solar radiation data for {hru_name}")
                continue
            
            # Load temperature/precipitation data
            temp_csv_path = hru_info['csv_path']
            temp_json_path = hru_info['json_path']
            
            temp_ts = load_timeseries_from_files(temp_csv_path, temp_json_path)
            if not temp_ts:
                print(f"Error: Could not load temperature data for {hru_name}")
                continue
            
            # Get landCoverTypes for this HRU from catchment data
            hru_catchment_data = None
            for catchment_hru in self.catchment_data['HRUs']:
                if catchment_hru['name'] == hru_name:
                    hru_catchment_data = catchment_hru
                    break
            
            if not hru_catchment_data:
                print(f"Error: No catchment data found for {hru_name}")
                continue
            
            landcover_types = hru_catchment_data.get('subcatchment', {}).get('landCoverTypes', [])
            if not landcover_types:
                print(f"Warning: No land cover types found for {hru_name}")
                continue
            
            print(f"  Found {len(landcover_types)} land cover types")
            
            # Calculate PET for each landCoverType
            for lc_data in landcover_types:
                lc_name = lc_data.get('name', 'Unknown')
                lc_abbrev = lc_data.get('abbreviation', 'UK')
                
                print(f"    Calculating PET for {lc_name} ({lc_abbrev})")
                
                # Get evaporation parameters
                evap_params = lc_data.get('evaporation', {})
                solar_scaling = evap_params.get('solarRadiationScalingFactor', 60.0)
                degree_offset = evap_params.get('growingDegreeOffset', 0.0)
                
                print(f"      Parameters: solarRadiationScalingFactor={solar_scaling}, growingDegreeOffset={degree_offset}")
                
                # Calculate PET
                try:
                    pet_ts = calculate_pet_with_landcover_params(
                        solar_ts, temp_ts, evap_params,
                        solar_column="solar_radiation",
                        temp_column="temperature_c"
                    )
                    
                    # Find output filename from time series configuration
                    output_filename = None
                    for ts_hru in self.timeseries_data['catchment']['HRUs']:
                        if ts_hru['name'] == hru_name:
                            try:
                                landcover_types_ts = ts_hru['timeSeries']['subcatchment']['landCoverTypes']
                                for lc_ts in landcover_types_ts:
                                    if lc_ts['name'] == lc_name:
                                        pet_info = lc_ts['timeSeries']['potentialEvapotranspiration']
                                        output_filename = pet_info['fileName']
                                        break
                                if output_filename:
                                    break
                            except KeyError:
                                pass
                    
                    if not output_filename:
                        output_filename = f"{hru_name}_{lc_name}_potentialEvapotranspiration"
                    
                    # Check if files already exist
                    csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                    json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                    
                    if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                        print(f"      ✓ Skipping (files exist): {output_filename}")
                        continue
                    
                    # Add landcover-specific metadata
                    pet_ts.add_metadata("hru_name", hru_name)
                    pet_ts.add_metadata("landcover_name", lc_name)
                    pet_ts.add_metadata("landcover_abbreviation", lc_abbrev)
                    
                    # Save PET time series
                    pet_ts.save_to_files(output_filename, self.base_folder)
                    
                    status_msg = "Regenerated" if (os.path.exists(csv_output_path)) else "Generated"
                    print(f"      ✓ {status_msg}: {csv_output_path}")
                    print(f"      ✓ Metadata: {json_output_path}")
                    
                    # Show sample PET values
                    if len(pet_ts.data) > 0:
                        sample_pet = pet_ts.data[0][2] if len(pet_ts.data[0]) > 2 else None
                        if sample_pet is not None:
                            print(f"      Sample PET value: {sample_pet:.3f} mm/day")
                
                except Exception as e:
                    print(f"      Error calculating PET for {hru_name}/{lc_name}: {e}")
                    continue
        
        print("\n✓ Potential evapotranspiration generation completed successfully")
        return True
    
    def generate_pet_builtin(self):
        """Generate PET using built-in calculation (fallback method)."""
        print("Using built-in PET calculation...")
        
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            print(f"\nProcessing PET for HRU: {hru_name} (built-in method)")
            
            # Get landCoverTypes from catchment data
            hru_catchment_data = None
            for catchment_hru in self.catchment_data['HRUs']:
                if catchment_hru['name'] == hru_name:
                    hru_catchment_data = catchment_hru
                    break
            
            if not hru_catchment_data:
                continue
            
            landcover_types = hru_catchment_data.get('subcatchment', {}).get('landCoverTypes', [])
            
            # Simple PET calculation for each landCoverType
            for lc_data in landcover_types:
                lc_name = lc_data.get('name', 'Unknown')
                
                try:
                    # Get parameters
                    evap_params = lc_data.get('evaporation', {})
                    solar_scaling = evap_params.get('solarRadiationScalingFactor', 60.0)
                    degree_offset = evap_params.get('growingDegreeOffset', 0.0)
                    
                    # Load temperature data
                    temp_data = []
                    temp_csv_path = hru_info['csv_path']
                    
                    with open(temp_csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        header = next(reader)
                        temp_col_idx = header.index('temperature_c') if 'temperature_c' in header else 3
                        
                        for row in reader:
                            if len(row) > temp_col_idx:
                                try:
                                    timestamp = datetime.datetime.fromisoformat(row[0])
                                    temperature = float(row[temp_col_idx])
                                    
                                    # Calculate adjusted temperature
                                    adjusted_temp = temperature + degree_offset
                                    
                                    # Simple PET calculation: assume 200 W/m² average solar radiation
                                    rs = 200.0 * 0.0864  # Convert to MJ/m²/day
                                    
                                    # Apply temperature constraint: PET = 0 when adjusted_temp <= 0
                                    if adjusted_temp <= 0.0:
                                        pet = 0.0
                                    else:
                                        pet = rs * (1.0 / solar_scaling) * adjusted_temp
                                    
                                    pet = max(0.0, pet)  # Ensure non-negative
                                    temp_data.append([timestamp.isoformat(), hru_name, pet])
                                except (ValueError, IndexError):
                                    continue
                    
                    # Find output filename
                    output_filename = f"{hru_name}_{lc_name}_potentialEvapotranspiration"
                    
                    # Check if files already exist
                    csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                    json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                    
                    if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                        print(f"      ✓ Skipping (files exist): {output_filename}")
                        continue
                    
                    # Write CSV
                    with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['timestamp', 'location', 'pet_mm_day'])
                        writer.writerows(temp_data)
                    
                    # Write JSON metadata
                    metadata = {
                        'uuid': str(uuid.uuid4()),
                        'hru_name': hru_name,
                        'landcover_name': lc_name,
                        'calculation_method': 'Built-in Jensen-Haise with landcover parameters',
                        'solar_radiation_scaling_factor': str(solar_scaling),
                        'growing_degree_offset': str(degree_offset),
                        'generation_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'formula': 'PET = Rs * (1/solarRadiationScalingFactor) * max(0, T + growingDegreeOffset)',
                        'temperature_constraint': 'PET = 0 when (T + growingDegreeOffset) <= 0',
                        'num_records': str(len(temp_data))
                    }
                    
                    with open(json_output_path, 'w', encoding='utf-8') as jsonfile:
                        json.dump(metadata, jsonfile, indent=4)
                    
                    status_msg = "Regenerated" if os.path.exists(csv_output_path) else "Generated"
                    print(f"      ✓ {status_msg}: {csv_output_path}")
                    
                except Exception as e:
                    print(f"      Error: {e}")
                    continue
        
        print("\n✓ Built-in PET generation completed")
        return True
    
    def generate_solar_radiation_builtin(self):
        """Generate solar radiation using built-in calculation (fallback method)."""
        print("Using built-in solar radiation calculation...")
        
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            print(f"\nGenerating solar radiation for {hru_name}...")
            
            # Get coordinates
            coordinates = hru_info['coordinates']
            latitude = coordinates.get('decimalLatitude', 45.0)
            longitude = coordinates.get('decimalLongitude', -15.0)
            
            # Handle longitude convention
            if longitude < 0:
                longitude = -longitude
            
            print(f"  Coordinates: {latitude}°N, {longitude}°E")
            
            # Get time series parameters
            start_dt = hru_info['start_datetime']
            timestep_seconds = hru_info['timestep_seconds']
            num_records = hru_info['num_records']
            
            # Calculate solar radiation at the midpoint between adjacent time periods
            midpoint_offset = timestep_seconds // 2
            adjusted_start = start_dt + datetime.timedelta(seconds=midpoint_offset)
            
            timezone_offset = longitude / 15.0
            
            print(f"  Using built-in calculation at midpoint: {adjusted_start.time()}")
            
            # Create output files using built-in calculation
            try:
                # Create a simple TimeSeries-like structure
                solar_data = []
                current_time = adjusted_start
                
                for i in range(num_records):
                    # Simple solar radiation calculation
                    day_of_year = current_time.timetuple().tm_yday
                    hour = current_time.hour + current_time.minute / 60.0
                    
                    # Basic solar calculation (simplified)
                    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
                    solar_time = hour + (longitude / 15) - timezone_offset
                    hour_angle = 15 * (solar_time - 12)
                    
                    lat_rad = math.radians(latitude)
                    decl_rad = math.radians(declination)
                    ha_rad = math.radians(hour_angle)
                    
                    elevation = math.asin(
                        math.sin(lat_rad) * math.sin(decl_rad) +
                        math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
                    )
                    elevation_deg = math.degrees(elevation)
                    
                    if elevation_deg > 0:
                        G_sc = 1367  # Solar constant
                        etr = G_sc * (1 + 0.033 * math.cos(math.radians(360 * day_of_year / 365)))
                        solar_rad = etr * 0.75 * math.sin(elevation)  # 0.75 = transmittance
                    else:
                        solar_rad = 0
                    
                    solar_data.append([current_time.isoformat(), hru_name, solar_rad])
                    current_time += datetime.timedelta(seconds=timestep_seconds)
                
                # Find output file name
                output_filename = None
                for ts_hru in self.timeseries_data['catchment']['HRUs']:
                    if ts_hru['name'] == hru_name:
                        try:
                            solar_info = ts_hru['timeSeries']['subcatchment']['solarRadiation']
                            output_filename = solar_info['fileName']
                            break
                        except KeyError:
                            pass
                
                if not output_filename:
                    output_filename = f"{hru_name}_subcatchment_solarRadiation"
                
                # Check if files already exist
                csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                
                if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                    print(f"  ✓ Skipping (files exist): {output_filename}")
                    continue
                
                # Write CSV file
                with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    # Use a simple header
                    writer.writerow(['timestamp', 'location', 'solar_radiation'])
                    writer.writerows(solar_data)
                
                # Write JSON metadata
                metadata = {
                    'uuid': str(uuid.uuid4()),
                    'latitude': str(latitude),
                    'longitude': str(longitude),
                    'source': 'Built-in solar radiation calculation',
                    'generation_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'location_id': hru_name,
                    'timezone_offset': str(timezone_offset),
                    'start_time': adjusted_start.isoformat(),
                    'timestep_seconds': str(timestep_seconds),
                    'num_records': str(num_records)
                }
                
                with open(json_output_path, 'w', encoding='utf-8') as jsonfile:
                    json.dump(metadata, jsonfile, indent=4)
                
                status_msg = "Regenerated" if os.path.exists(csv_output_path) else "Generated"
                print(f"  ✓ {status_msg}: {csv_output_path}")
                print(f"  ✓ Metadata: {json_output_path}")
                
            except Exception as e:
                print(f"Error generating solar radiation for {hru_name}: {e}")
                return False
        
        print("\n✓ Solar radiation generation completed successfully")
        return True
    
    def run_generation(self):
        """Run the complete time series generation process."""
        print("=" * 60)
        print("HYDROLOGICAL MODEL TIME SERIES GENERATOR")
        print("=" * 60)
        print(f"Replace existing files: {'Yes' if self.replace_all else 'No (--no-replace)'}")
        print("=" * 60)
        
        # Step 1: Load input files
        if not self.load_input_files():
            print("\nGeneration failed: Could not load input files")
            return False
        
        # Step 2: Validate temperature/precipitation files
        if not self.validate_temperature_precipitation_files():
            print("\nGeneration failed: Temperature/precipitation validation failed")
            return False
        
        # Step 3: Generate solar radiation time series
        if not self.generate_solar_radiation_timeseries():
            print("\nGeneration failed: Solar radiation generation failed")
            return False
        
        # Step 4: Generate potential evapotranspiration time series
        if not self.generate_potential_evapotranspiration_timeseries():
            print("\nGeneration failed: Potential evapotranspiration generation failed")
            return False
        
        print("\n" + "=" * 60)
        print("TIME SERIES GENERATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("Generated time series:")
        print("✓ Solar radiation for each HRU")
        print("✓ Potential evapotranspiration for each HRU/landCoverType combination")
        print("\nNext steps (not yet implemented):")
        print("- Snow and rain dynamics for each landcover type")
        print("- Soil temperature series for each bucket")
        print("- Precipitation routing between buckets")
        print("- Flow calculations to and within reaches")
        
        return True
    
    def interactive_file_selection(self):
        """Allow user to interactively select input files."""
        if not self.root:
            print("GUI not available for file selection")
            return False
        
        self.root.deiconify()  # Show the window
        
        # Select catchment file
        catchment_file = filedialog.askopenfilename(
            title="Select Catchment Structure File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="generated_catchment.json"
        )
        
        if not catchment_file:
            print("No catchment file selected")
            self.root.withdraw()
            return False
        
        # Select time series file
        timeseries_file = filedialog.askopenfilename(
            title="Select Model Time Series File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="modelTimeSeries.json"
        )
        
        if not timeseries_file:
            print("No time series file selected")
            self.root.withdraw()
            return False
        
        self.replace_all = replace_all
        self.catchment_file = catchment_file
        self.timeseries_file = timeseries_file
        
        self.root.withdraw()
        return True


def main():
    """Main function with command line argument handling."""
    
    # Default file paths (with correct path prefix)
    default_catchment = "../testData/generated_catchment.json"
    default_timeseries = "../testData/modelTimeSeries.json"
    
    # Parse command line arguments
    replace_all = True  # Default behavior: overwrite existing files
    
    # Check command line arguments
    if len(sys.argv) == 1:
        # No arguments - use defaults
        catchment_file = default_catchment
        timeseries_file = default_timeseries
        
    elif len(sys.argv) == 2:
        arg1 = sys.argv[1]
        if arg1 == "--gui":
            # GUI mode requested
            generator = HydrologicalTimeSeriesGenerator(replace_all=replace_all)
            if generator.interactive_file_selection():
                generator.run_generation()
            else:
                print("File selection cancelled")
            return
        elif arg1 == "--no-replace":
            # Don't replace existing files
            replace_all = False
            catchment_file = default_catchment
            timeseries_file = default_timeseries
        else:
            # One argument - assume it's the catchment file
            catchment_file = sys.argv[1]
            timeseries_file = default_timeseries
        
    elif len(sys.argv) == 3:
        arg1, arg2 = sys.argv[1], sys.argv[2]
        if arg1 == "--no-replace":
            # Don't replace existing files, with custom catchment file
            replace_all = False
            catchment_file = arg2
            timeseries_file = default_timeseries
        else:
            # Two arguments - catchment and timeseries files
            catchment_file = arg1
            timeseries_file = arg2
            
    elif len(sys.argv) == 4:
        arg1, arg2, arg3 = sys.argv[1], sys.argv[2], sys.argv[3]
        if arg1 == "--no-replace":
            # Don't replace existing files, with custom files
            replace_all = False
            catchment_file = arg2
            timeseries_file = arg3
        elif arg1 == "--gui":
            print("Error: --gui cannot be combined with file arguments")
            return
        else:
            print("Error: Too many arguments")
            return
        
    else:
        print("Usage:")
        print("  python hydro_timeseries_generator.py")
        print("  python hydro_timeseries_generator.py --no-replace")
        print("  python hydro_timeseries_generator.py <catchment_file>")
        print("  python hydro_timeseries_generator.py --no-replace <catchment_file>")
        print("  python hydro_timeseries_generator.py <catchment_file> <timeseries_file>")
        print("  python hydro_timeseries_generator.py --no-replace <catchment_file> <timeseries_file>")
        print("  python hydro_timeseries_generator.py --gui")
        print("")
        print("Options:")
        print("  --no-replace    Skip files that already exist (default: overwrite)")
        print("  --gui          Interactive file selection mode")
        print("")
        print("Default files:")
        print(f"  Catchment: {default_catchment}")
        print(f"  Time series: {default_timeseries}")
        return
    
    # Check if files exist
    if not os.path.exists(catchment_file):
        print(f"Error: Catchment file not found: {catchment_file}")
        return
    
    if not os.path.exists(timeseries_file):
        print(f"Error: Time series file not found: {timeseries_file}")
        return
    
    # Create generator and run
    print(f"Replace existing files: {'Yes' if replace_all else 'No'}")
    generator = HydrologicalTimeSeriesGenerator(catchment_file, timeseries_file, replace_all)
    generator.run_generation()


if __name__ == "__main__":
    main()
