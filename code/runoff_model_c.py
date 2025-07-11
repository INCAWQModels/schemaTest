#!/usr/bin/env python3
"""
Command Line Model Output Aggregator

A command-line version of the model output aggregator that can be used
in scripts or batch processing workflows.

Usage:
    python aggregator_cli.py [catchment_json] [timeseries_json] [data_folder] [output_folder]

If no arguments provided, will look for default files in testData directory.
"""

import json
import csv
import os
import sys
from datetime import datetime
from collections import defaultdict
import uuid
import argparse


class TimeSeries:
    """
    A class to represent time series data with associated metadata.
    
    The class contains two main data structures:
    1. A two-dimensional data table where:
       - First column: Python datetime (year, month, day, hour, minute, second)
       - Second column: Location identifier
       - Third+ columns: Numeric data values
    2. A dictionary for storing metadata about the time series
    """
    
    def __init__(self, name=None):
        """Initialize an empty TimeSeries object."""
        # Create an empty list for data rows
        self.data = []
        # Generate a UUID and store it in metadata
        self.uuid = str(uuid.uuid4())
        # Store column names - use UUID as the header for timestamp column
        self.columns = [self.uuid, "location"]
        # Create an empty dictionary for metadata
        self.metadata = {}
        # Store the UUID in metadata
        self.metadata["uuid"] = self.uuid
        # Set the name of the TimeSeries object
        self.name = name
    
    def add_column(self, column_name):
        """Add a new column to the data structure."""
        if column_name not in self.columns:
            self.columns.append(column_name)
            # Fill existing rows with None for the new column
            for row in self.data:
                if len(row) < len(self.columns):
                    row.extend([None] * (len(self.columns) - len(row)))
    
    def add_data(self, timestamp, location, values):
        """Add a new row of data to the time series."""
        if isinstance(values, dict):
            # Ensure all columns exist
            for col_name in values.keys():
                if col_name not in self.columns:
                    self.add_column(col_name)
            
            # Create new row
            new_row = [None] * len(self.columns)
            new_row[0] = timestamp
            new_row[1] = location
            
            # Fill in the values
            for col_name, value in values.items():
                col_index = self.columns.index(col_name)
                new_row[col_index] = value
        else:
            # Simple list of values
            new_row = [timestamp, location] + list(values)
        
        self.data.append(new_row)
    
    def add_metadata(self, key, value):
        """Add metadata to the time series."""
        self.metadata[key] = value
    
    def save_to_files(self, name=None, output_dir=None):
        """Save the TimeSeries data to CSV and metadata to JSON files."""
        base_name = name or self.name
        if not base_name:
            raise ValueError("No name provided for output files")
        
        if output_dir:
            csv_filename = os.path.join(output_dir, f"{base_name}.csv")
            json_filename = os.path.join(output_dir, f"{base_name}.json")
        else:
            csv_filename = f"{base_name}.csv"
            json_filename = f"{base_name}.json"
        
        # Ensure output directory exists
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Save data to CSV
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(self.columns)
            for row in self.data:
                formatted_row = []
                for i, value in enumerate(row):
                    if i == 0 and isinstance(value, datetime):
                        formatted_row.append(value.isoformat())
                    else:
                        formatted_row.append(value)
                writer.writerow(formatted_row)
        
        # Save metadata to JSON
        with open(json_filename, 'w') as jsonfile:
            json.dump(self.metadata, jsonfile, indent=4)
        
        return csv_filename, json_filename


