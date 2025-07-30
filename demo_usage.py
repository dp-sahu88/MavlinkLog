#!/usr/bin/env python3
"""
Demo script showing how to use the enhanced MAVLink core functions independently.
This is useful for batch processing or integration into other applications.
"""

import os
import tempfile
from core import (
    parse_all_mavlink_messages_to_csv,
    load_csvs_to_temp_db,
    get_all_dynamic_attributes,
    get_chart_data,
    calculate_data_statistics,
    get_database_schema
)

def demo_mavlink_processing(log_file_path):
    """
    Demonstrate the complete MAVLink processing pipeline.
    
    Args:
        log_file_path (str): Path to MAVLink log file (.tlog, .bin, .log)
    """
    
    print(f"🚁 Processing MAVLink log: {log_file_path}")
    print("="*60)
    
    # Step 1: Parse MAVLink messages to CSV files
    print("📝 Step 1: Parsing MAVLink messages...")
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            csv_files = parse_all_mavlink_messages_to_csv(log_file_path, temp_dir)
            print(f"   ✅ Created {len(csv_files)} CSV files")
            
            # Step 2: Load CSVs into SQLite database
            print("🗄️  Step 2: Loading data into database...")
            conn = load_csvs_to_temp_db(csv_files)
            print("   ✅ Database loaded successfully")
            
            # Step 3: Get database schema
            print("📊 Step 3: Analyzing database schema...")
            schema = get_database_schema(conn)
            print(f"   ✅ Found {len(schema)} message types")
            
            # Display schema summary
            print("\n📋 Message Types Summary:")
            print(f"{'Message Type':<20} {'Records':<10} {'Columns':<10}")
            print("-" * 42)
            total_records = 0
            for table_name, info in schema.items():
                print(f"{table_name:<20} {info['row_count']:<10} {len(info['columns']):<10}")
                total_records += info['row_count']
            print(f"\n   Total Records: {total_records:,}")
            
            # Step 4: Detect dynamic attributes
            print("\n🎯 Step 4: Detecting dynamic attributes...")
            dynamic_attrs = get_all_dynamic_attributes(conn)
            print(f"   ✅ Found {len(dynamic_attrs)} message types with dynamic attributes")
            
            # Display dynamic attributes
            print("\n📈 Dynamic Attributes by Message Type:")
            for msg_type, attrs in dynamic_attrs.items():
                print(f"\n{msg_type} ({attrs['row_count']} records):")
                print(f"  Time Column: {attrs['time_col']}")
                print(f"  Attributes: {', '.join(attrs['attributes'][:5])}")
                if len(attrs['attributes']) > 5:
                    print(f"              ... and {len(attrs['attributes']) - 5} more")
            
            # Step 5: Demonstrate data retrieval
            print("\n📊 Step 5: Sample data analysis...")
            if dynamic_attrs:
                # Pick first message type with dynamic attributes
                sample_msg_type = list(dynamic_attrs.keys())[0]
                sample_attrs = dynamic_attrs[sample_msg_type]['attributes'][:3]  # First 3 attributes
                
                print(f"   Analyzing {sample_msg_type} with attributes: {sample_attrs}")
                
                # Get chart data
                chart_data = get_chart_data(conn, sample_msg_type, sample_attrs, limit=1000)
                
                if 'error' not in chart_data:
                    df = chart_data['data']
                    print(f"   ✅ Retrieved {len(df)} data points")
                    
                    # Calculate statistics
                    stats = calculate_data_statistics(conn, sample_msg_type, sample_attrs)
                    
                    if 'error' not in stats:
                        print(f"\n📈 Statistical Summary for {sample_msg_type}:")
                        print(f"{'Parameter':<15} {'Mean':<10} {'Std':<10} {'Min':<10} {'Max':<10}")
                        print("-" * 60)
                        
                        for attr, stat in stats.items():
                            print(f"{attr:<15} {stat['mean']:<10.3f} {stat['std']:<10.3f} "
                                  f"{stat['min']:<10.3f} {stat['max']:<10.3f}")
                else:
                    print(f"   ❌ Error retrieving data: {chart_data['error']}")
            
            # Step 6: Demonstrate time formatting
            print("\n⏰ Step 6: Time formatting example...")
            if dynamic_attrs:
                sample_msg_type = list(dynamic_attrs.keys())[0]
                time_col = dynamic_attrs[sample_msg_type]['time_col']
                
                # Get a small sample of time data
                import pandas as pd
                query = f"SELECT [{time_col}] FROM [{sample_msg_type}] LIMIT 5"
                time_df = pd.read_sql_query(query, conn)
                
                if 'timeus' in time_col.lower():
                    from core import convert_timeus_to_datetime_and_format
                    datetime_series, formatted_series = convert_timeus_to_datetime_and_format(time_df[time_col])
                    
                    print(f"   Time Column: {time_col}")
                    print("   Raw TimeUS -> Formatted Time:")
                    for i in range(min(5, len(time_df))):
                        raw_time = time_df[time_col].iloc[i]
                        formatted_time = formatted_series.iloc[i]
                        print(f"   {raw_time:>12} -> {formatted_time}")
            
            print("\n🎉 Processing completed successfully!")
            print("💡 Use enhanced_streamlit_app.py for interactive visualization")
            
        except Exception as e:
            print(f"❌ Error during processing: {e}")
            raise

def main():
    """
    Main function - you can modify this to process your specific log files.
    """
    
    # Example usage - replace with your actual log file path
    log_file_path = "your_log_file.bin"  # Change this to your log file
    
    if not os.path.exists(log_file_path):
        print("📝 Demo Instructions:")
        print("="*50) 
        print("1. Replace 'your_log_file.bin' with your actual log file path")
        print("2. Supported formats: .tlog, .bin, .log")
        print("3. Run: python demo_usage.py")
        print("\nExample:")
        print("   log_file_path = '/path/to/your/flight_log.bin'")
        print("\n🚁 For interactive visualization, use:")
        print("   streamlit run enhanced_streamlit_app.py")
        return
    
    try:
        demo_mavlink_processing(log_file_path)
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("- Ensure the log file exists and is a valid MAVLink format")
        print("- Check that all dependencies are installed: pip install -r requirements.txt")
        print("- Verify Python version is 3.7 or higher")

if __name__ == "__main__":
    main()