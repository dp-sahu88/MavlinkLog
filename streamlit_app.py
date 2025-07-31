import streamlit as st
import tempfile
import os
import zipfile
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from core import (
    parse_all_mavlink_messages_to_csv,
    load_csvs_to_temp_db,
    get_all_dynamic_attributes,
    get_chart_data,
    calculate_data_statistics,
    get_database_schema
)

# Page configuration
st.set_page_config(
    page_title="Universal MAVLink Log Visualizer",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

def create_time_series_chart(chart_data, selected_attributes, message_type):
    """Create time series chart with MM:SS formatted time axis."""
    if 'error' in chart_data:
        st.error(f"Error loading data: {chart_data['error']}")
        return None
    
    df = chart_data['data']
    time_col = chart_data['time_column']
    time_formatted_col = chart_data['time_formatted_column']
    
    # Create subplots
    n_attrs = len(selected_attributes)
    fig = make_subplots(
        rows=n_attrs,
        cols=1,
        subplot_titles=selected_attributes,
        shared_xaxes=True,
        vertical_spacing=0.05
    )
    
    # Add traces for each attribute
    for i, attr in enumerate(selected_attributes, 1):
        if attr in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df[time_col],
                    y=df[attr],
                    mode='lines',
                    name=attr,
                    hovertemplate=f'<b>{attr}</b><br>' +
                                f'Time: %{{customdata}}<br>' +
                                f'Value: %{{y:.3f}}<extra></extra>',
                    customdata=df[time_formatted_col],
                    line=dict(width=1.5)
                ),
                row=i, col=1
            )
    
    # Update layout with custom time axis
    if not df.empty:
        # Create custom tick values (every 30 seconds or so)
        time_range = df[time_col].max() - df[time_col].min()
        n_ticks = min(15, len(df) // 50)  # Reasonable number of ticks
        
        if n_ticks > 0:
            tick_indices = np.linspace(0, len(df)-1, n_ticks, dtype=int)
            tick_vals = df[time_col].iloc[tick_indices]
            tick_texts = df[time_formatted_col].iloc[tick_indices]
            
            fig.update_xaxes(
                tickvals=tick_vals,
                ticktext=tick_texts,
                tickangle=45
            )
    
    fig.update_layout(
        title=f"{message_type} - Time Series Analysis",
        height=max(400, n_attrs * 150),
        showlegend=False,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Flight Time (MM:SS)", row=n_attrs, col=1)
    
    return fig

def create_scatter_matrix(chart_data, selected_attributes):
    """Create scatter matrix for correlation analysis."""
    if 'error' in chart_data or len(selected_attributes) < 2:
        return None
    
    df = chart_data['data']
    
    # Select numeric columns only
    numeric_df = df[selected_attributes].select_dtypes(include=[np.number])
    
    if numeric_df.empty or len(numeric_df.columns) < 2:
        return None
    
    fig = px.scatter_matrix(
        numeric_df,
        title="Parameter Correlation Matrix",
        height=600
    )
    
    fig.update_traces(diagonal_visible=False, showupperhalf=False)
    fig.update_layout(title_x=0.5)
    
    return fig

def create_3d_trajectory(chart_data):
    """Create 3D trajectory plot if GPS data is available."""
    if 'error' in chart_data:
        return None
    
    df = chart_data['data']
    
    # Look for GPS coordinates
    lat_cols = [col for col in df.columns if 'lat' in col.lower()]
    lon_cols = [col for col in df.columns if any(x in col.lower() for x in ['lng', 'lon'])]
    alt_cols = [col for col in df.columns if 'alt' in col.lower()]
    
    if not (lat_cols and lon_cols):
        return None
    
    lat_col = lat_cols[0]
    lon_col = lon_cols[0]
    alt_col = alt_cols[0] if alt_cols else None
    
    # Check if we have valid GPS data
    if df[lat_col].isna().all() or df[lon_col].isna().all():
        return None
    
    if alt_col and not df[alt_col].isna().all():
        fig = px.line_3d(
            df,
            x=lon_col,
            y=lat_col,
            z=alt_col,
            title="3D Flight Trajectory",
            labels={
                lon_col: "Longitude",
                lat_col: "Latitude", 
                alt_col: "Altitude (m)"
            }
        )
        
        # Add start and end markers
        fig.add_scatter3d(
            x=[df[lon_col].iloc[0]],
            y=[df[lat_col].iloc[0]],
            z=[df[alt_col].iloc[0]] if alt_col else [0],
            mode='markers',
            marker=dict(size=10, color='green'),
            name='Start',
            showlegend=True
        )
        
        fig.add_scatter3d(
            x=[df[lon_col].iloc[-1]],
            y=[df[lat_col].iloc[-1]],
            z=[df[alt_col].iloc[-1]] if alt_col else [0],
            mode='markers',
            marker=dict(size=10, color='red'),
            name='End',
            showlegend=True
        )
    else:
        # 2D trajectory
        fig = px.line(
            df,
            x=lon_col,
            y=lat_col,
            title="Flight Path (2D)",
            labels={lon_col: "Longitude", lat_col: "Latitude"}
        )
        
        # Add markers
        fig.add_scatter(
            x=[df[lon_col].iloc[0]],
            y=[df[lat_col].iloc[0]],
            mode='markers',
            marker=dict(size=10, color='green'),
            name='Start'
        )
        
        fig.add_scatter(
            x=[df[lon_col].iloc[-1]],
            y=[df[lat_col].iloc[-1]],
            mode='markers',
            marker=dict(size=10, color='red'),
            name='End'
        )
    
    fig.update_layout(height=600)
    return fig

def create_distribution_plots(chart_data, selected_attributes):
    """Create distribution plots for selected attributes."""
    if 'error' in chart_data:
        return None
    
    df = chart_data['data']
    
    # Filter numeric columns
    numeric_attrs = [attr for attr in selected_attributes if attr in df.columns and df[attr].dtype in ['int64', 'float64']]
    
    if not numeric_attrs:
        return None
    
    n_attrs = len(numeric_attrs)
    fig = make_subplots(
        rows=(n_attrs + 1) // 2,
        cols=2,
        subplot_titles=numeric_attrs
    )
    
    for i, attr in enumerate(numeric_attrs):
        row = (i // 2) + 1
        col = (i % 2) + 1
        
        fig.add_trace(
            go.Histogram(
                x=df[attr],
                name=attr,
                showlegend=False,
                nbinsx=30
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        title="Parameter Distributions",
        height=max(400, ((n_attrs + 1) // 2) * 250)
    )
    
    return fig

def export_selected_data(conn, selected_tables):
    """Export selected tables as CSV files in a ZIP archive."""
    if not selected_tables:
        return None
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for table_name in selected_tables:
            try:
                # Query table data
                df = pd.read_sql_query(f"SELECT * FROM [{table_name}]", conn)
                
                # Convert to CSV string
                csv_string = df.to_csv(index=False)
                
                # Add to ZIP
                zip_file.writestr(f"{table_name}.csv", csv_string)
                
            except Exception as e:
                st.error(f"Error exporting {table_name}: {e}")
    
    zip_buffer.seek(0)
    return zip_buffer

# Main application
def main():
    st.title("🚁 Universal MAVLink Log Visualizer")
    st.markdown("**Upload any MAVLink log and visualize all dynamic parameters with MM:SS time display**")
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'dynamic_attrs' not in st.session_state:
        st.session_state.dynamic_attrs = None
    
    # Sidebar for file upload and processing
    with st.sidebar:
        st.header("📁 Log File Upload")
        
        uploaded_file = st.file_uploader(
            "Choose MAVLink log file",
            type=['tlog', 'bin', 'log'],
            help="Upload .tlog, .bin, or .log files"
        )
        
        if uploaded_file is not None:
            if st.button("🔄 Process Log File", type="primary"):
                with st.spinner("Processing MAVLink log..."):
                    try:
                        # Save uploaded file temporarily
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        # Create temporary directory for CSVs
                        with tempfile.TemporaryDirectory() as temp_dir:
                            # Parse MAVLink messages
                            csv_files = parse_all_mavlink_messages_to_csv(tmp_file_path, temp_dir)
                            
                            if not csv_files:
                                st.error("No valid messages found in log file")
                                return
                            
                            # Load to database
                            conn = load_csvs_to_temp_db(csv_files)
                            
                            # Get dynamic attributes
                            dynamic_attrs = get_all_dynamic_attributes(conn)
                            
                            if not dynamic_attrs:
                                st.error("No dynamic attributes found for visualization")
                                return
                            
                            # Store in session state
                            st.session_state.processed_data = conn
                            st.session_state.dynamic_attrs = dynamic_attrs
                            
                            st.success(f"✅ Processed {len(csv_files)} message types")
                            
                        # Clean up temp file
                        os.unlink(tmp_file_path)
                        
                    except Exception as e:
                        st.error(f"Error processing file: {e}")
    
    # Main content area
    if st.session_state.processed_data is not None and st.session_state.dynamic_attrs is not None:
        conn = st.session_state.processed_data
        dynamic_attrs = st.session_state.dynamic_attrs
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📊 Visualization", "📈 Data Export", "ℹ️ Log Info"])
        
        with tab1:
            st.header("Dynamic Parameter Visualization")
            
            # Sidebar controls for visualization
            with st.sidebar:
                st.header("📊 Visualization Controls")
                
                # Message type selection
                message_types = list(dynamic_attrs.keys())
                selected_message = st.selectbox(
                    "Select Message Type:",
                    options=message_types,
                    format_func=lambda x: f"{x} ({dynamic_attrs[x]['row_count']} records)"
                )
                
                if selected_message:
                    msg_attrs = dynamic_attrs[selected_message]
                    
                    # Attribute selection with search
                    search_attr = st.text_input("🔍 Filter attributes:")
                    available_attrs = msg_attrs['attributes']
                    
                    if search_attr:
                        filtered_attrs = [attr for attr in available_attrs if search_attr.lower() in attr.lower()]
                    else:
                        filtered_attrs = available_attrs
                    
                    selected_attributes = st.multiselect(
                        "Select Attributes to Plot:",
                        options=filtered_attrs,
                        default=filtered_attrs[:min(3, len(filtered_attrs))],
                        help="Choose parameters to visualize"
                    )
                    
                    # Performance controls
                    st.subheader("⚡ Performance")
                    max_records = st.slider(
                        "Max records to plot:",
                        min_value=100,
                        max_value=20000,
                        value=5000,
                        step=500,
                        help="Limit records for better performance"
                    )
                    
                    # Chart type selection
                    st.subheader("📈 Chart Types")
                    show_timeseries = st.checkbox("Time Series", value=True)
                    show_scatter = st.checkbox("Scatter Matrix", value=False)
                    show_trajectory = st.checkbox("3D Trajectory", value=False)
                    show_distribution = st.checkbox("Distributions", value=False)
            
            # Generate visualizations
            if selected_message and selected_attributes:
                # Get chart data
                chart_data = get_chart_data(conn, selected_message, selected_attributes, max_records)
                
                if 'error' not in chart_data:
                    # Display parameter info
                    st.subheader(f"📋 {selected_message} Parameters")
                    
                    param_info = []
                    for attr in selected_attributes:
                        unit = msg_attrs['units'].get(attr, '')
                        desc = msg_attrs['descriptions'].get(attr, attr)
                        param_info.append({
                            'Parameter': attr,
                            'Description': desc,
                            'Unit': unit
                        })
                    
                    st.dataframe(pd.DataFrame(param_info), use_container_width=True)
                    
                    # Time Series Chart
                    if show_timeseries:
                        st.subheader("📈 Time Series Analysis")
                        fig_ts = create_time_series_chart(chart_data, selected_attributes, selected_message)
                        if fig_ts:
                            st.plotly_chart(fig_ts, use_container_width=True)
                    
                    # Scatter Matrix
                    if show_scatter and len(selected_attributes) >= 2:
                        st.subheader("🔗 Parameter Correlations")
                        fig_scatter = create_scatter_matrix(chart_data, selected_attributes)
                        if fig_scatter:
                            st.plotly_chart(fig_scatter, use_container_width=True)
                    
                    # 3D Trajectory
                    if show_trajectory:
                        st.subheader("🗺️ Flight Trajectory")
                        fig_3d = create_3d_trajectory(chart_data)
                        if fig_3d:
                            st.plotly_chart(fig_3d, use_container_width=True)
                        else:
                            st.info("No GPS coordinates found for trajectory visualization")
                    
                    # Distribution plots
                    if show_distribution:
                        st.subheader("📊 Parameter Distributions")
                        fig_dist = create_distribution_plots(chart_data, selected_attributes)
                        if fig_dist:
                            st.plotly_chart(fig_dist, use_container_width=True)
                    
                    # Statistics
                    st.subheader("📈 Statistical Summary")
                    stats = calculate_data_statistics(conn, selected_message, selected_attributes)
                    if 'error' not in stats:
                        stats_df = pd.DataFrame(stats).T
                        st.dataframe(stats_df.round(3), use_container_width=True)
                
                else:
                    st.error(f"Error loading data: {chart_data['error']}")
        
        with tab2:
            st.header("📤 Data Export")
            
            # Show available tables
            schema = get_database_schema(conn)
            
            st.subheader("Available Message Types")
            export_options = []
            for table, info in schema.items():
                export_options.append({
                    'Message Type': table,
                    'Records': info['row_count'],
                    'Columns': len(info['columns'])
                })
            
            export_df = pd.DataFrame(export_options)
            st.dataframe(export_df, use_container_width=True)
            
            # Export selection
            selected_for_export = st.multiselect(
                "Select message types to export:",
                options=list(schema.keys()),
                default=[],
                help="Choose message types to include in export"
            )
            
            if selected_for_export:
                if st.button("📦 Create Export Package"):
                    with st.spinner("Creating export package..."):
                        zip_data = export_selected_data(conn, selected_for_export)
                        
                        if zip_data:
                            st.download_button(
                                label="⬇️ Download CSV Package",
                                data=zip_data,
                                file_name=f"mavlink_export_{uploaded_file.name.split('.')[0]}.zip",
                                mime="application/zip"
                            )
                            st.success("✅ Export package ready!")
        
        with tab3:
            st.header("ℹ️ Log Information")
            
            # Display schema information
            schema = get_database_schema(conn)
            
            st.subheader("📋 Message Types Summary")
            summary_data = []
            total_records = 0
            
            for table, info in schema.items():
                summary_data.append({
                    'Message Type': table,
                    'Records': info['row_count'],
                    'Columns': len(info['columns']),
                    'Dynamic Attributes': len(dynamic_attrs.get(table, {}).get('attributes', []))
                })
                total_records += info['row_count']
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # Overall statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Message Types", len(schema))
            with col2:
                st.metric("Total Records", f"{total_records:,}")
            with col3:
                st.metric("Plottable Types", len(dynamic_attrs))
            with col4:
                total_attrs = sum(len(attrs['attributes']) for attrs in dynamic_attrs.values())
                st.metric("Dynamic Parameters", total_attrs)
            
            # Detailed table information
            st.subheader("📊 Detailed Table Information")
            selected_table = st.selectbox("Select table for details:", options=list(schema.keys()))
            
            if selected_table:
                table_info = schema[selected_table]
                
                st.write(f"**{selected_table}** - {table_info['row_count']} records")
                
                # Show columns
                col_df = pd.DataFrame({
                    'Column': table_info['columns'],
                    'Type': [table_info['column_types'].get(col, 'Unknown') for col in table_info['columns']]
                })
                
                # Mark dynamic attributes
                if selected_table in dynamic_attrs:
                    dynamic_cols = dynamic_attrs[selected_table]['attributes']
                    col_df['Dynamic'] = col_df['Column'].isin(dynamic_cols)
                else:
                    col_df['Dynamic'] = False
                
                st.dataframe(col_df, use_container_width=True)
    
    else:
        # Welcome screen
        st.info("👆 Upload a MAVLink log file using the sidebar to get started")
        
        st.markdown("""
        ### Features:
        - **Universal Compatibility**: Works with any MAVLink log format (.tlog, .bin, .log)
        - **Automatic Detection**: Finds all message types and numeric parameters automatically
        - **Time Formatting**: Displays flight time in easy-to-read MM:SS format
        - **Multiple Visualizations**: Time series, correlations, 3D trajectories, distributions
        - **Data Export**: Export processed data as CSV files
        - **Performance Optimized**: Handles large log files efficiently
        
        ### Supported Message Types:
        Works with **all** MAVLink message types including:
        - Attitude data (ATT, ATTITUDE)
        - GPS position (GPS, POS, GLOBAL_POSITION_INT)
        - Control data (CTUN, NTUN)
        - IMU data (IMU, RATE)
        - Battery status (BAT, BATTERY_STATUS)
        - And many more...
        """)

if __name__ == "__main__":
    main()