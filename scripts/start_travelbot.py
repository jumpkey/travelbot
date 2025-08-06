#!/usr/bin/env python3
"""
TravelBot v1.0 Startup Script with Unbuffered Output

Simple script to launch the TravelBot daemon with proper Python path handling
and immediate log flushing for real-time output under nohup.
"""

import sys
import os

# Force unbuffered output for real-time logging under nohup
# This ensures logs appear immediately in log files when using nohup
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    # Fallback for Python < 3.7
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, line_buffering=True)

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from travelbot.daemon import main

if __name__ == '__main__':
    main()
