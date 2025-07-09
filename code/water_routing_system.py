#!/usr/bin/env python3
"""
Water Routing System for INCA/PERSiST Model

This module implements water routing between buckets in landcover types based on
the specifications provided. It processes time series data and routes water
through bucket systems according to evapotranspiration and runoff calculations.

The system reads configuration from:
- testData/generated_catchment.json (catchment structure and parameters)
- testData/ModelTimeSeries.json (time series file mappings)

Usage:
    python water_routing_system.py [testData_folder]

Requirements:
    - generated_catchment.json in testData folder
    - ModelTimeSeries.json in testData folder
    - Time series files in testData folder
"""

import json
import csv
import os
import sys
import datetime
import math
import uuid
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple


class TimeSeries:
    """Simple TimeSeries class for handling time series data."""
    
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
    
    def save_to_files(self, base_name, output_dir=None):
        if output_dir:
            csv_filename = os.path.join(output_dir, f"{base_name}.csv")
            json_filename = os.path.join(output_dir, f"{base_name}.json")
        else:
            csv_filename = f"{base_name}.csv"
            json_filename = f"{base_name}.json"
        
        # Save data to CSV
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
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
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.metadata, jsonfile, indent=4)
        
        return csv_filename, json_filename


class WaterRoutingSystem:
    """Main class for water routing between buckets in landcover types."""
    
    def __init__(self, testdata_folder="testData"):
        self.testdata_folder = testdata_folder
        self.catchment_data = None
        self.timeseries_config = None
        self.time_series_data = {}
        self.results = {}
        
        # File paths
        self.catchment_file = os.path.join(testdata_folder, "generated_catchment.json")
        self.timeseries_file = os.path.join(testdata_folder, "ModelTimeSeries.json")
        
    def load_data(self):
        """Load catchment and time series configuration data."""
        print("Loading catchment data...")
        try:
            with open(self.catchment_file, 'r', encoding='utf-8') as f:
                self.catchment_data = json.load(f)
            print(f"  ✓ Loaded catchment: {self.catchment_data.get('name', 'Unknown')}")
            
            # Fix precipitation flags if needed
            self.fix_precipitation_flags()
            
        except Exception as e:
            print(f"  ✗ Error loading catchment file: {e}")
            return False
            
        print("Loading time series configuration...")
        try:
            with open(self.timeseries_file, 'r', encoding='utf-8') as f:
                self.timeseries_config = json.load(f)
            print(f"  ✓ Loaded time series config for {len(self.timeseries_config.get('catchment', {}).get('HRUs', []))} HRUs")
        except Exception as e:
            print(f"  ✗ Error loading time series config: {e}")
            return False
            
        return True
        
    def fix_precipitation_flags(self):
        """Fix receivesPrecipitation flags - typically the first bucket should receive precipitation."""
        print("  Checking precipitation flags...")
        
        hrus = self.catchment_data.get('HRUs', [])
        changes_made = False
        
        for hru in hrus:
            hru_name = hru.get('name', 'Unknown')
            subcatchment = hru.get('subcatchment', {})
            landcover_types = subcatchment.get('landCoverTypes', [])
            
            for landcover in landcover_types:
                landcover_name = landcover.get('name', 'Unknown')
                buckets = landcover.get('buckets', [])
                
                # Check if any bucket receives precipitation
                has_precipitation_bucket = any(bucket.get('receivesPrecipitation', False) for bucket in buckets)
                
                if not has_precipitation_bucket and buckets:
                    # Set the first bucket to receive precipitation
                    buckets[0]['receivesPrecipitation'] = True
                    changes_made = True
                    print(f"    ✓ Set {hru_name}/{landcover_name}/{buckets[0].get('name', 'Bucket_0')} to receive precipitation")
                    
        if not changes_made:
            print("    No changes needed to precipitation flags")
        
    def load_time_series_file(self, filename):
        """Load a single time series file (CSV + JSON)."""
        csv_path = os.path.join(self.testdata_folder, f"{filename}.csv")
        json_path = os.path.join(self.testdata_folder, f"{filename}.json")
        
        if not os.path.exists(csv_path) or not os.path.exists(json_path):
            return None
            
        try:
            # Load metadata
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Load CSV data
            data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Parse timestamp from first column (UUID column)
                    timestamp_str = None
                    location = row.get('location', 'default')
                    
                    # Find timestamp column
                    for key, value in row.items():
                        if key != 'location' and len(str(value)) > 15 and 'T' in str(value):
                            timestamp_str = str(value)
                            break
                    
                    if timestamp_str:
                        try:
                            timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('T', ' '))
                            data.append({
                                'timestamp': timestamp,
                                'location': location,
                                'row': row
                            })
                        except ValueError:
                            continue
            
            return {
                'metadata': metadata,
                'data': data
            }
            
        except Exception as e:
            print(f"  Warning: Error loading {filename}: {e}")
            return None
            
    def get_input_files(self):
        """Get all required input files from the time series configuration."""
        input_files = {}
        
        if not self.timeseries_config:
            return input_files
            
        catchment_config = self.timeseries_config.get('catchment', {})
        hrus = catchment_config.get('HRUs', [])
        
        for hru in hrus:
            hru_name = hru.get('name', '')
            subcatchment = hru.get('timeSeries', {}).get('subcatchment', {})
            landcover_types = subcatchment.get('landCoverTypes', [])
            
            for landcover in landcover_types:
                landcover_name = landcover.get('name', '')
                landcover_ts = landcover.get('timeSeries', {})
                
                # Get input files
                pet_file = landcover_ts.get('potentialEvapotranspiration', {}).get('fileName')
                rain_snow_file = landcover_ts.get('rainAndSnow', {}).get('fileName')
                
                if pet_file and rain_snow_file:
                    key = f"{hru_name}_{landcover_name}"
                    input_files[key] = {
                        'pet_file': pet_file,
                        'rain_snow_file': rain_snow_file,
                        'hru_name': hru_name,
                        'landcover_name': landcover_name
                    }
                    
        return input_files
        
    def get_output_files(self):
        """Get all required output files from the time series configuration."""
        output_files = {}
        
        if not self.timeseries_config:
            return output_files
            
        catchment_config = self.timeseries_config.get('catchment', {})
        hrus = catchment_config.get('HRUs', [])
        
        for hru in hrus:
            hru_name = hru.get('name', '')
            subcatchment = hru.get('timeSeries', {}).get('subcatchment', {})
            landcover_types = subcatchment.get('landCoverTypes', [])
            
            for landcover in landcover_types:
                landcover_name = landcover.get('name', '')
                landcover_ts = landcover.get('timeSeries', {})
                buckets = landcover_ts.get('buckets', [])
                
                key = f"{hru_name}_{landcover_name}"
                output_files[key] = {
                    'hru_name': hru_name,
                    'landcover_name': landcover_name,
                    'buckets': []
                }
                
                for bucket in buckets:
                    bucket_name = bucket.get('name', '')
                    bucket_ts = bucket.get('timeSeries', {})
                    
                    output_files[key]['buckets'].append({
                        'bucket_name': bucket_name,
                        'aet_file': bucket_ts.get('actualEvapotranspiration', {}).get('fileName'),
                        'water_level_file': bucket_ts.get('waterLevel', {}).get('fileName'),
                        'water_inputs_file': bucket_ts.get('waterInputs', {}).get('fileName'),
                        'water_outputs_file': bucket_ts.get('waterOutputs', {}).get('fileName')
                    })
                    
        return output_files
        
    def run_simulation(self):
        """Run the complete water routing simulation."""
        print("\n" + "="*60)
        print("WATER ROUTING SIMULATION")
        print("="*60)
        
        # Get input and output file mappings
        input_files = self.get_input_files()
        output_files = self.get_output_files()
        
        print(f"Found {len(input_files)} landcover combinations to process")
        
        # Load required time series data
        print("\nLoading time series data...")
        loaded_files = set()
        
        for key, files in input_files.items():
            pet_file = files['pet_file']
            rain_snow_file = files['rain_snow_file']
            
            if pet_file not in loaded_files:
                print(f"  Loading {pet_file}...")
                self.time_series_data[pet_file] = self.load_time_series_file(pet_file)
                loaded_files.add(pet_file)
                
            if rain_snow_file not in loaded_files:
                print(f"  Loading {rain_snow_file}...")
                self.time_series_data[rain_snow_file] = self.load_time_series_file(rain_snow_file)
                loaded_files.add(rain_snow_file)
        
        # Process each landcover combination
        print("\nProcessing landcover combinations...")
        for key in input_files:
            print(f"\nProcessing {key}...")
            self.process_landcover_combination(key, input_files[key], output_files.get(key, {}))
            
        # Generate output files
        print("\nGenerating output files...")
        self.generate_output_files(output_files)
        
        print("\n" + "="*60)
        print("SIMULATION COMPLETED")
        print("="*60)
        
    def process_landcover_combination(self, key, input_files, output_config):
        """Process a single landcover combination."""
        hru_name = input_files['hru_name']
        landcover_name = input_files['landcover_name']
        
        # Get catchment structure for this combination
        landcover_data = self.find_landcover_data(hru_name, landcover_name)
        if not landcover_data:
            print(f"  ✗ Could not find landcover data for {key}")
            return
            
        # Get time series data
        pet_data = self.time_series_data.get(input_files['pet_file'])
        rain_snow_data = self.time_series_data.get(input_files['rain_snow_file'])
        
        if not pet_data or not rain_snow_data:
            print(f"  ✗ Missing time series data for {key}")
            return
            
        # Calculate TSF from time series metadata
        tsf = self.calculate_tsf(pet_data)
        print(f"  TSF: {tsf:.4f}")
        
        # Get bucket configuration
        buckets = landcover_data.get('buckets', [])
        print(f"  Processing {len(buckets)} buckets")
        
        # Initialize bucket states
        bucket_states = self.initialize_bucket_states(buckets)
        
        # Process time series
        results = self.process_time_series(bucket_states, buckets, pet_data, rain_snow_data, tsf)
        
        # Store results
        self.results[key] = results
        print(f"  ✓ Processed {len(results['water_levels'])} timesteps")
        
    def find_landcover_data(self, hru_name, landcover_name):
        """Find landcover data in catchment structure."""
        if not self.catchment_data:
            return None
            
        hrus = self.catchment_data.get('HRUs', [])
        for hru in hrus:
            if hru.get('name') == hru_name:
                subcatchment = hru.get('subcatchment', {})
                landcover_types = subcatchment.get('landCoverTypes', [])
                
                for landcover in landcover_types:
                    if landcover.get('name') == landcover_name:
                        return landcover
                        
        return None
        
    def calculate_tsf(self, time_series_data):
        """Calculate Temporal Scaling Factor (TSF)."""
        if not time_series_data:
            return 1.0
            
        metadata = time_series_data.get('metadata', {})
        timestep_seconds = metadata.get('timestep_seconds', 86400)
        return timestep_seconds / 86400.0
        
    def initialize_bucket_states(self, buckets):
        """Initialize bucket states from catchment data."""
        bucket_states = []
        
        for bucket in buckets:
            water_depth = bucket.get('waterDepth', {})
            state = {
                'current_depth': water_depth.get('current', 1.0),
                'tightly_bound': water_depth.get('tightlyBound', 100.0),
                'plant_available': water_depth.get('plantAvailable', 200.0),
                'bucket_data': bucket
            }
            bucket_states.append(state)
            
        return bucket_states
        
    def process_time_series(self, bucket_states, buckets, pet_data, rain_snow_data, tsf):
        """Process the complete time series through bucket system."""
        # Initialize results
        results = {
            'buckets': [bucket.get('name', f'Bucket_{i}') for i, bucket in enumerate(buckets)],
            'water_levels': [],
            'evapotranspiration': [],
            'runoff': [],
            'water_inputs': [],
            'water_outputs': []
        }
        
        # Get data arrays
        pet_records = pet_data.get('data', [])
        rain_snow_records = rain_snow_data.get('data', [])
        
        # Process each timestep
        num_timesteps = min(len(pet_records), len(rain_snow_records))
        
        for t in range(num_timesteps):
            if t % 100 == 0:
                print(f"    Timestep {t+1}/{num_timesteps}")
                
            # Get input data
            pet_row = pet_records[t]
            rain_snow_row = rain_snow_records[t]
            
            # Extract values
            pet_value = self.extract_time_series_value(pet_row, 'pet')
            rain_depth = self.extract_time_series_value(rain_snow_row, 'rain_depth')
            snow_depth = self.extract_time_series_value(rain_snow_row, 'snowmelt_depth')
            
            # Debug output for first few timesteps
            if t < 3:
                print(f"    Timestep {t+1}: PET={pet_value:.3f}, Rain={rain_depth:.3f}, Snow={snow_depth:.3f}")
            
            # Process timestep
            timestep_results = self.process_timestep(bucket_states, buckets, rain_depth, snow_depth, pet_value, tsf)
            
            # Store results
            results['water_levels'].append([state['current_depth'] for state in bucket_states])
            results['evapotranspiration'].append(timestep_results['evapotranspiration'])
            results['runoff'].append(timestep_results['runoff'])
            results['water_inputs'].append(timestep_results['water_inputs'])
            results['water_outputs'].append(timestep_results['water_outputs'])
            
        return results
        
    def extract_time_series_value(self, row, value_name):
        """Extract a specific value from a time series row."""
        row_data = row.get('row', {})
        
        # Define alternative names to search for
        search_terms = {
            'pet': ['pet', 'evapotranspiration', 'potential_evapotranspiration'],
            'rain_depth': ['rain_depth', 'rain', 'rainfall', 'precipitation'],
            'snowmelt_depth': ['snowmelt_depth', 'snowmelt', 'snow_melt', 'snow']
        }
        
        # Get search terms for this value
        terms_to_search = search_terms.get(value_name, [value_name])
        
        # Look for the value in the row
        for key, value in row_data.items():
            for term in terms_to_search:
                if term.lower() in key.lower():
                    try:
                        return float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        continue
        
        # Debug: print available columns if value not found (only for first few calls)
        if not hasattr(self, '_debug_count'):
            self._debug_count = 0
        if self._debug_count < 5:
            print(f"    Warning: Could not find '{value_name}' in row. Available columns: {list(row_data.keys())}")
            self._debug_count += 1
                    
        return 0.0
        
    def process_timestep(self, bucket_states, buckets, rain_depth, snow_depth, pet_value, tsf):
        """Process a single timestep through all buckets."""
        total_precipitation = rain_depth + snow_depth
        
        # Initialize results
        timestep_results = {
            'evapotranspiration': [],
            'runoff': [],
            'water_inputs': [],
            'water_outputs': []
        }
        
        # Calculate water inputs to each bucket
        water_inputs = [0.0] * len(buckets)
        
        # Add precipitation to buckets that receive it
        precipitation_added = False
        for i, bucket in enumerate(buckets):
            if bucket.get('receivesPrecipitation', False):
                water_inputs[i] += total_precipitation
                precipitation_added = True
                # Only show first timestep for each landcover
                if not hasattr(self, '_precipitation_shown'):
                    self._precipitation_shown = set()
                if f"{bucket.get('name', 'Unknown')}" not in self._precipitation_shown:
                    print(f"      Bucket {i} ({bucket.get('name', 'Unknown')}) receives precipitation")
                    self._precipitation_shown.add(f"{bucket.get('name', 'Unknown')}")
        
        if not precipitation_added and total_precipitation > 0:
            if not hasattr(self, '_no_precipitation_warned'):
                self._no_precipitation_warned = True
                print(f"      Warning: No buckets receive precipitation (rain: {rain_depth:.3f}, snow: {snow_depth:.3f})")
                print(f"      Bucket precipitation flags: {[bucket.get('receivesPrecipitation', False) for bucket in buckets]}")
                
        # Process each bucket in order
        for i, (bucket_state, bucket_data) in enumerate(zip(bucket_states, buckets)):
            initial_depth = bucket_state['current_depth']
            
            # Step 1: Add water to bucket
            bucket_state['current_depth'] += water_inputs[i]
            
            # Step 2: Calculate actual evapotranspiration
            aet = self.calculate_aet(bucket_state, bucket_data, pet_value)
            timestep_results['evapotranspiration'].append(aet)
            
            # Step 3: Subtract AET from water depth
            bucket_state['current_depth'] -= aet
            bucket_state['current_depth'] = max(0, bucket_state['current_depth'])
            
            # Step 4: Calculate runoff
            runoff = self.calculate_runoff(bucket_state, bucket_data, tsf)
            timestep_results['runoff'].append(runoff)
            
            # Step 5: Subtract runoff from water depth
            bucket_state['current_depth'] -= runoff
            bucket_state['current_depth'] = max(0, bucket_state['current_depth'])
            
            # Step 6: Partition runoff to other buckets and stream
            self.partition_runoff(i, runoff, bucket_data, water_inputs, buckets)
            
            # Debug output for first few timesteps
            if not hasattr(self, '_timestep_debug_count'):
                self._timestep_debug_count = 0
            if self._timestep_debug_count < 3:  # Only for first 3 calls to this function
                print(f"      Bucket {i} ({bucket_data.get('name', 'Unknown')}): {initial_depth:.1f} -> {bucket_state['current_depth']:.1f} mm (input: {water_inputs[i]:.3f}, AET: {aet:.3f}, runoff: {runoff:.3f})")
            
        # Increment debug counter after processing all buckets
        if hasattr(self, '_timestep_debug_count'):
            self._timestep_debug_count += 1
            
        # Store input/output information
        timestep_results['water_inputs'] = water_inputs.copy()
        timestep_results['water_outputs'] = timestep_results['runoff'].copy()
        
        return timestep_results
        
    def calculate_aet(self, bucket_state, bucket_data, pet_value):
        """Calculate actual evapotranspiration for a bucket."""
        current_depth = bucket_state['current_depth']
        tightly_bound = bucket_state['tightly_bound']
        plant_available = bucket_state['plant_available']
        
        # Get evaporation parameters
        evap_params = bucket_data.get('evaporation', {})
        relative_amount_index = evap_params.get('relativeAmountIndex', 0.0)
        drought_adjustment = evap_params.get('droughtAdjustment', 1.0)
        
        # Only calculate AET if relativeAmountIndex > 0
        if relative_amount_index <= 0.0:
            return 0.0
            
        # Check water depth thresholds
        if current_depth <= tightly_bound:
            # No evapotranspiration can occur
            return 0.0
            
        elif current_depth <= (tightly_bound + plant_available):
            # Evapotranspiration only (no runoff)
            available_water = current_depth - tightly_bound
            stress_factor = (available_water / plant_available) ** drought_adjustment
            aet = min(relative_amount_index * pet_value * stress_factor, available_water)
            return aet
            
        else:
            # Both evapotranspiration and runoff can occur
            available_water_for_et = current_depth - (tightly_bound + plant_available)
            
            if current_depth >= (tightly_bound + plant_available) + pet_value:
                # Condition (i): plenty of water
                aet = relative_amount_index * pet_value
            else:
                # Condition (ii): limited water
                stress_component = min(
                    relative_amount_index * pet_value * ((current_depth - tightly_bound) / plant_available) ** drought_adjustment,
                    current_depth - tightly_bound
                )
                aet = relative_amount_index * available_water_for_et + stress_component
                
            return aet
            
    def calculate_runoff(self, bucket_state, bucket_data, tsf):
        """Calculate runoff from a bucket."""
        current_depth = bucket_state['current_depth']
        tightly_bound = bucket_state['tightly_bound']
        plant_available = bucket_state['plant_available']
        
        # Check if runoff can occur
        if current_depth <= (tightly_bound + plant_available):
            return 0.0
            
        # Get characteristic time constant
        time_constant = bucket_data.get('characteristicTimeConstant', 10.0)
        
        # Calculate runoff
        runoff = (1.0 / (tsf * time_constant)) * (current_depth - plant_available - tightly_bound)
        return max(0.0, runoff)
        
    def partition_runoff(self, bucket_index, runoff, bucket_data, water_inputs, buckets):
        """Partition runoff to other buckets and stream."""
        connections = bucket_data.get('connections', [])
        relative_area_index = bucket_data.get('relativeAreaIndex', 1.0)
        
        # Calculate actual runoff depth
        actual_runoff = runoff * relative_area_index
        
        # Partition according to connections array
        for i, connection_fraction in enumerate(connections):
            if connection_fraction > 0:
                if i == bucket_index:
                    # Water goes to reach (stream) - not implemented here
                    pass
                else:
                    # Water goes to another bucket
                    if i < len(buckets):
                        # Scale by receiving bucket's relative area index
                        receiving_bucket = buckets[i]
                        receiving_area_index = receiving_bucket.get('relativeAreaIndex', 1.0)
                        scaled_input = (actual_runoff * connection_fraction) / receiving_area_index
                        water_inputs[i] += scaled_input
                        
    def generate_output_files(self, output_files):
        """Generate all output time series files."""
        for key, config in output_files.items():
            if key not in self.results:
                continue
                
            results = self.results[key]
            
            # Generate timestep list
            num_timesteps = len(results['water_levels'])
            timesteps = [datetime.datetime(2023, 1, 1) + datetime.timedelta(days=i) for i in range(num_timesteps)]
            
            # Generate files for each bucket
            for i, bucket_config in enumerate(config['buckets']):
                bucket_name = bucket_config['bucket_name']
                
                # Actual evapotranspiration file
                if bucket_config['aet_file']:
                    self.generate_single_output_file(
                        bucket_config['aet_file'],
                        timesteps,
                        [row[i] for row in results['evapotranspiration']],
                        'actualEvapotranspiration',
                        f"{key}_{bucket_name}"
                    )
                    
                # Water level file
                if bucket_config['water_level_file']:
                    self.generate_single_output_file(
                        bucket_config['water_level_file'],
                        timesteps,
                        [row[i] for row in results['water_levels']],
                        'waterLevel',
                        f"{key}_{bucket_name}"
                    )
                    
                # Water inputs file
                if bucket_config['water_inputs_file']:
                    self.generate_single_output_file(
                        bucket_config['water_inputs_file'],
                        timesteps,
                        [row[i] for row in results['water_inputs']],
                        'waterInputs',
                        f"{key}_{bucket_name}"
                    )
                    
                # Water outputs file
                if bucket_config['water_outputs_file']:
                    self.generate_single_output_file(
                        bucket_config['water_outputs_file'],
                        timesteps,
                        [row[i] for row in results['water_outputs']],
                        'waterOutputs',
                        f"{key}_{bucket_name}"
                    )
                    
    def generate_single_output_file(self, filename, timesteps, values, value_name, location):
        """Generate a single output time series file."""
        ts = TimeSeries(filename)
        ts.add_column(value_name)
        
        # Add metadata
        ts.add_metadata("calculation_type", "water_routing")
        ts.add_metadata("value_type", value_name)
        ts.add_metadata("location", location)
        ts.add_metadata("timestep_seconds", 86400)
        ts.add_metadata("units", "mm" if value_name != "waterLevel" else "mm")
        
        # Add data
        for timestamp, value in zip(timesteps, values):
            ts.add_data(timestamp, location, {value_name: value})
            
        # Save files
        csv_file, json_file = ts.save_to_files(filename, self.testdata_folder)
        print(f"  ✓ Generated {filename}")


def main():
    """Main function to run the water routing system."""
    # Get testData folder from command line argument or use default
    testdata_folder = sys.argv[1] if len(sys.argv) > 1 else "testData"
    
    # Create and run the system
    system = WaterRoutingSystem(testdata_folder)
    
    # Load data
    if not system.load_data():
        print("Failed to load data. Exiting.")
        sys.exit(1)
        
    # Run simulation
    system.run_simulation()
    
    print("\nWater routing simulation completed successfully!")


if __name__ == "__main__":
    main()