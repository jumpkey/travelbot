#!/usr/bin/env python3
"""
TravelBot v1.0 Startup Script

Simple script to launch the TravelBot daemon with proper Python path handling.
"""

import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from travelbot.daemon import main

if __name__ == '__main__':
    main()
