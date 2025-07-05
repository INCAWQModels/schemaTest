#!/usr/bin/env python3
"""
createTimeSeriesFromPERSiSTdat.py

A Python script to read PERSiST .dat files and generate time series files.
Uses only Python standard library components.

Usage:
    python createTimeSeriesFromPERSiSTdat.py <persist_file> <start_datetime> [timestep_seconds] [output_directory]

Arguments:
    persist_file: Path to the PERSiST .dat file
    start_datetime: Start date and time in ISO format (e.g., "2023-01-01T00:00:00")
    timestep_seconds: Optional timestep in seconds between records (default: 86400)
    output_directory: Optional directory to save output files (default: current directory)

Output:
    Creates one time series file (.csv and .json) per block in the .dat file
"""

import sys
import os
import datetime
import csv
import json
import uuid
import tkinter as tk
from collections import defaultdict


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
        """
        Initialize an empty TimeSeries object.
        
        Parameters:
        name (str, optional): Name of the TimeSeries object
        """
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
        """
        Add a new column to the data structure.
        
        Parameters:
        column_name (str): The name of the new column
        """
        if column_name not in self.columns:
            self.columns.append(column_name)
            # Fill existing rows with None for the new column
            for row in self.data:
                if len(row) < len(self.columns):
                    row.extend([None] * (len(self.columns) - len(row)))
    
    def add_data(self, timestamp, location, values):
        """
        Add a new row of data to the time series.
        
        Parameters:
        timestamp (datetime): The timestamp for this data point
        location (str): The location identifier
        values (dict): Dictionary of column names and their values
        """
        # Create a new row starting with timestamp and location
        row = [timestamp, location]
        
        # Add values for each column beyond timestamp and location
        for col_name in self.columns[2:]:  # Skip timestamp and location columns
            if col_name in values:
                row.append(values[col_name])
            else:
                row.append(None)
        
        self.data.append(row)
    
    def add_metadata(self, key, value):
        """
        Add metadata to the time series.
        
        Parameters:
        key: The metadata key
        value: The metadata value
        """
        self.metadata[key] = value
    
    def save_to_files(self, name=None, output_dir=None):
        """
        Save the TimeSeries data to CSV and metadata to JSON files.
        
        Parameters:
        name (str, optional): Base name for the output files. If not provided, 
                             uses the TimeSeries object's name attribute.
        output_dir (str, optional): Directory to save files to. If not provided,
                                   uses current directory.
                             
        Returns:
        tuple: Paths to the created CSV and JSON files
        
        Raises:
        ValueError: If no name is provided and the TimeSeries object has no name
        """
        # Determine the base name for files
        base_name = name or self.name
        if not base_name:
            raise ValueError("No name provided for output files and TimeSeries object has no name")
        
        # Set output directory
        if output_dir is None:
            output_dir = os.getcwd()
        
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create full file paths
        csv_filename = os.path.join(output_dir, f"{base_name}.csv")
        json_filename = os.path.join(output_dir, f"{base_name}.json")
        
        # Save data to CSV
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow(self.columns)
            # Write data rows with datetime objects converted to ISO format strings
            for row in self.data:
                formatted_row = []
                for i, value in enumerate(row):
                    if i == 0 and isinstance(value, datetime.datetime):  # Convert timestamp
                        formatted_row.append(value.isoformat())
                    else:
                        formatted_row.append(value)
                writer.writerow(formatted_row)
        
        # Save metadata to JSON
        with open(json_filename, 'w') as jsonfile:
            json.dump(self.metadata, jsonfile, indent=4)
        
        return csv_filename, json_filename
    
    def __str__(self):
        """Return a string representation of the TimeSeries object."""
        name_info = f"TimeSeries '{self.name}'" if self.name else "Unnamed TimeSeries"
        data_info = f"with {len(self.data)} rows and {len(self.columns)} columns"
        meta_info = f"Metadata: {len(self.metadata)} entries"
        column_info = f"Columns: {', '.join(self.columns)}"
        return f"{name_info} {data_info}\n{column_info}\n{meta_info}"


