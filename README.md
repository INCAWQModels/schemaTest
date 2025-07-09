# INCA/PERSiST Schema Test Repository Documentation

## Overview

This repository contains code and schemas for testing how JSON schemas can be used to create and manage parameter sets for new versions of the INCA/PERSiST family of hydrological models. The repository provides a complete workflow from schema definition to time series generation for hydrological modeling.

## Repository Structure

```
schemaTest/
├── README.md
├── .gitignore
├── schemas/           # JSON schema definitions
├── code/             # Python tools and utilities
│   ├── calculations/ # Hydrological calculation modules
│   └── timeSeries/   # Time series handling tools
└── testData/         # Sample data and generated files
```

## Core Components

### 1. JSON Schemas (`schemas/`)

The repository defines a hierarchical set of JSON schemas for hydrological model components:

#### Primary Model Structure Schemas
- **`catchment.json`** - Top-level catchment definition containing HRUs
- **`HRU.json`** - Hydrological Response Unit with coordinates, subcatchment, and reach
- **`subcatchment.json`** - Contains land cover types, particle size classes, and precipitation adjustments
- **`landCover.json`** - Land cover type properties including evaporation, snowpack, soil temperature, buckets, and soils
- **`reach.json`** - River reach properties with Manning's equation parameters and dimensions

#### Component Schemas
- **`bucket.json`** - Water routing bucket properties with evaporation, soil temperature, and water depth parameters
- **`particleSizeClass.json`** - Particle (grain) size class properties for sediment modeling
- **`landCoverSoils.json`** - Terrestrial soil properties specific to land cover types
- **`timeSeries.json`** - Time series definitions for all model components
- **`generic.json`** - Generic header template with name and abbreviation
- **`schemas.json`** - Index file mapping all schema URLs

#### Key Schema Features
- **Hierarchical Structure**: Catchment → HRUs → Subcatchments → Land Cover Types → Buckets
- **Parameter Validation**: Min/max values, defaults, and type checking
- **Cross-References**: Uses `$ref` to link related schemas
- **Time Series Integration**: Embedded time series definitions for all components

### 2. Python Tools (`code/`)

#### GUI Applications
- **`getNames.py`** - Interactive GUI for creating basic naming structure (`names.json`)
  - Tabbed interface for catchment, HRUs, land cover types, buckets, and grain size classes
  - Built-in tooltips and validation
  - Save/load functionality

- **`catchment_editor.py`** - Advanced GUI editor for complete catchment structure
  - Hierarchical navigation through catchment components
  - Editable parameter values with type validation
  - Special handling for bucket connections and downstream HRU selection

- **`model_timeseries_editor.py`** - GUI editor for ModelTimeSeries.json files
  - File picker integration for CSV selection
  - Folder management for time series files
  - Batch editing capabilities

- **`timeseries_viewer.py`** - Time series data visualization tool
  - Multi-file CSV loading and plotting
  - Matplotlib integration for professional plots
  - Data summary and statistics

#### Core Generation Tools
- **`makeSchema.py`** - Generates full catchment structure from basic names
  - Creates complete parameter hierarchy
  - Populates default values from schemas
  - Generates bucket connection arrays

- **`model_timeseries_generator.py`** - Creates ModelTimeSeries.json structure
  - Maps time series requirements to file names
  - Supports fallback when catchment structure unavailable
  - Comprehensive metadata generation

- **`hydro_model_timeseries_generator.py`** - Main hydrological time series generator
  - Validates input temperature/precipitation data
  - Generates solar radiation, PET, rain/snow, and soil temperature time series
  - Comprehensive logging and error handling
  - Supports both GUI and command-line operation

#### Time Series Tools (`code/timeSeries/`)
- **`timeSeries.py`** - Core TimeSeries class
  - UUID-based column identification
  - Metadata management
  - CSV/JSON serialization
  - Merge functionality for combining time series

- **`persist_timeseries_converter.py`** - Converts PERSiST .dat files to TimeSeries format
  - Robust parsing with detailed error reporting
  - Automatic metadata generation
  - Command-line interface

#### Calculation Modules (`code/calculations/`)
- **`calculate_solar_radiation.py`** - Solar radiation calculation using astronomical formulas
  - Midpoint calculation approach for representative values
  - Latitude/longitude/timezone support
  - Multiple timestep support (daily, hourly, etc.)

- **`calculate_potential_evapotranspiration.py`** - Enhanced Jensen-Haise PET calculation
  - Land cover-specific parameters (solarRadiationScalingFactor, growingDegreeOffset)
  - Automatic timestep scaling from metadata
  - Temperature constraints (PET = 0 when adjusted temperature ≤ 0°C)

- **`calculate_rain_and_snow.py`** - Rain/snow partitioning and snowmelt modeling
  - Degree-day snowmelt model with timestep scaling
  - Subcatchment and land cover precipitation adjustments
  - Snow accumulation and melt tracking

- **`calculate_soil_temperature.py`** - Soil temperature simulation
  - Thermal conductivity model with snow insulation
  - Bucket-specific parameters and land cover thermal properties
  - Formula: `δT = (D/86400) * S * (Kt/(1e6*Cs*Zs²)) * (T-Ts0)`

### 3. Test Data (`testData/`)

#### Sample Configuration Files
- **`names.json`** - Schema definition for basic naming structure
- **`generatedNames.json`** - Example basic configuration with 3 HRUs, 2 land cover types, 3 buckets

