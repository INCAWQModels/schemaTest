import json
import os
from typing import Dict, List, Any, Optional

def load_json_file(filepath: str) -> Dict[str, Any]:
    """Load and return JSON data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return {}

def create_time_series_entry(base_name: str, ts_type: str, mandatory: bool = False, generated: bool = True) -> Dict[str, Any]:
    """Create a time series entry with filename and metadata."""
    filename = f"{base_name}_{ts_type}"
    return {
        "fileName": filename,
        "mandatory": mandatory,
        "generated": generated
    }

def get_component_name(component: Dict[str, Any], component_type: str, index: int) -> str:
    """Get a meaningful name for a component, using name or abbreviation if available."""
    if isinstance(component, dict):
        name = component.get("name", "")
        abbrev = component.get("abbreviation", "")
        
        if name:
            # Convert name to filename-safe format
            return name.replace(" ", "_").replace("-", "_")
        elif abbrev:
            return abbrev
    
    # Fallback to type and index
    return f"{component_type}_{index}"

def generate_bucket_time_series(bucket_info: Dict[str, Any], bucket_index: int, 
                               landcover_name: str, hru_name: str, 
                               time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for a bucket."""
    bucket_name = get_component_name(bucket_info, "bucket", bucket_index)
    base_name = f"{hru_name}_{landcover_name}_{bucket_name}"
    
    bucket_ts = {}
    bucket_time_series = time_series_defs.get("bucket", {})
    
    for ts_type in bucket_time_series.keys():
        bucket_ts[ts_type] = create_time_series_entry(base_name, ts_type)
    
    return bucket_ts

