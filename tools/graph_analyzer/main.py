#!/usr/bin/env python3
"""
H-Walker Graph Analyzer
Standalone CSV data analysis & visualization tool

Usage:
    python main.py                    # Launch GUI
    python main.py file1.csv file2.csv  # Launch with files pre-loaded
"""

import sys
import os

# Ensure package imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == '__main__':
    main()