def set_window_icon():
    """
    Set the tkinter window icon to INCAMan.png if available.
    This function is here for future GUI implementations.
    """
    try:
        # This would be used if creating a GUI version
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Try to find INCAMan.png in current directory or common locations
        icon_paths = [
            "INCAMan.png",
            os.path.join(os.path.dirname(__file__), "INCAMan.png"),
            os.path.join(os.path.dirname(__file__), "..", "INCAMan.png")
        ]
        
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                root.iconphoto(False, tk.PhotoImage(file=icon_path))
                break
        
        root.destroy()
    except Exception:
        # If anything fails with the icon, just continue
        pass


def parse_persist_dat_file(file_path):
    """
    Parse a PERSiST .dat file and extract the structured data.
    
    Parameters:
    file_path (str): Path to the PERSiST .dat file
    
    Returns:
    dict: Dictionary containing:
        - 'records_per_block': Number of records per block
        - 'num_blocks': Number of blocks
        - 'blocks': List of dictionaries, each containing:
            - 'reach_id': Reach identifier
            - 'data': List of tuples (precipitation, temperature)
    
    Raises:
    FileNotFoundError: If the file doesn't exist
    ValueError: If the file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PERSiST .dat file not found: {file_path}")
    
    blocks = []
    
    try:
        with open(file_path, 'r') as file:
            all_lines = file.readlines()
        
        # Filter out empty lines but keep track of original line numbers
        lines = []
        line_numbers = []
        for i, line in enumerate(all_lines):
            stripped_line = line.strip()
            if stripped_line:
                lines.append(stripped_line)
                line_numbers.append(i + 1)  # 1-based line numbering
        
        if len(lines) < 2:
            raise ValueError(f"File must contain at least 2 non-empty lines (records per block and number of blocks). Found only {len(lines)} non-empty lines.")
        
        # Parse header information with detailed error messages
        try:
            records_per_block = int(lines[0])
        except ValueError:
            raise ValueError(f"Line {line_numbers[0]}: First line must contain an integer (records per block). Found: '{lines[0]}'")
        
        try:
            num_blocks = int(lines[1])
        except ValueError:
            raise ValueError(f"Line {line_numbers[1]}: Second line must contain an integer (number of blocks). Found: '{lines[1]}'")
        
        if records_per_block <= 0:
            raise ValueError(f"Line {line_numbers[0]}: Records per block must be a positive integer. Found: {records_per_block}")
        
        if num_blocks <= 0:
            raise ValueError(f"Line {line_numbers[1]}: Number of blocks must be a positive integer. Found: {num_blocks}")
        
        # Calculate expected structure
        expected_lines = 2 + num_blocks * (1 + records_per_block)
        
        # Check if we have enough lines
        if len(lines) < expected_lines:
            missing_lines = expected_lines - len(lines)
            raise ValueError(
                f"File structure mismatch: Expected {expected_lines} non-empty lines for "
                f"{num_blocks} blocks with {records_per_block} records each, but found only {len(lines)}. "
                f"Missing {missing_lines} lines."
            )
        
        # Check if we have too many lines
        if len(lines) > expected_lines:
            extra_lines = len(lines) - expected_lines
            print(f"Warning: File contains {extra_lines} extra lines beyond expected structure. These will be ignored.")
        
        # Parse blocks with enhanced error checking
        line_index = 2  # Start after header
        reach_ids_seen = set()
        
        for block_num in range(num_blocks):
            block_start_line = line_numbers[line_index] if line_index < len(line_numbers) else "EOF"
            
            # Check if we have enough lines for this block
            if line_index >= len(lines):
                raise ValueError(
                    f"Block {block_num + 1}: Unexpected end of file. Expected reach identifier at line {block_start_line}"
                )
            
            # Read reach identifier
            reach_id = lines[line_index].strip()
            if not reach_id:
                raise ValueError(f"Line {line_numbers[line_index]}: Block {block_num + 1} reach identifier cannot be empty")
            
            # Check for duplicate reach identifiers
            if reach_id in reach_ids_seen:
                print(f"Warning: Duplicate reach identifier '{reach_id}' found in block {block_num + 1}")
            reach_ids_seen.add(reach_id)
            
            line_index += 1
            
            # Read data rows for this block
            data_rows = []
            for record_num in range(records_per_block):
                expected_data_line = line_numbers[line_index] if line_index < len(line_numbers) else "EOF"
                
                if line_index >= len(lines):
                    raise ValueError(
                        f"Block {block_num + 1} ('{reach_id}'): Unexpected end of file while reading data record {record_num + 1} of {records_per_block}. "
                        f"Expected data at line {expected_data_line}"
                    )
                
                data_line = lines[line_index].strip()
                current_line_num = line_numbers[line_index]
                line_index += 1
                
                # Parse the two data columns with detailed error reporting
                try:
                    parts = data_line.split()
                    if len(parts) == 0:
                        raise ValueError(f"Line {current_line_num}: Data line is empty")
                    elif len(parts) == 1:
                        raise ValueError(f"Line {current_line_num}: Data line contains only 1 value, expected 2 (precipitation and temperature). Found: '{data_line}'")
                    elif len(parts) > 2:
                        # Handle case where there might be extra whitespace or comments
                        print(f"Warning: Line {current_line_num}: Data line contains {len(parts)} values, using first 2. Line: '{data_line}'")
                    
                    try:
                        precipitation = float(parts[0])
                    except ValueError:
                        raise ValueError(f"Line {current_line_num}: Cannot convert precipitation value '{parts[0]}' to number")
                    
                    try:
                        temperature = float(parts[1])
                    except ValueError:
                        raise ValueError(f"Line {current_line_num}: Cannot convert temperature value '{parts[1]}' to number")
                    
                    # Optional: Add reasonable range checks
                    if precipitation < 0:
                        print(f"Warning: Line {current_line_num}: Negative precipitation value ({precipitation}) in block '{reach_id}'")
                    
                    if temperature < -100 or temperature > 60:
                        print(f"Warning: Line {current_line_num}: Unusual temperature value ({temperature}°C) in block '{reach_id}'")
                    
                    data_rows.append((precipitation, temperature))
                    
                except ValueError as e:
                    raise ValueError(f"Block {block_num + 1} ('{reach_id}'), record {record_num + 1}: {e}")
            
            # Verify we read the correct number of records
            if len(data_rows) != records_per_block:
                raise ValueError(
                    f"Block {block_num + 1} ('{reach_id}'): Expected {records_per_block} data records but read {len(data_rows)}"
                )
            
            blocks.append({
                'reach_id': reach_id,
                'data': data_rows
            })
        
        # Final verification
        if len(blocks) != num_blocks:
            raise ValueError(
                f"File header claims {num_blocks} blocks but parsed {len(blocks)} blocks"
            )
        
        # Verify all blocks have the same number of records
        for i, block in enumerate(blocks):
            if len(block['data']) != records_per_block:
                raise ValueError(
                    f"Block {i + 1} ('{block['reach_id']}'): Contains {len(block['data'])} records, expected {records_per_block}"
                )
        
        print(f"Successfully parsed {len(blocks)} blocks with {records_per_block} records each")
        
        return {
            'records_per_block': records_per_block,
            'num_blocks': num_blocks,
            'blocks': blocks
        }
    
    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        else:
            raise ValueError(f"Unexpected error reading file {file_path}: {e}")


def create_timeseries_from_block(block_data, start_datetime, timestep_seconds, source_file):
    """
    Create a TimeSeries object from a single block of PERSiST data.
    
    Parameters:
    block_data (dict): Dictionary containing 'reach_id' and 'data'
    start_datetime (datetime): Starting datetime for the time series
    timestep_seconds (int): Time step between records in seconds
    source_file (str): Path to the source PERSiST file
    
    Returns:
    TimeSeries: TimeSeries object containing the block data
    """
    reach_id = block_data['reach_id']
    data_rows = block_data['data']
    
    # Create TimeSeries object
    ts = TimeSeries(name=f"PERSiST_{reach_id}")
    
    # Add columns for precipitation and temperature
    ts.add_column("precipitation_mm")
    ts.add_column("temperature_c")
    
    # Add metadata
    ts.add_metadata("source_file", os.path.basename(source_file))
    ts.add_metadata("source_file_full_path", os.path.abspath(source_file))
    ts.add_metadata("reach_identifier", reach_id)
    ts.add_metadata("creation_date", datetime.datetime.now().isoformat())
    ts.add_metadata("start_datetime", start_datetime.isoformat())
    ts.add_metadata("timestep_seconds", timestep_seconds)
    ts.add_metadata("timestep_description", f"{timestep_seconds} seconds")
    ts.add_metadata("num_records", len(data_rows))
    ts.add_metadata("data_type", "PERSiST climate data")
    ts.add_metadata("precipitation_units", "mm/timestep")
    ts.add_metadata("temperature_units", "degrees Celsius")
    
    # Add data points
    current_datetime = start_datetime
    for precipitation, temperature in data_rows:
        ts.add_data(
            timestamp=current_datetime,
            location=reach_id,
            values={
                "precipitation_mm": precipitation,
                "temperature_c": temperature
            }
        )
        current_datetime += datetime.timedelta(seconds=timestep_seconds)
    
    return ts


def main():
    """
    Main function to process command line arguments and convert PERSiST .dat file.
    """
    # Check command line arguments
    if len(sys.argv) < 3:
        print("Usage: python createTimeSeriesFromPERSiSTdat.py <persist_file> <start_datetime> [timestep_seconds] [output_directory]")
        print("")
        print("Arguments:")
        print("  persist_file     : Path to the PERSiST .dat file")
        print("  start_datetime   : Start date and time in ISO format (e.g., '2023-01-01T00:00:00')")
        print("  timestep_seconds : Optional timestep in seconds between records (default: 86400)")
        print("  output_directory : Optional directory to save output files (default: current directory)")
        print("")
        print("Examples:")
        print("  python createTimeSeriesFromPERSiSTdat.py data.dat 2023-01-01T00:00:00")
        print("  python createTimeSeriesFromPERSiSTdat.py data.dat 2023-01-01T00:00:00 86400")
        print("  python createTimeSeriesFromPERSiSTdat.py data.dat 2023-01-01T00:00:00 86400 ./output")
        print("  python createTimeSeriesFromPERSiSTdat.py data.dat 2023-01-01T00:00:00 3600 /path/to/output")
        print("")
        print("Common timestep values:")
        print("  86400    = 1 day")
        print("  3600     = 1 hour") 
        print("  1800     = 30 minutes")
        print("  900      = 15 minutes")
        sys.exit(1)
    
    persist_file = sys.argv[1]
    start_datetime_str = sys.argv[2]
    
    # Parse optional arguments
    timestep_seconds = 86400  # Default
    output_directory = os.getcwd()  # Default to current directory
    
    # Validate timestep argument
    if len(sys.argv) > 3:
        try:
            timestep_seconds = int(sys.argv[3])
        except ValueError:
            print(f"Error: Timestep must be an integer (seconds), got '{sys.argv[3]}'")
            sys.exit(1)
    
    # Validate output directory argument
    if len(sys.argv) > 4:
        output_directory = sys.argv[4]
        # Expand user home directory if specified
        output_directory = os.path.expanduser(output_directory)
        # Convert to absolute path
        output_directory = os.path.abspath(output_directory)
    
    # Validate input file exists
    if not os.path.exists(persist_file):
        print(f"Error: PERSiST file '{persist_file}' not found.")
        print("Please check the file path and try again.")
        sys.exit(1)
    
    # Validate and parse start datetime
    try:
        start_datetime = datetime.datetime.fromisoformat(start_datetime_str)
    except ValueError:
        print(f"Error: Invalid datetime format '{start_datetime_str}'")
        print("Please use ISO format like:")
        print("  2023-01-01T00:00:00")
        print("  2023-12-31T23:59:59")
        print("  2023-06-15T12:30:00")
        sys.exit(1)
    
    # Validate timestep
    if timestep_seconds <= 0:
        print(f"Error: Timestep must be positive, got {timestep_seconds}")
        sys.exit(1)
    
    # Validate and create output directory
    try:
        if not os.path.exists(output_directory):
            print(f"Creating output directory: {output_directory}")
            os.makedirs(output_directory)
        elif not os.path.isdir(output_directory):
            print(f"Error: Output path '{output_directory}' exists but is not a directory")
            sys.exit(1)
        
        # Check if directory is writable
        test_file = os.path.join(output_directory, ".write_test")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
        except (PermissionError, OSError):
            print(f"Error: Cannot write to output directory '{output_directory}'")
            print("Please check directory permissions and try again.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error creating output directory '{output_directory}': {e}")
        sys.exit(1)
    
    # Check for very large timesteps that might indicate user error
    if timestep_seconds > 31536000:  # More than 1 year
        print(f"Warning: Very large timestep ({timestep_seconds} seconds = {timestep_seconds/86400:.1f} days)")
        response = input("Continue anyway? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("Operation cancelled.")
            sys.exit(0)
    
    try:
        # Set window icon for any future GUI components
        set_window_icon()
        
        # Parse the PERSiST .dat file
        print(f"Reading PERSiST file: {persist_file}")
        print(f"File size: {os.path.getsize(persist_file)} bytes")
        print(f"Output directory: {output_directory}")
        
        parsed_data = parse_persist_dat_file(persist_file)
        
        print(f"Start datetime: {start_datetime}")
        print(f"Timestep: {timestep_seconds} seconds ({timestep_seconds/86400:.3f} days)")
        
        # Calculate end datetime for information
        total_records = parsed_data['records_per_block']
        end_datetime = start_datetime + datetime.timedelta(seconds=(total_records - 1) * timestep_seconds)
        print(f"End datetime: {end_datetime}")
        print(f"Total time span: {end_datetime - start_datetime}")
        print("")
        
        # Check for potential issues
        reach_ids = [block['reach_id'] for block in parsed_data['blocks']]
        if len(set(reach_ids)) != len(reach_ids):
            duplicates = [rid for rid in set(reach_ids) if reach_ids.count(rid) > 1]
            print(f"Note: Found duplicate reach IDs: {duplicates}")
            print("Files for duplicate reaches will overwrite each other.")
            print("")
        
        # Create and save TimeSeries for each block
        created_files = []
        failed_blocks = []
        
        for i, block_data in enumerate(parsed_data['blocks']):
            reach_id = block_data['reach_id']
            print(f"Processing block {i + 1}/{parsed_data['num_blocks']}: {reach_id}")
            
            try:
                # Create TimeSeries
                ts = create_timeseries_from_block(
                    block_data, 
                    start_datetime, 
                    timestep_seconds, 
                    persist_file
                )
                
                # Save to files in the specified output directory
                csv_path, json_path = ts.save_to_files(output_dir=output_directory)
                created_files.append((reach_id, csv_path, json_path))
                print(f"  ✓ Created: {os.path.basename(csv_path)}")
                print(f"  ✓ Created: {os.path.basename(json_path)}")
                
                # Verify files were created and have expected size
                if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
                    print(f"  ⚠ Warning: CSV file appears to be empty or missing")
                if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
                    print(f"  ⚠ Warning: JSON file appears to be empty or missing")
                    
            except Exception as e:
                print(f"  ✗ Error processing block '{reach_id}': {e}")
                failed_blocks.append((reach_id, str(e)))
                continue
        
        print("")
        
        # Summary
        if created_files:
            print(f"✓ Conversion complete! Successfully created {len(created_files)} time series in '{output_directory}':")
            for reach_id, csv_path, json_path in created_files:
                print(f"  {reach_id}: {os.path.basename(csv_path)}, {os.path.basename(json_path)}")
        
        if failed_blocks:
            print(f"\n✗ Failed to process {len(failed_blocks)} blocks:")
            for reach_id, error in failed_blocks:
                print(f"  {reach_id}: {error}")
            sys.exit(1)
        
        if not created_files:
            print("✗ No time series files were created.")
            sys.exit(1)
        
    except FileNotFoundError as e:
        print(f"✗ File Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"✗ Data Format Error: {e}")
        print("\nPlease check that your PERSiST .dat file follows the expected format:")
        print("  Line 1: Number of records per block (integer)")
        print("  Line 2: Number of blocks (integer)")
        print("  Then for each block:")
        print("    - One line with reach identifier")
        print("    - N lines with precipitation and temperature values")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        print("\nThis may indicate a bug in the program or an unusual file format.")
        print("Please check your input file and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