def generate_landcover_time_series(landcover_info: Dict[str, Any], landcover_index: int,
                                 hru_name: str, time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for a land cover type."""
    landcover_name = get_component_name(landcover_info, "landCoverType", landcover_index)
    base_name = f"{hru_name}_{landcover_name}"
    
    landcover_ts = {}
    
    # Add land cover type time series
    landcover_time_series = time_series_defs.get("landCoverType", {})
    for ts_type in landcover_time_series.keys():
        landcover_ts[ts_type] = create_time_series_entry(base_name, ts_type)
    
    # Add buckets time series
    buckets = landcover_info.get("buckets", [])
    if buckets:
        landcover_ts["buckets"] = []
        for bucket_index, bucket_info in enumerate(buckets):
            bucket_ts = generate_bucket_time_series(
                bucket_info, bucket_index, landcover_name, hru_name, time_series_defs
            )
            landcover_ts["buckets"].append({
                "name": bucket_info.get("name", f"Bucket_{bucket_index}"),
                "abbreviation": bucket_info.get("abbreviation", f"B{bucket_index}"),
                "timeSeries": bucket_ts
            })
    
    return landcover_ts

def generate_subcatchment_time_series(subcatchment_info: Dict[str, Any], hru_name: str,
                                    time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for a subcatchment."""
    base_name = f"{hru_name}_subcatchment"
    
    subcatchment_ts = {}
    
    # Add subcatchment time series
    subcatchment_time_series = time_series_defs.get("subcatchment", {})
    for ts_type in subcatchment_time_series.keys():
        subcatchment_ts[ts_type] = create_time_series_entry(base_name, ts_type)
    
    # Add land cover types time series
    land_cover_types = subcatchment_info.get("landCoverTypes", [])
    if land_cover_types:
        subcatchment_ts["landCoverTypes"] = []
        for lc_index, lc_info in enumerate(land_cover_types):
            lc_ts = generate_landcover_time_series(lc_info, lc_index, hru_name, time_series_defs)
            subcatchment_ts["landCoverTypes"].append({
                "name": lc_info.get("name", f"LandCover_{lc_index}"),
                "abbreviation": lc_info.get("abbreviation", f"LC{lc_index}"),
                "timeSeries": lc_ts
            })
    
    # Add particle size classes if present
    particle_size_classes = subcatchment_info.get("particleSizeClasses", [])
    if particle_size_classes:
        subcatchment_ts["particleSizeClasses"] = {
            "count": len(particle_size_classes),
            "classes": [
                {
                    "name": psc.get("name", f"ParticleClass_{i}"),
                    "abbreviation": psc.get("abbreviation", f"PC{i}")
                }
                for i, psc in enumerate(particle_size_classes)
            ]
        }
    
    return subcatchment_ts

def generate_reach_time_series(reach_info: Dict[str, Any], hru_name: str,
                             time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for a reach."""
    base_name = f"{hru_name}_reach"
    
    reach_ts = {}
    
    # Add reach time series
    reach_time_series = time_series_defs.get("reach", {})
    for ts_type in reach_time_series.keys():
        reach_ts[ts_type] = create_time_series_entry(base_name, ts_type)
    
    # Add particle size classes if present
    particle_size_classes = reach_info.get("particleSizeClasses", [])
    if particle_size_classes:
        reach_ts["particleSizeClasses"] = {
            "count": len(particle_size_classes),
            "classes": [
                {
                    "name": psc.get("name", f"ParticleClass_{i}"),
                    "abbreviation": psc.get("abbreviation", f"PC{i}")
                }
                for i, psc in enumerate(particle_size_classes)
            ]
        }
    
    return reach_ts

def generate_hru_time_series(hru_info: Dict[str, Any], hru_index: int,
                           time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for an HRU."""
    hru_name = get_component_name(hru_info, "HRU", hru_index)
    
    hru_ts = {
        "name": hru_info.get("name", f"HRU_{hru_index}"),
        "abbreviation": hru_info.get("abbreviation", f"H{hru_index}"),
        "timeSeries": {}
    }
    
    # Add subcatchment time series
    subcatchment_info = hru_info.get("subcatchment", {})
    if subcatchment_info:
        hru_ts["timeSeries"]["subcatchment"] = generate_subcatchment_time_series(
            subcatchment_info, hru_name, time_series_defs
        )
    
    # Add reach time series
    reach_info = hru_info.get("reach", {})
    if reach_info:
        hru_ts["timeSeries"]["reach"] = generate_reach_time_series(
            reach_info, hru_name, time_series_defs
        )
    
    return hru_ts

def generate_catchment_time_series(catchment_info: Dict[str, Any],
                                 time_series_defs: Dict[str, Any]) -> Dict[str, Any]:
    """Generate time series entries for the entire catchment."""
    catchment_name = get_component_name(catchment_info, "catchment", 0)
    base_name = f"{catchment_name}_catchment"
    
    catchment_ts = {}
    
    # Add catchment-level time series
    catchment_time_series = time_series_defs.get("catchment", {})
    for ts_type in catchment_time_series.keys():
        # Set appropriate mandatory/generated flags for catchment inputs
        mandatory = ts_type in ["temperatureAndPrecipitation", "solarRadiation"]
        generated = not mandatory
        
        entry = create_time_series_entry(base_name, ts_type, mandatory, generated)
        catchment_ts[ts_type] = entry
    
    return catchment_ts

def generate_model_time_series(schemas_path: str, time_series_path: str, 
                             generated_names_path: str, output_path: str) -> None:
    """Main function to generate the ModelTimeSeries.json file."""
    
    # Load input files
    print("Loading input files...")
    schemas = load_json_file(schemas_path)
    time_series_defs = load_json_file(time_series_path)
    generated_names = load_json_file(generated_names_path)
    
    if not all([schemas, time_series_defs, generated_names]):
        print("Error: Could not load all required input files.")
        return
    
    print("Generating ModelTimeSeries structure...")
    
    # Initialize the model time series structure
    model_time_series = {
        "catchment": {
            "name": generated_names.get("catchment", {}).get("name", "Unknown Catchment"),
            "abbreviation": generated_names.get("catchment", {}).get("abbreviation", "UC"),
            "timeSeries": {},
            "HRUs": []
        }
    }
    
    # Generate catchment-level time series
    model_time_series["catchment"]["timeSeries"] = generate_catchment_time_series(
        generated_names.get("catchment", {}), time_series_defs
    )
    
    # Load the actual catchment structure to get HRU details
    # First, try to find the generated catchment file
    possible_catchment_paths = [
        "testData/generated_catchment.json",
        "../testData/generated_catchment.json",
        "generated_catchment.json"
    ]
    
    catchment_data = None
    for path in possible_catchment_paths:
        if os.path.exists(path):
            catchment_data = load_json_file(path)
            break
    
    if not catchment_data:
        print("Warning: Could not find generated catchment file. Using generatedNames.json structure.")
        # Fallback: create basic structure from generatedNames
        hrus_info = generated_names.get("HRU", [])
        for hru_index, hru_basic_info in enumerate(hrus_info):
            # Create a minimal HRU structure
            hru_ts = {
                "name": hru_basic_info.get("name", f"HRU_{hru_index}"),
                "abbreviation": hru_basic_info.get("abbreviation", f"H{hru_index}"),
                "timeSeries": {
                    "subcatchment": {},
                    "reach": {}
                }
            }
            model_time_series["catchment"]["HRUs"].append(hru_ts)
    else:
        # Use the full catchment structure
        hrus_data = catchment_data.get("HRUs", [])
        for hru_index, hru_info in enumerate(hrus_data):
            hru_ts = generate_hru_time_series(hru_info, hru_index, time_series_defs)
            model_time_series["catchment"]["HRUs"].append(hru_ts)
    
    # Add summary information
    model_time_series["summary"] = {
        "totalHRUs": len(model_time_series["catchment"]["HRUs"]),
        "generatedFrom": {
            "schemas": os.path.basename(schemas_path),
            "timeSeries": os.path.basename(time_series_path),
            "generatedNames": os.path.basename(generated_names_path)
        }
    }
    
    # If we used the full catchment data, add more detailed summary
    if catchment_data:
        # Count land cover types and buckets
        total_land_covers = 0
        total_buckets = 0
        total_particle_classes = 0
        
        for hru in model_time_series["catchment"]["HRUs"]:
            if "subcatchment" in hru["timeSeries"]:
                land_covers = hru["timeSeries"]["subcatchment"].get("landCoverTypes", [])
                total_land_covers += len(land_covers)
                
                for lc in land_covers:
                    buckets = lc["timeSeries"].get("buckets", [])
                    total_buckets += len(buckets)
                
                # Count particle size classes
                psc_info = hru["timeSeries"]["subcatchment"].get("particleSizeClasses", {})
                if isinstance(psc_info, dict) and "count" in psc_info:
                    total_particle_classes += psc_info["count"]
        
        model_time_series["summary"].update({
            "totalLandCoverTypes": total_land_covers,
            "totalBuckets": total_buckets,
            "totalParticleSizeClasses": total_particle_classes
        })
    
    # Save the generated model time series
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(model_time_series, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully generated {output_path}")
        print(f"Summary:")
        print(f"  - Catchment: {model_time_series['catchment']['name']}")
        print(f"  - Total HRUs: {model_time_series['summary']['totalHRUs']}")
        
        if "totalLandCoverTypes" in model_time_series["summary"]:
            print(f"  - Total Land Cover Types: {model_time_series['summary']['totalLandCoverTypes']}")
            print(f"  - Total Buckets: {model_time_series['summary']['totalBuckets']}")
            print(f"  - Total Particle Size Classes: {model_time_series['summary']['totalParticleSizeClasses']}")
        
    except Exception as e:
        print(f"Error writing output file: {e}")

def main():
    """Main function with default file paths."""
    # Default file paths based on the repository structure
    schemas_path = "../schemas/schemas.json"
    time_series_path = "../schemas/timeSeries.json"
    generated_names_path = "../testData/generatedNames.json"
    output_path = "../testData/ModelTimeSeries.json"
    
    # Check if files exist, adjust paths if needed
    for path_var, path_val in [
        ("schemas_path", schemas_path),
        ("time_series_path", time_series_path), 
        ("generated_names_path", generated_names_path)
    ]:
        if not os.path.exists(path_val):
            # Try with ../ prefix
            alt_path = f"../{path_val}"
            if os.path.exists(alt_path):
                if path_var == "schemas_path":
                    schemas_path = alt_path
                elif path_var == "time_series_path":
                    time_series_path = alt_path
                elif path_var == "generated_names_path":
                    generated_names_path = alt_path
            else:
                print(f"Warning: Could not find {path_val}")
    
    # Also try alternative output path
    if not os.path.exists(os.path.dirname(output_path)):
        alt_output = "../testData/ModelTimeSeries.json"
        if os.path.exists(os.path.dirname(alt_output)):
            output_path = alt_output
        else:
            # Use current directory as fallback
            output_path = "ModelTimeSeries.json"
    
    generate_model_time_series(schemas_path, time_series_path, generated_names_path, output_path)

if __name__ == "__main__":
    main()
