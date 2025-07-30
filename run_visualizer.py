#!/usr/bin/env python3
"""
Simple launcher script for the Universal MAVLink Log Visualizer.
This script checks dependencies and starts the Streamlit application.
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is adequate."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        'streamlit',
        'pandas', 
        'numpy',
        'plotly',
        'pymavlink'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} - Not installed")
    
    return missing_packages

def install_dependencies(missing_packages):
    """Install missing dependencies."""
    print(f"\n📦 Installing {len(missing_packages)} missing packages...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 
            '--upgrade', '--quiet'
        ] + missing_packages)
        print("✅ All dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def start_application():
    """Start the Streamlit application."""
    app_file = "enhanced_streamlit_app.py"
    
    if not os.path.exists(app_file):
        print(f"❌ Application file not found: {app_file}")
        print("   Make sure all files are in the same directory")
        return False
    
    print(f"\n🚀 Starting MAVLink Log Visualizer...")
    print("   Opening in your default web browser...")
    print("   Press Ctrl+C to stop the application")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run', app_file,
            '--server.headless', 'false',
            '--browser.gatherUsageStats', 'false'
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except FileNotFoundError:
        print("❌ Streamlit not found. Installing...")
        if install_dependencies(['streamlit']):
            print("🔄 Retrying...")
            start_application()
    
    return True

def main():
    """Main launcher function."""
    print("🚁 Universal MAVLink Log Visualizer Launcher")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        input("Press Enter to exit...")
        return
    
    # Check dependencies
    print("\n📋 Checking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"\n⚠️  Missing {len(missing)} required packages")
        response = input("Install missing packages automatically? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            if not install_dependencies(missing):
                input("Press Enter to exit...")
                return
        else:
            print("\n📝 Manual installation required:")
            print("   pip install -r requirements.txt")
            print("   or:")
            print(f"   pip install {' '.join(missing)}")
            input("Press Enter to exit...")
            return
    
    # Start application
    print("\n✅ All dependencies satisfied")
    start_application()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")