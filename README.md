# Universal MAVLink Log Visualizer

A comprehensive solution for visualizing **any** MAVLink log file with automatic parameter detection and user-friendly time formatting (MM:SS).

## 🚀 Features

### Universal Compatibility
- **No Hardcoded Message Types**: Automatically detects and processes ALL message types in your log
- **Smart Parameter Detection**: Uses statistical analysis to identify numeric, time-varying parameters  
- **Works with Any Log Format**: Supports `.tlog`, `.bin`, and `.log` files
- **Intelligent Unit Inference**: Automatically infers units and descriptions for common parameters

### Advanced Visualizations
- **Time Series Analysis**: Multi-panel charts with MM:SS formatted time axes
- **Scatter Matrix**: Correlation analysis between different parameters
- **3D Flight Trajectories**: GPS-based flight path visualization with altitude coloring
- **Distribution Plots**: Statistical analysis and histograms
- **Real-time Statistics**: Data quality metrics and parameter summaries

### User-Friendly Interface
- **Professional Dashboard**: Clean, tabbed interface with sidebar controls
- **Performance Optimizations**: Adjustable record limits for responsive visualization
- **Search & Filter**: Find parameters quickly with search functionality
- **Data Export**: Export processed data as CSV files in ZIP packages

## 🛠️ Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Quick Setup
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application
streamlit run enhanced_streamlit_app.py
```

### Alternative Installation
```bash
# Install packages individually if needed
pip install streamlit pandas numpy plotly pymavlink
```

## 📁 File Structure

```
mavlink-visualizer/
├── enhanced_generic_core.py      # Universal MAVLink processing engine
├── enhanced_streamlit_app.py     # Main Streamlit application
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚁 Usage

### Step 1: Start the Application
```bash
streamlit run enhanced_streamlit_app.py
```

### Step 2: Upload Your Log
- Click "Choose MAVLink log file" in the sidebar
- Select your `.tlog`, `.bin`, or `.log` file
- Click "Process Log File"

### Step 3: Visualize Data
- **Select Message Type**: Choose from automatically detected message types (ATT, POS, GPS, etc.)
- **Pick Parameters**: Select which numeric parameters to visualize
- **Choose Chart Types**: Enable time series, correlations, trajectories, or distributions
- **Adjust Performance**: Set record limits for optimal performance

### Step 4: Export Data (Optional)
- Switch to the "Data Export" tab
- Select message types to export
- Download as ZIP file containing CSV files

## 🔧 Technical Details

### Message Type Support
The visualizer automatically handles **all** MAVLink message types including:

**Common ArduPilot Messages:**
- `ATT` - Attitude data (roll, pitch, yaw)
- `POS` - Position data (lat, lon, alt)  
- `GPS` - GPS information
- `IMU` - Inertial measurement data
- `BAT` - Battery status
- `CTUN` - Control tuning
- `NTUN` - Navigation tuning
- `RCIN`/`RCOU` - RC input/output
- And 50+ more message types

### Time Format Conversion
The application converts raw `TimeUS` (microseconds) to readable formats:
- **Raw**: `254980762` microseconds
- **Converted**: `4:15` (4 minutes, 15 seconds)
- **Chart Display**: Custom tick labels showing MM:SS format

### Automatic Parameter Detection
The system uses intelligent algorithms to identify plottable parameters:
1. **Numeric Detection**: Scans data to find columns with ≥80% numeric values
2. **Variance Analysis**: Ensures parameters change over time (not constant)
3. **Unit Inference**: Maps parameter names to appropriate units (degrees, m/s, etc.)

## 🎯 Solving Common Issues

### "No suitable dynamic attributes found"
**Problem**: Your original code only looked for hardcoded message types like `ATTITUDE`, `GPS_RAW_INT`

**Solution**: This enhanced version automatically detects **any** message type in your log, including:
- `ATT` instead of `ATTITUDE`
- `POS` instead of `GLOBAL_POSITION_INT`  
- `GPS` instead of `GPS_RAW_INT`

### Large Log Files
**Performance Tips**:
- Use the "Max records to plot" slider to limit data points
- Start with fewer parameters and add more as needed
- Export specific message types rather than entire logs

### Missing Time Display
**Fixed**: All charts now show flight time in MM:SS format instead of raw microseconds

## 🔍 Example Workflow

### Typical Flight Analysis Session:
1. **Upload** your `.bin` log file from ArduPilot
2. **System detects** 50+ message types including ATT, POS, GPS, IMU, BAT
3. **Select ATT** message type (attitude data)
4. **Choose parameters**: Roll, Pitch, Yaw
5. **View time series** showing attitude changes during flight with MM:SS time axis
6. **Switch to POS** message type for GPS trajectory
7. **Enable 3D visualization** to see flight path
8. **Export data** for further analysis

## 🧪 Advanced Features

### Custom Parameter Analysis
- Filter parameters by name using the search box
- Combine different message types for comprehensive analysis
- View statistical summaries with mean, std dev, min, max values

### Multi-Format Support
- **DataFlash Logs** (`.bin`): ArduPilot binary logs
- **Telemetry Logs** (`.tlog`): MAVProxy telemetry files  
- **Text Logs** (`.log`): Human-readable log format

### Professional Output
- High-resolution Plotly charts suitable for reports
- Export capabilities for data sharing
- Responsive design works on desktop and tablets

## 🤝 Contributing

This is a complete, production-ready solution. Key areas for future enhancement:
- Real-time telemetry streaming
- Multi-drone log comparison
- Custom parameter calculations
- Integration with mission planning tools

## 📄 License

Open source - feel free to modify and distribute.

## 🆘 Support

If you encounter issues:
1. Check that your log file is valid MAVLink format
2. Ensure all dependencies are installed correctly  
3. Try reducing the "Max records to plot" for large files
4. Verify your Python version is 3.7+

## 🎉 Success!

You now have a universal MAVLink visualizer that works with **any** log file and displays time in user-friendly MM:SS format. No more "No suitable dynamic attributes found" errors!