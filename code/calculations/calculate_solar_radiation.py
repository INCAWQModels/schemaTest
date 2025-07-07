#!/usr/bin/env python3
"""
Standalone Solar Radiation Calculator

A self-contained version that includes the solar radiation calculation
and TimeSeries functionality using only Python standard library.
"""

import math
import datetime
import csv
import json
import uuid
import os


class TimeSeries:
    """A simplified TimeSeries class using only standard library."""
    
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
        if not isinstance(timestamp, datetime.datetime):
            raise TypeError("timestamp must be a datetime object")
        
        new_row = [timestamp, location]
        
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
        elif isinstance(values, list):
            for i in range(len(values)):
                col_name = f"value{i+1}"
                if col_name not in self.columns:
                    self.add_column(col_name)
            new_row.extend(values)
            if len(new_row) < len(self.columns):
                new_row.extend([None] * (len(self.columns) - len(new_row)))
        
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


def solar_declination(day_of_year):
    """Calculate solar declination angle."""
    return 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))


def solar_hour_angle(hour, longitude, timezone_offset):
    """Calculate solar hour angle."""
    solar_time = hour + (longitude / 15) - timezone_offset
    return 15 * (solar_time - 12)


def solar_elevation_angle(lat, decl, hour_angle):
    """Calculate solar elevation angle."""
    lat_rad = math.radians(lat)
    decl_rad = math.radians(decl)
    ha_rad = math.radians(hour_angle)

    elevation = math.asin(
        math.sin(lat_rad) * math.sin(decl_rad) +
        math.cos(lat_rad) * math.cos(decl_rad) * math.cos(ha_rad)
    )
    return math.degrees(elevation)


def extraterrestrial_radiation(day_of_year):
    """Calculate extraterrestrial radiation."""
    G_sc = 1367  # W/m²
    return G_sc * (1 + 0.033 * math.cos(math.radians(360 * day_of_year / 365)))


def solar_radiation(dt, lat, longitude=0, timezone_offset=0):
    """Calculate solar radiation for a given datetime and location."""
    day_of_year = dt.timetuple().tm_yday
    hour = dt.hour + dt.minute / 60 + dt.second / 3600

    decl = solar_declination(day_of_year)
    ha = solar_hour_angle(hour, longitude, timezone_offset)
    elev = solar_elevation_angle(lat, decl, ha)

    if elev <= 0:
        return 0

    I_0 = extraterrestrial_radiation(day_of_year)
    transmittance = 0.75
    radiation = I_0 * transmittance * math.sin(math.radians(elev))
    return radiation


def compute_radiation_series(start_time, end_time, step_seconds, latitude, longitude, timezone_offset):
    """Compute solar radiation values over a time period."""
    current_time = start_time
    times = []
    radiation = []

    while current_time <= end_time:
        rad = solar_radiation(current_time, latitude, longitude, timezone_offset)
        times.append(current_time)
        radiation.append(rad)
        current_time += datetime.timedelta(seconds=step_seconds)

    return times, radiation


def compute_radiation_timeseries(start_time, end_time, step_seconds, latitude, longitude, timezone_offset, location_id="default"):
    """
    Compute solar radiation over a time period and return results as a TimeSeries object.
    
    Args:
        start_time: datetime object, start of the computation period
        end_time: datetime object, end of the computation period  
        step_seconds: int, time step in seconds
        latitude: float, latitude in degrees
        longitude: float, longitude in degrees
        timezone_offset: float, timezone offset from UTC in hours
        location_id: str, identifier for the location
        
    Returns:
        TimeSeries object with solar radiation data and metadata
    """
    # Calculate radiation values
    times, radiation_values = compute_radiation_series(start_time, end_time, step_seconds, 
                                                      latitude, longitude, timezone_offset)
    
    # Create TimeSeries object
    ts = TimeSeries()
    
    # Add metadata
    ts.add_metadata("latitude", str(latitude))
    ts.add_metadata("longitude", str(longitude))
    ts.add_metadata("source", "Python solar radiation model (standalone)")
    ts.add_metadata("generation_time", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    ts.add_metadata("location_id", location_id)
    ts.add_metadata("timezone_offset", str(timezone_offset))
    ts.add_metadata("start_time", start_time.isoformat())
    ts.add_metadata("end_time", end_time.isoformat())
    ts.add_metadata("step_seconds", str(step_seconds))
    ts.add_metadata("num_records", str(len(times)))
    
    # Add column for solar radiation
    ts.add_column("solar_radiation")
    
    # Add data to TimeSeries
    for i in range(len(times)):
        ts.add_data(times[i], location_id, [radiation_values[i]])
    
    return ts


# Test the solar radiation calculation
if __name__ == "__main__":
    # Example usage
    start_date_str = "2024-06-21 06:00:00"  # Summer solstice
    end_date_str = "2024-06-21 20:00:00"
    step_seconds = 3600  # Every hour

    # Location info
    latitude = 45.0
    longitude = -15.0
    timezone_offset = 0  # UTC
    location_id = "Test_Location"

    # Parse datetimes
    start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")

    # Create TimeSeries object
    ts = compute_radiation_timeseries(start_dt, end_dt, step_seconds, latitude, longitude, timezone_offset, location_id)
    
    # Print TimeSeries information
    print(f"Generated solar radiation time series with {len(ts.data)} records")
    print("\nMetadata:")
    for key, value in ts.metadata.items():
        print(f"  {key}: {value}")
    
    # Print a sample of data
    print("\nSample of Solar Radiation Data:")
    for i, row in enumerate(ts.data[:5]):  # Print first 5 rows
        timestamp = row[0]
        location = row[1]
        solar_radiation = row[2]
        print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} at {location}: {solar_radiation:.2f} W/m²")
    
    # Save to files
    csv_file, json_file = ts.save_to_files("test_solar_radiation")
    print(f"\nSaved to: {csv_file} and {json_file}")
