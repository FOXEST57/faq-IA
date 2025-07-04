#!/bin/zsh

# --------------------------------------------------------------------------
# Marine Data Collection and Visualization Project Creator
# Version: 1.0.0
# --------------------------------------------------------------------------
# This script sets up a complete project structure for collecting, storing,
# and visualizing marine data including tides and weather conditions.
# --------------------------------------------------------------------------

PROJECT_NAME="marine-data-hub"
LOG_FILE="project_creation.log"

# --- Script Setup ---
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error when substituting.
set -o pipefail  # Return value of a pipeline is the status of the last command

# --- Logging Function ---
log() {
  local level="$1"
  local message="$2"
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# --- Error Handling ---
handle_error() {
  local line_number=$1
  local error_message=$2
  log "ERROR" "Error at line $line_number: $error_message"
  log "ERROR" "Script execution aborted"
  exit 1
}

# Setup error trap
trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# --- Welcome and Pre-checks ---
log "INFO" "🌊 Setting up the '$PROJECT_NAME' marine app project structure with web scraping..."

# Check for required tools
for tool in sqlite3 python3 pip; do
  if ! command -v $tool &> /dev/null; then
    log "ERROR" "$tool is required but not installed. Please install it and try again."
    exit 1
  fi
done

# Handle existing directory
if [[ -d "$PROJECT_NAME" ]]; then
    log "WARNING" "Directory '$PROJECT_NAME' already exists."
    read -q "REPLY?Do you want to remove it and continue? (y/N) "
    if [[ "$REPLY" = "y" || "$REPLY" = "Y" ]]; then
        log "INFO" "Removing existing directory..."
        rm -rf "$PROJECT_NAME"
    else
        log "INFO" "Aborting script. No changes made."
        exit 0
    fi
fi

# --- Create Project Root Directory ---
log "INFO" "Creating project root: $PROJECT_NAME/"
mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

# --- Create Project Structure ---
log "INFO" "Creating project structure..."
# Create directories with proper structure
mkdir -p data/raw data/processed logs config utils/scrapers utils/api tests/unit tests/integration docs

# Create __init__.py files to make directories Python packages
touch utils/__init__.py utils/scrapers/__init__.py utils/api/__init__.py tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py

# --- Create requirements.txt ---
log "INFO" "Creating requirements.txt..."
cat << 'EOF' > requirements.txt
# Web framework and data visualization
streamlit==1.24.0
flask==2.3.2
flask-cors==4.0.0
plotly==5.15.0

# Data handling and processing
pandas==2.0.3
numpy==1.24.3

# Web scraping
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.2

# Database
SQLAlchemy==2.0.17

# Testing
pytest==7.3.1
pytest-cov==4.1.0

# Utilities
python-dotenv==1.0.0
schedule==1.2.0
tenacity==8.2.2
EOF

# --- Create config/settings.py ---
log "INFO" "Creating config/settings.py..."
mkdir -p config
cat << 'EOF' > config/settings.py
"""
Application configuration settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Database settings
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'data', 'marine_data.db'))

# API settings
API_HOST = os.environ.get('API_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('API_PORT', 5000))
API_DEBUG = os.environ.get('API_DEBUG', 'False') == 'True'

# Web scraping settings
USER_AGENT = 'MarineDataHubBot/1.0 (https://example.com/bot; bot@example.com)'
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
RETRY_COUNT = int(os.environ.get('RETRY_COUNT', 3))
RETRY_BACKOFF = int(os.environ.get('RETRY_BACKOFF', 2))

# Locations configuration - can be extended or moved to database
LOCATIONS = [
    {
        "country": "France",
        "city": "Romagny",
        "tide_forecast_slug": "Romagny",
        "weather_com_id": "FRXX0076:1:FR"
    },
    {
        "country": "USA",
        "city": "New York",
        "tide_forecast_slug": "New-York",
        "weather_com_id": "USNY0996:1:US"
    },
    {
        "country": "Australia",
        "city": "Sydney",
        "tide_forecast_slug": "Sydney",
        "weather_com_id": "ASXX0112:1:AS"
    }
]

# Logging settings
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOG_FILE = os.environ.get('LOG_FILE', os.path.join(BASE_DIR, 'logs', 'app.log'))
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Update interval in minutes
DATA_UPDATE_INTERVAL = int(os.environ.get('DATA_UPDATE_INTERVAL', 360))  # 6 hours by default
EOF

# --- Create utils/database.py ---
log "INFO" "Creating utils/database.py..."
cat << 'EOF' > utils/database.py
"""
Database management module for marine data.
Provides functions to connect to the database and perform CRUD operations.
"""
import sqlite3
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

# Set up logging
logger = logging.getLogger(__name__)

class MarineDB:
    """
    Marine database management class.
    Handles all database operations for storing and retrieving marine data.
    """
    def __init__(self, db_path=None):
        """
        Initialize the database connection and create tables if they don't exist.
        
        Args:
            db_path (str, optional): Path to the SQLite database file.
                                     If None, uses the default path.
        """
        if db_path is None:
            # Get the base directory of the project
            base_dir = Path(__file__).resolve().parent.parent
            # Default path in the data directory
            db_path = os.path.join(base_dir, 'data', 'marine_data.db')
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        logger.info(f"Initializing database at {db_path}")
        self._create_tables()

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures connections are properly closed after use.
        
        Yields:
            sqlite3.Connection: An active database connection.
        """
        connection = None
        try:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            yield connection
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                connection.close()

    def _create_tables(self):
        """
        Creates all necessary database tables if they don't exist.
        Includes tables for observations, locations, and metadata.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create locations table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    country TEXT NOT NULL,
                    city TEXT NOT NULL,
                    tide_forecast_slug TEXT,
                    weather_com_id TEXT,
                    last_updated DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(country, city)
                )
                ''')
                
                # Create observations table with foreign key to locations
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_id INTEGER,
                    observation_time DATETIME NOT NULL,
                    tide_type TEXT CHECK(tide_type IN ('high', 'low', 'normal')),
                    coefficient REAL,
                    weather_condition TEXT,
                    wind_speed REAL,
                    wave_height REAL,
                    temperature REAL,
                    pressure REAL,
                    humidity REAL,
                    visibility TEXT,
                    uv_index INTEGER,
                    last_fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (location_id) REFERENCES locations(id),
                    UNIQUE(location_id, observation_time)
                )
                ''')
                
                # Create table for data source metadata
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    last_successful_fetch DATETIME,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, url)
                )
                ''')
                
                conn.commit()
                logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            logger.error(f"Database error during table creation: {e}")
            raise

    def ensure_location_exists(self, country, city, tide_forecast_slug=None, weather_com_id=None):
        """
        Ensures a location exists in the database, creating it if necessary.
        
        Args:
            country (str): Country name
            city (str): City name
            tide_forecast_slug (str, optional): Slug for tide forecast website
            weather_com_id (str, optional): ID for weather.com
            
        Returns:
            int: The location ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if location exists
                cursor.execute(
                    "SELECT id FROM locations WHERE country = ? AND city = ?", 
                    (country, city)
                )
                result = cursor.fetchone()
                
                if result:
                    location_id = result['id']
                    # Update slugs if provided
                    if tide_forecast_slug or weather_com_id:
                        updates = []
                        params = []
                        
                        if tide_forecast_slug:
                            updates.append("tide_forecast_slug = ?")
                            params.append(tide_forecast_slug)
                        
                        if weather_com_id:
                            updates.append("weather_com_id = ?")
                            params.append(weather_com_id)
                        
                        updates.append("last_updated = ?")
                        params.append(datetime.now())
                        params.append(location_id)
                        
                        cursor.execute(
                            f"UPDATE locations SET {', '.join(updates)} WHERE id = ?",
                            tuple(params)
                        )
                        conn.commit()
                else:
                    # Create new location
                    cursor.execute(
                        """INSERT INTO locations 
                           (country, city, tide_forecast_slug, weather_com_id, last_updated) 
                           VALUES (?, ?, ?, ?, ?)""",
                        (country, city, tide_forecast_slug, weather_com_id, datetime.now())
                    )
                    conn.commit()
                    location_id = cursor.lastrowid
                    
                return location_id
        except sqlite3.Error as e:
            logger.error(f"Database error ensuring location {city}, {country}: {e}")
            raise

    def get_available_countries(self):
        """
        Returns a list of unique countries present in the locations table.
        
        Returns:
            list: List of country names
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT country FROM locations ORDER BY country")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error getting countries: {e}")
            return []

    def get_cities_by_country(self, country):
        """
        Returns a list of unique cities for a given country.
        
        Args:
            country (str): Country name
            
        Returns:
            list: List of city names
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT city FROM locations WHERE country = ? ORDER BY city", 
                    (country,)
                )
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Database error getting cities for {country}: {e}")
            return []

    def get_location_id(self, country, city):
        """
        Gets the location ID for a given country and city.
        
        Args:
            country (str): Country name
            city (str): City name
            
        Returns:
            int: Location ID or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM locations WHERE country = ? AND city = ?", 
                    (country, city)
                )
                result = cursor.fetchone()
                return result['id'] if result else None
        except sqlite3.Error as e:
            logger.error(f"Database error getting location ID for {city}, {country}: {e}")
            return None

    def get_today_data(self, country, city):
        """
        Fetches all observations for the current day for the specified location.
        
        Args:
            country (str): Country name
            city (str): City name
            
        Returns:
            list: List of observation records as dict-like objects
        """
        try:
            location_id = self.get_location_id(country, city)
            if not location_id:
                logger.warning(f"Location not found: {city}, {country}")
                return []
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today_str = datetime.now().strftime('%Y-%m-%d')
                cursor.execute('''
                    SELECT o.*, l.country, l.city 
                    FROM observations o
                    JOIN locations l ON o.location_id = l.id
                    WHERE date(o.observation_time) = ?
                    AND o.location_id = ?
                    ORDER BY o.observation_time
                ''', (today_str, location_id))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error getting today's data for {city}, {country}: {e}")
            return []

    def get_latest_observation(self, country, city):
        """
        Fetches the single latest observation for the specified location.
        
        Args:
            country (str): Country name
            city (str): City name
            
        Returns:
            sqlite3.Row: Latest observation record or None if not found
        """
        try:
            location_id = self.get_location_id(country, city)
            if not location_id:
                logger.warning(f"Location not found: {city}, {country}")
                return None
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT o.*, l.country, l.city 
                    FROM observations o
                    JOIN locations l ON o.location_id = l.id
                    WHERE o.location_id = ?
                    ORDER BY o.observation_time DESC
                    LIMIT 1
                ''', (location_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database error getting latest observation for {city}, {country}: {e}")
            return None

    def insert_observation(self, country, city, obs_time, tide_type, coefficient, 
                           weather_condition, wind_speed, wave_height=None, 
                           temperature=None, pressure=None, humidity=None,
                           visibility=None, uv_index=None):
        """
        Inserts a single observation into the database.
        
        Args:
            country (str): Country name
            city (str): City name
            obs_time (datetime or str): Observation time
            tide_type (str): Tide type (high/low/normal)
            coefficient (float): Tide coefficient
            weather_condition (str): Weather condition description
            wind_speed (float): Wind speed
            wave_height (float, optional): Wave height
            temperature (float, optional): Temperature
            pressure (float, optional): Atmospheric pressure
            humidity (float, optional): Humidity percentage
            visibility (str, optional): Visibility description
            uv_index (int, optional): UV index
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure location exists
            location_id = self.ensure_location_exists(country, city)
            
            # Format observation time if it's a datetime object
            if isinstance(obs_time, datetime):
                obs_time_str = obs_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                obs_time_str = obs_time  # Assume it's already a string
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if an observation already exists for this time and location
                cursor.execute(
                    "SELECT id FROM observations WHERE location_id = ? AND observation_time = ?",
                    (location_id, obs_time_str)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing observation
                    cursor.execute('''
                        UPDATE observations SET
                            tide_type = ?,
                            coefficient = ?,
                            weather_condition = ?,
                            wind_speed = ?,
                            wave_height = ?,
                            temperature = ?,
                            pressure = ?,
                            humidity = ?,
                            visibility = ?,
                            uv_index = ?,
                            last_fetched_at = ?
                        WHERE id = ?
                    ''', (
                        tide_type, coefficient, weather_condition, wind_speed,
                        wave_height, temperature, pressure, humidity,
                        visibility, uv_index, datetime.now(), existing['id']
                    ))
                else:
                    # Insert new observation
                    cursor.execute('''
                        INSERT INTO observations (
                            location_id, observation_time, tide_type,
                            coefficient, weather_condition, wind_speed,
                            wave_height, temperature, pressure, humidity,
                            visibility, uv_index, last_fetched_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        location_id, obs_time_str, tide_type,
                        coefficient, weather_condition, wind_speed,
                        wave_height, temperature, pressure, humidity,
                        visibility, uv_index, datetime.now()
                    ))
                
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Database error during observation insertion: {e}")
            return False

    def clear_data_for_date(self, country, city, date_str):
        """
        Clears all observations for a specific location and date.
        
        Args:
            country (str): Country name
            city (str): City name
            date_str (str): Date string in YYYY-MM-DD format
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            location_id = self.get_location_id(country, city)
            if not location_id:
                logger.warning(f"Location not found: {city}, {country}")
                return False
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM observations
                    WHERE location_id = ?
                    AND date(observation_time) = ?
                ''', (location_id, date_str))
                conn.commit()
                logger.info(f"Cleared {cursor.rowcount} observations for {city}, {country} on {date_str}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Database error during data clearing for {city}, {country}: {e}")
            return False

    def get_data_for_date_range(self, country, city, start_date, end_date):
        """
        Fetches observations for a location within a specified date range.
        
        Args:
            country (str): Country name
            city (str): City name
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            list: List of observation records
        """
        try:
            location_id = self.get_location_id(country, city)
            if not location_id:
                logger.warning(f"Location not found: {city}, {country}")
                return []
                
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT o.*, l.country, l.city 
                    FROM observations o
                    JOIN locations l ON o.location_id = l.id
                    WHERE o.location_id = ?
                    AND date(o.observation_time) BETWEEN ? AND ?
                    ORDER BY o.observation_time
                ''', (location_id, start_date, end_date))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database error getting data range for {city}, {country}: {e}")
            return []
EOF

# --- Create utils/helpers.py ---
log "INFO" "Creating utils/helpers.py..."
cat << 'EOF' > utils/helpers.py
"""
Helper functions used across the marine data application.
Provides utility functions for data processing, formatting, and validation.
"""
import logging
import json
import re
from datetime import datetime, timedelta
import os

# Set up logging
logger = logging.getLogger(__name__)

def setup_logging(log_level='INFO', log_file=None, log_format=None):
    """
    Configure application-wide logging.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file (str, optional): Path to log file
        log_format (str, optional): Log message format
    """
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=handlers
    )
    
    logger.info(f"Logging configured with level {log_level}")

def parse_datetime(date_str, formats=None):
    """
    Parse a datetime string using multiple possible formats.
    
    Args:
        date_str (str): Date string to parse
        formats (list, optional): List of format strings to try
        
    Returns:
        datetime: Parsed datetime object or None if parsing fails
    """
    if formats is None:
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%d/%m/%Y %H:%M',
            '%H:%M'  # Time only (assumes today's date)
        ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If format doesn't include date, assume today
            if fmt == '%H:%M':
                today = datetime.now().date()
                dt = datetime.combine(today, dt.time())
            return dt
        except ValueError:
            continue
    
    logger.error(f"Failed to parse datetime: {date_str}")
    return None

def format_tide_coefficient(value):
    """
    Format a tide coefficient value for display.
    
    Args:
        value (float): Tide coefficient value
        
    Returns:
        str: Formatted tide coefficient with interpretation
    """
    if value is None:
        return "N/A"
        
    try:
        coef = float(value)
        
        # Interpret the coefficient
        if coef < 20:
            interpretation = "Neap tide (very weak)"
        elif coef < 40:
            interpretation = "Weak tide"
        elif coef < 70:
            interpretation = "Average tide"
        elif coef < 90:
            interpretation = "Strong tide"
        else:
            interpretation = "Spring tide (very strong)"
            
        return f"{coef:.1f} ({interpretation})"
    except (ValueError, TypeError):
        logger.warning(f"Invalid tide coefficient value: {value}")
        return "N/A"

def validate_country_city(country, city):
    """
    Validate country and city names.
    
    Args:
        country (str): Country name
        city (str): City name
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not country or not isinstance(country, str):
        return False, "Country name is required and must be a string"
    
    if not city or not isinstance(city, str):
        return False, "City name is required and must be a string"
    
    # Basic validation - could be extended with more sophisticated checks
    country_pattern = r'^[A-Za-z\s\-\'\.]{2,}$'
    city_pattern = r'^[A-Za-z\s\-\'\.]{2,}$'
    
    if not re.match(country_pattern, country):
        return False, f"Invalid country name format: {country}"
    
    if not re.match(city_pattern, city):
        return False, f"Invalid city name format: {city}"
    
    return True, ""

def safe_json_loads(json_str, default=None):
    """
    Safely parse JSON string.
    
    Args:
        json_str (str): JSON string to parse
        default (any, optional): Default value to return if parsing fails
        
    Returns:
        dict/list: Parsed JSON data or default value if parsing fails
    """
    if not json_str:
        return default
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return default

def calculate_next_update_time(interval_minutes=360):
    """
    Calculate the next update time based on the current time.
    
    Args:
        interval_minutes (int, optional): Update interval in minutes
        
    Returns:
        datetime: Next update time
    """
    now = datetime.now()
    return now + timedelta(minutes=interval_minutes)

def get_wind_description(speed_kmh):
    """
    Get a descriptive term for wind speed.
    
    Args:
        speed_kmh (float): Wind speed in km/h
        
    Returns:
        str: Wind description
    """
    try:
        speed = float(speed_kmh)
        
        if speed < 1:
            return "Calm"
        elif speed < 6:
            return "Light Air"
        elif speed < 12:
            return "Light Breeze"
        elif speed < 20:
            return "Gentle Breeze"
        elif speed < 29:
            return "Moderate Breeze"
        elif speed < 39:
            return "Fresh Breeze"
        elif speed < 50:
            return "Strong Breeze"
        elif speed < 62:
            return "Near Gale"
        elif speed < 75:
            return "Gale"
        elif speed < 89:
            return "Strong Gale"
        elif speed < 103:
            return "Storm"
        elif speed < 118:
            return "Violent Storm"
        else:
            return "Hurricane Force"
    except (ValueError, TypeError):
        logger.warning(f"Invalid wind speed value: {speed_kmh}")
        return "Unknown"
EOF

# --- Create utils/scrapers/tides.py ---
log "INFO" "Creating utils/scrapers/tides.py..."
mkdir -p utils/scrapers
cat << 'EOF' > utils/scrapers/tides.py
"""
Web scraper for tide data from tide-forecast.com.
Extracts tide times, types, and coefficients.
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set up logging
logger = logging.getLogger(__name__)

class TideDataScraper:
    """
    Scraper for tide data from tide-forecast.com.
    Handles requests, parsing, and data extraction.
    """
    
    def __init__(self, user_agent=None, timeout=30):
        """
        Initialize the tide data scraper.
        
        Args:
            user_agent (str, optional): User agent string for HTTP requests
            timeout (int, optional): Request timeout in seconds
        """
        self.base_url = "https://www.tide-forecast.com/locations"
        self.user_agent = user_agent or 'MarineDataHubBot/1.0'
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure session headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
        @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def fetch_tide_data(self, location_slug):
        """
        Fetches tide data for a specific location.
        
        Args:
            location_slug (str): Location slug for tide-forecast.com
            
        Returns:
            list: List of tide data entries
        """
        url = f"{self.base_url}/{location_slug}/tides/latest"
        logger.info(f"Fetching tide data from {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return self._parse_tide_data(response.content, location_slug)
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching tide data for {location_slug}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching tide data for {location_slug}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching tide data for {location_slug}: {e}")
            return []
    
    def _parse_tide_data(self, html_content, location_slug):
        """
        Parses HTML content to extract tide data.
        
        Args:
            html_content (bytes): HTML content to parse
            location_slug (str): Location slug (for logging)
            
        Returns:
            list: List of tide data entries
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        tide_data = []
        
        try:
            # Try to find the tide table
            tide_table = soup.find("table", class_="tide-table")
            if not tide_table:
                logger.warning(f"Tide table not found for {location_slug}. HTML structure may have changed.")
                # Try alternative selectors
                tide_table = soup.find("table", class_="tideTable")
                
            if not tide_table:
                logger.error(f"Could not find tide table for {location_slug} using any known selectors.")
                return []
            
            # Get the current date from the page if available
            date_header = soup.find("h4", class_="tide-day")
            today = datetime.now().date()
            if date_header and date_header.text:
                try:
                    # Try to parse the date from the header
                    date_text = date_header.text.strip()
                    date_match = re.search(r'(\d{1,2})[a-z]{2} (\w+) (\d{4})', date_text)
                    if date_match:
                        day, month, year = date_match.groups()
                        today = datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date()
                except Exception as e:
                    logger.warning(f"Failed to parse date from header: {e}")
            
            # Parse data rows
            data_rows = tide_table.find_all("tr")[1:]  # Skip header row
            
            for row in data_rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    try:
                        # Extract time
                        time_str = cols[0].text.strip()
                        # Extract tide type
                        tide_type = cols[1].text.strip().lower()
                        # Extract coefficient
                        coefficient_str = cols[2].text.strip()
                        
                        # Parse time and combine with date
                        time_obj = datetime.strptime(time_str, '%H:%M').time()
                        observation_time = datetime.combine(today, time_obj)
                        
                        # Clean and parse coefficient
                        coefficient = None
                        # Remove non-numeric characters except decimal point
                        clean_coeff = ''.join(filter(lambda x: x.isdigit() or x == '.', coefficient_str))
                        if clean_coeff:
                            try:
                                coefficient = float(clean_coeff)
                            except ValueError:
                                logger.warning(f"Could not parse coefficient: {coefficient_str}")
                        
                        # Validate tide type
                        valid_tide_types = ['high', 'low', 'normal']
                        if tide_type not in valid_tide_types:
                            if 'high' in tide_type.lower():
                                tide_type = 'high'
                            elif 'low' in tide_type.lower():
                                tide_type = 'low'
                            else:
                                tide_type = 'normal'
                        
                        tide_data.append({
                            'observation_time': observation_time,
                            'tide_type': tide_type,
                            'coefficient': coefficient
                        })
                    except Exception as e:
                        logger.warning(f"Error parsing tide row: {e}")
                        continue
            
            return tide_data
        except Exception as e:
            logger.error(f"Error parsing tide data for {location_slug}: {e}")
            return []
EOF

# --- Create utils/scrapers/weather.py ---
log "INFO" "Creating utils/scrapers/weather.py..."
cat << 'EOF' > utils/scrapers/weather.py
"""
Web scraper for weather data from weather.com.
Extracts current weather conditions, wind speed, and other metrics.
"""
import requests
from bs4 import BeautifulSoup
import logging
import re
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Set up logging
logger = logging.getLogger(__name__)

class WeatherDataScraper:
    """
    Scraper for weather data from weather.com.
    Handles requests, parsing, and data extraction.
    """
    
    def __init__(self, user_agent=None, timeout=30):
        """
        Initialize the weather data scraper.
        
        Args:
            user_agent (str, optional): User agent string for HTTP requests
            timeout (int, optional): Request timeout in seconds
        """
        self.base_url = "https://www.weather.com/weather/today/l"
        self.user_agent = user_agent or 'MarineDataHubBot/1.0'
        self.timeout = timeout
        self.session = requests.Session()
        
        # Configure session headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def fetch_weather_data(self, location_id):
        """
        Fetches weather data for a specific location.
        
        Args:
            location_id (str): Location ID for weather.com
            
        Returns:
            dict: Weather data dictionary
        """
        url = f"{self.base_url}/{location_id}"
        logger.info(f"Fetching weather data from {url}")
        
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return self._parse_weather_data(response.content, location_id)
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching weather data for {location_id}: {e}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching weather data for {location_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching weather data for {location_id}: {e}")
            return self._get_default_weather_data()
    
    def _parse_weather_data(self, html_content, location_id):
        """
        Parses HTML content to extract weather data.
        
        Args:
            html_content (bytes): HTML content to parse
            location_id (str): Location ID (for logging)
            
        Returns:
            dict: Weather data dictionary
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        weather_data = self._get_default_weather_data()
        
        try:
            # Find weather condition - try multiple possible class names
            condition_selectors = [
                "div.CurrentConditions--phraseValue--2xXSr",
                "div[data-testid='wxPhrase']",
                "div.condition-data"
            ]
            
            for selector in condition_selectors:
                condition_element = soup.select_one(selector)
                if condition_element:
                    weather_data['weather_condition'] = condition_element.text.strip()
                    break
            
            # Find wind speed - try multiple possible class names
            wind_selectors = [
                "span.Wind--windValue--3Kc1Z",
                "span[data-testid='Wind']",
                "div.wind-speed"
            ]
            
            for selector in wind_selectors:
                wind_element = soup.select_one(selector)
                if wind_element:
                    wind_text = wind_element.text.strip()
                    # Extract numeric part of wind speed
                    wind_match = re.search(r'(\d+(?:\.\d+)?)', wind_text)
                    if wind_match:
                        try:
                            weather_data['wind_speed'] = float(wind_match.group(1))
                        except ValueError:
                            logger.warning(f"Could not parse wind speed: {wind_text}")
                    break
            
            # Find temperature
            temp_selectors = [
                "span[data-testid='TemperatureValue']",
                "div.temperature"
            ]
            
            for selector in temp_selectors:
                temp_element = soup.select_one(selector)
                if temp_element:
                    temp_text = temp_element.text.strip()
                    # Extract numeric part of temperature
                    temp_match = re.search(r'(\d+(?:\.\d+)?)', temp_text)
                    if temp_match:
                        try:
                            weather_data['temperature'] = float(temp_match.group(1))
                        except ValueError:
                            logger.warning(f"Could not parse temperature: {temp_text}")
                    break
            
            # Find humidity
            humidity_selectors = [
                "span[data-testid='PercentageValue']",
                "div.humidity"
            ]
            
            for selector in humidity_selectors:
                humidity_element = soup.select_one(selector)
                if humidity_element:
                    humidity_text = humidity_element.text.strip()
                    # Extract numeric part of humidity
                    humidity_match = re.search(r'(\d+)', humidity_text)
                    if humidity_match:
                        try:
                            weather_data['humidity'] = float(humidity_match.group(1))
                        except ValueError:
                            logger.warning(f"Could not parse humidity: {humidity_text}")
                    break
            
            return weather_data
        except Exception as e:
            logger.error(f"Error parsing weather data for {location_id}: {e}")
            return self._get_default_weather_data()
    
    def _get_default_weather_data(self):
        """
        Returns default weather data when fetching fails.
        
        Returns:
            dict: Default weather data dictionary
        """
        return {
            'weather_condition': 'Unavailable',
            'wind_speed': 0.0,
            'temperature': None,
            'humidity': None,
            'visibility': None,
            'pressure': None,
            'uv_index': None
        }
EOF

# --- Create utils/fetch_data.py ---
log "INFO" "Creating utils/fetch_data.py..."
cat << 'EOF' > utils/fetch_data.py
"""
Main module for fetching and updating marine data.
Coordinates scraping operations and database updates.
"""
import logging
import sys
import os
from datetime import datetime
import traceback
import time
import random

# Import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    LOCATIONS, USER_AGENT, REQUEST_TIMEOUT, 
    RETRY_COUNT, LOG_LEVEL, LOG_FILE
)

# Import scrapers and database
from utils.scrapers.tides import TideDataScraper
from utils.scrapers.weather import WeatherDataScraper
from utils.database import MarineDB
from utils.helpers import setup_logging

# Set up logging
logger = logging.getLogger(__name__)

class MarineDataFetcher:
    """
    Orchestrates the fetching and updating of marine data.
    Coordinates between scrapers and database operations.
    """
    
    def __init__(self):
        """Initialize the data fetcher with scrapers and database connection."""
        # Configure logging
        setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)
        
        logger.info("Initializing MarineDataFetcher")
        
        # Initialize scrapers
        self.tide_scraper = TideDataScraper(
            user_agent=USER_AGENT,
            timeout=REQUEST_TIMEOUT
        )
        
        self.weather_scraper = WeatherDataScraper(
            user_agent=USER_AGENT,
            timeout=REQUEST_TIMEOUT
        )
        
        # Initialize database
        self.db = MarineDB()
        
        # Load locations
        self.locations = LOCATIONS
    
    def update_all_locations(self):
        """
        Update marine data for all configured locations.
        Handles each location separately to prevent one failure from affecting others.
        """
        logger.info(f"Starting update for {len(self.locations)} locations")
        
        today_date_str = datetime.now().strftime('%Y-%m-%d')
        updated_count = 0
        error_count = 0
        
        for location in self.locations:
            try:
                country = location["country"]
                city = location["city"]
                tide_slug = location["tide_forecast_slug"]
                weather_id = location["weather_com_id"]
                
                logger.info(f"Processing data for {city}, {country}")
                
                # Add jitter to avoid hammering servers
                time.sleep(random.uniform(1, 3))
                
                # Ensure location exists in database
                self.db.ensure_location_exists(
                    country=country,
                    city=city,
                    tide_forecast_slug=tide_slug,
                    weather_com_id=weather_id
                )
                
                # Fetch weather data
                weather_data = self.weather_scraper.fetch_weather_data(weather_id)
                
                # Fetch tide data
                tide_entries = self.tide_scraper.fetch_tide_data(tide_slug)
                
                if not tide_entries:
                    logger.warning(f"No tide data fetched for {city}, {country}. Skipping.")
                    error_count += 1
                    continue
                
                # Clear existing data for today
                self.db.clear_data_for_date(country, city, today_date_str)
                
                # Insert new observations
                success_count = 0
                for tide_entry in tide_entries:
                    success = self.db.insert_observation(
                        country=country,
                        city=city,
                        obs_time=tide_entry['observation_time'],
                        tide_type=tide_entry['tide_type'],
                        coefficient=tide_entry['coefficient'],
                        weather_condition=weather_data['weather_condition'],
                        wind_speed=weather_data['wind_speed'],
                        temperature=weather_data.get('temperature'),
                        humidity=weather_data.get('humidity')
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        logger.warning(f"Failed to insert observation for {city}, {country}")
                
                logger.info(f"Successfully inserted {success_count} observations for {city}, {country}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating {location.get('city', 'unknown')}, {location.get('country', 'unknown')}: {e}")
                logger.debug(traceback.format_exc())
                error_count += 1
        
        logger.info(f"Update completed. Updated {updated_count} locations with {error_count} errors.")
        return updated_count, error_count

def run_update():
    """Run the update process as a standalone operation."""
    try:
        fetcher = MarineDataFetcher()
        updated, errors = fetcher.update_all_locations()
        
        if errors > 0:
            logger.warning(f"Update completed with {errors} errors. Check the log for details.")
            return 1
        else:
            logger.info("Update completed successfully.")
            return 0
    except Exception as e:
        logger.critical(f"Critical error during update: {e}")
        logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(run_update())
EOF

# --- Create app.py ---
log "INFO" "Creating app.py..."
cat << 'EOF' > app.py
"""
Streamlit web application for visualizing marine data.
Provides interactive tide and weather information for coastal locations.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import sys
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from project
from utils.database import MarineDB
from utils.helpers import setup_logging, format_tide_coefficient, get_wind_description
from config.settings import LOG_LEVEL, LOG_FILE

# Set up logging
setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Marine Data Hub",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {text-align: center; color: #1E88E5; font-size: 3em; margin-bottom: 20px;}
    .location-header {text-align: center; font-size: 2em; margin-bottom: 10px;}
    .data-section {padding: 10px; border-radius: 5px; margin-bottom: 15px;}
    .tide-high {background-color: #bbdefb; padding: 10px; border-radius: 5px;}
    .tide-low {background-color: #ffecb3; padding: 10px; border-radius: 5px;}
    .tide-normal {background-color: #e8f5e9; padding: 10px; border-radius: 5px;}
    .footer {text-align: center; color: #666; margin-top: 30px; font-size: 0.8em;}
    .stMetric {background-color: #f8f9fa; padding: 15px; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# Initialize database using st.cache_resource for efficiency
@st.cache_resource
def get_database_instance():
    """Returns a singleton instance of MarineDB."""
    return MarineDB()

# Initialize database
db = get_database_instance()

def create_tide_chart(tide_data):
    """
    Create a tide chart using Plotly.
    
    Args:
        tide_data (list): List of tide data entries
        
    Returns:
        plotly.graph_objects.Figure: Plotly figure object
    """
    if not tide_data:
        return None
    
    # Convert to DataFrame for easier plotting
    df = pd.DataFrame([
        {
            'time': entry['observation_time'],
            'coefficient': entry['coefficient'],
            'tide_type': entry['tide_type']
        }
        for entry in tide_data
    ])
    
    # Create color map for tide types
    color_map = {
        'high': '#1E88E5',
        'low': '#FFC107',
        'normal': '#4CAF50'
    }
    
    # Create the line chart
    fig = px.line(
        df, 
        x='time', 
        y='coefficient',
        title='Tide Levels Throughout the Day',
        markers=True
    )
    
    # Add markers with colors based on tide type
    for tide_type in df['tide_type'].unique():
        subset = df[df['tide_type'] == tide_type]
        fig.add_trace(
            go.Scatter(
                x=subset['time'],
                y=subset['coefficient'],
                mode='markers',
                marker=dict(color=color_map.get(tide_type, '#000000'), size=10),
                name=tide_type.capitalize()
            )
        )
    
    # Customize layout
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title='Water Level (m)',
        legend_title='Tide Type',
        hovermode='x unified',
        height=400,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(tickformat='%H:%M')
    )
    
    return fig

def run_streamlit_app():
    """Main function to run the Streamlit application logic."""
    
    # Main header
    st.markdown("<h1 class='main-header'>🌊 Marine Data Hub</h1>", unsafe_allow_html=True)
    
    # Sidebar - Location Selection
    st.sidebar.header("Select Location")
    
    # Get available countries
    available_countries = db.get_available_countries()
    
    if not available_countries:
        st.error("No data available in the database. Please run the data fetcher first.")
        
        if st.button("Run Data Fetcher"):
            with st.spinner("Fetching marine data... This may take a minute."):
                try:
                    from utils.fetch_data import run_update
                    result = run_update()
                    if result == 0:
                        st.success("Data fetched successfully! Please refresh the page.")
                    else:
                        st.error("Error fetching data. Check the logs for details.")
                except Exception as e:
                    st.error(f"Error running data fetcher: {e}")
        
        # Show instructions
        st.markdown("""
        ### Getting Started
        
        This application displays tide and weather information for coastal locations.
        
        To populate the database:
        1. Run the data fetcher with the button above or
        2. Execute `python -m utils.fetch_data` from the command line
        
        The data fetcher will scrape tide and weather information for predefined locations.
        """)
        
        return
    
    # Country selection
    selected_country = st.sidebar.selectbox(
        "Country", 
        available_countries,
        help="Select a country to view marine data"
    )
    
    # City selection based on selected country
    if selected_country:
        available_cities = db.get_cities_by_country(selected_country)
        
        if not available_cities:
            st.warning(f"No cities found for {selected_country}.")
            return
        
        selected_city = st.sidebar.selectbox(
            "City", 
            available_cities,
            help="Select a city to view detailed marine data"
        )
    else:
        st.info("Please select a country from the sidebar.")
        return
    
    # Display selected location header
    st.markdown(
        f"<h2 class='location-header'>{selected_city}, {selected_country}</h2>",
        unsafe_allow_html=True
    )
    
    # Data sections
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Today's tidal chart
        st.subheader("Today's Tide Chart")
        
        today_data = db.get_today_data(selected_country, selected_city)
        
        if today_data:
            tide_chart = create_tide_chart(today_data)
            if tide_chart:
                st.plotly_chart(tide_chart, use_container_width=True)
            else:
                st.info("Could not create tide chart with the available data.")
        else:
            st.info("No tide data available for today.")
    
    with col2:
        # Latest marine conditions
        st.subheader("Current Marine Conditions")
        
        latest = db.get_latest_observation(selected_country, selected_city)
        
        if latest:
            # Format observation time
            try:
                obs_time = datetime.strptime(str(latest['observation_time']), '%Y-%m-%d %H:%M:%S')
                time_display = obs_time.strftime('%I:%M %p')
                date_display = obs_time.strftime('%A, %B %d, %Y')
            except (ValueError, TypeError):
                time_display = "Unknown"
                date_display = "Unknown"
            
            # Display time
            st.markdown(f"**Last Updated:** {date_display} at {time_display}")
            
            # Create metrics
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.metric(
                    label="Water Level", 
                    value=f"{latest['coefficient']:.2f} m" if latest['coefficient'] else "N/A"
                )
                
                wind_desc = get_wind_description(latest['wind_speed'])
                st.metric(
                    label="Wind", 
                    value=f"{latest['wind_speed']:.1f} km/h" if latest['wind_speed'] else "N/A",
                    delta=wind_desc
                )
            
            with col_b:
                st.metric(
                    label="Tide", 
                    value=latest['tide_type'].capitalize() if latest['tide_type'] else "Normal"
                )
                
                st.metric(
                    label="Weather", 
                    value=latest['weather_condition'] if latest['weather_condition'] else "Unknown"
                )
            
            # Additional information if available
            if latest.get('temperature'):
                st.metric(
                    label="Temperature", 
                    value=f"{latest['temperature']:.1f}°C"
                )
                
            if latest.get('humidity'):
                st.metric(
                    label="Humidity", 
                    value=f"{latest['humidity']:.0f}%"
                )
        else:
            st.info("No current marine conditions available.")
    
    # Detailed tide information
    st.markdown("---")
    st.subheader("Today's Tide Schedule")
    
    if today_data:
        # Convert to DataFrame
        tide_df = pd.DataFrame([
            {
                'Time': datetime.strptime(str(entry['observation_time']), '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p'),
                'Tide Type': entry['tide_type'].capitalize(),
                'Water Level (m)': f"{entry['coefficient']:.2f}" if entry['coefficient'] else "N/A",
                'Weather': entry['weather_condition'],
                'Wind Speed (km/h)': f"{entry['wind_speed']:.1f}" if entry['wind_speed'] else "N/A"
            }
            for entry in today_data
        ])
        
        st.dataframe(tide_df, use_container_width=True, hide_index=True)
    else:
        st.info("No tide schedule available for today.")
    
    # Footer with refresh button
    st.markdown("---")
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    
    with col_mid:
        if st.button("🔄 Refresh Data"):
            with st.spinner("Fetching latest marine data..."):
                try:
                    from utils.fetch_data import run_update
                    result = run_update()
                    if result == 0:
                        st.success("Data refreshed successfully!")
                    else:
                        st.error("Error refreshing data. Check the logs for details.")
                except Exception as e:
                    st.error(f"Error running data fetcher: {e}")
    
    # Version information
    st.markdown(
        "<div class='footer'>Marine Data Hub v1.0.0 | Data updates every 6 hours</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    try:
        run_streamlit_app()
    except Exception as e:
        logger.error(f"Error running Streamlit app: {e}")
        st.error(f"An error occurred: {e}")
EOF

# --- Create api.py ---
log "INFO" "Creating api.py..."
cat << 'EOF' > api.py
"""
RESTful API for marine data access.
Provides endpoints for querying tide and weather information.
"""
import logging
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from project
from utils.database import MarineDB
from utils.fetch_data import MarineDataFetcher
from utils.helpers import setup_logging, validate_country_city
from config.settings import API_HOST, API_PORT, API_DEBUG, LOG_LEVEL, LOG_FILE

# Set up logging
setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Initialize database
db = MarineDB()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API is running."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/api/marine-data/<country>/<city>', methods=['GET'])
def get_marine_data(country, city):
    """
    Get marine data for a specific location.
    
    Args:
        country (str): Country name
        city (str): City name
        
    Returns:
        JSON response with marine data
    """
    # Validate inputs
    valid, error_msg = validate_country_city(country, city)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    # Optional date parameter
    date_str = request.args.get('date')
    
    try:
        if date_str:
            # Validate date format
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                data = db.get_data_for_date_range(country, city, date_str, date_str)
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400
        else:
            # Default to today
            data = db.get_today_data(country, city)
        
        if not data:
            return jsonify({
                'message': f"No data found for {city}, {country} on the specified date."
            }), 404
        
        # Convert SQLite row objects to dictionaries
        serialized_data = []
            item = dict(row)
            # Convert datetime objects to ISO format strings
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.isoformat()
            serialized_data.append(item)
        
        return jsonify(serialized_data), 200
    except Exception as e:
        logger.error(f"Error fetching marine data for {city}, {country}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/latest-marine-data/<country>/<city>', methods=['GET'])
def get_latest_marine_data(country, city):
    """
    Get the latest marine data for a specific location.
    
    Args:
        country (str): Country name
        city (str): City name
        
    Returns:
        JSON response with latest marine data
    """
    # Validate inputs
    valid, error_msg = validate_country_city(country, city)
    if not valid:
        return jsonify({'error': error_msg}), 400
    
    try:
        observation = db.get_latest_observation(country, city)
        
        if not observation:
            return jsonify({
                'message': f"No latest observation found for {city}, {country}."
            }), 404
        
        # Convert SQLite row to dictionary
        result = dict(observation)
        
        # Convert datetime objects to ISO format strings
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error fetching latest marine data for {city}, {country}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/countries', methods=['GET'])
def get_countries():
    """
    Get all available countries.
    
    Returns:
        JSON response with list of countries
    """
    try:
        countries = db.get_available_countries()
        
        if not countries:
            return jsonify({
                'message': "No countries found in the database."
            }), 404
        
        return jsonify(countries), 200
    except Exception as e:
        logger.error(f"Error fetching countries: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/cities/<country>', methods=['GET'])
def get_cities(country):
    """
    Get all available cities for a country.
    
    Args:
        country (str): Country name
        
    Returns:
        JSON response with list of cities
    """
    # Validate input
    if not country or not isinstance(country, str):
        return jsonify({'error': 'Country name is required and must be a string'}), 400
    
    try:
        cities = db.get_cities_by_country(country)
        
        if not cities:
            return jsonify({
                'message': f"No cities found for {country}."
            }), 404
        
        return jsonify(cities), 200
    except Exception as e:
        logger.error(f"Error fetching cities for {country}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/trigger-data-fetch', methods=['POST'])
def api_trigger_data_fetch():
    """
    Trigger a fetch of new marine data for all predefined locations.
    
    Returns:
        JSON response with status of the operation
    """
    # Check for API key in header for security
    api_key = request.headers.get('X-API-Key')
    
    if not api_key or api_key != os.environ.get('API_KEY', 'default_key_change_me'):
        return jsonify({'error': 'Unauthorized. Valid API key required.'}), 401
    
    try:
        # Run data fetcher in a separate process to avoid blocking
        from multiprocessing import Process
        
        def fetch_data():
            fetcher = MarineDataFetcher()
            fetcher.update_all_locations()
        
        process = Process(target=fetch_data)
        process.start()
        
        return jsonify({
            'message': 'Data fetch initiated. This process runs in the background.',
            'status': 'running',
            'process_id': process.pid
        }), 202
    except Exception as e:
        logger.error(f"Error triggering data fetch: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get statistics about the database.
    
    Returns:
        JSON response with database statistics
    """
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get location count
            cursor.execute("SELECT COUNT(*) FROM locations")
            location_count = cursor.fetchone()[0]
            
            # Get observation count
            cursor.execute("SELECT COUNT(*) FROM observations")
            observation_count = cursor.fetchone()[0]
            
            # Get date range
            cursor.execute("""
                SELECT 
                    MIN(date(observation_time)),
                    MAX(date(observation_time))
                FROM observations
            """)
            min_date, max_date = cursor.fetchone()
            
            # Get top locations
            cursor.execute("""
                SELECT l.country, l.city, COUNT(o.id) as obs_count
                FROM locations l
                JOIN observations o ON l.id = o.location_id
                GROUP BY l.id
                ORDER BY obs_count DESC
                LIMIT 5
            """)
            top_locations = [
                {'country': row[0], 'city': row[1], 'observation_count': row[2]}
                for row in cursor.fetchall()
            ]
            
            return jsonify({
                'location_count': location_count,
                'observation_count': observation_count,
                'date_range': {
                    'start': min_date,
                    'end': max_date
                },
                'top_locations': top_locations,
                'generated_at': datetime.now().isoformat()
            }), 200
    except Exception as e:
        logger.error(f"Error fetching database stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def run_api():
    """Run the Flask API server."""
    app.run(
        host=API_HOST,
        port=API_PORT,
        debug=API_DEBUG
    )

if __name__ == "__main__":
    run_api()
EOF

# --- Create tests/test_database.py ---
log "INFO" "Creating tests/test_database.py..."
mkdir -p tests
cat << 'EOF' > tests/test_database.py
"""
Unit tests for the database module.
"""
import unittest
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

from utils.database import MarineDB

class TestMarineDB(unittest.TestCase):
    """Test cases for MarineDB class."""
    
    def setUp(self):
        """Set up test environment with a temporary database."""
        # Create a temporary file for the test database
        self.temp_db_file = tempfile.mktemp(suffix='.db')
        self.db = MarineDB(db_path=self.temp_db_file)
        
        # Insert test data
        self.db.ensure_location_exists(
            country="Test Country",
            city="Test City",
            tide_forecast_slug="test-city",
            weather_com_id="TEST123"
        )
    
    def tearDown(self):
        """Clean up temporary database file."""
        if os.path.exists(self.temp_db_file):
            os.remove(self.temp_db_file)
    
    def test_create_tables(self):
        """Test that tables are created correctly."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if tables exist
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('locations', 'observations', 'data_sources')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            self.assertEqual(len(tables), 3)
            self.assertIn('locations', tables)
            self.assertIn('observations', tables)
            self.assertIn('data_sources', tables)
    
    def test_ensure_location_exists(self):
        """Test that locations are created or updated correctly."""
        # Create a new location
        location_id = self.db.ensure_location_exists(
            country="New Country",
            city="New City",
            tide_forecast_slug="new-city",
            weather_com_id="NEW123"
        )
        
        self.assertIsNotNone(location_id)
        
        # Verify location exists
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM locations WHERE country = ? AND city = ?",
                ("New Country", "New City")
            )
            
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result['tide_forecast_slug'], "new-city")
    
    def test_insert_observation(self):
        """Test that observations are inserted correctly."""
        # Insert an observation
        now = datetime.now()
        
        success = self.db.insert_observation(
            country="Test Country",
            city="Test City",
            obs_time=now,
            tide_type="high",
            coefficient=4.5,
            weather_condition="Sunny",
            wind_speed=10.5
        )
        
        self.assertTrue(success)
        
        # Verify observation exists
        location_id = self.db.get_location_id("Test Country", "Test City")
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM observations WHERE location_id = ?",
                (location_id,)
            )
            
            result = cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result['tide_type'], "high")
            self.assertEqual(result['coefficient'], 4.5)
            self.assertEqual(result['weather_condition'], "Sunny")
            self.assertEqual(result['wind_speed'], 10.5)
    
    def test_get_today_data(self):
        """Test retrieving today's data."""
        # Insert test observations for today
        now = datetime.now()
        
        self.db.insert_observation(
            country="Test Country",
            city="Test City",
            obs_time=now,
            tide_type="high",
            coefficient=4.5,
            weather_condition="Sunny",
            wind_speed=10.5
        )
        
        self.db.insert_observation(
            country="Test Country",
            city="Test City",
            obs_time=now + timedelta(hours=6),
            tide_type="low",
            coefficient=1.5,
            weather_condition="Cloudy",
            wind_speed=5.5
        )
        
        # Get today's data
        results = self.db.get_today_data("Test Country", "Test City")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['tide_type'], "high")
        self.assertEqual(results[1]['tide_type'], "low")
    
    def test_get_latest_observation(self):
        """Test retrieving the latest observation."""
        # Insert test observations with different times
        now = datetime.now()
        
        self.db.insert_observation(
            country="Test Country",
            city="Test City",
            obs_time=now - timedelta(hours=6),
            tide_type="high",
            coefficient=4.5,
            weather_condition="Sunny",
            wind_speed=10.5
        )
        
        self.db.insert_observation(
            country="Test Country",
            city="Test City",
            obs_time=now,  # This should be the latest
            tide_type="low",
            coefficient=1.5,
            weather_condition="Cloudy",
            wind_speed=5.5
        )
        
        # Get the latest observation
        result = self.db.get_latest_observation("Test Country", "Test City")
        
        self.assertIsNotNone(result)
        self.assertEqual(result['tide_type'], "low")
        self.assertEqual(result['coefficient'], 1.5)

if __name__ == '__main__':
    unittest.main()
EOF

# --- Create .env.example file ---
log "INFO" "Creating .env.example file..."
cat << 'EOF' > .env.example
# Environment Configuration Example
# Copy this file to .env and adjust the values as needed

# Database settings
DB_PATH=data/marine_data.db

# API settings
API_HOST=0.0.0.0
API_PORT=5000
API_DEBUG=False
API_KEY=your_secure_api_key_here

# Logging settings
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Web scraping settings
REQUEST_TIMEOUT=30
RETRY_COUNT=3
RETRY_BACKOFF=2

# Update interval in minutes (6 hours)
DATA_UPDATE_INTERVAL=360
EOF

# --- Create README.md ---
log "INFO" "Creating README.md..."
cat << 'EOF' > README.md
# Marine Data Hub

A comprehensive application for collecting, storing, and visualizing marine data including tides and weather conditions for coastal locations.

## Features

- **Data Collection**: Automated scraping of tide and weather data from public sources
- **Data Storage**: Efficient SQLite database with comprehensive schema
- **Web Interface**: Interactive Streamlit dashboard for visualization
- **RESTful API**: Flask-based API for programmatic access to marine data
- **Scheduling**: Automated updates at configurable intervals

## Project Structure

