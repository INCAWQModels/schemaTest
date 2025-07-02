import json
import os
from typing import Dict, Any, List

def load_json_file(filepath: str) -> Dict[Any, Any]:
    """Load and return JSON data from file."""
    try:
        with open(filepath, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return {}

def create_particle_size_class(name: str = "Default", abbreviation: str = "PSC", 
                              min_size: float = 1.0, max_size: float = 2.0) -> Dict[str, Any]:
    """Create a particle size class object with default values."""
    return {
        "name": name,
        "abbreviation": abbreviation,
        "dimensions": {
            "minimumSize": min_size,
            "maximumSize": max_size
        },
        "density": 2.65,
        "mass": 1.0e+01
    }

def create_bucket(name: str, abbreviation: str) -> Dict[str, Any]:
    """Create a bucket object with default values."""
    return {
        "name": name,
        "abbreviation": abbreviation,
        "receivesPrecipitation": False,
        "useInSMDCalculation": False,
        "relativeAreaIndex": 1.0,
        "maximumInfiltration": 100.0,
        "droughtRunoffFraction": 0.0,
        "characteristicTimeConstant": 10.0,
        "evaporation": {
            "droughtAdjustment": 1.0,
            "relativeAmountIndex": 0.0
        },
        "soilTemperature": {
            "curentTemperature": 5.0,
            "effectiveDepth": 0.2,
            "infiltrationThresholdTemperature": 0.0
        },
        "waterDepth": {
            "current": 1.0,
            "tightlyBound": 100.0,
            "plantAvailable": 200.0,
            "freelyDraining": 700.0
        }
    }

def create_land_cover_soils(particle_size_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create land cover soils object."""
    return {
        "name": "Default Soil",
        "abbreviation": "DS",
        "particleSizeClasses": [
            {
                **psc,
                "parameters": {
                    "vegetationIndex": 10,
                    "splashDetachmentE": 0.1,
                    "flowErosionE": 0.1,
                    "splashDetachmentA": 1.0
                }
            } for psc in particle_size_classes
        ]
    }

def create_land_cover_type(name: str, abbreviation: str, buckets: List[Dict[str, Any]], 
                          particle_size_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a land cover type object."""
    return {
        "name": name,
        "abbreviation": abbreviation,
        "rainfallMultiplier": 1.0,
        "snowfallMultiplier": 1.0,
        "evaporation": {
            "canopyInterception": 0.0,
            "growingDegreeOffset": 0.0,
            "solarRadiationScalingFactor": 60.0
        },
        "snowpack": {
            "depth": 0.0,
            "meltTemperature": 0.0,
            "degreeDayMeltRate": 3.0
        },
        "soilTemperature": {
            "thermalConductivity": 0.7,
            "specificHeatFreezeThaw": 6.6,
            "snowDepthFactor": -0.25
        },
        "buckets": buckets,
        "soils": create_land_cover_soils(particle_size_classes)
    }

def create_reach(particle_size_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a reach object."""
    return {
        "flow": 1.0,
        "dimensions": {
            "length": 100.0,
            "widthAtSedimentSurface": 1.0,
            "slope": 10e-05
        },
        "particleSizeClasses": particle_size_classes,
        "Manning": {
            "a": 2.71,
            "b": 0.557,
            "c": 0.349,
            "f": 0.341,
            "n": 0.1
        }
    }

def create_subcatchment(land_cover_types: List[Dict[str, Any]], 
                       particle_size_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a subcatchment object."""
    return {
        "landCoverTypes": land_cover_types,
        "particleSizeClasses": particle_size_classes,
        "precipitationAdjustments": {
            "rainfallMultiplier": 1.0,
            "snowfallMultiplier": 1.0,
            "snowOffset": 0.0
        }
    }

def create_hru(name: str, abbreviation: str, land_cover_types: List[Dict[str, Any]], 
               particle_size_classes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create an HRU object."""
    return {
        "name": name,
        "abbreviation": abbreviation,
        "coordinates": {
            "decimalLatitude": 45.0,
            "decimalLongitude": -15.0
        },
        "subcatchment": create_subcatchment(land_cover_types, particle_size_classes),
        "reach": create_reach(particle_size_classes)
    }

def generate_catchment_json(generated_names: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the main catchment JSON structure."""
    
    # Extract catchment info
    catchment_info = generated_names.get("catchment", {})
    catchment_name = catchment_info.get("name", "Default Catchment")
    catchment_abbrev = catchment_info.get("abbreviation", "DC")
    
    # Create particle size classes if they exist
    particle_size_classes = []
    if "grainSizeClass" in generated_names:
        for i, grain_class in enumerate(generated_names["grainSizeClass"]):
            psc = create_particle_size_class(
                name=grain_class.get("name", f"Grain Class {i+1}"),
                abbreviation=grain_class.get("abbreviation", f"GC{i+1}"),
                min_size=grain_class.get("minimumSize", 1.0 + i * 0.5),
                max_size=grain_class.get("maximumSize", 2.0 + i * 0.5)
            )
            particle_size_classes.append(psc)
    
    # Create buckets
    buckets = []
    if "bucket" in generated_names:
        for bucket_info in generated_names["bucket"]:
            bucket = create_bucket(
                name=bucket_info.get("name", "Default Bucket"),
                abbreviation=bucket_info.get("abbreviation", "DB")
            )
            buckets.append(bucket)
    
    # Create land cover types
    land_cover_types = []
    if "landCoverType" in generated_names:
        for lc_info in generated_names["landCoverType"]:
            land_cover = create_land_cover_type(
                name=lc_info.get("name", "Default Land Cover"),
                abbreviation=lc_info.get("abbreviation", "DLC"),
                buckets=buckets.copy(),
                particle_size_classes=particle_size_classes.copy()
            )
            land_cover_types.append(land_cover)
    
    # Create HRUs
    hrus = []
    if "HRU" in generated_names:
        for hru_info in generated_names["HRU"]:
            hru = create_hru(
                name=hru_info.get("name", "Default HRU"),
                abbreviation=hru_info.get("abbreviation", "DHRU"),
                land_cover_types=land_cover_types.copy(),
                particle_size_classes=particle_size_classes.copy()
            )
            hrus.append(hru)
    
    # Create the main catchment structure
    catchment = {
        "name": catchment_name,
        "abbreviation": catchment_abbrev,
        "HRUs": hrus
    }
    
    return catchment

def main():
    """Main function to process the JSON files and generate output."""
    
    # File paths
    schemas_path = "../schemas/schemas.json"  # Adjust path as needed
    generated_names_path = "../testData/generatedNames.json"  # Adjust path as needed
    output_path = "../testData/generated_catchment.json"
    
    # Check if files exist, if not use the provided names.json structure
    if not os.path.exists(generated_names_path):
        print(f"Warning: {generated_names_path} not found. Using example structure.")
        # Use the structure from the provided names.json as example
        generated_names = {
            "catchment": {"name": "Example Catchment", "abbreviation": "EC"},
            "HRU": [
                {"name": "HRU 1", "abbreviation": "H1"},
                {"name": "HRU 2", "abbreviation": "H2"}
            ],
            "landCoverType": [
                {"name": "Forest", "abbreviation": "FOR"},
                {"name": "Grassland", "abbreviation": "GRA"}
            ],
            "bucket": [
                {"name": "Surface", "abbreviation": "SUR"},
                {"name": "Soil", "abbreviation": "SOL"},
                {"name": "Groundwater", "abbreviation": "GW"}
            ],
            "grainSizeClass": [
                {"name": "Clay", "abbreviation": "CL", "minimumSize": 0.002, "maximumSize": 0.063},
                {"name": "Silt", "abbreviation": "SI", "minimumSize": 0.063, "maximumSize": 2.0},
                {"name": "Sand", "abbreviation": "SA", "minimumSize": 2.0, "maximumSize": 63.0}
            ]
        }
    else:
        generated_names = load_json_file(generated_names_path)
    
    if not generated_names:
        print("Error: Could not load generated names data.")
        return
    
    # Generate the catchment JSON
    catchment_json = generate_catchment_json(generated_names)
    
    # Save to output file
    try:
        with open(output_path, 'w') as output_file:
            json.dump(catchment_json, output_file, indent=4)
        print(f"Successfully generated {output_path}")
        
        # Print summary
        print(f"\nGenerated catchment: {catchment_json['name']}")
        print(f"Number of HRUs: {len(catchment_json.get('HRUs', []))}")
        if catchment_json.get('HRUs'):
            sample_hru = catchment_json['HRUs'][0]
            print(f"Land cover types per HRU: {len(sample_hru['subcatchment'].get('landCoverTypes', []))}")
            if sample_hru['subcatchment'].get('landCoverTypes'):
                sample_lc = sample_hru['subcatchment']['landCoverTypes'][0]
                print(f"Buckets per land cover: {len(sample_lc.get('buckets', []))}")
            print(f"Particle size classes: {len(sample_hru['subcatchment'].get('particleSizeClasses', []))}")
        
    except Exception as e:
        print(f"Error writing output file: {e}")

if __name__ == "__main__":
    main()
