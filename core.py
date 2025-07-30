import os
import tempfile
import sqlite3
import pandas as pd
import numpy as np
from pymavlink import mavutil
from typing import Dict, List, Tuple, Optional, Any
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_all_mavlink_messages_to_csv(log_file_path: str, output_dir: str) -> Dict[str, str]:
    """
    Parse MAVLink log file and save each message type to separate CSV files.
    Returns dictionary mapping message types to their CSV file paths.
    """
    try:
        # Connect to MAVLink log
        mlog = mavutil.mavlink_connection(log_file_path)
        
        message_writers = {}
        message_files = {}
        
        logger.info(f"Parsing MAVLink log: {log_file_path}")
        
        while True:
            msg = mlog.recv_match(blocking=False)
            if msg is None:
                break
                
            msg_type = msg.get_type()
            
            # Skip invalid message types
            if msg_type in ['BAD_DATA', 'UNKNOWN']:
                continue
                
            # Initialize CSV writer for new message type
            if msg_type not in message_writers:
                csv_path = os.path.join(output_dir, f"{msg_type}.csv")
                
                # Get message fields
                if hasattr(msg, '_fieldnames'):
                    fieldnames = msg._fieldnames
                else:
                    # Fallback: extract from message dict
                    fieldnames = list(msg.to_dict().keys())
                
                # Create CSV file
                df_empty = pd.DataFrame(columns=fieldnames)
                df_empty.to_csv(csv_path, index=False)
                
                message_writers[msg_type] = csv_path
                message_files[msg_type] = []
                
                logger.info(f"Created CSV for message type: {msg_type}")
            
            # Convert message to dictionary
            try:
                msg_dict = msg.to_dict()
                message_files[msg_type].append(msg_dict)
            except Exception as e:
                logger.warning(f"Failed to convert message {msg_type}: {e}")
                continue
                
        # Write accumulated messages to CSV files
        for msg_type, records in message_files.items():
            if records:
                csv_path = message_writers[msg_type]
                df = pd.DataFrame(records)
                df.to_csv(csv_path, index=False)
                logger.info(f"Wrote {len(records)} records to {msg_type}.csv")
        
        return message_writers
        
    except Exception as e:
        logger.error(f"Error parsing MAVLink log: {e}")
        raise

def load_csvs_to_temp_db(csv_files: Dict[str, str]) -> sqlite3.Connection:
    """
    Load CSV files into a temporary SQLite database.
    Returns the database connection.
    """
    try:
        # Create in-memory database
        conn = sqlite3.connect(':memory:')
        
        for msg_type, csv_path in csv_files.items():
            if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
                try:
                    # Read CSV with error handling
                    df = pd.read_csv(csv_path, low_memory=False)
                    
                    if not df.empty:
                        # Clean table name for SQLite
                        table_name = msg_type.replace('-', '_').replace(' ', '_')
                        
                        # Write to SQLite
                        df.to_sql(table_name, conn, if_exists='replace', index=False)
                        logger.info(f"Loaded {len(df)} records into table: {table_name}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load {msg_type}: {e}")
                    continue
        
        return conn
        
    except Exception as e:
        logger.error(f"Error loading CSVs to database: {e}")
        raise