#### Generated Structure Files  
- **`generated_catchment.json`** - Complete catchment structure with:
  - 3 HRUs: Upper, Middle, Lower
  - 2 land cover types per HRU: Forest, Agriculture  
  - 3 buckets per land cover: Direct Runoff, Soilwater, Groundwater
  - Realistic parameter values and connection matrices

- **`ModelTimeSeries.json`** - Complete time series configuration mapping:
  - File names for all required time series
  - Mandatory/generated flags
  - Hierarchical structure matching catchment organization

## Workflow

### 1. Schema Definition Phase
```
schemas/ → Define JSON schemas for all model components
```

### 2. Basic Configuration Phase  
```
getNames.py → generatedNames.json
```

### 3. Full Structure Generation Phase
```
makeSchema.py → generated_catchment.json
model_timeseries_generator.py → ModelTimeSeries.json
```

### 4. Time Series Generation Phase
```
hydro_model_timeseries_generator.py → Complete time series files
```

### 5. Editing and Visualization Phase
```
catchment_editor.py → Edit parameters
model_timeseries_editor.py → Manage time series files
timeseries_viewer.py → Visualize results
```

## Key Features

### Schema-Driven Design
- **Validation**: All JSON structures validated against schemas
- **Documentation**: Self-documenting through schema descriptions
- **Defaults**: Automatic population of default values
- **Type Safety**: Strong typing with min/max constraints

### Hierarchical Parameter Management
- **Inheritance**: Parameters flow down from catchment to buckets
- **Overrides**: Lower-level parameters can override higher-level ones
- **Consistency**: Cross-component parameter validation

### Time Series Integration
- **Automatic Generation**: Physics-based calculation of derived time series
- **Metadata Preservation**: Full provenance tracking
- **Format Standardization**: Consistent CSV/JSON format
- **Timestep Flexibility**: Support for daily, hourly, or custom timesteps

### User-Friendly Tools
- **GUI Applications**: Point-and-click parameter editing
- **Tooltips and Help**: Context-sensitive documentation
- **Error Handling**: Comprehensive validation and error reporting
- **Visualization**: Built-in plotting and data exploration

### Scientific Rigor
- **Physics-Based Models**: Scientifically validated calculation methods
- **Parameter Constraints**: Realistic bounds on all parameters
- **Unit Consistency**: Proper unit handling and conversion
- **Timestep Scaling**: Automatic adjustment for different temporal resolutions

## Technical Architecture

### Design Patterns
- **Schema-First**: JSON schemas define all data structures
- **Component-Based**: Modular design with clear interfaces
- **Event-Driven**: GUI applications with proper event handling
- **Pipeline Architecture**: Clear data flow from input to output

### Data Flow
```
Input Data → Validation → Processing → Time Series Generation → Visualization
```

### Error Handling
- **Graceful Degradation**: Continue processing when possible
- **Detailed Logging**: Comprehensive error reporting
- **User Feedback**: Clear error messages and guidance
- **Recovery Mechanisms**: Fallback options when primary methods fail

## Dependencies

### Core Requirements
- **Python Standard Library**: All core functionality uses only standard library
- **tkinter**: For GUI applications (included with Python)
- **json, csv, datetime, math**: Standard library modules

### Optional Enhancements  
- **matplotlib**: For advanced plotting in timeseries_viewer.py
- **numpy**: For enhanced numerical operations (fallback provided)

### External Data
- **INCAMan.png**: Window icon for all GUI applications
- **PERSiST .dat files**: Input data format support

## Usage Examples

### Basic Workflow
```bash
# 1. Create basic names structure
python code/getNames.py

# 2. Generate full catchment structure  
python code/makeSchema.py

# 3. Generate time series structure
python code/model_timeseries_generator.py

# 4. Generate actual time series data
python code/hydro_model_timeseries_generator.py
```

### Advanced Usage
```bash
# Edit catchment parameters
python code/catchment_editor.py

# Manage time series files
python code/model_timeseries_editor.py

# Convert PERSiST data
python code/timeSeries/persist_timeseries_converter.py data.dat 2023-01-01T00:00:00

# View results
python code/timeSeries/timeseries_viewer.py
```

## File Naming Conventions

### Time Series Files
- **Temperature/Precipitation**: `PERSiST_{HRU_name}` 
- **Solar Radiation**: `{HRU_name}_solarRadiation`
- **PET**: `{HRU_name}_{LandCover_name}_potentialEvapotranspiration` 
- **Rain/Snow**: `{HRU_name}_{LandCover_name}_rainAndSnow`
- **Soil Temperature**: `{HRU_name}_{LandCover_name}_{Bucket_name}_soilTemperature`

### Configuration Files
- **Basic Names**: `generatedNames.json`
- **Full Structure**: `generated_catchment.json` 
- **Time Series Config**: `ModelTimeSeries.json`

## Future Extensions

### Planned Features
- **Water routing**: Between buckets and to reaches
- **Flow calculations**: In-reach hydraulics
- **Sediment transport**: Particle size class routing
- **Chemistry modules**: Nutrient and pollutant modeling
- **Calibration tools**: Parameter optimization
- **Uncertainty analysis**: Monte Carlo simulations

### Extension Points
- **New calculation modules**: Following established patterns
- **Additional schemas**: For new model components  
- **Enhanced GUIs**: More sophisticated parameter editing
- **Database integration**: For large-scale applications
- **Web interface**: Browser-based operation

This repository provides a complete, extensible framework for next-generation hydrological model development with strong emphasis on usability, scientific rigor, and maintainability.