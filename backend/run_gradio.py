#!/usr/bin/env python3
"""
SmartCaption Gradio App Launcher

Usage:
    python run_gradio.py

Note: This requires a standard Python environment (not restricted sandbox).
In sandbox environments, Gradio's network checks may fail.
"""
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Import and run the app
from app.gradio_app import main

if __name__ == "__main__":
    main()
