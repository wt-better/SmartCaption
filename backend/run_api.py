"""
Entry point for running the FastAPI server
"""
import os
import sys

# Add the backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.api import main

if __name__ == "__main__":
    main()