class ModelAggregatorCLI:
    def __init__(self):
        self.catchment_data = None
        self.timeseries_config = None
        
    def log_message(self, message, verbose=True):
        """Print a timestamped message."""
        if verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
    
    def load_json_file(self, filepath):
        """Load a JSON file safely."""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
            return None
    
    def load_csv_file(self, filepath):
        """Load a CSV file and return time series data."""
        data = []
        try:
            with open(filepath, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert timestamp string to datetime object
                    timestamp_str = list(row.values())[0]  # First column is timestamp
                    try:
                        # Try parsing as ISO format
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        # If that fails, try other common formats
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                timestamp = datetime.strptime(timestamp_str, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            # If all parsing fails, skip this row
                            print(f"Warning: Could not parse timestamp '{timestamp_str}' in {filepath}")
                            continue
                    
                    row_data = {'timestamp': timestamp}
                    row_data.update(row)
                    data.append(row_data)
        except Exception as e:
            print(f"Error loading CSV {filepath}: {e}")
            return []
        
        return data
    
    def load_timeseries_metadata(self, filepath):
        """Load metadata from a TimeSeries JSON file."""
        json_path = filepath.replace('.csv', '.json')
        try:
            with open(json_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load metadata from {json_path}: {e}")
            return {}

    def extract_timestep_seconds(self, bucket_configs, data_folder):
        """Extract timestep_seconds from input TimeSeries JSON files."""
        timestep_seconds = None
        
        # Look through bucket configs to find a JSON file with timestep_seconds
        for bucket_config in bucket_configs:
            bucket_timeseries = bucket_config['timeSeries']
            
            # Check waterOutputs first
            if 'waterOutputs' in bucket_timeseries:
                filename = bucket_timeseries['waterOutputs']['fileName']
                filepath = os.path.join(data_folder, f"{filename}.csv")
                
                if os.path.exists(filepath):
                    metadata = self.load_timeseries_metadata(filepath)
                    if 'timestep_seconds' in metadata:
                        timestep_seconds = metadata['timestep_seconds']
                        break
            
            # If not found, check actualEvapotranspiration
            if timestep_seconds is None and 'actualEvapotranspiration' in bucket_timeseries:
                filename = bucket_timeseries['actualEvapotranspiration']['fileName']
                filepath = os.path.join(data_folder, f"{filename}.csv")
                
                if os.path.exists(filepath):
                    metadata = self.load_timeseries_metadata(filepath)
                    if 'timestep_seconds' in metadata:
                        timestep_seconds = metadata['timestep_seconds']
                        break
        
        return timestep_seconds

    def create_aggregated_timeseries(self, aggregated_data, name, location, timestep_seconds=None):
        """Create a TimeSeries object from aggregated data."""
        ts = TimeSeries(name=name)
        
        # Add the data columns
        ts.add_column("runoffToReach")
        ts.add_column("actualEvapotranspiration")
        
        # Add metadata
        ts.add_metadata("name", name)
        ts.add_metadata("location", location)
        ts.add_metadata("description", f"Aggregated waterOutputs for {location}")
        ts.add_metadata("variables", ["runoffToReach", "actualEvapotranspiration"])
        ts.add_metadata("aggregation_level", "bucket_to_landcover" if "_" in location and location.count("_") == 2 else "landcover_to_subcatchment")
        
        # Add timestep_seconds if available
        if timestep_seconds is not None:
            ts.add_metadata("timestep_seconds", timestep_seconds)
        
        # Add data rows
        for row in aggregated_data:
            ts.add_data(
                timestamp=row['timestamp'],
                location=location,
                values={
                    'runoffToReach': row['runoffToReach'],
                    'actualEvapotranspiration': row['actualEvapotranspiration']
                }
            )
        
        return ts
    
    def aggregate_buckets_to_landcover(self, hru_name, landcover_name, bucket_configs, data_folder, verbose=True):
        """Aggregate bucket data to landcover level."""
        if verbose:
            self.log_message(f"Aggregating buckets for {hru_name}_{landcover_name}")
        
        aggregated_data = defaultdict(lambda: {
            'runoffToReach': 0.0,
            'actualEvapotranspiration': 0.0,
            'timestamp': None,
            'location': f"{hru_name}_{landcover_name}"
        })
        
        for bucket_config in bucket_configs:
            bucket_name = bucket_config['name']
            bucket_timeseries = bucket_config['timeSeries']
            
            # Process waterOutputs for runoffToReach
            if 'waterOutputs' in bucket_timeseries:
                filename = bucket_timeseries['waterOutputs']['fileName']
                filepath = os.path.join(data_folder, f"{filename}.csv")
                
                if os.path.exists(filepath):
                    data = self.load_csv_file(filepath)
                    for row in data:
                        timestamp = row['timestamp']
                        if 'runoffToReach' in row:
                            try:
                                value = float(row['runoffToReach'])
                                aggregated_data[timestamp]['runoffToReach'] += value
                                aggregated_data[timestamp]['timestamp'] = timestamp
                            except (ValueError, TypeError):
                                pass
                else:
                    if verbose:
                        self.log_message(f"Warning: File not found: {filepath}")
            
            # Process actualEvapotranspiration
            if 'actualEvapotranspiration' in bucket_timeseries:
                filename = bucket_timeseries['actualEvapotranspiration']['fileName']
                filepath = os.path.join(data_folder, f"{filename}.csv")
                
                if os.path.exists(filepath):
                    data = self.load_csv_file(filepath)
                    for row in data:
                        timestamp = row['timestamp']
                        # Look for actualEvapotranspiration column
                        et_column = None
                        for col in row.keys():
                            if 'evapotranspiration' in col.lower():
                                et_column = col
                                break
                        
                        if et_column and row[et_column]:
                            try:
                                value = float(row[et_column])
                                aggregated_data[timestamp]['actualEvapotranspiration'] += value
                                aggregated_data[timestamp]['timestamp'] = timestamp
                            except (ValueError, TypeError):
                                pass
                else:
                    if verbose:
                        self.log_message(f"Warning: File not found: {filepath}")
        
        return list(aggregated_data.values())
    
    def aggregate_landcovers_to_subcatchment(self, hru_name, landcover_configs, landcover_data, verbose=True):
        """Aggregate landcover data to subcatchment level."""
        if verbose:
            self.log_message(f"Aggregating landcovers for subcatchment {hru_name}")
        
        aggregated_data = defaultdict(lambda: {
            'runoffToReach': 0.0,
            'actualEvapotranspiration': 0.0,
            'timestamp': None,
            'location': f"{hru_name}_subcatchment"
        })
        
        # Get all timestamps from landcover data
        all_timestamps = set()
        for lc_name, lc_data in landcover_data.items():
            for row in lc_data:
                all_timestamps.add(row['timestamp'])
        
        for timestamp in all_timestamps:
            for landcover_config in landcover_configs:
                landcover_name = landcover_config['name']
                percent_cover = landcover_config.get('percentCover', 0.0) / 100.0
                
                if landcover_name in landcover_data:
                    # Find matching timestamp in landcover data
                    for row in landcover_data[landcover_name]:
                        if row['timestamp'] == timestamp:
                            aggregated_data[timestamp]['runoffToReach'] += row['runoffToReach'] * percent_cover
                            aggregated_data[timestamp]['actualEvapotranspiration'] += row['actualEvapotranspiration'] * percent_cover
                            aggregated_data[timestamp]['timestamp'] = timestamp
                            break
        
        return list(aggregated_data.values())
    
    def run_aggregation(self, catchment_file, timeseries_file, data_folder, output_folder, 
                       create_landcover=True, create_subcatchment=True, verbose=True):
        """Run the main aggregation process."""
        
        if verbose:
            self.log_message("Starting aggregation process")
        
        # Load configuration files
        self.catchment_data = self.load_json_file(catchment_file)
        self.timeseries_config = self.load_json_file(timeseries_file)
        
        if not self.catchment_data or not self.timeseries_config:
            print("Error: Failed to load configuration files")
            return False
        
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Process each HRU
        hrus = self.catchment_data.get('HRUs', [])
        total_hrus = len(hrus)
        
        # Handle different timeseries config structures
        timeseries_hrus = []
        if 'catchment' in self.timeseries_config and 'HRUs' in self.timeseries_config['catchment']:
            # New structure: {"catchment": {"HRUs": [...]}}
            timeseries_hrus = self.timeseries_config['catchment']['HRUs']
        elif 'HRUs' in self.timeseries_config:
            # Old structure: {"HRUs": [...]}
            timeseries_hrus = self.timeseries_config['HRUs']
        
        if verbose:
            self.log_message(f"Processing {total_hrus} HRUs")
            self.log_message(f"Found {len(timeseries_hrus)} HRU timeseries configurations")
        
        success_count = 0
        
        for hru_idx, hru in enumerate(hrus):
            hru_name = hru['name']
            if verbose:
                self.log_message(f"Processing HRU {hru_idx + 1}/{total_hrus}: {hru_name}")
            
            # Find corresponding timeseries configuration
            hru_timeseries = None
            for ts_hru in timeseries_hrus:
                if ts_hru['name'] == hru_name:
                    hru_timeseries = ts_hru
                    break
            
            if not hru_timeseries:
                if verbose:
                    self.log_message(f"Warning: No timeseries config found for HRU {hru_name}")
                continue
            
            landcover_types = hru['subcatchment'].get('landCoverTypes', [])
            landcover_timeseries = hru_timeseries['timeSeries']['subcatchment'].get('landCoverTypes', [])
            
            # Store landcover aggregated data for subcatchment aggregation
            landcover_aggregated_data = {}
            # Extract timestep_seconds once per HRU (should be consistent)
            hru_timestep_seconds = None
            
            # Level 1: Aggregate buckets to landcover types
            if create_landcover:
                for lc_idx, landcover in enumerate(landcover_types):
                    landcover_name = landcover['name']
                    
                    # Find corresponding timeseries config
                    lc_timeseries = None
                    for ts_lc in landcover_timeseries:
                        if ts_lc['name'] == landcover_name:
                            lc_timeseries = ts_lc
                            break
                    
                    if not lc_timeseries or 'buckets' not in lc_timeseries['timeSeries']:
                        continue
                    
                    # Extract timestep_seconds from first landcover if not already found
                    if hru_timestep_seconds is None:
                        hru_timestep_seconds = self.extract_timestep_seconds(
                            lc_timeseries['timeSeries']['buckets'], data_folder
                        )
                        if hru_timestep_seconds and verbose:
                            self.log_message(f"Found timestep_seconds: {hru_timestep_seconds}")
                    
                    # Aggregate bucket data
                    aggregated_data = self.aggregate_buckets_to_landcover(
                        hru_name, landcover_name, lc_timeseries['timeSeries']['buckets'], 
                        data_folder, verbose
                    )
                    
                    if aggregated_data:
                        # Create TimeSeries object for landcover-level waterOutputs
                        location_name = f"{hru_name}_{landcover_name}"
                        ts_name = f"{hru_name}_{landcover_name}_waterOutputs"
                        
                        ts = self.create_aggregated_timeseries(aggregated_data, ts_name, location_name, hru_timestep_seconds)
                        
                        # Save TimeSeries to files
                        try:
                            csv_file, json_file = ts.save_to_files(ts_name, output_folder)
                            if verbose:
                                self.log_message(f"Saved landcover waterOutputs: {os.path.basename(csv_file)} and {os.path.basename(json_file)}")
                            success_count += 1
                        except Exception as e:
                            if verbose:
                                self.log_message(f"Error saving landcover timeseries {ts_name}: {e}")
                        
                        # Store for subcatchment aggregation
                        landcover_aggregated_data[landcover_name] = aggregated_data
            
            # Level 2: Aggregate landcover types to subcatchment
            if create_subcatchment and landcover_aggregated_data:
                subcatchment_data = self.aggregate_landcovers_to_subcatchment(
                    hru_name, landcover_types, landcover_aggregated_data, verbose
                )
                
                if subcatchment_data:
                    # Create TimeSeries object for subcatchment-level waterOutputs
                    location_name = f"{hru_name}_subcatchment"
                    ts_name = f"{hru_name}_subcatchment_waterOutputs"
                    
                    ts = self.create_aggregated_timeseries(subcatchment_data, ts_name, location_name, hru_timestep_seconds)
                    
                    # Save TimeSeries to files
                    try:
                        csv_file, json_file = ts.save_to_files(ts_name, output_folder)
                        if verbose:
                            self.log_message(f"Saved subcatchment waterOutputs: {os.path.basename(csv_file)} and {os.path.basename(json_file)}")
                        success_count += 1
                    except Exception as e:
                        if verbose:
                            self.log_message(f"Error saving subcatchment timeseries {ts_name}: {e}")
        
        if verbose:
            self.log_message(f"Aggregation completed successfully. Created {success_count} output files.")
        
        return True


def find_default_files():
    """Find default files in testData directory."""
    testdata_paths = ["testData", "../testData", "../../testData", "./testData"]
    
    for testdata_path in testdata_paths:
        if os.path.exists(testdata_path):
            catchment_file = os.path.join(testdata_path, "generated_catchment.json")
            
            # Look for timeseries file
            timeseries_file = None
            for ts_file in ["model_timeseries.json", "ModelTimeSeries.json"]:
                ts_path = os.path.join(testdata_path, ts_file)
                if os.path.exists(ts_path):
                    timeseries_file = ts_path
                    break
            
            if os.path.exists(catchment_file) and timeseries_file:
                return catchment_file, timeseries_file, testdata_path, os.path.join(testdata_path, "aggregated")
    
    return None, None, None, None


def main():
    """Main function for command line interface."""
    parser = argparse.ArgumentParser(description="Aggregate model outputs from buckets to landcover and subcatchment levels")
    
    parser.add_argument("--catchment", "-c", help="Path to generated_catchment.json file")
    parser.add_argument("--timeseries", "-t", help="Path to model_timeseries.json file")
    parser.add_argument("--data", "-d", help="Path to data folder containing CSV files")
    parser.add_argument("--output", "-o", help="Path to output folder for aggregated files")
    parser.add_argument("--no-landcover", action="store_true", help="Skip landcover-level aggregation")
    parser.add_argument("--no-subcatchment", action="store_true", help="Skip subcatchment-level aggregation")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress messages")
    
    args = parser.parse_args()
    
    # Use provided arguments or find defaults
    if args.catchment and args.timeseries and args.data and args.output:
        catchment_file = args.catchment
        timeseries_file = args.timeseries
        data_folder = args.data
        output_folder = args.output
    else:
        if not args.quiet:
            print("Looking for default files in testData directory...")
        
        catchment_file, timeseries_file, data_folder, output_folder = find_default_files()
        
        if not all([catchment_file, timeseries_file, data_folder]):
            print("Error: Could not find default files and insufficient arguments provided.")
            print("Please provide --catchment, --timeseries, --data, and --output arguments")
            print("or ensure testData directory exists with required files.")
            sys.exit(1)
        
        if not args.quiet:
            print(f"Using default files from testData directory:")
            print(f"  Catchment: {catchment_file}")
            print(f"  Timeseries: {timeseries_file}")
            print(f"  Data: {data_folder}")
            print(f"  Output: {output_folder}")
    
    # Validate files exist
    if not os.path.exists(catchment_file):
        print(f"Error: Catchment file not found: {catchment_file}")
        sys.exit(1)
    
    if not os.path.exists(timeseries_file):
        print(f"Error: Timeseries file not found: {timeseries_file}")
        sys.exit(1)
    
    if not os.path.exists(data_folder):
        print(f"Error: Data folder not found: {data_folder}")
        sys.exit(1)
    
    # Run aggregation
    aggregator = ModelAggregatorCLI()
    
    success = aggregator.run_aggregation(
        catchment_file=catchment_file,
        timeseries_file=timeseries_file,
        data_folder=data_folder,
        output_folder=output_folder,
        create_landcover=not args.no_landcover,
        create_subcatchment=not args.no_subcatchment,
        verbose=not args.quiet
    )
    
    if success:
        if not args.quiet:
            print(f"\nAggregation completed successfully!")
            print(f"Output files saved to: {output_folder}")
        sys.exit(0)
    else:
        print("Aggregation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
