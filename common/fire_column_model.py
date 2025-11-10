"""
FireColumnModel - Python Implementation
Column-oriented fire air quality data model for efficient querying
"""

import csv
import os
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict


class FireColumnModel:
    """
    Column-oriented storage for fire air quality measurements.
    Provides efficient indexing and querying capabilities.
    """
    
    def __init__(self):
        # Columnar storage - parallel arrays
        self.latitudes: List[float] = []
        self.longitudes: List[float] = []
        self.datetimes: List[str] = []
        self.parameters: List[str] = []
        self.concentrations: List[float] = []
        self.units: List[str] = []
        self.raw_concentrations: List[float] = []
        self.aqis: List[int] = []
        self.categories: List[int] = []
        self.site_names: List[str] = []
        self.agency_names: List[str] = []
        self.aqs_codes: List[str] = []
        self.full_aqs_codes: List[str] = []
        
        # Index structures for fast lookups
        self._site_indices: Dict[str, List[int]] = defaultdict(list)
        self._parameter_indices: Dict[str, List[int]] = defaultdict(list)
        self._aqs_indices: Dict[str, List[int]] = defaultdict(list)
        
        # Metadata tracking
        self._unique_sites: Set[str] = set()
        self._unique_parameters: Set[str] = set()
        self._unique_agencies: Set[str] = set()
        self._datetime_range: List[str] = ["", ""]  # [min, max]
        
        # Geographic bounds
        self._min_latitude: Optional[float] = None
        self._max_latitude: Optional[float] = None
        self._min_longitude: Optional[float] = None
        self._max_longitude: Optional[float] = None
    
    def read_from_directory(self, directory_path: str, allowed_subdirs: List[str] = None) -> None:
        """
        Load all CSV files from a directory (recursively).
        
        Args:
            directory_path: Path to directory containing CSV files
            allowed_subdirs: Optional list of subdirectory names to load (for partitioning)
        """
        csv_files = self._get_csv_files(directory_path, allowed_subdirs)
        
        if not csv_files:
            print(f"[FireColumnModel] No CSV files found in: {directory_path}")
            return
        
        if allowed_subdirs:
            print(f"[FireColumnModel] Processing {len(csv_files)} CSV files from {len(allowed_subdirs)} subdirectories...")
        else:
            print(f"[FireColumnModel] Processing {len(csv_files)} CSV files from {directory_path}...")
        
        for csv_file in csv_files:
            try:
                self.read_from_csv(csv_file)
            except Exception as e:
                print(f"[FireColumnModel] Error processing {csv_file}: {e}")
        
        print(f"[FireColumnModel] Loaded {self.measurement_count()} measurements from {self.site_count()} sites")
    
    def read_from_csv(self, filename: str) -> None:
        """
        Load measurements from a single CSV file.
        
        Args:
            filename: Path to CSV file
        
        Expected CSV format (no header):
        latitude,longitude,datetime,parameter,concentration,unit,raw_concentration,aqi,category,site_name,agency_name,aqs_code,full_aqs_code
        """
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            for row in reader:
                if len(row) < 13:
                    continue  # Skip incomplete rows
                
                try:
                    # Parse and validate data
                    latitude = float(row[0].strip('"'))
                    longitude = float(row[1].strip('"'))
                    datetime = row[2].strip('"')
                    parameter = row[3].strip('"')
                    concentration = float(row[4].strip('"'))
                    unit = row[5].strip('"')
                    raw_concentration = float(row[6].strip('"'))
                    aqi = int(row[7].strip('"'))
                    category = int(row[8].strip('"'))
                    site_name = row[9].strip('"')
                    agency_name = row[10].strip('"')
                    aqs_code = row[11].strip('"')
                    full_aqs_code = row[12].strip('"')
                    
                    # Insert measurement
                    self.insert_measurement(
                        latitude, longitude, datetime, parameter,
                        concentration, unit, raw_concentration,
                        aqi, category, site_name, agency_name,
                        aqs_code, full_aqs_code
                    )
                    
                except (ValueError, IndexError) as e:
                    # Skip rows with invalid data
                    continue
    
    def insert_measurement(
        self,
        latitude: float,
        longitude: float,
        datetime: str,
        parameter: str,
        concentration: float,
        unit: str,
        raw_concentration: float,
        aqi: int,
        category: int,
        site_name: str,
        agency_name: str,
        aqs_code: str,
        full_aqs_code: str
    ) -> None:
        """Insert a single measurement into the columnar storage."""
        # Append to columns
        self.latitudes.append(latitude)
        self.longitudes.append(longitude)
        self.datetimes.append(datetime)
        self.parameters.append(parameter)
        self.concentrations.append(concentration)
        self.units.append(unit)
        self.raw_concentrations.append(raw_concentration)
        self.aqis.append(aqi)
        self.categories.append(category)
        self.site_names.append(site_name)
        self.agency_names.append(agency_name)
        self.aqs_codes.append(aqs_code)
        self.full_aqs_codes.append(full_aqs_code)
        
        # Update indices
        new_index = len(self.latitudes) - 1
        self._update_indices(new_index)
        self._update_geographic_bounds(latitude, longitude)
        self._update_datetime_range(datetime)
        
        # Update metadata
        self._unique_sites.add(site_name)
        self._unique_parameters.add(parameter)
        self._unique_agencies.add(agency_name)
    
    def get_indices_by_site(self, site_name: str) -> List[int]:
        """Get all measurement indices for a specific site."""
        return self._site_indices.get(site_name, [])
    
    def get_indices_by_parameter(self, parameter: str) -> List[int]:
        """Get all measurement indices for a specific parameter (e.g., PM2.5)."""
        return self._parameter_indices.get(parameter, [])
    
    def get_indices_by_aqs_code(self, aqs_code: str) -> List[int]:
        """Get all measurement indices for a specific AQS code."""
        return self._aqs_indices.get(aqs_code, [])
    
    def measurement_count(self) -> int:
        """Get total number of measurements."""
        return len(self.latitudes)
    
    def site_count(self) -> int:
        """Get number of unique sites."""
        return len(self._unique_sites)
    
    def unique_sites(self) -> Set[str]:
        """Get set of unique site names."""
        return self._unique_sites
    
    def unique_parameters(self) -> Set[str]:
        """Get set of unique parameters."""
        return self._unique_parameters
    
    def unique_agencies(self) -> Set[str]:
        """Get set of unique agencies."""
        return self._unique_agencies
    
    def datetime_range(self) -> Tuple[str, str]:
        """Get datetime range (min, max)."""
        return (self._datetime_range[0], self._datetime_range[1])
    
    def geographic_bounds(self) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Get geographic bounds (min_lat, max_lat, min_lon, max_lon)."""
        return (self._min_latitude, self._max_latitude, self._min_longitude, self._max_longitude)
    
    def _update_indices(self, index: int) -> None:
        """Update index structures for a new measurement."""
        if index >= len(self.site_names):
            return
        
        self._site_indices[self.site_names[index]].append(index)
        self._parameter_indices[self.parameters[index]].append(index)
        self._aqs_indices[self.aqs_codes[index]].append(index)
    
    def _update_geographic_bounds(self, latitude: float, longitude: float) -> None:
        """Update geographic bounds tracking."""
        if self._min_latitude is None:
            self._min_latitude = self._max_latitude = latitude
            self._min_longitude = self._max_longitude = longitude
        else:
            self._min_latitude = min(self._min_latitude, latitude)
            self._max_latitude = max(self._max_latitude, latitude)
            self._min_longitude = min(self._min_longitude, longitude)
            self._max_longitude = max(self._max_longitude, longitude)
    
    def _update_datetime_range(self, datetime: str) -> None:
        """Update datetime range tracking."""
        if not self._datetime_range[0] or datetime < self._datetime_range[0]:
            self._datetime_range[0] = datetime
        if not self._datetime_range[1] or datetime > self._datetime_range[1]:
            self._datetime_range[1] = datetime
    
    def _get_csv_files(self, directory_path: str, allowed_subdirs: List[str] = None) -> List[str]:
        """
        Recursively find all CSV files in directory.
        
        Args:
            directory_path: Base directory path
            allowed_subdirs: Optional list of allowed subdirectory names (for partitioning)
        """
        csv_files = []
        
        try:
            for root, dirs, files in os.walk(directory_path):
                # If we have partition restrictions, check if current directory is allowed
                if allowed_subdirs:
                    # Get the immediate subdirectory name relative to directory_path
                    rel_path = os.path.relpath(root, directory_path)
                    # Check if this directory or its parent is in allowed list
                    dir_name = rel_path.split(os.sep)[0]
                    if dir_name != '.' and dir_name not in allowed_subdirs:
                        continue  # Skip this directory
                
                for file in files:
                    if file.endswith('.csv'):
                        csv_files.append(os.path.join(root, file))
        except Exception as e:
            print(f"[FireColumnModel] Error accessing directory {directory_path}: {e}")
        
        csv_files.sort()
        return csv_files