def get_database_schema(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """
    Get complete database schema with table info and column details.
    """
    schema = {}
    
    try:
        # Get all tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            # Get table info
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            row_count = cursor.fetchone()[0]
            
            # Get column info
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = cursor.fetchall()
            
            schema[table_name] = {
                'row_count': row_count,
                'columns': [col[1] for col in columns],  # column names
                'column_types': {col[1]: col[2] for col in columns}  # name: type mapping
            }
    
    except Exception as e:
        logger.error(f"Error getting database schema: {e}")
    
    return schema

def detect_numeric_columns(conn: sqlite3.Connection, table_name: str, 
                          sample_size: int = 100) -> List[str]:
    """
    Detect which columns in a table contain numeric data suitable for plotting.
    """
    numeric_columns = []
    
    try:
        cursor = conn.cursor()
        
        # Get sample data
        cursor.execute(f"SELECT * FROM [{table_name}] LIMIT {sample_size}")
        rows = cursor.fetchall()
        
        if not rows:
            return numeric_columns
        
        # Get column names
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Analyze each column
        for i, col_name in enumerate(columns):
            values = [row[i] for row in rows if row[i] is not None]
            
            if len(values) < 5:  # Need minimum values
                continue
                
            # Try to convert to numeric
            numeric_values = []
            for val in values:
                try:
                    if isinstance(val, (int, float)):
                        numeric_values.append(float(val))
                    elif isinstance(val, str):
                        # Try to parse as number
                        parsed = float(val)
                        numeric_values.append(parsed)
                except (ValueError, TypeError):
                    continue
            
            # Check if column is mostly numeric and has variance
            if len(numeric_values) >= len(values) * 0.8:  # 80% numeric
                if len(set(numeric_values)) > 1:  # Has variance
                    variance = np.var(numeric_values)
                    if variance > 0:  # Not all the same value
                        numeric_columns.append(col_name)
    
    except Exception as e:
        logger.warning(f"Error detecting numeric columns for {table_name}: {e}")
    
    return numeric_columns

def infer_units_and_descriptions(column_name: str) -> Tuple[str, str]:
    """
    Infer units and descriptions for common MAVLink parameters.
    """
    col_lower = column_name.lower()
    
    # Common patterns and their units/descriptions
    patterns = {
        # Attitude
        'roll': ('degrees', 'Roll angle'),
        'pitch': ('degrees', 'Pitch angle'), 
        'yaw': ('degrees', 'Yaw angle'),
        'rollspeed': ('deg/s', 'Roll angular velocity'),
        'pitchspeed': ('deg/s', 'Pitch angular velocity'),
        'yawspeed': ('deg/s', 'Yaw angular velocity'),
        
        # Position
        'lat': ('degrees', 'Latitude'),
        'lng': ('degrees', 'Longitude'),
        'lon': ('degrees', 'Longitude'),
        'alt': ('meters', 'Altitude'),
        'relalt': ('meters', 'Relative altitude'),
        
        # Velocity
        'vx': ('m/s', 'Velocity X'),
        'vy': ('m/s', 'Velocity Y'),
        'vz': ('m/s', 'Velocity Z'),
        'vel': ('m/s', 'Velocity'),
        'speed': ('m/s', 'Speed'),
        'groundspeed': ('m/s', 'Ground speed'),
        'airspeed': ('m/s', 'Air speed'),
        
        # Acceleration
        'accx': ('m/s²', 'Acceleration X'),
        'accy': ('m/s²', 'Acceleration Y'),
        'accz': ('m/s²', 'Acceleration Z'),
        'acc': ('m/s²', 'Acceleration'),
        
        # Angular rates
        'gyrx': ('deg/s', 'Angular rate X'),
        'gyry': ('deg/s', 'Angular rate Y'),
        'gyrz': ('deg/s', 'Angular rate Z'),
        'p': ('deg/s', 'Roll rate'),
        'q': ('deg/s', 'Pitch rate'),
        'r': ('deg/s', 'Yaw rate'),
        
        # Power
        'volt': ('V', 'Voltage'),
        'curr': ('A', 'Current'),
        'bat': ('V', 'Battery voltage'),
        'power': ('W', 'Power'),
        
        # Pressure/Altitude
        'press': ('Pa', 'Pressure'),
        'baro': ('m', 'Barometric altitude'),
        'temp': ('°C', 'Temperature'),
        
        # Control
        'thr': ('%', 'Throttle'),
        'throttle': ('%', 'Throttle'),
        'rud': ('%', 'Rudder'),
        'ele': ('%', 'Elevator'),
        'ail': ('%', 'Aileron'),
        
        # Time
        'timeus': ('μs', 'Time (microseconds)'),
        'timestamp': ('s', 'Timestamp'),
        'time': ('s', 'Time'),
    }
    
    # Check for pattern matches
    for pattern, (unit, desc) in patterns.items():
        if pattern in col_lower:
            return unit, desc
    
    # Default fallback
    return '', column_name.replace('_', ' ').title()

def get_time_column(conn: sqlite3.Connection, table_name: str) -> Optional[str]:
    """
    Find the time column in a table (TimeUS, timestamp, etc.).
    """
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Common time column names (prioritized)
        time_patterns = ['TimeUS', 'timestamp', 'time_boot_ms', 'time', 'Time']
        
        for pattern in time_patterns:
            for col in columns:
                if pattern.lower() in col.lower():
                    return col
        
        return None
        
    except Exception as e:
        logger.warning(f"Error finding time column for {table_name}: {e}")
        return None

def get_all_dynamic_attributes(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """
    Get all dynamic attributes from all tables in the database.
    This replaces the hardcoded approach with universal detection.
    """
    dynamic_attrs = {}
    schema = get_database_schema(conn)
    
    for table_name, table_info in schema.items():
        if table_info['row_count'] == 0:
            continue
            
        # Find time column
        time_col = get_time_column(conn, table_name)
        if not time_col:
            continue
            
        # Detect numeric columns
        numeric_cols = detect_numeric_columns(conn, table_name)
        if not numeric_cols:
            continue
            
        # Remove time column from attributes
        attributes = [col for col in numeric_cols if col != time_col]
        if not attributes:
            continue
            
        # Get units and descriptions
        units = {}
        descriptions = {}
        for attr in attributes:
            unit, desc = infer_units_and_descriptions(attr)
            units[attr] = unit
            descriptions[attr] = desc
        
        dynamic_attrs[table_name] = {
            'time_col': time_col,
            'attributes': attributes,
            'units': units,
            'descriptions': descriptions,
            'row_count': table_info['row_count']
        }
        
        logger.info(f"Found {len(attributes)} dynamic attributes in {table_name}")
    
    return dynamic_attrs

def convert_timeus_to_datetime_and_format(timeus_values: pd.Series) -> Tuple[pd.Series, pd.Series]:
    """
    Convert TimeUS (microseconds) to datetime objects and MM:SS formatted strings.
    Returns (datetime_series, formatted_string_series).
    """
    # Convert microseconds to seconds
    seconds = timeus_values / 1_000_000
    
    # Create datetime objects (using epoch as reference)
    datetime_series = pd.to_datetime(seconds, unit='s')
    
    # Create MM:SS formatted strings
    def format_time(sec):
        minutes = int(sec // 60)
        seconds_remainder = int(sec % 60)
        return f"{minutes}:{seconds_remainder:02d}"
    
    formatted_series = seconds.apply(format_time)
    
    return datetime_series, formatted_series

def get_chart_data(conn: sqlite3.Connection, message_type: str, 
                   attributes: List[str], limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Get data for chart visualization with proper time formatting.
    """
    try:
        # Get time column
        time_col = get_time_column(conn, message_type)
        if not time_col:
            raise ValueError(f"No time column found for {message_type}")
        
        # Build query
        columns = [time_col] + attributes
        column_str = ', '.join([f'[{col}]' for col in columns])
        
        query = f"SELECT {column_str} FROM [{message_type}]"
        if limit:
            query += f" LIMIT {limit}"
        
        # Execute query
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            return {'error': 'No data found'}
        
        # Convert time column
        if 'timeus' in time_col.lower():
            datetime_col, formatted_col = convert_timeus_to_datetime_and_format(df[time_col])
            df['datetime'] = datetime_col
            df['time_formatted'] = formatted_col
            time_column = 'datetime'
        else:
            # Handle other time formats
            df['datetime'] = pd.to_datetime(df[time_col], errors='coerce')
            df['time_formatted'] = df[time_col].astype(str)
            time_column = 'datetime'
        
        return {
            'data': df,
            'time_column': time_column,
            'time_formatted_column': 'time_formatted',
            'attributes': attributes,
            'message_type': message_type
        }
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        return {'error': str(e)}

def calculate_data_statistics(conn: sqlite3.Connection, message_type: str, 
                            attributes: List[str]) -> Dict[str, Any]:
    """
    Calculate basic statistics for the selected attributes.
    """
    try:
        column_str = ', '.join([f'[{attr}]' for attr in attributes])
        query = f"SELECT {column_str} FROM [{message_type}]"
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            return {'error': 'No data found'}
        
        stats = {}
        for attr in attributes:
            if attr in df.columns:
                stats[attr] = {
                    'mean': float(df[attr].mean()),
                    'std': float(df[attr].std()),
                    'min': float(df[attr].min()),
                    'max': float(df[attr].max()),
                    'count': int(df[attr].count())
                }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return {'error': str(e)}