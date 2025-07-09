#!/usr/bin/env python3
"""
Hydrological Model Time Series Generator

This script generates time series data for hydrological modeling by:
1. Reading catchment structure and time series location files
2. Validating temperature/precipitation data for all HRUs
3. Generating solar radiation time series for each HRU
4. Generating potential evapotranspiration time series for each HRU/landcover combination
5. Generating rain and snow time series for each HRU/landcover combination
6. Generating soil temperature time series for each bucket in each HRU/landcover combination
7. Writing results to specified output locations

Uses only Python standard library components plus existing project code.
All output is written to a log file instead of console.
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
import logging

# Set up logging to file
def setup_logging():
    """Set up logging to write all output to a log file."""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create log filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"hydro_timeseries_generator_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
        ]
    )
    
    # Return the logger and log filename for reference
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_filename}")
    return logger, log_filename

# Initialize logging
logger, log_file_path = setup_logging()

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
    from calculate_rain_and_snow import calculate_rain_and_snow_with_params, load_timeseries_from_files
    from calculate_soil_temperature import calculate_soil_temperature_with_landcover_params
    from timeSeries import TimeSeries
except ImportError as e:
    logger.warning(f"Could not import project modules: {e}")
    logger.warning("Some functionality may be limited.")


class TimeSeriesValidator:
    """Class to validate time series data consistency."""
    
    def __init__(self):
        self.validation_results = {}
    
    def load_timeseries_metadata(self, csv_file_path, json_file_path):
        """Load and parse time series metadata from JSON file."""
        try:
            with open(json_file_path, 'r') as f:
                metadata = json.load(f)
            
            # Extract key information
            start_datetime = metadata.get('start_datetime')
            timestep_seconds = metadata.get('timestep_seconds')
            num_records = metadata.get('num_records')
            
            # Convert start_datetime to datetime object if it's a string
            if isinstance(start_datetime, str):
                try:
                    start_datetime = datetime.datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                except ValueError:
                    # Try alternative parsing
                    start_datetime = datetime.datetime.strptime(start_datetime, "%Y-%m-%dT%H:%M:%S")
            
            return {
                'start_datetime': start_datetime,
                'timestep_seconds': timestep_seconds,
                'num_records': num_records,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error loading metadata from {json_file_path}: {e}")
            return None
    
    def validate_csv_structure(self, csv_file_path):
        """Validate the structure of a CSV file."""
        try:
            with open(csv_file_path, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)  # First row should be headers
                
                # Count actual rows
                row_count = 0
                for row in reader:
                    if row:  # Skip empty rows
                        row_count += 1
                
                return {
                    'valid': True,
                    'headers': headers,
                    'row_count': row_count
                }
                
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def check_timeseries_consistency(self, timeseries_list):
        """Check that all time series have consistent parameters."""
        if not timeseries_list:
            return False, "No time series provided"
        
        # Get reference parameters from first series
        reference = timeseries_list[0]
        ref_start = reference['start_datetime']
        ref_timestep = reference['timestep_seconds']
        ref_records = reference['num_records']
        
        # Check all series against reference
        for i, ts in enumerate(timeseries_list[1:], 1):
            if ts['start_datetime'] != ref_start:
                return False, f"Start datetime mismatch: {ts['hru_name']} has {ts['start_datetime']}, expected {ref_start}"
            
            if ts['timestep_seconds'] != ref_timestep:
                return False, f"Timestep mismatch: {ts['hru_name']} has {ts['timestep_seconds']}s, expected {ref_timestep}s"
            
            if ts['num_records'] != ref_records:
                return False, f"Record count mismatch: {ts['hru_name']} has {ts['num_records']} records, expected {ref_records}"
        
        return True, "All time series are consistent"


class HydrologicalTimeSeriesGenerator:
    """Main class for generating hydrological time series data."""
    
    def __init__(self, catchment_file=None, timeseries_file=None, replace_all=True):
        self.catchment_file = catchment_file
        self.timeseries_file = timeseries_file
        self.replace_all = replace_all
        
        # Data storage
        self.catchment_data = None
        self.timeseries_data = None
        self.base_folder = None
        self.validator = TimeSeriesValidator()
        self.hru_timeseries_info = []
        
        # Initialize GUI support
        self.root = None
        self.setup_gui()
    
    def setup_gui(self):
        """Initialize tkinter for potential GUI operations."""
        try:
            self.root = tk.Tk()
            self.root.withdraw()  # Hide the main window initially
            
            # Try to set the window icon using the established pattern
            icon_paths = [
                "INCAMan.png",
                os.path.join(os.path.dirname(__file__), "INCAMan.png"),
                os.path.join(os.path.dirname(__file__), "..", "INCAMan.png"),
                os.path.join(os.path.dirname(__file__), "..", "..", "INCAMan.png")
            ]
            
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    icon = tk.PhotoImage(file=icon_path)
                    self.root.iconphoto(False, icon)
                    break
                
        except Exception as e:
            logger.warning(f"GUI setup warning: {e}")
    
    def load_json_file(self, file_path):
        """Load and parse a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"File {file_path} not found.")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return None
    
    def load_input_files(self):
        """Load the catchment structure and time series configuration files."""
        logger.info("Loading input files...")
        
        # Load catchment structure
        self.catchment_data = self.load_json_file(self.catchment_file)
        if not self.catchment_data:
            logger.error(f"Failed to load catchment file: {self.catchment_file}")
            return False
        
        # Load time series configuration
        self.timeseries_data = self.load_json_file(self.timeseries_file)
        if not self.timeseries_data:
            logger.error(f"Failed to load time series file: {self.timeseries_file}")
            return False
        
        # Extract base folder for time series files
        try:
            self.base_folder = self.timeseries_data['catchment']['timeSeries']['folder']
            logger.info(f"Time series base folder: {self.base_folder}")
        except KeyError:
            logger.warning("No base folder specified in time series configuration")
            self.base_folder = os.path.dirname(self.timeseries_file)
        
        return True
    
    def validate_temperature_precipitation_files(self):
        """Validate that all HRUs have valid temperature/precipitation files."""
        logger.info("Validating temperature/precipitation files...")
        
        hru_timeseries_info = []
        
        # Check each HRU
        for hru in self.catchment_data.get('HRUs', []):
            hru_name = hru.get('name', 'Unknown')
            logger.info(f"Validating {hru_name}...")
            
            try:
                # Find time series configuration for this HRU
                hru_ts_config = None
                for ts_hru in self.timeseries_data['catchment']['HRUs']:
                    if ts_hru['name'] == hru_name:
                        hru_ts_config = ts_hru
                        break
                
                if not hru_ts_config:
                    logger.error(f"No time series configuration found for {hru_name}")
                    return False
                
                # Get temperature/precipitation file info
                temp_precip_info = hru_ts_config['timeSeries']['subcatchment']['temperatureAndPrecipitation']
                file_name = temp_precip_info['fileName']
                
                # Construct file paths
                csv_path = os.path.join(self.base_folder, f"{file_name}.csv")
                json_path = os.path.join(self.base_folder, f"{file_name}.json")
                
                # Validate files exist
                if not os.path.exists(csv_path):
                    logger.error(f"CSV file not found: {csv_path}")
                    return False
                
                if not os.path.exists(json_path):
                    logger.error(f"JSON file not found: {json_path}")
                    return False
                
                # Load and validate metadata
                metadata_info = self.validator.load_timeseries_metadata(csv_path, json_path)
                if not metadata_info:
                    return False
                
                # Validate CSV structure
                csv_info = self.validator.validate_csv_structure(csv_path)
                if not csv_info['valid']:
                    logger.error(f"Invalid CSV structure for {hru_name}: {csv_info.get('error', 'Unknown error')}")
                    return False
                
                # Store information for consistency check
                metadata_info['hru_name'] = hru_name
                metadata_info['csv_path'] = csv_path
                metadata_info['json_path'] = json_path
                metadata_info['coordinates'] = hru.get('coordinates', {})
                hru_timeseries_info.append(metadata_info)
                
                logger.info(f"  ✓ Valid - {metadata_info['num_records']} records, timestep: {metadata_info['timestep_seconds']}s")
                
            except KeyError as e:
                logger.error(f"Missing temperature/precipitation configuration for {hru_name}: {e}")
                return False
        
        # Check consistency across all HRUs
        logger.info(f"Checking consistency across {len(hru_timeseries_info)} HRUs...")
        consistent, message = self.validator.check_timeseries_consistency(hru_timeseries_info)
        
        if not consistent:
            logger.error(f"Time series inconsistency detected: {message}")
            return False
        
        logger.info("✓ All temperature/precipitation files are valid and consistent")
        
        # Store for later use
        self.hru_timeseries_info = hru_timeseries_info
        return True
    
    def generate_solar_radiation_timeseries(self):
        """Generate solar radiation time series for all HRUs."""
        logger.info("Generating solar radiation time series...")
        
        # Process each HRU
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            coordinates = hru_info['coordinates']
            
            logger.info(f"Processing HRU: {hru_name}")
            
            try:
                # Extract parameters from the time series info
                start_datetime = hru_info['start_datetime']
                timestep_seconds = hru_info['timestep_seconds']
                num_records = hru_info['num_records']
                
                # Calculate end datetime
                total_seconds = num_records * timestep_seconds
                end_datetime = start_datetime + datetime.timedelta(seconds=total_seconds)
                
                # Start from the beginning of the first day
                adjusted_start = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Generate solar radiation data
                solar_data = []
                current_datetime = adjusted_start
                
                for i in range(num_records):
                    # Calculate solar radiation at the midpoint of the timestep
                    # This represents average conditions during the time period
                    midpoint_time = current_datetime + datetime.timedelta(seconds=timestep_seconds / 2)
                    
                    latitude = coordinates.get('decimalLatitude', 45.0)
                    longitude = coordinates.get('decimalLongitude', 0.0)
                    
                    # Simple solar radiation calculation using midpoint time
                    day_of_year = midpoint_time.timetuple().tm_yday
                    hour = midpoint_time.hour + midpoint_time.minute / 60.0
                    
                    # Solar declination
                    declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
                    
                    # Hour angle
                    hour_angle = 15 * (hour - 12)
                    
                    # Solar elevation angle
                    lat_rad = math.radians(latitude)
                    dec_rad = math.radians(declination)
                    hour_rad = math.radians(hour_angle)
                    
                    elevation = math.asin(
                        math.sin(lat_rad) * math.sin(dec_rad) +
                        math.cos(lat_rad) * math.cos(dec_rad) * math.cos(hour_rad)
                    )
                    
                    # Solar radiation (simplified model)
                    if elevation > 0:
                        solar_radiation = 1000 * math.sin(elevation)  # W/m²
                    else:
                        solar_radiation = 0.0
                    
                    solar_data.append([current_datetime.isoformat(), hru_name, solar_radiation])
                    
                    # Move to next timestep
                    current_datetime += datetime.timedelta(seconds=timestep_seconds)
                
                # Create output filename
                output_filename = f"{hru_name}_solarRadiation"
                
                # Check if files already exist
                csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                
                if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                    logger.info(f"  ✓ Skipping (files exist): {output_filename}")
                    continue
                
                # Write CSV file
                with open(csv_output_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['timestamp', 'location', 'solarRadiation'])
                    writer.writerows(solar_data)
                
                # Create metadata
                metadata = {
                    'description': f'Solar radiation time series for {hru_name}',
                    'start_datetime': adjusted_start.isoformat(),
                    'timestep_seconds': timestep_seconds,
                    'num_records': num_records,
                    'coordinates': coordinates,
                    'units': 'W/m²',
                    'calculation_method': 'built-in simple model'
                }
                
                # Write JSON file
                with open(json_output_path, 'w') as jsonfile:
                    json.dump(metadata, jsonfile, indent=4)
                
                logger.info(f"  ✓ Generated: {output_filename}")
                
            except Exception as e:
                logger.error(f"Error generating solar radiation for {hru_name}: {e}")
                return False
        
        return True
    
    def generate_potential_evapotranspiration_timeseries(self):
        """Generate potential evapotranspiration time series for all HRU/landcover combinations."""
        logger.info("Generating potential evapotranspiration time series...")
        
        # Process each HRU
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            logger.info(f"Processing HRU: {hru_name}")
            
            # Get temperature data path
            csv_path = hru_info['csv_path']
            
            # Get landCoverTypes for this HRU from catchment data
            hru_catchment_data = None
            for catchment_hru in self.catchment_data['HRUs']:
                if catchment_hru['name'] == hru_name:
                    hru_catchment_data = catchment_hru
                    break
            
            if not hru_catchment_data:
                logger.error(f"No catchment data found for {hru_name}")
                continue
            
            landcover_types = hru_catchment_data.get('subcatchment', {}).get('landCoverTypes', [])
            if not landcover_types:
                logger.warning(f"No land cover types found for {hru_name}")
                continue
            
            logger.info(f"  Found {len(landcover_types)} land cover types")
            
            # Calculate PET for each landCoverType
            for lc_data in landcover_types:
                lc_name = lc_data.get('name', 'Unknown')
                lc_abbrev = lc_data.get('abbreviation', 'UK')
                
                logger.info(f"    Calculating PET for {lc_name} ({lc_abbrev})")
                
                # Get evaporation parameters
                evap_params = lc_data.get('evaporation', {})
                solar_scaling = evap_params.get('solarRadiationScalingFactor', 60.0)
                degree_offset = evap_params.get('growingDegreeOffset', 0.0)
                
                logger.info(f"      Parameters: solarRadiationScalingFactor={solar_scaling}, growingDegreeOffset={degree_offset}")
                
                try:
                    # Load temperature data
                    temp_data = []
                    with open(csv_path, 'r') as f:
                        reader = csv.reader(f)
                        headers = next(reader)  # Skip header
                        
                        # Find temperature column index
                        temp_idx = None
                        for i, header in enumerate(headers):
                            if 'temperature' in header.lower():
                                temp_idx = i
                                break
                        
                        if temp_idx is None:
                            logger.error(f"No temperature column found in {csv_path}")
                            continue
                        
                        # Process each row
                        for row in reader:
                            if len(row) > temp_idx:
                                try:
                                    timestamp_str = row[0]
                                    location = row[1]
                                    temperature = float(row[temp_idx])
                                    
                                    # Parse timestamp
                                    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    
                                    # Calculate solar radiation at midpoint of timestep (like solar radiation generator)
                                    midpoint_time = timestamp + datetime.timedelta(seconds=hru_info['timestep_seconds'] / 2)
                                    day_of_year = midpoint_time.timetuple().tm_yday
                                    hour = midpoint_time.hour + midpoint_time.minute / 60.0
                                    
                                    # Simplified solar radiation calculation at midpoint
                                    if 6 <= hour <= 18:  # Daylight hours
                                        solar_factor = math.sin(math.pi * (hour - 6) / 12)
                                        rs = 300 * solar_factor  # Simplified calculation
                                    else:
                                        rs = 0.0
                                    
                                    # Convert to MJ/m²/day
                                    rs = rs * 0.0864
                                    
                                    # Calculate adjusted temperature
                                    adjusted_temp = temperature + degree_offset
                                    
                                    # Calculate PET using modified Jensen-Haise equation
                                    if adjusted_temp <= 0.0:
                                        pet = 0.0
                                    else:
                                        pet = rs * (1.0 / solar_scaling) * adjusted_temp
                                    
                                    pet = max(0.0, pet)  # Ensure non-negative
                                    temp_data.append([timestamp.isoformat(), hru_name, pet])
                                except (ValueError, IndexError):
                                    continue
                    
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
                        logger.info(f"      ✓ Skipping (files exist): {output_filename}")
                        continue
                    
                    # Write CSV file
                    with open(csv_output_path, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['timestamp', 'location', 'potentialEvapotranspiration'])
                        writer.writerows(temp_data)
                    
                    # Create metadata
                    metadata = {
                        'description': f'Potential evapotranspiration for {hru_name} - {lc_name}',
                        'start_datetime': hru_info['start_datetime'].isoformat(),
                        'timestep_seconds': hru_info['timestep_seconds'],
                        'num_records': len(temp_data),
                        'hru_name': hru_name,
                        'land_cover_type': lc_name,
                        'degree_offset': degree_offset,
                        'solar_scaling': solar_scaling,
                        'units': 'mm/day',
                        'calculation_method': 'simple temperature-based'
                    }
                    
                    # Write JSON file
                    with open(json_output_path, 'w') as jsonfile:
                        json.dump(metadata, jsonfile, indent=4)
                    
                    logger.info(f"      ✓ Generated: {output_filename}")
                    
                except Exception as e:
                    logger.error(f"Error generating PET for {hru_name}/{lc_name}: {e}")
                    return False
        
        return True
    
    def generate_rain_and_snow_timeseries(self):
        """Generate rain and snow time series for all HRU/landcover combinations."""
        logger.info("Generating rain and snow time series...")
        
        # Process each HRU
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            logger.info(f"Processing HRU: {hru_name}")
            
            # Get temperature and precipitation data paths
            csv_path = hru_info['csv_path']
            
            # Get landCoverTypes for this HRU from catchment data
            hru_catchment_data = None
            for catchment_hru in self.catchment_data['HRUs']:
                if catchment_hru['name'] == hru_name:
                    hru_catchment_data = catchment_hru
                    break
            
            if not hru_catchment_data:
                logger.error(f"No catchment data found for {hru_name}")
                continue
            
            # Get subcatchment parameters
            subcatchment_data = hru_catchment_data.get('subcatchment', {})
            precip_adjustments = subcatchment_data.get('precipitationAdjustments', {})
            snow_offset = precip_adjustments.get('snowOffset', 0.0)
            rain_mult_sc = precip_adjustments.get('rainfallMultiplier', 1.0)
            snow_mult_sc = precip_adjustments.get('snowfallMultiplier', 1.0)
            
            landcover_types = subcatchment_data.get('landCoverTypes', [])
            if not landcover_types:
                logger.warning(f"No land cover types found for {hru_name}")
                continue
            
            logger.info(f"  Found {len(landcover_types)} land cover types")
            
            # Calculate rain and snow for each landCoverType
            for lc_data in landcover_types:
                lc_name = lc_data.get('name', 'Unknown')
                lc_abbrev = lc_data.get('abbreviation', 'UK')
                
                logger.info(f"    Calculating rain/snow for {lc_name} ({lc_abbrev})")
                
                # Get landcover parameters
                rain_mult_lc = lc_data.get('rainfallMultiplier', 1.0)
                snow_mult_lc = lc_data.get('snowfallMultiplier', 1.0)
                snowpack_params = lc_data.get('snowpack', {})
                melt_temp = snowpack_params.get('meltTemperature', 0.0)
                melt_rate = snowpack_params.get('degreeDayMeltRate', 3.0)
                initial_depth = snowpack_params.get('depth', 0.0)
                
                logger.info(f"      Parameters: rain_mult={rain_mult_lc}, snow_mult={snow_mult_lc}, melt_temp={melt_temp}")
                
                try:
                    # Load temperature and precipitation data
                    rain_snow_data = []
                    snowpack_depth = initial_depth  # Track snowpack depth
                    
                    with open(csv_path, 'r') as f:
                        reader = csv.reader(f)
                        headers = next(reader)  # Skip header
                        
                        # Find column indices
                        temp_idx = None
                        precip_idx = None
                        for i, header in enumerate(headers):
                            if 'temperature' in header.lower():
                                temp_idx = i
                            elif 'precipitation' in header.lower():
                                precip_idx = i
                        
                        if temp_idx is None or precip_idx is None:
                            logger.error(f"Required columns not found in {csv_path}")
                            continue
                        
                        # Process each row
                        for row in reader:
                            if len(row) > max(temp_idx, precip_idx):
                                try:
                                    timestamp_str = row[0]
                                    location = row[1]
                                    temperature = float(row[temp_idx])
                                    precipitation = float(row[precip_idx]) if row[precip_idx] else 0.0
                                    
                                    # Parse timestamp
                                    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    
                                    # Determine if precipitation is rain or snow
                                    if temperature > snow_offset:
                                        # Rain
                                        rain_depth = rain_mult_lc * rain_mult_sc * precipitation
                                        snowfall_depth = 0.0
                                    else:
                                        # Snow
                                        rain_depth = 0.0
                                        snowfall_depth = snow_mult_lc * snow_mult_sc * precipitation
                                    
                                    # Calculate snowmelt using degree day model
                                    if temperature > melt_temp:
                                        # Potential melt
                                        potential_melt = melt_rate * (temperature - melt_temp)
                                        
                                        # Actual melt is limited by available snow (previous snowpack + new snowfall)
                                        available_snow = snowpack_depth + snowfall_depth
                                        actual_melt = min(potential_melt, available_snow)
                                    else:
                                        actual_melt = 0.0
                                    
                                    # Update snowpack depth
                                    snowpack_depth = snowpack_depth + snowfall_depth - actual_melt
                                    snowpack_depth = max(0.0, snowpack_depth)  # Cannot be negative
                                    
                                    # Store the calculated values
                                    rain_snow_data.append([
                                        timestamp.isoformat(),
                                        location,
                                        temperature,      # air_temperature
                                        snowfall_depth,   # snowfall_depth
                                        rain_depth,       # rain_depth
                                        snowpack_depth,   # snowpack_depth
                                        actual_melt       # snowmelt_depth
                                    ])
                                except (ValueError, IndexError):
                                    continue
                    
                    if len(rain_snow_data) == 0:
                        logger.warning(f"No rain/snow data generated for {hru_name}/{lc_name}")
                        continue
                    
                    logger.info(f"      Generated {len(rain_snow_data)} rain/snow records")
                    
                    # Find output filename from time series configuration
                    output_filename = None
                    for ts_hru in self.timeseries_data['catchment']['HRUs']:
                        if ts_hru['name'] == hru_name:
                            try:
                                landcover_types_ts = ts_hru['timeSeries']['subcatchment']['landCoverTypes']
                                for lc_ts in landcover_types_ts:
                                    if lc_ts['name'] == lc_name:
                                        rain_snow_info = lc_ts['timeSeries']['rainAndSnow']
                                        output_filename = rain_snow_info['fileName']
                                        break
                                if output_filename:
                                    break
                            except KeyError:
                                pass
                    
                    if not output_filename:
                        output_filename = f"{hru_name}_{lc_name}_rainAndSnow"
                    
                    # Check if files already exist
                    csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                    json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                    
                    if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                        logger.info(f"      ✓ Skipping (files exist): {output_filename}")
                        continue
                    
                    # Write CSV file
                    with open(csv_output_path, 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow(['timestamp', 'location', 'air_temperature', 'snowfall_depth', 'rain_depth', 'snowpack_depth', 'snowmelt_depth'])
                        writer.writerows(rain_snow_data)
                    
                    # Create metadata
                    metadata = {
                        'description': f'Rain and snow dynamics for {hru_name} - {lc_name}',
                        'start_datetime': hru_info['start_datetime'].isoformat(),
                        'timestep_seconds': hru_info['timestep_seconds'],
                        'num_records': len(rain_snow_data),
                        'hru_name': hru_name,
                        'land_cover_type': lc_name,
                        'snow_offset': snow_offset,
                        'rain_multiplier_sc': rain_mult_sc,
                        'snow_multiplier_sc': snow_mult_sc,
                        'rain_multiplier_lc': rain_mult_lc,
                        'snow_multiplier_lc': snow_mult_lc,
                        'melt_temperature': melt_temp,
                        'degree_day_melt_rate': melt_rate,
                        'initial_snowpack_depth': initial_depth,
                        'units': {
                            'air_temperature': 'degrees_C',
                            'snowfall_depth': 'mm',
                            'rain_depth': 'mm',
                            'snowpack_depth': 'mm_SWE',
                            'snowmelt_depth': 'mm'
                        },
                        'calculation_method': 'degree-day snowmelt model with scaling factors'
                    }
                    
                    # Write JSON file
                    with open(json_output_path, 'w') as jsonfile:
                        json.dump(metadata, jsonfile, indent=4)
                    
                    logger.info(f"      ✓ Generated: {output_filename}")
                    
                except Exception as e:
                    logger.error(f"Error generating rain/snow for {hru_name}/{lc_name}: {e}")
                    return False
        
        return True
    
    def generate_soil_temperature_timeseries(self):
        """Generate soil temperature time series for all buckets in each HRU/landcover combination."""
        logger.info("Generating soil temperature time series...")
        
        # Process each HRU
        for hru_info in self.hru_timeseries_info:
            hru_name = hru_info['hru_name']
            logger.info(f"Processing HRU: {hru_name}")
            
            # Get landCoverTypes for this HRU from catchment data
            hru_catchment_data = None
            for catchment_hru in self.catchment_data['HRUs']:
                if catchment_hru['name'] == hru_name:
                    hru_catchment_data = catchment_hru
                    break
            
            if not hru_catchment_data:
                logger.error(f"No catchment data found for {hru_name}")
                continue
            
            landcover_types = hru_catchment_data.get('subcatchment', {}).get('landCoverTypes', [])
            if not landcover_types:
                logger.warning(f"No land cover types found for {hru_name}")
                continue
            
            logger.info(f"  Found {len(landcover_types)} land cover types")
            
            # Process each landCoverType
            for lc_data in landcover_types:
                lc_name = lc_data.get('name', 'Unknown')
                lc_abbrev = lc_data.get('abbreviation', 'UK')
                
                logger.info(f"    Processing soil temperature for {lc_name} ({lc_abbrev})")
                
                # Find the corresponding rain and snow file to use as input
                rain_snow_filename = None
                for ts_hru in self.timeseries_data['catchment']['HRUs']:
                    if ts_hru['name'] == hru_name:
                        try:
                            landcover_types_ts = ts_hru['timeSeries']['subcatchment']['landCoverTypes']
                            for lc_ts in landcover_types_ts:
                                if lc_ts['name'] == lc_name:
                                    rain_snow_info = lc_ts['timeSeries']['rainAndSnow']
                                    rain_snow_filename = rain_snow_info['fileName']
                                    break
                            if rain_snow_filename:
                                break
                        except KeyError:
                            pass
                
                if not rain_snow_filename:
                    rain_snow_filename = f"{hru_name}_{lc_name}_rainAndSnow"
                    logger.warning(f"Rain/snow filename not found, using default: {rain_snow_filename}")
                
                # Load the rain and snow time series (contains air temperature and snow depth)
                try:
                    rain_snow_csv = os.path.join(self.base_folder, f"{rain_snow_filename}.csv")
                    rain_snow_json = os.path.join(self.base_folder, f"{rain_snow_filename}.json")
                    
                    if not os.path.exists(rain_snow_csv) or not os.path.exists(rain_snow_json):
                        logger.error(f"Rain/snow files not found: {rain_snow_filename}")
                        continue
                    
                    # Load the rain and snow time series using local function
                    rain_snow_csv = os.path.join(self.base_folder, f"{rain_snow_filename}.csv")
                    rain_snow_json = os.path.join(self.base_folder, f"{rain_snow_filename}.json")
                    
                    if not os.path.exists(rain_snow_csv) or not os.path.exists(rain_snow_json):
                        logger.error(f"Rain/snow files not found: {rain_snow_filename}")
                        continue
                    
                    # Load metadata from JSON
                    try:
                        with open(rain_snow_json, 'r') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        logger.error(f"Error loading JSON metadata: {e}")
                        continue
                    
                    # Load data from CSV
                    data = []
                    columns = []
                    
                    try:
                        with open(rain_snow_csv, 'r') as f:
                            reader = csv.reader(f)
                            columns = next(reader)  # First row is header
                            
                            for row in reader:
                                if not row:  # Skip empty rows
                                    continue
                                
                                try:
                                    # Convert timestamp to datetime object
                                    timestamp_str = row[0]
                                    timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    
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
                                
                                except Exception:
                                    continue  # Skip problematic rows
                    
                    except Exception as e:
                        logger.error(f"Error reading CSV file: {e}")
                        continue
                    
                    # Create TimeSeries object
                    TSClass = TimeSeries if TimeSeries is not None else SimplifiedTimeSeries
                    input_ts = TSClass()
                    input_ts.columns = columns
                    input_ts.data = data
                    input_ts.metadata = metadata
                    
                    # Get timestep from metadata
                    timestep_seconds = hru_info['timestep_seconds']
                    
                    # Calculate soil temperature for all buckets in this landcover
                    bucket_results = calculate_soil_temperature_with_landcover_params(
                        input_timeseries=input_ts,
                        landcover_params=lc_data,
                        timestep_seconds=timestep_seconds,
                        temp_column="air_temperature",
                        snow_column="snowpack_depth"
                    )
                    
                    logger.info(f"      Generated soil temperature for {len(bucket_results)} buckets")
                    
                    # Save results for each bucket
                    for bucket_name, soil_ts in bucket_results.items():
                        bucket_abbrev = ""
                        
                        # Find bucket abbreviation
                        for bucket in lc_data.get('buckets', []):
                            if bucket.get('name') == bucket_name:
                                bucket_abbrev = bucket.get('abbreviation', '')
                                break
                        
                        # Create output filename
                        safe_hru = hru_name.replace(" ", "_")
                        safe_lc = lc_name.replace(" ", "_")
                        safe_bucket = bucket_name.replace(" ", "_")
                        output_filename = f"{safe_hru}_{safe_lc}_{safe_bucket}_soilTemperature"
                        
                        # Check if files already exist
                        csv_output_path = os.path.join(self.base_folder, f"{output_filename}.csv")
                        json_output_path = os.path.join(self.base_folder, f"{output_filename}.json")
                        
                        if not self.replace_all and os.path.exists(csv_output_path) and os.path.exists(json_output_path):
                            logger.info(f"        ✓ Skipping (files exist): {output_filename}")
                            continue
                        
                        # Extract soil temperature data for CSV
                        soil_temp_data = []
                        
                        # Find the soil temperature column index
                        soil_temp_idx = None
                        for i, col in enumerate(soil_ts.columns):
                            if 'soil_temperature' in str(col).lower():
                                soil_temp_idx = i
                                break
                        
                        if soil_temp_idx is None:
                            logger.error(f"        Could not find soil temperature column in {soil_ts.columns}")
                            continue
                        
                        for row in soil_ts.data:
                            if len(row) > soil_temp_idx:
                                timestamp = row[0]
                                location = row[1] if len(row) > 1 else "Unknown"
                                soil_temp = row[soil_temp_idx] if row[soil_temp_idx] is not None else None
                                
                                if soil_temp is not None:
                                    soil_temp_data.append([
                                        timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
                                        location,
                                        soil_temp
                                    ])
                        
                        if len(soil_temp_data) == 0:
                            logger.warning(f"No soil temperature data generated for {bucket_name}")
                            continue
                        
                        # Write CSV file
                        with open(csv_output_path, 'w', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow(['timestamp', 'location', 'soil_temperature_c'])
                            writer.writerows(soil_temp_data)
                        
                        # Create metadata
                        metadata = {
                            'description': f'Soil temperature for {hru_name} - {lc_name} - {bucket_name}',
                            'start_datetime': hru_info['start_datetime'].isoformat(),
                            'timestep_seconds': hru_info['timestep_seconds'],
                            'num_records': len(soil_temp_data),
                            'hru_name': hru_name,
                            'land_cover_type': lc_name,
                            'bucket_name': bucket_name,
                            'bucket_abbreviation': bucket_abbrev,
                            'thermal_conductivity': soil_ts.metadata.get('thermal_conductivity', 'unknown'),
                            'specific_heat_capacity': soil_ts.metadata.get('specific_heat_capacity', 'unknown'),
                            'snow_depth_factor': soil_ts.metadata.get('snow_depth_factor', 'unknown'),
                            'effective_depth': soil_ts.metadata.get('effective_depth', 'unknown'),
                            'initial_temperature': soil_ts.metadata.get('initial_temperature', 'unknown'),
                            'receives_precipitation': soil_ts.metadata.get('receives_precipitation', 'unknown'),
                            'units': 'degrees_C',
                            'calculation_method': 'thermal conductivity model with snow insulation'
                        }
                        
                        # Write JSON file
                        with open(json_output_path, 'w') as jsonfile:
                            json.dump(metadata, jsonfile, indent=4)
                        
                        logger.info(f"        ✓ Generated: {output_filename}")
                    
                except Exception as e:
                    logger.error(f"Error generating soil temperature for {hru_name}/{lc_name}: {e}")
                    return False
        
        return True
    
    def run_generation(self):
        """Run the complete time series generation process."""
        logger.info("=" * 60)
        logger.info("HYDROLOGICAL MODEL TIME SERIES GENERATOR")
        logger.info("=" * 60)
        logger.info(f"Replace existing files: {'Yes' if self.replace_all else 'No (--no-replace)'}")
        logger.info("=" * 60)
        
        # Step 1: Load input files
        if not self.load_input_files():
            logger.error("Generation failed: Could not load input files")
            return False
        
        # Step 2: Validate temperature/precipitation files
        if not self.validate_temperature_precipitation_files():
            logger.error("Generation failed: Temperature/precipitation validation failed")
            return False
        
        # Step 3: Generate solar radiation time series
        if not self.generate_solar_radiation_timeseries():
            logger.error("Generation failed: Solar radiation generation failed")
            return False
        
        # Step 4: Generate potential evapotranspiration time series
        if not self.generate_potential_evapotranspiration_timeseries():
            logger.error("Generation failed: Potential evapotranspiration generation failed")
            return False
        
        # Step 5: Generate rain and snow time series
        if not self.generate_rain_and_snow_timeseries():
            logger.error("Generation failed: Rain and snow generation failed")
            return False
        
        # Step 6: Generate soil temperature time series
        if not self.generate_soil_temperature_timeseries():
            logger.error("Generation failed: Soil temperature generation failed")
            return False
        
        logger.info("=" * 60)
        logger.info("TIME SERIES GENERATION COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info("Generated time series:")
        logger.info("✓ Solar radiation for each HRU")
        logger.info("✓ Potential evapotranspiration for each HRU/landCoverType combination")
        logger.info("✓ Rain and snow dynamics for each HRU/landCoverType combination")
        logger.info("✓ Soil temperature for each bucket in each HRU/landCoverType combination")
        logger.info("")
        logger.info("Next steps (not yet implemented):")
        logger.info("- Precipitation routing between buckets")
        logger.info("- Flow calculations to and within reaches")
        
        return True
    
    def interactive_file_selection(self):
        """Allow user to interactively select input files."""
        if not self.root:
            logger.error("GUI not available for file selection")
            return False
        
        self.root.deiconify()  # Show the window
        
        # Select catchment file
        catchment_file = filedialog.askopenfilename(
            title="Select Catchment Structure File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="generated_catchment.json"
        )
        
        if not catchment_file:
            logger.info("No catchment file selected")
            self.root.withdraw()
            return False
        
        # Select time series file
        timeseries_file = filedialog.askopenfilename(
            title="Select Model Time Series File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="modelTimeSeries.json"
        )
        
        if not timeseries_file:
            logger.info("No time series file selected")
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
                logger.info("File selection cancelled")
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
            logger.error("--gui cannot be combined with file arguments")
            return
        else:
            logger.error("Too many arguments")
            return
        
    else:
        usage_message = """Usage:
  python hydro_timeseries_generator.py
  python hydro_timeseries_generator.py --no-replace
  python hydro_timeseries_generator.py <catchment_file>
  python hydro_timeseries_generator.py --no-replace <catchment_file>
  python hydro_timeseries_generator.py <catchment_file> <timeseries_file>
  python hydro_timeseries_generator.py --no-replace <catchment_file> <timeseries_file>
  python hydro_timeseries_generator.py --gui

Options:
  --no-replace    Skip files that already exist (default: overwrite)
  --gui          Interactive file selection mode

Default files:
  Catchment: {default_catchment}
  Time series: {default_timeseries}""".format(
            default_catchment=default_catchment,
            default_timeseries=default_timeseries
        )
        logger.info(usage_message)
        return
    
    # Check if files exist
    if not os.path.exists(catchment_file):
        logger.error(f"Catchment file not found: {catchment_file}")
        return
    
    if not os.path.exists(timeseries_file):
        logger.error(f"Time series file not found: {timeseries_file}")
        return
    
    # Create generator and run
    logger.info(f"Replace existing files: {'Yes' if replace_all else 'No'}")
    logger.info(f"Log file: {log_file_path}")
    generator = HydrologicalTimeSeriesGenerator(catchment_file, timeseries_file, replace_all)
    generator.run_generation()


if __name__ == "__main__":
    main()
